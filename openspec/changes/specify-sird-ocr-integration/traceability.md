# Prototype to OpenSpec Traceability

This migration ledger keeps the prototype as evidence until every row has an OpenSpec capability owner, migration task, and verification oracle. It is part of the change plan, not an implementation artifact. The ledger maps source files and stable IDs to capability areas and tasks; final one-to-one requirement links are closed by task 7.3.

| Prototype source | Stable IDs or scope | OpenSpec capability | Migration task / oracle |
|---|---|---|---|
| `product/PRD.md` | `PRD-OCR-001..003`, scope and boundaries | `ocr-recognition`, `sird-ocr-integration` | tasks 2.1–2.7, 3.1–3.5 |
| `product/use-cases/` | `UC-OCR-001..002` | `sird-ocr-integration`, `ocr-experiment` | tasks 3.1–3.5, 5.3 |
| `product/acceptance-criteria/` | `AC-OCR-001..003` | `ocr-verification` | tasks 6.4–6.6 |
| `requirements/SRS.md` | `FR-OCR-001..016`, `FR-EXP-001..005`, `NFR-OCR-001..004`, `SEC-OCR-001..004`, `CON-OCR-001` | `ocr-recognition`, `ocr-experiment`, `ocr-operations` | tasks 2.1–2.7, 5.3–5.6, 6.1–6.4 |
| `requirements/quality-attributes.md` | quality and refusal invariants | `ocr-recognition`, `ocr-verification` | tasks 2.4–2.6, 6.1–6.3 |
| `requirements/traceability.md` | existing requirement-to-test links | this ledger plus `ocr-verification` | tasks 1.2–1.4, 7.3 |
| `architecture/system-architecture.md` | computation stages and boundaries | `ocr-recognition` | tasks 2.1–2.5, 5.1 |
| `architecture/interfaces/` | module API, experiment API, internal ports, external systems | `sird-ocr-integration`, `ocr-recognition`, `ocr-experiment` | tasks 3.1–3.5, 5.3 |
| `architecture/data/` | data model and lifecycle | `ocr-recognition`, `sird-ocr-integration` | tasks 2.3–2.6, 3.3 |
| `architecture/security/` | trust boundaries, threats, controls | `ocr-recognition`, `ocr-operations`, `sird-ocr-integration` | tasks 3.3–3.4, 4.6, 7.1 |
| `architecture/views/` | component, context, container, flow, deployment views | `ocr-recognition`, `sird-ocr-integration`, `ocr-operations` | tasks 2.2–2.5, 3.1, 5.1–5.2 |
| `architecture/adr/` | proposed architecture decisions | `design.md`, integration/recognition specs | tasks 1.3, 3.1–3.5, 7.1 |
| `verification/test-cases.md` | `TEST-OCR-001..025` | `ocr-verification` | tasks 6.1, 6.5 |
| `verification/architecture-tests.md` | `VER-OCR-ARC-001..006` | `ocr-verification` | task 6.1 |
| `verification/test-plan.md` | test levels, risks, pass/block rules, responsibilities | `ocr-verification` | tasks 6.1–6.6 |
| `verification/test-data.md` | corpus units, strata, truth isolation, provenance | `ocr-verification` | task 6.2 |
| `verification/metrics.md` | exact-field, refusal, CER, form, cost, confidence, uncertainty rules | `ocr-experiment`, `ocr-verification` | tasks 5.3, 6.3, 6.6 |
| `verification/experiment-protocol.md` | experiment matrix, hard constraints, selection, reproducibility | `ocr-experiment` | task 5.3 |
| `verification/acceptance-tests.md` | acceptance execution | `ocr-verification` | task 6.4 |
| `operations/deployment.md` | packaging, startup, resources, update, rollback | `ocr-operations` | tasks 5.2, 5.4, 7.2 |
| `operations/observability.md` | stage events, safe telemetry, diagnostics | `ocr-operations` | task 5.5 |
| `operations/runbooks/` | `RB-OCR-001`, `RB-OCR-002` | `ocr-operations` | task 5.6 |
| `glossary.md` | shared vocabulary | all capability specs | tasks 1.2, 3.4, 7.3 |

## First-version scope decision

The first version is a local private deployment for a trusted SIRD backend. Its mandatory controls are task-bound artifact authorization, checksum/media/size validation, bounded decoding and model allowlists, safe logs, scratch cleanup, bounded retries, RabbitMQ TLS and fail-closed route authorization in the target Docker Compose profile. Docker Compose is the first integrated release gate. The current Kafka TLS/ACL profile remains migration baseline evidence until RabbitMQ runtime migration is verified and is not evidence of the selected target or production identity.

SPIFFE/SPIRE issuance and renewal, trust-bundle distribution, RabbitMQ workload identity and broker authorization, production ACL operations, service mesh, Helm/Kubernetes deployment, an OS-level decoder sandbox, protected production reference data, protected-corpus quality acceptance, and numeric p99 gates are production backlog items. They remain blocked, deferred, or not-run until the SIRD deployment, workload, corpus, identity decisions, and representative workload exist.

## Explicit migration decisions

1. The production `Recognize` facade classifies the MVP form internally; the prototype caller-selected form/profile flow remains only as an internal stage contract and is marked superseded for production integration.

