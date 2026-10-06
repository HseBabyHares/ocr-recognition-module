#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const pyprojectPath = path.join(repositoryRoot, "pyproject.toml");
const packageMode =
  fs.existsSync(pyprojectPath) &&
  fs.existsSync(path.join(repositoryRoot, "src/omp_fadd/cli.py")) &&
  /^\s*name\s*=\s*["']omp-fadd["']\s*$/m.test(
    fs.readFileSync(pyprojectPath, "utf8"),
  );

const artifactRoot = process.env.FADD_ARTIFACT_ROOT
  ? path.resolve(process.env.FADD_ARTIFACT_ROOT)
  : path.join(repositoryRoot, "artifacts");
const logDirectory = path.join(artifactRoot, "logs");
fs.mkdirSync(logDirectory, { recursive: true });
const isolatedRunner = path.join(
  repositoryRoot,
  "tools/harness/checks/run-isolated.py",
);

const packageCommands = [
  [process.execPath, ["tools/harness/checks/validate-package.mjs"]],
  [process.execPath, ["tools/harness/checks/test-policy.mjs"]],
  [process.execPath, ["tools/harness/checks/test-hook-contract.mjs"]],
  ["python3", ["tools/harness/checks/test-syntax.py"]],
  ["uv", ["run", "--isolated", "--group", "dev", "pytest", "tests"]],
  ["python3", ["tools/security/tests/self_test.py"]],
  ["python3", ["tools/quality/tests/self_test.py"]],
  ["python3", ["tools/container/tests/self_test.py"]],
  ["python3", ["tools/meta/tests/self_test.py"]],
  ["python3", ["tools/harness/checks/test-architecture-template.py"]],
  [process.execPath, ["tools/gc/test.mjs"]],
  [process.execPath, ["tools/ai-gates/test.mjs"]],
  [process.execPath, ["tools/harness/checks/test-openspec.mjs"]],
];

const repositoryCommands = [
  [
    process.execPath,
    ["--check", ".omp/hooks/pre/fadd-policy-guard.js"],
  ],
  ["python3", ["tools/security/preflight.py"]],
  [
    process.execPath,
    ["--check", ".omp/hooks/pre/fadd-completion-guard.js"],
  ],
  [process.execPath, ["--check", ".claude/hooks/fadd-completion-check.mjs"]],
  [
    "python3",
    [
      "tools/quality/run.py",
      "--repo",
      ".",
      "--out",
      path.join(artifactRoot, "quality"),
      "--advisory",
    ],
  ],
  [
    "python3",
    [
      "tools/container/check.py",
      "--repo",
      ".",
      "--out",
      path.join(artifactRoot, "container"),
      "--advisory",
    ],
  ],
  [
    "python3",
    [
      "tools/architecture/validate.py",
      "--repo",
      ".",
      "--mode",
      "advisory",
      "--out",
      path.join(artifactRoot, "architecture/report.json"),
    ],
  ],
  [
    process.execPath,
    [
      "tools/gc/run.mjs",
      "--repo",
      ".",
      "--out",
      path.join(artifactRoot, "gc"),
      "--fail-on",
      "none",
    ],
  ],
  [
    process.execPath,
    [
      "tools/harness/checks/run-openspec.mjs",
      "--repo",
      ".",
      "--out",
      path.join(artifactRoot, "openspec/result.json"),
    ],
  ],
];

const commands = packageMode ? packageCommands : repositoryCommands;
const commandResults = [];
let failed = false;
let combinedOutput = "";
const runEnvironment = {
  ...process.env,
  PYTHONDONTWRITEBYTECODE: "1",
};
for (const [command, args] of commands) {
  const startedAt = Date.now();
  const execution = spawnSync(
    "python3",
    [isolatedRunner, "300", "--", command, ...args],
    {
      cwd: repositoryRoot,
      encoding: "utf8",
      env: runEnvironment,
      timeout: 310000,
      maxBuffer: 32 * 1024 * 1024,
    },
  );
  const commandResult = {
    command: [command, ...args].join(" "),
    status: execution.status ?? 1,
    durationMs: Date.now() - startedAt,
  };

  commandResults.push(commandResult);

  const outputSection =
    `\n$ ${commandResult.command}\n` +
    `${execution.stdout || ""}${execution.stderr || ""}`;
  combinedOutput += outputSection;
  process.stdout.write(outputSection);

  if (commandResult.status !== 0) {
    failed = true;
    break;
  }
}

const report = {
  check: "run-all",
  mode: packageMode ? "package" : "repository",
  status: failed ? "fail" : "pass",
  commands: commandResults,
};

combinedOutput += `\n${JSON.stringify(report, null, 2)}\n`;
fs.writeFileSync(
  path.join(logDirectory, "deterministic-run.log"),
  combinedOutput,
);
console.log(JSON.stringify(report, null, 2));
process.exit(failed ? 1 : 0);
