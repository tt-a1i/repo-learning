# Investigation Checklist

Use this after Phase 0 intake. Default: **read-only** — no installs, no executing unknown commands, no repo writes.

## Phase 0 — Intake

- [ ] Confirm target path, scope (whole repo vs subdir), and depth mode (`full` / `standard` / `shallow` / `recon-only`)
- [ ] Record constraints: offline, no network, monorepo, private, time budget
- [ ] Choose output dir (prefer OS temp or user-specified; never pollute target repo unless asked)

## Phase 1 — Entry & workspace

- [ ] Read `README*`, `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, `docs/README.md`
- [ ] Identify package roots (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, …)
- [ ] Note build/test entry commands **from docs only** — do not run unless user allows
- [ ] Evidence: cite each doc path:line

## Phase 2 — Repo map

- [ ] Map top-level dirs to roles (app, lib, infra, docs, scripts)
- [ ] List primary entrypoints (main, server, cli, worker)
- [ ] Populate `modules[]` with stable ids
- [ ] Artifact: topology edges between modules

## Phase 3 — Language & framework

- [ ] Language breakdown (from manifests + sampled dirs; cite evidence)
- [ ] Frameworks, ORMs, routers, UI stacks
- [ ] Populate `overview.languages` and framework claims

## Phase 4 — Runtime & routes

- [ ] HTTP/CLI/job triggers; middleware; auth boundaries
- [ ] Document 1–3 critical flows in `flows[]` with step evidence
- [ ] Do not guess routes — trace imports/callers

## Phase 5 — Data, config & trust boundaries

- [ ] Config sources (env, yaml, secrets refs — never print secret values)
- [ ] DB/cache/queue boundaries
- [ ] External integrations; mark trust boundaries in risks

## Phase 6 — Tests & CI

- [ ] Test frameworks, layout, CI configs (`.github/workflows`, etc.)
- [ ] Fill `tests.matrix` per major area
- [ ] Note missing coverage as gaps, not failures

## Phase 7 — Risk register

- [ ] Security, concurrency, data-loss, ops, dependency drift
- [ ] Each risk: severity, evidence, confidence
- [ ] Unverified suspicions → `appendix.open_questions`

## Phase 8 — Learning path

- [ ] Ordered roadmap for a new contributor (files → concepts → flows)
- [ ] Tie each phase to concrete paths

## Phase 9 — Report emit

1. Write `report_data.json` per `references/analysis-json-schema.md`
2. `python3 scripts/generate_report.py --input report_data.json --out <dir> --strict`
3. `python3 scripts/validate_report.py <dir> --strict`
4. Tell user absolute path to `index.html`

## Chart artifacts (minimum)

| Phase | SVG in report | Source fields |
|-------|---------------|---------------|
| Languages | bar chart | `overview.languages` |
| Topology | module graph | `modules`, `topology.edges` |
| Dependencies | internal + external | `dependencies.*` |
| Risks | heatmap | `risks[]` |
| Tests | matrix | `tests.matrix` |
| Roadmap | timeline | `roadmap[]` |

Optional: Mermaid **source only** in appendix as fenced code — do not rely on CDN rendering.

## Failure boundaries

- **Stop** if path is not a repo / unreadable → report blocked with reason
- **Degrade** per `references/failure-modes.md` instead of hallucinating
- **Never** fabricate line numbers — use `appendix.gaps`
- **Never** exfiltrate secrets — redact values, cite key names only

## Cross-skill pointers

- Read-only cognition depth: `$codebase-onboarding` at `software-development/codebase-onboarding/SKILL.md`
- Optional polished diagram pass (needs npm): `$archify` — not required for default offline report
