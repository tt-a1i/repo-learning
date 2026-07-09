#!/usr/bin/env python3
"""Generate offline self-contained HTML repo learning reports from JSON."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schema_validate import collect_errors

SEVERITY_COLORS = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
SEVERITY_SYM = {"high": "▲", "medium": "◆", "low": "●"}
# Swimlane order by module kind (unknown kinds land in "other").
LANE_ORDER = ("entry", "ui", "frontend", "service", "backend", "domain", "lib", "data", "database", "external", "test", "config", "other")
LANE_KIND_GROUP = {
    "entry": "entry", "ui": "entry", "frontend": "entry",
    "service": "service", "backend": "service",
    "domain": "domain", "lib": "domain",
    "data": "data", "database": "data", "external": "data",
    "test": "test", "config": "test", "other": "other",
}
RISK_CATEGORIES = ("security", "complexity", "test", "ops", "unknown")
TEST_STATUS_ORDER = {"missing": 0, "unknown": 1, "partial": 2, "covered": 3}
TEST_SYM = {True: "✓", False: "✗", None: "?"}
TEST_LABEL = {True: "yes", False: "no", None: "?"}
MODULE_CAP = 24
RISK_CAP = 30
TEST_CAP = 24
ROADMAP_CAP = 12
EXTERNAL_CAP = 12

# UI copy: default Chinese unless --lang / meta.locale requests English.
UI = {
    "zh": {
        "html_lang": "zh-CN",
        "default_title": "仓库学习简报",
        "eyebrow": "仓库简报",
        "screenshot": "截图模式",
        "confidence": "置信度",
        "evidence": "证据",
        "sections_aria": "章节",
        "filter_aria": "按{group}筛选",
        "drawer_aria": "证据详情",
        "close": "关闭",
        "kpi_modules": "模块",
        "kpi_internal": "内部依赖",
        "kpi_high_risks": "高风险",
        "kpi_tests_missing": "缺测试",
        "kpi_gaps": "缺口",
        "kpi_flows": "流程",
        "toc_overview": "总览",
        "toc_topology": "拓扑",
        "toc_deps": "依赖",
        "toc_flows": "流程",
        "toc_risks": "风险",
        "toc_tests": "测试",
        "toc_path": "路径",
        "toc_appendix": "附录",
        "ch_overview": "总览",
        "ch_overview_dek": "这个仓库是什么，以及依据。",
        "ch_topology": "拓扑",
        "ch_topology_dek": "模块划分与连接关系。",
        "ch_deps": "依赖",
        "ch_deps_dek": "内部边与外部表面。",
        "ch_flows": "流程",
        "ch_flows_dek": "关键运行时路径。",
        "ch_risks": "风险",
        "ch_risks_dek": "哪里可能出问题。",
        "ch_tests": "测试与 CI",
        "ch_tests_dek": "覆盖了什么，缺了什么。",
        "ch_roadmap": "学习路径",
        "ch_roadmap_dek": "按这个顺序读。",
        "ch_appendix": "附录",
        "ch_appendix_dek": "缺口、待决问题与已读文件。",
        "languages": "语言",
        "external": "外部依赖",
        "gaps": "缺口",
        "open_questions": "待决问题",
        "files_examined": "已读文件",
        "legend_module": "模块",
        "legend_edge": "边",
        "legend_internal": "内部依赖",
        "legend_external": "外部依赖",
        "legend_high": "高",
        "legend_medium": "中",
        "legend_low": "低",
        "legend_covered": "已覆盖",
        "legend_missing": "缺失",
        "legend_unknown": "未知",
        "filter_high": "高",
        "filter_medium": "中",
        "filter_low": "低",
        "filter_all": "全部",
        "sev_high": "高",
        "sev_medium": "中",
        "sev_low": "低",
        "cat_security": "安全",
        "cat_complexity": "复杂度",
        "cat_test": "测试",
        "cat_ops": "运维",
        "cat_unknown": "未知",
        "global_unknown": "全局/未知",
        "phase": "阶段 {n}",
        "risk": "风险",
        "flow": "流程",
        "module": "模块",
        "th_area": "区域",
        "th_unit": "单元",
        "th_integration": "集成",
        "th_e2e": "端到端",
        "yes": "是",
        "no": "否",
        "unknown": "未知",
        "empty_items": "暂无条目。",
        "empty_modules": "暂无模块记录。",
        "empty_risks": "暂无风险记录。",
        "empty_flows": "暂无流程。请在 flows[] 中补充 title 与 steps[]。",
        "empty_tests": "暂无测试矩阵。请在 tests.matrix[] 中补充。",
        "empty_roadmap": "暂无学习路径。请在 roadmap[] 中补充。",
        "empty_lang": "暂无语言数据",
        "empty_lang_hint": "在 overview.languages[] 中补充 name、percent、evidence。",
        "empty_topo": "暂无模块记录",
        "empty_topo_hint": "在 modules[] 中补充 id、name、kind、evidence。",
        "empty_deps": "暂无依赖记录",
        "empty_deps_hint": "在 dependencies.internal/external 中补充。",
        "empty_risks_svg": "暂无风险记录",
        "empty_risks_hint": "在 risks[] 中补充 title、severity、category、module_id。",
        "aria_lang": "语言分布",
        "aria_topo": "模块拓扑",
        "aria_deps": "依赖泳道",
        "aria_risks": "风险矩阵（模块 × 类别）",
        "more_modules": "+{n} 个模块未显示",
        "more_risks": "+{n} 条风险未显示",
        "more_tests": "+{n} 个测试区域未显示",
        "more_external": "+{n} 个外部依赖未显示",
        "more_phases": "+{n} 个阶段未显示",
        "lane_entry": "入口/界面",
        "lane_service": "服务/后端",
        "lane_domain": "领域/库",
        "lane_data": "数据/存储",
        "lane_test": "测试/配置",
        "lane_other": "其他",
        "sec_overview": "总览",
        "sec_topology": "拓扑",
        "sec_deps": "依赖",
        "sec_flows": "流程",
        "sec_risks": "风险",
        "sec_roadmap": "学习路径",
        "sec_appendix_gaps": "附录 · 缺口",
        "sec_appendix_q": "附录 · 待决问题",
        "sec_appendix_files": "附录 · 已读文件",
    },
    "en": {
        "html_lang": "en",
        "default_title": "Repo Learning Report",
        "eyebrow": "Repo brief",
        "screenshot": "Screenshot mode",
        "confidence": "confidence",
        "evidence": "evidence",
        "sections_aria": "Sections",
        "filter_aria": "Filter by {group}",
        "drawer_aria": "Evidence details",
        "close": "Close",
        "kpi_modules": "Modules",
        "kpi_internal": "Internal deps",
        "kpi_high_risks": "High risks",
        "kpi_tests_missing": "Tests missing",
        "kpi_gaps": "Gaps",
        "kpi_flows": "Flows",
        "toc_overview": "Overview",
        "toc_topology": "Topology",
        "toc_deps": "Deps",
        "toc_flows": "Flows",
        "toc_risks": "Risks",
        "toc_tests": "Tests",
        "toc_path": "Path",
        "toc_appendix": "Appendix",
        "ch_overview": "Overview",
        "ch_overview_dek": "What this repo is, with evidence.",
        "ch_topology": "Topology",
        "ch_topology_dek": "Modules and how they connect.",
        "ch_deps": "Dependencies",
        "ch_deps_dek": "Internal edges and external surface.",
        "ch_flows": "Flows",
        "ch_flows_dek": "Critical runtime paths.",
        "ch_risks": "Risks",
        "ch_risks_dek": "Where it can break.",
        "ch_tests": "Tests & CI",
        "ch_tests_dek": "What is covered — and what is not.",
        "ch_roadmap": "Learning path",
        "ch_roadmap_dek": "Read in this order.",
        "ch_appendix": "Appendix",
        "ch_appendix_dek": "Gaps, questions, files examined.",
        "languages": "Languages",
        "external": "External",
        "gaps": "Gaps",
        "open_questions": "Open questions",
        "files_examined": "Files examined",
        "legend_module": "module",
        "legend_edge": "edge",
        "legend_internal": "internal",
        "legend_external": "external",
        "legend_high": "high",
        "legend_medium": "medium",
        "legend_low": "low",
        "legend_covered": "covered",
        "legend_missing": "missing",
        "legend_unknown": "unknown",
        "filter_high": "high",
        "filter_medium": "medium",
        "filter_low": "low",
        "filter_all": "all",
        "sev_high": "high",
        "sev_medium": "medium",
        "sev_low": "low",
        "cat_security": "security",
        "cat_complexity": "complexity",
        "cat_test": "test",
        "cat_ops": "ops",
        "cat_unknown": "unknown",
        "global_unknown": "global/unknown",
        "phase": "Phase {n}",
        "risk": "Risk",
        "flow": "Flow",
        "module": "module",
        "th_area": "Area",
        "th_unit": "Unit",
        "th_integration": "Integration",
        "th_e2e": "E2E",
        "yes": "yes",
        "no": "no",
        "unknown": "unknown",
        "empty_items": "No items recorded.",
        "empty_modules": "No modules recorded.",
        "empty_risks": "No risks recorded.",
        "empty_flows": "No flows documented. Add flows[] with title, steps[].",
        "empty_tests": "No test matrix recorded. Add tests.matrix[] with area, unit, integration, e2e, evidence.",
        "empty_roadmap": "No roadmap phases. Add roadmap[] with phase, title, items.",
        "empty_lang": "No language data",
        "empty_lang_hint": "Add overview.languages[] with name, percent, evidence.",
        "empty_topo": "No modules recorded",
        "empty_topo_hint": "Add modules[] with id, name, kind, evidence.",
        "empty_deps": "No dependencies recorded",
        "empty_deps_hint": "Add dependencies.internal/external.",
        "empty_risks_svg": "No risks recorded",
        "empty_risks_hint": "Add risks[] with title, severity, category, module_id.",
        "aria_lang": "Language breakdown",
        "aria_topo": "Module topology",
        "aria_deps": "Dependency swimlane",
        "aria_risks": "Risk matrix (module × category)",
        "more_modules": "+{n} more modules not shown",
        "more_risks": "+{n} more risks not shown",
        "more_tests": "+{n} more test areas not shown",
        "more_external": "+{n} more external deps",
        "more_phases": "+{n} more phases not shown",
        "lane_entry": "Entry/UI",
        "lane_service": "Service/Backend",
        "lane_domain": "Domain/Lib",
        "lane_data": "Data/Database",
        "lane_test": "Test/Config",
        "lane_other": "Other",
        "sec_overview": "Overview",
        "sec_topology": "Topology",
        "sec_deps": "Dependencies",
        "sec_flows": "Flows",
        "sec_risks": "Risks",
        "sec_roadmap": "Roadmap",
        "sec_appendix_gaps": "Appendix · Gaps",
        "sec_appendix_q": "Appendix · Open questions",
        "sec_appendix_files": "Appendix · Files examined",
    },
}


def resolve_lang(explicit: str | None = None, meta: dict[str, Any] | None = None) -> str:
    """Default zh. English only when explicitly requested."""
    candidates = [explicit or "", (meta or {}).get("locale") or "", (meta or {}).get("lang") or ""]
    for raw in candidates:
        s = str(raw).strip().lower().replace("_", "-")
        if not s:
            continue
        if s in ("en", "en-us", "en-gb", "english"):
            return "en"
        if s in ("zh", "zh-cn", "zh-hans", "zh-tw", "zh-hant", "chinese", "cn"):
            return "zh"
    return "zh"


def ui(lang: str) -> dict[str, str]:
    return UI["en" if lang == "en" else "zh"]


def t(lang: str, key: str, **kwargs: Any) -> str:
    table = ui(lang)
    text = table.get(key) or UI["zh"].get(key) or key
    return text.format(**kwargs) if kwargs else text



def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def json_for_script(data: dict[str, Any]) -> str:
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    return raw.replace("</", "<\\/")


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def module_kind(module: dict[str, Any]) -> str:
    k = _as_str(module.get("kind")).lower().strip()
    return k if k in LANE_ORDER else "other"


def lane_for_kind(kind: str, lang: str = "zh") -> str:
    group = LANE_KIND_GROUP.get(kind, "other")
    key = {
        "entry": "lane_entry",
        "service": "lane_service",
        "domain": "lane_domain",
        "data": "lane_data",
        "test": "lane_test",
        "other": "lane_other",
    }[group]
    return t(lang, key)


def module_id_of(item: Any) -> str:
    if isinstance(item, dict):
        return _as_str(item.get("module_id") or item.get("module") or "")
    return ""


def risk_row_id(risk: dict[str, Any], module_ids: list[str]) -> str:
    """Map a risk to its matrix row id.

    Known module_id → that module's row. Empty OR unknown module_id → the
    global/unknown row. Centralises this so the ternary-precedence bug that
    silently dropped unknown-module risks cannot recur.
    """
    mid = module_id_of(risk)
    return mid if mid in module_ids else "__global__"


def risk_category(risk: dict[str, Any]) -> str:
    c = _as_str(risk.get("category")).lower().strip()
    return c if c in RISK_CATEGORIES else "unknown"


def risk_severity(risk: dict[str, Any]) -> str:
    s = _as_str(risk.get("severity")).lower().strip()
    return s if s in SEVERITY_COLORS else "medium"


def svg_language_bars(languages: list[dict[str, Any]], lang: str = "zh") -> str:
    if not languages:
        return _empty_svg(t(lang, "empty_lang"), t(lang, "empty_lang_hint"))

    width, row_h, pad = 720, 34, 10
    height = pad * 2 + row_h * len(languages)
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(t(lang, "aria_lang"))}">'
    ]
    max_pct = max(float(lang.get("percent") or 0) for lang in languages) or 1
    for index, lang in enumerate(languages):
        y = pad + index * row_h
        pct = float(lang.get("percent") or 0)
        bar_w = max(4, int((pct / max_pct) * 420))
        name = esc(lang.get("name", "unknown"))
        parts.append(f'<text x="8" y="{y + 20}" class="svg-label">{name}</text>')
        parts.append(f'<rect x="150" y="{y + 8}" width="420" height="14" rx="2" class="bar-track"/>')
        parts.append(
            f'<rect x="150" y="{y + 8}" width="{bar_w}" height="14" rx="2" class="bar-fill"/>'
        )
        parts.append(f'<text x="{580}" y="{y + 20}" class="svg-muted">{pct:g}%</text>')
    parts.append("</svg>")
    return "".join(parts)


def _hue_for(text: str) -> int:
    """Deterministic accent hue (0-359) from repo name/path."""
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % 360
    return h


def _layout_modules(modules: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    """Grid layout with room for readable labels (node width 148)."""
    n = len(modules)
    cols = 1 if n <= 2 else (2 if n <= 6 else 3)
    positions: dict[str, tuple[int, int]] = {}
    for index, module in enumerate(modules):
        row, col = divmod(index, cols)
        positions[str(module.get("id"))] = (36 + col * 230, 48 + row * 88)
    return positions


def _short_label(text: str, max_len: int = 18) -> str:
    s = _as_str(text).strip() or "?"
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _empty_svg(label: str, hint: str = "") -> str:
    hint_xml = f'<text x="12" y="48" class="svg-muted">{esc(hint)}</text>' if hint else ""
    return (
        f'<svg class="chart" viewBox="0 0 640 80" role="img" aria-label="{esc(label)}">'
        f'<text x="12" y="24" class="svg-muted">{esc(label)}</text>{hint_xml}</svg>'
    )


def svg_topology(modules: list[dict[str, Any]], edges: list[dict[str, Any]], lang: str = "zh") -> str:
    if not modules:
        return _empty_svg(t(lang, "empty_topo"), t(lang, "empty_topo_hint"))
    shown = modules[:MODULE_CAP]
    over = len(modules) - len(shown)
    positions = _layout_modules(shown)
    n = len(shown)
    cols = 1 if n <= 2 else (2 if n <= 6 else 3)
    rows = (n + cols - 1) // cols
    node_w, node_h = 168, 52
    height = max(160, 40 + rows * 88) + (28 if over else 0)
    width = max(720, 36 + cols * 230)
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(t(lang, "aria_topo"))}">'
    ]
    for edge in edges:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        parts.append(
            f'<line x1="{x1 + node_w // 2}" y1="{y1 + node_h // 2}" '
            f'x2="{x2 + node_w // 2}" y2="{y2 + node_h // 2}" '
            f'class="edge" data-edge="{esc(src)}-{esc(dst)}"/>'
        )
    for module in shown:
        mid = str(module.get("id"))
        x, y = positions.get(mid, (20, 20))
        label = esc(_short_label(module.get("name") or mid, 20))
        kind_raw = module_kind(module)
        kind = esc(kind_raw)
        kind_label = esc(lane_for_kind(kind_raw, lang))
        parts.append(f'<g class="topo-node" data-module="{esc(mid)}" data-kind="{kind}">')
        parts.append(f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="4" class="node"/>')
        parts.append(f'<text x="{x + 12}" y="{y + 22}" class="svg-label">{label}</text>')
        parts.append(f'<text x="{x + 12}" y="{y + 40}" class="svg-muted">{kind_label}</text>')
        parts.append('</g>')
    if over:
        parts.append(f'<text x="12" y="{height - 8}" class="svg-muted">{esc(t(lang, "more_modules", n=over))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_dependencies(modules: list[dict[str, Any]], internal: list[dict[str, Any]], external: list[dict[str, Any]], lang: str = "zh") -> str:
    """Deterministic swimlane dependency graph grouped by module kind.

    Edges use cubic Bezier paths with arrow markers; edge kind is derived from
    the source module kind. External deps are pills grouped under a data lane.
    Large graphs cap visible nodes and show a +N summary.
    """
    if not modules and not external:
        return _empty_svg(t(lang, "empty_deps"), t(lang, "empty_deps_hint"))

    shown = modules[:MODULE_CAP]
    over_modules = len(modules) - len(shown)
    by_id = {str(m.get("id")): m for m in shown}

    # Assign lanes (unique, deterministic order). Only occupied lanes.
    lane_names: list[str] = []
    lane_of: dict[str, int] = {}
    data_lane_label = t(lang, "lane_data")
    for m in shown:
        lane = lane_for_kind(module_kind(m), lang)
        if lane not in lane_names:
            lane_names.append(lane)
        lane_of[str(m.get("id"))] = lane_names.index(lane)
    # External pills share the data lane when present; otherwise append one.
    if external and data_lane_label not in lane_names:
        lane_names.append(data_lane_label)
    data_lane = lane_names.index(data_lane_label) if data_lane_label in lane_names else 0

    n_lanes = max(1, len(lane_names))
    # Extra room in data lane when external pills are present.
    has_ext = bool(external)
    lane_h = 86 if has_ext else 72
    top = 28
    footer = 36 if (over_modules or len(external) > EXTERNAL_CAP) else 16
    # Count max nodes per lane for width.
    lane_counts_pre: dict[int, int] = {}
    for m in shown:
        li = lane_of.get(str(m.get("id")), 0)
        lane_counts_pre[li] = lane_counts_pre.get(li, 0) + 1
    max_in_lane = max(lane_counts_pre.values()) if lane_counts_pre else 1
    node_w, node_h = 148, 40
    width = max(720, 160 + max_in_lane * 170)
    height = top + n_lanes * lane_h + footer
    # Place nodes within their lane, left-to-right.
    lane_counts: dict[int, int] = {}
    positions: dict[str, tuple[int, int]] = {}
    for m in shown:
        mid = str(m.get("id"))
        li = lane_of.get(mid, 0)
        idx = lane_counts.get(li, 0)
        lane_counts[li] = idx + 1
        x = 150 + idx * 170
        y = top + li * lane_h + 18
        positions[mid] = (x, y)

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(t(lang, "aria_deps"))}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="edge-arrow"/></marker></defs>',
    ]
    # Lane backgrounds + labels.
    for li, name in enumerate(lane_names):
        y = top + li * lane_h
        parts.append(f'<rect x="8" y="{y}" width="{width - 16}" height="{lane_h - 8}" rx="2" class="lane"/>')
        parts.append(f'<text x="16" y="{y + 20}" class="svg-title">{esc(name)}</text>')

    # Internal edges as cubic paths with arrow markers.
    for edge in internal:
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        cx1, cx2 = x1 + node_w + 24, x2 - 24
        mid_y = (y1 + y2) // 2 + node_h // 2
        src_kind = module_kind(by_id.get(src, {}))
        parts.append(
            f'<path d="M{x1 + node_w},{y1 + node_h // 2} C{cx1},{mid_y} {cx2},{mid_y} {x2},{y2 + node_h // 2}" '
            f'class="edge-strong edge-{esc(src_kind)}" data-edge="{esc(src)}-{esc(dst)}" marker-end="url(#arrow)"/>'
        )

    # Nodes.
    for m in shown:
        mid = str(m.get("id"))
        x, y = positions.get(mid, (20, 20))
        label = esc(_short_label(m.get("name") or mid, 16))
        kind = esc(module_kind(m))
        parts.append(f'<g class="dep-node" data-module="{esc(mid)}" data-kind="{kind}">')
        parts.append(f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="3" class="node-alt"/>')
        parts.append(f'<text x="{x + 10}" y="{y + 25}" class="svg-label">{label}</text>')
        parts.append('</g>')

    # External dep pills in the data lane (below nodes in that lane).
    ext_shown = external[:EXTERNAL_CAP]
    over_ext = len(external) - len(ext_shown)
    if ext_shown and data_lane_label in lane_names:
        ex = 150
        ey = top + data_lane * lane_h + 58
        for dep in ext_shown:
            raw_name = _as_str(dep.get("name", "dep"))
            name = esc(_short_label(raw_name, 14))
            pill_w = min(128, 18 + len(raw_name) * 7)
            parts.append(f'<rect x="{ex}" y="{ey}" width="{pill_w}" height="22" rx="2" class="pill"/>')
            parts.append(f'<text x="{ex + 8}" y="{ey + 15}" class="svg-label">{name}</text>')
            ex += pill_w + 10
            if ex > width - 140:
                break
    if over_ext:
        parts.append(f'<text x="12" y="{height - 18}" class="svg-muted">{esc(t(lang, "more_external", n=over_ext))}</text>')
    if over_modules:
        parts.append(f'<text x="12" y="{height - 4}" class="svg-muted">{esc(t(lang, "more_modules", n=over_modules))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_risk_matrix(risks: list[dict[str, Any]], modules: list[dict[str, Any]], lang: str = "zh") -> str:
    """Module × category risk matrix. Cell shows count + highest severity symbol.

    Rows = modules (plus a global/unknown row), columns = risk categories.
    Falls back to empty state when no risks. No schema change: missing
    module_id is bucketed into the global row; missing category into unknown.
    """
    if not risks:
        return _empty_svg(t(lang, "empty_risks_svg"), t(lang, "empty_risks_hint"))

    module_ids = [str(m.get("id")) for m in modules]
    module_names = {str(m.get("id")): (m.get("name") or m.get("id")) for m in modules}
    rows_order = module_ids + (["__global__"] if any(risk_row_id(r, module_ids) == "__global__" for r in risks) else [])
    row_label = {mid: module_names.get(mid, mid) if mid != "__global__" else t(lang, "global_unknown") for mid in rows_order}

    # Only columns that actually appear (plus keep order from RISK_CATEGORIES).
    present = {risk_category(r) for r in risks}
    cols = tuple(c for c in RISK_CATEGORIES if c in present) or RISK_CATEGORIES
    # Drop empty module rows that have zero risks (keep global if used).
    used_rows = {risk_row_id(r, module_ids) for r in risks}
    rows_order = [mid for mid in rows_order if mid in used_rows]
    cell_w, cell_h, head_h, label_w = 92, 42, 30, 140
    width = label_w + len(cols) * cell_w + 16
    height = head_h + len(rows_order) * cell_h + 16
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(t(lang, "aria_risks"))}">',
    ]
    cat_label = {
        "security": t(lang, "cat_security"),
        "complexity": t(lang, "cat_complexity"),
        "test": t(lang, "cat_test"),
        "ops": t(lang, "cat_ops"),
        "unknown": t(lang, "cat_unknown"),
    }
    # Column headers.
    for ci, cat in enumerate(cols):
        x = label_w + ci * cell_w
        parts.append(f'<text x="{x + 8}" y="20" class="svg-title">{esc(cat_label.get(cat, cat))}</text>')
    # Cells.
    shown_risks = risks[:RISK_CAP]
    over = len(risks) - len(shown_risks)
    for ri, mid in enumerate(rows_order):
        y = head_h + ri * cell_h
        parts.append(f'<text x="8" y="{y + 26}" class="svg-label">{esc(_short_label(row_label[mid], 18))}</text>')
        for ci, cat in enumerate(cols):
            x = label_w + ci * cell_w
            cell_risks = [r for r in shown_risks if risk_category(r) == cat and risk_row_id(r, module_ids) == mid]
            if not cell_risks:
                parts.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cell_w - 8}" height="{cell_h - 8}" rx="6" class="cell cell-empty"/>')
                continue
            highest = max(cell_risks, key=lambda r: SEVERITY_RANK.get(risk_severity(r), 2))
            sev = risk_severity(highest)
            color = SEVERITY_COLORS[sev]
            sym = SEVERITY_SYM[sev]
            count = len(cell_risks)
            parts.append(f'<g class="risk-cell" data-module="{esc(mid)}" data-severity="{esc(sev)}" data-category="{esc(cat)}">')
            parts.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cell_w - 8}" height="{cell_h - 8}" rx="6" fill="{color}" opacity="0.85"/>')
            parts.append(f'<text x="{x + cell_w // 2}" y="{y + 22}" text-anchor="middle" class="svg-inverse">{count} {sym}</text>')
            parts.append('</g>')
    if over:
        parts.append(f'<text x="8" y="{height - 4}" class="svg-muted">{esc(t(lang, "more_risks", n=over))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_test_matrix(matrix: list[dict[str, Any]], lang: str = "zh") -> str:
    """HTML table for test matrix, sorted by missing/unknown first.

    Status uses both color (class) and a text symbol (✓/✗/?). Graceful
    fallback: no JS, fully readable. Capped with +N summary.
    """
    if not matrix:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_tests"))}</p>'

    def status_rank(row: dict[str, Any]) -> int:
        # missing all -> 0, unknown -> 1, partial -> 2, covered -> 3 (asc = worst first)
        flags = [row.get("unit"), row.get("integration"), row.get("e2e")]
        if all(f is True for f in flags):
            return TEST_STATUS_ORDER["covered"]
        if all(f is False for f in flags):
            return TEST_STATUS_ORDER["missing"]
        if any(f is None for f in flags):
            return TEST_STATUS_ORDER["unknown"]
        return TEST_STATUS_ORDER["partial"]

    sorted_rows = sorted(matrix, key=lambda r: (status_rank(r), _as_str(r.get("area"))))
    shown = sorted_rows[:TEST_CAP]
    over = len(matrix) - len(shown)

    def cell(flag: Any, kind: str) -> str:
        val = TEST_SYM.get(flag, "?")
        cls = "st-yes" if flag is True else ("st-no" if flag is False else "st-unknown")
        sr = t(lang, "yes") if flag is True else (t(lang, "no") if flag is False else t(lang, "unknown"))
        return f'<td class="{cls}" data-status="{cls}"><span class="sym">{val}</span> <span class="sr-only">{esc(sr)}</span></td>'

    rows_xml = []
    for row in shown:
        area = esc(row.get("area", "?"))
        mid = esc(module_id_of(row) or "")
        rows_xml.append(
            f'<tr class="test-row" data-module="{mid}" data-status="{"covered" if status_rank(row) == 3 else ("missing" if status_rank(row) == 0 else ("unknown" if status_rank(row) == 1 else "partial"))}">'
            f'<td class="area">{area}</td>{cell(row.get("unit"), "unit")}{cell(row.get("integration"), "integration")}{cell(row.get("e2e"), "e2e")}</tr>'
        )
    summary = f'<p class="muted cap-note">{esc(t(lang, "more_tests", n=over))}</p>' if over else ""
    return (
        '<div class="table-scroll"><table class="test-matrix"><thead><tr>'
        f'<th>{esc(t(lang, "th_area"))}</th><th>{esc(t(lang, "th_unit"))}</th>'
        f'<th>{esc(t(lang, "th_integration"))}</th><th>{esc(t(lang, "th_e2e"))}</th></tr></thead><tbody>'
        + "".join(rows_xml) + '</tbody></table></div>' + summary
    )


def render_roadmap(phases: list[dict[str, Any]], lang: str = "zh") -> str:
    """Metro/timeline roadmap as HTML with evidence chips. No SVG required."""
    if not phases:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_roadmap"))}</p>'
    shown = phases[:ROADMAP_CAP]
    over = len(phases) - len(shown)
    steps = []
    for index, phase in enumerate(shown):
        phase_no = phase.get("phase", index + 1)
        title = esc(phase.get("title") or t(lang, "phase", n=phase_no))
        items = phase.get("items") or []
        item_xml = []
        for it in items:
            if isinstance(it, str):
                item_xml.append(f'<li>{esc(it)}</li>')
            else:
                label_text = _as_str(it.get("text") or it.get("title") or "")
                label = esc(label_text)
                chip = render_evidence_chip(it.get("evidence"), label_text, t(lang, "sec_roadmap"), lang)
                item_xml.append(f"<li>{label}{chip}</li>")
        items_xml = "".join(item_xml)
        last = "last" if index == len(shown) - 1 else ""
        steps.append(
            f'<li class="metro-step {last}"><div class="metro-dot">{esc(str(phase_no))}</div>'
            f'<div class="metro-body"><h4>{title}</h4><ul>{items_xml}</ul></div></li>'
        )
    summary = f'<p class="muted cap-note">{esc(t(lang, "more_phases", n=over))}</p>' if over else ""
    return '<ol class="metro">' + "".join(steps) + '</ol>' + summary


def _evidence_text(evidence: Any) -> str:
    if evidence is None:
        return ""
    if isinstance(evidence, list):
        return "; ".join(str(e) for e in evidence if e not in (None, ""))
    return str(evidence)


def render_evidence_chip(evidence: Any, claim_text: Any, section_label: str, lang: str = "zh") -> str:
    """Render an evidence chip (button) that opens the evidence drawer with JS.

    Without JS the evidence text stays visible inside the chip and in the
    appendix, so nothing is hidden. All dynamic text is HTML-escaped.
    """
    text = _evidence_text(evidence)
    if not text:
        return ""
    ev_attr = esc(text)
    claim_attr = esc(claim_text if claim_text is not None else "")
    sec_attr = esc(section_label)
    return (
        f'<button class="ev-chip" type="button" '
        f'data-evidence="{ev_attr}" data-claim="{claim_attr}" data-section="{sec_attr}" '
        f'title="{ev_attr}"><span class="ev-tag">{esc(t(lang, "evidence"))}</span> '
        f'<span class="ev-text">{ev_attr}</span></button>'
    )


def _item_label(item: dict[str, Any]) -> str:
    """Best human label for a claim-like object (never empty if any field exists)."""
    for key in ("text", "title", "summary", "description", "name", "label"):
        val = item.get(key)
        if val not in (None, ""):
            return _as_str(val)
    return ""


def render_claim_list(items: list[dict[str, Any]] | list[str], section_label: str = "", lang: str = "zh", *, as_risks: bool = False) -> str:
    if not items:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_items"))}</p>'
    rows: list[str] = []
    for item in items:
        if isinstance(item, str):
            rows.append(f'<li class="claim-item"><span class="claim-text">{esc(item)}</span></li>')
            continue
        claim_text = _item_label(item)
        if not claim_text and not item.get("evidence"):
            continue
        label_html = esc(claim_text) if claim_text else ""
        confidence = esc(item.get("confidence") or "")
        chip = render_evidence_chip(item.get("evidence"), claim_text, section_label, lang)
        conf = f' <span class="conf">{confidence}</span>' if confidence else ""
        mid = esc(module_id_of(item) or "")
        sev = esc(risk_severity(item)) if as_risks else ""
        cat = esc(risk_category(item)) if as_risks else ""
        attrs = f' data-module="{mid}"' if mid else ""
        attrs += f' data-severity="{sev}" data-category="{cat}"' if as_risks else ""
        body = f'<span class="claim-text">{label_html}</span>' if label_html else ""
        rows.append(f'<li class="claim-item"{attrs}>{body}{chip}{conf}</li>')
    if not rows:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_items"))}</p>'
    return '<ul class="claim-list">' + "".join(rows) + "</ul>"


def render_module_cards(modules: list[dict[str, Any]], lang: str = "zh") -> str:
    if not modules:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_modules"))}</p>'
    shown = modules[:MODULE_CAP]
    over = len(modules) - len(shown)
    cards = []
    for m in shown:
        mid = esc(m.get("id") or "")
        name = esc(m.get("name") or m.get("id") or t(lang, "module"))
        kind = esc(lane_for_kind(module_kind(m), lang))
        desc = esc(m.get("description") or "")
        chip = render_evidence_chip(m.get("evidence"), m.get("name") or m.get("id"), t(lang, "sec_topology"), lang)
        desc_html = f'<p class="mod-desc">{desc}</p>' if desc else ""
        cards.append(
            f'<article class="mod-card" data-module="{mid}" data-kind="{esc(module_kind(m))}">'
            f'<header class="mod-head"><h3>{name}</h3><span class="mod-kind">{kind}</span></header>'
            f'{desc_html}{chip}</article>'
        )
    note = f'<p class="muted cap-note">{esc(t(lang, "more_modules", n=over))}</p>' if over else ""
    return '<div class="mod-grid">' + "".join(cards) + "</div>" + note


def render_risk_cards(risks: list[dict[str, Any]], lang: str = "zh") -> str:
    if not risks:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_risks"))}</p>'
    shown = risks[:RISK_CAP]
    over = len(risks) - len(shown)
    # high first
    shown = sorted(shown, key=lambda r: -SEVERITY_RANK.get(risk_severity(r), 2))
    sev_label = {"high": t(lang, "sev_high"), "medium": t(lang, "sev_medium"), "low": t(lang, "sev_low")}
    cat_label = {
        "security": t(lang, "cat_security"),
        "complexity": t(lang, "cat_complexity"),
        "test": t(lang, "cat_test"),
        "ops": t(lang, "cat_ops"),
        "unknown": t(lang, "cat_unknown"),
    }
    cards = []
    for r in shown:
        label = _item_label(r) or t(lang, "risk")
        title = esc(label)
        sev = risk_severity(r)
        cat = risk_category(r)
        mid = esc(module_id_of(r) or "")
        body = ""
        for key in ("summary", "description", "text"):
            val = _as_str(r.get(key))
            if val and val != label:
                body = esc(val)
                break
        chip = render_evidence_chip(r.get("evidence"), label, t(lang, "sec_risks"), lang)
        conf = esc(r.get("confidence") or "")
        conf_html = f'<span class="conf">{conf}</span>' if conf else ""
        body_html = f'<p class="risk-body">{body}</p>' if body else ""
        cards.append(
            f'<article class="risk-card sev-{esc(sev)}" data-module="{mid}" '
            f'data-severity="{esc(sev)}" data-category="{esc(cat)}">'
            f'<header class="risk-head"><span class="sev-badge sev-{esc(sev)}">{esc(sev_label.get(sev, sev))}</span>'
            f'<span class="risk-cat">{esc(cat_label.get(cat, cat))}</span></header>'
            f'<h3 class="risk-title">{title}</h3>{body_html}'
            f'<div class="risk-meta">{chip}{conf_html}</div></article>'
        )
    note = f'<p class="muted cap-note">{esc(t(lang, "more_risks", n=over))}</p>' if over else ""
    return '<div class="risk-list">' + "".join(cards) + "</div>" + note


def render_flows(flows: list[dict[str, Any]], lang: str = "zh") -> str:
    if not flows:
        return f'<p class="muted empty-state">{esc(t(lang, "empty_flows"))}</p>'
    blocks: list[str] = []
    for flow in flows:
        title = esc(flow.get("title") or flow.get("name") or flow.get("id") or t(lang, "flow"))
        summary = esc(flow.get("summary") or "")
        steps = flow.get("steps") or []
        step_items = []
        for index, step in enumerate(steps):
            if isinstance(step, str):
                step_items.append(
                    f'<li class="flow-step"><span class="flow-n">{index + 1}</span>'
                    f'<span class="flow-label">{esc(step)}</span></li>'
                )
            else:
                label_text = step.get("label") or step.get("text") or ""
                label = esc(label_text)
                chip = render_evidence_chip(step.get("evidence"), label_text, t(lang, "sec_flows"), lang)
                step_items.append(
                    f'<li class="flow-step"><span class="flow-n">{index + 1}</span>'
                    f'<span class="flow-label">{label}</span>{chip}</li>'
                )
        steps_xml = "".join(step_items)
        sum_html = f'<p class="flow-sum">{summary}</p>' if summary else ""
        blocks.append(
            f'<article class="flow-card"><h3>{title}</h3>{sum_html}'
            f'<ol class="flow-steps">{steps_xml}</ol></article>'
        )
    return '<div class="flow-grid">' + "".join(blocks) + "</div>"


def _kpi_items(data: dict[str, Any], lang: str = "zh") -> list[dict[str, str]]:
    """Derive 4-6 KPIs from existing JSON (no schema change)."""
    modules = data.get("modules") or []
    internal = (data.get("dependencies") or {}).get("internal") or []
    risks = data.get("risks") or []
    high = sum(1 for r in risks if risk_severity(r) == "high")
    matrix = (data.get("tests") or {}).get("matrix") or []
    missing_tests = sum(1 for r in matrix if all(r.get(k) is False for k in ("unit", "integration", "e2e")))
    gaps = (data.get("appendix") or {}).get("gaps") or []
    flows = data.get("flows") or []
    return [
        {"label": t(lang, "kpi_modules"), "value": str(len(modules))},
        {"label": t(lang, "kpi_internal"), "value": str(len(internal))},
        {"label": t(lang, "kpi_high_risks"), "value": str(high)},
        {"label": t(lang, "kpi_tests_missing"), "value": str(missing_tests)},
        {"label": t(lang, "kpi_gaps"), "value": str(len(gaps))},
        {"label": t(lang, "kpi_flows"), "value": str(len(flows))},
    ]


def render_hero(data: dict[str, Any], page_title: str, repo_path: str, mode: str, generated: str, lang: str = "zh") -> str:
    """Full-bleed cover: thesis first, stats as a quiet index — not a card."""
    hue = _hue_for((data.get("meta") or {}).get("repo_name", "") + (data.get("meta") or {}).get("repo_path", ""))
    kpis = _kpi_items(data, lang)
    shown = [k for k in kpis if k["value"] != "0"] or kpis[:3]
    kpi_xml = "".join(
        f'<li class="kpi" role="listitem"><span class="kpi-val">{esc(k["value"])}</span>'
        f'<span class="kpi-label">{esc(k["label"])}</span></li>'
        for k in shown
    )
    summary = esc((data.get("overview") or {}).get("summary") or (data.get("overview") or {}).get("elevator_pitch") or "")
    conf = esc((data.get("meta") or {}).get("confidence") or "")
    conf_html = f'<span class="meta-pill">{esc(t(lang, "confidence"))} {conf}</span>' if conf else ""
    repo_name = esc((data.get("meta") or {}).get("repo_name") or page_title)
    return (
        f'<header class="hero cover" style="--hue:{hue}">'
        f'<div class="cover-inner">'
        f'<div class="cover-top">'
        f'<p class="eyebrow">{esc(t(lang, "eyebrow"))}</p>'
        f'<div class="cover-tools">'
        f'<button class="ss-toggle" type="button" data-screenshot="1">{esc(t(lang, "screenshot"))}</button>'
        f'<span class="gen-stamp">{generated}</span>'
        f'</div></div>'
        f'<p class="cover-kicker">{repo_name}</p>'
        f'<h1 class="cover-title">{page_title}</h1>'
        f'<p class="lede">{summary}</p>'
        f'<p class="meta"><span class="meta-pill">{mode}</span>{conf_html}'
        f'<span class="meta-path">{repo_path}</span></p>'
        f'<ul class="kpi-strip" role="list">{kpi_xml}</ul>'
        f'</div></header>'
    )


def render_legend(items: list[tuple[str, str, str]]) -> str:
    """Compact legend list: (css-class, symbol, label)."""
    parts = [
        f'<span class="legend"><span class="legend-item {esc(cls)}">{esc(sym)}</span>{esc(label)}</span>'
        for cls, sym, label in items
    ]
    return '<div class="legend-row">' + "".join(parts) + '</div>'


def render_filter_chips(group: str, options: list[tuple[str, str]], lang: str = "zh") -> str:
    """Filter chip group: (value, label). Pure data attributes, no innerHTML."""
    chips = "".join(
        f'<button class="filter-chip" type="button" data-filter-group="{esc(group)}" data-filter="{esc(val)}">{esc(label)}</button>'
        for val, label in options
    )
    aria = t(lang, "filter_aria", group=group)
    return f'<div class="filter-row" role="group" aria-label="{esc(aria)}">{chips}</div>'


def build_html(data: dict[str, Any], title: str | None, lang: str | None = None) -> str:
    meta = data.get("meta", {})
    lang = resolve_lang(lang, meta if isinstance(meta, dict) else None)
    overview = data.get("overview", {})
    modules = data.get("modules", [])
    topology = data.get("topology", {})
    dependencies = data.get("dependencies", {})
    flows = data.get("flows", [])
    risks = data.get("risks", [])
    tests = data.get("tests", {})
    roadmap = data.get("roadmap", [])
    appendix = data.get("appendix", {})

    page_title = esc(title or meta.get("repo_name") or t(lang, "default_title"))
    repo_path = esc(meta.get("repo_path") or "")
    generated = esc(meta.get("generated_at") or datetime.now(timezone.utc).isoformat())
    mode = esc(meta.get("mode") or "standard")

    languages = overview.get("languages") or []
    topology_edges = topology.get("edges") or []
    internal = dependencies.get("internal") or []
    external = dependencies.get("external") or []
    matrix = tests.get("matrix") or []

    toc_items = [
        ("overview", "01", t(lang, "toc_overview")),
        ("topology", "02", t(lang, "toc_topology")),
        ("dependencies", "03", t(lang, "toc_deps")),
        ("flows", "04", t(lang, "toc_flows")),
        ("risks", "05", t(lang, "toc_risks")),
        ("tests", "06", t(lang, "toc_tests")),
        ("roadmap", "07", t(lang, "toc_path")),
        ("appendix", "08", t(lang, "toc_appendix")),
    ]
    toc_links = "".join(
        f'<li><a href="#{sid}"><span class="toc-num">{num}</span><span class="toc-label">{esc(label)}</span></a></li>'
        for sid, num, label in toc_items
    )
    toc_nav = (
        f'<nav id="toc" class="toc-rail" aria-label="{esc(t(lang, "sections_aria"))}"><ol>{toc_links}</ol></nav>'
    )

    def chapter(sid: str, num: str, title: str, dek: str, inner: str, empty: bool = False, band: str = "") -> str:
        empty_cls = " is-empty" if empty else ""
        band_cls = f" band-{band}" if band else ""
        dek_html = f'<p class="chapter-dek">{esc(dek)}</p>' if dek else ""
        return (
            f'<section id="{sid}" class="chapter{empty_cls}{band_cls}">'
            f'<header class="chapter-head">'
            f'<span class="chapter-num">{num}</span>'
            f'<div class="chapter-titles"><h2>{esc(title)}</h2>{dek_html}</div>'
            f'</header>'
            f'<div class="chapter-body">{inner}</div></section>'
        )

    claims = overview.get("claims") or []
    overview_inner = (
        f'<div class="split split-overview">'
        f'<div class="split-main">{render_claim_list(claims, t(lang, "sec_overview"), lang)}</div>'
        f'<aside class="split-side"><h3>{esc(t(lang, "languages"))}</h3>{svg_language_bars(languages, lang)}</aside>'
        f'</div>'
    )
    topo_inner = (
        f'<div class="diagram-stage">{svg_topology(modules, topology_edges, lang)}</div>'
        f'{render_legend([("node", "■", t(lang, "legend_module")), ("edge", "—", t(lang, "legend_edge"))])}'
        f'{render_module_cards(modules, lang)}'
    )
    dep_inner = (
        f'<div class="diagram-stage">{svg_dependencies(modules, internal, external, lang)}</div>'
        f'{render_legend([("edge-strong", "→", t(lang, "legend_internal")), ("pill", "▢", t(lang, "legend_external"))])}'
        + (f'<h3>{esc(t(lang, "external"))}</h3>{render_claim_list(external, t(lang, "sec_deps"), lang)}' if external else "")
    )
    risk_inner = (
        f'<div class="split split-risks">'
        f'<div class="split-side diagram-stage">{svg_risk_matrix(risks, modules, lang)}'
        f'{render_legend([("sev-high", "▲", t(lang, "legend_high")), ("sev-medium", "◆", t(lang, "legend_medium")), ("sev-low", "●", t(lang, "legend_low"))])}</div>'
        f'<div class="split-main">'
        f'{render_filter_chips("severity", [("high", t(lang, "filter_high")), ("medium", t(lang, "filter_medium")), ("low", t(lang, "filter_low")), ("", t(lang, "filter_all"))], lang)}'
        f'{render_risk_cards(risks, lang)}</div></div>'
    )
    notes = esc(tests.get("coverage_notes") or tests.get("notes") or "")
    notes_html = f'<p class="coverage-notes">{notes}</p>' if notes else ""
    tests_inner = (
        f'{notes_html}'
        f'{render_legend([("st-yes", "✓", t(lang, "legend_covered")), ("st-no", "✗", t(lang, "legend_missing")), ("st-unknown", "?", t(lang, "legend_unknown"))])}'
        f'{render_test_matrix(matrix, lang)}'
    )
    appendix_inner = (
        f'<div class="appendix-grid">'
        f'<div><h3>{esc(t(lang, "gaps"))}</h3>{render_claim_list(appendix.get("gaps") or [], t(lang, "sec_appendix_gaps"), lang)}</div>'
        f'<div><h3>{esc(t(lang, "open_questions"))}</h3>{render_claim_list(appendix.get("open_questions") or [], t(lang, "sec_appendix_q"), lang)}</div>'
        f'<div><h3>{esc(t(lang, "files_examined"))}</h3>{render_claim_list(appendix.get("files_examined") or [], t(lang, "sec_appendix_files"), lang)}</div>'
        f'</div>'
    )

    body_parts = [
        render_hero(data, page_title, repo_path, mode, generated, lang),
        toc_nav,
        '<div class="content-stream">',
        chapter("overview", "01", t(lang, "ch_overview"), t(lang, "ch_overview_dek"), overview_inner, not (claims or languages)),
        chapter("topology", "02", t(lang, "ch_topology"), t(lang, "ch_topology_dek"), topo_inner, not modules, "map"),
        chapter("dependencies", "03", t(lang, "ch_deps"), t(lang, "ch_deps_dek"), dep_inner, not (modules or external), "map"),
        chapter("flows", "04", t(lang, "ch_flows"), t(lang, "ch_flows_dek"), render_flows(flows, lang), not flows),
        chapter("risks", "05", t(lang, "ch_risks"), t(lang, "ch_risks_dek"), risk_inner, not risks, "alert"),
        chapter("tests", "06", t(lang, "ch_tests"), t(lang, "ch_tests_dek"), tests_inner, not matrix),
        chapter("roadmap", "07", t(lang, "ch_roadmap"), t(lang, "ch_roadmap_dek"), render_roadmap(roadmap, lang), not roadmap),
        chapter("appendix", "08", t(lang, "ch_appendix"), t(lang, "ch_appendix_dek"), appendix_inner, False, "quiet"),
        "</div>",
        (
            f'<dialog id="ev-drawer" aria-label="{esc(t(lang, "drawer_aria"))}">'
            f'<form method="dialog"><button class="ev-close" type="submit" aria-label="{esc(t(lang, "close"))}">×</button></form>'
            '<p class="ev-drawer-section" data-drawer-section></p>'
            '<p class="ev-drawer-claim" data-drawer-claim></p>'
            '<p class="ev-drawer-evidence" data-drawer-evidence></p>'
            '</dialog>'
        ),
    ]

    css = """
