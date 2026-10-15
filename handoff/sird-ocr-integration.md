# SIRD OCR integration handoff

## Owner decisions

- RabbitMQ 4.3 (`rabbitmq:4.3-management`, single node) is the workflow transport. Durable quorum queues carry task, result, retry, and terminal routes through `aio-pika`. The owner removed Kafka from the repository on 2026-10-13.
- RustFS is the local object-store profile.
- Workload identity uses mTLS client certificates and RabbitMQ broker authorization. The owner dropped SPIFFE/SPIRE on 2026-10-13. The old local profile is isolated in `integration/spire/` (`integration/spire/compose.yml`, `integration/spire/start.sh`) and is not supported.
- Task and Process APIs are trusted-SIRD-backend-only.
- SIRD owns result retention; integration uses a 12-hour fallback.
- OCR runtime remains broker- and database-independent; workflow code lives in `integration/`.
- Prototype ADR-OCR-005 remains frozen migration evidence. Its S3-Minio storage choice is superseded by RustFS in the OpenSpec change; the current transport is the RabbitMQ 4.3 profile.

## Local profile commands

```bash
integration/start.sh

docker compose -f compose.integration.yml ps

openspec validate specify-sird-ocr-integration --strict
node tools/harness/checks/run-all.mjs
```

The local profile publishes RabbitMQ (AMQPS `5671`, management `15672`), PostgreSQL (`5432`), and RustFS (`9000`, `9001`) only on loopback. RabbitMQ disables plain TCP listeners and requires TLS 1.2 with a verified client certificate (`integration/rabbitmq/rabbitmq.conf`). `integration/rabbitmq/definitions.json` declares vhost `/sird`, direct exchanges `sird.workflow` and `sird.workflow.dlx`, and quorum queues `sird.task.v1`, `sird.result.v1`, `sird.task.retry.v1` (1-second TTL, dead-letters back to `sird.task.v1`), and `sird.task.terminal.v1`. Migrations are under `integration/migrations/`; migration 005 adds durable `next_attempt_at` retry scheduling.

## Current evidence

- Root tests: 186 passed.
- Integration tests: 76 passed.
- Verification tests: 25 passed.
- Experiment tests: 6 passed.
- Test adapter tests: 3 passed.
- Ruff lint and format pass across all package paths.
- Strict OpenSpec validation passes.
- Strict architecture validation passes: 6 components, 6 views, 8 DFD elements, 10 flows, and 62 explicit STRIDE threats. This count predates the SPIFFE/SPIRE removal of 2026-10-13. The Archify DFD now has 7 elements and 8 flows; the STRIDE validation was not executed again.
- The threat model is DFD-backed: `security/threat-model/dfd.json` is linked to the English Archify source `architecture/sird-ocr-dfd.architecture.json` and delivered artifact `architecture/rendered/sird-ocr-dfd.html`; the adversary model is `security/threat-model/adversary-model.json`.
- STRIDE coverage is complete for 18 DFD subjects and 108 subject/category cells: 89 concrete threat dispositions and 19 subject-specific not-applicable dispositions; no catch-all or unreviewed threat reference remains.
- Each threat record now declares a primary DFD subject and, where a control spans multiple boundaries, explicit `relatedSubjects`; coverage references are traceable to those declarations.
- Archify DFD specification validation passes 9/9; delivered artifact SHA-256 is `6ee8b5d9f7d362f2c5e59d9a17a13101885be4539e83686fdf3b3ed63af8c2c2` and automated browser visual checks pass at 1440x900, 1600x1000, 1920x1080, and 2048x1320 in light/dark captures. Human perceptual review remains pending.
- Archify system architecture specification validation passes 9/9; delivered HTML has SHA-256 `32ddcaad099f9b4d1d6ded470a3a1e69f05e0202ccf6d175385d6962125c1a17` and passes automated browser visual checks at 1440x900, 1600x1000, 1920x1080, and 2048x1320 in light/dark captures. Human perceptual review remains pending.
- The architecture explicitly separates current Python workflow/OCR/local-profile evidence from target mTLS transport and production certificate deployment evidence. The experiment-to-verification edge is evidence-only, not a runtime dependency.
- Security preflight passes. Quality/container harness profiles remain advisory `not-configured`.
- `compose.integration.yml` defines healthchecks for the RabbitMQ, PostgreSQL, and RustFS containers. This handoff records no container health observation for the RabbitMQ profile.

The architecture registry is in `architecture/`; generated Archify HTML is excluded from garbage-collection size checks. The hand-authored DFD, adversary model, and STRIDE coverage remain visible to GC.
- Final GC inventory reports 2 unaccepted findings: one low `python-clone` clone class in production Python and one medium `large-file` finding for `integration/src/sird_workflow/process.py`. Production duplication is 16/8,085 Python LOC (0.1979%); tests are report-only at 144/4,511 LOC (3.1922%); repository-wide ratio is 160/12,596 LOC (1.2702%). Documentation and lockfiles are outside the application-code duplication scope; FADD internals and generated Archify output remain excluded from GC.
- The Python clone metric uses six-statement/50-token canonical token shingles, preserves attribute and callee names, and reports one finding per clone class with coalesced maximal locations. Clone fingerprints use the left-most window digest and are compatible with `quality/baseline.json` acceptance. It does not detect same-file clones, clones below the shingle threshold, or semantic near-clones; the repeated six-copy `_require_text` helper is four statements/23 AST nodes and is intentionally unreported.
## Open evidence and design gaps

- The `sird-ocr-server` gRPC entry point serves `sird.ocr.v1 OcrService` (`contract_version` must be `sird.ocr.v1`). It verifies the eleven-claim HMAC capability from sird-process-service and reads the source from S3 by the signed `object_key` claim; `object_id` stays opaque. The image is `Dockerfile`; the chart is `deploy/helm/sird-ocr`. One local Task API → Process → Recognition run reached `RECOGNIZED` with a `PARTIAL` result; result content was not reviewed.
- The policy ids, name order, capability issuer, audience and key id are proposals in sird-process-service `deploy/.env.example`; team agreement is pending. The `object_key` claim needs the matching sird-process-service change. The server has no `grpc.health.v1` service, so the chart probes TCP. S3 reads do not pin an object version id.
- Production certificate issuance and rotation for mTLS, RabbitMQ broker authorization, and per-service identity mapping are not deployed. The local profile uses one development user `sird` on vhost `/sird`; it has no per-workload RabbitMQ users or permissions.
- OS-level decoder isolation, model execution, labeled corpus acceptance, numeric thresholds, retention cleanup, and OCR/task p99 are not verified.
- No live RabbitMQ consumer smoke with broker acknowledgement is recorded.
- Archive requires explicit human approval.

## Next smallest slice

Run the live PostgreSQL/RabbitMQ smoke against the final tree over AMQPS with the client certificates from `integration/rabbitmq/generate-certs.sh`. Verify publisher confirms, mandatory returned-message handling, manual acknowledgement after durable result/terminal outbox state, and the retry and terminal routes. Record only observed facts. Do not claim production readiness without owner-provided model, corpus, thresholds, and deployment identity evidence.
