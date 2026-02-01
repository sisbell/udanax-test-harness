# Bug 018: Backend crashes on large insert

**Status:** Open
**Severity:** High
**Discovered:** 2026-01-31
**Test:** `edgecases/large_insert`

## Summary

The backend crashes (Trace/BPT trap) when inserting approximately 10KB of text in a single operation.

## Reproduction

```python
docid = session.create_document()
opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

# Generate ~10KB of text
large_text = "X" * 10000

session.insert(opened, Address(1, 1), [large_text])  # CRASH
```

## Expected Behavior

Either:
1. Successfully insert the text, or
2. Return an error indicating size limit exceeded

## Actual Behavior

Backend crashes with signal SIGTRAP (Trace/BPT trap: 5).

Note: The same scenario with 100 single-character inserts (`many_small_inserts`) completes successfully, producing 100 characters total.

## Analysis

The crash suggests a buffer overflow or assertion failure in the enfilade code when handling large text blocks. The 1999 backend may have been designed for smaller text chunks typical of that era.

Possible causes:
1. Fixed-size buffer overflow
2. Stack overflow in recursive tree operations
3. Assertion failure on unexpected input size

## Workaround

Break large inserts into smaller chunks (< 10KB each).

## Testing Notes

The `many_small_inserts` test demonstrates that cumulative inserts work fine - the issue is specifically with single large insert operations.

## Related

- Bug 016: Link count limit causes crash (similar resource limit issue)
