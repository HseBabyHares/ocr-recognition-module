# Spec Delta

## Purpose

Defines the observable SIRD integration contract around the migrated OCR computation, including asynchronous task ownership, artifact authorization, automatic MVP form selection, unary gRPC execution, result mapping, delivery reliability, and production/test boundaries.

## ADDED Requirements

### Requirement: Runtime boundaries are explicit

The system SHALL provide a production OCR runtime separately from the test-only HTTP adapter. The production image SHALL exclude the Litestar/Granian test adapter and the experimental runner/evaluator. Production OCR replicas SHALL be independently stateless and SHALL NOT require sticky sessions.

#### Scenario: Production image excludes test and experiment components
- **WHEN** the production image is assembled
- **THEN** it contains the OCR runtime and production dependencies but does not require the test-only HTTP adapter or experimental runner/evaluator

#### Scenario: Recognition is routed to any OCR replica
- **WHEN** Process Service sends a valid recognition request to an available OCR replica
- **THEN** the request can be processed without state created by an earlier request being present on that replica

### Requirement: SIRD owns document artifacts and authorizes references

The system SHALL identify input documents with a typed `artifact_ref` that resolves to SIRD-owned RustFS (S3-compatible) object storage. `artifact_ref.capability` SHALL be a signed, opaque, server-issued capability whose signature covers task/request binding, intended service audience, object checksum, media metadata, object generation, issuer, and expiry. OCR SHALL verify the signature and every claim before reading through least-privilege service credentials. OCR SHALL NOT accept arbitrary URL/path input or document bytes in the gRPC payload.

#### Scenario: OCR reads an authorized artifact
- **WHEN** Process Service sends a valid unexpired reference bound to the task and OCR has authorized access
- **THEN** OCR verifies the capability signature, every bound reference claim, and the stored object's checksum before reading the artifact and processing it under the active input policy

#### Scenario: Artifact reference is malformed, stale, cross-task, or mismatched
- **WHEN** the reference fails structure, expiry, audience, task binding, size, media, checksum, or authorization validation
- **THEN** OCR returns `INVALID_INPUT` or the applicable non-retryable authorization outcome, does not read an unintended object, and does not report successful recognition

#### Scenario: Referenced object is temporarily unavailable
- **WHEN** a valid reference cannot be read because of a classified transient storage failure
- **THEN** OCR returns `MATERIAL_UNAVAILABLE` with the transient reason and Process Service may retry under the shared attempt budget; a permanent absence is terminal without retry

#### Scenario: Input contains multiple logical documents
- **WHEN** the classifier detects more than one document candidate in the input
- **THEN** the result contains `multiple_candidates`, no fields from different candidates are merged, and no form profile is executed

### Requirement: SIRD exposes an asynchronous task workflow

The system SHALL create a durable `task_id` before document processing, persist the initial task state, and make task progress and the final result retrievable by that identifier. RabbitMQ 4.3 durable quorum queues, exchanges, and routing keys carry versioned task and result events through the target AMQP workflow. Task messages SHALL use stable identity; Process Service SHALL use manual acknowledgements only after the corresponding PostgreSQL state transition is durable. Task state and the authoritative attempt counter remain outside OCR. The Kafka baseline was removed by owner decision on 2026-10-13.

#### Scenario: Task is accepted for processing
- **WHEN** an authorized caller submits a valid document-processing request
- **THEN** SIRD creates a unique `task_id`, persists the initial state, publishes a task event, and returns the identifier to the caller

#### Scenario: Task status is queried
- **WHEN** a caller requests the state of an existing `task_id`
- **THEN** SIRD returns the current processing state without requiring the caller to remain connected to OCR

#### Scenario: Completed result is queried
- **WHEN** processing for a `task_id` has completed, been subject-rejected, failed, cancelled, or exceeded a limit
- **THEN** SIRD returns the recorded task outcome, result completeness, field values/statuses, diagnostics, and artifact references

#### Scenario: An untrusted caller knows a task identifier
- **WHEN** a caller without the authorized SIRD backend workload identity attempts task submission, status retrieval, result retrieval, or artifact access
- **THEN** access is denied even if the caller knows a valid `task_id`; end-user authorization remains the responsibility of the trusted SIRD backend

### Requirement: MVP automatically resolves the supported document form

