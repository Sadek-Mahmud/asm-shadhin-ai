#!/usr/bin/env bash
# ==============================================================================
# deploy.sh - Turnkey Deployment Script for AI Network Security System
# Headless Ubuntu Server (Intel Core i5 4th Gen, 16GB RAM, 4-Port PCIe GbE NIC)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TARGET_INSTALL_DIR="/opt/ai-security-system"
WAN_IF="${1:-}"
LAN_IF="${2:-}"
MODE="${3:-bridge}"  # 'bridge' (Transparent L2) or 'gateway' (Isolated L3)
BRIDGE_NAME="br0"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓ SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ------------------------------------------------------------------------------
# 1. Root & Hardware Pre-Flight Checks
# ------------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be executed with root privileges:"
   echo -e "  Dual-NIC Inline Bridge : sudo bash deploy.sh [WAN_IF] [LAN_IF] [bridge|gateway]"
   echo -e "  Single-NIC Sensor Mode : sudo bash deploy.sh [INTERFACE]"
   exit 1
fi

echo -e "${CYAN}"
echo "=========================================================================="
echo "    AI-Driven Automated Network Security Monitoring & Defense System      "
echo "      eBPF/XDP Fast-Path | A S M Shadhin AI (asm-shadhin-ai) | PQC | AI-Tarpit         "
echo "=========================================================================="
echo -e "${NC}"

# Auto-detect interfaces if not specified
PHYSICAL_IFS=($(ip -o link show | awk -F': ' '$2 !~ /^(lo|docker|veth|br-|virbr|dummy)/ {print $2}'))