2. Prototype technical `operation_status` semantics remain authoritative. SIRD adds task outcome and result completeness instead of changing the meaning of technical `ok`.
3. Subject outcomes are terminal and non-retryable only after analysis completes. Technical interruption remains technical and follows the retry matrix.
4. Process Service owns one shared attempt budget across gRPC calls and RabbitMQ consumer redelivery; durable PostgreSQL state precedes consumer acknowledgement.
5. Prototype documents are not deleted by this change. Archive requires a complete ledger, strict OpenSpec validation, applicable FADD checks, and explicit owner approval.
6. RabbitMQ 4.3 durable quorum queues, `aio-pika`, publisher confirms, explicit unroutable handling, manual acknowledgement after durable state, and at-least-once terminal transfer are the selected target contract. The current Kafka profile and its offsets/topics remain migration history and implementation baseline until the RabbitMQ runtime migration passes. `ADR-OCR-005` remains frozen migration evidence in its original form.
7. The owner placed Task/Process implementation in a separate integration package in this repository and selected backend-only access with a local private deployment boundary. SIRD result retention uses a 12-hour fallback. None of these decisions changes the broker-independent OCR module boundary.
8. SPIFFE identity verification, trust-bundle renewal, and RabbitMQ broker authorization are production deployment decisions deferred until SIRD deployment and team identity architecture exist. The current local Kafka TLS/ACL controls remain baseline evidence only.

## Gate status evidence

The migration planning gate was executed on 2026-09-20:

- `openspec validate specify-sird-ocr-integration --strict`: pass.
- `node tools/harness/checks/run-all.mjs`: pass; deterministic result is recorded in `artifacts/logs/deterministic-run.log`.
- Security preflight and JavaScript syntax checks: pass.
- Python quality and container checks: `not-configured` advisory status.
- Architecture validation: `not-configured` advisory status with `architecture-policy-unconfigured`.
- Repository garbage collection: 4,385 low-severity findings, primarily duplicate blocks; `--fail-on none` was used and no finding was suppressed.

The remaining non-complete gates are either deferred production work, implementation-dependent evidence, independent review, reconciliation, or human archive approval. Deferred production work is marked `[~]` in `tasks.md`; it is not passed.

### Re-executed evidence on 2026-09-21

- Strict architecture validation: pass; 6 components, 6 views, 8 DFD elements, 9 flows, and 9 threats.
- Archify validation: 9/9 checks pass; automated browser visual-check passes at all configured viewports and light/dark captures. Human perceptual review remains pending.
- Repository garbage collection: 6,159 unaccepted findings (`6,157` low-severity duplicate blocks and `2` medium large-file findings); `--fail-on none` was used. Generated Archify HTML is excluded from the GC walk; no product-code or threat-model finding was accepted.

### Re-executed after owner-authorized FADD exclusion scope

- GC policy now excludes repository harness/profile content: `.omp/**`, `.claude/**`, `.fadd/**`, `tools/**`, `agents/**`, `skills/**`, `.github/**`, and FADD root metadata.
- GC inventory is 1,872 unaccepted findings (`1,870` low-severity duplicate blocks and `2` medium large-file findings). Application and security evidence remain in scope; no baseline fingerprints were accepted.

## Evidence ownership and oracle index

The following index assigns one evidence owner and one primary oracle to every stable identifier carried from the prototype. Until the implementation and executable verification tasks run, the evidence state is `not-run`; OpenSpec validation is not behavioral evidence.

