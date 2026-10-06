#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

BRANCH = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.IfExp,
    ast.Match,
    ast.comprehension,
)


class Metrics(ast.NodeVisitor):
    def __init__(self):
        self.cyclomatic = 1
        self.cognitive = 0
        self.nesting = 0
        self.max_nesting = 0
        self.returns = 0
        self.locals = set()

    def visit_Return(self, node):
        self.returns += 1
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.locals.add(node.id)

    def generic_visit(self, node):
        nested = isinstance(node, BRANCH)
        if nested:
            self.cyclomatic += 1
            self.cognitive += 1 + self.nesting
            self.nesting += 1
            self.max_nesting = max(self.max_nesting, self.nesting)
        super().generic_visit(node)
        if nested:
            self.nesting -= 1


def iter_functions(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args()
    policy = json.loads(a.policy.read_text())["complexity"]
    files = []
    for raw in a.paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(
                x for x in p.rglob("*.py") if "__pycache__" not in x.parts
            )
        elif p.suffix == ".py" and p.exists():
            files.append(p)
    findings = []
    for p in sorted(set(files)):
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > policy["maxModuleLines"]:
            findings.append(
                {
                    "rule": "module-lines",
                    "path": str(p),
                    "line": 1,
                    "observed": len(lines),
                    "limit": policy["maxModuleLines"],
                }
            )
        try:
            tree = ast.parse(text, filename=str(p))
        except SyntaxError as e:
            findings.append(
                {
                    "rule": "syntax",
                    "path": str(p),
                    "line": e.lineno or 1,
                    "message": e.msg,
                }
            )
            continue
        for fn in iter_functions(tree):
            m = Metrics()
            m.visit(fn)
            end = getattr(fn, "end_lineno", fn.lineno)
            values = {
                "cyclomatic": m.cyclomatic,
                "cognitive": m.cognitive,
                "nesting": m.max_nesting,
                "arguments": len(fn.args.posonlyargs)
                + len(fn.args.args)
                + len(fn.args.kwonlyargs)
                + (1 if fn.args.vararg else 0)
                + (1 if fn.args.kwarg else 0),
                "locals": len(
                    m.locals
                    - {
                        a.arg
                        for a in [
                            *fn.args.posonlyargs,
                            *fn.args.args,
                            *fn.args.kwonlyargs,
                        ]
                    }
                ),
                "returns": m.returns,
                "function-lines": end - fn.lineno + 1,
            }
            limits = {
                "cyclomatic": "maxCyclomatic",
                "cognitive": "maxCognitive",
                "nesting": "maxNesting",
                "arguments": "maxArguments",
                "locals": "maxLocals",
                "returns": "maxReturns",
                "function-lines": "maxFunctionLines",
            }
            for rule, key in limits.items():
                if values[rule] > policy[key]:
                    findings.append(
                        {
                            "rule": rule,
                            "path": str(p),
                            "line": fn.lineno,
                            "symbol": fn.name,
                            "observed": values[rule],
                            "limit": policy[key],
                        }
                    )
    result = {
        "schemaVersion": "1.0",
        "status": "fail" if findings else "pass",
        "files": len(set(files)),
        "findings": findings,
    }
    text = json.dumps(result, indent=2) + "\n"
    print(text, end="")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
