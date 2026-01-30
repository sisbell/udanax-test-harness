# Finding 004: Link endpoints track content identity

**Date discovered:** 2026-01-30
**Updated:** 2026-01-30 (after Bug 008 client fixes)
**Category:** Link semantics / Content model

## Summary

~~Links in Xanadu Green store their endpoints by **document address** rather than by **content identity**.~~

**CORRECTED:** After fixing client-side bugs (Bug 008), all link survivability tests now pass. Links DO track content identity and survive document modifications, consistent with transclusion semantics.

## Key Behaviors Confirmed

### 1. Links survive document modification

When a document with links is modified, links remain valid:

| Operation | Result |
|-----------|--------|
| Insert before linked span | PASS - link still findable |
| Delete adjacent text | PASS - link survives |
| Delete linked span | PASS - link exists, points to empty |
| Delete target span | PASS - link exists, target empty |
| Partial delete of linked span | PASS - link points to remainder |
| vcopy linked content | PASS - link found from copy |
| Modify target document | PASS - link survives |

**Tests:** All `link_survives_*` and `link_when_*` tests PASS

### 2. Consistency with transclusion

Both transclusion (vcopy) and links use **content identity**:

**Transclusion:** When source content is deleted, transcluded copy survives (has its own reference to the content)

**Links:** When linked content is modified, link endpoints adjust to track the content

### 3. Link discovery from transcluded content

When content with a link is transcluded to another document, the link can be found from both locations:

```
Document A: "Click [here] for details"  ← link on "here"
Document C: "Copied: [here]"            ← vcopy of "here"

find_links(search in C) → returns the original link
```

This confirms links attach to content identity, not document position.

## Bug 008 Resolution

The original findings were incorrect due to client-side bugs:

1. **`delete()` used wrong FEBE command** - Used REARRANGE (3 cuts) instead of DELETEVSPAN
2. **`retrieve_contents()` passed wrong type** - Passed VSpec instead of SpecSet
3. **Scenarios opened document twice** - Backend doesn't allow duplicate handles

These client bugs caused protocol errors and crashes that were misattributed to backend link fragility.

## Architectural Conclusion

Xanadu Green implements the intended design:

| Feature | Implementation | Status |
|---------|---------------|--------|
| Permanent content identity | Transclusion (vcopy) | Working |
| Bidirectional links | Link enfilade (orgl) | Working |
| Links survive editing | Content-identity tracking | Working |

## Remaining Issues

1. **`compare_versions()` + links** - Backend crashes when comparing documents that contain links (separate bug)

## Tests - All Passing

- `link_survives_source_insert` - PASS
- `link_survives_source_delete_adjacent` - PASS
- `link_when_source_span_deleted` - PASS
- `link_when_target_span_deleted` - PASS
- `link_source_partial_delete` - PASS
- `link_with_vcopy_source` - PASS
- `link_survives_target_modify` - PASS

## Related

- Bug 008: ~~Backend crashes on linked document edit~~ RESOLVED (client bugs)
- Bug 009: compare_versions crashes when documents have links (link subspace issue)
- Finding 002: Transclusion preserves immutable content identity
- Finding 003: Multi-span operations preserve independent identity
- Finding 009: Document address space structure (explains how links are stored at V-position 0.x)
- `findings/xanadu-model-validation.md` - Detailed semantic validation
