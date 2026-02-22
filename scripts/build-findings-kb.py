#!/usr/bin/env python3
"""
Analyze findings for KB — one finding per claude invocation.

Stage 1 of the KB pipeline:
  1. analyze (this script) — classify each finding, write per-finding analysis files
  2. assemble (assemble-findings-kb.py) — concatenate analysis files
  3. organize (organize-findings-kb.py) — synthesize, cross-reference, produce kb-formal.md
  4. audit (audit-findings-kb.py) — review the full KB for quality

Each finding gets its own Opus call with max thinking. Analysis files are
written to knowledge-base/analyzed/{NNN}.md. Existing analysis files are
skipped unless --reanalyze is used.

Any failure aborts immediately. Analysis files already written are kept.

Usage:
    python scripts/build-findings-kb.py                # Analyze all new findings
    python scripts/build-findings-kb.py --from 045     # Start from finding 045
    python scripts/build-findings-kb.py --reanalyze 036,042  # Re-analyze specific findings
    python scripts/build-findings-kb.py --bootstrap    # Delete all analyses and redo
    python scripts/build-findings-kb.py --dry-run      # Show what would be analyzed
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parent.parent
FINDINGS_DIR = HARNESS_ROOT / "findings"
ANALYZED_DIR = HARNESS_ROOT / "knowledge-base" / "analyzed"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "findings-kb-instructions.md"

MODEL = "claude-opus-4-6"


def abort(message, finding_num=None):
    """Print error and exit."""
    if finding_num is not None:
        print(f"\nABORTED at finding {finding_num:04d}: {message}", file=sys.stderr)
    else:
        print(f"\nABORTED: {message}", file=sys.stderr)
    sys.exit(1)


def get_all_findings():
    """Get sorted list of (number, path) for all findings."""
    findings = []
    for f in FINDINGS_DIR.glob("*.md"):
        match = re.match(r"(\d+)", f.name)
        if match:
            findings.append((int(match.group(1)), f))
    findings.sort(key=lambda x: x[0])
    return findings


def is_analyzed(finding_num):
    """Check if a finding already has an analysis file."""
    return (ANALYZED_DIR / f"{finding_num:04d}.md").exists()


def build_prompt(finding_num, finding_path):
    """Build prompt from template with variable substitution."""
    return (
        PROMPT_PATH.read_text()
        .replace("{{finding_num}}", f"{finding_num:04d}")
        .replace("{{finding_path}}", str(finding_path.relative_to(HARNESS_ROOT)))
    )


def analyze_finding(finding_num, finding_path, usage):
    """Run claude --print to analyze one finding. Aborts on any failure."""
    prompt = build_prompt(finding_num, finding_path)

    cmd = [
        "claude", "--print",
        "--model", MODEL,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env["CLAUDE_CODE_EFFORT_LEVEL"] = "max"

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
        stderr_lines = ""
        if result.stderr:
            stderr_lines = "\n".join(
                f"    {line}"
                for line in result.stderr.strip().split("\n")[:5]
            )
        abort(
            f"claude exited {result.returncode} ({elapsed:.0f}s)\n{stderr_lines}",
            finding_num,
        )

    # Parse usage stats (best-effort)
    try:
        data = json.loads(result.stdout)
        raw_usage = data.get("usage", {})
        cost = data.get("total_cost_usd", 0)
        inp = (
            raw_usage.get("input_tokens", 0)
            + raw_usage.get("cache_read_input_tokens", 0)
            + raw_usage.get("cache_creation_input_tokens", 0)
        )
        out = raw_usage.get("output_tokens", 0)

        usage["input_tokens"] += inp
        usage["output_tokens"] += out
        usage["cost_usd"] += cost

        print(f"  {elapsed:.0f}s | in:{inp:,} out:{out:,} ${cost:.4f}")
    except (json.JSONDecodeError, KeyError):
        print(f"  {elapsed:.0f}s [no token data]")

    # Verify the analysis file was written
    analysis_path = ANALYZED_DIR / f"{finding_num:04d}.md"
    if not analysis_path.exists():
        abort(
            f"Analysis file not created at {analysis_path}. "
            f"The model may have failed to write the file.",
            finding_num,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze findings for KB — one finding per Opus call"
    )
    parser.add_argument(
        "--from", dest="from_num", type=int, default=None,
        help="Start from this finding number"
    )
    parser.add_argument(
        "--reanalyze", default=None,
        help="Comma-separated finding numbers to re-analyze"
    )
    parser.add_argument(
        "--bootstrap", action="store_true",
        help="Delete all analysis files and redo from scratch"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be analyzed without running"
    )
    args = parser.parse_args()

    if not FINDINGS_DIR.exists():
        abort(f"Findings directory not found: {FINDINGS_DIR}")

    if not PROMPT_PATH.exists():
        abort(f"Prompt not found: {PROMPT_PATH}")

    findings = get_all_findings()

    # Determine which findings to process
    if args.reanalyze:
        reanalyze_nums = {int(n.strip()) for n in args.reanalyze.split(",")}
        to_process = [(num, path) for num, path in findings if num in reanalyze_nums]
        missing = reanalyze_nums - {num for num, _ in to_process}
        if missing:
            abort(f"Findings not found: {sorted(missing)}")
    else:
        if args.bootstrap:
            if args.dry_run:
                print("Would delete all analysis files and redo from scratch")
            elif ANALYZED_DIR.exists():
                for f in ANALYZED_DIR.glob("*.md"):
                    f.unlink()
                print("Deleted all analysis files for bootstrap")

        if args.from_num is not None:
            to_process = [(num, path) for num, path in findings if num >= args.from_num]
        elif args.bootstrap:
            to_process = findings
        else:
            to_process = [(num, path) for num, path in findings if not is_analyzed(num)]

    if not to_process:
        print("All findings are analyzed")
        return

    print(f"Analyzing {len(to_process)} findings "
          f"({to_process[0][0]:04d}–{to_process[-1][0]:04d})")
    print(f"Model: {MODEL} | Thinking: max")

    if args.dry_run:
        for num, path in to_process:
            status = "reanalyze" if is_analyzed(num) else "new"
            print(f"  {num:04d}: {path.name} [{status}]")
        return

    ANALYZED_DIR.mkdir(parents=True, exist_ok=True)

    usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    total_start = time.time()
    processed = 0

    for i, (num, path) in enumerate(to_process):
        print(f"\n[{i + 1}/{len(to_process)}] Finding {num:04d}: {path.name}")
        analyze_finding(num, path, usage)  # aborts on any failure
        processed += 1

    total_elapsed = time.time() - total_start
    avg = total_elapsed / processed

    print(f"\n{'=' * 50}")
    print(f"Done. {processed} findings in {total_elapsed:.0f}s ({avg:.0f}s avg)")
    print(f"Tokens: in:{usage['input_tokens']:,} out:{usage['output_tokens']:,}")
    print(f"Cost: ${usage['cost_usd']:.2f}")


if __name__ == "__main__":
    main()
