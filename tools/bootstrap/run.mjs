#!/usr/bin/env bun
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const SDK_PACKAGE = "@oh-my-pi/pi-coding-agent";
const MAX_INPUT_BYTES = 1024 * 1024;
const MUTATING_TOOLS = new Set(["write", "edit", "delete", "move", "ast_edit"]);
const LOCAL_READ_TOOLS = new Set(["read", "grep", "glob"]);
const PATH_KEYS = new Set([
  "path",
  "paths",
  "filePath",
  "file_path",
  "target",
  "destination",
  "dest",
  "source",
  "from",
  "to",
  "oldPath",
  "newPath",
]);
const ALLOWED_COMMANDS = new Set([
  "node tools/harness/checks/run-all.mjs",
  "PYTHONPATH=src python3 -m pytest tests",
  "python3 tools/architecture/validate.py --repo . --mode strict",
  "python3 tools/security/preflight.py",
]);
const EXTERNAL_MUTATION_ACTIONS = new Set([
  "write",
  "edit",
  "delete",
  "remove",
  "move",
  "rename",
  "create",
  "update",
  "patch",
  "apply",
  "upload",
  "send",
  "post",
  "publish",
  "commit",
  "deploy",
  "execute",
  "click",
  "fill",
  "drag",
  "grant",
  "deny",
  "approve",
  "reject",
  "attach",
  "transition",
  "close",
  "mark",
  "link",
  "unlink",
  "set",
  "start",
  "stop",
  "restart",
  "trigger",
  "submit",
  "cancel",
  "revoke",
]);
const EXTERNAL_MUTATION_NAME_PARTS = [
  ...EXTERNAL_MUTATION_ACTIONS,
  "type_text",
  "press_key",
];
const XD_READ_ONLY_NAME_PREFIXES = [
  "get",
  "list",
  "search",
  "query",
  "read",
  "fetch",
  "resolve",
  "status",
  "health",
  "inspect",
  "compare",
  "find",
  "explain",
  "take",
  "whoami",
  "server_info",
  "grep",
  "explore",
  "node",
  "callers",
  "callees",
  "impact",
  "files",
  "account",
  "connections",
];
const XD_READ_ONLY_ACTIONS = new Set([
  "get",
  "list",
  "search",
  "query",
  "read",
  "fetch",
  "resolve",
  "status",
  "inspect",
  "compare",
  "find",
  "open",
  "diagnostics",
  "definition",
  "references",
  "hover",
  "symbols",
  "type_definition",
  "implementation",
  "capabilities",
  "threads",
  "stack_trace",
  "scopes",
  "variables",
  "read_memory",
  "modules",
  "loaded_sources",
  "output",
  "sessions",
]);

function containsAny(value, candidates) {
  return candidates.some((candidate) => value.includes(candidate));
}

function isReadOnlyXdToolName(toolName) {
  return toolName
    .split("__")
    .some((segment) =>
      XD_READ_ONLY_NAME_PREFIXES.some(
        (prefix) => segment === prefix || segment.startsWith(`${prefix}_`),
      ),
    );
}

function within(root, candidate) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return (
    relative === "" ||
    (!relative.startsWith("..") && !path.isAbsolute(relative))
  );
}

function resolveCandidate(root, raw) {
  const absolute = path.isAbsolute(raw)
    ? path.resolve(raw)
    : path.resolve(root, raw);
  let current = absolute;
  const missing = [];
  while (!fs.existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) break;
    missing.unshift(path.basename(current));
    current = parent;
  }
  const real = fs.existsSync(current)
    ? fs.realpathSync.native(current)
    : current;
  return path.resolve(real, ...missing);
}

function allowedRelative(relative) {
  const normalized = relative.split(path.sep).join("/");
  if (
    normalized === ".fadd/bootstrap-result.json" ||
    normalized === ".gitlab-ci.fadd.yml" ||
    normalized === "docs/spec-index.json" ||
    normalized === "tools/gc/policy.json" ||
    normalized === "AGENTS.md"
  )
    return true;
  if (/^\.github\/workflows\/fadd-[^/]+\.yml$/.test(normalized)) return true;
  return [
    "architecture/",
    "security/threat-model/",
    "quality/",
    "container/",
  ].some((prefix) => normalized.startsWith(prefix));
}