if [[ -z "$WAN_IF" ]]; then
    if [[ ${#PHYSICAL_IFS[@]} -ge 2 ]]; then
        WAN_IF="${PHYSICAL_IFS[0]}"
        LAN_IF="${PHYSICAL_IFS[1]}"
        log_info "Auto-detected Dual-NIC Hardware Appliance configuration:"
        log_info "  - Inbound WAN Interface (Router Side) : ${CYAN}${WAN_IF}${NC}"
        log_info "  - Protected LAN Interface (PC Side)   : ${CYAN}${LAN_IF}${NC}"
    elif [[ ${#PHYSICAL_IFS[@]} -eq 1 ]]; then
        WAN_IF="${PHYSICAL_IFS[0]}"
        LAN_IF=""
        log_warn "Single network interface detected: ${WAN_IF} (Operating in Host Sensor Mode)."
    else
        WAN_IF="eth0"
        LAN_IF=""
    fi
elif [[ -n "$WAN_IF" && -z "$LAN_IF" && ${#PHYSICAL_IFS[@]} -ge 2 && "$WAN_IF" == "${PHYSICAL_IFS[0]}" ]]; then
    # If user passed only 1 interface but machine has 2, auto-select 2nd as LAN
    LAN_IF="${PHYSICAL_IFS[1]}"
    log_info "Auto-paired second interface for Protected PC: ${CYAN}${LAN_IF}${NC}"
fi

INTERFACE="$WAN_IF"
log_info "Primary Inbound Interface : ${CYAN}${WAN_IF}${NC}"
if [[ -n "$LAN_IF" ]]; then
    log_info "Protected Downstream Interface : ${CYAN}${LAN_IF}${NC}"
    log_info "Deployment Topology: ${GREEN}INLINE HARDWARE SECURITY APPLIANCE (${MODE^^})${NC}"
else
    log_info "Deployment Topology: ${YELLOW}SINGLE-NIC HOST SENSOR MODE${NC}"
fi

# Hardware validation
CPU_FLAGS=$(lscpu 2>/dev/null | grep -i Flags || true)
if [[ "$CPU_FLAGS" =~ "avx2" ]]; then
    log_success "Intel AVX2 instruction set detected (Optimal for Quantized LLM & Crypto)."
else
    log_warn "AVX2 instructions not found; CPU inference may exhibit higher latency."
fi

# ------------------------------------------------------------------------------
# 2. Install System Dependencies & Compilers
# ------------------------------------------------------------------------------
log_info "Updating apt repositories and installing compiler tools..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

apt-get install -y -qq \
    build-essential \
    clang \
    llvm \
    libbpf-dev \
    linux-headers-$(uname -r) \
    linux-tools-common \
    linux-tools-generic \
    linux-tools-$(uname -r) || true

# Install bpftool if not present
if ! command -v bpftool &>/dev/null; then
    apt-get install -y -qq linux-tools-$(uname -r) || apt-get install -y -qq bpftool || true
fi

# Install Suricata IDS and utilities
log_info "Installing Suricata IDS and supporting utilities..."
apt-get install -y -qq suricata jq curl git python3 python3-pip python3-venv iptables

# ------------------------------------------------------------------------------
# 3. Mount BPF Virtual Filesystem
# ------------------------------------------------------------------------------
log_info "Configuring BPF filesystem..."
if ! mount | grep -q "/sys/fs/bpf"; then
    mount -t bpf bpf /sys/fs/bpf
    echo "bpf /sys/fs/bpf bpf defaults 0 0" >> /etc/fstab
    log_success "Mounted /sys/fs/bpf."
else
    log_success "/sys/fs/bpf already mounted."
fi

# ------------------------------------------------------------------------------
# 4. Ollama Installation & Model Compilation
# ------------------------------------------------------------------------------
if ! command -v ollama &>/dev/null; then
    log_info "Installing Ollama local inference engine..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    log_success "Ollama is already installed."
fi

# Ensure ollama service is running
systemctl daemon-reload
systemctl enable --now ollama
sleep 3

LOCAL_GGUF=$(find "$ROOT_DIR/models" -maxdepth 1 -name "*.gguf" 2>/dev/null | head -n 1 || true)
if [[ -n "$LOCAL_GGUF" && -f "$LOCAL_GGUF" ]]; then
    log_success "Found bundled offline AI model: $LOCAL_GGUF ($(du -h "$LOCAL_GGUF" | cut -f1))"
    log_info "Registering asm-shadhin-ai in Ollama directly from bundled GGUF (Zero Download)..."
    cd "$ROOT_DIR"
    ollama create asm-shadhin-ai -f "$ROOT_DIR/Modelfile.offline"
    log_success "asm-shadhin-ai registered in Ollama from local offline bundle."
else
    log_info "No offline GGUF found. Pulling A S M Shadhin AI base model from registry..."
    ollama pull asm-shadhin-ai
    log_info "Compiling custom model asm-shadhin-ai from Modelfile..."
    cd "$ROOT_DIR"
    ollama create asm-shadhin-ai -f "$ROOT_DIR/Modelfile"
    log_success "asm-shadhin-ai model compiled successfully."
fi

# ------------------------------------------------------------------------------
# 5. Compile eBPF Kernel Filter
# ------------------------------------------------------------------------------
log_info "Compiling eBPF/XDP C filter via Clang..."
cd "$ROOT_DIR/ebpf"
make clean
make all
if [[ ! -f "$ROOT_DIR/ebpf/ebpf_filter.o" ]]; then
    log_error "eBPF compilation failed! Check clang and linux headers."
    exit 1
fi
log_success "eBPF bytecode generated at $ROOT_DIR/ebpf/ebpf_filter.o"

# ------------------------------------------------------------------------------
# 6. Setup Directory & Python Virtual Environment
# ------------------------------------------------------------------------------
log_info "Deploying code to ${TARGET_INSTALL_DIR}..."
mkdir -p "$TARGET_INSTALL_DIR"
cp -r "$ROOT_DIR"/* "$TARGET_INSTALL_DIR"/

cd "$TARGET_INSTALL_DIR"
python3 -m venv venv

if [[ -d "$TARGET_INSTALL_DIR/wheels" ]] && compgen -G "$TARGET_INSTALL_DIR/wheels/*.whl" > /dev/null; then
    log_info "Installing Python dependencies from bundled offline wheels/ directory..."
    venv/bin/pip install --no-index --find-links="$TARGET_INSTALL_DIR/wheels" -r daemon/requirements.txt
else
    log_info "Installing Python dependencies via pip..."
    venv/bin/pip install --upgrade pip || true
    venv/bin/pip install -r daemon/requirements.txt
fi


# Run PQC cryptographic self-test
log_info "Executing Post-Quantum Cryptography self-test..."
venv/bin/python3 daemon/pqc_guard.py
log_success "PQC Module verification passed."

# ------------------------------------------------------------------------------
# 7. Hardware Inline Bridge / Dual-NIC Setup & Tarpit Ports
# ------------------------------------------------------------------------------
if [[ -n "$LAN_IF" ]]; then
    log_info "Configuring Hardware Inline Security Bridge between ${WAN_IF} <-> ${LAN_IF}..."
    if [[ "$MODE" == "gateway" ]]; then
        bash "$TARGET_INSTALL_DIR/scripts/setup_inline_gateway.sh" "$WAN_IF" "$LAN_IF"
    else
        bash "$TARGET_INSTALL_DIR/scripts/setup_inline_bridge.sh" "$WAN_IF" "$LAN_IF" "$BRIDGE_NAME"
    fi
    bash "$TARGET_INSTALL_DIR/scripts/configure_suricata_inline.sh" "$WAN_IF" "$LAN_IF"

    # Persist bridge configuration
    mkdir -p /etc/default
    cat <<EOF > /etc/default/ai-security-system
WAN_INTERFACE=${WAN_IF}
LAN_INTERFACE=${LAN_IF}
BRIDGE_NAME=${BRIDGE_NAME}
INLINE_MODE=${MODE}
SEC_INTERFACE=${BRIDGE_NAME}
EOF
    cp "$TARGET_INSTALL_DIR/systemd/sec-inline-bridge.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable sec-inline-bridge.service 2>/dev/null || true
    ACTIVE_MONITOR_IF="$BRIDGE_NAME"
else
    ACTIVE_MONITOR_IF="$WAN_IF"
fi

log_info "Configuring iptables decoy port rules for AI-Tarpit..."
# Decoy ports 8088 (HTTP) and 2222 (SSH)
iptables -t nat -C PREROUTING -p tcp --dport 8088 -j ACCEPT 2>/dev/null || \
    iptables -t nat -A PREROUTING -p tcp --dport 8088 -j ACCEPT
iptables -t nat -C PREROUTING -p tcp --dport 2222 -j ACCEPT 2>/dev/null || \
    iptables -t nat -A PREROUTING -p tcp --dport 2222 -j ACCEPT

# ------------------------------------------------------------------------------
# 8. Attach eBPF/XDP Program to Inbound Interface
# ------------------------------------------------------------------------------
log_info "Attaching eBPF/XDP filter to inbound WAN interface: ${WAN_IF}..."
# First detach any preexisting filter
ip link set dev "${WAN_IF}" xdp off 2>/dev/null || true

# Attempt Native Driver XDP first, fallback to Generic (SKB) mode
if ip link set dev "${WAN_IF}" xdpoffload obj "$TARGET_INSTALL_DIR/ebpf/ebpf_filter.o" sec xdp 2>/dev/null; then
    log_success "Attached via Hardware/Driver XDP Offload on ${WAN_IF}!"
elif ip link set dev "${WAN_IF}" xdpdrv obj "$TARGET_INSTALL_DIR/ebpf/ebpf_filter.o" sec xdp 2>/dev/null; then
    log_success "Attached via Native Driver XDP on ${WAN_IF} (Line-rate active)."
else
    log_warn "Native XDP not supported by NIC driver. Falling back to Generic (SKB) XDP mode..."
    ip link set dev "${WAN_IF}" xdpgeneric obj "$TARGET_INSTALL_DIR/ebpf/ebpf_filter.o" sec xdp
    log_success "Attached via Generic SKB XDP on ${WAN_IF}."
fi

# ------------------------------------------------------------------------------
# 9. Install and Start Systemd Services
# ------------------------------------------------------------------------------
log_info "Configuring and enabling Systemd services..."
cp "$TARGET_INSTALL_DIR/systemd/sec-monitor.service" /etc/systemd/system/
cp "$TARGET_INSTALL_DIR/systemd/sec-tarpit.service" /etc/systemd/system/
cp "$TARGET_INSTALL_DIR/systemd/sec-dashboard.service" /etc/systemd/system/

# Replace placeholder interface in service file
sed -i "s/SEC_INTERFACE=eth0/SEC_INTERFACE=${ACTIVE_MONITOR_IF}/g" /etc/systemd/system/sec-monitor.service

systemctl daemon-reload
systemctl enable --now sec-monitor.service
systemctl enable --now sec-tarpit.service
systemctl enable --now sec-dashboard.service

# ------------------------------------------------------------------------------
# 10. Final Status Report
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}=========================================================================="
echo "                   DEPLOYMENT COMPLETED SUCCESSFULLY                       "
echo "==========================================================================${NC}"
echo -e "Inbound WAN (Router)    : ${CYAN}${WAN_IF}${NC}"
if [[ -n "$LAN_IF" ]]; then
    echo -e "Protected LAN (Core PC) : ${CYAN}${LAN_IF}${NC}"
    echo -e "Security Topology       : ${GREEN}INLINE HARDWARE BRIDGE (${MODE^^} MODE)${NC}"
    echo -e "Bridge Interface        : ${CYAN}${BRIDGE_NAME}${NC}"
else
    echo -e "Security Topology       : ${YELLOW}SINGLE-NIC HOST SENSOR MODE${NC}"
fi
echo -e "eBPF Filter Status      : ${GREEN}ACTIVE (XDP on ${WAN_IF})${NC}"
echo -e "Local LLM Model         : ${CYAN}A S M Shadhin AI (asm-shadhin-ai)${NC}"
echo -e "Post-Quantum Cryptography: ${GREEN}NIST ML-KEM-768 / ML-DSA-65 ONLINE${NC}"
echo -e "AI-Tarpit Deception     : ${GREEN}HTTP: 8088 | SSH: 2222 ACTIVE${NC}"
echo -e "Suricata Monitor Daemon : ${GREEN}ACTIVE (sec-monitor.service)${NC}"
echo -e "Web SOC Dashboard       : ${CYAN}http://<server-ip>:5050 (sec-dashboard.service)${NC}"
echo ""
echo "Useful Commands:"
echo "  - Open Web SOC Dashboard   : http://<server-ip>:9090"
echo "  - Monitor Live Daemon Logs : journalctl -u sec-monitor.service -f"
echo "  - Monitor AI-Tarpit Traps  : journalctl -u sec-tarpit.service -f"
echo "  - View eBPF Blocklist Map  : bpftool map dump pinned /sys/fs/bpf/blocked_ips_map"
echo "  - Detach XDP Filter        : ip link set dev ${INTERFACE} xdp off"
echo "=========================================================================="

