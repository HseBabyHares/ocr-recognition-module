#!/usr/bin/env python3

from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DETECTOR = REPO / "tools/gc/python-clones.py"


FUNCTION = """
def convert(value):
    first = value.strip()
    second = first.lower()
    if not second:
        return None
    parts = second.split(":")
    values = []
    for index, part in enumerate(parts):
        cleaned = part.strip()
        if cleaned:
            values.append({"index": index, "value": cleaned})
    result = {"value": second, "length": len(second)}
    result["parts"] = values
    result["empty"] = not values
    return result
"""


DIFFERENT_CALL_FUNCTION = (
    FUNCTION.replace("value.strip()", "source.clean()")
    .replace("first.lower()", "source.fold()")
    .replace('second.split(":")', 'path.read_text().split(":")')
    .replace("part.strip()", "item.clean()")
    .replace("len(second)", "measure(second)")
)

SHORT_FUNCTION = """
def tiny(value):
    first = value.strip()
    second = first.lower()
    if not second:
        return None
    return second
"""


def run(
    production: list[Path], test: list[Path] | None = None
) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(DETECTOR),
            "--repo",
            str(REPO),
            "--production-files",
            *map(str, production),
            "--test-files",
            *(map(str, test or [])),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    with tempfile.TemporaryDirectory(dir=REPO) as directory:
        root = Path(directory)
        first = root / "first.py"
        second = root / "second.py"
        different = root / "different.py"
        short_first = root / "short_first.py"
        short_second = root / "short_second.py"
        test_first = root / "test_first.py"
        test_second = root / "test_second.py"
        first.write_text(FUNCTION, encoding="utf-8")
        second.write_text(
            FUNCTION.replace("convert", "normalize"), encoding="utf-8"
        )
        different.write_text(DIFFERENT_CALL_FUNCTION, encoding="utf-8")
        short_first.write_text(SHORT_FUNCTION, encoding="utf-8")
        short_second.write_text(
            SHORT_FUNCTION.replace("tiny", "small"), encoding="utf-8"
        )
        test_first.write_text(FUNCTION, encoding="utf-8")
        test_second.write_text(
            FUNCTION.replace("convert", "normalize"), encoding="utf-8"
        )

        production_report = run([first, second])
        assert len(production_report["findings"]) == 1
        assert production_report["metrics"]["production"]["cloneClasses"] == 1

        different_call_report = run([first, different])
        assert different_call_report["findings"] == []

        boundary_report = run([short_first, short_second])
        assert boundary_report["findings"] == []
        assert boundary_report["metrics"]["production"]["cloneClasses"] == 0

        test_report = run([], [test_first, test_second])
        assert test_report["findings"] == []
        assert test_report["metrics"]["tests"]["cloneClasses"] == 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
