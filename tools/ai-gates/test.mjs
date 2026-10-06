#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { validateReview } from "./lib/review.mjs";

const ROOT = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "../..",
);

const validReview = {
  schemaVersion: "1.0",
  reviewer: "x",
  verdict: "pass",
  confidence: 0.9,
  summary: "ok",
  findings: [],
  coverage: ["diff"],
  blindSpots: [],
};

function verifyReviewValidation() {
  assert.equal(validateReview(validReview).errors.length, 0);
  const invalidReview = { ...validReview, confidence: 2 };
  assert(validateReview(invalidReview).errors.length > 0);
}

function createRepositoryFixture(repositoryPath) {
  fs.mkdirSync(path.join(repositoryPath, "src"), { recursive: true });
  fs.mkdirSync(path.join(repositoryPath, "docs/specs"), { recursive: true });
  fs.writeFileSync(
    path.join(repositoryPath, "docs/spec-index.json"),
    JSON.stringify({
      schemaVersion: "1.0",
      status: "active",
      watchedImplementationRoots: ["src/**"],
      entries: [{ spec: "docs/specs/a.md" }],
    }),
  );
  fs.writeFileSync(
    path.join(repositoryPath, "docs/specs/a.md"),
    "# Requirement\nReturn the requested value.\n",
  );
  fs.writeFileSync(
    path.join(repositoryPath, "src/a.js"),
    "export const a=1;\n",
  );
}

function commitRepositoryFixture(repositoryPath) {
  spawnSync("git", ["init", "-q"], { cwd: repositoryPath });
  spawnSync("git", ["config", "user.email", "eval@example.invalid"], {
    cwd: repositoryPath,
  });
  spawnSync("git", ["config", "user.name", "Eval"], {
    cwd: repositoryPath,
  });
  spawnSync("git", ["add", "."], { cwd: repositoryPath });
  spawnSync("git", ["commit", "-qm", "chore(test): base"], { cwd: repositoryPath });

  const baseRevision = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: repositoryPath,
    encoding: "utf8",
  }).stdout.trim();

  fs.writeFileSync(
    path.join(repositoryPath, "src/a.js"),
    "export const a=2;\n",
  );
  spawnSync("git", ["add", "."], { cwd: repositoryPath });
  spawnSync("git", ["commit", "-qm", "chore(test): change"], { cwd: repositoryPath });

  const headRevision = spawnSync("git", ["rev-parse", "HEAD"], {
    cwd: repositoryPath,
    encoding: "utf8",
  }).stdout.trim();

  return { baseRevision, headRevision };
}

function prepareReviewContext(
  repositoryPath,
  baseRevision,
  headRevision,
  contextPath,
) {
  const commandResult = spawnSync(
    process.execPath,
    [
      path.join(ROOT, "tools/ai-gates/prepare-context.mjs"),
      "--repo",
      repositoryPath,
      "--base",
      baseRevision,
      "--head",
      headRevision,
      "--out",
      contextPath,
    ],
    { cwd: ROOT, encoding: "utf8" },
  );
  assert.equal(commandResult.status, 0, commandResult.stderr);
  assert.equal(
    JSON.parse(fs.readFileSync(path.join(contextPath, "review-context.json")))
      .complete,
    true,
  );
}

function runOpenRouterDryRun(temporaryDirectory, contextPath) {
  const commandResult = spawnSync(
    process.execPath,
    [
      path.join(ROOT, "tools/ai-gates/openrouter-vote.mjs"),
      "--context",
      path.join(contextPath, "review-context.json"),
      "--diff",
      path.join(contextPath, "candidate.diff"),
      "--prompt",
      path.join(contextPath, "review-prompt.md"),
      "--schema",
      path.join(contextPath, "spec-drift-review.schema.json"),
      "--out",
      path.join(temporaryDirectory, "or"),
      "--models",
      "vendor/model-a,vendor/model-b",
      "--dry-run",
    ],
    { cwd: ROOT, encoding: "utf8" },
  );
  assert.equal(commandResult.status, 0, commandResult.stderr);
}

function verifyDeliveryGate(temporaryDirectory) {
  const reviewPath = path.join(temporaryDirectory, "codex.json");
  fs.writeFileSync(
    reviewPath,
    JSON.stringify({ ...validReview, reviewer: "codex" }),
  );

  const commandResult = spawnSync(
    process.execPath,
    [
      path.join(ROOT, "tools/ai-gates/verify-delivery-gate.mjs"),
      "--mode",
      "shadow",
      "--upstream",
      '{"deterministic":"success"}',
      "--codex",
      reviewPath,
      "--out",
      path.join(temporaryDirectory, "gate.json"),
    ],
    { cwd: ROOT, encoding: "utf8" },
  );
  assert.equal(commandResult.status, 0, commandResult.stderr);
}

verifyReviewValidation();

const temporaryDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "fadd-ai-"));
try {
  const repositoryPath = path.join(temporaryDirectory, "repo");
  const contextPath = path.join(temporaryDirectory, "context");

  createRepositoryFixture(repositoryPath);
  const { baseRevision, headRevision } =
    commitRepositoryFixture(repositoryPath);
  prepareReviewContext(repositoryPath, baseRevision, headRevision, contextPath);
  runOpenRouterDryRun(temporaryDirectory, contextPath);
  verifyDeliveryGate(temporaryDirectory);
  console.log('{"check":"ai-gates","status":"pass"}');
} finally {
  fs.rmSync(temporaryDirectory, { recursive: true, force: true });
}
