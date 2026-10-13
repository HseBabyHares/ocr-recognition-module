# Proposal

## Why

SIRD Recognition has a broad prototype specification but no single executable OpenSpec source. The prototype covers product scope, computation, data lineage, integration, security, experiments, verification, and operations. The MVP also needs one explicit subject-level contract: classify the input among the three supported SNILS forms, reject unsupported or ambiguous documents without guessing, and preserve readable fields when an individual field is damaged.

## What Changes

- Migrate the complete `docs/prototype` specification into OpenSpec deltas instead of leaving normative behavior split across draft documents.
- Preserve stable requirement, test, acceptance, architecture, metric, and runbook identifiers through a source-to-OpenSpec traceability map.
- Migrate product scope, use cases, SRS functional/NFR/security/domain rules, data model/lifecycle, interfaces, architecture views/ADRs, glossary, verification, experiments, and operations.
- Define separate production OCR, SIRD integration, test, and experimental runtime boundaries; implement Task/Process Service in a separate integration package in this repository without adding broker/database dependencies to OCR.
- Define a production OCR runtime that scales as independent stateless replicas.
- Define a test-only Litestar + Granian HTTP adapter.
- Define the experimental runner/evaluator as a separate runtime excluded from the production image.
- Define SIRD-owned RustFS (S3-compatible) artifact access through task-bound `artifact_ref` and service credentials.
- Define the asynchronous SIRD workflow through Task Service, RabbitMQ 4.3 durable quorum queues using `aio-pika`, Process Service, PostgreSQL, and `task_id`. The Kafka baseline was removed by owner decision on 2026-10-13.
- Define unary gRPC + Protobuf communication from Process Service to OCR Service through `Recognize`.
- Define MVP classification for the old SNILS card, ADI-REG 2019, and ADI-REG 2023 with deterministic strict uncertainty behavior.
- Define explicit technical/subject/result-completeness mappings, retry taxonomy, idempotency, finite deadline, local TLS/mTLS boundary, result publication, redelivery recovery, and transactional outbox.
- Make Docker Compose the first integrated release gate. Defer Helm/Kubernetes deployment, multi-node broker availability, production workload identity and broker authorization, protected-corpus thresholds, and production p99 evidence.
- Keep the first version on a private local deployment boundary with a trusted SIRD backend, task-bound artifact capabilities, bounded decoding, safe logs, and cleanup. Defer production mTLS certificate issuance and rotation, service-mesh integration, RabbitMQ workload identity and broker-authorization operations until the SIRD deployment exists.
- Define field-level partial results and machine-readable diagnostics for glare, occlusion, low resolution, conflicts, and other unreadable fields.
- Keep prototype documents as migration evidence until traceability and validation complete; archive them only in a separately authorized cleanup step.

## Capabilities

### New Capabilities

- `sird-ocr-integration`: SIRD task workflow, artifact authorization, unary OCR gRPC execution, automatic form selection, result mapping, and failure recovery.
- `ocr-recognition`: Core OCR computation, data lineage, field behavior, bounded execution, no-guessing rules, and security.
- `ocr-experiment`: Independent experiment runner, per-sample records, evaluator, metrics, and selection evidence.
- `ocr-verification`: Contract, architecture, corpus, metrics, acceptance, and traceability oracles.
- `ocr-operations`: Reproducible packaging, startup/update, observability, rollback, and incident runbooks.

### Modified Capabilities

- None. The repository has no existing OpenSpec capabilities; this change creates the first capability specifications.

## Impact

- Replaces the prototype as the implementation source after migration reconciliation. The owner selected the current repository root for the Python implementation; implementation tasks remain open until their behavior is verified.
- Establishes contracts for Task Service, Process Service, OCR Service, gRPC/Protobuf, artifact access, PostgreSQL task state, RabbitMQ exchanges/queues/routing keys, classification, field diagnostics, experiments, acceptance, and operations. The Kafka baseline was removed by owner decision on 2026-10-13.
- Supersedes the prototype's caller-selected form/profile behavior only for the MVP production `Recognize` facade; internal OCR stages and their transport-neutral contracts remain.
- Requires explicit reconciliation where prototype transport, task, retry, or deployment details were intentionally open.
