import json
import os
import shutil
from pathlib import Path

import pytest

# Make src importable: add project root (chunking-service/) to sys.path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.chunking_strategies.markdown_paragraph_sentence import (
    MarkdownParagraphSentenceChunkingStrategy,
)

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "outputs"


def _iter_md_inputs():
    env_path = os.getenv("CHUNK_INPUT_PATH", "").strip()
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            candidate = INPUT_DIR / env_path
            p = candidate if candidate.exists() else p.resolve()
        return [p]
    return sorted(INPUT_DIR.glob("*.md"))


@pytest.fixture(autouse=True)
def clean_outputs():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _write_chunks_per_file(chunks):
    total = len(chunks)
    width = max(3, len(str(total)))
    for idx, chunk in enumerate(chunks, start=1):
        chunk_id = chunk.get("chunk_id") or "unknown"
        prefix = f"{idx:0{width}d}"
        out_path = OUTPUT_DIR / f"{prefix}_{chunk_id}.json"
        out_path.write_text(
            json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8"
        )


@pytest.mark.parametrize("input_path", _iter_md_inputs())
def test_markdown_paragraph_sentence_chunker(input_path: Path):
    text = input_path.read_text(encoding="utf-8")
    chunker = MarkdownParagraphSentenceChunkingStrategy()
    chunks = chunker.chunk(
        text=text,
        file_id=0,
        workspace_id=0,
        s3_key=str(input_path),
        document_parser_version=None,
    )
    _write_chunks_per_file(chunks)
    assert len(chunks) > 0
    assert all("chunk_id" in c and "content" in c for c in chunks) 