:root {
  color-scheme: light;
  --bg: #f3f5f7;
  --ink: #0e1116;
  --muted: #5a6572;
  --panel: #ffffff;
  --edge: #cfd6de;
  --line: #97a3b0;
  --accent: #2546a8;
  --accent-ink: #1a3278;
  --soft: #e8eefc;
  --band: #e7ebf0;
  --high: #a61b1b;
  --medium: #9a5b12;
  --low: #2f6b3a;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --sans: "Avenir Next", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --mono: "SF Mono", Menlo, Consolas, monospace;
  --measure: 72rem;
  --gutter: clamp(1.1rem, 3vw, 2.4rem);
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --bg: #0c0f14;
    --ink: #e8edf4;
    --muted: #93a0b0;
    --panel: #141922;
    --edge: #2a3340;
    --line: #556274;
    --accent: #8eabff;
    --accent-ink: #c2d0ff;
    --soft: #1a2438;
    --band: #121820;
    --high: #e07a7a;
    --medium: #e0a45a;
    --low: #7dba88;
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font: 16px/1.55 var(--sans);
  color: var(--ink);
  background: var(--bg);
}
main { display: block; }

/* ===== COVER ===== */
.hero.cover {
  --accent: hsl(var(--hue, 228) 65% 42%);
  --accent-ink: hsl(var(--hue, 228) 68% 30%);
  background:
    linear-gradient(105deg, color-mix(in srgb, var(--accent) 14%, var(--bg)) 0%, var(--bg) 48%, var(--band) 100%);
  border-bottom: 1px solid var(--edge);
  padding: clamp(2.2rem, 6vw, 4.5rem) var(--gutter) clamp(1.8rem, 4vw, 3rem);
}
@media (prefers-color-scheme: dark) {
  .hero.cover {
    --accent: hsl(var(--hue, 228) 55% 68%);
    --accent-ink: hsl(var(--hue, 228) 60% 82%);
  }
}
.cover-inner { max-width: var(--measure); margin: 0 auto; }
.cover-top { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 2.2rem; }
.eyebrow {
  margin: 0;
  font: 600 0.72rem/1 var(--sans);
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--accent-ink);
}
.cover-tools { display: flex; align-items: center; gap: .8rem; }
.ss-toggle {
  padding: .4rem .7rem;
  border: 1px solid var(--edge);
  background: transparent;
  color: var(--muted);
  font: 500 .72rem/1 var(--sans);
  letter-spacing: .04em;
  text-transform: uppercase;
  cursor: pointer;
}
.ss-toggle:hover, .ss-toggle[aria-pressed="true"] {
  border-color: var(--accent);
  color: var(--accent-ink);
  background: var(--soft);
}
.gen-stamp { font: 400 .72rem/1 var(--mono); color: var(--muted); }
.cover-kicker {
  margin: 0 0 .35rem;
  font: 500 .85rem/1.2 var(--mono);
  color: var(--muted);
  letter-spacing: .02em;
}
.cover-title {
  margin: 0 0 1.1rem;
  max-width: 16ch;
  font: 600 clamp(2.4rem, 6.5vw, 4.4rem)/1.02 var(--serif);
  letter-spacing: -.03em;
}
.lede {
  margin: 0 0 1.25rem;
  max-width: 38rem;
  font: 400 1.2rem/1.45 var(--serif);
  color: var(--ink);
}
.meta {
  display: flex; flex-wrap: wrap; gap: .55rem .7rem; align-items: center;
  margin: 0 0 2rem; color: var(--muted); font-size: .85rem;
}
.meta-pill {
  display: inline-block;
  padding: .2rem .55rem;
  border: 1px solid var(--edge);
  font: 500 .68rem/1.3 var(--mono);
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--muted);
  background: color-mix(in srgb, var(--panel) 70%, transparent);
}
.meta-path { font-family: var(--mono); font-size: .75rem; word-break: break-all; }
.kpi-strip {
  list-style: none; margin: 0; padding: 1.1rem 0 0;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(5.5rem, 1fr));
  gap: 1rem 1.4rem;
  border-top: 1px solid var(--edge);
  max-width: 42rem;
}
.kpi { display: flex; flex-direction: column; gap: .2rem; }
.kpi-val { font: 600 1.65rem/1 var(--serif); color: var(--accent-ink); }
.kpi-label { font: 500 .68rem/1.2 var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }

