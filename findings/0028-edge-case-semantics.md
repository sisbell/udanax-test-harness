# Finding 0028: Edge Case Semantics

**Date:** 2026-01-31
**Category:** Core Operations
**Tests:** `edgecases/*`

## Summary

Edge case testing revealed several important semantic behaviors that clarify how the backend handles boundary conditions.

---

## 1. Insertion Order: Prepend Semantics

When multiple inserts occur at the same position, **new text goes before existing text**.

```
Insert "First" at 1.1  → "First"
Insert "Second" at 1.1 → "SecondFirst"
Insert "Third" at 1.1  → "ThirdSecondFirst"
```

**Implication:** Position 1.1 means "before character 1" not "after start". This is cursor semantics - the cursor sits between characters.

---

## 2. Self-Transclusion Works

A document can transclude from itself:

```
Document: "Original"
Vcopy "Orig" to end → "OriginalOrig"
```

The transcluded portion maintains identity with the original, even within the same document. This enables patterns like:
- Creating repeated sections with shared identity
- Building recursive document structures

---

## 3. Overlapping Transclusions Preserve Identity

When transcluding overlapping regions from the same source:

```
Source: "ABCDEFGH"
Vcopy "ABCD" (1-4) → "ABCD"
Vcopy "CDEF" (3-6) → "ABCDCDEF"
```

Both "CD" instances in the destination share identity with the source "CD". The backend correctly tracks that characters at different V-positions can share the same I-position.

---

## 4. Single-Character Operations Work

The minimum unit of operation is one character:
- Insert single char: works
- Delete single char (first/middle/last): works
- Vcopy single char: works, maintains identity
- Pivot single chars: works ("AB" → "BA")

**No special handling needed** for minimum-size operations.

---

## 5. Empty/Zero-Width Behavior

| Operation | Zero-Width Input | Result |
|-----------|------------------|--------|
| Retrieve span | Span(1.1, 0.0) | Empty list (success) |
| Retrieve specset | Empty SpecSet() | Empty list (success) |
| Create link | Zero-width endpoints | **CRASH** (Bug 0017) |

Zero-width is valid for retrieval but crashes link creation.

---

## 6. Span Consolidation

Even with 100 separate single-character inserts, the backend maintains **a single contiguous span**:

```
100 inserts (A, B, C, ..., Z, A, B, ...)
retrieve_vspanset → span_count: 1
```

**The enfilade consolidates logically contiguous V-space** regardless of how it was constructed. This is important for performance - fragmented inserts don't create fragmented storage.

---

## 7. Self-Comparison Returns Full Content

Comparing a document with itself returns the entire document as "shared":

```python
compare_versions(doc, doc) → [(1.1, 0.17), (1.1, 0.17)]
```

This is correct - every character shares identity with itself.

---

## 8. Disjoint Documents Share Nothing

Documents created independently (not via version or vcopy) have no shared content:

```python
doc1 = create_document(); insert(doc1, "First content")
doc2 = create_document(); insert(doc2, "Second content")
compare_versions(doc1, doc2) → []
```

Even identical text has different I-positions if independently typed.

---

## 9. Version of Empty Document Works

Creating a version before adding any content succeeds:

```python
doc1 = create_document()  # empty
doc2 = create_version(doc1)  # succeeds: 1.1.0.1.0.1.1
insert(doc2, "Content")  # works
```

The version relationship is established even with no content to share.

---

## 10. Minimum-Width Links

Links with 1-character endpoints work fine:

```python
from_span = Span(1.1, 0.1)  # just 'S'
to_span = Span(1.12, 0.1)   # just 'T'
create_link(from_span, to_span)  # succeeds
```

But zero-width endpoints crash (Bug 0017).

---

## Architectural Implications

1. **V-positions are inter-character cursors**, not character indices
2. **I-position tracking is per-character granular** - single chars maintain identity
3. **The enfilade is self-healing** - fragmented inserts consolidate
4. **Identity requires common origin** - typed text is always distinct
5. **Zero-width is valid for queries, invalid for mutations**

---

## Related Findings

- Finding 0002: Transclusion content identity is immutable
- Finding 0016: Rearrange operations
- Finding 0027: Insertion order semantics
