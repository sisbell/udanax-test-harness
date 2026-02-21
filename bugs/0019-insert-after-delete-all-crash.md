# Bug 0019: Backend crashes on INSERT/VCOPY after deleting all content

## Status: Fixed

## Summary

After deleting ALL content from a document (emptying the POOM enfilade), any
subsequent INSERT or VCOPY into that document crashes the backend. The crash
occurs not during the insert itself, but during the next `retrieve_contents`
call — the insert corrupts the tree structure silently.

## Reproduction

```python
docid = session.create_document()
opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
session.insert(opened, Address(1, 1), ["Hello"])

# Delete all content
vs = session.retrieve_vspanset(opened)
session.remove(opened, vs.spans[0])

# Re-insert — this succeeds but corrupts the tree
session.insert(opened, Address(1, 1), ["After"])

# Retrieve crashes the backend
vs2 = session.retrieve_vspanset(opened)  # OK
ss = SpecSet(VSpec(opened, list(vs2.spans)))
contents = session.retrieve_contents(ss)  # CRASH: Abort trap 6
```

## Root Cause

Two-part bug in `firstinsertionnd()` (`backend/insertnd.c`):

### Part 1: NULL pointer dereference

After delete-all, `disown()` + `subtreefree()` free all children from the POOM
fullcrum. `findleftson(father)` returns NULL. The original `firstinsertionnd()`
unconditionally used this pointer:

```c
ptr = findleftson(father);
movewisp(origin, &ptr->cdsp);  // NULL dereference
```

A never-filled document doesn't hit this because `createorglingranf` creates an
initial bottom crum during document creation. But an empty-after-delete document
has no children — different internal state despite both being "empty" to
`isemptyenfilade()`.

### Part 2: reserve/rejuvinate mismatch

The initial fix (creating a new bottom crum) called `reserve(ptr)` to protect
the crum from the grim reaper, matching the pattern in `insertcbcnd()`. But
`insertcbcnd()` pairs its `reserve()` with `rejuvinate()` at the end. Without
the matching `rejuvinate()`, the crum stays permanently locked at `age == RESERVED`.

Later, `makecontextfromcbc()` (in `context.c:158`) calls `reserve()` on every
bottom crum during retrieval. Finding the crum already RESERVED, it calls
`gerror("reserve already reserved")` → `abort()`.

## Fix

In `firstinsertionnd()` (`backend/insertnd.c:204-211`):

```c
ptr = findleftson(father);
if (!ptr) {
    /* Enfilade was emptied by delete-all — no bottom crum remains.
       Create a fresh one and adopt it. No reserve() needed here:
       makecontextfromcbc will reserve/rejuvinate during retrieval. */
    ptr = createcrum(0, (INT)father->cenftype);
    adopt(ptr, SON, (typecorecrum*)father);
}
```

`reserve()` is deliberately omitted. The crum doesn't need protection during
setup because `firstinsertionnd()` doesn't trigger the grim reaper (no
`splitcrumupwards`, no complex tree operations). The retrieval path handles its
own `reserve()`/`rejuvinate()` pairing in `makecontextfromcbc()`.

## Affected Operations

- INSERT into a fully-deleted document
- VCOPY (transclusion) into a fully-deleted document
- Incremental deletion to empty, then INSERT
- DELETE + re-COPY of same I-addresses

## Relationship to Other Bugs

- **Bug 0007** fixed the delete-all crash itself (in `setwispnd` and
  `doretrievedocvspanset`). This bug is the sequel: the empty-after-delete
  state now survives, but inserting back into it was broken.
- **Bug 0014** (empty document crash) is about never-filled documents, which
  have a different internal structure (bottom crum exists from `createorglingranf`).

## Tests

- `febe/scenarios/delete_all_content.py::scenario_delete_all_content_simple`
- `febe/scenarios/delete_all_content.py::scenario_delete_all_incrementally`
- `febe/scenarios/delete_all_content.py::scenario_delete_all_then_transclude`
- `febe/scenarios/provenance.py::scenario_delete_then_recopy`
- `febe/tests/debug/bug019_insert_after_delete_all.py` (minimal repro)
