FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv build --wheel --out-dir /dist . \
    && uv export --project . --frozen --no-dev --no-emit-project \
        --no-emit-local --format requirements-txt \
        --output-file /dist/requirements.txt

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libglib2.0-0 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist/requirements.txt /tmp/requirements.txt
COPY --from=builder /dist/sird_recognition-*.whl /tmp/
RUN pip install --require-hashes -r /tmp/requirements.txt \
    && pip install --no-deps /tmp/sird_recognition-*.whl \
    && rm -rf /tmp/* \
    && useradd --create-home --uid 10001 appuser

USER 10001:10001
WORKDIR /app
EXPOSE 50051

CMD ["sird-ocr-server"]
