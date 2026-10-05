# Spec Delta

## Purpose

Migrates the prototype deployment, observability, security, and runbook rules into OpenSpec. SIRD integration mechanics remain in `sird-ocr-integration`; this capability defines the OCR runtime operating contract.

## ADDED Requirements

### Requirement: Runtime packaging is reproducible and separated

The production package SHALL contain the OCR module, allowlisted adapters, fixed dependencies, profile specifications, and permitted local model files. The test package MAY contain contract doubles and the Litestar + Granian adapter. The experiment package SHALL contain the runner, evaluator, corpus manifests, and experiment-only dependencies. Experiment and test packages SHALL NOT be required by the production image.

#### Scenario: Production package is assembled
- **WHEN** production dependencies and images are resolved
- **THEN** only production runtime components and allowlisted models are included

### Requirement: Startup and update checks are mandatory

Before a run, the operator SHALL verify code/model versions, checksums, usage conditions, input/result permissions, resource limits, thread counts, temporary-material retention, no reference-data access, and no public-model dependency. A first run SHALL include a valid example, a negative frame, a corrupted input, response-schema validation, configuration capture, cleanup verification, and log redaction verification.

#### Scenario: Model profile is updated
- **WHEN** a new model, adapter, calibration, or parameter profile is introduced
- **THEN** it receives a new immutable specification and passes contract/regression/resource checks before routing new requests

### Requirement: Observability uses safe correlated events

Stage start and finish telemetry SHALL include `request_id`, `attempt_id`, `stage_id`, implementation/version, specification hash, time, outcome, and safe reason code. Experiment telemetry SHALL additionally include `run_id`, `sample_id`, `variant_id`, and `repeat_id`. Personal values, document bytes, secrets, and access credentials SHALL NOT be telemetry labels or common log content.

#### Scenario: A stage fails
- **WHEN** a stage fails, is cancelled, or exceeds a limit
- **THEN** its safe event records the stage, outcome, reason, timing, and cleanup state without raw document data

### Requirement: Resource and regression runbooks are actionable

The runtime SHALL provide procedures for execution-limit incidents and OCR/regression reproducibility incidents. Limit handling SHALL stop the current process according to policy, delete incomplete temporary material, avoid automatic limit escalation for untrusted input, and verify the next call. Regression handling SHALL compare checksums, versions, device, defaults, stages, cache, predictions, and evaluator results; restore the prior immutable profile without rewriting references or old results.

#### Scenario: Limit regression is observed
- **WHEN** limit-exceeded or memory failures recur
- **THEN** the operator uses request/stage/policy evidence, does not silently raise limits, and verifies cleanup and recovery with a bounded synthetic check

### Requirement: Rollback preserves historical results

Rollback SHALL restore the previous immutable profile with its adapters, model files, and applicable calibration. Old and new stored results SHALL NOT be rewritten. New routing SHALL stop before profile replacement, and a focused regression set SHALL pass before resuming.

#### Scenario: New profile degrades a hard metric
- **WHEN** a new profile increases false output, corrupts correct fields, or breaks reproducibility
- **THEN** routing returns to the previous profile and the new results remain available for explicit analysis

### Requirement: OPS-OCR-DEPLOYMENT and ARC-OCR-DEPLOYMENT — readiness and isolation

The production OCR process SHALL be isolated, use local allowlisted models and read-only weights, a bounded per-call scratch area, a separate decoder, explicit CPU/thread and optional accelerator settings, and no public model network. Readiness SHALL resolve every adapter, read required weights, verify the device, and verify workspace writes; missing model/device returns an exact failure with no fallback. Warmup SHALL be separate from measured samples and cold-cache limitations SHALL be recorded.

#### Scenario: Required device is unavailable
- **WHEN** a profile requires a model or device that cannot be resolved
- **THEN** readiness fails with the exact reason and does not silently switch model or device

### Requirement: OPS-OCR-DEPLOYMENT — fair resource measurement and pinned updates

Resource checks SHALL measure fixed-thread single calls and concurrent calls with the same models and size distribution, including per-call time, total/process memory, technical outcomes, actual parallelism, process/thread effects, input/output size, call budget, warmup, and cache state. Accepted requests SHALL remain pinned to their profile versions. A new profile SHALL not inherit old calibration automatically. SIRD queue/cluster/DB scaling is outside this module contract.

#### Scenario: New profile is routed
- **WHEN** a new model, parameter, or calibration is proposed
- **THEN** it receives a new immutable profile, passes contract/regression/quality-cost checks, and does not alter already accepted requests

### Requirement: OPS-OCR-OBSERVABILITY — safe metrics and diagnostics

Telemetry SHALL distinguish monotonic stage/full-call duration, CPU collection scope, memory aggregation method, model/image calls, technical outcomes, search outcomes, field states, and cache hits versus actual compute. Confidence SHALL NOT be labeled accuracy. Field-to-image diagnostics SHALL use protected access with bounded retention; text and images SHALL not enter common logs or exceptions. Repeated uncertainty SHALL be investigated with permitted anonymized evidence, not score-shift assumptions alone.

#### Scenario: Memory is measured across replicas
- **WHEN** a resource run uses multiple processes
- **THEN** it records the aggregation method and does not add unsynchronized peak values as if they were one measurement

### Requirement: RB-OCR-001 — execution-limit recovery

The limit runbook SHALL trigger on `limit_exceeded`, memory stop, or stage timeout. It SHALL record request/stage/spec, input/output sizes, variants/model calls, threads/processes, weight-load time, and cache; stop the current process, delete incomplete temporary data, prohibit silent limit escalation, require a new profile for policy changes, preserve experiment failure records with new repeat IDs, and verify cancellation, partial fields, memory release, next-call recovery, and log-leak containment.

#### Scenario: Limit incident recovers
- **WHEN** a bounded synthetic case, small valid input, and cancellation check are rerun
- **THEN** no incomplete fields or temporary leak remains and the next call runs under the declared profile

### Requirement: RB-OCR-002 — regression and reproducibility recovery

The regression runbook SHALL cover degraded exact extraction, false output, corruption, and reproducibility. Diagnosis SHALL compare checksums, full profile, device/defaults, decode/color/orientation/normalization, evaluator, cache, hidden substitutions, and corpus mixing; localization SHALL trace raster→document→geometry→raw OCR→candidate→correction→selected value. Recovery SHALL restore the previous immutable profile or disable an optional stage without rewriting labels or historical results, and shall retain complete planned-pair evidence and ownership.

#### Scenario: Regression is confirmed
- **WHEN** affected samples and stage evidence identify a profile regression
- **THEN** routing rolls back or disables the declared optional stage, preserves old/new results, and passes the affected regression and contract set before resume
