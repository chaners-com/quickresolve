"""
Base classes for redaction strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RedactionConfig:
    # number of bytes (hex pairs) to append to
    # mask tokens; default 1 byte -> 2 hex chars
    suffix_bytes: int = 1
    # whether to redact inside code fences/inline code if AST is used (future)
    redact_in_code_fences: bool = False
    redact_in_inline_code: bool = False
    # scope keys for HMAC derivation
    file_id: Optional[str] = None
    workspace_id: Optional[int] = None
    service_secret: Optional[bytes] = None


@dataclass
class RedactionResult:
    text: str
    metrics: Dict[str, int]


class RedactionStrategy:
    def redact(self, text: str, config: RedactionConfig) -> RedactionResult:
        raise NotImplementedError
