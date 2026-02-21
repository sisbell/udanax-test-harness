# Finding 0027: Insertion Order Semantics

**Date:** 2026-01-31
**Category:** Content Operations
**Test:** `edgecases/multiple_inserts_same_position`

## Summary

When multiple inserts are performed at the same position, new text is inserted **before** existing text at that position. This creates a LIFO (last-in-first-out) ordering.

## Test Scenario

```python
session.insert(opened, Address(1, 1), ["First"])   # → "First"
session.insert(opened, Address(1, 1), ["Second"])  # → "SecondFirst"
session.insert(opened, Address(1, 1), ["Third"])   # → "ThirdSecondFirst"
```

## Observed Behavior

| Operation | Position | Text | Result |
|-----------|----------|------|--------|
| Insert 1 | 1.1 | "First" | "First" |
| Insert 2 | 1.1 | "Second" | "SecondFirst" |
| Insert 3 | 1.1 | "Third" | "ThirdSecondFirst" |

## Implications

1. **Prepend Semantics**
   - Insert at position N means "insert before character N"
   - Not "insert after character N-1"

2. **Consistent with Text Editing**
   - Cursor at position 1 → typing inserts before existing text
   - This matches typical text editor behavior

3. **Important for Transclusion**
   - When transcluding to a position, the transcluded content appears before any existing content at that position
   - Sequential transclusions to same position will appear in reverse order

## Architectural Significance

This behavior is fundamental to understanding V-stream address semantics:
- Positions identify points between characters
- Position 1 is before the first character
- Insert at position 1 always prepends

## Related Findings

- Finding 0016: Rearrange operations
- Finding 0002: Transclusion content identity
