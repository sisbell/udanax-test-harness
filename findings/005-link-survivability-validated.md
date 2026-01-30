# Finding 005: Link survivability and content identity validated

**Date discovered:** 2026-01-30
**Category:** Link semantics / Content identity

## Summary

Empirical observations confirming Xanadu semantic properties through golden test scenarios. After Bug 008 client fixes, all 17 link scenarios pass, validating that the Xanadu content identity model works as designed.

## Content Identity

### Links Follow Content, Not Position

**Observation:** When content is transcluded (vcopy'd) to another document, links attached to that content can be found from the new location.

**Test:** `link_with_vcopy_source` scenario
```
1. Create document A with "Click here for details"
2. Create link on "here" pointing to document B
3. Create document C, vcopy "here" from A to C
4. find_links() on document C returns the original link
```

**Implication:** Links are attached to content by tumbler address (I-stream identity), not by document position. The transcluded "here" in document C shares identity with the original "here" in document A, so the link is discoverable from both locations.

This validates the Xanadu principle that content has persistent identity independent of where it appears.

---

## Link Survivability

### Links Survive Adjacent Modifications

**Observation:** Links remain valid and findable when text is inserted or deleted adjacent to (but not overlapping) the linked span.

**Tests:**
- `link_survives_source_insert` - insert before linked span
- `link_survives_source_delete_adjacent` - delete adjacent text
- `link_survives_target_modify` - modify target document

**Implication:** The enfilade structure maintains link endpoints through document modifications. The tumbler addresses in the link's endsets continue to resolve correctly even as surrounding content changes.

---

### Partial Deletion Shrinks Link Span

**Observation:** When part of a linked span is deleted, the link remains valid and points to the remaining portion.

**Test:** `link_source_partial_delete`
```
1. Create link on "hyperlink" (9 characters)
2. Delete "hyper" (5 characters)
3. Link source now resolves to "link" (4 characters)
```

**Implication:** Link endpoints are ranges (start + width), and deletion operations properly adjust these ranges. The link doesn't break - it adapts to point to what remains.

---

### Full Deletion Preserves Link Existence

**Observation:** When the entire linked span is deleted, the link still exists and can be followed, though it resolves to empty content.

**Test:** `link_when_source_span_deleted`
```
1. Create link on "here"
2. Delete "here " from document
3. follow_link() still works, returns empty span
4. find_links() no longer finds the link from document
```

**Implication:** Links are independent objects stored in the orgl (link enfilade). Deleting content doesn't delete the link - it just removes the content the link referenced. This preserves referential integrity at the cost of having "dangling" links.

---

## Open Questions

### Link Discovery After Content Deletion

When a linked span is deleted:
- `follow_link()` still works (returns empty)
- `find_links()` doesn't find it (no content to match)

**Question:** Is this the intended behavior? Should there be a way to find "orphaned" links?

### Bidirectional Link Discovery

Links can be found by searching either source or target spans:
- `find_links(source_specs)` - find by source
- `find_links(NOSPECS, target_specs)` - find by target

**Validated in:** `find_links_by_target` scenario

---

## Test Coverage

| Property | Scenario | Status |
|----------|----------|--------|
| Content identity via vcopy | link_with_vcopy_source | PASS |
| Links survive insert | link_survives_source_insert | PASS |
| Links survive adjacent delete | link_survives_source_delete_adjacent | PASS |
| Links survive target modify | link_survives_target_modify | PASS |
| Partial span deletion | link_source_partial_delete | PASS |
| Full source span deletion | link_when_source_span_deleted | PASS |
| Full target span deletion | link_when_target_span_deleted | PASS |
| Bidirectional links | bidirectional_links | PASS |
| Find by target | find_links_by_target | PASS |
| Overlapping link spans | overlapping_links | PASS |

---

## Related

- Finding 004: Link endpoints track content identity (corrected after Bug 008)
- Finding 002: Transclusion preserves immutable content identity
- Finding 003: Multi-span operations preserve independent identity
- Bug 008: Client-side bugs caused test failures (RESOLVED)
