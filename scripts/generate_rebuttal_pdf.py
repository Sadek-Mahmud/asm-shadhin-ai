#!/usr/bin/env python3
"""
generate_rebuttal_pdf.py
Converts the Author Rebuttal DOCX into an IEEE-standard publication-grade PDF
using Chrome headless and reportlab page numbering.
"""

import os
import shutil
import subprocess
import io
import pypdf
from reportlab.pdfgen import canvas
from docx import Document

DOCX_IN   = "/Users/eng.shadhin/Desktop/ASM_Shadhin_AI_Author_Rebuttal_and_Experimental_Proof.docx"
HTML_OUT  = "/tmp/rebuttal_clean.html"
RAW_PDF   = "/tmp/rebuttal_raw.pdf"
FINAL_PDF = "/Users/eng.shadhin/Desktop/ASM_Shadhin_AI_Author_Rebuttal_and_Experimental_Proof.pdf"
CHROME    = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def escape_html(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_html_from_docx():
    doc = Document(DOCX_IN)
    html_lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<style>",
        "@page { size: letter; margin: 20mm 18mm 22mm 18mm; }",
        "body { font-family: 'Times New Roman', Times, serif; font-size: 10pt; line-height: 1.38; color: #111827; text-align: justify; margin: 0; }",
        "h1 { font-family: 'Times New Roman', serif; font-size: 13pt; color: #000000; border-bottom: 1.5px solid #000000; padding-bottom: 2px; margin-top: 18px; margin-bottom: 6px; text-align: left; }",
        "h2 { font-family: 'Times New Roman', serif; font-size: 11pt; color: #000000; margin-top: 12px; margin-bottom: 4px; text-align: left; }",
        "p { margin: 0 0 6px 0; }",
        ".title-block { text-align: center; margin-bottom: 14px; border-bottom: 2px solid #000000; padding-bottom: 10px; }",
        ".main-title { font-size: 16pt; font-weight: bold; color: #000000; margin-bottom: 4px; }",
        ".sub-title { font-size: 10.5pt; font-style: italic; color: #334155; margin-bottom: 6px; }",
        ".meta-line { font-size: 9.5pt; color: #475569; }",
        ".meta-line strong { color: #000000; }",
        ".repo-link { font-size: 10pt; font-weight: bold; color: #000000; margin: 4px 0; }",
        ".callout-box { background: #f8fafc; border-left: 4px solid #b91c1c; padding: 6px 12px; margin: 8px 0; border-radius: 0 4px 4px 0; }",
        ".callout-rev { font-size: 9.5pt; color: #7f1d1d; font-style: italic; margin-bottom: 4px; }",
        ".callout-rev strong { color: #991b1b; font-style: normal; }",
        ".callout-ans { font-size: 9.5pt; color: #14532d; }",
        ".callout-ans strong { color: #166534; }",
        "table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 8.5pt; }",
        "th { background: #111827; color: white; padding: 5px 6px; border: 1px solid #111827; text-align: center; font-weight: bold; }",
        "td { padding: 4px 6px; border: 1px solid #cbd5e1; }",
        "tr:nth-child(even) { background: #f8fafc; }",
        ".highlight-col { background: #f1f5f9 !important; font-weight: bold; }",
        "pre { font-family: 'Courier New', monospace; font-size: 8pt; background: #f1f5f9; border: 1px solid #cbd5e1; padding: 6px 8px; border-radius: 4px; white-space: pre-wrap; word-break: break-all; margin: 6px 0; }",
        "</style></head><body>"
    ]

    # Process paragraphs
    in_title = True
    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue

        if "AUTHOR REBUTTAL & EMPIRICAL PROOF DOSSIER" in txt:
            html_lines.append("<div class='title-block'>")
            html_lines.append(f"<div class='main-title'>{escape_html(txt)}</div>")
            continue
        if "Systematic Point-by-Point Academic Defense" in txt:
            html_lines.append(f"<div class='sub-title'>{escape_html(txt)}</div>")
            continue
        if "Author:" in txt and "Affiliation:" in txt:
            lines = txt.split("\n")
            for l in lines:
                if "https://github.com" in l:
                    html_lines.append(f"<div class='repo-link'>{escape_html(l)}</div>")
                else:
                    html_lines.append(f"<div class='meta-line'>{escape_html(l)}</div>")
            html_lines.append("</div>")
            in_title = False
            continue

        # Check headings
        if any(txt.startswith(prefix) for prefix in ["I. ", "II. ", "III. ", "IV. ", "V. ", "VI. ", "VII. ", "VIII. ", "IX. "]):
            html_lines.append(f"<h1>{escape_html(txt)}</h1>")
            continue
        if any(txt.startswith(prefix) for prefix in ["A. ", "B. ", "C. ", "D. "]):
            html_lines.append(f"<h2>{escape_html(txt)}</h2>")
            continue

        # Check callouts
        if txt.startswith("Reviewer Concern:"):
            rev_txt = txt.replace("Reviewer Concern:", "").strip()
            html_lines.append(f"<div class='callout-box'><div class='callout-rev'><strong>Reviewer Concern:</strong> {escape_html(rev_txt)}</div>")
            continue
        if txt.startswith("Author Response & Empirical Defense:"):
            ans_txt = txt.replace("Author Response & Empirical Defense:", "").strip()
            html_lines.append(f"<div class='callout-ans'><strong>Author Defense:</strong> {escape_html(ans_txt)}</div></div>")
            continue

        # Check code / pre blocks
        if "{" in txt and "}" in txt and ("verdict" in txt or "static __always_inline" in txt or "ALL 9/9" in txt or "Wilson Score" in txt or "$ python3" in txt):
            html_lines.append(f"<pre>{escape_html(txt)}</pre>")
            continue

        # Normal body
        html_lines.append(f"<p>{escape_html(txt)}</p>")

    # Add tables
    # Since tables in docx exist in doc.tables, let's extract them
    # For simplicity, we also inject the HTML tables at relevant points or append them
    html_lines.append("</body></html>")
    return "\n".join(html_lines)

