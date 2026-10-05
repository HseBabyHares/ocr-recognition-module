# Design

## Context

This change migrates the complete `docs/prototype` specification into OpenSpec. The source set includes product scope and use cases, SRS and quality attributes, architecture/data/interfaces/security/views/ADRs, verification plans/cases/corpus/metrics/experiments, operations/runbooks, and the glossary. The OpenSpec capability is split into five deltas:

- `sird-ocr-integration`: SIRD workflow and production boundary;
- `ocr-recognition`: computation, data, limits, field behavior, and security;
- `ocr-experiment`: experiment runner and evaluator;
- `ocr-verification`: verification, acceptance, corpus, metrics, and traceability;
- `ocr-operations`: runtime operations and runbooks.

The prototype remains the evidence source during migration. It is not deleted in this change. After OpenSpec validation and traceability reconciliation, a separate archive task may remove or mark the migrated prototype documents.

The target performance input is p99 OCR latency below 30 seconds for the production track, not a release gate for the first local version. OCR is designed to scale as independent stateless replicas, but the MVP runs as one bounded local deployment. SIRD owns task state, workflow delivery, and document artifacts. The MVP supports the old SNILS card, ADI-REG 2019, and ADI-REG 2023.

## First-version boundary

The first version is a local, private deployment for a trusted SIRD backend. It does not expose a public Task/Process API and does not require SPIFFE/SPIRE, Kubernetes identity issuance, service-mesh integration, RabbitMQ production workload identity, an OS-level decoder sandbox, a protected production corpus, or a numeric p99 release gate.

The first version still requires the controls that prevent accidental data exposure and unbounded work:

- task-bound opaque artifact references with audience, expiry, checksum, media, and size validation;
- bounded decoding and model loading from an explicit local allowlist;
- no arbitrary URL/path or network access from OCR input;
- structured logs without document bytes, personal values, credentials, or capability tokens;
- scratch cleanup on every terminal path and bounded result retention;
- trusted-backend-only workflow access on loopback or a private Docker network;
- RabbitMQ TLS and fail-closed route authorization in the target Compose workflow.

Docker Compose is the first integrated release gate. Helm/Kubernetes, multi-node RabbitMQ availability, production workload identity and broker authorization, protected-corpus quality thresholds, and production p99 gates are deferred. The current Kafka TLS/ACL profile remains migration baseline evidence until RabbitMQ runtime migration is verified; it is not the selected target or production identity evidence.

## Goals / Non-Goals

**Goals:**

- Move every normative prototype requirement, data rule, architecture boundary, verification oracle, and operational rule into OpenSpec deltas.
- Preserve stable source IDs such as `FR-OCR-*`, `FR-EXP-*`, `NFR-OCR-*`, `SEC-OCR-*`, `CON-OCR-*`, `TEST-OCR-*`, `VER-OCR-*`, `AC-OCR-*`, and runbook IDs through a traceability map.
- Keep client-facing processing asynchronous while keeping the internal OCR call unary and bounded.
- Let the OCR facade classify the three MVP SNILS forms without requiring caller selectors.
- Preserve readable fields, field provenance, negative validation, and machine diagnostics without guessing.
- Make artifact authorization, idempotency, attempt ownership, retry taxonomy, deadline, redelivery, result publication, bounded local service access, and safe cleanup executable.
- Keep test and experimental dependencies out of the production image.

**Non-Goals:**

- Treating Python project initialization as completion of OCR stages, model adapters, or container images.
- Selecting exact OCR model weights before experiment and calibration evidence exists.
- Exposing `Prepare`, `Probe`, or `ExecuteProfile` as separate production RPCs.
- Establishing document authenticity, ownership, or a business decision to accept a document.
- Defining human-facing error text.
- Deleting prototype documents before migration traceability and validation are complete.

## Decisions

### 1. Treat OpenSpec as the normative migration target

The OpenSpec deltas become the implementation source. The prototype documents remain read-only migration evidence until all source IDs are mapped. Any conflict is resolved explicitly in the OpenSpec design/spec and recorded as a migration decision; it is not silently dropped.

### 2. Preserve the prototype computation model

The computation path remains `Prepare` → `Probe` → form resolution → geometry/quality/preprocessing → OCR observation → field extraction/correction/validation. The internal stage contracts remain transport-neutral, stateless with respect to SIRD, bounded by explicit policies, and provenance-preserving.

### 3. Use one production unary gRPC facade

`Recognize` is the only production RPC. It invokes the migrated internal stages in one bounded request. Process Service owns task state, result publication, and total attempts. OCR owns computation and no durable task lifecycle.

### 4. Classify the MVP document form inside OCR

