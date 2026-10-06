"""Task submission and result retrieval over PostgreSQL and RabbitMQ."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Protocol

import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from sird_workflow import (
    config,
    db,
    exceptions,
    identity,
    models,
)
from sird_workflow import (
    producer as producer_module,
)


@dataclass(frozen=True, slots=True)
class _SubmissionContext:
    session: Session
    request: models.SubmitRequest
    fingerprint: str
    now: datetime.datetime
    retention_expires_at: datetime.datetime
    task: db.TaskRecord | None = None


class _WorkflowServiceState(Protocol):
    _config: config.WorkflowConfig
    _session_factory: sessionmaker[Session]
    _producer: producer_module.TaskProducer

    def _authorize(self, caller_identity: str) -> None: ...

    def _persist_with_retry(
        self,
        request: models.SubmitRequest,
        fingerprint: str,
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]: ...

    def _ensure_outbox(self, outbox: db.TaskOutbox | None) -> None: ...

    def _persist_submission(
        self,
        request: models.SubmitRequest,
        fingerprint: str,
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]: ...

    def _reuse_submission(
        self, context: _SubmissionContext
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]: ...

    def _create_submission(
        self, context: _SubmissionContext
    ) -> tuple[db.TaskRecord, db.TaskOutbox]: ...

    def _publish_outbox(self, outbox: db.TaskOutbox) -> None: ...


class _WorkflowSubmission:
    """Persist and publish task submissions."""

    def submit(
        self: _WorkflowServiceState,
        caller_identity: str,
        request: models.SubmitRequest,
    ) -> models.TaskSubmission:
        """Persist one task and publish its event before reporting success."""
        self._authorize(caller_identity)
        configured_request = _apply_configured_retention(self._config, request)
        fingerprint = identity.request_fingerprint(configured_request)
        task, outbox = self._persist_with_retry(
            configured_request, fingerprint
        )
        self._ensure_outbox(outbox)
        return models.TaskSubmission(
            task_id=task.task_id,
            request_id=task.request_id,
            status=task.status,
            submitted_at=task.created_at,
            retention_expires_at=task.retention_expires_at,
        )

    def _persist_with_retry(
        self: _WorkflowServiceState,
        request: models.SubmitRequest,
        fingerprint: str,
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]:
        from sqlalchemy.exc import IntegrityError

        for attempt_number in range(2):
            try:
                return self._persist_submission(request, fingerprint)
            except IntegrityError as exc:
                if attempt_number:
                    raise exceptions.InvalidIdempotentReuseError(
                        "task identity could not be resolved without a "
                        "conflicting row"
                    ) from exc
        raise exceptions.InvalidIdempotentReuseError(
            "submission retry was exhausted"
        )

    def _ensure_outbox(
        self: _WorkflowServiceState, outbox: db.TaskOutbox | None
    ) -> None:
        if outbox is None:
            raise exceptions.PublicationFailureError(
                "task event outbox row is missing for the durable task"
            )
        if outbox.published_at is None:
            self._publish_outbox(outbox)

    def _persist_submission(
        self: _WorkflowServiceState,
        request: models.SubmitRequest,
        fingerprint: str,
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]:
        now = datetime.datetime.now(datetime.UTC)
        retention_expires_at = now + datetime.timedelta(
            seconds=request.effective_retention_seconds
        )
        with self._session_factory() as session, session.begin():
            task = session.scalar(
                sa.select(db.TaskRecord)
                .where(db.TaskRecord.task_id == request.task_id)
                .with_for_update()
            )
            context = _SubmissionContext(
                session=session,
                request=request,
                fingerprint=fingerprint,
                now=now,
                retention_expires_at=retention_expires_at,
                task=task,
            )
            if task is not None:
                return self._reuse_submission(context)
            return self._create_submission(context)

    def _reuse_submission(
        self: _WorkflowServiceState, context: _SubmissionContext
    ) -> tuple[db.TaskRecord, db.TaskOutbox | None]:
        task = context.task
        assert task is not None
        if task.request_id != context.request.request_id:
            raise exceptions.InvalidIdempotentReuseError(
                "task_id is already bound to another request_id"
            )
        if task.request_fingerprint != context.fingerprint:
            raise exceptions.InvalidIdempotentReuseError(
                "request identity was reused with different content"
            )
        outbox = context.session.scalar(
            sa.select(db.TaskOutbox).where(
                sa.and_(
                    db.TaskOutbox.task_id == task.task_id,
                    db.TaskOutbox.request_id == task.request_id,
                )
            )
        )
        attempt = context.session.scalar(
            sa.select(db.TaskAttemptRecord).where(
                db.TaskAttemptRecord.task_id == task.task_id
            )
        )
        if attempt is None:
            context.session.add(
                db.TaskAttemptRecord(
                    task_id=task.task_id,
                    max_attempts=self._config.max_attempts,
                    updated_at=context.now,
                )
            )
        return task, outbox

    def _create_submission(
        self: _WorkflowServiceState, context: _SubmissionContext
    ) -> tuple[db.TaskRecord, db.TaskOutbox]:
        from uuid import uuid4

        request = context.request
        event_id = str(uuid4())
        payload = identity.task_event_payload(
            request,
            event_id=event_id,
            submitted_at=context.now,
            retention_expires_at=context.retention_expires_at,
            max_attempts=self._config.max_attempts,
        )
        task = db.TaskRecord(
            task_id=request.task_id,
            request_id=request.request_id,
            artifact_ref=request.artifact_ref,
            policy=dict(request.policy),
            request_fingerprint=context.fingerprint,
            status="queued",
            retention_seconds=request.effective_retention_seconds,
            retention_expires_at=context.retention_expires_at,
            created_at=context.now,
            updated_at=context.now,
        )
        outbox = db.TaskOutbox(
            event_id=event_id,
            task_id=request.task_id,
            request_id=request.request_id,
            topic=self._config.rabbitmq_task_route,
            payload=payload,
            created_at=context.now,
        )
        context.session.add(task)
        context.session.flush()
        context.session.add(
            db.TaskAttemptRecord(
                task_id=request.task_id,
                max_attempts=self._config.max_attempts,
                updated_at=context.now,
            )
        )
        context.session.add(outbox)
        return task, outbox

    def _publish_outbox(
        self: _WorkflowServiceState, outbox: db.TaskOutbox
    ) -> None:
        try:
            self._producer.publish(
                topic=outbox.topic,
                key=outbox.task_id,
                payload=outbox.payload,
            )
        except exceptions.PublicationFailureError:
            raise
        except Exception as exc:
            raise exceptions.PublicationFailureError(
                "task event publication failed"
            ) from exc

        with self._session_factory() as session, session.begin():
            session.execute(
                sa.update(db.TaskOutbox)
                .where(
                    sa.and_(
                        db.TaskOutbox.event_id == outbox.event_id,
                        db.TaskOutbox.published_at.is_(None),
                    )
                )
                .values(published_at=datetime.datetime.now(datetime.UTC))
            )


class _WorkflowRead:
    """Read and purge durable task state."""

    def get_status(
        self: _WorkflowServiceState,
        caller_identity: str,
        task_id: str,
    ) -> models.TaskStatus:
        """Read current durable state without invoking OCR."""

        self._authorize(caller_identity)
        with self._session_factory() as session:
            task = session.get(db.TaskRecord, task_id)
            if task is None:
                raise exceptions.TaskNotFoundError(
                    f"task {task_id!r} was not found"
                )
            return models.TaskStatus(
                task_id=task.task_id,
                request_id=task.request_id,
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
                retention_expires_at=task.retention_expires_at,
            )

    def get_result(
        self: _WorkflowServiceState,
        caller_identity: str,
        task_id: str,
    ) -> models.TaskResult:
        """Read the durable result and hide payloads after retention expiry."""

        self._authorize(caller_identity)
        with self._session_factory() as session:
            task = session.get(db.TaskRecord, task_id)
            if task is None:
                raise exceptions.TaskNotFoundError(
                    f"task {task_id!r} was not found"
                )
            expired = _is_expired(task.retention_expires_at)
            result_payload = None if expired else task.result_payload
            return models.TaskResult(
                task_id=task.task_id,
                request_id=task.request_id,
                status=task.status,
                result=result_payload,
                created_at=task.created_at,
                updated_at=task.updated_at,
                retention_expires_at=task.retention_expires_at,
                expired=expired,
            )

    def purge_expired_results(
        self: _WorkflowServiceState,
        *,
        now: datetime.datetime | None = None,
        limit: int = 100,
    ) -> int:
        """Clear expired integration-owned result payloads in
        bounded batches."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        current = datetime.datetime.now(datetime.UTC) if now is None else now
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        with self._session_factory() as session, session.begin():
            tasks = list(
                session.scalars(
                    sa.select(db.TaskRecord)
                    .where(
                        db.TaskRecord.retention_expires_at <= current,
                        db.TaskRecord.result_payload.is_not(None),
                    )
                    .order_by(
                        db.TaskRecord.retention_expires_at,
                        db.TaskRecord.task_id,
                    )
                    .limit(limit)
                )
            )
            for task in tasks:
                session.execute(
                    sa.update(db.TaskResultOutbox)
                    .where(
                        db.TaskResultOutbox.task_id == task.task_id,
                        db.TaskResultOutbox.published_at.is_(None),
                        db.TaskResultOutbox.suppressed_at.is_(None),
                    )
                    .values(
                        suppressed_at=current,
                        suppression_reason="retention_expired",
                    )
                )
                task.result_payload = sa.null()
                task.updated_at = current
            return len(tasks)

    def _authorize(self: _WorkflowServiceState, caller_identity: str) -> None:
        if caller_identity not in self._config.authorized_callers:
            raise exceptions.UnauthenticatedCallerError(
                "caller identity is not authorized"
            )


