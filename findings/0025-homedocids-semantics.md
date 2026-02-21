# Finding 0025: Home Document Semantics

## Summary

Testing the `homedocids` filter in `find_links` reveals semantic insights about how "home documents" work in Xanadu, and exposes a non-functional filter.

**Related Bug**: [Bug 0015 - homedocids filter has no effect](../bugs/0015-homedocids-filter-ignored.md)

## What is a "Home Document"?

When creating a link via `create_link(home_doc, source_specs, target_specs, type_specs)`:

1. **The home document is the first parameter** - This is the document where the link "lives"
2. **Link IDs are allocated under the home document** - A link created with home doc `1.1.0.1.0.1` receives an ID like `1.1.0.1.0.1.0.2.1`
3. **Home document ≠ source document** - The home can be different from where the link's source endpoint is

## Link ID Structure

```
1.1.0.1.0.1.0.2.1
└─────┬────┘ └┬┘
  home doc   link suffix
```

Links created in the same home document get sequential suffixes under that document's address space. This confirms the home document is meaningful for storage/allocation.

## Protocol Format for homedocids

The `homedocids` parameter must be passed as **I-spans** (identity spans), not plain addresses:

```python
# Correct: span format (start address + width)
home_span = Span(doc_address, Offset(0, 1))
results = session.find_links(source_specs, NOSPECS, NOSPECS, [home_span])

# Wrong: plain address (causes protocol hang)
results = session.find_links(source_specs, NOSPECS, NOSPECS, [doc_address])
```

This is consistent with other filtering mechanisms in Xanadu - queries use span-based specifications.

## Semantic Implications

### Home Document as Ownership

The concept of a "home document" appears to be about where a link is *stored* or *owned*, distinct from where it connects from/to. This suggests:

- **Permissions model** - The home document owner controls the link
- **Resource accounting** - Link storage counts against the home document
- **Lifecycle binding** - Link may be tied to home document's existence

### Design Intent (Speculative)

The home document parameter likely serves:

1. **Address allocation** - Confirmed by link ID structure
2. **Ownership/permissions** - Who can modify or delete the link
3. **Discovery** - "Show me all links belonging to this document" (currently broken)
4. **Garbage collection** - Delete home doc → clean up its links

## Test Evidence

From `find_links_filter_by_homedocid.json`:

| Link | Home Doc | Source Doc | Link ID |
|------|----------|------------|---------|
| Link1 | doc1 | doc1 | `1.1.0.1.0.1.0.2.1` |
| Link2 | doc2 | doc2 | `1.1.0.1.0.2.0.2.1` |
| Link3 | doc1 | doc1 | `1.1.0.1.0.1.0.2.2` |

The link ID prefixes confirm home document affects allocation, even though the query filter doesn't work.

## Open Questions

1. What happens to links when their home document is deleted?
2. Can a link's home document differ from its source document in practice?
3. Is the homedocids filter simply unimplemented, or intentionally disabled?

## Golden Tests

- `golden/links/find_links_filter_by_homedocid.json`
- `golden/links/find_links_homedocids_multiple.json`
- `golden/links/find_links_homedocids_no_match.json`

## Related

- [Bug 0015](../bugs/0015-homedocids-filter-ignored.md) - The filter doesn't work
- Finding 0024 - Link permanence and orphaned links
