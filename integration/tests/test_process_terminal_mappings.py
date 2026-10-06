from __future__ import annotations

import pytest
from process_terminal_mappings_support import TerminalScenario
from sird_workflow.ocr_outcome import OcrOutcome


@pytest.mark.parametrize(
    ("ocr_outcome", "status"),
    [
        (OcrOutcome.SUCCESS, "succeeded"),
        (OcrOutcome.REJECTED, "rejected"),
        (OcrOutcome.PERMANENT, "failed"),
        (OcrOutcome.CANCELLED, "cancelled"),
        (OcrOutcome.LIMIT, "limit"),
    ],
)
def test_terminal_outcomes_idempotent(
    ocr_outcome: OcrOutcome, status: str
) -> None:
    TerminalScenario(ocr_outcome, status).run()


def test_transient_retries_and_dead_letter() -> None:
    TerminalScenario(OcrOutcome.TRANSIENT, "retrying").run_retry()
