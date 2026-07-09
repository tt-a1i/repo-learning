# Failure Modes & Degradation

Pick the deepest mode the constraints allow. Document chosen mode in `meta.mode`.

## Modes

| Mode | When | Minimum output |
|------|------|----------------|
| `full` | Time + access OK | All phases, strict evidence, full SVG set |
| `standard` | Default | Phases 1–8, core SVGs, some gaps OK |
| `shallow` | Large repo / time box | Entry map + top modules + risks + roadmap |
| `recon-only` | Read blocked / partial tree | README + manifest summary, empty modules OK, heavy gaps |

## Triggers to degrade

- **Monorepo**: scope to one package; set gap "other packages not analyzed"
- **Huge tree**: sample by entrypoints + manifests; don't enumerate every file
- **No network**: skip live registry lookups; cite lockfiles only
- **Unreadable/private paths**: recon-only from visible metadata
- **Non-writable output dir**: write to `$TMPDIR/repo-learning-<ts>/`
- **Missing manifests**: infer from extensions with low confidence + gap

## Strict vs pragmatic

- `--strict` on generator: requires evidence on modules/claims, non-empty gaps
- Without strict: allow sparse modules but never invent line numbers

## Blocked (report to user, do not proceed silently)

- Target path does not exist
- Permission denied on entire tree
- User forbids all file reads

## Validator failures

| Error | Fix |
|-------|-----|
| missing section id | regenerate with current `generate_report.py` |
| http/cdn match | remove external URLs; inline assets |
| TODO/FIXME | replace placeholders before ship |
| dangling module id | fix JSON edges or add module node |

## Optional archify path

Not a fallback for offline failure. Use only when user opts in and npm is available. Default offline SVG charts must still ship in main report.
