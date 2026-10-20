# Test protocol for IDRS-TP-20261020-01

This protocol records the actual runs against the test plan IDRS-TP-20261020-01, version 1, dated 20 October 2026. It uses the plan statuses: PASS, FAIL, BLOCKED and NOT RUN. A status applies only to the stated level and baseline. A component PASS does not replace the system run that the plan requires.

The protocol contains no personal data. Every document in the runs is synthetic. Benchmark rows give aggregates only.

## Run record

| Field | Value |
| --- | --- |
| Protocol date | 2026-10-20 |
| Executor | Dmitry Alekseev (recognition) |
| Reviewer | TBD (plan §13: a person other than the executor) |
| OCR baseline | `sird-recognition` commit `7fd8f0a` |
| Demo baseline | `sird-demo-spa` commit `759b8e4` |
| Management UI baseline | `sird-frontend` commit `5cc637a (local on main, not pushed yet)` |
| OCR engine | Tesseract 5.5.3; checksums in `artifacts/benchmark/pr2/environment.json` |
| Host | One shared developer workstation, 20 CPU threads; not the measured-test hardware of D-04 |

## Summary

| Area | Status | Reason |
| --- | --- | --- |
| Overall MVP | NOT RUN | The deployed system chain was not executed. Plan §8 requires all MUST requirements and PR-1 to PR-5. |
| OCR component (ST-03, ST-04, PR-2) | PASS | Frozen synthetic benchmark plus unit and gRPC tests. |
| Demo consumer (ST-07, ST-11) | PASS for ST-07 and automated ST-11; NOT RUN for manual ST-11 | Playwright runs against the demo application. |
| Management UI (ST-06, ST-11) | PASS for ST-06 and automated ST-11; NOT RUN for manual ST-11 | Playwright runs against the management UI; ST-06 on real services. |

## System acceptance scenarios

| ID | Owner | Level | Status | Evidence | Note |
| --- | --- | --- | --- | --- | --- |
| ST-01 | Onar Shamaev | System | NOT RUN | — | Upload, batch and idempotency belong to Task Service. |
| ST-02 | Onar Shamaev | System | NOT RUN | — | Depends on D-01 and D-02. |
| ST-03 | Dmitry Alekseev | OCR component | PASS | [`pr2-benchmark-report.json`](pr2-benchmark-report.json), `tests/test_form_classifier.py`, `tests/test_ocr_server.py` | Real Tesseract on synthetic renders of `snils_card`, `adi_reg_2019` and `adi_reg_2023`, photo and scan. Form accuracy 0.993 on 144 documents. The one miss is a `snils_card` photo that was rejected as `FORM_UNSUPPORTED`; it is a safe refusal, not a false value. Unsupported and ambiguous pages return `SUBJECT_REJECTED` with `FORM_UNSUPPORTED` or `FORM_AMBIGUOUS`. |
| ST-03 | Dmitry Alekseev | System | NOT RUN | — | The deployed Task → Process → OCR chain was not run. D-03: the mapping of `adi_reg_2019` to the PFR notice and `adi_reg_2023` to the SFR notice needs owner confirmation. |
| ST-04 | Dmitry Alekseev | OCR component | PASS | [`pr2-benchmark-report.json`](pr2-benchmark-report.json), `tests/` | 24 negative documents, 0 false acceptances. A checksum-invalid SNILS is refused. A technical failure maps to a technical code, not to a subject rejection. |
| ST-04 | Dmitry Alekseev | System | NOT RUN | — | Public nullability depends on D-01. |
| ST-05 | Onar Shamaev | System | NOT RUN | — | Owner isolation and flush belong to Task Service. |
| ST-06 | Sergey Galichenko, Onar Shamaev | Management UI with real ACL and Keycloak (Compose profile `acl`) | PASS | `sird-frontend` `e2e/real/st06-credentials.spec.ts`, `E2E_REAL=1 bunx playwright test`: 6 passed, 0 failed, 0 skipped | 401 without a token; 403 for a developer on admin API and pages; client create, list, rotate and delete with old-secret invalidation; owner isolation; user invite, find and deactivate; audit records without a secret. Residual risk: `GET /app/credentials/{app_id}` of the ACL contract still returns `client_secret` on the wire; the portal hides it. |
| ST-07 | Dmitry Alekseev | Demo consumer | PASS | `sird-demo-spa` `e2e/review.spec.ts`, `bun run test:e2e` on chromium, firefox and webkit: 123 passed, 0 failed, 0 flaky | The specialist corrects a field and confirms the result with the keyboard only. An invalid SNILS or date blocks the confirmation. Corrections stay in the browser and do not go to SIRD. The timing log stores no field values and exports as JSON or CSV. The runs use a mock Consumer API, not the deployed chain. Known limits: a reload before confirmation writes no retake entry; two tabs overwrite one log. |
| ST-08 | Dmitry Alekseev | OCR component | PASS | `tests/test_ocr_server.py::TestOcrServer::test_latency_has_status_attributes_only` | The OCR server records the histogram `sird.ocr.recognition.duration` in seconds. Its only attributes are `sird.ocr.operation_status` and `sird.ocr.task_outcome`. No field value, document byte, object key or token is an attribute. |
| ST-08 | Sergey Galichenko | System | NOT RUN | — | The cross-service trace, the platform dashboard and the Consumer API percentiles were not run. |
| ST-09 | Sergey Galichenko | System | NOT RUN | — | Depends on D-04. |
| ST-10 | Onar Shamaev, Sergey Galichenko | System | NOT RUN | — | Fault injection on the deployed chain was not run. |
| ST-11 | Dmitry Alekseev | Demo consumer | PASS | `sird-demo-spa` `e2e/a11y.spec.ts`, `e2e/review.spec.ts`; `@axe-core/playwright` 4.14.0 tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`; 0 violations | Automated scan and keyboard journey only. The scan uses reduced motion: a 150 ms button transition gave a false contrast result. Screen-reader and manual WCAG 2.2 checks in `docs/accessibility-review.md` are NOT RUN. |
| ST-11 | Sergey Galichenko | Management UI, automated and keyboard | PASS | `sird-frontend` `e2e/a11y.spec.ts`, `e2e/keyboard.spec.ts` on chromium, firefox and mobile-320: 96 passed, 0 failed; axe-core 4.13.0 tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`; 0 violations | WebKit did not start: the host lacks system libraries. Grafana iframes and the Keycloak sign-in page are outside the axe scan. |
| ST-11 | Sergey Galichenko | Management UI, screen reader and manual WCAG 2.2 | NOT RUN | `sird-frontend` `docs/accessibility-review.md` (checklist) | Needs a person: screen-reader pairs and the manual criteria 1.4.4, 1.4.11, 1.4.12, 2.4.7, 2.4.11, 2.5.3 and 3.1.2. |

