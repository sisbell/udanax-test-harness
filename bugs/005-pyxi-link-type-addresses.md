# Bug 005: pyxi has malformed link type addresses

**Date discovered:** 2026-01-29
**Status:** Fixed
**Severity:** High - link type addressing was fundamentally incorrect

## Summary

The pyxi client (`client.py`) uses malformed tumbler addresses for link types. The addresses are missing the element field separator, making them document addresses rather than element addresses.

## The Problem

```python
# What pyxi has (wrong):
LINK_DOCID = Address(1, 1, 0, 1, 0, 2)  # This is just "document 2"

JUMP_TYPE = VSpec(LINK_DOCID, [Span(Address(2, 1), Offset(0, 1))])
```

The address `1.1.0.1.0.2` is missing the element field. Proper tumbler structure:

```
1.1.0.1.0.1.0.2.1
───  ─  ─  ─  ─
Node.0.User.0.Doc.0.Element
     │      │     │
     └──────┴─────┴── Field separators
```

So `1.1.0.1.0.2` is just "document 2 under account 1.1.0.1" - there's no element address at all.

## What Link Types Should Be

Link types should reference actual link elements within a document:

```python
# Conceptually correct (actual format TBD):
# Document 1, version 1, link 1
Address(1, 1, 0, 1, 0, 1, 1, 0, 2, 1)
#       ───  ─  ─  ─  ─  ─  ─  ─  ─
#       Node.0.User.0.Doc.Ver.0.Link
```

Or the type system may work differently - this needs investigation of the original Xanadu specification.

## Why It "Works"

Current tests pass because:
1. We create document 2 (`1.1.0.1.0.2`)
2. The backend accepts the malformed type specset
3. The backend may be lenient or treating it as "anything in document 2"

But this is accidental, not correct behavior.

## Impact

- Cannot rely on pyxi for accurate link golden tests
- Link type semantics are unclear/wrong
- May cause issues with link queries that filter by type

## Options

1. **Fix pyxi** - Correct the address format to proper element addresses
2. **Build fresh** - Implement correct link handling in test harness
3. **Research first** - Find original Xanadu docs on link type addressing

## Related

- `febe/client.py` lines 597-602 - Link type definitions
- FEBE protocol MAKELINK (opcode 4) - uses `<three set>` for type
- Literary Machines - original link specification