function bootstrapPath(root, raw) {
  if (typeof raw !== "string" || !raw.trim() || raw.includes("\0"))
    return false;
  const candidate = resolveCandidate(root, raw.trim());
  if (!within(root, candidate)) return false;
  return allowedRelative(path.relative(root, candidate));
}

function readablePath(root, raw) {
  if (typeof raw !== "string" || !raw.trim() || raw.includes("\0"))
    return false;
  let value = raw.trim();
  const scheme = value.match(/^([a-z][a-z0-9+.-]*):\/\//i);
  if (scheme) return scheme[1].toLowerCase() !== "file";
  const selector =
    /:(?:raw|conflicts|img|\d+(?:-\d+)?(?:\+\d+)?(?:,\d+(?:-\d+)?)*)$/i;
  while (selector.test(value)) value = value.replace(selector, "");
  const candidate = resolveCandidate(root, value);
  if (!within(root, candidate)) return false;
  const relative = path.relative(root, candidate).split(path.sep).join("/");
  const parts = relative.split("/");
  if (
    relative.startsWith(".omp/") ||
    relative.startsWith("schemas/") ||
    (relative.startsWith("tools/") && relative !== "tools/gc/policy.json")
  ) {
    return false;
  }
  return !parts.some(
    (part) =>
      part === ".git" ||
      part === ".ssh" ||
      part === ".gnupg" ||
      part === ".env" ||
      part.startsWith(".env.") ||
      /^(?:id_rsa|id_ed25519|credentials(?:\.json)?|.*\.(?:pem|key))$/i.test(
        part,
      ),
  );
}

function pathsFrom(input) {
  const paths = [];
  function visit(value, key = "") {
    if (value == null) return;
    if (typeof value === "string") {
      if (PATH_KEYS.has(key)) paths.push(value);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => visit(item, key));
      return;
    }
    if (typeof value === "object") {
      Object.entries(value).forEach(([childKey, child]) =>
        visit(child, childKey),
      );
    }
  }
  visit(input);
  return [...new Set(paths)];
}

function initialAllowedFiles(root) {
  const files = [];
  const visit = (current) => {
    if (!fs.existsSync(current)) return;
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink()) return;
    if (stat.isFile()) {
      const relative = path.relative(root, current);
      if (allowedRelative(relative))
        files.push(resolveCandidate(root, current));
      return;
    }
    if (!stat.isDirectory()) return;
    for (const entry of fs.readdirSync(current))
      visit(path.join(current, entry));
  };
  [
    "architecture",
    "security/threat-model",
    "quality",
    "container",
    ".github/workflows",
  ].forEach((relative) => visit(path.join(root, relative)));
  [
    ".gitlab-ci.fadd.yml",
    "docs/spec-index.json",
    "tools/gc/policy.json",
    "AGENTS.md",
    ".fadd/bootstrap-result.json",
  ].forEach((relative) => visit(path.join(root, relative)));
  return new Set(files);
}

function managedParts(content) {
  const start = "<!-- OMP-FADD-REPO:START -->";
  const end = "<!-- OMP-FADD-REPO:END -->";
  const startIndex = content.indexOf(start);
  const endIndex = content.indexOf(end, startIndex + start.length);
  if (startIndex < 0 || endIndex < 0) return null;
  return {
    before: content.slice(0, startIndex),
    after: content.slice(endIndex + end.length),
  };
}

