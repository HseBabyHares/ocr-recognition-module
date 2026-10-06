#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
function parse(argv) {
  const o = {
    repo: ".",
    out: "artifacts/gc",
    policy: "tools/gc/policy.json",
    failOn: "new",
  };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--help" || k === "-h") return { help: true };
    const v = argv[++i];
    if (!v) throw new Error(`${k} requires value`);
    if (k === "--repo") o.repo = v;
    else if (k === "--out") o.out = v;
    else if (k === "--policy") o.policy = v;
    else if (k === "--fail-on") o.failOn = v;
    else throw new Error(`unknown ${k}`);
  }
  return o;
}
function sha(s) {
  return crypto.createHash("sha256").update(s).digest("hex").slice(0, 24);
}
function globRe(g) {
  let s = "^";
  for (let i = 0; i < g.length; i++) {
    if (g[i] == "*" && g[i + 1] == "*") {
      s += ".*";
      i++;
    } else if (g[i] == "*") s += "[^/]*";
    else {
      s += g[i].replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
    }
  }
  return new RegExp(s + "$");
}
function excluded(rel, p) {
  return p.exclude.some((g) => globRe(g).test(rel));
}
function finding(rule, rel, line, evidence, severity = "medium") {
  return {
    fingerprint: `${rule}:${sha(`${rule}|${rel}|${evidence.replace(/\d+/g, "#")}`)}`,
    rule,
    path: rel,
    line,
    severity,
    evidence,
  };
}
const a = parse(process.argv.slice(2));
if (a.help) {
  console.log("Usage: run.mjs --repo DIR --out DIR [--fail-on none|new|any]");
  process.exit(0);
}
const repo = path.resolve(a.repo),
  out = path.resolve(a.out),
  policy = JSON.parse(fs.readFileSync(path.resolve(a.policy), "utf8"));
