"""General document boundary candidates."""

from __future__ import annotations

import cv2
import numpy as np

from sird_recognition._snils_geometry_config import _GeometryConfig
from sird_recognition._snils_geometry_document_helpers import _edge_candidates


def document_candidates(frame: np.ndarray) -> list[tuple[float, np.ndarray]]:
    """Return usable document candidates across edge thresholds."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    image_area = float(frame.shape[0] * frame.shape[1])
    candidates: list[tuple[float, np.ndarray]] = []
    for edge_pair in _GeometryConfig.document_edge_pairs:
        candidates.extend(_edge_candidates(frame, gray, edge_pair, image_area))
    return candidates
