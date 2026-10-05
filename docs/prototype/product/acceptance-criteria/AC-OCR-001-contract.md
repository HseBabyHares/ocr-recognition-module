---
id: AC-OCR-001
title: Функциональный контракт модуля
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
  - TEST-OCR-021
---

# Функциональный контракт модуля

## Предусловия

Зафиксированы схема операции, профили и контролируемые входы; известны ожидаемые ответы полевых и геометрических функций.

## Действие

Выполнить контрактные и компонентные тесты, затем интеграционный вызов без компонентов СИРД.

## Ожидаемый результат

Все обязательные инварианты соблюдены: корректный отказ от недопустимого входа, раздельные кандидаты, происхождение координат и полей, отсутствие неподдержанных исправлений, конечный бюджет и защита материалов. Различие между результатом модели и ожидаемым значением реальной фотографии переносится в измерение качества; оно не стирается из результатов.

## Допустимые отклонения

Отклонения в типах, состояниях и связывании данных не допускаются. Допуск численных функций геометрии указан в соответствующем тесте и не является допустимой потерей текста.

## Метод и тесты

[TEST-OCR-001](../../verification/test-cases.md#test-ocr-001), [TEST-OCR-002](../../verification/test-cases.md#test-ocr-002), [TEST-OCR-003](../../verification/test-cases.md#test-ocr-003), [TEST-OCR-004](../../verification/test-cases.md#test-ocr-004), [TEST-OCR-005](../../verification/test-cases.md#test-ocr-005), [TEST-OCR-006](../../verification/test-cases.md#test-ocr-006), [TEST-OCR-007](../../verification/test-cases.md#test-ocr-007), [TEST-OCR-008](../../verification/test-cases.md#test-ocr-008), [TEST-OCR-009](../../verification/test-cases.md#test-ocr-009), [TEST-OCR-010](../../verification/test-cases.md#test-ocr-010), [TEST-OCR-011](../../verification/test-cases.md#test-ocr-011), [TEST-OCR-012](../../verification/test-cases.md#test-ocr-012), [TEST-OCR-013](../../verification/test-cases.md#test-ocr-013), [TEST-OCR-014](../../verification/test-cases.md#test-ocr-014), [TEST-OCR-015](../../verification/test-cases.md#test-ocr-015), [TEST-OCR-016](../../verification/test-cases.md#test-ocr-016), [TEST-OCR-017](../../verification/test-cases.md#test-ocr-017), [TEST-OCR-018](../../verification/test-cases.md#test-ocr-018), [TEST-OCR-021](../../verification/test-cases.md#test-ocr-021).
