#!/usr/bin/env python3
"""
Organize the assembled findings into kb-formal.md — pure Python, no LLM call.

Stage 3 of the KB pipeline:
  1. analyze (build-findings-kb.py) — classify each finding
  2. assemble (assemble-findings-kb.py) — concatenate analysis files
  3. organize (this script) — group by category, preserve all contributions
  4. audit (audit-findings-kb.py) — review the full KB for quality

Parses the assembled analysis files, groups entries by category prefix,
and produces kb-formal.md with each finding's contribution preserved
separately under its entry ID. No merging, no synthesis, no judgment calls.
Contradictions between findings are preserved for the spec-writing agent
to resolve.

Usage:
    python scripts/organize-findings-kb.py
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
ASSEMBLED_PATH = HARNESS_ROOT / "knowledge-base" / "assembled.md"
KB_PATH = HARNESS_ROOT / "knowledge-base" / "kb-formal.md"

# Standard category order
CATEGORIES = [
    ("SS", "State Structure", "What the state IS — types, address spaces, data model"),
    ("PRE", "Preconditions", "When an operation is valid — what must hold before"),
    ("ST", "State Transitions", "What an operation changes — postconditions"),
    ("FC", "Frame Conditions", "What an operation leaves unchanged"),
    ("INV", "Invariants", "What always holds across all operations"),
    ("INT", "Interactions", "How subsystems affect each other"),
    ("EC", "Edge Cases", "Boundary and unusual behavior"),
]

CATEGORY_PREFIXES = {cat[0] for cat in CATEGORIES}


def abort(message):
    print(f"\nABORTED: {message}", file=sys.stderr)
    sys.exit(1)


def parse_assembled(text):
    """Parse assembled.md into a list of (entry_id, finding_number, body) tuples."""
    entries = []
    current_finding = None

    # Split into lines for processing
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        # Track which finding we're in
        m = re.match(r"^# Finding (\d+) Analysis", line)
        if m:
            current_finding = m.group(1)
            i += 1
            continue

        # Skip omit sections
        if line.startswith("## Omit"):
            i += 1
            continue

        # Parse entry headers
        m = re.match(r"^### ([A-Z]+-[A-Z0-9-]+)", line)
        if m and current_finding:
            entry_id = m.group(1)
            # Collect body until next ### or # Finding or ---
            body_lines = []
            i += 1
            while i < len(lines):
                if re.match(r"^###\s", lines[i]):
                    break
                if re.match(r"^# Finding \d+", lines[i]):
                    break
                if lines[i].strip() == "---":
                    i += 1  # consume the separator
                    break
                body_lines.append(lines[i])
                i += 1
            body = "\n".join(body_lines).strip()
            entries.append((entry_id, current_finding, body))
            continue

        i += 1

    return entries


def extract_prefix(entry_id):
    """Extract the category prefix from an entry ID like 'SS-TUMBLER' -> 'SS'."""
    return entry_id.split("-", 1)[0]


def build_cooccurrence(entries):
    """Build co-occurrence: which entry IDs appeared together in the same finding."""
    finding_entries = defaultdict(set)
    for entry_id, finding, _ in entries:
        finding_entries[finding].add(entry_id)

    cooccurrence = defaultdict(set)
    for finding, ids in finding_entries.items():
        for eid in ids:
            cooccurrence[eid].update(ids - {eid})

    return cooccurrence


def find_highest_finding(entries):
    """Find the highest finding number across all entries."""
    highest = 0
    for _, finding, _ in entries:
        n = int(finding)
        if n > highest:
            highest = n
    return highest


def format_kb(entries):
    """Format entries into the final kb-formal.md content."""
    # Group by (prefix, entry_id) preserving order of first appearance
    grouped = defaultdict(list)
    entry_order = {}  # entry_id -> order of first appearance
    order_counter = 0
    for entry_id, finding, body in entries:
        grouped[entry_id].append((finding, body))
        if entry_id not in entry_order:
            entry_order[entry_id] = order_counter
            order_counter += 1

    # Build co-occurrence map
    cooccurrence = build_cooccurrence(entries)

    # Find highest finding number
    highest = find_highest_finding(entries)

    # Group entry IDs by category
    category_entries = defaultdict(list)
    other_entries = []
    for entry_id in entry_order:
        prefix = extract_prefix(entry_id)
        if prefix in CATEGORY_PREFIXES:
            category_entries[prefix].append(entry_id)
        else:
            other_entries.append(entry_id)

    # Sort entries within each category by order of first appearance
    for prefix in category_entries:
        category_entries[prefix].sort(key=lambda eid: entry_order[eid])

    # Build output
    out = []
    out.append("# Formal Properties Knowledge Base")
    out.append(f"<!-- last-finding: {highest:04d} -->")
    out.append("")
    out.append("> Formal properties of udanax-green, extracted from implementation findings.")
    out.append("> Each entry preserves all contributing findings separately — no merging, no synthesis.")
    out.append("> Contradictions between findings are preserved for the spec-writing agent to resolve.")
    out.append("> Cite entries as `[SS-ADDRESS-SPACE]`, `[ST-INSERT]`, `[FC-SUBSPACE]`, etc.")
    out.append("")

    for prefix, section_name, description in CATEGORIES:
        out.append(f"## {section_name}")
        out.append("")
        out.append(f"> {description}")
        out.append("")

        eids = category_entries.get(prefix, [])
        if not eids:
            out.append("*No entries.*")
            out.append("")
            continue

        for entry_id in eids:
            contributions = grouped[entry_id]
            out.append(f"### {entry_id}")
            out.append("")

            if len(contributions) == 1:
                finding, body = contributions[0]
                out.append(f"**Source:** Finding {finding}")
                out.append("")
                out.append(body)
            else:
                findings_list = ", ".join(f"{f}" for f, _ in contributions)
                out.append(f"**Sources:** Findings {findings_list}")
                out.append("")
                for finding, body in contributions:
                    out.append(f"#### Finding {finding}")
                    out.append("")
                    out.append(body)
                    out.append("")

            # Add co-occurrence
            related = cooccurrence.get(entry_id, set())
            if related:
                # Sort related by category order then alphabetically
                def sort_key(eid):
                    p = extract_prefix(eid)
                    cat_order = {c[0]: i for i, c in enumerate(CATEGORIES)}
                    return (cat_order.get(p, 99), eid)
                related_sorted = sorted(related, key=sort_key)
                out.append(f"**Co-occurring entries:** {', '.join(f'[{r}]' for r in related_sorted)}")
                out.append("")

            out.append("---")
            out.append("")

    # Other categories (invented prefixes)
    if other_entries:
        out.append("## Other Categories")
        out.append("")
        out.append("> These categories were invented during analysis.")
        out.append("")
        for entry_id in other_entries:
            contributions = grouped[entry_id]
            out.append(f"### {entry_id}")
            out.append("")
            if len(contributions) == 1:
                finding, body = contributions[0]
                out.append(f"**Source:** Finding {finding}")
                out.append("")
                out.append(body)
            else:
                findings_list = ", ".join(f"{f}" for f, _ in contributions)
                out.append(f"**Sources:** Findings {findings_list}")
                out.append("")
                for finding, body in contributions:
                    out.append(f"#### Finding {finding}")
                    out.append("")
                    out.append(body)
                    out.append("")
            out.append("---")
            out.append("")

    return "\n".join(out)


def main():
    if not ASSEMBLED_PATH.exists():
        abort(f"Assembled file not found: {ASSEMBLED_PATH}")

    text = ASSEMBLED_PATH.read_text()
    assembled_size = len(text.encode("utf-8"))
    print(f"Organizing KB from assembled file ({assembled_size:,} bytes)")

    entries = parse_assembled(text)
    print(f"Parsed {len(entries)} entries from {len(set(e[1] for e in entries))} findings")

    # Count by category
    prefix_counts = defaultdict(int)
    for entry_id, _, _ in entries:
        prefix_counts[extract_prefix(entry_id)] += 1
    for prefix, name, _ in CATEGORIES:
        count = prefix_counts.get(prefix, 0)
        if count:
            print(f"  {prefix}: {count} entries")
    other_count = sum(v for k, v in prefix_counts.items() if k not in CATEGORY_PREFIXES)
    if other_count:
        print(f"  Other: {other_count} entries")

    unique_ids = len(set(e[0] for e in entries))
    multi_source = sum(1 for eid in set(e[0] for e in entries)
                       if sum(1 for e in entries if e[0] == eid) > 1)
    print(f"Unique entry IDs: {unique_ids} ({multi_source} with multiple findings)")

    kb_content = format_kb(entries)
    KB_PATH.write_text(kb_content)

    kb_size = KB_PATH.stat().st_size
    kb_lines = kb_content.count("\n")
    print(f"KB written to {KB_PATH} ({kb_size:,} bytes, {kb_lines:,} lines)")


if __name__ == "__main__":
    main()
