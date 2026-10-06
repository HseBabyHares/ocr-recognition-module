#!/usr/bin/env python3
"""Measure normalized Python token clones by statement shingles."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import keyword
import tokenize
from collections import defaultdict
from pathlib import Path
from typing import Any

MIN_STATEMENTS = 6
MIN_TOKENS = 50
_DOCSTRING_NODES = (
    ast.Module,
    ast.ClassDef,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
)


def _docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_NODES):
            continue
        body = node.body
        if not body or not isinstance(body[0], ast.Expr):
            continue
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            first = body[0]
            start = first.lineno
            end = getattr(first, "end_lineno", start)
            lines.update(range(start, end + 1))
    return lines


def _canonical_tokens(text: str, tree: ast.AST) -> list[tuple[str, int]]:
    doc_lines = _docstring_lines(tree)
    significant: list[tokenize.TokenInfo] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.start[0] in doc_lines:
                continue
            if token.type in {
                tokenize.COMMENT,
                tokenize.NL,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENCODING,
                tokenize.ENDMARKER,
            }:
                continue
            significant.append(token)
    except tokenize.TokenError:
        return []

    result: list[tuple[str, int]] = []
    for index, token in enumerate(significant):
        if token.type == tokenize.NEWLINE:
            result.append(("$stmt", token.start[0]))
            continue
        previous = significant[index - 1].string if index else ""
        following = (
            significant[index + 1].string
            if index + 1 < len(significant)
            else ""
        )
        if token.type == tokenize.NAME:
            preserve = (
                keyword.iskeyword(token.string)
                or previous == "."
                or following == "("
            )
            value = token.string if preserve else "$id"
        elif token.type in {tokenize.NUMBER, tokenize.STRING}:
            value = "$lit"
        else:
            value = token.string
        result.append((value, token.start[0]))
    return result


def _statements(path: Path) -> tuple[list[dict[str, Any]], int]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return [], 0
    statements: list[dict[str, Any]] = []
    current: list[tuple[str, int]] = []
    tokens = _canonical_tokens(text, tree)
    for token in tokens:
        if token[0] == "$stmt":
            if current:
                statements.append(
                    {
                        "tokens": current,
                        "start": current[0][1],
                        "end": token[1],
                    }
                )
                current = []
        else:
            current.append(token)
    if current:
        statements.append(
            {
                "tokens": current,
                "start": current[0][1],
                "end": current[-1][1],
            }
        )
    return statements, len(text.splitlines())


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["path"] == right["path"]
        and left["startStatement"] <= right["endStatement"] + 1
        and right["startStatement"] <= left["endStatement"] + 1
    )


def _collapse_locations(
    locations: set[tuple[str, int, int, int, int]],
) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    for path, start_statement, end_statement, start_line, end_line in sorted(
        locations
    ):
        if (
            collapsed
            and collapsed[-1]["path"] == path
            and start_statement <= collapsed[-1]["endStatement"] + 1
        ):
            collapsed[-1]["endStatement"] = max(
                collapsed[-1]["endStatement"], end_statement
            )
            collapsed[-1]["endLine"] = max(collapsed[-1]["endLine"], end_line)
        else:
            collapsed.append(
                {
                    "path": path,
                    "startStatement": start_statement,
                    "endStatement": end_statement,
                    "startLine": start_line,
                    "endLine": end_line,
                }
            )
    return collapsed


def _scope_metrics(
    files: list[Path], repo: Path, scope: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_classes: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    total_lines = 0
    for path in files:
        statements, line_count = _statements(path)
        total_lines += line_count
        for index in range(0, len(statements) - MIN_STATEMENTS + 1):
            window = statements[index : index + MIN_STATEMENTS]
            tokens = [
                token
                for statement in window
                for token, _ in statement["tokens"]
            ]
            if len(tokens) < MIN_TOKENS:
                continue
            digest = hashlib.sha256("\x1f".join(tokens).encode()).hexdigest()[
                :24
            ]
            raw_classes[digest].append(
                {
                    "path": path.relative_to(repo).as_posix(),
                    "startStatement": index,
                    "endStatement": index + MIN_STATEMENTS - 1,
                    "startLine": window[0]["start"],
                    "endLine": window[-1]["end"],
                }
            )

    merged_classes: list[dict[str, Any]] = []
    for digest, locations in sorted(raw_classes.items()):
        unique = {
            (
                item["path"],
                item["startStatement"],
                item["endStatement"],
                item["startLine"],
                item["endLine"],
            )
            for item in locations
        }
        deduplicated = [
            {
                "path": path,
                "startStatement": start_statement,
                "endStatement": end_statement,
                "startLine": start_line,
                "endLine": end_line,
            }
            for path, start_statement, end_statement, start_line, end_line in sorted(
                unique
            )
        ]
        paths = {item["path"] for item in deduplicated}
        if len(paths) < 2:
            continue
        anchor = min(
            (item["path"], item["startStatement"], digest)
            for item in deduplicated
        )
        for clone_class in merged_classes:
            if clone_class["paths"] != paths:
                continue
            if any(
                _overlaps(left, right)
                for left in clone_class["locations"]
                for right in deduplicated
            ):
                clone_class["locations"].extend(deduplicated)
                clone_class["anchor"] = min(clone_class["anchor"], anchor)
                break
        else:
            merged_classes.append(
                {"paths": paths, "locations": deduplicated, "anchor": anchor}
            )

    findings: list[dict[str, Any]] = []
    duplicated_lines: set[tuple[str, int]] = set()
    for clone_class in merged_classes:
        unique = {
            (
                item["path"],
                item["startStatement"],
                item["endStatement"],
                item["startLine"],
                item["endLine"],
            )
            for item in clone_class["locations"]
        }
        collapsed = _collapse_locations(unique)
        for item in collapsed:
            duplicated_lines.update(
                (item["path"], line)
                for line in range(item["startLine"], item["endLine"] + 1)
            )
        if scope == "production":
            digest = clone_class["anchor"][2]
            locations_text = ", ".join(
                f"{item['path']}:{item['startLine']}-{item['endLine']}"
                for item in collapsed
            )
            first = collapsed[0]
            findings.append(
                {
                    "fingerprint": f"python-clone:{digest}",
                    "rule": "python-clone",
                    "path": first["path"],
                    "line": first["startLine"],
                    "severity": "low",
                    "evidence": (
                        f"clone class {digest}: {len(collapsed)} locations, "
                        f"{locations_text}"
                    ),
                }
            )

    return findings, {
        "pythonLoc": total_lines,
        "duplicatedLoc": len(duplicated_lines),
        "duplicatedLineRatio": round(
            len(duplicated_lines) / total_lines if total_lines else 0.0, 6
        ),
        "cloneClasses": len(merged_classes),
        "scope": scope,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--production-files", nargs="*", default=[])
    parser.add_argument("--test-files", nargs="*", default=[])
    args = parser.parse_args()

    production_findings, production = _scope_metrics(
        [Path(item) for item in args.production_files], args.repo, "production"
    )
    _, tests = _scope_metrics(
        [Path(item) for item in args.test_files], args.repo, "tests"
    )
    total = {
        "pythonLoc": production["pythonLoc"] + tests["pythonLoc"],
        "duplicatedLoc": production["duplicatedLoc"] + tests["duplicatedLoc"],
        "duplicatedLineRatio": round(
            (production["duplicatedLoc"] + tests["duplicatedLoc"])
            / max(production["pythonLoc"] + tests["pythonLoc"], 1),
            6,
        ),
        "cloneClasses": production["cloneClasses"] + tests["cloneClasses"],
        "scope": "repository",
    }
    print(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "findings": production_findings,
                "metrics": {
                    "production": production,
                    "tests": tests,
                    "repository": total,
                    "thresholds": {
                        "minStatements": MIN_STATEMENTS,
                        "minTokens": MIN_TOKENS,
                    },
                },
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
