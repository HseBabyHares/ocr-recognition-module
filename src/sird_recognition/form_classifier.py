"""Resolve the MVP document form from the page text.

The card and the ADI-REG notice carry distinct printed titles. The two
notice editions differ by issuer: the Pension Fund (PFR) form of 2019 and
the Social Fund (SFR) form of 2023. A missing or conflicting marker is an
ambiguity, never a fallback to a default form.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sird_recognition.contracts.stages import AmbiguousForm, UnsupportedForm

CALIBRATION_REF = "form-markers-v1"
SNILS_CARD = "snils_card"
ADI_REG_2019 = "adi_reg_2019"
ADI_REG_2023 = "adi_reg_2023"
SUPPORTED_FORMS = (SNILS_CARD, ADI_REG_2019, ADI_REG_2023)

_CARD_MARKERS = ("СТРАХОВОЕ СВИДЕТЕЛЬСТВО", "ПЕНСИОННОГО СТРАХОВАНИЯ")
_NOTICE_MARKERS = ("ПЕРСОНИФИЦИРОВАН", "АДИ-РЕГ", "О РЕГИСТРАЦИИ В СИСТЕМЕ")
_ISSUERS = {
    ADI_REG_2019: re.compile(r"\bПФР\b|ПЕНСИОННОГО ФОНДА"),
    ADI_REG_2023: re.compile(r"\bСФР\b|СОЦИАЛЬНОГО СТРАХОВАНИЯ"),
}
# OCR often returns Latin letters that look like Cyrillic ones.
_HOMOGLYPHS = str.maketrans("ABCEHKMOPTXY", "АВСЕНКМОРТХУ")

type FormDecision = str | AmbiguousForm | UnsupportedForm


def normalized(text: str) -> str:
    """Upper-case Cyrillic text with Latin look-alikes and spacing folded."""
    folded = text.upper().translate(_HOMOGLYPHS).replace("Ё", "Е")
    return " ".join(folded.split())


def classify_form(texts: Iterable[str]) -> FormDecision:
    """Return one supported form id, or an explicit rejection decision."""
    page = " ".join(normalized(text) for text in texts)
    families = [
        family
        for family, markers in (
            ("card", _CARD_MARKERS),
            ("notice", _NOTICE_MARKERS),
        )
        if any(marker in page for marker in markers)
    ]
    if not families:
        return UnsupportedForm()
    if families == ["card"]:
        return SNILS_CARD
    issuers = tuple(
        form for form, pattern in _ISSUERS.items() if pattern.search(page)
    )
    if families == ["notice"] and len(issuers) == 1:
        return issuers[0]
    if families == ["notice"]:
        return AmbiguousForm((ADI_REG_2019, ADI_REG_2023))
    return AmbiguousForm((SNILS_CARD, *(issuers or _ISSUERS)))
