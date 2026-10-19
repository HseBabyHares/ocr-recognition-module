from sird_recognition._snils_birth_fields import optional_unique_birth_place


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
