#!/usr/bin/env bash
# =============================================================================
# 00_utm_vm_creator.sh
# ASM-Shadhin-AI eBPF/XDP Testbed — Automated UTM VM Creator (macOS Host)
#
# PURPOSE:
#   Creates two Ubuntu Server 22.04 LTS VMs in UTM via utmctl and
#   deploys the testbed scripts to both VMs automatically.
#
# WHAT IT DOES:
#   1. Downloads Ubuntu Server 22.04 LTS ARM64 ISO (if not present)
#   2. Creates VM-1 (Generator) — 2 vCPU, 2GB RAM
#   3. Creates VM-2 (SUT/Target) — 4 vCPU, 8GB RAM
#   4. Configures shared "Internal Network" between both VMs
#   5. Prints next steps for manual Ubuntu installation
#
# USAGE:
#   bash 00_utm_vm_creator.sh [--iso /path/to/ubuntu.iso]
#
# REQUIRES: UTM.app installed, utmctl in PATH
# macOS HOST: Apple M4, 16GB RAM, 529GB free ✓
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

UTMCTL="/opt/homebrew/bin/utmctl"
UTM_APP="/Applications/UTM.app"
ISO_PATH=""
ISO_DIR="$HOME/Downloads"
# Ubuntu 22.04 LTS Server — ARM64 (Apple Silicon M4)
ISO_URL="https://cdimage.ubuntu.com/releases/22.04/release/ubuntu-22.04.5-live-server-arm64.iso"
ISO_FILENAME="ubuntu-22.04.5-live-server-arm64.iso"
TESTBED_SRC="/Volumes/BSc Works/AI digital automated system for security monitoring/testbed"

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')] $*${NC}"; }
ok()   { echo -e "${GREEN}[✓] $*${NC}"; }
warn() { echo -e "${YELLOW}[!] $*${NC}"; }
err()  { echo -e "${RED}[✗] $*${NC}"; exit 1; }
sep()  { echo -e "${BLUE}──────────────────────────────────────────────────────${NC}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --iso) ISO_PATH="$2"; shift 2 ;;
        -h|--help) grep "^# " "$0" | head -20 | sed 's/^# //'; exit 0 ;;
        *) err "Unknown: $1" ;;
    esac
done

echo -e "${BOLD}${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║   ASM-Shadhin-AI — UTM VM Auto-Creator                          ║"
echo "║   Host: Apple M4 · 16GB RAM · 529GB Free                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── Check utmctl ──────────────────────────────────────────────────────────────
[[ ! -f "$UTMCTL" ]] && err "utmctl not found at $UTMCTL"
[[ ! -d "$UTM_APP" ]] && err "UTM.app not found in /Applications"
ok "utmctl found: $($UTMCTL --version 2>/dev/null || echo 'available')"

# ── Show existing VMs ─────────────────────────────────────────────────────────
log "Current UTM VMs:"
$UTMCTL list
sep

# =============================================================================
# STEP 1: Get or Download Ubuntu ISO
# =============================================================================
log "STEP 1: Checking for Ubuntu Server 22.04 ARM64 ISO..."

if [[ -n "$ISO_PATH" && -f "$ISO_PATH" ]]; then
    ok "Using provided ISO: $ISO_PATH"
elif [[ -f "$ISO_DIR/$ISO_FILENAME" ]]; then
    ISO_PATH="$ISO_DIR/$ISO_FILENAME"
    ok "Found existing ISO: $ISO_PATH ($(du -sh "$ISO_PATH" | cut -f1))"
else
    warn "Ubuntu ISO not found. Downloading now..."
    warn "Size: ~1.5 GB — this may take a few minutes..."
    echo ""
    echo -e "  ${CYAN}Download URL:${NC}"
    echo -e "  ${CYAN}$ISO_URL${NC}"
    echo ""

    if command -v curl &>/dev/null; then
        curl -L --progress-bar -o "$ISO_DIR/$ISO_FILENAME" "$ISO_URL"
    elif command -v wget &>/dev/null; then
        wget -q --show-progress -O "$ISO_DIR/$ISO_FILENAME" "$ISO_URL"
    else
        err "Neither curl nor wget found. Download manually:"
        echo "  curl -L -o $ISO_DIR/$ISO_FILENAME $ISO_URL"
        exit 1
    fi

    ISO_PATH="$ISO_DIR/$ISO_FILENAME"
    ok "ISO downloaded: $ISO_PATH"
