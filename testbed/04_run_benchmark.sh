#!/usr/bin/env bash
# =============================================================================
# 04_run_benchmark.sh
# ASM-Shadhin-AI eBPF/XDP Testbed — Master Benchmark Orchestrator
#
# PURPOSE:
#   Coordinates the full benchmark run from VM-1, while simultaneously
#   signalling VM-2 to start/stop metrics collection via SSH.
#   Merges TX results (VM-1) with RX/eBPF results (VM-2) into a single
#   final report.
#
# TOPOLOGY:
#   VM-1 (Generator): 10.100.0.1  — runs this script
#   VM-2 (SUT):       10.100.0.2  — SSH target for logger control
#
# USAGE (run on VM-1):
#   bash 04_run_benchmark.sh \
#       --iface eth1 \
#       --pcap /opt/pcap-benchmarks/cic-ids2017.pcap \
#       --sut-ip 10.100.0.2 \
#       --sut-user ubuntu \
#       [--ssh-key ~/.ssh/id_ed25519] \
#       [--rates "100 500 1000"] \
#       [--duration 60]
#
# REQUIREMENTS (VM-1):
#   - SSH key-based login to VM-2 (no password prompt)
#   - Scripts deployed to /opt/asm-testbed/ on both VMs
#   - tcpreplay, python3, bc
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

# ── Defaults ───────────────────────────────────────────────────────────────────
IFACE="eth1"
PCAP=""
SUT_IP="10.100.0.2"
SUT_USER="ubuntu"
SSH_KEY="$HOME/.ssh/id_ed25519"
RATES="100 500 1000"
DURATION=60
TESTBED_DIR="/opt/asm-testbed"
RESULTS_DIR="/opt/asm-testbed-results"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
RUN_ID="run_${TIMESTAMP}"

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}"; }
ok()   { echo -e "${GREEN}[✓] $*${NC}"; }
warn() { echo -e "${YELLOW}[!] $*${NC}"; }
err()  { echo -e "${RED}[✗] $*${NC}"; exit 1; }
sep()  { echo -e "${BLUE}──────────────────────────────────────────────────────${NC}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --iface)    IFACE="$2";    shift 2 ;;
        --pcap)     PCAP="$2";     shift 2 ;;
        --sut-ip)   SUT_IP="$2";   shift 2 ;;
        --sut-user) SUT_USER="$2"; shift 2 ;;
        --ssh-key)  SSH_KEY="$2";  shift 2 ;;
        --rates)    RATES="$2";    shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        -h|--help)
            sed -n '/^# USAGE/,/^# REQUIREMENTS/p' "$0" | head -15
            exit 0 ;;
        *) err "Unknown option: $1" ;;
    esac
done

# ── SSH helper (passwordless) ──────────────────────────────────────────────────
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes"
sut_ssh() { ssh $SSH_OPTS "${SUT_USER}@${SUT_IP}" "$@"; }
sut_scp() { scp $SSH_OPTS "$@"; }

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     ASM-Shadhin-AI Testbed — Master Benchmark Orchestrator       ║"
echo "║     Run ID: $(printf '%-51s' "${RUN_ID}") ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================
log "Running pre-flight checks..."

[[ $EUID -ne 0 ]] && err "Must run as root on VM-1."
[[ -z "$PCAP" ]]  && err "PCAP file required. Use --pcap <path>."
[[ ! -f "$PCAP" ]] && err "PCAP not found: $PCAP"
[[ ! -f "$SSH_KEY" ]] && err "SSH key not found: $SSH_KEY"

# Test SSH to SUT
if ! sut_ssh "echo ok" &>/dev/null; then
    err "Cannot SSH to SUT (${SUT_USER}@${SUT_IP}) — ensure key is authorized."
fi
ok "SSH to SUT verified."

# Check tcpreplay
command -v tcpreplay &>/dev/null || err "tcpreplay not found."
ok "tcpreplay found: $(tcpreplay --version 2>&1 | head -1)"

# Verify eBPF is loaded on SUT
BPF_LOADED=$(sut_ssh "test -f /sys/fs/bpf/blocked_ips_map && echo yes || echo no")
if [[ "$BPF_LOADED" == "yes" ]]; then
    ok "SUT eBPF maps confirmed loaded."
else
    warn "SUT eBPF maps NOT detected — deploy the XDP filter first."
    warn "  On VM-2: sudo bash /opt/asm-testbed/deploy.sh (or the project's deploy.sh)"
fi

mkdir -p "${RESULTS_DIR}/${RUN_ID}"
ok "Local results directory: ${RESULTS_DIR}/${RUN_ID}"

# =============================================================================
# STEP 1: Start metrics logger on SUT (background via nohup)
# =============================================================================
log "STEP 1: Starting metrics logger on SUT (VM-2: ${SUT_IP})..."

