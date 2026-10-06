"""SQLAlchemy schema and engine helpers for durable workflow state."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    add_mapped_attribute,
    mapped_column,
    sessionmaker,
    synonym,
)

_MAX_TEXT_LENGTH = 255
_FINGERPRINT_LENGTH = 64
_RESULT_FIELD_NAME = "result"
_TASK_ID_COLUMN = "task_id"
_TASK_FOREIGN_KEY = "sird_tasks.task_id"


class Base(DeclarativeBase):
    """Base for the integration-owned PostgreSQL tables."""

    @classmethod
    def make_engine(cls, database_url: str, **engine_options: Any) -> Engine:
        """Create a synchronous SQLAlchemy engine for PostgreSQL."""
        return create_engine(database_url, **engine_options)

    @classmethod
    def session_factory(cls, engine: Engine) -> sessionmaker[Session]:
        """Return a short-lived synchronous session factory."""
        return sessionmaker(bind=engine, expire_on_commit=False)

    @classmethod
    def create_schema(cls, engine: Engine) -> None:
        """Create the integration tables for local development."""
        cls.metadata.create_all(engine)


class TaskRecord(Base):
    """One durable task and its latest workflow/result state."""

    __tablename__ = "sird_tasks"

    task_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), primary_key=True
    )
    request_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    artifact_ref: Mapped[str] = mapped_column(Text, nullable=False)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(
        String(_FINGERPRINT_LENGTH), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(_FINGERPRINT_LENGTH), nullable=False, default="queued"
    )
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(
        "result", JSONB, nullable=True
    )
    retention_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            _TASK_ID_COLUMN,
            "request_id",
            name="uq_sird_task_request",
        ),
        Index("ix_sird_tasks_request_id", "request_id"),
    )


add_mapped_attribute(TaskRecord, _RESULT_FIELD_NAME, synonym("result_payload"))


class TaskAttemptRecord(Base):
    """Shared attempt budget and fencing state for one durable task."""

    __tablename__ = "sird_task_attempts"

    task_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        ForeignKey(_TASK_FOREIGN_KEY),
        primary_key=True,
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    attempts_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    fencing_token: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    active_delivery_id: Mapped[str | None] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        nullable=True,
    )
    active_worker_id: Mapped[str | None] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        nullable=True,
    )
    active_lease_id: Mapped[str | None] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        nullable=True,
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    terminal_outcome: Mapped[str | None] = mapped_column(
        String(_FINGERPRINT_LENGTH),
        nullable=True,
    )
    terminal_result_id: Mapped[str | None] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class TaskOutbox(Base):
    """A task event that is published after its transaction commits."""

    __tablename__ = "sird_task_outbox"

    event_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    task_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        ForeignKey(_TASK_FOREIGN_KEY),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    topic: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            _TASK_ID_COLUMN,
            "request_id",
            "topic",
            name="uq_sird_task_outbox_identity",
        ),
        Index("ix_sird_task_outbox_pending", "published_at"),
    )


class TaskResultOutbox(Base):
    """Stable terminal result event awaiting broker publication."""

    __tablename__ = "sird_task_result_outbox"

    event_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), primary_key=True
    )
    task_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        ForeignKey(_TASK_FOREIGN_KEY),
        nullable=False,
    )
    source_event_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    request_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    topic: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    suppressed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    suppression_reason: Mapped[str | None] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            _TASK_ID_COLUMN,
            "source_event_id",
            name="uq_sird_task_result_source_event",
        ),
        Index("ix_sird_task_result_outbox_pending", "published_at"),
    )


class TaskDeadLetterOutbox(Base):
    """Stable dead-letter event pending external broker acknowledgement."""

    __tablename__ = "sird_task_dead_letter_outbox"

    event_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), primary_key=True
    )
    task_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH),
        ForeignKey(_TASK_FOREIGN_KEY),
        nullable=False,
    )
    source_event_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    request_id: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    topic: Mapped[str] = mapped_column(
        String(_MAX_TEXT_LENGTH), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            _TASK_ID_COLUMN,
            "source_event_id",
            name="uq_sird_task_dead_letter_source_event",
        ),
        Index("ix_sird_task_dead_letter_pending", "acknowledged_at"),
    )


make_engine = Base.make_engine
session_factory = Base.session_factory
create_schema = Base.create_schema
