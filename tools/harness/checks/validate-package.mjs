#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const failures = [],
  warnings = [];
const exists = (r) => fs.existsSync(path.join(ROOT, r)),
  read = (r) => fs.readFileSync(path.join(ROOT, r), "utf8");
const required = [
  ".editorconfig",
  ".gitignore",
  "pyproject.toml",
  "uv.lock",
  "README.md",
  "APPEND_SYSTEM.md",
  "AGENTS.md",
  "config.overlay.yml",
  "src/omp_fadd/__init__.py",
  "src/omp_fadd/__main__.py",
  "src/omp_fadd/cli.py",
  "src/omp_fadd/bootstrap.py",
  "src/omp_fadd/config.py",
  "src/omp_fadd/common.py",
  "src/omp_fadd/runtime.py",
  "src/omp_fadd/managed.py",
  "src/omp_fadd/profile.py",
  "src/omp_fadd/repository.py",
  "src/omp_fadd/lifecycle.py",
  "src/omp_fadd/py.typed",
  "src/omp_fadd/data/__init__.py",
  "tests/test_cli.py",
  "tests/test_bootstrap.py",
  "tests/cli_workflow.py",
  "tools/bootstrap/run.mjs",
  "schemas/bootstrap-result.schema.json",
  "tools/harness/policy.json",
  "tools/harness/checks/run-all.mjs",
  "tools/security/toolchain.lock.json",
  "tools/security/install.py",
  "tools/security/preflight.py",
  "tools/security/scan.py",
  "tools/security/refresh-databases.sh",
  "tools/quality/toolchain.lock.json",
  "tools/quality/policy.example.json",
  "tools/quality/complexity.py",
  "tools/quality/run.py",
  "templates/repository/quality/python-policy.json",
  "tools/container/versions.json",
  "tools/container/policy.example.json",
  "tools/container/check.py",
  "tools/container/install.py",
  "templates/repository/container/policy.json",
  "tools/meta/toolchain.lock.json",
  "tools/meta/lint.sh",
  "tools/architecture/validate.py",
  "tools/harness/checks/run-openspec.mjs",
  "tools/harness/checks/fadd-completion-check.mjs",
  "tools/harness/checks/test-openspec.mjs",
  "tools/ai-gates/openrouter-vote.mjs",
  "tools/ai-gates/verify-delivery-gate.mjs",
  "tools/gc/run.mjs",
  "repository/.omp/hooks/pre/fadd-policy-guard.js",
  "repository/.omp/hooks/pre/fadd-completion-guard.js",
  "repository/.claude/hooks/fadd-completion-check.mjs",
  "repository/.github/CODEOWNERS.fadd.example",
  "repository/.github/rulesets/fadd-main-evaluate.json",
  "repository/.github/workflows/fadd-delivery-gates.yml",
  "repository/.github/workflows/fadd-ai-review.yml",
  "repository/.github/workflows/fadd-security-db-refresh.yml",
  "repository/.github/workflows/fadd-smart-gc.yml",
  "templates/repository/architecture/policy.json",
  "templates/repository/security/threat-model/dfd.json",
];
for (const r of required) if (!exists(r)) failures.push(`missing ${r}`);
if (exists("SYSTEM.md")) failures.push("active root SYSTEM.md must be absent");
const pyproject = exists("pyproject.toml") ? read("pyproject.toml") : "";
const version = pyproject.match(/^version\s*=\s*"([^"]+)"/m)?.[1] || "";
if (version !== "7.1.1") failures.push(`unexpected project version ${version}`);
if (!pyproject.includes('omp-fadd = "omp_fadd.cli:main"'))
  failures.push("pyproject console script must target omp_fadd.cli:main");
if (!pyproject.includes('packages = ["src/omp_fadd"]'))
  failures.push("pyproject must use the src package layout");
