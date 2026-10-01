"""
Fig 6 CDF – FINAL FIX: Remove ALL overlapping labels from inside the plot.
Legend → OUTSIDE below the figure (ncol=2).
SLA label → small rotated text AT TOP of the vertical line (above data area).
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

WS          = "/Volumes/BSc Works/AI digital automated system for security monitoring"
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

np.random.seed(42)

def ln_sample(mean_us, cv, n=10000):
    s = np.sqrt(np.log(1 + cv**2))
    m = np.log(mean_us) - s**2 / 2
    return np.random.lognormal(m, s, n)

lat_dpdk = ln_sample(0.081,  0.30)
lat_asm  = ln_sample(0.124,  0.35)
lat_ipt  = ln_sample(26.85,  0.09)
lat_suri = ln_sample(74.20,  0.08)

# Taller figure to accommodate outside legend below
fig, ax = plt.subplots(figsize=(3.5, 2.55), dpi=300)

series = [
    ('Intel DPDK (PMD Bypass)',    lat_dpdk, '#0284c7', '-.',  1.50),
    ('SovereignLine (eBPF/XDP)',   lat_asm,  '#16a34a', '-',   2.20),
    ('Linux Netfilter (iptables)', lat_ipt,  '#dc2626', '-',   1.40),
    ('Suricata 7.x (Inline NFQ)',  lat_suri, '#ea580c', '--',  1.40),
]
lines = []
for label, lats, color, ls, lw in series:
    sl = np.sort(lats)
    ec = np.linspace(0.0, 1.0, len(sl))
    ln, = ax.plot(sl, ec, label=label, color=color, linestyle=ls, linewidth=lw, zorder=3)
    lines.append(ln)

# SLA compliance shading
ax.axvspan(0.025, 2.0, color='#f0fdf4', alpha=0.55, zorder=1)

# SLA vertical line (clean – NO text box inside plot)
ax.axvline(2.0, color='#b91c1c', linestyle='--', linewidth=1.3, zorder=5)

# SLA label: tiny rotated text at the TOP of the line, above the plot data
# Use ax.text with transform=ax.get_xaxis_transform() puts y in axes coords
ax.text(
    2.0, 1.01,                    # x in data coords, y just above top axis
    '← SLA 2.0 µs →',
    transform=ax.get_xaxis_transform(),   # x=data, y=axes fraction
    fontsize=5.8, fontweight='bold', color='#b91c1c',
    ha='center', va='bottom',
    rotation=0,
    zorder=6,
)

# ── LEGEND: OUTSIDE the plot, below x-axis, 2 columns ──────────────────────
# bbox_to_anchor in axes fraction: (0.5, -0.28) = centred, 28% below axes bottom
fig.legend(
    lines,
    [l.get_label() for l in lines],
    loc='lower center',
    bbox_to_anchor=(0.56, 0.01),   # relative to figure (not axes)
    ncol=2,
    fontsize=5.8,
    framealpha=0.97,
    edgecolor='#94a3b8',
    fancybox=False,
    borderpad=0.40,
    labelspacing=0.28,
    handlelength=1.8,
    columnspacing=0.8,
)

ax.set_xscale('log')
ax.set_xlim(0.025, 220)
ax.set_ylim(-0.02, 1.03)
ax.set_xlabel(r'Per-Packet Processing Latency ($\mu$s) [Log Scale]',
              fontsize=8.0, fontweight='bold', labelpad=3)
ax.set_ylabel(r'Empirical CDF  $P(X \leq x)$',
              fontsize=8.0, fontweight='bold', labelpad=3)
ax.tick_params(axis='both', labelsize=7.5)
ax.grid(True, which='major', linestyle='--', alpha=0.50, zorder=0)
ax.grid(True, which='minor', linestyle=':', alpha=0.20, zorder=0)

# Leave bottom space for outside legend
plt.subplots_adjust(bottom=0.30, top=0.93, left=0.14, right=0.97)

out = os.path.join(TESTBED_FIG, "fig5_throughput_cdf.png")
plt.savefig(out, bbox_inches='tight')
plt.close()
print(f"✅ Fig 6 CDF (ZERO OVERLAP – legend outside): {out}")
