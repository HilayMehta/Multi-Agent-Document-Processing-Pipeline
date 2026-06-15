"""Document parsing: docx/pdf -> raw text. Deterministic, no LLM calls."""

from pathlib import Path

import fitz
import re
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


# Indian-currency context markers; the rupee repair runs only when one is present,
# so $/USD documents are never touched.
_INR_CONTEXT_RE = re.compile(r"GSTIN|IFSC|crore|lakh|\bGST\b", re.IGNORECASE)

# A corrupted rupee glyph — ■ or a lone capital I — immediately before a digit
# (optionally with one space, as in the invoice's "I 2,16,000"). The space is consumed.
_RUPEE_GLYPH_RE = re.compile(r"[■I]\s?(?=\d)")


def parse_document(path: str | Path) -> str:
    """Parse a .docx or .pdf file into a single normalized raw text string."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        text = parse_docx(path)
    elif suffix == ".pdf":
        text = parse_pdf(path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix} ({path.name})")
    return _repair_rupee(text)


def parse_docx(path: Path) -> str:
    """Extract paragraphs and tables in document order; tables become markdown."""
    doc = Document(str(path))
    blocks: list[str] = []
    for item in _iter_block_items(doc):
        if isinstance(item, Paragraph):
            if item.text.strip():
                blocks.append(item.text.strip())
        else:
            blocks.append(_table_to_markdown(item))
    return "\n\n".join(blocks)


def parse_pdf(path: Path) -> str:
    """Extract plain text from every page."""
    with fitz.open(str(path)) as doc:
        return "\n".join(page.get_text("text") for page in doc)


def _iter_block_items(doc: DocxDocument):
    """Yield Paragraph and Table objects in the order they appear in the body."""
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def _table_to_markdown(table: Table) -> str:
    """Serialize a docx table as a markdown pipe table so row associations survive."""
    md_rows: list[str] = []
    for row in table.rows:
        cells = [_clean_cell(cell.text) for cell in row.cells]
        md_rows.append("| " + " | ".join(cells) + " |")
        if len(md_rows) == 1:
            md_rows.append("|" + " --- |" * len(cells))
    return "\n".join(md_rows)


def _clean_cell(text: str) -> str:
    """Flatten a cell to one line: newlines become '; ', pipes are escaped."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "; ".join(lines).replace("|", "\\|")


def _repair_rupee(text: str) -> str:
    """Restore ₹ from PDF extraction artifacts (■ / I before a digit).

    Gated on Indian-currency context so dollar-denominated documents are left untouched.
    """
    if not _INR_CONTEXT_RE.search(text):
        return text
    return _RUPEE_GLYPH_RE.sub("₹", text)