/* ===== TOP TOC (horizontal index) ===== */
.toc-rail {
  position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--edge);
}
.toc-rail ol {
  list-style: none; margin: 0 auto; padding: .55rem var(--gutter);
  max-width: var(--measure);
  display: flex; gap: .15rem; overflow-x: auto;
}
.toc-rail a {
  display: flex; flex-direction: column; gap: .1rem;
  min-width: 4.6rem; padding: .45rem .55rem;
  text-decoration: none; color: var(--muted);
  border-bottom: 2px solid transparent;
}
.toc-num { font: 500 .65rem/1 var(--mono); letter-spacing: .08em; }
.toc-label { font: 500 .78rem/1.1 var(--sans); white-space: nowrap; }
.toc-rail a:hover { color: var(--ink); }
.toc-rail a.active { color: var(--accent-ink); border-bottom-color: var(--accent); }

/* ===== CHAPTER STREAM ===== */
.content-stream { max-width: var(--measure); margin: 0 auto; padding: 0 var(--gutter) 5rem; }
.chapter {
  padding: clamp(2rem, 4vw, 3.2rem) 0;
  border-bottom: 1px solid var(--edge);
  scroll-margin-top: 4.2rem;
}
.chapter.is-empty { opacity: .55; }
.chapter.band-map .diagram-stage,
.chapter.band-alert .diagram-stage {
  background: var(--band);
  margin: 0 calc(-1 * var(--gutter));
  padding: 1.15rem var(--gutter);
  border-top: 1px solid var(--edge);
  border-bottom: 1px solid var(--edge);
}
.chapter.band-quiet { opacity: .92; }
.chapter-head {
  display: grid;
  grid-template-columns: 3.2rem 1fr;
  gap: .9rem 1.1rem;
  align-items: start;
  margin-bottom: 1.4rem;
}
.chapter-num {
  font: 500 .85rem/1 var(--mono);
  color: var(--accent);
  letter-spacing: .08em;
  padding-top: .35rem;
}
.chapter-titles h2 {
  margin: 0;
  font: 600 clamp(1.55rem, 2.8vw, 2.1rem)/1.15 var(--serif);
  letter-spacing: -.02em;
}
.chapter-dek {
  margin: .4rem 0 0;
  max-width: 36rem;
  color: var(--muted);
  font: 400 .98rem/1.4 var(--serif);
}
.chapter-body h3 {
  margin: 1.4rem 0 .55rem;
  font: 600 .72rem/1.2 var(--sans);
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
}

