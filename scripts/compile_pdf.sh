#!/usr/bin/env bash
# ============================================================
# compile_pdf.sh — Compile updated LaTeX → ASM_Shadhin_AI_Research_Paper_NEW.pdf
# Run from Terminal: bash scripts/compile_pdf.sh
# ============================================================

set -e

WORKDIR="/Volumes/BSc Works/AI digital automated system for security monitoring"
TEX_MAIN="ASM_Shadhin_AI_Research_Paper_NEW.tex"
PDF_OUT="ASM_Shadhin_AI_Research_Paper_NEW.pdf"

# ── Find pdflatex ────────────────────────────────────────────
PDFLATEX=""
for candidate in \
    /Library/TeX/texbin/pdflatex \
    /usr/local/texlive/2026/bin/universal-darwin/pdflatex \
    /usr/local/texlive/2025/bin/universal-darwin/pdflatex \
    /usr/local/texlive/2024/bin/universal-darwin/pdflatex \
    /usr/texbin/pdflatex \
    $(which pdflatex 2>/dev/null); do
    if [ -x "$candidate" ]; then
        PDFLATEX="$candidate"
        break
    fi
done

if [ -z "$PDFLATEX" ]; then
    echo "❌ pdflatex not found. Please install BasicTeX first:"
    echo "   sudo installer -pkg /opt/homebrew/Caskroom/basictex/2026.0301/mactex-basictex-20260301.pkg -target /"
    echo "   Then run this script again."
    exit 1
fi

echo "✅ Using: $PDFLATEX"
echo "📂 Working directory: $WORKDIR"

cd "$WORKDIR"

# ── Run pdflatex (2 passes for cross-references) ─────────────
echo ""
echo "▶ Pass 1/2..."
"$PDFLATEX" -interaction=nonstopmode "$TEX_MAIN" 2>&1 | grep -E "^(!|Error|Warning)" || true

echo ""
echo "▶ Pass 2/2 (resolving cross-references)..."
"$PDFLATEX" -interaction=nonstopmode "$TEX_MAIN" 2>&1 | grep -E "^(!|Error|Warning)" || true

# ── Also sync the IEEE Access named tex ───────────────────────
cp "$TEX_MAIN" "ASM_Shadhin_AI_IEEE_Access_Research_Paper.tex"

# ── Also copy compiled PDF to IEEE Access named PDF ───────────
if [ -f "ASM_Shadhin_AI_Research_Paper_NEW.pdf" ]; then
    cp "ASM_Shadhin_AI_Research_Paper_NEW.pdf" "ASM_Shadhin_AI_IEEE_Access_Research_Paper.pdf"
    echo ""
    echo "✅ PDF compiled successfully → $PDF_OUT"
    echo "✅ Also saved as  → ASM_Shadhin_AI_IEEE_Access_Research_Paper.pdf"
else
    echo "❌ PDF not generated. Check LaTeX errors above."
    exit 1
fi

# ── Clean up auxiliary files ─────────────────────────────────
rm -f *.aux *.log *.out *.toc *.lof *.lot *.bbl *.blg *.synctex.gz 2>/dev/null
echo "🧹 Auxiliary files cleaned."
echo ""
echo "Done! Open: $WORKDIR/$PDF_OUT"
