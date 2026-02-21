# Finding 0019: Endset Operation Semantics

**Date:** 2026-01-30
**Status:** Documented

## Summary

Testing `retrieve_endsets` (FEBE opcode 28) reveals important semantics about how link endpoints are stored and queried.

## Key Findings

### 1. Endsets Use V-Addresses, Not I-Addresses

When content is inserted within a linked region, the link's source endset V-address shifts accordingly:

```
Before: "Click here for info" - link on "here" at 1.7 width 0.4
Insert: "right " at position 1.7
After:  "Click right here for info" - link now shows 1.13 width 0.4
```

The linked content "here" moved from V-position 1.7 to 1.13, and the endset reflects this new position.

### 2. Partial Deletion Shrinks Link Endsets

When part of a linked region is deleted, the link shrinks rather than breaking:

```
Before: "Click right here for info" - link on "right here" at 1.7 width 0.10
Delete: "right " (6 chars)
After:  "Click here for info" - link now shows 1.7 width 0.4
```

The remaining content "here" stays linked. The link endpoint adapts to the surviving content.

### 3. Pivot Operations Fragment Link Endsets

When linked content is rearranged with pivot, the endsets become fragmented:

```
Before: "ABCDEFGH" - link on "CD" at 1.3 width 0.2
Pivot:  swap BC and DE
After:  "ADEBCFGH" - endsets show FOUR spans:
        - 1.2 width 0.1 (twice)
        - 1.5 width 0.1 (twice)
```

The same link is also returned twice by `find_links`. This suggests the pivot operation creates internal fragmentation that is visible through the endset API.

### 4. Links Are Discovered Through Content Identity

When content is transcluded (vcopy) and then linked, the link can be found by searching the ORIGINAL document:

```
Document 1: "Original shared text"
Document 2: "Prefix: " + vcopy("shared" from doc 1)
Link created: from "shared" in doc 2 to target

find_links(doc 1, "shared" region) -> finds the link in doc 2!
```

This confirms that link discovery uses I-addresses (content identity), not just V-addresses.

### 5. Versions Inherit Links Through Content Identity

Links created on original documents are discoverable from versions:

```
Original doc: 1.1.0.1.0.1 with link at 1.17 width 0.4
Version:      1.1.0.1.0.1.1

find_links(version) -> finds original's link!
retrieve_endsets(version) -> shows version's docid (1.1.0.1.0.1.1)
```

The version shares content identity with the original, so links are inherited. However, when queried from the version, the endsets report the version's docid.

### 6. Target Endsets Often Empty

In most tests, the `target` specset returned by `retrieve_endsets` is empty when querying from the source document. This may indicate:
- Target endsets require querying from the target document
- The API returns only endpoints that intersect the query specset

### 7. Multi-Span Links Work But May Duplicate

Creating a link with multiple source spans works, but `retrieve_endsets` sometimes returns duplicate spans:

```
Link source: ["First" at 1.1, "second" at 1.16]
Endsets return: 3 spans (1.16 appears twice)
```

## Implications for Specification

1. **V-address tracking**: Endsets are dynamic - they reflect current V-positions after edits
2. **Identity-based discovery**: Links follow content, not position
3. **Version inheritance**: Links are logically inherited through content sharing
4. **Pivot fragmentation**: Rearrangement operations may fragment link representations

## Test Coverage

- `endsets/retrieve_endsets` - Basic endset retrieval
- `endsets/endsets_after_source_insert` - Endsets shift with content
- `endsets/endsets_after_source_delete` - Endsets after partial deletion
- `endsets/endsets_multispan_link` - Multi-span link endsets
- `endsets/endsets_after_pivot` - Endsets after rearrangement
- `endsets/endsets_transcluded_source` - Links on transcluded content
- `endsets/endsets_after_version` - Endsets across versions
- `endsets/endsets_compare_link_ends` - Source vs target comparison

## Related

- **Finding 0004**: Link endpoint semantics
- **Finding 0005**: Link survivability
- **Finding 0017**: vspan vs vspanset differences
