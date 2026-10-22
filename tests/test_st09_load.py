import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_SCRIPT = Path(__file__).parents[1] / "tools" / "benchmark" / "st09_load.py"
_SPEC = spec_from_file_location("st09_load", _SCRIPT)
assert _SPEC and _SPEC.loader
load = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = load
_SPEC.loader.exec_module(load)

_REJECTED, _DUPLICATE, _LOST, _FAILED = 1, 2, 3, 4
_CASES = 6
_ID_BASE = 100
_MULTI_STATUS = 207
_POOL_SIZE = 5004
_POOL = tuple(f"scan/doc-{index}.png" for index in range(_POOL_SIZE))
_SHORT_RUN = 20
_BURST = 250
_MINUTE = 60
_DRAIN = 30
_TICK = 0.01
_OCR_DEPTH = 3
_BURST_RUN = tuple(
    (sequence, 0, _POOL[sequence])
    for sequence in range(_ID_BASE, _ID_BASE + _BURST)
)
_COUNT_NAMES = ("accepted", "rejected", "duplicate_task_ids", "lost")
_EXPECTED_COUNTS = (_CASES - 1, 1, 1, 1)


class _FakeApi:
    """Task API double; the sequence in the file name selects the case."""

    def __init__(self) -> None:
        self.batches: list[int] = []

    def create(self, files: list) -> tuple[int, dict]:
        self.batches.append(len(files))
        rows = [self._row(name) for name, _, _ in files]
        return _MULTI_STATUS, {"results": rows}

    def statuses(self, ids: list[int]) -> list[dict]:
        return [self._status(task_id) for task_id in ids]

    def _row(self, name: str) -> dict:
        sequence = int(name.split("-")[1])
        if sequence == _REJECTED:
            return {"filename": name, "outcome": "REJECTED"}
        if sequence == _DUPLICATE:
            sequence = 0
        return {"filename": name, "task": {"task_id": _ID_BASE + sequence}}

    def _status(self, task_id: int) -> dict:
        state, outcome = "RECOGNIZED", "COMPLETED"
        if task_id == _ID_BASE + _LOST:
            state, outcome = "PENDING", None
        if task_id == _ID_BASE + _FAILED:
            state, outcome = "ERROR", "FAILED"
        return {
            "task_id": task_id,
            "state": state,
            "task_outcome": outcome,
            "updated_at": "fixed",
        }


class _Clock:
    def __init__(self) -> None:
        self.seconds: float = 0

    def read(self) -> float:
        return self.seconds

    def sleep(self, seconds: float) -> None:
        self.seconds += max(seconds, _TICK)


def _replay(api: _FakeApi):
    clock = _Clock()
    return load.Replay(
        api,
        str.encode,
        lambda: {"queues": [{"name": "sird.ocr", "messages": _OCR_DEPTH}]},
        clock.read,
        clock.sleep,
    )


def test_profile_is_seeded_and_day_shaped() -> None:
    counts = load.hourly_counts(load.DOCUMENTS, load.HOURLY_WEIGHTS)
    arrivals = load.build_arrivals(list(_POOL), load.PROFILE_SEED)
    offsets = [offset for _, offset, _ in arrivals]
    assert sum(counts) == len(arrivals) == load.DOCUMENTS
    assert max(counts) > 2 * load.DOCUMENTS / len(counts)
    assert len({key for _, _, key in arrivals}) == load.DOCUMENTS
    assert offsets == sorted(offsets)
    assert offsets[-1] < load.WINDOW_SECONDS


def test_select_spreads_a_short_run() -> None:
    arrivals = load.build_arrivals(list(_POOL), load.PROFILE_SEED)
    chosen = load.select(arrivals, _SHORT_RUN)
    step = load.DOCUMENTS // _SHORT_RUN
    assert chosen == [arrivals[index * step] for index in range(_SHORT_RUN)]
    assert load.read_arrivals(load.arrivals_text(chosen)) == chosen
    again = load.build_arrivals(list(reversed(_POOL)), load.PROFILE_SEED)
    assert again == arrivals


def test_replay_caps_batches_at_the_api_limit() -> None:
    api = _FakeApi()
    replay = _replay(api)
    replay.run(
        list(_BURST_RUN),
        speed=1,
        poll_every=1,
        sample_every=5,
        drain_timeout=10,
    )
    full, rest = divmod(_BURST, load.MAX_FILES)
    assert api.batches == [load.MAX_FILES, load.MAX_FILES, rest]
    assert full == 2
    report = load.reconcile(replay, _BURST, 1)
    assert report["counts"]["terminal"] == _BURST


def test_reconcile_finds_lost_duplicate_failed() -> None:
    api = _FakeApi()
    replay = _replay(api)
    replay.run(
        [(index, index * _MINUTE, _POOL[index]) for index in range(_CASES)],
        speed=_MINUTE,
        poll_every=1,
        sample_every=2,
        drain_timeout=_DRAIN,
    )
    report = load.reconcile(replay, _CASES, _MINUTE)
    counts = report["counts"]
    found = tuple(counts[name] for name in _COUNT_NAMES)
    assert found == _EXPECTED_COUNTS
    assert counts["by_outcome"] == {"COMPLETED": 2, "FAILED": 1}
    assert report["backlog_max_messages"] == {"sird.ocr": _OCR_DEPTH}
    assert not report["pr1_passed"]
    assert replay.recheck() == 0
