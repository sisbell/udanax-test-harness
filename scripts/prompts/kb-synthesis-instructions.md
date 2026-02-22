# KB Synthesis — Synthesize All Findings

You are building a synthesis knowledge base from {{finding_count}} implementation findings about udanax-green. This KB is the map — synthesize all findings into integrated, cross-referenced descriptions that show how the system's components connect.

## Process

1. Read all findings below.
2. Classify each finding into one or more categories.
3. Synthesize entries — weave complementary findings into integrated descriptions.
4. Add cross-references between related entries (`[ST-INSERT]`, `[FC-SUBSPACE]`, etc.).
5. Write the KB to `knowledge-base/kb-synthesis.md`.

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

Some findings contribute to multiple entries. Some findings are not relevant to specification and should be omitted (test infrastructure, FEBE protocol details, build issues, performance internals, retracted findings).

## Entry Guidelines

Each entry should be self-contained. Include:

1. **What happens**: Clear behavioral description
2. **Why it matters for spec**: Which properties/invariants this supports
3. **Code references**: Function names and file:line for traceability (use relative paths)
4. **Concrete example**: At least one before/after for essential entries
5. **Cross-references**: Cite related entries as `[ENTRY-ID]` — these connections are crucial
6. **Provenance**: Which findings this entry draws from

Detail levels:
- **Essential** (directly needed for postconditions, invariants, frame conditions): Full behavioral detail, concrete before/after examples, code references. 1-2KB per entry.
- **Useful** (supports understanding but not directly formalized): Key facts plus code references. ~500 bytes per entry.

Do NOT include:
- Implementation performance details (cache strategy, memory layout)
- Test infrastructure specifics (how to run tests, FEBE opcodes)
- Speculative claims — only documented behavior
- Duplicate information across entries — cross-reference instead

## Output Format

Write to `knowledge-base/kb-synthesis.md`:

```markdown
# Synthesis Knowledge Base
<!-- last-finding: {{last_finding}} -->

> Implementation knowledge about udanax-green, synthesized for specification writing.
> Cite entries as `[SS-ADDRESS-SPACE]`, `[ST-INSERT]`, `[FC-SUBSPACE]`, etc.

## State Structure

### SS-ENTRY-ID
{integrated entry}

---

## Preconditions
...

## State Transitions
...

## Frame Conditions
...

## Invariants
...

## Interactions
...

## Edge Cases
...
```

Target size: 40-100KB. Larger means too verbose, smaller means missing detail.

## Quality Check

Before writing, verify:
- Every entry has provenance (finding numbers)
- Every essential entry has at least one concrete example
- Cross-references point to entries that exist
- Entry IDs are consistent (ST-INSERT not ST_INSERT)

---

## Findings

{{findings}}
