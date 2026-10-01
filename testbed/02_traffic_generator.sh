#!/usr/bin/env bash
# =============================================================================
# 02_traffic_generator.sh
# ASM-Shadhin-AI eBPF/XDP Testbed — tcpreplay Traffic Generator (VM-1)
#
# PURPOSE:
#   Replay raw PCAP files toward VM-2 (SUT) at incremental throughput targets:
#     100 Mbps → 500 Mbps → 1 Gbps (wire-speed)
#   Log transmission time, throughput, packet counts, and dropped packets per
#   rate tier. Optionally loop through multiple PCAP files.
#
# USAGE:
#   sudo bash 02_traffic_generator.sh \
#       --iface eth1 \
#       --pcap /opt/pcap-benchmarks/cic-ids2017.pcap \
#       [--rates "100 500 1000"] \
#       [--duration 60] \
#       [--loops 3] \
#       [--output /tmp/tx_results.csv]
#
# DEPENDENCIES:
#   tcpreplay >= 4.3, tcpprep, python3, bc
#
# TESTED ON: Ubuntu Server 22.04 LTS
# =============================================================================

set -euo pipefail

# ── Color palette ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

# ── Defaults ───────────────────────────────────────────────────────────────────
IFACE=""
PCAP_PATH=""
# Space-separated Mbps rate targets
RATES="100 500 1000"
# Duration per rate in seconds (0 = replay the file once at each rate)
DURATION=60
# Number of loops per rate (0 = infinite until duration expires)
LOOPS=1
OUTPUT_CSV="/tmp/tx_benchmark_results.csv"
SUT_IP="10.100.0.2"
PCAP_DIR="/opt/pcap-benchmarks"

# ── Argument parsing ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --iface)    IFACE="$2";         shift 2 ;;
        --pcap)     PCAP_PATH="$2";     shift 2 ;;
        --rates)    RATES="$2";         shift 2 ;;
        --duration) DURATION="$2";      shift 2 ;;
        --loops)    LOOPS="$2";         shift 2 ;;
        --output)   OUTPUT_CSV="$2";    shift 2 ;;
        --sut-ip)   SUT_IP="$2";        shift 2 ;;
        -h|--help)
            grep "^# " "$0" | head -20 | sed 's/^# //'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Privilege check ────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && echo -e "${RED}[✗] Must run as root.${NC}" && exit 1

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}"; }
ok()   { echo -e "${GREEN}[✓] $*${NC}"; }
warn() { echo -e "${YELLOW}[!] $*${NC}"; }
err()  { echo -e "${RED}[✗] $*${NC}"; exit 1; }
sep()  { echo -e "${BLUE}──────────────────────────────────────────────────────${NC}"; }

# ── Dependency checks ──────────────────────────────────────────────────────────
for dep in tcpreplay tcpprep bc python3 awk grep; do
    command -v "$dep" &>/dev/null || err "Missing dependency: ${dep}. Run: apt-get install tcpreplay"
done

# ── Interface validation ───────────────────────────────────────────────────────
[[ -z "$IFACE" ]] && err "No interface specified. Use --iface <iface>."
ip link show "$IFACE" &>/dev/null || err "Interface '${IFACE}' does not exist."

# ── PCAP resolution ────────────────────────────────────────────────────────────
if [[ -z "$PCAP_PATH" ]]; then
    # Auto-discover first PCAP in benchmark directory
    PCAP_PATH=$(find "$PCAP_DIR" -maxdepth 2 -name "*.pcap" -o -name "*.pcapng" 2>/dev/null | head -1)
    [[ -z "$PCAP_PATH" ]] && err "No PCAP specified or found in ${PCAP_DIR}. Use --pcap <path>."
    warn "No PCAP specified — using auto-discovered: ${PCAP_PATH}"
fi
[[ ! -f "$PCAP_PATH" ]] && err "PCAP file not found: ${PCAP_PATH}"