/* claims as editorial list */
.claim-list { list-style: none; margin: 0; padding: 0; }
.claim-list li {
  margin: 0;
  padding: .85rem 0;
  border-bottom: 1px solid color-mix(in srgb, var(--edge) 75%, transparent);
  display: flex; flex-wrap: wrap; gap: .55rem .7rem; align-items: baseline;
}
.claim-list li:last-child { border-bottom: 0; }
.claim-text { flex: 1 1 28rem; font: 500 1.05rem/1.4 var(--serif); }
.conf { font: 500 .68rem/1 var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.empty-state { color: var(--muted); font-style: italic; margin: 0; }
.cap-note, .muted, .evidence { color: var(--muted); font-size: .9rem; }
.coverage-notes { color: var(--muted); margin: 0 0 .8rem; }

/* splits */
.split { display: grid; gap: 1.4rem 2rem; align-items: start; }
@media (min-width: 900px) {
  .split-overview { grid-template-columns: minmax(0, 1.4fr) minmax(14rem, .8fr); }
  .split-risks { grid-template-columns: minmax(16rem, .9fr) minmax(0, 1.2fr); }
}
.split-side { min-width: 0; }
.diagram-stage { overflow-x: auto; }

/* modules as index rows, not cards */
.mod-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  margin-top: 1rem;
  border-top: 1px solid var(--edge);
}
.mod-card {
  display: grid;
  grid-template-columns: minmax(9rem, 13rem) minmax(0, 1fr) auto;
  column-gap: 1.2rem;
  row-gap: .25rem;
  align-items: baseline;
  padding: .95rem 0;
  border-bottom: 1px solid var(--edge);
  background: transparent;
}
.mod-head {
  display: flex;
  flex-direction: column;
  gap: .2rem;
}
.mod-head h3 {
  margin: 0;
  font: 600 1.02rem/1.25 var(--serif);
  text-transform: none;
  letter-spacing: 0;
  color: var(--ink);
}
.mod-kind {
  font: 500 .65rem/1.2 var(--mono);
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--muted);
}
.mod-desc { margin: 0; font-size: .9rem; color: var(--muted); }
.mod-card > .ev-chip { align-self: center; }