def generate_pdf_via_chrome():
    doc = Document(DOCX_IN)
    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        "<style>",
        "@page { size: letter; margin: 18mm 16mm 20mm 16mm; }",
        "body { font-family: 'Times New Roman', Times, serif; font-size: 9.8pt; line-height: 1.36; color: #111827; text-align: justify; margin: 0; }",
        "h1 { font-family: 'Times New Roman', serif; font-size: 12.5pt; color: #000000; border-bottom: 1.5px solid #000000; padding-bottom: 2px; margin-top: 16px; margin-bottom: 5px; text-align: left; }",
        "h2 { font-family: 'Times New Roman', serif; font-size: 10.5pt; color: #000000; margin-top: 10px; margin-bottom: 3px; text-align: left; }",
        "p { margin: 0 0 5px 0; }",
        ".title-block { text-align: center; margin-bottom: 12px; border-bottom: 2px solid #000000; padding-bottom: 8px; }",
        ".main-title { font-size: 15pt; font-weight: bold; color: #000000; margin-bottom: 3px; }",
        ".sub-title { font-size: 10pt; font-style: italic; color: #334155; margin-bottom: 4px; }",
        ".meta-line { font-size: 9pt; color: #475569; }",
        ".repo-link { font-size: 9.5pt; font-weight: bold; color: #000000; margin: 3px 0; }",
        ".callout-box { background: #f8fafc; border-left: 3.5px solid #b91c1c; padding: 5px 10px; margin: 6px 0; border-radius: 0 3px 3px 0; }",
        ".callout-rev { font-size: 9pt; color: #7f1d1d; font-style: italic; margin-bottom: 3px; }",
        ".callout-rev strong { color: #991b1b; font-style: normal; }",
        ".callout-ans { font-size: 9pt; color: #14532d; }",
        ".callout-ans strong { color: #166534; }",
        "table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8pt; }",
        "th { background: #111827; color: white; padding: 4px 5px; border: 1px solid #111827; text-align: center; font-weight: bold; }",
        "td { padding: 3.5px 5px; border: 1px solid #cbd5e1; }",
        "tr:nth-child(even) { background: #f8fafc; }",
        ".center { text-align: center; }",
        ".highlight { background: #f1f5f9 !important; font-weight: bold; }",
        "pre { font-family: 'Courier New', monospace; font-size: 7.8pt; background: #f1f5f9; border: 1px solid #cbd5e1; padding: 5px 7px; border-radius: 3px; white-space: pre-wrap; word-break: break-all; margin: 5px 0; }",
        "</style></head><body>"
    ]

    # Convert paragraphs and tables in order
    body_elements = []
    for child in doc.element.body:
        tag = child.tag.split('}')[-1]
        if tag == 'p':
            p_text = child.text or ""
            # collect full text from runs
            full_txt = "".join([t.text for t in child.iter() if t.tag.endswith('t') and t.text])
            if full_txt.strip():
                body_elements.append(('p', full_txt.strip()))
        elif tag == 'tbl':
            # Extract table rows
            table_rows = []
            for row in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'):
                row_cells = []
                for cell in row.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                    c_text = "".join([t.text for t in cell.iter() if t.tag.endswith('t') and t.text])
                    row_cells.append(c_text.strip())
                if row_cells:
                    table_rows.append(row_cells)
            if table_rows:
                body_elements.append(('tbl', table_rows))

    in_title = True
    for item_type, data in body_elements:
        if item_type == 'p':
            txt = data
            if "AUTHOR REBUTTAL & EMPIRICAL PROOF DOSSIER" in txt:
                html_parts.append("<div class='title-block'>")
                html_parts.append(f"<div class='main-title'>{escape_html(txt)}</div>")
                continue
            if "Systematic Point-by-Point Academic Defense" in txt:
                html_parts.append(f"<div class='sub-title'>{escape_html(txt)}</div>")
                continue
            if "Author:" in txt and "Affiliation:" in txt:
                for l in txt.split("\n"):
                    if "https://github.com" in l:
                        html_parts.append(f"<div class='repo-link'>{escape_html(l)}</div>")
                    else:
                        html_parts.append(f"<div class='meta-line'>{escape_html(l)}</div>")
                html_parts.append("</div>")
                in_title = False
                continue

            if any(txt.startswith(prefix) for prefix in ["I. ", "II. ", "III. ", "IV. ", "V. ", "VI. ", "VII. ", "VIII. ", "IX. "]):
                html_parts.append(f"<h1>{escape_html(txt)}</h1>")
                continue
            if any(txt.startswith(prefix) for prefix in ["A. ", "B. ", "C. ", "D. "]):
                html_parts.append(f"<h2>{escape_html(txt)}</h2>")
                continue

            if txt.startswith("Reviewer Concern:"):
                rev_txt = txt.replace("Reviewer Concern:", "").strip()
                html_parts.append(f"<div class='callout-box'><div class='callout-rev'><strong>Reviewer Concern:</strong> {escape_html(rev_txt)}</div>")
                continue
            if txt.startswith("Author Response & Empirical Defense:"):
                ans_txt = txt.replace("Author Response & Empirical Defense:", "").strip()
                html_parts.append(f"<div class='callout-ans'><strong>Author Defense:</strong> {escape_html(ans_txt)}</div></div>")
                continue

            if "{" in txt and "}" in txt and ("verdict" in txt or "static __always_inline" in txt or "ALL 9/9" in txt or "Wilson Score" in txt or "$ python3" in txt):
                html_parts.append(f"<pre>{escape_html(txt)}</pre>")
                continue

            html_parts.append(f"<p>{escape_html(txt)}</p>")

        elif item_type == 'tbl':
            rows = data
            if not rows:
                continue
            html_parts.append("<table>")
            # Header
            html_parts.append("<thead><tr>")
            for h in rows[0]:
                html_parts.append(f"<th>{escape_html(h)}</th>")
            html_parts.append("</tr></thead><tbody>")
            # Data rows
            for r_idx, r in enumerate(rows[1:]):
                html_parts.append("<tr>")
                for c_idx, cell in enumerate(r):
                    is_bold = cell.startswith("**")
                    clean = cell.strip("*")
                    css_class = ""
                    if c_idx > 0:
                        css_class += " center"
                    if "A S M Shadhin AI" in rows[0][c_idx] or "**" in cell or c_idx == len(r)-1 and ("State-of-the-Art" in cell or "Wire Speed" in cell or "100% Air-Gapped" in cell):
                        css_class += " highlight"
                    
                    bold_tag = f"<strong>{escape_html(clean)}</strong>" if is_bold else escape_html(clean)
                    html_parts.append(f"<td class='{css_class.strip()}'>{bold_tag}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody></table>")

    html_parts.append("</body></html>")
    
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    # Print to PDF via Chrome headless
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={RAW_PDF}",
        HTML_OUT
    ]
    subprocess.run(cmd, check=True)

    # Stamp bottom-centered IEEE page numbers
    stamp_pdf(RAW_PDF, FINAL_PDF)
    print(f"[OK] Rebuttal PDF built: {FINAL_PDF}")

def stamp_pdf(raw_path, out_path):
    reader = pypdf.PdfReader(raw_path)
    writer = pypdf.PdfWriter()
    total_pages = len(reader.pages)

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(612, 792))
    for page_num in range(1, total_pages + 1):
        c.setFont("Times-Roman", 9)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawCentredString(306, 24, f"— Page {page_num} of {total_pages} —")
        c.showPage()
    c.save()
    packet.seek(0)

    numbering_reader = pypdf.PdfReader(packet)
    for i, page in enumerate(reader.pages):
        page.merge_page(numbering_reader.pages[i])
        writer.add_page(page)

    with open(out_path, "wb") as f:
        writer.write(f)

if __name__ == "__main__":
    import io
    generate_pdf_via_chrome()
    
    # Also sync to workspace
    ws_pdf = "/Volumes/BSc Works/AI digital automated system for security monitoring/ASM_Shadhin_AI_Author_Rebuttal_and_Experimental_Proof.pdf"
    shutil.copy2(FINAL_PDF, ws_pdf)
    print(f"[OK] Copied to Workspace: {ws_pdf}")
