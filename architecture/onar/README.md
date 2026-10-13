# Onar Excalidraw conversion

These artifacts are a separate conversion of the supplied `IDRS(8).excalidraw` archive.
They do not replace the governed repository architecture under `architecture/sird-ocr.architecture.json`, `architecture/sird-ocr-dfd.architecture.json`, or `architecture/views.json`.

## Source areas

The Excalidraw canvas has four titled areas:

- `4C: Context` -> `context.architecture.json`
- `Statemachine` -> `statemachine.lifecycle.json`
- `User Story Mapping` -> represented in the cards of `use-cases.workflow.json`; it is not emitted as a standalone Archify type because Archify has no story-map-only diagram type
- `Use-cases Diagram` -> `use-cases.workflow.json`

The separate right-hand container topology is represented by `containers.architecture.json`.

## Proposed reconciliation shown here

- The proposed target keeps durable task state and polling inside the OCR module.
- The proposed external facade is gRPC `SubmitTask`, `GetStatus`, and `GetResult`.
- The bounded OCR operation remains `Recognize` inside the runtime.
- Result/error events return from preprocessing and OCR through the message bus to Task Service.
- Task and worker telemetry flows through OTLP to an OTEL Collector, telemetry backends, and Grafana.

These are proposals. The diagrams explicitly record that the current OpenSpec and `api.md` still define unary `Recognize` without durable OCR jobs. Kafka was removed from the repository by owner decision on 2026-10-13. RabbitMQ 4.3 is the workflow transport.
