# Spec Delta

## ADDED Requirements

### Requirement: Candidate decision evidence is distinct from OCR

The recognition pipeline SHALL preserve Tesseract text, regions, variant identity, and declared adapter capabilities as the source OCR observation. An optional candidate decision stage MAY identify spans and field hypotheses, but it SHALL NOT claim to read pixels or replace the OCR observation.

#### Scenario: OCR observation is available
- **WHEN** the OCR adapter returns text and any supported regions or scores
- **THEN** the candidate stage receives that observation with its source and variant identity, and the final result can trace each candidate back to the observation

#### Scenario: Candidate stage is unavailable
- **WHEN** the candidate model is missing, incompatible, or not ready
- **THEN** the pipeline returns explicit unavailable/unreadable field evidence or a technical outcome and does not silently select a value from an unverified fallback

### Requirement: Candidate spans are field-scoped and label-bound

Candidate evidence SHALL identify a field kind, source observation, text span or region, raw text, score scale, model identity, and model version. A candidate SHALL be associated with a configured field label or coordinate region before it can be considered for selection. Candidate scores SHALL NOT be represented as calibrated probabilities unless a calibration identifier and scope are present.


#### Scenario: A birth date and registration date coexist
- **WHEN** OCR contains a registration date and a birth-date label with different dates
- **THEN** only the candidate attached to the birth-date label or configured birth-date region may enter birth-date validation; the registration date SHALL NOT be selected as `birth_date`

#### Scenario: Candidate has no field binding
- **WHEN** a model returns a plausible date, name, or place without a label/region binding
- **THEN** it remains evidence-only and the field result is not extracted from that candidate

### Requirement: Field selection remains deterministic and conservative

The final field decision SHALL combine candidate evidence with deterministic label/region binding, normalization, calendar or format validation, and cross-observation consistency. The pipeline SHALL select a field only when exactly one supported value remains under the active policy. Multiple distinct values, invalid dates, unsupported formats, or missing evidence SHALL produce an explicit field state and diagnostic rather than a guess.

#### Scenario: One candidate is consistent across observations
- **WHEN** one field candidate is uniquely bound, valid under the applicable rule, and consistent across the permitted OCR observations
- **THEN** the result contains the normalized field value, raw source text, evidence references, validation result, and model metadata

#### Scenario: Candidates conflict
- **WHEN** two or more distinct bound candidates remain for one field
- **THEN** the field is `conflict` or `unreadable`, all competing evidence is retained, and no candidate is silently preferred by score alone

### Requirement: Birth-date formats are resource-driven and semantically separated

The parser SHALL load month names and field labels from a versioned UTF-8 resource. It SHALL support configured numeric date forms and configured day-number/month-name/year-number forms, including Russian genitive month names when the resource declares them. It SHALL validate calendar boundaries and normalize a unique birth date to `YYYY-MM-DD`. Registration labels and birth labels SHALL remain separate.

#### Scenario: Month-name birth date is valid
- **WHEN** a birth-date-bound candidate contains a configured day, month name, and year
- **THEN** the parser validates the calendar date and returns the normalized ISO date only when the candidate is unambiguous

#### Scenario: Registration date is the only date
- **WHEN** OCR contains only a registration date
- **THEN** `birth_date` remains null and the result does not report the registration date as a birth date

### Requirement: Name and place fields preserve partial results

The pipeline SHALL attempt `full_name` and `birth_place` independently of `snils_number`. It SHALL preserve an independently confirmed field when another optional field is unreadable, conflicting, or absent. A field value SHALL remain null when the candidate is not uniquely bound and validated.

#### Scenario: Number is readable but optional fields are not
- **WHEN** SNILS passes checksum validation but name or birth-place evidence is missing or ambiguous
- **THEN** the result keeps the verified number, returns null for the unresolved optional fields, and records field-specific diagnostics without fabricating values

### Requirement: Model configuration is reproducible

Every candidate decision SHALL record the model identifier, model revision or checksum, tokenizer/resource revision, label schema version, threshold configuration, inference device, and CPU-thread policy. A requested model that does not satisfy the declared language/task contract SHALL be rejected before field selection.

#### Scenario: Decision checkpoint is an English classifier
- **WHEN** a checkpoint is declared for Russian field extraction but its verified contract is classification-only or does not support the required language/task
- **THEN** readiness fails or the checkpoint is restricted to its supported role; it SHALL NOT be used as a Russian field extractor by assumption
