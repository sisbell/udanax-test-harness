# Finding 028b: Link Discovery via Content Identity

**Date:** 2026-01-31
**Related:** Finding 004, Finding 010, Finding 027b

## Summary

Links are discoverable from any document that shares content identity (I-address) with a link endpoint. However, the link itself is an immutable entity with fixed endpoints - discovery gives you the complete link, not a "view" filtered to your document's content.

## Key Semantic Properties

### 1. Links Have Fixed Endpoints

When a link is created, its source and target endpoints are fixed V-spans in specific documents. These never change.

```
Link created:
  Source: Document A, V-span 1.4 for 0.3 ("DEF")
  Target: Document B, V-span 1.1 for 0.6 ("Target")
```

### 2. Discovery is via I-Address Overlap

`find_links` searches using content identity (I-address), not document identity:

```
Document A: "ABCDEFGHIJ" (I-addresses I.1 through I.10)
Link source: "DEF" (I-addresses I.4, I.5, I.6)

Document C transcludes "EF" from A:
  C contains: "Copy: EF"
  C's "EF" has I-addresses I.5, I.6 (same as in A)

find_links(C) → finds the link (I-address overlap on I.5, I.6)
```

### 3. follow_link Returns Complete Endpoints

Even when discovered via partial overlap, `follow_link` returns the **full** link endpoint:

```
find_links(C) → Link ID (found via I.5, I.6 overlap)
follow_link(Link ID, SOURCE) → SpecSet referencing A at 1.4 for 0.3
retrieve_contents → "DEF" (complete source, not just "EF")
```

The link doesn't know or care how you discovered it. It always returns its full, fixed endpoints.

### 4. Transclusion Shares Identity, Not Links

Transclusion (vcopy) creates shared content identity. It does NOT:
- Copy links to the new document
- Create new links
- Modify existing links

It DOES:
- Share I-addresses between documents
- Enable link discovery from the new document
- Preserve the semantic relationship "this content has a link"

### 5. Links Exist in Link-Space

Links are stored separately from document content (in the span-f enfilade). They reference documents but don't "belong to" any single document. A link can be:
- Created from document A
- Discovered from document B (via transclusion)
- Retrieved showing content from document A

## Semantic Model

```
┌─────────────────────────────────────────────────────────────┐
│                     LINK SPACE (span-f)                      │
│  Link L1: Source(A, 1.4, 0.3) → Target(B, 1.1, 0.6)         │
│           I-addresses: I.4, I.5, I.6                         │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐
│   Document A      │ │  Document B   │ │   Document C      │
│ "ABCDEFGHIJ"      │ │ "Target..."   │ │ "Copy: EF"        │
│ I.1-I.10          │ │               │ │ I.5, I.6 (shared) │
│                   │ │               │ │                   │
│ find_links → L1 ✓ │ │               │ │ find_links → L1 ✓ │
│ (direct match)    │ │               │ │ (I-addr overlap)  │
└───────────────────┘ └───────────────┘ └───────────────────┘
```

## Implications for Specifications

### find_links Semantics

```
find_links(search_specset) returns links where:
  ∃ I-address i:
    i ∈ I-addresses(search_specset) ∧
    i ∈ I-addresses(link.source_endpoint)
```

The search is purely I-address based. Document identity doesn't matter.

### follow_link Semantics

```
follow_link(link_id, endpoint) returns:
  The complete, original SpecSet for that endpoint
  (as specified when link was created)
```

No filtering, no "view" - the full endpoint.

### Content Identity Principle

Links demonstrate the Xanadu content identity principle:
- Content has permanent identity (I-address)
- Operations reference identity, not location
- Identity survives copying, moving, editing
- Semantic relationships (links) attach to identity

## Test Evidence

From `partial_vcopy_of_linked_span.json`:
```json
{
  "op": "vcopy",
  "text": "link",
  "comment": "Transclude only 'link' which is PART of 'hyperlink text'"
},
{
  "op": "find_links",
  "from": "copy",
  "result": ["1.1.0.1.0.1.0.2.1"],
  "comment": "Link discoverable from partial copy via I-address overlap"
},
{
  "op": "follow_link",
  "from": "copy",
  "result": ["hyperlink text"],
  "comment": "follow_link returns full link source (link is immutable entity)"
}
```

Copy contains "link" (4 chars), but `follow_link` returns "hyperlink text" (14 chars) - the complete original link source.

## Related

- **Finding 004**: Link endpoint semantics
- **Finding 010**: Unified storage abstraction (links stored via I-addresses)
- **Finding 027b**: retrieve_contents requires source document open
- **Literary Machines**: "Links are always between specific bytes"
