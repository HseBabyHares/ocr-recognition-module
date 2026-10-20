#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10"]
# ///
"""Render synthetic SNILS documents with exact ground truth.

Three layouts: the green insurance card, the ADI-REG notice of the Pension
Fund (2019) and the notice of the Social Fund (2023). Every value is
fictional, every SNILS has a valid checksum, and every image carries a small
SYNTHETIC TEST mark. Negative layouts (--negatives N) add pages that must be
rejected: an unsupported page, a notice with no issuer, and a card with a bad
SNILS checksum. Run: uv run tools/corpus/render_snils_forms.py --out DIR
[--count N] [--negatives N] [--seed S] [--clean]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from generate_gpt_test_images import WATERMARK, snils_checksum  # noqa: E402

LAYOUTS = ("snils_card", "adi_reg_2019", "adi_reg_2023")
# Negative layout -> (expected form decision, a verified SNILS is allowed).
NEGATIVES = {
    "unsupported_page": ("form_unsupported", False),
    "notice_no_issuer": ("form_ambiguous", False),
    "card_bad_checksum": ("snils_card", False),
}
ISSUERS = {"adi_reg_2019": "ПФР", "adi_reg_2023": "СФР"}
MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
SURNAMES = (
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Васильев",
    "Петров",
    "Соколов",
    "Михайлов",
    "Новиков",
    "Волков",
    "Морозов",
    "Лебедев",
    "Козлов",
    "Егоров",
    "Павлов",
    "Орлов",
    "Зайцев",
    "Белов",
    "Медведев",
    "Никитин",
    "Тарасов",
)
MALE_NAMES = (
    "Александр",
    "Дмитрий",
    "Максим",
    "Сергей",
    "Андрей",
    "Алексей",
    "Иван",
    "Михаил",
    "Никита",
    "Олег",
    "Павел",
    "Роман",
    "Игорь",
    "Виктор",
)
FEMALE_NAMES = (
    "Анна",
    "Мария",
    "Елена",
    "Ольга",
    "Наталья",
    "Татьяна",
    "Ирина",
    "Светлана",
    "Екатерина",
    "Юлия",
    "Дарья",
    "Ксения",
)
PATRONYMICS = {
    "Александр": ("Александрович", "Александровна"),
    "Дмитрий": ("Дмитриевич", "Дмитриевна"),
    "Сергей": ("Сергеевич", "Сергеевна"),
    "Андрей": ("Андреевич", "Андреевна"),
    "Алексей": ("Алексеевич", "Алексеевна"),
    "Иван": ("Иванович", "Ивановна"),
    "Михаил": ("Михайлович", "Михайловна"),
    "Олег": ("Олегович", "Олеговна"),
    "Павел": ("Павлович", "Павловна"),
    "Игорь": ("Игоревич", "Игоревна"),
    "Виктор": ("Викторович", "Викторовна"),
    "Николай": ("Николаевич", "Николаевна"),
    "Юрий": ("Юрьевич", "Юрьевна"),
}
CITIES = (
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Самара",
    "Омск",
    "Ростов-на-Дону",
    "Уфа",
    "Пермь",
    "Воронеж",
    "Тверь",
    "Тула",
)
FONT_DIRS = (
    os.environ.get("SIRD_FONT_DIR", ""),
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    str(Path.home() / ".local/share/fonts"),
)
FONT_FILES = {
    "serif": ("LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"),
    "serif_bold": ("LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"),
    "serif_italic": ("LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf"),
    "mono": ("LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"),
}
INK = (25, 25, 25)
BLUE = (55, 60, 150)


@dataclass(frozen=True)
class Person:
    """Ground truth for one synthetic document."""

    surname: str
    name: str
    patronymic: str
    sex: str
    snils: str
    birth_date: date
    birth_place: str
    registration_date: date

    @property
    def full_name(self) -> str:
        return f"{self.surname} {self.name} {self.patronymic}"


def make_person(rng: random.Random) -> Person:
    male = rng.random() < 0.5
    surname = rng.choice(SURNAMES)
    patronymic = PATRONYMICS[rng.choice(tuple(PATRONYMICS))][0 if male else 1]
    base = f"{rng.randrange(2_000_000, 999_999_999):09d}"
    born = date(1950, 1, 1) + timedelta(days=rng.randrange(20_000))
    return Person(
        surname=surname if male else f"{surname}а",
        name=rng.choice(MALE_NAMES if male else FEMALE_NAMES),
        patronymic=patronymic,
        sex="мужской" if male else "женский",
        snils=f"{base}{snils_checksum(base)}",
        birth_date=born,
        birth_place=rng.choice(CITIES),
        registration_date=born + timedelta(days=rng.randrange(6_600, 20_000)),
    )


def snils_text(digits: str, check_separator: str) -> str:
    groups = f"{digits[:3]}-{digits[3:6]}-{digits[6:9]}"
    return f"{groups}{check_separator}{digits[9:]}"


def long_date(value: date) -> str:
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def find_font(role: str) -> str:
    for file_name in FONT_FILES[role]:
        for directory in filter(None, FONT_DIRS):
            match = next(Path(directory).rglob(file_name), None)
            if match:
                return str(match)
    raise SystemExit(f"no font for {role}: install one of {FONT_FILES[role]}")


class Fonts:
    def __init__(self) -> None:
        self._paths = {role: find_font(role) for role in FONT_FILES}

    def __call__(self, role: str, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self._paths[role], size)


def centered(
    draw: ImageDraw.ImageDraw,
    width: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=INK,
) -> None:
    draw.text(
        ((width - draw.textlength(text, font=font)) / 2, y),
        text,
        font=font,
        fill=fill,
    )


def watermark(
    draw: ImageDraw.ImageDraw, size: tuple[int, int], fonts: Fonts
) -> None:
    font = fonts("serif", 18)
    text_width = draw.textlength(WATERMARK, font=font)
    draw.text(
        (size[0] - text_width - 16, size[1] - 32),
        WATERMARK,
        font=font,
        fill=(150, 150, 150),
    )


def render_card(
    person: Person, rng: random.Random, fonts: Fonts
) -> Image.Image:
    width, height = 1400, 880
    image = Image.new("RGB", (width, height), (229, 238, 222))
    draw = ImageDraw.Draw(image)
    for offset in range(0, 150, 6):  # guilloche band
        points = [
            (1000 + offset + 18 * math.sin(y / 23 + offset), y)
            for y in range(0, height, 8)
        ]
        draw.line(points, fill=(196, 216, 180), width=2)
    for radius in range(40, 200, 14):  # rosette
        draw.ellipse(
            (1080 - radius, 640 - radius, 1080 + radius, 640 + radius),
            outline=(200, 220, 190),
            width=2,
        )
    draw.rectangle((0, 170, width, 250), fill=(205, 222, 190))
    centered(draw, width, 100, "Российская Федерация", fonts("serif_bold", 44))
    centered(draw, width, 180, "СТРАХОВОЕ СВИДЕТЕЛЬСТВО", fonts("serif", 64))
    centered(
        draw,
        width,
        262,
        "ГОСУДАРСТВЕННОГО ПЕНСИОННОГО СТРАХОВАНИЯ",
        fonts("serif_bold", 32),
    )
    number = snils_text(person.snils, rng.choice(("-", " ")))
    draw.text((460, 350), f"N~ {number}", font=fonts("mono", 44), fill=INK)
    label, value = fonts("serif_italic", 28), fonts("serif", 38)
    draw.text((140, 470), "Ф.И.О.", font=label, fill=(70, 70, 70))
    for index, part in enumerate(
        (person.surname, person.name, person.patronymic)
    ):
        draw.text((310, 460 + 50 * index), part.upper(), font=value, fill=INK)
    draw.text(
        (140, 630), "Дата и место рождения", font=label, fill=(70, 70, 70)
    )
    draw.text(
        (640, 620),
        f"{long_date(person.birth_date)} года",
        font=fonts("mono", 40),
        fill=INK,
    )
    draw.text((310, 690), person.birth_place.upper(), font=value, fill=INK)
    draw.text((140, 790), "Пол", font=label, fill=(70, 70, 70))
    draw.text((310, 780), person.sex.capitalize(), font=value, fill=INK)
    watermark(draw, (width, height), fonts)
    return image


def _notice_rows(person: Person, bold: bool) -> list[tuple[list[str], str]]:
    birth = (
        long_date(person.birth_date)
        if bold
        else person.birth_date.strftime("%d.%m.%Y")
    )
    registration = (
        long_date(person.registration_date)
        if bold
        else person.registration_date.strftime("%d.%m.%Y")
    )
    snils_label = (
        ["Страховой номер", "индивидуального лицевого счета", "(СНИЛС)"]
        if bold
        else ["Страховой номер индивидуального", "лицевого счета (СНИЛС)"]
    )
    return [
        (snils_label, snils_text(person.snils, "-")),
        (["Фамилия"], person.surname),
        (["Имя"], person.name),
        (["Отчество (при наличии)"], person.patronymic),
        (["Дата рождения"], birth),
        (
            ["Место рождения"],
            person.birth_place if bold else f"г. {person.birth_place}",
        ),
        ([""], ""),
        (["Пол"], person.sex if bold else person.sex.capitalize()),
        (["Дата регистрации"], registration),
    ]


def render_notice(
    person: Person,
    rng: random.Random,
    fonts: Fonts,
    bold: bool,
    issuer: str | None,
) -> Image.Image:
    width, height = 1200, 1260
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    label_font = fonts("serif", 30)
    value_font = fonts("serif_bold", 32) if bold else fonts("serif_italic", 32)
    value_fill = INK if bold else BLUE
    if bold:
        centered(
            draw,
            width,
            50,
            "Уведомление о регистрации в системе индивидуального",
            label_font,
        )
        centered(draw, width, 90, "(персонифицированного) учета", label_font)
        y, value_x = 200, 540
    else:
        draw.text((70, 40), "Форма АДИ-РЕГ", font=label_font, fill=INK)
        title = fonts("serif_bold", 32)
        for index, line in enumerate(
            (
                "Уведомление",
                "о регистрации в системе индивидуального",
                "(персонифицированного) учета",
            )
        ):
            centered(draw, width, 90 + 44 * index, line, title)
        y, value_x = 270, 680
    for labels, value in _notice_rows(person, bold):
        for index, line in enumerate(labels):
            draw.text((70, y + 38 * index), line, font=label_font, fill=INK)
        value_y = y + 38 * (len(labels) - 1)
        if value:
            draw.text(
                (value_x + 20, value_y - 2),
                value,
                font=value_font,
                fill=value_fill,
            )
            draw.line(
                (value_x, value_y + 40, width - 70, value_y + 40),
                fill=INK,
                width=2,
            )
        y = value_y + (60 if bold else 50)
    y += 50
    draw.text(
        (70, y), "Наименование должности работника", font=label_font, fill=INK
    )
    if issuer:
        draw.text(
            (70, y + 38),
            f"территориального органа {issuer}",
            font=label_font,
            fill=INK,
        )
    y += 130
    officer = (
        f"{rng.choice('АВЕКМНОС')}.{rng.choice('АВЕКМНОС')}. "
        f"{rng.choice(SURNAMES)}{'а' if rng.random() < 0.5 else ''}"
    )
    small = fonts("serif", 24)
    for x0, x1, text, caption in (
        (70, 520, "Специалист", "(заполняется только при получении)"),
        (600, 780, "", "(подпись)"),
        (830, 1130, officer, "(расшифровка подписи)"),
    ):
        if text:
            draw.text(
                (x0 + 30, y - 40),
                text,
                font=fonts("serif_italic", 28),
                fill=value_fill,
            )
        draw.line((x0, y, x1, y), fill=INK, width=2)
        draw.text((x0 + 10, y + 8), caption, font=small, fill=INK)
    draw.line(
        [
            (620 + 12 * step, y - 15 - 18 * math.sin(step))
            for step in range(14)
        ],
        fill=BLUE,
        width=3,
    )  # signature
    draw.ellipse((90, y + 70, 260, y + 240), outline=(110, 110, 180), width=5)
    centered_x = 175 - draw.textlength("ОБРАЗЕЦ", font=small) / 2
    draw.text(
        (centered_x, y + 140), "ОБРАЗЕЦ", font=small, fill=(110, 110, 180)
    )
    draw.text((330, y + 140), "М.П.", font=label_font, fill=INK)
    watermark(draw, (width, height), fonts)
    return image


def degrade(image: Image.Image, rng: random.Random) -> Image.Image:
    """Add the skew, blur and noise of a phone photo."""
    background = image.getpixel((5, 5))
    image = image.rotate(
        rng.uniform(-2.0, 2.0),
        resample=Image.BICUBIC,
        expand=True,
        fillcolor=background,
    )
    image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.0, 1.2)))
    noise = Image.effect_noise(image.size, rng.uniform(8, 24)).convert("RGB")
    return Image.blend(image, noise, rng.uniform(0.03, 0.08))


def render_unsupported(
    person: Person, rng: random.Random, fonts: Fonts
) -> Image.Image:
    """A certificate page with no SNILS form marker and no SNILS number."""
    width, height = 1200, 900
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    text = fonts("serif", 32)
    centered(draw, width, 80, "СПРАВКА", fonts("serif_bold", 48))
    for index, line in enumerate(
        (
            f"Выдана: {person.full_name}",
            f"Дата рождения: {person.birth_date.strftime('%d.%m.%Y')}",
            "в том, что указанное лицо является студентом",
            f"очной формы обучения с {rng.randrange(2018, 2025)} года.",
            "Справка выдана для предъявления по месту требования.",
        )
    ):
        draw.text((90, 220 + 60 * index), line, font=text, fill=INK)
    watermark(draw, (width, height), fonts)
    return image


def bad_checksum(person: Person) -> Person:
    """The same person with a SNILS whose control number is wrong."""
    control = (int(person.snils[9:]) + 1) % 100
    return replace(person, snils=f"{person.snils[:9]}{control:02d}")


def render(
    layout: str, person: Person, rng: random.Random, fonts: Fonts
) -> Image.Image:
    if layout in {"snils_card", "card_bad_checksum"}:
        return render_card(person, rng, fonts)
    if layout == "unsupported_page":
        return render_unsupported(person, rng, fonts)
    bold = layout == "adi_reg_2023"
    return render_notice(person, rng, fonts, bold, ISSUERS.get(layout))


def _plan(count: int, negatives: int) -> list[tuple[str, int]]:
    # Positives come first, so --negatives never changes the positive files.
    return [
        (layout, index) for layout in LAYOUTS for index in range(count)
    ] + [(layout, index) for layout in NEGATIVES for index in range(negatives)]


def _expected(layout: str) -> dict[str, object]:
    form, verified = NEGATIVES.get(layout, (layout, True))
    return {"expected_form": form, "expected_verified": verified}


def generate(
    out: Path, count: int, seed: int, clean: bool, negatives: int = 0
) -> list[dict]:
    rng = random.Random(seed)
    fonts = Fonts()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for layout, index in _plan(count, negatives):
        person = make_person(rng)
        if layout == "card_bad_checksum":
            person = bad_checksum(person)
        image = render(layout, person, rng, fonts)
        suffix = "png" if clean else "jpg"
        file_name = f"{layout}-{index:03d}.{suffix}"
        if clean:
            image.save(out / file_name)
        else:
            degrade(image, rng).save(
                out / file_name, quality=rng.randrange(60, 95)
            )
        truth = asdict(person)
        truth["birth_date"] = person.birth_date.isoformat()
        truth["registration_date"] = person.registration_date.isoformat()
        rows.append(
            {
                "file": file_name,
                "layout": layout,
                **_expected(layout),
                "full_name": person.full_name,
                **truth,
            }
        )
    with (out / "manifest.jsonl").open("w", encoding="utf-8") as manifest:
        for row in rows:
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--count", type=int, default=5, help="documents per layout"
    )
    parser.add_argument(
        "--negatives",
        type=int,
        default=0,
        help="documents per negative layout",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="write lossless PNG with no photo noise",
    )
    args = parser.parse_args()
    rows = generate(
        args.out, args.count, args.seed, args.clean, args.negatives
    )
    print(f"wrote {len(rows)} documents to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