## Measured targets

| ID | Owner | Status | Evidence | Note |
| --- | --- | --- | --- | --- |
| PR-1 | Sergey Galichenko | NOT RUN | — | Depends on D-04. |
| PR-2 | Dmitry Alekseev | PASS | [`pr2-benchmark-report.json`](pr2-benchmark-report.json) | OCR component level on the frozen synthetic corpus: 120 positive documents, three layouts, photo and scan. Exact-match accuracy: SNILS 0.992, full name 0.908, birth date 0.967; every field is at or above 0.90. Lowest stratum: `snils_card` full name 0.80, which the plan does not gate. Benchmark seeds differ from the development seeds 0 and 3. The benchmark's own p99 latency guard (10 s) failed at 10.2 s. The host was shared: load average median 18.5, maximum 72 on 20 threads. Plan §9 treats this latency figure as unreliable; PR-2 has no latency criterion. |
| PR-3 | Elina Dyukina | NOT RUN | — | The controlled pilot needs two evaluators and two matched sets of ten documents. |
| PR-4 | Sergey Galichenko | NOT RUN | ST-08 OCR component row | The OCR side records the latency histogram (ST-08, OCR component). Platform p50, p95 and p99 for the Consumer API and the measurement window are not recorded. The plan has no numeric SLO. |
| PR-5 | Onar Shamaev | NOT RUN | — | Needs a timestamped trace of the deployed chain. |

## Open decisions

| ID | Status in this protocol |
| --- | --- |
| D-01 | Open. Blocks the system PASS of ST-02 and ST-04. |
| D-02 | Open. Blocks the system PASS of ST-02 and ST-10. |
| D-03 | All three forms exist in OCR and have real-OCR synthetic evidence. The layout mapping needs owner confirmation. |
| D-04 | Open. The PR-2 corpus is frozen in `tools/benchmark/pr2-corpus.lock.json`; the PR-1 profile and hardware are not frozen. |

## How to repeat the OCR rows

```bash
uv run pytest tests
uv run --with pillow pytest tools/corpus
uv run python tools/benchmark/pr2_benchmark.py run
uv run python tools/benchmark/pr2_benchmark.py score
```
