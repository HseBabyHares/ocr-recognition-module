#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

function getArgument(name, defaultValue) {
  const argumentIndex = process.argv.indexOf(`--${name}`);
  return argumentIndex >= 0 ? process.argv[argumentIndex + 1] : defaultValue;
}

function runGit(repositoryPath, arguments_) {
  const result = spawnSync("git", ["-C", repositoryPath, ...arguments_], {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.status !== 0) throw new Error(result.stderr);
  return result.stdout;
}

function redactSecrets(diff) {
  let redactionCount = 0;
  let redactedDiff = diff;
  const secretPatterns = [
    /-----BEGIN[^\n]+PRIVATE KEY-----[\s\S]*?-----END[^\n]+PRIVATE KEY-----/g,
    /\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b/g,
    /\bsk-[A-Za-z0-9_-]{16,}\b/g,
  ];

  for (const secretPattern of secretPatterns) {
    redactedDiff = redactedDiff.replace(secretPattern, (secret) => {
      redactionCount++;
      const digest = crypto
        .createHash("sha256")
        .update(secret)
        .digest("hex")
        .slice(0, 12);
      return `[REDACTED:${digest}]`;
    });
  }

  return { redactedDiff, redactionCount };
}

function readSpecIndex(repositoryPath) {
  let specIndex = { status: "missing", entries: [] };
  const specIndexFile = path.join(repositoryPath, "docs/spec-index.json");
  if (fs.existsSync(specIndexFile)) {
    specIndex = JSON.parse(fs.readFileSync(specIndexFile, "utf8"));
  }
  return specIndex;
}

function readSpecReferences(repositoryPath, entries) {
  const references = [];
  for (const entry of entries || []) {
    const specPaths = [entry.spec, ...(entry.additionalSpecs || [])].filter(
      Boolean,
    );

    for (const specPath of specPaths) {
      const absoluteSpecPath = path.join(repositoryPath, specPath);
      if (fs.existsSync(absoluteSpecPath)) {
        references.push({
          path: specPath,
          content: fs.readFileSync(absoluteSpecPath, "utf8").slice(0, 50000),
        });
      }
    }
  }
  return references;
}

function globToRegExp(pattern) {
  return new RegExp(
    "^" +
      pattern
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*\*/g, ".*")
        .replace(/\*/g, "[^/]*") +
      "$",
  );
}

const repositoryPath = path.resolve(getArgument("repo", "."));
const base = getArgument("base", process.env.FADD_BASE_SHA || "HEAD^");
const head = getArgument("head", "HEAD");
const outputDirectory = path.resolve(
  getArgument("out", "artifacts/ai-gates/context"),
);
const maximumDiffBytes = Number(getArgument("max-bytes", "240000"));

fs.mkdirSync(outputDirectory, { recursive: true });

const changedPaths = runGit(repositoryPath, [
  "diff",
  "--name-only",
  `${base}...${head}`,
])
  .split(/\r?\n/)
  .filter(Boolean);

let candidateDiff = runGit(repositoryPath, [
  "diff",
  "--no-ext-diff",
  "--unified=50",
  "--no-color",
  `${base}...${head}`,
]);

const sensitivePaths = changedPaths.filter((changedPath) =>
  /(^|\/)(\.env|secrets?|credentials?)(\/|\.|$)|\.(pem|key|p12|pfx)$/i.test(
    changedPath,
  ),
);

const redactionResult = redactSecrets(candidateDiff);
candidateDiff = redactionResult.redactedDiff;
const redactions = redactionResult.redactionCount;

const truncated = Buffer.byteLength(candidateDiff) > maximumDiffBytes;
candidateDiff = Buffer.from(candidateDiff)
  .subarray(0, maximumDiffBytes)
  .toString();
fs.writeFileSync(path.join(outputDirectory, "candidate.diff"), candidateDiff);

const specIndex = readSpecIndex(repositoryPath);
const references = readSpecReferences(repositoryPath, specIndex.entries);
const watchedImplementationRoots = specIndex.watchedImplementationRoots || [];
const implementationChanged = changedPaths.some((changedPath) =>
  watchedImplementationRoots.some((rootPattern) =>
    globToRegExp(rootPattern).test(changedPath),
  ),
);
const mappingBlocked = implementationChanged && specIndex.status !== "active";
const complete =
  !truncated && !sensitivePaths.length && !redactions && !mappingBlocked;

const context = {
  schemaVersion: "1.0",
  base,
  head,
  changedPaths,
  diffBytes: Buffer.byteLength(candidateDiff),
  truncated,
  sensitivePaths,
  redactions,
  specIndexStatus: specIndex.status || "unknown",
  implementationChanged,
  mappingBlocked,
  references,
  complete,
  externalReviewAllowed: complete,
};

fs.writeFileSync(
  path.join(outputDirectory, "review-context.json"),
  JSON.stringify(context, null, 2) + "\n",
);
fs.copyFileSync(
  path.resolve("tools/ai-gates/review-prompt.md"),
  path.join(outputDirectory, "review-prompt.md"),
);
fs.copyFileSync(
  path.resolve("schemas/spec-drift-review.schema.json"),
  path.join(outputDirectory, "spec-drift-review.schema.json"),
);
console.log(
  JSON.stringify(
    { status: complete ? "ready" : "blocked", ...context },
    null,
    2,
  ),
);
if (process.env.GITHUB_OUTPUT) {
  fs.appendFileSync(
    process.env.GITHUB_OUTPUT,
    `complete=${complete}\nexternal_review_allowed=${complete}\n`,
  );
}
