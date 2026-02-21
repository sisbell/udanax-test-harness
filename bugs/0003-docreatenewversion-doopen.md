# Bug 0003: docreatenewversion internal doopen fails

**Date discovered:** 2026-01-29
**Status:** Fixed
**Severity:** High - causes abort trap on create_version

## Summary

In `docreatenewversion()`, the internal `doopen()` call fails for the newly created document, triggering `gerror()` which calls `abort()`.

## Symptoms

- `create_version` causes "Abort trap: 6"
- Backend crashes during version creation

## Root Cause

After creating a new document via `createorglingranf()`, the code calls:

```c
doopen(taskptr, newisaptr, &newtp, WRITEBERT, BERTMODEONLY, user)
```

This fails because:
1. The new document isn't in the bert table yet
2. `checkforopen()` returns -1 (before Bug 0001 fix) or 0 (after)
3. `BERTMODEONLY` with `type == WRITEBERT` always returned 0 (failure)
4. Failure triggers `gerror()` → `abort()`

## Original Code

```c
if (!doopen(taskptr, newisaptr, &newtp, WRITEBERT, BERTMODEONLY, user)) {
    gerror("Couldn't do internal doopen for new doc in docreatenewversion\n");
}
```

## Fix

Bypass `doopen()` entirely for internally created documents. Since we just created the document, we know we own it. Call `addtoopen()` directly.

```c
/* Skip doopen ownership check - we just created this document so we own it.
   Add directly to bert table instead. */
addtoopen(newisaptr, user, TRUE, WRITEBERT);
```

## Files Changed

- `backend/do1.c` - docreatenewversion function
- `backend/protos.h` - added addtoopen prototype

## Why Not Fix doopen Instead?

The `doopen()` path involves ownership checks that don't make sense for internally-created documents:
- `checkforopen()` checks if document is in bert table
- `isthisusersdocument()` compares against user account
- For a brand new document, these checks are unnecessary

Directly calling `addtoopen()` is cleaner and more correct for this use case.

## Related

- Bug 0001: tumbleraccounteq child/parent comparison
- Bug 0002: BERTMODEONLY openState handling
