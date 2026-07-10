#!/usr/bin/env python3
"""Build a safe, bounded repository inventory for AI investigation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "vendor",
    "dist", "build", "target", "coverage", ".next", ".turbo", ".venv",
    "venv", "__pycache__", ".cache",
}
DOC_NAMES = {
    "readme", "contributing", "architecture", "design", "development",
    "getting-started", "agents", "claude", "security", "skill",
}
MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "gemfile", "composer.json",
    "mix.exs", "deno.json", "bunfig.toml", "turbo.json", "workspace.json",
    "docker-compose.yml", "docker-compose.yaml", "makefile", "justfile",
}
ENTRY_STEMS = {
    "main", "index", "app", "server", "cli", "worker", "bootstrap",
    "entrypoint", "manage", "program",
}
DEPLOY_PARTS = {
    "dockerfile", "compose", "helm", "terraform", "pulumi", "kubernetes",
    "k8s", "deploy", "workflow", "workflows", "vercel", "netlify",
}
EXT_LANG = {
    ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".py": "Python", ".rs": "Rust", ".go": "Go",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".cc": "C++",
    ".c": "C", ".h": "C/C++ Header", ".swift": "Swift", ".scala": "Scala",
    ".ex": "Elixir", ".exs": "Elixir", ".lua": "Lua", ".sh": "Shell",
    ".vue": "Vue", ".svelte": "Svelte", ".sol": "Solidity",
}


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        values = [root / item.decode("utf-8", "replace") for item in result.stdout.split(b"\0") if item]
        return [path for path in values if path.is_file()]

    values = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        values.extend(Path(base) / name for name in files)
    return values


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def bounded(items: list[str], limit: int) -> list[str]:
    return sorted(dict.fromkeys(items), key=lambda value: (value.count("/"), value))[:limit]


def classify(root: Path, files: list[Path], max_examples: int) -> dict[str, object]:
    docs: list[str] = []
    manifests: list[str] = []
    entries: list[str] = []
    tests: list[str] = []
    deploy: list[str] = []
    instructions: list[str] = []
    languages: Counter[str] = Counter()
    top_dirs: Counter[str] = Counter()
    total_bytes = 0

    for path in files:
        rel = relative(root, path)
        parts = Path(rel).parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        lower_name = path.name.lower()
        stem = path.stem.lower()
        suffix = path.suffix.lower()
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        total_bytes += size
        if parts:
            top_dirs[parts[0] if len(parts) > 1 else "."] += 1
        if suffix in EXT_LANG:
            languages[EXT_LANG[suffix]] += size
        if stem in DOC_NAMES or lower_name in {"agents.md", "claude.md"}:
            docs.append(rel)
        if lower_name in {"agents.md", "claude.md"}:
            instructions.append(rel)
        if lower_name in MANIFEST_NAMES:
            manifests.append(rel)
        if stem in ENTRY_STEMS and suffix in EXT_LANG:
            entries.append(rel)
        elif parts and parts[0] in {"bin", "cmd", "scripts"} and suffix in EXT_LANG:
            entries.append(rel)
        if any(token in lower_name for token in ("test", "spec")) or "tests" in parts or "test" in parts:
            tests.append(rel)
        if any(token in rel.lower() for token in DEPLOY_PARTS):
            deploy.append(rel)

    language_total = sum(languages.values()) or 1
    language_rows = [
        {"name": name, "bytes": size, "percent": round(size * 100 / language_total, 1)}
        for name, size in languages.most_common(12)
    ]
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "top_level_areas": [{"path": key, "files": count} for key, count in top_dirs.most_common(30)],
        "languages": language_rows,
        "repository_guidance_files": bounded(instructions, max_examples),
        "documentation": bounded(docs, max_examples),
        "manifests": bounded(manifests, max_examples),
        "entrypoint_candidates": bounded(entries, max_examples),
        "test_candidates": bounded(tests, max_examples),
        "deployment_candidates": bounded(deploy, max_examples),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a bounded repository inventory")
    parser.add_argument("repository", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--max-files", type=int, default=50_000)
    parser.add_argument("--max-examples", type=int, default=40)
    args = parser.parse_args(argv)

    root = args.repository.expanduser().resolve()
    if not root.is_dir():
        print(f"error: repository is not a directory: {root}", file=sys.stderr)
        return 1
    files = tracked_files(root)
    truncated = len(files) > args.max_files
    files = files[: args.max_files]
    payload = {
        "repository": str(root),
        "name": root.name,
        "inventory_truncated": truncated,
        **classify(root, files, args.max_examples),
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
