# Finding 0003: Multi-span operations preserve independent content identity

**Date discovered:** 2026-01-30
**Category:** SpecSet semantics / Content addressing

## Summary

Xanadu's SpecSet mechanism allows operations on multiple non-contiguous spans, potentially from multiple documents. Each span maintains independent content identity through these operations.

## Key Behaviors Verified

### 1. Multi-span retrieve concatenates content

When retrieving multiple spans, the contents are concatenated in order:

```
Document: "The quick brown fox jumps over the lazy dog"
Retrieve spans: "quick" (chars 5-9), "lazy" (chars 36-39)
Result: "quicklazy"
```

The spans are extracted independently and combined. Order matters - the result reflects the order spans are specified.

**Test:** `retrieve_noncontiguous_spans`

### 2. Multi-span vcopy preserves identity for each span

When copying multiple non-contiguous spans:

```
Source: "First part. Middle part. Last part."
vcopy spans: "First part", "Last part" (skipping middle)
Target: "Copied: First partLast part."

Compare shows TWO shared regions:
  - "First part" (source pos 1-10 ↔ target pos 9-18)
  - "Last part" (source pos 26-35 ↔ target pos 19-28)
```

Each span gets its own identity mapping. The compare operation returns multiple shared regions, one for each copied span.

**Test:** `vcopy_multiple_spans`

### 3. SpecSets can reference multiple documents

A single SpecSet can contain VSpecs from different documents:

```
DocA: "Alpha content"
DocB: "Beta content"
DocC: "Gamma content"

SpecSet: [span from A, span from B, span from C]
vcopy to Target combines all three
```

The operation works atomically across document boundaries.

**Test:** `vcopy_from_multiple_documents`

### 4. Retrieve from multiple documents works

Content can be retrieved from multiple documents in a single operation:

```
Doc1: "Document one content"
Doc2: "Document two content"

Retrieve SpecSet with spans from both:
Result: "one contenttwo content"
```

**Test:** `retrieve_multiple_documents`

### 5. Compare respects SpecSet boundaries

When comparing documents using SpecSets, only the specified spans are considered:

```
DocA: "Shared prefix. A middle. Shared suffix."
DocB: "Shared prefix. B middle. Shared suffix."

Compare full documents: shares prefix and suffix
Compare only middles: no shared content
```

**Test:** `compare_multispan_specsets`

## Implications

1. **Granular content selection** - Operations can target exactly the content needed
2. **Cross-document operations** - Content from multiple documents combines naturally
3. **Independent identity tracking** - Each span maintains its own identity chain
4. **Composable specifications** - SpecSets build complex selections from simple spans

## Technical Details

### VSpec Structure
A VSpec (Virtual Specification) identifies a span within a document:
- Document ID (tumbler address)
- Start position (tumbler)
- Width (tumbler representing span size)

### SpecSet Structure
A SpecSet is an ordered collection of VSpecs. Operations process VSpecs in order, maintaining the sequence in results.

## Xanadu Model Confirmation

These findings confirm the SpecSet model:
- VSpecs are the fundamental unit of content reference
- SpecSets compose VSpecs into complex selections
- Content identity is preserved per-VSpec, not per-SpecSet
- Cross-document operations are first-class (no special handling needed)

## Related Tests

- `retrieve_noncontiguous_spans`
- `retrieve_multiple_documents`
- `vcopy_multiple_spans`
- `vcopy_from_multiple_documents`
- `compare_multispan_specsets`
