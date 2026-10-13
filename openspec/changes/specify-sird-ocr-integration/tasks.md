# Tasks

## 1. Migration inventory and traceability

- [x] 1.1 Inventory every file under `docs/prototype` and classify it as product, requirement, architecture, data, interface, security, view, verification, experiment, operation, runbook, or glossary evidence.
- [x] 1.2 Extract stable source IDs (`FR-OCR-*`, `FR-EXP-*`, `NFR-OCR-*`, `SEC-OCR-*`, `CON-OCR-*`, `TEST-OCR-*`, `VER-OCR-*`, `AC-OCR-*`, architecture IDs, metric IDs, and runbook IDs) into a source-to-OpenSpec traceability matrix.
- [x] 1.3 Record every prototype conflict or superseded statement, including caller-selected form/profile behavior and open transport/task boundaries, with an explicit OpenSpec decision.
- [x] 1.4 Define traceability evidence ownership and an oracle for every migrated source ID; mark missing or intentionally deferred evidence as blocked or not-run, never passed.

## 2. Core recognition specification

- [x] 2.1 Migrate input policy, decoding, page/raster provenance, preparation completeness, and invalid-input behavior from `FR-OCR-001`.
- [x] 2.2 Migrate search, candidate identity, no-detection, uncertainty, multiple-candidate, and three-form resolution behavior from `FR-OCR-002` through `FR-OCR-004`.
- [x] 2.3 Migrate orientation, coordinate spaces, geometry, quality measurements, optional preprocessing, and material lineage from `FR-OCR-005` through `FR-OCR-007`.
- [x] 2.4 Migrate OCR capability reporting, field extraction, raw/normalized values, correction candidates, validation, conflicts, partial fields, and no-guessing rules from `FR-OCR-008` through `FR-OCR-013`.
- [x] 2.5 Migrate finite execution limits, applied configuration, independent integration execution, domain field representations, and CPU correction constraints from `FR-OCR-014` through `FR-OCR-016`, `NFR-OCR-*`, and `CON-OCR-001`.
- [x] 2.6 Define complete field-state mapping for `extracted`, `absent`, `unreadable`, `conflict`, `not_applicable`, and `not_processed`, including null/value, diagnostic, result-completeness, cancellation, and limit semantics.
- [x] 2.7 Define the classifier decision table for resolved, ambiguous, unresolved, unsupported, uncertain/incomplete, no-target, and multiple-candidate states, including threshold, tie, calibration, and no-profile behavior.

## 3. Production integration contract

- [x] 3.1 Define and version unary Protobuf `Recognize` with task/request identity, task-bound artifact reference, processing policy, operation status, task outcome, result completeness, form resolution, field results, validations, diagnostics, and execution metadata.
- [x] 3.2 Reject caller-selected candidate/form/profile selectors in the MVP wire contract and map internal `ExecuteProfile` selection only from the classifier.
- [x] 3.3 Define the artifact-reference authorization contract: task/request binding, audience, expiry, checksum, media metadata, least privilege, stale/cross-task rejection, and no arbitrary URL/path access.
- [x] 3.4 Define stable wire mappings for prototype technical codes, subject diagnostics, field statuses, diagnostic scope/evidence, unknown-code preservation, and task terminal outcomes.
- [x] 3.5 Define the test-only Litestar + Granian adapter separately from the production gRPC boundary and keep transport-neutral internal stage ports.

## 4. Workflow reliability and security

