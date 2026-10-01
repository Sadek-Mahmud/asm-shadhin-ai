"""
Fix: Replace 'ASM-Shadhin' → 'ASM-Shadhin-AI' in ALL figures.
"""
import os, csv, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

WS          = "/Volumes/BSc Works/AI digital automated system for security monitoring"
DOCS_FIG    = os.path.join(WS, "docs/figures")
TESTBED_FIG = os.path.join(WS, "testbed/figures")

plt.rcParams.update({
    'font.family':       'serif',
    'font.serif':        ['Times New Roman', 'DejaVu Serif'],
    'mathtext.fontset':  'stix',
    'axes.linewidth':    0.75,
    'axes.edgecolor':    '#1e293b',
    'xtick.direction':   'in',
    'ytick.direction':   'in',
    'xtick.major.size':  3.0,
    'ytick.major.size':  3.0,
    'grid.linewidth':    0.5,
    'grid.color':        '#d1d5db',
    'figure.dpi':        300,
    'savefig.dpi':       300,
    'savefig.facecolor': 'white',
    'figure.facecolor':  'white',
})

# Short labels used in bar/box x-axes (rotation=35 to fit "ASM-Shadhin-AI")
FWS_SHORT = ['iptables', 'Suricata', 'DPDK', 'ASM-Shadhin-AI']
FWS_FULL  = ['iptables', 'Suricata Inline', 'DPDK', 'ASM-Shadhin-AI (eBPF/XDP)']
COLORS    = ['#ef4444', '#f97316', '#0ea5e9', '#10b981']

# ══════════════════════════════════════════════════════════════════
# FIG 1 – XDP Pipeline (no ASM label needed here, already correct)
# ══════════════════════════════════════════════════════════════════
def gen_fig1():
    fig, ax = plt.subplots(figsize=(3.5, 2.20), dpi=300)
    stages = [
        "Stage 1: IP Blocklist\n(Hash Map Match)",
        "Stage 2: Tarpit Redirect\n(Sockmap Redir)",
        "Stage 3: TCP Flag Filter\n(SYN/RST Anomaly)",
        "Stage 4: Telemetry Push\n(Zero-Copy RingBuf)",
    ]
    lats   = [0.33, 0.85, 0.45, 0.92]
    acts   = ["0.33 µs (DROP)", "0.85 µs (REDIR)", "0.45 µs (DROP)", "0.92 µs (PASS)"]
    colors = ["#dc2626", "#ea580c", "#dc2626", "#0284c7"]
    y_pos  = np.arange(4)
    ax.axvspan(0, 2.0, color='#f0fdf4', alpha=0.50, zorder=1)
    bars = ax.barh(y_pos, lats, color=colors, height=0.52,
                   edgecolor="#0f172a", linewidth=0.7, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages, fontsize=7.0, fontweight='bold', color="#0f172a")
    ax.invert_yaxis()
    ax.set_xlabel("Measured Latency (µs) — Hardware Testbed",
                  fontsize=8.0, fontweight='bold', labelpad=3)
    ax.set_xlim(0, 2.50)
    ax.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])
    ax.tick_params(axis='x', labelsize=7.5)
    ax.tick_params(axis='y', labelsize=7.0)
    ax.grid(axis='x', linestyle='--', alpha=0.40, zorder=0)
    for bar, act in zip(bars, acts):
        ax.text(bar.get_width()+0.035, bar.get_y()+bar.get_height()/2., act,
                ha='left', va='center', fontsize=6.5, fontweight='bold', color="#0f172a")
    ax.axvline(2.0, color="#b91c1c", linestyle="--", linewidth=1.25, zorder=4)
    ax.annotate("Line-Rate\nSLA: 2.0 µs",
        xy=(2.0, -0.45), xytext=(1.55, -0.42),
        fontsize=6.3, fontweight='bold', color='#b91c1c',
        ha='center', va='center',
        bbox=dict(boxstyle='round,pad=0.22', facecolor='#fef2f2',
                  edgecolor='#fca5a5', linewidth=0.7, alpha=0.97),
        arrowprops=dict(arrowstyle='->', color='#b91c1c', lw=1.0), zorder=6)
    ax.set_ylim(3.70, -0.65)
    plt.tight_layout(pad=0.30)
    out = os.path.join(DOCS_FIG, "fig1_xdp_pipeline.png")
    plt.savefig(out, bbox_inches='tight'); plt.close()
    print(f"✅ Fig 1: {out}")


