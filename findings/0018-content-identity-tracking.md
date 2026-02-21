# Finding 0018: Content Identity Tracking (FINDDOCSCONTAINING and Sporgl)

**Date discovered:** 2026-01-30
**Category:** Content model / Provenance tracking

## Summary

The Xanadu backend tracks content identity through I-addresses (immutable positions in the permascroll). The `FINDDOCSCONTAINING` operation (opcode 22) enables discovery of all documents containing specific content, and `compare_versions` reveals shared content identity between documents. These operations expose the underlying sporgl (span + orgl) provenance tracking system.

## Key Findings

### 1. Identical text has different I-addresses when created independently

Two documents with identical text do NOT share content identity:

```
Source1: "From source one"  (I-address: X)
Source2: "From source two"  (I-address: Y)

compare_versions(source1, source2) → [] (empty - no shared content!)
```

Content identity is based on **when and where** content was created, not its textual value.

**Test:** `identity_mixed_sources`

### 2. FINDDOCSCONTAINING finds transitive transclusions

When A transcludes from B, and B transcludes from C, querying C's content finds all three:

```
C: "Original content from C"
B: "B: Original content"  (vcopied from C)
A: "A: B: Original content"  (vcopied from B)

find_documents("Original" from C) → [C, B, A]
```

Content identity flows transitively through transclusion chains.

**Test:** `find_documents_transitive`

### 3. Rearrange operations preserve content identity

Pivot and swap operations change V-positions but preserve I-addresses:

```
Before pivot: "First Second"
  - "First " at V-position 1.1
  - "Second" at V-position 1.7

After pivot: "SecondFirst "
  - "Second" at V-position 1.1 (same I-address!)
  - "First " at V-position 1.7 (same I-address!)

compare_versions(before, after) → all content shared
```

Rearrange is a structural operation that doesn't create new content.

**Tests:** `identity_through_rearrange_pivot`, `identity_through_rearrange_swap`

### 4. Content identity persists after deletion from source

When transcluded content is deleted from the source document, it remains discoverable through the target:

```
Source before: "Keep. Transclude this. End."
Target: "Target has: Transclude this"

After deleting "Transclude this" from source:
  Source: "Keep.  End."
  Target: "Target has: Transclude this"  (unchanged)

find_documents("Transclude this" from target) → [source, target]
```

The spanf index retains the I-address mapping even after deletion from a document's V-stream.

**Test:** `find_documents_after_source_deletion`

### 5. Version chains share content identity

When a version is created, content identity is preserved:

```
Original: "Original text"
Version:  "Original text v2 additions"

compare_versions(original, version) → "Original text" shared
find_documents("Original" from original) → [original, version]
```

**Test:** `identity_through_version_chain`

**Note:** Deep version chains (3+ versions with content added at each level) cause the backend to crash when using `compare_versions` or `find_documents`. See Bug 0012.

### 6. Partial transclusion preserves identity transitively

Transcluding part of already-transcluded content maintains the chain:

```
C: "ABCDEFGHIJ"
B: vcopies all of C
A: vcopies "DEFGH" from B

compare_versions(A, C) → "DEFGH" shared
find_documents("DEF" from C) → [A, B, C]
```

A never directly referenced C, but shares content identity through B.

**Test:** `identity_partial_transclusion`

## Architectural Insight

These findings confirm the sporgl architecture documented in Finding 0013:

1. **Sporgl** = I-address span + source document ISA
2. **Spanf** index maps I-addresses to documents containing that content
3. **FINDDOCSCONTAINING** queries spanf by I-address
4. **compare_versions** finds intersection of I-addresses between documents

The dual enfilade architecture (granf for content, spanf for link/content index) enables efficient content identity queries across the entire docuverse.

## Implications

1. **Full-text search is NOT content search** - Same words created separately have different identities
2. **Provenance is trackable** - You can trace content back to its origin
3. **Deletion is soft** - Content persists as long as any document references it
4. **Rearrangement is cheap** - Only V-positions change, not I-addresses
5. **Version comparison is O(content)** - Based on I-address intersection, not diff

## Related Tests

- `find_documents_basic`
- `find_documents_transitive`
- `find_documents_after_source_deletion`
- `find_documents_empty_result`
- `identity_through_rearrange_pivot`
- `identity_through_rearrange_swap`
- `identity_multi_document_sharing`
- `identity_through_version_chain`
- `identity_partial_transclusion`
- `identity_mixed_sources`

## Related Findings

- **Finding 0002:** Transclusion content identity immutable
- **Finding 0012:** Dual enfilade architecture (granf + spanf)
- **Finding 0013:** Sporgl provenance tracking

## Related Bugs

- **Bug 0012:** Deep version chain crash - backend crashes on 3+ version chains with compare_versions or find_documents
