#!/usr/bin/env python3
"""
03_performance_metrics_logger.py
ASM-Shadhin-AI eBPF/XDP Testbed — Real-Time Performance & Metrics Logger (VM-2 SUT)

PURPOSE:
    Collect real-time performance metrics on the SUT during tcpreplay benchmark runs:
      • eBPF/XDP drop rates      — via bpftool map dump + /proc/net/dev
      • CPU/RAM utilization       — of the Ollama/LLM daemon and kernel threads
      • Alert queue backlog       — from the sec-daemon IPC socket or log tail
      • Packet processing latency — inferred from eBPF ringbuf timestamps

OUTPUT:
    • benchmark_results.csv       — structured per-sample metrics
    • summary statistics          — printed to console (mean, P99, loss %)

USAGE:
    sudo python3 03_performance_metrics_logger.py \
        --iface eth1 \
        [--interval 0.5] \
        [--duration 300] \
        [--output /opt/asm-testbed-results/benchmark_results.csv] \
        [--bpf-map /sys/fs/bpf/blocked_ips_map] \
        [--llm-process ollama]

REQUIREMENTS:
    pip install psutil
    (bpftool must be installed: apt-get install linux-tools-generic)

TESTED ON: Ubuntu Server 22.04 LTS, kernel 5.15+, Python 3.10+
"""

import argparse
import csv
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import time
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional psutil — install if missing
# ---------------------------------------------------------------------------
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[WARN] psutil not found. Install: pip install psutil", file=sys.stderr)
    print("       CPU/RAM metrics will be limited.", file=sys.stderr)

# ---------------------------------------------------------------------------
# ANSI Colors
# ---------------------------------------------------------------------------
R = '\033[0;31m'; G = '\033[0;32m'; Y = '\033[1;33m'
C = '\033[0;36m'; B = '\033[0;34m'; BOLD = '\033[1m'; NC = '\033[0m'


# ===========================================================================
# Helper: run a shell command, return stdout (or "" on error)
# ===========================================================================
def _run(cmd: List[str], timeout: float = 5.0) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return ""


# ===========================================================================
# /proc/net/dev reader
# ===========================================================================
class NetDevReader:
    """Fast parser for /proc/net/dev interface statistics."""

    FIELDS = [
        "rx_bytes", "rx_packets", "rx_errs", "rx_drop",
        "rx_fifo", "rx_frame", "rx_compressed", "rx_multicast",
        "tx_bytes", "tx_packets", "tx_errs", "tx_drop",
        "tx_fifo", "tx_colls", "tx_carrier", "tx_compressed",
    ]

    def read(self, iface: str) -> Dict[str, int]:
        try:
            with open("/proc/net/dev") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{iface}:"):
                        parts = line.split(":")[1].split()
                        return dict(zip(self.FIELDS, (int(x) for x in parts)))
        except OSError:
            pass
        return {f: 0 for f in self.FIELDS}

    def delta(self, a: Dict, b: Dict) -> Dict:
        """Return per-field deltas (b - a)."""
        return {k: b[k] - a.get(k, 0) for k in b}


