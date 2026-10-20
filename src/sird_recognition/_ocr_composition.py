"""Compose the SNILS recognizer runtime from the process environment."""

from __future__ import annotations

import os

from sird_recognition._tesseract_pins import tesseract_checksums
from sird_recognition.artifact_capability import (
    CapabilityVerifier,
    parse_keys,
)
from sird_recognition.contracts.stages import ExecutionSpec
from sird_recognition.form_classifier import CALIBRATION_REF, SUPPORTED_FORMS
from sird_recognition.runtime import RecognizerRuntime
from sird_recognition.s3_material import S3MaterialReader
from sird_recognition.snils_recognition import SnilsRecognitionService
from sird_recognition.snils_stages import (
    CapabilityPrepare,
    MarkerFormResolve,
    SnilsExecuteProfile,
    TextFormProbe,
)
from sird_recognition.tesseract_text_reader import TesseractTextReader


def build_runtime() -> RecognizerRuntime:
    """Compose the SNILS runtime from the environment, failing closed."""
    tesseract_sha, tessdata_sha = tesseract_checksums()
    verifier = CapabilityVerifier(
        keys=parse_keys(_required("CAPABILITY_KEYS")),
        issuer=_required("CAPABILITY_ISSUER"),
        audience=_required("CAPABILITY_AUDIENCE"),
    )
    service = SnilsRecognitionService(
        TesseractTextReader(
            implementation_checksum=tesseract_sha,
            tessdata_checksum=tessdata_sha,
        )
    )
    material = S3MaterialReader(
        endpoint=_required("S3_ENDPOINT"),
        bucket=_required("S3_BUCKET"),
        access_key=_required("S3_ACCESS_KEY"),
        secret_key=_required("S3_SECRET_KEY"),
        region=os.environ.get("S3_REGION", "us-east-1"),
    )
    return RecognizerRuntime(
        CapabilityPrepare(verifier, os.environ.get("SIRD_OCR_POLICY_ID")),
        TextFormProbe(service, material),
        MarkerFormResolve(_specifications(tesseract_sha, tessdata_sha)),
        SnilsExecuteProfile(service, material),
    )


def _specifications(
    tesseract_sha: str, tessdata_sha: str
) -> dict[str, ExecutionSpec]:
    # All three forms share one field profile; the form id is still recorded.
    return {
        form_id: ExecutionSpec(
            form_id=form_id,
            profile_id="snils-tesseract-v1",
            stage_names=("prepare", "probe", "resolve", "execute"),
            implementation_checksums={
                "tesseract": tesseract_sha,
                "tessdata": tessdata_sha,
            },
            calibration_ref=CALIBRATION_REF,
            reader_language="rus+eng",
        )
        for form_id in SUPPORTED_FORMS
    }


def _required(name: str) -> str:
    configured = os.environ.get(name, "").strip()
    if not configured:
        raise RuntimeError(f"{name} is required")
    return configured