The classifier resolves one of `snils_card`, `adi_reg_2019`, or `adi_reg_2023`. Caller selectors are absent from the MVP request; unknown selector fields are rejected. Missing/invalid calibration is `INVALID_CONFIGURATION`. A tie or score below the configured calibrated threshold is `FormResolution=ambiguous`. Completed no-evidence is `unresolved` or `unsupported` according to the source evidence; incomplete analysis is technical, not a subject rejection. No profile runs unless exactly one candidate and one supported form resolve.

### 5. Separate technical status from result completeness

The prototype meaning of `operation_status` is preserved:

- `ok`: the operation completed by its contract, including a completed subject rejection;
- `partial`: preparation or execution itself completed only partially;
- `failed`, `cancelled`, `limit_exceeded`: technical non-success.

The SIRD result adds `task_outcome` and `result_completeness`. A resolved form with one unreadable field is `operation_status=ok`, `task_outcome=completed`, `result_completeness=partial`; it is not a transport failure. Unreadable, absent, conflicting, and not-processed fields retain their distinct prototype states.

### 6. Define one authoritative subject/outcome mapping

Completed `target_not_detected`, `form_ambiguous`, `form_unsupported`, `form_unresolved`, and `multiple_candidates` are `operation_status=ok`, `task_outcome=subject_rejected`, `result_completeness=none`, no profile result, and no retry. Technical interruption before a subject conclusion uses the matching technical status and retry matrix. The complete table is in the integration spec and is frozen into the Protobuf/task contract.

### 7. Define one authoritative retry owner and RabbitMQ delivery contract

Process Service stores one total attempt counter per task/request. The MVP uses three total OCR attempts, a 35-second gRPC deadline per attempt, and one/two-second backoff. RabbitMQ 4.3 durable quorum queues carry task, result, retry, and terminal-failure routes through `aio-pika`; messages use stable identities and explicit routing. Publisher confirms and mandatory/equivalent unroutable checks are required. Consumers use bounded prefetch and manual acknowledgements only after durable PostgreSQL state and idempotency effects. RabbitMQ redelivery resumes the same counter and never starts a fresh budget. At-least-once dead-letter transfer is required for terminal routes; it is a recovery path, not an infinite replay loop. The current Kafka implementation remains migration baseline evidence until this target runtime is verified.

### 8. Bind artifact authorization to the task

`artifact_ref` is a typed scoped reference issued by SIRD for the intended task/request and service audience. It carries or resolves checksum, media metadata, expiry, and authorization binding. OCR rejects malformed, stale, cross-task, wrong-audience, mismatched, or checksum-invalid references and never follows paths or URLs found in OCR text.

### 9. Preserve field evidence and no-guessing behavior

The field contract retains raw value, normalized value, status, candidates, corrections, validations, confidence scale, evidence, and issues. Readable fields survive an unreadable field. Formal validation is evidence, not permission to invent a replacement. UI text is outside OCR; consumers translate machine codes.

### 10. Separate runtimes

Production contains only the OCR runtime and allowlisted local dependencies. Litestar + Granian remain test-only. Experiment runner/evaluator, corpus manifests, and protected reference access are separate and excluded from production.

## Migration inventory and mapping

| Prototype source | OpenSpec target | Migration result |
|---|---|---|
| `product/PRD.md`, use cases, acceptance criteria | `ocr-recognition`, `sird-ocr-integration`, `ocr-verification` | Product scope, workflows, acceptance invariants |
| `requirements/SRS.md`, quality attributes, traceability | `ocr-recognition`, `ocr-verification` | Functional, NFR, security, domain, and source-ID mapping |
| `architecture/system-architecture.md`, interfaces, data, security, views, ADRs | `ocr-recognition`, `sird-ocr-integration`, `ocr-operations` | Components, data lineage, boundaries, threat controls |
| `verification/test-plan.md`, cases, data, metrics, architecture tests | `ocr-verification` | Oracles, corpus independence, metrics, acceptance |
| `verification/experiment-protocol.md`, experiment contract | `ocr-experiment` | Plan, variants, records, evaluator, selection rules |
| `operations/deployment.md`, observability, runbooks | `ocr-operations` | Packaging, startup/update, telemetry, rollback, incident response |
| `glossary.md` | traceability and contract vocabulary | Terminology reconciliation |

The migration MUST retain the source identifier and link to an OpenSpec requirement or task. Prototype statements that describe the old caller-selected form flow are superseded only for the MVP `Recognize` facade; the internal `ExecuteProfile` stage remains available to the computation model.

## Risks / Trade-offs

