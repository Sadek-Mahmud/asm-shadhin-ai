#!/usr/bin/env python3
"""
generate_paper_figures.py
Generates publication-grade, high-resolution (300 DPI) IEEE standard figures
corresponding to Tables I, II, III, IV, and V in the research paper.
All plots use authentic data from the evaluation tables with zero dummy data.
No overlapping labels or clipped legends.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Set strict IEEE Publication typography
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 9.0
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['axes.titlesize'] = 10.5
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.0
plt.rcParams['figure.titlesize'] = 11.0
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.alpha'] = 0.4

OUT_DIR = "/Volumes/BSc Works/AI digital automated system for security monitoring/docs/figures"
os.makedirs(OUT_DIR, exist_ok=True)

# Curated IEEE palette
COLOR_OURS = "#0f766e"      # Deep Teal (Ours)
COLOR_OURS_LIGHT = "#14b8a6"
COLOR_ACCENT = "#0284c7"    # Sky Blue
COLOR_SNORT = "#64748b"     # Slate Gray
COLOR_SURI = "#475569"      # Dark Slate
COLOR_PALO = "#d97706"      # Amber
COLOR_CF = "#ea580c"        # Orange
COLOR_CISCO = "#7c3aed"     # Deep Violet


# ==============================================================================
# FIG 1: In-Kernel XDP Pipeline Latency Breakdown (Table I)
# ==============================================================================
def generate_fig1_xdp_pipeline():
    stages = [
        "Stage 1: IP Blocklist\n(Hash Map Match)",
        "Stage 2: Tarpit Redirect\n(Sockmap Redirection)",
        "Stage 3: TCP Flag Classifier\n(SYN/RST Anomaly)",
        "Stage 4: RingBuffer Telemetry\n(Async User-Space Push)"
    ]
    latencies = [0.33, 0.85, 0.45, 0.92]  # in microseconds
    actions = ["XDP_DROP (0.33 µs)", "XDP_PASS (0.85 µs)", "XDP_DROP (0.45 µs)", "XDP_PASS (0.92 µs)"]
    bar_colors = ["#b91c1c", "#d97706", "#b91c1c", "#0f766e"]

    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    y_pos = np.arange(len(stages))
    
    bars = ax.barh(y_pos, latencies, color=bar_colors, height=0.52, edgecolor="#1e293b", linewidth=0.8, zorder=3)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages, fontweight="normal", fontsize=8.5)
    ax.invert_yaxis()  # Top-down order
    ax.set_xlabel("Measured Kernel Latency (µs) — Hardware DMA Testbed", fontweight="bold", fontsize=9)
    ax.set_xlim(0, 2.3)
    ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)

    # Clean text badges next to bars
    for bar, action in zip(bars, actions):
        width = bar.get_width()
        ax.text(width + 0.04, bar.get_y() + bar.get_height()/2.0, action,
                ha='left', va='center', fontsize=8.0, fontweight='bold', color="#1e293b")

    # SLA Line
    ax.axvline(2.0, color="#dc2626", linestyle=":", linewidth=1.3, label="Line-Rate Budget SLA Target (2.0 µs max)", zorder=4)
    ax.legend(loc="lower right", frameon=True, edgecolor="#cbd5e1", facecolor="#ffffff", framealpha=0.95)

    plt.title("In-Kernel XDP Pipeline Execution Latency per Stage (Table I)", fontweight="bold", pad=10)
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, "fig1_xdp_pipeline.png")
    plt.savefig(out_path)
    plt.close()
    print(f"[✓] Fig 1 saved: {out_path}")


# ==============================================================================
# FIG 2: Architectural Sovereignty & Autonomy Comparison Curves (Table II)
# ==============================================================================
def generate_fig2_architecture_comparison():
    categories = [
        'Data\nSovereignty',
        'Air-Gap\nCapability',
        'Zero Cloud\nDependencies',
        'In-Kernel\nLine-Rate',
        'Active Attacker\nDeception'
    ]

    ours =       [100, 100, 100, 100, 100]
    snort_suri = [ 85,  75,  90,  30,   0]
    palo_cisco = [ 40,   0,   0,  90,  15]
    cloudflare = [  0,   0,   0,  75,  20]

    x = np.arange(len(categories))
    x_smooth = np.linspace(0, len(categories) - 1, 300)

    def smooth_curve(x_pts, y_pts, x_new):
        n = len(x_pts)
        dx = np.diff(x_pts)
        dy = np.diff(y_pts)
        m = dy / dx
        d = np.zeros(n)
        d[0] = m[0]
        d[-1] = m[-1]
        for i in range(1, n - 1):
            if m[i-1] * m[i] <= 0:
                d[i] = 0
            else:
                d[i] = 2.0 / (1.0/m[i-1] + 1.0/m[i])
        
        y_new = np.zeros_like(x_new)
        for idx, xi in enumerate(x_new):
            i = min(int(np.floor(xi)), n - 2)
            i = max(i, 0)
            h = dx[i]
            t = (xi - x_pts[i]) / h
            h00 = 2*t**3 - 3*t**2 + 1
            h10 = t**3 - 2*t**2 + t
            h01 = -2*t**3 + 3*t**2
            h11 = t**3 - t**2
            y_val = h00 * y_pts[i] + h10 * h * d[i] + h01 * y_pts[i+1] + h11 * h * d[i+1]
            y_new[idx] = np.clip(y_val, 0, 100)
        return y_new

    fig, ax = plt.subplots(figsize=(7.2, 3.6))

    series = [
        ("Autonomous Agent (Ours)", ours, COLOR_OURS, "-", "o", 2.6, 7),
        ("Snort 3.x / Suricata 7.x", snort_suri, COLOR_SURI, "--", "s", 1.8, 6),
        ("Palo Alto / Cisco Firepower", palo_cisco, COLOR_PALO, "-.", "^", 1.8, 6),
        ("Cloudflare Magic Transit", cloudflare, COLOR_CF, ":", "D", 1.8, 5)
    ]

    for label, data, color, ls, marker, lw, ms in series:
        y_smooth = smooth_curve(x, data, x_smooth)
        ax.plot(x_smooth, y_smooth, color=color, linestyle=ls, linewidth=lw, label=label, zorder=4)
        ax.plot(x, data, color=color, linestyle="none", marker=marker, markersize=ms,
                markeredgewidth=1.2, markeredgecolor="white" if label.startswith("Auto") else color,
                markerfacecolor=color, zorder=5)

    y_ours_smooth = smooth_curve(x, ours, x_smooth)
    ax.fill_between(x_smooth, 0, y_ours_smooth, color=COLOR_OURS, alpha=0.08, zorder=2)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontweight="bold", fontsize=8.5)
    ax.set_ylabel("Autonomy & Compliance Score (%)", fontweight="bold", fontsize=9.0)
    ax.set_ylim(-2, 108)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8.5)
    ax.grid(True, linestyle="--", alpha=0.5, zorder=1)

    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
              ncol=4, mode="expand", borderaxespad=0., frameon=True,
              edgecolor="#cbd5e1", fontsize=7.8)

    plt.title("Architectural Sovereignty & Autonomy Comparison Curves (Table II)", fontweight="bold", pad=28, fontsize=9.8)
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, "fig2_architecture_comparison.png")
    plt.savefig(out_path)
    plt.close()
    print(f"[✓] Fig 2 saved: {out_path}")


# ==============================================================================
# FIG 3: Detection Accuracy & Evasion Resistance (Table III)
# ==============================================================================
def generate_fig3_detection_accuracy():
    metrics = [
        "Evasion Recall / TPR\n(Higher is better)",
        "False Positive Rate\n(Lower is better)",
        "Encrypted C2 Detect\n(Zero-Decryption)",
        "Scan Evasion Resist\n(MTD Disruption)",
        "Adversarial Robustness\n(Prompt / Evasion)"
    ]
    
    # Exact data from Table III
    snort =      [68.4, 14.8, 12.0, 41.0, 29.0]
    suricata =   [71.2, 11.3, 18.5, 49.0, 34.0]
    palo_alto =  [89.2,  4.5, 72.3, 76.0, 67.0]
    cloudflare = [87.6,  5.1, 68.0, 63.0, 61.0]
    cisco =      [85.4,  6.2, 64.1, 71.0, 59.0]
    ours =       [98.64, 0.12, 87.9, 96.8, 94.1]
    
    x = np.arange(len(metrics))
    width = 0.13

    # Taller figure so annotations+legend have room
    fig, ax = plt.subplots(figsize=(7.6, 5.0))

    ax.bar(x - 2.5*width, snort,      width, label='Snort 3.x',          color="#cbd5e1", edgecolor="#475569", linewidth=0.5)
    ax.bar(x - 1.5*width, suricata,   width, label='Suricata 7.x',       color="#94a3b8", edgecolor="#334155", linewidth=0.5)
    ax.bar(x - 0.5*width, palo_alto,  width, label='Palo Alto PAN-OS',   color="#f59e0b", edgecolor="#78350f", linewidth=0.5)
    ax.bar(x + 0.5*width, cloudflare, width, label='Cloudflare MT',      color="#ea580c", edgecolor="#7c2d12", linewidth=0.5)
    ax.bar(x + 1.5*width, cisco,      width, label='Cisco Firepower',    color="#8b5cf6", edgecolor="#4c1d95", linewidth=0.5)
    rects6 = ax.bar(x + 2.5*width, ours, width, label='Autonomous Agent (Ours)', color="#0f766e", edgecolor="#042f2e", linewidth=1.0)

    ax.set_ylabel("Detection / Robustness Rate (%)", fontweight="bold", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=8.0, fontweight="bold")
    # Extra headroom above 100 for annotations, legend goes below
    ax.set_ylim(0, 130)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Legend placed BELOW x-axis labels so it never overlaps annotations
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=3, frameon=True, edgecolor="#cbd5e1", fontsize=7.5)

    # Annotate each 'Ours' bar — text always above bar, arrow down to top of bar
    for i, rect in enumerate(rects6):
        height = rect.get_height()
        label_str = f'{height:.2f}%' if height < 1.0 else f'{height:.1f}%'
        bar_cx = rect.get_x() + rect.get_width() / 2
        # FPR bar is tiny — needs large lift so text is visible
        text_y = max(height + 18, 6) if height < 1.0 else height + 6
        ax.annotate(label_str,
                    xy=(bar_cx, height),
                    xytext=(bar_cx, text_y),
                    textcoords="data",
                    ha='center', va='bottom', fontsize=7.5, fontweight='bold', color="#0f766e",
                    arrowprops=dict(arrowstyle="->", color="#0f766e", lw=1.1,
                                   shrinkA=2, shrinkB=2))

    plt.title("Detection Accuracy & Evasion Resistance Benchmark Across 10M Flows (Table III)",
              fontweight="bold", pad=10)
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, "fig3_detection_accuracy.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"[✓] Fig 3 saved: {out_path}")


# ==============================================================================
# FIG 4: Mitigation Latency Spectrum (Table IV)
# ==============================================================================
def generate_fig4_latency_comparison():
    systems = [
        "Snort 3.x\n(User-Space DAQ)",
        "Suricata 7.x\n(AF_PACKET / Ring)",
        "Palo Alto\n(Hardware / Cloud)",
        "Cloudflare\n(WAN Anycast Scrub)",
        "Cisco Firepower\n(NGIPS Kernel Module)",
        "Autonomous Agent\n(Kernel eBPF/XDP)"
    ]
    
    # In microseconds
    lat_data_plane = [525.0, 390.0, 72.5, 45000.0, 230.0, 0.33]
    lat_control_plane = [140000.0, 100000.0, 300000.0, 200000.0, 500000.0, 148000.0]
    
    x = np.arange(len(systems))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7.4, 4.4))

    b1 = ax.bar(x - width/2, lat_data_plane,  width, label='Data-Plane Inline Drop / Forward Latency',
                color="#0f766e", edgecolor="#042f2e", linewidth=0.8, zorder=3)
    b2 = ax.bar(x + width/2, lat_control_plane, width, label='Control-Plane Semantic Triage Latency',
                color="#0284c7", edgecolor="#0369a1", linewidth=0.8, zorder=3)

    ax.set_ylabel("Measured Latency (µs) — Logarithmic Scale", fontweight="bold", fontsize=9)
    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(systems, fontsize=7.8, fontweight="normal")
    ax.set_ylim(0.08, 5 * 10**6)
    ax.grid(axis='y', which='both', linestyle='--', alpha=0.4, zorder=0)
    ax.legend(loc="upper left", frameon=True, edgecolor="#cbd5e1", fontsize=8.0)

    # Table III-style: text directly above bar, small font, arrow down — no overlap
    bar_cx6 = x[5] - width / 2
    ax.annotate('0.33 µs\n(545× faster)',
                xy=(bar_cx6, 0.33),        # arrow tip → top of tiny green bar
                xytext=(bar_cx6 - 0.12, 4.5),  # text: above bar, nudged left
                textcoords='data',
                ha='center', va='bottom',
                fontsize=6.5, fontweight='bold', color='#0f766e',
                arrowprops=dict(arrowstyle='->', color='#0f766e', lw=1.1,
                                shrinkA=2, shrinkB=2))

    plt.title("Data-Plane vs Control-Plane Mitigation Latency Profile (Table IV)",
              fontweight="bold", pad=12)
    plt.tight_layout()

    out_path = os.path.join(OUT_DIR, "fig4_latency_comparison.png")
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"[✓] Fig 4 saved: {out_path}")


# ==============================================================================
# FIG 5: Sovereignty, Privacy & Defense Capability Matrix (Table V)
# ==============================================================================
def generate_fig5_capability_matrix():
    capabilities = [
        "Air-Gapped Offline Operation",
        "Zero Cloud Telemetry Exposure",
        "NIST Post-Quantum Cryptography",
        "Zero Annual Subscription Overhead ($0)",
        "AI-Tarpit Active Deception Engine",
        "HMAC-SHA256 Moving Target Defense"
    ]
    
    systems = ["Snort / Suricata", "Palo Alto / Cisco", "Cloudflare MT", "Autonomous Agent (Ours)"]
    
    # 2 = Native / Sovereign (100%), 1 = Partial / Cloud-Tied (50%), 0 = None (0%)
    matrix = np.array([
        [2, 0, 0, 2],  # Air-Gapped
        [2, 0, 0, 2],  # Zero Cloud Telemetry
        [0, 1, 1, 2],  # PQC
        [2, 0, 0, 2],  # Zero Subscription
        [0, 0, 0, 2],  # AI-Tarpit Deception
        [0, 0, 0, 2]   # MTD Port Hopping
    ])
    
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=300)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    
    # Pure white background for all cells (IEEE monochrome publication style)
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#ffffff"])
    
    cax = ax.imshow(np.zeros_like(matrix), cmap=cmap, aspect="auto", vmin=0, vmax=1)
    
    ax.set_xticks(np.arange(len(systems)))
    ax.set_yticks(np.arange(len(capabilities)))
    ax.set_xticklabels(systems, fontweight="bold", fontsize=8.5, color="#000000")
    ax.set_yticklabels(capabilities, fontweight="normal", fontsize=8.5, color="#000000")
    
    # Text annotations in each cell: high-contrast dark text on pure white
    labels = {0: "None (0%)", 1: "Partial", 2: "Native (100%)"}
    text_colors = {0: "#64748b", 1: "#0f172a", 2: "#000000"}
    font_weights = {0: "normal", 1: "bold", 2: "bold"}
    
    for i in range(len(capabilities)):
        for j in range(len(systems)):
            val = matrix[i, j]
            ax.text(j, i, labels[val], ha="center", va="center",
                    color=text_colors[val], fontsize=8.0, fontweight=font_weights[val])
                    
    # Draw clean grid lines
    ax.set_xticks(np.arange(-.5, len(systems), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(capabilities), 1), minor=True)
    ax.grid(which="minor", color="#94a3b8", linestyle='-', linewidth=0.75)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(which="major", bottom=False, left=False)
    
    # Outer border
    for spine in ax.spines.values():
        spine.set_edgecolor('#475569')
        spine.set_linewidth(0.8)
    
    plt.title("Sovereignty, Privacy & Security Defense Capability Matrix (Table V)", fontweight="bold", fontsize=9.0, pad=10, color="#000000")
    
    out_path = os.path.join(OUT_DIR, "fig5_capability_matrix.png")
    plt.savefig(out_path, facecolor='#ffffff', edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"[✓] Fig 5 saved: {out_path}")


if __name__ == "__main__":
    print("[*] Generating all 5 authentic IEEE publication figures (Fig 1 to Fig 5)...")
    generate_fig1_xdp_pipeline()
    generate_fig2_architecture_comparison()
    generate_fig3_detection_accuracy()
    generate_fig4_latency_comparison()
    generate_fig5_capability_matrix()
    print("[✓] Figures 1 to 5 generated successfully in docs/figures/")
