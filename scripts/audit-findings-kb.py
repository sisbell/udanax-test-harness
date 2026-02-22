#!/usr/bin/env python3
"""
Audit the findings KB — mechanical checks in Python, Opus for miscategorization.

Stage 4 of the KB pipeline:
  1. analyze (build-findings-kb.py) — classify each finding
  2. assemble (assemble-findings-kb.py) — concatenate analysis files
  3. organize (organize-findings-kb.py) — group by category (pure Python)
  4. audit (this script) — mechanical checks + miscategorization review

Python handles: invented categories, category imbalance, cross-reference
integrity. Opus handles: miscategorization detection (the only check that
requires understanding content).

Usage:
    python scripts/audit-findings-kb.py [--skip-opus]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
KB_PATH = HARNESS_ROOT / "knowledge-base" / "kb-formal.md"
AUDIT_PATH = HARNESS_ROOT / "knowledge-base" / "audit.md"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "kb-audit-instructions.md"

MODEL = "claude-opus-4-6"

STANDARD_PREFIXES = {"SS", "PRE", "ST", "FC", "INV", "INT", "EC"}


def abort(message):
    print(f"\nABORTED: {message}", file=sys.stderr)
    sys.exit(1)


def parse_kb(text):
    """Parse kb-formal.md into a list of (entry_id, body) tuples."""
    entries = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^### ([A-Z]+-[A-Z0-9-]+)", lines[i])
        if m:
            entry_id = m.group(1)
            body_lines = []
            i += 1
            while i < len(lines):
                if re.match(r"^### ", lines[i]):
                    break
                if re.match(r"^## ", lines[i]):
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines).strip()
            entries.append((entry_id, body))
            continue
        i += 1
    return entries


def check_invented_categories(entries):
    """Find entries with non-standard prefixes."""
    invented = defaultdict(list)
    for entry_id, body in entries:
        prefix = entry_id.split("-", 1)[0]
        if prefix not in STANDARD_PREFIXES:
            # Extract provenance
            provenance = ""
            for line in body.split("\n"):
                if "Provenance" in line or "Source" in line:
                    provenance = line.strip()
                    break
            invented[prefix].append((entry_id, provenance))
    return invented


def check_category_imbalance(entries):
    """Count entries per category and flag imbalances."""
    counts = defaultdict(int)
    for entry_id, _ in entries:
        prefix = entry_id.split("-", 1)[0]
        counts[prefix] += 1

    standard_counts = {p: counts.get(p, 0) for p in STANDARD_PREFIXES}
    values = [v for v in standard_counts.values() if v > 0]
    median = sorted(values)[len(values) // 2] if values else 0

    flags = []
    for prefix in STANDARD_PREFIXES:
        count = standard_counts[prefix]
        if count == 0:
            flags.append(f"  - **{prefix}**: 0 entries (unused category)")
        elif median > 0 and count >= 3 * median:
            flags.append(f"  - **{prefix}**: {count} entries (3x+ median of {median})")

    return standard_counts, flags


def check_cross_references(entries):
    """Find [XX-NAME] citations that don't point to existing entries."""
    entry_ids = {eid for eid, _ in entries}
    ref_pattern = re.compile(r"\[([A-Z]+-[A-Z][A-Z0-9-]+)\]")

    dead_refs = []
    for entry_id, body in entries:
        refs = ref_pattern.findall(body)
        for ref in refs:
            if ref not in entry_ids:
                dead_refs.append((entry_id, ref))

    return dead_refs


