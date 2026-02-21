# Finding 0023: find_documents Returns Deleted Content

## Summary

When content is deleted from a document, `find_documents` **still reports that document** as containing the content. Deletion does not remove content identity association.

## Evidence

From `golden/discovery/find_documents_after_delete.json`:

```
Source: "Findable content"
Dest: "Prefix: " + vcopy("Findable") → "Prefix: Findable"

Before delete:
  find_documents("Findable") → [source, dest]  ✓ Expected: 2 documents

After delete("Findable" from dest):
  Dest contents: "Prefix: "  (Findable is gone)
  find_documents("Findable") → [source, dest]  ✗ Expected: 1, Got: 2
```

## Interpretation

The backend's content discovery mechanism tracks content identity at the **address space level**, not the **current content level**. This means:

1. **Content identity is permanent** - Once content is placed at an address, that address permanently associates with the content's I-stream identity
2. **Deletion removes content from V-stream** - The document no longer displays the content
3. **Deletion does NOT remove content from I-stream** - The historical association remains

This aligns with Xanadu's philosophy of **permanent storage** - nothing is ever truly deleted, only hidden from the current view.

## Implications

1. **`find_documents` is NOT a "current content" search** - It's a "content identity ever existed here" search
2. **For current-content search**, use `retrieve_contents` and compare
3. **Documents accumulate content identity** over time through edits
4. **Privacy implications** - Even deleted content leaves traces discoverable via `find_documents`

## Related

- Finding 0018: Content Identity Tracking
- Finding 0013: SPORGL Provenance Tracking
- The I-stream vs V-stream distinction in enfilade architecture
