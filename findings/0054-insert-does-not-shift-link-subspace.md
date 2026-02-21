# Finding 0054: INSERT Does Not Shift Link Subspace -- The Second Cut Blade

**Date:** 2026-02-07
**Category:** POOM operations / Subspace isolation
**Agent:** Gregory
**Related:** Finding 0038, Finding 0052, Finding 0053

## Summary

INSERT at V-position 1.x does NOT shift link entries at V-position 2.x. The mechanism is `findaddressofsecondcutforinsert`, which computes the start of the next subspace as a second cut blade. This blade causes `insertcutsectionnd` to classify all crums at or beyond the subspace boundary as case 2 (no shift).

EWD-037's claim that `insertcutsectionnd` shifts ALL crums after the insertion point via lexicographic comparison is incorrect. The two-blade knife structure explicitly partitions the shift to the current subspace only.

## Test Evidence

**Golden test:** `golden/subspace/insert_text_check_both_link_positions.json`

Setup:
- Document with text "ABCDE" at V-positions 1.1-1.5
- Link at V-position 2.1 (link ISA: `1.1.0.1.0.1.0.2.1`)

Action: INSERT "XY" at V-position 1.3

Results:
- **V-position 2.1 AFTER insert:** `["1.1.0.1.0.1.0.2.1"]` -- link STILL HERE
- **V-position 2.3 AFTER insert:** `[]` -- EMPTY, nothing shifted here
- **FINDLINKS after insert:** Link still discoverable (returned twice -- source + target match)
- **FOLLOWLINK after insert:** Returns `<SpecSet [<VSpec in 1.1.0.1.0.2, at 1.2 for 0.2>]>` -- still resolves
- **Text after insert:** `"ABXYCDE"` -- text shifted correctly within 1.x subspace

## Code Trace

### The Two-Blade Knife

When `makegappm` runs for an insertion at V-position 1.3, it constructs a two-blade knife:

```c
// insertnd.c:144-146
movetumbler (&origin->dsas[V], &knives.blades[0]);    // blade[0] = 1.3
findaddressofsecondcutforinsert(&origin->dsas[V], &knives.blades[1]);  // blade[1] = 2.1
knives.nblades = 2;
```

### How findaddressofsecondcutforinsert Computes 2.1

**File:** `insertnd.c:174-183`

```c
int findaddressofsecondcutforinsert(tumbler *position, tumbler *secondcut)
{    /*needs this to give it a place to find intersectionof for text is 2.1*/
    tumbler zero, intpart;
    tumblerclear (&zero);
    tumblerincrement (position, -1, 1, secondcut);        // Step 1: 1.3 -> 2.3
    beheadtumbler (position, &intpart);                   // Step 2: 1.3 -> 0.3
    tumblerincrement(secondcut, 0,                        // Step 3: 2.3 -> 2.0
        -tumblerintdiff(&intpart, &zero), secondcut);
    tumblerincrement (secondcut, 1, 1, secondcut);        // Step 4: 2.0 -> 2.1
}
```

For insertion at `1.3`:
1. Increment first digit by 1: `1.3 -> 2.3`
2. Behead `1.3` to get fractional tail: `0.3`
3. Subtract fractional part: `2.3 - 0.3 = 2.0`
4. Add 1 at second digit: `2.0 -> 2.1`

**Result: blade[1] = 2.1** -- exactly the start of the link subspace.

The comment in the source code confirms intent: "needs this to give it a place to find intersectionof for text is 2.1". This function was deliberately designed to compute the subspace boundary.

### How insertcutsectionnd Classifies the Link Crum

**File:** `edit.c:207-233`

```c
INT insertcutsectionnd(typecorecrum *ptr, typewid *offset, typeknives *knives)
{
    if (knives->nblades == 2) {
        i = 1;
        cmp = whereoncrum(ptr, offset, &knives->blades[1], knives->dimension);
        // For link crum at 2.1: blade[1]=2.1 is ON the left border of crum [2.1, 2.2)
        // whereoncrum returns ONMYLEFTBORDER (-1)
        if (cmp <= ONMYLEFTBORDER) {
            return (2);    // <-- CASE 2: NO SHIFT
        }
    }
    // ...blade[0] check never reached for link crum
}
```

