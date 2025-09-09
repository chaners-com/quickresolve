"""
Registry of parsers for different file types.
Each registry entry maps an extension to a Parser class exposing:
    - VERSION: str
    - parse(content_bytes: bytes, context: dict)
         -> Tuple[str, List[dict]] (async staticmethod)
"""

import os
from typing import Optional, Type

from .complete_docx_parser import CompleteDOCXParser
from .complete_pdf_parser import CompletePDFParser
from .fast_docx_parser import FastDOCXParser
from .fast_pdf_parser import FastPDFParser

PARSERS = [
    CompletePDFParser,
    CompleteDOCXParser,
    FastPDFParser,
    FastDOCXParser,
]


async def warmup_parsers():
    pdf_parser_version = _normalize(os.getenv("PDF_PARSER_VERSION", "default"))
    docx_parser_version = _normalize(
        os.getenv("DOCX_PARSER_VERSION", "default")
    )

    for parser in PARSERS:
        if parser.VERSION == pdf_parser_version:
            await parser.warmup()
        if parser.VERSION == docx_parser_version:
            await parser.warmup()


def _normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def get_parser_class(
    extension: Optional[str], content_type: Optional[str]
) -> Optional[Type]:
    """Return the appropriate Parser CLASS
    based on extension, content_type and env.

    Env vars:
      - PDF_PARSER_VERSION:
            "complete" (default), "fast", or a VERSION string
      - DOCX_PARSER_VERSION:
            "complete" (default), "fast", or a VERSION string
    """
    ext = _normalize(extension)
    ctype = _normalize(content_type)

    is_pdf = ext == "pdf" or "application/pdf" in ctype
    is_docx = ext in {"docx", "doc"} or (
        "application/msword" in ctype
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in ctype
    )

    if is_pdf:
        pdf_parser_version = _normalize(
            os.getenv("PDF_PARSER_VERSION", "default")
        )
        for parser in PARSERS:
            if parser.VERSION == pdf_parser_version:
                return parser

    if is_docx:
        docx_parser_version = _normalize(
            os.getenv("DOCX_PARSER_VERSION", "default")
        )
        for parser in PARSERS:
            if parser.VERSION == docx_parser_version:
                return parser

    return None