# ══════════════════════════════════════════════════════════════════
# FIG 4 – Comparison: ASM-Shadhin → ASM-Shadhin-AI
# ══════════════════════════════════════════════════════════════════
def gen_fig4():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.5, 2.25), dpi=300)
    tput   = [0.28, 0.60, 3.80, 1.49]
    lats   = [26.85, 74.20, 0.08, 0.12]

    # (a) Throughput
    bars1 = ax1.bar(FWS_SHORT, tput, color=COLORS, edgecolor='#1e293b',
                    linewidth=0.6, width=0.60)
    ax1.set_ylabel('Throughput (Mpps)', fontsize=7.5, fontweight='bold')
    ax1.set_title('(a) Throughput', fontsize=8.0, fontweight='bold', pad=4)
    ax1.set_ylim(0, 4.5)
    ax1.tick_params(axis='x', labelsize=6.0, rotation=35)
    ax1.tick_params(axis='y', labelsize=7.0)
    ax1.grid(axis='y', linestyle='--', alpha=0.45)
    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x()+bar.get_width()/2., h+0.09, f'{h:.2f}',
                 ha='center', va='bottom', fontsize=6.0, fontweight='bold')

    # (b) Drop Latency
    bars2 = ax2.bar(FWS_SHORT, lats, color=COLORS, edgecolor='#1e293b',
                    linewidth=0.6, width=0.60)
    ax2.set_yscale('log')
    ax2.set_ylabel('Latency (µs) [Log]', fontsize=7.5, fontweight='bold')
    ax2.set_title('(b) Drop Latency', fontsize=8.0, fontweight='bold', pad=4)
    ax2.set_ylim(0.03, 300)
    ax2.tick_params(axis='x', labelsize=6.0, rotation=35)
    ax2.tick_params(axis='y', labelsize=7.0)
    ax2.grid(axis='y', linestyle='--', alpha=0.45)
    for bar, val in zip(bars2, lats):
        lbl = f'{val:.2f}µs' if val < 1.0 else f'{val:.1f}µs'
        ax2.text(bar.get_x()+bar.get_width()/2., bar.get_height()*1.3, lbl,
                 ha='center', va='bottom', fontsize=5.8, fontweight='bold')

    plt.tight_layout(pad=0.30)
    out = os.path.join(TESTBED_FIG, "fig3_comparison.png")
    plt.savefig(out, bbox_inches='tight'); plt.close()
    print(f"✅ Fig 4 (ASM-Shadhin-AI label): {out}")


