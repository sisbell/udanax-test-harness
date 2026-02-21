# Finding 0037: Link Endsets Automatically Split Discontiguous I-Addresses

**Date:** 2026-02-06
**Category:** Link semantics / Content addressing
**Status:** Documented from code analysis

## Summary

When MAKELINK receives a V-span that maps to non-contiguous I-addresses (due to transclusion from multiple sources), the backend **automatically creates multiple I-spans** to represent the discontiguous regions in the link endset. The front end does NOT need to pre-split the V-span.

## Implementation Evidence

### Code Path Analysis

The link creation code path in `domakelink` (do1.c:173):

```c
bool domakelink(typetask *taskptr, typeisa *docisaptr,
                typespecset fromspecset, typespecset tospecset,
                typeisa *linkisaptr)
{
    ...
    return (
        ...
        && specset2sporglset (taskptr, fromspecset, &fromsporglset, NOBERTREQUIRED)
        && specset2sporglset (taskptr, tospecset, &tosporglset, NOBERTREQUIRED)
        ...
    );
}
```

### Key Function: vspanset2sporglset (sporgl.c:35-65)

This function converts V-spans to I-spans and creates separate sporgl (stored orgl) entries for each discontiguous region:

```c
typesporglset *vspanset2sporglset(typetask *taskptr, typeisa *docisa,
                                   typevspanset vspanset,
                                   typesporglset *sporglsetptr, int type)
{
    ...
    for (; vspanset; vspanset = vspanset->next) {
        (void) vspanset2ispanset (taskptr, orgl, vspanset, &ispanset);

        // CRITICAL LOOP: For EACH ispan returned
        for (; ispanset; ispanset = ispanset->next) {
            sporglset = (typesporgl *) taskalloc (taskptr, sizeof(typesporgl));
            sporglset->itemid = SPORGLID;
            sporglset->next = NULL;
            movetumbler (docisa, &sporglset->sporgladdress);
            movetumbler(&ispanset->stream,&sporglset->sporglorigin);
            movetumbler (&ispanset->width, &sporglset->sporglwidth);
            *sporglsetptr = (typesporglset)sporglset;
            sporglsetptr = (typesporglset *)&sporglset->next;
        }
    }
    return (sporglsetptr);
}
```

### The Critical Inner Loop (lines 49-58)

**For each I-span returned by `vspanset2ispanset`, a separate sporgl is created.**

The function `vspanset2ispanset` (orglinks.c:397) calls `permute`, which calls `span2spanset`, which uses `retrieverestricted` to find ALL context entries where the V-span maps to I-addresses. Each contiguous I-address region becomes a separate I-span in the result.

Therefore:
- Input: **One** V-span (e.g., positions 1.1-1.4 in document C)
- If that V-span maps to:
  - I-addresses 1.1-1.2 from document A
  - I-addresses 1.1-1.2 from document B (non-contiguous with A's addresses)
- Output: **Two** I-spans (sporgls) in the link endset

## Behavioral Implications

### 1. Front End Simplicity
The front end can create links on ANY contiguous V-span, regardless of the underlying I-address structure. The backend handles the complexity of splitting discontiguous regions.

### 2. Link Endset Structure
A link created with:
- Source: Single V-span from document C covering "AABB" (positions 1.1 width 0.4)
- Where "AA" came from document A and "BB" came from document B

Will store:
- **Two separate I-spans** in the source endset
- One pointing to the I-addresses for "AA" from document A
- One pointing to the I-addresses for "BB" from document B

### 3. Link Survivability
Each I-span independently tracks its content. If document A is deleted:
- The I-span referencing A's content becomes empty
- The I-span referencing B's content remains valid
- The link survives partially (points to "BB" but not "AA")

### 4. Endset Reporting
When `retrieve_endsets` is called:
- The endset will report **multiple V-spans** if the original V-span mapped to discontiguous I-addresses
- Each V-span corresponds to one of the I-spans created during link creation
- Finding 0019 confirms this behavior (see "Pivot Operations Fragment Link Endsets")

## Consistency with Finding 0019

Finding 0019 (Endset Operation Semantics) observed that pivot operations fragment link endsets into multiple spans. This is the SAME mechanism:

- **Pivot**: Rearranges content, making previously contiguous I-addresses non-contiguous
- **Result**: Multiple spans appear in endset because they now map to discontiguous I-regions
- **Mechanism**: The same `vspanset2sporglset` splitting logic

## Answer to Original Question

**Question**: When a POOM maps a contiguous V-span to non-contiguous I-addresses, does link creation produce multiple I-spans?

**Answer**: **YES**. The backend automatically splits the V-span into multiple I-spans, one for each contiguous I-address region. The front end does NOT need to pre-split the spans.

## Code References

- [do1.c:173-197] `domakelink` - Main link creation function
- [sporgl.c:35-65] `vspanset2sporglset` - V-span to I-span conversion with splitting
- [sporgl.c:49-58] **Critical loop** - Creates one sporgl per I-span
- [orglinks.c:397-402] `vspanset2ispanset` - Calls permute to find all I-spans
- [orglinks.c:404-422] `permute` - Finds all contiguous I-regions for a V-span
- [orglinks.c:425-454] `span2spanset` - Uses retrieverestricted to get contexts

## Related Findings

- **Finding 0019**: Endset Operation Semantics - Observed multi-span endsets after pivot
- **Finding 0004**: Link endpoints track content identity - Links follow I-addresses, not V-positions
- **Finding 0002**: Transclusion content identity immutable - Explains how V-spans map to I-addresses

## Architectural Insight

This design embodies a key Xanadu principle: **Content identity is fundamental**. Links are stored by I-address, not V-address. The system automatically handles the mapping, allowing users to create links on any visible content without understanding the underlying transclusion structure.
