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
const EVIDENCE_REMINDER =
  "Before acting, inspect the real repository/runtime code and relevant current official or version-matched primary documentation. " +
  "Model memory is not proof: cite sources, identify gaps, and do not invent verification.";

function readHookInput() {
  try {
    const input = fs.readFileSync(0, "utf8").trim();
    return input ? JSON.parse(input) : {};
  } catch {
    return {};
  }
}

function noticeMarker(sessionId) {
  if (!sessionId) return null;
  const key = crypto
    .createHash("sha256")
    .update(`${path.resolve(repository)}\0${sessionId}`)
    .digest("hex");
  return path.join(noticeDirectory, `${key}.shown`);
}
function claimNotice(sessionId) {
  const marker = noticeMarker(sessionId);
  if (!marker) return true;
  fs.mkdirSync(noticeDirectory, { recursive: true });
  try {
    const descriptor = fs.openSync(marker, "wx");
    fs.closeSync(descriptor);
    return true;
  } catch (error) {
    if (error.code === "EEXIST") return false;
    return true;
  }
}

function clearNotice(sessionId) {
  const marker = noticeMarker(sessionId);
  if (!marker) return;
  try {
    fs.unlinkSync(marker);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

const hookInput = readHookInput();
if (hookInput.hook_event_name === "SessionStart") {
  if (hookInput.source === "compact") clearNotice(hookInput.session_id);
  console.log(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: EVIDENCE_REMINDER,
      },
    }),
  );
  process.exit(0);
}
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