| Identifier set | Evidence owner | Primary oracle | State |
|---|---|---|---|
| `FR-OCR-001`, `FR-OCR-002`, `FR-OCR-003`, `FR-OCR-004`, `FR-OCR-005`, `FR-OCR-006`, `FR-OCR-007`, `FR-OCR-008`, `FR-OCR-009`, `FR-OCR-010`, `FR-OCR-011`, `FR-OCR-012`, `FR-OCR-013`, `FR-OCR-014`, `FR-OCR-015`, `FR-OCR-016` | Recognition owner | `TEST-OCR-001` through `TEST-OCR-018`, mapped in `ocr-verification` | not-run |
| `FR-EXP-001`, `FR-EXP-002`, `FR-EXP-003`, `FR-EXP-004`, `FR-EXP-005` | Experiment owner | `TEST-OCR-019`, `TEST-OCR-020`, `TEST-OCR-022`, `TEST-OCR-023`, `TEST-OCR-024` | not-run |
| `NFR-OCR-001`, `NFR-OCR-002`, `NFR-OCR-003`, `NFR-OCR-004` | Recognition and experiment owners | `TEST-OCR-010`, `TEST-OCR-017`, `TEST-OCR-019`, `TEST-OCR-020`, `TEST-OCR-023`, `TEST-OCR-025` | not-run |
| `SEC-OCR-001`, `SEC-OCR-002`, `SEC-OCR-003`, `SEC-OCR-004` | Security owner | `TEST-OCR-002`, `TEST-OCR-017`, `TEST-OCR-021`, `TEST-OCR-022` plus security review | not-run |
| `CON-OCR-001` | Recognition owner | `TEST-OCR-024` and CPU resource oracle | not-run |
| `TEST-OCR-001`, `TEST-OCR-002`, `TEST-OCR-003`, `TEST-OCR-004`, `TEST-OCR-005`, `TEST-OCR-006`, `TEST-OCR-007`, `TEST-OCR-008`, `TEST-OCR-009`, `TEST-OCR-010`, `TEST-OCR-011`, `TEST-OCR-012`, `TEST-OCR-013`, `TEST-OCR-014`, `TEST-OCR-015`, `TEST-OCR-016`, `TEST-OCR-017`, `TEST-OCR-018`, `TEST-OCR-019`, `TEST-OCR-020`, `TEST-OCR-021`, `TEST-OCR-022`, `TEST-OCR-023`, `TEST-OCR-024`, `TEST-OCR-025` | Verification owner | Focused executable contract and integration suite | not-run |
| `VER-OCR-ARC-001`, `VER-OCR-ARC-002`, `VER-OCR-ARC-003`, `VER-OCR-ARC-004`, `VER-OCR-ARC-005`, `VER-OCR-ARC-006` | Architecture and verification owners | Architecture boundary suite and dependency/provenance checks | not-run |
| `AC-OCR-001` | Verification owner and human owner | Local contract/component/integration suite without protected corpus or numeric quality threshold | blocked; MVP slice partially executable, missing ID-specific oracles |
| `AC-OCR-002`, `AC-OCR-003` | Verification owner and human owner | Protected-corpus quality and experiment/replay evidence | blocked; production backlog |
| `ARC-OCR-MODULE`, `ARC-OCR-COMPONENTS`, `ARC-OCR-CONTAINERS`, `ARC-OCR-CONTEXT`, `ARC-OCR-FLOWS`, `ARC-OCR-DEPLOYMENT`, `ARC-OCR-PREPARE`, `ARC-OCR-PROBE`, `ARC-OCR-GEOMETRY`, `ARC-OCR-QUALITY`, `ARC-OCR-READER`, `ARC-OCR-CORRECTION`, `ARC-OCR-FIELDS`, `ARC-OCR-RUNTIME`, `ARC-OCR-EXPERIMENT`, `ARC-OCR-EVALUATOR` | Architecture owner | Architecture reconciliation and `VER-OCR-ARC-001..006` | not-run |
| `API-OCR-MODULE`, `API-OCR-STAGES`, `API-OCR-DEPENDENCIES`, `DATA-OCR-MODEL` | Contract and data owners | Protobuf/schema compatibility and contract suite | not-run |
| `OPS-OCR-DEPLOYMENT`, `OPS-OCR-OBSERVABILITY`, `RB-OCR-001`, `RB-OCR-002` | Operations owner | Startup/update/rollback and bounded recovery checks | not-run |
| `VER-OCR-METRICS` | Experiment and verification owners | Independent metric recomputation and grouped uncertainty oracle | not-run |
| `ADR-OCR-001`, `ADR-OCR-002`, `ADR-OCR-003`, `ADR-OCR-004`, `ADR-OCR-005` | Architecture owner and human owner | Architecture review with code-to-documentation reconciliation | not-run |


### Owner decision: Alpha release

- The owner approved the first Alpha release on the Docker Compose RabbitMQ profile.
- Alpha requires RabbitMQ TLS/quorum routes, task-bound artifact controls, bounded decoder/model controls, safe metadata, available cleanup evidence, local workflow tests, and the observed broker transport smoke.
- Helm/Kubernetes, multi-node RabbitMQ recovery, production workload identity and broker authorization, protected-corpus acceptance, representative production workload, and numeric p99 remain post-Alpha backlog.
- Tasks `4.6`, `6.4`, `6.6`, and `7.4` are closed for the Alpha scope. Their post-Alpha work remains explicitly listed in the task text. Prototype and Kafka migration evidence remains retained; archive/removal is not part of Alpha.
- Tasks `3.2` and `3.4` in `add-gliner-decision-stage` are closed for the Alpha scope. Hard model isolation/interrupt enforcement and runtime-owned optional-stage telemetry remain post-Alpha backlog.

This is an owner-approved release boundary. It does not claim production readiness, protected-corpus quality, multi-node availability, or production latency.

## Current implementation evidence

- `src/sird_recognition/codes.py` mirrors wire status/reason classes, including fail-closed gRPC statuses.
- `src/sird_recognition/retry.py` implements the fixed technical-code and gRPC-status retry mapping.
- `src/sird_recognition/contracts/stages.py` and `contracts/ports.py` define explicit transport-neutral stage records, typed six-state field results, and typed resolved/ambiguous/unsupported/unresolved form decisions.
- `tests/test_adapter.py` exercises the test-only Litestar adapter; Granian remains a test/development dependency and is excluded from production dependencies.
- `tests/test_retry.py` covers every technical and gRPC mapping branch, including unspecified/permanent reason classes and unknown statuses.
- `tests/test_contracts.py`, `tests/test_runtime.py`, `tests/test_runtime_mappings.py`, and `tests/test_field_results.py` cover typed form decisions, all six field states, conservative completeness, selector rejection, partial preservation, and technical mappings.
- `tests/test_decoder_security.py` covers fail-closed decoder allow-list, compressed/output bounds, forbidden access flags, and sanitized decoder failure.
- `compose.integration.yml` provides RabbitMQ 4.3-management with AMQPS TLS, PostgreSQL 17, and RustFS 1.0.0. RabbitMQ exposes the local TLS listener and the selected durable quorum routes; Helm/Kubernetes and multi-node availability remain deferred.
- `integration/start.sh` generates or validates local RabbitMQ TLS material, starts the Compose profile, waits for healthy services, and configures the local `/sird` user permissions. It is a local Compose control, not production workload identity evidence.
- `integration/src/sird_workflow/mtls.py` validates the RabbitMQ CA/client certificate/private-key material and emits TLS-only client settings; it does not claim SPIFFE/SPIRE issuance.
- `integration/src/sird_workflow/consumer.py` uses bounded prefetch, manual acknowledgement, redelivery-safe handling, durable outbox gating, and terminal acknowledgement ordering. These behaviors have focused tests; full Process Service deployment remains a Compose acceptance item.

