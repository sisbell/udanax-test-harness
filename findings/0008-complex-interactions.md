# Finding 0008: Complex Interactions - Links, Versions, and Transclusion

**Date:** 2026-01-30
**Status:** Validated via golden tests (6 of 7 scenarios)
**Tests:** `golden/interactions/*.json`

## Summary

Links in Xanadu are truly bound to content identity, not document identity. This means links are discoverable from ANY document that shares the linked content's identity - whether through transclusion, versioning, or chains of both.

## Key Findings

### 1. Links Follow Content Through Transclusion

When content with a link is transcluded to another document, the link is discoverable from the copy:

```
Source: "Click here for details"  (link on "here")
Copy:   "Transcluded: here"       (vcopy of "here")

find_links(Source) → [link_id]
find_links(Copy)   → [link_id]  ← SAME LINK!
```

**Test:** `transclude_linked_content`

The copy document can find the link because it contains content with the same identity as the link source.

### 2. Links Added to Version Are Discoverable from Original

If you add a link to a version, the original document (which shares content identity) can also discover it:

```
Original: "Shared content here"
Version:  "Shared content here"  (version of original)

Add link on "content" to VERSION:
find_links(Version)  → [link_id]
find_links(Original) → [link_id]  ← FINDS IT!
```

**Test:** `version_add_link_check_original`

This is bidirectional - links added to either document are discoverable from both.

### 3. Transitive Link Discovery Across Version + Transclusion

Links are discoverable transitively through combined version and transclusion chains:

```
C: "Original content in C"    (link on "content")
B: version of C
A: transcludes from B

find_links(C) → [link_id]
find_links(B) → [link_id]  (B is version of C)
find_links(A) → [link_id]  (A transcludes from B!)
```

**Test:** `transitive_link_discovery`

Document A never directly interacted with C, yet it can discover C's link because:
1. A transcludes from B (shares content identity with B)
2. B is version of C (shares content identity with C)
3. Therefore A shares content identity with C transitively

### 4. Links Work When Both Endpoints Are Transcluded

You can create a link where both the source and target are transcluded content:

```
source_origin: "Clickable source text"
target_origin: "Target destination text"
link_doc:      "Link doc: Clickable -> Target"  (both transcluded)

Create link from "Clickable" to "Target" in link_doc:
find_links(link_doc)       → [link_id]
find_links(source_origin)  → [link_id]  (by source search)
find_links(target_origin)  → [link_id]  (by target search)
```

**Test:** `link_both_endpoints_transcluded`

All three documents can discover the link! The original content providers can find links that were created on their transcluded content.

### 5. Link on Transcluded Content Survives Versioning

When a document transcludes content, you create a link on it, and then version the document:

```
Source: "Source with linked text here"  (link on "linked")
Doc:    "Doc prefix: linked text"       (transcludes "linked text")
Version: version of Doc

find_links(Source)  → [link_id]
find_links(Doc)     → [link_id]
find_links(Version) → [link_id]  ← survives versioning!
```

**Test:** `version_transcluded_linked_content`

The version can discover the link because it shares content identity with Doc, which shares content identity with Source.

## Bug Discovered

**Bug 0009:** `compare_versions` crashes when documents have links embedded. See `bugs/0009-compare-versions-crashes-with-links.md`.

This prevented the `compare_versions_with_different_links` test from completing.

## Implications

### For Xanadu Semantics

1. **Links are global** - A link created in one document is discoverable from any document sharing that content
2. **Content identity is the key** - Not document identity, not addresses, but content identity
3. **Transitivity works** - Chains of versions and transclusions all share link discoverability
4. **Bidirectional discovery** - Links can be found by searching source OR target content

### For Implementation

1. Link search must traverse content identity relationships
2. `find_links` effectively searches the content identity graph
3. Version creation must preserve content identity (it does)
4. Transclusion (vcopy) must preserve content identity (it does)

### For User Experience

This is powerful but potentially surprising:
- A user might add a link in their document, not realizing it becomes visible to anyone who transcluded that content
- Version management must consider that links are shared between versions
- Content reuse through transclusion automatically "inherits" links

## Test Matrix

| Scenario | Link Created In | Discoverable From |
|----------|-----------------|-------------------|
| transclude_linked_content | source | source, copy |
| link_to_transcluded_then_version | doc (on transcluded) | source, doc, version |
| version_add_link_check_original | version | original, version |
| transitive_link_discovery | C | A, B, C |
| link_both_endpoints_transcluded | link_doc | link_doc, source_origin, target_origin |
| version_transcluded_linked_content | source | source, doc, version |

## Related Findings

- **Finding 0002:** Transclusion content identity - foundation for this behavior
- **Finding 0007:** Version semantics - versioning also preserves content identity
- **Finding 0004:** Link endpoint semantics - how links are stored and searched
