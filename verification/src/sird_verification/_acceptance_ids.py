"""Stable acceptance-test identifiers for the acceptance runner."""

from __future__ import annotations

_FIRST_TEST_NUMBER = 1
_LAST_TEST_NUMBER = 25
_AC_OCR_ONE_END = 19
_TEST_ID_PREFIX = "TEST-OCR-"


def _test_id(number: int) -> str:
    return "{}{:03d}".format(_TEST_ID_PREFIX, number)


def _ids_for(numbers: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(_test_id(number) for number in numbers)


FIRST_TEST_NUMBER = _FIRST_TEST_NUMBER
LAST_TEST_NUMBER = _LAST_TEST_NUMBER
TEST_ID_PREFIX = _TEST_ID_PREFIX
ALL_TEST_NUMBERS = tuple(range(FIRST_TEST_NUMBER, LAST_TEST_NUMBER + 1))
ALL_TEST_IDS = _ids_for(ALL_TEST_NUMBERS)
AC_OCR_ONE_NUMBERS = tuple(
    range(FIRST_TEST_NUMBER, _AC_OCR_ONE_END)
) + (21,)
AC_OCR_ONE_IDS = _ids_for(AC_OCR_ONE_NUMBERS)
_AC_OCR_TWO_NUMBERS_FIRST = (3, 4, 5, 7, 8, 9)
_AC_OCR_TWO_NUMBERS_LAST = (11, 12, 14, 17, 23, 24, 25)
AC_OCR_TWO_NUMBERS = _AC_OCR_TWO_NUMBERS_FIRST + _AC_OCR_TWO_NUMBERS_LAST
AC_OCR_TWO_IDS = _ids_for(AC_OCR_TWO_NUMBERS)
AC_OCR_THREE_NUMBERS = (18, 19, 20, 22, 23, 24, 25)
AC_OCR_THREE_IDS = _ids_for(AC_OCR_THREE_NUMBERS)