fs.mkdirSync(out, { recursive: true });
const findings = [];
function walk(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    const rel = path.relative(repo, abs).replaceAll("\\", "/");
    if (
      excluded(rel, policy) ||
      (ent.isDirectory() && excluded(`${rel}/`, policy))
    )
      continue;
    if (ent.isDirectory()) {
      walk(abs);
      continue;
    }
    if (!ent.isFile()) continue;
    let buffer;
    try {
      if (fs.statSync(abs).size > (policy.maxFileBytes || 2 * 1024 * 1024)) {
        continue;
      }
      buffer = fs.readFileSync(abs);
    } catch {
      continue;
    }
    if (buffer.includes(0)) continue;
    const text = buffer.toString("utf8");
    const lines = text.split(/\r?\n/);
    if (lines.length > policy.maxFileLines) {
      findings.push(
        finding(
          "large-file",
          rel,
          1,
          `${lines.length} lines > ${policy.maxFileLines}`,
        ),
      );
    }
    let todos = 0;
    lines.forEach((line) => {
      if (/\b(?:TODO|FIXME|HACK|XXX)\b/.test(line)) todos++;
    });
    if (todos > policy.maxTodoPerFile) {
      findings.push(
        finding(
          "todo-density",
          rel,
          1,
          `${todos} markers > ${policy.maxTodoPerFile}`,
        ),
      );
    }
  }
}
walk(repo);
function optional(name, args) {
  const r = spawnSync(args[0], args.slice(1), {
    cwd: repo,
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
    name,
    status: r.error ? "blocked" : r.status === 0 ? "pass" : "finding",
    exitCode: r.status ?? 127,
    stdout: (r.stdout || "").slice(-4000),
    stderr: (r.stderr || r.error?.message || "").slice(-4000),
  };
}
const sensors = [];
if (fs.existsSync(path.join(repo, "architecture/policy.json")))
  sensors.push(
    optional("architecture", [
      "python3",
      path.join(
        path.dirname(new URL(import.meta.url).pathname),
        "../architecture/validate.py",
      ),
      "--repo",
      repo,
      "--mode",
      "strict",
    ]),
  );
const pythonFiles = [...walkPython(repo)];
let pythonDuplication = null;
const toolRoot = path.resolve(
  path.dirname(new URL(import.meta.url).pathname),
  "../..",
);
const qualityPolicyPath = fs.existsSync(
  path.join(repo, "quality/python-policy.json"),
)
  ? path.join(repo, "quality/python-policy.json")
  : path.join(toolRoot, "quality/python-policy.json");
const qualityPolicy = JSON.parse(
  fs.readFileSync(qualityPolicyPath, "utf8"),
);
const matchesPath = (file, prefix) =>
  file === prefix || file.startsWith(`${prefix}/`);
const relativePythonFiles = pythonFiles.map((file) => ({
  abs: file,
  rel: path.relative(repo, file).replaceAll("\\", "/"),
}));
const productionFiles = relativePythonFiles
  .filter(({ rel }) =>
    (qualityPolicy.pythonPaths || []).some((prefix) =>
      matchesPath(rel, prefix),
    ),
  )
  .map(({ abs }) => abs);
const testFiles = relativePythonFiles
  .filter(({ rel }) =>
    (qualityPolicy.testPaths || []).some((prefix) =>
      matchesPath(rel, prefix),
    ),
  )
  .map(({ abs }) => abs);
if (pythonFiles.length) {
  const detector = spawnSync(
    "python3",
    [
      path.join(
        path.dirname(new URL(import.meta.url).pathname),
        "python-clones.py",
      ),
      "--repo",
      repo,
      "--production-files",
      ...productionFiles,
      "--test-files",
      ...testFiles,
    ],
    { cwd: repo, encoding: "utf8", maxBuffer: 8 * 1024 * 1024 },
  );
  if (detector.status !== 0) {
    throw new Error(
      `python clone detector failed: ${detector.stderr || detector.stdout}`,
    );
  }
  const detectorReport = JSON.parse(detector.stdout || "{}");
  pythonDuplication = detectorReport.metrics;
  findings.push(...(detectorReport.findings || []));
}
if (pythonFiles.length) {
  sensors.push(
    optional("python-complexity", [
      "python3",
      path.join(
        path.dirname(new URL(import.meta.url).pathname),
        "../quality/complexity.py",
      ),
      "--policy",
      qualityPolicyPath,
      ...pythonFiles,
    ]),
  );
}
function* walkPython(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    const rel = path.relative(repo, abs).replaceAll("\\", "/");
    if (
      excluded(rel, policy) ||
      (ent.isDirectory() && excluded(`${rel}/`, policy))
    )
      continue;
    if (ent.isDirectory()) {
      yield* walkPython(abs);
    } else if (ent.isFile() && ent.name.endsWith(".py")) {
      yield abs;
    }
  }
}
const baselinePath = path.join(repo, "quality/baseline.json");
const accepted = new Set(
  fs.existsSync(baselinePath)
    ? JSON.parse(fs.readFileSync(baselinePath, "utf8")).accepted.map((x) =>
        typeof x === "string" ? x : x.fingerprint,
      )
    : [],
);
const normalized = [
  ...new Map(findings.map((f) => [f.fingerprint, f])).values(),
];
const fresh = normalized.filter((f) => !accepted.has(f.fingerprint));
const report = {
  schemaVersion: "1.0",
  generatedAt: new Date().toISOString(),
  status: fresh.length ? "findings" : "pass",
  counts: {
    all: normalized.length,
    new: fresh.length,
    accepted: normalized.length - fresh.length,
    ...(pythonDuplication
      ? {
          pythonProductionDuplicatedLines:
            pythonDuplication.production.duplicatedLoc,
          pythonProductionTotalLines: pythonDuplication.production.pythonLoc,
          pythonTestDuplicatedLines: pythonDuplication.tests.duplicatedLoc,
          pythonTestTotalLines: pythonDuplication.tests.pythonLoc,
          pythonRepositoryDuplicatedLines:
            pythonDuplication.repository.duplicatedLoc,
          pythonRepositoryTotalLines: pythonDuplication.repository.pythonLoc,
        }
      : {}),
  },
  findings: normalized,
  newFindings: fresh,
  sensors,
  ...(pythonDuplication ? { pythonDuplication } : {}),
};
fs.writeFileSync(
  path.join(out, "inventory.json"),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report, null, 2));
if (a.failOn === "any" && normalized.length) process.exit(1);
if (a.failOn === "new" && fresh.length) process.exit(1);
