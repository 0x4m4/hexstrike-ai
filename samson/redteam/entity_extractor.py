"""Extract financial and credential entities from HTTP response bodies."""

from __future__ import annotations

import json
import re
from typing import Any

_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_SK_RE = re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.IGNORECASE)
_CARD_RE = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")
_API_KEY_RE = re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*['\"]?([A-Za-z0-9\-_]{8,})", re.IGNORECASE)


def extract_financial_entities(response_payload: dict[str, Any] | str) -> list[str]:
    """Scan response text for IBANs, API keys, bearer tokens, and card-like patterns."""
    if isinstance(response_payload, dict):
        text = json.dumps(response_payload, ensure_ascii=False)
    else:
        text = str(response_payload)

    found: list[str] = []
    for pattern in (_IBAN_RE, _SK_RE, _BEARER_RE, _CARD_RE):
        found.extend(match.group(0) for match in pattern.finditer(text))
    for match in _API_KEY_RE.finditer(text):
        found.append(match.group(0))
    return sorted(set(found))
