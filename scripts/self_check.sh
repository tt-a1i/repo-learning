#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$ROOT/scripts"
EXAMPLES="$SCRIPTS/examples"
OUT="$ROOT/.self_check_out"
TMP="$ROOT/.self_check_tmp"

fail() { echo "self_check FAIL: $*" >&2; exit 1; }
pass() { echo "self_check OK: $*"; }

rm -rf "$OUT" "$TMP"
mkdir -p "$OUT" "$TMP"
trap 'rm -rf "$OUT" "$TMP"' EXIT

echo "== compile =="
python3 -m py_compile "$SCRIPTS/prepare_repo.py" "$SCRIPTS/schema_validate.py" \
  "$SCRIPTS/generate_report.py" "$SCRIPTS/validate_report.py"
pass "python entrypoints compile"

echo "== v2 generate and validate =="
python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/site_data.v2.json" --out "$OUT" --validate-only --strict
python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/site_data.v2.json" --out "$OUT" --strict
python3 "$SCRIPTS/validate_report.py" "$OUT" --strict
HTML="$OUT/index.html"
grep -q 'class="hero"' "$HTML" || fail "missing hero"
grep -q 'class="architecture"' "$HTML" || fail "missing architecture diagram"
grep -q 'class="arch-edge-label"' "$HTML" || fail "missing architecture relationship labels"
grep -q 'class="connection-legend"' "$HTML" || fail "missing sourced relationship legend"
grep -q 'class="flow-story"' "$HTML" || fail "missing flow story"
grep -q 'class="concept-grid"' "$HTML" || fail "missing concept grid"
grep -q 'class="file-atlas"' "$HTML" || fail "missing code atlas"
grep -q 'class="learning-path"' "$HTML" || fail "missing learning path"
grep -q 'prefers-reduced-motion' "$HTML" || fail "missing reduced motion"
grep -q 'prefers-color-scheme' "$HTML" || fail "missing dark mode"
grep -q 'IntersectionObserver' "$HTML" || fail "missing motivated reveal/navigation motion"
grep -q 'id="site-data"' "$HTML" || fail "missing embedded site data"
pass "v2 visual site contract"

echo "== summary remains visible without highlights or languages =="
python3 - "$EXAMPLES/site_data.v2.json" "$TMP/summary-only.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
data["project"]["summary"] = "A summary that must remain visible."
data["highlights"] = []
data["languages"] = []
Path(sys.argv[2]).write_text(json.dumps(data), encoding="utf-8")
PY
SUMMARY_ONLY="$TMP/summary-only"
python3 "$SCRIPTS/generate_report.py" --input "$TMP/summary-only.json" --out "$SUMMARY_ONLY" --strict
python3 - "$SUMMARY_ONLY/index.html" <<'PY'
import re, sys
from pathlib import Path
source = Path(sys.argv[1]).read_text(encoding="utf-8")
visible = re.sub(r'<script id="site-data" type="application/json">.*?</script>', '', source, flags=re.S)
if 'id="overview"' not in visible or visible.count("A summary that must remain visible.") != 1:
    raise SystemExit("summary-only overview was omitted from visible HTML")
PY
pass "summary-only overview remains visible"

echo "== architecture does not silently truncate large repositories =="
python3 - "$EXAMPLES/site_data.v2.json" "$TMP/large.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
data["modules"] = [
    {"id": f"m{i}", "name": f"Module {i}", "kind": "service", "role": "Test node"}
    for i in range(1, 21)
]
data["connections"] = [
    {"from": f"m{i}", "to": f"m{i+1}", "label": "calls", "evidence": f"src/m{i}.py:1"}
    for i in range(1, 20)
]
Path(sys.argv[2]).write_text(json.dumps(data), encoding="utf-8")
PY
LARGE="$TMP/large"; python3 "$SCRIPTS/generate_report.py" --input "$TMP/large.json" --out "$LARGE" --strict
grep -q 'data-module="m20"' "$LARGE/index.html" || fail "module 20 was truncated"
grep -q '>calls</text>' "$LARGE/index.html" || fail "connection label not rendered"
grep -q 'src/m19.py:1' "$LARGE/index.html" || fail "connection evidence not rendered"
pass "all modules and sourced relationship labels render"