- Current local suites observed 121 root tests and 89 integration tests passing. The Tesseract live smoke recognized the generated digit sequence with word regions and scores; adapter tests cover TSV parsing, paragraph line preservation, timeout mapping, first-reader ordering, unavailable-only fallback, execution failure, chain deadline exhaustion, and explicit project-local Tesseract factory order.
- `src/sird_recognition/snils_recognition.py` now provides a bounded local SNILS image pipeline: byte/pixel limits, quadrilateral perspective correction, glare repair, grayscale/threshold variants, local Tesseract observations, strict SNILS checksum validation, and explicit refusal diagnostics for malformed, unreadable, invalid, or conflicting evidence. Optional full name and birth date are returned only when uniquely observed.
- `test_app/src/sird_test_app/local_snils.py` exposes a runnable local `app` backed by system Tesseract and `rus+eng` trained data. `POST /snils/recognize` accepts JPEG, PNG, WebP, or TIFF multipart uploads, returns `200` with verified fields, `422` with an explicit refusal, and rejects invalid upload boundaries before OCR. `test_app/run-local.sh` pins the required ASGI interface. Focused route tests passed (7), and real local Tesseract upload smokes passed through both TestClient and the launched HTTP server for a straight image and a perspective-warped image.
- `ReaderAwareExecuteProfile` owns the declared `read` stage, loads each prepared page by its distinct `prepared_artifact` through an injected reader with an expected checksum, skips failed pages, validates adapter/model provenance, and passes observations to the delegate. The runtime does not construct or default to Tesseract. The existing repository contains no VLM implementation; a production VLM chain must be supplied explicitly by the application.
- Integration tests cover bounded OCR, caller-terminal cancellation, nonterminal revoke requeue without result publication or attempt-budget consumption, hostile client requeue sanitization, outbox gating, retention cleanup, TLS configuration, RabbitMQ publication/return handling, manual acknowledgement ordering, and `close()` cancellation. The Compose configuration fails closed when `RABBITMQ_PASSWORD` is absent and starts the RabbitMQ TLS profile when it is supplied. A separate local SPIRE Compose profile starts SPIRE Server 1.13.2 and an Agent, bootstraps an ephemeral local upstream CA, issues a workload X.509-SVID through the Workload API, and rejects an unregistered UID.
- These checks do not establish a full deployed Task/Process workflow, production model execution, OS-level decoder isolation, SPIFFE/SPIRE Kubernetes issuance/trust-bundle wiring/renewal, multi-node RabbitMQ recovery, protected-corpus accuracy, numeric p99 latency, or production retention/recovery evidence. The earlier local latency observation was not a p99 measurement. Production identity, broker authorization, Helm/Kubernetes deployment, production corpus, SPIRE Kubernetes deployment, and numeric latency gates remain unverified or blocked.
- The Alpha release scope is closed for tasks 4.6, 6.4, 6.6, and 7.4. RabbitMQ broker transport, local integration tests, and Docker Compose infrastructure evidence are recorded. Production identity, multi-node availability, protected-corpus acceptance, production p99, Helm/Kubernetes deployment, and archive/removal remain post-Alpha work.

## Independent review evidence

Independent architecture, security, traceability, and adversarial reviews were run against the planning artifacts and prototype evidence. The result is `pass-with-gaps` for architecture coherence, `disproved` for the earlier claim that the ownership/oracle index was complete, and `blocked` for adversarial executability. Findings are recorded here rather than treated as passed evidence.

Review findings and their current disposition:

1. Access authority: the owner selected trusted-SIRD-backend-only Task/Process APIs. SIRD owns end-user authorization. The integration service enforces an explicit caller allow-list; SPIFFE ID-to-role policy primitives are tested, while deployment SVID/trust-bundle and role wiring remain not-run.
2. Initial task state and RabbitMQ publication: one PostgreSQL transaction persists task, attempt, and task outbox state. The focused tests and AMQPS Compose smoke observed confirmed routed publication, mandatory unroutable handling, manual acknowledgement, and stable message identity. Full deployed Process Service consumption and end-to-end result publication remain part of the Compose acceptance report.
3. Attempt processing: PostgreSQL row-lock claims, shared three-attempt state, lease fencing, stale completion handling, terminal result outbox, and pending dead-letter outbox are covered by focused tests and a live terminal PostgreSQL smoke. Concurrent production rebalance evidence remains not-run.
4. Retention: the owner selected the SIRD policy with a 12-hour fallback for results and integration-owned result artifacts. Result reads hide expired payloads in the service implementation; expiry cleanup and publication recovery need runtime evidence.
5. Decoder isolation: signed capability validation and bounded size/media/checksum guards are implemented and tested. An explicit process/sandbox boundary remains not-run.
6. Workload identity: the owner selected SPIFFE/SPIRE for the deferred production track. Exact identity-to-role and credential-expiry policy primitives are implemented and tested; SPIRE issuance, trust bundles, renewal integration, and RabbitMQ production broker authorization remain deployment evidence. Local RabbitMQ credentials and TLS are Compose integration controls only.

The owner resolved the repository boundary: Task Service and Process Service will be implemented here in a separate integration package. The prototype exclusion of SIRD workflow applies to the OCR module, not to the repository. These decisions do not authorize production deployment.

