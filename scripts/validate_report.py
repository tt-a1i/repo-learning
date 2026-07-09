#!/usr/bin/env python3
"""Validate offline repo learning HTML reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from schema_validate import REQUIRED_SECTIONS, collect_errors

REPORT_DATA_SCRIPT_RE = re.compile(
    r'<script id="report-data" type="application/json">\s*(.*?)\s*</script>',
    re.DOTALL,
)
# Remote-resource risk: only flag actual remote/executable references in
# markup/CSS (src/href attributes and CSS url(...)). Plain URLs that appear
# inside embedded JSON or evidence text are NOT remote resources and must not
# be rejected. See references/report-design.md.
#
# Dangerous scheme prefix matched after src=/href= or url(: http(s)://,
# protocol-relative //, and data: (data URIs can carry executable HTML/JS).
_REMOTE_SCHEME = r'(?:https?://|//|data:)'
REMOTE_RESOURCE_PATTERNS = (
    re.compile(r'<[^>]+\b(?:src|href)\s*=\s*["\']?\s*' + _REMOTE_SCHEME, re.IGNORECASE),
    re.compile(r'url\s*\(\s*["\']?\s*' + _REMOTE_SCHEME, re.IGNORECASE),
)
FORBIDDEN_PATTERNS = (
    re.compile(r'\bTODO\b'),
    re.compile(r'\bFIXME\b'),
)


def extract_embedded_json(text: str) -> tuple[dict | None, str | None]:
    match = REPORT_DATA_SCRIPT_RE.search(text)
    if not match:
        return None, "strict mode could not extract report-data JSON"
    payload = match.group(1).replace("<\\/", "</")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, f"embedded JSON invalid: {exc}"
    if not isinstance(data, dict):
        return None, "embedded JSON root must be an object"
    return data, None


def validate_html(path: Path, strict: bool) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing index.html at {path}"]

    text = path.read_text(encoding="utf-8")

    for section_id in REQUIRED_SECTIONS:
        pattern = re.compile(rf'\bid="{re.escape(section_id)}"')
        matches = pattern.findall(text)
        count = len(matches)
        if count == 0:
            errors.append(f"missing section id: {section_id}")
        elif strict and count != 1:
            errors.append(
                f"section id {section_id} must appear exactly once (found {count})"
            )
        elif not strict and count > 1:
            print(
                f"warning: section id {section_id} appears {count} times",
                file=sys.stderr,
            )

    if 'id="report-data"' not in text:
        errors.append("missing script#report-data")

    if "<svg" not in text:
        errors.append("expected at least one inline SVG chart")

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            errors.append(f"forbidden pattern matched: {pattern.pattern}")

    for pattern in REMOTE_RESOURCE_PATTERNS:
        if pattern.search(text):
            errors.append(f"remote resource reference matched: {pattern.pattern}")

    if strict:
        if "<script" in text and 'type="application/json"' not in text:
            errors.append("strict mode expects embedded JSON in application/json script")
        data, parse_error = extract_embedded_json(text)
        if parse_error:
            errors.append(parse_error)
        elif data is not None:
            errors.extend(collect_errors(data, strict=True))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate repo learning HTML report")
    parser.add_argument("report_dir", help="Directory containing index.html")
    parser.add_argument("--strict", action="store_true", help="Enable strict checks")
    args = parser.parse_args(argv)

    report_dir = Path(args.report_dir)
    index_path = report_dir / "index.html"
    errors = validate_html(index_path, strict=args.strict)

    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    print("validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
