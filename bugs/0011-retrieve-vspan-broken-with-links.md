# Bug 0011: retrieve_vspan returns invalid span for documents with links

**Date:** 2026-01-30
**Severity:** Medium
**Status:** Closed (workaround: use retrieve_vspanset instead)

## Summary

`RETRIEVEDOCVSPAN` (opcode 14) returns meaningless values when a document contains links. The implementation copies raw internal V-dimension values without handling the dual subspace structure (0.x for links, 1.x for text).

## Reproduction

```python
doc = session.create_document()
opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

# Insert text (10 chars)
session.insert(opened, Address(1, 1), ["Click here"])

# Create a link
link_source = SpecSet(VSpec(opened, [Span(Address(1, 7), Offset(0, 4))]))
link_target = SpecSet(VSpec(target, [Span(Address(1, 1), Offset(0, 6))]))
session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))

# Compare results
vspan = session.retrieve_vspan(opened)      # Returns: 1.1 for 1.2 (WRONG)
vspanset = session.retrieve_vspanset(opened) # Returns: [{0, 0.1}, {1, 1}] (CORRECT)
```

## Expected Behavior

For a document with 10 characters of text and 1 link, `retrieve_vspan` should return either:
- **Option A:** Text span only: `1.1 for 0.10`
- **Option B:** Error/indication that document has multiple subspaces

## Actual Behavior

Returns `1.1 for 1.2` which:
- Doesn't match text length (10 chars ≠ width 1.2)
- Doesn't include link subspace (0.x)
- Is the raw internal `cwid.dsas[V]` value, not a valid extent

## Root Cause

In `backend/orglinks.c`, the two functions differ:

**retrievevspanpm (broken)** - lines 165-172:
```c
bool retrievevspanpm(typetask *taskptr, typeorgl orgl, typevspan *vspanptr)
{
    vspanptr->next = NULL;
    vspanptr->itemid = VSPANID;
    movetumbler (&((typecuc *) orgl)->cdsp.dsas[V], &vspanptr->stream);
    movetumbler (&((typecuc *) orgl)->cwid.dsas[V], &vspanptr->width);
    return (TRUE);
}
```

Just copies raw internal values. No handling for links.

**retrievevspansetpm (correct)** - lines 173-221:
```c
if (is1story (&ccptr->cwid.dsas[V])) {
    // Simple case: just text - return one span
} else {
    // Complex case: has links
    // Extract link span (0.x) using maxtextwid()
    // Return TWO separate spans
}
```

Detects links with `is1story()` check and handles them specially.

## Proposed Fix

Modify `retrievevspanpm` to return the text span only:

```c
bool retrievevspanpm(typetask *taskptr, typeorgl orgl, typevspan *vspanptr)
{
    typecorecrum *ccptr = (typecorecrum *) orgl;
    tumbler voffset;
    tumbler maxwid;

    vspanptr->next = NULL;
    vspanptr->itemid = VSPANID;

    if (is1story(&ccptr->cwid.dsas[V])) {
        // Simple case: just text
        movetumbler(&ccptr->cdsp.dsas[V], &vspanptr->stream);
        movetumbler(&ccptr->cwid.dsas[V], &vspanptr->width);
    } else {
        // Has links: return text span only (1.x subspace)
        tumblerclear(&voffset);
        maxtextwid(taskptr, ccptr, &voffset, &maxwid);
        tumblerclear(&vspanptr->stream);
        movetumbler(&maxwid, &vspanptr->width);
        vspanptr->width.mantissa[0] = 0;  // Remove first digit
    }
    return TRUE;
}
```

## Spec Ambiguity

Literary Machines says RETRIEVEDOCVSPAN:
> "Returns a span determining the origin and extent of the V-stream of the document."

But doesn't define "V-stream" for documents with multiple subspaces. RETRIEVEDOCVSPANSET explicitly mentions "text and links" - implying VSPAN was meant for the simple (text-only) case.

## Workaround

Always use `retrieve_vspanset()` instead of `retrieve_vspan()`.

## Test Coverage

- `golden/documents/retrieve_vspan.json` - text only (works)
- `golden/documents/retrieve_vspan_with_links.json` - exposes bug

## Related

- **Finding 0009**: Document address space structure
- **Finding 0017**: vspan vs vspanset differences
- **Bug 0010**: No V-position validation (related subspace issue)
