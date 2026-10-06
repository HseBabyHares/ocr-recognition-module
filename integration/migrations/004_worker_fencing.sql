ALTER TABLE sird_task_attempts
    ADD COLUMN IF NOT EXISTS active_worker_id VARCHAR(255);

ALTER TABLE sird_task_result_outbox
    ADD COLUMN IF NOT EXISTS suppressed_at TIMESTAMPTZ;

ALTER TABLE sird_task_result_outbox
    ADD COLUMN IF NOT EXISTS suppression_reason VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_sird_task_result_outbox_suppressed
    ON sird_task_result_outbox (suppressed_at);
