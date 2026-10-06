"""Status calculations used by the acceptance report."""

from __future__ import annotations

from collections.abc import Mapping

STATUS_KEY = "status"
PASSED_STATUS = "passed"
FAILED_STATUS = "failed"
BLOCKED_STATUS = "blocked"
NOT_RUN_STATUS = "not_run"
STATUSES = frozenset(
    (
        PASSED_STATUS,
        FAILED_STATUS,
        BLOCKED_STATUS,
        NOT_RUN_STATUS,
    ),
)


Row = dict[str, object]
Rows = list[Row]
RowsById = Mapping[str, Row]


def _required_statuses(
    rows_by_id: RowsById,
    required_ids: tuple[str, ...],
) -> set[str]:
    return {str(rows_by_id[test_id][STATUS_KEY]) for test_id in required_ids}


def acceptance_status(required_statuses: set[str]) -> str:
    if FAILED_STATUS in required_statuses:
        return FAILED_STATUS
    if required_statuses & {BLOCKED_STATUS, NOT_RUN_STATUS}:
        return BLOCKED_STATUS
    return PASSED_STATUS


def command_status(rows: Rows) -> str:
    statuses = {str(row[STATUS_KEY]) for row in rows}
    if FAILED_STATUS in statuses:
        return "fail"
    if statuses & {BLOCKED_STATUS, NOT_RUN_STATUS}:
        return BLOCKED_STATUS
    return "pass"