## Ownership-index corrections

The following entries extend or override the coarse rows above:

| Source identifier | Evidence owner | Primary oracle | State |
|---|---|---|---|
| `PRD-OCR-001`, `PRD-OCR-002`, `PRD-OCR-003` | Product and human owners | `AC-OCR-001`, `AC-OCR-002`, `AC-OCR-003` respectively | not-run |
| `UC-OCR-001`, `UC-OCR-002` | Product and integration owners | End-to-end task workflow and experiment workflow scenarios; executable oracle is task 6.5 | not-run |
| `API-OCR-MODULE` | Contract owner | `TEST-OCR-001..019` contract suite and schema compatibility check | not-run |
| `API-OCR-STAGES` | Recognition owner | `VER-OCR-ARC-001..005` and focused stage-port contract checks | not-run |
| `API-OCR-DEPENDENCIES` | Security and runtime owners | Material authorization, model registry, network-denial, and package-boundary checks; tasks 4.6 and 6.5 | not-run |
| `API-OCR-EXPERIMENT` | Experiment owner | `TEST-OCR-019`, `TEST-OCR-020`, `TEST-OCR-022`, `TEST-OCR-023`, `TEST-OCR-024`, `TEST-OCR-025` | not-run |
| `DATA-OCR-MODEL` | Data and recognition owners | Provenance/field-state checks in `TEST-OCR-006..015` and `VER-OCR-ARC-002..003` | not-run |
| `DATA-OCR-LIFECYCLE` | Data and operations owners | Material cleanup, handoff-expiry, crash-recovery, and cache checks; tasks 4.5, 4.6, and 6.5 | not-run |
| `SEC-OCR-ARCHITECTURE` | Security owner | `TEST-OCR-021`, `TEST-OCR-022`, and security review | not-run |
| `SEC-OCR-THREATS` | Security owner | Threat-control checks in `TEST-OCR-002`, `TEST-OCR-013`, `TEST-OCR-017`, `TEST-OCR-021`, and `TEST-OCR-022` | not-run |
| `VER-OCR-ACCEPTANCE`, `VER-OCR-ARCHITECTURE`, `VER-OCR-EXPERIMENTS`, `VER-OCR-TEST-CASES`, `VER-OCR-DATA`, `VER-OCR-TEST-PLAN` | Verification owner | Corresponding `ocr-verification` requirements and acceptance runner | not-run |
| `DOC-OCR-OVERVIEW`, `DOC-OCR-GLOSSARY`, `DOC-OCR-ARCHITECTURE-OVERVIEW`, `DOC-OCR-VIEWS-OVERVIEW`, `DOC-OCR-SECURITY-OVERVIEW`, `DOC-OCR-INTERFACES-OVERVIEW`, `DOC-OCR-DATA-OVERVIEW`, `DOC-OCR-VERIFICATION-OVERVIEW`, `DOC-OCR-REQUIREMENTS-OVERVIEW`, `DOC-OCR-PRODUCT-OVERVIEW`, `DOC-OCR-USE-CASES-OVERVIEW`, `DOC-OCR-ACCEPTANCE-OVERVIEW`, `DOC-OCR-OPERATIONS-OVERVIEW`, `DOC-OCR-RUNBOOKS-OVERVIEW`, `DOC-OCR-ADR-OVERVIEW`, `DOC-OCR-PRD`, `DOC-OCR-SRS`, `DOC-OCR-TRACEABILITY` | Documentation and traceability owners | Document inventory, vocabulary review, and source-file reconciliation; no behavioral oracle for overview documents | not-run |
| `FR-EXP-001` | Experiment owner | `TEST-OCR-019` plus plan/mode/order/seed oracle from task 6.1 | not-run |
| `FR-EXP-002` | Experiment owner | `TEST-OCR-020` | not-run |
| `FR-EXP-003` | Experiment and security owners | `TEST-OCR-022` | not-run |
| `FR-EXP-004` | Experiment owner | `TEST-OCR-023` and selection/constraint checks in `TEST-OCR-025` | not-run |
| `FR-EXP-005` | Experiment and verification owners | `TEST-OCR-024` cost checks and quality/selection checks in `TEST-OCR-025` | not-run |
| `OPS-OCR-DEPLOYMENT` | Operations owner | Startup/readiness/resource/update/rollback checks in task 6.1 | not-run |
| `OPS-OCR-OBSERVABILITY` | Operations owner | Safe event, duration/resource scope, memory aggregation, cache, and redaction checks in task 6.1 | not-run |
| `RB-OCR-001` | Operations owner | Bounded limit-recovery scenario in task 6.1 | not-run |
| `RB-OCR-002` | Operations owner | Regression/reproducibility recovery scenario in task 6.1 | not-run |
| `AC-OCR-001` | Verification owner and human owner | Contract/component/integration suite; no corpus or numeric threshold is required by its prototype precondition | not-run |
| `AC-OCR-002` | Verification owner and human owner | Quality/resource suite; blocked until corpus and numeric boundaries exist | blocked |
| `AC-OCR-003` | Verification owner and human owner | Experiment/replay suite; blocked until corpus and numeric boundaries exist | blocked |

## Source-file reconciliation ledger

Every file under `docs/prototype` is listed below. Overview and glossary files are mapped as vocabulary/evidence sources; they do not receive a false behavioral pass.

