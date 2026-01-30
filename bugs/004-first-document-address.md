# Bug 004: First document gets account address instead of document address

**Date discovered:** 2026-01-29
**Status:** Fixed
**Severity:** High - violates tumbler semantics, first document unusable as proper document

## Summary

The first document created under an account was assigned the account address itself (e.g., `1.1.0.1`) instead of a proper document address (e.g., `1.1.0.1.0.1`). This violates tumbler semantics where the `.0.` separator distinguishes field levels.

## Symptoms

- First document address equals the account address
- Document addresses don't follow tumbler format (missing `.0.` document field separator)
- Subsequent documents work correctly

```
Account: 1.1.0.1
Doc 1: 1.1.0.1      <- WRONG (this is the account!)
Doc 2: 1.1.0.1.0.1  <- correct
Doc 3: 1.1.0.1.0.2  <- correct
```

## Root Cause

In `granf2.c`, `findisatoinsertgr` calls a "kluge" function when `isaexistsgr` returns false (nothing exists at the account address):

```c
if (!isaexistsgr (fullcrumptr, &hintptr->hintisa)) {
    if(hintptr->subtype != ATOM){
        klugefindisatoinsertnonmolecule(fullcrumptr, hintptr, isaptr);
        ...
    }
}
```

The kluge function simply copied the hint address unchanged:

```c
static int klugefindisatoinsertnonmolecule(...) {
    tumblercopy(&hintptr->hintisa, isaptr);  // Just returns account address!
}
```

After the first document was created at the account address, `isaexistsgr` returned true (something now exists at that address), so subsequent documents correctly used `findisatoinsertnonmolecule`.

## Original Code

```c
bool findisatoinsertgr(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    if (!isaexistsgr (fullcrumptr, &hintptr->hintisa)) {
        if(hintptr->subtype != ATOM){
            klugefindisatoinsertnonmolecule(fullcrumptr, hintptr, isaptr);
            tumblerjustify(isaptr);
            return(TRUE);
        }
        return (FALSE);
    }
    if (hintptr->subtype == ATOM)
        findisatoinsertmolecule (fullcrumptr, hintptr, isaptr);
    else
        findisatoinsertnonmolecule (fullcrumptr, hintptr, isaptr);
    tumblerjustify(isaptr);
    return (TRUE);
}

static int klugefindisatoinsertnonmolecule(...) {
    tumblercopy(&hintptr->hintisa, isaptr);  // BUG: returns account address
}

static int findisatoinsertnonmolecule(...) {
    // ... uses findpreviousisagr but doesn't handle empty tree case
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);
    tumblertruncate (&lowerbound, hintlength + depth, isaptr);
    tumblerincrement(isaptr, ...);  // BUG: produces "1" when lowerbound is zero
}
```

## Fix

1. Always use `findisatoinsertnonmolecule` for non-ATOM types (documents, accounts, nodes)
2. Handle empty tree case in `findisatoinsertnonmolecule` - when nothing exists, create `hintisa.0.1`

```c
bool findisatoinsertgr(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    if (hintptr->subtype == ATOM) {
        if (!isaexistsgr (fullcrumptr, &hintptr->hintisa)) {
            return (FALSE);
        }
        findisatoinsertmolecule (fullcrumptr, hintptr, isaptr);
    } else {
        findisatoinsertnonmolecule (fullcrumptr, hintptr, isaptr);
    }
    tumblerjustify(isaptr);
    return (TRUE);
}

static int findisatoinsertnonmolecule(...) {
    // ...
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);

    if (iszerotumbler(&lowerbound)) {
        // Nothing exists yet - create first child as hintisa.0.1
        tumblerincrement(&hintptr->hintisa, depth, 1, isaptr);
    } else {
        tumblertruncate (&lowerbound, hintlength + depth, isaptr);
        tumblerincrement(isaptr, ...);
    }
}
```

## Files Changed

- `backend/granf2.c` - `findisatoinsertgr`, `findisatoinsertnonmolecule`

## Test Case

```python
acct = Address(1, 1, 0, 1)
session.account(acct)

doc1 = session.create_document()
# Before fix: 1.1.0.1 (account address)
# After fix:  1.1.0.1.0.1 (proper document address)

doc2 = session.create_document()
# Both before and after: 1.1.0.1.0.2 (correct)
```

## Related

- Tumbler semantics: `.0.` separates field levels (node, user, document, element)
- Bug 001, 002, 003: Other document/version operation fixes
