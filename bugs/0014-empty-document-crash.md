# Bug 0014: Backend Crashes During Empty Document Scenario

## Summary

The backend crashes (Abort trap: 6) during execution of the `find_documents_empty_document` test scenario.

## Reproduction

```python
# Create empty document (no insert)
empty = session.create_document()

# Create document with content
full = session.create_document()
full_opened = session.open_document(full, READ_WRITE, CONFLICT_FAIL)
session.insert(full_opened, Address(1, 1), ["Has content"])
session.close_document(full_opened)

# Open empty document and retrieve vspanset
empty_opened = session.open_document(empty, READ_ONLY, CONFLICT_COPY)
empty_vs = session.retrieve_vspanset(empty_opened)
# empty_vs.spans is empty list - no spans in empty document
```

## Error

```
/bin/sh: line 1: 66694 Abort trap: 6           /Users/shane/.../backend --test-mode < pyxi.66691
```

## Analysis

The crash occurs during the test scenario, though the exact trigger is unclear. The test code handles the "no spans" case before calling `find_documents`, so the crash may occur during:
- `open_document` on an empty document
- `retrieve_vspanset` on an empty document
- `close_document` sequence
- Some other operation in the scenario

## Workaround

The test scenario handles the empty case by not calling `find_documents` when there are no spans to search with.

## Status

Open - crash observed but exact trigger needs investigation.

## Test

`febe/scenarios/discovery.py::scenario_find_documents_empty_document`