const cliModules = [
  "cli.py",
  "bootstrap.py",
  "config.py",
  "common.py",
  "runtime.py",
  "managed.py",
  "profile.py",
  "repository.py",
  "lifecycle.py",
];
for (const file of cliModules) {
  const rel = `src/omp_fadd/${file}`;
  if (!exists(rel)) continue;
  const lines = read(rel).split(/\r?\n/).length;
  const limit = file === "cli.py" ? 400 : 500;
  if (lines > limit)
    failures.push(`${rel} exceeds ${limit} lines; got ${lines}`);
}
if (exists("APPEND_SYSTEM.md")) {
  const lines = read("APPEND_SYSTEM.md").trimEnd().split(/\r?\n/).length;
  if (lines < 8 || lines > 80)
    failures.push(`APPEND_SYSTEM.md unexpected length ${lines}`);
}
if (exists("AGENTS.md")) {
  const lines = read("AGENTS.md").trimEnd().split(/\r?\n/).length;
  if (lines >= 100)
    failures.push(`AGENTS.md must remain below 100 lines; got ${lines}`);
}
if (exists("config.overlay.yml")) {
  const c = read("config.overlay.yml");
  if (/includeSkills\s*:/.test(c))
    failures.push("overlay must not hide the existing skill library");
  if (/security\s*:\s*\n\s*enabled\s*:\s*true/.test(c))
    failures.push("OMP LLM review must not replace real scanner gates");
}
const disposable = [
  "VERSION",
  "CHECKSUMS.sha256",
  "PACKAGE_MANIFEST.json",
  "EVAL_REPORT.md",
  "IMPLEMENTATION_NOTES.md",
  "SOURCE_NOTES.md",
  "install.py",
  "capabilities",
  "docs/spec-index.example.json",
  "evals",
  "docs/archive/security-scan.original.sh",
];
for (const rel of disposable)
  if (exists(rel)) failures.push(`disposable package artifact present: ${rel}`);
const labOnly = ["RUNTIME_EVAL.md", "runtime-eval", "tools/runtime-eval"];
for (const rel of labOnly)
  if (exists(rel))
    failures.push(
      `research-lab artifact present in production package: ${rel}`,
    );
const expected = [
  "adversarial-review",
  "architecture-review",
  "aws-s3",
  "bdd",
  "change-audit",
  "clean-code",
  "container-delivery",
  "ddd-blueprint",
  "editorial-restraint",
  "error-kb",
  "fadd-context-management",
  "fadd-controlled-change",
  "fadd-defect-repair",
  "fadd-independent-review",
  "fadd-openspec",
  "fadd-repository-garbage-collection",
  "fadd-repository-recon",
  "fadd-system-verification",
  "fadd-verifiable-spec",
  "fadd-work-route",
  "grpc-contract",
  "language-contract",
  "message-delivery",
  "opentelemetry",
  "prometheus",
  "python-alembic-migrations",
  "python-granian",
  "python-litestar-service",
  "python-quality",
  "python-sqlalchemy",
  "python-taskiq",
  "redis",
  "requirement-boundary",
  "requirement-traceability",
  "security-remediation",
  "spec-authoring",
  "spec-change-plan",
  "spec-dependency-evidence",
  "spec-design-contract",
  "spec-environment-scout",
  "spec-experiment",
  "spec-migrations",
  "spec-observability",
  "spec-performance",
  "spec-prd-decomposition",
  "spec-readme",
  "spec-release",
  "spec-security-scanners",
  "spec-threat-model",
  "stride-review",
  "tdd",
  "test-reality",
  "uuid-tracking",
  "verify",
  "wide-log",
];
const methodologySkills = new Set([
  "fadd-context-management",
  "fadd-controlled-change",
  "fadd-defect-repair",
  "fadd-independent-review",
  "fadd-openspec",
  "fadd-repository-garbage-collection",
  "fadd-repository-recon",
  "fadd-system-verification",
  "fadd-verifiable-spec",
  "fadd-work-route",
]);
const skillRoot = path.join(ROOT, "skills");
const actual = exists("skills")
  ? fs
      .readdirSync(skillRoot, { withFileTypes: true })
      .filter((x) => x.isDirectory())
      .map((x) => x.name)
      .sort()
  : [];
if (JSON.stringify(actual) !== JSON.stringify(expected))
  failures.push(`active skills mismatch: ${actual.join(", ")}`);
const headings = [
  "## Purpose",
  "## Use when",
  "## Do not use when",
  "## Required capabilities",
  "## Optional capabilities",
  "## Inputs",
  "## Workflow",
  "## Outputs",
  "## Evidence",
  "## Completion criteria",
  "## Stop and escalate",
  "## Context policy",
];
for (const name of actual) {
  const rel = `skills/${name}/SKILL.md`;
  if (!exists(rel)) {
    failures.push(`missing ${rel}`);
    continue;
  }
  const text = read(rel);
  if (!new RegExp(`^name:\\s*${name}$`, "m").test(text))
    failures.push(`${rel}: name mismatch`);
  if (!/^description:\s*.+$/m.test(text))
    failures.push(`${rel}: description missing`);
  for (const h of headings)
    if (!text.includes(h)) failures.push(`${rel}: missing ${h}`);
}
for (const name of actual.filter((x) => x.startsWith("fadd-")))
  if (!methodologySkills.has(name))
    failures.push(`non-methodology skill uses fadd prefix: ${name}`);
