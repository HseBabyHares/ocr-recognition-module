CREATE TABLE IF NOT EXISTS sird_task_attempts (
    task_id VARCHAR(255) PRIMARY KEY REFERENCES sird_tasks (task_id),
    max_attempts INTEGER NOT NULL CHECK (max_attempts > 0),
    attempts_used INTEGER NOT NULL DEFAULT 0 CHECK (attempts_used >= 0),
    fencing_token INTEGER NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
    active_delivery_id VARCHAR(255),
    active_lease_id VARCHAR(255),
    terminal_outcome VARCHAR(64),
    terminal_result_id VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL
);
