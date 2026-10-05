---
id: ADR-OCR-005
title: Модель выполнения интеграции SIRD и OCR
status: proposed
owner: Дмитрий Алексеев
last_updated: '2026-09-20'
scope: ocr-module
related:
  requirements: []
  adrs:
  - ADR-OCR-001
  components: []
  verification: []
---

# Модель выполнения интеграции SIRD и OCR

## Контекст

SIRD обрабатывает документы через Task Service, Process Service и OCR Service. Архитектурная схема IDRS показывает RabbitMQ, task events, retry attempts, result events, PostgreSQL и S3/Minio. Пользователь подтвердил, что production SIRD вызывает OCR runtime по gRPC с Protobuf.

Заявленный p99 времени OCR для документа меньше 30 секунд. Production OCR должен масштабироваться независимыми stateless replicas. Долговечное состояние задания и публикация результата находятся за границей OCR runtime.

## Рассмотренные варианты

| Вариант | Плюсы | Ограничения |
|---|---|---|
| Асинхронный API самого OCR: `Submit`/`GetStatus`/`GetResult` | Подходит для долгой обработки | Требует внешнего durable job state и усложняет границу stateless OCR |
| Синхронный unary `Recognize` на всем внешнем API | Простой клиентский контракт | Не соответствует существующему task workflow и очереди |
| Асинхронный workflow SIRD + unary `Recognize` внутри | Сохраняет очередь и task state SIRD; OCR остается stateless; подходит для p99 < 30 секунд | Нужны finite deadline, retry и идемпотентность на границе Process Service → OCR Service |

## Решение

Решение состоит из границ поставки и модели выполнения:

Дополнительные границы поставки:

- production runtime отделен от HTTP-адаптера;
- Litestar + Granian используются только в test application;
- production image не включает test-only HTTP adapter и experimental runner/evaluator;
- experimental runner/evaluator поставляется отдельным runtime/package;
- production OCR масштабируется независимыми stateless replicas.

Модель выполнения:

Production RPC: единый unary `Recognize`; `Prepare`, `Probe` и `ExecuteProfile` не публикуются как отдельные production RPC.

1. **Внешний workflow SIRD асинхронный.** Task Service создает `task_id`, сохраняет начальный статус в PostgreSQL и публикует task event через RabbitMQ. Клиент получает статус и результат по идентификатору задания.
2. **Process Service — worker workflow.** Он потребляет task event, выполняет ограниченные retry attempts и вызывает OCR Service.
3. **Process Service → OCR Service — unary gRPC.** Метод `Recognize` принимает запрос с `task_id`/`request_id`, `artifact_ref` и согласованными параметрами обработки и возвращает operation status, form resolution, field results, diagnostics и execution metadata.
4. **OCR Service stateless.** OCR не создает и не хранит долговечные jobs. Любая реплика может обработать вызов.
5. **Материал передается через S3/Minio.** `artifact_ref` указывает на SIRD-owned object storage. OCR использует служебные полномочия; байты документа не передаются в gRPC payload.
6. **PostgreSQL владеет task state.** В нем хранятся статус, попытки, ошибки и результат либо ссылка на результат.
7. **Result delivery идемпотентен.** PostgreSQL transactional outbox фиксирует публикацию результата; повторная доставка безопасно допубликовывает событие без создания второго logical result.

Связь `recognize request` на исходной схеме уточняется как gRPC. Протокол не был указан в подписи схемы; он принят отдельным решением.

MVP-предметное поведение:

