# Finding 0050: BERT Tokens Are Not Enforced by the Back End

**Date:** 2026-02-07
**Category:** Security / Architecture
**Severity:** Critical Design Flaw

## Summary

The back end **does not enforce** BERT token requirements for state-modifying operations. Although the code contains checks for WRITE tokens via `checkforopen()` and `findorgl()`, these checks occur AFTER the back end has already sent a success response to the front end. The back end **trusts** the front end to acquire tokens voluntarily.

## The Protocol Sequence

For every state-modifying FEBE command (INSERT, DELETEVSPAN, REARRANGE, COPY, etc.), the back end follows this sequence:

```c
void insert(typetask *taskptr) {
    (void) getinsert(taskptr, &docisa, &vsa, &textset);  // [1] Parse request
    putinsert(taskptr);                                   // [2] Send success response
    if (!doinsert(taskptr, &docisa, &vsa, textset))      // [3] Attempt operation
        fprintf(stderr,"requestfailed in insert\n");     // [4] Silent failure
}
```

**[fns.c:84-98]**

The critical issue: the success response is sent at step [2], before the BERT check at step [3].

## The BERT Check

State-modifying operations call `findorgl()` with `WRITEBERT`:

```c
bool dodeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr) {
    typeorgl docorgl;
    return (
        findorgl(taskptr, granf, docisaptr, &docorgl, WRITEBERT)  // BERT check here
        && deletevspanpm(taskptr, docisaptr, docorgl, vspanptr)
    );
}
```

**[do1.c:162-171]**

The `findorgl()` function calls `checkforopen()`:

```c
bool findorgl(typetask *taskptr, typegranf granfptr, typeisa *isaptr,
              typeorgl *orglptr, int type) {
    int temp;

    if ((temp = checkforopen(isaptr, type, user)) <= 0) {
        if (!isxumain) {
            fprintf(stderr,"orgl for ");
            dumptumbler(isaptr);
            fprintf(stderr," not open in findorgl temp = %d\n", temp);
            return FALSE;  // Operation rejected
        }
    }
    *orglptr = fetchorglgr(taskptr, granfptr, isaptr);
    return (*orglptr ? TRUE : FALSE);
}
```

**[granf1.c:17-41]**

When `checkforopen()` returns:
- `<= 0` → `findorgl()` returns FALSE
- `> 0` → operation proceeds

## The Problem

The back end sends the success response **before** calling `findorgl()`. When the BERT check fails:

1. Front end receives success response (matching command code)
2. Back end prints error to stderr
3. **Operation is silently skipped**
4. Front end believes the operation succeeded

## Evidence Across All Operations

This pattern is consistent for all state-modifying operations:

| Operation | Handler | Pattern |
|-----------|---------|---------|
| INSERT | `insert()` [fns.c:84-98] | `putinsert()` → `doinsert()` |
| DELETEVSPAN | `deletevspan()` [fns.c:333-347] | `putdeletevspan()` → `dodeletevspan()` |
| REARRANGE | `rearrange()` [fns.c:~245] | `putrearrange()` → `dorearrange()` |
| COPY (via INSERT) | `insert()` [fns.c:84-98] | `putinsert()` → `doinsert()` → `docopy()` |

All call `findorgl(..., WRITEBERT)` which can return FALSE, but this happens after the response.

## Comparison with Query Operations

Some query operations have the correct pattern:

```c
void createlink(typetask *taskptr) {
    if (getcreatelink(taskptr, &docisa, &fromspecset, &tospecset, &threespecset)
        && docreatelink(taskptr, &docisa, fromspecset, tospecset, threespecset, &linkisa)) {
        putcreatelink(taskptr, &linkisa);  // Send response AFTER success
    } else {
        putrequestfailed(taskptr);  // Send failure on error
    }
}
```

**[fns.c:100-115]**

This is the **correct** pattern - check first, then respond.

## Implications

### Security

1. **No access control enforcement** - A malicious front end can modify any document without acquiring WRITE tokens
2. **No write serialization** - Multiple front ends can concurrently modify the same document
3. **BERT is advisory only** - The entire BERT mechanism is a voluntary protocol, not an enforced constraint

### For the Specification

This fundamentally affects EWD-025 (Concurrency) and EWD-032 (FEBE Contract):

1. **CON1 (BERT exclusion) is NOT enforced** - The back end does not prevent concurrent writes
2. **FE3 (token acquisition) is required** - The contract depends entirely on front end compliance
3. **BE5 does NOT exist** - There is no back end enforcement of token requirements

The FEBE boundary is **not a trust boundary** - it's a **coordination protocol** where the back end trusts the front end completely.

### For Multi-User Systems

This design requires:
- Trusted front ends that follow the BERT protocol voluntarily
- Or an intermediate layer (proxy/gateway) that enforces BERT tokens
- Or single-user deployments where all processes are trusted

## Why This Design?

Two possible explanations:

1. **Performance** - Sending the response immediately reduces latency
2. **Protocol simplicity** - Always sending matching response codes simplifies client logic

But the cost is complete loss of back end enforcement.

## Commented-Out Code

The codebase contains commented-out versions with the correct pattern:

```c
/* void deletevspan (taskptr)
  if (getdeletevspan(taskptr, &docisa, &vspan)
      && dodeletevspan(taskptr, &docisa, &vspan))
    putdeletevspan(taskptr);
  else
    putrequestfailed(taskptr);
*/
```

This suggests the implementers **knew** about the issue but chose the current design anyway.

## Recommendation

For a production system, this would need to be fixed by:

1. Checking `doXXX()` success **before** sending `putXXX()` response
2. Sending `putrequestfailed()` on any error
3. Making the back end a proper trust boundary

Or alternatively, documenting that:
- The back end is designed for single-user or trusted-frontend deployments
- Multi-user systems require an enforcement layer above the back end

## Related

- **Finding 0014**: BERT access control mechanism (documents the BERT design)
- **Finding 0011**: Convention over enforcement (this is the most extreme case)
- **EWD-025**: Concurrency and the permanent layer (assumes BERT is enforced)
- **EWD-032**: The FEBE contract (defines front end obligations including FE3)

## Files

| File | Purpose |
|------|---------|
| `fns.c:84-98` | INSERT handler - sends response before check |
| `fns.c:333-347` | DELETEVSPAN handler - same pattern |
| `do1.c:34-43` | `dorearrange()` - calls `findorgl(..., WRITEBERT)` |
| `do1.c:45-65` | `docopy()` - calls `findorgl(..., WRITEBERT)` |
| `do1.c:162-171` | `dodeletevspan()` - calls `findorgl(..., WRITEBERT)` |
| `granf1.c:17-41` | `findorgl()` - checks BERT and returns FALSE on failure |
| `bert.c:52-87` | `checkforopen()` - the actual BERT checking logic |
