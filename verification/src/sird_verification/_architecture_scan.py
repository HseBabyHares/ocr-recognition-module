"""Source scanning helpers for the architecture boundary oracle."""

from __future__ import annotations

import ast
from pathlib import Path

from sird_verification._oracle_support import imported_modules

type ScanResult = tuple[tuple[str, ...], bool]


def scan_path(
    path: Path,
    package_root: Path,
    forbidden: tuple[str, ...],
) -> ScanResult:
    """Read one Python source file and locate forbidden imports."""
    try:
        syntax_tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return (), True
    return _forbidden_locations(syntax_tree, path, package_root, forbidden), False


def _forbidden_locations(
    syntax_tree: ast.AST,
    path: Path,
    package_root: Path,
    forbidden: tuple[str, ...],
) -> tuple[str, ...]:
    locations = (
        _forbidden_locations_for_node(node, path, package_root, forbidden)
        for node in ast.walk(syntax_tree)
    )
    return tuple(
        location
        for node_locations in locations
        for location in node_locations
    )


def _forbidden_locations_for_node(
    node: ast.AST,
    path: Path,
    package_root: Path,
    forbidden: tuple[str, ...],
) -> tuple[str, ...]:
    locations = (
        f"{path.relative_to(package_root)}:{top_level}"
        for module_name in imported_modules(node)
        for top_level in (module_name.split(".", maxsplit=1)[0].lower(),)
        if top_level in forbidden
    )
    return tuple(locations)


def scan(
    package_root: Path,
    forbidden: tuple[str, ...],
) -> tuple[int, tuple[str, ...], int]:
    """Collect forbidden imports and parse failures across Python files."""
    python_files = sorted(package_root.rglob("*.py"))
    return _scan_files(python_files, package_root, forbidden)


def _scan_files(
    python_files: list[Path],
    package_root: Path,
    forbidden: tuple[str, ...],
) -> tuple[int, tuple[str, ...], int]:
    scan_results = tuple(
        scan_path(path, package_root, forbidden) for path in python_files
    )
    return (
        len(python_files),
        _collect_violations(scan_results),
        _count_parse_failures(scan_results),
    )


def _collect_violations(
    scan_results: tuple[ScanResult, ...],
) -> tuple[str, ...]:
    return tuple(
        violation
        for violations_for_file, _parse_failed in scan_results
        for violation in violations_for_file
    )


def _count_parse_failures(
    scan_results: tuple[ScanResult, ...],
) -> int:
    return sum(
        int(parse_failed) for _violations, parse_failed in scan_results
    )
