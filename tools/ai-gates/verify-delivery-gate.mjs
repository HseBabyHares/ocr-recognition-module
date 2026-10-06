#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

import { RANK, validateReview } from "./lib/review.mjs";

const VALID_MODES = ["off", "shadow", "strict"];

function getArgument(name, defaultValue) {
  const argumentIndex = process.argv.indexOf(`--${name}`);
  return argumentIndex >= 0 ? process.argv[argumentIndex + 1] : defaultValue;
}

function readReview(filePath, reviewer, warnings) {
  if (!filePath || !fs.existsSync(filePath)) {
    return null;
  }

  try {
    const rawReview = JSON.parse(fs.readFileSync(filePath, "utf8"));
    const validationResult = validateReview(rawReview, reviewer);

    if (validationResult.errors.length) {
      warnings.push(
        `${reviewer} invalid: ${validationResult.errors.join(",")}`,
      );
      return null;
    }

    return validationResult.value;
  } catch (error) {
    warnings.push(`${reviewer} invalid: ${error.message}`);
    return null;
  }
}

function readOpenRouterVote(filePath, warnings) {
  if (!filePath || !fs.existsSync(filePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    warnings.push(`openrouter invalid: ${error.message}`);
    return null;
  }
}

function addStrictModeBlockers(blockers, codexReview, openRouterVote) {
  if (!codexReview || codexReview.verdict !== "pass") {
    blockers.push("codex review unavailable or non-pass");
  }

  if (
    !openRouterVote ||
    openRouterVote.status !== "complete" ||
    (openRouterVote.successfulModels?.length || 0) < 2
  ) {
    blockers.push("openrouter quorum unavailable");
  }

  for (const finding of openRouterVote?.findings || []) {
    const isBlockingFinding =
      finding.blockingCandidate &&
      RANK[finding.severity] >= RANK.high &&
      finding.confidence >= 0.8 &&
      finding.support >= 2;

    if (isBlockingFinding) {
      blockers.push(`AI:${finding.fingerprint}`);
    }
  }
}

function addShadowModeWarnings(warnings, codexReview, openRouterVote) {
  if (codexReview && codexReview.verdict !== "pass") {
    warnings.push(`codex:${codexReview.verdict}`);
  }

  if (openRouterVote && openRouterVote.findings?.length) {
    warnings.push(`openrouter findings:${openRouterVote.findings.length}`);
  }
}

function parseUpstreamStatuses() {
  try {
    return JSON.parse(getArgument("upstream", "{}"));
  } catch (error) {
    console.error(`invalid upstream JSON: ${error.message}`);
    process.exit(2);
  }
}

function collectUpstreamBlockers(upstreamStatuses) {
  return Object.entries(upstreamStatuses)
    .filter(([, status]) => status !== "success")
    .map(([name, status]) => `${name}:${status}`);
}

function determineReportStatus(blockers, warnings) {
  if (blockers.length) {
    return "fail";
  }

  return warnings.length ? "pass-with-warnings" : "pass";
}

function writeReport(outputFile, report) {
  fs.mkdirSync(path.dirname(path.resolve(outputFile)), { recursive: true });
  fs.writeFileSync(outputFile, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
}

function runDeliveryGate() {
  const mode = getArgument("mode", process.env.FADD_AI_GATE_MODE || "shadow");
  const outputFile = getArgument("out", "artifacts/delivery-gate/report.json");

  if (!VALID_MODES.includes(mode)) {
    console.error(`invalid mode ${mode}`);
    process.exit(2);
  }

  const upstream = parseUpstreamStatuses();
  const blockers = collectUpstreamBlockers(upstream);
  const warnings = [];

  const codexReview = readReview(getArgument("codex"), "codex", warnings);
  const openRouterVote = readOpenRouterVote(
    getArgument("openrouter"),
    warnings,
  );

  if (mode === "strict") {
    addStrictModeBlockers(blockers, codexReview, openRouterVote);
  } else if (mode === "shadow") {
    addShadowModeWarnings(warnings, codexReview, openRouterVote);
  }

  const report = {
    schemaVersion: "1.0",
    mode,
    status: determineReportStatus(blockers, warnings),
    upstream,
    blockers,
    warnings,
  };

  writeReport(outputFile, report);
  process.exit(blockers.length ? 1 : 0);
}

runDeliveryGate();
