import pytest

from sird_recognition.contracts.stages import AmbiguousForm, UnsupportedForm
from sird_recognition.form_classifier import (
    ADI_REG_PFR,
    ADI_REG_SFR,
    SNILS_CARD,
    classify_form,
)

_NOTICE = "Уведомление о регистрации в системе индивидуального учета"
_CARD = "СТРАХОВОЕ СВИДЕТЕЛЬСТВО"


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        ((_CARD, "ГОСУДАРСТВЕННОГО ПЕНСИОННОГО СТРАХОВАНИЯ"), SNILS_CARD),
        ((_NOTICE, "территориального органа ПФР"), ADI_REG_PFR),
        ((_NOTICE, "территориального органа СФР"), ADI_REG_SFR),
        (("Форма АДИ-РЕГ", "органа CФP"), ADI_REG_SFR),
    ],
)
def test_supported_form_is_resolved(texts: tuple[str, ...], expected: str):
    assert classify_form(texts) == expected


@pytest.mark.parametrize(
    "texts",
    [
        (_NOTICE,),
        (_NOTICE, "органа ПФР", "органа СФР"),
        (_CARD, _NOTICE, "органа ПФР"),
    ],
)
def test_conflicting_markers_are_ambiguous(texts: tuple[str, ...]):
    assert isinstance(classify_form(texts), AmbiguousForm)


def test_page_without_markers_is_unsupported():
    assert classify_form(("Справка", "")) == UnsupportedForm()
