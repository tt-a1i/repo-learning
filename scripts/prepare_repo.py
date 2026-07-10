#!/usr/bin/env python3
"""Resolve a local repository or shallow-clone a remote repository for analysis."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def repo_slug(source: str) -> str:
    candidate = source.rstrip("/").rsplit("/", 1)[-1]
    candidate = candidate.removesuffix(".git") or "repository"
    return re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-.") or "repository"


def is_remote(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https", "ssh", "git"} or source.startswith("git@")


def prepare(source: str, destination: Path | None) -> dict[str, object]:
    local = Path(source).expanduser()
    if local.exists():
        if not local.is_dir():
            raise ValueError(f"local source is not a directory: {local}")
        resolved = local.resolve()
        return {
            "source": source,
            "repo_path": str(resolved),
            "repo_name": resolved.name,
            "cloned": False,
            "cleanup_required": False,
        }

    if not is_remote(source):
        raise ValueError("source must be an existing directory or a git URL")

    if destination is None:
        root = Path(tempfile.mkdtemp(prefix="repo-learning-"))
        destination = root / repo_slug(source)
        cleanup_required = True
    else:
        destination = destination.expanduser().resolve()
        cleanup_required = False

    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"destination is not empty: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "git",
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--",
        source,
        str(destination),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git clone failed"
        raise RuntimeError(detail)

    return {
        "source": source,
        "repo_path": str(destination),
        "repo_name": destination.name,
        "cloned": True,
        "cleanup_required": cleanup_required,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a repository for repo-learning analysis")
    parser.add_argument("source", help="Git URL or local repository path")
    parser.add_argument("--destination", type=Path, help="Optional clone destination")
    parser.add_argument("--json-out", type=Path, help="Also write the result as JSON")
    args = parser.parse_args(argv)

    try:
        result = prepare(args.source, args.destination)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
