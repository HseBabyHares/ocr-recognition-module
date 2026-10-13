# Design

## Context

The current recognition path owns bounded OpenCV preprocessing and Tesseract reads. `TextObservation` already carries raw text, regions, word scores, adapter identity, and descriptor metadata. Optional field extraction is currently local and resource-driven, while the test HTTP adapter serializes the recognition result. See `proposal.md` for motivation.

The selected candidate checkpoint is `urchade/gliner_multi-v2.1`. A CPU probe on the text fixture returned useful person and place candidates, but classified the birth date as `registration date`; the checkpoint is therefore suitable only as candidate evidence, with deterministic label/region binding and rule-driven date selection remaining authoritative.

The candidate model is an untrusted inference component. The model, tokenizer, and resources are external runtime artifacts that require a versioned contract and checksum.

## Goals / Non-Goals

**Goals:**

- Add a transport-neutral candidate-extraction port after Tesseract observations.
- Preserve source observation, text span, coordinates, variant identity, score scale, and model metadata.
- Bind candidates to field labels/regions and run deterministic validation before selection.
- Keep the model optional, locally pinned, CPU-bounded, and fail-closed.
- Make registration-vs-birth separation and conflict handling observable.
- Keep Russian labels/months in UTF-8 resources rather than Python source literals.
- Produce reproducible fixture, model-contract, resource, and performance evidence.

**Non-Goals:**

- Replacing Tesseract or reading pixels with GLiNER.
- Treating model scores as calibrated probabilities or final truth.
- Adding production SIRD/gRPC/mTLS/RabbitMQ integration.
- Enabling a model in the production image before the model-contract and CPU gates pass.

- Validating a private real document without an authorized fixture.

## First-version disposition

The optional candidate stage remains test/experiment-scoped and disabled for final field selection in the first version. The deterministic OCR path is the MVP path. Docker Compose is the first integrated release gate; Helm/Kubernetes is deferred and historical Helm smoke evidence cannot substitute for Compose acceptance. Tasks 3.2 and 3.4 remain prerequisites for enabling the candidate model in a long-lived runtime; unit tests and test-only deployment evidence do not substitute for hard timeout/memory enforcement, correct backend thread configuration, request-scoped call budgets, or wired safe telemetry.

## Decisions

### 1. Use a candidate port, not a direct model dependency

Define a small adapter boundary that accepts an OCR observation plus declared labels and returns candidate spans. The recognition service depends on this port, not on `gliner`, Transformers, or a specific checkpoint. The adapter descriptor records model ID, revision/checksum, tokenizer/resource revision, device, thread count, and supported output capabilities.

This keeps the existing Tesseract-only path usable and allows a test/experiment adapter to be exercised without placing a large ML dependency in the base production package.

### 2. Use the selected Russian-capable checkpoint only as candidate evidence

The first implementation targets `urchade/gliner_multi-v2.1` behind the candidate port. Its model revision, tokenizer revision, checksum, CPU profile, and probe evidence are pinned. The `fastino/GLiNER2.5-Decide` checkpoint is not selected for Russian field extraction because its published contract is English decision/classification.

The observed birth-date misclassification is a required regression case: GLiNER may propose `registration_date`, but a printed birth label/region and deterministic parser decide whether a date can enter `birth_date`.

### 3. Run field binding before normalization

For each OCR observation:

1. retain Tesseract text and regions;
2. ask the candidate adapter for spans for `full_name`, `birth_date`, `birth_place`, and `registration_date`;
3. bind spans to configured labels and/or field regions;
4. reject candidates with no binding;
5. normalize and validate only bound candidates;
6. aggregate identical candidates across allowed observations;
7. select only one unique valid value.

A date classified by the model as `registration_date` cannot enter `birth_date` validation. A model label never overrides an explicit conflicting document label.

### 4. Keep deterministic validators authoritative

The validators own:

- calendar validity;
- numeric and resource-declared month-name parsing;
- registration/birth field separation;
- name/place non-empty and field-region checks;
- cross-variant agreement;
- conflict/refusal behavior.

The model only proposes spans and field hypotheses. The final response retains raw text, candidate span, model score, label/region binding, validation, and rejection reason.

### 5. Add `birth_place` as an append-only result extension

`birth_place` is appended to the result data structure with a default for source compatibility. The schema/version metadata is updated when the field is exposed through the API. Existing consumers that ignore unknown fields remain compatible; exact response contracts must be updated in the same change.

### 6. Keep resources and models immutable

OCR labels, Russian genitive months, and field-binding configuration live in versioned UTF-8 resource files. Model and tokenizer files are loaded from an allowlisted local cache or package and verified by checksum. The active profile records the resource/model revisions. Runtime downloads are disabled.

### 7. Bound CPU inference and fail closed

The adapter uses a fixed CPU-thread count, maximum text length, maximum candidate count, timeout, and memory budget. Warmup is excluded from measurements. Missing or exceeded limits yield unavailable/limit evidence; they do not trigger a hidden fallback or guessed field.

### 8. Integrate only after a probe and fixture gate

The implementation sequence is: contract probe, adapter, deterministic binding, fixtures, refusal/conflict tests, CPU benchmark, then optional test deployment. The named checkpoint is not enabled for final field decisions until it passes Russian field-binding cases, registration separation, invalid-date cases, conflict cases, and resource limits.

## Data Flow

```text
encoded image
  -> bounded OpenCV variants
  -> Tesseract TextObservation(text, regions, scores, variant)
  -> optional CandidateExtractor
  -> label/region binding
  -> deterministic field normalizers and validators
  -> unique field result or explicit refusal/conflict
```

## Risks / Trade-offs

- A 300M+ model can exceed the current 1 GiB test-pod limit; the deployment must measure memory before enabling it.
- Multilingual zero-shot extraction may be weaker on Russian forms than a domain-specific model; the fixture gate must remain independent of model confidence.
- Keeping the model optional means some fields can remain unreadable when the model is absent. This is safer than silently selecting OCR text by plausibility.
- GLiNER output can disagree with printed labels. The binding layer must prefer explicit labels/regions and record disagreement instead of resolving by score.
- Real-image validation remains unavailable until an authorized fixture is stored outside chat. Text fixtures prove parser semantics, not camera/OCR quality.
