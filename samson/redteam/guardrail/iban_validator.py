"""IBAN extraction, format validation, and ISO 13616 mod-97 checksum verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# ISO 13616 country → total IBAN length (chars). Used to bound embedded extraction.
_IBAN_LENGTHS: dict[str, int] = {
    "AL": 28, "AD": 24, "AT": 20, "AZ": 28, "BE": 16, "BH": 22, "BA": 20, "BR": 29,
    "BG": 22, "CR": 22, "HR": 21, "CY": 28, "CZ": 24, "DK": 18, "DO": 28, "EE": 20,
    "FO": 18, "FI": 18, "FR": 27, "GE": 22, "DE": 22, "GI": 23, "GR": 27, "GL": 18,
    "GT": 28, "HU": 28, "IS": 26, "IE": 22, "IL": 23, "IT": 27, "JO": 30, "KZ": 20,
    "KW": 30, "LV": 21, "LB": 28, "LI": 21, "LT": 20, "LU": 20, "MK": 19, "MT": 31,
    "MR": 27, "MU": 30, "MC": 27, "MD": 24, "ME": 22, "NL": 18, "NO": 15, "PK": 24,
    "PS": 29, "PL": 28, "PT": 25, "QA": 29, "RO": 24, "SM": 27, "SA": 24, "RS": 22,
    "SK": 24, "SI": 19, "ES": 24, "SE": 24, "CH": 21, "TN": 24, "TR": 26, "AE": 23,
    "GB": 22, "VG": 24, "XK": 20, "UA": 29, "EG": 29, "LC": 32, "SC": 31, "ST": 25,
    "TL": 23, "BY": 28, "SV": 28, "IQ": 23, "VA": 22,
}

_IBAN_STRUCT = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")
_IBAN_LOOSE = re.compile(
    r"(?<![A-Za-z0-9])("
    r"[A-Z]{2}"
    r"(?:[\s\-\u00ad\u200b-\u200f\u202a-\u202e\u2060\ufeff]*\d){2}"
    r"(?:[\s\-\u00ad\u200b-\u200f\u202a-\u202e\u2060\ufeff]*[A-Z0-9]){11,30}"
    r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_NORMALIZE_RE = re.compile(
    r"[\s\-\u00ad\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060\ufeff]+"
)


class IbanValidationStatus(str, Enum):
    VALID_WHITELISTED = "valid_whitelisted"
    VALID_NOT_WHITELISTED = "valid_not_whitelisted"
    INVALID_FORMAT = "invalid_format"
    INVALID_CHECKSUM = "invalid_checksum"


@dataclass(frozen=True)
class IbanValidationResult:
    raw: str
    normalized: str
    status: IbanValidationStatus
    whitelisted: bool


def normalize_outbound_text(text: str) -> str:
    """Strip spaces, dashes, and invisible characters before IBAN regex extraction."""
    if not text:
        return ""
    return _NORMALIZE_RE.sub("", text)


def normalize_iban(value: str) -> str:
    return normalize_outbound_text(value).upper()


def extract_ibans(text: str) -> list[str]:
    """Return deduplicated normalized IBAN candidates from outbound payload text.

    Normalization (spaces / dashes / invisible chars) runs first. Candidates are
    bounded by ISO country lengths so trailing prose cannot glue onto the BBAN.
    A separator-tolerant loose pattern also runs on the raw payload.
    """
    if not text:
        return []

    seen: set[str] = set()
    results: list[str] = []

    def _add(candidate: str) -> None:
        normalized = normalize_iban(candidate)
        if not _IBAN_STRUCT.fullmatch(normalized):
            return
        cc = normalized[:2]
        expected = _IBAN_LENGTHS.get(cc)
        if expected is not None and len(normalized) != expected:
            return
        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    cleaned = normalize_outbound_text(text).upper()
    i = 0
    while i <= len(cleaned) - 15:
        cc = cleaned[i : i + 2]
        expected = _IBAN_LENGTHS.get(cc)
        if expected and cleaned[i + 2 : i + 4].isdigit() and i + expected <= len(cleaned):
            candidate = cleaned[i : i + expected]
            if _IBAN_STRUCT.fullmatch(candidate):
                _add(candidate)
                i += expected
                continue
        i += 1

    for match in _IBAN_LOOSE.finditer(text):
        _add(match.group(1))

    return results


def _iban_to_numeric(iban: str) -> str:
    rearranged = iban[4:] + iban[:4]
    digits: list[str] = []
    for char in rearranged:
        if char.isdigit():
            digits.append(char)
        elif char.isalpha():
            digits.append(str(ord(char) - 55))
        else:
            return ""
    return "".join(digits)


def verify_iban_checksum(iban: str) -> bool:
    """ISO 13616 mod-97 check — remainder must equal 1. Never raises on bad input."""
    try:
        normalized = normalize_iban(iban)
        if not _IBAN_STRUCT.fullmatch(normalized):
            return False
        expected = _IBAN_LENGTHS.get(normalized[:2])
        if expected is not None and len(normalized) != expected:
            return False
        numeric = _iban_to_numeric(normalized)
        if not numeric:
            return False
        remainder = 0
        for i in range(0, len(numeric), 9):
            chunk = str(remainder) + numeric[i : i + 9]
            remainder = int(chunk) % 97
        return remainder == 1
    except (TypeError, ValueError, OverflowError):
        return False


def validate_iban(value: str, whitelist: frozenset[str]) -> IbanValidationResult:
    """Validate a single IBAN candidate against format, whitelist, and mod-97."""
    try:
        normalized = normalize_iban(value or "")
    except (TypeError, AttributeError):
        return IbanValidationResult(
            raw=str(value),
            normalized="",
            status=IbanValidationStatus.INVALID_FORMAT,
            whitelisted=False,
        )

    expected = _IBAN_LENGTHS.get(normalized[:2]) if len(normalized) >= 2 else None
    if not _IBAN_STRUCT.fullmatch(normalized) or (
        expected is not None and len(normalized) != expected
    ):
        return IbanValidationResult(
            raw=value,
            normalized=normalized,
            status=IbanValidationStatus.INVALID_FORMAT,
            whitelisted=False,
        )

    whitelist_norm = frozenset(normalize_iban(w) for w in whitelist)
    if normalized in whitelist_norm:
        return IbanValidationResult(
            raw=value,
            normalized=normalized,
            status=IbanValidationStatus.VALID_WHITELISTED,
            whitelisted=True,
        )

    if not verify_iban_checksum(normalized):
        return IbanValidationResult(
            raw=value,
            normalized=normalized,
            status=IbanValidationStatus.INVALID_CHECKSUM,
            whitelisted=False,
        )

    return IbanValidationResult(
        raw=value,
        normalized=normalized,
        status=IbanValidationStatus.VALID_NOT_WHITELISTED,
        whitelisted=False,
    )


def evaluate_outbound_ibans(
    text: str,
    whitelist: frozenset[str],
) -> list[IbanValidationResult]:
    """Evaluate all IBANs in an outbound payload; never raises on malformed text."""
    try:
        candidates = extract_ibans(text or "")
    except (TypeError, AttributeError):
        return []
    return [validate_iban(iban, whitelist) for iban in candidates]
