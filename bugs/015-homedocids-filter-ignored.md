# Bug 015: find_links homedocids Filter Has No Effect

## Summary

The `homedocids` parameter (4th argument to `find_links`, command 30) is parsed correctly but has no effect on filtering. All links matching the source/target specs are returned regardless of which document they are "homed" in.

## Reproduction

```python
# Create 3 documents
doc1 = session.create_document()
doc2 = session.create_document()
doc3 = session.create_document()

# Create link homed in doc1
link1 = session.create_link(doc1, source_in_doc1, target_in_doc2, type)

# Search with homedocids filter for doc3 (which has no links)
home_span = Span(doc3, Offset(0, 1))
results = session.find_links(source_in_doc1, NOSPECS, NOSPECS, [home_span])

# Expected: [] (no links homed in doc3)
# Actual: [link1] (filter ignored, returns all matching links)
```

## Evidence

See golden tests:
- `golden/links/find_links_filter_by_homedocid.json`
- `golden/links/find_links_homedocids_multiple.json`
- `golden/links/find_links_homedocids_no_match.json`

| Test Case | Filter | Expected | Actual |
|-----------|--------|----------|--------|
| 3 links, filter by 1 home | doc1 only | 1 link | 3 links |
| 3 links, filter by 2 homes | doc1+doc2 | 2 links | 3 links |
| 1 link, filter by uninvolved doc | doc3 | 0 links | 1 link |

## Technical Details

The backend correctly:
- Parses the homedocids as I-spans (passing addresses instead of spans causes hang)
- Stores home document info (link IDs are allocated under home doc address)

But the filtering logic appears to be missing or disabled.

Relevant C code:
- `get1fe.c:104-112` - Parameter parsing
- `do1.c` - Where filtering should occur

## Is This Intended Behavior?

**Uncertain.** Possible explanations:

1. **Unimplemented feature** - The parameter was added but filtering never implemented
2. **Disabled for performance** - Filtering by home doc may have been expensive
3. **Design change** - The concept of "home document" may have evolved to mean something different than "filterable ownership"

The fact that:
- The parameter exists and is correctly parsed
- Link IDs are allocated under the home document
- But filtering doesn't work

...suggests this was intended to work but may be incomplete.

## Workaround

Filter client-side by examining link ID prefixes (links are allocated under their home document's address).

## Related

- Finding 025: Home Document Semantics
- The "home document" concept in link creation
