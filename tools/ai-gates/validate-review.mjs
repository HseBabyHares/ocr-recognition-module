#!/usr/bin/env node
import fs from "node:fs";
import { validateReview } from "./lib/review.mjs";

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile) {
  console.error("Usage: validate-review.mjs INPUT [OUTPUT]");
  process.exit(2);
}

const reviewInput = JSON.parse(fs.readFileSync(inputFile, "utf8"));
const validationResult = validateReview(reviewInput);

if (validationResult.errors.length) {
  console.error(validationResult.errors.join("\n"));
  process.exit(1);
}

const serializedReview = `${JSON.stringify(validationResult.value, null, 2)}\n`;

if (outputFile) {
  fs.writeFileSync(outputFile, serializedReview);
}

console.log(serializedReview);
