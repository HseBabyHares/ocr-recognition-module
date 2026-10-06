#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import {
  fingerprint,
  parseContent,
  readJson,
  validateReview,
  RANK,
} from "./lib/review.mjs";

function getArgumentValue(name, defaultValue) {
  const argumentIndex = process.argv.indexOf(`--${name}`);
  return argumentIndex >= 0 ? process.argv[argumentIndex + 1] : defaultValue;
}

function requireInputFiles(contextFile, diffFile, promptFile, schemaFile) {
  if (contextFile && diffFile && promptFile && schemaFile) return;

  console.error(
    "Usage: openrouter-vote.mjs --context FILE --diff FILE --prompt FILE --schema FILE --out DIR --models a,b [--dry-run]",
  );
  process.exit(2);
}

function requireReviewableContext(context) {
  if (context.complete && context.externalReviewAllowed) return;

  console.error("context blocked");
  process.exit(2);
}

function getRequestedModels() {
  return String(
    getArgumentValue("models", process.env.OPENROUTER_REVIEW_MODELS || ""),
  )
    .split(",")
    .map((model) => model.trim())
    .filter(Boolean);
}

function requireExplicitModels(models) {
  const hasInvalidModel = models.some(
    (model) => !model.includes("/") || /(?:\/auto|\/latest)$/i.test(model),
  );

  if (
    models.length >= 2 &&
    new Set(models).size === models.length &&
    !hasInvalidModel
  ) {
    return;
  }

  console.error("two distinct explicit model slugs required");
  process.exit(2);
}

function requireDataApproval(isDryRun) {
  if (process.env.OPENROUTER_REVIEW_DATA_APPROVED === "true" || isDryRun) {
    return;
  }

  console.error("OPENROUTER_REVIEW_DATA_APPROVED=true required");
  process.exit(2);
}

function writeDryRun(outputDirectory, models, userContent) {
  fs.writeFileSync(
    path.join(outputDirectory, "dry-run.json"),
    JSON.stringify(
      {
        status: "dry-run",
        models,
        bytes: Buffer.byteLength(userContent),
        provider: {
          data_collection: "deny",
          zdr: true,
          allow_fallbacks: false,
        },
      },
      null,
      2,
    ),
  );
}

function requireApiKey() {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (apiKey) return apiKey;

  console.error("OPENROUTER_API_KEY missing");
  process.exit(2);
}

async function requestReview(model, apiKey, schema, prompt, userContent) {
  const response = await fetch(
    "https://openrouter.ai/api/v1/chat/completions",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      signal: AbortSignal.timeout(
        Number(process.env.OPENROUTER_TIMEOUT_MS || 180000),
      ),
      body: JSON.stringify({
        model,
        temperature: 0,
        max_tokens: 5000,
        provider: {
          data_collection: "deny",
          zdr: true,
          allow_fallbacks: false,
          require_parameters: true,
        },
        response_format: {
          type: "json_schema",
          json_schema: { name: "fadd_review", strict: true, schema },
        },
        messages: [
          { role: "system", content: prompt },
          { role: "user", content: userContent },
        ],
      }),
    },
  );

  const rawResponse = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${rawResponse.slice(0, 300)}`);
  }

  const responsePayload = JSON.parse(rawResponse);
  const parsedReview = parseContent(
    responsePayload.choices?.[0]?.message?.content,
  );
  const validation = validateReview(parsedReview, model);
  if (validation.errors.length) {
    throw new Error(validation.errors.join(","));
  }

  return validation.value;
}

function writeModelReview(outputDirectory, model, review) {
  const modelFileName = model.replace(/[^A-Za-z0-9._-]/g, "_") + ".json";
  fs.writeFileSync(
    path.join(outputDirectory, modelFileName),
    JSON.stringify(review, null, 2) + "\n",
  );
}

function aggregateFindings(reviews) {
  const findingGroups = new Map();

  for (const review of reviews) {
    for (const finding of review.findings) {
      const findingFingerprint = fingerprint(finding);
      const group = findingGroups.get(findingFingerprint) || {
        ...finding,
        support: 0,
        reviewers: [],
      };
      group.support++;
      group.reviewers.push(review.reviewer);
      findingGroups.set(findingFingerprint, group);
    }
  }

  return [...findingGroups.values()].sort(
    (firstFinding, secondFinding) =>
      RANK[secondFinding.severity] - RANK[firstFinding.severity] ||
      secondFinding.support - firstFinding.support,
  );
}

function getResultStatus(successfulReviewCount, requestedModelCount) {
  return successfulReviewCount === requestedModelCount
    ? "complete"
    : successfulReviewCount
      ? "partial"
      : "blocked";
}

const isDryRun = process.argv.includes("--dry-run");
const contextFile = getArgumentValue("context");
const diffFile = getArgumentValue("diff");
const promptFile = getArgumentValue("prompt");
const schemaFile = getArgumentValue("schema");
const outputDirectory = getArgumentValue(
  "out",
  "artifacts/ai-gates/openrouter",
);

requireInputFiles(contextFile, diffFile, promptFile, schemaFile);

const context = readJson(contextFile);
requireReviewableContext(context);

const models = getRequestedModels();
requireExplicitModels(models);
requireDataApproval(isDryRun);

fs.mkdirSync(outputDirectory, { recursive: true });

const schema = readJson(schemaFile);
const prompt = fs.readFileSync(promptFile, "utf8");
const diff = fs.readFileSync(diffFile, "utf8");
const userContent = JSON.stringify({ context, candidateDiff: diff });

if (isDryRun) {
  writeDryRun(outputDirectory, models, userContent);
  process.exit(0);
}

const apiKey = requireApiKey();
const reviews = [];
const errors = [];

for (const model of models) {
  try {
    const review = await requestReview(
      model,
      apiKey,
      schema,
      prompt,
      userContent,
    );
    reviews.push(review);
    writeModelReview(outputDirectory, model, review);
  } catch (error) {
    errors.push({ model, error: String(error.message || error) });
  }
}

const findings = aggregateFindings(reviews);
const result = {
  schemaVersion: "1.0",
  status: getResultStatus(reviews.length, models.length),
  requestedModels: models,
  successfulModels: reviews.map((review) => review.reviewer),
  findings,
  errors,
};

fs.writeFileSync(
  path.join(outputDirectory, "aggregate.json"),
  JSON.stringify(result, null, 2) + "\n",
);
console.log(JSON.stringify(result, null, 2));
if (result.status !== "complete") process.exit(1);
