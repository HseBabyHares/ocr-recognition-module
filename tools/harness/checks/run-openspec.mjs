#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

function argumentValue(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

function activeChanges(root) {
  const changes = path.join(root, "openspec", "changes");
  if (!fs.existsSync(changes)) return [];
  return fs
    .readdirSync(changes, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== "archive")
    .map((entry) => entry.name)
    .sort();
}

function openspecCommand(repository) {
  const local = path.join(repository, "node_modules", ".bin", "openspec");
  return fs.existsSync(local) ? local : "openspec";
}

function parseJson(text) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.lastIndexOf("\n{");
    if (start < 0) return null;
    try {
      return JSON.parse(trimmed.slice(start + 1));
    } catch {
      return null;
    }
  }
}

function writeResult(result, outputPath) {
  const text = `${JSON.stringify(result, null, 2)}\n`;
  if (outputPath) {
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, text);
  }
  process.stdout.write(text);
}

const repository = path.resolve(argumentValue("repo", process.cwd()));
const outputPath = argumentValue("out", null);
const openspecRoot = path.join(repository, "openspec");
const changes = activeChanges(repository);

if (!fs.existsSync(openspecRoot)) {
  writeResult(
    {
      schemaVersion: "1.0",
      check: "openspec",
      status: "not-applicable",
      repository,
      activeChanges: [],
      message: "No openspec directory exists.",
    },
    outputPath,
  );
  process.exit(0);
}
const command = spawnSync(
  openspecCommand(repository),
  ["validate", "--all", "--json", "--no-interactive"],
  { cwd: repository, encoding: "utf8" },
);

if (command.error) {
  writeResult(
    {
      schemaVersion: "1.0",
      check: "openspec",
      status: "blocked",
      repository,
      activeChanges: changes,
      error: "OpenSpec CLI is not available.",
      message: "Install the repository's pinned OpenSpec CLI before completion.",
    },
    outputPath,
  );
  process.exit(1);
}

const validation = parseJson(command.stdout);
const passed = command.status === 0 && validation !== null;
const result = {
  schemaVersion: "1.0",
  check: "openspec",
  status: passed ? "pass" : "fail",
  repository,
  activeChanges: changes,
  validation,
};

if (!passed) {
  result.error = command.stderr.trim() || "OpenSpec validation failed.";
}

writeResult(result, outputPath);
process.exit(passed ? 0 : 1);
