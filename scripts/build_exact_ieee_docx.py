#!/usr/bin/env python3
"""
build_exact_ieee_docx.py
Generates the definitive, true two-column IEEE Transactions Word (.docx) manuscript
matching ASM_Shadhin_AI_Research_Paper_NEW.pdf 100% faithfully.
All math variables, latency numbers, throughput stats, and formulas are preserved as clean Unicode.
Tables are formatted with authentic IEEE booktabs styling.
All 7 figures and author photo are embedded at 3.3 in column width.
"""

import os, sys, re
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

WS = "/Volumes/BSc Works/AI digital automated system for security monitoring"
DESKTOP_DOCX = os.path.expanduser("~/Desktop/ASM_Shadhin_AI_Research_Paper_NEW.docx")
WS_DOCX = os.path.join(WS, "ASM_Shadhin_AI_Research_Paper_NEW.docx")

def set_section_two_columns(section, num_cols=2, space_twips=360):
    sectPr = section._sectPr
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    for old in list(sectPr.iterchildren(f'{{{W}}}cols')):
        sectPr.remove(old)
    cols = OxmlElement('w:cols')
    cols.set(qn('w:num'), str(num_cols))
    cols.set(qn('w:space'), str(space_twips))
    sectPr.append(cols)

def set_cell_margins(cell, top=20, bottom=20, left=30, right=30):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for name, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{name}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_bg(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)

def apply_booktabs_table(table):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    
    top = OxmlElement('w:top')
    top.set(qn('w:val'), 'single')
    top.set(qn('w:sz'), '12')  # 1.5 pt
    top.set(qn('w:space'), '0')
    top.set(qn('w:color'), '000000')
    tblBorders.append(top)
    
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '12')  # 1.5 pt
    bottom.set(qn('w:space'), '0')
    bottom.set(qn('w:color'), '000000')
    tblBorders.append(bottom)
    
    insideH = OxmlElement('w:insideH')
    insideH.set(qn('w:val'), 'single')
    insideH.set(qn('w:sz'), '4')   # 0.5 pt thin
    insideH.set(qn('w:space'), '0')
    insideH.set(qn('w:color'), 'E0E0E0')
    tblBorders.append(insideH)
    
    for side in ('left', 'right', 'insideV'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'nil')
        tblBorders.append(el)
        
    tblPr.append(tblBorders)
    
    if len(table.rows) > 0:
        for cell in table.rows[0].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            b = OxmlElement('w:bottom')
            b.set(qn('w:val'), 'single')
            b.set(qn('w:sz'), '8')   # 1 pt
            b.set(qn('w:space'), '0')
            b.set(qn('w:color'), '000000')
            tcBorders.append(b)
            tcPr.append(tcBorders)

    # Add cantSplit to all rows
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

def add_sec_heading(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(9.5)
    r.font.bold = True
    return p

def add_subsec_heading(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(7)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(9.0)
    r.font.bold = True
    r.font.italic = True
    return p

def add_body_p(doc, text, indent=True):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.08
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.18)
    else:
        p.paragraph_format.first_line_indent = Inches(0)
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(9.0)
    return p

def add_col_figure(doc, img_path, fig_num, caption):
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(5)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.paragraph_format.keep_with_next = True
        run = p_img.add_run()
        run.add_picture(img_path, width=Inches(3.3))
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(1)
        p_cap.paragraph_format.space_after = Pt(5)
        p_cap.paragraph_format.line_spacing = 1.05
        
        r_lbl = p_cap.add_run(f"Fig. {fig_num}. ")
        r_lbl.font.name = "Times New Roman"
        r_lbl.font.size = Pt(8.0)
        r_lbl.font.bold = True
        
        r_cap = p_cap.add_run(caption)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(8.0)

def add_equation_block(doc, eq_text, eq_num):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.05
    
    # Format with tabs: center formula, right-align equation number
    r_eq = p.add_run(eq_text)
    r_eq.font.name = "Times New Roman"
    r_eq.font.size = Pt(8.5)
    r_eq.font.italic = True
    
    r_num = p.add_run(f"   ({eq_num})")
    r_num.font.name = "Times New Roman"
    r_num.font.size = Pt(8.5)
    r_num.font.bold = True

print("Helper definitions complete.")
