from sird_recognition._snils_birth_fields import (
    birth_date_candidates,
    optional_unique_birth_place,
)

_PLACE = "КАЗАНЬ"


def test_card_place_on_line_after_date() -> None:
    text = "Дата и место рождения 20 де Кабря 1993 года\nКАЗАНЬ\nПол Женский"
    assert optional_unique_birth_place([text]) == _PLACE


def test_damaged_year_word_not_a_place() -> None:
    damaged = "Дата и место рождения 18 февраля 1960 Ода\nOMCK (e"
    clean = "Дата и место рождения 18 февраля 1960 года\nКАЗАНЬ"
    assert optional_unique_birth_place([damaged, clean]) == _PLACE
    # One-letter OCR dust can come before the year word.
    dusty = "Дата и место рождения 18 февраля 1960 a годах\nКАЗАНЬ"
    assert optional_unique_birth_place([dusty]) == _PLACE


def test_place_after_comma_kept() -> None:
    text = "Дата и место рождения: 3 апреля 1980, г. Москва\nПол Мужской"
    assert optional_unique_birth_place([text]) == "г. Москва"


def test_empty_place_row_skips_sex_row() -> None:
    text = "Место рождения\nПол Женский\nДата регистрации 07.09.1990"
    assert optional_unique_birth_place([text]) is None


def test_damaged_birth_label_keeps_fields() -> None:
    # One wrong letter in "рождения" and a lost "дата" word.
    text = "Лаиа и место рожденця 20 декабря 1993 года\nКАЗАНЬ\nПол Женский"
    assert optional_unique_birth_place([text]) == _PLACE
    assert birth_date_candidates([text]) == {"1993-12-20"}


def test_registration_date_is_no_birth_date() -> None:
    assert not birth_date_candidates(["Дата регистрации 07.09.1990"])


def test_majority_of_variants_gives_place() -> None:
    clean = "Дата и место рождения 18 февраля 1960 года\nКАЗАНЬ"
    noisy = "Дата и место рождения 18 февраля 1960 года\nКАЗАНБ"
    assert optional_unique_birth_place([clean, clean, noisy, ""]) == _PLACE
    # A tie between two variants gives no place.
    assert optional_unique_birth_place([clean, noisy]) is None
