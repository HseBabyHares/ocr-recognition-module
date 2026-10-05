---
id: ARC-OCR-COMPONENTS
title: Паспорта компонентов OCR-модуля
status: draft
owner: Дмитрий Алексеев
last_updated: '2026-09-16'
scope: ocr-module
related:
  requirements: []
  adrs: []
  components: []
  verification:
  - TEST-OCR-001
  - TEST-OCR-002
  - TEST-OCR-003
  - TEST-OCR-004
  - TEST-OCR-005
  - TEST-OCR-006
  - TEST-OCR-007
  - TEST-OCR-008
  - TEST-OCR-009
  - TEST-OCR-010
  - TEST-OCR-011
  - TEST-OCR-012
  - TEST-OCR-013
  - TEST-OCR-014
  - TEST-OCR-015
  - TEST-OCR-016
  - TEST-OCR-017
  - TEST-OCR-018
  - TEST-OCR-019
  - TEST-OCR-020
  - TEST-OCR-021
  - TEST-OCR-022
  - TEST-OCR-023
  - TEST-OCR-024
  - TEST-OCR-025
---

# Паспорта компонентов OCR-модуля

Каждый компонент имеет самостоятельный контракт и набор проверок. Исполнитель экспериментов и оценщик находятся вне рабочего пути распознавания.

<a id="arc-ocr-prepare"></a>
## ARC-OCR-PREPARE – Подготовка растров страниц

**Вход:** Байты и InputPolicy.

**Выход:** Страницы PreparedPage, растры, ориентация, размеры, полнота подготовки и техническая диагностика.

**Граница:** Не определяет форму и не обращается к каталогу. Ошибка декодера не означает отсутствие объекта.

**Проверка:** Поврежденный файл или страница, размер и число страниц на границе, цветовые каналы, EXIF, частичная подготовка и отмена.

