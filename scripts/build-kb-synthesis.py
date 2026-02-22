#!/usr/bin/env python3
"""
Build the synthesis knowledge base — all findings in one Opus context.

Reads all raw findings, injects them into the prompt, and produces
knowledge-base/kb-synthesis.md in a single call. The LLM sees everything
at once, enabling cross-finding synthesis and cross-references.

This is separate from the formal KB pipeline (kb-pipeline.py) which
analyzes findings incrementally.

Usage:
    python scripts/build-kb-synthesis.py
    python scripts/build-kb-synthesis.py --dry-run
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
KB_PATH = HARNESS_ROOT / "knowledge-base" / "kb-synthesis.md"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "kb-synthesis-instructions.md"

MODEL = "claude-opus-4-6"


def abort(message):
    print(f"\nABORTED: {message}", file=sys.stderr)
    sys.exit(1)


def get_all_findings():
    """Read all findings, sorted by number. Returns list of (num, text)."""
    findings = []
    for f in FINDINGS_DIR.glob("*.md"):
        match = re.match(r"(\d+)", f.name)
        if match:
            findings.append((int(match.group(1)), f.read_text()))
    findings.sort(key=lambda x: x[0])
    return findings


def main():
    parser = argparse.ArgumentParser(
        description="Build the synthesis KB — all findings in one Opus context"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show stats without running")
    args = parser.parse_args()

    if not FINDINGS_DIR.exists():
        abort(f"Findings directory not found: {FINDINGS_DIR}")

    if not PROMPT_PATH.exists():
        abort(f"Prompt not found: {PROMPT_PATH}")

    findings = get_all_findings()
    if not findings:
        abort("No findings found")

    # Build the full prompt: instructions + all findings injected
    instructions = PROMPT_PATH.read_text()

    findings_text = []
    for num, text in findings:
        findings_text.append(f"--- Finding {num:04d} ---\n{text}")
    all_findings = "\n\n".join(findings_text)

    prompt = instructions.replace("{{findings}}", all_findings)
    prompt = prompt.replace("{{last_finding}}", f"{findings[-1][0]:04d}")
    prompt = prompt.replace("{{finding_count}}", str(len(findings)))

    prompt_size = len(prompt.encode())
    print(f"Findings: {len(findings)} ({findings[0][0]:04d}–{findings[-1][0]:04d})")
    print(f"Prompt size: {prompt_size:,} bytes (~{prompt_size // 4:,} tokens)")
    print(f"Model: {MODEL} | Thinking: max")

    if args.dry_run:
        print("\nDry run — not running")
        return

    KB_PATH.parent.mkdir(parents=True, exist_ok=True)

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
        abort(f"claude exited {result.returncode} ({elapsed:.0f}s)\n{stderr_lines}")

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

    if KB_PATH.exists():
        kb_size = KB_PATH.stat().st_size
        print(f"KB written to {KB_PATH} ({kb_size:,} bytes)")
    else:
        print("WARNING: kb-synthesis.md was not created", file=sys.stderr)


if __name__ == "__main__":
    main()
