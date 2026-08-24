#!/usr/bin/env python3
"""Validate ZIP/EPUB invariants and report a machine-readable result."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def validate(path: Path) -> dict:
    errors: list[str] = []
    chapter_count = 0
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if not names or names[0] != "mimetype":
            errors.append("mimetype must be the first ZIP member")
        info = archive.getinfo("mimetype") if "mimetype" in names else None
        if info is None or info.compress_type != zipfile.ZIP_STORED:
            errors.append("mimetype must be stored without compression")
        elif archive.read("mimetype") != b"application/epub+zip":
            errors.append("invalid mimetype content")
        if "META-INF/container.xml" not in names:
            errors.append("META-INF/container.xml is missing")
        chapter_count = sum(name.startswith("text/chapter-") and name.endswith(".xhtml") for name in names)
        if chapter_count == 0:
            errors.append("no chapter XHTML files found")
        bad_member = archive.testzip()
        if bad_member:
            errors.append(f"CRC check failed for {bad_member}")
    result = {"path": str(path), "valid": not errors, "chapter_count": chapter_count, "errors": errors}
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.epub), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
