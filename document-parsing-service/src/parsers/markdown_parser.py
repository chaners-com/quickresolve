"""
Pass through for Markdown documents.
Used for documents that are already in Markdown format.
"""

from typing import List, Tuple


class MarkdownParser:
    VERSION = "markdown-parser-1.0.0"

    @staticmethod
    def parse(content: bytes, context: dict) -> Tuple[str, List[dict]]:
        return (content.decode("utf-8", errors="ignore"), [])
