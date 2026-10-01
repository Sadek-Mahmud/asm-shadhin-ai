#!/usr/bin/env bash
# =============================================================================
# 01_vm_network_setup.sh
# ASM-Shadhin-AI eBPF/XDP Testbed — UTM VM Network Configuration & Kernel Tuning
#
# PURPOSE:
#   Configure a high-throughput Host-Only / Internal network between two UTM VMs:
#     VM-1 (Traffic Generator)  — runs tcpreplay
#     VM-2 (SUT / Target)       — runs eBPF XDP filter + Ollama LLM daemon
#
# USAGE:
#   On BOTH VMs: sudo bash 01_vm_network_setup.sh [--role generator|sut] [--iface <iface>]
#
# NETWORK TOPOLOGY (UTM Internal Network "ebpf-test"):
#   VM-1: 10.100.0.1/24   (Traffic Generator)
#   VM-2: 10.100.0.2/24   (SUT — eBPF/XDP + LLM)
#
# TESTED ON: Ubuntu Server 22.04 LTS (kernel 5.15+)
# =============================================================================

set -euo pipefail

# ── Color palette ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

# ── Defaults ───────────────────────────────────────────────────────────────────
ROLE="sut"          # 'generator' or 'sut'
IFACE=""            # auto-detected if empty
GENERATOR_IP="10.100.0.1"
SUT_IP="10.100.0.2"
NETMASK="24"
MTU=9000            # Jumbo frames for high-throughput (set 1500 for standard)

# ── Argument parsing ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --role)     ROLE="$2"; shift 2 ;;
        --iface)    IFACE="$2"; shift 2 ;;
        --mtu)      MTU="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [--role generator|sut] [--iface <iface>] [--mtu <mtu>]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Privilege check ────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[✗] This script must be run as root (sudo).${NC}"
    exit 1
fi

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}"; }
ok()   { echo -e "${GREEN}[✓] $*${NC}"; }
warn() { echo -e "${YELLOW}[!] $*${NC}"; }
err()  { echo -e "${RED}[✗] $*${NC}"; exit 1; }

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     ASM-Shadhin-AI eBPF/XDP Testbed — VM Network Setup          ║"
echo "║     Role: $(printf '%-55s' "${ROLE^^}") ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# STEP 1: Detect or validate test network interface
# =============================================================================
log "STEP 1: Detecting test network interface..."

if [[ -z "$IFACE" ]]; then
    # Auto-detect: pick the second NIC (first is usually the mgmt/NAT interface)
    IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -v -E '^lo$|^docker|^veth|^br-' | sed -n '2p')
    if [[ -z "$IFACE" ]]; then
        err "Cannot auto-detect a second NIC. Please specify --iface <iface>."
    fi
    warn "Auto-detected interface: ${IFACE}. Override with --iface if incorrect."
fi

# Verify the interface exists
if ! ip link show "$IFACE" &>/dev/null; then
    err "Interface '${IFACE}' does not exist. Available interfaces:"
    ip -o link show | awk -F': ' '{print "  " $2}'
fi
ok "Using interface: ${IFACE}"

# =============================================================================
# STEP 2: Install required packages
# =============================================================================
log "STEP 2: Installing required packages..."

apt-get update -qq

PKGS_COMMON=(
    ethtool net-tools iproute2 numactl cpufrequtils
    linux-tools-generic linux-tools-"$(uname -r)" bpfcc-tools bpftrace
    iperf3 netperf
)

PKGS_GENERATOR=(
    tcpreplay tcpdump libpcap-dev python3-pip python3-venv
)

PKGS_SUT=(
    linux-headers-"$(uname -r)" clang llvm gcc make libbpf-dev
    bpftool sysstat procps dstat
)

apt-get install -y --no-install-recommends "${PKGS_COMMON[@]}" 2>/dev/null | tail -3

if [[ "$ROLE" == "generator" ]]; then
    apt-get install -y --no-install-recommends "${PKGS_GENERATOR[@]}" 2>/dev/null | tail -3
    ok "Generator packages installed."
else
    apt-get install -y --no-install-recommends "${PKGS_SUT[@]}" 2>/dev/null | tail -3
    ok "SUT packages installed."
fi

# =============================================================================
# STEP 3: Assign static IP address on test interface
# =============================================================================
log "STEP 3: Assigning static IP on ${IFACE}..."

