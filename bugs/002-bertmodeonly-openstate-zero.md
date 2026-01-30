# Bug 002: BERTMODEONLY doesn't handle openState==0

**Date discovered:** 2026-01-29
**Status:** Fixed
**Severity:** Medium - affects document opening after tumbleraccounteq fix

## Summary

The `BERTMODEONLY` case in `doopen()` doesn't properly handle `openState==0` (document not yet in bert table but can be opened). After fixing Bug 001, this case is reached but not handled.

## Symptoms

- Documents that pass `isthisusersdocument` check fail to open
- `open_document` returns error for valid documents

## Root Cause

When `checkforopen()` returns 0 (document not open, but user owns it), the `BERTMODEONLY` case only handled:
- `openState == -1` (needs new version) → return 0
- `openState == WRITEBERT` (already open for write) → return 0
- else → `incrementopen()` (assumes already in table)

But `incrementopen()` fails silently when document isn't in bert table yet.

## Original Code

```c
case BERTMODEONLY:
    if (openState == -1 || type == WRITEBERT || openState == WRITEBERT) {
        return 0;
    } else {
        incrementopen(tp, connection);  // BUG: assumes already in table
        tumblercopy(tp, newtp);
        return 1;
    }
```

Note: The `type == WRITEBERT` condition was also problematic - it caused ALL write opens to fail.

## Fix

Add explicit handling for `openState == 0`: call `addtoopen()` to register the document.

```c
case BERTMODEONLY:
    if (openState == -1 || openState == WRITEBERT) {
        return 0;
    } else if (openState == 0) {
        addtoopen(tp, connection, FALSE, type);  // Add new entry
        tumblercopy(tp, newtp);
        return 1;
    } else {
        incrementopen(tp, connection);  // Increment existing
        tumblercopy(tp, newtp);
        return 1;
    }
```

## Files Changed

- `backend/bert.c` - doopen BERTMODEONLY case

## Related

- Bug 001: tumbleraccounteq child/parent comparison
- Bug 003: docreatenewversion doopen failure