| Prototype file | OpenSpec owner | Migration task | Primary oracle/state |
|---|---|---|---|
| `documentation-overview.md` | all capability specs | 1.1, 7.3 | document inventory / not-run |
| `glossary.md` | all capability specs | 1.2, 3.4, 7.3 | vocabulary reconciliation / not-run |
| `architecture/architecture-overview.md` | `ocr-recognition`, `sird-ocr-integration`, `ocr-operations` | 2.1–2.5, 3.1, 5.1–5.2 | architecture review / not-run |
| `architecture/system-architecture.md` (`ARC-OCR-MODULE`) | `ocr-recognition` | 2.1–2.5, 5.1 | `VER-OCR-ARC-001..005` / not-run |
| `architecture/adr/adr-overview.md` | design and integration specs | 1.3, 7.1 | ADR reconciliation / not-run |
| `architecture/adr/ADR-OCR-001-scope-and-dependencies.md` | `ocr-recognition`, `sird-ocr-integration` | 1.3, 3.3, 7.1 | `VER-OCR-ARC-001` / not-run |
| `architecture/adr/ADR-OCR-002-conditional-processing.md` | `ocr-recognition` | 1.3, 2.3–2.4, 6.1 | `TEST-OCR-006..009` / not-run |
| `architecture/adr/ADR-OCR-003-evidence-correction.md` | `ocr-recognition`, `ocr-verification` | 1.3, 2.4, 6.1, 6.3 | `TEST-OCR-012..015`, `CON-OCR-001` / not-run |
| `architecture/adr/ADR-OCR-004-reproducible-selection.md` | `ocr-experiment` | 1.3, 5.3, 6.1, 7.1 | `TEST-OCR-019`, `020`, `022–025` / not-run |
| `architecture/adr/ADR-OCR-005-sird-execution-model.md` | `sird-ocr-integration` | 1.3, 3.1–4.6, 7.1 | integration reliability review / blocked by findings |
| `architecture/views/architecture-views-overview.md` | `ocr-recognition`, `sird-ocr-integration`, `ocr-operations` | 2.2–2.5, 3.1, 5.1–5.2 | architecture model / not-run |
| `architecture/views/components.md` (`ARC-OCR-COMPONENTS`, component ARC IDs) | `ocr-recognition`, `ocr-experiment` | 2.1–2.5, 5.1, 5.3 | `VER-OCR-ARC-001..006` / not-run |
| `architecture/views/containers.md` (`ARC-OCR-CONTAINERS`) | `sird-ocr-integration`, `ocr-operations` | 3.1–3.5, 5.1–5.2 | deployment/package boundary / not-run |
| `architecture/views/context.md` (`ARC-OCR-CONTEXT`) | `sird-ocr-integration` | 3.1–3.5 | integration architecture review / not-run |
| `architecture/views/data-flows.md` (`ARC-OCR-FLOWS`) | `sird-ocr-integration`, `ocr-recognition` | 2.3, 3.1–4.5 | sequence/data-flow oracle / not-run |
| `architecture/views/deployment.md` (`ARC-OCR-DEPLOYMENT`) | `ocr-operations` | 5.1–5.2, 5.4, 7.1 | deployment isolation oracle / not-run |
| `architecture/security/security-architecture-overview.md` | `sird-ocr-integration`, `ocr-recognition`, `ocr-operations` | 3.3–3.4, 4.6, 7.1 | threat/security review / not-run |
| `architecture/security/security-architecture.md` (`SEC-OCR-ARCHITECTURE`) | `ocr-recognition`, `ocr-operations` | 3.3, 4.6, 6.5 | `TEST-OCR-002`, `017`, `021`, `022` / not-run |
| `architecture/security/threat-model.md` (`SEC-OCR-THREATS`) | `sird-ocr-integration`, `ocr-recognition`, `ocr-operations` | 3.3, 4.6, 6.5, 7.1 | threat-control suite / not-run |
| `architecture/interfaces/interfaces-overview.md` | all integration/runtime capability specs | 3.1–3.5, 5.1–5.3 | contract reconciliation / not-run |
| `architecture/interfaces/api.md` (`API-OCR-MODULE`) | `ocr-recognition` | 2.5, 3.1, 3.4 | module contract suite / not-run |
| `architecture/interfaces/experiment-contract.md` (`API-OCR-EXPERIMENT`) | `ocr-experiment` | 5.3, 6.1–6.3 | experiment contract suite / not-run |
| `architecture/interfaces/external-systems.md` (`API-OCR-DEPENDENCIES`) | `sird-ocr-integration`, `ocr-recognition`, `ocr-operations` | 3.3, 4.6, 5.1 | artifact/model/network boundary checks / not-run |
| `architecture/interfaces/internal-contracts.md` (`API-OCR-STAGES`) | `ocr-recognition` | 2.1–2.5, 3.5, 5.1 | stage-port contract suite / not-run |
| `architecture/data/data-architecture-overview.md` | `ocr-recognition`, `sird-ocr-integration` | 2.3–2.6, 3.3 | data architecture review / not-run |
| `architecture/data/data-lifecycle.md` (`DATA-OCR-LIFECYCLE`) | `ocr-recognition`, `sird-ocr-integration`, `ocr-operations` | 2.3, 3.3, 4.5–4.6, 5.6 | lifecycle/expiry/cleanup oracle / not-run |
| `architecture/data/data-model.md` (`DATA-OCR-MODEL`) | `ocr-recognition`, `sird-ocr-integration` | 2.3–2.6, 3.1–3.4 | provenance and field-state suite / not-run |
| `verification/verification-overview.md` | `ocr-verification` | 6.1–6.6 | verification plan review / not-run |
| `verification/test-cases.md` (`TEST-OCR-001..025`) | `ocr-verification` | 6.1, 6.5 | executable contract/integration suite / not-run |
| `verification/acceptance-tests.md` (`VER-OCR-ACCEPTANCE`) | `ocr-verification` | 6.4, 7.3 | acceptance runner / not-run |
| `verification/architecture-tests.md` (`VER-OCR-ARCHITECTURE`, `VER-OCR-ARC-001..006`) | `ocr-verification` | 6.1, 7.1 | architecture boundary suite / not-run |
| `verification/experiment-protocol.md` (`VER-OCR-EXPERIMENTS`) | `ocr-experiment`, `ocr-verification` | 5.3, 6.1–6.3 | independent experiment/replay suite / not-run |
| `verification/metrics.md` (`VER-OCR-METRICS`) | `ocr-experiment`, `ocr-verification` | 5.3, 6.3, 6.6 | metric recomputation and uncertainty oracle / not-run |
| `verification/test-data.md` (`VER-OCR-DATA`) | `ocr-experiment`, `ocr-verification` | 6.2–6.3 | corpus/provenance fixture suite / blocked |
| `verification/test-plan.md` (`VER-OCR-TEST-PLAN`) | `ocr-verification` | 6.1–6.6 | test-level and evidence policy / not-run |
| `requirements/requirements-overview.md` | `ocr-recognition`, `ocr-experiment` | 1.1–1.4, 2.1–2.7 | requirements inventory / not-run |
| `requirements/SRS.md` (`FR-OCR-*`, `FR-EXP-*`, `NFR-OCR-*`, `SEC-OCR-*`, `CON-OCR-001`) | `ocr-recognition`, `ocr-experiment`, `ocr-operations` | 2.1–2.7, 5.3–5.6 | stable-ID oracles listed above / not-run |
| `requirements/quality-attributes.md` | `ocr-recognition`, `ocr-verification` | 2.4–2.6, 6.1–6.3 | quality/refusal metric suite / not-run |
| `requirements/traceability.md` (`DOC-OCR-TRACEABILITY`) | traceability ledger and `ocr-verification` | 1.2–1.4, 7.3 | source-ID reconciliation / not-run |
| `product/product-overview.md` | `ocr-recognition`, `sird-ocr-integration` | 1.1, 2.1–2.7, 3.1–3.5 | product boundary review / not-run |
| `product/PRD.md` (`PRD-OCR-001..003`) | `ocr-recognition`, `sird-ocr-integration`, `ocr-experiment` | 2.1–2.7, 3.1–3.5, 5.3 | `AC-OCR-001..003` / not-run |
| `product/use-cases/use-cases-overview.md` | `sird-ocr-integration`, `ocr-experiment` | 1.1, 3.1–4.5, 5.3 | use-case workflow suite / not-run |
| `product/use-cases/UC-OCR-001-recognize.md` (`UC-OCR-001`) | `sird-ocr-integration` | 3.1–4.6, 6.5 | end-to-end task workflow / not-run |
| `product/use-cases/UC-OCR-002-compare.md` (`UC-OCR-002`) | `ocr-experiment` | 5.3, 6.1–6.4 | end-to-end experiment workflow / not-run |
| `product/acceptance-criteria/acceptance-criteria-overview.md` | `ocr-verification` | 6.4, 7.3 | acceptance coverage review / not-run |
| `product/acceptance-criteria/AC-OCR-001-contract.md` (`AC-OCR-001`) | `ocr-verification` | 6.1, 6.4–6.5 | contract/component/integration suite / not-run |
| `product/acceptance-criteria/AC-OCR-002-quality.md` (`AC-OCR-002`) | `ocr-verification` | 6.2–6.4, 6.6 | quality/resource acceptance / blocked |
| `product/acceptance-criteria/AC-OCR-003-experiments.md` (`AC-OCR-003`) | `ocr-experiment`, `ocr-verification` | 5.3, 6.2–6.4 | experiment/replay acceptance / blocked |
| `operations/operations-overview.md` | `ocr-operations` | 5.2, 5.4–5.6 | operations review / not-run |
| `operations/deployment.md` (`OPS-OCR-DEPLOYMENT`) | `ocr-operations` | 5.2, 5.4, 7.2 | startup/update/rollback suite / not-run |
| `operations/observability.md` (`OPS-OCR-OBSERVABILITY`) | `ocr-operations` | 5.5, 6.1 | safe telemetry/resource/redaction suite / not-run |
| `operations/runbooks/runbooks-overview.md` | `ocr-operations` | 5.6, 7.3 | runbook reconciliation / not-run |
| `operations/runbooks/RB-OCR-001-execution-limits.md` (`RB-OCR-001`) | `ocr-operations` | 5.6, 6.1 | bounded limit-recovery scenario / not-run |
| `operations/runbooks/RB-OCR-002-regression.md` (`RB-OCR-002`) | `ocr-operations` | 5.6, 6.1 | reproducibility/recovery scenario / not-run |

