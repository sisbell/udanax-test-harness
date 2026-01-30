# Bug 007: Backend crashes when deleting all content

## Status: Fixed

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
`febe/scenarios/content.py::scenario_delete_all`

## Fix
Two changes were required:

1. **wisp.c:185-194** - `setwispnd()` was calling `gerror()` (which aborts) when
   `findleftson(father)` returned NULL after all children were deleted. Fixed by
   removing the abort and properly clearing the dsp/wid for the empty parent.

2. **do1.c:360-369** - `doretrievedocvspanset()` was failing on empty documents
   because of the `!isemptyorgl(docorgl)` check. Fixed by returning success with
   an empty vspanset (`*vspansetptr = NULL`) for empty documents instead of failing.