echo "== legacy v1 compatibility =="
LEGACY="$TMP/legacy"
python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/report_data.rich.json" --out "$LEGACY" --strict
python3 "$SCRIPTS/validate_report.py" "$LEGACY" --strict
grep -q 'polyglot-monorepo' "$LEGACY/index.html" || fail "legacy title missing"
grep -q 'class="architecture"' "$LEGACY/index.html" || fail "legacy modules not normalised"
grep -q '>fastapi<' "$LEGACY/index.html" || fail "legacy external dependencies were lost"
grep -q 'class="test-grid"' "$LEGACY/index.html" || fail "legacy test matrix was lost"
grep -q '>orders<' "$LEGACY/index.html" || fail "legacy test area was lost"
grep -q 'Is there a staging environment?' "$LEGACY/index.html" || fail "legacy open questions were lost"
pass "legacy v1 data still generates the new site"

echo "== links are allowed, remote assets are not =="
grep -q 'href="https://github.com/example/northstar"' "$HTML" || fail "source link was not rendered"
REMOTE="$TMP/remote"; mkdir -p "$REMOTE"; cp "$HTML" "$REMOTE/index.html"
printf '%s\n' '<script src="https://example.org/bad.js"></script>' >> "$REMOTE/index.html"
set +e
remote_output="$(python3 "$SCRIPTS/validate_report.py" "$REMOTE" --strict 2>&1)"
remote_status=$?
set -e
[ "$remote_status" -ne 0 ] || fail "remote script should fail validation"
echo "$remote_output" | grep -q 'remote executable asset matched' || fail "remote asset error missing"
pass "source links pass and executable assets fail"

echo "== dynamic text and embedded JSON are escaped =="
XSS="$TMP/xss"
python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/site_data.v2.xss.json" --out "$XSS" --strict
python3 "$SCRIPTS/validate_report.py" "$XSS" --strict
grep -Fq '&lt;/SCRIPT&gt;&lt;script&gt;globalThis.pwned=true&lt;/script&gt;' "$XSS/index.html" || fail "mixed-case script text not escaped"
grep -Fq '\u003c/SCRIPT\u003e' "$XSS/index.html" || fail "embedded JSON did not escape angle brackets"
python3 - "$XSS/index.html" <<'PY'
import re, sys
from pathlib import Path
source = Path(sys.argv[1]).read_text(encoding="utf-8")
without_data = re.sub(r'<script id="site-data" type="application/json">.*?</script>', '', source, flags=re.S)
if "globalThis.pwned" in without_data and "&lt;script&gt;" not in without_data:
    raise SystemExit("executable XSS leaked into the website")
if without_data.count("<script") != 1:
    raise SystemExit("unexpected executable script count")
PY
pass "mixed-case script text and URL-like prose are safe"

echo "== malformed inputs fail cleanly =="
for fixture in bad_top_level_overview_array.json bad_nested_language_percent_string.json \
  bad_nested_flow_step_int.json bad_dangling_edge.json; do
  set +e
  result="$(python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/$fixture" --out "$TMP/bad" --validate-only --strict 2>&1)"
  status=$?
  set -e
  [ "$status" -ne 0 ] || fail "$fixture unexpectedly passed"
  echo "$result" | grep -q 'Traceback' && fail "$fixture emitted a traceback"
done
pass "malformed legacy fixtures fail without traceback"

set +e
v2_bad="$(python3 "$SCRIPTS/generate_report.py" --input "$EXAMPLES/bad_v2_learning_path_int.json" --out "$TMP/bad-v2" --strict 2>&1)"
v2_status=$?
set -e
[ "$v2_status" -ne 0 ] || fail "bad v2 nested learning path unexpectedly passed"
echo "$v2_bad" | grep -q 'learning_path\[0\].files must be an array' || fail "bad v2 error missing"
echo "$v2_bad" | grep -q 'Traceback' && fail "bad v2 emitted traceback"
pass "malformed v2 nested fields fail before rendering"

echo "== duplicate section ids fail =="
DUP="$TMP/duplicate"; mkdir -p "$DUP"; cp "$HTML" "$DUP/index.html"
printf '%s\n' '<section id="overview"></section>' >> "$DUP/index.html"
set +e
duplicate_output="$(python3 "$SCRIPTS/validate_report.py" "$DUP" --strict 2>&1)"
duplicate_status=$?
set -e
[ "$duplicate_status" -ne 0 ] || fail "duplicate section id should fail"
echo "$duplicate_output" | grep -q 'duplicate section ids' || fail "duplicate id error missing"
pass "duplicate sections rejected"

echo "== local repository preparation =="
python3 "$SCRIPTS/prepare_repo.py" "$ROOT" --json-out "$TMP/prepared.json" >/dev/null
python3 - "$TMP/prepared.json" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text())
assert data["cloned"] is False
assert Path(data["repo_path"]).is_dir()
PY
pass "local repository input resolves without cloning"

echo "self_check: all checks passed"
