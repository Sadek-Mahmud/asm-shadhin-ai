# eBPF/XDP Testbed — UTM VM Benchmark Suite
**ASM-Shadhin-AI · Real-World Performance Validation**

> Full testbed for validating the eBPF/XDP fast-path firewall and local LLM daemon under production-representative network loads using two Ubuntu Server 22.04 UTM VMs on macOS.

---

## Network Topology

```
┌─────────────────────────────────┐        UTM "Internal Network"        ┌────────────────────────────────────────┐
│         VM-1 (Generator)        │   ◄── eth1 · 10.100.0.0/24 ──►      │         VM-2 (SUT / Target)            │
│                                 │                                       │                                        │
│  tcpreplay → raw PCAP frames    │ ─────────────────────────────────►   │  XDP hook (ebpf_filter.o)              │
│  100 / 500 / 1000 Mbps          │                                       │  → Ollama LLM daemon (asm-shadhin-ai)  │
│  02_traffic_generator.sh        │                                       │  → 03_performance_metrics_logger.py    │
│                                 │                                       │                                        │
│  Management: NAT (eth0)         │                                       │  Management: NAT (eth0)                │
│  Test NIC:   eth1 · 10.100.0.1  │                                       │  Test NIC:   eth1 · 10.100.0.2         │
└─────────────────────────────────┘                                       └────────────────────────────────────────┘
```

---

## Files in this Directory

| File | Runs On | Purpose |
|------|---------|---------|
| [`01_vm_network_setup.sh`](./01_vm_network_setup.sh) | **Both VMs** | Interface config, static IPs, NIC offload disable, kernel tuning |
| [`02_traffic_generator.sh`](./02_traffic_generator.sh) | **VM-1** | tcpreplay automation at 100/500/1000 Mbps, CSV output |
| [`03_performance_metrics_logger.py`](./03_performance_metrics_logger.py) | **VM-2** | Real-time eBPF/CPU/queue metrics → `benchmark_results.csv` |
| [`04_run_benchmark.sh`](./04_run_benchmark.sh) | **VM-1** | Master orchestrator — SSH-controls VM-2, merges results |
| [`requirements.txt`](./requirements.txt) | VM-2 | Python deps for the metrics logger |

---

## Step-by-Step Setup

### Part A — UTM VM Configuration (macOS host)

1. **Create two Ubuntu Server 22.04 LTS VMs** in UTM.

2. **Add a second NIC** (Internal Network) to each VM:
   - UTM → VM Settings → Network → Add Network Interface
   - Mode: **Shared Network** → change to **Host Only** OR
   - Mode: **Emulated VLAN** (both VMs on the same VLAN ID, e.g. `100`)
   - This second NIC appears as `eth1` (or `enp0s2`) inside Ubuntu.

3. **Enable nested virtualization** (recommended for eBPF JIT):
   - UTM → VM Settings → System → Enable Hypervisor (VirtIO)

4. **RAM allocation**:
   - VM-1 (Generator): ≥ 2 GB
   - VM-2 (SUT): ≥ 8 GB (for Ollama + eBPF maps)

---

### Part B — Network Setup (Both VMs)

Copy this `testbed/` directory to `/opt/asm-testbed/` on both VMs:

```bash
# From macOS host (run once per VM)
scp -r ./testbed/ ubuntu@<VM-IP>:/opt/asm-testbed/
```

**On VM-1 (Generator):**
```bash
sudo bash /opt/asm-testbed/01_vm_network_setup.sh --role generator --iface eth1
```

**On VM-2 (SUT):**
```bash
sudo bash /opt/asm-testbed/01_vm_network_setup.sh --role sut --iface eth1
```

Verify connectivity:
```bash
# On VM-1
ping -c 4 10.100.0.2
iperf3 -c 10.100.0.2 -t 10 -P 4     # Baseline bandwidth test
```

---

### Part C — Deploy eBPF Filter on VM-2

Before running benchmarks, the XDP program must be attached:

