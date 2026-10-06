"""Explicit adapters for the root recognition and integration packages.

The adapters keep oracle code independent from transport and persistence.  They
only forward calls to injected ports or to the existing typed package APIs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class AdapterUnavailableError(RuntimeError):
    """An adapter cannot execute because its injected service is absent."""


@dataclass(frozen=True, slots=True)
class RuntimeAdapter:
    """Adapter around an injected ``RecognizerRuntime`` instance."""

    runtime: Any

    def parse_request(self, payload: Mapping[str, object]) -> Any:
        """Parse through the production strict request boundary."""

        if self.runtime is None:
            raise AdapterUnavailableError("recognition runtime is unavailable")
        try:
            from sird_recognition.runtime import RecognizeRequest
        except ImportError as exc:
            raise AdapterUnavailableError(
                "recognition package is unavailable"
            ) from exc
        return RecognizeRequest.from_mapping(payload)

    def recognize(self, request: Any, context: Any) -> Any:
        """Invoke the injected runtime without changing its result."""

        if self.runtime is None:
            raise AdapterUnavailableError("recognition runtime is unavailable")
        method = getattr(self.runtime, "recognize", None)
        if not callable(method):
            raise AdapterUnavailableError("recognition adapter is incomplete")
        return method(request, context)


@dataclass(frozen=True, slots=True)
class ArtifactCapabilityAdapter:
    """Adapter around the integration capability validator."""

    validator: Any

    def validate(
        self,
        token: str,
        *,
        task_id: str,
        request_id: str,
        artifact: Any,
        **options: Any,
    ) -> Any:
        """Validate one capability through the existing validator."""

        audience: str | None = options.pop("audience", None)
        now: datetime | None = options.pop("now", None)
        if options:
            option_name = next(iter(options))
            message = (
                "validate() got an unexpected keyword argument "
                f"{option_name!r}"
            )
            raise TypeError(message)

        if self.validator is None:
            raise AdapterUnavailableError(
                "artifact capability validator is unavailable"
            )
        method = getattr(self.validator, "validate", None)
        if not callable(method):
            raise AdapterUnavailableError("capability adapter is incomplete")
        return method(
            token,
            task_id=task_id,
            request_id=request_id,
            artifact=artifact,
            audience=audience,
            now=now,
        )


@dataclass(frozen=True, slots=True)
class AttemptBudgetAdapter:
    """Adapter around the pure integration attempt-budget state machine."""

    budget: Any

    def claim(
        self,
        worker_id: str,
        *,
        delivery_id: str,
        budget: Any | None = None,
    ) -> tuple[Any, Any]:
        """Claim a delivery using the existing shared budget."""

        selected_budget = self.budget if budget is None else budget
        if selected_budget is None:
            raise AdapterUnavailableError("attempt budget is unavailable")
        method = getattr(selected_budget, "claim", None)
        if not callable(method):
            raise AdapterUnavailableError("attempt adapter is incomplete")
        return method(worker_id, delivery_id=delivery_id)


@dataclass(frozen=True, slots=True)
class DeadLetterAdapter:
    """Adapter around the integration dead-letter outbox state machine."""

    outbox: Any

    def publish(self, publisher: Any) -> Any:
        """Record an explicit publisher acknowledgement."""

        if self.outbox is None:
            raise AdapterUnavailableError("dead-letter outbox is unavailable")
        method = getattr(self.outbox, "publish", None)
        if not callable(method):
            raise AdapterUnavailableError("dead-letter adapter is incomplete")
        return method(publisher)

    def commit_source_offset(self, outbox: Any) -> Any:
        """Attempt the explicit source-offset commit transition."""

        method = getattr(outbox, "commit_source_offset", None)
        if not callable(method):
            raise AdapterUnavailableError("dead-letter commit is unavailable")
        return method()


@dataclass(frozen=True, slots=True)
class ProcessOutboxAdapter:
    """Adapter around the durable process outbox dispatcher."""

    dispatcher: Any

    def dispatch_pending(self, limit: int = 100) -> Any:
        """Run one bounded dispatcher pass."""

        if self.dispatcher is None:
            raise AdapterUnavailableError("process outbox is unavailable")
        method = getattr(self.dispatcher, "dispatch_pending", None)
        if not callable(method):
            raise AdapterUnavailableError(
                "process outbox adapter is incomplete"
            )
        return method(limit=limit)


PublisherFactory = Callable[[Any], Any]
