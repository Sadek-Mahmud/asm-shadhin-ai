import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def generate_perfect_fig1():
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
    plt.rcParams['mathtext.fontset'] = 'stix'
    plt.rcParams['font.size'] = 9.2
    plt.rcParams['axes.linewidth'] = 0.8

    fig, ax = plt.subplots(figsize=(5.6, 2.6), dpi=300)

    stages = [
        "Stage 1: IP Blocklist\n(Hash Map Match)",
        "Stage 2: Tarpit Redirect\n(Sockmap Redirection)",
        "Stage 3: TCP Flag Classifier\n(SYN/RST Anomaly)",
        "Stage 4: RingBuffer Telemetry\n(Zero-Copy Push)"
    ]
    latencies = [0.33, 0.85, 0.45, 0.92]
    actions = [
        "XDP_DROP (0.33 µs)",
        "XDP_REDIRECT (0.85 µs)",
        "XDP_DROP (0.45 µs)",
        "XDP_PASS (0.92 µs)"
    ]
    
    # Modern professional IEEE palette
    # Crimson for DROP, Amber/Orange for REDIRECT, Blue/Teal for PASS
    colors = ["#dc2626", "#ea580c", "#dc2626", "#0284c7"]

    y_pos = np.arange(len(stages))
    
    # Shaded SLA compliance zone (0 to 2.0 µs)
    ax.axvspan(0, 2.0, color='#f0fdf4', alpha=0.45, zorder=1)

    # Invert so Stage 1 is at top
    bars = ax.barh(y_pos, latencies, color=colors, height=0.52, edgecolor='#1e293b', linewidth=0.9, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages, fontsize=8.6, fontweight='bold', color='#1e293b')
    ax.invert_yaxis()

    ax.set_xlabel("Measured Fast-Path Latency (µs) — Hardware DMA Testbed", fontsize=9.0, fontweight='bold', labelpad=5)
    ax.set_xlim(0, 2.30)
    ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)
    ax.tick_params(axis='x', labelsize=8.8)
    ax.tick_params(axis='y', labelsize=8.6)

    # Badges next to each bar
    for bar, action in zip(bars, actions):
        width = bar.get_width()
        ax.text(width + 0.04, bar.get_y() + bar.get_height() / 2.0, action,
                ha='left', va='center', fontsize=8.3, fontweight='bold', color='#0f172a')

    # Line-Rate SLA Line at 2.0 µs
    ax.axvline(2.0, color="#b91c1c", linestyle="--", linewidth=1.5, zorder=4)
    ax.text(1.97, 3.48, "Line-Rate SLA (2.0 µs Limit)", ha='right', va='center',
            fontsize=8.0, fontweight='bold', color="#b91c1c",
            bbox=dict(boxstyle='round,pad=0.35', facecolor='#fef2f2', edgecolor="#fca5a5", linewidth=0.9, alpha=0.95))

    ax.set_ylim(3.8, -0.6)

    plt.tight_layout()
    out_path = "docs/figures/fig1_xdp_pipeline.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"✅ Generated crisp Fig 1: {out_path}")

if __name__ == '__main__':
    generate_perfect_fig1()
