from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest
from sird_workflow import artifact_security
from test_artifact_security_helpers import (
    CURRENT_TIME,
    PDF_MEDIA_TYPE,
    REF,
    REQUEST_ID,
    TASK_ID,
)


def reader(
    source: artifact_security.ArtifactSource,
    validator: artifact_security.ArtifactCapabilityValidator,
    max_bytes: int = 1024,
) -> artifact_security.ArtifactReader:
    policy = artifact_security.ArtifactReadPolicy(
        max_bytes=max_bytes, allowed_media_types={PDF_MEDIA_TYPE}
    )
    return artifact_security.ArtifactReader(source, validator, policy)


def decode(
    artifact_reader: artifact_security.ArtifactReader,
    callback: Callable[[bytes], object],
    token: str,
    artifact: artifact_security.ArtifactRef = REF,
) -> object:
    return artifact_reader.decode(
        cast(artifact_security.ArtifactDecoder, callback),
        token,
        artifact=artifact,
        task_id=TASK_ID,
        request_id=REQUEST_ID,
        now=CURRENT_TIME,
    )


def assert_rejected_without_decode(
    artifact_reader: artifact_security.ArtifactReader,
    callback: Callable[[bytes], object],
    token: str,
    error: type[Exception],
    artifact: artifact_security.ArtifactRef = REF,
) -> None:
    with pytest.raises(error):
        decode(artifact_reader, callback, token, artifact)
