# Finding 0056: Rearrange Operation Semantics

**Date:** 2026-02-10
**Status:** Validated via code analysis and golden tests
**Tests:** `golden/rearrange/*.json`, code analysis in `backend/edit.c:78-184`

## Summary

The REARRANGE operation (FEBE opcode 3) moves content within the POOM by adding computed offsets to V-addresses while preserving I-addresses. It operates via cut points specified in the **pre-move address space**, and implements either pivot (3 cuts, 2 adjacent regions) or swap (4 cuts, 2 non-adjacent regions with middle section).

## Core Implementation

### Algorithm (edit.c:78-184)

```c
int rearrangend(typecuc *fullcrumptr, typecutseq *cutseqptr, INT index) {
    // 1. Convert cuts to sorted "knives"
    sortknives(&knives);

    // 2. Compute offset for each region based on cut positions
    makeoffsetsfor3or4cuts(&knives, diff);

    // 3. Classify each content span by which region it's in
    i = rearrangecutsectionnd(ptr, &fgrasp, &knives);

    // 4. Apply computed offset to move content
    tumbleradd(&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index]);
}
```

The key insight: **rearrange adds tumbler offsets to existing V-addresses**. It does not copy content or change I-addresses.

### Offset Computation for 3 Cuts (Pivot)

For cuts at positions `cut0`, `cut1`, `cut2`:

```c
diff[1] = cut2 - cut1;      // size of region 2
diff[2] = -(cut1 - cut0);   // negative size of region 1
```

**Regions:**
- Region 0: content before cut0 (never moves, no offset)
- Region 1: [cut0, cut1) - moves forward by diff[1]
- Region 2: [cut1, cut2) - moves backward by |diff[2]|
- Region 4: content after cut2 (never moves, no offset)

**Result:** The two adjacent regions swap positions.

### Offset Computation for 4 Cuts (Swap)

For cuts at positions `cut0`, `cut1`, `cut2`, `cut3`:

```c
diff[1] = cut2 - cut0;                    // offset for region 1
diff[2] = (cut3 - cut2) - (cut1 - cut0);  // offset for middle region
diff[3] = -(cut2 - cut0);                 // offset for region 3 (negative)
```

**Regions:**
- Region 0: before cut0 (no move)
- Region 1: [cut0, cut1) - moves to where region 3 was
- Region 2: [cut1, cut2) - middle section, shifts to accommodate swap
- Region 3: [cut2, cut3) - moves to where region 1 was
- Region 4: after cut3 (no move)

## Answers to Semantic Questions

### 1. Is v₃ in pre-move or post-move address space?

**Pre-move.** All cut points are positions in the document **before** rearrangement. The algorithm:
1. Reads current V-positions
2. Computes offsets based on pre-move cut positions
3. Adds offsets to move content

**Evidence:**
- `makeoffsetsfor3or4cuts` takes only the cut positions (`knives->blades[]`)
- Offsets are computed purely from arithmetic on these positions
- No reference to post-move state

[edit.c:164-184]

### 2. What happens when v₃ falls inside the source span [v₁, v₂]?

This question misunderstands the operation. Pivot has 3 cuts defining **2 adjacent regions**, not a source/destination model:
- Region 1: [cut0, cut1)
- Region 2: [cut1, cut2)

There is no "v₃ inside source" case. The cuts must be properly ordered: cut0 < cut1 < cut2.

**Actual behavior if cuts are misordered:** `sortknives(&knives)` reorders them, so the operation proceeds with sorted cuts regardless of input order.

[edit.c:107]

### 3. For the three main cases, what is the resulting arrangement?

**Pivot (3 cuts at cut0, cut1, cut2):**

```
Before: [... A ...][... region1 ...][... region2 ...][... B ...]
              ^cut0          ^cut1          ^cut2

After:  [... A ...][... region2 ...][... region1 ...][... B ...]
```

- Content before cut0: unchanged position
- Region 1 [cut0, cut1): moves to [cut1, cut2)
- Region 2 [cut1, cut2): moves to [cut0, cut1)
- Content after cut2: unchanged position

**Example:** `"ABCDE"` with cuts at 1.2, 1.4, 1.6
- A (at 1.1): stays at 1.1
- BC (at 1.2-1.3): moves to 1.4-1.5
- DE (at 1.4-1.5): moves to 1.2-1.3
- Result: `"ADEBC"`

