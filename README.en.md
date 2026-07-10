<div align="center">

[中文](README.md) · **English**

# Repo Learning

### Give it a repository. Get a project learning website.

Turn an unfamiliar codebase into a readable, evidence-backed guide for new contributors.

</div>

## What it explains

- The problem the project solves
- The modules that matter and how they connect
- How a real request, job, or event moves through the system
- The domain concepts a contributor needs
- The files worth reading first
- A practical learning path into the code

The output adapts to the repository. It can include a source-backed architecture map, runtime flow stories, concepts, a code atlas, quick-start commands, risks, and a contributor roadmap.

## Use

```text
Use $repo-learning to study https://github.com/owner/repository and open the generated learning website.
```

That is the complete user interface. The skill resolves and investigates the repository, builds an evidence-backed model, checks content depth, generates an unstyled semantic site, and returns a clickable `index.html`.

The deterministic tools that guard the internal workflow are:

```bash
python3 scripts/prepare_repo.py https://github.com/owner/repository \
  --json-out /tmp/repo-source.json

python3 scripts/inventory_repo.py /tmp/resolved-repo \
  --json-out /tmp/inventory.json

# The agent investigates source and writes /tmp/site_data.json.
python3 scripts/quality_check.py /tmp/site_data.json --repo /tmp/resolved-repo --strict

python3 scripts/generate_report.py \
  --input /tmp/site_data.json \
  --out /tmp/repo-learning-site \
  --strict

python3 scripts/validate_report.py /tmp/repo-learning-site --strict
open /tmp/repo-learning-site/index.html
```

## Install

```bash
git clone https://github.com/tt-a1i/repo-learning.git
cd repo-learning
./install.sh
```

## Verify

```bash
bash scripts/self_check.sh
```

## License

MIT
