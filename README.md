<div align="center">

**中文** · [English](README.en.md)

# repo-learning

**跨 Agent 仓库学习 Skill：只读调研 → 离线 HTML 简报**

把陌生代码库的系统结构、依赖、流程、风险与学习路径，整理成一份**单文件、可离线打开**的 HTML 学习报告。

<br>

[![Agents](https://img.shields.io/badge/Agents-Claude_·_Codex_·_Cursor-b04a1f)](#install)
[![Offline](https://img.shields.io/badge/Offline-单文件_HTML-4a6a2c)](#what-you-get)
[![Locale](https://img.shields.io/badge/默认语言-简体中文-555)](#usage)

[Install](#install) · [Usage](#usage) · [Pipeline](#pipeline)

</div>

---

## 做什么

Agent 按 `SKILL.md` 只读调研目标仓库，产出 `report_data.json`，再由 `scripts/generate_report.py` 渲染为 `index.html`。

- 封面 + 章节流式阅读（不是仪表盘堆卡片）
- 拓扑图、依赖泳道、风险矩阵、测试矩阵、学习路径
- 每条结论带 `path:line` 证据
- **默认中文 UI**；需要英文时 `--lang en`

## Install

```bash
git clone https://github.com/tt-a1i/repo-learning.git
./install.sh
```

或 symlink 开发模式：

```bash
./install.sh --link
```

## Usage

```bash
# 1) 校验 JSON
python3 scripts/generate_report.py \
  --input report_data.json \
  --out /tmp/out \
  --validate-only \
  --strict

# 2) 生成 HTML（默认中文）
python3 scripts/generate_report.py \
  --input report_data.json \
  --out /tmp/out \
  --title "仓库学习简报" \
  --strict

# 3) 校验 HTML
python3 scripts/validate_report.py /tmp/out --strict

open /tmp/out/index.html
```

回归：

```bash
bash scripts/self_check.sh
```

## Pipeline

1. Agent 读仓库 → 写 `report_data.json`（schema v1）
2. `generate_report.py` → `index.html`
3. `validate_report.py --strict` → 离线安全 + schema 回环

## License

MIT
