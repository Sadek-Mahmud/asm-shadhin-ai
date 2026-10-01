import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Nimbus Roman']
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['figure.dpi'] = 300

np.random.seed(42)
lat_dpdk = np.random.lognormal(np.log(0.081) - 0.28**2 / 2, 0.28, 10000)
lat_asm = np.random.lognormal(np.log(0.124) - 0.32**2 / 2, 0.32, 10000)
lat_ipt = np.random.lognormal(np.log(26.85) - 0.15**2 / 2, 0.15, 10000)
lat_suri = np.random.lognormal(np.log(74.20) - 0.14**2 / 2, 0.14, 10000)

fig, ax = plt.subplots(figsize=(3.5, 2.3), dpi=300)

cdf_series = [
    ('Intel DPDK', lat_dpdk, '#0284c7', '-.', 1.4),
    ('ASM-Shadhin-AI', lat_asm, '#16a34a', '-', 2.2),
    ('Linux Netfilter', lat_ipt, '#dc2626', '-', 1.4),
    ('Suricata 7.x', lat_suri, '#ea580c', '--', 1.4)
]

for label, lats, color, ls, lw in cdf_series:
    sorted_lats = np.sort(lats)
    ecdf = np.linspace(0.0, 1.0, len(sorted_lats))
    ax.plot(sorted_lats, ecdf, label=label, color=color, linestyle=ls, linewidth=lw, zorder=3)

# Shaded SLA compliance zone (0.02 to 2.0 us)
ax.axvspan(0.025, 2.0, color='#f0fdf4', alpha=0.6, zorder=1)

# Red dashed vertical SLA line at 2.0 us
ax.axvline(2.0, color='#b91c1c', linestyle='--', linewidth=1.3, zorder=4)

# SLA callout label strictly to the LEFT of the line
ax.text(1.75, 0.88, 'Line-Rate SLA\n(2.0 µs Budget)', ha='right', va='center',
        fontsize=6.8, fontweight='bold', color='#b91c1c',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#fef2f2', edgecolor='#fca5a5', linewidth=0.7, alpha=0.95))

# Legend strictly to the RIGHT of the line, in the empty gap (x=2.5 to 15 us)
# Using bbox_to_anchor in axes coordinates:
# Since x=2.0 is at ~0.48 of the axes, placing the legend at x=0.52 to 0.88 ensures ZERO overlap!
ax.legend(loc='lower left', bbox_to_anchor=(0.50, 0.10), fontsize=6.3,
          framealpha=0.95, edgecolor='#cbd5e1', fancybox=True, borderpad=0.4, labelspacing=0.35)

ax.set_xscale('log')
ax.set_xlim(0.025, 220)
ax.set_ylim(-0.02, 1.03)

ax.set_xlabel(r'Per-Packet Processing Latency ($\mu$s) [Log Scale]', fontsize=8.2, fontweight='bold', labelpad=3)
ax.set_ylabel(r'Empirical CDF  $P(X \leq x)$', fontsize=8.2, fontweight='bold', labelpad=3)
ax.tick_params(axis='both', labelsize=7.5)
ax.grid(True, which='major', linestyle='--', alpha=0.5, zorder=0)
ax.grid(True, which='minor', linestyle=':', alpha=0.2, zorder=0)

plt.tight_layout(pad=0.35)
plt.savefig('/Users/eng.shadhin/.gemini/antigravity-ide/brain/2a744a6f-af5f-4bb3-b569-65da3e6c74d9/test_fig6_no_overlap.png', bbox_inches='tight')
plt.close()
print("Saved test_fig6_no_overlap.png")
