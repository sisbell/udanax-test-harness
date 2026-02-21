# Finding 0014: BERT - Document Access Control Mechanism

**Date:** 2026-01-30
**Category:** Architecture / Concurrency

## Summary

**BERT** (likely "Booking Entry Record Table") is the access control mechanism for document operations. It tracks which documents are open, by whom, and with what access level.

## Access Levels

From common.h:165-167:
```c
#define NOBERTREQUIRED 0   // No access check needed (internal ops)
#define READBERT 1         // Read access
#define WRITEBERT 2        // Write access
```

## The BERT Table

From bert.c:13-29:
```c
typedef struct {
    int connection;          // Which client connection
    tumbler documentid;      // Document being accessed
    char created, modified;  // Flags
    int type;               // READBERT or WRITEBERT
    int count;              // Reference count
} bertentry;

static conscell *berttable[NUMBEROFBERTTABLE];  // Hash table
```

## Access Control Matrix

From bert.c:43-50, the `checkforopen` function implements this state machine:

```
                     Document State
                ┌────────────────────────────────────────────┐
                │  Not Open      │   Open READ   │ Open WRITE │
    Request     │ !owned │ owned │ conn= │ conn≠ │ conn= │conn≠│
    ────────────┼────────┼───────┼───────┼───────┼───────┼─────┤
    READ        │   0    │   0   │ READ  │   0   │ WRITE │ -1  │
    ────────────┼────────┼───────┼───────┼───────┼───────┼─────┤
    WRITE       │  -1    │   0   │  -1   │  -1   │ WRITE │ -1  │
    └────────────────────────────────────────────────────────────┘

    Return values:
      >0 = Access granted (returns access type)
       0 = Need to open document first
      -1 = Access denied (should create new version)
```

## How It's Used

### In Document Operations

Every document access calls `findorgl` with an access type:

```c
// Read-only access
findorgl(taskptr, granf, &docisa, &orgl, READBERT)

// Write access
findorgl(taskptr, granf, &docisa, &orgl, WRITEBERT)

// Internal operation (no check)
findorgl(taskptr, granf, &docisa, &orgl, NOBERTREQUIRED)
```

### Opening Documents

From the FEBE protocol:
```c
// doopen() checks/creates BERT entry
bool doopen(taskptr, tp, newtp, type, mode, connection)
```

### Closing Documents

```c
// doclose() removes BERT entry
bool doclose(taskptr, tp, connection)
```

## Key Behaviors

### Read Sharing

Multiple connections can have READBERT access to the same document simultaneously:
- Connection A opens READ → OK
- Connection B opens READ → OK
- Both can read concurrently

### Write Exclusivity

Only one connection can have WRITEBERT access:
- Connection A opens WRITE → OK
- Connection B opens WRITE → Denied (-1)

### Version Branching

When write access is denied, the return value -1 suggests creating a new version:
```c
// If WRITEBERT returns -1, client should:
// 1. Create a version of the document
// 2. Open the version for WRITE
```

This supports Xanadu's non-destructive editing model.

## NOBERTREQUIRED Usage

Internal operations bypass BERT checks:

```c
// Examples from do1.c:
docopy(taskptr, docisaptr, &linkvsa, ispanset)
  → specset2ispanset(taskptr, specset, &ispanset, NOBERTREQUIRED)

docopyinternal(...)
  → findorgl(taskptr, granf, docisaptr, &docorgl, NOBERTREQUIRED)
```

This is used when:
1. The operation is already within a BERT-protected context
2. System operations that don't need user-level access control
3. Internal data structure manipulation

## Connection Tracking

BERT tracks which **connection** owns each access:

```c
if (connection == bert->connection) {
    // Same connection - may upgrade or reuse
} else {
    // Different connection - check for conflicts
}
```

This enables:
- Same connection to have multiple opens (reference counting)
- Detection of cross-connection conflicts
- Proper cleanup on connection close

## Implications

### For Multi-User

BERT enables concurrent access:
- Readers don't block readers
- Writers block writers
- Writers block readers on other connections

### For the Test Harness

The test harness runs with a single connection, so BERT conflicts are rare. But:
- Opening a document twice for WRITE would fail
- Must close documents before re-opening with different mode

### For Formal Specification

The spec should model:
- Document access state (not open, read, write)
- Ownership by connection
- State transitions on open/close/upgrade

## Related

- **Finding 0011**: Convention over enforcement (BERT is one of the few enforced rules)
- **Bug 0008**: Had issues with opening documents multiple times
- `bert.c`: Full implementation

## Files

| File | Purpose |
|------|---------|
| `bert.c` | BERT table and access checks |
| `common.h:165-167` | Access level constants |
| `do2.c:doopen/doclose` | Open/close operations |
| Most `do*.c` files | Use BERT in findorgl calls |