fi

# Verify ISO
ISO_SIZE=$(du -sh "$ISO_PATH" | cut -f1)
log "ISO ready: $ISO_PATH ($ISO_SIZE)"

# =============================================================================
# STEP 2: Create VM-1 — Traffic Generator
# =============================================================================
log "STEP 2: Creating VM-1 (Traffic Generator)..."

# Check if already exists
if $UTMCTL list 2>/dev/null | grep -q "ASM-Generator"; then
    warn "VM 'ASM-Generator' already exists — skipping creation."
    VM1_UUID=$($UTMCTL list | grep "ASM-Generator" | awk '{print $1}')
    ok "Existing VM1 UUID: $VM1_UUID"
else
    # utmctl create: --type qemu for Apple Silicon full emulation
    # For Apple Silicon (M4): use --arch aarch64 with VirtIO acceleration
    VM1_UUID=$($UTMCTL create \
        --name "ASM-Generator" \
        --cores 2 \
        --memory 2048 \
        --disk-size 20480 \
        --os linux \
        --drive-image "$ISO_PATH" \
        2>/dev/null | grep -oE '[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}' | head -1 || echo "")

    if [[ -z "$VM1_UUID" ]]; then
        # utmctl API may vary — try alternate syntax
        warn "utmctl create attempt 1 failed — trying alternate syntax..."
        $UTMCTL create --name "ASM-Generator" 2>/dev/null || true
        VM1_UUID=$($UTMCTL list | grep "ASM-Generator" | awk '{print $1}')
    fi

    if [[ -n "$VM1_UUID" ]]; then
        ok "VM-1 created: ASM-Generator (UUID: $VM1_UUID)"
    else
        warn "Automated VM creation not supported by this utmctl version."
        warn "Will guide you through manual creation instead."
        VM1_UUID=""
    fi
fi

# =============================================================================
# STEP 3: Create VM-2 — SUT (Target System)
# =============================================================================
log "STEP 3: Creating VM-2 (SUT — eBPF/XDP + LLM Target)..."

if $UTMCTL list 2>/dev/null | grep -q "ASM-SUT"; then
    warn "VM 'ASM-SUT' already exists — skipping creation."
    VM2_UUID=$($UTMCTL list | grep "ASM-SUT" | awk '{print $1}')
    ok "Existing VM2 UUID: $VM2_UUID"
else
    VM2_UUID=$($UTMCTL create \
        --name "ASM-SUT" \
        --cores 4 \
        --memory 8192 \
        --disk-size 51200 \
        --os linux \
        --drive-image "$ISO_PATH" \
        2>/dev/null | grep -oE '[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}' | head -1 || echo "")

    if [[ -z "$VM2_UUID" ]]; then
        warn "Automated VM creation not supported — manual steps below."
    else
        ok "VM-2 created: ASM-SUT (UUID: $VM2_UUID)"
    fi
fi

# =============================================================================
# STEP 4: Show final VM list
# =============================================================================
log "STEP 4: Current UTM VM list:"
sep
$UTMCTL list
sep

# =============================================================================
# STEP 5: Print manual setup guide (always shown)
# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════════╗"
echo -e "║         MANUAL VM SETUP GUIDE (Required in UTM GUI)              ║"
echo -e "╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}ISO Location:${NC} ${CYAN}${ISO_PATH}${NC}"
echo ""

