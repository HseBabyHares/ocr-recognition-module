from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests._object_store import object_store


@pytest.fixture
def store() -> Iterator[str]:
    """Yield the endpoint of a local S3 stand-in."""
    with object_store() as endpoint:
        yield endpoint
