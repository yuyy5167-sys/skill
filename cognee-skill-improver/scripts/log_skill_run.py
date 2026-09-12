#!/usr/bin/env python3
"""Append a structured skill usage record to the local improvement log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--worked", default="")
    parser.add_argument("--failed", default="")
    parser.add_argument("--change", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--root", default=".")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    data_dir = root / ".skill-improver-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "skill-runs.jsonl"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": args.skill.strip(),
        "request": args.request.strip(),
        "result": args.result.strip(),
        "worked": args.worked.strip(),
        "failed": args.failed.strip(),
        "change": args.change.strip(),
        "tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
    }

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