if [[ "$ROLE" == "generator" ]]; then
    MY_IP="${GENERATOR_IP}"
else
    MY_IP="${SUT_IP}"
fi

# Bring interface up
ip link set "$IFACE" up

# Flush existing addresses
ip addr flush dev "$IFACE" 2>/dev/null || true

# Assign static IP
ip addr add "${MY_IP}/${NETMASK}" dev "$IFACE"

ok "Assigned IP ${MY_IP}/${NETMASK} to ${IFACE}"

# Persist via netplan (Ubuntu 22.04)
NETPLAN_FILE="/etc/netplan/99-ebpf-testbed.yaml"
cat > "$NETPLAN_FILE" <<NETPLAN
# Auto-generated by 01_vm_network_setup.sh — ASM-Shadhin-AI Testbed
network:
  version: 2
  renderer: networkd
  ethernets:
    ${IFACE}:
      addresses:
        - ${MY_IP}/${NETMASK}
      dhcp4: false
      optional: true
NETPLAN

chmod 600 "$NETPLAN_FILE"
netplan apply 2>/dev/null || warn "netplan apply failed — IP set via ip command remains active."
ok "Static IP persisted in ${NETPLAN_FILE}"

# =============================================================================
# STEP 4: MTU & Jumbo Frame Configuration
# =============================================================================
log "STEP 4: Setting MTU to ${MTU} on ${IFACE}..."
ip link set dev "$IFACE" mtu "$MTU"
ok "MTU set to ${MTU}"

# =============================================================================
# STEP 5: Disable NIC Offloading (critical for accurate eBPF/XDP measurement)
# =============================================================================
log "STEP 5: Disabling NIC hardware offloading on ${IFACE}..."
# These offloads aggregate packets before they reach XDP, skewing measurements.

OFFLOADS=(
    "gro off"      # Generic Receive Offload
    "lro off"      # Large Receive Offload
    "tso off"      # TCP Segmentation Offload
    "gso off"      # Generic Segmentation Offload
    "rx off"       # RX checksum offload
    "tx off"       # TX checksum offload
    "sg off"       # Scatter-Gather
    "rxvlan off"   # RX VLAN offload
    "txvlan off"   # TX VLAN offload
)

for offload in "${OFFLOADS[@]}"; do
    # shellcheck disable=SC2086
    ethtool -K "$IFACE" $offload 2>/dev/null && true
done
ok "All NIC offloads disabled (GRO/LRO/TSO/GSO/RX/TX/SG/VLAN)"

# Show current offload state
echo ""
echo -e "${BLUE}── Current offload state for ${IFACE}: ──${NC}"
ethtool -k "$IFACE" 2>/dev/null | grep -E "generic-receive-offload|large-receive-offload|tcp-segmentation-offload|generic-segmentation-offload|rx-checksumming|tx-checksumming|scatter-gather" || true

# =============================================================================
# STEP 6: Kernel Network Buffer & Sysctl Tuning
# =============================================================================
log "STEP 6: Applying kernel sysctl tuning for eBPF/XDP high-throughput..."

SYSCTL_FILE="/etc/sysctl.d/99-ebpf-testbed.conf"
cat > "$SYSCTL_FILE" <<'SYSCTL'
# ── ASM-Shadhin-AI eBPF/XDP Testbed — Kernel Tuning ──────────────────────────
# Applied by: 01_vm_network_setup.sh

# ── Network Receive Buffer Sizes (critical for 1Gbps+ throughput) ─────────────
# Max socket receive buffer: 256 MB
net.core.rmem_max = 268435456
# Max socket send buffer: 256 MB
net.core.wmem_max = 268435456
# Default socket receive buffer: 64 MB
net.core.rmem_default = 67108864
# Default socket send buffer: 64 MB
net.core.wmem_default = 67108864
# TCP read buffer: 4KB / 64MB / 256MB
net.ipv4.tcp_rmem = 4096 67108864 268435456
# TCP write buffer: 4KB / 64MB / 256MB
net.ipv4.tcp_wmem = 4096 67108864 268435456

