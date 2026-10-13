# Proposal

## Why

The current OCR pipeline extracts text with Tesseract but resolves `full_name`, `birth_date`, and `birth_place` with brittle field rules. A second, local CPU candidate-extraction stage can use OCR text and regions to identify which field a span belongs to, while deterministic validators retain final authority. This is needed now because the real-SNILS test confirmed that the number was extracted but the name and birth fields were not reliably resolved, and a registration date was incorrectly treated as a birth date.

The selected candidate checkpoint is `urchade/gliner_multi-v2.1`, chosen for Russian-capable multilingual extraction. It is still not authoritative: the probe observed useful person/place candidates but misclassified a birth date as a registration date, so deterministic label/region binding remains mandatory and date selection stays rule-driven.

## What Changes

- Add an optional local GLiNER candidate stage after Tesseract text/TSV extraction.
- Preserve Tesseract text, coordinates, variant identity, and model scores as evidence; do not replace OCR or validators.
- Extract candidate spans for `full_name`, `birth_date`, `birth_place`, and `registration_date`.
- Bind candidates to labels and regions before deterministic validation.
- Normalize numeric and Russian month-name dates, reject invalid calendar dates, and prevent registration dates from becoming birth dates.
- Resolve fields only when evidence is unique and consistent across applicable OCR observations; otherwise return an explicit conflict/unreadable result.
- Pin the selected model, tokenizer, resource checksum, threshold, CPU-thread policy, and schema version in applied execution evidence when the optional stage is enabled.
- Add fixture-driven tests, a model-contract probe, CPU latency/memory measurements, and refusal/conflict scenarios; keep hard runtime bounds and operational telemetry as prerequisites for later enablement, not as a first-version release gate.
- Keep model loading optional and fail closed: model absence or incompatibility must produce unavailable candidate evidence, not a guessed field value.

## Capabilities

### New Capabilities

None. This change extends the existing OCR recognition and operations contracts.

### Modified Capabilities

- `ocr-recognition`: add an evidence-only candidate decision stage, field/label/region binding, Russian date-format handling, and explicit model-unavailable/conflict behavior.
- `ocr-operations`: add local model/resource allowlisting, startup checksum checks, CPU resource limits, reproducible model configuration, and safe telemetry for the optional decision stage.

## Non-goals

- GLiNER will not read pixels or replace Tesseract/OpenCV.
- GLiNER output will not be accepted as a final value without label/region binding and deterministic validation.
- This change does not add production SIRD/gRPC/mTLS/RabbitMQ integration. The Docker Compose RabbitMQ MVP is the first integration gate; Helm/Kubernetes production deployment remains deferred.
- This change does not claim successful real-image validation until a real image is available as a repository-owned or otherwise authorized fixture.
- This change does not use the user's real SNILS image in source code, artifacts, or chat.

## Risks and Open Questions

- The selected multilingual checkpoint is CPU-capable but may exceed the current 1 GiB test-pod memory limit or violate the CPU latency budget.
- Its observed date-label confusion is a known risk; deterministic binding must prevent it from changing `birth_date`.
- Model scores are not calibrated probabilities and must not be exposed as accuracy or used alone for acceptance.
- Exact ADI REG labels and layouts require real fixtures; missing fixtures remain an explicit validation boundary.
