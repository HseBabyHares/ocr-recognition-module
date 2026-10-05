import importlib


def test_package_imports() -> None:
    package = importlib.import_module("sird_recognition")

    assert package.__doc__ == "SIRD document recognition runtime package."
