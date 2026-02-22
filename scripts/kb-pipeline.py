#!/usr/bin/env python3
"""
Findings KB pipeline — analyze, assemble, organize, audit.

Orchestrates the four stages of KB construction. Stops after audit
for human review.

Usage:
    python scripts/kb-pipeline.py                          # full pipeline
    python scripts/kb-pipeline.py --bootstrap              # rebuild from scratch
    python scripts/kb-pipeline.py --reanalyze 036,042      # repair cycle
    python scripts/kb-pipeline.py --analyze                # stage 1 only
    python scripts/kb-pipeline.py --assemble               # stage 2 only
    python scripts/kb-pipeline.py --organize               # stage 3 only
    python scripts/kb-pipeline.py --audit                  # stage 4 only
    python scripts/kb-pipeline.py --dry-run                # preview all stages
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
HARNESS_ROOT = SCRIPTS_DIR.parent
AUDIT_PATH = HARNESS_ROOT / "knowledge-base" / "audit.md"


def run_stage(name, script, args=None):
    """Run a pipeline stage. Aborts pipeline on failure."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)]
    if args:
        cmd.extend(args)

    print(f"\n{'=' * 50}")
    print(f"STAGE: {name}")
    print(f"{'=' * 50}")

    start = time.time()
    result = subprocess.run(cmd, cwd=str(HARNESS_ROOT))
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n{name} failed (exit {result.returncode}, {elapsed:.0f}s)")
        sys.exit(1)

    print(f"\n{name} complete ({elapsed:.0f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="Findings KB pipeline — analyze, assemble, organize, audit"
    )

    # Stage selection
    parser.add_argument("--analyze", action="store_true", help="Run analyze stage only")
    parser.add_argument("--assemble", action="store_true", help="Run assemble stage only")
    parser.add_argument("--organize", action="store_true", help="Run organize stage only")
    parser.add_argument("--audit", action="store_true", help="Run audit stage only")
    parser.add_argument("--skip-opus", action="store_true", help="Skip Opus miscategorization check in audit")

    # Pipeline options
    parser.add_argument("--bootstrap", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--reanalyze", default=None, help="Re-analyze specific findings (comma-separated)")
    parser.add_argument("--from", dest="from_num", type=int, default=None, help="Start analysis from this finding")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")

    args = parser.parse_args()

    # Determine which stages to run
    single_stage = args.analyze or args.assemble or args.organize or args.audit

    # Build stage args
    analyze_args = []
    if args.bootstrap:
        analyze_args.append("--bootstrap")
    if args.reanalyze:
        analyze_args.extend(["--reanalyze", args.reanalyze])
    if args.from_num is not None:
        analyze_args.extend(["--from", str(args.from_num)])
    if args.dry_run:
        analyze_args.append("--dry-run")

    assemble_args = []
    if args.dry_run:
        assemble_args.append("--dry-run")

    audit_args = []
    if args.skip_opus:
        audit_args.append("--skip-opus")

    total_start = time.time()

    if single_stage:
        if args.analyze:
            run_stage("Analyze", "build-findings-kb.py", analyze_args)
        if args.assemble:
            run_stage("Assemble", "assemble-findings-kb.py", assemble_args)
        if args.organize:
            run_stage("Organize", "organize-findings-kb.py")
        if args.audit:
            run_stage("Audit", "audit-findings-kb.py", audit_args)
    else:
        # Full pipeline
        run_stage("Analyze", "build-findings-kb.py", analyze_args)
        run_stage("Assemble", "assemble-findings-kb.py", assemble_args)

        if args.dry_run:
            print("\nDry run — skipping organize and audit")
        else:
            run_stage("Organize", "organize-findings-kb.py")
            run_stage("Audit", "audit-findings-kb.py", audit_args)

            total_elapsed = time.time() - total_start
            print(f"\n{'=' * 50}")
            print(f"Pipeline complete ({total_elapsed:.0f}s)")
            print(f"{'=' * 50}")
            print(f"\nReview: knowledge-base/audit.md")
            if AUDIT_PATH.exists():
                lines = AUDIT_PATH.read_text().split("\n")
                for line in lines[:10]:
                    print(f"  {line}")
                if len(lines) > 10:
                    print(f"  ... ({len(lines) - 10} more lines)")


if __name__ == "__main__":
    main()