The production `Recognize` operation SHALL classify all prepared pages allowed by the input policy and resolve the input among `snils_card`, `adi_reg_2019`, and `adi_reg_2023`. The MVP request SHALL NOT contain caller-selected `candidate_id`, `form_id`, or `profile_id`; the ingress parser SHALL reject any unknown wire field and return `INVALID_INPUT` when a reserved selector field or selector-like extension is supplied. A profile SHALL run only after exactly one logical candidate across the allowed pages and one supported form have been resolved by the classifier and versioned calibrated policy.

#### Scenario: Supported form is resolved
- **WHEN** exactly one candidate is found and one supported form is above the configured calibrated threshold with a deterministic tie/margin decision
- **THEN** the response records `FormResolution=resolved`, the form identifier, calibration reference, decision evidence, and executes the corresponding profile

#### Scenario: Form is ambiguous
- **WHEN** multiple supported forms tie or fall below the configured confidence/margin rule
- **THEN** the response records `FormResolution=ambiguous` with `form_ambiguous`, does not execute a profile, and produces a terminal non-retryable subject outcome

#### Scenario: Form is unsupported or unresolved
- **WHEN** the evidence matches no supported class or completed analysis cannot resolve a supported form
- **THEN** the response records `FormResolution=unsupported` or `unresolved`, does not execute a profile, and produces a terminal non-retryable subject outcome

#### Scenario: Analysis does not complete
- **WHEN** form analysis stops because of a technical error, cancellation, or execution limit before a subject conclusion
- **THEN** the response uses the applicable technical outcome (`failed`, `cancelled`, or `limit_exceeded`), does not claim unsupported/absent input, and does not execute a profile

#### Scenario: No document is detected after complete analysis
- **WHEN** analysis completes within its budget without a document candidate
- **THEN** the response records `SearchResult=not_detected` with `target_not_detected`, does not execute a profile, and produces a terminal non-retryable subject outcome

### Requirement: Process Service invokes OCR with unary gRPC

The production SIRD-to-OCR integration SHALL provide one unary Protobuf/gRPC recognition operation, `Recognize`. `Prepare`, `Probe`, form resolution, and `ExecuteProfile` SHALL remain internal stages and SHALL NOT be published as separate production RPCs in the MVP. Process Service SHALL send stable task/request identity, an authorized `artifact_ref`, and processing policy parameters. OCR SHALL return one bounded response and SHALL NOT expose a durable OCR job lifecycle.

#### Scenario: Recognition completes
- **WHEN** Process Service sends a valid unary recognition request and OCR completes within the request deadline
- **THEN** OCR returns operation status, task-level subject/technical outcome, result completeness, form resolution, field results, diagnostics, and execution metadata

#### Scenario: Caller cancels recognition
- **WHEN** the caller cancels the request
- **THEN** OCR stops where supported, records `operation_status=cancelled`, marks fields not reached as `not_processed`, and Process Service does not retry the cancelled task

#### Scenario: Recognition deadline expires
- **WHEN** a recognition attempt reaches its deadline without caller cancellation
- **THEN** the attempt is classified as transient only when the retry matrix permits it; the authoritative task attempt counter is consumed and the task is retried or terminally failed according to that matrix

### Requirement: Status and result mappings are explicit

The integration SHALL preserve the prototype technical `operation_status` semantics: `ok` means the operation completed by its contract; `partial` means preparation or execution itself completed only partially; `failed`, `cancelled`, and `limit_exceeded` are technical non-success outcomes. Subject and field completeness SHALL be represented separately.

The response SHALL include:

- `task_outcome`: `completed`, `subject_rejected`, `failed`, `cancelled`, or `limit_exceeded`;
- `result_completeness`: `complete`, `partial`, or `none`;
- `subject_diagnostic`: `supported`, `target_not_detected`, `form_ambiguous`, `form_unsupported`, `form_unresolved`, or `multiple_candidates`, when applicable;
- field status, value/null, validation, evidence references, and diagnostics.

