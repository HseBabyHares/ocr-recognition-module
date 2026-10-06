ALTER TABLE sird_task_attempts
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_sird_task_attempts_next_attempt_at
    ON sird_task_attempts (next_attempt_at);
