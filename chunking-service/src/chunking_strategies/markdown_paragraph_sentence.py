"""
Chunker

Chunks by markdown sections > paragraphs > sentences > tokens.
"""

import hashlib
import os
import re
import time
from typing import List, Tuple, Optional, Dict
from uuid import uuid4

from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    NLTKTextSplitter,
    RecursiveCharacterTextSplitter,
    SpacyTextSplitter,
    TokenTextSplitter,
)

from .base import Chunk, ChunkingStrategy

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP_TOKENS = int(
    os.getenv("CHUNK_OVERLAP_TOKENS", str(int(CHUNK_SIZE * 0.15)))
)
CHUNK_CHAR_MAX = int(os.getenv("CHUNK_CHAR_MAX", "4000"))

# Chunking strategy constants
STRATEGY_NAME = os.getenv(
    "CHUNKING_STRATEGY_NAME", "markdown+paragraph+sentence"
)
STRATEGY_VERSION = os.getenv("CHUNKING_STRATEGY_VERSION", "multistrategy-1")
STRATEGY_TOOL_NAME = os.getenv(
    "CHUNKING_STRATEGY_TOOL_NAME", "chunking-strategy"
)
STRATEGY_TOOL_VERSION = os.getenv(
    "CHUNKING_STRATEGY_TOOL_VERSION", "markdown_paragraph_sentence-1.0"
)


def _normalize_text(text: str) -> str:
    return re.sub(r"\r\n?|\u2028|\u2029", "\n", text).strip()


def _estimate_tokens_len(text: str) -> int:
    return max(1, int(len(text) / 4))


def _sha256_of_content(text: str) -> str:
    normalized = _normalize_text(text)
    h = hashlib.sha256(normalized.encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


def _normalize_headers(headers: List) -> List[str]:
    titles: List[str] = []
    for h in headers:
        if isinstance(h, (list, tuple)):
            if len(h) >= 2:
                titles.append(str(h[1]))
            elif len(h) == 1:
                titles.append(str(h[0]))
        elif isinstance(h, dict):
            titles.append(
                str(h.get("title") or h.get("name") or h.get("text") or "")
            )
        else:
            titles.append(str(h))
    return [t for t in titles if t]


def _split_headings(markdown_text: str) -> List[Tuple[str, List[str]]]:
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
    )
    docs = splitter.split_text(markdown_text)
    sections: List[Tuple[str, List[str]]] = []
    for doc in docs:
        section_text = getattr(doc, "page_content", "")
        headers: List[str] = []
        meta = getattr(doc, "metadata", {}) or {}
        if isinstance(meta, dict):
            raw_headers = meta.get("headers")
            if raw_headers:
                headers = _normalize_headers(raw_headers)
            else:
                # Fallback: collect keys like h1/h2/h3 or "header 1", "Header2"
                candidates: List[Tuple[int, str]] = []
                for key, value in meta.items():
                    if not value:
                        continue
                    key_norm = str(key).lower().replace(" ", "")
                    m = re.search(r"(?:^h|header)(\d+)$", key_norm)
                    if m:
                        try:
                            level = int(m.group(1))
                        except Exception:
                            level = 99
                        candidates.append((level, str(value)))
                if candidates:
                    headers = [v for _, v in sorted(candidates, key=lambda x: x[0])]
        sections.append((section_text, headers))
    if not sections:
        sections = [(markdown_text, [])]
    return sections


def _split_paragraphs(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n"], chunk_size=10_000, chunk_overlap=0
    )
    return [t for t in splitter.split_text(text) if t.strip()]


def _split_sentences(text: str) -> List[str]:
    try:
        sent_splitter = SpacyTextSplitter()
        return [s for s in sent_splitter.split_text(text) if s.strip()]
    except Exception:
        try:
            fallback = NLTKTextSplitter()
            return [s for s in fallback.split_text(text) if s.strip()]
        except Exception:
            return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _token_windows(text: str, size: int, overlap: int) -> List[str]:
    splitter = TokenTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return [t for t in splitter.split_text(text) if t.strip()]


