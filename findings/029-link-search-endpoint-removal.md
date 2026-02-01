# Link Search Behavior When Endpoints Removed from V-stream

**Date:** 2026-01-31
**Test file:** `febe/scenarios/links/search_endpoint_removal.py`
**Golden files:** `golden/links/search_*.json`

## Summary

This investigation tested how `find_links()` behaves when the content that link endpoints reference is partially or completely removed from a document's V-stream (visible view).

**TL;DR:** Links remain permanent but become undiscoverable when their endpoint content is deleted. Cross-endpoint search (find by target when source deleted) still works. Transclusion preserves findability. Type filtering is non-functional (pre-existing issue, not related to endpoint removal).

## Key Findings

### 1. Search Requires V-stream Presence

When searching for links by source endpoint, if the source content has been deleted from the V-stream, `find_links()` will **not** find the link.

```
Before delete: find_links(source_spec) → [link_id]
After delete:  find_links(source_spec) → []
```

**Test:** `search_by_source_after_source_removed`

### 2. Cross-Endpoint Search Works

If one endpoint is deleted but the other remains intact, `find_links()` can still discover the link via the intact endpoint.

| Source State | Target State | Search by Source | Search by Target |
|--------------|--------------|------------------|------------------|
| Intact       | Intact       | Found            | Found            |
| Deleted      | Intact       | Not found        | **Found**        |
| Intact       | Deleted      | **Found**        | Not found        |
| Deleted      | Deleted      | Not found        | Not found        |

**Tests:** `search_by_target_after_source_removed`, `search_by_source_after_target_removed`

### 3. Partial Deletion Preserves Findability

If only part of a linked span is deleted, the link remains findable as long as any portion of the original linked content remains in the V-stream.

```
Link created on: "hyperlink" (9 chars)
Delete: "hyper" (5 chars)
Remaining: "link" (4 chars)
Result: Link is STILL FINDABLE
```

**Test:** `search_partial_source_removal`

### 4. Transclusion Preserves Findability

When content is transcluded (vcopy'd) to another document, deleting from the original does not affect findability from the copy. The copy retains the content identity.

```
Original: "linked" → create link → vcopy to Copy
Delete "linked" from Original
find_links(Original) → []
find_links(Copy) → [link_id]  ← Still found!
```

**Test:** `search_after_vcopy_source_deleted`

### 5. Multiple Links with Selective Removal

When multiple links share a common target, deleting one source only affects findability of that specific link via source search. Target search still finds all links.

```
3 sources → 1 shared target (3 links total)
Delete source2 content
find_links(target) → [link1, link2, link3]  ← All 3 found
find_links(source2) → []  ← Only this one not found by source
```

**Test:** `search_multiple_links_selective_removal`

### 6. Links Are Permanent

Even when a link cannot be discovered via `find_links()`, it still exists and can be accessed directly if you have the link ID.

```
link_id = create_link(...)
delete source content
find_links(source) → []  ← Not discoverable
follow_link(link_id, LINK_SOURCE) → works!  ← Still accessible
follow_link(link_id, LINK_TARGET) → works!
follow_link(link_id, LINK_TYPE) → works!
```

This aligns with Xanadu's principle of permanent storage - links cannot be deleted, only orphaned.

## Semantic Model

The `find_links()` operation performs an **intersection** between:
1. The search specset (positions you're searching)
2. The link's endpoint specset (positions the link references)

For a link to be found, there must be **overlap in the current V-stream** between these two specsets. If the linked content no longer exists in the V-stream, there's nothing to intersect with.

However, the link itself is stored separately (in its home document) and continues to exist. The link's endpoint specifications still reference the original I-stream addresses, which:
- May resolve to empty if that content was deleted
- May resolve to content in a different document if that content was transcluded

### 7. AND Semantics for Multi-Criteria Search

When `find_links(source_spec, target_spec)` is called with both criteria, the search uses **AND semantics**. Both endpoints must be present in V-stream for the link to be found.

```
find_links(source, target) before delete → [link_id]
delete source content
find_links(source, target) after delete  → []  ← AND fails
find_links(NOSPECS, target) after delete → [link_id]  ← target-only works
```

**Test:** `search_by_both_endpoints_one_removed`

### 8. Search Specs Tolerate Non-Existent Positions

When a search spec references positions that no longer exist in the V-stream (e.g., after deletion shrinks the document), the search still works. It intersects with whatever content remains.

```
Document: "Start MIDDLE End link text" (26 chars)
Link on: "link"
Search spec: positions 1-26
Delete: "MIDDLE " (7 chars)
Document now: "Start End link text" (19 chars)
find_links(original 1-26 spec) → [link_id]  ← Still works!
```

The backend gracefully handles specs that extend beyond current document bounds.

**Test:** `search_spanning_deleted_boundary`

### 9. Type Filtering Anomaly

Type filtering with `find_links(source, NOSPECS, type_spec)` returns **empty results** for specific type filters, even when unfiltered search finds links of those types.

```
Before delete:
  find_links(source) → [jump, quote, footnote]  ← 3 links found
  find_links(source, NOSPECS, JUMP_TYPE) → []   ← Empty!
  find_links(source, NOSPECS, QUOTE_TYPE) → []  ← Empty!
```

This suggests either:
- Type specset format doesn't match how links store their type
- Type filtering has different semantics than endpoint filtering
- Possible bug in type matching

**Test:** `search_type_filter_with_removed_endpoints`

**Note:** This is a **pre-existing issue** - the `find_links_by_type` golden test also shows empty results for type-filtered searches. The type filtering API either:
- Requires a different specset format than we're using
- Has undocumented semantics
- May be a backend limitation

See also: `golden/links/find_links_by_type.json`

## Implications for Applications

1. **Bookmark link IDs** - Applications should store link IDs for important links, not rely solely on `find_links()` discovery
2. **Transclusion creates resilience** - Content that is transcluded to multiple documents has more findability paths
3. **Orphaned links are not broken** - They still work, just can't be discovered via content search
4. **Partial edits are safe** - Editing around (but not completely removing) linked content preserves findability

## Test Scenarios

| Scenario | Description |
|----------|-------------|
| `search_by_source_after_source_removed` | Find by source after source deleted |
| `search_by_target_after_source_removed` | Find by target when source gone |
| `search_by_source_after_target_removed` | Find by source when target gone |
| `search_by_both_endpoints_one_removed` | AND search with one endpoint deleted |
| `search_partial_source_removal` | Partial deletion of linked span |
| `search_multiple_links_selective_removal` | Multiple links, selective deletion |
| `search_spanning_deleted_boundary` | Search spec crossing deletion point |
| `search_after_vcopy_source_deleted` | Transclusion preserves findability |
| `search_type_filter_with_removed_endpoints` | Type filtering with mixed states |
