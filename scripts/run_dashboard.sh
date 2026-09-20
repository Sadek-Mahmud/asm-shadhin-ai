#!/usr/bin/env bash
# Quick launcher for Q-Vigilance AI Cyber Defense Dashboard
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/dashboard"

echo "=================================================================="
echo "  Starting Q-Vigilance AI — Autonomous Defense Operations Center..."
echo "  Access URL: http://localhost:9090  (or http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1'):9090)"
echo "=================================================================="

if [[ -f "$ROOT_DIR/venv/bin/python3" ]]; then
    "$ROOT_DIR/venv/bin/python3" app.py
else
    python3 app.py
fi