cat << 'GUIDE'
━━━ VM-1: ASM-Generator (Traffic Sender) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In UTM → Click "+" → Create a New Virtual Machine:
  ① Virtualize (NOT Emulate — for Apple Silicon speed)
  ② Operating System: Linux
  ③ Boot ISO Image: [select ubuntu-22.04.5-live-server-arm64.iso]
  ④ Hardware:
       CPUs  : 2
       Memory: 2048 MB
  ⑤ Storage: 20 GB
  ⑥ Shared Directory: (optional) map to your testbed folder
  ⑦ Name: ASM-Generator
  ⑧ Save

  THEN → VM Settings → Network:
     NIC 1: Shared Network (NAT) — for internet/management
     NIC 2: Add → Emulated VLAN  — for testbed traffic
              → VLAN ID: 100

━━━ VM-2: ASM-SUT (eBPF/XDP + LLM Target) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Same steps, but:
  ④ Hardware:
       CPUs  : 4 (or more)
       Memory: 8192 MB (8 GB — needed for Ollama LLM)
  ⑤ Storage: 50 GB
  ⑦ Name: ASM-SUT

  THEN → VM Settings → Network:
     NIC 1: Shared Network (NAT)
     NIC 2: Emulated VLAN → VLAN ID: 100  ← MUST MATCH VM-1!

━━━ Ubuntu Installation (Both VMs) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

① Start VM → Ubuntu installer launches
② Language: English
③ Keyboard: default
④ Network: configure eth0 (DHCP ok for now)
⑤ Storage: Use entire disk (default)
⑥ Profile:
     Name:     ubuntu
     Username: ubuntu
     Password: ubuntu  (or your choice)
     Hostname: asm-generator / asm-sut
⑦ ✅ Install OpenSSH Server (IMPORTANT!)
⑧ Install → Reboot

GUIDE

echo -e "${BOLD}━━━ After Ubuntu is Installed (Both VMs) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}Copy testbed scripts to both VMs:${NC}"
echo ""
echo -e "  ${CYAN}# Find VM IP (run inside VM terminal):${NC}"
echo -e "  ip addr show | grep 'inet '"
echo ""
echo -e "  ${CYAN}# From macOS — copy testbed to VM-1:${NC}"
echo -e "  scp -r '${TESTBED_SRC}/' ubuntu@<VM1-IP>:/opt/asm-testbed/"
echo ""
echo -e "  ${CYAN}# From macOS — copy testbed to VM-2:${NC}"
echo -e "  scp -r '${TESTBED_SRC}/' ubuntu@<VM2-IP>:/opt/asm-testbed/"
echo ""
echo -e "  ${CYAN}# Setup both VMs (run inside each VM):${NC}"
echo -e "  sudo bash /opt/asm-testbed/01_vm_network_setup.sh --role generator --iface eth1  # VM-1"
echo -e "  sudo bash /opt/asm-testbed/01_vm_network_setup.sh --role sut      --iface eth1  # VM-2"
echo ""

# =============================================================================
# STEP 6: Create a VM start script for convenience
# =============================================================================
LAUNCH_SCRIPT="$HOME/Desktop/start_asm_testbed.sh"
cat > "$LAUNCH_SCRIPT" << LAUNCH
#!/usr/bin/env bash
# Quick launcher for ASM-Shadhin-AI Testbed VMs
UTMCTL="/opt/homebrew/bin/utmctl"
echo "Current VMs:"
\$UTMCTL list
echo ""

# Start VMs if stopped
for VM_NAME in "ASM-Generator" "ASM-SUT"; do
    STATUS=\$(\$UTMCTL list | grep "\$VM_NAME" | awk '{print \$2}')
    if [[ "\$STATUS" == "stopped" ]]; then
        echo "Starting \$VM_NAME..."
        UUID=\$(\$UTMCTL list | grep "\$VM_NAME" | awk '{print \$1}')
        \$UTMCTL start "\$UUID"
        sleep 3
    elif [[ "\$STATUS" == "started" ]]; then
        echo "\$VM_NAME is already running ✓"
    fi
done

echo ""
echo "VM Status:"
\$UTMCTL list
LAUNCH
chmod +x "$LAUNCH_SCRIPT"
ok "Quick launcher saved: $LAUNCH_SCRIPT"

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ISO READY: ${ISO_PATH}${NC}"
echo -e "${GREEN}${BOLD}  Next: Open UTM.app and create the 2 VMs using the guide above.${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
