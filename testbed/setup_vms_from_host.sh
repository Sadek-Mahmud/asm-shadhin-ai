#!/usr/bin/env bash
# ==============================================================================
# ASM-Shadhin-AI: Host-Side One-Click VM Provisioner & Setup
# Run this on macOS after installing Ubuntu on UTM VMs: "ASM-Generator" & "ASM-SUT"
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

UTMCTL="/opt/homebrew/bin/utmctl"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VM_GEN_NAME="ASM-Generator"
VM_SUT_NAME="ASM-SUT"
SSH_USER="ubuntu"
SSH_KEY="${HOME}/.ssh/id_ed25519"

echo "=================================================================="
echo "    ASM-Shadhin-AI — Host Automation Provisioner"
echo "=================================================================="

# Check utmctl
if [[ ! -x "$UTMCTL" ]]; then
    log_error "utmctl not found at $UTMCTL"
    exit 1
fi

log_info "Detecting UTM VM status..."
$UTMCTL list

# Get IP of Generator
get_vm_ip() {
    local vm_name="$1"
    local ip=""
    ip=$($UTMCTL ip-address "$vm_name" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || true)
    echo "$ip"
}

log_info "Querying IP for $VM_GEN_NAME..."
GEN_IP=$(get_vm_ip "$VM_GEN_NAME")
if [[ -z "$GEN_IP" ]]; then
    read -rp "Enter IP address for $VM_GEN_NAME (e.g., 192.168.64.x): " GEN_IP
fi
log_ok "$VM_GEN_NAME IP: $GEN_IP"

log_info "Querying IP for $VM_SUT_NAME..."
SUT_IP=$(get_vm_ip "$VM_SUT_NAME")
if [[ -z "$SUT_IP" ]]; then
    read -rp "Enter IP address for $VM_SUT_NAME (e.g., 192.168.64.y): " SUT_IP
fi
log_ok "$VM_SUT_NAME IP: $SUT_IP"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5"

# Copy SSH public key if available
if [[ -f "${SSH_KEY}.pub" ]]; then
    log_info "Ensuring SSH key access on $VM_GEN_NAME..."
    ssh-copy-id -i "${SSH_KEY}.pub" ${SSH_OPTS} "${SSH_USER}@${GEN_IP}" 2>/dev/null || true
    log_info "Ensuring SSH key access on $VM_SUT_NAME..."
    ssh-copy-id -i "${SSH_KEY}.pub" ${SSH_OPTS} "${SSH_USER}@${SUT_IP}" 2>/dev/null || true
fi

# Sync files to Generator
log_info "Uploading testbed suite to $VM_GEN_NAME ($GEN_IP)..."
ssh ${SSH_OPTS} "${SSH_USER}@${GEN_IP}" "sudo mkdir -p /opt/asm-testbed && sudo chown -R ${SSH_USER}:${SSH_USER} /opt/asm-testbed"
scp ${SSH_OPTS} -r "${SCRIPT_DIR}/"* "${SSH_USER}@${GEN_IP}:/opt/asm-testbed/"
ssh ${SSH_OPTS} "${SSH_USER}@${GEN_IP}" "chmod +x /opt/asm-testbed/*.sh /opt/asm-testbed/*.py"
log_ok "Uploaded to $VM_GEN_NAME"

# Sync files to SUT
log_info "Uploading full project suite to $VM_SUT_NAME ($SUT_IP)..."
ssh ${SSH_OPTS} "${SSH_USER}@${SUT_IP}" "sudo mkdir -p /opt/asm-firewall && sudo chown -R ${SSH_USER}:${SSH_USER} /opt/asm-firewall"
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude 'build' \
    -e "ssh ${SSH_OPTS}" "${PROJECT_ROOT}/" "${SSH_USER}@${SUT_IP}:/opt/asm-firewall/"
ssh ${SSH_OPTS} "${SSH_USER}@${SUT_IP}" "chmod +x /opt/asm-firewall/testbed/*.sh /opt/asm-firewall/testbed/*.py /opt/asm-firewall/*.sh 2>/dev/null || true"
log_ok "Uploaded to $VM_SUT_NAME"

# Configure Network on Generator
log_info "Configuring network on $VM_GEN_NAME (10.100.0.1)..."
ssh ${SSH_OPTS} "${SSH_USER}@${GEN_IP}" "sudo bash /opt/asm-testbed/01_vm_network_setup.sh --role generator --iface eth1"
log_ok "$VM_GEN_NAME network ready."

# Configure Network on SUT
log_info "Configuring network on $VM_SUT_NAME (10.100.0.2)..."
ssh ${SSH_OPTS} "${SSH_USER}@${SUT_IP}" "sudo bash /opt/asm-firewall/testbed/01_vm_network_setup.sh --role sut --iface eth1"
ssh ${SSH_OPTS} "${SSH_USER}@${SUT_IP}" "sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip linux-tools-common linux-tools-\$(uname -r) tcpreplay jq htop ethtool && pip3 install -r /opt/asm-firewall/testbed/requirements.txt"
log_ok "$VM_SUT_NAME network and dependencies ready."

# Connectivity test
log_info "Testing VLAN 100 connectivity (ping 10.100.0.2 from 10.100.0.1)..."
if ssh ${SSH_OPTS} "${SSH_USER}@${GEN_IP}" "ping -c 3 -W 2 10.100.0.2"; then
    log_ok "VLAN 100 connection ACTIVE! 10.100.0.1 <---> 10.100.0.2"
else
    log_warn "Ping check failed! Please ensure both VMs have Network 2 set to Emulated VLAN 100 in UTM."
fi

echo ""
echo "=================================================================="
echo -e "${GREEN}PROVISIONING COMPLETE!${NC}"
echo "To run the benchmark benchmark suite, execute on $VM_GEN_NAME:"
echo "  ssh ${SSH_USER}@${GEN_IP}"
echo "  sudo bash /opt/asm-testbed/04_run_benchmark.sh \\"
echo "      --iface eth1 \\"
echo "      --pcap /path/to/test.pcap \\"
echo "      --sut-ip 10.100.0.2 \\"
echo "      --sut-user ${SSH_USER} \\"
echo "      --ssh-key ~/.ssh/id_ed25519"
echo "=================================================================="
