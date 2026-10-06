from __future__ import annotations

import sqlalchemy as sa
from sird_workflow import db as workflow_db
from sird_workflow.identity import request_fingerprint
from sird_workflow.models import SubmitRequest
from sird_workflow.ocr_client import OcrClient
from sird_workflow.process import ProcessService
from sird_workflow.task_event import TaskEvent
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(
    _type: JSONB, _compiler: object, **_kwargs: object
) -> str:
    return "JSON"


def service(
    event_value: TaskEvent, ocr: OcrClient
) -> tuple[ProcessService, Engine]:
    engine = sa.create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    workflow_db.create_schema(engine)
    request = SubmitRequest(
        task_id=event_value.task_id,
        request_id=event_value.request_id,
        artifact_ref=event_value.artifact_ref,
        policy=event_value.policy,
        retention_seconds=event_value.retention_seconds,
    )
    with workflow_db.session_factory(engine)() as session, session.begin():
        session.add(
            workflow_db.TaskRecord(
                task_id=event_value.task_id,
                request_id=event_value.request_id,
                artifact_ref=event_value.artifact_ref,
                policy={},
                request_fingerprint=request_fingerprint(request),
                status="queued",
                retention_seconds=event_value.retention_seconds,
                retention_expires_at=event_value.retention_expires_at,
                created_at=event_value.submitted_at,
                updated_at=event_value.submitted_at,
            )
        )
    return ProcessService(engine, ocr), engine
