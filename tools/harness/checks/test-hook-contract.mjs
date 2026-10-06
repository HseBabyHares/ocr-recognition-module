#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
const PACKAGE = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "../../..",
);
const td = fs.mkdtempSync(path.join(os.tmpdir(), "fadd-hook-"));
try {
  fs.mkdirSync(path.join(td, ".omp/hooks/pre"), { recursive: true });
  fs.mkdirSync(path.join(td, ".omp/authority"), { recursive: true });
  fs.mkdirSync(path.join(td, "tools/harness/lib"), { recursive: true });
  fs.copyFileSync(
    path.join(PACKAGE, "tools/harness/policy.json"),
    path.join(td, "tools/harness/policy.json"),
  );
  fs.copyFileSync(
    path.join(PACKAGE, "tools/harness/lib/policy.mjs"),
    path.join(td, "tools/harness/lib/policy.mjs"),
  );
  const hook = path.join(td, ".omp/hooks/pre/fadd-policy-guard.js");
  let src = fs.readFileSync(
    path.join(PACKAGE, "repository/.omp/hooks/pre/fadd-policy-guard.js"),
    "utf8",
  );
  fs.writeFileSync(hook, src);
  fs.writeFileSync(
    path.join(td, ".omp/hooks/package.json"),
    '{"type":"module"}\n',
  );
  const handlers = new Map();
  const pi = { on: (e, h) => handlers.set(e, h) };
  const mod = await import(`${pathToFileURL(hook).href}?t=${Date.now()}`);
  mod.default(pi);
  assert(handlers.has("tool_call"));
  assert(handlers.has("tool_result"));
  const allowed = await handlers.get("tool_call")({
    toolName: "bash",
    input: { command: "printf FADD_POLICY_DENY_CANARY" },
  });
  assert.equal(allowed, undefined);
  const red = await handlers.get("tool_result")({
    toolName: "read",
    content: [{ type: "text", text: "Authorization: Bearer abc.def.ghi" }],
    details: { x: "OPENAI_API_KEY=sk-abcdefghijklmnopqrst" },
  });
  assert(red);
  assert(!JSON.stringify(red).includes("abc.def.ghi"));
  assert(!JSON.stringify(red).includes("abcdefghijkl"));
  assert(fs.existsSync(path.join(td, ".omp/audit/fadd-policy.jsonl")));
  console.log('{"check":"hook-contract","status":"pass"}');
} finally {
  fs.rmSync(td, { recursive: true, force: true });
}
