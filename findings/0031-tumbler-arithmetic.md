# Finding 0031: Tumbler Arithmetic and Span Operations

**Date discovered:** 2026-02-01
**Category:** Addressing / Core data structures

## Summary

Tumblers are the fundamental addressing mechanism in udanax-green. They are hierarchical decimal numbers with fractional-like semantics, stored as arrays of digits with an exponent. Span widths are tumbler differences, meaning width is in tumbler units (not characters per se).

## Tumbler Data Structure

From `common.h:59-65`:

```c
typedef struct structtumbler {
    humber xvartumbler;        // Pointer to variable-length serialized form
    char varandnotfixed;       // Flag: using variable or fixed representation
    char sign BIT;             // 1 if negative, otherwise 0
    short exp;                 // Exponent (negative for fractional positions)
    tdigit mantissa[NPLACES];  // 16 digits of mantissa
} tumbler;
```

### Tumbler Representation

A tumbler like `1.1.0.2.0.5` is stored as:
- `exp = 0` (no leading zeros)
- `mantissa = [1, 1, 0, 2, 0, 5, 0, 0, ...]`

The zeros in the mantissa act as hierarchical separators:
- `1.1` = Node
- `1.1.0.2` = Account under node
- `1.1.0.2.0.5` = Document/item under account

### Key Insight: Zeros Are Semantic

Zeros separate hierarchy levels. The tumbler `1.1.0.2` is the "account address" and `1.1.0.2.0.5` is "item 5 under that account." This is why `tumblerlength()` counts significant digits:

```c
INT tumblerlength(tumbler *tumblerptr)
{
    return (nstories(tumblerptr) - tumblerptr->exp);
}
```

## Tumbler Comparison

### tumblercmp (tumble.c:72-85)

Returns `LESS`, `EQUAL`, or `GREATER`:

```c
INT tumblercmp(tumbler *aptr, tumbler *bptr)
{
    if (iszerotumbler(aptr)) {
        if (iszerotumbler(bptr)) return EQUAL;
        else return (bptr->sign ? GREATER : LESS);
    }
    if (iszerotumbler(bptr))
        return (aptr->sign ? LESS : GREATER);
    if (aptr->sign == bptr->sign)
        return (aptr->sign ? abscmp(bptr,aptr) : abscmp(aptr,bptr));
    return (aptr->sign ? LESS : GREATER);
}
```

The comparison is lexicographic on the mantissa digits, with exponent checked first:
1. Check if either is zero
2. Handle sign differences
3. Compare exponents
4. Compare mantissa digit-by-digit

### abscmp (tumble.c:87-111)

Absolute value comparison:

```c
static INT abscmp(tumbler *aptr, tumbler *bptr)
{
    if (aptr->exp != bptr->exp) {
        return (aptr->exp < bptr->exp) ? LESS : GREATER;
    }
    for (i = NPLACES; i--;) {
        cmp = *a++ - *b++;
        if (cmp < 0) return LESS;
        if (cmp > 0) return GREATER;
    }
    return EQUAL;
}
```

### tumblereq (tumble.c:24-36)

Equality check:

```c
bool tumblereq(tumbler *a, tumbler *b)
{
    if (a->sign != b->sign) return FALSE;
    if (a->exp != b->exp) return FALSE;
    for (i = 0; i < NPLACES; i++) {
        if (a->mantissa[i] != b->mantissa[i]) return FALSE;
    }
    return TRUE;
}
```

## Tumbler Arithmetic

### tumblerincrement (tumble.c:599-623)

Adds a value at a specific digit position:

```c
int tumblerincrement(tumbler *aptr, INT rightshift, INT bint, tumbler *cptr)
{
    if (iszerotumbler(aptr)) {
        tumblerclear(cptr);
        cptr->exp = -rightshift;
        cptr->mantissa[0] = bint;
        return(0);
    }
    // Find last non-zero digit
    for (idx = NPLACES; aptr->mantissa[--idx] == 0 && idx > 0;);
    // Add bint at position (idx + rightshift)
    cptr->mantissa[idx + rightshift] += bint;
    tumblerjustify(cptr);
}
```

This is how spans are extended and new positions allocated.

### tumbleradd (tumble.c:365-404)

Full tumbler addition with sign handling:

```c
int functiontumbleradd(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
    if (iszerotumbler(bptr)) { movetumbler(aptr, cptr); return; }
    if (iszerotumbler(aptr)) { movetumbler(bptr, cptr); return; }

    if (aptr->sign == bptr->sign) {
        absadd(aptr, bptr, cptr);
        cptr->sign = aptr->sign;
    } else if (abscmp(aptr, bptr) == GREATER) {
        strongsub(aptr, bptr, cptr);
        cptr->sign = aptr->sign;
    } else {
        weaksub(bptr, aptr, cptr);
        cptr->sign = bptr->sign;
    }
}
```

### tumblersub (tumble.c:406-440)

Subtraction via negated addition:

