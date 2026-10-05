# Spec Delta

## Purpose

Migrates the prototype OCR module requirements into the OpenSpec capability. The production integration facade is defined separately in `sird-ocr-integration`; this capability preserves the computation, data, safety, and experiment-independent behavior of the OCR module.

## ADDED Requirements

### Requirement: Input preparation is bounded and traceable

The OCR module SHALL validate actual media type, decodability, compressed size, decoded dimensions, channels, bit depth, page count, and total pixel count against a finite `InputPolicy`. Prepared pages SHALL preserve source identity, page order, rasterization/decode version, checksum, and preparation completeness. A partial preparation SHALL carry its reason and SHALL NOT be reported as complete.

#### Scenario: Valid photo or scan is prepared
- **WHEN** the source satisfies the active input policy and decodes successfully
- **THEN** the module returns ordered prepared raster pages with source and decoder provenance

#### Scenario: Input violates a limit or cannot decode
- **WHEN** media, size, dimensions, pages, pixels, or decoding violates policy
- **THEN** the module returns a typed technical outcome and does not publish an apparently complete prepared page

### Requirement: Search distinguishes detection, absence, uncertainty, and multiple candidates

The search stage SHALL return candidate objects with stable identity, geometry, visible-corner mask, form hypotheses, score scale, implementation reference, and issues. It SHALL distinguish `detected`, `not_detected`, and `uncertain`. A failed or budget-exhausted analysis SHALL NOT be reported as completed absence. Candidates from different documents SHALL retain different `candidate_id` values and SHALL NOT be merged without an explicit separate-processing policy.

#### Scenario: No document is found after complete analysis
- **WHEN** search completes within its budget without a candidate
- **THEN** the result is `not_detected` with evidence that analysis completed

#### Scenario: Search is incomplete or uncertain
- **WHEN** search cannot reach a reliable conclusion because of an execution error, limit, or weak evidence
- **THEN** the result is `uncertain` or a technical outcome with a reason, never a confident absence

#### Scenario: Multiple documents are visible
- **WHEN** more than one candidate is detected
- **THEN** each candidate has separate identity and fields are not combined

### Requirement: Form resolution is explicit and fail-safe

The module SHALL represent `FormResolution` as `resolved`, `ambiguous`, `unresolved`, or `unsupported`. The MVP supported form identifiers are `snils_card`, `adi_reg_2019`, and `adi_reg_2023`. A profile SHALL execute only for one resolved supported form. Missing or invalid calibration is an invalid configuration. Ties and scores below the versioned calibrated threshold SHALL resolve to ambiguity, never by arbitrary fallback.

#### Scenario: One calibrated form wins
- **WHEN** one supported form is above the configured threshold and satisfies the tie/margin rule
- **THEN** the result records the form, calibration reference, score scale, and decision evidence

#### Scenario: Form decision is ambiguous or unsupported
- **WHEN** no supported form meets the decision policy or the evidence matches no supported class
- **THEN** the module returns the corresponding resolution and does not run a profile

### Requirement: Geometry and quality preserve origin

The module SHALL distinguish metadata orientation, quarter-turn rotation, perspective, residual skew, crop, scale, and visibility. Every applied transformation SHALL record source and destination coordinate spaces, parameters, and the accessible source region. Quality measurements SHALL include region, scale, algorithm, unit, status, value, and reason. A missing measurement SHALL be `not_measured` with a reason and SHALL NOT be replaced by a zero defect.

#### Scenario: Image is rotated or perspective-distorted
- **WHEN** geometry processing changes the raster or region
- **THEN** downstream evidence can be mapped back to the original coordinate space with the recorded transformation chain

#### Scenario: Quality metric is unavailable
- **WHEN** an implementation cannot calculate a requested quality metric
- **THEN** it returns an explicit unavailable status and reason

### Requirement: Optional preprocessing is controlled

The module SHALL provide a baseline path without optional enhancements. Additional preprocessing, alternate reads, and retries SHALL be selected by a named profile, bounded by finite budgets, and recorded in material lineage.

#### Scenario: Optional enhancement is disabled
- **WHEN** a baseline profile is executed
- **THEN** no unconfigured enhancement or hidden second read changes the result

#### Scenario: Field-specific reread is requested
- **WHEN** the profile requests a reread for a named reason such as low score, conflict, failed validation, or insufficient evidence
- **THEN** the field, reason, attempt number, pixel source, and consumed model-call budget are recorded

### Requirement: OCR observations expose only real capabilities

An OCR adapter SHALL return raw text, actual regions, available scores, and actual alternatives. Unsupported coordinates, probabilities, and character alternatives SHALL be represented as unavailable rather than synthesized. Adapter capabilities SHALL be checked before a profile uses them.

