# Finding 015: Semantic Definition of compare_versions

**Date:** 2026-01-30
**Category:** Semantics / Formal Specification
**Related:** Bug 009, Finding 009

## Summary

The `compare_versions` operation (FEBE opcode 10: SHOWRELATIONOF2VERSIONS) answers the question:

> **"What text content do these two documents share by common origin?"**

It should compare only the **text subspace** (V-position ≥ 1), NOT the link subspace (V-position 0.x).

## Evidence from Xanadu Principles

### 1. Content Identity is the Basis of Comparison

From the FEBE protocol documentation:
> SHOWRELATIONOF2VERSIONS - Returns a list of ordered pairs of spans that **correspond (share common origin)**.

From Finding 002:
> Transclusion creates references to **immutable content identities**.

From Finding 007:
> The `compare_versions` operation finds shared content because both documents reference the **same underlying content identity**, not because the bytes happen to match.

**Key insight:** "Common origin" means shared **permascroll content identity** (I-addresses that point to immutable characters in the global permascroll).

### 2. Links Are Not Content with "Origin"

The document address space has two subspaces (Finding 009):

| V-Position | Contains | I-Address Type | Has "Common Origin"? |
|------------|----------|----------------|----------------------|
| 0.x | Link references | Link orgl ISAs | **No** |
| 1.x | Text content | Permascroll addresses | **Yes** |

**Why links have no "common origin":**

1. **Link ISAs are unique identities**, not content origins
   - A link orgl ISA like `1.1.0.1.0.2` identifies that specific link
   - Two documents cannot "share" the same link ISA via transclusion
   - Link ISAs are NOT permascroll addresses

2. **Links are metadata about content**, not content itself
   - Links attach to content identity (the FROM/TO endpoints)
   - The link reference at 0.x says "this document has a link"
   - It's document metadata, not shareable content

3. **Comparing link ISAs produces no meaningful result**
   - Two link ISAs will never match (each link is unique)
   - Even if they did match, it wouldn't mean "shared content"
   - The comparison is semantically undefined

### 3. The Semantic Question

When a user calls `compare_versions(doc_a, doc_b)`, they are asking:

> "Show me what text content these documents share through transclusion or common ancestry."

They are NOT asking:
> "Show me if these documents happen to have the same link references."

## The Correct Behavior

### What Should Happen

1. **Retrieve V-spans from both documents** (current behavior)
2. **Filter to text subspace only (V ≥ 1)** (missing step)
3. Convert V-spans to I-spans (current behavior)
4. Find common I-addresses (current behavior)
5. Map back to V-spans in each document (current behavior)

### Why the C Code Fails

The current implementation in `correspond.c`:
1. Retrieves ALL V-spans (including 0.x link subspace)
2. Converts ALL to I-spans
3. Tries to find common I-addresses

When processing link subspace (0.x):
- I-spans contain link orgl ISAs
- These ISAs are in a different address space than permascroll
- No intersection will be found (correct)
- But the code paths don't handle empty intersections gracefully → crash

### The Semantic Fix

The fix is to filter V-spans to the text subspace **before** conversion:

```c
// Before calling vspanset2ispanset for comparison:
vspanset = filter_to_text_subspace(vspanset);  // V >= 1.0

// Or in Dafny spec:
requires forall span :: span in vspanset ==> span.start >= V_TEXT_SUBSPACE
```

This is not a workaround - it's the semantically correct behavior. The operation is defined over text content, not link metadata.

## Implications for Formal Specification

### Precondition

```dafny
method CompareVersions(doc_a: DocumentId, doc_b: DocumentId)
  requires ValidDocument(doc_a) && ValidDocument(doc_b)
  returns (correspondences: seq<(VSpan, VSpan)>)
  ensures forall (span_a, span_b) in correspondences ::
    // Both spans are in text subspace
    span_a.start >= V_TEXT_START &&
    span_b.start >= V_TEXT_START &&
    // They share content origin (same I-address range)
    ContentOrigin(doc_a, span_a) == ContentOrigin(doc_b, span_b)
```

### Definition of Content Origin

```dafny
// Content has "origin" only if it's text content with a permascroll I-address
function ContentOrigin(doc: DocumentId, span: VSpan): Option<IAddressRange>
{
  if span.start >= V_TEXT_START then
    Some(VSpanToISpan(doc, span))  // Permascroll address
  else
    None  // Link subspace has no "origin" in this sense
}
```

## Summary

| Aspect | Text Subspace (V ≥ 1) | Link Subspace (0.x) |
|--------|----------------------|---------------------|
| Contains | Text characters | Link ISA references |
| I-address type | Permascroll | Document orgl |
| Has "common origin"? | Yes | No |
| Included in compare_versions? | **Yes** | **No** |
| Can be transcluded? | Yes | No (metadata) |

## Related

- **Bug 009**: Crash caused by processing link subspace in compare_versions
- **Finding 009**: Document address space structure (text vs link subspace)
- **Finding 002**: Transclusion and content identity
- **Finding 007**: Version semantics and content identity
- **Finding 010**: Unified storage abstraction leaks (this is one of the leaks)

## Conclusion

The semantic fix for Bug 009 is not defensive NULL handling - it's recognizing that `compare_versions` is defined over **text content**, and the link subspace should be filtered out before comparison. This aligns with the Xanadu principle that "common origin" means shared permascroll content identity.
