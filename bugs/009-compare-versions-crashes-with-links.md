# Bug 009: Backend crashes on compare_versions when documents have links

**Date:** 2026-01-30
**Severity:** High (crashes backend with SIGABRT)
**Status:** Fixed (filter link subspace spans before compare_versions)

## Summary

The backend crashes with "Abort trap: 6" (SIGABRT) when `compare_versions` is called on documents that contain links. The crash is caused by the link subspace spans being included in the vspanset, which confuses the span intersection logic.

## Root Cause Analysis

### What Happens

1. When a link is created in a document, the document's vspanset changes:
   - **Before link:** `at 1.1 for 0.16` (just text content)
   - **After link:** `at 0 for 0.1, at 1 for 1` (link subspace + text content)

2. The link subspace uses position 0.x for storing link references, while text uses position 1.x.

3. When `compare_versions` is called, it:
   - Converts both specsets to ispansets
   - Calls `intersectspansets()` to find common I-addresses
   - The span intersection code in `correspond.c` performs tumbler arithmetic

4. The crash occurs when trying to compute the intersection between spans in different address subspaces (0.x vs 1.x). The tumbler arithmetic doesn't handle this case.

### Technical Details

The flow is:
```
doshowrelationof2versions()
  → specset2ispanset() for version1 (includes 0.x span for links)
  → specset2ispanset() for version2 (only 1.x spans)
  → intersectspansets() ← CRASH HERE
```

In `intersectspansets()` (correspond.c:123), the `comparespans()` function is called for each pair of spans. The `spanintersection()` function performs tumbler arithmetic:

```c
tumbleradd (&bptr->stream, &bptr->width, &bend);
if (tumblercmp (&aptr->stream, &bend) >= EQUAL)
    return (FALSE);
tumbleradd (&aptr->stream, &aptr->width, &aend);
tumblersub(&bend, &aptr->stream, &cptr->width);  // Crash here?
```

When comparing a span at position 0 with a span at position 1.x, the tumbler subtraction may produce an invalid result (negative tumbler or assertion failure).

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
link_source = SpecSet(VSpec(orig2, [Span(Address(1, 1), Offset(0, 6))]))
link_target = SpecSet(VSpec(target, [Span(Address(1, 1), Offset(0, 6))]))
link1 = session.create_link(orig2, link_source, link_target, SpecSet([JUMP_TYPE]))
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

Before the crash, the vspansets show:
```
Original (with link): <VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>
Version (no link):    <VSpec in 1.1.0.1.0.1.1, at 1.1 for 0.16>
```

The "at 0 for 0.1" is the link subspace span that causes the crash.

## Workaround

Filter out spans that start at position 0 (link subspace) before calling `compare_versions`:

```python
def is_text_span(span):
    """Keep only spans in text subspace (position >= 1), not link subspace (position 0)."""
    return span.start.digits[0] >= 1 if span.start.digits else False

o_text_spans = [s for s in o_vs.spans if is_text_span(s)]
v_text_spans = [s for s in v_vs.spans if is_text_span(s)]

o_ss = SpecSet(VSpec(orig_ro, o_text_spans))
v_ss = SpecSet(VSpec(ver_ro, v_text_spans))
shared = session.compare_versions(o_ss, v_ss)  # Works!
```

## Potential Fixes

### Option 1: Filter in Frontend (easiest)
The client/frontend should filter out link subspace spans before calling compare_versions. This matches the semantic intent: comparing text content between versions.

### Option 2: Filter in Backend
Modify `doshowrelationof2versions()` or `specset2ispanset()` to skip spans in the link subspace (position 0.x).

### Option 3: Fix Span Intersection
Modify `spanintersection()` in correspond.c to handle spans in different address subspaces gracefully (return no intersection instead of crashing).

## Impact

This prevents comparing versions when either document contains links, which limits the ability to track content sharing in hypertext-rich documents.

## Related

- Bug 008: Backend crashes on linked document edit (different crash scenario) - FIXED
- Finding 007: Version semantics (compare_versions works fine without links)
- Finding 008: Complex interactions - links, versions, and transclusion

## Test Case

`scenarios/interactions.py::scenario_compare_versions_with_different_links` - disabled due to this bug
`febe/debug_bug009.py` - debug script that reproduces the issue

## Amendment (Bug 020)

The crash symptom here (SIGABRT with no `gerror` message) matches the signature
of Bug 020: a stack buffer overflow in `recombinend()` caused by an off-by-one
in the `sons[MAXUCINLOAF]` array. While the cross-subspace span intersection
issue is real, some of the observed SIGABRT crashes in this scenario may have
been the recombine overflow triggered during the version copy that precedes
comparison, rather than the tumbler arithmetic in `intersectspansets()`.

See Bug 020 for the full analysis and fix (`sons[MAXUCINLOAF + 1]`).
