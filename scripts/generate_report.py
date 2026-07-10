#!/usr/bin/env python3
"""Generate a self-contained, unstyled repository learning website."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schema_validate import collect_errors


SEVERITY = {"high": (3, "高"), "medium": (2, "中"), "low": (1, "低")}
KIND_LABEL = {
    "entry": "入口",
    "ui": "界面",
    "frontend": "前端",
    "service": "服务",
    "backend": "后端",
    "domain": "领域",
    "lib": "基础能力",
    "data": "数据",
    "database": "存储",
    "external": "外部系统",
    "test": "测试",
    "config": "配置",
    "other": "模块",
}


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def text(value: Any) -> str:
    return "" if value is None else str(value)


def label(item: dict[str, Any]) -> str:
    for key in ("title", "name", "text", "label", "summary", "description"):
        if item.get(key) not in (None, ""):
            return text(item[key])
    return ""


def evidence_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text(item) for item in value if item not in (None, "")]
    return [text(value)] if value not in (None, "") else []


def evidence(value: Any) -> str:
    values = evidence_values(value)
    if not values:
        return ""
    sources = "".join(f"<code>{esc(item)}</code>" for item in values)
    return f'<span aria-label="源码证据">{sources}</span>'


def json_for_script(data: dict[str, Any]) -> str:
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def normalise(data: dict[str, Any]) -> dict[str, Any]:
    """Convert the legacy report schema into the looser storytelling schema."""
    if data.get("schema_version") == "2":
        return data

    meta = data.get("meta") or {}
    overview = data.get("overview") or {}
    dependencies = data.get("dependencies") or {}
    appendix = data.get("appendix") or {}
    roadmap = data.get("roadmap") or []
    return {
        "schema_version": "2",
        "project": {
            "name": meta.get("repo_name") or "Repository",
            "source": meta.get("repo_path") or "",
            "tagline": overview.get("elevator_pitch") or overview.get("summary") or "",
            "summary": overview.get("summary") or "",
            "generated_at": meta.get("generated_at"),
            "mode": meta.get("mode"),
        },
        "languages": overview.get("languages") or [],
        "highlights": overview.get("claims") or [],
        "modules": data.get("modules") or [],
        "connections": (data.get("topology") or {}).get("edges") or dependencies.get("internal") or [],
        "external_dependencies": dependencies.get("external") or [],
        "flows": data.get("flows") or [],
        "concepts": data.get("concepts") or [],
        "code_map": [
            item if isinstance(item, dict) else {"path": item, "role": "已调查文件"}
            for item in appendix.get("files_examined") or []
        ],
        "quick_start": data.get("quick_start") or [],
        "tests": data.get("tests") or {},
        "learning_path": [
            {
                "title": item.get("title") or f"阶段 {item.get('phase', index + 1)}",
                "outcome": item.get("outcome") or "",
                "items": item.get("items") or [],
                "evidence": item.get("evidence"),
            }
            for index, item in enumerate(roadmap)
            if isinstance(item, dict)
        ],
        "risks": data.get("risks") or [],
        "gaps": (appendix.get("gaps") or []) + (appendix.get("open_questions") or []),
    }


def language_bars(languages: list[dict[str, Any]]) -> str:
    if not languages:
        return ""
    rows = []
    for item in languages[:8]:
        percent = max(0.0, float(item.get("percent") or 0))
        rows.append(
            f"<div><dt>{esc(item.get('name') or 'Unknown')}</dt>"
            f"<dd>{percent:g}%</dd></div>"
        )
    return '<section><h3>语言构成</h3><dl>' + "".join(rows) + "</dl></section>"


def highlight_list(items: list[Any]) -> str:
    rows = []
    for item in items[:8]:
        if isinstance(item, str):
            rows.append(f'<li><span>{esc(item)}</span></li>')
        elif isinstance(item, dict):
            rows.append(f'<li><span>{esc(label(item))}</span>{evidence(item.get("evidence"))}</li>')
    if not rows:
        return ""
    return '<ul class="highlight-list">' + "".join(rows) + "</ul>"


def module_layer(module: dict[str, Any]) -> str:
    return text(module.get("layer") or module.get("kind") or "other").strip().lower() or "other"


def architecture_svg(modules: list[dict[str, Any]], connections: list[dict[str, Any]]) -> str:
    visible = [module for module in modules if isinstance(module, dict) and module.get("id")]
    if not visible:
        return '<div class="empty-state"><strong>还没有架构图</strong><span>补充 modules 和 connections 后会自动生成。</span></div>'

    layers: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for module in visible:
        layer = module_layer(module)
        if layer not in layers:
            layers.append(layer)
        grouped.setdefault(layer, []).append(module)

    column_width = 220
    node_width = 172
    node_height = 72
    gap_y = 28
    width = max(720, 80 + len(layers) * column_width)
    tallest = max(len(grouped[layer]) for layer in layers)
    height = max(330, 96 + tallest * (node_height + gap_y))
    positions: dict[str, tuple[float, float]] = {}
    node_parts: list[str] = []

    for column, layer in enumerate(layers):
        x = 44 + column * column_width
        layer_name = KIND_LABEL.get(layer, layer.replace("_", " ").title())
        node_parts.append(f'<text class="arch-layer" x="{x}" y="34">{esc(layer_name)}</text>')
        for row, module in enumerate(grouped[layer]):
            y = 58 + row * (node_height + gap_y)
            module_id = text(module["id"])
            positions[module_id] = (x, y)
            name = text(module.get("name") or module_id)
            role = text(module.get("role") or module.get("description") or "")
            if len(role) > 34:
                role = role[:33] + "…"
            node_parts.append(
                f'<g class="arch-node" data-module="{esc(module_id)}" tabindex="0" role="button">'
                f'<rect x="{x}" y="{y}" width="{node_width}" height="{node_height}" rx="14"/>'
                f'<text class="arch-name" x="{x + 16}" y="{y + 29}">{esc(name)}</text>'
                f'<text class="arch-role" x="{x + 16}" y="{y + 50}">{esc(role)}</text></g>'
            )

    edge_parts: list[str] = []
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        source = text(connection.get("from"))
        target = text(connection.get("to"))
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        start_x, start_y = sx + node_width, sy + node_height / 2
        end_x, end_y = tx, ty + node_height / 2
        if tx <= sx:
            start_x, start_y = sx + node_width / 2, sy + node_height
            end_x, end_y = tx + node_width / 2, ty
        bend = (start_x + end_x) / 2
        relation = text(connection.get("label") or connection.get("type") or "连接")
        source_note = "; ".join(evidence_values(connection.get("evidence")))
        title = relation + (f" | {source_note}" if source_note else "")
        label_x, label_y = bend, (start_y + end_y) / 2 - 7
        edge_parts.append(
            f'<g class="arch-link"><title>{esc(title)}</title>'
            f'<path class="arch-edge" data-from="{esc(source)}" data-to="{esc(target)}" '
            f'd="M {start_x:.1f} {start_y:.1f} C {bend:.1f} {start_y:.1f}, {bend:.1f} {end_y:.1f}, {end_x:.1f} {end_y:.1f}"/>'
            f'<text class="arch-edge-label" x="{label_x:.1f}" y="{label_y:.1f}">{esc(relation)}</text></g>'
        )

    names = {text(module.get("id")): text(module.get("name") or module.get("id")) for module in visible}
    legend_items = []
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        source, target = text(connection.get("from")), text(connection.get("to"))
        if source not in positions or target not in positions:
            continue
        legend_items.append(
            f'<li><span><strong>{esc(names.get(source, source))}</strong><i>→</i><strong>{esc(names.get(target, target))}</strong>'
            f'<em>{esc(connection.get("label") or connection.get("type") or "连接")}</em></span>{evidence(connection.get("evidence"))}</li>'
        )
    legend = '<ol class="connection-legend">' + "".join(legend_items) + "</ol>" if legend_items else ""
    return (
        '<div class="architecture-canvas"><svg class="architecture" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="项目架构图">'
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>'
        + "".join(edge_parts)
        + "".join(node_parts)
        + f'</svg><p class="diagram-help">悬停模块可以追踪直接关系</p>{legend}</div>'
    )


def module_index(modules: list[dict[str, Any]]) -> str:
    cards = []
    for module in modules:
        if not isinstance(module, dict):
            continue
        module_id = text(module.get("id"))
        cards.append(
            f'<article class="module-card" data-module-card="{esc(module_id)}">'
            f'<span class="module-kind">{esc(KIND_LABEL.get(module_layer(module), module_layer(module)))}</span>'
            f'<h3>{esc(module.get("name") or module_id)}</h3>'
            f'<p>{esc(module.get("role") or module.get("description") or "")}</p>'
            f'{evidence(module.get("evidence"))}</article>'
        )
    return '<div class="module-grid">' + "".join(cards) + "</div>" if cards else ""


def flow_sections(flows: list[dict[str, Any]]) -> str:
    blocks = []
    for flow in flows:
        if not isinstance(flow, dict):
            continue
        steps = []
        for index, step in enumerate(flow.get("steps") or []):
            if isinstance(step, str):
                step_label, source = step, None
            elif isinstance(step, dict):
                step_label, source = label(step), step.get("evidence")
            else:
                continue
            module = text(step.get("module")) if isinstance(step, dict) else ""
            module_html = f'<small>{esc(module)}</small>' if module else ""
            steps.append(
                f'<li><span class="step-number">{index + 1}</span><div>{module_html}<strong>{esc(step_label)}</strong>{evidence(source)}</div></li>'
            )
        blocks.append(
            '<article class="flow-story">'
            f'<header><h3>{esc(flow.get("title") or flow.get("name") or flow.get("id") or "关键流程")}</h3>'
            f'<p>{esc(flow.get("summary") or "")}</p></header>'
            f'<ol>{"".join(steps)}</ol></article>'
        )
    return '<div class="flow-stack">' + "".join(blocks) + "</div>" if blocks else ""


def concept_grid(concepts: list[dict[str, Any]]) -> str:
    cards = []
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        cards.append(
            '<article class="concept-card">'
            f'<h3>{esc(concept.get("name") or concept.get("title") or "概念")}</h3>'
            f'<p>{esc(concept.get("explanation") or concept.get("description") or "")}</p>'
            f'<strong class="why">{esc(concept.get("why_it_matters") or "")}</strong>'
            f'{evidence(concept.get("evidence"))}</article>'
        )
    return '<div class="concept-grid">' + "".join(cards) + "</div>" if cards else ""


def ecosystem_grid(items: list[dict[str, Any]]) -> str:
    cards = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cards.append(
            '<article class="ecosystem-card">'
            f'<span>{esc(item.get("type") or "dependency")}</span>'
            f'<h3>{esc(item.get("name") or "外部依赖")}</h3>'
            f'<p>{esc(item.get("role") or item.get("description") or "")}</p>'
            f'{evidence(item.get("evidence"))}</article>'
        )
    return '<div class="ecosystem-grid">' + "".join(cards) + "</div>" if cards else ""


def test_map(tests: dict[str, Any]) -> str:
    if not isinstance(tests, dict):
        return ""
    cards = []
    for item in tests.get("matrix") or []:
        if not isinstance(item, dict):
            continue
        statuses = []
        for key, name in (("unit", "单元"), ("integration", "集成"), ("e2e", "端到端")):
            value = item.get(key)
            state = "有" if value is True else ("缺" if value is False else "未知")
            class_name = "yes" if value is True else ("no" if value is False else "unknown")
            statuses.append(f'<span class="test-status {class_name}">{name} {state}</span>')
        cards.append(
            '<article class="test-card">'
            f'<h3>{esc(item.get("area") or "测试区域")}</h3><div>{"".join(statuses)}</div>'
            f'{evidence(item.get("evidence"))}</article>'
        )
    notes = text(tests.get("coverage_notes") or tests.get("notes"))
    notes_html = f'<p class="test-notes">{esc(notes)}</p>' if notes else ""
    grid = '<div class="test-grid">' + "".join(cards) + "</div>" if cards else ""
    return notes_html + grid if notes_html or grid else ""


def code_atlas(items: list[dict[str, Any]]) -> str:
    cards = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or item.get("file") or label(item)
        cards.append(
            '<article class="file-card">'
            f'<code>{esc(path)}</code><h3>{esc(item.get("role") or item.get("title") or "")}</h3>'
            f'<p>{esc(item.get("read_when") or item.get("description") or "")}</p>'
            f'{evidence(item.get("evidence"))}</article>'
        )
    return '<div class="file-atlas">' + "".join(cards) + "</div>" if cards else ""


def quick_start(items: list[Any]) -> str:
    rows = []
    for item in items:
        if isinstance(item, str):
            title, command, note = "运行", item, ""
        elif isinstance(item, dict):
            title = item.get("title") or item.get("label") or "运行"
            command = item.get("command") or item.get("text") or ""
            note = item.get("note") or item.get("description") or ""
        else:
            continue
        rows.append(
            f'<article class="command-card"><h3>{esc(title)}</h3><p>{esc(note)}</p>'
            f'<pre><code>{esc(command)}</code></pre></article>'
        )
    return '<div class="command-list">' + "".join(rows) + "</div>" if rows else ""


def learning_timeline(items: list[dict[str, Any]]) -> str:
    rows = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        sources = []
        for source in item.get("items") or item.get("files") or []:
            if isinstance(source, str):
                sources.append(f'<code>{esc(source)}</code>')
            elif isinstance(source, dict):
                sources.append(f'<code>{esc(label(source))}</code>')
        rows.append(
            f'<li><span>{index + 1}</span><article><h3>{esc(item.get("title") or "继续探索")}</h3>'
            f'<p>{esc(item.get("outcome") or item.get("description") or "")}</p>'
            f'<div class="learning-files">{"".join(sources)}</div>{evidence(item.get("evidence"))}</article></li>'
        )
    return '<ol class="learning-path">' + "".join(rows) + "</ol>" if rows else ""


def risk_cards(risks: list[dict[str, Any]]) -> str:
    ordered = sorted(
        [risk for risk in risks if isinstance(risk, dict)],
        key=lambda item: -SEVERITY.get(text(item.get("severity")).lower(), (2, "中"))[0],
    )
    rows = []
    for risk in ordered:
        severity = text(risk.get("severity")).lower()
        severity = severity if severity in SEVERITY else "medium"
        rows.append(
            f'<article class="risk-card risk-{severity}"><span>{SEVERITY[severity][1]}风险</span>'
            f'<h3>{esc(label(risk) or "待确认风险")}</h3>'
            f'<p>{esc(risk.get("impact") or risk.get("description") or "")}</p>'
            f'{evidence(risk.get("evidence"))}</article>'
        )
    return '<div class="risk-grid">' + "".join(rows) + "</div>" if rows else ""


def gaps_panel(items: list[Any]) -> str:
    values = []
    for item in items:
        if isinstance(item, str):
            values.append(f"<li>{esc(item)}</li>")
        elif isinstance(item, dict):
            values.append(f"<li>{esc(label(item))}{evidence(item.get('evidence'))}</li>")
    return '<ul class="gap-list">' + "".join(values) + "</ul>" if values else ""


def hero_graph(
    modules: list[dict[str, Any]], connections: list[dict[str, Any]], project_name: str
) -> str:
    """Render a cinematic, data-backed preview of the repository architecture."""
    visible = [item for item in modules if isinstance(item, dict) and item.get("id")][:12]
    if not visible:
        return f'<div class="hero-wordmark">{esc(project_name)}</div>'

    width, height = 1080, 520
    cx, cy, rx, ry = width / 2, height / 2, 410, 165
    positions: dict[str, tuple[float, float]] = {}
    nodes = []
    for index, module in enumerate(visible):
        angle = -math.pi / 2 + index * (2 * math.pi / len(visible))
        x, y = cx + math.cos(angle) * rx, cy + math.sin(angle) * ry
        module_id = text(module.get("id"))
        positions[module_id] = (x, y)
        nodes.append(
            f'<g class="hero-node"><circle cx="{x:.1f}" cy="{y:.1f}" r="7"/>'
            f'<text x="{x:.1f}" y="{y + 28:.1f}">{esc(module.get("name") or module_id)}</text></g>'
        )

    edges = []
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        source, target = text(connection.get("from")), text(connection.get("to"))
        if source not in positions or target not in positions:
            continue
        sx, sy = positions[source]
        tx, ty = positions[target]
        edges.append(f'<path d="M {sx:.1f} {sy:.1f} Q {cx:.1f} {cy:.1f} {tx:.1f} {ty:.1f}"/>')

    initials = "".join(part[:1] for part in project_name.split()[:2]).upper() or project_name[:2].upper()
    omitted = len(modules) - len(visible)
    more = f'<text class="hero-more" x="{width - 34}" y="{height - 26}" text-anchor="end">另有 {omitted} 个模块</text>' if omitted > 0 else ""
    return (
        f'<svg class="hero-graph" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(project_name)} 架构预览">'
        f'<g class="hero-edges">{"".join(edges)}</g><text class="hero-initials" x="{cx}" y="{cy + 22}" text-anchor="middle">{esc(initials)}</text>'
        f'{"".join(nodes)}{more}</svg>'
    )


def section(section_id: str, title: str, intro: str, content: str, class_name: str = "") -> str:
    if not content:
        return ""
    return (
        f'<section id="{section_id}" class="story-section {esc(class_name)}">'
        f'<header class="section-title"><h2>{esc(title)}</h2><p>{esc(intro)}</p></header>{content}</section>'
    )


def build_html(raw: dict[str, Any], title: str | None = None) -> str:
    data = normalise(raw)
    project = data.get("project") or {}
    modules = data.get("modules") or []
    connections = data.get("connections") or []
    flows = data.get("flows") or []
    concepts = data.get("concepts") or []
    code_map = data.get("code_map") or []
    learning = data.get("learning_path") or []
    risks = data.get("risks") or []
    external_dependencies = data.get("external_dependencies") or []
    tests = data.get("tests") or {}
    page_title = text(title or project.get("name") or "Repository")
    tagline = text(project.get("tagline") or project.get("summary") or "从全局架构到第一行代码")
    summary = text(project.get("summary") or project.get("tagline") or "")
    source = text(project.get("source") or "")
    generated = text(project.get("generated_at") or datetime.now(timezone.utc).isoformat())

    highlights = data.get("highlights") or []
    languages = data.get("languages") or []
    intro_content = f'<p class="project-summary">{esc(summary)}</p>' if summary else ""
    if highlights or languages:
        intro_content += '<div class="overview-layout"><div>' + highlight_list(highlights) + "</div>"
        intro_content += language_bars(languages) + "</div>"
    architecture = architecture_svg(modules, connections) + module_index(modules)
    sections = [
        ("overview", "先建立整体认识", "用几条判断抓住项目的角色、边界和价值。", intro_content, "overview-section"),
        ("architecture", "系统是怎么拼起来的", "模块和连接构成项目的运行骨架。", architecture if modules else "", "architecture-section"),
        ("flows", "跟着一次真实流程走", "不要背目录，从触发点一路看到结果。", flow_sections(flows), "flows-section"),
        ("concepts", "先理解这些概念", "掌握项目自己的语言，再进入实现细节。", concept_grid(concepts), "concepts-section"),
        ("ecosystem", "它依赖哪些外部能力", "框架、服务和基础设施构成项目的外部边界。", ecosystem_grid(external_dependencies), "ecosystem-section"),
        ("code", "代码地图", "这些文件是理解系统的最佳入口。", code_atlas(code_map), "code-section"),
        ("run", "把项目跑起来", "命令只展示，不会由报告自动执行。", quick_start(data.get("quick_start") or []), "run-section"),
        ("tests", "如何验证改动", "测试分布会告诉你哪里有保护，哪里需要更谨慎。", test_map(tests), "tests-section"),
        ("learn", "推荐学习顺序", "每一步都对应一个明确的理解目标。", learning_timeline(learning), "learn-section"),
        ("risks", "理解它的边界", "风险和未知项同样是项目认知的一部分。", risk_cards(risks), "risks-section"),
        ("gaps", "还没有确认的部分", "这些问题需要运行环境、维护者或更深调查才能回答。", gaps_panel(data.get("gaps") or []), "gaps-section"),
    ]
    active_sections = [item for item in sections if item[3]]
    nav_priority = {"overview", "architecture", "flows", "concepts", "code", "learn"}
    nav = "".join(
        f'<a href="#{sid}">{esc(name)}</a>'
        for sid, name, _intro, _content, _cls in active_sections
        if sid in nav_priority
    )
    body = "".join(section(*item) for item in active_sections)
    primary_target = active_sections[0][0] if active_sections else "about"
    repo_link = ""
    if source.startswith(("http://", "https://")):
        repo_link = f'<a class="button button-secondary" href="{esc(source)}" target="_blank" rel="noreferrer">查看源码</a>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(tagline)}">
<title>{esc(page_title)} | 项目学习站</title>
</head>
<body>
<a class="skip-link" href="#main">跳到正文</a>
<header class="site-header">
  <a class="brand" href="#top">Repo Learning</a>
  <nav aria-label="主要章节">{nav}</nav>
</header>
<main id="main">
  <section id="top" class="hero">
    <div class="hero-copy">
      <p class="hero-kicker">项目学习站</p>
      <h1>{esc(page_title)}</h1>
      <p class="tagline">{esc(tagline)}</p>
      <div class="hero-actions"><a class="button button-primary" href="#{primary_target}">开始理解</a>{repo_link}</div>
    </div>
    <figure class="hero-visual">{hero_graph(modules, connections, page_title)}
      <figcaption><span>{esc(source)}</span><time>{esc(generated[:10])}</time></figcaption>
    </figure>
  </section>
  {body}
  <section id="about" class="closing">
    <h2>现在你已经有了一张地图。</h2>
    <p>下一步不是继续浏览摘要，而是沿着学习路径进入真实源码。</p>
    <a class="button button-primary" href="#top">回到顶部</a>
  </section>
</main>
<footer><span>{esc(page_title)} 学习站</span><span>由源码证据生成</span></footer>
<script id="site-data" type="application/json">{json_for_script(data)}</script>
</body>
</html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a repository learning website")
    parser.add_argument("--input", required=True, help="Path to site_data.json or legacy report_data.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--mode", default="site", choices=["site", "single"], help="Compatibility option")
    parser.add_argument("--title", help="Override the page title")
    parser.add_argument("--strict", action="store_true", help="Validate core identity and graph integrity")
    parser.add_argument("--validate-only", action="store_true", help="Validate data without generating HTML")
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
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    if args.validate_only:
        print("validation ok")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "index.html"
    output.write_text(build_html(data, args.title), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
