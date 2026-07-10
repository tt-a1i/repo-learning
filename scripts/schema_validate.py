#!/usr/bin/env python3
"""Shared JSON schema validation for repo-learning report_data v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "2"
REQUIRED_TOP = ("schema_version", "meta", "overview", "modules")


def _type_label(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    return type(value).__name__


def _expect_dict(errors: list[str], value: Any, path: str) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object, got {_type_label(value)}")
        return None
    return value


def _expect_list(errors: list[str], value: Any, path: str) -> list[Any] | None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array, got {_type_label(value)}")
        return None
    return value


def _validate_numeric(errors: list[str], value: Any, path: str, *, required: bool = False) -> None:
    if value is None:
        if required:
            errors.append(f"{path} must be numeric")
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"{path} must be numeric, got {_type_label(value)}")


def _validate_string_or_object_items(
    errors: list[str],
    items: list[Any],
    path: str,
) -> None:
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if isinstance(item, str):
            continue
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object or string, got {_type_label(item)}")
            continue
        evidence = item.get("evidence")
        if evidence is not None and not isinstance(evidence, (str, list)):
            errors.append(
                f"{item_path}.evidence must be a string or array, got {_type_label(evidence)}"
            )


def _validate_languages(
    errors: list[str], languages: list[Any], base_path: str = "overview.languages"
) -> None:
    for index, lang in enumerate(languages):
        path = f"{base_path}[{index}]"
        if not isinstance(lang, dict):
            errors.append(f"{path} must be an object, got {_type_label(lang)}")
            continue
        name = lang.get("name")
        if name is not None and not isinstance(name, str):
            errors.append(f"{path}.name must be a string, got {_type_label(name)}")
        if "percent" in lang:
            _validate_numeric(errors, lang.get("percent"), f"{path}.percent", required=True)


def _validate_flows_nested(errors: list[str], flows: list[Any]) -> None:
    for flow_index, flow in enumerate(flows):
        path = f"flows[{flow_index}]"
        if not isinstance(flow, dict):
            errors.append(f"{path} must be an object, got {_type_label(flow)}")
            continue
        steps = flow.get("steps")
        if steps is None:
            continue
        steps_list = _expect_list(errors, steps, f"{path}.steps")
        if steps_list is None:
            continue
        for step_index, step in enumerate(steps_list):
            step_path = f"{path}.steps[{step_index}]"
            if isinstance(step, str):
                continue
            if not isinstance(step, dict):
                errors.append(
                    f"{step_path} must be an object or string, got {_type_label(step)}"
                )
                continue
            evidence = step.get("evidence")
            if evidence is not None and not isinstance(evidence, (str, list)):
                errors.append(
                    f"{step_path}.evidence must be a string or array, got {_type_label(evidence)}"
                )


def _validate_risks_nested(errors: list[str], risks: list[Any]) -> None:
    for index, risk in enumerate(risks):
        path = f"risks[{index}]"
        if not isinstance(risk, dict):
            errors.append(f"{path} must be an object, got {_type_label(risk)}")
            continue
        severity = risk.get("severity")
        if severity is not None and not isinstance(severity, str):
            errors.append(f"{path}.severity must be a string, got {_type_label(severity)}")


def _validate_test_matrix_nested(errors: list[str], matrix: list[Any]) -> None:
    for index, row in enumerate(matrix):
        path = f"tests.matrix[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{path} must be an object, got {_type_label(row)}")
            continue
        area = row.get("area")
        if area is not None and not isinstance(area, str):
            errors.append(f"{path}.area must be a string, got {_type_label(area)}")
        for flag in ("unit", "integration", "e2e"):
            value = row.get(flag)
            if value is not None and not isinstance(value, bool):
                errors.append(f"{path}.{flag} must be a boolean, got {_type_label(value)}")


def _validate_roadmap_nested(errors: list[str], roadmap: list[Any]) -> None:
    for index, phase in enumerate(roadmap):
        path = f"roadmap[{index}]"
        if not isinstance(phase, dict):
            errors.append(f"{path} must be an object, got {_type_label(phase)}")
            continue
        phase_no = phase.get("phase")
        if phase_no is not None and (
            isinstance(phase_no, bool) or not isinstance(phase_no, (int, float))
        ):
            errors.append(f"{path}.phase must be numeric, got {_type_label(phase_no)}")
        items = phase.get("items")
        if items is not None:
            items_list = _expect_list(errors, items, f"{path}.items")
            if items_list is not None:
                _validate_string_or_object_items(errors, items_list, f"{path}.items")


def _validate_external_deps(errors: list[str], external: list[Any]) -> None:
    for index, dep in enumerate(external):
        path = f"dependencies.external[{index}]"
        if not isinstance(dep, dict):
            errors.append(f"{path} must be an object, got {_type_label(dep)}")
            continue
        name = dep.get("name")
        if name is not None and not isinstance(name, str):
            errors.append(f"{path}.name must be a string, got {_type_label(name)}")


def _validate_appendix_nested(errors: list[str], appendix: dict[str, Any]) -> None:
    for field in ("gaps", "open_questions", "files_examined"):
        value = appendix.get(field)
        if value is None:
            continue
        items = _expect_list(errors, value, f"appendix.{field}")
        if items is not None:
            _validate_string_or_object_items(errors, items, f"appendix.{field}")


def _validate_edges(errors: list[str], field: str, edges: list[Any], module_ids: set[str]) -> None:
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"{field}[{index}] must be an object, got {_type_label(edge)}")
            continue
        src = edge.get("from")
        dst = edge.get("to")
        for endpoint, label in ((src, "from"), (dst, "to")):
            if not isinstance(endpoint, str) or not endpoint:
                errors.append(f"{field} edge[{index}] missing string {label}")
            elif endpoint not in module_ids:
                errors.append(
                    f"{field} edge[{index}] dangling module id '{endpoint}' in {label}"
                )


def _collect_v1_errors(data: dict[str, Any], strict: bool) -> list[str]:
    errors: list[str] = []

    if data.get("schema_version") != "1":
        errors.append("schema_version must be '1'")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level field: {key}")

    meta = data.get("meta", {})
    if not isinstance(meta, dict):
        errors.append(f"meta must be an object, got {_type_label(meta)}")
        meta = {}

    for field in ("repo_name", "repo_path"):
        if strict and not meta.get(field):
            errors.append(f"meta.{field} is required in --strict mode")

    modules_raw = data.get("modules", [])
    modules = _expect_list(errors, modules_raw, "modules")
    if modules is None:
        modules = []

    module_ids: set[str] = set()
    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            errors.append(f"modules[{index}] must be an object, got {_type_label(module)}")
            continue
        mid = module.get("id")
        if not mid:
            errors.append(f"modules[{index}] missing id")
            continue
        if mid in module_ids:
            errors.append(f"duplicate module id: {mid}")
        module_ids.add(str(mid))
        if strict and not module.get("evidence"):
            errors.append(f"modules[{index}] ({mid}) missing evidence in --strict mode")

    overview_raw = data.get("overview")
    overview = _expect_dict(errors, overview_raw, "overview") if "overview" in data else None
    if overview is not None:
        languages = overview.get("languages")
        if languages is not None:
            languages_list = _expect_list(errors, languages, "overview.languages")
            if languages_list is not None:
                _validate_languages(errors, languages_list)

        claims = overview.get("claims")
        if claims is not None:
            claims_list = _expect_list(errors, claims, "overview.claims")
            if claims_list is not None:
                _validate_string_or_object_items(errors, claims_list, "overview.claims")
                if strict and not claims_list:
                    errors.append("overview.claims must be non-empty in --strict mode")
                if strict:
                    for index, claim in enumerate(claims_list):
                        if isinstance(claim, dict) and not claim.get("evidence"):
                            errors.append(
                                f"overview.claims[{index}] missing evidence in --strict mode"
                            )
        elif strict:
            errors.append("overview.claims must be non-empty in --strict mode")

    if "topology" in data:
        topology = _expect_dict(errors, data["topology"], "topology")
        if topology is not None:
            edges = topology.get("edges")
            if edges is None:
                edges = []
            edges_list = _expect_list(errors, edges, "topology.edges")
            if edges_list is not None:
                _validate_edges(errors, "topology.edges", edges_list, module_ids)

    if "dependencies" in data:
        dependencies = _expect_dict(errors, data["dependencies"], "dependencies")
        if dependencies is not None:
            internal = dependencies.get("internal")
            if internal is not None:
                internal_list = _expect_list(errors, internal, "dependencies.internal")
                if internal_list is not None:
                    _validate_edges(errors, "dependencies.internal", internal_list, module_ids)
            external = dependencies.get("external")
            if external is not None:
                external_list = _expect_list(errors, external, "dependencies.external")
                if external_list is not None:
                    _validate_external_deps(errors, external_list)

    if "flows" in data:
        flows = _expect_list(errors, data["flows"], "flows")
        if flows is not None:
            _validate_flows_nested(errors, flows)

    if "risks" in data:
        risks = _expect_list(errors, data["risks"], "risks")
        if risks is not None:
            _validate_risks_nested(errors, risks)

    if "tests" in data:
        tests = _expect_dict(errors, data["tests"], "tests")
        if tests is not None:
            matrix = tests.get("matrix")
            if matrix is not None:
                matrix_list = _expect_list(errors, matrix, "tests.matrix")
                if matrix_list is not None:
                    _validate_test_matrix_nested(errors, matrix_list)

    if "roadmap" in data:
        roadmap = _expect_list(errors, data["roadmap"], "roadmap")
        if roadmap is not None:
            _validate_roadmap_nested(errors, roadmap)

    if "appendix" in data:
        appendix = _expect_dict(errors, data["appendix"], "appendix")
        if appendix is not None:
            _validate_appendix_nested(errors, appendix)
            if strict:
                gaps = appendix.get("gaps")
                if gaps is not None:
                    gaps_list = _expect_list(errors, gaps, "appendix.gaps")
                    if gaps_list is not None and not gaps_list:
                        errors.append("appendix.gaps should document unknowns in --strict mode")
                elif not appendix.get("gaps"):
                    errors.append("appendix.gaps should document unknowns in --strict mode")

    return errors


def _check_evidence(errors: list[str], value: Any, path: str) -> None:
    if value is None:
        return
    if isinstance(value, str):
        return
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return
    errors.append(f"{path} must be a string or array of strings")


def _collect_v2_errors(data: dict[str, Any], strict: bool) -> list[str]:
    """Validate the intentionally small v2 storytelling contract.

    V2 validates identity and graph integrity. It deliberately does not force a
    fixed set of website sections: the available repository story decides what
    the generator renders.
    """
    errors: list[str] = []
    if data.get("schema_version") != "2":
        errors.append("schema_version must be '2'")

    project = data.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
        project = {}
    for field in ("name", "source"):
        if strict and not project.get(field):
            errors.append(f"project.{field} is required in --strict mode")
    if strict and not (project.get("tagline") or project.get("summary")):
        errors.append("project.tagline or project.summary is required in --strict mode")

    languages = data.get("languages", [])
    if not isinstance(languages, list):
        errors.append("languages must be an array")
        languages = []
    _validate_languages(errors, languages, "languages")

    modules = data.get("modules", [])
    if not isinstance(modules, list):
        errors.append("modules must be an array")
        modules = []
    module_ids: set[str] = set()
    for index, module in enumerate(modules):
        path = f"modules[{index}]"
        if not isinstance(module, dict):
            errors.append(f"{path} must be an object")
            continue
        module_id = module.get("id")
        if not isinstance(module_id, str) or not module_id:
            errors.append(f"{path}.id is required")
            continue
        if module_id in module_ids:
            errors.append(f"duplicate module id: {module_id}")
        module_ids.add(module_id)
        _check_evidence(errors, module.get("evidence"), f"{path}.evidence")

    connections = data.get("connections", [])
    if not isinstance(connections, list):
        errors.append("connections must be an array")
        connections = []
    _validate_edges(errors, "connections", connections, module_ids)
    for index, connection in enumerate(connections):
        if isinstance(connection, dict):
            _check_evidence(errors, connection.get("evidence"), f"connections[{index}].evidence")

    list_sections = {
        "highlights": (str, dict),
        "concepts": (dict,),
        "flows": (dict,),
        "code_map": (dict,),
        "learning_path": (dict,),
        "risks": (dict,),
        "quick_start": (str, dict),
        "external_dependencies": (dict,),
        "gaps": (str, dict),
    }
    meaningful_count = len(modules)
    for field, accepted in list_sections.items():
        value = data.get(field, [])
        if not isinstance(value, list):
            errors.append(f"{field} must be an array")
            continue
        meaningful_count += len(value)
        for index, item in enumerate(value):
            if not isinstance(item, accepted):
                names = " or ".join(kind.__name__ for kind in accepted)
                errors.append(f"{field}[{index}] must be {names}")
                continue
            if isinstance(item, dict):
                _check_evidence(errors, item.get("evidence"), f"{field}[{index}].evidence")

    _validate_flows_nested(errors, data.get("flows", []) if isinstance(data.get("flows", []), list) else [])
    _validate_risks_nested(errors, data.get("risks", []) if isinstance(data.get("risks", []), list) else [])

    tests = data.get("tests", {})
    if not isinstance(tests, dict):
        errors.append("tests must be an object")
    else:
        matrix = tests.get("matrix", [])
        if not isinstance(matrix, list):
            errors.append("tests.matrix must be an array")
        else:
            _validate_test_matrix_nested(errors, matrix)

    learning_path = data.get("learning_path", [])
    if isinstance(learning_path, list):
        for index, step in enumerate(learning_path):
            if not isinstance(step, dict):
                continue
            for field in ("items", "files"):
                value = step.get(field)
                if value is None:
                    continue
                items = _expect_list(errors, value, f"learning_path[{index}].{field}")
                if items is not None:
                    _validate_string_or_object_items(
                        errors, items, f"learning_path[{index}].{field}"
                    )

    if strict and meaningful_count == 0:
        errors.append("strict mode requires at least one learning section")
    return errors


def collect_errors(data: dict[str, Any], strict: bool) -> list[str]:
    version = data.get("schema_version")
    if version == "1":
        return _collect_v1_errors(data, strict)
    if version == "2":
        return _collect_v2_errors(data, strict)
    return ["schema_version must be '1' or '2'"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate repo-learning site data")
    parser.add_argument("input", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("error: top-level JSON must be an object", file=sys.stderr)
        return 1
    errors = collect_errors(data, strict=args.strict)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print("schema validation ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
