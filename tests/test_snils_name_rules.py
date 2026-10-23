from sird_recognition._snils_name_resolution import resolve_name
from sird_recognition._snils_name_rules import name_candidates

_CARD = "Ф.И.О. СИДОРОВ\nПЕТР\n{}\nДата и место рождения 23 января 2004"
_GOOD = _CARD.format("ПЕТРОВИЧ")
_NOISY = _CARD.format("ПЕТРОВИЧЬ")
_NAME = "СИДОРОВ ПЕТР ПЕТРОВИЧ"


def test_dotted_label_outranks_header_words() -> None:
    text = (
        "СТРАХОВОЕ СВИДЕТЕЛЬСТВО\n"
        "ГОСУДАРСТВЕННОГО ПЕНСИОННОГО СТРАХОВАНИЯ\n"
        "Ф.И.О. СИДОРОВ\n"
        "ПЕТР\n"
        "ПЕТРОВИЧ\n"
        "Дата и место рождения 23 января 2004"
    )

    assert name_candidates([text]) == {_NAME}


def test_unlabelled_header_words_are_no_name() -> None:
    text = (
        "РОССИЙСКАЯ ФЕДЕРАЦИЯ\n"
        "СТРАХОВОЕ СВИДЕТЕЛЬСТВО\n"
        "ГОСУДАРСТВЕННОГО ПЕНСИОННОГО СТРАХОВАНИЯ\n"
        "СИДОРОВ ПЕТР ПЕТРОВИЧ\n"
        "Пол Мужской ГОР\n"
    )

    assert name_candidates([text]) == {_NAME}


def test_mixed_case_run_is_no_name() -> None:
    text = "ВЕР то ко\nВеРНО ГОР ТО\nСИДОРОВ ПЕТР ПЕТРОВИЧ"

    assert name_candidates([text]) == {_NAME}


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

    assert name == _NAME


def test_tied_variants_stay_ambiguous() -> None:
    texts = (_GOOD, _GOOD, _NOISY, _NOISY)

    name, evidence = resolve_name(texts, ())

    assert (name, len(evidence)) == (None, 2)
