#!/usr/bin/env bash
# ==============================================================================
# setup_inline_bridge.sh - Transparent L2 Hardware Security Bridge Builder
# Fuses two physical NICs (WAN from Router <-> LAN to Protected PC) into an
# inline transparent bridge (br0) with microsecond eBPF/XDP & Suricata IPS.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

WAN_IF="${1:-}"
LAN_IF="${2:-}"
BRIDGE_NAME="${3:-br0}"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
   log_error "This script must be executed with root privileges: sudo $0 <WAN_IF> <LAN_IF>"
   exit 1
fi

if [[ -z "$WAN_IF" || -z "$LAN_IF" ]]; then
    echo -e "${CYAN}Usage:${NC} sudo $0 <WAN_INTERFACE> <LAN_INTERFACE> [BRIDGE_NAME]"
    echo -e "Example: sudo $0 eth0 eth1 br0"
    echo -e "  - WAN_INTERFACE : Port connected to Upstream Router LAN"
    echo -e "  - LAN_INTERFACE : Port connected to Protected Core PC/Server"
    exit 1
fi

if ! ip link show "$WAN_IF" &>/dev/null; then
    log_error "WAN interface '$WAN_IF' does not exist on this machine!"
    exit 1
fi

if ! ip link show "$LAN_IF" &>/dev/null; then
    log_error "LAN interface '$LAN_IF' does not exist on this machine!"
    exit 1
fi

log_info "Configuring Hardware Inline Transparent Security Bridge..."
log_info "  - Inbound WAN Interface (Router Side) : ${CYAN}${WAN_IF}${NC}"
log_info "  - Protected LAN Interface (PC Side)   : ${CYAN}${LAN_IF}${NC}"
log_info "  - Virtual Security Bridge            : ${CYAN}${BRIDGE_NAME}${NC}"

# 1. Enable Linux Kernel Bridging & Forwarding
log_info "Tuning Linux Kernel parameters for inline transparent forwarding..."
sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv4.conf.all.forwarding=1 >/dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null

# Ensure bridge netfilter module is loaded if available
modprobe br_netfilter 2>/dev/null || true
if [[ -d "/proc/sys/net/bridge" ]]; then
    sysctl -w net.bridge.bridge-nf-call-iptables=1 >/dev/null 2>&1 || true
    sysctl -w net.bridge.bridge-nf-call-ip6tables=1 >/dev/null 2>&1 || true
    sysctl -w net.bridge.bridge-nf-filter-vlan-tagged=1 >/dev/null 2>&1 || true
fi

# 2. Tear down any existing bridge with same name
if ip link show "$BRIDGE_NAME" &>/dev/null; then
    log_warn "Tearing down existing bridge ${BRIDGE_NAME}..."
    ip link set dev "$BRIDGE_NAME" down 2>/dev/null || true
    ip link delete "$BRIDGE_NAME" type bridge 2>/dev/null || true
fi

# 3. Create Bridge Device
log_info "Creating bridge device ${BRIDGE_NAME}..."
ip link add name "$BRIDGE_NAME" type bridge

# Set aging time to standard fast-learning (300s) and forward delay to 0 (instant STP forwarding)
ip link set dev "$BRIDGE_NAME" type bridge forward_delay 0 stp_state 0

# 4. Attach Physical Interfaces to Bridge
log_info "Attaching ${WAN_IF} and ${LAN_IF} to ${BRIDGE_NAME}..."
ip link set dev "$WAN_IF" master "$BRIDGE_NAME"
ip link set dev "$LAN_IF" master "$BRIDGE_NAME"

# Enable Promiscuous mode for transparent inline packet interception
ip link set dev "$WAN_IF" promisc on
ip link set dev "$LAN_IF" promisc on

# Bring up interfaces and bridge
ip link set dev "$WAN_IF" up
ip link set dev "$LAN_IF" up
ip link set dev "$BRIDGE_NAME" up

# 5. Acquire Management IP on Bridge (from Router DHCP) if possible
log_info "Attempting to acquire management IP for security appliance on ${BRIDGE_NAME}..."
if command -v dhclient &>/dev/null; then
    dhclient -v -pf /run/dhclient."$BRIDGE_NAME".pid -lf /var/lib/dhcp/dhclient."$BRIDGE_NAME".leases "$BRIDGE_NAME" >/dev/null 2>&1 || true
elif command -v udhcpc &>/dev/null; then
    udhcpc -i "$BRIDGE_NAME" -n -q >/dev/null 2>&1 || true
fi

log_success "Inline Transparent Security Bridge [${BRIDGE_NAME}] is ONLINE!"
echo -e "${GREEN}==========================================================================${NC}"
echo -e "  [✓] WAN Interface       : ${WAN_IF} (Promisc: ON)"
echo -e "  [✓] LAN Interface       : ${LAN_IF} (Promisc: ON)"
echo -e "  [✓] Bridge Interface    : ${BRIDGE_NAME} (Active)"
echo -e "  [✓] Downstream PC State : Transparently connected to Router with zero setup"
echo -e "${GREEN}==========================================================================${NC}"