PCAP_SIZE=$(du -sh "$PCAP_PATH" | cut -f1)
PCAP_PKT_COUNT=$(tcpdump -r "$PCAP_PATH" --count 2>/dev/null | tail -1 | awk '{print $1}' || echo "unknown")

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     ASM-Shadhin-AI — tcpreplay Traffic Generator (VM-1)         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${BOLD}Run Configuration:${NC}"
echo -e "  Interface     : ${BOLD}${IFACE}${NC}"
echo -e "  PCAP File     : ${BOLD}${PCAP_PATH}${NC}  (${PCAP_SIZE})"
echo -e "  Packet Count  : ${BOLD}${PCAP_PKT_COUNT}${NC}"
echo -e "  Rate Targets  : ${BOLD}${RATES} Mbps${NC}"
echo -e "  Duration/Rate : ${BOLD}${DURATION}s${NC}"
echo -e "  Loops/Rate    : ${BOLD}${LOOPS}${NC}"
echo -e "  SUT Target IP : ${BOLD}${SUT_IP}${NC}"
echo -e "  Results CSV   : ${BOLD}${OUTPUT_CSV}${NC}"
sep

# =============================================================================
# FUNCTION: Pre-process PCAP with tcpprep for 2-NIC mode (client/server split)
# =============================================================================
preprocess_pcap() {
    local pcap="$1"
    local cache_file="${pcap%.pcap}.cache"

    if [[ ! -f "$cache_file" ]]; then
        log "Pre-processing PCAP with tcpprep (client/server auto mode)..."
        tcpprep --auto=client --pcap="$pcap" --cachefile="$cache_file" 2>/dev/null || \
        tcpprep --auto=first  --pcap="$pcap" --cachefile="$cache_file" 2>/dev/null || \
        warn "tcpprep failed — tcpreplay will use single-NIC mode."
    fi

    echo "$cache_file"
}

# =============================================================================
# FUNCTION: Verify peer SUT is reachable before replaying
# =============================================================================
check_sut_reachability() {
    log "Checking SUT reachability (${SUT_IP})..."
    if ping -c 2 -W 2 "$SUT_IP" &>/dev/null; then
        RTT=$(ping -c 3 -W 2 "$SUT_IP" 2>/dev/null | tail -1 | awk -F'/' '{print $5}')
        ok "SUT reachable. Baseline RTT: ${RTT}ms"
    else
        warn "SUT (${SUT_IP}) not responding to ping — proceeding anyway (XDP may be dropping ICMP)."
    fi
}

