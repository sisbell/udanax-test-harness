# Finding 006: FEBE protocol and client bugs

**Date discovered:** 2026-01-30
**Category:** Protocol / Client implementation

## Summary

Discoveries about the FEBE protocol and Python client made while investigating Bug 008. These client-side bugs caused test failures that were initially misattributed to backend issues.

## FEBE Command Semantics

### Command 3: REARRANGE
- **Purpose**: Rearrange content within a document (pivot or swap operations)
- **NOT for deletion** - despite the name "rearrange"
- **Expects 3 or 4 cuts**:
  - 3 cuts = pivot operation (`pivot(doc, start, pivot, end)`)
  - 4 cuts = swap operation (`swap(doc, starta, enda, startb, endb)`)
- **Aborts with "Wrong number of cuts"** if given 2 cuts

### Command 12: DELETEVSPAN
- **Purpose**: Delete content from a document
- **Takes a vspan** (start address + width offset)
- Use this for all deletion operations

### Correct Client Usage
```python
# For deletion - use remove() or delete()
session.remove(docid, Span(Address(1, 1), Offset(0, 10)))
session.delete(docid, Address(1, 1), Offset(0, 10))  # constructs Span internally

# For rearrangement - use pivot() or swap()
session.pivot(docid, start, pivot, end)
session.swap(docid, starta, enda, startb, endb)
```

## Document Handle Constraints

### Cannot Open Same Document Twice
- Backend returns error if you try to open a document that's already open
- Even with different modes (e.g., READ_WRITE then READ_ONLY)
- **Workaround**: Use the existing handle, or close before reopening

### Handle Requirements by Operation
- `vcopy`: Can use READ_WRITE handle as source (doesn't require READ_ONLY)
- `retrieve_vspanset`: Works with any open handle
- `retrieve_contents`: Requires SpecSet, not raw VSpec

## API Type Requirements

### retrieve_contents() Requires SpecSet
```python
# WRONG - causes malformed protocol input
session.retrieve_contents(vspanset)  # VSpanSet is not SpecSet

# CORRECT
session.retrieve_contents(SpecSet(VSpec(docid, list(vspanset.spans))))
```

### SpecSet vs VSpec
- `VSpec`: Document-local specification (docid + list of spans)
- `SpecSet`: Protocol-level container that wraps one or more VSpecs
- Most FEBE operations expect SpecSet at the protocol level

## Known Backend Bugs

### compare_versions() Crash with Links
- `compare_versions()` crashes the backend when comparing documents that contain links
- Abort occurs during the comparison operation
- Workaround: Avoid comparing documents with links until fixed

### Debug Output
- Backend stderr shows internal operations:
  - `xgrabmorecore` - memory allocation
  - `levelpush/splitcrumupwards` - enfilade operations
  - `addtoopen` - document handle tracking
  - `INSERTENDSETSINORGL` - link creation
- These can help diagnose issues when operations fail

## Testing Notes

### Golden Test Generator
- Run with `python generate_golden.py` for all scenarios
- Run with `python generate_golden.py --scenario <category>` for specific category
- Backend stderr goes to file when using `2>backenderror` redirect
- Test failures show as "ERROR:" in output, success shows "ok"

### Debug Test Scripts
- Located in `tests/debug/`
- Useful for isolating specific operations
- Print backend error log at end for debugging
