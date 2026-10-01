import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Recreate Fig 3 with publication-standard IEEE typography:
# Two subplots:
# (a) Packet Throughput (Mpps)
# (b) Processing Latency (μs) [Log scale]

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 9.0
plt.rcParams['axes.linewidth'] = 0.8

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.2, 2.5), dpi=300)

frameworks = ['iptables', 'Suricata', 'DPDK', 'ASM-Shadhin-AI\n(eBPF/XDP)']
colors = ['#4a90e2', '#f5a623', '#7ed321', '#1b365d']

# (a) Throughput
throughput = [0.28, 0.60, 3.80, 1.49]
bars1 = ax1.bar(frameworks, throughput, color=['#b0c4de', '#f4a460', '#90ee90', '#3b82f6'], edgecolor='black', linewidth=0.8, width=0.55)
ax1.set_ylabel('Throughput (Million Pkts/Sec)', fontsize=8.5, fontweight='bold')
ax1.set_title('(a) Packet Throughput', fontsize=9.0, fontweight='bold', pad=4)
ax1.set_ylim(0, 4.3)
ax1.grid(axis='y', linestyle='--', alpha=0.5)
ax1.tick_params(axis='x', labelsize=7.5)
ax1.tick_params(axis='y', labelsize=8.0)

for bar in bars1:
    y = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2.0, y + 0.1, f'{y:.2f}', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

# (b) Latency (log scale)
latency = [2.40, 24.50, 0.35, 0.12]
bars2 = ax2.bar(frameworks, latency, color=['#b0c4de', '#f4a460', '#90ee90', '#3b82f6'], edgecolor='black', linewidth=0.8, width=0.55)
ax2.set_yscale('log')
ax2.set_ylabel('Drop Latency (μs - Log scale)', fontsize=8.5, fontweight='bold')
ax2.set_title('(b) Processing Latency', fontsize=9.0, fontweight='bold', pad=4)
ax2.set_ylim(0.05, 100)
ax2.grid(axis='y', linestyle='--', alpha=0.5)
ax2.tick_params(axis='x', labelsize=7.5)
ax2.tick_params(axis='y', labelsize=8.0)

for bar in bars2:
    y = bar.get_height()
    txt = f'{y:.2f}μs' if y < 1.0 else f'{y:.1f}μs'
    ax2.text(bar.get_x() + bar.get_width()/2.0, y * 1.25, txt, ha='center', va='bottom', fontsize=7.5, fontweight='bold')

plt.tight_layout()
out_fig = 'testbed/figures/fig3_comparison.png'
plt.savefig(out_fig, bbox_inches='tight')
plt.close()
print(f"✅ Cleanly regenerated {out_fig} without clipped top title!")