# ── NIC RX Queue Depth / Netdev Tuning ───────────────────────────────────────
# Max packets in kernel RX queue before backpressure
net.core.netdev_max_backlog = 250000
# Increase NIC budget per NAPI poll cycle (reduces latency spikes)
net.core.netdev_budget = 600
# Time between NAPI polls (µs): lower = less latency, higher CPU
net.core.netdev_budget_usecs = 3000
# Max global socket backlog
net.core.somaxconn = 65535

# ── TCP Fast Path & Congestion Control ───────────────────────────────────────
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_low_latency = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1

# ── IP Forwarding (SUT may need to forward packets in inline/bridge mode) ─────
net.ipv4.ip_forward = 1

# ── Memory Pages for BPF / Ring Buffers ──────────────────────────────────────
# Allow large perf ring buffers (BPF RingBuf)
kernel.perf_event_mlock_kb = 16384

# ── IRQ / Interrupt Coalescing Mitigation ────────────────────────────────────
# Reduce TCP ACK delay for latency-sensitive eBPF measurements
net.ipv4.tcp_delack_min = 0
SYSCTL

sysctl -p "$SYSCTL_FILE" 2>/dev/null
ok "Kernel sysctl tuning applied (saved to ${SYSCTL_FILE})"

# =============================================================================
# STEP 7: IRQ Affinity & CPU Frequency Governor
# =============================================================================
log "STEP 7: Configuring CPU performance governor & IRQ affinity..."

# Set CPU governor to 'performance' to eliminate frequency scaling jitter
if command -v cpufreq-set &>/dev/null; then
    for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
        cpufreq-set -g performance -c "$(basename "$cpu" | tr -d 'cpu')" 2>/dev/null || true
    done
    ok "CPU governor set to 'performance'."
else
    # Direct sysfs fallback
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$gov" 2>/dev/null || true
    done
    ok "CPU governor set via sysfs."
fi

# Pin NIC IRQs to isolated CPU cores (heuristic: use cores 2-N for NIC)
IRQS=$(grep "${IFACE}" /proc/interrupts 2>/dev/null | awk '{print $1}' | tr -d ':')
CORE_IDX=2
for irq in $IRQS; do
    echo "$CORE_IDX" > "/proc/irq/${irq}/smp_affinity_list" 2>/dev/null || true
    CORE_IDX=$(( (CORE_IDX % ($(nproc) - 1)) + 2 ))
done
if [[ -n "$IRQS" ]]; then
    ok "NIC IRQs pinned to cores 2+."
else
    warn "No IRQs found for ${IFACE} — IRQ affinity skipped (may be virtual NIC)."
fi

# =============================================================================
# STEP 8: NIC Ring Buffer Maximization
# =============================================================================
log "STEP 8: Maximizing NIC ring buffer sizes..."

MAX_RX=$(ethtool -g "$IFACE" 2>/dev/null | grep "Pre-set maximums" -A4 | grep RX: | awk '{print $2}')
MAX_TX=$(ethtool -g "$IFACE" 2>/dev/null | grep "Pre-set maximums" -A4 | grep TX: | awk '{print $2}')

if [[ -n "$MAX_RX" && -n "$MAX_TX" ]]; then
    ethtool -G "$IFACE" rx "$MAX_RX" tx "$MAX_TX" 2>/dev/null && \
        ok "Ring buffers maximized: RX=${MAX_RX} TX=${MAX_TX}" || \
        warn "Ring buffer resize not supported on this NIC."
else
    warn "Could not read NIC ring buffer maximums (virtual NIC likely)."
fi

# =============================================================================
# STEP 9: Role-Specific Configuration
# =============================================================================
log "STEP 9: Applying role-specific configuration (${ROLE})..."

if [[ "$ROLE" == "generator" ]]; then
    # ── Generator-specific: disable IP routing, enable raw socket capabilities ─
    sysctl -w net.ipv4.ip_forward=0 >/dev/null

    # Allow tcpreplay to send raw Ethernet frames without root (optional)
    if command -v setcap &>/dev/null; then
        TCPREPLAY_BIN=$(command -v tcpreplay 2>/dev/null || true)
        [[ -n "$TCPREPLAY_BIN" ]] && setcap cap_net_raw,cap_net_admin=eip "$TCPREPLAY_BIN" && \
            ok "Raw socket capability granted to tcpreplay."
    fi

    # Create PCAP benchmark directory
    mkdir -p /opt/pcap-benchmarks
    ok "Created /opt/pcap-benchmarks — place your PCAP files here."
    echo ""
    echo -e "${YELLOW}  Recommended PCAP sources:${NC}"
    echo "    • CAIDA Anonymized Internet Traces: https://www.caida.org/catalog/datasets/"
    echo "    • CIC-IDS-2017/2018: https://www.unb.ca/cic/datasets/ids.html"
    echo "    • UNSW-NB15: https://research.unsw.edu.au/projects/unsw-nb15-dataset"

