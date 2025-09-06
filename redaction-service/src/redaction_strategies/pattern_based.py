"""
Pattern-based redaction strategy.

- Mask PII types with deterministic rules (always enabled in v1):
  - Emails in text and in URLs (including `mailto:`)
  - IPv4 and IPv6 (validated)
  - Credit card candidates (Luhn-validated)
  - IBAN (mod-97 check)
  - E.164 phones (conservative pattern)
- Deterministic per-document suffix:
  - Use HMAC-SHA256 with a per-document key derived
    as `HMAC(service_secret, file_id)`; token suffix
    for each matched value
    is `HMAC(per_doc_key, value)[:suffix_bytes]` in hex.
    This guarantees consistent suffixes for the same value
    within a document even when chunks are processed
    in parallel and across instances, without in-memory maps.
  - If later we need cross-file stability within a workspace,
  derive `per_workspace_key = HMAC(service_secret, workspace_id)`
  and switch derivation accordingly. For now, per-document only.
- Produce output Markdown preserving structure.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
from typing import Dict, Optional

from .base import RedactionConfig, RedactionResult, RedactionStrategy


def _derive_per_doc_key(
    service_secret: Optional[bytes], file_id: Optional[str]
) -> bytes:
    secret = service_secret or b"quickresolve-redaction-default"
    msg = (file_id or "").encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).digest()


def _hmac_suffix(per_doc_key: bytes, value: str, suffix_bytes: int) -> str:
    if suffix_bytes <= 0:
        return ""
    dig = hmac.new(per_doc_key, value.encode("utf-8"), hashlib.sha256).digest()
    return dig.hex()[: suffix_bytes * 2]


def _luhn_ok(num: str) -> bool:
    digits = [int(c) for c in num if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    # Reject sequences with all identical digits (e.g., all zeros)
    if all(d == digits[0] for d in digits):
        return False
    checksum = 0
    dbl = False
    for d in reversed(digits):
        x = d * 2 if dbl else d
        if x > 9:
            x -= 9
        checksum += x
        dbl = not dbl
    return checksum % 10 == 0


def _iban_ok(s: str) -> bool:
    s = re.sub(r"\s+", "", s).upper()
    if not 15 <= len(s) <= 34:
        return False
    if not re.match(r"^[A-Z]{2}[0-9A-Z]{13,32}$", s):
        return False
    s2 = s[4:] + s[:4]
    trans = "".join(str(int(ch, 36)) for ch in s2)
    mod = 0
    for ch in trans:
        mod = (mod * 10 + int(ch)) % 97
    return mod == 1


class PatternBasedRedactionStrategy(RedactionStrategy):
    VERSION = "pattern-based-1"

    def __init__(self) -> None:
        # Precompile patterns
        self.email_re = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
        self.mailto_re = re.compile(r"(?i)mailto:([^\s>)]+)")
        self.query_email_re = re.compile(
            r"(?i)([?&])(email|e|user_email)=([^&#\s]+)"
        )
        self.ipv4_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        # Simplified IPv6, validated later
        self.ipv6_re = re.compile(
            r"\b([0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}\b"
        )
        # Credit card candidate
        self.cc_re = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
        self.e164_re = re.compile(r"\+\d{6,15}")
        # IBAN candidate with optional spaces between groups
        # Matches two letters, then groups of 1-4 alphanumerics
        # possibly separated by spaces
        self.iban_candidate_re = re.compile(
            r"\b[A-Z]{2}[0-9A-Z]{2}(?: ?[0-9A-Z]{1,4}){3,8}\b"
        )

    def redact(self, text: str, config: RedactionConfig) -> RedactionResult:
        per_doc_key = _derive_per_doc_key(
            config.service_secret, config.file_id
        )
        metrics: Dict[str, int] = {
            "emails_masked": 0,
            "url_emails_masked": 0,
            "ipv4_masked": 0,
            "ipv6_masked": 0,
            "cc_masked": 0,
            "iban_masked": 0,
            "phones_masked": 0,
        }

        def mask_email(m: re.Match) -> str:
            value = m.group(0)
            suffix = _hmac_suffix(per_doc_key, value, config.suffix_bytes)
            metrics["emails_masked"] += 1
            return f"[EMAIL_MASKED_{suffix}]" if suffix else "[EMAIL_MASKED]"

        def mask_mailto(m: re.Match) -> str:
            addr = m.group(1)
            suffix = _hmac_suffix(per_doc_key, addr, config.suffix_bytes)
            metrics["url_emails_masked"] += 1
            return (
                f"mailto:[EMAIL_MASKED_{suffix}]"
                if suffix
                else "mailto:[EMAIL_MASKED]"
            )

        def mask_query_email(m: re.Match) -> str:
            prefix, key, value = m.group(1), m.group(2), m.group(3)
            suffix = _hmac_suffix(per_doc_key, value, config.suffix_bytes)
            metrics["url_emails_masked"] += 1
            rep = (
                f"{prefix}{key}=[EMAIL_MASKED_{suffix}]"
                if suffix
                else f"{prefix}{key}=[EMAIL_MASKED]"
            )
            return rep

        def mask_ipv4(m: re.Match) -> str:
            value = m.group(0)
            try:
                ipaddress.IPv4Address(value)
            except Exception:
                return value
            suffix = _hmac_suffix(per_doc_key, value, config.suffix_bytes)
            metrics["ipv4_masked"] += 1
            return f"[IP_MASKED_{suffix}]" if suffix else "[IP_MASKED]"

        def mask_ipv6(m: re.Match) -> str:
            value = m.group(0)
            try:
                ipaddress.IPv6Address(value)
            except Exception:
                return value
            suffix = _hmac_suffix(per_doc_key, value, config.suffix_bytes)
            metrics["ipv6_masked"] += 1
            return f"[IP_MASKED_{suffix}]" if suffix else "[IP_MASKED]"

        def mask_cc(m: re.Match) -> str:
            raw = m.group(0)
            digits_only = re.sub(r"[^0-9]", "", raw)
            if not _luhn_ok(digits_only):
                return raw
            suffix = _hmac_suffix(
                per_doc_key, digits_only, config.suffix_bytes
            )
            metrics["cc_masked"] += 1
            return f"[CC_MASKED_{suffix}]" if suffix else "[CC_MASKED]"

        def mask_iban(m: re.Match) -> str:
            value = m.group(0)
            compact = re.sub(r"\s+", "", value).upper()
            if not _iban_ok(compact):
                return value
            suffix = _hmac_suffix(per_doc_key, compact, config.suffix_bytes)
            metrics["iban_masked"] += 1
            return f"[IBAN_MASKED_{suffix}]" if suffix else "[IBAN_MASKED]"

        def mask_phone(m: re.Match) -> str:
            value = m.group(0)
            suffix = _hmac_suffix(per_doc_key, value, config.suffix_bytes)
            metrics["phones_masked"] += 1
            return f"[PHONE_MASKED_{suffix}]" if suffix else "[PHONE_MASKED]"

        # Order: URLs before plain email
        # to avoid double masking inside mailto/queries
        text = self.mailto_re.sub(mask_mailto, text)
        text = self.query_email_re.sub(mask_query_email, text)
        text = self.email_re.sub(mask_email, text)
        text = self.ipv4_re.sub(mask_ipv4, text)
        text = self.ipv6_re.sub(mask_ipv6, text)
        # IBAN before credit cards
        # to avoid CC masking inside IBAN sequences
        text = self.iban_candidate_re.sub(mask_iban, text)
        text = self.cc_re.sub(mask_cc, text)
        text = self.e164_re.sub(mask_phone, text)

        return RedactionResult(text=text, metrics=metrics)
