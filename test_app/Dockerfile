FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY test_app/pyproject.toml test_app/uv.lock ./test_app/
COPY test_app/src ./test_app/src

RUN uv build --wheel --out-dir /dist . \
    && uv build --wheel --out-dir /dist ./test_app \
    && uv export --project . --frozen --no-dev --no-emit-project \
        --no-emit-local --format requirements-txt \
        --output-file /dist/root-requirements.txt \
    && uv export --project test_app --frozen --no-dev --no-emit-project \
        --no-emit-local --format requirements-txt \
        --output-file /dist/app-requirements.txt

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libglib2.0-0 \
        libgl1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist/root-requirements.txt /tmp/root-requirements.txt
COPY --from=builder /dist/app-requirements.txt /tmp/app-requirements.txt
COPY --from=builder /dist/sird_recognition-*.whl /tmp/
COPY --from=builder /dist/sird_test_app-*.whl /tmp/
RUN pip install --require-hashes -r /tmp/root-requirements.txt \
    && pip install --require-hashes -r /tmp/app-requirements.txt \
    && pip install --no-deps /tmp/sird_recognition-*.whl /tmp/sird_test_app-*.whl \
    && rm -rf /tmp/* \
    && useradd --create-home --uid 10001 appuser

USER 10001:10001
WORKDIR /app
EXPOSE 8000

CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "sird_test_app.local_snils:app"]