# ===========================================================================
# eBPF Map Inspector via bpftool
# ===========================================================================
class BPFMapInspector:
    """
    Reads eBPF map statistics using bpftool.
    Falls back to /sys/kernel/debug/tracing if bpftool unavailable.
    """

    def __init__(self, blocked_map: str, tarpit_map: str):
        self.blocked_map = Path(blocked_map)
        self.tarpit_map  = Path(tarpit_map)
        self._bpftool_available = bool(_run(["which", "bpftool"]))

    def get_blocked_ip_count(self) -> int:
        """Return number of entries in the blocked_ips_map."""
        if not self.blocked_map.exists():
            return -1
        if self._bpftool_available:
            out = _run(["bpftool", "map", "dump", "pinned", str(self.blocked_map)])
            # Each entry is one JSON object in the array
            try:
                entries = json.loads(f"[{out}]") if out else []
                return len(entries)
            except json.JSONDecodeError:
                # Fallback: count "key" lines
                return out.count('"key"')
        return -1

    def get_xdp_drop_rate(self, iface: str) -> Dict[str, int]:
        """
        Read XDP program statistics via bpftool prog show.
        Returns dict with 'run_cnt' and 'run_time_ns'.
        """
        result = {"xdp_run_cnt": 0, "xdp_run_time_ns": 0}
        if not self._bpftool_available:
            return result

        out = _run(["bpftool", "prog", "show", "--json"])
        try:
            progs = json.loads(out) if out else []
            for prog in progs:
                if prog.get("type") == "xdp":
                    result["xdp_run_cnt"]     = prog.get("run_cnt", 0)
                    result["xdp_run_time_ns"] = prog.get("run_time_ns", 0)
                    break
        except (json.JSONDecodeError, TypeError):
            pass
        return result

    def get_map_info(self) -> Dict:
        """Return name/id info for all pinned BPF maps on /sys/fs/bpf."""
        maps = {}
        if not self._bpftool_available:
            return maps
        out = _run(["bpftool", "map", "show", "--json"])
        try:
            for m in json.loads(out):
                maps[m.get("name", "?")] = {
                    "id":       m.get("id"),
                    "type":     m.get("type"),
                    "max_ents": m.get("max_entries"),
                }
        except (json.JSONDecodeError, TypeError):
            pass
        return maps


# ===========================================================================
# Process Monitor (LLM daemon + kernel threads)
# ===========================================================================
class ProcessMonitor:
    """Monitor CPU/RAM of named processes using psutil."""

    def __init__(self, process_names: List[str]):
        self.names = [n.lower() for n in process_names]
        self._cache: Dict[int, psutil.Process] = {}

    def _refresh_cache(self):
        if not HAS_PSUTIL:
            return
        active_pids = set()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pname = (proc.info['name'] or "").lower()
                cmdline = " ".join(proc.info.get('cmdline') or []).lower()
                if any(n in pname or n in cmdline for n in self.names):
                    active_pids.add(proc.pid)
                    if proc.pid not in self._cache:
                        self._cache[proc.pid] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        # Remove stale pids
        for pid in list(self._cache.keys()):
            if pid not in active_pids:
                del self._cache[pid]

    def get_aggregate_metrics(self) -> Dict[str, float]:
        """Return aggregated CPU%, RSS MB, VMS MB across all matched processes."""
        metrics = {
            "llm_cpu_pct":    0.0,
            "llm_rss_mb":     0.0,
            "llm_vms_mb":     0.0,
            "llm_proc_count": 0,
            "llm_threads":    0,
        }
        if not HAS_PSUTIL:
            return metrics

        self._refresh_cache()
        for proc in list(self._cache.values()):
            try:
                cpu  = proc.cpu_percent(interval=None)
                mem  = proc.memory_info()
                thrd = proc.num_threads()
                metrics["llm_cpu_pct"]    += cpu
                metrics["llm_rss_mb"]     += mem.rss / 1048576
                metrics["llm_vms_mb"]     += mem.vms / 1048576
                metrics["llm_proc_count"] += 1
                metrics["llm_threads"]    += thrd
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return metrics


