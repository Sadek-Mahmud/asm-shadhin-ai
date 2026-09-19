#!/usr/bin/env bash
# ==============================================================================
# configure_suricata_inline.sh - Configure Suricata for Inline IPS Mode
# Bridges WAN_IF <-> LAN_IF via AF_PACKET zero-copy packet inspection.
# ==============================================================================

set -euo pipefail

WAN_IF="${1:-eth0}"
LAN_IF="${2:-eth1}"
SURICATA_CONF="/etc/suricata/suricata.yaml"

if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] Must run as root"
   exit 1
fi

echo "[INFO] Configuring Suricata AF_PACKET Inline IPS Mode between $WAN_IF <-> $LAN_IF..."

if [[ -f "$SURICATA_CONF" ]]; then
    # Backup original config
    cp "$SURICATA_CONF" "$SURICATA_CONF.bak_inline" 2>/dev/null || true

    # Create inline IPS snippet for af-packet
    cat <<EOF > /etc/suricata/suricata_inline_afpacket.yaml
af-packet:
  - interface: ${WAN_IF}
    threads: auto
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
    copy-mode: ips
    copy-iface: ${LAN_IF}
    buffer-size: 64535
  - interface: ${LAN_IF}
    threads: auto
    cluster-id: 98
    cluster-type: cluster_flow
    defrag: yes
    copy-mode: ips
    copy-iface: ${WAN_IF}
    buffer-size: 64535
EOF
    echo "[✓] Suricata inline af-packet configuration generated."
else
    echo "[!] Suricata configuration file not found at $SURICATA_CONF (suricata not yet installed or running standalone)."
fi