- **[Migration omission]** A source file may be missed. → Inventory every prototype section, require source-ID mapping, and block archive until the reconciliation report is complete.
- **[Classifier false negative]** Strict resolution rejects borderline documents. → Preserve evidence and request a new capture; never guess a profile.
- **[Partial result misuse]** A consumer may treat partial fields as complete. → Separate operation status from result completeness and emit field status for every target field.
- **[Retry amplification]** RabbitMQ redelivery may repeat work before acknowledgement. → Store one authoritative counter, commit durable state before acknowledgement, and test crash/redelivery windows.
- **[Artifact confused deputy]** A valid object reference may be reused for another task. → Bind and validate task, audience, expiry, metadata, and checksum.
- **[Latency budget]** p99 OCR under 30 seconds does not prove end-to-end task latency. Keep the 35-second per-attempt deadline and bounded retries in the MVP; defer numeric p99 and end-to-end SLO gates until a production workload and corpus exist.
- **[Packaging leakage]** Test or experiment dependencies enter production. → Validate production dependency and image boundaries.

## Migration Plan

1. Inventory all prototype documents and stable IDs; create a source-to-OpenSpec traceability matrix.
2. Migrate product scope, use cases, SRS functional/NFR/security/domain rules, and glossary.
3. Migrate computation architecture, data model/lifecycle, interfaces, component/view boundaries, and proposed ADR decisions.
4. Migrate production SIRD integration and apply the explicit MVP classifier/partial-result decisions.
5. Migrate experiment contract, protocol, corpus rules, metrics, test cases, test plan, architecture checks, and acceptance criteria.
6. Migrate deployment, observability, and both operational runbooks.
7. Review for contradictions, validate all OpenSpec artifacts, and verify that every source ID has an owner and oracle.
8. Only after reconciliation, archive or remove superseded prototype documents in a separately authorized cleanup step.

Rollback retains the prototype evidence. Local implementation lives in the current repository, as selected by the owner; deployment, production migration, and data backfill require separate authorization.

## Deployment Inputs

Environment-specific certificate issuance, RustFS endpoint/credential binding, RabbitMQ host/port/vhost, exchange/queue/routing-key names, PostgreSQL connection details, model versions, and calibrated numeric thresholds are implementation inputs. They cannot change the selected RabbitMQ workflow, no-guessing rules, source traceability, or unary OCR boundary.

The repository provides a current local integration profile in `compose.integration.yml`. It runs Apache Kafka 4.3.1 in single-node KRaft mode, PostgreSQL 17, and RustFS 1.0.0. This Kafka profile is retained as migration baseline evidence only. The first release target is a RabbitMQ `4.3-management` Docker Compose profile with TLS; its route declarations, durable quorum queues, publisher confirms, manual acknowledgements, bounded retry, at-least-once terminal transfer, and safe metadata checks must be verified before claiming runtime migration. Published ports bind to loopback; local credentials and certificates are not production inputs. Helm/Kubernetes and production-scale evidence remain deferred.

RabbitMQ routes terminal failures through configured dead-letter policies with at-least-once transfer and duplicate-safe recovery. Process Service records terminal state and outbox identity in PostgreSQL before acknowledgement; publisher confirms and mandatory/equivalent returned-message handling protect publication. The Kafka offset/dead-letter behavior remains current implementation evidence until the RabbitMQ migration is verified.

## Implementation location

The owner selected the current repository root for Python implementation. `uv init --bare` creates `pyproject.toml` without demonstration code or a service stub. The root project is named `sird-recognition`; production, test, and experiment dependencies must still follow the declared runtime boundaries. Project initialization does not close tasks 3–6 or demonstrate model compatibility, recognition quality, or latency.

The owner confirmed that Task Service and Process Service belong in this repository as a separate integration package. The OCR module boundary is unchanged: `sird_recognition` owns stateless recognition and must not import the workflow package or require broker/PostgreSQL dependencies. The integration package owns task state, RabbitMQ delivery, PostgreSQL transactions, attempts, and result publication. Its dependencies and deployable artifact must be separate from the production OCR artifact. The current Kafka integration is migration baseline evidence, not the selected target. Prototype statements excluding durable SIRD workflow from the OCR module apply to that module, not to the repository as a whole.

Task/Process APIs serve only the authorized SIRD backend. In the first version this means a trusted caller on loopback or a private Docker network; the adapter MUST NOT treat a user-supplied `caller_identity` as transport authentication. SIRD owns end-user authorization; knowledge of a task identifier never grants access. SPIFFE/SPIRE workload identities, trust bundles, renewal, explicit production identity-to-role authorization, and RabbitMQ broker authorization are production deployment inputs deferred until the SIRD deployment and team identity architecture exist.

SIRD supplies result retention policy. When it supplies none, stored results and integration-owned result artifacts use a 12-hour default. Diagnostic retention remains opt-in; the fallback neither grants diagnostic access nor changes ownership or deletion authority for SIRD originals.
