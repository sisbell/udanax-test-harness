# Finding 0024: Link Deletion and Orphaned Links

**Date discovered:** 2026-01-31
**Category:** Link semantics / Permanence / Architecture

## Summary

Links in Xanadu are **permanent** and **independent objects** - there is no DELETELINK operation in the FEBE protocol. Links become "orphaned" when their endpoint content is deleted, but the links themselves continue to exist and can be accessed by their link ID. This reveals fundamental aspects of Xanadu's architecture and philosophy.

---

## Semantic Insights

### 1. Links Are First-Class Citizens, Not Annotations

Links aren't metadata attached to content - they're **independent objects** stored in their own address space. When you delete "the link's source text," you haven't touched the link at all. The link continues to exist, pointing to an address that now resolves to empty.

This is philosophically significant: **links have their own identity separate from what they link**.

```
Content deleted  →  Link unaffected
Link points to   →  Address that resolves to empty
Link itself      →  Still exists, still accessible
```

### 2. "Deletion" in Xanadu is Soft

Nothing is ever truly deleted. When you "delete" text:
- The I-stream addresses remain valid (they just resolve to empty)
- Links pointing to that content still exist
- `find_documents` still reports the document contained that content (per Finding 0023)

This supports **permanent storage** - the historical record that "content X existed here and was linked to Y" is preserved even after deletion.

**Implication:** Xanadu maintains a complete audit trail. You can always answer "was there ever a link here?" even if the linked content is gone.

### 3. The Home Document Distinction is Architecturally Significant

```python
# Link stored in doc_A, connecting content in doc_B to doc_C
link = create_link(doc_A, source_in_B, target_in_C, type)
```

The "home document" is where the link **lives**, not where it **points**. Deleting all text from doc_A has zero effect on the link's functionality.

This architectural choice enables:

| Use Case | How It Works |
|----------|--------------|
| **Third-party linking** | Create links between documents you don't own |
| **Link collections** | A document can be purely a container of links with no text |
| **Link aggregators** | Curate links to others' content in your own document |
| **Annotation layers** | Overlay links on content without modifying it |

### 4. Asymmetry of Discoverability vs Accessibility

| Method | Requires | When It Works |
|--------|----------|---------------|
| `find_links(source_specs)` | Content at source address | Only when content exists |
| `follow_link(link_id)` | Just the link ID | Always (even orphaned) |

This creates an interesting information asymmetry:
- If you **bookmarked** a link ID, you can always access it
- If you're **searching** for links, deleted content makes them invisible

**Implication:** Link IDs are valuable "capabilities" - knowing one grants access even when normal discovery fails. They function like permanent access tokens.

### 5. "Right to Be Forgotten" is Architecturally Impossible

Links create permanent references that survive content deletion:
- The link still exists after source/target deletion
- The link ID remains valid forever
- Anyone with the link ID can see "there was a link from X to Y"

This is a fundamental design choice, not a bug. Xanadu prioritizes **historical integrity** over **erasure**.

---

## Technical Discoveries

### 1. Link Storage Architecture

Links occupy a separate address subspace (0.2.x) within documents:

```
Document address: 1.1.0.1.0.1
                  └─────────┘ document ID

Link address:     1.1.0.1.0.1.0.2.1
                  └─────────┘ home document
                            └───┘ link subspace (0.2)
                                └─┘ link number
```

Links are stored AS content in their home document, but in a separate namespace from text.

### 2. Links Appear in Document vspanset

After deleting all text from a document that contains links:

```json
{
  "op": "vspanset",
  "doc": "source",
  "spans": [{"start": "2.1", "width": "0.1"}]  // This is the link!
}
```

The document isn't "empty" - it contains a link in the 0.2.x subspace. This means:
- **Can't use vspanset length to check "is document empty?"**
- **Document "content" includes both text and links**

### 3. retrieve_contents Returns Links as Content

When retrieving document contents after text deletion:

```json
{
  "op": "contents",
  "result": [{"link_id": "1.1.0.1.0.1.0.2.1"}]
}
```

The `retrieve_contents` call returns the link as content in the document. Links are literally stored as document content, just in a different address range.

### 4. Link Type Returns Empty When Both Endpoints Deleted

**Unexpected behavior:** When both source AND target content are deleted, `follow_link(link_id, LINK_TYPE)` returns empty.

```json
{
  "op": "follow_link",
  "end": "type",
  "result": [],  // Expected: type vspec, Got: empty
  "comment": "Link type should still be accessible"
}
```

The type references the bootstrap document (doc 1), which wasn't deleted. Possible explanations:
- Bug in backend type resolution
- Type resolution depends on endpoint resolution succeeding
- Internal caching/state issue

**Status:** Needs further investigation.

### 5. Link Type Storage and the Type Registry

Link types are stored as **VSpec references to a type registry** in the bootstrap document (doc 1). When you create a link with a type, the type endset points to a specific address:

