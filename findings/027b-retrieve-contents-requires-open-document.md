# Finding 027b: retrieve_contents requires referenced documents to be open

**Date:** 2026-01-31
**Related:** Bug 008, Finding 010

## Summary

`retrieve_contents` (FEBE opcode 5) fails with "error response from back-end" if the SpecSet references a document that is not currently open. This is expected behavior but can cause confusing errors when following links.

## Discovery

When testing partial overlap scenarios with links and transclusion:

1. Create link in document A
2. Close document A
3. `find_links` from document B (which transcludes from A) - **works**
4. `follow_link` on found link ID - **works**, returns SpecSet referencing A
5. `retrieve_contents` on that SpecSet - **FAILS** because A is closed

## Backend Log Evidence

```
orgl for 0.1.1.0.1.0.1~ not open in findorgl temp = 0
```

The backend's `findorgl` function requires the document orgl to be in the "open" list.

## Code Path

1. `retrieve_contents` calls `doretrievev` (do1.c)
2. `doretrievev` calls `specset2ispanset` which calls `findorgl`
3. `findorgl` checks if the document is in the open list
4. If not open, returns FALSE, causing the operation to fail

## Implications

### For `follow_link`

`follow_link` returns a SpecSet containing the link endpoint spans. These spans reference the document where the link endpoint exists (the source document for LINK_SOURCE, target document for LINK_TARGET).

To successfully `retrieve_contents` on a `follow_link` result, the referenced document(s) must be open.

### For Link Discovery Across Documents

When discovering links via transclusion:
1. Document B transcludes content from A
2. Link exists on A's content
3. `find_links` from B finds the link (via I-address lookup)
4. `follow_link` returns spans in A
5. Must open A to retrieve the actual link source text

### Workaround Pattern

```python
# After follow_link, check which documents need to be opened
link_specset = session.follow_link(link_id, LINK_SOURCE)
for spec in link_specset.specs:
    doc_id = spec.docid
    # Ensure document is open before retrieve_contents
    handle = session.open_document(doc_id, READ_ONLY, CONFLICT_COPY)

# Now retrieve_contents will work
text = session.retrieve_contents(link_specset)
```

## Relationship to Finding 010

This is another case of the unified storage abstraction requiring caller awareness:
- `find_links` works with just I-address overlap (no document handle needed)
- `follow_link` returns document references (no content retrieval)
- `retrieve_contents` requires open document handles

The FEBE protocol assumes the caller manages document lifecycle correctly.

## Test Impact

Test scenarios that call `retrieve_contents` on `follow_link` results must ensure the source/target documents remain open or are reopened before retrieval.

## Recommendation

Golden tests should document this behavior explicitly:
- When link source is in a different document than the search context
- The source document must be open to retrieve link source text
- This is protocol-correct behavior, not a bug
