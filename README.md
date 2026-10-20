# SIRD Recognition

Stateless OCR runtime for extracting structured data from scanned or photographed SIRD documents.

The repository contains the OCR computation boundary, a gRPC adapter, a separate workflow package, a test-only HTTP adapter, deterministic experiments, and executable verification oracles.

## Overview

The runtime processes one bounded recognition request at a time. It validates the request and context, runs the stage ports, and returns fields, observations, diagnostics, and technical failure information. The runtime does not own task state, queues, databases, user accounts, or result retention.

The project is useful for:

- integrating OCR computation into a caller-owned workflow;
- testing request and response contracts at the gRPC boundary;
- running deterministic experiments against the same stage ports;
- checking architecture and acceptance constraints with executable oracles.

The prototype documentation describes the document domain as SNILS-related forms. The implementation and integration boundaries remain the source of truth for executable behavior.

## Scope

This repository owns:

- request validation and stateless stage orchestration;
- `Prepare`, `Probe`, `Resolve`, and `ExecuteProfile` stage contracts;
- OCR, candidate-extraction, field-result, and technical-status models;
- synchronous unary gRPC request and response mapping;
- the `sird-ocr-server` gRPC service, its image, and its Helm chart;
- the separate `sird-workflow` integration package;
- test-only HTTP and in-memory task adapters;
- deterministic experiment and verification packages;
- repository-local security, quality, architecture, container, and delivery checks.

This repository does not own:

- production task storage or result retention;
- authentication, user interfaces, or final business acceptance;
- a production broker deployment;
- production certificate issuance and rotation for mTLS;
- a production OCR model or an accepted labeled corpus.

Workload identity uses mTLS client certificates and RabbitMQ broker authorization. Production certificate issuance is not yet present. The owner dropped SPIFFE/SPIRE on 2026-10-13. The old local profile is isolated in `integration/spire/` (`integration/spire/compose.yml`) and is not supported. See [`handoff/sird-ocr-integration.md`](handoff/sird-ocr-integration.md).

## Quick start

The supported local toolchain is:

