# Finding 017: retrieve_vspan vs retrieve_vspanset

**Date:** 2026-01-30
**Status:** Validated via golden tests
**Tests:** `golden/documents/retrieve_vspan*.json`

## Summary

`retrieve_vspan` and `retrieve_vspanset` return different views of document extent. For documents with mixed content (text + links), `vspanset` is more useful because it reveals the subspace structure.

## The Two Operations

| Operation | Opcode | Returns |
|-----------|--------|---------|
| RETRIEVEDOCVSPAN | 14 | Single span (overall extent) |
| RETRIEVEDOCVSPANSET | 1 | Multiple spans (per subspace) |

## Text-Only Document

For a document containing just "Hello World":

```
retrieve_vspan:    1.1 for 0.11
retrieve_vspanset: [{start: 1.1, width: 0.11}]
```

Same result - one span covering the text.

## Document With Links

For a document with text "Click here" and a link:

```
retrieve_vspan:    1.1 for 1.2  (tries to span everything)

retrieve_vspanset: [
  {start: 0,   width: 0.1},   // link subspace (0.x)
  {start: 1,   width: 1}      // text subspace (1.x)
]
```

**Key insight:** The vspanset reveals the dual subspace structure:
- **0.x subspace:** Link references (ISAs pointing to link atoms)
- **1.x subspace:** Text content

## Why This Matters

### 1. Content Type Awareness

To retrieve only text, use the 1.x span:
```python
text_span = vspanset.spans[1]  # 1.x subspace
```

To retrieve link references, use the 0.x span:
```python
link_span = vspanset.spans[0]  # 0.x subspace
```

### 2. Document Size Calculation

Using vspan on a document with links gives a misleading size. The span `1.1 for 1.2` suggests content from position 1.1 to 2.3, but actually there's a gap between 0.x and 1.x.

### 3. Iteration Over Content

To iterate all content correctly:
```python
for span in vspanset.spans:
    content = retrieve(span)
    # Process each subspace separately
```

## Recommendation

**Always use `retrieve_vspanset`** unless you specifically need a single bounding span. The vspanset:
- Shows all content regions
- Reveals subspace structure
- Enables correct content iteration
- Gives accurate size information

## Related

- **Finding 009**: Document address space structure (0.x vs 1.x subspaces)
- **Finding 010**: Unified storage abstraction (why subspaces exist)
