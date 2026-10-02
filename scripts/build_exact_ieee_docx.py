#!/usr/bin/env python3
"""
build_exact_ieee_docx.py
Generates the definitive, true two-column IEEE Transactions Word (.docx) manuscript
matching ASM_Shadhin_AI_Research_Paper_NEW.pdf 100% faithfully.
Preserves all statistical values (N=30 Welch t-test, df, Cohen's d, CIs),
all 7 tables with IEEE booktabs styling, all figures, equations, references,
and author biography with photo.
"""

import os, sys, shutil, re
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

WS = "/Volumes/BSc Works/AI digital automated system for security monitoring"
OUT_DOCX_WS = os.path.join(WS, "ASM_Shadhin_AI_Research_Paper_NEW.docx")
OUT_DOCX_DESKTOP = os.path.expanduser("~/Desktop/ASM_Shadhin_AI_Research_Paper_NEW.docx")

def build_paper_docx():
    doc = Document()

    # ── Section 0: Title & Abstract (1-Column Full Width) ──
    s0 = doc.sections[0]
    s0.top_margin = Cm(1.78)
    s0.bottom_margin = Cm(1.78)
    s0.left_margin = Cm(1.65)
    s0.right_margin = Cm(1.65)
    s0.page_width = Cm(21.59)
    s0.page_height = Cm(27.94)

    # Set default style font
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(9.5)
    style.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Helpers for 2-column sections
    W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

    def set_section_cols(section, num_cols=2, space_twips=360):
        sectPr = section._sectPr
        for old in list(sectPr.iterchildren(f'{{{W_NS}}}cols')):
            sectPr.remove(old)
        cols = OxmlElement('w:cols')
        if num_cols > 1:
            cols.set(qn('w:num'), str(num_cols))
            cols.set(qn('w:space'), str(space_twips))
        else:
            cols.set(qn('w:num'), '1')
        sectPr.append(cols)

    def add_footer_page_number(section):
        ftr = section.footer
        ftr.is_linked_to_previous = False
        p = ftr.paragraphs[0] if ftr.paragraphs else ftr.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run()
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.0)
        # Add PAGE field XML
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = "PAGE"
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'separate')
        fldChar3 = OxmlElement('w:fldChar')
        fldChar3.set(qn('w:fldCharType'), 'end')
        r._r.append(fldChar1)
        r._r.append(instrText)
        r._r.append(fldChar2)
        r._r.append(fldChar3)

    add_footer_page_number(s0)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(6)
    r_title = p_title.add_run("Autonomous Post-Quantum Cyber Defense Agent (ASM-Shadhin-AI): Sovereign Line-Rate Intrusion Defense via Kernel-eBPF and Local-LLM")
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(20.0)

    # Author
    p_author = doc.add_paragraph()
    p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_author.paragraph_format.space_before = Pt(0)
    p_author.paragraph_format.space_after = Pt(2)
    r_author = p_author.add_run("A S M Hossain Mahmud (Shadhin)")
    r_author.font.name = "Times New Roman"
    r_author.font.size = Pt(11.0)
    r_author.bold = True

    # Affiliation
    p_affil = doc.add_paragraph()
    p_affil.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_affil.paragraph_format.space_before = Pt(0)
    p_affil.paragraph_format.space_after = Pt(12)
    r_affil = p_affil.add_run("Department of Computer Science and Engineering, Bangladesh Army University of Science and Technology (BAUST), Saidpur 5310, Bangladesh\nEmail: eng.shadhin.ai@gmail.com")
    r_affil.font.name = "Times New Roman"
    r_affil.font.size = Pt(9.0)
    r_affil.italic = True

    # Abstract Box / Paragraph
    p_abs = doc.add_paragraph()
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs.paragraph_format.space_before = Pt(0)
    p_abs.paragraph_format.space_after = Pt(4)
    p_abs.paragraph_format.line_spacing = 1.05
    r_abs_lbl = p_abs.add_run("Abstract—")
    r_abs_lbl.bold = True
    r_abs_lbl.italic = True
    r_abs_lbl.font.name = "Times New Roman"
    r_abs_lbl.font.size = Pt(9.0)

    abs_text = (
        "Modern network perimeters face a fundamental trade-off between inspection depth, inline latency, "
        "and operational data sovereignty. Conventional user-space intrusion-prevention systems (e.g., Snort 3.x, "
        "Suricata 7.x) operate via packet-capture interfaces, incurring socket-buffer allocation penalties, "
        "soft-interrupt saturation, and 180–800 µs queuing latencies that cause measurable packet drops under "
        "multi-gigabit loads. Commercial cloud firewalls introduce mandatory telemetry egress and recurring costs "
        "that violate air-gapped sovereignty requirements in critical infrastructure. "
        "This paper presents ASM-Shadhin-AI, an open, fully sovereign, line-rate intrusion-mitigation and "
        "cognitive-defense architecture uniting in-kernel programmable packet processing with local Edge Large "
        "Language Model (Edge-LLM) reasoning. By attaching verified Extended Berkeley Packet Filter (eBPF) bytecode "
        "to the native driver hook of the eXpress Data Path (XDP), ASM-Shadhin-AI executes deterministic filtering, "
        "streaming Shannon entropy analysis, and packet drops before kernel socket-buffer creation, reducing average "
        "lookup latency to approximately 64 ns under the tested testbed workload. Ambiguous threat telemetry is "
        "streamed via zero-copy BPF ring buffers to an asynchronous, air-gapped Edge-LLM (Qwen2.5-Coder-3B Q4_K_M) "
        "governed by strict Context-Free Grammar (CFG) decoding constraints, completely eliminating syntactic hallucinations "
        "and producing deterministic JSON mitigation actions. ASM-Shadhin-AI integrates proactive Moving Target "
        "Defense (MTD) using HMAC-SHA256 port mutation, cryptographically seeded via post-quantum NIST FIPS 203 "
        "(ML-KEM-1024) and authenticated via FIPS 204 (ML-DSA-65). "
        "Under a 10,000,000-packet wire-speed flood on a bare-metal testbed and N = 30 independent benchmark trials, "
        "ASM-Shadhin-AI sustained 1.495 ± 0.015 Mpps (1.18 Gbps) throughput with 0.0000% packet drop (under the tested load) "
        "and 26.2 ± 0.6% mean CPU utilization. Mean per-packet in-kernel processing latency was 0.126 ± 0.007 µs, with an "
        "observed XDP-pipeline stage peak of 0.33 µs. Compared with Linux Netfilter (mean 26.49 ± 1.65 µs), this represents a "
        "5.30× throughput advantage and a ≈210× latency reduction (p < 10^-15, Welch's two-sample t-test, Welch–Satterthwaite "
        "df ≈ 39.1, Cohen's d = 108.2, 95% CI for throughput: [1.489, 1.500] Mpps). DPDK achieves higher raw forwarding throughput "
        "(3.798 Mpps) under the tested single-core configuration but requires 100% dedicated CPU core busy-polling. "
        "In end-to-end subsystem ablation, ASM-Shadhin-AI achieved 98.64% evasion recall. The Edge-LLM daemon was evaluated "
        "separately across 50 labeled threat scenarios, achieving 96.0% overall accuracy (48/50). Over the 40 non-adversarial "
        "classification scenarios (UNSW-NB15 and CSE-CIC-IDS2018 malicious plus benign traffic), precision, recall, and F1-score "
        "were each 0.967. All 10 adversarial context-free grammar (CFG)-stress scenarios produced valid, executable directives, "
        "confirming CFG-constrained decoding robustness under the tested inputs."
    )
    r_abs_txt = p_abs.add_run(abs_text)
    r_abs_txt.font.name = "Times New Roman"
    r_abs_txt.font.size = Pt(9.0)

    # Index Terms
    p_idx = doc.add_paragraph()
    p_idx.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_idx.paragraph_format.space_before = Pt(2)
    p_idx.paragraph_format.space_after = Pt(12)
    p_idx.paragraph_format.line_spacing = 1.05
    r_idx_lbl = p_idx.add_run("Index Terms—")
    r_idx_lbl.bold = True
    r_idx_lbl.italic = True
    r_idx_lbl.font.name = "Times New Roman"
    r_idx_lbl.font.size = Pt(9.0)

    idx_text = (
        "Extended Berkeley Packet Filter (eBPF), eXpress Data Path (XDP), Autonomous Cyber Defense, Edge-LLM, "
        "Context-Free Grammar (CFG), Post-Quantum Cryptography, ML-KEM-1024, ML-DSA-65, Moving Target Defense, "
        "Shannon Entropy, Line-Rate Mitigation, Air-Gapped Security."
    )
    r_idx_txt = p_idx.add_run(idx_text)
    r_idx_txt.font.name = "Times New Roman"
    r_idx_txt.font.size = Pt(9.0)

    # ── Section 1: 2-Column Body Layout ──
    s1 = doc.add_section(WD_SECTION_START.CONTINUOUS)
    s1.top_margin = Cm(1.78)
    s1.bottom_margin = Cm(1.78)
    s1.left_margin = Cm(1.65)
    s1.right_margin = Cm(1.65)
    set_section_cols(s1, 2, space_twips=360)
    add_footer_page_number(s1)

    # Typography & Helper Functions
    def add_sec(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title.upper())
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.5)
        r.bold = True
        return p

    def add_subsec(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title)
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.0)
        r.bold = True
        r.italic = True
        return p

    def add_body(text, indent=True):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.08
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.18)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.0)
        return p

    def add_bullet(label, text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.first_line_indent = Inches(-0.15)
        p.paragraph_format.line_spacing = 1.05
        r_b = p.add_run("•  ")
        r_b.font.name = "Times New Roman"
        r_b.font.size = Pt(9.0)
        r_lbl = p.add_run(label + " ")
        r_lbl.bold = True
        r_lbl.font.name = "Times New Roman"
        r_lbl.font.size = Pt(9.0)
        r_txt = p.add_run(text)
        r_txt.font.name = "Times New Roman"
        r_txt.font.size = Pt(9.0)
        return p

    def add_eq(eq_str, num_str):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.right_indent = Inches(0.1)
        r_eq = p.add_run(eq_str)
        r_eq.italic = True
        r_eq.font.name = "Times New Roman"
        r_eq.font.size = Pt(8.5)
        r_num = p.add_run(f"    ({num_str})")
        r_num.bold = True
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(8.5)
        return p

    def add_fig(img_path, fig_str, caption):
        if os.path.exists(img_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(5)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True
            run = p.add_run()
            run.add_picture(img_path, width=Inches(3.3))
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_cap.paragraph_format.space_before = Pt(1)
            p_cap.paragraph_format.space_after = Pt(5)
            p_cap.paragraph_format.line_spacing = 1.05
            r_num = p_cap.add_run(fig_str + " ")
            r_num.bold = True
            r_num.font.name = "Times New Roman"
            r_num.font.size = Pt(8.0)
            r_cap = p_cap.add_run(caption)
            r_cap.font.name = "Times New Roman"
            r_cap.font.size = Pt(8.0)

    def apply_booktabs(table):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = table._tbl.tblPr
        tblBorders = OxmlElement('w:tblBorders')
        top = OxmlElement('w:top')
        top.set(qn('w:val'), 'single'); top.set(qn('w:sz'), '12'); top.set(qn('w:space'), '0'); top.set(qn('w:color'), '000000')
        tblBorders.append(top)
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single'); bottom.set(qn('w:sz'), '12'); bottom.set(qn('w:space'), '0'); bottom.set(qn('w:color'), '000000')
        tblBorders.append(bottom)
        insideH = OxmlElement('w:insideH')
        insideH.set(qn('w:val'), 'single'); insideH.set(qn('w:sz'), '4'); insideH.set(qn('w:space'), '0'); insideH.set(qn('w:color'), 'E0E0E0')
        tblBorders.append(insideH)
        for s in ('left', 'right', 'insideV'):
            el = OxmlElement(f'w:{s}')
            el.set(qn('w:val'), 'nil')
            tblBorders.append(el)
        tblPr.append(tblBorders)
        
        # Header bottom border
        if len(table.rows) > 0:
            for cell in table.rows[0].cells:
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = OxmlElement('w:tcBorders')
                b = OxmlElement('w:bottom')
                b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '8'); b.set(qn('w:space'), '0'); b.set(qn('w:color'), '000000')
                tcBorders.append(b)
                tcPr.append(tcBorders)
        for row in table.rows:
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

    def add_table_header(table_num_str, title_str):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.keep_with_next = True
        r1 = p.add_run(table_num_str + "\n")
        r1.bold = True
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(8.5)
        r2 = p.add_run(title_str.upper())
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(8.0)

    # ══════════════════════════════════════════════════════════════════════
    # BODY TEXT GENERATION
    # ══════════════════════════════════════════════════════════════════════

    # ── Section I: Introduction ──
    add_sec("I. Introduction")
    add_body(
        "The threat landscape confronting enterprise and critical-infrastructure networks has evolved beyond the "
        "defensive capacities of static, rule-based perimeter appliances. Volumetric denial-of-service (DDoS) campaigns, "
        "polymorphic command-and-control (C2) beaconing, automated port scanning, and multi-stage advanced persistent "
        "threats (APTs) execute with sub-second propagation dynamics. Simultaneously, emerging quantum-computing "
        "capabilities threaten legacy asymmetric cryptographic primitives, necessitating forward-looking post-quantum "
        "cryptographic (PQC) agility against Store Now, Decrypt Later (SNDL) exploitation strategies."
    )
    add_body(
        "Traditional perimeter intrusion-detection and prevention architectures (e.g., Snort 3.x, Suricata 7.x, "
        "Netfilter/iptables) suffer from severe architectural bottlenecks. Kernel-to-user-space buffer transitions, "
        "socket-buffer (sk_buff) allocation overheads, and packet reassembly queues introduce 180–800 µs queuing latencies. "
        "Under multi-gigabit saturating packet floods, the kernel networking stack experiences soft-interrupt (SoftIRQ) "
        "starvation, causing severe packet drops and CPU saturation."
    )
    add_body(
        "Commercial cloud solutions (e.g., Cloudflare Magic Transit, AWS Shield, Palo Alto Networks WildFire) offload "
        "threat intelligence to centralized cloud environments. However, transmitting internal telemetry outside the "
        "network perimeter violates data-sovereignty mandates in defense, aerospace, financial, and air-gapped critical "
        "infrastructure. Local Large Language Model (Edge-LLM) reasoning provides an attractive sovereign alternative, but "
        "unconstrained autoregressive generation produces variable latency, probabilistic hallucinations, and malformed "
        "syntax that can crash network control daemons."
    )

    add_subsec("A. Research Contributions")
    add_body("To address these challenges, we present ASM-Shadhin-AI with five concrete architectural contributions:", indent=False)
    add_bullet("In-Kernel eBPF/XDP Line-Rate Data Plane:",
               "A verified in-kernel packet inspection and mitigation engine running at the native network driver layer via XDP, "
               "eliminating sk_buff allocation and context switches. Operates in O(log N) worst-case time with ≈64 ns average lookup latency.")
    add_bullet("Air-Gapped Edge-LLM with Formal Grammar Constraints:",
               "A decoupled slow-path cognitive triage engine executing locally on an air-gapped host. Guided by strict Context-Free "
               "Grammar (CFG) decoding constraints, ensuring 100% syntactically valid JSON directives with zero parser crashes.")
    add_bullet("Post-Quantum Moving Target Defense (MTD):",
               "A proactive MTD mechanism mutating external service ports across discrete epochs using HMAC-SHA256 keyed permutations. "
               "Key establishment is secured via NIST FIPS 203 (ML-KEM-1024) and authenticated via FIPS 204 (ML-DSA-65), providing IND-CCA2 "
               "primitive security against SNDL adversaries. Measured full-port Nmap SYN scan duration increased from 12.4 s to 4.2 h (1,219× multiplier).")
    add_bullet("Zero-Decryption Streaming Entropy Engine:",
               "An inline streaming Shannon byte-entropy and inter-arrival timing jitter analyzer detecting high-entropy encrypted C2 beaconing "
               "without requiring invasive Man-in-the-Middle TLS decryption.")
    add_bullet("Reproducible Empirical & Statistical Benchmarking:",
               "Under a 10M-packet stress flood and N = 30 independent benchmark runs, ASM-Shadhin-AI achieved 1.495 ± 0.015 Mpps throughput, "
               "0.126 ± 0.007 µs mean latency, 0.0000% packet loss (under the tested load), and 26.2 ± 0.6% CPU utilization. Welch's two-sample "
               "t-test confirmed extreme statistical significance over Netfilter (5.30× throughput, ≈210× latency reduction, t = 419.0, df ≈ 39.1, "
               "d = 108.2 for throughput; t = -87.8, df ≈ 29.0, d = 22.7 for latency; all p < 10^-15).")

    # ── Section II: Related Work & Literature Gap ──
    add_sec("II. Related Work & Literature Gap")
    add_subsec("A. Programmable Data Planes and In-Kernel Packet Processing")
    add_body(
        "Software-defined networking and kernel bypass techniques have advanced packet forwarding. The Intel Data Plane "
        "Development Kit (DPDK) achieves multi-gigabit line-rate processing by moving packet management entirely to user space. "
        "However, DPDK requires dedicated CPU core pinning via busy-polling Poll Mode Drivers (PMD), pegging CPU core utilization to 100% "
        "and breaking native Linux OS integration. Extended Berkeley Packet Filter (eBPF) with the eXpress Data Path (XDP) offers "
        "an optimal middle ground, executing verified bytecode directly inside the network driver before socket buffer allocation."
    )
    add_subsec("B. Machine Learning and Language Models in Network Security")
    add_body(
        "To detect polymorphic threats, research shifted toward ML on network telemetry. Kitsune used autoencoder ensembles, and "
        "Ring et al. surveyed intrusion detection datasets, highlighting common benchmarking deficiencies. Sarhan et al. analyzed "
        "CSE-CIC-IDS2018 and UNSW-NB15, showing that tree-based ensembles perform well on static features. However, conventional ML "
        "models fail to reason about multi-stage adversarial intent. Large language models provide semantic analysis, but inline LLM "
        "inference latency (100–3,000 ms) is incompatible with line-rate per-packet execution."
    )
    add_subsec("C. Post-Quantum Cryptography and Moving Target Defense")
    add_body(
        "Moving Target Defense (MTD) creates asymmetric uncertainty for attackers by dynamically mutating IP addresses, ports, and routes. "
        "However, legacy MTD relies on classical RSA or ECC key exchanges vulnerable to quantum Shor's algorithm attacks. NIST finalized "
        "FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) in August 2024. Prior works evaluated PQC overhead in IoT protocols, but integrating "
        "hardware-accelerated PQC key encapsulation with eBPF-driven port hopping remains unexplored."
    )
    add_subsec("D. Literature Gap Analysis")
    add_body(
        "Table I compares state-of-the-art perimeter defense paradigms against ASM-Shadhin-AI across key performance and architectural metrics."
    )

    # ── Table I: Wide Table spanning both columns ──
    def add_wide_table_1():
        # Start 1-column section
        s_wide = doc.add_section(WD_SECTION_START.CONTINUOUS)
        s_wide.top_margin = Cm(1.78); s_wide.bottom_margin = Cm(1.78)
        s_wide.left_margin = Cm(1.65); s_wide.right_margin = Cm(1.65)
        set_section_cols(s_wide, 1)
        add_footer_page_number(s_wide)

        add_table_header("TABLE I", "Architectural Comparison of State-of-the-Art Perimeter Defense Paradigms")
        t1 = doc.add_table(rows=7, cols=7)
        headers = ["Architecture", "Data-Plane Latency", "Packet Drop", "AI Triage", "Sovereignty", "PQC Protection", "Primary Bottleneck"]
        for j, h in enumerate(headers):
            cell = t1.cell(0, j)
            cell.text = h
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].bold = True
            p.runs[0].font.name = "Times New Roman"
            p.runs[0].font.size = Pt(8.5)

        t1_rows = [
            ["Snort 3.x", "250–800 µs", "> 15%", "Static Rules", "Sovereign", "None", "Kernel-to-user buffer copy; SoftIRQ starvation"],
            ["Suricata 7.x", "180–600 µs", "> 10%", "Heuristic Rules", "Sovereign", "None", "User-space packet reassembly queue"],
            ["Intel DPDK 22.11", "0.08–0.10 µs", "≈ 0%", "External", "Sovereign", "None", "100% dedicated core polling; no OS integration"],
            ["Palo Alto PAN-OS", "25–120 µs", "< 2%", "Cloud WildFire ML", "Telemetry Leaked", "Partial", "Mandatory vendor cloud uplink; license cost"],
            ["Cloudflare Magic Transit", "10–80 ms", "≈ 0%", "Cloud ML", "Telemetry Leaked", "Experimental", "WAN routing latency; disqualified for air-gap"],
            ["ASM-Shadhin-AI (Ours)", "0.126 µs (mean)", "0.00%", "Local Edge-LLM (CFG)", "Sovereign", "FIPS 203/204", "Decoupled fast-path + local AI; LLM on slow path"]
        ]
        for i, row in enumerate(t1_rows):
            for j, val in enumerate(row):
                cell = t1.cell(i+1, j)
                cell.text = val
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j in (1, 2, 4, 5) else WD_ALIGN_PARAGRAPH.LEFT
                p.runs[0].font.name = "Times New Roman"
                p.runs[0].font.size = Pt(8.0)
                if i == 5:
                    p.runs[0].bold = True

        apply_booktabs(t1)

        # Resume 2-column section
        s_two = doc.add_section(WD_SECTION_START.CONTINUOUS)
        s_two.top_margin = Cm(1.78); s_two.bottom_margin = Cm(1.78)
        s_two.left_margin = Cm(1.65); s_two.right_margin = Cm(1.65)
        set_section_cols(s_two, 2, space_twips=360)
        add_footer_page_number(s_two)

    add_wide_table_1()

    # ── Section III: Threat Model & System Assumptions ──
    add_sec("III. Threat Model & System Assumptions")
    add_subsec("A. Adversary Goals and Attack Vectors")
    add_body(
        "We consider an active network-based adversary commanding botnets, automated scanning tools, and sophisticated "
        "polymorphic exploit payloads. Key threat vectors include: (1) Volumetric Saturation Floods (SYN floods, UDP amplification); "
        "(2) Polymorphic C2 Communication using encrypted tunnels and high-entropy beaconing; (3) Adversarial Prompt Injections "
        "targeting LLM triage daemons; (4) Automated Reconnaissance Port Scanning (e.g., Nmap); and (5) Store Now, Decrypt Later (SNDL) "
        "harvesting of key exchanges for future quantum cryptanalysis."
    )
    add_subsec("B. Trust Boundaries and Security Invariants")
    add_bullet("Trusted Computing Base (TCB):", "The Linux kernel, the eBPF verifier, and the physical host hardware. Side-channel and cold-boot hardware attacks are out of scope.")
    add_bullet("Kernel Memory Isolation:", "BPF maps verified by the in-kernel verifier are tamper-proof against unprivileged user-space processes.")
    add_bullet("Endpoint Integrity:", "Gateway host kernels and authorized client operating systems are assumed free of root compromise; system-level guarantees hold within this boundary.")
    add_bullet("Control-Plane Authentication:", "Key announcements and epoch tokens are authenticated using ML-DSA-65 digital signatures, precluding active MITM attacks during key encapsulation.")
    add_bullet("Ephemeral Forward Secrecy:", "Key material (K_epoch and sk) is securely zeroized from volatile memory at each epoch boundary; compromising an active epoch key exposes no past traffic.")

    add_subsec("C. Key Lifecycle and Authentication Protocol")
    add_body(
        "At each epoch boundary (Δt = 30 s default), the MTD controller generates a fresh ML-KEM-1024 key pair (pk, sk) and "
        "broadcasts pk along with an ML-DSA-65 signature over (pk || epoch_counter || nonce). Authorized clients verify the signature, "
        "encapsulate a shared secret K_epoch, and transmit the ciphertext c. The server decapsulates K_epoch, and both parties derive "
        "active service ports via HMAC-SHA256. At epoch expiry, sk and K_epoch are zeroized from RAM."
    )
    add_subsec("D. Formal Security Properties")
    add_bullet("Property 1 (LPM Blocklist Drop Completeness):",
               "For every packet whose source IPv4 matches a CIDR prefix in blocklist_map, the XDP pipeline deterministically returns XDP_DROP before socket-buffer creation.")
    add_bullet("Property 2 (MTD Reconnaissance Resistance):",
               "An adversary scanning the ephemeral port range [10,000, 65,535] has single-probe guessing probability Pr ≈ 1 / 55,536 per epoch under modulo-based HMAC-SHA256 selection.")
    add_bullet("Property 3 (Post-Quantum Key Encapsulation and Forward Secrecy):",
               "ML-KEM-1024 provides IND-CCA2 security under the MLWE hardness assumption. Complete system forward secrecy holds in combination with ML-DSA-65 authentication and per-epoch key zeroization.")

    # ── Section IV: System Architecture & Mathematical Foundations ──
    add_sec("IV. System Architecture & Mathematical Foundations")
    add_subsec("A. Kernel-Space Fast Data Plane (eBPF/XDP)")
    add_body(
        "ASM-Shadhin-AI decouples line-rate packet mitigation from asynchronous cognitive triage. The fast path executes "
        "entirely within the network driver RX ring buffer via XDP. When a frame arrives, the eBPF program parses Ethernet, "
        "IPv4, and transport headers, checks the BPF LPM trie blocklist, updates flow statistics, evaluates streaming Shannon entropy, "
        "and handles MTD port translation. Malicious frames are dropped instantly via XDP_DROP within ≈64 ns."
    )

    # Wide Architecture Figure 1
    def add_wide_fig_1():
        s_wide = doc.add_section(WD_SECTION_START.CONTINUOUS)
        s_wide.top_margin = Cm(1.78); s_wide.bottom_margin = Cm(1.78)
        s_wide.left_margin = Cm(1.65); s_wide.right_margin = Cm(1.65)
        set_section_cols(s_wide, 1)
        add_footer_page_number(s_wide)

        if os.path.exists("docs/figures/fig1_xdp_pipeline.png"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run()
            run.add_picture("docs/figures/fig1_xdp_pipeline.png", width=Inches(6.8))

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_cap.paragraph_format.space_before = Pt(2)
            p_cap.paragraph_format.space_after = Pt(6)
            r1 = p_cap.add_run("Fig. 1.  ")
            r1.bold = True
            r1.font.name = "Times New Roman"
            r1.font.size = Pt(8.5)
            r2 = p_cap.add_run("High-level dual-plane system architecture of ASM-Shadhin-AI, showing the in-kernel eBPF/XDP fast data plane (driver layer, sub-microsecond line-rate enforcement) decoupled from the asynchronous user-space Edge-LLM cognitive triage daemon via lockless BPF ring buffers.")
            r2.font.name = "Times New Roman"
            r2.font.size = Pt(8.0)

        s_two = doc.add_section(WD_SECTION_START.CONTINUOUS)
        s_two.top_margin = Cm(1.78); s_two.bottom_margin = Cm(1.78)
        s_two.left_margin = Cm(1.65); s_two.right_margin = Cm(1.65)
        set_section_cols(s_two, 2, space_twips=360)
        add_footer_page_number(s_two)

    add_wide_fig_1()

    add_subsec("B. Mathematical Latency & Queuing Model")
    add_body("We model in-kernel packet processing latency as:")
    add_eq("T_process = t_DMA + t_hook + t_lpm_lookup + t_action", "1")
    add_body("where t_hook ≈ 25 ns, t_lpm_lookup ≈ 64 ns, and t_action ∈ {XDP_DROP, XDP_PASS}. Under saturating arrival rate λ, drop probability follows an M/M/1/K queue:")
    add_eq("P_drop = ((1 - ρ) * ρ^K) / (1 - ρ^(K+1)),  where ρ = λ / µ", "2")
    add_body("For Netfilter, µ ≈ 280 kpps, leading to severe packet drops when λ > 1 Mpps. In contrast, ASM-Shadhin-AI achieves µ_XDP ≈ 1.495 Mpps, maintaining ρ < 1.0 with zero loss.")

    add_subsec("C. Post-Quantum Moving Target Defense")
    add_body("Active service ports mutate across discrete epochs τ according to:")
    add_eq("P(s, τ) = P_min + [ HMAC-SHA256(K_epoch, s || τ) mod (P_max - P_min + 1) ]", "3")
    add_body("where [P_min, P_max] = [10,000, 65,535] (55,536 positions in the ephemeral range). Modulo reduction introduces negligible bias (< 10^-72), ensuring uniform port selection.")

    add_subsec("D. Streaming Shannon Entropy Estimation")
    add_body("Shannon byte entropy H(W_k) over sliding payload windows of N = 1024 bytes is computed inline without TLS decryption:")
    add_eq("H(W_k) = - ∑ ( p(b_i) * log2(p(b_i)) )", "4")
    add_body("Inter-arrival timing jitter J_k is monitored concurrently to detect automated periodic beaconing:")
    add_eq("J_k = ( (1 / (M - 1)) ∑ |Δt_(j+1) - Δt_j| ) / Δt_mean", "5")

    add_subsec("E. Asynchronous Edge-LLM Reasoning with Formal Grammars")
    add_body(
        "Ambiguous flows exceeding the entropy threshold (H ≥ 7.85 bits/byte, J ≤ 0.10) trigger a zero-copy ring-buffer event "
        "to the Edge-LLM daemon. The daemon samples tokens under a strict Context-Free Grammar (CFG) enforcing JSON schema compliance: "
        "{ 'verdict': V, 'action': A, 'confidence': C }. This guarantees 100% executable directives with zero syntax crashes."
    )

    # ── Section V: Implementation Details ──
    add_sec("V. Implementation Details")
    add_subsec("A. eBPF Program Architecture and Map Design")
    add_body(
        "The kernel-space data plane is implemented in 847 lines of C (Clang/LLVM 18, -O2 -target bpf) passing the Linux eBPF "
        "verifier with 0 warnings. BPF maps include: (1) blocklist_map (LPM trie, up to 65,536 CIDR entries, 64.2 ± 3.1 ns lookup); "
        "(2) tarpit_ips_map (Hash map mapping quarantined IPs to tarpit markers); (3) flow_entropy_map (LRU hash tracking 5-tuple state); "
        "and (4) telemetry_ring (4 MB lockless ring buffer for zero-copy export)."
    )
    add_subsec("B. Edge-LLM Daemon Integration")
    add_body(
        "The user-space daemon (1,243 lines of Python 3.11) uses llama-cpp-python v0.2.56 with AVX2 SIMD acceleration. The static "
        "4-bit quantized Qwen2.5-Coder-3B Q4_K_M model executes in an isolated Unix process with greedy decoding (temperature T = 0), "
        "producing decisions in 1.88–2.92 seconds."
    )

    # ── Section VI: Empirical Evaluation & Results ──
    add_sec("VI. Empirical Evaluation & Results")
    add_subsec("A. Physical Testbed and Experimental Setup")
    add_body(
        "Benchmarks executed on a dedicated bare-metal host (Intel Core i5-4570 @ 3.20 GHz, 16 GB DDR3-1600 RAM, Intel 82574L Gigabit NIC, "
        "Ubuntu Server 22.04 LTS, Linux kernel 6.8.0-49-generic). Traffic generated via tcpreplay 4.4.2 at wire-speed topspeed across 30 independent runs."
    )

    # Table V: Hardware Specifications
    add_table_header("TABLE V", "Hardware Specifications of Evaluation Testbed")
    t5 = doc.add_table(rows=7, cols=3)
    t5_headers = ["Subsystem Component", "Physical Specification", "Operational Role"]
    for j, h in enumerate(t5_headers):
        cell = t5.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.5)
    t5_rows = [
        ["Processor (CPU)", "Intel Core i5-4570 @ 3.20 GHz (4 Cores, 4 Threads)", "Dedicated core 0 for XDP, cores 1–3 for LLM daemon"],
        ["System Memory", "16 GB DDR3-1600 MHz Dual-Channel RAM", "eBPF maps, Ring buffer, and Q4_K_M model weights (1.92 GB)"],
        ["Network Adapter", "Intel 82574L PCIe Gigabit NIC (e1000e driver)", "Wire-speed 1.0 Gbps physical data plane"],
        ["Operating System", "Ubuntu Server 22.04 LTS (Linux kernel 6.8.0)", "Host OS with eBPF native driver XDP hook"],
        ["LLM Inference Engine", "llama-cpp-python v0.2.56 (AVX2 SIMD accelerated)", "Local air-gapped cognitive triage daemon"],
        ["Traffic Generator", "tcpreplay v4.4.2 (top-speed wire replay)", "High-rate 10,000,000-packet PCAP stress flood"]
    ]
    for i, r in enumerate(t5_rows):
        for j, val in enumerate(r):
            cell = t5.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j == 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
    apply_booktabs(t5)

    add_subsec("B. 10M-Packet Stress Benchmark Results")
    add_body(
        "Table II reports operational telemetry during the 10,000,000-packet stress flood. ASM-Shadhin-AI processed all 10M packets "
        "with 0.0000% packet loss, achieving a peak rate of 1.49 Mpps (1,179 Mbps) and a 30-run mean latency of 0.126 µs with peak CPU of 26.2%."
    )

    # Table II: Telemetry Under 10M Flood
    add_table_header("TABLE II", "Empirical Telemetry Under 10,000,000-Packet Wire-Speed Stress Flood")
    t2 = doc.add_table(rows=11, cols=3)
    t2_headers = ["Operational Telemetry Metric", "Empirical Measurement", "Validation Criterion"]
    for j, h in enumerate(t2_headers):
        cell = t2.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.5)
    t2_rows = [
        ["Total Packets Ingested", "10,000,000 pkts", "PASS (100%)"],
        ["Wire Bytes Processed", "989.47 MB", "PASS (> 500 MB)"],
        ["Peak Packet Rate", "1,490,200 pps", "PASS (1.49 Mpps)"],
        ["Sustained Bandwidth", "1,179.04 Mbps", "PASS (1.18 Gbps)"],
        ["30-Run Mean Processing Latency", "0.126 µs (126 ns)", "PASS (Sub-µs)"],
        ["Observed Stage-Peak Latency", "0.33 µs (330 ns)", "PASS (Sub-µs)"],
        ["Peak CPU Utilization", "26.2%", "PASS (< 80%)"],
        ["Packet Drop Ratio", "0.0000%", "ZERO LOSS (100% Ingested)"],
        ["Memory Footprint (RSS)", "18.4 MB", "PASS (< 256 MB)"],
        ["eBPF JIT Compilation", "Native x86-64", "PASS (Verified)"]
    ]
    for i, r in enumerate(t2_rows):
        for j, val in enumerate(r):
            cell = t2.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
            if i == 7: p.runs[0].bold = True
    apply_booktabs(t2)

    # Figures 2 & 3
    add_fig("testbed/figures/fig1_throughput.png", "Fig. 2.", "Real-time packet ingestion rate (Mpps) and bandwidth (Gbps) under 10M-packet stress flood (1.495 ± 0.015 Mpps, 1.18 Gbps).")
    add_fig("testbed/figures/fig2_cpu_utilization.png", "Fig. 3.", "CPU core 0 utilization (%) during 10M-packet saturation run. Peak utilization remained bounded at 26.2 ± 0.6%.")

    add_subsec("C. Multi-Run Statistical Rigor (N = 30 Independent Trials)")
    add_body(
        "We conducted N = 30 independent benchmark runs comparing ASM-Shadhin-AI against Linux Netfilter (iptables 1.8.7), "
        "Suricata 7.0.2 inline IPS (NFQUEUE), and Intel DPDK 22.11 LTS. Normality was confirmed by Shapiro-Wilk tests (p > 0.05). "
        "Levene's test confirmed significant heteroscedasticity (W = 16.26, p < 10^-3 for throughput; W = 49.66, p < 10^-8 for latency), "
        "mathematically mandating Welch's unequal-variance t-test rather than Student's t-test. With Bonferroni correction (α_adj = 0.010), "
        "all reported differences satisfy p < 10^-15."
    )

    # Table III: Comparative Benchmark
    add_table_header("TABLE III", "Comparative Benchmark Across N = 30 Independent Trials (Mean ± s.d.)")
    t3 = doc.add_table(rows=5, cols=5)
    t3_headers = ["Architecture", "Throughput (Mpps)", "Latency (µs)", "Jitter (µs)", "CPU (%)"]
    for j, h in enumerate(t3_headers):
        cell = t3.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.5)
    t3_rows = [
        ["Netfilter (iptables 1.8.7)", "0.282 ± 0.006", "26.49 ± 1.65", "7.20 ± 0.75", "89.4 ± 2.4"],
        ["Suricata 7.0.2 (NFQUEUE)", "0.596 ± 0.010", "74.47 ± 2.61", "14.03 ± 1.19", "99.0 ± 0.7"],
        ["Intel DPDK 22.11", "3.798 ± 0.011", "0.081 ± 0.002", "0.024 ± 0.001", "100.0 ± 0.0"],
        ["ASM-Shadhin-AI (Ours)", "1.495 ± 0.015", "0.126 ± 0.007", "0.042 ± 0.003", "26.2 ± 0.6"]
    ]
    for i, r in enumerate(t3_rows):
        for j, val in enumerate(r):
            cell = t3.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
            if i == 3: p.runs[0].bold = True
    apply_booktabs(t3)

    # Table IV: Welch's t-test
    add_table_header("TABLE IV", "Welch's Two-Sample t-Test and Effect Size Metrics (N = 30 Independent Trials)")
    t4 = doc.add_table(rows=6, cols=7)
    t4_headers = ["Comparison Pair", "Mean Diff.", "95% CI of Diff.", "t-Stat.", "df", "p-Value", "Cohen's d"]
    for j, h in enumerate(t4_headers):
        cell = t4.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
    t4_rows = [
        ["Throughput: ASM vs Netfilter", "+1.213 Mpps", "[+1.207, +1.218]", "419.0", "39.1", "< 10^-15", "108.2"],
        ["Throughput: ASM vs Suricata", "+0.898 Mpps", "[+0.892, +0.905]", "283.0", "49.7", "< 10^-15", "73.1"],
        ["Latency: ASM vs Netfilter", "-26.37 µs", "[-26.98, -25.75]", "-87.8", "29.0", "< 10^-15", "22.7"],
        ["Latency: ASM vs Suricata", "-74.34 µs", "[-75.32, -73.37]", "-155.8", "29.0", "< 10^-15", "40.2"],
        ["CPU Util: ASM vs Suricata", "-72.71%", "[-73.04, -72.38]", "-438.6", "55.5", "< 10^-15", "113.3"]
    ]
    for i, r in enumerate(t4_rows):
        for j, val in enumerate(r):
            cell = t4.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
    apply_booktabs(t4)

    # Figures 4, 5, 6, 7
    add_fig("testbed/figures/fig3_comparison.png", "Fig. 4.", "Architectural performance comparison across four systems on identical hardware (Intel i5-4570, N = 30 trials, mean ± s.d.).")
    add_fig("testbed/figures/fig4_statistical_boxplots.png", "Fig. 5.", "Boxplots of per-packet processing latency (µs, log scale) across N = 30 independent benchmark trials.")
    add_fig("testbed/figures/fig5_throughput_cdf.png", "Fig. 6.", "Empirical cumulative distribution function (CDF) of per-packet processing latency (µs) pooled across N = 30 independent trials.")
    add_fig("testbed/figures/fig6_confidence_intervals.png", "Fig. 7.", "95% confidence intervals for mean throughput (Mpps) and CPU utilization (%) across N = 30 independent runs.")

    add_subsec("D. Edge-LLM Semantic Triage Evaluation")
    add_body(
        "We evaluated the Edge-LLM across 50 labeled scenarios. Because no model fine-tuning was performed on this static 4-bit "
        "quantized model (Qwen2.5-Coder-3B Q4_K_M), the dataset was partitioned into a development/calibration subset (35 scenarios, 70%) "
        "and a held-out evaluation subset (15 scenarios, 30%). To ensure rigorous interpretation, evaluation is reported across three separate tiers:"
    )
    add_bullet("50-Scenario Overall Task Evaluation:", "Measures comprehensive directive generation across all inputs, achieving 48/50 = 96.0% overall accuracy.")
    add_bullet("40-Scenario Confusion-Matrix Analysis:", "Restricted strictly to binary threat classification (15 UNSW-NB15 + 15 CIC-IDS2018 + 10 benign). Achieved TP=29, TN=9, FP=1, FN=1, precision = 0.967, recall = 0.967, and F1 = 0.967. This 96.7% triage recall is distinct from the 98.64% system-level evasion recall in Section VII.")
    add_bullet("10-Scenario Adversarial CFG-Stress Evaluation:", "Tested grammar constraints against prompt injections and jailbreak strings. All 10 inputs (100%) produced strictly valid JSON with zero crashes.")

    # Table VI: Edge-LLM Evaluation
    add_table_header("TABLE VI", "Edge-LLM Triage Evaluation Across 50 Labeled Scenarios")
    t6 = doc.add_table(rows=7, cols=6)
    t6_headers = ["Evaluation Tier / Category", "Scenarios", "Correct", "Precision", "Recall", "F1-Score"]
    for j, h in enumerate(t6_headers):
        cell = t6.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.5)
    t6_rows = [
        ["Malicious (UNSW-NB15)", "15", "14", "1.000", "0.933", "0.966"],
        ["Malicious (CIC-IDS2018)", "15", "15", "1.000", "1.000", "1.000"],
        ["Benign (Normal traffic)", "10", "9", "0.900", "0.900", "0.900"],
        ["Subtotal: Classification (40)", "40", "38", "0.967", "0.967", "0.967"],
        ["Adversarial (CFG stress)", "10", "10", "1.000", "1.000", "1.000"],
        ["Total: Overall Evaluation (50)", "50", "48", "0.967", "0.967", "0.967"]
    ]
    for i, r in enumerate(t6_rows):
        for j, val in enumerate(r):
            cell = t6.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
            if i in (3, 5): p.runs[0].bold = True
    apply_booktabs(t6)

    add_subsec("E. Entropy/Jitter Detector Evaluation")
    add_body(
        "Thresholds H(W_k) ≥ 7.85 bits/byte and J_k ≤ 0.10 were selected via ROC-curve analysis on 200 labeled flows: "
        "AUC-ROC = 0.893 (95% CI: [0.843, 0.943]), Recall = 87.9%, FPR = 8.1%, Precision = 91.5%, and F1 = 0.896."
    )

    # ── Section VII: Ablation Study & Sensitivity Analysis ──
    add_sec("VII. Ablation Study & Sensitivity Analysis")
    add_subsec("A. Subsystem Ablation Analysis")
    add_body(
        "Table VII quantifies the contribution of each subsystem under identical flood traffic. Evasion Recall (Column 2) "
        "is the end-to-end multi-vector mitigation recall across the full pipeline (98.64% in Config A). In Configuration C "
        "(Without MTD Engine), overall evasion recall against general attacks is 91.20% (0.18% FPR, 1.49 Mpps, 0.00% packet loss); "
        "however, under dedicated reconnaissance probing, scan resistance falls from 96.8% to 54.2% due to fixed port exposure. "
        "This resolves the operational distinction between multi-vector evasion recall (91.20%) and scan resistance (54.2%)."
    )

    # Table VII: Ablation Matrix
    add_table_header("TABLE VII", "System Subsystem Ablation Matrix")
    t7 = doc.add_table(rows=5, cols=5)
    t7_headers = ["Configuration", "Evasion Recall", "FPR", "Throughput", "Packet Loss"]
    for j, h in enumerate(t7_headers):
        cell = t7.cell(0, j); cell.text = h
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold = True; p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.5)
    t7_rows = [
        ["A: Full ASM-Shadhin-AI", "98.64%", "0.12%", "1.49 Mpps", "0.00%"],
        ["B: eBPF Fast-Path Only", "73.10%", "0.45%", "1.51 Mpps", "0.00%"],
        ["C: Without MTD Engine", "91.20%", "0.18%", "1.49 Mpps", "0.00%"],
        ["D: User-Space Fallback", "82.40%", "3.80%", "0.31 Mpps", "19.40%"]
    ]
    for i, r in enumerate(t7_rows):
        for j, val in enumerate(r):
            cell = t7.cell(i+1, j); cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.runs[0].font.name = "Times New Roman"; p.runs[0].font.size = Pt(8.0)
            if i == 0: p.runs[0].bold = True
    apply_booktabs(t7)

    add_subsec("B. Post-Quantum Handshake Overhead")
    add_body(
        "ML-KEM-1024 encapsulation required 48.2 µs and decapsulation required 59.4 µs, compared to 38.1 µs for X25519. "
        "The marginal 11–21 µs overhead occurs only during epoch initialization (every 30 s) and introduces zero inline latency."
    )

    # ── Section VIII: Defensive Deception & Tarpit Dynamics ──
    add_sec("VIII. Defensive Deception & Tarpit Dynamics")
    add_subsec("A. Reconnaissance Scan-Duration Analysis and 1,219× Derivation")
    add_body(
        "In empirical Nmap testing (-sS -p 1-65535 --max-retries 2), scanning a baseline host required T_base = 12.4 s. Against "
        "the tarpit-augmented MTD host, the scan extended to T_MTD = 4.2 h (15,120 s), yielding a 1,219× measured scan-duration "
        "multiplier. The MTD engine specifically shifts services across the ephemeral port range [10,000, 65,535] (55,536 positions) "
        "with an approximate single-probe guessing probability of 1/55,536 under modulo selection."
    )
    add_subsec("B. Adversarial Resource Exhaustion Analysis")
    add_body(
        "A single gateway thread holds up to 65,535 simultaneous connections at win 0 state using only 1.2 MB of kernel memory "
        "and < 0.1% single-core CPU, exhausting remote scanning sockets while preserving gateway availability."
    )

    # ── Section IX: Limitations & Future Work ──
    add_sec("IX. Limitations & Future Work")
    add_bullet("IPv6 Extension Headers:", "Current eBPF parsing focuses on IPv4. Extending the verifier-compliant parser to arbitrary IPv6 header chains is underway.")
    add_bullet("Hardware SmartNIC Offload:", "Offloading bytecode into SmartNICs (e.g., Netronome Agilio or NVIDIA BlueField) will unlock 40–100 Gbps line rates.")
    add_bullet("Evaluation Scale & Drift:", "The 50-scenario dataset limits generalizability. Future work will incorporate online privacy-preserving QLoRA adapters.")

    # ── Section X: Ethics, Responsible Disclosure, and Reproducibility ──
    add_sec("X. Ethics, Responsible Disclosure, and Reproducibility")
    add_body(
        "Evaluations were conducted on a physically isolated air-gapped testbed. Datasets (UNSW-NB15, CSE-CIC-IDS2018) are publicly available. "
        "The framework is released under the MIT License with complete C eBPF source, Python daemon, raw measurement CSVs, and statistical notebooks."
    )

    # ── Section XI: Conclusion ──
    add_sec("XI. Conclusion")
    add_body(
        "This paper presented ASM-Shadhin-AI, an open, fully sovereign, line-rate intrusion-mitigation and cognitive-defense architecture. "
        "The eBPF/XDP data plane sustained 1.495 ± 0.015 Mpps with 0.0000% packet loss under the tested load, 0.126 ± 0.007 µs mean latency, "
        "and 26.2 ± 0.6% CPU utilization. Across N = 30 independent trials using Welch's two-sample t-test (Welch–Satterthwaite df ≈ 39.1, "
        "t = 419.0, d = 108.2 for throughput; df ≈ 29.0, t = -87.8, d = 22.7 for latency; both p < 10^-15 << α_adj = 0.010), ASM-Shadhin-AI's "
        "5.30× throughput advantage and ≈210× latency reduction over Netfilter were statistically significant under the tested experimental conditions. "
        "The air-gapped Edge-LLM achieved 96.0% overall accuracy with 100% grammar adherence. In aggregate, the results demonstrate that deterministic "
        "line-rate defense, sovereign intelligence, and post-quantum cryptographic agility can coexist on commodity x86-64 hardware."
    )

    # ── Acknowledgment ──
    p_ack = doc.add_paragraph()
    p_ack.paragraph_format.space_before = Pt(8); p_ack.paragraph_format.space_after = Pt(2)
    p_ack.paragraph_format.keep_with_next = True
    r_ack_h = p_ack.add_run("ACKNOWLEDGMENT\n")
    r_ack_h.bold = True; r_ack_h.font.name = "Times New Roman"; r_ack_h.font.size = Pt(9.0)
    r_ack_t = p_ack.add_run("The author expresses sincere appreciation to the Department of Computer Science and Engineering at Bangladesh Army University of Science and Technology (BAUST) for providing laboratory resources and testbed computing facilities.")
    r_ack_t.font.name = "Times New Roman"; r_ack_t.font.size = Pt(8.5)

    # ── References ──
    p_ref_h = doc.add_paragraph()
    p_ref_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ref_h.paragraph_format.space_before = Pt(10); p_ref_h.paragraph_format.space_after = Pt(4)
    p_ref_h.paragraph_format.keep_with_next = True
    r_ref = p_ref_h.add_run("REFERENCES")
    r_ref.bold = True; r_ref.font.name = "Times New Roman"; r_ref.font.size = Pt(9.5)

    references_list = [
        "[1] M. Sarhan, S. Layeghifard, N. Moustafa, and M. Gallagher, “Towards a standard feature set for network intrusion detection datasets,” IEEE Trans. Inf. Forensics Security, vol. 17, pp. 367–381, 2022.",
        "[2] Y. Mirsky, T. Doitshman, Y. Elovici, and A. Shabtai, “Kitsune: An ensemble of autoencoders for online network intrusion detection,” in Proc. 25th NDSS Symp., 2018, pp. 1–15.",
        "[3] M. Roesch, “Snort: Lightweight intrusion detection for networks,” in Proc. 13th USENIX LISA Conf., 1999, pp. 229–238.",
        "[4] V. Paxson, “Bro: A system for detecting network intruders in real-time,” Comput. Netw., vol. 31, no. 23–24, pp. 2435–2463, 1999.",
        "[5] S. Miano, M. Bertrone, F. Risso, M. Tumolo, and M. Bernal, “Creating complex network services with eBPF: Experience and lessons learned,” in Proc. IEEE HPCC, 2018, pp. 1–8.",
        "[6] T. Høiland-Jørgensen et al., “The eXpress data path: Fast programmable packet processing in the operating system kernel,” in Proc. 14th ACM CoNEXT, 2018, pp. 54–66.",
        "[7] S. Miano, R. Doriguzzi-Corin, F. Risso, D. Siracusa, and R. Sompalle, “Introducing SmartNIC support in BEBA,” in Proc. IEEE NetSoft, 2018, pp. 1–9.",
        "[8] M. Ring et al., “A survey of network-based intrusion detection data sets,” Comput. Secur., vol. 86, pp. 147–167, 2019.",
        "[9] T. Dettmers, A. Pagnoni, A. Holtzman, and L. Zettlemoyer, “QLoRA: Efficient finetuning of quantized LLMs,” in Proc. NeurIPS, vol. 36, 2023, pp. 10088–10115.",
        "[10] National Institute of Standards and Technology, “Module-Lattice-Based Key-Encapsulation Mechanism Standard,” FIPS PUB 203, Aug. 2024.",
        "[11] National Institute of Standards and Technology, “Module-Lattice-Based Digital Signature Standard,” FIPS PUB 204, Aug. 2024.",
        "[12] S. Jajodia et al., Eds., Moving Target Defense: Creating Asymmetric Uncertainty for Cyber Threats. New York: Springer, 2011.",
        "[13] Open Information Security Foundation, “Suricata User Guide Release 7.0.2,” Tech. Rep., 2024. [Online]. Available: https://suricata.io",
        "[14] I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward generating a new intrusion detection dataset and intrusion traffic characterization,” in Proc. ICISSP, 2018, pp. 108–116.",
        "[15] N. Moustafa and J. Slay, “UNSW-NB15: A comprehensive data set for network intrusion detection systems,” in Proc. IEEE MilCIS, 2015, pp. 1–6.",
        "[16] S. Garcia, M. Grill, J. Stiborek, and P. Zunino, “An empirical comparison of botnet detection methods,” Comput. Secur., vol. 45, pp. 100–123, 2014.",
        "[17] B. Anderson and D. McGrew, “Identifying encrypted malware traffic with contextual flow data,” in Proc. ACM IH&MMSec, 2016, pp. 35–46.",
        "[18] G. Bertoli, L. Verderame, and A. Merlo, “eBPF for cyber security: A comprehensive survey,” IEEE Access, vol. 11, pp. 75892–75916, 2023.",
        "[19] Q. Zhao, J. Chen, and D. Guan, “GRAPHIDS: A network anomaly intrusion detection system based on graph neural network,” IEEE Trans. Netw. Service Manag., vol. 20, no. 4, pp. 4215–4228, 2023.",
        "[20] E. Alkim, L. Ducas, T. Pöppelmann, and P. Schwabe, “Post-quantum key exchange—a new hope,” in Proc. 25th USENIX Security Symp., 2016, pp. 327–343.",
        "[21] M. Atighetchi, P. Pal, F. Webber, and C. Jones, “Adaptive use of network-centric mechanisms in cyber-defense,” in Proc. IEEE ISORC, 2003, pp. 183–192.",
        "[22] P. Sharma and R. Arora, “Evaluating post-quantum cryptographic primitives in lightweight network protocols,” IEEE Internet Things J., vol. 10, no. 18, pp. 16201–16212, 2023.",
        "[23] M. A. S. Vieira et al., “Fast packet processing with eBPF and XDP: Security on the edge,” IEEE Commun. Surv. Tuts., vol. 22, no. 4, pp. 2526–2544, 2020.",
        "[24] J. Zheng, A. Chowdhury, and D. Guan, “Moving target defense for network security: A survey,” IEEE Commun. Surv. Tuts., vol. 24, no. 3, pp. 1800–1835, 2022.",
        "[25] D. J. Bernstein and T. Lange, “Post-quantum cryptography,” Nature, vol. 549, pp. 188–194, 2017.",
        "[26] P. Bosshart et al., “P4: Programming protocol-independent packet processors,” ACM SIGCOMM CCR, vol. 44, no. 3, pp. 87–95, 2014.",
        "[27] H. Touvron et al., “Llama 2: Open foundation and fine-tuned chat models,” arXiv preprint arXiv:2307.09288, 2023.",
        "[28] Qwen Team, Alibaba Cloud, “Qwen2.5-Coder Technical Report,” arXiv preprint arXiv:2409.12186, 2024.",
        "[29] G. Gerganov et al., “llama.cpp: Inference of LLaMA model in pure C/C++,” [Online]. Available: https://github.com/ggerganov/llama.cpp, 2024.",
        "[30] T. Turner et al., “Tcpreplay: Pcap editing and replay tools,” [Online]. Available: https://tcpreplay.appneta.com, 2024."
    ]

    for ref in references_list:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(8.0)

    # ── Author Biography with Photo ──
    if os.path.exists("docs/ref_photo.jpg"):
        p_bio_gap = doc.add_paragraph()
        p_bio_gap.paragraph_format.space_before = Pt(8); p_bio_gap.paragraph_format.space_after = Pt(2)
        
        t_bio = doc.add_table(rows=1, cols=2)
        t_bio.alignment = WD_TABLE_ALIGNMENT.CENTER
        # Remove borders
        tblPr = t_bio._tbl.tblPr
        tblBorders = OxmlElement('w:tblBorders')
        for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{s}')
            el.set(qn('w:val'), 'nil')
            tblBorders.append(el)
        tblPr.append(tblBorders)

        cell_pic = t_bio.cell(0, 0)
        cell_pic.width = Inches(1.1)
        p_p = cell_pic.paragraphs[0]
        p_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_pic = p_p.add_run()
        r_pic.add_picture("docs/ref_photo.jpg", width=Inches(1.0))

        cell_txt = t_bio.cell(0, 1)
        cell_txt.width = Inches(2.2)
        p_b = cell_txt.paragraphs[0]
        p_b.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_b.paragraph_format.line_spacing = 1.05
        r_bname = p_b.add_run("A S M Hossain Mahmud (Shadhin) ")
        r_bname.bold = True
        r_bname.font.name = "Times New Roman"
        r_bname.font.size = Pt(8.5)
        bio_body = (
            "is a full-time undergraduate student pursuing the B.Sc. degree in Computer Science and Engineering "
            "at Bangladesh Army University of Science and Technology (BAUST), Saidpur, Bangladesh. "
            "His research focuses on kernel-space high-throughput packet processing using eBPF/XDP, post-quantum "
            "cryptographic implementations (NIST FIPS 203 ML-KEM-1024 and FIPS 204 ML-DSA-65), sovereign local artificial "
            "intelligence architectures for automated threat reasoning, proactive moving target defense (HMAC-SHA256 port hopping), "
            "and active cyber deception. He is the lead architect and developer of the open-source ASM-Shadhin-AI framework."
        )
        r_btxt = p_b.add_run(bio_body)
        r_btxt.font.name = "Times New Roman"
        r_btxt.font.size = Pt(8.0)

    # Save to workspace & Desktop
    doc.save(OUT_DOCX_WS)
    shutil.copyfile(OUT_DOCX_WS, OUT_DOCX_DESKTOP)
    print(f"[SUCCESS] Built: {OUT_DOCX_WS} ({os.path.getsize(OUT_DOCX_WS)} bytes)")
    print(f"[SUCCESS] Copied to Desktop: {OUT_DOCX_DESKTOP} ({os.path.getsize(OUT_DOCX_DESKTOP)} bytes)")

if __name__ == "__main__":
    build_paper_docx()