1. OCR автоматически классифицирует ровно одну из форм `snils_card`, `adi_reg_2019`, `adi_reg_2023`; caller не обязан передавать форму или профиль в production `Recognize`.
2. При `form_ambiguous`, `FormResolution=unsupported`, `target_not_detected` или `multiple_candidates` профиль не запускается, документ не угадывается, а SIRD получает terminal non-retryable subject outcome.
3. Для resolved form OCR возвращает `snils`, `full_name` и `birth_date`. Читаемые поля сохраняются при повреждении другого поля; поврежденное поле получает `null`, существующий field status и machine-readable diagnostic. Восстановление по догадке запрещено.
4. Полный результат имеет `operation_status=ok`. Resolved form с неполными полями имеет `operation_status=ok` и `result_completeness=partial`; `operation_status=partial` сохраняется для неполной подготовки или исполнения. Технический сбой отделен от предметной диагностики.

Внутренний `ExecuteProfile` сохраняет caller-selected `form_id`/`profile_id` как транспортно-нейтральный stage contract; production `Recognize` не принимает эти selectors и передает их только после внутренней классификации.

Операционные значения MVP:

- gRPC deadline — 35 секунд на попытку;
- максимум три попытки на task, включая первую;
- backoff — одна секунда, затем две секунды;
- повторяются только transient technical failures;
- production channel использует mTLS и service identity authorization;
- исчерпание бюджета переводит delivery в настроенный DLQ;
- subject outcomes и field-quality outcomes автоматически не повторяются.

## Согласование с протодокументацией

Это ADR уточняет target production integration и не переписывает внутренние вычислительные порты:

- `architecture/interfaces/internal-contracts.md` оставляет транспортную реализацию вычислительных портов неназначенной. Это правило сохраняется для внутренних стадий; для production SIRD → OCR выбрана отдельная gRPC/Protobuf-граница.
- `architecture/views/containers.md` допускает общую транспортную оболочку с СИРД. Для target production выбран отдельный OCR runtime с gRPC endpoint; общая оболочка остается допустимой для других локальных/test сценариев, но не является выбранной production-моделью.
- `requirements/SRS.md` требует, чтобы OCR-модуль не зависел от базы, брокера и учетных записей СИРД. Это ADR не переносит эти зависимости в OCR runtime: Task Service и Process Service владеют workflow, а OCR получает только контракт запроса и `artifact_ref` с необходимыми служебными полномочиями.


## Границы решения

Это ADR фиксирует модель выполнения, MVP-предметное поведение и владение состоянием. Оно не фиксирует только deployment-specific значения:

- точные номера полей Protobuf и имена RabbitMQ topology;
- конкретный issuer сертификатов и значения endpoint/credential binding;
- версии моделей и числовые пороги калибровки, которые фиксируются после эксперимента на размеченном корпусе.

Эти значения не меняют выбранные workflow, unary RPC, правила строгой классификации и field-level partial result.

## Последствия

Положительные последствия:

- внешний клиент не удерживает gRPC-соединение на время всего workflow;
- OCR не зависит от PostgreSQL, RabbitMQ или долговечного task state;
- горизонтальное масштабирование OCR не требует sticky sessions;
- исходные материалы и крупные результаты не проходят через gRPC payload.

Риски и обязательные условия:

- deadline должен иметь запас относительно p99 и учитывать сетевые задержки;
- retry одного task event и retry одного gRPC-вызова не должны создавать неконтролируемые дубли;
- повторная доставка должна быть безопасной для PostgreSQL и result event;
- сбой между записью результата и публикацией события закрывается выбранным PostgreSQL transactional outbox; повторная доставка использует его для безопасной допубликации без альтернативного владельца публикации.

## Связь с другими решениями

- [ADR-OCR-001: Граница модуля и явные зависимости](ADR-OCR-001-scope-and-dependencies.md)

## Основание решения

- Подтвержденные решения пользователя в текущем exploratory-обсуждении.
- `IDRS(7).excalidraw`: RabbitMQ, Task Service, Process Service, OCR Service, `recognize request`, retry attempt, result event, PostgreSQL и S3/Minio.
- Заявленное ограничение: p99 OCR меньше 30 секунд.

## Статус проверки

Решение зафиксировано для дальнейшей спецификации. Реализация и runtime interoperability check отсутствуют.
