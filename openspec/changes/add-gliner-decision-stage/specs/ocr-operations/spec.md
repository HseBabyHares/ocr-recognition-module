# Spec Delta

## ADDED Requirements

### Requirement: Candidate model resources are local and allowlisted

The optional candidate decision stage SHALL load model, tokenizer, and label resources from an allowlisted local package or cache with immutable identifiers and checksums. Startup SHALL fail closed when a required resource is absent, mismatched, or incompatible with the declared language/task contract. Runtime model download and public model-network access SHALL not be required.

#### Scenario: Required model checksum mismatches
- **WHEN** a model or tokenizer checksum differs from the declared profile
- **THEN** readiness fails with an explicit model-resource diagnostic and no request uses that resource

#### Scenario: Candidate stage is disabled
- **WHEN** the active profile disables the candidate model
- **THEN** the OCR adapter remains usable for raw observations, and final fields remain conservative without hidden model invocation

### Requirement: Candidate inference is bounded and reproducible

Candidate inference SHALL use a finite CPU-thread, memory, input-length, candidate-count, and time budget. Warmup SHALL be separated from measured calls. The applied model/profile, thresholds, device, thread count, and resource revisions SHALL be captured in execution evidence. Repeated inference with the same declared input and profile SHALL be reproducible within the declared output ordering and score tolerance.

These bounds are prerequisites for enabling the optional candidate stage in a long-lived runtime. The first version keeps the stage disabled for final field selection and uses deterministic OCR rules as the MVP path; test-only evidence does not establish production runtime enforcement.

#### Scenario: Candidate inference exceeds a limit
- **WHEN** model inference reaches its time, memory, input, or candidate-count limit
- **THEN** the stage stops, releases temporary resources, returns an explicit limit outcome, and does not select an incomplete candidate

### Requirement: Candidate telemetry is safe

Logs and telemetry for candidate inference SHALL contain request/attempt/stage identifiers, model/resource revisions, timing, limit state, candidate counts, and safe reason codes. They SHALL NOT contain document bytes, raw OCR text, personal field values, model credentials, or temporary access material.

#### Scenario: Candidate stage emits an event
- **WHEN** inference starts, completes, fails, or is limited
- **THEN** the event includes safe correlation and outcome fields but omits OCR text, images, names, dates, places, and secrets

### Requirement: Candidate quality is gated by behavioral evidence

A candidate model SHALL not be enabled for field selection until a versioned fixture set measures field binding, registration-versus-birth separation, invalid-date refusal, conflict handling, false-output behavior, CPU latency, memory, and model-unavailable behavior. Model scores SHALL not be treated as accuracy without an explicit calibration protocol.

#### Scenario: Model probe is inconclusive or semantically wrong
- **WHEN** a model mislabels a registration date as a birth date or cannot satisfy the language/task contract
- **THEN** the model remains disabled for final selection, the evidence records the failure, and deterministic rules remain authoritative