# =============================================================================
# FUNCTION: Replay at a target Mbps rate for DURATION seconds, return metrics
# =============================================================================
# Returns CSV line: timestamp,rate_mbps,actual_mbps,pps,tx_pkts,tx_bytes,
#                   failed_pkts,retry_cnt,duration_sec,pcap_file
run_replay_at_rate() {
    local rate_mbps="$1"
    local pcap="$2"

    local tmplog
    tmplog=$(mktemp /tmp/tcpreplay_out_XXXXXX.log)

    log "Starting replay at ${BOLD}${rate_mbps} Mbps${NC}..."
    sep

    # Build tcpreplay command
    # --mbps          : target wire rate in Mbps
    # --loop          : number of PCAP loops (0=infinite)
    # --duration      : stop after N seconds (requires tcpreplay >= 4.3)
    # --stats=1       : print stats every second
    # --preload-pcap  : load PCAP into RAM before sending (reduces jitter)
    # --suppress-warnings : cleaner output

    local TCPREPLAY_CMD=(
        tcpreplay
        --intf1="$IFACE"
        --mbps="$rate_mbps"
        --loop="$LOOPS"
        --preload-pcap
        --stats=1
    )

    # Add duration flag if supported and DURATION > 0
    if [[ "$DURATION" -gt 0 ]]; then
        TCPREPLAY_CMD+=(--duration="$DURATION")
    fi

    TCPREPLAY_CMD+=("$pcap")

    local START_EPOC
    START_EPOC=$(date +%s%3N)  # ms since epoch
    local START_TS
    START_TS=$(date '+%Y-%m-%dT%H:%M:%S')

    # Run tcpreplay — capture stdout+stderr, also tee to terminal
    "${TCPREPLAY_CMD[@]}" 2>&1 | tee "$tmplog" || true

    local END_EPOC
    END_EPOC=$(date +%s%3N)
    local ELAPSED_MS=$(( END_EPOC - START_EPOC ))
    local ELAPSED_SEC
    ELAPSED_SEC=$(echo "scale=3; $ELAPSED_MS / 1000" | bc)

    # ── Parse tcpreplay statistics ──────────────────────────────────────────────
    # tcpreplay final line format (>= 4.3.4):
    # "Actual: 12345678 packets (987654321 bytes) sent in 60.00 seconds"
    # "Rated: 1234.5 Mbps, 98765.4 pps"
    # "Statistics for network device: eth1"
    # "Successful packets: 12345678, Failed: 0, Retried: 0"

    TX_PKTS=$(grep -oP 'Actual:\s+\K[0-9]+(?= packets)' "$tmplog" | tail -1 || echo "0")
    TX_BYTES=$(grep -oP 'Actual:.*?\(\K[0-9]+(?= bytes\))' "$tmplog" | tail -1 || echo "0")
    ACTUAL_MBPS=$(grep -oP 'Rated:\s+\K[0-9.]+(?= Mbps)' "$tmplog" | tail -1 || echo "0")
    ACTUAL_PPS=$(grep -oP 'Rated:.*?,\s+\K[0-9.]+(?= pps)' "$tmplog" | tail -1 || echo "0")
    FAILED_PKTS=$(grep -oP 'Failed:\s+\K[0-9]+' "$tmplog" | tail -1 || echo "0")
    RETRIED=$(grep -oP 'Retried:\s+\K[0-9]+' "$tmplog" | tail -1 || echo "0")

    # Fallback: compute throughput from bytes/elapsed if tcpreplay didn't print Rated
    if [[ "$ACTUAL_MBPS" == "0" && "$TX_BYTES" != "0" && "$ELAPSED_SEC" != "0" ]]; then
        ACTUAL_MBPS=$(echo "scale=2; ($TX_BYTES * 8) / ($ELAPSED_SEC * 1000000)" | bc)
    fi

    local LINE="${START_TS},${rate_mbps},${ACTUAL_MBPS},${ACTUAL_PPS},${TX_PKTS},${TX_BYTES},${FAILED_PKTS},${RETRIED},${ELAPSED_SEC},$(basename "$pcap")"

    # Print per-rate summary
    echo ""
    echo -e "${BOLD}── Rate Tier ${rate_mbps} Mbps — Summary ──────────────────────────${NC}"
    printf "  %-22s : %s\n" "Target Rate"    "${rate_mbps} Mbps"
    printf "  %-22s : %s\n" "Actual Rate"    "${ACTUAL_MBPS} Mbps"
    printf "  %-22s : %s\n" "Actual PPS"     "${ACTUAL_PPS} pps"
    printf "  %-22s : %s\n" "TX Packets"     "${TX_PKTS}"
    printf "  %-22s : %s\n" "TX Bytes"       "${TX_BYTES}"
    printf "  %-22s : %s\n" "Failed Packets" "${FAILED_PKTS}"
    printf "  %-22s : %s\n" "Retried"        "${RETRIED}"
    printf "  %-22s : %s\n" "Duration"       "${ELAPSED_SEC}s"

    # Efficiency metric
    if [[ "$ACTUAL_MBPS" != "0" && "$rate_mbps" != "0" ]]; then
        EFF=$(echo "scale=1; $ACTUAL_MBPS * 100 / $rate_mbps" | bc)
        printf "  %-22s : %s%%\n" "Efficiency" "$EFF"
        if (( $(echo "$EFF < 80" | bc -l) )); then
            warn "Efficiency < 80% — check system resources or increase PCAP file size."
        fi
    fi
    echo ""

    rm -f "$tmplog"
    echo "$LINE"
}

