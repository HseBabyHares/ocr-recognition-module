"""Compose the SNILS recognizer runtime from the process environment."""

from __future__ import annotations

import os

from sird_recognition._tesseract_pins import tesseract_checksums
from sird_recognition.artifact_capability import (
    CapabilityVerifier,
    parse_keys,
)
from sird_recognition.contracts.stages import ExecutionSpec
from sird_recognition.runtime import RecognizerRuntime
from sird_recognition.s3_material import S3MaterialReader
from sird_recognition.snils_recognition import SnilsRecognitionService
from sird_recognition.snils_stages import (
    SNILS_FORM_ID,
    CapabilityPrepare,
    FixedFormResolve,
    SnilsExecuteProfile,
    WholePageProbe,
)
from sird_recognition.tesseract_text_reader import TesseractTextReader


def build_runtime() -> RecognizerRuntime:
    """Compose the SNILS runtime from the environment, failing closed."""
    tesseract_sha, tessdata_sha = tesseract_checksums()
    specification = ExecutionSpec(
        form_id=SNILS_FORM_ID,
        profile_id="snils-tesseract-v1",
        stage_names=("prepare", "probe", "resolve", "execute"),
        implementation_checksums={
            "tesseract": tesseract_sha,
            "tessdata": tessdata_sha,
        },
        calibration_ref="snils-card-v1",
        reader_language="rus+eng",
    )
    verifier = CapabilityVerifier(
        keys=parse_keys(_required("CAPABILITY_KEYS")),
        issuer=_required("CAPABILITY_ISSUER"),
        audience=_required("CAPABILITY_AUDIENCE"),
    )
    return RecognizerRuntime(
        CapabilityPrepare(verifier, os.environ.get("SIRD_OCR_POLICY_ID")),
        WholePageProbe(),
        FixedFormResolve(specification),
        SnilsExecuteProfile(
            SnilsRecognitionService(
                TesseractTextReader(
                    implementation_checksum=tesseract_sha,
                    tessdata_checksum=tessdata_sha,
                )
            ),
            S3MaterialReader(
                endpoint=_required("S3_ENDPOINT"),
                bucket=_required("S3_BUCKET"),
                access_key=_required("S3_ACCESS_KEY"),
                secret_key=_required("S3_SECRET_KEY"),
                region=os.environ.get("S3_REGION", "us-east-1"),
            ),
        ),
    )


def _required(name: str) -> str:
    configured = os.environ.get(name, "").strip()
    if not configured:
        raise RuntimeError(f"{name} is required")
    return configured