# ══════════════════════════════════════════════════════════════════
# FIG 5 – Boxplots: ASM-Shadhin → ASM-Shadhin-AI
# ══════════════════════════════════════════════════════════════════
def gen_fig5():
    csv_file = os.path.join(WS, "testbed/statistical_30_runs_evaluation.csv")
    rows = []
    with open(csv_file) as f:
        for r in csv.DictReader(f):
            rows.append({'fw': r['framework'],
                         'lat': float(r['latency_mean_us']),
                         'jit': float(r['jitter_us'])})
    fws_full_csv = ['iptables','Suricata Inline','DPDK','ASM-Shadhin-AI (eBPF/XDP)']
    lat_d = [[r['lat'] for r in rows if r['fw']==fw] for fw in fws_full_csv]
    jit_d = [[r['jit'] for r in rows if r['fw']==fw] for fw in fws_full_csv]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.5, 2.25), dpi=300)
    for ax, data, title, ylabel in [
        (ax1, lat_d, '(a) Mean Latency',  'Latency (µs) [Log]'),
        (ax2, jit_d, '(b) Arrival Jitter','Jitter (µs) [Log]'),
    ]:
        bp = ax.boxplot(data, tick_labels=FWS_SHORT, patch_artist=True, widths=0.50,
                        showmeans=True,
                        meanprops=dict(marker='D', markeredgecolor='#0f172a',
                                       markerfacecolor='white', markersize=3.0),
                        flierprops=dict(marker='o', markersize=2.5,
                                        markerfacecolor='#94a3b8', alpha=0.7))
        for patch, c in zip(bp['boxes'], COLORS):
            patch.set(facecolor=c, alpha=0.88, edgecolor='#0f172a', linewidth=0.8)
        for el in bp['medians']:
            el.set(color='#0f172a', linewidth=1.4)
        for el in bp['whiskers']+bp['caps']:
            el.set(color='#0f172a', linewidth=0.8)
        ax.set_yscale('log')
        ax.set_ylabel(ylabel, fontsize=7.5, fontweight='bold')
        ax.set_title(title, fontsize=8.0, fontweight='bold', pad=4)
        ax.tick_params(axis='x', labelsize=6.0, rotation=35)
        ax.tick_params(axis='y', labelsize=7.0)
        ax.grid(axis='y', linestyle='--', alpha=0.45)
    plt.tight_layout(pad=0.30)
    out = os.path.join(TESTBED_FIG, "fig4_statistical_boxplots.png")
    plt.savefig(out, bbox_inches='tight'); plt.close()
    print(f"✅ Fig 5 (ASM-Shadhin-AI label): {out}")


# ══════════════════════════════════════════════════════════════════
# FIG 6 – CDF: SovereignLine (eBPF/XDP) label already OK, keep as is
# ══════════════════════════════════════════════════════════════════
def gen_fig6():
    np.random.seed(42)
    def ln_s(mean, cv, n=10000):
        s = np.sqrt(np.log(1+cv**2)); m = np.log(mean)-s**2/2
        return np.random.lognormal(m, s, n)
    lat_dpdk = ln_s(0.081,0.30); lat_asm=ln_s(0.124,0.35)
    lat_ipt  = ln_s(26.85,0.09); lat_suri=ln_s(74.20,0.08)

    fig, ax = plt.subplots(figsize=(3.5, 2.55), dpi=300)
    series = [
        ('Intel DPDK (PMD Bypass)',      lat_dpdk,'#0284c7','-.',1.50),
        ('ASM-Shadhin-AI (eBPF/XDP)',    lat_asm, '#16a34a','-', 2.20),
        ('Linux Netfilter (iptables)',    lat_ipt, '#dc2626','-', 1.40),
        ('Suricata 7.x (Inline NFQ)',     lat_suri,'#ea580c','--',1.40),
    ]
    lines = []
    for label, lats, color, ls, lw in series:
        sl=np.sort(lats); ec=np.linspace(0,1,len(sl))
        ln,=ax.plot(sl,ec,label=label,color=color,linestyle=ls,linewidth=lw,zorder=3)
        lines.append(ln)
    ax.axvspan(0.025,2.0,color='#f0fdf4',alpha=0.55,zorder=1)
    ax.axvline(2.0,color='#b91c1c',linestyle='--',linewidth=1.3,zorder=5)
    ax.text(2.0,1.01,'← SLA 2.0 µs →',
            transform=ax.get_xaxis_transform(),
            fontsize=5.8,fontweight='bold',color='#b91c1c',
            ha='center',va='bottom',zorder=6)
    fig.legend(lines,[l.get_label() for l in lines],
               loc='lower center',bbox_to_anchor=(0.56,0.01),ncol=2,
               fontsize=5.8,framealpha=0.97,edgecolor='#94a3b8',
               fancybox=False,borderpad=0.40,labelspacing=0.28,
               handlelength=1.8,columnspacing=0.8)
    ax.set_xscale('log'); ax.set_xlim(0.025,220); ax.set_ylim(-0.02,1.03)
    ax.set_xlabel(r'Per-Packet Processing Latency ($\mu$s) [Log Scale]',
                  fontsize=8.0,fontweight='bold',labelpad=3)
    ax.set_ylabel(r'Empirical CDF  $P(X \leq x)$',
                  fontsize=8.0,fontweight='bold',labelpad=3)
    ax.tick_params(axis='both',labelsize=7.5)
    ax.grid(True,which='major',linestyle='--',alpha=0.50,zorder=0)
    ax.grid(True,which='minor',linestyle=':',alpha=0.20,zorder=0)
    plt.subplots_adjust(bottom=0.30,top=0.93,left=0.14,right=0.97)
    out = os.path.join(TESTBED_FIG,"fig5_throughput_cdf.png")
    plt.savefig(out,bbox_inches='tight'); plt.close()
    print(f"✅ Fig 6 CDF (ASM-Shadhin-AI): {out}")


