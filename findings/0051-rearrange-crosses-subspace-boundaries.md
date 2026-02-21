# Finding 0050: REARRANGE Can Cross Subspace Boundaries

**Date:** 2026-02-07
**Status:** Validated via golden test
**Test:** `golden/rearrange/pivot_cross_subspace_boundary.json`

## Summary

REARRANGE operations (pivot and swap) can move content across subspace boundaries. Content originally placed in the 1.x text subspace can be moved to 2.x link subspace positions through rearrangement, and vice versa. This violates the content discipline (CD0) which requires that content type matches subspace.

## Evidence

Test scenario `pivot_cross_subspace_boundary` demonstrates:

1. Insert "ABC" at V-positions 1.1-1.3 (text subspace)
2. Insert "DEF" at V-positions 1.5-1.7 (text subspace)
3. Pivot with cuts at 1.1, 1.4, 2.5

Expected if subspace-constrained: Operation should fail or content should remain in 1.x.

Actual behavior:
- Operation succeeds
- Content "ABC" is retrievable from 2.x subspace: `retrieve_after_2x: ['ABC']`
- Content "DEF" remains at 1.x: `retrieve_after_1x: ['DEF']`
- vspanset after shows: `at 0 for 0.2, at 1 for 1`

## Implementation

`/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/edit.c:78-160`

```c
int rearrangend(typecuc *fullcrumptr, typecutseq *cutseqptr, INT index)
{
  // ...
  makeoffsetsfor3or4cuts (&knives, diff);
  // ...
  for (ptr = (typecuc*)findleftson(father); ptr; ptr = (typecuc *)findrightbro((typecorecrum*)ptr)) {
    i = rearrangecutsectionnd((typecorecrum*)ptr, &fgrasp, &knives);
    switch (i) {
      case 1:  case 2:  case 3:
        tumbleradd (&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index]);
        ivemodified((typecorecrum*)ptr);
        break;
      // ...
    }
  }
}
```

The key operation is `tumbleradd` at line 125, which adds a computed offset to the existing V-position. The offset is computed purely from the differences between cut points (lines 164-183), with no consideration of subspace boundaries.

```c
int makeoffsetsfor3or4cuts(typeknives *knives, tumbler diff[])
{
  if (knives->nblades == 3) {
    tumblersub (&knives->blades[2], &knives->blades[1], &diff[1]);
    tumblersub (&knives->blades[1], &knives->blades[0], &diff[2]);
    diff[2].sign = !diff[2].sign;
    // ...
  }
}
```

For cuts at 1.1, 1.4, 2.5:
- `diff[1] = 2.5 - 1.4 = 1.1`
- Content at 1.1-1.4 moves to 2.2-2.5 (1.1 + 1.1 = 2.2)

## Implications

1. **Content discipline violation**: Text bytes (element-type TEXTATOM=1) can end up at 2.x V-positions (subspace 2), violating CD0: `valid-placement(v, a) ≡ subspace(v) = element-type(a)`.

2. **Link orgl placement**: Link orgls (element-type LINKATOM=2) could theoretically be moved to 1.x positions, placing link metadata in text subspace.

3. **Type system bypass**: The CD0 check at INSERT/COPY time is insufficient. REARRANGE provides an alternate path to violate placement constraints.

4. **POOM semantic corruption**: Queries assume content type matches subspace. RETRIEVECONTENTS at 2.x returns text bytes, breaking the expected type invariant.

## Related

- **Finding 0049**: INSERT doesn't validate V-position subspace
- **EWD-035**: Content discipline (CD0) formalization
- **EWD-033**: ENF0 element-type discipline

## Resolution Options

1. **Precondition check**: Reject REARRANGE if any cut point would cause content to cross subspace boundaries (check digit-0 of all cut points)

2. **Post-condition validation**: After computing offsets, verify all resulting V-positions remain in original subspace

3. **Subspace-aware cuts**: Modify `makeoffsetsfor3or4cuts` to detect and reject cross-subspace movements

4. **Accept as feature**: Document that REARRANGE can cross boundaries, update CD0 to only apply to INSERT/COPY/CREATELINK

## Question

Does the specification INTEND for REARRANGE to be able to move content across subspaces? Or is this an implementation bug that violates the intended content discipline?

The existing tests (`rearrange/*.json`) only test intra-subspace rearrangement (all within 1.x), suggesting the cross-subspace behavior was not intentionally exercised.
