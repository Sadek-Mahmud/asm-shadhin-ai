#!/usr/bin/env python3
"""
Convert the IEEE Transactions paper to the official IEEE Access template format (ieeeaccess.cls)
and compile to ASM_Shadhin_AI_IEEE_Access_Paper.pdf.
"""
import re
import os
import subprocess

def main():
    tex_path = "ASM_Shadhin_AI_IEEE_Transactions_Research_Paper.tex"
    with open(tex_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace documentclass
    content = re.sub(r'\\documentclass\[journal\]\{IEEEtran\}', r'\\documentclass{ieeeaccess}', content)

    # 2. Remove fancyhdr package and page style configurations
    fancyhdr_block = r'''% Page style: page number top-right, no running header text
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\thepage}
\renewcommand{\headrulewidth}{0pt}
\fancypagestyle{plain}{%
  \fancyhf{}
  \fancyhead[R]{\thepage}
  \renewcommand{\headrulewidth}{0pt}
}'''
    content = content.replace(r'\usepackage{fancyhdr}', '')
    content = content.replace(fancyhdr_block, '')

    # 3. Extract Abstract & Keywords
    abstract_match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', content, re.DOTALL)
    keywords_match = re.search(r'\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}', content, re.DOTALL)

    if not abstract_match or not keywords_match:
        raise ValueError("Could not extract abstract or keywords")

    abstract_text = abstract_match.group(1).strip()
    keywords_text = keywords_match.group(1).strip()

    # 4. Remove old title, author, maketitle, abstract, keywords, IEEEpeerreviewmaketitle
    # Find start of document
    doc_start_idx = content.find(r'\begin{document}')
    # Find start of Introduction
    intro_idx = content.find(r'\section{Introduction}')

    preamble = content[:doc_start_idx].strip()
    body = content[intro_idx:].strip()

    # 5. Build IEEE Access Header block
    access_header = r'''
\history{Date of publication xxxx 00, 0000, date of current version xxxx 00, 0000.}
\doi{10.1109/ACCESS.2026.DOI}

\title{Autonomous Post-Quantum Cyber Defense Agent (ASM-Shadhin-AI): Sovereign Line-Rate Intrusion Defense via Kernel-eBPF and Local-LLM}

\author{\uppercase{A~S~M~Hossain~Mahmud~(Shadhin)}}

\address[1]{Department of Computer Science and Engineering, Bangladesh Army University of Science and Technology (BAUST), Saidpur 5310, Bangladesh (e-mail: shadhin.cse@baust.edu.bd)}

\tfootnote{This research was conducted in the Department of Computer Science and Engineering at Bangladesh Army University of Science and Technology (BAUST), Saidpur, Bangladesh.}

\markboth
{Mahmud: Autonomous Post-Quantum Cyber Defense Agent (ASM-Shadhin-AI)}
{Mahmud: Autonomous Post-Quantum Cyber Defense Agent (ASM-Shadhin-AI)}

\corresp{Corresponding author: A~S~M~Hossain~Mahmud~(Shadhin) (e-mail: shadhin.cse@baust.edu.bd).}
'''

    access_abstract_block = f'''
\\begin{{document}}

\\begin{{abstract}}
{abstract_text}
\\end{{abstract}}

\\begin{{keywords}}
{keywords_text}
\\end{{keywords}}

\\titlepgskip=-15pt

\\maketitle
'''

    # 6. Add XGBoost vs LLM justification to Section V-C
    xgb_justification = r'''
\textit{Architectural Rationale: Edge-LLM vs. Tabular Classifiers:} While classical tree-based models (such as XGBoost or Random Forest) execute in tens of microseconds, they operate strictly on static, pre-engineered scalar features and cannot interpret non-deterministic protocol framing, obfuscated ASN.1 field lengths, or multi-stage natural-language prompt-injection sequences. The 4-bit Edge-LLM serves as a zero-shot cognitive arbiter, synthesizing heterogeneous telemetry into a contextual semantic verdict while the in-kernel fast path guarantees deterministic bounded latency.
'''
    target_str = r'The prompt is submitted to'
    if target_str in body:
        body = body.replace(target_str, xgb_justification + '\n' + target_str)

    # 7. Add \EOD before \end{document}
    if r'\end{document}' in body:
        body = body.replace(r'\end{document}', r'\EOD' + '\n\n' + r'\end{document}')

    # Combine everything
    full_access_tex = preamble + '\n' + access_header + '\n' + access_abstract_block + '\n' + body

    out_file = "ASM_Shadhin_AI_IEEE_Access_Research_Paper.tex"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(full_access_tex)
    print(f"✅ Generated {out_file}")

if __name__ == "__main__":
    main()