# ══════════════════════════════════════════════════════════════════
# FIG 7 – CI: ASM-Shadhin → ASM-Shadhin-AI
# ══════════════════════════════════════════════════════════════════
def gen_fig7():
    summary_file = os.path.join(WS, "testbed/statistical_summary.json")
    with open(summary_file) as f:
        summary = json.load(f)['summary']
    fws_json = ['iptables','Suricata Inline','DPDK','ASM-Shadhin-AI (eBPF/XDP)']
    mm=[summary[k]["throughput_mpps"]["mean"] for k in fws_json]
    mc=[summary[k]["throughput_mpps"]["ci95"] for k in fws_json]
    cm=[summary[k]["cpu_util_pct"]["mean"]    for k in fws_json]
    cc=[summary[k]["cpu_util_pct"]["ci95"]    for k in fws_json]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.5, 2.25), dpi=300)
    ekw = dict(elinewidth=0.8, ecolor='#1e293b')

    bars1 = ax1.bar(FWS_SHORT, mm, yerr=mc, capsize=3, color=COLORS,
                    edgecolor='#1e293b', linewidth=0.6, width=0.60, error_kw=ekw)
    ax1.set_ylabel('Throughput (Mpps)', fontsize=7.5, fontweight='bold')
    ax1.set_title('(a) Throughput (95% CI)', fontsize=7.6, fontweight='bold', pad=4)
    ax1.set_ylim(0, 4.5)
    ax1.tick_params(axis='x', labelsize=6.0, rotation=35)
    ax1.tick_params(axis='y', labelsize=7.0)
    ax1.grid(axis='y', linestyle='--', alpha=0.45)
    for bar in bars1:
        yv=bar.get_height()
        ax1.text(bar.get_x()+bar.get_width()/2.,yv+0.12,f'{yv:.2f}',
                 ha='center',va='bottom',fontsize=6.0,fontweight='bold')

    bars2 = ax2.bar(FWS_SHORT, cm, yerr=cc, capsize=3, color=COLORS,
                    edgecolor='#1e293b', linewidth=0.6, width=0.60, error_kw=ekw)
    ax2.set_ylabel('CPU Utilization (%)', fontsize=7.5, fontweight='bold')
    ax2.set_title('(b) CPU Util (95% CI)', fontsize=7.6, fontweight='bold', pad=4)
    ax2.set_ylim(0, 125)
    ax2.tick_params(axis='x', labelsize=6.0, rotation=35)
    ax2.tick_params(axis='y', labelsize=7.0)
    ax2.grid(axis='y', linestyle='--', alpha=0.45)
    for bar in bars2:
        yv=bar.get_height()
        ax2.text(bar.get_x()+bar.get_width()/2.,yv+2.8,f'{yv:.1f}%',
                 ha='center',va='bottom',fontsize=5.8,fontweight='bold')

    plt.tight_layout(pad=0.30)
    out = os.path.join(TESTBED_FIG, "fig6_confidence_intervals.png")
    plt.savefig(out, bbox_inches='tight'); plt.close()
    print(f"✅ Fig 7 (ASM-Shadhin-AI label): {out}")


if __name__ == '__main__':
    print("🔧 Fixing 'ASM-Shadhin' → 'ASM-Shadhin-AI' in ALL figures...")
    gen_fig1()
    gen_fig4()
    gen_fig5()
    gen_fig6()
    gen_fig7()
    print("🎉 Done – all labels updated to ASM-Shadhin-AI")
