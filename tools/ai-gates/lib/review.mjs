import crypto from "node:crypto";
import fs from "node:fs";

export const RANK = { low: 1, medium: 2, high: 3, critical: 4 };

const FINDING_FIELDS = [
  "severity",
  "category",
  "criterion",
  "path",
  "condition",
  "impact",
  "evidence",
  "confidence",
  "blockingCandidate",
];

export function canonical(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(canonical).join(",")}]`;
  }

  const properties = Object.keys(value)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`);
  return `{${properties.join(",")}}`;
}

export function fingerprint(finding) {
  if (finding.fingerprint) return finding.fingerprint;

  const identity = [
    finding.category,
    finding.criterion,
    finding.path,
    finding.condition,
  ]
    .join("|")
    .toLowerCase();
  const digest = crypto
    .createHash("sha256")
    .update(identity)
    .digest("hex")
    .slice(0, 24);
  return `review:${digest}`;
}

function validateFinding(finding, index, errors) {
  for (const field of FINDING_FIELDS) {
    if (finding[field] === undefined) errors.push(`finding${index}.${field}`);
  }
  if (!RANK[finding.severity]) errors.push(`finding${index}.severity`);
  if (
    typeof finding.confidence !== "number" ||
    finding.confidence < 0 ||
    finding.confidence > 1
  ) {
    errors.push(`finding${index}.confidence`);
  }

  return { ...finding, fingerprint: fingerprint(finding) };
}

export function validateReview(review, reviewer) {
  const errors = [];
  if (!review || typeof review !== "object" || Array.isArray(review)) {
    return { errors: ["object required"] };
  }

  if (review.schemaVersion !== "1.0") errors.push("schemaVersion");
  if (!["pass", "fail", "inconclusive", "blocked"].includes(review.verdict)) {
    errors.push("verdict");
  }
  if (
    typeof review.confidence !== "number" ||
    review.confidence < 0 ||
    review.confidence > 1
  ) {
    errors.push("confidence");
  }
  for (const field of ["summary"]) {
    if (typeof review[field] !== "string" || !review[field].trim()) {
      errors.push(field);
    }
  }
  for (const field of ["findings", "coverage", "blindSpots"]) {
    if (!Array.isArray(review[field])) errors.push(field);
  }

  const findings = [];
  for (const [index, finding] of (review.findings || []).entries()) {
    findings.push(validateFinding(finding, index, errors));
  }

  if (errors.length) return { errors };
  return {
    value: { ...review, reviewer: reviewer || review.reviewer, findings },
    errors: [],
  };
}

export function parseContent(content) {
  if (typeof content === "string") {
    return JSON.parse(content.replace(/^```json\s*|\s*```$/g, ""));
  }
  if (Array.isArray(content)) {
    const combinedContent = content
      .map((part) => (typeof part === "string" ? part : part?.text || ""))
      .join("");
    return parseContent(combinedContent);
  }
  throw new Error("unsupported content");
}

export function readJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}