# ===========================================================================
# Alert Queue Monitor (tails the sec-daemon log or IPC socket)
# ===========================================================================
class AlertQueueMonitor:
    """
    Estimates the alert queue backlog by counting recent QUEUED vs PROCESSED
    entries in /var/log/sec_monitor.log, or by querying a Unix socket.
    """

    LOG_PATH = Path("/var/log/sec_monitor.log")
    SOCKET_PATH = Path("/run/asm-daemon/metrics.sock")

    def __init__(self):
        self._last_pos = 0
        self._queued   = 0
        self._processed = 0
        self._socket_tried = False
        self._log_fd: Optional[object] = None
        self._open_log()

    def _open_log(self):
        if self.LOG_PATH.exists():
            try:
                self._log_fd = open(self.LOG_PATH, 'r')
                self._log_fd.seek(0, 2)  # Seek to end
            except PermissionError:
                self._log_fd = None

    def get_queue_depth(self) -> Dict[str, int]:
        # Try Unix domain socket first (fastest path)
        if self.SOCKET_PATH.exists() and not self._socket_tried:
            self._socket_tried = True
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(str(self.SOCKET_PATH))
                    s.sendall(b'{"cmd":"metrics"}')
                    data = s.recv(4096).decode()
                    info = json.loads(data)
                    return {
                        "alert_queue_depth":   info.get("queue_size", 0),
                        "alert_processed_total": info.get("processed_total", 0),
                    }
            except Exception:
                pass

        # Fallback: tail log file
        new_queued = new_proc = 0
        if self._log_fd:
            try:
                for line in self._log_fd:
                    if "QUEUED" in line or "enqueue" in line.lower():
                        new_queued += 1
                    elif "PROCESSED" in line or "LLM verdict" in line.lower():
                        new_proc += 1
            except Exception:
                pass

        self._queued    += new_queued
        self._processed += new_proc
        depth = max(0, self._queued - self._processed)
        return {"alert_queue_depth": depth, "alert_processed_total": self._processed}

    def close(self):
        if self._log_fd:
            self._log_fd.close()


# ===========================================================================
# System CPU / Memory Reader
# ===========================================================================
class SystemResourceMonitor:
    """Global system CPU/RAM via psutil or /proc/stat fallback."""

    def __init__(self):
        self._last_stat: Optional[Dict] = None

    def _read_proc_stat(self) -> Dict[str, int]:
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        keys = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"]
        return dict(zip(keys, (int(x) for x in parts[1:])))

    def get_system_metrics(self) -> Dict[str, float]:
        metrics: Dict[str, float] = {}

        if HAS_PSUTIL:
            metrics["sys_cpu_pct"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            metrics["sys_ram_used_mb"]  = vm.used  / 1048576
            metrics["sys_ram_total_mb"] = vm.total / 1048576
            metrics["sys_ram_pct"]      = vm.percent
            # Per-core softirq load (kernel / BPF thread indicator)
            try:
                metrics["sys_softirq_pct"] = sum(
                    c.softirq for c in psutil.cpu_times(percpu=True)
                ) / psutil.cpu_count()
            except (AttributeError, TypeError):
                metrics["sys_softirq_pct"] = 0.0
        else:
            # /proc/stat fallback
            curr = self._read_proc_stat()
            if self._last_stat:
                diff = {k: curr[k] - self._last_stat.get(k, 0) for k in curr}
                total = sum(diff.values())
                idle  = diff.get("idle", 0) + diff.get("iowait", 0)
                metrics["sys_cpu_pct"] = 100.0 * (total - idle) / max(total, 1)
            else:
                metrics["sys_cpu_pct"] = 0.0
            self._last_stat = curr

            # /proc/meminfo fallback
            meminfo: Dict[str, int] = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":")
                    meminfo[k.strip()] = int(v.strip().split()[0])
            total_kb = meminfo.get("MemTotal", 0)
            free_kb  = meminfo.get("MemAvailable", 0)
            used_kb  = total_kb - free_kb
            metrics["sys_ram_used_mb"]  = used_kb  / 1024
            metrics["sys_ram_total_mb"] = total_kb / 1024
            metrics["sys_ram_pct"]      = 100.0 * used_kb / max(total_kb, 1)
            metrics["sys_softirq_pct"]  = 0.0

        return metrics


