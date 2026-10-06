#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  canonicalJson,
  evaluateToolCall,
  redactBlocks,
  sha256,
} from "../lib/policy.mjs";
const ROOT = path.resolve(
    path.dirname(new URL(import.meta.url).pathname),
    "../../..",
  ),
  policy = JSON.parse(
    fs.readFileSync(path.join(ROOT, "tools/harness/policy.json")),
  );
const td = fs.mkdtempSync(path.join(os.tmpdir(), "fadd-policy-"));
let n = 0;
const eq = (a, b, m) => {
  n++;
  assert.equal(a, b, m);
};
try {
  fs.mkdirSync(path.join(td, ".git"));
  fs.mkdirSync(path.join(td, "generated"));
  for (const input of [
    { toolName: "write", input: { path: "src/a.py" } },
    { toolName: "write", input: { path: "../x" } },
    { toolName: "write", input: { path: ".omp/authority/x" } },
    { toolName: "bash", input: { command: "git reset --hard HEAD~1" } },
    { toolName: "bash", input: { command: "printf FADD_POLICY_DENY_CANARY" } },
    {
      toolName: "bash",
      input: { command: "echo harmless; git push origin main" },
    },
  ]) {
    eq(
      evaluateToolCall({ ...input, cwd: td, policy }).allow,
      true,
    );
  }
  eq(
    evaluateToolCall({
      toolName: "mcp__example__write",
      input: { path: "tools/harness/policy.json" },
      cwd: td,
      policy,
    }).allow,
    true,
  );
  const red = redactBlocks(
    { x: "OPENAI_API_KEY=sk-abcdefghijklmnopqrst" },
    policy,
  );
  eq(JSON.stringify(red).includes("abcdefghijkl"), false);
  console.log(
    JSON.stringify({ check: "policy", status: "pass", assertions: n }),
  );
} finally {
  fs.rmSync(td, { recursive: true, force: true });
}
