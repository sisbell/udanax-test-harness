# Bug 017: Backend crashes on zero-width link endpoints

**Status:** Open
**Severity:** Medium
**Discovered:** 2026-01-31
**Test:** `edgecases/link_zero_width_endpoints`

## Summary

The backend crashes (Abort trap) when attempting to create a link with zero-width span endpoints.

## Reproduction

```python
doc = session.create_document()
opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
session.insert(opened, Address(1, 1), ["Source and Target"])

# Zero-width spans
from_span = Span(Address(1, 1), Offset(0, 0))
to_span = Span(Address(1, 8), Offset(0, 0))

from_specs = SpecSet(VSpec(opened, [from_span]))
to_specs = SpecSet(VSpec(opened, [to_span]))
type_specs = SpecSet(Span(Address(1, 1, 0, 1), Offset(0, 1)))

link_id = session.create_link(opened, from_specs, to_specs, type_specs)  # CRASH
```

## Expected Behavior

Either:
1. Reject the operation with an error (zero-width endpoints not allowed), or
2. Create a "point" link that attaches to a position rather than a span

## Actual Behavior

Backend crashes with signal SIGABRT (Abort trap: 6).

## Analysis

Zero-width spans are valid for retrieval operations (returns empty content), so the crash appears specific to link creation. The enfilade code may not handle zero-width spans correctly when creating link endpoints.

## Workaround

Ensure link endpoints have non-zero width before creating links.

## Related

- Finding 004: Link endpoint semantics
- The zero-width span works fine for `retrieve_contents` (returns empty list)
