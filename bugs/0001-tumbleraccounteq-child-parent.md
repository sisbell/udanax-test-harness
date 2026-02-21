# Bug 0001: tumbleraccounteq fails for child/parent address comparison

**Date discovered:** 2026-01-29
**Status:** Fixed
**Severity:** High - blocks version creation and document operations

## Summary

`tumbleraccounteq` in `tumble.c` fails when comparing a child address against its parent account, causing `isthisusersdocument` to incorrectly reject documents that belong to the user.

## Symptoms

- `create_version` operation fails with error response
- `open_document` fails for version documents
- `isthisusersdocument` returns FALSE for valid user documents

## Root Cause

The function compares mantissa arrays byte-by-byte and returns FALSE on any mismatch. It only terminates early when finding two zeros in `aptr` (the document).

When comparing:
- Account `0.1.1.0.1~` with mantissa `[1, 1, 0, 1, 0, 0, ...]`
- Document `0.1.1.0.1.1~` with mantissa `[1, 1, 0, 1, 1, 0, 0, ...]`

At position 4: account has `0` (boundary), document has `1` (sub-address). Mismatch detected before recognizing the account has terminated.

## Original Code

```c
bool tumbleraccounteq(tumbler *aptr, tumbler *bptr)
{
  INT i, j;

    if (aptr->exp != bptr->exp || aptr->sign != bptr->sign) {
        return(FALSE);
    }
    for (j = 0, i = 0; i < NPLACES; i++) {
        if (aptr->mantissa[i] != bptr->mantissa[i]) {
            return(FALSE);  // BUG: mismatch before account termination
        }
        if (aptr->mantissa[i] == 0 && ++j == 2) {
            return(TRUE);
        }
    }
    return (TRUE);
}
```

## Fix

Check for account termination (zeros in `bptr`) BEFORE checking for mismatch. When the account has a zero, the document can have any value there - it's extending into sub-address space.

```c
for (j_b = 0, i = 0; i < NPLACES; i++) {
    if (bptr->mantissa[i] == 0) {
        if (++j_b == 2) {
            return(TRUE);  // Account terminated, document is under this account
        }
        // First zero - document can continue, skip mismatch check
    } else {
        if (aptr->mantissa[i] != bptr->mantissa[i]) {
            return(FALSE);
        }
    }
}
```

## Files Changed

- `backend/tumble.c` - tumbleraccounteq function

## Test Case

```python
# create_version scenario in generate_golden.py
docid = session.create_document()
session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
session.insert(docid, Address(1, 1), ["Original text"])
session.close_document(docid)
version_docid = session.create_version(docid)  # Creates child address
session.open_document(version_docid, READ_WRITE, CONFLICT_FAIL)  # FAILS without fix
```

## Related

- Bug 0002: BERTMODEONLY openState handling
- Bug 0003: docreatenewversion doopen failure
