# Findings Analysis — Instructions

This knowledge base feeds formal specification — Dafny verification and Alloy bounded checking. Extract facts as formalizable properties: boolean predicates for preconditions, concrete before/after states for transitions, universally quantified statements for invariants. Prefer precise types and operations over prose descriptions.

Analyze ONE implementation finding about udanax-green. Classify its content into spec-relevant categories and write a structured analysis file.

## Process

1. Read the finding you've been given.
2. Classify its content into one or more categories (see below).
3. If the finding should be omitted (test infrastructure, FEBE protocol details, build issues, performance internals, retracted findings), write an analysis file with just the omit reason.
4. For each category the finding contributes to, write an entry in the analysis file.
5. If the finding doesn't fit any existing category, use whatever category name makes sense.

## Categories

| Prefix | Meaning | Example |
|--------|---------|---------|
| `SS-*` | **State Structure** — what the state IS (types, address spaces, data model) | `SS-ADDRESS-SPACE`, `SS-DUAL-ENFILADE` |
| `PRE-*` | **Precondition** — what must hold before an operation is valid | `PRE-INSERT`, `PRE-COPY` |
| `ST-*` | **State Transition** — what an operation changes (postconditions) | `ST-INSERT`, `ST-DELETE` |
| `FC-*` | **Frame Condition** — what an operation leaves unchanged | `FC-DOC-ISOLATION`, `FC-SUBSPACE` |
| `INV-*` | **Invariant** — what always holds across all operations | `INV-MONOTONIC`, `INV-ATOMICITY` |
| `INT-*` | **Interaction** — how subsystems affect each other | `INT-LINK-INSERT`, `INT-TRANSCLUSION` |
| `EC-*` | **Edge Case** — boundary and unusual behavior | `EC-SELF-TRANSCLUSION`, `EC-EMPTY-DOC` |

**SS entries come first** — they define the state that all other categories reference.

**PRE entries pair with ST entries** — the precondition defines when an operation is valid, the state transition defines what it changes. Findings about missing validation, accepted-but-invalid inputs, or silent failures are precondition findings.

These categories are not exhaustive. If a finding genuinely doesn't fit, use a new prefix that describes the concern. Don't force it into a bad fit. Don't omit it.

## Detail Levels

- **Essential** (directly needed for postconditions, invariants, frame conditions): Full behavioral detail, concrete before/after examples, code references. 1-2KB per entry.
- **Useful** (supports understanding but not directly formalized): Key facts plus code references. ~500 bytes per entry.

## Entry Format

Each entry should be self-contained. Include:

1. **What happens**: Clear behavioral description
2. **Why it matters for spec**: Which properties/invariants this supports
3. **Code references**: Function names and file:line for traceability (use relative paths)
4. **Concrete example**: At least one before/after for essential entries
5. **Provenance**: The finding number this entry draws from

Do NOT include:
- Implementation performance details (cache strategy, memory layout)
- Test infrastructure specifics (how to run tests, FEBE opcodes)
- Speculative claims — only documented behavior

## Analysis File Format

Write to `knowledge-base/analyzed/{NNNN}.md`:

```markdown
# Finding {NNNN} Analysis

## Entries

### {CATEGORY-ID}
{entry content following the entry format above}

### {CATEGORY-ID}
{entry content}

## Omit
{reason, or remove this section if the finding has entries}
```

If a finding contributes to an existing entry ID (e.g., ST-INSERT already exists from a prior finding), use the same ID. The organize step groups entries with matching IDs together.

---

## Task

Analyze finding {{finding_num}} and write the analysis to `knowledge-base/analyzed/{{finding_num}}.md`.

1. Read `{{finding_path}}`.
2. Classify and write the analysis file according to the instructions above.

After writing, the file `knowledge-base/analyzed/{{finding_num}}.md` must exist.