# ===========================================================================
# Latency Estimator (from eBPF ringbuf timestamps or heuristic)
# ===========================================================================
class LatencyEstimator:
    """
    Estimates packet processing latency using a rolling window of
    inter-packet timestamps from the eBPF RingBuffer event log,
    or from bpftool prog stats run_time_ns / run_cnt.
    """

    def __init__(self, ringbuf_path: str, window: int = 1000):
        self.ringbuf_path = Path(ringbuf_path)
        self.window = window
        self._latencies: deque = deque(maxlen=window)
        self._last_run_cnt = 0
        self._last_run_ns  = 0
        self._bpftool_ok   = bool(_run(["which", "bpftool"]))

    def sample_from_bpftool(self) -> Optional[float]:
        """
        Read XDP program run_cnt and run_time_ns to compute
        mean per-invocation latency (ns).
        """
        if not self._bpftool_ok:
            return None
        out = _run(["bpftool", "prog", "show", "--json"])
        try:
            progs = json.loads(out)
            for prog in progs:
                if prog.get("type") == "xdp":
                    cnt = prog.get("run_cnt", 0)
                    ns  = prog.get("run_time_ns", 0)
                    delta_cnt = cnt - self._last_run_cnt
                    delta_ns  = ns  - self._last_run_ns
                    self._last_run_cnt = cnt
                    self._last_run_ns  = ns
                    if delta_cnt > 0:
                        mean_lat = delta_ns / delta_cnt
                        self._latencies.append(mean_lat)
                        return mean_lat
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def get_stats(self) -> Dict[str, float]:
        """Return mean, p50, p99 latency in microseconds."""
        if not self._latencies:
            return {"lat_mean_us": 0.0, "lat_p50_us": 0.0, "lat_p99_us": 0.0, "lat_max_us": 0.0}
        # Convert ns → µs
        lat_us = sorted(x / 1000 for x in self._latencies)
        n = len(lat_us)
        p50_idx = int(n * 0.50)
        p99_idx = int(n * 0.99)
        return {
            "lat_mean_us": sum(lat_us) / n,
            "lat_p50_us":  lat_us[p50_idx],
            "lat_p99_us":  lat_us[min(p99_idx, n - 1)],
            "lat_max_us":  lat_us[-1],
        }


# ===========================================================================
# CSV Column Schema
# ===========================================================================
CSV_COLUMNS = [
    "timestamp",
    "elapsed_sec",
    # Interface counters (delta)
    "rx_packets_delta",
    "rx_bytes_delta",
    "rx_drop_delta",
    "tx_packets_delta",
    "tx_bytes_delta",
    "rx_pps",
    "rx_mbps",
    # eBPF metrics
    "blocked_ip_count",
    "xdp_run_cnt_delta",
    "xdp_run_time_ns_delta",
    "xdp_mean_lat_ns",
    # Latency estimates
    "lat_mean_us",
    "lat_p50_us",
    "lat_p99_us",
    "lat_max_us",
    # LLM daemon
    "llm_cpu_pct",
    "llm_rss_mb",
    "llm_vms_mb",
    "llm_proc_count",
    "llm_threads",
    # Alert queue
    "alert_queue_depth",
    "alert_processed_total",
    # System
    "sys_cpu_pct",
    "sys_ram_used_mb",
    "sys_ram_pct",
    "sys_softirq_pct",
]


