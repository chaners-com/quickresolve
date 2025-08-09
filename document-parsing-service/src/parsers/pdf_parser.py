"""
Parses PDF documents to Markdown.

This parser uses the `pymupdf` library to parse the document.
"""

import time
from typing import Dict, Tuple
import fitz


def parse(content: bytes) -> Tuple[str, Dict]:
    start = time.time()
    doc = fitz.open(stream=content, filetype="pdf")
    parts: list[str] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        parts.append(f"\n\n## Page {i}\n\n{text.strip()}\n")
    metadata = {
        "page_count": doc.page_count,
        "title": doc.metadata.get("title") if doc.metadata else None,
        "author": doc.metadata.get("author") if doc.metadata else None,
        "processing_ms": int((time.time() - start) * 1000),
    }
    doc.close()
    return ("".join(parts).strip(), metadata) 