/* flows as numbered columns */
.flow-grid {
  display: grid;
  gap: 1.2rem;
}
@media (min-width: 860px) {
  .flow-grid { grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); }
}
.flow-card {
  padding: 0;
  background: transparent;
  border: 0;
  border-top: 3px solid var(--accent);
  padding-top: .9rem;
}
.flow-card h3 {
  margin: 0 0 .35rem;
  font: 600 1.15rem/1.2 var(--serif);
  text-transform: none;
  letter-spacing: -.01em;
  color: var(--ink);
}
.flow-sum { margin: 0 0 .8rem; color: var(--muted); font-size: .92rem; }
.flow-steps { list-style: none; margin: 0; padding: 0; }
.flow-step {
  display: grid;
  grid-template-columns: 1.6rem 1fr auto;
  gap: .65rem;
  align-items: baseline;
  padding: .55rem 0;
  border-top: 1px dashed color-mix(in srgb, var(--edge) 85%, transparent);
}
.flow-step:first-child { border-top: 0; }
.flow-n {
  font: 600 .75rem/1 var(--mono);
  color: var(--accent-ink);
}
.flow-label { font: 500 .98rem/1.35 var(--serif); }

/* risks */
.risk-list { display: grid; gap: 0; }
.risk-card {
  padding: .9rem 0 .9rem .85rem;
  border: 0;
  border-bottom: 1px solid var(--edge);
  border-left: 3px solid var(--line);
  background: transparent;
  border-radius: 0;
}
.risk-card.sev-high { border-left-color: var(--high); }
.risk-card.sev-medium { border-left-color: var(--medium); }
.risk-card.sev-low { border-left-color: var(--low); }
.risk-head { display: flex; gap: .55rem; align-items: center; margin-bottom: .2rem; }
.sev-badge {
  font: 600 .65rem/1 var(--mono);
  text-transform: uppercase;
  letter-spacing: .08em;
  padding: .2rem .45rem;
  border: 1px solid currentColor;
}
.sev-badge.sev-high { color: var(--high); }
.sev-badge.sev-medium { color: var(--medium); }
.sev-badge.sev-low { color: var(--low); }
.risk-cat { font: 500 .68rem/1 var(--mono); color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
.risk-title { margin: .2rem 0 .35rem; font: 600 1.05rem/1.25 var(--serif); }
.risk-body { margin: 0 0 .45rem; color: var(--muted); font-size: .9rem; }
.risk-meta { display: flex; flex-wrap: wrap; gap: .55rem; align-items: center; }

/* legend / filters / chips */
.legend-row { display: flex; flex-wrap: wrap; gap: .85rem; margin: .7rem 0 1rem; font-size: .78rem; color: var(--muted); }
.legend { display: inline-flex; align-items: center; gap: .3rem; }
.legend-item { min-width: 12px; text-align: center; font-weight: 700; font-family: var(--mono); }
.legend-item.node, .legend-item.node-alt, .legend-item.pill { color: var(--accent); }
.legend-item.edge, .legend-item.edge-strong { color: var(--line); }
.legend-item.sev-high { color: var(--high); }
.legend-item.sev-medium { color: var(--medium); }
.legend-item.sev-low { color: var(--low); }
.legend-item.st-yes { color: var(--low); }
.legend-item.st-no { color: var(--high); }
.legend-item.st-unknown { color: var(--medium); }
.filter-row { display: flex; flex-wrap: wrap; gap: .4rem; margin: 0 0 .9rem; }
.filter-chip {
  padding: .3rem .6rem;
  border: 1px solid var(--edge);
  background: transparent;
  color: var(--muted);
  font: 500 .72rem/1 var(--sans);
  cursor: pointer;
}
.filter-chip[aria-pressed="true"] {
  border-color: var(--accent);
  color: var(--accent-ink);
  background: var(--soft);
}
.ev-chip {
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .15rem .5rem;
  border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--edge));
  background: color-mix(in srgb, var(--soft) 65%, transparent);
  color: var(--ink);
  font: 500 .72rem/1.35 var(--mono);
  cursor: pointer;
  max-width: 100%;
}
.ev-chip:hover { border-color: var(--accent); background: var(--soft); }
.ev-tag { font-size: .62rem; text-transform: uppercase; letter-spacing: .06em; color: var(--accent-ink); font-weight: 600; font-family: var(--sans); }
.ev-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 36ch; }

