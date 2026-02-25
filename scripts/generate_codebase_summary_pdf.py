"""Generate a one-page PDF from docs/codebase_summary.md without external dependencies."""

from __future__ import annotations

from pathlib import Path
import textwrap

INPUT = Path("docs/codebase_summary.md")
OUTPUT = Path("docs/codebase_summary.pdf")

PAGE_W = 612  # US Letter width (pt)
PAGE_H = 792  # US Letter height (pt)
LEFT = 54
RIGHT = 54
TOP = 54
BOTTOM = 54
BODY_SIZE = 11
H1_SIZE = 16
H2_SIZE = 12
LEADING = 13


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap(line: str, width_chars: int) -> list[str]:
    if not line.strip():
        return [""]
    return textwrap.wrap(line, width=width_chars, break_long_words=False, break_on_hyphens=False)


def to_draw_ops(md_text: str) -> list[tuple[str, int, str]]:
    ops: list[tuple[str, int, str]] = []
    width_chars = 92
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            ops.append(("Helvetica-Bold", H1_SIZE, line[2:].strip()))
            ops.append(("Helvetica", BODY_SIZE, ""))
            continue
        if line.startswith("## "):
            ops.append(("Helvetica-Bold", H2_SIZE, line[3:].strip()))
            continue
        cleaned = line
        if cleaned.startswith("- "):
            cleaned = "• " + cleaned[2:]
        for part in wrap(cleaned, width_chars):
            ops.append(("Helvetica", BODY_SIZE, part))
    return ops


def build_pdf(ops: list[tuple[str, int, str]]) -> bytes:
    y = PAGE_H - TOP
    lines_capacity = int((PAGE_H - TOP - BOTTOM) / LEADING)
    if len(ops) > lines_capacity:
        raise ValueError(
            f"Summary exceeds one page ({len(ops)} lines > {lines_capacity} capacity). Shorten source text."
        )

    content_lines: list[str] = ["BT"]
    for font, size, text in ops:
        y -= LEADING
        content_lines.append(f"/{font} {size} Tf")
        content_lines.append(f"1 0 0 1 {LEFT} {y:.2f} Tm")
        content_lines.append(f"({esc(text)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    page_obj = (
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >> endobj\n"
    ).replace("/Helvetica", "/F1").replace("/Helvetica-Bold", "/F2").encode("ascii")
    objects.append(page_obj)
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n")
    objects.append(
        f"6 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
        + stream
        + b"\nendstream endobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_start = len(pdf)
    count = len(objects) + 1
    pdf.extend(f"xref\n0 {count}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        (
            "trailer << /Size {count} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).format(count=count).encode("ascii")
    )
    return bytes(pdf)


def main() -> None:
    md = INPUT.read_text(encoding="utf-8")
    ops = to_draw_ops(md)
    pdf_bytes = build_pdf(ops)
    OUTPUT.write_bytes(pdf_bytes)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
