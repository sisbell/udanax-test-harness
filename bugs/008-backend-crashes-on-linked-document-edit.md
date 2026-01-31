# Bug 008: Backend crashes when editing documents with links

**Date discovered:** 2026-01-30
**Status:** Fixed (client was using wrong FEBE command)
**Severity:** High

## Summary

The backend crashes (abort trap/segfault) or returns errors when any modification is made to a document that has links attached to it (either as source or target).

## Reproduction

Any of these operations on a document with links causes failure:

1. **Insert before linked span**: Segmentation fault
2. **Delete adjacent text**: Abort trap (crash)
3. **Delete linked source span**: Abort trap (crash)
4. **Delete linked target span**: Abort trap (crash)
5. **Partial delete of linked span**: Abort trap (crash)
6. **vcopy of linked content**: Backend returns error
7. **Insert in target document**: Backend returns error

## Test Cases

```
links/link_survives_source_insert          - Segmentation fault: 11
links/link_survives_source_delete_adjacent - Abort trap: 6 (crash)
links/link_when_source_span_deleted        - Abort trap: 6 (crash)
links/link_when_target_span_deleted        - Abort trap: 6 (crash)
links/link_source_partial_delete           - Abort trap: 6 (crash)
links/link_with_vcopy_source               - ERROR: error response from back-end
links/link_survives_target_modify          - ERROR: error response from back-end
```

## Impact

Links are effectively immutable after creation - you cannot edit any document that participates in a link relationship. This severely limits the utility of the linking system.

## Technical Analysis

### Where the crash occurs

From backenderror log during crash:
```
in levelpush
leaving levelpush
splitcrumupwards split something
```

The crash happens during tree rebalancing operations (`splitcrumupwards`, `levelpush`, `recombine`) in the POOM enfilade structure. This occurs when:
1. A document has links (stored in the same POOM enfilade as text content)
2. Content is inserted/deleted, requiring tree restructuring
3. The split/recombine code fails when handling the mixed content

### Related to Bug 006

Bug 006 (crashes on 6th link) is likely the same root cause - the POOM enfilade tree structure becomes corrupted or inconsistent when too many links are present or when modifications occur.

### Root Cause Hypothesis

Links and text content share the same POOM (permutation matrix) enfilade:
- Text content at addresses 1.1.x
- Links at addresses 1.2.x

The tree split/rebalance code in `split.c`, `insertnd.c`, and `ndcuts.c` may not correctly handle:
1. Cuts that interact with crums in different "stories" (1.1.x vs 1.2.x)
2. Width/displacement calculations when both text and link crums exist
3. The `splitcrumpm()` function's selection of which crum to peel off

### Key Files

- `backend/split.c:16` - `splitcrumupwards()` - crash occurs during this
- `backend/split.c:117` - `splitcrumpm()` - POOM-specific split logic
- `backend/insertnd.c:124` - `makegappm()` - makes gaps for insertions
- `backend/ndcuts.c` - cut operations that prepare for insert/delete
- `backend/orglinks.c` - link storage in POOM enfilades

## Possible Fixes

1. **Fix tree rebalancing for mixed content**: Ensure split/recombine correctly handles crums in different stories (text vs link address spaces)

2. **Separate link storage**: Store links in a separate enfilade rather than mixing with text content

3. **Add validation**: Add assertions to detect tree inconsistencies before they cause crashes

## Related

- Bug 006: Backend crashes on 6th link (same root cause)
- Bug 007: Backend crashes on delete-all (similar crash pattern, now fixed)
- Finding 004: Link endpoint semantics
