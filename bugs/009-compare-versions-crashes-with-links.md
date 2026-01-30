# Bug 009: Backend crashes on compare_versions when documents have links

**Date:** 2026-01-30
**Severity:** High (crashes backend)
**Status:** Open

## Summary

The backend crashes with "Abort trap: 6" when `compare_versions` is called on documents that contain links.

## Reproduction

```python
# Create original with content
original = session.create_document()
orig = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
session.insert(orig, Address(1, 1), ['Shared text'])
session.close_document(orig)

# Create version
version = session.create_version(original)

# Add link to original
target = session.create_document()
# ... insert target content ...
orig2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
link_s = SpecSet(VSpec(orig2, [Span(Address(1, 1), Offset(0, 6))]))
link_t = SpecSet(VSpec(target, [Span(Address(1, 1), Offset(0, 4))]))
link1 = session.create_link(orig2, link_s, link_t, SpecSet([JUMP_TYPE]))
session.close_document(orig2)

# This crashes:
orig_r = session.open_document(original, READ_ONLY, CONFLICT_COPY)
ver_r = session.open_document(version, READ_ONLY, CONFLICT_COPY)
o_vs = session.retrieve_vspanset(orig_r)
v_vs = session.retrieve_vspanset(ver_r)
o_ss = SpecSet(VSpec(orig_r, list(o_vs.spans)))
v_ss = SpecSet(VSpec(ver_r, list(v_vs.spans)))
shared = session.compare_versions(o_ss, v_ss)  # CRASH
```

## Observations

Before the crash, the vspanset of the document with links shows unusual structure:
```
Original vspanset: <VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>
```

This suggests the link is being included in the vspanset in an unexpected way (starting at position 0).

The version (which has no links) shows normal structure:
```
Version vspanset: <VSpec in 1.1.0.1.0.1.1, at 1.1 for 0.11>
```

## Error

```
/bin/sh: line 1: XXXXX Abort trap: 6  .../backend --test-mode < pyxi.XXXXX
```

## Workaround

Avoid calling `compare_versions` on documents that have links embedded in them.

## Impact

This prevents comparing versions when either document contains links, which limits the ability to track content sharing in hypertext-rich documents.

## Related

- Bug 008: Backend crashes on linked document edit (different crash scenario)
- Finding 007: Version semantics (compare_versions works fine without links)

## Test Case

`scenarios/interactions.py::scenario_compare_versions_with_different_links` - disabled due to this bug
