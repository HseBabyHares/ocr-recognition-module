# Repository map

This repository contains the installable OMP 18.0.x FADD profile,
deterministic policy, delivery gates, security scanners, Python and container
quality controls, architecture and STRIDE evidence, AI review adapters, and
smart garbage collection.

## Start here

- `README.md` describes installation, operating modes, and safety boundaries.
- `APPEND_SYSTEM.md` contains additive invariants. Keep root `SYSTEM.md` absent.
- `pyproject.toml` exposes the `omp-fadd` command through `uv` and `uvx`.

## Runtime surfaces

- `skills/*/SKILL.md` contains methods loaded on demand; only methodology-level skills use the `fadd-` prefix.
- `agents/fadd-*.md` contains optional focused subagents.
- `repository/.omp/hooks/pre/fadd-policy-guard.js` is the fail-closed OMP hook.
- `repository/.omp/hooks/pre/fadd-completion-guard.js` checks OpenSpec completion.
- `repository/.claude/hooks/fadd-completion-check.mjs` is the Claude Code adapter.
- `config.overlay.yml` contains additive settings.


## Agent roles

Astra coordinates the work. Astra separates target architecture, current
implementation, and migration work. Astra selects the smallest useful route,
assigns bounded slices, and gives the final completion verdict.

Luna performs repository research and may edit any relevant files when assigned.
Luna reads large and related files, relevant architecture evidence, and relevant
git history. Luna returns concise plain-text findings in Simplified Technical
English and does not make architecture decisions unless the task assigns one.

Sol implements one approved bounded slice. Sol may edit assigned files and run
local checks. Sol updates direct callers and current-state documentation when
the slice requires it. Sol does not expand scope or invent architecture.

Use common technical terms. Treat user-supplied architecture as target evidence
until repository evidence proves that it is current. Use the architecture
freshness gate as a staleness tripwire. Perform semantic code-to-documentation
reconciliation before claiming that current-state documentation is synchronized.
## Delivery controls

- `repository/.github/workflows/` contains CI and scheduled gates.
- `tools/security/` contains scanner installation, preflight, and scan logic.
- `tools/quality/` contains Python quality and ratchet controls.
- `tools/container/` contains image, SBOM, and runtime checks.
- `tools/architecture/` and `tools/threat-model/` validate architecture and risk.
- `tools/ai-gates/` contains bounded model-review adapters.
- `tools/gc/` contains inventory, recurrence, and proposal logic.

## Critical commands

```bash
uvx --from . omp-fadd inspect /path/to/repository
uvx --from . omp-fadd plan /path/to/repository
uvx --from . omp-fadd install /path/to/repository
uvx --from . omp-fadd verify /path/to/repository
node tools/harness/checks/run-all.mjs
```

## Boundaries

Existing OMP skills, devices, MCP servers, built-in subagents, Hub, and memoir
remain available. Repository policies and controls are editable by default.
Human owners may explicitly configure restrictions when they want them.

<!-- OMP-FADD-REPO:START -->
FADD gates are repository-local under `tools/` and `.github/workflows/fadd-*`. Use the existing repository map as the system of record and run `node tools/harness/checks/run-all.mjs` before claiming completion.
Before acting, verify relevant official/version-matched documentation and real implementation/callers. Cite URLs and file/line evidence, mark unknowns, and treat model memory as a hypothesis, not proof.
<!-- OMP-FADD-REPO:END -->
