# Bug 0010: No V-Position Validation (acceptablevsa always returns TRUE)

**Date:** 2026-01-30
**Severity:** Medium (allows invalid document states)
**Status:** Identified

## Summary

The function `acceptablevsa()` in do2.c:110-113 is supposed to validate V-positions for copy/insert operations, but it **always returns TRUE** without any actual validation.

## Code

```c
// do2.c:110-113
bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr)
{
    return (TRUE);  // No validation performed!
}
```

## Impact

This allows operations that violate the document address space conventions:

| Invalid Operation | What Happens | Consequence |
|-------------------|--------------|-------------|
| Insert text at V-position 0.x | Text stored in link subspace | Appears as link reference, corrupts link semantics |
| Insert link ref at V-position 1.x | Link ISA stored in text subspace | Appears as "content", gibberish when retrieved |
| Insert at negative V-position | Unknown behavior | Potential crash or corruption |
| Insert beyond document extent | May create gaps | Sparse document, undefined retrieval |

## Callers

`acceptablevsa` is called by:

1. **`docopy`** (do1.c:56) - Transclusion/copy operations
2. **`docopyinternal`** (do1.c:77) - Internal copy operations

These are fundamental operations used throughout the system.

## Expected Behavior

The function should validate:

1. **Subspace appropriateness**:
   - Text content → V-position ≥ 1.0
   - Link references → V-position in 0.x range

2. **Position bounds**:
   - Not negative
   - Not creating excessive gaps

3. **Content type matching**:
   - Source I-address type matches destination subspace

## Proposed Fix

```c
bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr, INT content_type)
{
    // Reject negative positions
    if (tumblercmp(vsaptr, &zero) < 0)
        return FALSE;

    // Validate subspace
    INT first_digit = vsaptr->digits[0];

    if (content_type == LINK_CONTENT && first_digit >= 1)
        return FALSE;  // Links must be at 0.x

    if (content_type == TEXT_CONTENT && first_digit < 1)
        return FALSE;  // Text must be at 1.x or higher

    return TRUE;
}
```

Note: This would require updating all callers to specify content type.

## Why This Exists

The original designers likely:
1. Trusted all code to follow conventions
2. Optimized for performance over safety
3. Considered validation overhead unnecessary

This is typical of 1970s-80s systems design where trusted code was assumed.

## Related

- **Finding 0009**: Document address space structure (defines the subspace conventions)
- **Finding 0010**: Unified storage abstraction leaks (this is one of the leaks)
- **Finding 0011**: Convention over enforcement design philosophy (explains why this exists)
- **Bug 0009**: Crash caused by link subspace content in compare_versions

## Test Case

Not yet created. Would need to:
1. Attempt to insert text at V-position 0.5
2. Attempt to insert a link reference at V-position 1.5
3. Verify the document state becomes invalid

## Notes

This may be intentional "trust the caller" design rather than a bug. However, it means:
- All FEBE protocol implementations must enforce conventions
- A malicious or buggy client could corrupt documents
- Debugging document corruption is difficult
