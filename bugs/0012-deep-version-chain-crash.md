# Bug 0012: Backend crashes on deep version chains

**Date discovered:** 2026-01-30
**Severity:** Medium
**Status:** Fixed

## Summary

The backend crashes when creating or accessing version chains deeper than 3-4 levels. The root cause was tumbler overflow - document addresses for deep versions exceed the tumbler mantissa capacity, and struct padding bytes caused incorrect tumbler comparisons.

## Root Cause Analysis

The crash was caused by multiple interacting issues:

### 1. Tumbler mantissa overflow
- Document addresses grow with version depth: `1.1.0.1.0.1` -> `1.1.0.1.0.1.1` -> `1.1.0.1.0.1.1.1`
- The tumbler struct had `NPLACES=11` mantissa digits
- Deep version chains exceed this, causing overflow in `tumblerincrement`

### 2. Struct padding comparison bug
- `tumblereq()` compared tumblers byte-by-byte including struct padding
- C struct assignment doesn't guarantee padding bytes are copied
- Tumblers with identical values would fail equality tests due to garbage in padding

### 3. Version deletion on close
- `removefromopen()` deletes newly created versions if not marked as modified
- `docreatenewversion()` copies content but didn't mark the bert entry as modified
- The version was deleted before it could be read

## Fixes Applied

### backend/common.h
```c
// Increased from 11 to 16 to support deeper version chains
#define NPLACES 16

// Updated to match 16 mantissa places + 4 header fields
#define ZEROTUMBLER {0,0,0,0,  0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}

// Changed to use memset to zero all bytes including padding
#define tumblerclear(tumblerptr) clear((tumblerptr), sizeof(tumbler))
```

### backend/tumble.c
```c
// Changed from byte-by-byte to field-by-field comparison
bool tumblereq(tumbler *a, tumbler *b)
{
  register INT i;
  if (a->xvartumbler != b->xvartumbler) return FALSE;
  if (a->varandnotfixed != b->varandnotfixed) return FALSE;
  if (a->sign != b->sign) return FALSE;
  if (a->exp != b->exp) return FALSE;
  for (i = 0; i < NPLACES; i++) {
    if (a->mantissa[i] != b->mantissa[i]) return FALSE;
  }
  return TRUE;
}
```

### backend/do1.c
```c
// Added logbertmodified() call after docopyinternal in docreatenewversion
addtoopen(newisaptr, user, TRUE, WRITEBERT);
docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);
logbertmodified(newisaptr, user);  // <-- Added this line
doclose(taskptr, newisaptr, user);
```

## Verification

The fix was verified with `test_deep_chain.py`:
- 2 versions: SUCCESS
- 3 versions: SUCCESS
- 4 versions: SUCCESS
- 5 versions: SUCCESS

All golden tests pass after the fix.

## Test reference

The `identity_through_version_chain` test now works with deep version chains. The test was previously simplified to 2 versions as a workaround.

## Amendment (Bug 0020)

The three issues identified here (tumbler overflow, struct padding, version
deletion) were all real bugs. However, deep version chains also trigger Bug 0020:
each `create_version` copies content via `docopyinternal` → `insertspanf` →
`insertnd` → `recombine`, and after enough versions the spanfilade accumulates
6 children at height >= 2, triggering a stack buffer overflow in
`recombinend()` (`sons[MAXUCINLOAF]` off-by-one). Some crashes attributed to
tumbler overflow may have been this buffer overflow instead — both produce
SIGABRT with no `gerror` message.

See Bug 0020 for the full analysis and fix (`sons[MAXUCINLOAF + 1]`).
