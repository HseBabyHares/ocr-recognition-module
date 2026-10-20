import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("PIL")

SCRIPT = Path(__file__).with_name("render_snils_forms.py")
spec = importlib.util.spec_from_file_location("snils_renderer", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module  # dataclasses resolve their module
spec.loader.exec_module(module)


def test_renders_every_layout_with_valid_truth(tmp_path):
    module.generate(tmp_path, count=1, seed=3, clean=False, negatives=1)
    rows = [
        json.loads(line)
        for line in (tmp_path / "manifest.jsonl").read_text().splitlines()
    ]
    assert sorted(row["layout"] for row in rows) == sorted(
        (*module.LAYOUTS, *module.NEGATIVES)
    )
    for row in rows:
        assert (tmp_path / row["file"]).stat().st_size > 0
        valid = row["snils"][-2:] == module.snils_checksum(row["snils"][:-2])
        assert valid == (row["layout"] != "card_bad_checksum")
        assert row["expected_verified"] == (row["layout"] in module.LAYOUTS)


def test_negatives_do_not_change_positive_files(tmp_path):
    module.generate(tmp_path / "a", count=1, seed=3, clean=True)
    module.generate(tmp_path / "b", count=1, seed=3, clean=True, negatives=1)
    for layout in module.LAYOUTS:
        name = f"{layout}-000.png"
        first = (tmp_path / "a" / name).read_bytes()
        assert first == (tmp_path / "b" / name).read_bytes()
