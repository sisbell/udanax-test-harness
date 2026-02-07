# Finding 053: DELETE Shifts V-Positions, Can Produce Negative Tumblers

**Status**: Documented
**Severity**: Semantic
**Component**: POOM operations, tumbler arithmetic
**Tests**: `links/delete_text_before_link.json`, `links/delete_partial_text_before_link.json`

## Summary

When DELETE removes text content, ALL entries in the POOM that are positioned after the deletion point have their V-positions shifted leftward by the deletion width. This shift is performed by `tumblersub` and can produce **negative tumblers** when the deletion width exceeds the entry's current position.

Entries with negative V-positions remain in the POOM tree but become invisible to queries because negative tumblers compare as LESS than all positive tumblers, effectively placing them "before" the valid V-space.

## Behavior

### V-Position Shifting Mechanism

From `edit.c:31-76`, the `deletend` function:

```c
case 2:
    tumblersub (&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);
    /* This will get set to modified in setwisp */
    break;
```

**Case 2** applies to POOM entries that are positioned entirely **after** the deletion range. For each such entry, the deletion width is subtracted from its V-position.

### Tumbler Subtraction Allowing Negative Results

From `tumble.c:406-440`, `tumblersub` implementation:

```c
int tumblersub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
  tumbler temp;

  if (iszerotumbler (bptr))
    movetumbler (aptr, cptr);
  else if (tumblereq (aptr, bptr))
    tumblerclear (cptr);
  else if (iszerotumbler (aptr)) {
    movetumbler (bptr, cptr);
    cptr->sign = !cptr->sign;      // ← Negate
  } else {
    movetumbler (bptr, &temp);
    temp.sign = !temp.sign;        // ← Negate and add
    tumbleradd (aptr, &temp, cptr);
  }
  tumblerjustify (cptr);
}
```

The function implements subtraction as addition of a negated value. When `a - b` would be negative (i.e., `b > a`), the result tumbler has its `sign` field set to 1.

Tumblers have a `sign` field that can be 0 (positive) or 1 (negative). There is **no validation** preventing negative V-positions in the POOM.

### Observed Effects

**Test Setup**: Document with text at 1.1-1.15, link from 1.1-1.5 to 1.10-1.14

**Test 1 - Complete Deletion**:
- DELETE 15 bytes starting at 1.1 (all text removed)
- Link V-position would shift: 2.something → 2.(something - 15) → **negative**
- Result: `RETRIEVEVSPANSET` shows only `2.1` to `2.1+0.1` (the link orgl V-span remains visible)
- Result: `FOLLOWLINK` returns **empty endsets** `[]`

**Test 2 - Incremental Deletion**:
1. Initial: Link source at 1.5
2. DELETE 3 bytes at 1.1: Link source shifts to **1.2** (confirmed in golden test)
3. DELETE 10 more bytes at 1.1: Link source would shift to 1.2 - 0.10 = **negative**
4. Result: `FOLLOWLINK` returns **empty endsets** `[]`

## Technical Analysis

### Why Endsets Become Empty

When link endsets have negative V-positions:

1. The POOM entry still exists in the tree
2. Its V-position tumbler has `sign=1` (negative)
3. When `FOLLOWLINK` retrieves the endset V-span and converts to I-addresses:
   - `orglinks.c:446-448` (FOLLOWLINK implementation) calls conversion routines
   - Negative V-positions fail to map to valid I-addresses
   - Empty result returned

From `tumblercmp` (tumble.c:72-85):
```c
if (iszerotumbler(bptr))
    return (aptr->sign ? LESS : GREATER);
if (aptr->sign == bptr->sign)
    return (aptr->sign ? abscmp(bptr,aptr) : abscmp(aptr,bptr));
return (aptr->sign ? LESS : GREATER);  // ← negative always LESS
```

Negative tumblers compare as LESS than all positive tumblers, effectively sorting them "before" the start of the valid address space.

### Position Digit Cannot Go Below 1 (Because It Goes Negative Instead)

The question "can the position digit go below 1?" has a nuanced answer:

- **Positive tumblers**: Position digit ≥ 1 (enforced by tumbler normalization)
- **After excessive deletion**: Tumbler becomes **negative** rather than having digit < 1
- **Example**: 1.2 - 0.10 = **-0.8** (sign=1, mantissa=[8], exp=-1), NOT 0.12

The tumbler representation uses sign-magnitude format, not two's complement. Subtraction that would underflow produces a negative tumbler with positive magnitude.

## Implications

### For Link Survival

**Links physically survive deletion of all their content** (consistent with Finding 038 on orphaned links), but:

1. Link endsets become **unretrievable** when V-positions go negative
2. The link orgl itself remains in I-space (permanent)
3. The POOM entry exists but maps to invalid V-space
4. `FINDLINKS` cannot locate the link (endsets empty)
5. Link becomes a **"deeply orphaned"** state: not just content deleted, but V-position invalid

### For POOM Integrity

DELETE can create POOM entries with negative V-positions, which:

1. Violate the implicit assumption that V-space is non-negative
2. Are invisible to traversal (sort before all positive positions)
3. Waste POOM tree space (unreachable but allocated)
4. Cannot be reclaimed without garbage collection

### For Invariant I₁ (POOM Bijectivity)

From EWD-018, I₁ requires `poom_d` to be a bijection between V-addresses and I-addresses.

**Negative V-positions violate I₁**: They are in the domain of the POOM map but do not correspond to valid V-addresses in the document's V-stream (which is defined over non-negative tumblers only).

The system allows I₁ violations to persist in the POOM tree structure.

## Citation

**Code References**:
- Deletion shift: `edit.c:63`
- Tumbler subtraction: `tumble.c:406-440`
- Tumbler comparison: `tumble.c:72-85`
- Sign field negation: `tumble.c:424, 427`

**Golden Tests**:
- `golden/links/delete_text_before_link.json` (lines 118-122: empty endsets after full deletion)
- `golden/links/delete_partial_text_before_link.json` (lines 118-126: shift from 1.5→1.2; lines 160: empty endsets after negative shift)

**Related Findings**:
- Finding 038: Orphaned links (content deleted but I-addresses remain)
- Finding 023: Link immutability (endsets in I-space are immutable)

## Open Questions

1. **Can negative V-positions be reconstituted?** If text is re-inserted at 1.1, do negative positions become positive again?
2. **What happens to link orgl V-span (2.x)?** Does the link's home position also shift negative, or only endsets?
3. **Is there cleanup?** Are negative-position POOM entries ever garbage collected?
4. **REARRANGE interaction**: Can REARRANGE produce negative V-positions via similar tumbler arithmetic?
5. **CREATENEWVERSION**: Does version copying preserve negative V-positions?