function safetyExtension(root, managedPaths) {
  const agentsPath = path.join(root, "AGENTS.md");
  const originalAgents = fs.existsSync(agentsPath)
    ? managedParts(fs.readFileSync(agentsPath, "utf8"))
    : null;
  const initialExisting = initialAllowedFiles(root);
  const managed = new Set(
    managedPaths.map((raw) => resolveCandidate(root, raw)),
  );
  return function bootstrapSafety(pi) {
    pi.on("tool_call", async (event) => {
      const name = String(event.toolName || "").toLowerCase();
      process.stderr.write(`[bootstrap-tool] ${name}\n`);
      const input = event.input || {};
      const xdDispatch =
        name === "write" &&
        typeof input.path === "string" &&
        /^xd:\/\/[A-Za-z0-9_./-]+$/.test(input.path);
      let xdTool = "";
      let xdInput = {};
      if (xdDispatch) {
        xdTool = input.path.slice("xd://".length).toLowerCase();
        if (typeof input.content === "string") {
          try {
            const parsed = JSON.parse(input.content);
            if (
              parsed &&
              typeof parsed === "object" &&
              !Array.isArray(parsed)
            ) {
              xdInput = parsed;
            }
          } catch {
            xdInput = {};
          }
        }
        const xdAction = String(xdInput.action || "").toLowerCase();
        const readOnlyDispatch =
          isReadOnlyXdToolName(xdTool) || XD_READ_ONLY_ACTIONS.has(xdAction);
        if (
          !readOnlyDispatch ||
          containsAny(xdTool, EXTERNAL_MUTATION_NAME_PARTS) ||
          EXTERNAL_MUTATION_ACTIONS.has(xdAction) ||
          (xdTool === "browser" && xdAction === "run")
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-XD: only classified read-only device dispatch is allowed",
          };
        }
      }
      if (LOCAL_READ_TOOLS.has(name)) {
        const candidates = pathsFrom(input);
        if (
          !candidates.length ||
          candidates.some((candidate) => !readablePath(root, candidate))
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-READ: local reads are confined to non-secret product and configuration paths; installed harness internals are excluded",
          };
        }
      }
      if (MUTATING_TOOLS.has(name) && !xdDispatch) {
        const candidates = pathsFrom(input);
        if (
          !candidates.length ||
          candidates.some((candidate) => !bootstrapPath(root, candidate))
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-SCOPE: configuration write is outside the bounded bootstrap roots",
          };
        }
        const resolvedCandidates = candidates.map((candidate) =>
          resolveCandidate(root, candidate),
        );
        if (
          resolvedCandidates.some(
            (candidate) =>
              initialExisting.has(candidate) && !managed.has(candidate),
          )
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-OWNER: pre-existing user-owned configuration is read-only",
          };
        }
        if (resolvedCandidates.some((candidate) => candidate === agentsPath)) {
          if (
            name !== "write" ||
            typeof input.content !== "string" ||
            !originalAgents
          ) {
            return {
              block: true,
              reason:
                "FADD-BOOTSTRAP-AGENTS: use write and preserve text outside the managed block",
            };
          }
          const proposed = managedParts(input.content);
          if (
            !proposed ||
            proposed.before !== originalAgents.before ||
            proposed.after !== originalAgents.after
          ) {
            return {
              block: true,
              reason:
                "FADD-BOOTSTRAP-AGENTS: text outside the managed block changed",
            };
          }
        }
      }
      const externalAction = String(input.action || "").toLowerCase();
      if (
        !LOCAL_READ_TOOLS.has(name) &&
        !MUTATING_TOOLS.has(name) &&
        name !== "bash" &&
        name !== "lsp" &&
        name !== "task" &&
        name !== "eval" &&
        (containsAny(name, EXTERNAL_MUTATION_NAME_PARTS) ||
          EXTERNAL_MUTATION_ACTIONS.has(externalAction))
      ) {
        return {
          block: true,
          reason:
            "FADD-BOOTSTRAP-EXTERNAL: state-changing external tools are disabled; read and research tools remain available",
        };
      }
      if (
        name === "browser" &&
        (externalAction === "run" ||
          EXTERNAL_MUTATION_ACTIONS.has(externalAction))
      ) {
        return {
          block: true,
          reason:
            "FADD-BOOTSTRAP-BROWSER: state-changing browser actions are disabled during bootstrap",
        };
      }
      if (name === "task" || name === "eval") {
        return {
          block: true,
          reason:
            "FADD-BOOTSTRAP-SESSION: nested agents and unrestricted eval are disabled in the bounded bootstrap",
        };
      }
      if (name === "lsp") {
        const action = String(input.action || "");
        if (
          action === "rename" ||
          action === "rename_file" ||
          (action === "code_actions" && input.apply === true)
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-LSP: source-changing LSP actions are disabled",
          };
        }
      }
      if (name === "bash") {
        const command = String(input.command || "").trim();
        const requestedCwd =
          input.cwd == null
            ? path.resolve(root)
            : resolveCandidate(root, String(input.cwd));
        const suppliedEnvironment = input.env ?? input.environment;
        const hasEnvironmentOverride =
          suppliedEnvironment != null &&
          (typeof suppliedEnvironment !== "object" ||
            Array.isArray(suppliedEnvironment) ||
            Object.keys(suppliedEnvironment).length > 0);
        if (
          !ALLOWED_COMMANDS.has(command) ||
          requestedCwd !== path.resolve(root) ||
          hasEnvironmentOverride ||
          input.async === true
        ) {
          return {
            block: true,
            reason:
              "FADD-BOOTSTRAP-COMMAND: only documented synchronous evidence commands in the repository with inherited environment are allowed",
          };
        }
      }
      return undefined;
    });
  };
}

