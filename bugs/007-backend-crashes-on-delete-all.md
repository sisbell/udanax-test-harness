# Bug 007: Backend crashes when deleting all content

## Status: Open

## Summary
The backend crashes (Abort trap: 6) when attempting to delete all content from a document.

## Reproduction
```python
docid = session.create_document()
opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
session.insert(opened_docid, Address(1, 1), ["Content to delete"])  # 17 chars
session.remove(opened_docid, Span(Address(1, 1), Offset(0, 17)))  # CRASH
```

## Expected Behavior
Deleting all content should result in an empty document, not a crash.

## Actual Behavior
Backend process terminates with "Abort trap: 6".

## Notes
- This appears to be a separate bug from Bug 006 (link crash)
- The backend doesn't handle edge case of removing the entire vspan
- May be related to enfilade becoming empty/invalid after deletion

## Workaround
Don't delete all content from a document in a single operation.

## Test
`febe/scenarios/content.py::scenario_delete_all` (currently causes crash)
