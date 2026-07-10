#!/usr/bin/env python3
"""Validate generated repo-learning websites without dictating their layout."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from schema_validate import collect_errors


SITE_DATA_RE = re.compile(
    r'<script id="site-data" type="application/json">\s*(.*?)\s*</script>',
    re.DOTALL,
)
REMOTE_ASSET_PATTERNS = (
    re.compile(r'<(?:script|img|iframe|source|video|audio)[^>]+\bsrc\s*=\s*["\']?\s*(?:https?://|//|data:)', re.IGNORECASE),
    re.compile(r'<link[^>]+\bhref\s*=\s*["\']?\s*(?:https?://|//|data:)', re.IGNORECASE),
)
REMOTE_CSS_URL_RE = re.compile(
    r'url\s*\(\s*["\']?\s*(?:https?://|//|data:)', re.IGNORECASE
)


def extract_site_data(source: str) -> tuple[dict | None, str | None]:
    matches = SITE_DATA_RE.findall(source)
    if len(matches) != 1:
        return None, f"site-data script must appear exactly once (found {len(matches)})"
    payload = matches[0].replace("<\\/", "</")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, f"embedded site-data JSON is invalid: {exc}"
    if not isinstance(data, dict):
        return None, "embedded site-data root must be an object"
    return data, None


def validate_html(path: Path, strict: bool) -> list[str]:
    if not path.is_file():
        return [f"missing index.html at {path}"]
    source = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for fragment, message in (
        ("<!doctype html>", "missing HTML doctype"),
        ('<meta name="viewport"', "missing viewport metadata"),
        ('id="main"', "missing main content landmark"),
        ("<h1>", "missing project heading"),
        ('class="site-header"', "missing site navigation"),
    ):
        if fragment.lower() not in source.lower():
            errors.append(message)

    if not re.search(r'class="[^"]*\bhero\b', source):
        errors.append("missing project hero")

    if not re.search(r'<section\b[^>]*class="[^"]*story-section', source):
        errors.append("expected at least one learning story section")
    markup_without_data = SITE_DATA_RE.sub("", source)
    for pattern in REMOTE_ASSET_PATTERNS:
        if pattern.search(markup_without_data):
            errors.append(f"remote executable asset matched: {pattern.pattern}")
    for style in re.findall(r"<style\b[^>]*>(.*?)</style>", markup_without_data, re.I | re.S):
        if REMOTE_CSS_URL_RE.search(style):
            errors.append(f"remote executable asset matched: {REMOTE_CSS_URL_RE.pattern}")

    data, data_error = extract_site_data(source)
    if data_error:
        errors.append(data_error)
    elif strict and data is not None:
        errors.extend(collect_errors(data, strict=True))

    if strict:
        section_ids = re.findall(r'<section\b[^>]*\bid="([^"]+)"', source)
        duplicates = sorted({item for item in section_ids if section_ids.count(item) > 1})
        if duplicates:
            errors.append("duplicate section ids: " + ", ".join(duplicates))

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a repo-learning website")
    parser.add_argument("report_dir", help="Directory containing index.html")
    parser.add_argument("--strict", action="store_true", help="Enable strict data and document-structure checks")
    args = parser.parse_args(argv)
    errors = validate_html(Path(args.report_dir) / "index.html", strict=args.strict)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