def run_mechanical_checks(text):
    """Run all mechanical checks and return report sections."""
    entries = parse_kb(text)
    total = len(entries)
    finding_count = len(set(
        m.group(1)
        for _, body in entries
        for m in re.finditer(r"Finding (\d+)", body)
    ))

    sections = []

    # Invented categories
    invented = check_invented_categories(entries)
    if invented:
        lines = []
        for prefix, items in sorted(invented.items()):
            lines.append(f"### {prefix}-*")
            lines.append(f"  - {len(items)} entries")
            for eid, prov in items:
                lines.append(f"  - `{eid}` ({prov})")
            lines.append("")
        sections.append(("Invented Categories", "\n".join(lines)))
    else:
        sections.append(("Invented Categories", "None — all entries use standard categories."))

    # Category imbalance
    counts, flags = check_category_imbalance(entries)
    table = "| Category | Count |\n|----------|-------|\n"
    for prefix in ["SS", "PRE", "ST", "FC", "INV", "INT", "EC"]:
        table += f"| {prefix} | {counts.get(prefix, 0)} |\n"
    non_standard = sum(1 for eid, _ in entries if eid.split("-", 1)[0] not in STANDARD_PREFIXES)
    if non_standard:
        table += f"| Other | {non_standard} |\n"
    if flags:
        table += "\n**Flags:**\n" + "\n".join(flags)
        sections.append(("Category Imbalance", table))
    else:
        sections.append(("Category Imbalance", table + "\nNo imbalance flags."))

    # Cross-reference integrity
    dead_refs = check_cross_references(entries)
    if dead_refs:
        lines = []
        for src, ref in dead_refs:
            lines.append(f"- `{src}` cites `[{ref}]` — not found")
        sections.append(("Cross-Reference Integrity", "\n".join(lines)))
    else:
        sections.append(("Cross-Reference Integrity", "All references valid."))

    return total, finding_count, sections


def run_opus_miscategorization():
    """Run Opus to check for miscategorized entries."""
    if not PROMPT_PATH.exists():
        print(f"WARNING: Prompt not found: {PROMPT_PATH}", file=sys.stderr)
        return None

    prompt = PROMPT_PATH.read_text()

    cmd = [
        "claude", "--print",
        "--model", MODEL,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env["CLAUDE_CODE_EFFORT_LEVEL"] = "max"

    kb_size = KB_PATH.stat().st_size
    print(f"Running miscategorization review ({kb_size:,} bytes)")
    print(f"Model: {MODEL} | Thinking: max")

    start = time.time()

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(HARNESS_ROOT),
        timeout=None,
    )

    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"WARNING: Opus exited {result.returncode} ({elapsed:.0f}s)", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
        usage = data.get("usage", {})
        cost = data.get("total_cost_usd", 0)
        inp = (
            usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
        )
        out = usage.get("output_tokens", 0)
        print(f"Done. {elapsed:.0f}s | in:{inp:,} out:{out:,} ${cost:.4f}")
    except (json.JSONDecodeError, KeyError):
        print(f"Done. {elapsed:.0f}s [no token data]")

    # Read the output file that Opus wrote
    miscat_path = HARNESS_ROOT / "knowledge-base" / "miscategorized.md"
    if miscat_path.exists():
        return miscat_path.read_text()

    return None


def main():
    parser = argparse.ArgumentParser(description="Audit the findings KB")
    parser.add_argument("--skip-opus", action="store_true",
                        help="Skip the Opus miscategorization check (mechanical only)")
    args = parser.parse_args()

    if not KB_PATH.exists():
        abort(f"KB not found: {KB_PATH}")

    text = KB_PATH.read_text()

    # Mechanical checks
    print("Running mechanical checks...")
    total, finding_count, sections = run_mechanical_checks(text)
    print(f"  {total} entries, {finding_count} findings referenced")
    for name, content in sections:
        issues = "OK" if ("None" in content or "All references valid" in content or "No imbalance" in content) else "issues found"
        print(f"  {name}: {issues}")

    # Opus miscategorization check
    miscat_section = None
    if not args.skip_opus:
        miscat_section = run_opus_miscategorization()

    # Write audit report
    report = []
    report.append(f"# KB Audit — {date.today().isoformat()}")
    report.append("")
    report.append(f"KB: {total} entries, {finding_count} findings referenced")
    report.append("")

    # Miscategorization (Opus or skipped)
    report.append("## Miscategorized Entries")
    report.append("")
    if miscat_section:
        report.append(miscat_section)
    elif args.skip_opus:
        report.append("*Skipped (--skip-opus flag).*")
    else:
        report.append("*Opus check failed or timed out. Run again or review manually.*")
    report.append("")

    # Mechanical sections
    for name, content in sections:
        report.append(f"## {name}")
        report.append("")
        report.append(content)
        report.append("")

    audit_text = "\n".join(report)
    AUDIT_PATH.write_text(audit_text)
    print(f"\nAudit written to {AUDIT_PATH} ({len(audit_text):,} bytes)")


if __name__ == "__main__":
    main()
