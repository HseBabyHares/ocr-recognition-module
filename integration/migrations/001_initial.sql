CREATE TABLE IF NOT EXISTS sird_tasks (
    task_id VARCHAR(255) PRIMARY KEY,
    request_id VARCHAR(255) NOT NULL,
    artifact_ref TEXT NOT NULL,
    policy JSONB NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL,
    result JSONB,
    retention_seconds INTEGER NOT NULL CHECK (retention_seconds > 0),
    retention_expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_sird_task_request UNIQUE (task_id, request_id)
);

CREATE INDEX IF NOT EXISTS ix_sird_tasks_request_id ON sird_tasks (request_id);

CREATE TABLE IF NOT EXISTS sird_task_outbox (
    event_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL REFERENCES sird_tasks (task_id),
    request_id VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    CONSTRAINT uq_sird_task_outbox_identity UNIQUE (task_id, request_id, topic)
);

CREATE INDEX IF NOT EXISTS ix_sird_task_outbox_pending
    ON sird_task_outbox (published_at);
