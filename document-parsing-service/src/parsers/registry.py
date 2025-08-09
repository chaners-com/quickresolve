"""
Registry of parsers for different file types.
"""

from . import docx_parser, md_parser, pdf_parser

PARSER_REGISTRY = {
    "pdf": pdf_parser.parse,
    "docx": docx_parser.parse,
    "doc": docx_parser.parse,
    "md": md_parser.parse,
}
