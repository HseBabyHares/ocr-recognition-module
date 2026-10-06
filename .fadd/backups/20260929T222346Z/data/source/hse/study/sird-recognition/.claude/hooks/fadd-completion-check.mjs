#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import { spawnSync } from "node:child_process";
import path from "node:path";

const repository = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const checker = path.join(repository, "tools/harness/checks/fadd-completion-check.mjs");
const noticeDirectory =
  process.env.FADD_NOTICE_DIR ||
  path.join(os.tmpdir(), "omp-fadd-completion-notices");

function readHookInput() {
  try {
    const input = fs.readFileSync(0, "utf8").trim();
    return input ? JSON.parse(input) : {};
  } catch {
    return {};
  }
}

function claimNotice(sessionId) {
  if (!sessionId) return true;
  fs.mkdirSync(noticeDirectory, { recursive: true });
  const key = crypto
    .createHash("sha256")
    .update(`${path.resolve(repository)}\0${sessionId}`)
    .digest("hex");
  const marker = path.join(noticeDirectory, `${key}.shown`);
  try {
    const descriptor = fs.openSync(marker, "wx");
    fs.closeSync(descriptor);
    return true;
  } catch (error) {
    if (error.code === "EEXIST") return false;
    return true;
  }
}

const hookInput = readHookInput();
if (hookInput.stop_hook_active) {
  process.exit(0);
}

const result = spawnSync(process.execPath, [checker, "--repo", repository], {
  cwd: repository,
  encoding: "utf8",
});

if (result.status === 0 || !claimNotice(hookInput.session_id)) process.exit(0);

let report;
try {
  report = JSON.parse(result.stdout);
} catch {
  report = null;
}

const reason = report?.reasons?.join("; ") || result.stderr.trim() || "FADD completion check failed.";
console.log(JSON.stringify({ decision: "block", reason }));
process.exit(0);
