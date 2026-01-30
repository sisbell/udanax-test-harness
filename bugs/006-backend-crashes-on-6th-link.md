# Bug 006: Backend crashes when creating 6th link in a document

**Date discovered:** 2026-01-30
**Status:** Open
**Severity:** High - backend crash (abort trap)

## Summary

The backend crashes with an abort trap when creating the 6th link in a document. This is a backend bug unrelated to link type address format - it occurs with both malformed and correct addresses.

## Reproduction

```python
# With LINK_DOCID = Address(1, 1, 0, 1, 0, 2) (doc 2):
# Links 1-5: OK
# Link 6: CRASH (abort trap)

# With LINK_DOCID = Address(1, 1, 0, 1, 0, 1) (doc 1 = link home):
# Links 1-3: OK
# Link 4: CRASH (abort trap)
```

## Test Case

```python
from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL, JUMP_TYPE
)

session = XuSession(XuConn(PipeStream("backend --test-mode")))
session.account(Address(1, 1, 0, 1))

doc1 = session.create_document()
opened = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
session.insert(opened, Address(1, 1), ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

doc2 = session.create_document()
target = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
session.insert(target, Address(1, 1), ["Target text"])

# Create 6 links - crashes on the 6th
for i in range(1, 7):
    source = SpecSet(VSpec(opened, [Span(Address(1, i), Offset(0, 1))]))
    tgt = SpecSet(VSpec(target, [Span(Address(1, 1), Offset(0, 1))]))
    link = session.create_link(opened, source, tgt, SpecSet([JUMP_TYPE]))
    # Link 6 crashes with: Abort trap: 6
```

## Observations

| LINK_DOCID points to | Links before crash |
|---------------------|-------------------|
| Doc 1 (link home)   | 3 (crash on 4th)  |
| Doc 2 (target)      | 5 (crash on 6th)  |
| Doc 3 (separate)    | 5 (crash on 6th)  |

The crash threshold depends on which document the malformed type specset references. When it references the same document where links are being created (doc 1), the threshold is lower.

## Why Golden Tests Pass

Current golden tests create at most 4 links per document:
- `overlapping_links`: 4 links
- `multiple_links_same_doc`: 3 links
- `link_types`: 3 links

With LINK_DOCID = doc 2 (pyxi default), 5 links work, so tests pass.

## Root Cause (Hypothesis)

The malformed type addresses (`Address(2, 1)` within the type document) may be interpreted by the backend in unexpected ways, possibly as link subspace references. This could cause:
- Memory corruption after N links
- Index overflow in link tracking structures
- Collision between link addresses and type address interpretation

## Impact

- Cannot create more than 5 links per document with pyxi
- Backend instability with malformed addresses
- Potential data corruption before crash

## Fix

1. Fix pyxi's link type addresses (Bug 005) - use proper element addresses
2. Investigate backend to understand why malformed addresses cause crash
3. Consider adding validation to reject malformed type specsets

## Files

- `febe/client.py` - LINK_DOCID and type constants (Bug 005)
- Backend link creation code - crash location unknown