- [x] 4.1 Implement Task/Process workflow in a separate integration package in this repository: trusted-SIRD-backend-only task submission, PostgreSQL initial state and task outbox, RabbitMQ task-route delivery as the target, status retrieval, and result retrieval under `task_id`. The Kafka baseline was removed by owner decision on 2026-10-13.
- [x] 4.2 Implement Process Service idempotency with unique `(task_id, request_id)`, divergent-payload rejection, concurrent-winner/reuse behavior, and timeout-result reconciliation.
- [x] 4.3 Define and implement one retry matrix for every prototype technical code and relevant gRPC status, including cancellation, material/model readiness, and execution limits; timeout-vs-completed-OCR reconciliation remains task 4.2.
- [x] 4.4 Make Process Service own one shared three-attempt budget across gRPC attempts and RabbitMQ redelivery; persist attempt transitions before durable acknowledgement. The Kafka baseline, including its offset/redelivery path, was removed by owner decision on 2026-10-13.
- [x] 4.5 Implement the 35-second per-attempt deadline, one/two-second backoff, cancellation propagation, PostgreSQL transactional outbox, idempotent result publication, and RabbitMQ at-least-once terminal route before consumer acknowledgement without infinite replay; apply SIRD result retention with a 12-hour fallback and verify expiry behavior. The Kafka baseline, including its dead-letter path, was removed by owner decision on 2026-10-13.
- [x] 4.6 **Alpha scope completed; production backlog deferred.** The Alpha release uses Docker Compose, RabbitMQ TLS/quorum routes, trusted-backend authorization, task-bound artifact checks, safe metadata, bounded decoder/model controls, and available cleanup evidence as its release boundary. The owner accepts production mTLS certificate issuance and rotation, CA trust-anchor distribution, RabbitMQ workload identity and broker authorization, production ACL operations, OS-level decoder isolation, and protected production reference-data separation as post-Alpha backlog. These items are not Alpha release gates.

## 5. Runtime, experiment, and operations migration

- [x] 5.1 Implement or wire the stateless OCR runtime around the migrated computation ports without durable SIRD task state.
- [x] 5.2 Build separate OCR production, SIRD integration, test, and experimental packages; exclude workflow/PostgreSQL dependencies, Litestar, Granian, evaluator, corpus, and experiment-only dependencies from the production OCR image. The Kafka baseline, including its client dependency, was removed by owner decision on 2026-10-13.
- [x] 5.3 Migrate `FR-EXP-001` through `FR-EXP-005` and the experiment contract: immutable plan, resolved variants, per-sample terminal records, truth isolation, independent evaluator, metrics, and selection evidence.
- [x] 5.4 Migrate deployment/startup/update/rollback rules and immutable profile/version/calibration handling.
- [x] 5.5 Migrate safe correlated observability fields and stage/resource/quality measurements without personal values or document bytes.
- [x] 5.6 Migrate and validate the execution-limit and OCR-regression runbooks, including bounded recovery and preservation of historical results.

## 6. Verification and acceptance migration

- [x] 6.1 Implement focused executable oracles for `TEST-OCR-*`, `VER-OCR-*`, and architecture checks; preserve negative, partial, conflict, provenance, cleanup, and no-guessing behavior.
- [x] 6.2 Implement corpus fixtures with source groups, page/raster provenance, visibility/readability labels, synthetic seeds, protected reference access, and comparison-policy versions.
- [x] 6.3 Implement exact-field, refusal, false-output, corruption, form, geometry, time, memory, and uncertainty metrics with versioned strata and denominators.
- [x] 6.4 **Alpha scope completed; production acceptance deferred.** The Alpha release accepts the available local behavioral oracles, RabbitMQ task/result transport checks, durable outbox checks, acknowledgement/redelivery checks, bounded retry checks, terminal-route checks, and safe metadata checks. `AC-OCR-002`, `AC-OCR-003`, protected-corpus evidence, numeric quality thresholds, and missing ID-specific oracles are post-Alpha backlog items.
- [x] 6.5 Add integration checks for every subject mapping, every field state, selector rejection, artifact authorization failure, retry matrix branch, shared attempt budget, duplicate delivery, timeout race, outbox recovery, and terminal-route behavior.
- [x] 6.6 **Alpha scope completed; production performance deferred.** The Alpha release accepts observed local timing and bounded retry evidence. Representative workload p99, production queueing/retry/backoff latency, and the numeric OCR latency gate are post-Alpha backlog items. Alpha does not claim production p99.

## 7. Reconciliation and archive gate

- [x] 7.1 Run independent architecture, security/threat, traceability, and adversarial reviews against OpenSpec and prototype evidence.
- [x] 7.2 Validate all OpenSpec artifacts and run applicable FADD harness checks; record configured, not-configured, findings, and blocked gates without weakening them.
- [x] 7.3 Produce the migration reconciliation report showing every prototype source file and stable ID mapped to an OpenSpec requirement/task/oracle.
- [x] 7.4 **OWNER DECISION — Alpha release approved.** The owner approves the Alpha release with superseded Kafka implementation and prototype documents retained as migration evidence. Archive/removal is not part of Alpha and requires a later explicit owner decision; it does not block the Alpha release. The Kafka baseline was removed by owner decision on 2026-10-13.
