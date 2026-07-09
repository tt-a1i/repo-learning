#!/bin/sh
# Repo-learning regression self-check (P0+P1). Run from skill root: bash scripts/self_check.sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SCRIPTS="$ROOT/scripts"
EXAMPLES="$SCRIPTS/examples"
OUT="$ROOT/.self_check_out"
DUP="$ROOT/.self_check_dup"

fail() {
  echo "self_check FAIL: $*" >&2
  exit 1
}

pass() {
  echo "self_check OK: $*"
}

echo "== py_compile =="
python3 -m py_compile "$SCRIPTS/schema_validate.py" "$SCRIPTS/generate_report.py" "$SCRIPTS/validate_report.py"

OK_JSON="$EXAMPLES/report_data.ok.json"
rm -rf "$OUT" "$DUP"
mkdir -p "$OUT" "$DUP"

echo "== ok fixture: validate-only strict =="
python3 "$SCRIPTS/generate_report.py" \
  --input "$OK_JSON" \
  --out "$OUT" \
  --validate-only \
  --strict

echo "== ok fixture: generate strict =="
python3 "$SCRIPTS/generate_report.py" \
  --input "$OK_JSON" \
  --out "$OUT" \
  --strict

echo "== ok fixture: validate HTML strict =="
python3 "$SCRIPTS/validate_report.py" "$OUT" --strict

echo "== generated HTML must not contain remote resource attributes =="
HTML="$OUT/index.html"
python3 - "$HTML" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
scheme = r'(?:https?://|//|data:)'
patterns = [
    re.compile(r'<[^>]+\b(?:src|href)\s*=\s*["\']?\s*' + scheme, re.I),
    re.compile(r'url\s*\(\s*["\']?\s*' + scheme, re.I),
]
for p in patterns:
    m = p.search(text)
    if m:
        print(f"remote resource pattern matched: {p.pattern}", file=sys.stderr)
        sys.exit(1)
PY
pass "no remote resource attributes in generated HTML"

echo "== generated HTML contains sticky TOC, evidence chip, drawer =="
grep -q 'id="toc"' "$HTML" || fail "missing TOC nav (id=toc)"
grep -q 'class="ev-chip"' "$HTML" || fail "missing evidence chip (class=ev-chip)"
grep -q '<dialog id="ev-drawer"' "$HTML" || fail "missing evidence drawer (dialog#ev-drawer)"
grep -q 'IntersectionObserver' "$HTML" || fail "missing nav active-section JS"
pass "TOC nav, evidence chips, drawer, nav JS present"

echo "== rich fixture: hero KPI, legend, filter chips, swimlane, risk matrix, metro, print/screenshot =="
RICH_OUT="$DUP/rich_out"
mkdir -p "$RICH_OUT"
python3 "$SCRIPTS/generate_report.py" \
  --input "$EXAMPLES/report_data.rich.json" \
  --out "$RICH_OUT" \
  --strict
python3 "$SCRIPTS/validate_report.py" "$RICH_OUT" --strict
RICH_HTML="$RICH_OUT/index.html"
grep -q 'class="kpi-strip"' "$RICH_HTML" || fail "missing hero KPI strip"
grep -q 'class="kpi"' "$RICH_HTML" || fail "missing KPI items"
grep -q 'style="--hue:' "$RICH_HTML" || fail "missing deterministic accent hue"
grep -q 'class="legend-row"' "$RICH_HTML" || fail "missing legend"
grep -q 'class="filter-chip"' "$RICH_HTML" || fail "missing filter chips"
grep -q 'class="lane"' "$RICH_HTML" || fail "missing swimlane lane backgrounds"
grep -q 'id="arrow"' "$RICH_HTML" || fail "missing dependency arrow marker"
grep -q 'class="risk-cell"' "$RICH_HTML" || fail "missing risk matrix cells"
grep -q 'class="test-matrix"' "$RICH_HTML" || fail "missing test matrix table"
grep -q 'class="metro"' "$RICH_HTML" || fail "missing metro roadmap"
grep -q 'data-module=' "$RICH_HTML" || fail "missing data-module highlight hooks"
grep -q 'data-screenshot=' "$RICH_HTML" || fail "missing screenshot toggle"
grep -q '@media print' "$RICH_HTML" || fail "missing print CSS"
grep -q 'screenshot-mode' "$RICH_HTML" || fail "missing screenshot-mode CSS"
grep -q 'data-filter-group=' "$RICH_HTML" || fail "missing filter data attributes"
grep -q 'data-status=' "$RICH_HTML" || fail "missing test status data attributes"
grep -q 'data-severity=' "$RICH_HTML" || fail "missing risk severity data attributes"
pass "rich fixture: hero KPI+hue, legends, filters, swimlane, risk matrix, metro, print/screenshot, data hooks present"

