# Findings KB Pipeline

## Motivation

Findings are produced by agents as they build golden tests against the udanax-green implementation, documenting each newly discovered behavior. They accumulate organically — each finding captures what one test run revealed, in whatever structure made sense at the time.

Raw findings are the wrong input for specification writing. There are 50+ of them, they overlap, they sometimes contradict each other, and the knowledge is scattered — half of an invariant in one finding, the other half in another. Spec-writing agents need pre-processed, structured knowledge they can consume directly.

This pipeline transforms raw findings into two knowledge bases, each serving a distinct role during specification writing.

## Two Knowledge Bases

### `kb-synthesis.md` — Cross-cutting synthesis

The synthesis KB exists to capture relationships *between* findings. When you're specifying an insert operation, you need to know: what happens to links? How does the address space shift? What about transclusions into the affected region? These cross-cutting concerns are invisible when looking at findings individually — they only emerge when all findings are seen together in one context.

The synthesis KB is built in a single LLM pass over all raw findings. It produces a cross-referenced narrative where entries cite each other (`[ST-INSERT]`, `[FC-SUBSPACE]`, `[INV-MONOTONIC]`). During spec writing, these cross-references guide agents to related concerns they might otherwise miss.

### `kb-formal.md` — Formal property extraction

The formal KB exists to identify precise, formalizable properties: boolean predicates for preconditions, concrete before/after states for transitions, universally quantified statements for invariants. Each finding gets its own LLM call with max thinking — full attention on extracting exact properties from that one finding, without distraction.

The formal KB does not deal in cross-cutting concerns. Its job is depth: get the individual properties right, classified into the correct categories (SS, PRE, ST, FC, INV, INT, EC), with code references and concrete examples. The organize step groups entries by category and preserves every finding's contribution separately — no merging, no synthesis, no judgment calls. Contradictions between findings are preserved for the spec-writing agent to resolve.

### Together

The synthesis KB tells you what connects. The formal KB tells you what's precise. Together they give spec-writing agents both the map and the evidence.

## Pipeline

This pipeline produces `kb-formal.md`. The synthesis KB is produced separately by `build-kb-synthesis.py` in a single pass over all raw findings.

## Flow

```
Raw Findings
    │
    ▼
ANALYZE — classify each finding independently
    │      One finding at a time, full attention per finding.
    │      No awareness of prior findings or the KB.
    │      Output: one analysis file per finding.
    │
    ▼
ASSEMBLE — concatenate analysis files
    │        Pure Python. No parsing, no grouping.
    │        Produces a single file for the organize step.
    │
    ▼
ORGANIZE — group by category, produce kb-formal.md
    │        Pure Python. No LLM call.
    │        Groups entries by category prefix.
    │        Preserves every finding's contribution separately.
    │        Adds co-occurrence data (related entries from
    │        the same finding). No merging, no synthesis.
    │
    ▼
AUDIT — mechanical checks + optional miscategorization review
    │     Python: invented categories, category imbalance,
    │     cross-reference integrity.
    │     Optional Opus: miscategorization detection.
    │     Output: audit report.
    │
    ▼
HUMAN DECISION
    │
    ├── Accept
    │     KB is ready for consumption by spec agents.
    │
    ├── Re-analyze
    │     Specific findings were miscategorized.
    │     Re-run analysis for those findings → reassemble → re-audit.
    │
    └── Expand taxonomy
          Invented categories reveal a real gap.
          Add new category to the analysis instructions.
          Re-analyze affected findings → reassemble → re-audit.
```

## Categories

The KB organizes knowledge by its role in specification:

| Prefix | Role |
|--------|------|
| SS     | What the state IS — types, address spaces, data model |
| PRE    | When an operation is valid — preconditions |
| ST     | What an operation changes — postconditions |
| FC     | What an operation preserves — frame conditions |
| INV    | What always holds — invariants |
| INT    | How subsystems affect each other — interactions |
| EC     | Boundary and unusual behavior — edge cases |

These categories are not fixed. If the analysis step can't fit a finding, it invents a prefix. The audit flags it. The human decides whether it's a real gap or a misclassification.

## Key Constraints

- **One finding per analysis.** Quality degrades when processing multiple findings in a single session. Each finding gets its own LLM call with max thinking.

- **Analysis never reads the KB.** The model sees only the finding and the instructions. No context pollution from prior classifications.

- **Assembly is mechanical.** Pure concatenation. No parsing, no interpretation. Eliminates format fragility between analyze and organize.

- **Organize is mechanical.** Pure Python grouping by category prefix. No LLM call, no synthesis, no merging. Each finding's contribution is preserved separately under its entry ID. The spec-writing agent decides how to reconcile multiple perspectives on the same entry.

- **Contradictions preserved.** The organize step does not resolve conflicts between findings. When two findings disagree about the same entry, both are presented with provenance. Consuming agents handle contradictions.

- **Human intervenes once — after audit.** Everything before the audit is automated. The audit produces a report. The human decides what to do.

## Commands

```bash
# Full pipeline — analyze → assemble → organize → audit
python scripts/kb-pipeline.py

# Full pipeline from scratch
python scripts/kb-pipeline.py --bootstrap

# Individual stages
python scripts/kb-pipeline.py --analyze
python scripts/kb-pipeline.py --assemble
python scripts/kb-pipeline.py --organize
python scripts/kb-pipeline.py --audit

# Audit without Opus (mechanical checks only)
python scripts/audit-findings-kb.py --skip-opus

# Repair cycle — re-analyze specific findings, reassemble, re-organize, re-audit
python scripts/kb-pipeline.py --reanalyze 036,042

# Preview without running
python scripts/kb-pipeline.py --dry-run

# Synthesis KB (separate from pipeline)
python scripts/build-kb-synthesis.py
```
