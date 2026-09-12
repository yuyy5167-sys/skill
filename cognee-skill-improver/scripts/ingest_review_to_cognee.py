#!/usr/bin/env python3
"""Ingest a prepared skill review into the local Cognee runtime."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--skip-cognify", action="store_true")
    return parser.parse_args()


def load_dotenv(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    review_path = root / ".skill-improver-data" / "reviews" / f"{args.skill}.md"
    cognee_python = root / ".venv-cognee" / "Scripts" / "python.exe"

    if not review_path.exists():
        print(f"Review file not found: {review_path}", file=sys.stderr)
        return 1
    if not cognee_python.exists():
        print(f"Cognee runtime not found: {cognee_python}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.update(load_dotenv(root / ".env"))
    if not env.get("LLM_API_KEY"):
        print("LLM_API_KEY is required to ingest into Cognee.", file=sys.stderr)
        return 1

    code = f"""
import asyncio
import pathlib
import cognee

text = pathlib.Path({json.dumps(str(review_path))}).read_text(encoding="utf-8")

async def main():
    await cognee.add(text)
    {'await cognee.cognify()' if not args.skip_cognify else 'pass'}

asyncio.run(main())
print("INGESTED")
""".strip()

    result = subprocess.run(
        [str(cognee_python), "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
