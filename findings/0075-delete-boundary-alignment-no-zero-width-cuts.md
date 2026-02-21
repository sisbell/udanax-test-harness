# Finding 0075: DELETE Boundary Alignment — No Zero-Width Cuts

**Date:** 2026-02-14
**Component:** DELETE Phase 1 (ndcuts.c)
**Severity:** Clarification
**Status:** Documented

---

## Summary

When DELETE boundaries align exactly with existing bottom crum boundaries, `slicecbcpm` is **not called** for those boundaries. The function can only be invoked for cuts that fall strictly in the **interior** of a crum, meaning `localcut.mantissa[0]` is always strictly positive and strictly less than `cwid.mantissa[0]`. **Zero-width pieces cannot be produced** by `slicecbcpm`.

---

## Question Investigated

In the DELETE pipeline:
1. When DELETE is called with boundaries that exactly coincide with existing bottom crum boundaries (e.g., deletion start equals a crum's grasp, or deletion end equals a crum's reach), does `slicecbcpm` still get called?
2. Can `slicecbcpm` ever produce a zero-width piece (i.e., can `localcut.mantissa[0]` be 0 or equal to `cwid.mantissa[0]`)?

---

## Implementation Analysis

### DELETE Entry Point

`deletend()` in `edit.c:31`:
```c
int deletend(typecuc *fullcrumptr, tumbler *origin, tumbler *width, INT index)
{
  typeknives knives;

  movetumbler (origin, &knives.blades[0]);           // Start boundary
  tumbleradd (origin, width, &knives.blades[1]);     // End boundary
  knives.nblades = 2;
  knives.dimension = index;
  makecutsnd (fullcrumptr, &knives);                 // Phase 1: Cut
  // ... Phase 2: Classify and remove
}
```

### Phase 1: Cut Decision Logic

`makecutsbackuptohere()` in `ndcuts.c:77-90`:
```c
if (ptr->height == 0) {
    for (i = 0; i < knives->nblades; i++) {
        if (whereoncrum((typecorecrum*)ptr, offset, &knives->blades[i],
                        knives->dimension) == THRUME) {
            new = (typecuc *)createcrum((INT)ptr->height,(INT)ptr->cenftype);
            slicecbcpm((typecorecrum*)ptr, offset, (typecorecrum*)new,
                      &knives->blades[i], knives->dimension);
        }
    }
}
```

**Key:** `slicecbcpm` is called **only when** `whereoncrum() == THRUME`.

### whereoncrum Return Values

From `retrie.c:345-372` and `common.h:86-90`:
```c
#define TOMYLEFT -2          // Cut is before crum
#define ONMYLEFTBORDER -1    // Cut equals crum's grasp (left edge)
#define THRUME 0             // Cut is INTERIOR to crum
#define ONMYRIGHTBORDER 1    // Cut equals crum's reach (right edge)
#define TOMYRIGHT 2          // Cut is after crum
```

Logic in `whereoncrum` for POOM/SPAN:
```c
tumbleradd(&offset->dsas[index], &ptr->cdsp.dsas[index], &left);  // grasp
cmp = tumblercmp(address, &left);
if (cmp == LESS)   return TOMYLEFT;
if (cmp == EQUAL)  return ONMYLEFTBORDER;  // ← Boundary aligned!

tumbleradd(&left, &ptr->cwid.dsas[index], &right);  // reach
cmp = tumblercmp(address, &right);
if (cmp == LESS)   return THRUME;           // ← Interior only
if (cmp == EQUAL)  return ONMYRIGHTBORDER;  // ← Boundary aligned!
return TOMYRIGHT;
```

### Consequence for slicecbcpm

From `slicecbcpm` in `ndcuts.c:396`:
```c
tumblersub(cut, &grasp.dsas[index], &localcut);  // localcut = cut - grasp
```

Since `slicecbcpm` is **only called when `whereoncrum() == THRUME`**, we know:
- `cut > grasp` (not equal)
- `cut < reach` (not equal)
- Therefore: `0 < localcut.mantissa[0] < cwid.mantissa[0]`

The function **cannot** be called with a cut at the exact left boundary (`grasp`) or exact right boundary (`reach`).

---

## Test Verification

See `febe/tests/test_delete_boundary_alignment.py`.

### Test 1: Exact Single-Crum Deletion
```python
session.insert(opened, Address(1, 1), ["ABC"])    # Creates crum [1.1, 1.4)
session.delete(opened, Address(1, 1), Offset(0, 3))  # Delete [1.1, 1.4)
```

**Result:** Document is empty. The entire crum is classified for deletion without cutting.

**Analysis:**
- `whereoncrum(1.1, crum)` returns `ONMYLEFTBORDER` (not `THRUME`)
- `whereoncrum(1.4, crum)` returns `ONMYRIGHTBORDER` (not `THRUME`)
- `slicecbcpm` is **not called**
- The crum is classified as type 1 (delete entirely) in Phase 2

