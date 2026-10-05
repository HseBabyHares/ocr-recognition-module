# Spec Delta

## Purpose

Migrates the prototype experimental-runner and evaluator contract into OpenSpec without adding experiment dependencies to the production OCR runtime.

## ADDED Requirements

### Requirement: FR-EXP-001 — stage selection and resolved variants

The runner SHALL support `end_to_end`, `component`, and `replay_metrics` modes. `ExperimentPlan` SHALL include `experiment_id`, `plan_version`, `plan_hash`, corpus manifest/version/sample IDs/checksums/partitions, variants, pair order, seed, repeats, resources, metrics, hard boundaries, failure rules, output/access/retention policy, and intermediate-material mode. Every variant SHALL select adapters by identifier and MAY enable or disable only declared stages without changing unrelated stage code. Every adapter/model reference SHALL resolve code/weight checksums, defaults, device, language, decoding, extraction, correction, normalization, calibration, cache, warmup, and thread/process parameters before execution. The fully resolved profile, including defaults, SHALL be persisted. The working manifest SHALL omit truth values, correct forms, and correct geometry; component assistance SHALL be marked.

#### Scenario: Variant resolution fails
- **WHEN** an adapter, model, device, permission, checksum, or required parameter is unavailable
- **THEN** the variant is excluded with a reason before the first comparison and no fallback is selected

### Requirement: FR-EXP-002 — complete sample/repeat records

For every planned `(sample_id, variant_id, repeat_id)` the runner SHALL persist one terminal `SampleRunRecord` with `group_id`, mode, assistance/test doubles, input and resolved-spec hashes, applied execution, status `ok|partial|failed|cancelled|limit_exceeded|not_run`, reason/failed stage, module result reference, stage records, wall/CPU time, peak memory, cache hits, and warmup state. A missing pair blocks the aggregate; reruns receive a new repeat ID and preserve the prior failure.

#### Scenario: Planned pair is missing
- **WHEN** a pair has no terminal record or a rerun overwrites its prior record
- **THEN** the aggregate is blocked and the original record remains available for audit

### Requirement: FR-EXP-003 — truth isolation and component assistance

The working OCR stages and end-to-end experiment SHALL NOT receive reference values, correct angles or geometry, correct form labels, or hidden field values. The protected reference set SHALL be accessible only to the independent evaluator. Substitution of a known crop, form, geometry, or field is allowed only in an explicitly marked component mode and SHALL be recorded in the sample result; such a result SHALL NOT be presented as an end-to-end score.

#### Scenario: Component mode uses known assistance
- **WHEN** a component experiment injects a known crop, form, geometry, or field dependency
- **THEN** the result marks the injected dependency and is excluded from end-to-end scoring

### Requirement: FR-EXP-004 — independent evaluation and replay

The evaluator SHALL write `EvaluationRecord` values from saved predictions and protected truth without OCR execution, including evaluator/version, text normalization policy, metric, stratum, unit, numerator, denominator, value/null, interval or reason, and exclusions. Replay SHALL use the original manifest and resolved specification. Metric replay SHALL NOT load an OCR model. The evaluator SHALL reject incompatible schemas, missing pairs, checksum mismatches, or undeclared substitutions. Selection SHALL record hard constraints, every variant, per-constraint exclusions, non-dominated variants, and the final rule. A post-hoc constraint creates a new comparison.

#### Scenario: Metrics are replayed
- **WHEN** saved predictions and a compatible protected reference set are provided
- **THEN** metrics are recomputed without OCR and any closed-corpus or publication limitation is recorded

### Requirement: FR-EXP-005 — quality and cost accounting

Experiments SHALL report exact field extraction, refusal behavior, false output on negative examples, corruption of correct values, form and geometry outcomes, cold and warm time, stage time, model/image call count, memory, repeats, cache state, and technical outcomes. Cost records SHALL separate cold-start, warm, full-call, and stage time, model/image variant counts, CPU and memory, and repeat costs. CER MAY be reported as an auxiliary metric but SHALL NOT replace exact-field, refusal, false-output, or corruption metrics. Grouped resampling SHALL keep all photos and variants of one physical document together.

#### Scenario: Variant violates a hard constraint
- **WHEN** a variant improves an average text-error metric but violates locality, resource, output, false-output, refusal, or declared quality constraints
- **THEN** it is not selected as the winner and the exclusion reason is recorded
