#!/usr/bin/env python3
"""
Concatenate analysis files into a single file for the organize step.

Stage 2 of the KB pipeline:
  1. analyze (build-findings-kb.py) — classify each finding
  2. assemble (this script) — concatenate analysis files
  3. organize (organize-findings-kb.py) — synthesize, cross-reference, produce kb-formal.md
  4. audit (audit-findings-kb.py) — review the full KB for quality

No parsing, no grouping, no regex. Just reads all analysis files in
numeric order and concatenates them. The organize step handles the rest.

Usage:
    python scripts/assemble-findings-kb.py
    python scripts/assemble-findings-kb.py --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
ANALYZED_DIR = HARNESS_ROOT / "knowledge-base" / "analyzed"
ASSEMBLED_PATH = HARNESS_ROOT / "knowledge-base" / "assembled.md"


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate analysis files for the organize step"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show stats without writing"
    )
    args = parser.parse_args()

    if not ANALYZED_DIR.exists():
        print(f"No analyzed directory: {ANALYZED_DIR}", file=sys.stderr)
        sys.exit(1)

    # Collect and sort by finding number
    files = []
    for f in ANALYZED_DIR.glob("*.md"):
        match = re.match(r"(\d+)", f.name)
        if match:
            files.append((int(match.group(1)), f))
    files.sort(key=lambda x: x[0])

    if not files:
        print("No analysis files found", file=sys.stderr)
        sys.exit(1)

    # Concatenate (skip empty files)
    parts = []
    empty = []
    for num, path in files:
        content = path.read_text().strip()
        if not content:
            empty.append(num)
            continue
        parts.append(content)

    assembled = "\n\n---\n\n".join(parts) + "\n"

    # Report
    print(f"Analysis files: {len(files)}")
    print(f"Range: {files[0][0]:04d}–{files[-1][0]:04d}")
    print(f"Assembled size: {len(assembled.encode()):,} bytes")

    if empty:
        print(f"\nWARNING: {len(empty)} empty analysis files: "
              f"{', '.join(f'{n:04d}' for n in empty)}")

    if args.dry_run:
        print("\nDry run — not written")
        return

    ASSEMBLED_PATH.write_text(assembled)
    print(f"\nWritten to {ASSEMBLED_PATH}")


if __name__ == "__main__":
    main()