| Subject condition | `operation_status` | `task_outcome` | `result_completeness` | Profile | Retry |
|---|---|---|---|---|---|
| One supported form resolved; all required fields extracted | `ok` | `completed` | `complete` | Runs | No |
| One supported form resolved; at least one field is unreadable, absent, conflicting, or not applicable | `ok` | `completed` | `partial` | Runs | No |
| No target after complete analysis | `ok` | `subject_rejected` | `none` | Does not run | No |
| Ambiguous, unsupported, or unresolved form after complete analysis | `ok` | `subject_rejected` | `none` | Does not run | No |
| Multiple candidates without an explicit MVP selection | `ok` | `subject_rejected` | `none` | Does not run | No |
| Technical failure, cancellation, or execution limit before subject conclusion | Technical status | Matching technical outcome | `none` or partial completed-stage data | Does not run unless stage already resolved | Matrix |

#### Scenario: Consumer maps a completed partial result
- **WHEN** the response contains `operation_status=ok`, `task_outcome=completed`, and `result_completeness=partial`
- **THEN** the consumer keeps readable fields, inspects every field status/diagnostic, and does not interpret the result as a transport failure or as a complete document

### Requirement: Resolved documents return field-level results

For a resolved supported document, the system SHALL attempt `snils`, `full_name`, and `birth_date`. It SHALL return readable fields even when another field is unreadable. Each field SHALL carry value or null, field status, validations, evidence references, and machine-readable diagnostics. The system SHALL NOT infer a hidden or damaged value from plausibility, a checksum, or another field.

The stable field mapping SHALL be:

| Field state | Value | Result effect | Required reason |
|---|---|---|---|
| `extracted` | Observed/normalized value | Complete unless another field is incomplete | Validation and evidence |
| `absent` | `null` | Partial | Observed field area is available and empty |
| `unreadable` | `null` | Partial | `field_unreadable`, `partial_visibility`, or `insufficient_resolution` |
| `conflict` | `null` | Partial | `field_conflict` and competing evidence |
| `not_applicable` | `null` | Partial only if required by the active profile | Applicability rule |
| `not_processed` | `null` | Partial or none | Cancellation, limit, or upstream stop reason |

#### Scenario: All target fields are readable
- **WHEN** the resolved document provides sufficient evidence for all three target fields
- **THEN** the response has `operation_status=ok`, `task_outcome=completed`, `result_completeness=complete`, and returns all three values with evidence and validations

#### Scenario: One field is unreadable
- **WHEN** the document form is resolved but one field is covered by glare, occlusion, insufficient resolution, or another observed defect
- **THEN** the response has `operation_status=ok`, `result_completeness=partial`, preserves readable fields, returns null for the unreadable field, and attaches the applicable machine diagnostic

#### Scenario: Extracted value fails formal validation
- **WHEN** a field is read as a representable value but its formal validation, including the SNILS check-number rule, is invalid
- **THEN** the extracted value and negative validation result are preserved; the system does not silently replace or delete the value

#### Scenario: No confirmed value exists
- **WHEN** reading a target field produces conflicting or insufficient hypotheses
- **THEN** the field has null value and status `unreadable` or `conflict`, with a machine-readable reason; no guessed value is returned

### Requirement: Diagnostics are versioned and forward-safe

The response SHALL use stable machine codes, diagnostic scope, and evidence references. MVP field/subject codes include `field_unreadable`, `field_absent`, `field_conflict`, `partial_visibility`, `insufficient_resolution`, `not_processed`, `target_not_detected`, `form_ambiguous`, `form_unsupported`, `form_unresolved`, and `multiple_candidates`. Consumers SHALL preserve unknown future codes without treating them as success; OCR SHALL not generate human-facing UI text.

#### Scenario: Consumer receives an unknown diagnostic
- **WHEN** a newer OCR service returns a diagnostic code unknown to the consumer
- **THEN** the consumer preserves the code and conservatively treats the affected result as not fully accepted

### Requirement: Task delivery and recognition are idempotent

The system SHALL use `task_id` and `request_id` as stable identities. PostgreSQL SHALL enforce one logical request record per `(task_id, request_id)` and one terminal result per task. A concurrent duplicate request SHALL return or await the existing record. A reused identity with different artifact or policy content SHALL be rejected as invalid input. Result publication SHALL use a unique outbox key.

#### Scenario: Task event or recognition request is delivered twice
- **WHEN** the same event or request is delivered more than once
- **THEN** the Process Service reuses the existing identity, does not reset the total attempt counter, and does not create a second logical result