[Finding 0016, test: `pivot_adjacent_regions`]

**Swap (4 cuts at cut0, cut1, cut2, cut3):**

```
Before: [... A ...][... region1 ...][... middle ...][... region3 ...][... B ...]
              ^cut0          ^cut1          ^cut2            ^cut3

After:  [... A ...][... region3 ...][... middle ...][... region1 ...][... B ...]
```

- Region 1 and region 3 swap positions
- Middle section shifts to accommodate the swap
- Content before cut0 and after cut3: unchanged

**Example:** `"ABCDEFGH"` with cuts at 1.2, 1.4, 1.6, 1.8
- A (at 1.1): stays
- BC (at 1.2-1.3): swaps with FG
- DE (at 1.4-1.5): middle section, shifts
- FG (at 1.6-1.7): swaps with BC
- H (at 1.8): stays
- Result: `"AFGDEBCH"`

[Finding 0016, test: `swap_non_adjacent`]

### 4. Does rearrange preserve I-addresses exactly?

**Yes.** Rearrange operates on the POOM enfilade by modifying the V-address (dsas[index]) of each content span without touching the I-address.

**Code evidence:**
```c
tumbleradd(&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index]);
```

This adds an offset to the V-address component (`dsas[index]`) of the displacement (`cdsp`). The I-address of the content is stored separately and is never modified.

**Behavioral evidence:**
- Links bound to rearranged content remain discoverable [Finding 0016, test: `swap_with_links`]
- Transclusions of rearranged content still reference the same I-addresses
- `retrieve_vspanset` shows same I-addresses at different V-positions after rearrange

[edit.c:125, Finding 0016]

### 5. How does the implementation handle rearrange?

**Not a cut-and-paste.** Rearrange operates **in-place on the POOM enfilade** by:
1. Making cuts to ensure span boundaries at cut points
2. Classifying each span into regions (0, 1, 2, 3, or 4)
3. Adding computed tumbler offsets to V-addresses for regions that move

**Not copying content:**
- No new I-addresses are allocated
- No content is duplicated in permascroll
- The same enfilade nodes (crums) are retained, just with modified V-addresses

**Key functions:**
- `makecutsnd()` - inserts cut points into enfilade structure
- `rearrangecutsectionnd()` - determines which region a span is in
- `tumbleradd()` - modifies V-address in place
- `recombine()` - merges adjacent spans after operation

[edit.c:78-160]

## Edge Cases and Constraints

### Subspace Boundaries

Rearrange **can move content across subspace boundaries** because offsets are computed purely from tumbler arithmetic with no digit-0 (subspace) validation.

**Example:** Content at 1.x can be moved to 2.x by using cuts that span the boundary.

This violates the content discipline (CD0) which requires content type to match subspace. See [Finding 0051].

### Empty Regions

If a region [cutN, cutN+1) is empty (no content), it contributes to offset computation but doesn't move anything. The algorithm works correctly because it operates per-span, and there are simply no spans in that region.

### Zero-Width Moves

Pivot with cut0 = cut1 or cut1 = cut2 creates a zero-width region. The offset becomes zero, effectively making it a no-op for that region.

## Comparison with Delete+Insert

| Aspect | REARRANGE | DELETE + INSERT |
|--------|-----------|-----------------|
| I-addresses | Preserved | New I-addresses allocated |
| Operation count | 1 | 2+ |
| Links to content | Follow content | Break (link to deleted I-addr) |
| Transclusions | Maintained | Lost (original I-addr removed) |
| Cross-document refs | Survive | Break |

Rearrange is the **only** operation that moves content while preserving identity.

## Related

- **Finding 0016**: Rearrange operations (pivot and swap) - behavioral tests
- **Finding 0051**: Rearrange can cross subspace boundaries
- **Finding 0002**: Content identity immutability (transclusion)
- **Finding 0005**: Link survivability through edits
- **EWD-035**: Content discipline (CD0) - violated by cross-subspace rearrange

## Files

- `udanax-test-harness/backend/edit.c:78-184` - Core rearrange implementation
- `udanax-test-harness/febe/scenarios/rearrange.py` - Test scenarios
- `udanax-test-harness/findings/0016-rearrange-operations.md` - Behavioral findings
