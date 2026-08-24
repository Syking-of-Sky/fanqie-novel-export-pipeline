#!/usr/bin/env python3
"""Create the title-based manifest consumed by the server import job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path, help="directory containing EPUB files")
    parser.add_argument("--channel", default="uncategorized")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    rows: dict[str, dict[str, str]] = {}
    for epub in sorted(args.directory.glob("*.epub")):
        rows[epub.name] = {"title": epub.stem, "channel": args.channel}
    if not rows:
        raise SystemExit(f"no .epub files found in {args.directory}")
    output = args.output or args.directory / "manifest.json"
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
