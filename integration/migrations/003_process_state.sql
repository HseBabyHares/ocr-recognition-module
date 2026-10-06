CREATE TABLE IF NOT EXISTS sird_task_result_outbox (
    event_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL REFERENCES sird_tasks (task_id),
    source_event_id VARCHAR(255) NOT NULL,
    request_id VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    CONSTRAINT uq_sird_task_result_source_event UNIQUE (task_id, source_event_id)
);

CREATE INDEX IF NOT EXISTS ix_sird_task_result_outbox_pending
    ON sird_task_result_outbox (published_at);

CREATE TABLE IF NOT EXISTS sird_task_dead_letter_outbox (
    event_id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL REFERENCES sird_tasks (task_id),
    source_event_id VARCHAR(255) NOT NULL,
    request_id VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    CONSTRAINT uq_sird_task_dead_letter_source_event UNIQUE (task_id, source_event_id)
);

CREATE INDEX IF NOT EXISTS ix_sird_task_dead_letter_pending
    ON sird_task_dead_letter_outbox (acknowledged_at);
