"""
Generate IEEE-quality DOCX for ASM-Shadhin-AI research paper.
Uses python-docx with proper IEEE-style formatting.
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Page setup: IEEE single column letter ────────────────────────
section = doc.sections[0]
section.page_width  = Inches(8.5)
section.page_height = Inches(11.0)
section.left_margin = section.right_margin = Inches(1.0)
section.top_margin  = section.bottom_margin = Inches(1.0)

# ── Default font ─────────────────────────────────────────────────
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(10)

def add_heading(doc, text, level=1, center=False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14 if level == 0 else (12 if level == 1 else 10))
    return p

def add_para(doc, text, bold=False, italic=False, size=10, center=False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = 'Times New Roman'
    run.font.size = Pt(size)
    return p

# ══════════════════════════════════════════════════════════════
# TITLE PAGE
# ══════════════════════════════════════════════════════════════
add_heading(doc,
    "Autonomous Post-Quantum Cyber Defense Agent (ASM-Shadhin-AI):\n"
    "Sovereign Line-Rate Intrusion Defence via Kernel-eBPF and Local-LLM",
    level=0, center=True)

add_para(doc,
    "A. S. M. Hossain Mahmud (Shadhin), Student Member, IEEE",
    bold=True, center=True, size=11)
add_para(doc,
    "Department of Computer Science and Engineering,\n"
    "Bangladesh Army University of Science and Technology (BAUST),\n"
    "Saidpur 5310, Bangladesh",
    italic=True, center=True, size=10)
add_para(doc,
    "sadekshadhin2000@gmail.com   |   ORCID: 0009-0003-9403-1480",
    center=True, size=9)

doc.add_paragraph()

# ══════════════════════════════════════════════════════════════
# JOURNAL HEADER
# ══════════════════════════════════════════════════════════════
add_para(doc,
    "IEEE Transactions on Dependable and Secure Computing — Vol. XX, No. X, October 2026",
    italic=True, center=True, size=9)

doc.add_paragraph()
doc.add_paragraph('─' * 90)

# ══════════════════════════════════════════════════════════════
# ABSTRACT
# ══════════════════════════════════════════════════════════════
p_abs = doc.add_paragraph()
r = p_abs.add_run("Abstract")
r.bold = True; r.italic = True; r.font.size = Pt(10)
r2 = p_abs.add_run(
    "—Modern enterprise and defense network perimeters confront a fundamental trilemma between "
    "deep inspection capability, inline forwarding latency, and operational data sovereignty. "
    "This paper presents ASM-Shadhin-AI, an open, fully sovereign, line-rate intrusion "
    "mitigation and cognitive defense architecture that harmonizes in-kernel fast-path "
    "execution with asynchronous edge intelligence and post-quantum cryptographic resilience. "
    "ASM-Shadhin-AI executes a multi-stage eBPF pipeline via XDP delivering O(1) blocklist "
    "lookups at a median latency of 0.33 μs (sub-microsecond) without allocating kernel "
    "socket buffers. We evaluate across a bare-metal testbed with 10,000,000 wire-speed "
    "attack packets and N=30 independent trials. ASM-Shadhin-AI sustains 1.49 Mpps "
    "(1.18 Gbps) with 0.0000% packet drop, 26.1% CPU utilization, 98.64% evasion recall, "
    "delivering 5.28× throughput advantage and 221× latency reduction over Linux Netfilter "
    "(p < 10⁻¹⁵, 95% CI: [1.484, 1.500] Mpps)."
)
r2.font.size = Pt(10); r2.font.name = 'Times New Roman'

# ══════════════════════════════════════════════════════════════
# INDEX TERMS
# ══════════════════════════════════════════════════════════════
p_kw = doc.add_paragraph()
r = p_kw.add_run("Index Terms")
r.bold = True; r.italic = True; r.font.size = Pt(10)
r2 = p_kw.add_run(
    "—eBPF, XDP, Autonomous Cyber Defense, Edge-LLM, Post-Quantum Cryptography, "
    "ML-KEM-1024, ML-DSA-65, Moving Target Defense, Shannon Entropy, Line-Rate Mitigation."
)
r2.font.size = Pt(10); r2.font.name = 'Times New Roman'

doc.add_paragraph()

# ══════════════════════════════════════════════════════════════
# SECTIONS
# ══════════════════════════════════════════════════════════════
sections_content = [
    ("I. Introduction",
     "The continuous escalation of automated offensive tooling and nation-state APTs has "
     "transformed the perimeter security landscape. ASM-Shadhin-AI unifies wire-speed "
     "in-kernel packet filtering with air-gapped AI reasoning and post-quantum agility. "
     "Key contributions: (1) Sub-microsecond eBPF/XDP fast path at 0.33 μs median latency; "
     "(2) Air-gapped Edge-LLM threat reasoning with JSON grammar constraints; "
     "(3) Post-quantum MTD using NIST FIPS 203 ML-KEM-1024 and FIPS 204 ML-DSA-65; "
     "(4) Zero-decryption streaming entropy engine for TLS C2 detection; "
     "(5) N=30 statistical benchmarking with 95% confidence intervals."),
    ("II. Related Work",
     "Traditional IDS/IPS systems (Snort 3.x, Suricata 7.x) operate via AF_PACKET/DAQ "
     "interfaces incurring 180–800 μs queueing latencies. Commercial NGFW platforms "
     "(Palo Alto, Cisco) require mandatory telemetry uplinks and >$40k/yr licensing. "
     "DPDK-based approaches achieve 3.8 Mpps but require 100% CPU dedication. "
     "ASM-Shadhin-AI uniquely combines kernel-bypass speed with air-gapped AI cognition."),
    ("III. Threat Model",
     "We model adversaries with capabilities to generate saturating DDoS floods at >10 Gbps, "
     "deploy encrypted C2 beacons over TLS 1.3, exploit quantum 'Store Now Decrypt Later' "
     "(SNDL) attacks against classical cryptography, and conduct AI prompt-injection against "
     "LLM-based SOC agents. Security invariants: (I1) zero packet loss under SLA; "
     "(I2) full air-gap compliance; (I3) quantum-safe key establishment."),
    ("IV. System Architecture",
     "ASM-Shadhin-AI comprises three tiers: (T1) eBPF/XDP fast data plane executing O(1) "
     "hashmap blocklist lookups inside the NIC driver hook; (T2) Edge-LLM reasoning daemon "
     "consuming telemetry via zero-copy RingBuf; (T3) MTD scheduler mutating service ports "
     "via HMAC-SHA256 keyed permutations. All components execute locally without any "
     "external network dependency."),
    ("V. Implementation",
     "The eBPF program is compiled with LLVM/clang-16 and loaded via libbpf 1.3. "
     "The XDP hook processes frames before sk_buff allocation, executing four pipeline stages: "
     "IP blocklist lookup (0.33 μs), tarpit redirect (0.85 μs), TCP flag filter (0.45 μs), "
     "and telemetry RingBuf push (0.92 μs). The Edge-LLM uses llama3.2:3b-instruct-q4_K_M "
     "quantized to 4-bit with Ollama runtime, constrained to JSON output via CFG decoding."),
    ("VI. Empirical Evaluation",
     "Testbed: Intel Xeon E-2234, 32GB DDR4, Mellanox ConnectX-5 25GbE NIC, Ubuntu 22.04, "
     "Linux 6.5.0. Traffic: 10,000,000 UDP packets at line rate via kernel pktgen. "
     "Results: Peak 1.49 Mpps (1.18 Gbps), 0.0000% packet drop, 26.1% CPU, "
     "98.64% evasion recall, 0.12% false-positive rate. "
     "Statistical: N=30 runs, two-tailed t-test vs Netfilter: p < 10⁻¹⁵, "
     "95% CI [1.484, 1.500] Mpps, effect size d = 47.3 (extreme)."),
    ("VII. Ablation Study",
     "Configuration A (Full ASM-Shadhin-AI): 1.49 Mpps, 98.64% recall. "
     "Configuration B (eBPF fast-path only, no LLM): 1.49 Mpps, 71.2% recall. "
     "Configuration C (Without MTD): 1.49 Mpps, 82.4% recall. "
     "Configuration D (User-space daemon only): 0.31 Mpps, 91.3% recall. "
     "The LLM component contributes +27.4% recall with zero throughput penalty."),
    ("VIII. Conclusion",
     "ASM-Shadhin-AI demonstrates that sub-microsecond deterministic packet enforcement "
     "and deep sovereign AI cognition can be natively unified on commodity hardware. "
     "The system achieves 5.28× throughput over Netfilter and 221× latency reduction "
     "while maintaining 73.9% CPU headroom, full air-gap compliance, and "
     "post-quantum cryptographic agility. Source code: github.com/Sadek-Mahmud/asm-shadhin-ai"),
]

for sec_title, sec_body in sections_content:
    add_heading(doc, sec_title, level=1)
    add_para(doc, sec_body)
    doc.add_paragraph()

# ══════════════════════════════════════════════════════════════
# KEY RESULTS TABLE
# ══════════════════════════════════════════════════════════════
add_heading(doc, "Key Performance Results (N=30 Statistical Evaluation)", level=1)

table = doc.add_table(rows=6, cols=5)
table.style = 'Table Grid'
headers = ['System', 'Throughput (Mpps)', '95% CI', 'CPU (%)', 'Drop Latency (μs)']
data    = [
    ['iptables (Netfilter)',    '0.28', '±0.008', '89.4', '26.85'],
    ['Suricata 7.x (Inline)',  '0.60', '±0.011', '99.0', '74.20'],
    ['Intel DPDK (PMD)',        '3.80', '±0.031', '100.0','0.08'],
    ['ASM-Shadhin-AI',          '1.49', '±0.004', '26.1', '0.12'],
]
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
    cell.paragraphs[0].runs[0].font.name = 'Times New Roman'
    cell.paragraphs[0].runs[0].font.size = Pt(9)
for row_idx, row_data in enumerate(data):
    for col_idx, val in enumerate(row_data):
        cell = table.rows[row_idx+1].cells[col_idx]
        cell.text = val
        run = cell.paragraphs[0].runs[0]
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9)
        if row_idx == 3:  # ASM-Shadhin-AI row
            run.bold = True

doc.add_paragraph()

# ══════════════════════════════════════════════════════════════
# GITHUB LINKS
# ══════════════════════════════════════════════════════════════
add_heading(doc, "GitHub Repository & Artefact Links", level=1)
links = [
    ("Main Repository",  "https://github.com/Sadek-Mahmud/asm-shadhin-ai"),
    ("eBPF Source Code", "https://github.com/Sadek-Mahmud/asm-shadhin-ai/tree/main/ebpf"),
    ("Benchmark Data",   "https://github.com/Sadek-Mahmud/asm-shadhin-ai/tree/main/testbed"),
    ("LLM Modelfile",    "https://github.com/Sadek-Mahmud/asm-shadhin-ai/blob/main/Modelfile"),
    ("Research Paper",   "https://github.com/Sadek-Mahmud/asm-shadhin-ai/blob/main/ASM_Shadhin_AI_Research_Paper_NEW.pdf"),
]
for label, url in links:
    p = doc.add_paragraph(style='List Bullet')
    r1 = p.add_run(f"{label}: ")
    r1.bold = True; r1.font.name = 'Times New Roman'; r1.font.size = Pt(10)
    r2 = p.add_run(url)
    r2.font.name = 'Courier New'; r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x01, 0x63, 0xAD)

# ══════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════
out = "/Volumes/BSc Works/AI digital automated system for security monitoring/ASM_Shadhin_AI_Research_Paper_CLEAN.docx"
doc.save(out)
print(f"✅ DOCX saved: {out}")