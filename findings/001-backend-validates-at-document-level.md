# Finding 001: Backend validates specsets at document level

**Date discovered:** 2026-01-29
**Category:** Tumbler validation / Specset handling

## Observation

When processing link type specsets, the backend validates that referenced documents exist but does not enforce element-level tumbler structure.

## Context: Tumbler Structure

Tumblers are just digit sequences - they have no inherent structure requirements. The `.0.` field dividers are a **docuverse convention** for addresses starting with `1`:

```
1.1.0.1.0.1.0.2.1
───  ─  ─  ─  ─
Node.0.User.0.Doc.0.Element  (docuverse convention)
```

But a tumbler like `1.1.0.1.0.2` is still a valid tumbler - it just represents a document, not an element within a document.

## Backend Behavior

The backend's `specset2sporglset()` performs docuverse-level validation:
- Checks if the referenced document exists
- Does not enforce element-level addressing

This is arguably correct - tumbler structure enforcement is not the backend's responsibility.

## Implication

Clients (like pyxi) must use correct element addresses. The backend won't catch malformed addresses as long as the document portion is valid.

```python
# pyxi uses (Bug 005):
VSpec(Address(1,1,0,1,0,2), [...])  # Document 2 - backend accepts if doc exists

# Should use:
VSpec(Address(1,1,0,1,0,1,0,2,N), [...])  # Document 1, link N
```

## Related

- Bug 005: pyxi link type addresses were malformed (now fixed)
- Tumbler semantics: structure is convention, not inherent
