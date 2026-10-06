import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
const PATH_KEYS = new Set([
  "path",
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
export const sha256 = (v) =>
  crypto.createHash("sha256").update(String(v)).digest("hex");
export function canonicalJson(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return `[${v.map(canonicalJson).join(",")}]`;
  return `{${Object.keys(v)
    .sort()
    .map((k) => `${JSON.stringify(k)}:${canonicalJson(v[k])}`)
    .join(",")}}`;
}
export function loadPolicy(cwd) {
  return JSON.parse(
    fs.readFileSync(path.join(cwd, "tools/harness/policy.json"), "utf8"),
  );
}
function realRoot(cwd) {
  return fs.realpathSync.native(path.resolve(cwd));
}
function resolveCandidate(root, raw) {
  const abs = path.isAbsolute(raw)
    ? path.resolve(raw)
    : path.resolve(root, raw);
  let cur = abs,
    missing = [];
  while (!fs.existsSync(cur)) {
    const par = path.dirname(cur);
    if (par === cur) break;
    missing.unshift(path.basename(cur));
    cur = par;
  }
  const real = fs.existsSync(cur) ? fs.realpathSync.native(cur) : cur;
  return path.resolve(real, ...missing);
}
function within(base, candidate) {
  const rel = path.relative(path.resolve(base), path.resolve(candidate));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}
function pathsFrom(input) {
  const out = [];
  function visit(v, k = "") {
    if (v == null) return;
    if (typeof v === "string") {
      if (PATH_KEYS.has(k) && v.trim()) out.push(v.trim());
      return;
    }
    if (Array.isArray(v)) {
      v.forEach((x) => visit(x, k));
      return;
    }
    if (typeof v === "object")
      for (const [key, val] of Object.entries(v)) visit(val, key);
  }
  visit(input);
  return [...new Set(out)];
}
function records(root) {
  const d = path.join(root, ".omp/authority");
  if (!fs.existsSync(d)) return [];
  return fs
    .readdirSync(d)
    .filter((x) => x.endsWith(".json"))
    .flatMap((x) => {
      try {
        return [
          {
            ...JSON.parse(fs.readFileSync(path.join(d, x), "utf8")),
            __file: path.join(d, x),
          },
        ];
      } catch {
        return [];
      }
    });
}
function authority(root, type, action, hash, now) {
  const t = new Date(now ?? Date.now()).getTime();
  return records(root).find(
    (r) =>
      r.schemaVersion === "1.0" &&
      r.authorizedByType === "human" &&
      r.operationType === type &&
      r.actionClass === action &&
      (r.operationSha256 === hash || r.commandSha256 === hash) &&
      Date.parse(r.authorizedAt) <= t &&
      Date.parse(r.expiresAt) > t,
  );
}
const allow = (ruleId, reason, extra = {}) => ({
    allow: true,
    ruleId,
    reason,
    ...extra,
  }),
  block = (ruleId, reason, extra = {}) => ({
    allow: false,
    ruleId,
    reason,
    ...extra,
  });
export function evaluateToolCall({ toolName, input = {}, cwd, policy, now }) {
  const root = realRoot(cwd),
    name = String(toolName || "").toLowerCase();
  if (["write", "edit", "delete", "move"].includes(name)) {
    const candidates = pathsFrom(input);
    if (!candidates.length)
      return block(
        "POLICY-PATH-UNRESOLVED",
        "No target path could be identified.",
      );
    const opHash = sha256(canonicalJson({ toolName, input }));
    const auth = [];
    for (const raw of candidates) {
      const c = resolveCandidate(root, raw);
      if (
        policy.workspace?.denyOutside !== false &&
        !within(root, c)
      )
        return block("POLICY-PATH-OUTSIDE", `Path escapes workspace: ${raw}`);
      for (const rel of policy.generatedPaths) {
        if (within(resolveCandidate(root, rel), c))
          return block("POLICY-PATH-GENERATED", `Generator-owned path: ${raw}`);
      }
      for (const rel of policy.protectedPaths) {
        if (!within(resolveCandidate(root, rel), c)) continue;
        const absolute = policy.nonAuthorizableProtectedPaths.some((x) =>
          within(resolveCandidate(root, x), c),
        );
        if (absolute)
          return block(
            "POLICY-PATH-PROTECTED-ABSOLUTE",
            `Non-authorizable control: ${raw}`,
          );
        const action = `protected-write:${rel}`,
          record = authority(root, "tool-call", action, opHash, now);
        if (!record)
          return block(
            "POLICY-PATH-PROTECTED",
            `Protected control requires exact human tool-call authority: ${raw}`,
            { actionClass: action, operationSha256: opHash },
          );
        auth.push(path.relative(root, record.__file));
      }
    }
    return auth.length
      ? allow(
          "POLICY-PATH-PROTECTED-AUTHORIZED",
          "Exact protected write authorized.",
          { authorityRecords: auth },
        )
      : allow("POLICY-PATH-ALLOW", "Workspace write allowed.");
  }
  if (name === "bash") {
    const command = String(input.command || "").trim();
    if (!command) return block("POLICY-COMMAND-MISSING", "Empty command");
    for (const p of policy.destructiveCommandPatterns)
      if (new RegExp(p, "i").test(command))
        return block(
          "POLICY-COMMAND-DESTRUCTIVE",
          "Destructive or authority-forging command.",
        );
    for (const p of policy.externalWriteCommandPatterns)
      if (new RegExp(p, "i").test(command)) {
        const hash = sha256(command),
          action = /^git\s+push/i.test(command)
            ? "external-write:git-push"
            : "external-write";
        const record = authority(root, "command", action, hash, now);
        return record
          ? allow(
              "POLICY-EXTERNAL-AUTHORIZED",
              "Exact external command authorized.",
            )
          : block(
              "POLICY-EXTERNAL-AUTHORITY",
              "External action requires exact human authority.",
              { actionClass: action, commandSha256: hash },
            );
      }
    return allow(
      "POLICY-COMMAND-DEFER",
      "Profile approval and sandbox remain authoritative.",
    );
  }
  if (name.startsWith("mcp") || name.includes("mcp__")) {
    if (
      policy.allowedMcpReadTools.includes("*") ||
      policy.allowedMcpReadTools.includes(toolName)
    ) {
      return allow("POLICY-MCP-READ-ALLOW", "MCP tool allowed by policy.");
    }
    const hash = sha256(canonicalJson({ toolName, input })),
      action = `mcp:${toolName}`,
      record = authority(root, "tool-call", action, hash, now);
    return record
      ? allow("POLICY-MCP-AUTHORIZED", "Exact MCP call authorized.")
      : block(
          "POLICY-MCP-DEFAULT-DENY",
          "Unknown/action-capable MCP call requires classification and authority.",
          { actionClass: action, operationSha256: hash },
        );
  }
  return allow("POLICY-TOOL-DEFER", "Outside deterministic policy scope.");
}
export function redactText(text, policy) {
  let out = String(text);
  for (const r of policy.redactionPatterns)
    out = out.replace(new RegExp(r.pattern, "gi"), r.replacement);
  return out;
}
export function redactBlocks(v, p) {
  if (typeof v === "string") return redactText(v, p);
  if (Array.isArray(v)) return v.map((x) => redactBlocks(x, p));
  if (v && typeof v === "object")
    return Object.fromEntries(
      Object.entries(v).map(([k, x]) => [k, redactBlocks(x, p)]),
    );
  return v;
}
