# Spec Delta

## Purpose

Migrates the prototype verification plan, acceptance criteria, test data, test cases, architecture checks, and metrics into executable OpenSpec obligations.

## ADDED Requirements

### Requirement: Verification is traceable to stable requirement IDs

Every migrated product, functional, security, quality, architecture, experiment, and operational requirement SHALL retain a stable source identifier or a documented OpenSpec mapping. Every acceptance claim SHALL identify its oracle, input class, expected state, and evidence location.

#### Scenario: Requirement is implemented
- **WHEN** a requirement is marked complete
- **THEN** its mapped contract, focused check, and evidence are available and the check distinguishes pass, fail, blocked, and not-run

### Requirement: Contract verification covers negative and partial behavior

The verification set SHALL cover invalid and corrupted input, absent target, uncertainty, multiple documents, all three supported forms, orientation, perspective, crop, quality measurement absence, baseline versus optional preprocessing, adapter capability mismatch, all target fields, normalization, correction limits, conflicts, partial documents, formal validations, budgets, cancellation, version/calibration, independence, and cache identity. The existing prototype cases `TEST-OCR-001` through `TEST-OCR-025` SHALL be migrated or mapped without losing their expected behavior.

#### Scenario: Expected rejection occurs
- **WHEN** a negative or limit test reaches its expected rejection
- **THEN** the rejection is a passing behavioral result and is not rewritten as a successful recognition

### Requirement: Architecture verification covers origin and isolation

Architecture checks SHALL verify autonomous execution without SIRD database/broker state, coordinate lineage, field provenance, bounded execution cleanup, real configuration and adapter replacement, independent experiment execution, protected reference data, and production/test package boundaries.

#### Scenario: Field provenance is inspected
- **WHEN** a result field is traced backward
- **THEN** its source observation, candidate, normalization, correction, validation, and coordinate space are recoverable

### Requirement: Metrics are versioned and stratified

Quality and resource metrics SHALL identify corpus version, variant, mode, form, input-quality stratum, numerator, denominator, comparison policy, evaluator version, and uncertainty method. Missing measurements SHALL remain explicit. Full-call time SHALL include preparation, repeats, correction, and result assembly; cold and warm modes SHALL be distinguished.

#### Scenario: Acceptance threshold is absent
- **WHEN** a required numerical boundary or sufficient stratum has not been fixed before the independent run
- **THEN** the corresponding acceptance result is blocked or not-run, never passed by default

### Requirement: Test data protects independence and provenance

The corpus SHALL retain source groups, page identity, rasterization metadata, visible geometry, field presence/readability, observed text, normalized value only when unambiguous, and comparison-policy version. Synthetic transformations SHALL preserve generator, template, parameters, and seed. Working manifests SHALL omit truth values, and protected labels SHALL be accessible only to the evaluator.

#### Scenario: Same physical document has several photos
- **WHEN** metrics are resampled or grouped
- **THEN** all related photos and variants remain in one provenance group and are not treated as independent observations

### Requirement: Acceptance requires evidence, not schema shape alone

Functional acceptance SHALL verify exact types, states, origins, budgets, cleanup, security boundaries, and refusal behavior. Quality acceptance SHALL verify fields, forms, false output, corruption, time, and memory separately. Experiment acceptance SHALL independently recompute results and decisions. A JSON-schema or validator pass SHALL NOT replace behavioral or reference-based verification.

#### Scenario: Evidence is incomplete
- **WHEN** code, corpus, version, or applicable boundary is missing
- **THEN** the acceptance item is blocked or not-run and the missing evidence is recorded

### Requirement: TEST-OCR-001..019 — contract and computation oracles

The migrated contract suite SHALL retain the prototype cases for valid/invalid media and limits, no-target and uncertainty, multiple candidates, all three forms, orientation and geometry, quality `not_measured`, P0/P1/P2 preprocessing, adapter capabilities, three fields and spatial labels, normalization/correction, conflicts/shared pixels, partial fields, validators, execution budget/cancellation, and configuration/calibration/cache. Expected rejection is a pass; incomplete/error analysis is never `not_detected`.

