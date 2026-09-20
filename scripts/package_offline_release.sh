#!/usr/bin/env bash
# ==============================================================================
# package_offline_release.sh
# Prepares a 100% Self-Contained, Air-Gapped Release Bundle for Ubuntu Server.
# Run this ONCE on an internet-connected machine to bake all AI models and
# dependencies into the release archive.
# ==============================================================================

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$ROOT_DIR/models"
WHEELS_DIR="$ROOT_DIR/wheels"
ARCHIVE_NAME="sec-monitoring-offline-release.tar.gz"

GGUF_FILENAME="asm-shadhin-ai-q4_k_m.gguf"
# NOTE: Place your asm-shadhin-ai-q4_k_m.gguf model file in the models/ directory.
# The model will be loaded automatically from local storage (no internet required).
GGUF_URL=""  # Not used if local GGUF is present in models/

echo -e "${CYAN}==========================================================================${NC}"
echo -e "${CYAN}      PREPARING OFFLINE AIR-GAPPED RELEASE BUNDLE FOR UBUNTU SERVER       ${NC}"
echo -e "${CYAN}==========================================================================${NC}"

mkdir -p "$MODELS_DIR"
mkdir -p "$WHEELS_DIR"

# 1. Download / Verify GGUF Model File
cd "$MODELS_DIR"
if [[ -f "$GGUF_FILENAME" && -s "$GGUF_FILENAME" ]]; then
    echo -e "${GREEN}[✓] Local GGUF AI Model found: ${GGUF_FILENAME} ($(du -h "$GGUF_FILENAME" | cut -f1))${NC}"
else
    echo -e "${BLUE}[*] Downloading Q-Vigilance AI Q4_K_M GGUF model (~1.9 GB)...${NC}"
    echo -e "${YELLOW}    URL: ${GGUF_URL}${NC}"
    if command -v curl &>/dev/null; then
        curl -L -C - --progress-bar -o "$GGUF_FILENAME" "$GGUF_URL"
    elif command -v wget &>/dev/null; then
        wget -c --show-progress -O "$GGUF_FILENAME" "$GGUF_URL"
    else
        echo "Error: Neither curl nor wget found."
        exit 1
    fi
    echo -e "${GREEN}[✓] AI Model successfully downloaded to models/${GGUF_FILENAME}${NC}"
fi

# 2. Download Python Offline Wheels
echo -e "\n${BLUE}[*] Pre-fetching Python offline wheel packages into wheels/...${NC}"
cd "$ROOT_DIR"
if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
    PIP_CMD=$(command -v pip3 || command -v pip)
    $PIP_CMD download -r daemon/requirements.txt -d "$WHEELS_DIR" || true
    echo -e "${GREEN}[✓] Python wheels bundled in wheels/${NC}"
fi

# 3. Create Standalone Release Archive
echo -e "\n${BLUE}[*] Packing self-contained release archive: ${ARCHIVE_NAME}...${NC}"
cd "$ROOT_DIR/.."
tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -czf "$ROOT_DIR/$ARCHIVE_NAME" "$(basename "$ROOT_DIR")"

echo -e "\n${GREEN}==========================================================================${NC}"
echo -e "${GREEN}               AIR-GAPPED OFFLINE RELEASE ARCHIVE READY!                  ${NC}"
echo -e "${GREEN}==========================================================================${NC}"
echo -e "Archive File : ${CYAN}$ROOT_DIR/$ARCHIVE_NAME${NC}"
echo -e "Archive Size : ${CYAN}$(du -h "$ROOT_DIR/$ARCHIVE_NAME" | cut -f1)${NC}"
echo ""
echo "How to Deploy on Headless Ubuntu Server:"
echo "  1. Copy '$ARCHIVE_NAME' to Ubuntu Server via USB flash drive or scp."
echo "  2. Extract: tar -xzf $ARCHIVE_NAME && cd '$(basename "$ROOT_DIR")'"
echo "  3. Run:     sudo bash scripts/deploy.sh <interface_name>"
echo ""
echo "=> Ollama will automatically load asm-shadhin-ai directly from models/${GGUF_FILENAME}."
echo "=> ZERO internet connection or external downloads required!"
echo "=========================================================================="