dialog#ev-drawer {
  border: 1px solid var(--edge);
  border-radius: 0;
  padding: 1.2rem 1.3rem;
  max-width: 32rem;
  width: min(92vw, 32rem);
  color: var(--ink);
  background: var(--panel);
}
dialog#ev-drawer::backdrop { background: rgba(18,21,26,.48); }
.ev-close { position: absolute; top: .45rem; right: .55rem; border: 0; background: transparent; font-size: 1.3rem; cursor: pointer; color: var(--muted); }
.ev-drawer-section { font: 600 .68rem/1 var(--sans); letter-spacing: .1em; text-transform: uppercase; color: var(--accent); margin: .2rem 0; }
.ev-drawer-claim { font: 600 1.05rem/1.3 var(--serif); margin: .45rem 0; }
.ev-drawer-evidence { margin: .45rem 0; word-break: break-word; font: 400 .85rem/1.4 var(--mono); color: var(--muted); }

/* charts / tables / metro */
.chart { width: 100%; height: auto; display: block; margin: .4rem 0; }
.svg-label { fill: var(--ink); font-size: 12px; font-family: var(--sans); }
.svg-muted, .svg-inverse-muted { fill: var(--muted); font-size: 11px; font-family: var(--sans); }
.svg-title { fill: var(--muted); font-size: 11px; font-weight: 600; font-family: var(--sans); letter-spacing: .04em; text-transform: uppercase; }
.svg-inverse { fill: #fff; font-size: 11px; font-family: var(--mono); }
.bar-track { fill: color-mix(in srgb, var(--edge) 55%, var(--panel)); }
.bar-fill { fill: var(--accent); stroke: none; }
.node, .node-alt, .cell { fill: color-mix(in srgb, var(--soft) 75%, var(--panel)); stroke: var(--edge); stroke-width: 1; }
.cell-empty { fill: color-mix(in srgb, var(--edge) 16%, var(--panel)); stroke: color-mix(in srgb, var(--edge) 45%, transparent); }
.lane { fill: color-mix(in srgb, var(--panel) 70%, transparent); stroke: var(--edge); }
.pill { fill: color-mix(in srgb, var(--accent) 12%, var(--panel)); stroke: color-mix(in srgb, var(--accent) 35%, var(--edge)); }
.edge, .edge-strong { stroke: var(--line); stroke-width: 1.4; fill: none; }
.edge-strong { stroke: var(--accent); stroke-opacity: .8; }
.edge-arrow { fill: var(--accent); }
.topo-node, .dep-node { cursor: pointer; }
.topo-node.dim, .dep-node.dim, [data-module].dim, .claim-item.dim, .test-row.dim { opacity: .2; }
.topo-node.hit .node, .dep-node.hit .node-alt { stroke: var(--accent); stroke-width: 2; }
[data-module].hit, .claim-item.hit { background: var(--soft); }

.test-matrix { width: 100%; border-collapse: collapse; margin: .5rem 0; font-size: .92rem; }
.test-matrix th, .test-matrix td { border-bottom: 1px solid var(--edge); padding: .65rem .55rem; text-align: left; }
.test-matrix th {
  font: 600 .68rem/1.2 var(--sans);
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
  border-bottom-color: var(--line);
}
.test-matrix .st-yes { color: var(--low); }
.test-matrix .st-no { color: var(--high); }
.test-matrix .st-unknown { color: var(--muted); }
.table-scroll { overflow-x: auto; }

.metro { list-style: none; margin: .4rem 0; padding: 0; position: relative; }
.metro::before {
  content: "";
  position: absolute; left: .7rem; top: .5rem; bottom: .5rem; width: 1px;
  background: var(--edge);
}
.metro-step { display: grid; grid-template-columns: 1.8rem 1fr; gap: .9rem; margin: 1rem 0; }
.metro-dot {
  width: 1.5rem; height: 1.5rem; border-radius: 50%;
  border: 1.5px solid var(--accent);
  background: var(--bg);
  display: flex; align-items: center; justify-content: center;
  font: 600 .7rem/1 var(--mono); color: var(--accent-ink); z-index: 1;
}
.metro-body h4 { margin: .15rem 0 .4rem; font: 600 1.05rem/1.2 var(--serif); }
.metro-body ul { margin: .2rem 0; padding-left: 1.1rem; }
.metro-body li { margin: .4rem 0; }

.appendix-grid {
  display: grid;
  gap: 1.4rem;
}
@media (min-width: 860px) {
  .appendix-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }

@media (max-width: 760px) {
  .cover-title { max-width: none; }
  .chapter-head { grid-template-columns: 2.2rem 1fr; }
  .mod-card { grid-template-columns: 1fr; }
  .mod-kind { grid-row: auto; }
  .mod-card .ev-chip { justify-self: start; }
  .ev-text { max-width: 24ch; }
  .chart { min-width: 480px; }
  .table-scroll, .diagram-stage { overflow-x: auto; }
  .chapter.band-map .diagram-stage,
  .chapter.band-alert .diagram-stage {
    margin-left: 0; margin-right: 0; padding-left: 0; padding-right: 0;
  }
}

@media print {
  :root { --bg: #fff; --ink: #000; --panel: #fff; --edge: #999; --muted: #444; --accent: #000; --accent-ink: #000; --soft: #f2f2f2; --band: #f7f7f7; }
  body { background: #fff; }
  .toc-rail, .ss-toggle, .filter-row, .ev-chip, .cover-tools { display: none !important; }
  .chapter, .hero { break-inside: avoid; }
  dialog#ev-drawer { display: none; }
  .chart { min-width: 0; }
}
.screenshot-mode .toc-rail,
.screenshot-mode .filter-row,
.screenshot-mode .ss-toggle { display: none; }
"""

    nav_js = """
(function(){
  function $(sel, ctx){ return (ctx||document).querySelectorAll(sel); }
  function clearHL(){
    $('[data-module]').forEach(function(el){ el.classList.remove('dim'); el.classList.remove('hit'); });
    $('.topo-node,.dep-node').forEach(function(el){ el.classList.remove('dim'); el.classList.remove('hit'); });
  }
  function highlightModule(mid){
    clearHL();
    if (!mid) return;
    var hit = false;
    $('[data-module]').forEach(function(el){
      if (el.getAttribute('data-module') === mid) { el.classList.add('hit'); hit = true; }
      else { el.classList.add('dim'); }
    });
    $('.topo-node,.dep-node').forEach(function(el){
      if (el.getAttribute('data-module') === mid) { el.classList.add('hit'); }
      else { el.classList.add('dim'); }
    });
  }
  var activeModule = null;
  document.addEventListener('click', function(e){
    var chip = e.target.closest && e.target.closest('.ev-chip');
    if (chip) {
      var drawer = document.getElementById('ev-drawer');
      if (drawer) {
        var dSec = drawer.querySelector('[data-drawer-section]');
        var dClaim = drawer.querySelector('[data-drawer-claim]');
        var dEv = drawer.querySelector('[data-drawer-evidence]');
        if (dSec) dSec.textContent = chip.getAttribute('data-section') || '';
        if (dClaim) dClaim.textContent = chip.getAttribute('data-claim') || '';
        if (dEv) dEv.textContent = chip.getAttribute('data-evidence') || '';
        if (typeof drawer.showModal === 'function') { drawer.showModal(); } else { drawer.setAttribute('open',''); }
      }
      return;
    }
    var fc = e.target.closest && e.target.closest('.filter-chip');
    if (fc) {
      var group = fc.getAttribute('data-filter-group');
      var val = fc.getAttribute('data-filter');
      var pressed = fc.getAttribute('aria-pressed') === 'true';
      $('[data-filter-group="' + group + '"]').forEach(function(b){ b.setAttribute('aria-pressed','false'); });
      if (pressed || val === '') {
        // clear filter
        $('[data-module]').forEach(function(el){ el.classList.remove('dim'); });
      } else {
        fc.setAttribute('aria-pressed','true');
        var items = group === 'severity' ? $('.claim-item[data-severity]') : $('.test-row[data-status]');
        items.forEach(function(el){
          var attr = group === 'severity' ? el.getAttribute('data-severity') : el.getAttribute('data-status');
          if (val === attr) { el.classList.remove('dim'); }
          else { el.classList.add('dim'); }
        });
      }
      return;
    }
    var node = e.target.closest && e.target.closest('.topo-node,.dep-node,.risk-cell');
    if (node) {
      var mid = node.getAttribute('data-module');
      if (mid) {
        if (activeModule === mid) { clearHL(); activeModule = null; }
        else { highlightModule(mid); activeModule = mid; }
      }
    }
  });
  var ssBtn = document.querySelector('[data-screenshot]');
  if (ssBtn) {
    ssBtn.addEventListener('click', function(){
      var on = document.body.classList.toggle('screenshot-mode');
      ssBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }
  var links = $('.toc-rail a');
  if (links.length && 'IntersectionObserver' in window) {
    var map = {};
    links.forEach(function(a){ var id = a.getAttribute('href').slice(1); var s = document.getElementById(id); if (s) map[id] = a; });
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(en){
        if (en.isIntersecting) {
          links.forEach(function(l){ l.classList.remove('active'); });
          if (map[en.target.id]) map[en.target.id].classList.add('active');
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px' });
    Object.keys(map).forEach(function(id){ io.observe(document.getElementById(id)); });
  }
})();
"""

    return f"""<!doctype html>
<html lang="{esc(t(lang, "html_lang"))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>{css}</style>
</head>
<body>
<main>
{''.join(body_parts)}
</main>
<script>{nav_js}</script>
<script id="report-data" type="application/json">
{json_for_script(data)}
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate offline repo learning HTML report")
    parser.add_argument("--input", required=True, help="Path to report_data.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--mode", default="single", choices=["single"], help="Output mode")
    parser.add_argument("--title", help="Override HTML title")
    parser.add_argument("--lang", default=None, help="UI language: zh (default) or en")
    parser.add_argument("--strict", action="store_true", help="Require evidence-rich fields")
    parser.add_argument("--validate-only", action="store_true", help="Validate JSON only")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print("error: root JSON must be an object", file=sys.stderr)
        return 1

    errors = collect_errors(data, strict=args.strict)
    if errors:
        for err in errors:
            print(f"error: {err}", file=sys.stderr)
        return 1

    if args.validate_only:
        print("validation ok")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "index.html"
    html_path.write_text(build_html(data, args.title, lang=args.lang), encoding="utf-8")
    print(f"wrote {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
