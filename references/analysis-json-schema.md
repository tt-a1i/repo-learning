# report_data.json v1 Schema

`scripts/generate_report.py` consumes a single JSON object. Root field `schema_version` must be `"1"`.

Validation is centralized in `scripts/schema_validate.py` (`collect_errors(data, strict)`). Both `generate_report.py --validate-only --strict` and `validate_report.py --strict` (embedded `#report-data` JSON) call the same function—no duplicate drift.

Golden fixtures live in `scripts/examples/`. Run `bash scripts/self_check.sh` from the skill root for regression checks.

## Top-level fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `schema_version` | string | yes | Always `"1"` |
| `meta` | object | yes | Report metadata |
| `overview` | object | yes | Summary + claims |
| `modules` | array | yes | Internal module nodes (may be empty in recon-only) |
| `topology` | object | no | Module relationships |
| `dependencies` | object | no | Internal + external deps |
| `flows` | object[] | no | Runtime / request flows |
| `risks` | object[] | no | Risk register |
| `tests` | object | no | Test/CI notes + matrix |
| `roadmap` | object[] | no | Suggested learning path |
| `appendix` | object | no | Gaps, open questions, files examined |

## meta

| Field | Type | Notes |
|-------|------|-------|
| `repo_name` | string | Display name |
| `repo_path` | string | Absolute or workspace path analyzed |
| `generated_at` | string | ISO-8601 timestamp |
| `mode` | string | `full` / `standard` / `shallow` / `recon-only` |
| `confidence` | string | Optional rollup: `high` / `medium` / `low` |

## Evidence objects

Any claim-like item should include:

```json
{
  "text": "FastAPI app mounts routers under /api",
  "evidence": "src/main.py:18-42",
  "confidence": "high"
}
```

Use `path:line` or `path:start-end`. If unverified, move to `appendix.gaps` instead of asserting.

## modules[]

```json
{ "id": "api", "name": "HTTP API", "description": "...", "evidence": "src/api/:1" }
```

`id` must be unique. Topology/dependency edges reference these ids.

## topology / dependencies

```json
"topology": { "edges": [{ "from": "api", "to": "core", "label": "calls", "evidence": "..." }] },
"dependencies": {
  "internal": [{ "from": "api", "to": "core", "evidence": "..." }],
  "external": [{ "name": "fastapi", "type": "runtime", "evidence": "pyproject.toml:12" }]
}
```

## tests.matrix[]

```json
{ "area": "auth", "unit": true, "integration": false, "e2e": false, "evidence": "tests/test_auth.py:1" }
```

`unit`/`integration`/`e2e` are optional booleans. In the rendered matrix, `true` → `✓` (covered), `false` → `✗` (missing), and a **missing** flag renders as `?` (unknown) — the report never silently hides an unassessed test status.

## Nested type rules (always enforced)

These apply in both normal and `--strict` mode (strict adds evidence requirements on top):

| Path | Expected type | Notes |
|------|---------------|-------|
| `overview` | object | Not an array |
| `overview.languages[]` | object | Each entry |
| `overview.languages[].percent` | number | Not string/bool; required numeric when `percent` key present |
| `overview.claims[]` | string \| object | Objects may include `evidence` string or array |
| `modules[]` | object | Each with unique string `id` |
| `topology`, `dependencies`, `tests`, `appendix` | object | Section containers |
| `topology.edges[]`, `dependencies.internal[]` | object | `from`/`to` must reference existing module ids |
| `dependencies.external[]` | object | Each entry |
| `flows[]` | object | Each flow |
| `flows[].steps[]` | string \| object | Not number/bool/array |
| `risks[]` | object | `severity` must be string when present |
| `tests.matrix[]` | object | `unit`/`integration`/`e2e` must be boolean when present |
| `roadmap[]` | object | `phase` numeric when present; `items[]` string \| object |
| `appendix.gaps[]`, etc. | string \| object | Same as claims |

## Minimal example

```json
{
  "schema_version": "1",
  "meta": {
    "repo_name": "demo-app",
    "repo_path": "/tmp/demo-app",
    "generated_at": "2026-07-08T12:00:00Z",
    "mode": "standard",
    "confidence": "medium"
  },
  "overview": {
    "summary": "Small FastAPI service with one router and pytest coverage.",
    "claims": [
      { "text": "Entrypoint creates FastAPI app", "evidence": "src/main.py:8", "confidence": "high" }
    ],
    "languages": [{ "name": "Python", "percent": 100, "evidence": "pyproject.toml:1" }]
  },
  "modules": [
    { "id": "api", "name": "API", "description": "HTTP layer", "evidence": "src/api/routes.py:1" },
    { "id": "core", "name": "Core", "description": "Domain logic", "evidence": "src/core/service.py:1" }
  ],
  "topology": { "edges": [{ "from": "api", "to": "core", "evidence": "src/api/routes.py:4" }] },
  "dependencies": {
    "internal": [{ "from": "api", "to": "core", "evidence": "src/api/routes.py:4" }],
    "external": [{ "name": "fastapi", "type": "runtime", "evidence": "pyproject.toml:12" }]
  },
  "flows": [{ "id": "health", "title": "Health check", "steps": [{ "label": "GET /health", "evidence": "src/api/routes.py:10" }] }],
  "risks": [{ "title": "No auth on admin route", "severity": "high", "evidence": "src/api/routes.py:22", "confidence": "medium" }],
  "tests": {
    "coverage_notes": "pytest only; no CI config found",
    "matrix": [{ "area": "health", "unit": true, "integration": false, "e2e": false, "evidence": "tests/test_health.py:1" }]
  },
  "roadmap": [{ "phase": 1, "title": "Read entry + routes", "items": ["src/main.py", "src/api/routes.py"] }],
  "appendix": {
    "gaps": ["Deployment topology not verified"],
    "open_questions": ["Is there a staging environment?"],
    "files_examined": ["src/main.py:1-40", "pyproject.toml:1-30"]
  }
}
```
