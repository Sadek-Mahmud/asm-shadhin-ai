"""
security_daemon.py - Suricata & eBPF Security Monitor Daemon
Asynchronously tails Suricata EVE JSON, evaluates threats via asm-shadhin-ai,
and pushes atomic line-rate filtering rules directly into kernel eBPF maps.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    pass


import sys
from pathlib import Path

_daemon_dir = str(Path(__file__).resolve().parent)
if _daemon_dir not in sys.path:
    sys.path.insert(0, _daemon_dir)

from config import (
    SURICATA_EVE_PATH,
    SURICATA_MIN_SEVERITY,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
    DEFAULT_BLOCK_TTL_SECONDS,
    LOG_FILE,
    LOG_LEVEL,
)
from bpf_controller import BPFController
from entropy_analyzer import EncryptedTrafficAnalyzer
from mtd_service import MovingTargetDefense
from pqc_guard import PQCSigner

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE) if os.access("/var/log", os.W_OK) else logging.NullHandler()
    ]
)
logger = logging.getLogger("sec_daemon")


class SecurityMonitorDaemon:
    """Core intelligence daemon bridging Suricata IDS, asm-shadhin-ai LLM, eBPF/XDP, MTD, and PQC."""

    def __init__(self):
        self.bpf = BPFController()
        self.entropy_analyzer = EncryptedTrafficAnalyzer(min_entropy_threshold=7.1)
        self.mtd = MovingTargetDefense(hop_interval_seconds=60)
        self.pqc_signer = PQCSigner()
        self.pqc_signer.generate_keypair()
        self.eve_path = Path(SURICATA_EVE_PATH)
        self.http_client = httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT_SECONDS) if HTTPX_AVAILABLE else None
        self.is_running = True
        self._processed_ips_cache: Dict[str, float] = {}  # Deduplication cache: {ip: last_evaluated_time}
        self.cache_ttl = 300.0  # 5 minutes
        # Initialize kernel NAT forwarding for active MTD ports
        self.mtd.sync_kernel_nat_rules()

    async def query_ai_engine(self, alert_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Wrap Suricata event into strict prompt and query local asm-shadhin-ai via Ollama.
        Enforces strict JSON parsing.
        """
        src_ip = alert_event.get("src_ip", "")
        dest_port = alert_event.get("dest_port", 0)
        proto = alert_event.get("proto", "TCP")
        alert_info = alert_event.get("alert", {})
        signature = alert_info.get("signature", "Unknown Anomaly")
        severity = alert_info.get("severity", 3)
        category = alert_info.get("category", "General")

        prompt = (
            f"INPUT_SURICATA_EVENT:\n"
            f"Source IP: {src_ip}\n"
            f"Target Port: {dest_port}\n"
            f"Protocol: {proto}\n"
            f"Signature: {signature}\n"
            f"Severity: {severity}\n"
            f"Category: {category}\n\n"
            f"Analyze threat and return valid JSON per operational schema."
        )

        try:
            raw_text = None
            if HTTPX_AVAILABLE and self.http_client:
                response = await self.http_client.post(
                    "/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.85,
                            "num_predict": 256
                        }
                    }
                )
                if response.status_code == 200:
                    body = response.json()
                    # Detect Ollama-level model output errors (empty output / tool call conflict)
                    if "error" in body:
                        logger.warning("Ollama model error: %s — using heuristic fallback.", body["error"])
                        return self._heuristic_fallback(alert_event)
                    raw_text = body.get("response", "").strip()
                else:
                    logger.error("Ollama query failed with HTTP %d: %s", response.status_code, response.text)
                    return self._heuristic_fallback(alert_event)
            else:
                # Built-in standard library urllib fallback (zero-dependency)
                import urllib.request
                import urllib.error
                url = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
                payload = json.dumps({
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.85,
                        "num_predict": 256
                    }
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                loop = asyncio.get_event_loop()
                def _do_req():
                    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS) as resp:
                        return json.loads(resp.read().decode("utf-8"))
                res_data = await loop.run_in_executor(None, _do_req)
                if "error" in res_data:
                    logger.warning("Ollama urllib error: %s — using heuristic fallback.", res_data["error"])
                    return self._heuristic_fallback(alert_event)
                raw_text = res_data.get("response", "").strip()

            if not raw_text:
                logger.warning("Ollama returned empty response for model '%s' — using heuristic fallback.", OLLAMA_MODEL)
                return self._heuristic_fallback(alert_event)

            # Clean possible edge-case markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`").replace("json\n", "", 1)

            parsed = json.loads(raw_text)
            return parsed

        except Exception as e:
            # Check for connection error
            err_msg = str(e).lower()
            if "connection" in err_msg or "refused" in err_msg or "connecterror" in err_msg:
                logger.warning("Could not connect to Ollama at %s. Falling back to deterministic heuristic.", OLLAMA_HOST)
            elif isinstance(e, json.JSONDecodeError):
                logger.error("Failed to parse JSON from asm-shadhin-ai: %s", e)
            else:
                logger.warning("Error querying LLM (%s). Using heuristic fallback.", e)
            return self._heuristic_fallback(alert_event)

    def _heuristic_fallback(self, alert_event: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic safety fallback when Ollama is busy or initializing."""
        src_ip = alert_event.get("src_ip", "")
        dest_port = alert_event.get("dest_port", 0)
        severity = alert_event.get("alert", {}).get("severity", 3)

        if severity == 1:
            action = "BLOCK_IMMEDIATE"
            rule_action = "XDP_DROP"
        else:
            action = "TARPIT_REDIRECT"
            rule_action = "XDP_REDIRECT_TARPIT"

        return {
            "verdict": "MALICIOUS",
            "threat_type": "HEURISTIC_SEV_TRIGGER",
            "confidence": 0.90,
            "action": action,
            "source_ip": src_ip,
            "target_port": dest_port,
            "reason": "High-severity Suricata alert triggered deterministic fallback rule.",
            "ebpf_rule": {
                "action": rule_action,
                "ip": src_ip,
                "ttl_seconds": DEFAULT_BLOCK_TTL_SECONDS
            }
        }

    async def process_eve_line(self, line: str):
        """Parse one line of Suricata EVE JSON and act on high-priority events."""
        if not line.strip():
            return

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return

        if event.get("event_type") != "alert":
            return

        alert = event.get("alert", {})
        severity = alert.get("severity", 99)
        src_ip = event.get("src_ip")

        if not src_ip or severity > SURICATA_MIN_SEVERITY:
            return

        # Skip loopback or internal private if whitelisted
        if src_ip.startswith("127.") or src_ip == "::1":
            return

        # Deduplication check with bounded LRU memory protection (max 10,000 active entries)
        now = time.time()
        last_eval = self._processed_ips_cache.get(src_ip, 0)
        if (now - last_eval) < self.cache_ttl:
            return

        # Memory leak safeguard: evict oldest entries if cache exceeds 10,000
        if len(self._processed_ips_cache) >= 10000:
            oldest_keys = sorted(self._processed_ips_cache, key=self._processed_ips_cache.get)[:2000]
            for k in oldest_keys:
                del self._processed_ips_cache[k]

        self._processed_ips_cache[src_ip] = now
        logger.info("[ALERT DETECTED] Suricata alert from %s (Severity: %d): %s", src_ip, severity, alert.get("signature"))

        # Dispatch to asm-shadhin-ai for inline judgment
        decision = await self.query_ai_engine(event)
        if not decision:
            return

        verdict = decision.get("verdict")
        action = decision.get("action")
        confidence = decision.get("confidence", 0.0)
        target_ip = decision.get("source_ip", src_ip)

        logger.info("[LLM VERDICT] IP: %s | Verdict: %s | Action: %s | Conf: %.2f", target_ip, verdict, action, confidence)

        if verdict == "MALICIOUS" and confidence >= 0.80:
            if action == "BLOCK_IMMEDIATE":
                ttl = decision.get("ebpf_rule", {}).get("ttl_seconds", DEFAULT_BLOCK_TTL_SECONDS)
                self.bpf.block_ip(target_ip, ttl_seconds=ttl, reason_code=3)
                # Create immutable PQC-signed audit telemetry record
                audit_msg = f"BLOCK:{target_ip}:{ttl}:{time.time()}".encode("utf-8")
                sig = self.pqc_signer.sign(audit_msg)
                logger.debug("[PQC-AUDIT] Decision sealed with ML-DSA signature: %s...", sig[:16].hex())
            elif action == "TARPIT_REDIRECT":
                self.bpf.divert_to_tarpit(target_ip, redirect_port=8088)


    async def tail_eve_log(self):
        """Asynchronous non-blocking file tailing supporting log rotation."""
        logger.info("[*] Initializing EVE log tailer on: %s", self.eve_path)

        while self.is_running:
            if not self.eve_path.exists():
                logger.warning("EVE log not found at %s. Waiting for Suricata...", self.eve_path)
                await asyncio.sleep(5.0)
                continue

            try:
                with open(self.eve_path, "r", encoding="utf-8", errors="replace") as f:
                    # Seek to end on startup to only process new alerts
                    f.seek(0, os.SEEK_END)
                    init_ino = os.fstat(f.fileno()).st_ino
                    logger.info("[✓] Actively tailing %s from current EOF", self.eve_path)

                    while self.is_running:
                        line = f.readline()
                        if line:
                            await self.process_eve_line(line)
                        else:
                            # Check for log rotation (file truncated, renamed, or new inode)
                            try:
                                curr_stat = os.stat(self.eve_path)
                                if f.tell() > curr_stat.st_size or curr_stat.st_ino != init_ino:
                                    logger.info("[*] Log rotation detected (size/inode shift). Reopening %s", self.eve_path)
                                    break
                            except FileNotFoundError:
                                break
                            await asyncio.sleep(0.1)

            except Exception as e:
                logger.error("Error reading EVE log: %s", e)
                await asyncio.sleep(2.0)

    async def periodic_maintenance_loop(self):
        """Periodic background tasks: TTL sweeping, cache purging, and BPF health metrics."""
        while self.is_running:
            await asyncio.sleep(60.0)
            try:
                swept = self.bpf.sweep_expired_ttls()
                if swept > 0:
                    logger.info("[*] Swept %d expired IP entries from eBPF map.", swept)

                # Purge in-memory deduplication cache
                now = time.time()
                self._processed_ips_cache = {
                    ip: ts for ip, ts in self._processed_ips_cache.items() if (now - ts) < self.cache_ttl
                }
            except Exception as e:
                logger.exception("Error in maintenance loop: %s", e)

    async def start(self):
        """Launch main daemon loops concurrently."""
        logger.info("=================================================================")
        logger.info("  Q-Vigilance AI: Autonomous Post-Quantum Cyber Defense Agent")
        logger.info("  Fast-Path: eBPF/XDP | Intelligence: Q-Vigilance AI | Protocol: NIST PQC")
        logger.info("=================================================================")

        await asyncio.gather(
            self.tail_eve_log(),
            self.periodic_maintenance_loop(),
        )

    def stop(self):
        """Clean shutdown handler."""
        logger.info("[*] Stopping Security Monitor Daemon...")
        self.is_running = False


if __name__ == "__main__":
    daemon = SecurityMonitorDaemon()

    def handle_signal(sig, frame):
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Daemon halted by user.")
