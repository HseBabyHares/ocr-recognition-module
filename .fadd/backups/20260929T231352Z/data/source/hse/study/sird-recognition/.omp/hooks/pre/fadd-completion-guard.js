import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const NODE = process.env.FADD_NODE_BIN || "node";
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const CHECK = path.join(ROOT, "tools/harness/checks/fadd-completion-check.mjs");
const DOCS_REMINDER =
  "Before taking any action, read https://omp.sh/docs/hooks and the repository AGENTS.md. " +
  "Confirm the hook lifecycle and loaded files before editing tasks.md or running commands. " +
  "After a hook change, restart the OMP or Claude session so the new module is loaded.";
let startReminderShown = false;
let completionNoticeShown = false;

async function checkCompletion() {
  try {
    const { stdout } = await execFileAsync(NODE, [CHECK, "--repo", ROOT], {
      cwd: ROOT,
      maxBuffer: 1024 * 1024,
      timeout: 25_000,
    });
    const report = JSON.parse(stdout);
    if (report.status === "pass") return null;
    return report.reasons?.join("; ") || "FADD completion check is blocked.";
  } catch (error) {
    const output = error.stdout || error.stderr || error.message;
    try {
      const report = JSON.parse(output);
      return report.reasons?.join("; ") || "FADD completion check is blocked.";
    } catch {
      return `FADD completion check failed: ${output}`;
    }
  }
}

export default function completionGuard(pi) {
  pi.on("before_agent_start", () => {
    if (startReminderShown) return;
    startReminderShown = true;
    return {
      message: {
        content: DOCS_REMINDER,
        display: false,
        attribution: "agent",
      },
    };
  });

  const resetSessionState = () => {
    startReminderShown = false;
    completionNoticeShown = false;
  };
  pi.on("session_start", resetSessionState);
  pi.on("session_switch", resetSessionState);
  pi.on("session_compact", resetSessionState);

  pi.on("session_stop", async ({ stop_hook_active }) => {
    if (stop_hook_active || completionNoticeShown) return;
    const reason = await checkCompletion();
    if (!reason) return;
    completionNoticeShown = true;
    return { decision: "block", reason };
  });
}