```c
int tumblersub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
    if (iszerotumbler(bptr)) movetumbler(aptr, cptr);
    else if (tumblereq(aptr, bptr)) tumblerclear(cptr);
    else {
        movetumbler(bptr, &temp);
        temp.sign = !temp.sign;
        tumbleradd(aptr, &temp, cptr);
    }
    tumblerjustify(cptr);
}
```

### tumblertruncate (tumble.c:625-639)

Truncates a tumbler to a given length (used for hierarchy operations):

```c
int tumblertruncate(tumbler *aptr, INT bint, tumbler *cptr)
{
    movetumbler(aptr, &answer);
    for (i = answer.exp; i < 0 && bint > 0; ++i, --bint);
    if (bint <= 0) tumblerclear(&answer);
    else for (; bint < NPLACES; ++bint)
        answer.mantissa[bint] = 0;
    tumblerjustify(&answer);
    movetumbler(&answer, cptr);
}
```

## Span Structure and Width Semantics

From `xanadu.h:65-76`:

```c
typedef struct structtypespan {
    struct structtypespan *next;
    typeitemid itemid;
    tumbler stream;   // Start position (I-address or V-address)
    tumbler width;    // Width as a tumbler
} typespan;

typedef typespan typeispan;   // I-space span
typedef typespan typevspan;   // V-space span
```

### Width Interpretation

**Width is a tumbler, not an integer.** This is critical:

From `granf2.c:100` in `inserttextgr`:
```c
tumblerincrement(&lsa, 0, textset->length, &lsa);
```

When inserting text of length N:
- The I-address advances by N at the deepest digit level
- Width = end - start (tumbler subtraction)

From `granf2.c:106`:
```c
tumblersub(&lsa, &spanorigin, &ispanptr->width);
```

The width is computed as: `width = endAddress - startAddress`

### For Text Content

**One I-address per character.** Evidence from `inserttextgr`:
1. Text is inserted at an I-address
2. The I-address increments by `textset->length`
3. Width equals the number of characters

Example:
- Insert "Hello" (5 chars) at I-address `2.1.0.5.0.100`
- After insert: I-address is `2.1.0.5.0.105`
- Width tumbler is the difference: represents 5 positions

### Width as Tumbler Difference

From `insertpm` in `orglinks.c:116-117`:
```c
inc = tumblerintdiff(&lwidth, &zero);
tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V]);
```

`tumblerintdiff` extracts the integer value from a tumbler difference. This is only meaningful when the width is "flat" (no hierarchical structure).

## Interval Comparison

From `tumble.c:144-160`:

```c
INT intervalcmp(tumbler *left, tumbler *right, tumbler *address)
{
    cmp = tumblercmp(address, left);
    if (cmp == LESS) return TOMYLEFT;
    if (cmp == EQUAL) return ONMYLEFTBORDER;

    cmp = tumblercmp(address, right);
    if (cmp == LESS) return THRUME;
    if (cmp == EQUAL) return ONMYRIGHTBORDER;
    return TOMYRIGHT;
}
```

Returns spatial relationship of an address to an interval:
- `TOMYLEFT` (-2): address < left
- `ONMYLEFTBORDER` (-1): address == left
- `THRUME` (0): left < address < right
- `ONMYRIGHTBORDER` (1): address == right
- `TOMYRIGHT` (2): address > right

## Iterating Over a Span

There is no explicit "iterate" function. Instead:

1. **Enfilade traversal** - The enfilade data structure stores content in ranges. Retrieval walks the tree, collecting content for the requested span.

2. **Context lists** - `retrieverestricted()` returns a `context` list with matching ranges. Each context entry contains offset and width.

3. **Span arithmetic** - To process a span:
   - Use `tumblercmp` to check boundaries
   - Use `tumbleradd`/`tumblersub` to compute offsets
   - Use `tumblerincrement` to advance positions

## Permascroll and I-Addresses

From `granf2.c:83-108` (`inserttextgr`):

1. Find an available I-address via `findisatoinsertgr`
2. For each text chunk:
   - Store text at current I-address
   - Increment I-address by text length
3. Return the I-span (start + width)

**Key behavior**: Text characters are stored contiguously in I-space. Each character occupies one I-address position. The "permascroll" is the append-only global I-address space.

## Implications for Spec

1. **ISpan(start, width)** - Both start and width are tumblers. Width is computed as `end - start`.

2. **No iteration primitive** - Spans are processed through enfilade retrieval, not character-by-character iteration.

3. **Width in characters** - For text content, width equals character count. The tumbler representation allows for hierarchical addressing, but text uses flat numeric sequences.

4. **Address comparison** - Use `tumblercmp` returning LESS/EQUAL/GREATER. No separate "less than" function.

5. **Computing end address** - `end = tumbleradd(start, width)`. Then iterate by enfilade retrieval, not address enumeration.

## Related Source Files

- `tumble.c` - Core tumbler arithmetic
- `tumbleari.c` - Variable-length serialization
- `xanadu.h` - Span type definitions
- `orglinks.c` - insertpm showing span construction
- `granf2.c` - inserttextgr showing I-address allocation

## Related Findings

- Finding 0009: Document address space structure
- Finding 0021: Address allocation mechanism
- Finding 0003: Multi-span operations