echo "== over-cap fixture: +N more summaries rendered ==="
OVER_OUT="$DUP/over_out"
mkdir -p "$OVER_OUT"
python3 - "$EXAMPLES/report_data.rich.json" "$DUP/overcap.json" <<'PY'
import json, sys
from pathlib import Path
base = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
orig = base["modules"][:]
base["modules"] = orig + [
    {"id": f"m{i}", "name": f"Mod{i}", "kind": ["ui","service","domain","data","test","config"][i%6], "description": "x", "evidence": f"src/m{i}.py:1"}
    for i in range(24)
]
base["risks"] = [
    {"title": f"risk-{i}", "severity": "high" if i%3==0 else "medium",
     "category": ["security","complexity","test","ops","unknown"][i%5],
     "module_id": base["modules"][i % len(base["modules"])]["id"], "evidence": f"src/r{i}.py:1"}
    for i in range(35)
]
base["tests"]["matrix"] = [
    {"area": f"area{i}", "unit": i%2==0, "integration": i%3==0, "e2e": False, "evidence": f"tests/t{i}.py:1"}
    for i in range(30)
]
base["dependencies"]["external"] = [
    {"name": f"dep{i}", "type": "runtime", "evidence": f"pkg.toml:{i}"}
    for i in range(15)
]
Path(sys.argv[2]).write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
PY
python3 "$SCRIPTS/generate_report.py" \
  --input "$DUP/overcap.json" \
  --out "$OVER_OUT" \
  --strict
python3 "$SCRIPTS/validate_report.py" "$OVER_OUT" --strict
OVER_HTML="$OVER_OUT/index.html"
# Cap notes are localized (default zh). Accept zh or en wording.
grep -E -q '\+[0-9]+ (more modules not shown|个模块未显示)' "$OVER_HTML" || fail "missing +N modules cap note"
grep -E -q '\+[0-9]+ (more risks not shown|条风险未显示)' "$OVER_HTML" || fail "missing +N risks cap note"
grep -E -q '\+[0-9]+ (more test areas not shown|个测试区域未显示)' "$OVER_HTML" || fail "missing +N tests cap note"
grep -E -q '\+[0-9]+ (more external deps|个外部依赖未显示)' "$OVER_HTML" || fail "missing +N external deps cap note"
# external +N note must sit below the dep pills, not overlap them.
python3 - "$OVER_HTML" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(
    r'<svg class="chart" viewBox="0 0 (\d+) (\d+)" role="img" aria-label="(?:Dependency swimlane|依赖泳道)">(.*?)</svg>',
    text, re.DOTALL,
)
if not m:
    print("dependency swimlane svg not found", file=sys.stderr); sys.exit(1)
h, body = int(m.group(2)), m.group(3)
notes = re.findall(r'y="(\d+)"[^>]*>\+(\d+) (?:more external deps|个外部依赖未显示)', body)
pills = re.findall(r'<rect x="\d+" y="(\d+)" width="\d+" height="\d+" rx="\d+" class="pill"/>', body)
if not notes or not pills:
    print("missing external note or pills", file=sys.stderr); sys.exit(1)
# external note y must be greater than every pill y (i.e. below the pills)
max_pill = max(int(p) for p in pills)
for y_str, _ in notes:
    if int(y_str) <= max_pill:
        print(f"external +N note y={y_str} overlaps pills (max pill y={max_pill})", file=sys.stderr)
        sys.exit(1)
PY
pass "over-cap fixture: +N summaries rendered (modules/risks/tests/external) and external note below pills"