#### Scenario: Timeout races with completed OCR
- **WHEN** the client times out while OCR may have completed
- **THEN** Process Service reconciles the idempotent request/result record before starting another attempt

### Requirement: Retry classification and delivery ownership are explicit

Process Service SHALL own one total attempt budget across gRPC attempts and RabbitMQ consumer redelivery. RabbitMQ redelivery, caused by a delivery that was not acknowledged after durable processing, SHALL resume the same PostgreSQL attempt record and SHALL NOT reset the budget. The MVP budget is three total OCR attempts per task, with a 35-second gRPC deadline and one-second then two-second backoff.
`technical_reason_class` is authoritative for retry decisions. `UNSPECIFIED` and `PERMANENT` are non-retryable; only `TRANSIENT` can enable retry for rows that explicitly allow it. `technical_reason` is diagnostic text and SHALL NOT be parsed for control flow.

| Code/status | Retry | `operation_status` | `task_outcome` | `result_completeness` | Terminal rule |
|---|---|---|---|---|---|
| `INVALID_INPUT` | No | `failed` | `failed` | `none` | Terminal immediately |
| `INPUT_LIMIT_EXCEEDED` | No | `limit_exceeded` | `limit_exceeded` | `none` | Terminal immediately |
| `INVALID_CONFIGURATION` | No | `failed` | `failed` | `none` | Terminal immediately |
| `CAPABILITY_MISMATCH` | No | `failed` | `failed` | `none` | Terminal immediately |
| `AUTHORIZATION_FAILED` | No | `failed` | `failed` | `none` | Terminal immediately |
| `MATERIAL_UNAVAILABLE` | Only with explicit transient storage reason | `failed` | `failed` after budget | `none` | Retry while budget remains; otherwise terminal |
| `MODEL_UNAVAILABLE` | Only with explicit transient readiness reason | `failed` | `failed` after budget | `none` | Retry while budget remains; otherwise terminal |
| `EXECUTION_LIMIT_EXCEEDED` | No | `limit_exceeded` | `limit_exceeded` | `none` | Terminal immediately |
| `CANCELLED` or caller cancellation | No | `cancelled` | `cancelled` | `none` | Terminal immediately |
| `EXECUTION_ERROR` | Only with explicit transient classification | `failed` | `failed` after budget | `none` | Retry while budget remains; otherwise terminal |
| gRPC `UNAVAILABLE`, `DEADLINE_EXCEEDED` without caller cancellation | Yes while budget remains | `failed` | `failed` after budget | `none` | Consume one shared attempt before retry |
| gRPC `INVALID_ARGUMENT`, `FAILED_PRECONDITION`, `PERMISSION_DENIED`, `UNAUTHENTICATED` | No | `failed` | `failed` | `none` | Terminal immediately |

Rows that permit retry describe a non-terminal attempt. While retrying, the response may retain `operation_status=failed` but SHALL NOT persist terminal `task_outcome` or `result_completeness`; after the shared budget is exhausted, the terminal mapping in the table applies. A technical row has `result_completeness=none` at terminal completion unless a separately defined completed-stage partial result is retained.

#### Scenario: Transient dependency failure
- **WHEN** an attempt fails with an explicitly transient code/status
- **THEN** Process Service consumes one shared attempt, records the reason, retries within the budget, and applies the configured backoff

#### Scenario: Permanent or subject outcome
- **WHEN** an attempt produces a permanent technical code or a completed subject outcome
- **THEN** the task receives its terminal mapping and is not retried as if the same input could be fixed by transport repetition

#### Scenario: Retry budget is exhausted
- **WHEN** all three total attempts fail transiently or a task delivery cannot be safely resumed
- **THEN** Process Service atomically persists the terminal technical outcome and a dead-letter outbox record with a stable event ID in PostgreSQL; the dispatcher publishes that record to the configured RabbitMQ terminal route with publisher confirmation and an explicit mandatory/equivalent unroutable check before the consumer acknowledges the source delivery; a crash or uncertain confirmation can repeat publication but cannot reset the attempt budget or create a second logical terminal result

#### Scenario: Dead-letter publication is interrupted
- **WHEN** the task outcome is durable but RabbitMQ has not confirmed the terminal publication
- **THEN** the source delivery remains unacknowledged, the durable outbox remains pending, and recovery retries publication with the same event ID without calling OCR again

