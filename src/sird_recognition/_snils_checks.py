"""SNILS formatting, checksum, and text candidate checks."""

from __future__ import annotations

import re
from collections.abc import Iterable


class ServiceConfig:
    """Bound defaults and extraction patterns."""

    bytes_per_megabyte = 1024 * 1024
    max_input_megabytes = 15
    max_input_bytes = max_input_megabytes * bytes_per_megabyte
    max_pixels = 12_000_000
    max_side = 4096
    default_max_variants = 5
    checksum_digit_count = 9
    checksum_length = 11
    checksum_floor = 100
    checksum_special_values = (100, 101)
    checksum_modulus = 101
    snils_pattern = re.compile(
        r"(?<!\d)(?:\d{3}[\s\-\u2010\u2011\u2012\u2013\u2212]?){3}\d{2}(?!\d)"
    )
    snils_format = re.compile(
        r"\d{3}[\s\-\u2010\u2011\u2012\u2013\u2212]?"
        r"\d{3}[\s\-\u2010\u2011\u2012\u2013\u2212]?"
        r"\d{3}[\s\-\u2010\u2011\u2012\u2013\u2212]?\d{2}"
    )


def normalize_snils(candidate: str) -> str | None:
    """Normalize one formatted SNILS candidate without repairing digits."""
    if not isinstance(candidate, str):
        return None
    if not ServiceConfig.snils_format.fullmatch(candidate.strip()):
        return None
    return re.sub(r"\D", "", candidate)


def is_valid_snils(candidate: str) -> bool:
    """Validate all eleven digits using the official SNILS checksum."""
    if (
        not re.fullmatch(rf"\d{{{ServiceConfig.checksum_length}}}", candidate)
        or candidate == "00000000000"
    ):
        return False
    total = sum(
        int(digit) * (ServiceConfig.checksum_digit_count - index)
        for index, digit in enumerate(
            candidate[: ServiceConfig.checksum_digit_count]
        )
    )
    if total < ServiceConfig.checksum_floor:
        expected = total
    elif total in ServiceConfig.checksum_special_values:
        expected = 0
    else:
        remainder = total % ServiceConfig.checksum_modulus
        expected = remainder if remainder < ServiceConfig.checksum_floor else 0
    return expected == int(candidate[ServiceConfig.checksum_digit_count :])


def snils_candidates(texts: Iterable[str]) -> tuple[str, ...]:
    """Return normalized SNILS candidates in first-seen order."""
    candidates: list[str] = []
    for text in texts:
        for match in ServiceConfig.snils_pattern.finditer(text):
            normalized = normalize_snils(match.group())
            if normalized is not None and normalized not in candidates:
                candidates.append(normalized)
    return tuple(candidates)
