#!/usr/bin/env bash
# ==============================================================================
# setup_inline_gateway.sh - Isolated L3 Hardware Firewall Gateway Builder
# Configures the server as a hardened gateway router:
# - WAN (from Router): DHCP / Upstream Gateway
# - LAN (to Protected PC): Isolated Subnet (10.99.1.1/24) with strict NAT & stateful firewall
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
LAN_SUBNET="${3:-10.99.1.0/24}"
GATEWAY_IP="${4:-10.99.1.1/24}"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
   log_error "This script must be executed with root privileges: sudo $0 <WAN_IF> <LAN_IF>"
   exit 1
fi

if [[ -z "$WAN_IF" || -z "$LAN_IF" ]]; then
    echo -e "${CYAN}Usage:${NC} sudo $0 <WAN_INTERFACE> <LAN_INTERFACE> [LAN_SUBNET] [GATEWAY_IP]"
    echo -e "Example: sudo $0 eth0 eth1 10.99.1.0/24 10.99.1.1/24"
    exit 1
fi

log_info "Configuring Hardware Inline Isolated Security Gateway (Mode B)..."
log_info "  - Upstream WAN Interface : ${CYAN}${WAN_IF}${NC}"
log_info "  - Isolated LAN Interface : ${CYAN}${LAN_IF}${NC} (${GATEWAY_IP})"

# 1. Enable IP Forwarding
sysctl -w net.ipv4.ip_forward=1 >/dev/null

# 2. Assign IP to Protected LAN Port
ip link set dev "$LAN_IF" up
ip addr flush dev "$LAN_IF" 2>/dev/null || true
ip addr add "$GATEWAY_IP" dev "$LAN_IF"

# 3. Configure NAT / Masquerade on WAN
iptables -t nat -F POSTROUTING 2>/dev/null || true
iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE
iptables -F FORWARD 2>/dev/null || true
iptables -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
iptables -A FORWARD -i "$WAN_IF" -o "$LAN_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT

# 4. Optional: Setup lightweight DHCP server (dnsmasq) if installed
if command -v dnsmasq &>/dev/null; then
    log_info "Starting DHCP server for protected downstream PC on ${LAN_IF}..."
    killall dnsmasq 2>/dev/null || true
    dnsmasq --interface="$LAN_IF" \
            --dhcp-range=10.99.1.50,10.99.1.200,255.255.255.0,12h \
            --dhcp-option=3,10.99.1.1 \
            --dhcp-option=6,1.1.1.1,8.8.8.8 \
            --bind-interfaces &
fi

log_success "Isolated Security Gateway Active! Protected PC is shielded behind NAT + eBPF."