TOTAL_DURATION=$(( (${#RATES[@]} + 3) * (DURATION + 15) ))
SUT_LOG_PID_FILE="/tmp/asm_metrics_logger.pid"
SUT_CSV="/opt/asm-testbed-results/${RUN_ID}_metrics.csv"

sut_ssh "mkdir -p /opt/asm-testbed-results"
sut_ssh "nohup python3 ${TESTBED_DIR}/03_performance_metrics_logger.py \
    --iface ${IFACE} \
    --interval 0.5 \
    --duration ${TOTAL_DURATION} \
    --output ${SUT_CSV} \
    --llm-process 'ollama,security_daemon,asm-shadhin' \
    > /tmp/asm_metrics_logger.log 2>&1 & echo \$! > ${SUT_LOG_PID_FILE}"

sleep 2
SUT_LOGGER_PID=$(sut_ssh "cat ${SUT_LOG_PID_FILE} 2>/dev/null || echo 0")
if [[ "$SUT_LOGGER_PID" -gt 0 ]]; then
    ok "Metrics logger started on SUT (PID: ${SUT_LOGGER_PID})"
else
    warn "Could not confirm logger PID on SUT — proceeding anyway."
fi

# =============================================================================
# STEP 2: Run traffic generator (this VM)
# =============================================================================
log "STEP 2: Running tcpreplay benchmark on VM-1..."
sep

TX_CSV="${RESULTS_DIR}/${RUN_ID}/tx_results.csv"

sudo bash "$(dirname "$0")/02_traffic_generator.sh" \
    --iface   "$IFACE" \
    --pcap    "$PCAP" \
    --rates   "$RATES" \
    --duration "$DURATION" \
    --output  "$TX_CSV" \
    --sut-ip  "$SUT_IP"

ok "Traffic generation complete. TX CSV: ${TX_CSV}"

# =============================================================================
# STEP 3: Stop metrics logger on SUT and fetch results
# =============================================================================
log "STEP 3: Stopping SUT metrics logger and fetching results..."
sleep 5  # Allow logger to flush final samples

sut_ssh "kill -SIGTERM \$(cat ${SUT_LOG_PID_FILE}) 2>/dev/null || true"
sleep 3

# Copy SUT CSV to local results directory
RX_CSV="${RESULTS_DIR}/${RUN_ID}/rx_metrics.csv"
sut_scp "${SUT_USER}@${SUT_IP}:${SUT_CSV}" "$RX_CSV" 2>/dev/null && \
    ok "SUT metrics CSV fetched: ${RX_CSV}" || \
    warn "Could not fetch SUT CSV — retrieve manually: scp ${SUT_USER}@${SUT_IP}:${SUT_CSV} ./"

# Also grab the logger stdout log
sut_scp "${SUT_USER}@${SUT_IP}:/tmp/asm_metrics_logger.log" \
    "${RESULTS_DIR}/${RUN_ID}/sut_logger.log" 2>/dev/null || true

# =============================================================================
# STEP 4: Merge and generate combined report
# =============================================================================
log "STEP 4: Generating combined benchmark report..."

python3 - <<PYEOF
import csv, sys, json
from pathlib import Path
from datetime import datetime

run_dir = Path("${RESULTS_DIR}/${RUN_ID}")
tx_csv  = run_dir / "tx_results.csv"
rx_csv  = run_dir / "rx_metrics.csv"
report  = run_dir / "combined_report.json"
summary = run_dir / "SUMMARY.txt"

def load_csv(p):
    if not p.exists():
        return []
    with open(p) as f:
        return list(csv.DictReader(f))

tx_rows = load_csv(tx_csv)
rx_rows = load_csv(rx_csv)

# ── TX summary per rate tier ──────────────────────────────────────────────────
tx_summary = []
for row in tx_rows:
    target = float(row.get("target_rate_mbps", 0))
    actual = float(row.get("actual_rate_mbps", 0))
    tx_pkts = int(row.get("tx_packets", 0))
    failed  = int(row.get("failed_packets", 0))
    tx_summary.append({
        "target_mbps": target,
        "actual_mbps": actual,
        "efficiency_pct": round(actual / target * 100, 2) if target > 0 else 0,
        "tx_packets": tx_pkts,
        "failed_packets": failed,
        "duration_sec": float(row.get("duration_sec", 0)),
    })

# ── RX / SUT aggregate stats ──────────────────────────────────────────────────
def floats(key):
    out = []
    for r in rx_rows:
        try: out.append(float(r[key]))
        except: pass
    return out

def pct(vals, p):
    if not vals: return 0
    s = sorted(vals)
    return s[min(int(len(s) * p / 100), len(s)-1)]

def mean(vals):
    return sum(vals) / len(vals) if vals else 0

rx_mbps   = floats("rx_mbps")
lat_p99   = floats("lat_p99_us")
lat_mean  = floats("lat_mean_us")
drops     = floats("rx_drop_delta")
rx_pkts   = floats("rx_packets_delta")
cpu_sys   = floats("sys_cpu_pct")
cpu_llm   = floats("llm_cpu_pct")
ram_llm   = floats("llm_rss_mb")
queue_d   = floats("alert_queue_depth")

total_rx   = sum(rx_pkts)
total_drop = sum(drops)
loss_pct   = 100.0 * total_drop / max(total_rx + total_drop, 1)

rx_summary = {
    "total_samples":        len(rx_rows),
    "rx_mbps_mean":         round(mean(rx_mbps), 3),
    "rx_mbps_p99":          round(pct(rx_mbps, 99), 3),
    "rx_mbps_max":          round(max(rx_mbps) if rx_mbps else 0, 3),
    "lat_mean_us":          round(mean(lat_mean), 4),
    "lat_p99_us":           round(pct(lat_p99, 99), 4),
    "lat_max_us":           round(max(lat_p99) if lat_p99 else 0, 4),
    "total_rx_packets":     int(total_rx),
    "total_drops":          int(total_drop),
    "loss_pct":             round(loss_pct, 5),
    "sys_cpu_mean_pct":     round(mean(cpu_sys), 2),
    "sys_cpu_p99_pct":      round(pct(cpu_sys, 99), 2),
    "llm_cpu_mean_pct":     round(mean(cpu_llm), 2),
    "llm_rss_mean_mb":      round(mean(ram_llm), 1),
    "alert_queue_max":      int(max(queue_d) if queue_d else 0),
    "alert_queue_mean":     round(mean(queue_d), 1),
}

# SLA assessment
sla = {
    "loss_lt_1pct":        loss_pct < 1.0,
    "p99_lat_lt_100us":    pct(lat_p99, 99) < 100.0,
    "mean_lat_lt_10us":    mean(lat_mean) < 10.0,
    "sys_cpu_p99_lt_90":   pct(cpu_sys, 99) < 90.0,
    "queue_max_lt_50":     (max(queue_d) if queue_d else 0) < 50,
}
sla["all_passed"] = all(sla.values())

combined = {
    "run_id":       "${RUN_ID}",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "config": {
        "iface":    "${IFACE}",
        "rates_mbps": "${RATES}",
        "duration_per_rate_sec": ${DURATION},
        "pcap": "${PCAP}",
    },
    "tx_summary":  tx_summary,
    "rx_summary":  rx_summary,
    "sla_results": sla,
}

with open(report, "w") as f:
    json.dump(combined, f, indent=2)

# ── Plain text SUMMARY ────────────────────────────────────────────────────────
lines = [
    "=" * 68,
    f"  ASM-Shadhin-AI eBPF/XDP Benchmark — Run ID: ${RUN_ID}",
    f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
    "=" * 68,
    "",
    "TX Results (per rate tier):",
    f"  {'Target':>8}  {'Actual':>8}  {'Eff%':>6}  {'TX Pkts':>12}  {'Failed':>8}",
    "  " + "-"*52,
]
for t in tx_summary:
    lines.append(
        f"  {t['target_mbps']:>7.0f}M  {t['actual_mbps']:>7.1f}M  "
        f"{t['efficiency_pct']:>5.1f}%  {t['tx_packets']:>12,}  {t['failed_packets']:>8}"
    )

lines += [
    "",
    "RX / SUT Aggregate Results:",
    f"  Throughput   Mean={rx_summary['rx_mbps_mean']}M  P99={rx_summary['rx_mbps_p99']}M  Max={rx_summary['rx_mbps_max']}M",
    f"  Latency      Mean={rx_summary['lat_mean_us']}µs  P99={rx_summary['lat_p99_us']}µs  Max={rx_summary['lat_max_us']}µs",
    f"  Packet Loss  {rx_summary['loss_pct']}%  ({rx_summary['total_drops']:,} drops / {rx_summary['total_rx_packets']:,} RX)",
    f"  CPU (Sys)    Mean={rx_summary['sys_cpu_mean_pct']}%  P99={rx_summary['sys_cpu_p99_pct']}%",
    f"  CPU (LLM)    Mean={rx_summary['llm_cpu_mean_pct']}%  RAM={rx_summary['llm_rss_mean_mb']}MB",
    f"  Alert Queue  Mean={rx_summary['alert_queue_mean']}  Max={rx_summary['alert_queue_max']}",
    "",
    "SLA Assessment:",
]
for check, passed in sla.items():
    if check == "all_passed": continue
    icon = "PASS" if passed else "FAIL"
    lines.append(f"  [{icon}]  {check}")
lines += [
    "",
    f"  OVERALL: {'ALL SLA CHECKS PASSED' if sla['all_passed'] else 'SLA FAILURES DETECTED'}",
    "",
    f"Full report: {report}",
    "=" * 68,
]

with open(summary, "w") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
PYEOF

sep
ok "Combined report saved to: ${RESULTS_DIR}/${RUN_ID}/"
echo ""
echo -e "${BOLD}Files generated:${NC}"
ls -lh "${RESULTS_DIR}/${RUN_ID}/" 2>/dev/null || true
echo ""
echo -e "${CYAN}  ℹ  To copy all results to your macOS host:${NC}"
echo -e "     ${CYAN}scp -r ${SUT_USER}@${SUT_IP}:${RESULTS_DIR}/${RUN_ID}/ ./testbed_results/${NC}"