#### Scenario: Adapter lacks a capability
- **WHEN** a profile requests a capability that the adapter does not provide
- **THEN** execution returns an explicit capability mismatch or unavailable field and does not invent the missing data

### Requirement: Fields preserve evidence and limited correction

The module SHALL produce `snils`, `full_name`, and `birth_date` with field status, raw value, normalized value, evidence references, candidates, corrections, normalizations, validations, confidence, and issues. Formatting normalization SHALL be distinct from replacement of an observed character. Every correction SHALL preserve the source and new fragment, method, and supporting evidence.

#### Scenario: Field is read and normalized
- **WHEN** a field is read unambiguously
- **THEN** the raw value, normalized value, evidence, and applied validations are all retained

#### Scenario: Correction is only plausible
- **WHEN** a candidate is supported only by language plausibility, an existing date, or a checksum
- **THEN** it remains a candidate or rejected hypothesis and is not selected as the field value

### Requirement: Partial and conflicting fields are explicit

The module SHALL preserve confirmed readable fields when another field is unreadable. It SHALL preserve conflicts between comparable hypotheses and SHALL NOT treat repeated reads of the same pixels as independent evidence. Field states SHALL include `extracted`, `absent`, `unreadable`, `conflict`, `not_applicable`, and `not_processed`. `not_processed` SHALL NOT be rewritten as `absent`.

#### Scenario: One field is occluded
- **WHEN** one target field is unreadable but other fields are supported
- **THEN** readable fields are returned, the unreadable field is null with a reason, and no value is guessed

#### Scenario: Execution stops before a field
- **WHEN** cancellation or a limit stops a stage before a field is processed
- **THEN** the field is `not_processed` with the stopping reason

### Requirement: Formal validations are versioned

Format, calendar, and check-number validations SHALL record rule identifier, rule version, applicability, and outcome. An inapplicable or unexecuted rule SHALL NOT return `valid`. A read value with a failed validation SHALL remain observable together with the negative validation outcome.

#### Scenario: SNILS check-number validation fails
- **WHEN** the visible SNILS value is representable but fails the check-number rule
- **THEN** the value is preserved and the versioned validation is `invalid`; no correction is inferred from the checksum

### Requirement: Execution limits are finite and clean up

Each execution SHALL have finite time, memory, model-call, variant, thread, and retry limits. Stopping SHALL return the reason and only completed-stage results. Temporary resources SHALL be released so a subsequent call can execute with its declared profile.

#### Scenario: Limit is exceeded
- **WHEN** a limit is reached
- **THEN** the result is `limit_exceeded` with the exact limit and reason, incomplete fields remain `not_processed`, and temporary resources are cleaned

### Requirement: Applied configuration is reproducible

Results SHALL record requested and applied code, policy, model, calibration, device, and schema versions. An unavailable or incompatible implementation SHALL fail explicitly and SHALL NOT be silently replaced. Cache identity SHALL include input checksum, implementation/model versions, full parameters, mode, and authorization scope.

#### Scenario: Model version is unavailable
- **WHEN** the requested implementation cannot be loaded or does not match the declared capability
- **THEN** the result contains an explicit technical outcome and does not silently select another model

### Requirement: OCR computation is independent from SIRD state

The internal OCR stages SHALL run with explicit materials, policies, and limits without direct dependency on SIRD database tables, broker state, user accounts, or the experiment reference set. The computational result SHALL not claim a durable task status, document authenticity, ownership, or final business acceptance.

#### Scenario: OCR runs in an isolated test environment
- **WHEN** Prepare, Probe, form resolution, and profile execution receive local permitted materials and policies
- **THEN** they execute without SIRD database or broker components and return only computation results

### Requirement: Domain field representations are stable

`snils` SHALL represent eleven digits without formatting separators while retaining original spelling. `full_name` SHALL represent the observed full name without assuming exactly three words. `birth_date` SHALL use `YYYY-MM-DD` only when the calendar date is unambiguous. Additional fields SHALL require a versioned schema extension.

#### Scenario: Field is not safely representable
- **WHEN** the observed content cannot be represented under the field rule
- **THEN** the value is null with the applicable field state and reason, not a fabricated normalized value

### Requirement: Security protects input, models, personal data, and reference data

Untrusted decoding SHALL run with resource limits and without network, model catalog, secrets, or experiment-reference access. Production code and models SHALL come from an allowlisted local registry with identifiers and checksums. Shared logs and telemetry SHALL omit images, personal values, secrets, and temporary access credentials. Temporary materials and reference data SHALL be isolated by run and removed by policy. Working OCR SHALL never receive the experiment truth set.

