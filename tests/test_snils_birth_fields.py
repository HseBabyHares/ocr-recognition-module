from sird_recognition._snils_birth_fields import (
    birth_date_candidates,
    optional_unique_birth_place,
)


def test_card_place_on_line_after_date() -> None:
    text = "Дата и место рождения 20 де Кабря 1993 года\nКАЗАНЬ\nПол Женский"
    assert optional_unique_birth_place([text]) == "КАЗАНЬ"


def test_damaged_year_word_not_a_place() -> None:
    damaged = "Дата и место рождения 18 февраля 1960 Ода\nOMCK (e"
    clean = "Дата и место рождения 18 февраля 1960 года\nКАЗАНЬ"
    assert optional_unique_birth_place([damaged, clean]) == "КАЗАНЬ"


def test_place_after_comma_kept() -> None:
    text = "Дата и место рождения: 3 апреля 1980, г. Москва\nПол Мужской"
    assert optional_unique_birth_place([text]) == "г. Москва"


def test_empty_place_row_skips_sex_row() -> None:
    text = "Место рождения\nПол Женский\nДата регистрации 07.09.1990"
    assert optional_unique_birth_place([text]) is None


def test_damaged_birth_label_keeps_fields() -> None:
    # One wrong letter in "рождения" and a lost "дата" word.
    text = "Лаиа и место рожденця 20 декабря 1993 года\nКАЗАНЬ\nПол Женский"
    assert optional_unique_birth_place([text]) == "КАЗАНЬ"
    assert birth_date_candidates([text]) == {"1993-12-20"}


def test_registration_date_is_no_birth_date() -> None:
    assert not birth_date_candidates(["Дата регистрации 07.09.1990"])