# ===========================================================================
# Main Collector
# ===========================================================================
class BenchmarkCollector:
    def __init__(self, args: argparse.Namespace):
        self.iface    = args.iface
        self.interval = args.interval
        self.duration = args.duration
        self.output   = Path(args.output)
        self.verbose  = args.verbose

        self.net_reader   = NetDevReader()
        self.bpf_insp     = BPFMapInspector(args.bpf_map, args.tarpit_map)
        self.proc_mon     = ProcessMonitor(args.llm_process.split(","))
        self.alert_mon    = AlertQueueMonitor()
        self.sys_mon      = SystemResourceMonitor()
        self.lat_est      = LatencyEstimator(args.ringbuf, window=2000)

        self._running = True
        self._start   = time.monotonic()
        self._prev_net: Dict = {}
        self._prev_xdp: Dict = {"xdp_run_cnt": 0, "xdp_run_time_ns": 0}

        # Warmup psutil CPU percent (first call always returns 0.0)
        if HAS_PSUTIL:
            import psutil as _ps
            _ps.cpu_percent(interval=None)
            for p in _ps.process_iter():
                try:
                    p.cpu_percent(interval=None)
                except Exception:
                    pass
            time.sleep(0.2)

    def _sample(self) -> Dict:
        ts       = datetime.utcnow().isoformat() + "Z"
        elapsed  = time.monotonic() - self._start

        # ── Network ──────────────────────────────────────────────────────────
        curr_net = self.net_reader.read(self.iface)
        if self._prev_net:
            delta = self.net_reader.delta(self._prev_net, curr_net)
        else:
            delta = {k: 0 for k in curr_net}
        self._prev_net = curr_net.copy()

        rx_pps  = delta["rx_packets"] / self.interval
        rx_mbps = (delta["rx_bytes"] * 8) / (self.interval * 1_000_000)

        # ── eBPF / XDP ───────────────────────────────────────────────────────
        blocked_count = self.bpf_insp.get_blocked_ip_count()
        curr_xdp      = self.bpf_insp.get_xdp_drop_rate(self.iface)
        xdp_cnt_d     = curr_xdp["xdp_run_cnt"]     - self._prev_xdp["xdp_run_cnt"]
        xdp_ns_d      = curr_xdp["xdp_run_time_ns"] - self._prev_xdp["xdp_run_time_ns"]
        xdp_mean_ns   = xdp_ns_d / xdp_cnt_d if xdp_cnt_d > 0 else 0
        self._prev_xdp = curr_xdp.copy()

        # Latency (from bpftool prog stats)
        self.lat_est.sample_from_bpftool()
        lat_stats = self.lat_est.get_stats()

        # ── Process metrics ───────────────────────────────────────────────────
        proc_metrics = self.proc_mon.get_aggregate_metrics()

        # ── Alert queue ───────────────────────────────────────────────────────
        alert_metrics = self.alert_mon.get_queue_depth()

        # ── System ───────────────────────────────────────────────────────────
        sys_metrics = self.sys_mon.get_system_metrics()

        row = {
            "timestamp":            ts,
            "elapsed_sec":          f"{elapsed:.3f}",
            "rx_packets_delta":     delta["rx_packets"],
            "rx_bytes_delta":       delta["rx_bytes"],
            "rx_drop_delta":        delta["rx_drop"],
            "tx_packets_delta":     delta["tx_packets"],
            "tx_bytes_delta":       delta["tx_bytes"],
            "rx_pps":               f"{rx_pps:.1f}",
            "rx_mbps":              f"{rx_mbps:.3f}",
            "blocked_ip_count":     blocked_count,
            "xdp_run_cnt_delta":    xdp_cnt_d,
            "xdp_run_time_ns_delta":xdp_ns_d,
            "xdp_mean_lat_ns":      f"{xdp_mean_ns:.1f}",
            "lat_mean_us":          f"{lat_stats['lat_mean_us']:.3f}",
            "lat_p50_us":           f"{lat_stats['lat_p50_us']:.3f}",
            "lat_p99_us":           f"{lat_stats['lat_p99_us']:.3f}",
            "lat_max_us":           f"{lat_stats['lat_max_us']:.3f}",
            "llm_cpu_pct":          f"{proc_metrics['llm_cpu_pct']:.1f}",
            "llm_rss_mb":           f"{proc_metrics['llm_rss_mb']:.1f}",
            "llm_vms_mb":           f"{proc_metrics['llm_vms_mb']:.1f}",
            "llm_proc_count":       proc_metrics["llm_proc_count"],
            "llm_threads":          proc_metrics["llm_threads"],
            "alert_queue_depth":    alert_metrics["alert_queue_depth"],
            "alert_processed_total":alert_metrics["alert_processed_total"],
            "sys_cpu_pct":          f"{sys_metrics['sys_cpu_pct']:.1f}",
            "sys_ram_used_mb":      f"{sys_metrics['sys_ram_used_mb']:.1f}",
            "sys_ram_pct":          f"{sys_metrics['sys_ram_pct']:.1f}",
            "sys_softirq_pct":      f"{sys_metrics.get('sys_softirq_pct', 0):.2f}",
        }
        return row

    def _print_live(self, row: Dict, n: int):
        """Print a compact live status line every sample."""
        if n % 20 == 0:  # Header every 20 rows
            print(f"\n{BOLD}{'Elapsed':>8}  {'RX Mpps':>8}  {'RX Mbps':>9}  "
                  f"{'Drop/s':>7}  {'XDP lat':>8}  {'P99 µs':>7}  "
                  f"{'LLM CPU%':>8}  {'LLM RAM':>8}  {'SysCPU%':>8}  "
                  f"{'Queue':>6}{NC}")
            print("─" * 100)

        rx_pps_m = float(row["rx_pps"]) / 1_000_000
        print(
            f"{float(row['elapsed_sec']):>8.1f}  "
            f"{rx_pps_m:>8.3f}M  "
            f"{float(row['rx_mbps']):>8.2f}M  "
            f"{row['rx_drop_delta']:>7}  "
            f"{float(row['xdp_mean_lat_ns']):>7.0f}ns  "
            f"{float(row['lat_p99_us']):>7.2f}µs  "
            f"{float(row['llm_cpu_pct']):>8.1f}%  "
            f"{float(row['llm_rss_mb']):>7.0f}M  "
            f"{float(row['sys_cpu_pct']):>8.1f}%  "
            f"{row['alert_queue_depth']:>6}",
            flush=True,
        )

    def run(self):
        """Main collection loop — writes to CSV and prints live stats."""
        self.output.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n{BOLD}{B}")
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║   ASM-Shadhin-AI eBPF/XDP SUT — Real-Time Metrics Logger        ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print(NC)
        print(f"  Interface  : {BOLD}{self.iface}{NC}")
        print(f"  Interval   : {BOLD}{self.interval}s{NC}")
        print(f"  Duration   : {BOLD}{self.duration}s{NC} (0 = run until Ctrl+C)")
        print(f"  Output CSV : {BOLD}{self.output}{NC}")
        print(f"  BPF Map    : {BOLD}{self.bpf_insp.blocked_map}{NC}")
        print()

        bpf_maps = self.bpf_insp.get_map_info()
        if bpf_maps:
            print(f"  {G}Detected BPF Maps:{NC}")
            for name, info in bpf_maps.items():
                print(f"    • {name}  (id={info['id']}, type={info['type']}, max_ents={info['max_ents']})")
        else:
            print(f"  {Y}No BPF maps detected via bpftool — metrics will rely on /proc/net/dev.{NC}")
        print()

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        samples: List[Dict] = []
        n = 0

        with open(self.output, "w", newline="") as csvf:
            writer = csv.DictWriter(csvf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()

            while self._running:
                t0 = time.monotonic()

                row = self._sample()
                writer.writerow(row)
                csvf.flush()
                samples.append(row)
                n += 1

                if self.verbose or True:  # Always print live
                    self._print_live(row, n)

                # Duration check
                elapsed = time.monotonic() - self._start
                if self.duration > 0 and elapsed >= self.duration:
                    print(f"\n{G}[✓] Duration {self.duration}s elapsed — stopping collection.{NC}")
                    break

                # Sleep for remainder of interval
                sleep_t = self.interval - (time.monotonic() - t0)
                if sleep_t > 0:
                    time.sleep(sleep_t)

        self._print_summary(samples)
        self.alert_mon.close()

    def _handle_signal(self, signum, frame):
        print(f"\n{Y}[!] Signal {signum} received — stopping...{NC}")
        self._running = False

    def _print_summary(self, samples: List[Dict]):
        """Compute and print final summary statistics."""
        if not samples:
            print(f"{Y}[!] No samples collected.{NC}")
            return

        def safe_floats(key: str) -> List[float]:
            out = []
            for s in samples:
                try:
                    out.append(float(s[key]))
                except (ValueError, KeyError):
                    pass
            return out

        def stats(vals: List[float]) -> Dict:
            if not vals:
                return {"mean": 0, "p50": 0, "p99": 0, "max": 0, "min": 0}
            s = sorted(vals)
            n = len(s)
            return {
                "mean": sum(s) / n,
                "p50":  s[int(n * 0.50)],
                "p99":  s[min(int(n * 0.99), n - 1)],
                "max":  s[-1],
                "min":  s[0],
            }

        rx_mbps_vals  = safe_floats("rx_mbps")
        drop_vals     = safe_floats("rx_drop_delta")
        lat_p99_vals  = safe_floats("lat_p99_us")
        lat_mean_vals = safe_floats("lat_mean_us")
        cpu_vals      = safe_floats("sys_cpu_pct")
        llm_cpu_vals  = safe_floats("llm_cpu_pct")
        queue_vals    = safe_floats("alert_queue_depth")

        rx_s  = stats(rx_mbps_vals)
        dr_s  = stats(drop_vals)
        lat_s = stats(lat_p99_vals)
        cpu_s = stats(cpu_vals)

        total_rx_pkts = sum(safe_floats("rx_packets_delta"))
        total_drops   = sum(drop_vals)
        loss_pct      = 100.0 * total_drops / max(total_rx_pkts + total_drops, 1)

        print(f"\n{BOLD}{G}")
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║                  BENCHMARK SUMMARY STATISTICS                   ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print(NC)

        print(f"  {BOLD}Total Samples Collected : {len(samples)}{NC}")
        print(f"  {BOLD}Total Collection Time   : {float(samples[-1]['elapsed_sec']):.1f}s{NC}")
        print()

        print(f"  {BOLD}── Throughput (Mbps) ─────────────────────────────────────{NC}")
        print(f"    Mean   : {rx_s['mean']:>10.2f} Mbps")
        print(f"    P50    : {rx_s['p50']:>10.2f} Mbps")
        print(f"    P99    : {rx_s['p99']:>10.2f} Mbps")
        print(f"    Max    : {rx_s['max']:>10.2f} Mbps")
        print()

        print(f"  {BOLD}── Processing Latency (µs) ───────────────────────────────{NC}")
        lat_mean_s = stats(lat_mean_vals)
        print(f"    Mean   : {lat_mean_s['mean']:>10.3f} µs")
        print(f"    P50    : {lat_s['p50']:>10.3f} µs")
        print(f"    P99    : {lat_s['p99']:>10.3f} µs  ← key SLA metric")
        print(f"    Max    : {lat_s['max']:>10.3f} µs")
        print()

        print(f"  {BOLD}── Packet Loss ───────────────────────────────────────────{NC}")
        print(f"    Total RX Pkts  : {int(total_rx_pkts):>12,}")
        print(f"    Total Drops    : {int(total_drops):>12,}")
        dr_color = R if loss_pct > 1.0 else G
        print(f"    Loss %         : {dr_color}{loss_pct:>11.4f}%{NC}  (< 1% = acceptable)")
        print()

        print(f"  {BOLD}── CPU Utilization ───────────────────────────────────────{NC}")
        print(f"    System Mean    : {cpu_s['mean']:>10.1f}%")
        print(f"    System P99     : {cpu_s['p99']:>10.1f}%")
        llm_s = stats(llm_cpu_vals)
        print(f"    LLM Daemon Mean: {llm_s['mean']:>10.1f}%")
        print(f"    LLM Daemon P99 : {llm_s['p99']:>10.1f}%")
        print()

        queue_s = stats(queue_vals)
        print(f"  {BOLD}── Alert Queue Backlog ───────────────────────────────────{NC}")
        print(f"    Mean Depth     : {queue_s['mean']:>10.1f}")
        print(f"    Max Depth      : {queue_s['max']:>10.0f}")
        q_color = R if queue_s['max'] > 50 else G
        print(f"    Status         : {q_color}{'BACKLOGGED' if queue_s['max'] > 50 else 'HEALTHY'}{NC}")
        print()

        print(f"  {G}{BOLD}Results exported to: {self.output}{NC}")
        print()

        # ── SLA Assessment ───────────────────────────────────────────────────
        print(f"  {BOLD}── SLA Assessment ────────────────────────────────────────{NC}")
        sla_ok = True

        checks = [
            ("Packet Loss < 1%",      loss_pct < 1.0,          f"{loss_pct:.4f}%"),
            ("P99 Latency < 100µs",   lat_s['p99'] < 100.0,    f"{lat_s['p99']:.2f}µs"),
            ("Mean Latency < 10µs",   lat_mean_s['mean'] < 10.0, f"{lat_mean_s['mean']:.2f}µs"),
            ("Sys CPU P99 < 90%",     cpu_s['p99'] < 90.0,     f"{cpu_s['p99']:.1f}%"),
            ("Alert Queue < 50",      queue_s['max'] < 50,      f"max={queue_s['max']:.0f}"),
        ]

        for check_name, passed, value in checks:
            icon  = f"{G}[PASS]{NC}" if passed else f"{R}[FAIL]{NC}"
            print(f"    {icon}  {check_name:<30} actual: {value}")
            if not passed:
                sla_ok = False

        print()
        if sla_ok:
            print(f"  {G}{BOLD}✓ ALL SLA CHECKS PASSED — System performing within targets.{NC}")
        else:
            print(f"  {R}{BOLD}✗ ONE OR MORE SLA CHECKS FAILED — Review metrics above.{NC}")
        print()


# ===========================================================================
# CLI Entry Point
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="ASM-Shadhin-AI eBPF/XDP SUT Real-Time Metrics Logger",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--iface",       default="eth1",
                        help="Network interface under test (e.g. eth1)")
    parser.add_argument("--interval",    type=float, default=0.5,
                        help="Sampling interval in seconds")
    parser.add_argument("--duration",    type=float, default=0,
                        help="Total collection duration in seconds (0=until Ctrl+C)")
    parser.add_argument("--output",      default="/opt/asm-testbed-results/benchmark_results.csv",
                        help="Output CSV path")
    parser.add_argument("--bpf-map",     default="/sys/fs/bpf/blocked_ips_map",
                        help="Path to pinned blocked_ips BPF map")
    parser.add_argument("--tarpit-map",  default="/sys/fs/bpf/tarpit_ips_map",
                        help="Path to pinned tarpit BPF map")
    parser.add_argument("--ringbuf",     default="/sys/fs/bpf/packet_metrics_rb",
                        help="Path to pinned packet metrics RingBuffer map")
    parser.add_argument("--llm-process", default="ollama,asm-shadhin,security_daemon",
                        help="Comma-separated process name(s) to monitor for LLM daemon")
    parser.add_argument("--verbose",     action="store_true",
                        help="Extra verbose output")

    args = parser.parse_args()

    # Privilege check
    if os.geteuid() != 0:
        print(f"{Y}[!] WARNING: Not running as root. Some metrics (bpftool, IRQ) may be unavailable.{NC}")

    collector = BenchmarkCollector(args)
    collector.run()


if __name__ == "__main__":
    main()
