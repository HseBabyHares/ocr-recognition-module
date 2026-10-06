#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const [inventoryFile, historyFile, outDir, policyFile] = process.argv.slice(2);
if (!inventoryFile || !historyFile || !outDir) {
  console.error("Usage: promote.mjs INVENTORY HISTORY OUT [POLICY]");
  process.exit(2);
}

const inventory = JSON.parse(fs.readFileSync(inventoryFile, "utf8"));
const history = fs.existsSync(historyFile)
  ? JSON.parse(fs.readFileSync(historyFile, "utf8"))
  : { schemaVersion: "1.0", findings: {} };
const policy = policyFile
  ? JSON.parse(fs.readFileSync(policyFile, "utf8"))
  : {};
const threshold = policy.recurrenceThreshold ?? 3;
if (!Number.isInteger(threshold) || threshold < 1) {
  throw new Error("recurrenceThreshold must be a positive integer");
}

const proposals = [];
for (const finding of inventory.findings) {
  const item = history.findings[finding.fingerprint] || {
    count: 0,
    firstSeen: new Date().toISOString(),
  };
  item.count++;
  item.lastSeen = new Date().toISOString();
  item.rule = finding.rule;
  item.example = {
    path: finding.path,
    line: finding.line,
    evidence: finding.evidence,
  };
  history.findings[finding.fingerprint] = item;
  if (item.count >= threshold) {
    proposals.push({
      fingerprint: finding.fingerprint,
      occurrences: item.count,
      rule: finding.rule,
      proposal:
        "Create a reviewed deterministic harness improvement or explain why the pattern cannot be encoded.",
      required: [
        "regression fixture",
        "false-positive analysis",
        "owner",
        "retirement condition",
      ],
    });
  }
}

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(
  path.join(outDir, "proposed-history.json"),
  `${JSON.stringify(history, null, 2)}\n`,
);
fs.writeFileSync(
  path.join(outDir, "harness-improvement-proposals.json"),
  `${JSON.stringify({ schemaVersion: "1.0", proposals }, null, 2)}\n`,
);
console.log(JSON.stringify({ status: "pass", proposals: proposals.length }));
