# Tasks

## 1. Contract and model probe

- [x] 1.1 Define transport-neutral candidate types and the `CandidateExtractor` port, including raw span, field kind, source observation, region, score scale, model metadata, and rejection reasons.
- [x] 1.2 Add a versioned resource manifest for field labels, Russian genitive months, model identifier, tokenizer/resource revisions, thresholds, CPU threads, input length, candidate count, timeout, and memory budget.
- [x] 1.3 Run a CPU model-contract probe for `urchade/gliner_multi-v2.1`; record model revision, tokenizer revision, output shape, cold/warm latency, memory, CPU threads, and the observed Russian field-binding behavior.
- [x] 1.4 Pin the selected checkpoint, tokenizer, resource checksum, labels, thresholds, and CPU profile; retain the observed birth-date misclassification as a regression fixture.
- [x] 1.5 Keep GLiNER candidate-only for `full_name` and `birth_place` until binding and quality gates pass; keep `birth_date` rule-driven and reject model-only date decisions.

## 2. Candidate extraction and deterministic binding

- [x] 2.1 Implement an optional local candidate adapter over Tesseract `TextObservation` text, regions, variant identity, and declared capabilities.
- [x] 2.2 Preserve candidate evidence with source observation ID, text offsets, region coordinates, field label, raw span, score scale, model revision, and rejection reason.
- [x] 2.3 Bind candidates to configured labels and OCR regions before normalization; reject unbound candidates from final field selection.
- [x] 2.4 Implement deterministic field resolution for `full_name`, `birth_date`, `birth_place`, and `registration_date`, including numeric dates and Russian month-name dates from UTF-8 resources.
- [x] 2.5 Enforce registration-versus-birth separation, calendar validation, unique-candidate selection, conflict refusal, and no-guessing behavior.
- [x] 2.6 Extend the result schema with versioned `birth_place` evidence while preserving existing positional/internal callers and explicit null field states.

## 3. Runtime safety and operations

- [x] 3.1 Load model/tokenizer resources only from an allowlisted local cache or package and fail closed on missing or mismatched checksums.
- [x] 3.2 **Alpha scope completed; optional-stage backlog deferred.** The Alpha release keeps GLiNER candidate extraction out of final field selection. It accepts the existing allowlisted-resource, disabled-stage, bounded-input/output, cleanup, refusal, and safe model-unavailable evidence. Hard interruption/RSS/thread enforcement, a request-scoped budget, a real runtime owner, hard isolation, and representative benchmark evidence are post-Alpha backlog items.
- [x] 3.3 Disable runtime model downloads and public model network access in the test container/profile.
- [x] 3.4 **Alpha scope completed; operational telemetry deferred.** The Alpha release accepts the safe telemetry record shape and redaction tests. Request/attempt wiring, runtime ownership, and operational telemetry integration are post-Alpha backlog items. The Alpha release does not claim production operational telemetry for the optional candidate stage.
- [x] 3.5 Keep the ML dependency and model out of the production image until the model-contract and acceptance gates pass; keep the first integration test-only or experiment-scoped.

## 4. Evidence and regression tests

- [x] 4.1 Add UTF-8 text fixtures and authorized image fixtures with protected expected values; do not place real personal data in source code or chat.
- [x] 4.2 Add parser tests for numeric separators, day/month-name/year dates, all declared Russian genitive months, invalid calendar dates, registration-only dates, and birth-label/date-on-next-line cases.
- [x] 4.3 Add candidate-binding tests for full name, birth place, label/region mismatch, duplicate candidates, conflicts, unavailable model, and unsupported score semantics.
- [x] 4.4 Add end-to-end OCR fixture tests proving that a valid SNILS number can coexist with unreadable optional fields and that no registration date is returned as birth date.
- [x] 4.5 Add a CPU benchmark with declared warmup, sample count, memory scope, latency aggregation, and predeclared acceptance boundary; leave the result blocked when the boundary or representative corpus is absent.
- [x] 4.6 Add evidence for safe logs, temporary cleanup, resource checksums, model-unavailable behavior, and refusal paths.

## 5. Test deployment and documentation

- [x] 5.1 Add the optional candidate-stage dependency and model resources only to the test/experiment packaging path after the probe passes.
- [x] 5.2 Keep the existing isolated Helm test profile as optional historical evidence only; Helm/Kubernetes is deferred as a release/deployment gate and does not substitute for the Docker Compose MVP gate.
- [x] 5.3 Treat any existing Helm-managed smoke and fixture evidence as test-only, not as first-release or production acceptance; the first release verification target is the RabbitMQ Docker Compose profile.
- [x] 5.4 Record model-contract, fixture, CPU, security, and deployment evidence with explicit `passed`, `failed`, `blocked`, and `not-run` states.
- [x] 5.5 Update current-state traceability with the selected checkpoint, known limits, real-image validation boundary, and any residual risk; do not mark production acceptance from test-only evidence.