[TEST-OCR-001](../../verification/test-cases.md#test-ocr-001), [TEST-OCR-002](../../verification/test-cases.md#test-ocr-002), [TEST-OCR-006](../../verification/test-cases.md#test-ocr-006).

<a id="arc-ocr-probe"></a>
## ARC-OCR-PROBE – Поиск объекта и признаки формы

**Вход:** Подготовленный растр и план поиска.

**Выход:** ObjectCandidate и наблюдения формы/качества.

**Граница:** Не смешивает кандидаты. Собственная оценка детектора не объявляется вероятностью правильности поля.

**Проверка:** Положительные и отрицательные кадры, схожие формы, несколько объектов, недостаток признаков.

[TEST-OCR-003](../../verification/test-cases.md#test-ocr-003), [TEST-OCR-004](../../verification/test-cases.md#test-ocr-004), [TEST-OCR-005](../../verification/test-cases.md#test-ocr-005).

<a id="arc-ocr-geometry"></a>
## ARC-OCR-GEOMETRY – Геометрия и условная подготовка

**Вход:** Выбранный кандидат, растр, измерения и профиль.

**Выход:** Производный растр, преобразования и область доступных пикселей.

**Граница:** Не дорисовывает недоступный текст и не подменяет перспективу minAreaRect.

**Проверка:** Независимые углы, маски полей, ориентация, вырожденная геометрия и вариант без улучшений.

[TEST-OCR-006](../../verification/test-cases.md#test-ocr-006), [TEST-OCR-007](../../verification/test-cases.md#test-ocr-007), [TEST-OCR-009](../../verification/test-cases.md#test-ocr-009).

<a id="arc-ocr-quality"></a>
## ARC-OCR-QUALITY – Измерения качества

**Вход:** Материал, область и масштаб.

**Выход:** Измерения и интерпретации с версиями.

**Граница:** Белая бумага не равна доказанному блику; невозможность оценки сохраняется отдельно.

**Проверка:** Локальный дефект поля на хорошем фоне, разные масштабы, not_measured, условия полевого отказа.

[TEST-OCR-008](../../verification/test-cases.md#test-ocr-008), [TEST-OCR-014](../../verification/test-cases.md#test-ocr-014).

<a id="arc-ocr-reader"></a>
## ARC-OCR-READER – OCR-адаптер

**Вход:** Материал или ROI и настройки чтения.

**Выход:** Исходные TextObservation.

**Граница:** Не исправляет результат скрытым внешним сервисом; недоступные возможности указаны в descriptor.

**Проверка:** Набор контрактов движка, сырой текст, области, отсутствие scores, стоимость каждого вызова.

[TEST-OCR-010](../../verification/test-cases.md#test-ocr-010), [TEST-OCR-011](../../verification/test-cases.md#test-ocr-011).

<a id="arc-ocr-correction"></a>
## ARC-OCR-CORRECTION – Кандидаты исправлений

**Вход:** Поле, raw_value, OCR-наблюдения, политика.

**Выход:** Предложения изменения и их основания.

**Граница:** Не выбирает фамилию по частоте и номер по одной контрольной сумме. CPU-режим объявлен.

**Проверка:** Правильные редкие ФИО, типовые OCR-подмены, неподтвержденная замена, ограниченный бюджет.

[TEST-OCR-012](../../verification/test-cases.md#test-ocr-012), [TEST-OCR-013](../../verification/test-cases.md#test-ocr-013), [TEST-OCR-024](../../verification/test-cases.md#test-ocr-024).

<a id="arc-ocr-fields"></a>
## ARC-OCR-FIELDS – Извлечение и согласование полей

**Вход:** Наблюдения, профиль формы, кандидаты, правила и калибровка.

**Выход:** FieldResult и локальные проверки.

**Граница:** Не принимает решение о подлинности или пригодности документа для ВШЭ.

**Проверка:** Метки даты, конфликт, неприменимая проверка, частичный результат и некалиброванный score.

[TEST-OCR-011](../../verification/test-cases.md#test-ocr-011), [TEST-OCR-013](../../verification/test-cases.md#test-ocr-013), [TEST-OCR-014](../../verification/test-cases.md#test-ocr-014), [TEST-OCR-015](../../verification/test-cases.md#test-ocr-015), [TEST-OCR-025](../../verification/test-cases.md#test-ocr-025).

<a id="arc-ocr-runtime"></a>
## ARC-OCR-RUNTIME – Исполнитель стадий

**Вход:** Операция, материалы, спецификация и ограничения.

**Выход:** Ответ операции и записи завершенных стадий.

**Граница:** Не владеет брокером, транзакцией задания и опубликованным ответом СИРД.

**Проверка:** Отмена, пределы, версии, автономный запуск, освобождение ресурсов и изоляция.

[TEST-OCR-016](../../verification/test-cases.md#test-ocr-016), [TEST-OCR-017](../../verification/test-cases.md#test-ocr-017), [TEST-OCR-018](../../verification/test-cases.md#test-ocr-018), [TEST-OCR-021](../../verification/test-cases.md#test-ocr-021).

<a id="arc-ocr-experiment"></a>
## ARC-OCR-EXPERIMENT – Исполнитель экспериментов

**Вход:** ExperimentPlan и манифест без эталона.

**Выход:** Запись на каждую назначенную пару и паспорт.

**Граница:** Не удаляет неудачи, не меняет список вариантов по закрытому результату.

**Проверка:** Смена адаптера, отключение стадии, прерванный запуск, измерение затрат и повтор.

[TEST-OCR-019](../../verification/test-cases.md#test-ocr-019), [TEST-OCR-020](../../verification/test-cases.md#test-ocr-020), [TEST-OCR-024](../../verification/test-cases.md#test-ocr-024).

<a id="arc-ocr-evaluator"></a>
## ARC-OCR-EVALUATOR – Независимый оценщик

**Вход:** Предсказания, закрытый эталон и протокол.

**Выход:** Метрики, ошибки оценивания и область вывода.

**Граница:** Не передает эталон OCR и не заменяет отсутствующую строку успехом.

**Проверка:** Ручные числители и знаменатели, пустые страты, утечка, группировка и пересчет.

[TEST-OCR-022](../../verification/test-cases.md#test-ocr-022), [TEST-OCR-023](../../verification/test-cases.md#test-ocr-023), [TEST-OCR-025](../../verification/test-cases.md#test-ocr-025).
