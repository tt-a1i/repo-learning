<div align="center">

[中文](README.md) · **English**

# Repo Learning

### Give it a repository. Get one elegant learning page.

</div>

## What it does

Point an agent at a repo URL. It clones into a temp directory, reads the code (no install/build), and fills a polished single-file HTML template with project value, architecture and operating principles, Mermaid diagrams, key concepts, and optional code entry points — not implementation minutiae.

You get a clickable `index.html` — not a JSON pipeline or audit report.

## Usage

```text
Use repo-learning on https://github.com/owner/repository
```

## Install

```bash
git clone https://github.com/tt-a1i/repo-learning.git
cd repo-learning
./install.sh
```

Dev symlink:

```bash
./install.sh --link --force
```

## Layout

```text
SKILL.md
assets/learning-page.template.html
references/analysis-guide.md
PRODUCT.md
install.sh
```

## License

MIT
