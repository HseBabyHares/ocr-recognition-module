#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../..");
const runner = path.join(ROOT, "tools/harness/checks/run-openspec.mjs");
const completion = path.join(ROOT, "tools/harness/checks/fadd-completion-check.mjs");

function run(script, repository) {
  return spawnSync(process.execPath, [script, "--repo", repository], {
    cwd: repository,
    encoding: "utf8",
  });
}

function readResult(result) {
  assert.equal(result.stdout.trim().length > 0, true, result.stderr);
  return JSON.parse(result.stdout);
}

const temporaryDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "fadd-openspec-"));
try {
  let result = run(runner, temporaryDirectory);
  assert.equal(result.status, 0);
  assert.equal(readResult(result).status, "not-applicable");

  fs.mkdirSync(path.join(temporaryDirectory, "openspec/changes/example"), {
    recursive: true,
  });
  fs.mkdirSync(path.join(temporaryDirectory, "node_modules/.bin"), {
    recursive: true,
  });
  const fakeCli = path.join(temporaryDirectory, "node_modules/.bin/openspec");
  fs.writeFileSync(
    fakeCli,
    `#!/usr/bin/env node
const fs = require("node:fs");
const path = require("node:path");
if (process.argv.includes("status")) {
  const tasks = fs.readFileSync(
    path.join(process.cwd(), "openspec/changes/example/tasks.md"),
    "utf8",
  );
  console.log(JSON.stringify({
    changes: [{
      changeName: "example",
      isComplete: tasks.includes("[x]") || tasks.includes("[X]"),
    }],
  }));
} else {
  console.log(JSON.stringify({
    items: [],
    summary: { totals: { items: 0, passed: 0, failed: 0 } },
  }));
}
`,
    "utf8",
  );
  fs.chmodSync(fakeCli, 0o755);

  fs.writeFileSync(
    path.join(temporaryDirectory, "openspec/changes/example/tasks.md"),
    "# Tasks\n\n- [ ] 1.1 Implement the change\n",
    "utf8",
  );
  result = run(completion, temporaryDirectory);
  assert.equal(result.status, 1);
  let report = readResult(result);
  assert.match(report.reasons.join(" "), /unfinished OpenSpec tasks/);
  fs.writeFileSync(
    path.join(temporaryDirectory, "openspec/changes/example/tasks.md"),
    "# Tasks\n\n* [~] 1.1 Implement the change\n",
    "utf8",
  );
  result = run(completion, temporaryDirectory);
  assert.equal(result.status, 1);
  report = readResult(result);
  assert.equal(report.status, "blocked");

  fs.writeFileSync(
    path.join(temporaryDirectory, "openspec/changes/example/tasks.md"),
    "# Tasks\n\n1. [X] 1.1 Implement the change\n",
    "utf8",
  );
  result = run(completion, temporaryDirectory);
  assert.equal(result.status, 0, `${result.stderr}\n${result.stdout}`);
  report = readResult(result);
  assert.equal(report.status, "pass");

  fs.writeFileSync(
    path.join(temporaryDirectory, "openspec/changes/example/tasks.md"),
    "# Tasks\n\n- [ ] 1.2 Another change\n",
    "utf8",
  );
  const ompHookPath = path.join(
    temporaryDirectory,
    ".omp/hooks/pre/fadd-completion-guard.js",
  );
  fs.mkdirSync(path.dirname(ompHookPath), { recursive: true });
  fs.copyFileSync(
    path.join(ROOT, "repository/.omp/hooks/pre/fadd-completion-guard.js"),
    ompHookPath,
  );
  const tempChecks = path.join(temporaryDirectory, "tools/harness/checks");
  fs.mkdirSync(tempChecks, { recursive: true });
  fs.copyFileSync(
    path.join(ROOT, "tools/harness/checks/fadd-completion-check.mjs"),
    path.join(tempChecks, "fadd-completion-check.mjs"),
  );
  fs.copyFileSync(
    path.join(ROOT, "tools/harness/checks/run-openspec.mjs"),
    path.join(tempChecks, "run-openspec.mjs"),
  );
  const handlers = new Map();
  const ompModule = await import(
    `${pathToFileURL(ompHookPath).href}?test=${Date.now()}`,
  );
  ompModule.default({ on: (event, handler) => handlers.set(event, handler) });
  let decision = await handlers.get("session_stop")({});
  assert.equal(decision.decision, "block");

  const claudeHook = path.join(
    ROOT,
    "repository/.claude/hooks/fadd-completion-check.mjs",
  );
  result = spawnSync(process.execPath, [claudeHook], {
    cwd: temporaryDirectory,
    env: { ...process.env, CLAUDE_PROJECT_DIR: temporaryDirectory },
    encoding: "utf8",
  });
  assert.equal(result.status, 0);
  assert.equal(JSON.parse(result.stdout).decision, "block");

  fs.writeFileSync(
    path.join(temporaryDirectory, "openspec/changes/example/tasks.md"),
    "# Tasks\n\n- [x] 1.2 Another change\n",
    "utf8",
  );
  decision = await handlers.get("session_stop")({});
  assert.equal(decision, undefined);

  console.log('{"check":"openspec","status":"pass"}');
} finally {
  fs.rmSync(temporaryDirectory, { recursive: true, force: true });
}
