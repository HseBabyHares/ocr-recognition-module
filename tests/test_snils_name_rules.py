from sird_recognition._snils_name_rules import name_candidates


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
