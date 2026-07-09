<div align="center">

[中文](README.md) · **English**

# repo-learning

**Cross-agent repo learning skill: read-only analysis → offline HTML brief**

</div>

Turn an unfamiliar codebase into a **single-file, offline** HTML learning report: structure, dependencies, flows, risks, and a contributor roadmap — each claim backed by `path:line` evidence.

- Editorial chapter stream (not a dashboard of cards)
- Topology, dependency swimlane, risk matrix, test matrix, learning path
- **Chinese UI by default**; pass `--lang en` for English chrome

## Install

```bash
git clone https://github.com/tt-a1i/repo-learning.git
./install.sh
```

## Usage

```bash
python3 scripts/generate_report.py --input report_data.json --out /tmp/out --strict
python3 scripts/validate_report.py /tmp/out --strict
```

## License

MIT
