"""Quote PDF generation.

Uses a lightweight pure-Python approach: builds a simple PDF directly without
heavy external dependencies. In production you'd typically use ReportLab or
WeasyPrint for richer formatting; for our purposes the goal is to demonstrate
the artifact-generation pattern, not produce print-quality typography.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.domain import Quote, Submission


def generate_quote_pdf(quote: Quote, submission: Submission) -> bytes:
    """Generate a PDF for a quote.

    Returns the PDF as bytes. Uses a minimal pure-Python PDF writer to
    avoid heavyweight dependencies. The output is a single page with the
    quote details, premium, and rationale.
    """
    lines = _build_quote_lines(quote, submission)
    buffer = BytesIO()
    _write_minimal_pdf(buffer, lines)
    return buffer.getvalue()


def _build_quote_lines(quote: Quote, submission: Submission) -> list[str]:
    """Compose the human-readable text of the quote document."""
    return [
        "HELIOS UNDERWRITING - QUOTE DOCUMENT",
        "",
        f"Quote reference: {quote.quote_reference}",
        f"Created: {quote.created_at.strftime('%d %B %Y')}",
        f"Valid until: {quote.valid_until.strftime('%d %B %Y')}",
        "",
        "INSURED",
        f"  Name: {submission.insured_name}",
        f"  Submission reference: {submission.reference}",
        f"  Address: {submission.insured_address.line_1}, {submission.insured_address.city}",
        f"           {submission.insured_address.postcode}",
        "",
        "COVERAGE",
        f"  Type: {quote.coverage.coverage_type.value.replace('_', ' ').title()}",
        f"  Period: {quote.coverage.period.start} to {quote.coverage.period.end}",
        f"  Excess: {quote.excess}",
        "",
        "FLEET",
        f"  Vehicles: {submission.fleet_size}",
        f"  Drivers: {len(submission.drivers)}",
        f"  Total fleet value: {submission.annual_revenue.currency.value} "
        f"{submission.total_fleet_value:,.2f}",
        "",
        "PREMIUM",
        f"  Annual premium: {quote.premium}",
        "",
        "RATIONALE",
        *_wrap_text(quote.rationale, 80),
    ]


def _wrap_text(text: str, width: int) -> list[str]:
    """Wrap a long string into lines no wider than `width` characters."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        if current_len + len(word) + len(current) > width:
            lines.append("  " + " ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word)

    if current:
        lines.append("  " + " ".join(current))

    return lines


def _write_minimal_pdf(buffer: BytesIO, lines: list[str]) -> None:
    """Write a minimal, valid PDF containing the given text lines.

    This produces a tiny, one-page PDF using PDF 1.4 syntax. It's not
    designed to be pretty - it's designed to demonstrate that a real
    binary PDF artifact is produced from the quote data.
    """
    # PDF objects, built in order
    objects: list[bytes] = []

    # 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # 2: Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    # 3: Page (A4, 595x842 pts)
    objects.append(
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 595 842] "
        b"/Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> "
        b">>"
    )

    # 4: Content stream
    content_lines = []
    y = 800
    for line in lines:
        # Escape parens and backslashes
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"BT /F1 11 Tf 50 {y} Td ({escaped}) Tj ET")
        y -= 16
        if y < 50:
            break

    content_stream = "\n".join(content_lines).encode("utf-8")
    content_obj = (
        f"<< /Length {len(content_stream)} >>\nstream\n".encode() + content_stream + b"\nendstream"
    )
    objects.append(content_obj)

    # 5: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Now write the PDF
    buffer.write(b"%PDF-1.4\n")
    offsets: list[int] = []
    for idx, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{idx} 0 obj\n".encode())
        buffer.write(obj)
        buffer.write(b"\nendobj\n")

    xref_pos = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode())
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets:
        buffer.write(f"{offset:010d} 00000 n \n".encode())

    buffer.write(b"trailer\n")
    buffer.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    buffer.write(b"startxref\n")
    buffer.write(f"{xref_pos}\n".encode())
    buffer.write(b"%%EOF")