const agents = exists("agents")
  ? fs.readdirSync(path.join(ROOT, "agents")).filter((x) => x.endsWith(".md"))
  : [];
if (agents.length !== 6)
  failures.push(`expected 6 namespaced agents, got ${agents.length}`);
for (const a of agents)
  if (!a.startsWith("fadd-")) failures.push(`unnamespaced agent ${a}`);
for (const rel of [
  "tools/security/toolchain.lock.json",
  "tools/quality/toolchain.lock.json",
  "tools/container/versions.json",
  "tools/meta/toolchain.lock.json",
  "repository/.github/action-pins.json",
]) {
  if (!exists(rel)) continue;
  try {
    const value = JSON.parse(read(rel));
    if (JSON.stringify(value).includes('"error"'))
      failures.push(`${rel}: unresolved tool/action version`);
  } catch (e) {
    failures.push(`${rel}: ${e.message}`);
  }
}
let pins = {};
try {
  pins = JSON.parse(read("repository/.github/action-pins.json")).actions || {};
} catch {}
if (exists("repository/.github/workflows"))
  for (const file of fs
    .readdirSync(path.join(ROOT, "repository/.github/workflows"))
    .filter((x) => /\.ya?ml$/.test(x))) {
    const text = read(`repository/.github/workflows/${file}`);
    for (const match of text.matchAll(/uses:\s*([^\s#]+)@([^\s#]+)/g)) {
      const action = match[1],
        ref = match[2],
        pin = pins[action];
      if (!pin) {
        failures.push(`${file}: action ${action} absent from action-pins.json`);
        continue;
      }
      if (ref !== pin.ref)
        failures.push(
          `${file}: ${action}@${ref} does not match manifest ${pin.ref}`,
        );
      if (!/^[0-9a-f]{40}$/.test(ref)) {
        if (action === "openai/codex-action" && pin.strictModeAllowed === false)
          warnings.push(
            `${file}: Codex action remains tag-pinned and is shadow/manual only`,
          );
        else failures.push(`${file}: ${action} not pinned to full SHA`);
      }
    }
  }
if (exists("repository/.github/workflows/fadd-delivery-gates.yml")) {
  const text = read("repository/.github/workflows/fadd-delivery-gates.yml");
  for (const token of [
    "pull_request:",
    "push:",
    "merge_group:",
    "FADD / required-gate",
    "CI and harness meta-lint",
    "actions/cache/restore@",
    "tools/security/scan.py",
    "tools/architecture/validate.py",
    "tools/container/install.py",
    "tools/quality/install.py",
  ])
    if (!text.includes(token))
      failures.push(`delivery workflow missing ${token}`);
}
if (exists("repository/.github/workflows/fadd-ai-review.yml")) {
  const text = read("repository/.github/workflows/fadd-ai-review.yml");
  for (const token of [
    "pull_request:",
    "push:",
    "FADD AI / required-gate",
    "openai/codex-action@86365089eb2b84e0a8fb0717b304f8bdcb13b20e",
    "verify-delivery-gate.mjs",
  ])
    if (!text.includes(token)) failures.push(`AI workflow missing ${token}`);
}
if (exists("repository/.github/workflows/fadd-security-db-refresh.yml")) {
  const text = read(
    "repository/.github/workflows/fadd-security-db-refresh.yml",
  );
  if (!text.includes("schedule:") || !text.includes("refresh-databases.sh"))
    failures.push("weekly DB refresh workflow incomplete");
}
const forbidden = [];
const ignoredDirectories = new Set([
  ".git",
  ".cache",
  ".venv",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  "artifacts",
  "dist",
]);
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.name === "__pycache__" || entry.name.endsWith(".pyc")) {
      forbidden.push(path.relative(ROOT, full));
    } else if (entry.isDirectory() && !ignoredDirectories.has(entry.name)) {
      walk(full);
    }
  }
}
walk(ROOT);
if (forbidden.length)
  failures.push(
    `package contains generated Python artifacts: ${forbidden.join(", ")}`,
  );
console.log(
  JSON.stringify(
    {
      check: "validate-package",
      status: failures.length ? "fail" : "pass",
      version,
      skills: actual.length,
      agents: agents.length,
      failures,
      warnings,
    },
    null,
    2,
  ),
);
if (failures.length) process.exit(1);