def _pack_paragraphs(paragraphs: List[str]) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para = _normalize_text(para)
        para_tokens = _estimate_tokens_len(para)
        if para_tokens > CHUNK_SIZE:
            sentences = _split_sentences(para)
            for sent in sentences:
                sent = _normalize_text(sent)
                sent_tokens = _estimate_tokens_len(sent)
                if sent_tokens > CHUNK_SIZE:
                    for win in _token_windows(
                        sent, CHUNK_SIZE, CHUNK_OVERLAP_TOKENS
                    ):
                        if (
                            current_tokens + _estimate_tokens_len(win)
                            > CHUNK_SIZE
                            and current_tokens >= 300
                        ):
                            chunks.append("\n\n".join(current).strip())
                            current, current_tokens = [], 0
                        current.append(win)
                        current_tokens += _estimate_tokens_len(win)
                else:
                    if current_tokens + sent_tokens > CHUNK_SIZE:
                        if current_tokens >= 300:
                            chunks.append("\n\n".join(current).strip())
                            current, current_tokens = [], 0
                        else:
                            for win in _token_windows(
                                sent, CHUNK_SIZE - current_tokens, 0
                            ):
                                current.append(win)
                                current_tokens += _estimate_tokens_len(win)
                                if current_tokens >= CHUNK_SIZE:
                                    break
                            continue
                    current.append(sent)
                    current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > CHUNK_SIZE:
                if current_tokens >= 300:
                    chunks.append("\n\n".join(current).strip())
                    current, current_tokens = [], 0
                else:
                    sentences = _split_sentences(para)
                    for sent in sentences:
                        st = _estimate_tokens_len(sent)
                        if current_tokens + st > CHUNK_SIZE:
                            break
                        current.append(sent)
                        current_tokens += st
                    remaining = " ".join(sentences)
                    remaining_tokens = _estimate_tokens_len(remaining)
                    if remaining_tokens:
                        paragraphs.insert(
                            paragraphs.index(para) + 1, remaining
                        )
                    continue
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append("\n\n".join(current).strip())
    final_chunks: List[str] = []
    for ch in chunks:
        if len(ch) > CHUNK_CHAR_MAX:
            final_chunks.extend(
                _token_windows(ch, CHUNK_SIZE, CHUNK_OVERLAP_TOKENS)
            )
        else:
            final_chunks.append(ch)
    return final_chunks


class MarkdownParagraphSentenceChunkingStrategy(ChunkingStrategy):
    def chunk(
        self,
        *,
        text: str,
        file_id: int,
        workspace_id: int,
        s3_key: str,
        document_parser_version: str | None = None,
    ) -> List[Chunk]:
        text = _normalize_text(text)
        sections = _split_headings(text)
        all_chunks: List[Chunk] = []
        next_index = 0

        # Track first chunk id for the last seen section at each depth
        first_chunk_by_depth: Dict[int, str] = {}

        for section_text, section_path in sections:
            paragraphs = _split_paragraphs(section_text)
            chunks_text = (
                _pack_paragraphs(paragraphs)
                if paragraphs
                else _pack_paragraphs(_split_sentences(section_text))
            )
            section_local_index = 0

            # Determine parent section's first chunk id (nearest previous major of lower depth)
            depth = max(1, len(section_path))
            parent_first_chunk_id: Optional[str] = None
            for d in range(depth - 1, 0, -1):
                if d in first_chunk_by_depth:
                    parent_first_chunk_id = first_chunk_by_depth[d]
                    break
            # Fallback to previous section of the same depth if no higher-level parent found
            if parent_first_chunk_id is None and depth in first_chunk_by_depth:
                parent_first_chunk_id = first_chunk_by_depth[depth]

            first_chunk_id_current_section: Optional[str] = None

            for content in chunks_text:
                chunk_id = str(uuid4()).lower()
                # Prefix content with section header for context, if present
                if section_path:
                    header_depth = max(1, min(len(section_path), 6))
                    header_line = f"{'#' * header_depth} {section_path[-1]}\n"
                    content_full = f"{header_line}{content}".strip()
                else:
                    content_full = content

                # Build version object
                parser_version = document_parser_version or ""
                version: Dict[str, object] = {
                    "chunking_strategy": STRATEGY_VERSION,
                }
                if parser_version:
                    version["parser"] = parser_version

                payload: Chunk = {
                    "created_at": int(time.time()),
                    "s3_key": s3_key,
                    "file_id": file_id,
                    "workspace_id": workspace_id,
                    "acl_groups": ["*"],
                    "chunk_id": chunk_id,
                    "chunk_index": next_index,
                    "chunk_total": 0,
                    "previous_chunk_id": None,
                    "next_chunk_id": None,
                    "section_path": section_path,
                    "section_title": section_path[-1] if section_path else "",
                    "section_index": section_local_index,
                    # overlap tokens: 0 for this strategy's header-based splitting
                    "tokens": _estimate_tokens_len(content_full),
                    "overlap_tokens": 0,
                    "version": version,
                    "version_alias": f"{(parser_version or '')}:"
                    + STRATEGY_VERSION,
                    "domain": "",
                    "document_type": "",
                    "parent_id": parent_first_chunk_id,
                    "keywords": [],
                    "entities": [],
                    "language": "en",
                    "hash": _sha256_of_content(content_full),
                    "summary": "",
                    "provenance": {"original_s3_key": s3_key, "parsed": True},
                    "content": content_full,
                }

                # Capture first chunk id for this section
                if first_chunk_id_current_section is None:
                    first_chunk_id_current_section = chunk_id
                    first_chunk_by_depth[depth] = chunk_id

                all_chunks.append(payload)
                next_index += 1
                section_local_index += 1

        # relational fields
        total = len(all_chunks)
        for i, d in enumerate(all_chunks):
            d["chunk_total"] = total
            if i > 0:
                d["previous_chunk_id"] = all_chunks[i - 1]["chunk_id"]
            if i < total - 1:
                d["next_chunk_id"] = all_chunks[i + 1]["chunk_id"]
        return all_chunks 