```python
# QUOTE type - references address 1.0.2.3 in bootstrap doc
QUOTE_TYPE = VSpec(
    docid=Address(1, 1, 0, 1, 0, 1),           # Bootstrap document
    spans=[Span(Address(1, 0, 2, 3), Offset(0, 1))]  # Local addr 1.0.2.3
)

# MARGIN type - references address 1.0.2.6.2 in bootstrap doc
MARGIN_TYPE = VSpec(
    docid=Address(1, 1, 0, 1, 0, 1),           # Same bootstrap document
    spans=[Span(Address(1, 0, 2, 6, 2), Offset(0, 1))]  # Local addr 1.0.2.6.2
)
```

**Type Registry Addresses:**

| Type | Local Address | Interpretation |
|------|---------------|----------------|
| JUMP | `1.0.2.2` | version.0.types.2 |
| QUOTE | `1.0.2.3` | version.0.types.3 |
| FOOTNOTE | `1.0.2.6` | version.0.types.6 |
| MARGIN | `1.0.2.6.2` | version.0.types.6.2 |

**Key observations:**

1. **Types are content references** - A link's type is a VSpec pointing to an address in the type registry, not a simple enum or flag.

2. **Hierarchical type system** - MARGIN (`2.6.2`) is under FOOTNOTE (`2.6`), suggesting subtypes. This enables type queries like "find all footnote-family links."

3. **Type registry is in doc 1** - The bootstrap document contains the canonical type definitions at addresses `1.0.2.x`.

4. **Link address vs type address clarity**:
   - In a regular document: `2.1` = "link subspace, first link instance"
   - In bootstrap doc type registry: `1.0.2.3` = "version 1, into subspace, types (2), quote (3)"

**Retrieval limitation:** Despite types being stored when links are created, `follow_link(link_id, LINK_TYPE)` and `retrieve_endsets` often return empty for the type endset. This appears to be a backend limitation - see Finding 0019 section 6.

---

## Orphaned Link Behavior Matrix

| Deleted Content | `find_links` | source endpoint | target endpoint | type endpoint |
|-----------------|--------------|-----------------|-----------------|---------------|
| Nothing | Works | Works | Works | Works |
| Source text only | Empty | Empty | Works | Works |
| Target text only | Works | Works | Empty | Works |
| Both source & target | Empty | Empty | Empty | Empty* |
| Home doc text only | Works | Works | Works | Works |

*Unexpected - type should reference bootstrap doc which wasn't deleted.

---

## Design Implications

### For System Implementers

1. **Link garbage collection would require explicit operation** - No automatic cleanup exists or is possible without new protocol commands

2. **"Empty" documents may contain links** - Can't trust vspanset to determine if document is truly empty; must check for both text spans (1.x) and link spans (2.x)

3. **Link IDs should be treated as sensitive** - They're permanent access tokens that survive content deletion

### For Application Developers

1. **Bookmark important link IDs** - They remain useful even when find_links fails

2. **Design for orphaned links** - UI should handle links that resolve to empty gracefully

3. **Consider link discovery vs direct access** - Different capabilities, different use cases

### For Users/Policy

1. **Deletion is not erasure** - Content can be removed from view but references persist

2. **Links are permanent commitments** - Creating a link creates a permanent record

3. **Third-party links exist** - Others can create links to/from your content stored in their documents

---

## Test Coverage

| Scenario | Status | Key Finding |
|----------|--------|-------------|
| `link_permanence_no_delete_operation` | PASS | No delete_link operation exists |
| `orphaned_link_source_all_deleted` | PASS | Link survives, source empty, target works |
| `orphaned_link_target_all_deleted` | PASS | Link survives, target empty, source works |
| `orphaned_link_both_endpoints_deleted` | PASS | Link survives, both empty, type empty* |
| `orphaned_link_discovery_by_link_id` | PASS | Direct access works when find_links fails |
| `link_home_document_content_deleted` | PASS | Home text deletion has no effect |
| `multiple_orphaned_links_same_content` | PASS | All links orphan simultaneously |
| `link_retrieval_via_endsets` | PASS | Endsets shrink to empty |

---

## Open Questions

1. **Why does link type return empty when both endpoints are deleted?** Needs investigation - may be bug or intentional.

2. **Is there any way to enumerate all links in a document?** Current API requires content to search against. Could query the 0.2.x address range directly?

3. **Can links be "revived"?** If content is re-inserted at the same I-stream address, does the orphaned link start working again?

4. **What about link permissions?** Can anyone follow a link if they know the ID, or are there access controls?

---

## Related Findings

- **Finding 0005:** Link survivability validated (links survive adjacent modifications)
- **Finding 0019:** Endset semantics (how link endpoints track content)
- **Finding 0023:** find_documents returns deleted content (soft deletion throughout)
- **FEBE Protocol:** No DELETELINK operation defined in specification
