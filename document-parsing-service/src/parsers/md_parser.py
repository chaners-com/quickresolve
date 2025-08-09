from typing import Dict, Tuple


def parse(content: bytes) -> Tuple[str, Dict]:
    return (content.decode("utf-8", errors="ignore"), {})
