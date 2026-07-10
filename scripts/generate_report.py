#!/usr/bin/env python3
"""Generate a visual, self-contained repository learning website."""

from __future__ import annotations

import argparse
import html
import json
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
    chips = "".join(
        f'<button class="source-chip" type="button" data-copy-source="{esc(item)}" title="复制源码位置">{esc(item)}</button>'
        for item in values
    )
    return f'<span class="source-list">{chips}</span>'


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
    total = sum(max(0.0, float(item.get("percent") or 0)) for item in languages) or 1
    rows = []
    for item in languages[:8]:
        percent = max(0.0, float(item.get("percent") or 0))
        width = min(100.0, percent / total * 100 if total > 100 else percent)
        rows.append(
            '<div class="language-row">'
            f'<span>{esc(item.get("name") or "Unknown")}</span>'
            f'<span class="language-line"><i style="--value:{width:.2f}%"></i></span>'
            f'<strong>{percent:g}%</strong></div>'
        )
    return '<div class="language-card"><h3>语言构成</h3>' + "".join(rows) + "</div>"


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
            f'<article class="command-card"><div><strong>{esc(title)}</strong><p>{esc(note)}</p></div>'
            f'<button type="button" data-copy-command="{esc(command)}"><code>{esc(command)}</code><span>复制</span></button></article>'
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


