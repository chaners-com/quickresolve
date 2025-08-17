"""
Parses PDF documents to Markdown.
This parser uses the `pymupdf` library to parse the document.
It is fast but does not handle images, tables,
sections or other complex elements.
"""

from typing import List, Tuple


class FastPDFParser:
    VERSION = "fast-pdf-parser-1.0.0"

    @staticmethod
    async def parse(content: bytes, context: dict) -> Tuple[str, List[dict]]:
        try:
            import fitz  # PyMuPDF
        except Exception as e:
            raise RuntimeError(
                """PyMuPDF (fitz) is required for fast
                PDF parsing but not available."""
            ) from e

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            parts: list[str] = []
            for i, page in enumerate(doc, start=1):
                text = page.get_text()
                parts.append(f"\n\n## Page {i}\n\n{text.strip()}\n")
            doc.close()
            markdown = "".join(parts).strip()
        except Exception as e:
            raise RuntimeError(f"Fast PDF parsing failed: {e}")

        images: List[dict] = []
        return markdown, images
