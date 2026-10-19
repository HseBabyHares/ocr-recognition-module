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
    module.generate(tmp_path, count=1, seed=3, clean=False)
    rows = [
        json.loads(line)
        for line in (tmp_path / "manifest.jsonl").read_text().splitlines()
    ]
    assert sorted(row["layout"] for row in rows) == sorted(module.LAYOUTS)
    for row in rows:
        assert (tmp_path / row["file"]).stat().st_size > 0
        assert row["snils"][-2:] == module.snils_checksum(row["snils"][:-2])
