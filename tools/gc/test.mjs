#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
const root = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "../..",
);
const td = fs.mkdtempSync(path.join(os.tmpdir(), "fadd-gc-"));
try {
  fs.mkdirSync(path.join(td, "src"));
  fs.writeFileSync(
    path.join(td, "src/a.py"),
    "# TODO\n".repeat(20) + "def a():\n    return 1\n",
  );
  const out = path.join(td, "out");
  const r = spawnSync(
    process.execPath,
    [
      path.join(root, "tools/gc/run.mjs"),
      "--repo",
      td,
      "--out",
      out,
      "--policy",
      path.join(root, "tools/gc/policy.json"),
      "--fail-on",
      "new",
    ],
    { encoding: "utf8" },
  );
  if (r.status !== 1) throw new Error(`expected finding exit 1: ${r.stderr}`);
  const j = JSON.parse(fs.readFileSync(path.join(out, "inventory.json")));
  if (!j.newFindings.some((x) => x.rule === "todo-density"))
    throw new Error("canary missing");
  console.log('{"check":"gc-canary","status":"pass"}');
} finally {
  fs.rmSync(td, { recursive: true, force: true });
}
