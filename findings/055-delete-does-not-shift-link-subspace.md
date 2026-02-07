# Finding 055: DELETE Does Not Shift Link Subspace -- strongsub Exponent Guard

**Date:** 2026-02-07
**Category:** POOM operations / Subspace isolation
**Agent:** Gregory
**Corrects:** Finding 053
**Related:** Finding 054, Finding 038

## Summary

DELETE at V-position 1.x does NOT shift link entries at V-position 2.x. While `deletend` classifies the link crum as case 2 (shift), the actual `tumblersub` operation is a no-op because `strongsub` returns the minuend unchanged when the subtrahend has a smaller exponent. This exponent mismatch between the deletion width (exp=-1, e.g., `0.3`) and the link's V-position displacement (exp=0, e.g., `2.1`) acts as an implicit subspace guard.

**Finding 053 is wrong.** Links do not shift to negative V-positions after text deletion. Empty endsets observed after deletion are caused by the I-addresses being freed from the POOM (case 1 in `deletend`), not by V-position corruption.

## The Mechanism: Two Different Protections

### INSERT: Explicit Two-Blade Subspace Guard (Finding 054)

INSERT uses `findaddressofsecondcutforinsert` to compute a second blade at the next subspace boundary (e.g., `2.1` for an insert at `1.x`). This causes `insertcutsectionnd` to classify link crums as case 2 (no shift), so `tumbleradd` is never even called for them.

### DELETE: Implicit Exponent Guard in strongsub

DELETE constructs its two blades as `[origin, origin + width]`, e.g., `[1.1, 1.4]` for a deletion of 3 bytes at 1.1. There is **no second-cut subspace boundary computation** analogous to INSERT's `findaddressofsecondcutforinsert`.

Instead, `deletecutsectionnd` classifies the link crum at 2.1 as case 2 (shift), and `tumblersub(2.1, 0.3)` is called. But the subtraction is a no-op because of the exponent mismatch in `strongsub`.

## Code Trace

### deletend Knife Construction (edit.c:40-43)

```c
movetumbler (origin, &knives.blades[0]);          // blade[0] = 1.1
tumbleradd (origin, width, &knives.blades[1]);    // blade[1] = 1.1 + 0.3 = 1.4
knives.nblades = 2;
```

No call to `findaddressofsecondcutforinsert` or equivalent.

### deletecutsectionnd Classification (edit.c:235-248)

```c
for (i = knives->nblades-1; i >= 0; --i) {
    cmp = whereoncrum(ptr, offset, &knives->blades[i], knives->dimension);
    if (cmp == THRUME) return (-1);
    else if (cmp <= ONMYLEFTBORDER) return (i+1);
}
return (0);
```

For a link crum at V-position 2.1 with blades [1.1, 1.4]:
1. i=1: blade 1.4 is TOMYLEFT of crum at 2.1. `TOMYLEFT <= ONMYLEFTBORDER` is TRUE. Return 2.

**Case 2 is reached.** This means `tumblersub` WILL be called on the link crum.

### The tumblersub Call (edit.c:63)

```c
case 2:
    tumblersub(&ptr->cdsp.dsas[V], width, &ptr->cdsp.dsas[V]);
    break;
```

This calls `tumblersub(2.1, 0.3)`.

### tumblersub -> tumbleradd -> strongsub (tumble.c:406-430, 534-565)

`tumblersub(a=2.1, b=0.3)`:
1. Neither zero, not equal. Goes to `else` branch.
2. `temp = 0.3; temp.sign = 1` (negate to -0.3)
3. `tumbleradd(2.1, -0.3)`

`tumbleradd(a=2.1, b=-0.3)`:
1. Different signs (a.sign=0, b.sign=1)
2. `abscmp(a, b)`: a.exp=0 > b.exp=-1, so GREATER
3. `strongsub(a, b, c)` with `c.sign = a.sign = 0`

### The Exponent Guard in strongsub (tumble.c:534-547)

```c
int strongsub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
    tumblerclear(&answer);
    if (tumblereq(aptr, bptr)) { ... }
    if (bptr->exp < aptr->exp) {       // <-- THIS LINE
        movetumbler(aptr, cptr);       // Returns a UNCHANGED
        return(0);
    }
    // ... main subtraction logic never reached
}
```

For `strongsub(a={exp=0, mant=[2,1,...]}, b={exp=-1, mant=[3,...]})`:
- `bptr->exp(-1) < aptr->exp(0)` is TRUE
- Returns `a` unchanged: `2.1`

**The link crum's V-position displacement is NOT modified.**

### Why Text Crums DO Shift

