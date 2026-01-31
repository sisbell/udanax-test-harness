# Finding 020: Internal (Self-Referential) Links Are Supported

**Date discovered:** 2026-01-30
**Category:** Feature discovery

## Summary

Internal links where both source and target are within the same document ARE supported by the backend, contrary to earlier assumptions.

## Evidence

Test `links/self_referential_link` demonstrates:

```json
{
  "op": "create_link",
  "home_doc": "1.1.0.1.0.1",
  "source_text": "glossary",
  "target_text": "Glossary",
  "same_document": true,
  "type": "jump",
  "result": "1.1.0.1.0.1.0.2.1",
  "success": true
}
```

The link can be followed in both directions:
- `follow_link(..., "target")` returns "Glossary"
- `follow_link(..., "source")` returns "glossary"

## Semantic Implications

1. **Navigation within documents**: Users can create internal cross-references (e.g., "see glossary" links to glossary section)

2. **Self-annotation**: A document can have links from text to annotations about that text within the same document

3. **No cross-document requirement**: Links are more general than previously documented

## Previous Understanding

The comment in `scenario_bidirectional_links` incorrectly stated:
> "Internal links (source and target in same document) are NOT supported by the backend - it returns an error."

This has been corrected.

## Related Tests

- `links/self_referential_link` - Internal link creation and traversal
- `links/link_chain` - Shows intermediate nodes can be both targets and sources
- `links/overlapping_links_different_targets` - Same span can have multiple links