### Re-executed after DFD-backed STRIDE model

- `security/threat-model/dfd.json` is the machine-readable source of the reviewed data flows. `architecture/sird-ocr-dfd.architecture.json` is the English Archify DFD derived from the same elements, trust zones, and ten flows, including the explicit `task-to-sird` status/result response.
- Archify DFD validation passes 9/9. The delivered artifact is `architecture/rendered/sird-ocr-dfd.html` with SHA-256 `f239f93633dc2081be85a1edbadf1ba434c0ac97a0eab9583c74509a9e2ad526`; automated browser visual-check passes at all configured viewports and light/dark captures. Human perceptual review remains pending.
- `security/threat-model/adversary-model.json` defines five attacker profiles, protected assets, attacker capabilities, non-capabilities, goals, assumptions, and exclusions. The STRIDE catalog contains 62 explicit threats with controls, verification paths, owners, statuses, attacker references, and primary DFD subjects; cross-boundary controls use explicit `relatedSubjects`.
- `security/threat-model/stride-coverage.json` covers 18 DFD subjects and 108 STRIDE cells: 89 concrete threat dispositions and 19 subject-specific not-applicable dispositions. No `TM-UNREVIEWED` or generic catch-all reference remains, and the PostgreSQL denial-of-service and RustFS privilege-boundary cells are concrete rather than contradictory N/A entries.
- Strict architecture validation passes with 6 components, 6 views, 8 DFD elements, 10 flows, and 62 threats. Production SPIRE issuance, trust-bundle distribution, RabbitMQ broker authorization, decoder isolation, broker redelivery fencing, retention cleanup, ingress/operator audit, corpus acceptance, and numeric quality evidence remain open rather than being marked passed. Kafka ACL mapping is current-baseline evidence only.

