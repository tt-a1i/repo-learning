# `site_data.json` v2

Version 2 is a storytelling model, not a database schema. Only `project` and one
useful learning section are required in strict mode. Omit empty sections.

## Core shape

```json
{
  "schema_version": "2",
  "project": {
    "name": "Project name",
    "source": "https://github.com/org/repo",
    "tagline": "One clear sentence.",
    "summary": "A short mental model for a new contributor.",
    "generated_at": "2026-07-10T10:00:00Z"
  },
  "languages": [],
  "highlights": [],
  "modules": [],
  "connections": [],
  "flows": [],
  "concepts": [],
  "external_dependencies": [],
  "code_map": [],
  "quick_start": [],
  "learning_path": [],
  "tests": {},
  "risks": [],
  "gaps": []
}
```

## Evidence

Use a string or a list of source locations:

```json
{"evidence": ["src/server.ts:18", "src/router.ts:9-22"]}
```

Attach evidence to conclusions that benefit from a direct path into source.
Narrative copy does not need a citation on every sentence.

## Modules and connections

```json
"modules": [
  {
    "id": "api",
    "name": "API",
    "kind": "service",
    "role": "Turns HTTP requests into domain commands",
    "evidence": "src/api/server.ts:1"
  }
],
"connections": [
  {
    "from": "web",
    "to": "api",
    "label": "HTTP",
    "evidence": "src/web/client.ts:12"
  }
]
```

Module `id` values must be unique. Connection endpoints must reference existing
module ids. Suggested `kind` values include `entry`, `ui`, `service`, `domain`,
`lib`, `data`, `database`, `external`, `test`, and `config`.

## Runtime flows

```json
{
  "title": "Create an order",
  "summary": "The API validates synchronously and persists through the domain layer.",
  "steps": [
    {"label": "Receive POST /orders", "evidence": "src/routes/orders.ts:20"},
    {"label": "Validate order", "evidence": "src/domain/order.ts:31"},
    {"label": "Persist record", "evidence": "src/data/orders.ts:44"}
  ]
}
```

Use flows for requests, CLI commands, background jobs, sync cycles, event
lifecycles, and build pipelines.

## Concepts

```json
{
  "name": "Snapshot",
  "explanation": "An immutable view of imported source state.",
  "why_it_matters": "Diffs and retries are calculated between snapshots.",
  "evidence": "src/domain/snapshot.ts:5"
}
```

Prefer project-specific language over generic framework terms.

## Code map

```json
{
  "path": "src/server.ts",
  "role": "Application entrypoint",
  "read_when": "Start here to see middleware and routes assembled."
}
```

Choose a small set of high-value entrypoints. Do not dump the repository tree.

## External dependencies and tests

Use `external_dependencies[]` for frameworks, hosted services and infrastructure
that shape the system boundary. Each item can contain `name`, `type`, `role` and
`evidence`.

Use `tests.coverage_notes` for a short assessment and `tests.matrix[]` for major
areas. Matrix flags `unit`, `integration` and `e2e` are booleans when known.

## Quick start

```json
{
  "title": "Start development",
  "command": "pnpm dev",
  "note": "Starts the web and API packages."
}
```

Quick-start commands are displayed in the website. The generator does not run
them.

## Learning path

```json
{
  "title": "Trace one request",
  "outcome": "Explain the route-to-storage call chain.",
  "files": ["src/routes/orders.ts", "src/domain/order.ts"]
}
```

Name steps by their learning outcome, not generic phase numbers.

## Risks and gaps

Risks are source-backed known concerns. Gaps are things the investigation could
not verify.

```json
"risks": [
  {
    "title": "Retry path lacks an idempotency key",
    "severity": "high",
    "impact": "A repeated job may create duplicate facts.",
    "evidence": "src/jobs/import.ts:52"
  }
],
"gaps": ["Production deployment topology is not visible in this repository."]
```

## Legacy compatibility

`generate_report.py` also accepts schema v1 `report_data.json` files and maps
their overview, modules, topology, flows, roadmap, risks, and appendix into the
new website.
