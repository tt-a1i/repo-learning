#!/usr/bin/env python3
"""Evaluate whether site data can teach a repository rather than merely describe it."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from schema_validate import collect_errors


GENERIC = {
    "todo", "tbd", "a software project", "this project",
    "helps users", "modern application", "powerful tool",
}


def items(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def has_evidence(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    evidence = value.get("evidence")
    if bool(evidence) and (isinstance(evidence, str) or isinstance(evidence, list)):
        return True
    return isinstance(value.get("path"), str) and bool(value.get("path"))


def evidence_ratio(values: list[Any]) -> float:
    candidates = [value for value in values if isinstance(value, dict)]
    return sum(has_evidence(value) for value in candidates) / len(candidates) if candidates else 0.0


def evidence_values(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    evidence = value.get("evidence")
    if isinstance(evidence, str):
        return [evidence]
    if isinstance(evidence, list):
        return [item for item in evidence if isinstance(item, str)]
    return []


def evidence_path(raw: str) -> str:
    candidate = raw.strip()
    match = re.match(r"^(.*?):(?:L)?\d+(?:-\d+)?$", candidate)
    return match.group(1) if match else candidate


def validate_source_paths(data: dict[str, Any], repo: Path) -> list[str]:
    errors: list[str] = []
    root = repo.expanduser().resolve()
    if not root.is_dir():
        return [f"repository does not exist: {root}"]

    checks: list[tuple[str, str]] = []
    for field in ("modules", "connections", "concepts", "risks"):
        for index, value in enumerate(items(data, field)):
            checks.extend((f"{field}[{index}].evidence", raw) for raw in evidence_values(value))
    for flow_index, flow in enumerate(items(data, "flows")):
        if not isinstance(flow, dict):
            continue
        steps = flow.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step_index, step in enumerate(steps):
            checks.extend(
                (f"flows[{flow_index}].steps[{step_index}].evidence", raw)
                for raw in evidence_values(step)
            )
    for index, value in enumerate(items(data, "code_map")):
        if isinstance(value, dict) and isinstance(value.get("path"), str):
            checks.append((f"code_map[{index}].path", value["path"]))
        checks.extend((f"code_map[{index}].evidence", raw) for raw in evidence_values(value))

    for label, raw in checks:
        rel = evidence_path(raw)
        if not rel or rel.startswith(("http://", "https://")):
            errors.append(f"{label} must point to a file inside the repository: {raw}")
            continue
        candidate = (root / rel).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            errors.append(f"{label} does not resolve to a repository file: {raw}")
    return errors


def evaluate(data: dict[str, Any], repo: Path | None = None) -> tuple[int, list[str], list[str]]:
    failures = collect_errors(data, strict=True)
    warnings: list[str] = []
    score = 100
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    copy = " ".join(str(project.get(key, "")) for key in ("tagline", "summary")).lower()
    if len(copy.strip()) < 80:
        score -= 15
        warnings.append("project story is too thin; write a concrete tagline and mental model")
    if any(phrase in copy for phrase in GENERIC):
        score -= 20
        warnings.append("project story contains placeholder or generic product language")

    modules, connections = items(data, "modules"), items(data, "connections")
    for index, connection in enumerate(connections):
        if not evidence_values(connection):
            failures.append(f"connections[{index}].evidence is required for a traceable architecture edge")
    code_map = items(data, "code_map")
    if not modules and not code_map:
        score -= 20
        warnings.append("neither a system skeleton nor a code-entry map is present")
    if len(modules) >= 3 and len(connections) < max(1, len(modules) // 2):
        score -= 15
        warnings.append("architecture relationships are too sparse for the module count")

    flows = items(data, "flows")
    for flow_index, flow in enumerate(flows):
        if not isinstance(flow, dict) or not isinstance(flow.get("steps"), list):
            continue
        for step_index, step in enumerate(flow["steps"]):
            if not evidence_values(step):
                failures.append(
                    f"flows[{flow_index}].steps[{step_index}].evidence is required for a traceable flow"
                )
    valid_flows = [flow for flow in flows if isinstance(flow, dict) and len(flow.get("steps", [])) >= 3]
    concepts = items(data, "concepts")
    if not valid_flows and len(concepts) < 2:
        score -= 20
        warnings.append("no deep runtime flow or project-specific concept model is present")

    if len(code_map) < 2:
        score -= 15
        warnings.append("code map has fewer than two high-value reading entrypoints")
    if len(items(data, "learning_path")) < 2:
        score -= 10
        warnings.append("learning path has fewer than two outcome-oriented steps")

    teaching_sections = sum(
        bool(items(data, key))
        for key in ("modules", "flows", "concepts", "code_map", "learning_path")
    )
    tests = data.get("tests")
    teaching_sections += int(isinstance(tests, dict) and bool(tests))
    if teaching_sections < 3:
        score -= 15
        warnings.append("fewer than three complementary teaching views are present")

    evidence_items = modules + connections + [
        step
        for flow in flows if isinstance(flow, dict)
        for step in flow.get("steps", []) if isinstance(flow.get("steps", []), list)
    ] + concepts + code_map
    ratio = evidence_ratio(evidence_items)
    if ratio < 0.6:
        score -= 15
        warnings.append(f"only {ratio:.0%} of architecture, flow, concept, and code items carry evidence")

    gaps = items(data, "gaps")
    if score < 80 and not gaps:
        score -= 5
        warnings.append("thin sections are not explained by explicit investigation gaps")
    if repo is not None:
        failures.extend(validate_source_paths(data, repo))
    return max(0, score), failures, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check repo-learning content depth")
    parser.add_argument("input", type=Path)
    parser.add_argument("--repo", type=Path, help="Verify evidence paths against this repository")
    parser.add_argument("--strict", action="store_true", help="Fail below --minimum")
    parser.add_argument("--minimum", type=int, default=70)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("error: top-level JSON must be an object", file=sys.stderr)
        return 1
    score, failures, warnings = evaluate(data, repo=args.repo)
    for failure in failures:
        print(f"error: {failure}", file=sys.stderr)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if failures:
        print(f"quality score: invalid ({len(failures)} hard error(s))")
    else:
        print(f"quality score: {score}/100")
    if failures or (args.strict and score < args.minimum):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
