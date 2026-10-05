---
id: AC-OCR-002
title: Качество и ресурсная пригодность
status: draft
owner: Дмитрий Алексеев
last_updated: '2026-09-16'
scope: ocr-module
related:
  requirements: []
  adrs: []
  components: []
  verification:
  - TEST-OCR-003
  - TEST-OCR-004
  - TEST-OCR-005
  - TEST-OCR-007
  - TEST-OCR-008
  - TEST-OCR-009
  - TEST-OCR-011
  - TEST-OCR-012
  - TEST-OCR-014
  - TEST-OCR-017
  - TEST-OCR-023
  - TEST-OCR-024
  - TEST-OCR-025
---

# Качество и ресурсная пригодность

## Предусловия

До открытия независимого корпуса зафиксированы метрики, численные границы, формы, группы, правила учета отказа, способ интервала, модели и среда.

## Действие

Выполнить сквозные и ресурсные измерения выбранной конфигурации с независимым оценщиком.

## Ожидаемый результат

Каждое обязательное ограничение проверено на собственной области: поля и формы, неподдержанная выдача, отрицательные входы, порча, время и память. Улучшение среднего CER не компенсирует нарушение ограничения. CPU-корректор действительно работает на CPU; стоимость повторов включена.

## Допустимые отклонения

Численные границы еще не утверждены. Критерий требует их предварительной фиксации; отсутствие значения либо недостаточность страты блокирует соответствующий приемочный вывод. Исследовательские измерения при этом сохраняются с ограниченной областью.

## Метод и тесты

[TEST-OCR-003](../../verification/test-cases.md#test-ocr-003), [TEST-OCR-004](../../verification/test-cases.md#test-ocr-004), [TEST-OCR-005](../../verification/test-cases.md#test-ocr-005), [TEST-OCR-007](../../verification/test-cases.md#test-ocr-007), [TEST-OCR-008](../../verification/test-cases.md#test-ocr-008), [TEST-OCR-009](../../verification/test-cases.md#test-ocr-009), [TEST-OCR-011](../../verification/test-cases.md#test-ocr-011), [TEST-OCR-012](../../verification/test-cases.md#test-ocr-012), [TEST-OCR-014](../../verification/test-cases.md#test-ocr-014), [TEST-OCR-017](../../verification/test-cases.md#test-ocr-017), [TEST-OCR-023](../../verification/test-cases.md#test-ocr-023), [TEST-OCR-024](../../verification/test-cases.md#test-ocr-024), [TEST-OCR-025](../../verification/test-cases.md#test-ocr-025).

## Состав численного условия

Для каждой границы обязательны: ID метрики, поле/форма, направление сравнения, численное значение, знаменатель, корпус и число независимых групп, интервал или правило достаточности, версии нормализации/оценщика и аппаратный режим. Эти сведения являются частью конкретной согласованной редакции критерия.
