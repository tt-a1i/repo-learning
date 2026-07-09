---
name: repo-learning
description: Deep-read unfamiliar repositories and produce a polished, self-contained HTML learning report with architecture, dependency, workflow, and onboarding diagrams backed by file-level evidence. Use when the user asks to learn, onboard to, analyze, map, or research a new/unfamiliar codebase or repo; wants a repo overview, architecture review, dependency graph, visual study guide, or shareable HTML artifact. Read-only by default—do not modify the target repo, install packages, or execute unknown commands unless explicitly allowed.
---

# Repo Learning

Orchestrate a **read-only** repository investigation and ship an **offline** HTML report with inline SVG charts. You compile findings into JSON, then render with bundled scripts—no CDN, no npm, no target-repo writes by default.

## Default rules

1. **Read-only** — grep/read/list only; no commits, installs, or mystery shell commands.
2. **Evidence required** — every claim uses `path:line` (or range); unverified items go to `appendix.gaps` with confidence noted.
3. **Offline report** — final `index.html` must be self-contained (inline CSS/JS/SVG). No remote/executable resources: `src=`/`href=`/`url()` pointing at `http(s)://`, protocol-relative `//`, or `data:` URIs; plain URLs cited inside evidence text are allowed.
4. **Chinese by default** — write `report_data.json` content (summary, claims, risks, flows, roadmap, gaps) in **简体中文**, and generate HTML UI in Chinese, unless the user explicitly asks for English (or another language). Override HTML chrome with `--lang en` or `meta.locale: "en"`.
5. **Degrade gracefully** — pick `meta.mode` per constraints; see [references/failure-modes.md](references/failure-modes.md).
6. **Reuse cognition skills** — for onboarding depth, read `$codebase-onboarding` (`software-development/codebase-onboarding/SKILL.md`) before deep mapping; do not duplicate its full checklist here.

## When to read references

| Reference | Read when |
|-----------|-----------|
| [investigation-checklist.md](references/investigation-checklist.md) | Starting any non-trivial analysis |
| [analysis-json-schema.md](references/analysis-json-schema.md) | Building or validating `report_data.json` |
| [report-design.md](references/report-design.md) | Before emit; understand section/chart contract |
| [failure-modes.md](references/failure-modes.md) | Time-boxed, monorepo, offline, or partial access |

## Workflow (Phases 0–9)

| Phase | Goal | Key outputs |
|-------|------|-------------|
| 0 Intake | Scope, mode, output path | `meta.*` |
| 1 Entry & workspace | Docs, manifests, entrypoints | overview claims |
| 2 Repo map | Dirs → modules | `modules[]`, topology |
| 3 Language & framework | Stack ID | `overview.languages` |
| 4 Runtime & routes | Flows, auth | `flows[]` |
| 5 Data & trust | Config, boundaries | risks, deps |
| 6 Tests & CI | Harness map | `tests.*` |
| 7 Risk register | Pitfalls | `risks[]` |
| 8 Learning path | Contributor roadmap | `roadmap[]` |
| 9 Report emit | HTML | `index.html` |

Detailed checklists: [references/investigation-checklist.md](references/investigation-checklist.md).

## Script pipeline (order)

Run from this skill directory or use absolute paths under `~/.agents_skills/repo-learning/scripts/`.

### 1. Validate JSON (optional dry-run)

```bash
python3 scripts/generate_report.py --input report_data.json --out /tmp/repo-learning-out --validate-only --strict
```

### 2. Generate HTML

```bash
python3 scripts/generate_report.py \
  --input report_data.json \
  --out /tmp/repo-learning-out \
  --mode single \
  --title "仓库学习简报" \
  --strict
```

Default UI language is Chinese. For English chrome: add `--lang en` (or set `meta.locale` to `"en"`).

Writes `/tmp/repo-learning-out/index.html` with sections: `overview`, `topology`, `dependencies`, `flows`, `risks`, `tests`, `roadmap`, `appendix` plus embedded `report-data` JSON.

### 3. Validate HTML

```bash
python3 scripts/validate_report.py /tmp/repo-learning-out --strict
```

Fix any errors before delivering. Open locally: `open /tmp/repo-learning-out/index.html` (macOS).

## JSON contract

Follow [references/analysis-json-schema.md](references/analysis-json-schema.md) (`schema_version: "1"`).

Minimum for `--strict` generation:

- `meta.repo_name`, `meta.repo_path`
- `overview.claims[]` each with `evidence`
- `modules[]` each with unique `id` + `evidence`
- `appendix.gaps[]` listing unknowns
- Topology/dependency edges must reference existing module ids

## Evidence rules

- Format: `relative/path:line` or `path:start-end`
- Prefer primary sources (entrypoints, manifests, ADRs) over transitive guesses
- Confidence: `high` (read source), `medium` (strong inference), `low` (pattern guess—prefer gap instead)
- Never cite line 0 or fabricated paths

## Charts & brief (default)

`generate_report.py` renders an offline editorial **learning brief** (inline SVG/HTML, no D3/Mermaid/CDN):

- Layout: full-bleed cover → sticky horizontal chapter index → numbered chapter stream (not sidebar + white cards)
- Cover thesis + quiet KPIs + deterministic accent hue
- Language bars, topology grid, dependency swimlane (occupied lanes only)
- Risk matrix densified to occupied rows/cols + severity-sorted risk list
- Module index rows, numbered flow columns, test matrix, metro learning path
- Empty sections stay present (id contract) but visually de-emphasized
- Evidence chips/drawer, cross-highlight, severity filters, print/screenshot/mobile

Mermaid: optional **source blocks** in appendix only—not rendered in default offline HTML.

## Optional upgrades (non-default)

| Need | Skill | Note |
|------|-------|------|
| Deeper read-only onboarding | `$codebase-onboarding` | Methods only; this skill owns HTML output |
| Premium diagram HTML | `$archify` | Requires npm; supplementary only if user opts in |
| LOC metrics | `$codebase-inspection` | Optional evidence for overview |

Do **not** make archify/npm a prerequisite for the default report.

## Degradation quick pick

| Situation | `meta.mode` |
|-----------|-------------|
| Normal analysis | `standard` |
| Thorough pass | `full` |
| Large repo / tight time | `shallow` |
| Minimal visibility | `recon-only` |

See [references/failure-modes.md](references/failure-modes.md).

## Delivery checklist

- [ ] `report_data.json` matches schema
- [ ] `generate_report.py --strict` succeeds
- [ ] `validate_report.py --strict` succeeds
- [ ] User given absolute path to `index.html`
- [ ] Gaps and open questions surfaced in appendix
- [ ] No secrets in JSON or HTML

## Skill self-check

```bash
bash scripts/self_check.sh
```

`self_check.sh` runs `py_compile`, golden fixture validation, bad-fixture rejection, duplicate-section HTML checks, embedded JSON strict round-trip, sticky-TOC/evidence-chip/drawer presence, hero KPI/legend/filter/swimlane/risk-matrix/metro/print/screenshot structure checks (rich fixture), over-cap +N summaries, URL-in-evidence passes, remote script/link + protocol-relative/data:URI injection rejection, and XSS escape checks.

Optional skill metadata check:

```bash
python3 ~/.agents_skills/.system/skill-creator/scripts/quick_validate.py ~/.agents_skills/repo-learning
```

If `quick_validate.py` fails on missing PyYAML, `self_check.sh` alone is sufficient.