function sdkEntry() {
  const roots = String(process.env.NODE_PATH || "")
    .split(path.delimiter)
    .map((item) => item.trim())
    .filter(Boolean);
  for (const root of roots) {
    const packageDirectory = path.join(root, ...SDK_PACKAGE.split("/"));
    const packageJson = path.join(packageDirectory, "package.json");
    if (!fs.existsSync(packageJson)) continue;
    const metadata = JSON.parse(fs.readFileSync(packageJson, "utf8"));
    const entry = metadata.exports?.["."]?.import || metadata.main;
    if (typeof entry === "string") return path.resolve(packageDirectory, entry);
  }
  throw new Error(`${SDK_PACKAGE} could not be resolved from NODE_PATH`);
}

async function waitForReadyResult(resultPath, repository, isPromptSettled) {
  const expected = path.join(repository, ".fadd", "bootstrap-result.json");
  if (path.resolve(resultPath) !== expected) {
    throw new Error(
      "runner resultPath is outside the bootstrap result contract",
    );
  }
  while (!isPromptSettled()) {
    await Bun.sleep(1000);
    try {
      const value = JSON.parse(fs.readFileSync(expected, "utf8"));
      if (
        value?.schemaVersion === "1.0" &&
        value?.status === "ready" &&
        value?.ready === true &&
        value?.repository === repository &&
        Array.isArray(value?.checks) &&
        value.checks.length > 0
      ) {
        return true;
      }
    } catch {
      // The agent has not written a complete result yet.
    }
  }
  return false;
}

function emit(value) {
  process.stdout.write(
    `${JSON.stringify({ kind: "omp-fadd-bootstrap", ...value })}\n`,
  );
}

let session;
try {
  const inputText = await Bun.stdin.text();
  if (Buffer.byteLength(inputText) > MAX_INPUT_BYTES)
    throw new Error("runner input exceeds 1 MiB");
  const input = JSON.parse(inputText);
  if (
    !input ||
    typeof input.cwd !== "string" ||
    typeof input.agentDir !== "string" ||
    typeof input.resultPath !== "string" ||
    typeof input.prompt !== "string" ||
    !Array.isArray(input.managedPaths) ||
    !input.managedPaths.every((item) => typeof item === "string")
  ) {
    throw new Error(
      "runner input must contain cwd, agentDir, resultPath, prompt, and managedPaths",
    );
  }
  const cwd = fs.realpathSync.native(path.resolve(input.cwd));
  const agentDir = fs.realpathSync.native(path.resolve(input.agentDir));
  const sdk = await import(pathToFileURL(sdkEntry()).href);
  const created = await sdk.createAgentSession({
    cwd,
    agentDir,
    sessionManager: sdk.SessionManager.inMemory(),
    autoApprove: true,
    spawns: "",
    enableIrc: false,
    extensions: [safetyExtension(cwd, input.managedPaths)],
  });
  session = created.session;
  let promptSettled = false;
  const promptPromise = session.prompt(input.prompt).finally(() => {
    promptSettled = true;
  });
  const completionSource = await Promise.race([
    promptPromise.then(() => "agent"),
    waitForReadyResult(input.resultPath, cwd, () => promptSettled).then(
      (ready) => (ready ? "result" : "agent"),
    ),
  ]);
  if (completionSource === "result") {
    await session.abort({
      goalReason: "internal",
      reason: "validated bootstrap result written",
    });
    await promptPromise.catch(() => undefined);
  } else {
    await promptPromise;
  }
  const advisorCatchup = await session.waitForAdvisorCatchup(5000);
  emit({ status: "completed", advisorCatchup, completionSource });
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  emit({ status: "failed", error: message.slice(0, 4096) });
  process.exitCode = 1;
} finally {
  if (session) {
    try {
      await session.dispose();
    } catch (error) {
      if (!process.exitCode) {
        const message = error instanceof Error ? error.message : String(error);
        emit({
          status: "failed",
          error: `dispose failed: ${message.slice(0, 4000)}`,
        });
        process.exitCode = 1;
      }
    }
  }
}