#### Scenario: Same pixels are reread
- **WHEN** a correction or second OCR read reuses the same pixel source
- **THEN** it is not treated as independent evidence and the attempt/cost lineage remains visible

### Requirement: TEST-OCR-020..025 — experiment, evaluator, and isolation oracles

The migrated suite SHALL retain the prototype checks for every planned pair, experiment order/seed/repeats, evaluator independence, replay without OCR, protected reference data, adapter/configuration replacement, cache identity, and complete result reporting. Missing pairs, hidden assistance, schema mismatch, or undeclared substitution block acceptance.

#### Scenario: Evaluator receives an incomplete run
- **WHEN** a planned pair, checksum, or resolved specification is missing
- **THEN** it rejects the evaluation and does not publish an aggregate result

### Requirement: VER-OCR-ARC-001..006 — architecture boundaries

Architecture verification SHALL cover autonomous execution without SIRD infrastructure, coordinate pixel-center/half-open bounds and transformation composition, field provenance/conflict lineage, cancellation/cleanup/resource release, real adapter/model/device/calibration/cache replacement, and evaluator execution without OCR or reference leakage.

#### Scenario: Coordinate transformation is composed
- **WHEN** a point crosses two recorded transforms
- **THEN** the composed result follows the declared source/destination spaces and valid-region mask, and degenerate geometry cannot yield a successful document

### Requirement: MVP and production acceptance are separate gates

The first version SHALL run the functional contract and architecture/security checks that do not require a protected corpus or production workload. For the first integrated release, Docker Compose with the target RabbitMQ workflow is the release gate. This includes contract validation, negative/refusal behavior, field states, selector rejection, artifact authorization, bounded execution, cleanup, and integration workflow behavior. Helm/Kubernetes, multi-node broker availability, production workload identity and broker authorization, protected-corpus thresholds, and production p99 evidence are deferred and SHALL NOT be reported as passed by the Compose gate. These checks require behavioral evidence beyond JSON or schema validation.

Production quality acceptance SHALL separately verify exact fields, forms, false output, corruption, time, memory, and CPU correction cost against a protected corpus and predeclared numeric boundaries. Production experiment acceptance SHALL rerun selected pairs and independently recompute metrics. Missing numeric thresholds, strata, code, corpus, or applicable boundary produce `blocked` or `not-run`.

The 30-second OCR p99 target and end-to-end task latency are production measurements, not first-version release gates. The MVP MAY record observed timings while retaining the fixed per-attempt deadline and bounded retry policy.

#### Scenario: First-version contract acceptance runs
- **WHEN** local contract, security, and workflow checks have executable behavioral oracles
- **THEN** the MVP acceptance report records their individual pass/fail/blocked state without requiring a protected corpus or numeric quality threshold

#### Scenario: A production quality threshold is absent
- **WHEN** a production acceptance run lacks a predeclared numerical boundary or sufficient independent stratum
- **THEN** the result is blocked/not-run and cannot be passed by schema validation

### Requirement: Corpus and metrics preserve independence

The corpus SHALL keep source groups, page/raster metadata, visible geometry, field `present=true|false|unknown`, readability `readable|unreadable|disputed`, observed text, versioned comparison policy, synthetic generator/seed, and protected labels separate from the working manifest. Metrics SHALL retain R/U/A/K/N field classes, exact/coverage/refusal/false-output/corruption measures, CER formula/version, IoU/form/geometry/mask-loss, quality precision/recall, calibration/Brier, cold/warm P50/P95, technical outcomes, and grouped bootstrap uncertainty (2000 resamples, 95% CI when that protocol is selected).

#### Scenario: Same physical document has multiple photos
- **WHEN** a metric is resampled or compared
- **THEN** all related photos, pages, variants, and repeats stay in one provenance group and are not treated as independent samples