def section(section_id: str, title: str, intro: str, content: str, class_name: str = "") -> str:
    if not content:
        return ""
    return (
        f'<section id="{section_id}" class="story-section {esc(class_name)} reveal">'
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
    hero_size = " hero-long" if len(page_title) > 14 else ""
    if len(page_title) > 28:
        hero_size = " hero-very-long"
    tagline = text(project.get("tagline") or project.get("summary") or "从全局架构到第一行代码")
    summary = text(project.get("summary") or project.get("tagline") or "")
    source = text(project.get("source") or "")
    generated = text(project.get("generated_at") or datetime.now(timezone.utc).isoformat())

    intro_content = '<div class="overview-layout"><div>' + highlight_list(data.get("highlights") or []) + '</div>'
    intro_content += language_bars(data.get("languages") or []) + "</div>"
    architecture = architecture_svg(modules, connections) + module_index(modules)
    sections = [
        ("overview", "先建立整体认识", "用几条判断抓住项目的角色、边界和价值。", intro_content if (data.get("highlights") or data.get("languages")) else "", "overview-section"),
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
    nav = "".join(f'<a href="#{sid}">{esc(name)}</a>' for sid, name, _intro, _content, _cls in active_sections)
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
<style>{CSS}</style>
</head>
<body>
<a class="skip-link" href="#main">跳到正文</a>
<header class="site-header">
  <a class="brand" href="#top"><span class="brand-mark">R</span><span>Repo Learning</span></a>
  <nav aria-label="主要章节">{nav}</nav>
  <button class="theme-toggle" type="button" data-theme-toggle aria-label="切换深浅主题"><span>主题</span><b aria-hidden="true">◐</b></button>
</header>
<main id="main">
  <section id="top" class="hero{hero_size}">
    <div class="hero-copy reveal">
      <p class="eyebrow">项目学习站</p>
      <h1>{esc(page_title)}</h1>
      <p class="tagline">{esc(tagline)}</p>
      <p class="hero-summary">{esc(summary)}</p>
      <div class="hero-actions"><a class="button button-primary" href="#{primary_target}">开始理解</a>{repo_link}</div>
    </div>
    <div class="hero-visual reveal" aria-label="项目概览">
      <div class="visual-orbit">
        <span class="orbit-core">{esc(page_title[:2].upper())}</span>
        <span class="orbit-label orbit-a">{len(modules)} 个模块</span>
        <span class="orbit-label orbit-b">{len(flows)} 条流程</span>
        <span class="orbit-label orbit-c">{len(code_map)} 个入口</span>
        <i class="orbit-ring ring-a"></i><i class="orbit-ring ring-b"></i>
      </div>
    </div>
    <div class="hero-meta"><span>{esc(source)}</span><time>{esc(generated[:10])}</time></div>
  </section>
  {body}
  <section id="about" class="closing reveal">
    <h2>现在你已经有了一张地图。</h2>
    <p>下一步不是继续浏览摘要，而是沿着学习路径进入真实源码。</p>
    <a class="button button-primary" href="#top">回到顶部</a>
  </section>
</main>
<footer><span>{esc(page_title)} 学习站</span><span>由源码证据生成</span></footer>
<div class="toast" role="status" aria-live="polite"></div>
<script>{JS}</script>
<script id="site-data" type="application/json">{json_for_script(data)}</script>
</body>
</html>"""


CSS = r"""
:root{color-scheme:light dark;--bg:#f4f6f8;--surface:#fbfcfd;--surface-2:#e9eef5;--ink:#111827;--muted:#526071;--line:#cbd5e1;--accent:#175cd3;--accent-strong:#0b45a5;--accent-soft:#dce9ff;--danger:#b42318;--warning:#b54708;--radius:18px;--max:1240px;--shadow:0 24px 80px rgba(28,45,75,.12);--sans:"Avenir Next","Segoe UI","PingFang SC",system-ui,sans-serif;--mono:"SFMono-Regular",Consolas,"Liberation Mono",monospace}
html[data-theme="dark"]{--bg:#0e1420;--surface:#151e2d;--surface-2:#1c293d;--ink:#eef4ff;--muted:#9eacc1;--line:#30415a;--accent:#77a7ff;--accent-strong:#a9c7ff;--accent-soft:#1c3762;--danger:#ff8a82;--warning:#ffb36b;--shadow:0 28px 90px rgba(0,0,0,.34)}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1420;--surface:#151e2d;--surface-2:#1c293d;--ink:#eef4ff;--muted:#9eacc1;--line:#30415a;--accent:#77a7ff;--accent-strong:#a9c7ff;--accent-soft:#1c3762;--danger:#ff8a82;--warning:#ffb36b;--shadow:0 28px 90px rgba(0,0,0,.34)}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:400 16px/1.65 var(--sans);-webkit-font-smoothing:antialiased}button,a{font:inherit}a{color:inherit}.skip-link{position:fixed;left:1rem;top:-5rem;z-index:30;background:var(--ink);color:var(--bg);padding:.7rem 1rem;border-radius:10px}.skip-link:focus{top:1rem}
.site-header{height:72px;position:sticky;top:0;z-index:20;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:2rem;padding:0 max(1.25rem,calc((100vw - var(--max))/2));background:color-mix(in srgb,var(--bg) 88%,transparent);border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent);backdrop-filter:blur(18px)}.brand{display:flex;align-items:center;gap:.65rem;text-decoration:none;font-weight:750;white-space:nowrap}.brand-mark{display:grid;place-items:center;width:34px;height:34px;border-radius:11px;background:var(--accent);color:#f8fbff;font-weight:900}.site-header nav{display:flex;justify-content:center;gap:.15rem;overflow-x:auto;scrollbar-width:none}.site-header nav a{padding:.45rem .7rem;border-radius:9px;text-decoration:none;color:var(--muted);font-size:.85rem;white-space:nowrap}.site-header nav a:hover,.site-header nav a.active{color:var(--accent-strong);background:var(--accent-soft)}.theme-toggle{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:10px;padding:.45rem .7rem;cursor:pointer}.theme-toggle b{display:none}.theme-toggle:active,.button:active{transform:translateY(1px)}
main{overflow:hidden}.hero{min-height:calc(100dvh - 72px);max-width:var(--max);margin:0 auto;padding:clamp(3rem,8vh,6rem) 1.5rem 2rem;display:grid;grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr);grid-template-rows:1fr auto;gap:2rem 4rem;align-items:center}.hero-copy{max-width:690px}.eyebrow{margin:0 0 1.2rem;color:var(--accent-strong);font-size:.76rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}.hero h1{margin:0;font-size:clamp(3.5rem,8vw,7.2rem);line-height:.92;letter-spacing:-.065em;word-break:break-word}.hero-long h1{font-size:clamp(3rem,6vw,5.7rem)}.hero-very-long h1{font-size:clamp(2.5rem,4.8vw,4.5rem);line-height:1}.tagline{max-width:650px;margin:1.6rem 0 .8rem;font-size:clamp(1.35rem,2.2vw,2rem);font-weight:650;line-height:1.25;letter-spacing:-.02em}.hero-summary{max-width:60ch;margin:0;color:var(--muted);font-size:1.02rem}.hero-actions{display:flex;gap:.75rem;flex-wrap:wrap;margin-top:2rem}.button{display:inline-flex;justify-content:center;align-items:center;min-height:46px;padding:.75rem 1.05rem;border-radius:12px;text-decoration:none;font-weight:750;white-space:nowrap;transition:transform .2s ease,background .2s ease}.button-primary{background:var(--accent);color:#f8fbff}.button-primary:hover{background:var(--accent-strong)}.button-secondary{border:1px solid var(--line);background:var(--surface)}
.hero-visual{display:grid;place-items:center;min-height:480px}.visual-orbit{position:relative;width:min(35vw,430px);aspect-ratio:1;border-radius:50%;background:radial-gradient(circle at 42% 38%,var(--surface),var(--surface-2));box-shadow:var(--shadow)}.orbit-core{position:absolute;inset:37%;display:grid;place-items:center;border-radius:var(--radius);background:var(--accent);color:#f8fbff;font-size:clamp(1.5rem,3vw,2.5rem);font-weight:900;letter-spacing:-.08em;z-index:3}.orbit-ring{position:absolute;border:1px solid var(--line);border-radius:50%;inset:16%}.ring-b{inset:29%}.orbit-label{position:absolute;z-index:4;padding:.5rem .7rem;border:1px solid var(--line);border-radius:11px;background:var(--surface);box-shadow:0 12px 30px rgba(27,42,70,.1);font:700 .8rem/1 var(--mono)}.orbit-a{left:-4%;top:19%}.orbit-b{right:-3%;top:44%}.orbit-c{left:13%;bottom:5%}.hero-meta{grid-column:1/-1;display:flex;justify-content:space-between;gap:1rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--muted);font:500 .76rem/1.4 var(--mono);word-break:break-all}
.story-section{max-width:var(--max);margin:0 auto;padding:clamp(5rem,10vw,9rem) 1.5rem;scroll-margin-top:88px}.section-title{max-width:780px;margin-bottom:3rem}.section-title h2{margin:0;font-size:clamp(2.2rem,5vw,4.8rem);line-height:1;letter-spacing:-.055em}.section-title p{max-width:54ch;margin:1rem 0 0;color:var(--muted);font-size:1.05rem}.overview-layout{display:grid;grid-template-columns:1.3fr .7fr;gap:2rem}.highlight-list{list-style:none;margin:0;padding:0}.highlight-list li{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;padding:1rem 0;border-bottom:1px solid var(--line);font-size:1.05rem}.language-card{padding:1.4rem;background:var(--surface);border-radius:var(--radius);box-shadow:var(--shadow)}.language-card h3{margin:0 0 1rem}.language-row{display:grid;grid-template-columns:84px 1fr 46px;align-items:center;gap:.7rem;margin:.7rem 0;font-size:.78rem}.language-row strong{text-align:right;font-family:var(--mono)}.language-line{height:4px;background:var(--line);border-radius:99px;overflow:hidden}.language-line i{display:block;width:var(--value);height:100%;background:var(--accent)}
.architecture-section{max-width:none;background:var(--surface-2)}.architecture-section>.section-title,.architecture-section>.architecture-canvas,.architecture-section>.module-grid{max-width:var(--max);margin-left:auto;margin-right:auto}.architecture-canvas{overflow-x:auto;padding:1rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--bg);box-shadow:var(--shadow)}.architecture{display:block;width:100%;min-width:720px;height:auto}.architecture marker path{fill:var(--line)}.arch-edge{fill:none;stroke:var(--line);stroke-width:1.5;marker-end:url(#arrow);transition:opacity .2s ease,stroke .2s ease}.arch-edge-label{fill:var(--muted);stroke:var(--bg);stroke-width:5px;paint-order:stroke;stroke-linejoin:round;text-anchor:middle;font:700 10px var(--mono)}.arch-node{cursor:pointer;outline:none}.arch-node rect{fill:var(--surface);stroke:var(--line);transition:fill .2s ease,stroke .2s ease}.arch-node:hover rect,.arch-node:focus rect,.arch-node.is-active rect{fill:var(--accent-soft);stroke:var(--accent)}.arch-edge.is-active{stroke:var(--accent);stroke-width:2.5}.architecture.has-focus .arch-edge:not(.is-active),.architecture.has-focus .arch-node:not(.is-active){opacity:.22}.arch-layer{fill:var(--muted);font:800 12px var(--sans);letter-spacing:.08em;text-transform:uppercase}.arch-name{fill:var(--ink);font:750 14px var(--sans)}.arch-role{fill:var(--muted);font:11px var(--sans)}.diagram-help{margin:.7rem 0;color:var(--muted);font-size:.78rem}.connection-legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.5rem 1rem;margin:1.2rem 0 0;padding:1rem 0 0;border-top:1px solid var(--line);list-style:none}.connection-legend li{display:flex;justify-content:space-between;gap:.7rem;align-items:center;min-width:0}.connection-legend li>span{display:flex;gap:.4rem;align-items:center;min-width:0}.connection-legend i{color:var(--accent);font-style:normal}.connection-legend em{color:var(--muted);font:650 .7rem/1 var(--mono);font-style:normal}.module-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:1rem;margin-top:1.2rem}.module-card{grid-column:span 4;min-height:180px;padding:1.25rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}.module-card:nth-child(5n+1){grid-column:span 5}.module-card:nth-child(5n+2){grid-column:span 7}.module-kind{color:var(--accent-strong);font:750 .72rem/1 var(--mono)}.module-card h3{margin:1.5rem 0 .45rem;font-size:1.2rem}.module-card p{margin:0 0 1rem;color:var(--muted)}
.flow-stack{display:grid;gap:2rem}.flow-story{padding:2rem;border-radius:var(--radius);background:var(--surface);box-shadow:var(--shadow)}.flow-story header{max-width:620px;margin-bottom:2rem}.flow-story h3{margin:0;font-size:1.5rem}.flow-story header p{color:var(--muted)}.flow-story ol{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(160px,1fr);gap:1.5rem;overflow-x:auto;list-style:none;margin:0;padding:0 0 .6rem}.flow-story li{position:relative;display:grid;grid-template-rows:34px 1fr;gap:.8rem;min-width:0}.flow-story li:not(:last-child):after{content:"→";position:absolute;right:-1.15rem;top:.15rem;color:var(--accent);font-weight:900}.step-number{display:grid;place-items:center;width:28px;height:28px;border-radius:9px;background:var(--accent);color:#f8fbff;font:750 .75rem/1 var(--mono)}.flow-story li div{display:flex;flex-direction:column;gap:.4rem;padding-top:.8rem;border-top:2px solid var(--accent)}.flow-story li small{color:var(--accent-strong);font:700 .68rem/1 var(--mono)}
.concepts-section{max-width:none;background:var(--accent-soft)}.concepts-section>.section-title,.concepts-section>.concept-grid{max-width:var(--max);margin-left:auto;margin-right:auto}.concept-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:1rem}.concept-card{grid-column:span 4;min-height:230px;padding:1.5rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}.concept-card:nth-child(4n+1){grid-column:span 7;background:var(--accent);color:#f8fbff;border-color:var(--accent)}.concept-card:nth-child(4n+2){grid-column:span 5}.concept-card h3{margin:0 0 2rem;color:inherit;font-size:1.45rem}.concept-card p{color:inherit;opacity:.8}.concept-card .why{display:block;margin-top:1.5rem;color:inherit}.concept-card .source-chip{color:inherit;border-color:currentColor;background:transparent}
.ecosystem-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}.ecosystem-card{padding:1.4rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}.ecosystem-card>span{color:var(--accent-strong);font:750 .7rem/1 var(--mono);text-transform:uppercase}.ecosystem-card h3{margin:2rem 0 .5rem;font-size:1.35rem}.ecosystem-card p{color:var(--muted)}
.file-atlas{display:grid;grid-template-columns:repeat(2,1fr);gap:1rem}.file-card{padding:1.4rem;border-left:4px solid var(--accent);border-radius:0 var(--radius) var(--radius) 0;background:var(--surface)}.file-card>code{display:block;color:var(--accent-strong);font-size:.8rem;overflow-wrap:anywhere}.file-card h3{margin:1.2rem 0 .35rem}.file-card p{margin:0 0 1rem;color:var(--muted)}
.run-section{max-width:none;background:var(--surface-2)}.run-section>.section-title,.run-section>.command-list{max-width:var(--max);margin-left:auto;margin-right:auto}.command-list{display:grid;gap:1rem}.command-card{display:grid;grid-template-columns:.55fr 1.45fr;gap:2rem;align-items:center;padding:1.4rem;border-radius:var(--radius);background:var(--surface)}.command-card p{margin:.3rem 0 0;color:var(--muted)}.command-card button{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-width:0;padding:1rem;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--ink);cursor:pointer}.command-card code{overflow:auto;text-align:left}.command-card button span{color:var(--accent-strong);font-weight:750}
.learning-path{list-style:none;margin:0;padding:0;counter-reset:path}.learning-path li{display:grid;grid-template-columns:70px 1fr;gap:1.2rem;position:relative;padding-bottom:1.2rem}.learning-path li>span{display:grid;place-items:center;width:52px;height:52px;border-radius:15px;background:var(--accent);color:#f8fbff;font:850 1rem/1 var(--mono);z-index:1}.learning-path li:not(:last-child):before{content:"";position:absolute;left:25px;top:52px;bottom:0;width:2px;background:var(--line)}.learning-path article{padding:1.4rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}.learning-path h3{margin:0}.learning-path p{color:var(--muted)}.learning-files{display:flex;flex-wrap:wrap;gap:.4rem}.learning-files code{padding:.3rem .5rem;border-radius:7px;background:var(--surface-2);font-size:.76rem}
.tests-section{max-width:none;background:var(--surface-2)}.tests-section>.section-title,.tests-section>.test-notes,.tests-section>.test-grid{max-width:var(--max);margin-left:auto;margin-right:auto}.test-notes{color:var(--muted);margin-bottom:1.5rem}.test-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}.test-card{padding:1.3rem;border-radius:var(--radius);background:var(--surface)}.test-card h3{margin:0 0 1rem}.test-card>div{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:1rem}.test-status{padding:.3rem .5rem;border-radius:8px;background:var(--surface-2);font:700 .72rem/1 var(--mono)}.test-status.yes{color:var(--accent-strong)}.test-status.no{color:var(--danger)}.test-status.unknown{color:var(--muted)}
.risk-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:1rem}.risk-card{grid-column:span 4;min-height:200px;padding:1.4rem;border:1px solid var(--line);border-top:5px solid var(--warning);border-radius:var(--radius);background:var(--surface)}.risk-card.risk-high{grid-column:span 6;border-top-color:var(--danger)}.risk-card.risk-low{border-top-color:var(--accent)}.risk-card>span{color:var(--muted);font:750 .75rem/1 var(--mono)}.risk-card h3{margin:1.5rem 0 .5rem}.risk-card p{color:var(--muted)}.gap-list{columns:2;column-gap:3rem;margin:0;padding-left:1.2rem}.gap-list li{break-inside:avoid;margin:0 0 1rem}.closing{max-width:var(--max);margin:4rem auto;padding:clamp(3rem,7vw,6rem);border-radius:calc(var(--radius) * 1.4);background:var(--accent);color:#f8fbff}.closing h2{max-width:800px;margin:0;font-size:clamp(2.4rem,6vw,5.5rem);line-height:.95;letter-spacing:-.055em}.closing p{max-width:54ch;margin:1.5rem 0 2rem}.closing .button{background:#f8fbff;color:#113c82}footer{max-width:var(--max);margin:0 auto;padding:2rem 1.5rem;display:flex;justify-content:space-between;color:var(--muted);font-size:.8rem}
.source-list{display:flex;flex-wrap:wrap;gap:.3rem;width:100%;min-width:0}.source-chip{display:block;max-width:100%;padding:.24rem .45rem;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--muted);font:500 .7rem/1.2 var(--mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}.flow-story li div{min-width:0}.source-chip:hover{border-color:var(--accent);color:var(--accent-strong)}.empty-state{display:grid;place-items:center;min-height:280px;border:1px dashed var(--line);border-radius:var(--radius);color:var(--muted)}.empty-state strong{color:var(--ink)}.toast{position:fixed;left:50%;bottom:1.5rem;z-index:40;transform:translate(-50%,140%);padding:.65rem .9rem;border-radius:10px;background:var(--ink);color:var(--bg);font-size:.82rem;transition:transform .25s ease}.toast.show{transform:translate(-50%,0)}.reveal{opacity:0;transform:translateY(24px);transition:opacity .65s cubic-bezier(.16,1,.3,1),transform .65s cubic-bezier(.16,1,.3,1)}.reveal.visible{opacity:1;transform:none}
@media(max-width:900px){.site-header{grid-template-columns:1fr auto}.site-header nav{display:none}.hero{grid-template-columns:1fr;grid-template-rows:auto auto auto;padding-top:3rem}.hero h1{font-size:clamp(3.2rem,15vw,6rem)}.hero-visual{min-height:360px}.visual-orbit{width:min(82vw,380px)}.overview-layout,.flow-story,.command-card{grid-template-columns:1fr}.module-card,.module-card:nth-child(n),.concept-card,.concept-card:nth-child(n),.risk-card,.risk-card.risk-high{grid-column:span 6}}
@media(max-width:640px){.site-header{height:64px;padding:0 1rem}.brand span:last-child,.theme-toggle span{display:none}.theme-toggle b{display:block;font-size:1rem}.hero{min-height:calc(100dvh - 64px);padding:2.4rem 1rem 1.2rem}.hero h1{letter-spacing:-.05em}.hero-visual{min-height:310px}.orbit-label{font-size:.68rem}.hero-meta{flex-direction:column}.story-section{padding:4.5rem 1rem}.section-title{margin-bottom:2rem}.module-grid,.concept-grid,.risk-grid{display:block}.module-card,.concept-card,.risk-card{margin-bottom:.8rem;min-height:0}.connection-legend{grid-template-columns:1fr}.file-atlas{grid-template-columns:1fr}.flow-story{padding:1.25rem}.flow-story ol{grid-auto-flow:row;grid-auto-columns:1fr;overflow:visible}.flow-story li:not(:last-child):after{content:"↓";right:auto;left:.45rem;top:100%}.gap-list{columns:1}.closing{margin:1rem;border-radius:var(--radius);padding:3rem 1.4rem}footer{padding:2rem 1rem;flex-direction:column;gap:.4rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal{opacity:1;transform:none;transition:none}.button,.toast,.arch-edge,.arch-node rect{transition:none}}
@media print{.site-header,.theme-toggle,.hero-actions,.diagram-help,.toast{display:none!important}.hero{min-height:0}.reveal{opacity:1;transform:none}.story-section{break-inside:avoid;padding:2rem 0}.architecture-section,.run-section,.concepts-section{background:transparent;color:var(--ink)}.concept-card{color:var(--ink)}.closing{background:transparent;color:var(--ink);border:2px solid var(--ink)}}
"""


JS = r"""
(function(){
  var root=document.documentElement,toggle=document.querySelector('[data-theme-toggle]'),toast=document.querySelector('.toast');
  try{var stored=localStorage.getItem('repo-learning-theme');if(stored)root.dataset.theme=stored}catch(e){}
  if(toggle)toggle.addEventListener('click',function(){var current=root.dataset.theme;var dark=current==='dark'||(!current&&matchMedia('(prefers-color-scheme: dark)').matches);root.dataset.theme=dark?'light':'dark';try{localStorage.setItem('repo-learning-theme',root.dataset.theme)}catch(e){}});
  function copied(message){if(!toast)return;toast.textContent=message;toast.classList.add('show');clearTimeout(copied.timer);copied.timer=setTimeout(function(){toast.classList.remove('show')},1500)}
  function copyText(value,done){if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(value).then(done).catch(function(){fallbackCopy(value,done)});return}fallbackCopy(value,done)}
  function fallbackCopy(value,done){var area=document.createElement('textarea');area.value=value;area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();try{document.execCommand('copy');done()}finally{area.remove()}}
  document.addEventListener('click',function(event){var source=event.target.closest('[data-copy-source]');var command=event.target.closest('[data-copy-command]');var value=source&&source.dataset.copySource||command&&command.dataset.copyCommand;if(!value)return;copyText(value,function(){copied(source?'源码位置已复制':'命令已复制')})});
  var reveals=document.querySelectorAll('.reveal');if('IntersectionObserver'in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){var revealObserver=new IntersectionObserver(function(entries){entries.forEach(function(entry){if(entry.isIntersecting){entry.target.classList.add('visible');revealObserver.unobserve(entry.target)}})},{threshold:.12});reveals.forEach(function(el){revealObserver.observe(el)})}else{reveals.forEach(function(el){el.classList.add('visible')})}
  var navLinks=document.querySelectorAll('.site-header nav a');if('IntersectionObserver'in window){var sectionObserver=new IntersectionObserver(function(entries){entries.forEach(function(entry){if(entry.isIntersecting){navLinks.forEach(function(link){link.classList.toggle('active',link.getAttribute('href')==='#'+entry.target.id)})}})},{rootMargin:'-30% 0px -60% 0px'});navLinks.forEach(function(link){var target=document.querySelector(link.getAttribute('href'));if(target)sectionObserver.observe(target)})}
  document.querySelectorAll('.architecture').forEach(function(svg){svg.querySelectorAll('.arch-node').forEach(function(node){function focus(){var id=node.dataset.module;svg.classList.add('has-focus');svg.querySelectorAll('.arch-node').forEach(function(n){n.classList.toggle('is-active',n.dataset.module===id)});svg.querySelectorAll('.arch-edge').forEach(function(edge){edge.classList.toggle('is-active',edge.dataset.from===id||edge.dataset.to===id)})}function clear(){svg.classList.remove('has-focus');svg.querySelectorAll('.is-active').forEach(function(el){el.classList.remove('is-active')})}node.addEventListener('mouseenter',focus);node.addEventListener('mouseleave',clear);node.addEventListener('focus',focus);node.addEventListener('blur',clear)})});
})();
"""


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