### Test 2: Start Boundary Aligned
```python
session.insert(opened, Address(1, 1), ["ABCDEF"])  # Creates crum [1.1, 1.7)
session.delete(opened, Address(1, 1), Offset(0, 3))  # Delete [1.1, 1.4)
```

**Result:** "DEF" remains at 1.1 (shifted).

**Analysis:**
- `whereoncrum(1.1, crum)` returns `ONMYLEFTBORDER` → no cut at 1.1
- `whereoncrum(1.4, crum)` returns `THRUME` → **cut is made at 1.4**
- `slicecbcpm` is called **only for the 1.4 cut**
- `localcut = 1.4 - 1.1 = 0.3` (strictly positive)

### Test 3: End Boundary Aligned
```python
session.insert(opened, Address(1, 1), ["ABCDEF"])  # Creates crum [1.1, 1.7)
session.delete(opened, Address(1, 4), Offset(0, 3))  # Delete [1.4, 1.7)
```

**Result:** "ABC" remains at 1.1.

**Analysis:**
- `whereoncrum(1.4, crum)` returns `THRUME` → **cut is made at 1.4**
- `whereoncrum(1.7, crum)` returns `ONMYRIGHTBORDER` → no cut at 1.7
- `slicecbcpm` is called **only for the 1.4 cut**
- `localcut = 1.4 - 1.1 = 0.3` (strictly less than `cwid = 0.6`)

### Test 4: Cross-Crum Deletion
```python
session.insert(opened, Address(1, 1), ["ABC"])  # Crum 1: [1.1, 1.4)
session.insert(opened, Address(1, 4), ["DEF"])  # Crum 2: [1.4, 1.7)
session.delete(opened, Address(1, 2), Offset(0, 4))  # Delete [1.2, 1.6)
```

**Result:** "AF" remains.

**Analysis:**
- Two separate bottom crums at different I-addresses
- `whereoncrum(1.2, crum1)` returns `THRUME` → cut at 1.2 in first crum
- `whereoncrum(1.6, crum2)` returns `THRUME` → cut at 1.6 in second crum
- Both cuts are **interior**, so both invoke `slicecbcpm`
- `localcut1 = 1.2 - 1.1 = 0.1` (positive)
- `localcut2 = 1.6 - 1.4 = 0.2` (positive, less than 0.3)

---

## Answer to Original Question

### Q1: Does `slicecbcpm` get called for boundary-aligned cuts?

**No.** The code explicitly checks `whereoncrum() == THRUME` before calling `slicecbcpm`. When a deletion boundary aligns exactly with a crum boundary:
- Start aligns with grasp → `whereoncrum() == ONMYLEFTBORDER` → no call
- End aligns with reach → `whereoncrum() == ONMYRIGHTBORDER` → no call

### Q2: Can `slicecbcpm` produce a zero-width piece?

**No.** Since `slicecbcpm` is only called when the cut is strictly interior (`THRUME`), we have:
- `cut > grasp` (strict inequality)
- `cut < reach` (strict inequality)
- Therefore: `0 < localcut.mantissa[0] < cwid.mantissa[0]` (both strict)

The function cannot create a zero-width piece. The assertions at `ndcuts.c:410` and `ndcuts.c:398` would fail if this invariant were violated.

---

## Implications

1. **No Degenerate Crums from DELETE:** The cutting mechanism cannot produce zero-width crums, because cuts are only made for interior points.

2. **Boundary-Aligned Deletions Are Efficient:** When deletion boundaries align exactly with existing crum boundaries, no cutting occurs. The crum is simply classified and removed/shifted in Phase 2.

3. **Invariant for Formal Models:** In any formal specification of DELETE (e.g., DN-0011), we can assume:
   - `localcut > 0` (strictly)
   - `localcut < cwid` (strictly)
   - No zero-width pieces exist after Phase 1

4. **Safety of locksubtract:** The `locksubtract` call at `ndcuts.c:444` is guaranteed to receive:
   - `ptr->cwid` = original width
   - `newwid.dsas[i].mantissa[0] = localcut.mantissa[0]` (strictly between 0 and cwid)
   - Result: `new->cwid` is always positive and less than original

---

## Code References

- `[edit.c:31-76]` — `deletend()` entry point, constructs knives
- `[ndcuts.c:77-90]` — `makecutsbackuptohere()` bottom-crum cutting logic
- `[ndcuts.c:373-450]` — `slicecbcpm()` implementation
- `[retrie.c:345-398]` — `whereoncrum()` classification logic
- `[common.h:86-90]` — Return value constants

---

## Related Findings

- **Finding 0053:** DELETE shifts V-positions by negative offset
- **Finding 0055:** DELETE does not shift link subspace
- **Finding 0058:** DELETE everything leaves valid empty tree state
- **DN-0011:** Leaf linearity enforcement (relies on no zero-width pieces)

---

## Test Files

- `febe/tests/test_delete_boundary_alignment.py` — Comprehensive boundary alignment tests
