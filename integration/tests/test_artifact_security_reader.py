from __future__ import annotations

from functools import partial
from hashlib import sha256

import pytest
import test_artifact_security_helpers
from artifact_security_reader_support import (
    assert_rejected_without_decode,
    decode,
    reader,
)
from sird_workflow import artifact_security


def test_reader_validates_before_decode() -> None:
    source = test_artifact_security_helpers.Source(
        test_artifact_security_helpers.ARTIFACT_DATA
    )
    seen: list[bytes] = []
    token = test_artifact_security_helpers.signer().sign(
        test_artifact_security_helpers.capability()
    )

    assert decode(
        reader(source, test_artifact_security_helpers.validator()),
        partial(test_artifact_security_helpers.record_data, seen),
        token,
    ) == len(test_artifact_security_helpers.ARTIFACT_DATA)
    assert seen == [test_artifact_security_helpers.ARTIFACT_DATA]


def test_reader_rejects_oversized() -> None:
    seen: list[bytes] = []
    assert_rejected_without_decode(
        reader(
            test_artifact_security_helpers.Source(
                test_artifact_security_helpers.ARTIFACT_DATA
            ),
            test_artifact_security_helpers.validator(),
            max_bytes=2,
        ),
        partial(test_artifact_security_helpers.record_data_only, seen),
        test_artifact_security_helpers.signer().sign(
            test_artifact_security_helpers.capability()
        ),
        artifact_security.ArtifactPolicyError,
    )


def test_reader_rejects_media_type() -> None:
    seen: list[bytes] = []
    wrong_media_ref = artifact_security.ArtifactRef(
        object_id=test_artifact_security_helpers.REF.object_id,
        generation=test_artifact_security_helpers.REF.generation,
        checksum=test_artifact_security_helpers.REF.checksum,
        media_type="text/plain",
        size=test_artifact_security_helpers.REF.size,
    )
    token = test_artifact_security_helpers.signer().sign(
        test_artifact_security_helpers.capability(artifact=wrong_media_ref)
    )

    assert_rejected_without_decode(
        reader(
            test_artifact_security_helpers.Source(
                test_artifact_security_helpers.ARTIFACT_DATA
            ),
            test_artifact_security_helpers.validator(),
        ),
        partial(test_artifact_security_helpers.record_data_only, seen),
        token,
        artifact_security.ArtifactPolicyError,
        artifact=wrong_media_ref,
    )
    assert seen == []


def test_reader_rejects_wrong_size() -> None:
    seen: list[bytes] = []
    assert_rejected_without_decode(
        reader(
            test_artifact_security_helpers.Source(b"bad"),
            test_artifact_security_helpers.validator(),
        ),
        partial(test_artifact_security_helpers.record_data_only, seen),
        test_artifact_security_helpers.signer().sign(
            test_artifact_security_helpers.capability()
        ),
        artifact_security.ArtifactSizeMismatchError,
    )
    assert seen == []


def test_reader_rejects_wrong_checksum() -> None:
    seen: list[bytes] = []
    checksum_ref = artifact_security.ArtifactRef(
        object_id=test_artifact_security_helpers.REF.object_id,
        generation=test_artifact_security_helpers.REF.generation,
        checksum=sha256(b"bad").hexdigest(),
        media_type=test_artifact_security_helpers.REF.media_type,
        size=len(test_artifact_security_helpers.ARTIFACT_DATA),
    )
    token = test_artifact_security_helpers.signer().sign(
        test_artifact_security_helpers.capability(artifact=checksum_ref)
    )

    assert_rejected_without_decode(
        reader(
            test_artifact_security_helpers.Source(
                test_artifact_security_helpers.ARTIFACT_DATA
            ),
            test_artifact_security_helpers.validator(),
        ),
        partial(test_artifact_security_helpers.record_data_only, seen),
        token,
        artifact_security.ArtifactChecksumError,
        artifact=checksum_ref,
    )
    assert seen == []


def test_reader_rejects_after_retention() -> None:
    source = test_artifact_security_helpers.Source(
        test_artifact_security_helpers.ARTIFACT_DATA
    )
    token = test_artifact_security_helpers.signer().sign(
        test_artifact_security_helpers.capability()
    )
    with pytest.raises(artifact_security.CapabilityExpiredError):
        reader(source, test_artifact_security_helpers.validator()).read(
            token,
            artifact=test_artifact_security_helpers.REF,
            task_id=test_artifact_security_helpers.TASK_ID,
            request_id=test_artifact_security_helpers.REQUEST_ID,
            now=test_artifact_security_helpers.CURRENT_TIME,
            retention_expires_at=test_artifact_security_helpers.CURRENT_TIME,
        )
    assert source.reads == 0
