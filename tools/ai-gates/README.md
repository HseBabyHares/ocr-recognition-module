# Codex and OpenRouter specification-drift review

The model layer runs only after deterministic gates and receives a bounded, redacted review package. It never receives repository secrets, an unrestricted external-fork checkout, or authority to edit code. Codex runs in a read-only isolated job; OpenRouter requires explicit data-transfer approval, distinct pinned model slugs, strict JSON Schema, no provider fallback, denied data collection, and ZDR routing.

`shadow` is the default. Strict mode requires a complete Codex review and a two-model OpenRouter quorum. Model consensus is not ground truth: only concrete high/critical findings tied to an explicit criterion and reproducible evidence may become candidate blockers, and product/architecture/risk/release decisions remain human-owned.