Text crums' V-position displacements (`cdsp.dsas[V]`) are stored as offsets within their hierarchy level, with exponents matching the deletion width. For example, a text crum at V-position 1.4 has `cdsp.dsas[V]` with exp=-1 (same level as the width `0.3`). So `strongsub(0.4, 0.3)` proceeds to the main subtraction path (same exponent), producing `0.1`. The text crum shifts.

Link crums have `cdsp.dsas[V]` with exp=0 (e.g., `2.1`), which is a HIGHER hierarchy level than the width (exp=-1). The exponent check in `strongsub` prevents the subtraction.

## Test Evidence

**Golden test:** `golden/subspace/delete_text_does_not_shift_link_subspace.json`

Setup:
- Document with "ABCDEFGHIJ" (10 bytes) at V-positions 1.1-1.10
- Link at V-position 2.1

Action 1: DELETE 3 bytes at 1.1 (width 0.3)

Results:
- Text shifted: 1.1=D, 1.2=E, ..., 1.7=J (shifted left by 3)
- Link at 2.1: **STILL PRESENT** (I-address `1.1.0.1.0.1.0.2.1`)
- FOLLOWLINK: **STILL WORKS** (target resolves to `1.2 for 0.2` in doc2)

Action 2: DELETE all remaining 7 bytes at 1.1

Results:
- vspanset: `at 2.1 for 0.1` (ONLY the link remains)
- Link at 2.1: **STILL PRESENT**
- FOLLOWLINK: **STILL WORKS** (target in doc2 unaffected)

## Corrections to Finding 053

Finding 053 made three incorrect claims:

1. **WRONG: "ALL entries in the POOM that are positioned after the deletion point have their V-positions shifted leftward."** Only entries at the same tumbler exponent level are shifted. Link entries at a higher hierarchy level (exp=0 vs exp=-1) are unaffected because `strongsub` returns the value unchanged.

2. **WRONG: "`tumblersub` can produce negative tumblers when the deletion width exceeds the entry's current position."** This cannot happen for cross-subspace entries because `strongsub` exits early when the exponents differ. The link at 2.1 minus width 0.15 equals 2.1 (unchanged), not a negative value.

3. **WRONG: "Entries with negative V-positions remain in the POOM tree but become invisible to queries."** The link remains at V-position 2.1 with a positive, valid tumbler. The empty endsets observed in the golden tests are caused by the ENDSET I-ADDRESSES being deleted from the POOM (case 1: `disown` + `subtreefree`), not by the link's own V-position going negative.

### What Actually Causes Empty Endsets

When FOLLOWLINK returns empty spans after deletion:

1. The link's POOM entry is STILL at V-position 2.1 (verified by `retrieve_contents` at 2.1)
2. The link's endset I-addresses are immutable (stored in link orgl, in I-space)
3. FOLLOWLINK resolves those I-addresses through the HOME DOCUMENT's current POOM
4. If the I-addresses were in the deletion range, they were freed from the POOM (case 1)
5. Resolution fails because the I-addresses no longer have V-position mappings
6. Result: empty endset spans

This is I-address removal from the POOM, not V-position corruption.

## Why DELETE and INSERT Have Different Guard Mechanisms

INSERT needs an explicit second blade because the shift operation (`tumbleradd`) CAN cross hierarchy levels. Adding `0.2` to `2.1` would produce `2.3` -- the exponents align during addition. So without the second blade, INSERT WOULD shift link crums.

DELETE does not need an explicit second blade because the shift operation (`tumblersub`) has an implicit guard in `strongsub`: subtraction with mismatched exponents returns the minuend unchanged. This is an accidental property of the implementation, not a deliberate design choice (there is no comment explaining it as a subspace guard).

## Implications

1. **Both INSERT and DELETE preserve subspace isolation**, but through different mechanisms.
2. **INSERT's protection is deliberate** (explicit second blade with explanatory comment in the source).
3. **DELETE's protection is accidental** (side effect of `strongsub`'s exponent check).
4. **The asymmetry is a fragility risk**: if `strongsub` were "fixed" to handle cross-exponent subtraction, DELETE would break subspace isolation.

## References

- `edit.c:31-76` -- deletend (knife construction and case dispatch)
- `edit.c:235-248` -- deletecutsectionnd (crum classification)
- `tumble.c:406-430` -- tumblersub (subtraction via negated addition)
- `tumble.c:534-547` -- strongsub (exponent guard at line 544)
- `insertnd.c:174-183` -- findaddressofsecondcutforinsert (INSERT's explicit guard, for comparison)
- `golden/subspace/delete_text_does_not_shift_link_subspace.json` -- empirical evidence
- `golden/links/delete_text_before_link.json` -- original test (misinterpreted by Finding 053)
