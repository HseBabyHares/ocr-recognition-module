from __future__ import annotations

from collections.abc import Mapping

from sird_workflow.config import WorkflowConfig
from sird_workflow.db import create_schema
from sird_workflow.service import WorkflowService
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

BACKEND = "sird-backend"
CAPABILITY = "v1.capability"
RETENTION_SECONDS = 43_200


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(
    _type: JSONB, _compiler: object, **_kwargs: object
) -> str:
    return "JSON"


class Producer:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(
        self, *, topic: str, key: str, payload: Mapping[str, object]
    ) -> None:
        self.events.append({"topic": topic, "key": key, "payload": payload})


def service() -> tuple[WorkflowService, Producer, Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_schema(engine)
    producer = Producer()
    config = WorkflowConfig(
        database_url="sqlite://",
        rabbitmq_url="amqps://unused:5671/sird",
        authorized_callers=frozenset((BACKEND,)),
    )
    return WorkflowService(engine, config, producer), producer, engine