- Python 3.14 or newer;
- [`uv`](https://docs.astral.sh/uv/);
- Node.js for repository delivery checks;
- a system that can install the OpenCV wheel selected by `uv`.

Start from a fresh checkout:

```bash
# Clone the repository using the URL provided by your project owner, then:
cd sird-recognition
uv sync --dev
```

The root package declares `opencv-python-headless` as its runtime dependency. The root `dev` group also includes the gRPC runtime and generator used by the checked-in contract tests.

### Verify the root package

```bash
uv run --project . --group dev pytest -q tests
```

A successful run exits with status `0`.

This path covers the transport-neutral runtime and its gRPC contract tests. It does not start Docker, a broker, a database, or a model download.

## Run the OCR service

The deployable module is the gRPC server `sird-ocr-server`. It serves `sird.ocr.v1.OcrService/Recognize` on port `50051`. Its only caller is `sird-process-service`. The server checks the HMAC capability from Process, reads the image from S3 by the signed `object_key`, and returns the recognition result.

| What | Where |
| --- | --- |
| Image source | [`Dockerfile`](Dockerfile) at the repository root |
| Published image | `ghcr.io/hsebabyhares/sird-ocr:main` and `:sha-<commit>`, built by [`sird-ocr-image.yml`](.github/workflows/sird-ocr-image.yml) on every push to `main` |
| Helm chart | [`deploy/helm/sird-ocr/`](deploy/helm/sird-ocr/README.md) |
| Settings | [`src/sird_recognition/ocr_server.py`](src/sird_recognition/ocr_server.py) docstring |

The GHCR package is private. Log in with a GitHub token that has `read:packages`:

```bash
docker login ghcr.io -u <github-user>
```

### Settings

| Variable | Required | Value |
| --- | --- | --- |
| `CAPABILITY_KEYS` | yes | `kid:hex` with a 64-hex key, for example `v1-k1:<hex>`. Process must sign with the same key id and key. |
| `CAPABILITY_ISSUER`, `CAPABILITY_AUDIENCE` | yes | Must equal the Process values, for example `process-service` and `ocr.service`. |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | yes | The object store and bucket where `sird-task-service` stores uploads. |
| `S3_REGION` | no | Default `us-east-1`. |
| `SIRD_OCR_LISTEN` | no | Default `[::]:50051`. |
| `SIRD_OCR_MAX_WORKERS` | no | Default `4`. |
| `SIRD_OCR_POLICY_ID` | no | The only accepted `input_policy_id`, for example `snils-card-input`. Empty accepts any. |
| `SIRD_OCR_TLS_CERT`, `SIRD_OCR_TLS_KEY`, `SIRD_OCR_TLS_CLIENT_CA` | no | All three enable mTLS. None serves plaintext gRPC. |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` or `OTEL_EXPORTER_OTLP_ENDPOINT` | no | Enables OTLP/HTTP export of the `sird.ocr.recognition.duration` histogram (seconds), for example `http://otel-collector:4318`. Its only attributes are `sird.ocr.operation_status` and `sird.ocr.task_outcome`. |

The server stops at start when a required variable is missing.

### Docker

This example uses the RustFS object store from `integration/start.sh` on `127.0.0.1:9000`. Use the same key in `CAPABILITY_KEYS` and in the Process `CAPABILITY_KEY`.

```bash
docker run --rm --read-only --tmpfs /tmp \
  --add-host=host.docker.internal:host-gateway \
  -p 127.0.0.1:50051:50051 \
  -e CAPABILITY_KEYS="v1-k1:<64 hex, same as Process CAPABILITY_KEY>" \
  -e CAPABILITY_ISSUER=process-service \
  -e CAPABILITY_AUDIENCE=ocr.service \
  -e S3_ENDPOINT=http://host.docker.internal:9000 \
  -e S3_BUCKET=<bucket of sird-task-service> \
  -e S3_ACCESS_KEY=<RUSTFS_ACCESS_KEY> \
  -e S3_SECRET_KEY=<RUSTFS_SECRET_KEY> \
  ghcr.io/hsebabyhares/sird-ocr:main
```

To build the image from the checkout, run `docker build -t sird-ocr:local .` and use `sird-ocr:local`. The server has no `grpc.health.v1` service. An empty `Recognize` request returns `INVALID_ARGUMENT` when the server is up.

### Kubernetes

The chart [`deploy/helm/sird-ocr/`](deploy/helm/sird-ocr/README.md) gives the install commands, the secrets, and the matching `sird-process-service` settings (`OCR_TARGET`, `OCR_PLAINTEXT`, `CAPABILITY_*`). The short form:

```bash
helm install sird-ocr deploy/helm/sird-ocr \
  --set image.tag=main \
  --set imagePullSecrets[0].name=ghcr-pull \
  --set existingSecret=sird-ocr \
  --set storage.endpoint=http://<s3-host>:9000 \
  --set storage.bucket=<bucket of sird-task-service>
```

Process must sign the `object_key` claim (sird-process-service branch `fix/task-contract`). Without it, the OCR service refuses every capability.

## Architecture

The runtime composes caller-provided stage ports and keeps transport concerns outside the computation path:

```mermaid
flowchart LR
    REQUEST["RecognizeRequest + StageContext"] --> RUNTIME["RecognizerRuntime"]
    RUNTIME --> PREPARE["Prepare"]
    PREPARE --> PROBE["Probe"]
    PROBE --> RESOLVE["Resolve"]
    RESOLVE --> EXECUTE["ExecuteProfile"]
    EXECUTE --> RESPONSE["RecognitionResponse"]
    RESPONSE --> BOUNDARY["gRPC adapter or caller-owned workflow"]
```

The main runtime entry point is [`RecognizerRuntime`](src/sird_recognition/runtime.py). The gRPC boundary is implemented in [`grpc_adapter.py`](src/sird_recognition/grpc_adapter.py). The Protobuf source contract is [`proto/sird/ocr/v1/recognize.proto`](proto/sird/ocr/v1/recognize.proto).

For the detailed stage model, data flow, and boundaries, see [`docs/prototype/architecture/system-architecture.md`](docs/prototype/architecture/system-architecture.md) and [`docs/prototype/architecture/interfaces/api.md`](docs/prototype/architecture/interfaces/api.md). Those documents are marked as draft or proposed design evidence where applicable.

## Repository structure

| Path | Responsibility |
| --- | --- |
| `src/sird_recognition/` | Stateless OCR runtime, contracts, adapters, and generated gRPC modules |
| `proto/` | Authoritative Protobuf source contract |
| `tests/` | Root runtime and gRPC contract tests |
| `integration/` | Separate `sird-workflow` package with durable task workflow code and local service profile |
| `test_app/` | Test-only Litestar/Granian HTTP adapter with an in-memory task service |
| `experiment/` | Deterministic experiment runner and evaluator |
| `verification/` | Architecture, contract, metric, recognition, and acceptance oracles |
| `docs/prototype/` | Product, requirements, architecture, operations, security, and verification documentation |
| `Dockerfile`, `deploy/helm/sird-ocr/` | gRPC OCR service image and Helm chart |
| `deploy/`, `container/`, `compose*.yml` | Other deployment and local container profiles |
| `tools/`, `.github/`, `.omp/`, `.claude/` | Repository delivery, security, quality, architecture, container, and automation controls |

## Development

Each package has its own `pyproject.toml` and lockfile where it owns an independent environment. Run package-specific commands from that package directory or pass the package path to `uv`.

### Root package

```bash
uv run --project . --group dev pytest tests
uv run --project . --group dev ruff check src tests
uv run --project . --group dev ruff format --check src tests
uv run --project . --group dev ty check src tests
uv build --wheel --out-dir dist
```

`ty check` is the repository type-check command. It currently reports baseline diagnostics in generated Protobuf stubs and a small number of adapter/test typing paths; treat a non-zero result as a real issue, not as a passed check. `uv build` writes the wheel to `dist/`.

The pre-commit hook runs changed-file Python checks. The pre-push hook runs the repository harness, the root suite, and the integration suite.

### Integration package

The integration package has separate SQLAlchemy, PostgreSQL, and AMQP dependencies. Run its tests with the integration project:

```bash
uv run --project integration --extra test pytest integration/tests
```

The local service profile requires Docker and a development environment file:

```bash
cp integration/.env.example integration/.env
integration/start.sh
```

`integration/start.sh` validates plain `KEY=VALUE` syntax and requires `RABBITMQ_PASSWORD`. The compose profile binds RabbitMQ, PostgreSQL, and RustFS to loopback addresses. The values in `.env.example` are for development only.

### Experiment and verification packages

Run the experiment from its own project directory so its `tests` import helpers resolve through the configured test path:

```bash
uv run --project experiment --group dev pytest experiment/tests
```

Run the focused verification oracles with the verification environment:

```bash
(cd verification && uv run --project . pytest -q tests/test_acceptance_runner.py tests/test_architecture_oracle.py tests/test_corpus.py tests/test_metrics.py tests/test_recognition_oracles.py)
```

The verification package's development environment includes SQLAlchemy, `psycopg[binary]`, and `aio-pika`, which its full workflow oracles import through `sird_workflow`. The integration package's `test` extra supplies `pytest` for `integration/tests`; it does not provide the verification runtime dependencies.

### Build and delivery checks

Build the root wheel with:

```bash
uv build --wheel --out-dir dist
```

Run the repository harness from the root:

```bash
node tools/harness/checks/run-all.mjs
```

The harness runs syntax, security, quality, container, architecture, OpenSpec, and garbage-collection checks. Quality, container, and architecture policies are currently explicitly `template-unconfigured`, so their advisory results are not a strict quality ratchet. Garbage-collection findings are written to the generated artifacts directory and do not fail the harness by themselves.

If the repository contains OpenSpec changes, install the pinned CLI before running the harness:

```bash
npm install --no-save --no-package-lock --ignore-scripts @fission-ai/openspec@1.13.1
```

The harness fails closed when this CLI is unavailable; do not replace that failure with a skipped validation.

### CI mapping

| Local check | CI owner |
| --- | --- |
| `node tools/harness/checks/run-all.mjs` | [`fadd-delivery-gates.yml`](.github/workflows/fadd-delivery-gates.yml) |
| Root and integration suites from the pre-push hook | `.githooks/pre-push` |
| Security database refresh | [`fadd-security-db-refresh.yml`](.github/workflows/fadd-security-db-refresh.yml) |

The FADD delivery workflow mirrors the local harness and runs on Python 3.14. The pre-push hook additionally runs the root and integration test suites. Security database refreshes use the same Python version.

## Local HTTP adapter

`test_app/` provides a test-only HTTP surface with these routes:

- `POST /tasks` accepts JPEG, PNG, WebP, or TIFF multipart uploads in the `file` field;
- `GET /tasks/{task_id}` returns in-memory task status;
- `GET /tasks/{task_id}/result` returns the current or completed result.

The local profile requires Tesseract with the `eng` and `rus` language data. The checked-in [`test_app/Dockerfile`](test_app/Dockerfile) installs those system packages for the container path. GLiNER is disabled by default and becomes an opt-in local model path when `SIRD_GLINER_ENABLED=1` and `SIRD_GLINER_MODEL_DIR` points to an existing model directory.

Run the host launcher after installing the same Tesseract prerequisites:

```bash
SIRD_HOST=127.0.0.1 SIRD_PORT=8000 ./test_app/run-local.sh
```

Submit an image and poll the task:

```bash
response=$(curl -fsS -X POST \
  -F 'file=@path/to/image.png;type=image/png' \
  http://127.0.0.1:8000/tasks)
task_id=$(printf '%s' "$response" | uv run python -c 'import json, sys; print(json.load(sys.stdin)["task_id"])')
curl -fsS "http://127.0.0.1:8000/tasks/$task_id"
curl -fsS "http://127.0.0.1:8000/tasks/$task_id/result"
```

The submission response is `202 Accepted` and contains `task_id`, `status_url`, and `result_url`. The job runs in memory and is lost when the process exits. The local adapter is not a production deployment.

## Protobuf and gRPC generation

Generated files under `src/sird_recognition/_proto/` are not hand-edited. Regenerate them from the checked-in `.proto` source with:

```bash
uv run python -m grpc_tools.protoc \
  -I proto \
  --python_out=src/sird_recognition/_proto \
  --pyi_out=src/sird_recognition/_proto \
  --grpc_python_out=src/sird_recognition/_proto \
  proto/sird/ocr/v1/recognize.proto
```

The same command is recorded in [`src/sird_recognition/_proto/__init__.py`](src/sird_recognition/_proto/__init__.py).

## Security and deployment boundaries

The root runtime is transport-neutral and does not persist task state. Local integration uses development-only credentials and loopback-bound services. Do not treat the local Compose profile as a production deployment.

The current evidence records these open gaps:

- team agreement on the capability issuer, audience, key id, and policy ids that `sird-process-service` uses;
- production certificate issuance and rotation for mTLS, RabbitMQ broker authorization, and per-service identity mapping;
- OS-level decoder isolation;
- a real labeled corpus, retention cleanup, and production task queue latency evidence.

The frozen synthetic OCR benchmark for SRS PR-2 and PR-4 is in [`tools/benchmark/pr2_benchmark.py`](tools/benchmark/pr2_benchmark.py). Its corpus lock and thresholds are in [`tools/benchmark/pr2-corpus.lock.json`](tools/benchmark/pr2-corpus.lock.json). The last report is [`docs/acceptance/pr2-benchmark-report.json`](docs/acceptance/pr2-benchmark-report.json). Run `uv run python tools/benchmark/pr2_benchmark.py run`, then `uv run python tools/benchmark/pr2_benchmark.py score`.

Security and architecture material is indexed from [`docs/prototype/documentation-overview.md`](docs/prototype/documentation-overview.md) and [`handoff/sird-ocr-integration.md`](handoff/sird-ocr-integration.md).

## Further documentation

- [Documentation overview](docs/prototype/documentation-overview.md)
- [Product requirements](docs/prototype/product/PRD.md)
- [System architecture](docs/prototype/architecture/system-architecture.md)
- [Architecture decisions](docs/prototype/architecture/adr/adr-overview.md)
- [API and module contract](docs/prototype/architecture/interfaces/api.md)
- [Internal stage contracts](docs/prototype/architecture/interfaces/internal-contracts.md)
- [Verification overview](docs/prototype/verification/verification-overview.md)
- [Integration handoff](handoff/sird-ocr-integration.md)
- [OpenSpec proposal](openspec/changes/specify-sird-ocr-integration/proposal.md)

## Maintainers and support

The prototype documentation names Dmitrii Alekseev as the current document owner. No separate contribution guide, support channel, or license file is present in this repository.
