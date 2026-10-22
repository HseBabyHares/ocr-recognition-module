from sird_recognition._snils_name_resolution import resolve_name
from sird_recognition._snils_name_rules import name_candidates

_CARD = "Ф.И.О. СИДОРОВ\nПЕТР\n{}\nДата и место рождения 23 января 2004"
_GOOD = _CARD.format("ПЕТРОВИЧ")
_NOISY = _CARD.format("ПЕТРОВИЧЬ")


def test_dotted_label_outranks_header_words() -> None:
    text = (
        "СТРАХОВОЕ СВИДЕТЕЛЬСТВО\n"
        "ГОСУДАРСТВЕННОГО ПЕНСИОННОГО СТРАХОВАНИЯ\n"
        "Ф.И.О. СИДОРОВ\n"
        "ПЕТР\n"
        "ПЕТРОВИЧ\n"
        "Дата и место рождения 23 января 2004"
    )

    assert name_candidates([text]) == {"СИДОРОВ ПЕТР ПЕТРОВИЧ"}


def test_separate_name_rows_resolved() -> None:
    text = (
        "Уведомление о регистрации в системе индивидуального\n"
        "лицевого счета\n"
        "Фамилия Сидоров\n"
        "Имя Петр\n"
        "Отчество (при наличии) Петрович\n"
        "Дата рождения 23.01.2004"
    )

    assert name_candidates([text]) == {"Сидоров Петр Петрович"}


def test_empty_patronymic_row_gives_two_word_name() -> None:
    text = (
        "Фамилия Сидоров\n"
        "Имя Петр\n"
        "Отчество (при наличии)\n"
        "Дата рождения 23.01.2004"
    )
    assert name_candidates([text]) == {"Сидоров Петр"}


def test_majority_of_variants_resolves_rule_name() -> None:
    texts = (_GOOD, _GOOD, _GOOD, _NOISY)

    name, _ = resolve_name(texts, ())

    assert name == "СИДОРОВ ПЕТР ПЕТРОВИЧ"


def test_tied_variants_stay_ambiguous() -> None:
    texts = (_GOOD, _GOOD, _NOISY, _NOISY)

    name, evidence = resolve_name(texts, ())

    assert (name, len(evidence)) == (None, 2)
