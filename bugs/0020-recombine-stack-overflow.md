# Bug 0020: Stack buffer overflow in recombinend when spanfilade has MAXUCINLOAF sons

## Status: Fixed

## Summary

When a 2D enfilade node (SPAN or POOM type) accumulates exactly MAXUCINLOAF (6)
children — the maximum valid count — `recombinend()` overflows a stack buffer by
one pointer, corrupting the caller's stack frame. The backend aborts on return
from `recombine()`, typically during `create_version` on documents that have
undergone multiple inserts, links, and versions.

## Reproduction

```python
doc1 = session.create_document()
opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)

# Build up enough state to get 6 children in the spanfilade
session.insert(opened1, Address(1, 1), ["AAA"])
link1 = session.create_link(opened1, link_from, link_to, link_type)
session.close_document(opened1)
ver1 = session.create_version(doc1)

opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
session.remove(opened1, Span(Address(1, 2), Offset(0, 1)))
session.insert(opened1, Address(1, 3), ["BBB"])

# Copy to another doc, add another link
doc2 = session.create_document()
opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
session.vcopy(opened2, Address(1, 1), copy_spec)
link2 = session.create_link(opened1, link2_from, link2_to, link_type)

# This create_version triggers the abort
session.close_document(opened1)
ver2 = session.create_version(doc1)  # CRASH: Abort trap 6
```

The `all_operations_interleaved` scenario in `allocation_independence.py`
reproduces this reliably.

## Root Cause

Off-by-one buffer overflow in `getorderedsons()` / `recombinend()`.

### The overflow

`getorderedsons()` (`recombine.c:278`) fills a caller-provided array and
appends a NULL sentinel:

```c
int getorderedsons(typecuc *father, typecorecrum *sons[])
{
    ...
    for (ptr = getleftson(father), i = 0; ptr; ptr = getrightbro(ptr))
        sons[i++] = ptr;
    sons[i] = NULL;   // sentinel write
    shellsort(sons, i);
}
```

Both callers declare the array with exactly MAXUCINLOAF elements:

```c
// recombinend():
typecorecrum *sons[MAXUCINLOAF];  // sons[0..5]

// takeovernephewsnd():
typecorecrum *sons[MAXUCINLOAF];  // sons[0..5]
```

`MAXUCINLOAF` is 6 (`enf.h:26`). A node with 6 children is valid — it's the
maximum before `splitcrumupwards` fires (which triggers at > 6). When
`numberofsons == 6`, `getorderedsons` fills `sons[0]` through `sons[5]`, then
writes `sons[6] = NULL` — one element past the array bounds.

### Why it's hard to trigger

The spanfilade needs exactly 6 children at height 2. This only happens after
enough operations to cause tree splits and rebalancing. A simple
insert-retrieve-insert cycle won't do it — the tree needs multiple inserts,
link creations, versions, and copies to accumulate enough bottom crums.

### Why the crash is delayed

The NULL write at `sons[6]` overwrites whatever follows the array on the stack
(likely the `i` or `j` loop variable, or saved frame data). The corruption
doesn't always cause an immediate crash — `recombinend` may complete its work
with corrupted local variables. The abort occurs when the corrupted stack frame
is unwound on function return, or when macOS's heap allocator detects the
damage during a subsequent `malloc`/`free`.

The symptom is SIGABRT ("Abort trap: 6") with no error message from `gerror`,
since the crash comes from the runtime, not from a code-level assertion.

## Fix

In `recombine.c`, increase both `sons` arrays by one element to accommodate
the NULL sentinel:

```c
// recombinend():
typecorecrum *sons[MAXUCINLOAF + 1]; /* +1 for NULL sentinel from getorderedsons */

// takeovernephewsnd():
typecorecrum *sons[MAXUCINLOAF + 1]; /* +1 for NULL sentinel from getorderedsons */
```

## Affected Operations

Any operation that triggers `recombine()` on a spanfilade with 6 children:

- `create_version` (copies content via `docopyinternal` → `insertspanf` → `insertnd`)
- `insert` (via `insertnd` → `recombine`)
- `create_link` (inserts endsets via `insertspanf`)
- `vcopy` (via `docopyinternal`)

The specific trigger is the tree having accumulated enough structure (through
prior inserts, deletes, links, and versions) that the spanfilade has 6 children
at height >= 2.

## Relationship to Other Bugs

- **Bug 0006** (crash on 6th link) — may have been this same underlying bug.
  The 6th link would be the operation that pushes the spanfilade to 6 children,
  triggering the overflow during recombine.
- **Bug 0009** (compare versions crashes with links) — the version+links
  combination is exactly the pattern that accumulates enough spanfilade children
  to trigger this overflow.
- **Bug 0012** (deep version chain crash) — deep version chains create multiple
  copies, each adding children to the spanfilade, making 6 children inevitable.

## Investigation Method

1. Added `fprintf(stderr, "TRACE: ...")` to `fns.c`, `do1.c`, `insertnd.c`,
   `spanf1.c`, `recombine.c` to trace the call chain
2. Discovered stderr was redirected to `backenderror` file by
   `freopen("backenderror", "w", stderr)` in `be.c:71`
3. Traced crash to `insertspanf` → `insertnd` → `recombine` → `recombinend`
4. Observed `recombinend` completing ("done" printed with `fflush`) but
   `insertnd` never resuming after `recombine()` returns
5. Identified the off-by-one: `sons[MAXUCINLOAF]` + `sons[i] = NULL` where
   `i == MAXUCINLOAF`
6. Confirmed fix: 1123/1123 tests pass after changing to `sons[MAXUCINLOAF + 1]`

## Tests

- `febe/scenarios/allocation_independence.py::scenario_all_operations_interleaved`
  (was aborting, now passes)
