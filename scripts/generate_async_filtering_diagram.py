#!/usr/bin/env python3
"""
generate_async_filtering_diagram.py
================================================================================
Generates publication-quality architectural flow diagram illustrating fast-path
packet filtering control during the Edge-LLM's 2.41s asynchronous latency window.
Saves to docs/figures/fig_async_filtering_lifecycle.png
================================================================================
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

WS = "/Volumes/BSc Works/AI digital automated system for security monitoring"
DOCS_FIG = os.path.join(WS, "docs/figures")
os.makedirs(DOCS_FIG, exist_ok=True)

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['axes.linewidth'] = 0.75

fig, ax = plt.subplots(figsize=(7.1, 4.0), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Background Zones
# Zone 1: In-Kernel Fast-Path (XDP / eBPF)
fast_path_bg = patches.FancyBboxPatch((1, 2), 46, 95, boxstyle="round,pad=1.0",
                                     edgecolor="#004c6d", facecolor="#f0f7fa", linewidth=1.2)
ax.add_patch(fast_path_bg)
ax.text(24, 94, "IN-KERNEL FAST PATH: eBPF / XDP (Driver Level, < 0.2 µs)",
        fontsize=8.5, fontweight='bold', ha='center', color="#004c6d")

# Zone 2: Edge-LLM Slow Path (User-Space)
slow_path_bg = patches.FancyBboxPatch((53, 2), 46, 95, boxstyle="round,pad=1.0",
                                     edgecolor="#7b1fa2", facecolor="#fcf5ff", linewidth=1.2)
ax.add_patch(slow_path_bg)
ax.text(76, 94, "EDGE-LLM ASYNCHRONOUS SLOW PATH (User-Space, ~2.41 s)",
        fontsize=8.5, fontweight='bold', ha='center', color="#7b1fa2")

# Fast Path Steps
# 1. Packet Ingestion
p1 = patches.Rectangle((4, 79), 40, 10, facecolor="#ffffff", edgecolor="#004c6d", linewidth=1.0)
ax.add_patch(p1)
ax.text(24, 85, "1. Ingress Packet Hook (XDP)", fontsize=8, fontweight='bold', ha='center')
ax.text(24, 81.5, "L3/L4 Parsing + LPM Blocklist Trie Check", fontsize=7, ha='center', color="#333333")

# Arrow p1 -> p2
ax.annotate('', xy=(24, 67), xytext=(24, 79),
            arrowprops=dict(arrowstyle="->", color="#004c6d", lw=1.2))

# 2. Streaming Entropy & Jitter Check
p2 = patches.Rectangle((4, 57), 40, 10, facecolor="#ffffff", edgecolor="#004c6d", linewidth=1.0)
ax.add_patch(p2)
ax.text(24, 63, "2. Stage 4: Dual-Metric Anomaly Trigger", fontsize=8, fontweight='bold', ha='center')
ax.text(24, 59.5, "Is Entropy H >= 7.85 and Jitter J <= 0.10 s?", fontsize=7, ha='center', color="#c53929")

# Decision branches from p2
# If No: Pass
ax.annotate('No: Line-Rate Pass\n(WireGuard / Normal Web)', xy=(3, 48), xytext=(8, 57),
            fontsize=6.5, color="#1b5e20", ha='center',
            arrowprops=dict(arrowstyle="->", color="#1b5e20", lw=1.0, linestyle="--"))
ax.text(3, 44, "[XDP_PASS]\n(0 µs penalty)", fontsize=6.5, fontweight='bold', color="#1b5e20", ha='center')

# If Yes: Quarantine + Telemetry Push
ax.annotate('Yes: Flagged Anomaly', xy=(24, 45), xytext=(24, 57),
            fontsize=7, fontweight='bold', color="#c53929", ha='center',
            arrowprops=dict(arrowstyle="->", color="#c53929", lw=1.2))

# 3. Fast-Path In-Flight Control (The 2.41s window)
p3 = patches.Rectangle((4, 23), 40, 22, facecolor="#fff9db", edgecolor="#f57f17", linewidth=1.2)
ax.add_patch(p3)
ax.text(24, 41, "3. Fast-Path In-Flight Filtering (2.41s Window)", fontsize=7.5, fontweight='bold', ha='center', color="#b78103")
ax.text(24, 37.5, "• Flow registered in suspicious_flow_table (LRU)", fontsize=6.8, ha='center', color="#333333")
ax.text(24, 34, "• Speculative Token Bucket: clamped to 10 pps", fontsize=6.8, ha='center', color="#d32f2f", fontweight='bold')
ax.text(24, 30.5, "• Tarpit Throttling on SYN Handshakes (win=0)", fontsize=6.8, ha='center', color="#333333")
ax.text(24, 26, "Prevents data exfiltration & exploit delivery!", fontsize=6.8, fontstyle='italic', ha='center', color="#1565c0")

# Push across the boundary via Lock-Free Ring Buffer
ax.annotate('', xy=(56, 75), xytext=(36, 45),
            arrowprops=dict(arrowstyle="->", color="#7b1fa2", lw=1.5, linestyle="-"))
ax.text(49, 62, "Lock-Free RingBuffer\n(30-byte telemetry event)", fontsize=7, fontweight='bold',
        ha='center', color="#7b1fa2", bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec="#7b1fa2", lw=0.8))

# Slow Path Steps
# 4. Ring Buffer Polling & Prompt Synthesis
p4 = patches.Rectangle((56, 70), 40, 11, facecolor="#ffffff", edgecolor="#7b1fa2", linewidth=1.0)
ax.add_patch(p4)
ax.text(76, 77, "4. Telemetry Ingestion (epoll)", fontsize=8, fontweight='bold', ha='center')
ax.text(76, 73, "Extracts 5-Tuple, Entropy Hint, Jitter (AVX2)", fontsize=7, ha='center', color="#333333")

# Arrow p4 -> p5
ax.annotate('', xy=(76, 57), xytext=(76, 70),
            arrowprops=dict(arrowstyle="->", color="#7b1fa2", lw=1.2))

# 5. Edge-LLM GBNF Grammar Constrained Reasoning
p5 = patches.Rectangle((56, 41), 40, 16, facecolor="#ffffff", edgecolor="#7b1fa2", linewidth=1.0)
ax.add_patch(p5)
ax.text(76, 53, "5. Edge-LLM Semantic Triage", fontsize=8, fontweight='bold', ha='center')
ax.text(76, 49, "Qwen2.5-Coder-3B Q4_K_M (T=0, Greedy)", fontsize=7, ha='center', color="#333333")
ax.text(76, 45, "Strict Context-Free JSON Grammar (GBNF)", fontsize=7, ha='center', color="#7b1fa2")
ax.text(76, 42.5, "Mean Execution Latency: 2.41 seconds", fontsize=7, fontweight='bold', ha='center', color="#c53929")

# Arrow p5 -> p6
ax.annotate('', xy=(76, 28), xytext=(76, 41),
            arrowprops=dict(arrowstyle="->", color="#7b1fa2", lw=1.2))

# 6. Atomic Policy Dispatch
p6 = patches.Rectangle((56, 12), 40, 16, facecolor="#ffffff", edgecolor="#7b1fa2", linewidth=1.0)
ax.add_patch(p6)
ax.text(76, 24, "6. Verdict & Atomic Kernel Sync", fontsize=8, fontweight='bold', ha='center')
ax.text(76, 20.5, "PQC Signature (ML-DSA-65) on Audit Log", fontsize=6.8, ha='center', color="#333333")
ax.text(76, 16.5, "MALICIOUS: bpf_map_update_elem() (< 5 µs)", fontsize=6.8, fontweight='bold', ha='center', color="#c53929")
ax.text(76, 13.5, "BENIGN: Clear flow from quarantine table", fontsize=6.8, fontweight='bold', ha='center', color="#2e7d32")

# Feedback from User-Space to In-Kernel Fast-Path
ax.annotate('', xy=(34, 18), xytext=(56, 18),
            arrowprops=dict(arrowstyle="->", color="#c53929", lw=1.5, linestyle="-"))
ax.text(45, 13, "Atomic BPF Map Update\n(< 5 µs live sync)", fontsize=6.8, fontweight='bold',
        ha='center', color="#c53929", bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec="#c53929", lw=0.8))

# Final Action in Fast-Path
p7 = patches.Rectangle((4, 7), 30, 13, facecolor="#ffebee", edgecolor="#c53929", linewidth=1.0)
ax.add_patch(p7)
ax.text(19, 16, "Permanent Enforcement", fontsize=7.5, fontweight='bold', ha='center', color="#c53929")
ax.text(19, 12, "• Hard XDP_DROP at wire speed", fontsize=6.5, ha='center')
ax.text(19, 8.5, "• Out-of-Band TCP RST Injection", fontsize=6.5, ha='center')

plt.tight_layout()
out_file = os.path.join(DOCS_FIG, "fig_async_filtering_lifecycle.png")
plt.savefig(out_file, dpi=300)
plt.close()
print(f"[+] Successfully generated async filtering architecture diagram: {out_file}")

if __name__ == "__main__":
    pass
