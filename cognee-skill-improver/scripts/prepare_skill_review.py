#!/usr/bin/env python3
"""Create a markdown review brief for one skill from logged usage records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def load_records(log_path: Path, skill: str) -> list[dict]:
    if not log_path.exists():
        return []

    records: list[dict] = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("skill") == skill:
                records.append(record)
    return records


def bullet_list(values: list[str]) -> list[str]:
    return [value for value in values if value]


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    data_dir = root / ".skill-improver-data"
    log_path = data_dir / "skill-runs.jsonl"
    review_dir = data_dir / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(log_path, args.skill)
    recent = records[-args.limit :]

    worked = bullet_list([r.get("worked", "").strip() for r in recent])
    failed = bullet_list([r.get("failed", "").strip() for r in recent])
    changes = bullet_list([r.get("change", "").strip() for r in recent])
    tags = Counter(tag for r in recent for tag in r.get("tags", []))

    lines: list[str] = []
    lines.append(f"# Review: {args.skill}")
    lines.append("")
    lines.append(f"- Total logged runs: {len(records)}")
    lines.append(f"- Included in this review: {len(recent)}")
    lines.append("")

    lines.append("## Frequent Tags")
    if tags:
        for tag, count in tags.most_common():
            lines.append(f"- {tag}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## What Worked")
    if worked:
        for item in worked:
            lines.append(f"- {item}")
    else:
        lines.append("- no structured notes")
    lines.append("")

    lines.append("## What Failed")
    if failed:
        for item in failed:
            lines.append(f"- {item}")
    else:
        lines.append("- no structured notes")
    lines.append("")

    lines.append("## Suggested Changes")
    if changes:
        for item in changes:
            lines.append(f"- {item}")
    else:
        lines.append("- no structured notes")
    lines.append("")

    lines.append("## Recent Runs")
    if recent:
        for record in recent:
            lines.append(
                f"- {record.get('timestamp', '')}: {record.get('request', '').strip()} -> {record.get('result', '').strip()}"
            )
    else:
        lines.append("- no matching runs found")
    lines.append("")

    review_path = review_dir / f"{args.skill}.md"
    review_path.write_text("\n".join(lines), encoding="utf-8")
    print(review_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
