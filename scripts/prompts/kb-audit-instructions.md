# KB Audit — Miscategorization Review

Read the organized knowledge base and check whether per-finding analyses got the categorization right.

## Categories

| Prefix | Meaning |
|--------|---------|
| `SS-*` | State Structure — what the state IS (types, address spaces, data model) |
| `PRE-*` | Preconditions — when an operation is valid (what must hold before) |
| `ST-*` | State Transitions — what an operation changes (postconditions) |
| `FC-*` | Frame Conditions — what an operation leaves unchanged |
| `INV-*` | Invariants — what always holds across all operations |
| `INT-*` | Interactions — how subsystems affect each other |
| `EC-*` | Edge Cases — boundary and unusual behavior |

## Detection Heuristics

- **ST entries containing precondition language**: "must exist", "requires", "only valid when", "validation", "always returns TRUE", "does not enforce", "accepts invalid". These are PRE facts hiding in ST entries.
- **ST entries containing structural definitions**: explanations of what addresses ARE, what the POOM IS, how subspaces are laid out. These are SS facts hiding in ST entries.
- **INV entries that are really about preconditions**: invariants about what the system does NOT enforce are often cross-cutting precondition observations.
- **INT entries that are really invariants**: if an interaction holds unconditionally across all states, it might be an invariant.
- **EC entries that are really precondition violations**: edge cases that describe "what happens when input is invalid" are precondition boundary findings.

## What to Do

1. Read `knowledge-base/kb-formal.md`.
2. For each entry, check whether its primary content matches its category prefix.
3. Write findings to `knowledge-base/miscategorized.md`.

An entry can mention other categories — the issue is when its **primary content** belongs elsewhere.

## What NOT to Do

- Do not modify the KB. Read-only. Produce a report.
- Do not re-classify entries. Flag issues; the human decides.

## Output Format

Write to `knowledge-base/miscategorized.md`:

```markdown
# Miscategorized Entries

{N} entries flagged out of {total} reviewed.

### {ENTRY-ID}
**Current category:** {prefix}
**Suggested category:** {better prefix}
**Reason:** {why the primary content belongs elsewhere}
**Finding(s):** {which finding contributions are affected}

### {ENTRY-ID}
...
```

If no miscategorizations are found, write:

```markdown
# Miscategorized Entries

No miscategorizations detected. All {total} entries match their category prefix.
```
