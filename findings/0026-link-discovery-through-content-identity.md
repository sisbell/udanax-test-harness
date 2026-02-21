# Finding 0026: Link Discovery Through Content Identity

**Date:** 2026-01-31
**Category:** Links / Content Identity
**Test:** `links/link_to_transcluded_content`

## Summary

When a link targets transcluded content, `find_links` discovers it through **both** the document containing the transclusion **and** the original source document. This validates that Xanadu's content identity model extends to link discovery.

## Test Scenario

```
Document B: "Source content in B: important text here"
Document A: "A contains: " + vcopy("important text" from B)
Document C: "C references: see the important text"

Link: C's "important text" → A's transcluded "important text"
```

## Observed Behavior

| Query | Result |
|-------|--------|
| `find_links(target=A's transcluded content)` | Found link |
| `find_links(target=B's original content)` | **Also found link** |

The same link appears in both queries because A's transcluded content shares identity with B's original content.

## Implications

1. **Content Identity Is Preserved Across Links**
   - Links follow content, not just document/position
   - A link to transcluded content is discoverable from the original source

2. **Transitive Discovery**
   - If A transcludes from B, and C links to A's copy, searching B finds the link
   - This enables powerful "where is this content referenced?" queries

3. **Semantic Linking**
   - Links attach to content meaning, not just location
   - Moving or copying content preserves its link relationships

## Architectural Significance

This behavior is fundamental to Xanadu's vision:
- **Transclusion** preserves content identity
- **Links** attach to content identity, not document position
- **Discovery** works through the identity graph

This means you can ask "what links to this content?" and get answers regardless of how many times the content has been transcluded.

## Related Findings

- Finding 0002: Transclusion content identity is immutable
- Finding 0018: Content identity tracking mechanisms
- Finding 0004: Link endpoint semantics

## Test Evidence

From `golden/links/link_to_transcluded_content.json`:

```json
{
  "op": "find_links",
  "to": "B's original content",
  "result": ["1.1.0.1.0.3.0.2.1"],
  "comment": "Does link to A's transcluded content appear when searching B?"
}
```

The link (created pointing to A) appears when searching B's original content.

## Additional Patterns Tested

The same session tested several complex link topologies:

| Pattern | Description | Links | Result |
|---------|-------------|-------|--------|
| Circular | A → B → C → A | 3 | Works |
| Diamond | A → B, A → C, B → D, C → D | 4 | Works |
| Star (incoming) | P1, P2, P3 → Hub | 3 | Works |
| Star (outgoing) | Hub → P1, P2, P3 | 3 | Works |
| Bidirectional | A ⟷ B | 2 | Works |
| Reverse traversal | Find path D ← C ← B ← A | 3 | Works |

All patterns confirm that link discovery correctly follows content identity relationships.
