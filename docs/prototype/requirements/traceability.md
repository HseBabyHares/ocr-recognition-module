---
id: DOC-OCR-TRACEABILITY
title: Трассируемость требований OCR-модуля
status: draft
owner: Дмитрий Алексеев
last_updated: '2026-09-16'
scope: ocr-module
related:
  requirements:
  - CON-OCR-001
  - FR-EXP-001
  - FR-EXP-002
  - FR-EXP-003
  - FR-EXP-004
  - FR-EXP-005
  - FR-OCR-001
  - FR-OCR-002
  - FR-OCR-003
  - FR-OCR-004
  - FR-OCR-005
  - FR-OCR-006
  - FR-OCR-007
  - FR-OCR-008
  - FR-OCR-009
  - FR-OCR-010
  - FR-OCR-011
  - FR-OCR-012
  - FR-OCR-013
  - FR-OCR-014
  - FR-OCR-015
  - FR-OCR-016
  - NFR-OCR-001
  - NFR-OCR-002
  - NFR-OCR-003
  - NFR-OCR-004
  - SEC-OCR-001
  - SEC-OCR-002
  - SEC-OCR-003
  - SEC-OCR-004
  adrs: []
  components:
  - ARC-OCR-CORRECTION
  - ARC-OCR-EVALUATOR
  - ARC-OCR-EXPERIMENT
  - ARC-OCR-FIELDS
  - ARC-OCR-GEOMETRY
  - ARC-OCR-PREPARE
  - ARC-OCR-PROBE
  - ARC-OCR-QUALITY
  - ARC-OCR-READER
  - ARC-OCR-RUNTIME
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

# Трассируемость требований OCR-модуля

Одна строка связывает нормативное требование модуля с назначением, компонентом, критерием и проверками. Результаты выполненных тестов хранятся в отдельных запусках.

