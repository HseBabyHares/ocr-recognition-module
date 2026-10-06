import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("generate_gpt_test_images.py")
spec = importlib.util.spec_from_file_location("gpt_generator", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_validate_only_contract_and_checksum(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", [str(SCRIPT), "--validate-only"])
    assert module.main() == 0
    assert "validated 3 forms" in capsys.readouterr().out
    forms = [item["form"] for item in module.entries()]
    assert forms == ["SNILS card", "ADI REG 2019", "ADI REG 2013"]
    assert all(module.WATERMARK in item["prompt"] for item in module.entries())
    snils = module.entries()[0]["truth"]["snils"]
    compact = snils.replace("-", "").replace(" ", "")
    assert compact[-2:] == module.snils_checksum(compact[:-2])