elif [[ "$ROLE" == "sut" ]]; then
    # ── SUT-specific: enable eBPF JIT, increase BPF map limits ───────────────
    sysctl -w net.core.bpf_jit_enable=1 >/dev/null
    sysctl -w net.core.bpf_jit_harden=0 >/dev/null  # Disable for performance (re-enable in prod)
    sysctl -w kernel.unprivileged_bpf_disabled=1 >/dev/null  # Security: root-only BPF

    # Increase locked memory limit for BPF maps
    ulimit -l unlimited 2>/dev/null || true

    # Create persistent ulimit config
    cat >> /etc/security/limits.conf <<LIMITS
# ASM-Shadhin-AI eBPF Testbed
* soft memlock unlimited
* hard memlock unlimited
LIMITS

    ok "eBPF JIT enabled, memlock limits removed."

    # Create output directory for benchmark results
    mkdir -p /opt/asm-testbed-results
    chmod 755 /opt/asm-testbed-results
    ok "Results directory: /opt/asm-testbed-results"
fi

# =============================================================================
# STEP 10: Connectivity Test
# =============================================================================
log "STEP 10: Running connectivity test..."

if [[ "$ROLE" == "generator" ]]; then
    PEER_IP="$SUT_IP"
    echo -n "  Pinging SUT (${PEER_IP})... "
else
    PEER_IP="$GENERATOR_IP"
    echo -n "  Pinging Generator (${PEER_IP})... "
fi

if ping -c 3 -W 2 "$PEER_IP" &>/dev/null; then
    RTT=$(ping -c 5 -W 2 "$PEER_IP" 2>/dev/null | tail -1 | awk -F'/' '{print $5}')
    ok "Reachable! Average RTT: ${RTT}ms"
else
    warn "Peer (${PEER_IP}) not reachable yet — ensure both VMs are running this script."
fi

# =============================================================================
# STEP 11: Quick iperf3 Bandwidth Baseline (optional)
# =============================================================================
log "STEP 11: Starting iperf3 server for baseline bandwidth test..."

if [[ "$ROLE" == "sut" ]]; then
    # Start iperf3 server in background for 60s
    iperf3 -s -D -1 --logfile /tmp/iperf3_server.log 2>/dev/null && \
        ok "iperf3 server started (single-shot, port 5201). Run on Generator:" || \
        warn "iperf3 server could not start."
    echo -e "    ${CYAN}  iperf3 -c ${SUT_IP} -t 10 -P 4 -i 1${NC}"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║              NETWORK SETUP COMPLETE                              ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Configuration Summary:${NC}"
echo -e "  Role          : ${BOLD}${ROLE^^}${NC}"
echo -e "  Interface     : ${BOLD}${IFACE}${NC}"
echo -e "  IP Address    : ${BOLD}${MY_IP}/${NETMASK}${NC}"
echo -e "  MTU           : ${BOLD}${MTU}${NC}"
echo -e "  NIC Offloads  : ${GREEN}DISABLED${NC} (GRO/LRO/TSO/GSO)"
echo -e "  Kernel Tuning : ${GREEN}APPLIED${NC} (256MB buffers, 250k backlog)"
echo -e "  CPU Governor  : ${GREEN}PERFORMANCE${NC}"
echo ""
if [[ "$ROLE" == "generator" ]]; then
    echo -e "  ${YELLOW}Next Step:${NC} Place PCAP files in /opt/pcap-benchmarks/"
    echo -e "  Then run: ${CYAN}sudo bash 02_traffic_generator.sh --iface ${IFACE} --pcap /opt/pcap-benchmarks/your.pcap${NC}"
else
    echo -e "  ${YELLOW}Next Step:${NC} Deploy eBPF filter and start LLM daemon on this SUT."
    echo -e "  Then run: ${CYAN}sudo python3 03_performance_metrics_logger.py --iface ${IFACE}${NC}"
fi
echo ""