### Re-executed after Python GC metric and application-code scope

- `tools/gc/policy.json` excludes `docs/**`, machine-generated lockfiles (`uv.lock`, `bun.lock`), FADD internals, and generated Archify output from the application-code inventory. Markdown files outside `docs/**` remain eligible for general `large-file` and `todo-density` checks.
- The line-window `duplicate-block` heuristic was replaced with `python-clone`: Python tokenization drops comments/docstrings/NL tokens, canonicalizes ordinary identifiers and literals, preserves attribute/callee names, and hashes six-statement/50-token shingles. Overlapping shingles are coalesced into one clone class.
- Production scope follows `quality/python-policy.json` (`src`, `integration/src`, `verification/src`, `experiment/src`); test paths are measured separately and report-only. Clone fingerprints use the existing `quality/baseline.json` acceptance mechanism; no new duplication policy fields or baseline entries were added.
- Focused detector regression checks and GC canary pass. Final GC inventory reports 2 unaccepted findings: one low production `python-clone` clone class and one medium `large-file` finding for `integration/src/sird_workflow/process.py`. Production ratio is 0.1979%; tests are 3.1922% report-only; repository ratio is 1.2702%. Inventory counts include duplicated and total Python lines for each scope.
- Known blind spots are same-file clones, sub-threshold clones, and semantic near-clones. Attribute and callee names remain literal to reduce false positives. The repeated six-copy `_require_text` helper is below the six-statement/50-token threshold and is intentionally unreported.

### Acceptance execution evidence

- On 2026-09-24, `uv run --project verification --group dev pytest verification/tests` passed 25 focused contract, corpus, metric, and architecture-oracle tests. This is local injected-fixture evidence, not AC-OCR-001 completion.
- On 2026-09-24, `uv run --project experiment --group dev pytest experiment/tests` passed 6 experiment-runner and evaluator tests. This is not AC-OCR-003 replay evidence because no protected corpus, model outputs, or independent full run were available.
- On 2026-09-27, the stable-ID acceptance runner executed four registered oracles and wrote one row for every `TEST-OCR-001..025` to `artifacts/acceptance/report.json`; four rows are `passed` and 21 remain `blocked` because no ID-specific executable oracle is registered. AC-OCR-001 gates `TEST-OCR-001..018` and `021` only and remains `blocked`; experiment IDs `019`, `020`, and `022..025` belong to AC-OCR-003, which remains hard-blocked pending protected replay evidence. The full verification suite passed 30 tests, but injected-fixture checks do not replace the missing ID-specific acceptance scenarios.
- AC-OCR-002 and AC-OCR-003 remain `blocked`; production acceptance execution is deferred to the backlog because the protected corpus, fixed numeric boundaries, production model/profile, and independent evaluation inputs are unavailable.
- Task 6.6 remains `blocked` and is deferred for the production track: `latency_percentile` is a calculation primitive only; no representative OCR workload or production task-latency sample with queueing, retries, and backoff exists. Any Compose timing observation remains non-p99 evidence.
- Task 7.4 remains blocked pending explicit human owner approval to archive superseded prototype documents.

### Security task 4.6 evidence

- On 2026-09-27, `artifacts/security/4.6-evidence.json` recorded focused test-namespace controls. The Compose MVP security/cleanup slice still requires RabbitMQ Compose evidence; the production security portion remains deferred to the backlog until SIRD implementation and team-approved identity architecture. The evidence does not mark the task passed.

### GLiNER decision-stage evidence

- The selected test-only candidate checkpoint is `urchade/gliner_multi-v2.1`, revision `443d26d654e0324125a96bebd8e796c14ff2efe6`.
- CPU probe evidence is recorded in `artifacts/ocr/gliner-probe.json`; the model returns useful person/place candidates but mislabels a birth date as a registration date, so it remains candidate-only and deterministic date binding remains authoritative.
- Historical isolated test deployment evidence is recorded in `artifacts/ocr/gliner-deployment-evidence.json`. It is not a Docker Compose first-release or production gate; fixture-backed recognition, kind final image verification, latency acceptance, and real-image validation remain not-run or blocked.