echo "== unknown-module-id risk must land in global/unknown row (not dropped) =="
UNK_OUT="$DUP/unk_out"
mkdir -p "$UNK_OUT"
python3 "$SCRIPTS/generate_report.py" \
  --input "$EXAMPLES/report_data.unknown_risk.json" \
  --out "$UNK_OUT" \
  --strict
python3 "$SCRIPTS/validate_report.py" "$UNK_OUT" --strict
UNK_HTML="$UNK_OUT/index.html"
grep -E -q 'global/unknown|全局/未知' "$UNK_HTML" || fail "missing global/unknown row for unknown module_id risks"
python3 - "$UNK_HTML" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
# The fixture has a high-severity risk with module_id="nonexistent" (unknown)
# and category=security. It must appear as a global/__global__ cell, high severity.
global_security = re.findall(
    r'<g class="risk-cell" data-module="__global__" data-severity="(\w+)" data-category="(\w+)">.*?<text[^>]*>([^<]*)</text>',
    text, re.DOTALL,
)
match = [g for g in global_security if g[1] == "security" and g[0] == "high"]
if not match:
    print("high-severity unknown-module risk not found in global/unknown security cell", file=sys.stderr)
    print("global cells found:", global_security, file=sys.stderr)
    sys.exit(1)
if "1" not in match[0][2] or "▲" not in match[0][2]:
    print(f"global security cell text unexpected: {match[0][2]!r}", file=sys.stderr)
    sys.exit(1)
PY
pass "unknown-module-id high risk visible in global/unknown row, not dropped"

echo "== URL in evidence must pass generate+validate strict =="
URL_OUT="$DUP/url_out"
mkdir -p "$URL_OUT"
python3 "$SCRIPTS/generate_report.py" \
  --input "$EXAMPLES/report_data.url_evidence.json" \
  --out "$URL_OUT" \
  --strict
python3 "$SCRIPTS/validate_report.py" "$URL_OUT" --strict
grep -q 'https://example.org/spec' "$URL_OUT/index.html" \
  && pass "URL evidence rendered and validated strict" \
  || fail "URL evidence not found in generated HTML"

echo "== remote script/link injection must fail validate strict =="
REMOTE_DIR="$DUP/remote"
mkdir -p "$REMOTE_DIR"
cp "$OUT/index.html" "$REMOTE_DIR/index.html"
printf '%s\n' '<script src="https://example.org/x.js"></script>' >> "$REMOTE_DIR/index.html"
printf '%s\n' '<link href="https://example.org/x.css" rel="stylesheet">' >> "$REMOTE_DIR/index.html"
set +e
remote_out="$(python3 "$SCRIPTS/validate_report.py" "$REMOTE_DIR" --strict 2>&1)"
remote_status=$?
set -e
if [ "$remote_status" -eq 0 ]; then
  fail "remote script/link injection should fail strict validation"
fi
echo "$remote_out" | grep -q 'remote resource reference matched' \
  && pass "remote script/link injection rejected" \
  || fail "unexpected remote injection output: $remote_out"

echo "== protocol-relative // and data: URI injection must fail validate strict =="
PROTO_DIR="$DUP/proto"
mkdir -p "$PROTO_DIR"
cp "$OUT/index.html" "$PROTO_DIR/index.html"
{
  printf '%s\n' '<script src="//cdn.evil/x.js"></script>'
  printf '%s\n' '<img src="data:text/html,<script>alert(1)</script>">'
  printf '%s\n' '<style>body{background:url(//cdn.evil/x.png)}</style>'
  printf '%s\n' '<style>body{background:url(data:image/svg+xml,x)}</style>'
} >> "$PROTO_DIR/index.html"
set +e
proto_out="$(python3 "$SCRIPTS/validate_report.py" "$PROTO_DIR" --strict 2>&1)"
proto_status=$?
set -e
if [ "$proto_status" -eq 0 ]; then
  fail "protocol-relative // and data: URI injection should fail strict validation"
fi
echo "$proto_out" | grep -q 'remote resource reference matched' \
  && pass "protocol-relative // and data: URI injection rejected" \
  || fail "unexpected proto injection output: $proto_out"

echo "== XSS: evidence with <script> must be escaped, not executable =="
XSS_OUT="$DUP/xss_out"
mkdir -p "$XSS_OUT"
python3 "$SCRIPTS/generate_report.py" \
  --input "$EXAMPLES/report_data.xss_evidence.json" \
  --out "$XSS_OUT" \
  --strict