# =============================================================================
# FUNCTION: Collect live TX interface statistics via /proc/net/dev
# =============================================================================
snapshot_netdev() {
    local iface="$1"
    # Returns: rx_bytes rx_pkts rx_errs rx_drop tx_bytes tx_pkts tx_errs tx_drop
    awk -v iface="${iface}:" '$1==iface{print $2,$3,$4,$5,$10,$11,$12,$13}' /proc/net/dev
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================
check_sut_reachability

# Write CSV header
CSV_HEADER="timestamp,target_rate_mbps,actual_rate_mbps,actual_pps,tx_packets,tx_bytes,failed_packets,retried,duration_sec,pcap_file"
echo "$CSV_HEADER" > "$OUTPUT_CSV"
ok "CSV results file initialized: ${OUTPUT_CSV}"

# Pre-process PCAP
CACHE_FILE=$(preprocess_pcap "$PCAP_PATH")

# Snapshot baseline netdev counters before any replay
IFS=' ' read -r _ _ _ BASE_DROP_RX _ _ _ BASE_DROP_TX <<< "$(snapshot_netdev "$IFACE")"

log "Starting benchmark run — $(date '+%Y-%m-%d %H:%M:%S')"
OVERALL_START=$(date +%s)

# ── Rate Iteration Loop ────────────────────────────────────────────────────────
for RATE in $RATES; do
    sep
    log "━━━  RATE TIER: ${BOLD}${RATE} Mbps  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Warm-up: 5s at target rate to fill RX queues before measurement
    log "Warm-up: 5 seconds at ${RATE} Mbps..."
    tcpreplay --intf1="$IFACE" --mbps="$RATE" --duration=5 --loop=0 "$PCAP_PATH" &>/dev/null || true
    sleep 1

    # Snapshot netdev before measurement
    IFS=' ' read -r _ PRE_RX_PKT _ PRE_DROP_RX _ PRE_TX_PKT _ PRE_DROP_TX <<< "$(snapshot_netdev "$IFACE")"

    # Run replay and collect result row
    RESULT_ROW=$(run_replay_at_rate "$RATE" "$PCAP_PATH")
    echo "$RESULT_ROW" >> "$OUTPUT_CSV"

    # Snapshot netdev after measurement
    IFS=' ' read -r _ POST_RX_PKT _ POST_DROP_RX _ POST_TX_PKT _ POST_DROP_TX <<< "$(snapshot_netdev "$IFACE")"

    IFACE_TX_PKTS=$(( POST_TX_PKT - PRE_TX_PKT ))
    IFACE_DROP=$(( (POST_DROP_RX - PRE_DROP_RX) + (POST_DROP_TX - PRE_DROP_TX) ))

    echo -e "  ${BLUE}[/proc/net/dev] Δ TX Packets: ${IFACE_TX_PKTS}  |  Δ Interface Drops: ${IFACE_DROP}${NC}"

    # Brief inter-rate cooldown
    [[ "$RATE" != "$(echo "$RATES" | awk '{print $NF}')" ]] && {
        log "Cooldown: 10 seconds before next rate tier..."
        sleep 10
    }
done

OVERALL_END=$(date +%s)
TOTAL_TIME=$(( OVERALL_END - OVERALL_START ))

sep
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║           TRAFFIC GENERATION BENCHMARK COMPLETE                  ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Total benchmark time : ${BOLD}${TOTAL_TIME}s${NC}"
echo -e "  Results saved to     : ${BOLD}${OUTPUT_CSV}${NC}"
echo ""
echo -e "${BOLD}CSV Contents:${NC}"
cat "$OUTPUT_CSV"
echo ""
echo -e "${CYAN}  ℹ  Transfer this CSV to VM-2 for merged analysis:${NC}"
echo -e "     ${CYAN}scp ${OUTPUT_CSV} sut-vm:/opt/asm-testbed-results/tx_results.csv${NC}"

# =============================================================================
# OPTIONAL: Python-based summary statistics from CSV
# =============================================================================
python3 - <<'PYEOF'
import csv, sys
try:
    results = []
    with open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tx_benchmark_results.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)

    if not results:
        print("No data rows in CSV.")
        sys.exit(0)

    print("\n\033[1mRate-by-Rate Summary:\033[0m")
    print(f"  {'Target':>8}  {'Actual':>8}  {'PPS':>10}  {'TX Pkts':>12}  {'Failed':>8}  {'Eff%':>6}")
    print("  " + "-"*60)
    for r in results:
        target = float(r.get('target_rate_mbps', 0))
        actual = float(r.get('actual_rate_mbps', 0))
        pps    = float(r.get('actual_pps', 0))
        tx_pk  = int(r.get('tx_packets', 0))
        fail   = int(r.get('failed_packets', 0))
        eff    = (actual / target * 100) if target > 0 else 0
        print(f"  {target:>7.0f}M  {actual:>7.1f}M  {pps:>10.0f}  {tx_pk:>12,}  {fail:>8}  {eff:>5.1f}%")

except Exception as e:
    print(f"Summary generation error: {e}")
PYEOF
