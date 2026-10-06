#!/usr/bin/env python3
"""Generate synthetic OCR forms with the OpenAI Images API.

Validation is local and never needs credentials. The normal mode calls the API
only after it finds OPENAI_API_KEY in the environment.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import stat
import sys
import urllib.request
from pathlib import Path

MODEL = "gpt-image-1"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
WATERMARK = "SYNTHETIC TEST"


def snils_checksum(number: str) -> str:
    """Return the SNILS check digits for the first nine digits."""
    digits = number.replace("-", "").replace(" ", "")
    if len(digits) != 9 or not digits.isdigit():
        raise ValueError("SNILS base must contain nine digits")
    total = sum(int(digit) * (9 - index) for index, digit in enumerate(digits))
    if total < 100:
        check = total
    elif total in (100, 101):
        check = 0
    else:
        check = total % 101
        if check == 100:
            check = 0
    return f"{check:02d}"


def _snils(base: str) -> str:
    return f"{base[:3]}-{base[3:6]}-{base[6:]} {snils_checksum(base)}"


def entries() -> list[dict[str, object]]:
    """Return deterministic prompts and protected synthetic values."""
    values = {
        "snils": _snils("123456789"),
        "full_name": "ИВАНОВА ТЕСТОВА АЛЬФА",
        "birth_date": "01.01.1990",
        "registration_number": "АДИ-РЕГ-000001",
    }
    return [
        {
            "id": "snils-card-001",
            "form": "SNILS card",
            "prompt": (
                "A realistic Russian SNILS insurance card for OCR testing, "
                f"with the large visible watermark {WATERMARK}, "
                "fictional data only, no real logos or personal data."
            ),
            "truth": {
                "snils": values["snils"],
                "full_name": values["full_name"],
            },
        },
        {
            "id": "adi-reg-2019-001",
            "form": "ADI REG 2019",
            "prompt": (
                "A realistic Russian ADI REG 2019 registration form for OCR "
                f"testing, visibly marked {WATERMARK}, fictional data only."
            ),
            "truth": {
                "form": "ADI REG 2019",
                "registration_number": values["registration_number"],
                "full_name": values["full_name"],
            },
        },
        {
            "id": "adi-reg-2013-001",
            "form": "ADI REG 2013",
            "prompt": (
                "A realistic Russian ADI REG 2013 registration form for OCR "
                f"testing, visibly marked {WATERMARK}, fictional data only."
            ),
            "truth": {
                "form": "ADI REG 2013",
                "registration_number": "АДИ-РЕГ-000002",
                "full_name": values["full_name"],
            },
        },
    ]


def validate() -> None:
    items = entries()
    if [item["form"] for item in items] != [
        "SNILS card",
        "ADI REG 2019",
        "ADI REG 2013",
    ]:
        raise ValueError("form coverage is incomplete")
    for item in items:
        if WATERMARK not in str(item["prompt"]):
            raise ValueError(f"missing watermark in {item['id']} prompt")
    snils = items[0]["truth"]["snils"]
    compact = str(snils).replace("-", "").replace(" ", "")
    if compact[-2:] != snils_checksum(compact[:-2]):
        raise ValueError("invalid SNILS checksum")


def _request_image(prompt: str, api_key: str, base_url: str) -> bytes:
    payload = json.dumps(
        {"model": MODEL, "prompt": prompt, "size": "1024x1024"}
    ).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/images/generations",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.load(response)
    try:
        return base64.b64decode(data["data"][0]["b64_json"], validate=True)
    except (KeyError, IndexError, ValueError) as error:
        raise RuntimeError(
            "Images API response did not contain b64_json"
        ) from error


def generate(output: Path) -> None:
    validate()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required (use --validate-only without a key)"
        )
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    truth = {}
    for item in entries():
        image = _request_image(
            str(item["prompt"]),
            api_key,
            os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
        )
        filename = f"{item['id']}.png"
        (output / filename).write_bytes(image)
        manifest.append(
            {
                "id": item["id"],
                "form": item["form"],
                "image": filename,
                "model": MODEL,
            }
        )
        truth[str(item["id"])] = item["truth"]
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    truth_path = output / "truth.json"
    truth_path.write_text(
        json.dumps(truth, ensure_ascii=False, indent=2) + "\n"
    )
    truth_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("generated-gpt-images")
    )
    args = parser.parse_args()
    try:
        validate()
        if args.validate_only:
            print("validated 3 forms and SNILS checksum")
        else:
            generate(args.output)
    except (RuntimeError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
