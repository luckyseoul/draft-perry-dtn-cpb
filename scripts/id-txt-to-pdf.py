#!/usr/bin/env python3
"""Render a paginated xml2rfc .txt as a US-Letter I-D PDF (Courier 10)."""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


# enscript --margins 76::76:  (points)
MARGIN = 76
FONT_SIZE = 10
CHAR_W = 6.0  # Courier 10 = 10/10 * 6 pt
LEADING = 11.5


def register_mono() -> str:
    # Built-in Courier keeps 72-column spacing (same as posted I-D PDFs).
    return "Courier"


def pages_from_txt(text: str) -> list[str]:
    if "\f" in text:
        raw = text.split("\f")
    else:
        raw = [text]
    pages = []
    for chunk in raw:
        chunk = chunk.replace("\r\n", "\n").replace("\r", "\n")
        if chunk.endswith("\n"):
            chunk = chunk[:-1]
        if chunk.strip() == "" and pages:
            continue
        pages.append(chunk)
    return pages or [""]


def render(txt_path: Path, pdf_path: Path) -> None:
    text = txt_path.read_text(encoding="utf-8")
    pages = pages_from_txt(text)
    font = register_mono()
    width, height = letter
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setTitle(txt_path.stem)
    c.setAuthor("Internet-Draft")
    y0 = height - MARGIN - FONT_SIZE

    for page in pages:
        c.setFont(font, FONT_SIZE)
        y = y0
        for line in page.split("\n"):
            # Keep 72-col alignment; don't wrap.
            c.drawString(MARGIN, y, line.replace("\t", "    "))
            y -= LEADING
            if y < 36:
                break
        c.showPage()
    c.save()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: id-txt-to-pdf.py <draft.txt> <out.pdf>", file=sys.stderr)
        return 2
    render(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