#### Scenario: Malformed or hostile raster is processed
- **WHEN** decoding encounters malformed content or reaches a resource limit
- **THEN** the decoder stops, cleans temporary data, and returns a technical outcome without exposing secrets or reference data

#### Scenario: Runtime log is emitted
- **WHEN** a stage starts, finishes, or fails
- **THEN** telemetry contains safe identifiers and reason codes but not document bytes or personal field values

### Requirement: FR-OCR-001 and API `ocr.module/1` — explicit input context and limits

The module contract SHALL carry `contract_version`, `request_id`, `attempt_id`, `ExecutionLimits`, and scoped `material_access`. Required limits SHALL be positive finite values for timeout, memory, input/output bytes/pixels, pages, and CPU threads; model-call and variant limits MAY be zero but SHALL be bounded. Missing, negative, or unbounded required limits SHALL return `INVALID_CONFIGURATION`. Page and total-pixel budgets are distinct, do not reset on internal retry, and model wait counts toward timeout.

#### Scenario: Limit configuration is invalid
- **WHEN** a request omits a required limit or supplies a negative/unbounded value
- **THEN** the module returns `INVALID_CONFIGURATION` before processing untrusted material

### Requirement: FR-OCR-001 — Prepare preserves pages and partial completeness

`InputPolicy` SHALL include policy ID/version, accepted media types, allowlisted decoders, rasterization, channel/bit-depth limits, orientation rule, and partial-preparation policy. `Prepare` SHALL return `pages`, `page_count`, `preparation_complete`, diagnostics, and applied execution. Each page SHALL retain page ID, zero-based index, source ID, status `prepared|failed|not_processed`, artifact reference, reason, checksum, and raster metadata. Unknown page count is incomplete; text layers, scripts, and attachments are not OCR inputs.

#### Scenario: A page is damaged
- **WHEN** one page cannot be decoded or prepared
- **THEN** it remains represented with a failure reason and the response cannot claim complete preparation or confident absence

### Requirement: FR-OCR-002..007 — stage contracts and provenance

`Probe` SHALL return `SearchResult` with `detected|not_detected|uncertain` and `analysis_complete`; `not_detected` is valid only after complete analysis. `ExecuteProfile` SHALL receive a page, candidate, observations, and a pre-resolved `CompiledExecutionSpec` containing form/profile, targets, ordered stages, retry transitions, implementations/checksums/device, parameters, validations, stopping policy, calibration, and retention. Unknown stages, missing models, unbounded cycles, and unsupported outputs SHALL be rejected before execution. Coordinate spaces SHALL use top-left origin, x-right/y-down, half-open bounds, pixel centers at `i+0.5,j+0.5`, and explicit `TransformRecord` composition and valid-region masks.

#### Scenario: Stage specification is not executable
- **WHEN** a profile contains an unknown stage, missing model, unbounded transition, or unsupported output
- **THEN** the module returns an explicit configuration/capability outcome without a hidden fallback

### Requirement: FR-OCR-008..013 and data model — observations, candidates, fields, and validation

The data contract SHALL preserve `SourceFile`, `ImageArtifact`, `PreparedPage`, `ArtifactAccess`, `AppliedExecution`, `ObjectCandidate`, `QualityMeasurement`, `TextObservation`, `FieldCandidate`, `FieldResult`, and `ValidationResult` semantics from the prototype. Candidates retain source/page/artifact/coordinate-space/geometry/visibility/form hypotheses/score scale/implementation/issues. Measurements retain region/scale/algorithm/unit/status/value/reason. Observations expose only actual text, regions, scores, and alternatives. Confidence probability SHALL be null unless calibrated with a calibration ID and scope.

#### Scenario: A field is resolved
- **WHEN** a field candidate is selected
- **THEN** its evidence, lineage, corrections, normalizations, validations, confidence scale, and source coordinate space are recoverable

### Requirement: NFR-OCR-001..004, SEC-OCR-001..004, and lifecycle — safe material state

Adapters SHALL expose declared capabilities and use explicit `AdapterDescriptor` identifiers, versions, model revisions, checksums, device, I/O, and parameter ranges. Pure normalizers/validators SHALL use only explicit versioned inputs. Material state SHALL follow `Allocated → Writing → Ready → Retained/Deleted`, with failures/cancellation going through `Aborted → Deleted`; ready handoff artifacts remain available until caller-owned expiry. Cache hits SHALL be recorded and timing/resource experiments SHALL disable or isolate cache. Temporary material, source lineage, and reference data SHALL be isolated by run and cleaned according to policy.

#### Scenario: A stage adapter lacks a capability
- **WHEN** a profile requires coordinates, alternatives, or scores not declared by the adapter
- **THEN** the module returns `CAPABILITY_MISMATCH` or an explicit unavailable capability and does not synthesize the missing output