python3 "$SCRIPTS/validate_report.py" "$XSS_OUT" --strict
XSS_HTML="$XSS_OUT/index.html"
# The escaped form must be present as text inside the evidence chip.
grep -q '&lt;script&gt;alert(1)&lt;/script&gt;' "$XSS_HTML" \
  || fail "evidence <script> not HTML-escaped in chip"
# No unescaped executable <script>alert(1) sequence outside the JSON blob.
python3 - "$XSS_HTML" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
# Remove the embedded report-data JSON block before scanning: it legitimately
# stores the evidence string as data (closing </script> already escaped).
body = re.sub(
    r'<script id="report-data" type="application/json">.*?</script>',
    '', text, flags=re.DOTALL,
)
# Outside JSON, only the nav JS <script> tag is legitimate.
real = body.count("<script")
if real != 1:
    print(f"expected 1 nav <script> tag outside JSON, found {real}", file=sys.stderr)
    sys.exit(1)
if "<script>alert(1)" in body:
    print("unescaped <script>alert(1) found in HTML body", file=sys.stderr)
    sys.exit(1)
PY
pass "XSS evidence escaped, only nav JS <script> outside JSON blob"

echo "== bad fixtures must fail validate-only strict (no traceback) =="
for bad in \
  bad_top_level_overview_array.json \
  bad_nested_language_percent_string.json \
  bad_nested_flow_step_int.json \
  bad_dangling_edge.json
do
  set +e
  output="$(python3 "$SCRIPTS/generate_report.py" \
    --input "$EXAMPLES/$bad" \
    --out "$OUT" \
    --validate-only \
    --strict 2>&1)"
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    fail "$bad should fail validation but exited 0"
  fi
  case "$output" in
    *Traceback*) fail "$bad produced traceback: $output" ;;
  esac
  case "$output" in
    *error:*) pass "$bad failed as expected" ;;
    *) fail "$bad failed but missing error: prefix: $output" ;;
  esac
done

echo "== duplicate section id must fail validate strict =="
cp "$HTML" "$DUP/index.html"
printf '%s\n' '<section id="overview" class="panel"><h2>Duplicate</h2></section>' >> "$DUP/index.html"
set +e
dup_out="$(python3 "$SCRIPTS/validate_report.py" "$DUP" --strict 2>&1)"
dup_status=$?
set -e
if [ "$dup_status" -eq 0 ]; then
  fail "duplicate overview section should fail strict validation"
fi
echo "$dup_out" | grep -q Traceback && fail "duplicate section test produced traceback"
echo "$dup_out" | grep -q 'section id overview must appear exactly once' \
  && pass "duplicate section rejected" \
  || fail "unexpected duplicate section output: $dup_out"

echo "== embedded JSON round-trip: tamper percent to string must fail strict =="
TAMPER="$DUP/tampered.html"
python3 - <<'PY'
import json
import re
from pathlib import Path

html_path = Path(".self_check_out/index.html")
text = html_path.read_text(encoding="utf-8")
match = re.search(
    r'<script id="report-data" type="application/json">\s*(.*?)\s*</script>',
    text,
    re.DOTALL,
)
payload = match.group(1).replace("<\\/", "</")
data = json.loads(payload)
data["overview"]["languages"][0]["percent"] = "100"
raw = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
tampered = text[: match.start(1)] + raw + text[match.end(1) :]
Path(".self_check_dup/tampered.html").write_text(tampered, encoding="utf-8")
PY
mkdir -p "$DUP/tampered"
mv "$DUP/tampered.html" "$DUP/tampered/index.html"
set +e
tamper_out="$(python3 "$SCRIPTS/validate_report.py" "$DUP/tampered" --strict 2>&1)"
tamper_status=$?
set -e
if [ "$tamper_status" -eq 0 ]; then
  fail "tampered embedded JSON should fail strict validation"
fi
echo "$tamper_out" | grep -q 'overview.languages\[0\].percent must be numeric' \
  && pass "embedded JSON strict round-trip works" \
  || fail "unexpected tamper output: $tamper_out"

rm -rf "$OUT" "$DUP"
echo "self_check: all checks passed"
