from collections.abc import Awaitable, Callable
from typing import Any

from litestar import Litestar, Request, post
from litestar.datastructures import State
from litestar.testing import TestClient

Payload = dict[str, object]
RecognizeHandler = Callable[[Payload], Awaitable[Payload]]
RECOGNIZE_PATH = "/recognize"
TASK_ID_KEY = "task_id"
TASK_ID_VALUE = "task-1"
CREATED_STATUS = 201


@post(RECOGNIZE_PATH)
async def recognize(request: Request[Any, Any, State]) -> Payload:
    payload = await request.json()
    recognition_handler = request.app.state["recognition_handler"]
    return await recognition_handler(payload)


def create_test_app(recognition_handler: RecognizeHandler) -> Litestar:
    """Build a test-only HTTP boundary for the transport-neutral ports."""
    return Litestar(
        route_handlers=[recognize],
        state=State({"recognition_handler": recognition_handler}),
    )


async def echo_recognition(payload: Payload) -> Payload:
    return {
        "contract_version": "sird.ocr.v1",
        TASK_ID_KEY: payload[TASK_ID_KEY],
        "operation_status": "ok",
    }


def test_adapter_delegates_recognize_request() -> None:
    with TestClient(create_test_app(echo_recognition)) as client:
        response = client.post(
            RECOGNIZE_PATH,
            json={TASK_ID_KEY: TASK_ID_VALUE},
        )

    assert response.status_code == CREATED_STATUS
    assert response.json()[TASK_ID_KEY] == TASK_ID_VALUE
