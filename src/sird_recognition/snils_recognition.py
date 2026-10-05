"""Bounded local image preprocessing and strict SNILS extraction."""

from sird_recognition._snils_service import (
    SnilsRecognitionService as _SnilsRecognitionService,
)
from sird_recognition._snils_types import (
    SnilsRecognitionResult as _SnilsRecognitionResult,
)
from sird_recognition._snils_types import (
    SnilsRecognitionStatus as _SnilsRecognitionStatus,
)
from sird_recognition._snils_types import (
    SnilsTextReader as _SnilsTextReader,
)

SnilsRecognitionResult = _SnilsRecognitionResult
SnilsRecognitionService = _SnilsRecognitionService
SnilsRecognitionStatus = _SnilsRecognitionStatus
SnilsTextReader = _SnilsTextReader
