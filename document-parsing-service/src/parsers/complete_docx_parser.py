"""
Docling-backed DOC/DOCX parser
"""

import os
import tempfile
from typing import List, Tuple


class CompleteDOCXParser:
    VERSION = "complete-docx-parser-1"

    @staticmethod
    async def warmup():
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            converter.initialize_pipeline(InputFormat.DOCX)
        except Exception as e:
            print(f"Docx parser Docling warmup failed: {e}")

    @staticmethod
    async def parse(
        content_bytes: bytes, context: dict
    ) -> Tuple[str, List[dict]]:
        try:
            from docling.document_converter import DocumentConverter
        except Exception as e:
            raise RuntimeError(
                "Docling is required for DOCX parsing but not available."
            ) from e

        converter = DocumentConverter()

        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".docx"
            ) as tmp_file:
                tmp_file.write(content_bytes)
                tmp_file_path = tmp_file.name

            result = converter.convert(tmp_file_path)
            markdown: str = (
                getattr(result.document, "markdown", None)
                or getattr(result.document, "export_to_markdown", lambda: "")()
            )
        except Exception as e:
            raise RuntimeError(f"Docling DOCX conversion failed: {e}")
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)

        images_out: List[dict] = []
        try:
            images = getattr(result.document, "images", [])
            for idx, img in enumerate(images, start=1):
                content = img.get("content")
                ext = img.get("ext", "png").lstrip(".")
                alt = img.get("alt") or f"image-{idx}"
                if not content:
                    continue
                images_out.append(
                    {"content": content, "ext": ext, "alt": alt, "index": idx}
                )
        except Exception:
            # Ignore image extraction issues
            # TODO: log this
            pass

        return markdown, images_out
