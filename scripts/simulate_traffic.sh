#!/usr/bin/env bash
# ==============================================================================
# simulate_traffic.sh - Security Simulation & Verification Toolkit
# Validates:
# 1. Direct eBPF Fast-Path XDP Drop
# 2. Suricata Alert -> asm-shadhin-ai LLM -> Automated eBPF Block Pipeline
# 3. AI-Tarpit Bot Deception & Token-Drain Response
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TARGET_IP="${1:-198.51.100.99}"
EVE_LOG="${SURICATA_EVE_PATH:-/var/log/suricata/eve.json}"

echo -e "${CYAN}==========================================================================${NC}"
echo -e "${CYAN}       AI INLINE DEFENSE SYSTEM - SECURITY VERIFICATION TESTER           ${NC}"
echo -e "${CYAN}==========================================================================${NC}"

# Test 1: Simulate Suricata High-Severity Exploit Alert
echo -e "\n${BLUE}[TEST 1] Simulating High-Severity Suricata Alert for IP: ${TARGET_IP}...${NC}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.%6N+0000")

MOCK_ALERT=$(cat <<EOF
{"timestamp":"${TIMESTAMP}","flow_id":1029384756,"event_type":"alert","src_ip":"${TARGET_IP}","src_port":44321,"dest_ip":"192.168.1.10","dest_port":80,"proto":"TCP","alert":{"action":"allowed","gid":1,"signature_id":2010935,"rev":3,"signature":"ET EXPLOIT Apache Log4j RCE Attempt (CVE-2021-44228)","category":"Attempted Administrator Privilege Gain","severity":1}}
EOF
)

if [[ -f "$EVE_LOG" || -w "$(dirname "$EVE_LOG")" ]]; then
    echo "$MOCK_ALERT" >> "$EVE_LOG"
    echo -e "${GREEN}[✓] Injected synthetic Log4j exploit alert into ${EVE_LOG}${NC}"
    echo -e "    Waiting 4 seconds for sec-daemon & asm-shadhin-ai evaluation..."
    sleep 4
else
    echo -e "${YELLOW}[!] ${EVE_LOG} not writable directly. Ensure security_daemon is running in test mode.${NC}"
fi

# Test 2: Verify Kernel eBPF Map State
echo -e "\n${BLUE}[TEST 2] Checking Kernel eBPF blocked_ips_map via bpftool...${NC}"
if command -v bpftool &>/dev/null && [[ -f "/sys/fs/bpf/blocked_ips_map" ]]; then
    echo "Dumping blocked IPs:"
    bpftool map dump pinned /sys/fs/bpf/blocked_ips_map || true
else
    echo -e "${YELLOW}[!] bpftool or pinned map not found at /sys/fs/bpf/blocked_ips_map.${NC}"
    echo -e "    (Run sudo ./scripts/deploy.sh first to attach the XDP filter)."
fi

# Test 3: AI-Tarpit Deception Test
echo -e "\n${BLUE}[TEST 3] Testing AI-Tarpit Token-Drain Honey-Port (HTTP 8088)...${NC}"
if nc -z 127.0.0.1 8088 2>/dev/null || curl -s --max-time 1 http://127.0.0.1:8088 >/dev/null 2>&1; then
    echo -e "${GREEN}[✓] Port 8088 is open. Connecting as simulated vulnerability scanner...${NC}"
    echo -e "--- Received Tarpit Stream (first 5 chunks) ---"
    curl -s -N --max-time 5 "http://127.0.0.1:8088/admin/secret_cluster.env" | head -n 5 || true
    echo -e "-----------------------------------------------"
else
    echo -e "${YELLOW}[!] AI-Tarpit port 8088 is not currently listening. Start sec-tarpit.service to test.${NC}"
fi

# Test 4: Post-Quantum Cryptography Test
echo -e "\n${BLUE}[TEST 4] Running Post-Quantum Cryptography Handshake Test...${NC}"
if command -v python3 &>/dev/null; then
    python3 "$(dirname "$0")/test_pqc_handshake.py"
fi

echo -e "\n${GREEN}==========================================================================${NC}"
echo -e "${GREEN}                     TEST SUITE EXECUTION COMPLETED                       ${NC}"
echo -e "${GREEN}==========================================================================${NC}"