### Requirement: Result publication preserves durable outcomes

Process Service SHALL persist a terminal task/result record before committing the consumed task-event offset. PostgreSQL SHALL provide a transactional outbox for result-event publication. Result events SHALL be idempotent and recoverable after a crash between result persistence and publication.

#### Scenario: Result persistence succeeds before publication fails
- **WHEN** PostgreSQL contains a completed result but result-event publication did not complete
- **THEN** the outbox republishes the pending result event and no second logical result is created

### Requirement: MVP service access is private, bounded, and fail-closed

The first version SHALL run behind one trusted SIRD backend on loopback or a private Docker network and SHALL NOT expose an end-user Task/Process API. The adapter SHALL NOT use a caller-supplied `caller_identity` as transport authentication. Artifact references SHALL be issued for the intended task/service audience and validated before reads. Logs and telemetry SHALL not contain document bytes, raw personal field values, unrestricted intermediate images, secrets, or access credentials.

The target RabbitMQ Compose workflow SHALL use TLS and fail-closed route authorization for Task Service and Process Service. This local profile is a development control; it is not evidence of production workload identity or production broker authorization. The Kafka baseline, including its TLS client/ACL profile, was removed by owner decision on 2026-10-13.

#### Scenario: Untrusted caller reaches the local boundary
- **WHEN** a caller outside the trusted backend or private deployment boundary attempts task submission, status retrieval, result retrieval, or artifact access
- **THEN** access is denied before the privileged operation, even if the caller knows a valid `task_id`

#### Scenario: Local RabbitMQ client lacks its certificate or route permission
- **WHEN** a local task or result publisher/consumer connects without the required TLS material or exchange/queue authorization
- **THEN** the connection or operation is rejected and no task state transition is acknowledged as delivered

### Requirement: Production identity and broker authorization are a separate track

Production deployment SHALL additionally use mutually authenticated TLS with X.509 client certificates issued by a deployment CA, explicit client-certificate identity-to-role authorization, certificate rotation, and least-privilege RabbitMQ exchange/queue permissions. These controls are deployment inputs and acceptance gates for the production track; they are not required to run the first Docker Compose MVP.

#### Scenario: Production caller lacks its workload identity
- **WHEN** a production caller lacks an authorized mTLS client certificate identity, presents an expired/untrusted credential, or lacks the required RabbitMQ authorization
- **THEN** the call or broker operation is rejected before recognition or durable acknowledgement


#### Scenario: Diagnostic retention is not enabled
- **WHEN** a task completes, fails, is cancelled, or exceeds a limit without explicit diagnostic retention
- **THEN** temporary OCR materials are deleted according to cleanup policy and only permitted result metadata or references remain


### Requirement: SIRD controls result retention with a bounded default

The integration SHALL use the trusted SIRD retention policy for stored results and integration-owned result artifacts. If SIRD supplies no retention policy, the retention period SHALL be 12 hours. The fallback SHALL NOT enable diagnostic retention, extend an artifact capability's expiry, or authorize deletion of SIRD-owned originals. Expiry enforcement SHALL cover result reads and artifact access as well as stored payload cleanup. Retention and outbox recovery SHALL NOT turn an expired result into an apparently available artifact.

#### Scenario: SIRD supplies a retention period
- **WHEN** the trusted SIRD backend supplies a valid retention policy
- **THEN** the integration applies that policy to the result and integration-owned result artifacts instead of the default

#### Scenario: No SIRD retention policy is supplied
- **WHEN** a task is accepted without a SIRD retention policy
- **THEN** the integration records the 12-hour retention default, does not enable diagnostic retention, and does not change the lifecycle of the SIRD-owned original

### Requirement: Experimental and test execution remain outside production

The system SHALL provide experimental execution as a separate runtime/package and SHALL keep it out of the production image. The test-only Litestar + Granian adapter SHALL exercise the production OCR contract without becoming a production dependency.

#### Scenario: Experimental runner executes a corpus
- **WHEN** an experiment is started
- **THEN** it runs through the separate experimental runtime and does not change production task state or image contents

#### Scenario: Test adapter exercises OCR
- **WHEN** the test-only adapter sends a supported request
- **THEN** it exercises the defined OCR integration contract without requiring the adapter in the production runtime image
