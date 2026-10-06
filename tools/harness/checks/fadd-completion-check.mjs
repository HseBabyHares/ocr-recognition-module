#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const NODE = process.env.FADD_NODE_BIN || "node";

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function openspecCommand(repository) {
  const local = path.join(repository, "node_modules", ".bin", "openspec");
  return fs.existsSync(local) ? local : "openspec";
}

function findActiveChanges(repository) {
  const directory = path.join(repository, "openspec", "changes");
  if (!fs.existsSync(directory)) return [];
  return fs
    .readdirSync(directory, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== "archive")
    .map((entry) => entry.name)
    .sort();
}

function unfinishedTasks(repository, changes) {
  const tasks = [];
  for (const change of changes) {
    const file = path.join(repository, "openspec", "changes", change, "tasks.md");
    if (!fs.existsSync(file)) continue;
    const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
    lines.forEach((line, index) => {
      const match = line.match(
        /^\s*(?:[-*+]|(?:\d{1,9}[.)]))\s*\[([^\]]*)\]\s*(.*)$/,
      );
      if (match && match[1].trim().toLowerCase() !== "x") {
        tasks.push(`${path.relative(repository, file)}:${index + 1}`);
      }
    });
  }
  return tasks;
}

function runOpenSpecValidation(repository) {
  const checker = path.join(
    path.dirname(fileURLToPath(import.meta.url)),
    "run-openspec.mjs",
  );
  const result = spawnSync(NODE, [checker, "--repo", repository], {
    cwd: repository,
    encoding: "utf8",
    timeout: 8_000,
  });
  let report = null;
  try {
    report = JSON.parse(result.stdout);
  } catch {
    report = null;
  }
  return { result, report };
}

function runOpenSpecStatus(repository) {
  const result = spawnSync(
    openspecCommand(repository),
    ["status", "--all", "--json", "--no-color"],
    { cwd: repository, encoding: "utf8", timeout: 8_000 },
  );
  let report = null;
  try {
    report = JSON.parse(result.stdout);
  } catch {
    report = null;
  }
  return { result, report };
}

const repository = path.resolve(argumentValue("repo", process.cwd()));
const changes = findActiveChanges(repository);

if (!fs.existsSync(path.join(repository, "openspec"))) {
  console.log(JSON.stringify({
    schemaVersion: "1.0",
    check: "fadd-completion",
    status: "pass",
    repository,
    activeChanges: [],
    message: "No OpenSpec change is active.",
  }, null, 2));
  process.exit(0);
}

const unfinished = unfinishedTasks(repository, changes);
const validation = runOpenSpecValidation(repository);
const status = runOpenSpecStatus(repository);
const incompleteChanges = [];
if (Array.isArray(status.report?.changes)) {
  const statusByName = new Map(
    status.report.changes.map((change) => [change.changeName, change]),
  );
  for (const change of changes) {
    const entry = statusByName.get(change);
    if (!entry || entry.isComplete !== true) {
      incompleteChanges.push(change);
    }
  }
}
const statusUnavailable =
  !Array.isArray(status.report?.changes) || status.result.status !== 0;
const blocked =
  unfinished.length > 0 ||
  incompleteChanges.length > 0 ||
  validation.result.status !== 0 ||
  statusUnavailable;
const reasons = [];
if (unfinished.length > 0) {
  reasons.push(`unfinished OpenSpec tasks: ${unfinished.join(", ")}`);
}
if (incompleteChanges.length > 0) {
  reasons.push(`incomplete OpenSpec changes: ${incompleteChanges.join(", ")}`);
}
if (validation.result.status !== 0) {
  reasons.push(
    validation.report?.message ||
      validation.report?.error ||
      "OpenSpec validation failed",
  );
}
if (statusUnavailable) {
  reasons.push("OpenSpec status is unavailable.");
}

console.log(JSON.stringify({
  schemaVersion: "1.0",
  check: "fadd-completion",
  status: blocked ? "blocked" : "pass",
  repository,
  activeChanges: changes,
  reasons,
  validation: validation.report,
  openSpecStatus: status.report,
}, null, 2));
process.exit(blocked ? 1 : 0);
