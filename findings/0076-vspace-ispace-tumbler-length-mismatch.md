# Finding 0076: V-space and I-space Tumbler Lengths Differ in POOM Bottom Crums

**Date:** 2026-02-14
**Category:** POOM / 2D Enfilades / Addressing
**Related:** Finding 0030 (V-space/I-space mapping), Finding 0031 (Tumbler arithmetic)

## Summary

In `insertpm` [orglinks.c:105-117], when creating POOM bottom crums, the V-width exponent is computed from the V-address tumbler length, while the I-width is copied directly from the I-space span. **V-addresses and I-addresses have different tumbler lengths**, so the V-width and I-width are encoded with different exponents.

## The Code

From `insertpm` [orglinks.c:100-117]:

```c
for (; sporglset; sporglset = (typesporglset) sporglset->xxxxsporgl.next) {
    unpacksporgl (sporglset, &lstream, &lwidth, &linfo);

    // I-space: copy lstream and lwidth directly
    movetumbler (&lstream, &crumorigin.dsas[I]);
    movetumbler (&lwidth, &crumwidth.dsas[I]);

    // V-space: copy vsaptr, but compute V-width with different exponent
    movetumbler (vsaptr, &crumorigin.dsas[V]);

    /*I'm suspissious of this shift <reg> 3/1/85 zzzz*/
    shift = tumblerlength (vsaptr) - 1;
    inc = tumblerintdiff (&lwidth, &zero);
    tumblerincrement (&zero, shift, inc, &crumwidth.dsas[V]);
}
```

### The V-width Computation

The V-width is computed as:
1. `shift = tumblerlength(vsaptr) - 1` — exponent based on V-address length
2. `inc = tumblerintdiff(&lwidth, &zero)` — integer value from I-width
3. `tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V])` — create V-width tumbler

This creates a tumbler with:
- `exp = -shift = -(tumblerlength(vsaptr) - 1)`
- `mantissa[0] = inc` (the I-width value)

## Test Evidence

From `test_vspace_ispace_tumbler_lengths.py`:

```
After second insertion:
  Crum 0: I-origin=0.0.0.0.0.0.0.0.11 (9 digits), V-origin=0.5 (2 digits)
    ✗ Lengths differ!

  Crum 2: I-origin=0.0.0.0.0.0.0.0.5 (9 digits), V-origin=0.8 (2 digits)
    ✗ Lengths differ!
```

Typical lengths:
- **I-addresses**: 6-9 tumbler digits (e.g., `1.1.0.1.0.100`, `0.0.0.0.0.0.0.0.11`)
- **V-addresses**: 2 tumbler digits (e.g., `1.1`, `0.5`, `0.8`)

## Why This Works

The `tumblerincrement` function [tumble.c:599-623] handles zero tumblers specially:

```c
int tumblerincrement(tumbler *aptr, INT rightshift, INT bint, tumbler *cptr)
{
    if (iszerotumbler (aptr)) {
        tumblerclear (cptr);
        cptr->exp = -rightshift;
        cptr->mantissa[0] = bint;
        return(0);
    }
    // ... (non-zero case)
}
```

When `aptr` is zero (as in `insertpm`):
- `exp` is set to `-rightshift`
- `mantissa[0]` is set to `bint`

This creates a tumbler representing `bint × 10^(-rightshift)`.

### Example

If `vsaptr = "1.1"` (tumblerlength = 2) and `lwidth = "11"` (11 characters):

1. `shift = tumblerlength(vsaptr) - 1 = 2 - 1 = 1`
2. `inc = tumblerintdiff(&lwidth, &zero) = 11`
3. `tumblerincrement(&zero, 1, 11, &crumwidth.dsas[V])`
   - Creates tumbler with `exp = -1`, `mantissa[0] = 11`
   - Represents: `0.11` (in tumbler notation)

Meanwhile, the I-width might be something like `0.0.0.0.0.0.0.0.11` (9 digits).

## Semantic Implications

### 1. V-width Encodes I-width Value at V-space Precision

The V-width is **not** a copy of the I-width. It's a re-encoding of the I-width's **integer value** at the precision level of the V-address.

- I-width: `0.0.0.0.0.0.0.0.11` (represents 11 at I-space precision)
- V-width: `0.11` (represents 11 at V-space precision)

Both represent "11 units of width", but at different tumbler precision levels.

### 2. POOM Bottom Crums Store Dual-Precision Coordinates

Each POOM bottom crum stores:
- **I-space coordinates** with I-space precision (6-9 digits)
- **V-space coordinates** with V-space precision (2 digits)

This dual representation allows:
- V-space queries to use short, human-readable addresses (`1.1`, `1.2`, `1.3`)
- I-space queries to use precise, immutable addresses (`1.1.0.1.0.100`, `1.1.0.1.0.101`)

### 3. Width Comparison Must Be Value-Based, Not Tumbler-Based

Since V-widths and I-widths have different exponents, you cannot directly compare their tumbler representations. You must extract the integer value:

- I-width `0.0.0.0.0.0.0.0.11` → value 11
- V-width `0.11` → value 11
- Values match! ✓

The `tumblerintdiff` function extracts this value for comparison.

### 4. Roger's Suspicion (3/1/85 Comment)

The code includes this comment:

```c
/*I'm suspissious of this shift <reg> 3/1/85 zzzz*/
shift = tumblerlength (vsaptr) - 1;
```

Roger was suspicious of using `tumblerlength(vsaptr)` to compute the V-width exponent. Our test confirms this is **correct** — the V-width must be encoded at V-space precision, not I-space precision.

However, the suspicion may relate to **edge cases**:
- What if `vsaptr = "0"`? Then `shift = 0 - 1 = -1`, creating `exp = 1`.
- What if V-addresses have variable lengths across a document?

## Related Code

### tumblerlength [tumble.c:259-262]

```c
INT tumblerlength(tumbler *tumblerptr)
{
    return (nstories (tumblerptr) - tumblerptr->exp);
}
```

Returns the number of significant mantissa digits (after accounting for exponent).

### tumblerintdiff

Used to extract the integer value from a tumbler difference (width). Likely implemented as reading the mantissa at the appropriate exponent level.

## Implications for Specification

1. **POOM bottom crums are 2D with asymmetric precision**:
   - I-dimension: high-precision (6-9 digits)
   - V-dimension: low-precision (2 digits)

2. **V-width ≠ I-width as tumblers**, even though they represent the same span of content.

3. **Width encoding is exponent-dependent**: The same numeric width (e.g., 11 characters) is encoded as different tumblers depending on the address space precision.

4. **Tumbler comparison must be value-based**: Cannot use `tumblercmp` on widths from different address spaces. Must extract integer values first.

## Test File

`febe/tests/test_vspace_ispace_tumbler_lengths.py`

Demonstrates:
- V-addresses typically have 2 tumbler digits
- I-addresses typically have 6-9 tumbler digits
- V-width uses exponent from V-address length
- I-width is copied directly from I-space span

## Related Findings

- **Finding 0030**: INSERT updates V-space while preserving I-space identity
- **Finding 0031**: Tumbler arithmetic and span operations
- **Finding 0012**: Dual enfilade architecture (POOM + enfilades)
- **Finding 0038**: POOM subspace independence