class WorkflowService(_WorkflowSubmission, _WorkflowRead):
    """Own durable task identity, transactional outbox, and retrieval."""

    def __init__(
        self,
        engine: Engine,
        config: config.WorkflowConfig,
        producer: producer_module.TaskProducer | None = None,
    ) -> None:
        self._config = config
        self._session_factory: sessionmaker[Session] = db.session_factory(
            engine
        )
        self._producer = producer or producer_module.RabbitMQTaskProducer(
            producer_module.RabbitMQProducerConfig(
                amqp_url=config.rabbitmq_url,
                exchange_name=config.rabbitmq_exchange,
                tls_identity=config.rabbitmq_tls_identity,
                extra=config.rabbitmq_properties,
            )
        )

    @classmethod
    def from_config(
        cls, config: config.WorkflowConfig, **engine_kwargs: Any
    ) -> WorkflowService:
        """Create a production service from explicit PostgreSQL/RabbitMQ
        settings."""

        return cls(
            db.make_engine(config.database_url, **engine_kwargs), config
        )


def _apply_configured_retention(
    config: config.WorkflowConfig,
    request: models.SubmitRequest,
) -> models.SubmitRequest:
    if request.retention_seconds is not None:
        return request
    return models.SubmitRequest(
        task_id=request.task_id,
        request_id=request.request_id,
        artifact_ref=request.artifact_ref,
        policy=request.policy,
        retention_seconds=config.default_retention_seconds,
    )


def _is_expired(expires_at: datetime.datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=datetime.UTC)
    return expires_at <= datetime.datetime.now(datetime.UTC)