| Требование | Назначение | Компонент | Критерий | Тесты |
|---|---|---|---|---|
| [FR-OCR-001](SRS.md#fr-ocr-001) – Проверка входа | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-PREPARE](../architecture/views/components.md#arc-ocr-prepare) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-001](../verification/test-cases.md#test-ocr-001), [TEST-OCR-002](../verification/test-cases.md#test-ocr-002) |
| [FR-OCR-002](SRS.md#fr-ocr-002) – Отсутствие и неопределенность объекта | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-PROBE](../architecture/views/components.md#arc-ocr-probe) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-003](../verification/test-cases.md#test-ocr-003) |
| [FR-OCR-003](SRS.md#fr-ocr-003) – Несколько объектов | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-PROBE](../architecture/views/components.md#arc-ocr-probe) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-004](../verification/test-cases.md#test-ocr-004) |
| [FR-OCR-004](SRS.md#fr-ocr-004) – Форма документа | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-PROBE](../architecture/views/components.md#arc-ocr-probe) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-005](../verification/test-cases.md#test-ocr-005) |
| [FR-OCR-005](SRS.md#fr-ocr-005) – Ориентация и геометрия | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-GEOMETRY](../architecture/views/components.md#arc-ocr-geometry) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-006](../verification/test-cases.md#test-ocr-006), [TEST-OCR-007](../verification/test-cases.md#test-ocr-007) |
| [FR-OCR-006](SRS.md#fr-ocr-006) – Измерение качества | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-QUALITY](../architecture/views/components.md#arc-ocr-quality) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-008](../verification/test-cases.md#test-ocr-008) |
| [FR-OCR-007](SRS.md#fr-ocr-007) – Управляемая предобработка | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-GEOMETRY](../architecture/views/components.md#arc-ocr-geometry) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-009](../verification/test-cases.md#test-ocr-009), [TEST-OCR-016](../verification/test-cases.md#test-ocr-016) |
| [FR-OCR-008](SRS.md#fr-ocr-008) – Наблюдения OCR | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-READER](../architecture/views/components.md#arc-ocr-reader) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-010](../verification/test-cases.md#test-ocr-010) |
| [FR-OCR-009](SRS.md#fr-ocr-009) – Извлечение полей | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-FIELDS](../architecture/views/components.md#arc-ocr-fields) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-011](../verification/test-cases.md#test-ocr-011) |
| [FR-OCR-010](SRS.md#fr-ocr-010) – Нормализация и коррекция | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-CORRECTION](../architecture/views/components.md#arc-ocr-correction) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-012](../verification/test-cases.md#test-ocr-012) |
| [FR-OCR-011](SRS.md#fr-ocr-011) – Ограничение исправлений | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-CORRECTION](../architecture/views/components.md#arc-ocr-correction) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-012](../verification/test-cases.md#test-ocr-012), [TEST-OCR-013](../verification/test-cases.md#test-ocr-013) |
| [FR-OCR-012](SRS.md#fr-ocr-012) – Частичность и конфликт | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-FIELDS](../architecture/views/components.md#arc-ocr-fields) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-013](../verification/test-cases.md#test-ocr-013), [TEST-OCR-014](../verification/test-cases.md#test-ocr-014) |
| [FR-OCR-013](SRS.md#fr-ocr-013) – Формальные проверки | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-FIELDS](../architecture/views/components.md#arc-ocr-fields) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-015](../verification/test-cases.md#test-ocr-015) |
| [FR-OCR-014](SRS.md#fr-ocr-014) – Ограничение исполнения | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-016](../verification/test-cases.md#test-ocr-016), [TEST-OCR-021](../verification/test-cases.md#test-ocr-021) |
| [FR-OCR-015](SRS.md#fr-ocr-015) – Фактическая конфигурация | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-017](../verification/test-cases.md#test-ocr-017) |
| [FR-OCR-016](SRS.md#fr-ocr-016) – Контракт интеграции | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-018](../verification/test-cases.md#test-ocr-018) |
| [FR-EXP-001](SRS.md#fr-exp-001) – Смена и отключение стадий | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EXPERIMENT](../architecture/views/components.md#arc-ocr-experiment) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-019](../verification/test-cases.md#test-ocr-019) |
| [FR-EXP-002](SRS.md#fr-exp-002) – Результат каждого примера | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EXPERIMENT](../architecture/views/components.md#arc-ocr-experiment) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-020](../verification/test-cases.md#test-ocr-020) |
| [FR-EXP-003](SRS.md#fr-exp-003) – Изоляция эталона | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EVALUATOR](../architecture/views/components.md#arc-ocr-evaluator) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-022](../verification/test-cases.md#test-ocr-022) |
| [FR-EXP-004](SRS.md#fr-exp-004) – Повторный расчет | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EVALUATOR](../architecture/views/components.md#arc-ocr-evaluator) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-023](../verification/test-cases.md#test-ocr-023) |
| [FR-EXP-005](SRS.md#fr-exp-005) – Измерение затрат | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EXPERIMENT](../architecture/views/components.md#arc-ocr-experiment) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-024](../verification/test-cases.md#test-ocr-024) |
| [NFR-OCR-001](SRS.md#nfr-ocr-001) – Изменяемость реализаций | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-010](../verification/test-cases.md#test-ocr-010), [TEST-OCR-019](../verification/test-cases.md#test-ocr-019) |
| [NFR-OCR-002](SRS.md#nfr-ocr-002) – Интерпретация уверенности | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-FIELDS](../architecture/views/components.md#arc-ocr-fields) | [AC-OCR-002](../product/acceptance-criteria/AC-OCR-002-quality.md) | [TEST-OCR-017](../verification/test-cases.md#test-ocr-017), [TEST-OCR-025](../verification/test-cases.md#test-ocr-025) |
| [NFR-OCR-003](SRS.md#nfr-ocr-003) – Воспроизводимость | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EXPERIMENT](../architecture/views/components.md#arc-ocr-experiment) | [AC-OCR-003](../product/acceptance-criteria/AC-OCR-003-experiments.md) | [TEST-OCR-019](../verification/test-cases.md#test-ocr-019), [TEST-OCR-020](../verification/test-cases.md#test-ocr-020) |
| [NFR-OCR-004](SRS.md#nfr-ocr-004) – Качество в условиях применения | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-EVALUATOR](../architecture/views/components.md#arc-ocr-evaluator) | [AC-OCR-002](../product/acceptance-criteria/AC-OCR-002-quality.md) | [TEST-OCR-023](../verification/test-cases.md#test-ocr-023), [TEST-OCR-025](../verification/test-cases.md#test-ocr-025) |
| [CON-OCR-001](SRS.md#con-ocr-001) – Локальная коррекция на CPU | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-CORRECTION](../architecture/views/components.md#arc-ocr-correction) | [AC-OCR-002](../product/acceptance-criteria/AC-OCR-002-quality.md) | [TEST-OCR-024](../verification/test-cases.md#test-ocr-024) |
| [SEC-OCR-001](SRS.md#sec-ocr-001) – Изоляция декодирования | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-PREPARE](../architecture/views/components.md#arc-ocr-prepare) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-002](../verification/test-cases.md#test-ocr-002), [TEST-OCR-021](../verification/test-cases.md#test-ocr-021) |
| [SEC-OCR-002](SRS.md#sec-ocr-002) – Данные в диагностике | [PRD-OCR-001](../product/PRD.md#prd-ocr-001) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-021](../verification/test-cases.md#test-ocr-021) |
| [SEC-OCR-003](SRS.md#sec-ocr-003) – Загрузка реализаций | [PRD-OCR-002](../product/PRD.md#prd-ocr-002) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-017](../verification/test-cases.md#test-ocr-017), [TEST-OCR-021](../verification/test-cases.md#test-ocr-021) |
| [SEC-OCR-004](SRS.md#sec-ocr-004) – Разделение материалов | [PRD-OCR-003](../product/PRD.md#prd-ocr-003) | [ARC-OCR-RUNTIME](../architecture/views/components.md#arc-ocr-runtime) | [AC-OCR-001](../product/acceptance-criteria/AC-OCR-001-contract.md) | [TEST-OCR-021](../verification/test-cases.md#test-ocr-021), [TEST-OCR-022](../verification/test-cases.md#test-ocr-022) |
