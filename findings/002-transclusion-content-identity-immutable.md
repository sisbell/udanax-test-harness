# Finding 002: Transclusion preserves immutable content identity

**Date discovered:** 2026-01-30
**Category:** Transclusion semantics / Content model

## Summary

Xanadu's vcopy (virtual copy / transclusion) creates references to immutable content identities. Modifications to documents create new content rather than altering existing content.

## Key Behaviors Verified

### 1. Modifications don't affect transcluded content

When source document is modified after transclusion, the target is **not affected**:

```
Source before: "Original content here"
Target after vcopy: "Target: Original content"

Source modified to: "NEW: Original content here"
Target unchanged: "Target: Original content"
```

The edit to source created NEW content ("NEW: "). The original content identity that target references is unchanged.

**Test:** `vcopy_source_modified`

### 2. Deletion from source doesn't destroy content

When transcluded content is deleted from source, target **still has it**:

```
Source: "Keep this. Delete this. Keep end."
Target vcopies "Delete this."

After deleting "Delete this." from source:
  Source: "Keep this. Keep end."
  Target: "Transcluded: Delete this."  ← still has it!
```

Deletion removes content from a document's view, but the content identity persists as long as any document references it.

**Test:** `vcopy_source_deleted`

### 3. Transclusion is transitive

Content identity is preserved through chains of transclusion:

```
C: "Original from C"
B: "B prefix: Original"  (vcopied "Original" from C)
A: "A prefix: B prefix: Original"  (vcopied from B)

Comparing A and C shows shared content: "Original"
```

A never directly referenced C, but shares content identity with C through B.

**Test:** `nested_vcopy`

### 4. Version transclusion works correctly

Content can be transcluded from specific versions, and shares identity with both the version and the original document's common content.

**Test:** `vcopy_from_version`

## Implications

1. **Content is never destroyed** - only removed from views
2. **Edits create new content** - they don't modify existing content
3. **Identity tracking is fundamental** - the system tracks content by identity, not by location
4. **Transclusion chains work** - identity is preserved transitively

## Xanadu Model Confirmation

These findings confirm the Xanadu content model:
- Content has permanent, immutable identity
- Documents are collections of references to content
- "Editing" means adding new content and changing which content a document references
- Transclusion creates additional references to existing content identity

## Related Tests

- `vcopy_source_modified`
- `vcopy_source_deleted`
- `nested_vcopy`
- `vcopy_from_version`
- `vcopy_preserves_identity`

## Related Findings

- **Finding 007: Version Semantics** - Versioning also preserves content identity, and links follow content through both versioning and transclusion