The link crum at 2.1 is classified as **case 2** because blade[1] = 2.1 lands exactly on the crum's left border (`ONMYLEFTBORDER`). Case 2 means "this crum is entirely at or beyond the second cut" -- it does NOT get shifted.

### Classification Logic Summary

For any crum in the POOM tree, `insertcutsectionnd` with blades [1.3, 2.1] classifies as:

| Crum V-position | blade[1]=2.1 check | blade[0]=1.3 check | Case | Action |
|---|---|---|---|---|
| < 1.3 (e.g., 1.1) | TOMYLEFT -> fall through | TOMYLEFT -> fall through | 0 | No shift (before insertion) |
| = 1.3 (on boundary) | TOMYLEFT -> fall through | ONMYLEFTBORDER | 1 | SHIFT right |
| 1.3 < x < 2.1 (e.g., 1.5) | TOMYLEFT -> fall through | TOMYLEFT... or case depends | varies | SHIFT right |
| >= 2.1 (e.g., 2.1) | ONMYLEFTBORDER | never reached | 2 | No shift (beyond second cut) |

## Architectural Significance

The `findaddressofsecondcutforinsert` function is the implementation of subspace isolation. It uses tumbler arithmetic to compute "the next subspace boundary" from any insertion point. For ANY insertion at `N.x` (where N is the subspace digit), the second blade will be `(N+1).1`.

This means:
- INSERT at 1.x shifts only crums in the 1.x range (text subspace)
- INSERT at 2.x would shift only crums in the 2.x range (link subspace)
- INSERT at 3.x would shift only crums in the 3.x range (type subspace)

Each subspace is a self-contained shift domain.

## Corrections

### EWD-037 Is Incorrect

EWD-037 claims that `insertcutsectionnd` shifts ALL crums after the insertion point via lexicographic tumbler comparison. This is wrong. The two-blade knife structure creates a bounded shift region. Only crums between blade[0] and blade[1] get shifted. Crums at or beyond blade[1] are classified as case 2 and left untouched.

### Finding 0038 Is Correct

Finding 0038 (POOM Subspace Independence) correctly identifies that "operations in the text subspace (INSERT, DELETE) do not renumber or shift link V-positions." This finding provides the detailed code-level mechanism that explains WHY.

### Finding 0052 Needs Clarification

Finding 0052 (CREATELINK Shifts POOM Entries) correctly identifies that `makegappm` is called during CREATELINK. But the shift from a link creation at 2.x would only affect crums in the 2.x range (other links), not crums in 1.x (text). The second cut blade for an insertion at 2.x would be 3.1, so text crums are safe.

## Related Findings

- **Finding 0038**: POOM Subspace Independence (behavioral observation, confirmed here)
- **Finding 0052**: CREATELINK Shifts POOM Entries (mechanism analysis, clarified here)
- **Finding 0053**: DELETE Shifts V-Positions (analogous mechanism for deletion -- uses `deletecutsectionnd` which likely has similar two-blade structure)
- **Finding 0031**: Tumbler Arithmetic (explains the digit-level operations)

## References

- `insertnd.c:124-172` -- makegappm with two-blade knife
- `insertnd.c:174-183` -- findaddressofsecondcutforinsert (subspace boundary computation)
- `edit.c:207-233` -- insertcutsectionnd (classification logic)
- `retrie.c:345-391` -- whereoncrum (spatial relationship)
- `common.h:86-90` -- TOMYLEFT, ONMYLEFTBORDER, THRUME, ONMYRIGHTBORDER, TOMYRIGHT
- `golden/subspace/insert_text_check_both_link_positions.json` -- empirical evidence