```bash
# On VM-2 — from the project root
sudo bash scripts/deploy.sh --interface eth1

# Verify XDP is attached
ip link show eth1 | grep xdp
bpftool prog list | grep xdp
bpftool map show pinned /sys/fs/bpf/blocked_ips_map
```

---

### Part D — Install Python Dependencies (VM-2)

```bash
sudo apt-get install -y python3-pip
sudo pip3 install -r /opt/asm-testbed/requirements.txt
```

---

### Part E — Obtain PCAP Benchmark Datasets (VM-1)

Place PCAP files in `/opt/pcap-benchmarks/`. Recommended sources:

| Dataset | Size | Attack Types | URL |
|---------|------|-------------|-----|
| **CIC-IDS-2017** | ~50 GB | DoS, PortScan, Brute-Force, Web | [unb.ca/cic](https://www.unb.ca/cic/datasets/ids-2017.html) |
| **CAIDA Traces** | Variable | DDoS amplification | [caida.org](https://www.caida.org/catalog/datasets/) |
| **UNSW-NB15** | ~100 MB pcap | Reconnaissance, Fuzzers | [unsw.edu.au](https://research.unsw.edu.au/projects/unsw-nb15-dataset) |

Or generate a synthetic PCAP for quick testing:
```bash
# On VM-1 — generate 100MB synthetic traffic PCAP
sudo tcpdump -i eth1 -w /opt/pcap-benchmarks/synthetic.pcap -c 1000000 &
# Trigger traffic, then kill tcpdump
# OR use tcpgen / scapy to create synthetic flows
```

---

### Part F — Run the Benchmark

#### Option 1: Manual (run scripts independently)

**Terminal on VM-2 — start logger:**
```bash
sudo python3 /opt/asm-testbed/03_performance_metrics_logger.py \
    --iface eth1 \
    --interval 0.5 \
    --duration 300 \
    --output /opt/asm-testbed-results/benchmark_results.csv
```

**Terminal on VM-1 — start traffic:**
```bash
sudo bash /opt/asm-testbed/02_traffic_generator.sh \
    --iface eth1 \
    --pcap /opt/pcap-benchmarks/cic-ids2017-monday.pcap \
    --rates "100 500 1000" \
    --duration 60
```

#### Option 2: Automated via SSH (recommended)

```bash
# On VM-1 — set up SSH key to VM-2 first
ssh-keygen -t ed25519 -f ~/.ssh/testbed_key -N ""
ssh-copy-id -i ~/.ssh/testbed_key.pub ubuntu@10.100.0.2

# Run the full orchestrated benchmark
sudo bash /opt/asm-testbed/04_run_benchmark.sh \
    --iface eth1 \
    --pcap /opt/pcap-benchmarks/cic-ids2017-monday.pcap \
    --sut-ip 10.100.0.2 \
    --sut-user ubuntu \
    --ssh-key ~/.ssh/testbed_key \
    --rates "100 500 1000" \
    --duration 60
```

---

## Output Files

After a successful run, the following files are produced:

```
/opt/asm-testbed-results/<run_id>/
├── tx_results.csv          ← Per-rate TX throughput, packet counts, efficiency
├── rx_metrics.csv          ← Per-sample SUT metrics (eBPF, CPU, queue, latency)
├── combined_report.json    ← Machine-readable merged results
├── SUMMARY.txt             ← Human-readable summary + SLA assessment
└── sut_logger.log          ← Raw stdout from the metrics logger
```

### `tx_results.csv` Schema

| Column | Description |
|--------|-------------|
| `timestamp` | ISO-8601 timestamp of rate tier start |
| `target_rate_mbps` | Requested tcpreplay rate |
| `actual_rate_mbps` | Measured actual rate achieved |
| `actual_pps` | Packets per second |
| `tx_packets` | Total packets transmitted |
| `tx_bytes` | Total bytes transmitted |
| `failed_packets` | Packets that failed to transmit |
| `retried` | Retry count |
| `duration_sec` | Elapsed time for this tier |
| `pcap_file` | Source PCAP filename |

### `benchmark_results.csv` Schema (SUT)

| Column | Description |
|--------|-------------|
| `rx_packets_delta` | Packets received in this interval |
| `rx_drop_delta` | Kernel-level drops in this interval |
| `rx_pps` | Receive PPS |
| `rx_mbps` | Receive throughput (Mbps) |
| `blocked_ip_count` | Current entries in eBPF `blocked_ips_map` |
| `xdp_run_cnt_delta` | XDP program invocations this interval |
| `xdp_mean_lat_ns` | Mean XDP execution time (nanoseconds) |
| `lat_mean_us` | Mean processing latency (µs) |
| `lat_p99_us` | P99 latency (µs) — **primary SLA metric** |
| `llm_cpu_pct` | Combined CPU% of Ollama/daemon processes |
| `llm_rss_mb` | LLM daemon RSS memory (MB) |
| `alert_queue_depth` | Estimated unprocessed alert backlog |
| `sys_cpu_pct` | System-wide CPU% |
| `sys_ram_pct` | System RAM utilization % |
| `sys_softirq_pct` | SoftIRQ load (BPF/NIC kernel threads) |

---

## Kernel Tuning Reference

Applied by `01_vm_network_setup.sh` to both VMs:

| Sysctl / Setting | Value | Rationale |
|------------------|-------|-----------|
| `net.core.rmem_max` | 256 MB | Prevent RX buffer overflows at 1Gbps |
| `net.core.netdev_max_backlog` | 250,000 | Queue depth before kernel drop |
| `net.core.netdev_budget` | 600 | NAPI packets per poll (reduces latency spikes) |
| `net.core.bpf_jit_enable` | 1 | JIT-compile BPF programs (2–10× faster) |
| GRO/LRO/TSO/GSO | **Disabled** | Prevent packet aggregation before XDP |
| CPU Governor | `performance` | Eliminate frequency-scaling jitter |
| MTU | 9000 (jumbo) | Reduce per-packet overhead at high rates |

---

## SLA Targets

| Metric | Target | Status Field |
|--------|--------|-------------|
| Packet loss | < 1% | `loss_lt_1pct` |
| P99 latency | < 100 µs | `p99_lat_lt_100us` |
| Mean latency | < 10 µs | `mean_lat_lt_10us` |
| System CPU P99 | < 90% | `sys_cpu_p99_lt_90` |
| Alert queue max depth | < 50 | `queue_max_lt_50` |

---

## Troubleshooting

### tcpreplay rate is much lower than target
- Ensure NIC offloads are disabled: `ethtool -k eth1 | grep offload`
- Use `--preload-pcap` to prevent disk I/O bottleneck
- Increase PCAP size: small files cause loop overhead
- Check CPU governor: `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`

### bpftool shows no XDP program
```bash
# Verify XDP attachment on VM-2
ip link show eth1
# Look for: xdp prog/xdp id <N>

# If missing, re-attach:
sudo ip link set dev eth1 xdp obj /path/to/ebpf_filter.o sec xdp
```

### Metrics logger shows 0 latency
- `bpftool prog show --json` must include `run_cnt`/`run_time_ns` fields
- Enable via: `sysctl -w kernel.bpf_stats_enabled=1`

### SSH connection refused in orchestrator
```bash
# Verify key auth works:
ssh -i ~/.ssh/testbed_key ubuntu@10.100.0.2 "hostname"
```

---

## Integration with Research Paper

Results from `SUMMARY.txt` and `combined_report.json` directly map to the
metrics reported in **Table III** and **Figure 5** of
*ASM-Shadhin-AI Research Paper 2026*:

- **XDP Processing Latency (P99)** → Paper Section IV-B
- **Packet Loss Rate under Load** → Paper Table III (column: "Drop Rate %")
- **LLM Daemon CPU utilization** → Paper Section V-A (Resource overhead)
- **Alert Queue Backlog** → Paper Figure 5 (Alert pipeline saturation)
