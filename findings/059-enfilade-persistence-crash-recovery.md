# Finding 059: Enfilade Persistence and Crash Recovery

**Date:** 2026-02-10
**Category:** Storage Architecture
**Agent:** Gregory
**Related:** Finding 042 (Backend Event Loop Atomicity)

## Summary

Udanax-green enfilades use **lazy write-back caching with no transaction log**. Modified nodes are held in memory and written to disk only during memory pressure (grim reaper) or at session boundaries. There is **no write-ahead log (WAL)**, **no fsync**, and **no crash recovery mechanism**. A process crash mid-operation leaves the on-disk enfilade in an **inconsistent state with no recovery path**.

## Persistence Architecture

### 1. Modified Flag Tracking

**File:** `/udanax-test-harness/backend/enf.h:35,59`

```c
struct structcorecrumhedr {
    bool isapex BIT;
    SINT height;
    SINT cenftype;
    bool modified BIT;         // ← Dirty flag
    bool isleftmost BIT;
    struct structcorecrumhedr *nextcrum, *prevcrum;
    unsigned char age;         // ← LRU counter
    struct structcorecrumhedr *leftbroorfather;
    struct structcorecrumhedr *rightbro;
    typewid cwid;
    typedsp cdsp;
};
```

Each in-core enfilade node ("crum") tracks:
- `modified`: TRUE if this node has uncommitted changes
- `age`: LRU counter incremented by grim reaper; starts at NEW (0), becomes OLD (1), eventually reaped

### 2. Lazy Write-Back via Grim Reaper

**File:** `/udanax-test-harness/backend/credel.c:106-162`

Nodes are written to disk **only when**:

#### A. Memory Pressure (Grim Reaper)

When `ealloc()` runs out of memory ([credel.c:75]()), it calls `grimlyreap()`:

```c
int grimlyreap(void) {
    for (ptr = grimreaper; grimreaper; grimreaper = grimreaper->nextcrum) {
        if (grimreaper->age == RESERVED) continue;
        if (isreapable(&eh, grimreaper)) {
            reap(grimreaper);  // ← Writes modified nodes
            break;
        }
        ++grimreaper->age;  // Age nodes not yet reaped
    }
}
```

**File:** `/udanax-test-harness/backend/credel.c:292-330`

```c
int reap(typecorecrum *localreaper) {
    if (localreaper->isapex) {
        temp = (typecuc *)localreaper->leftbroorfather;
        orglwrite((typecbc*)temp);  // ← Write apex to disk
        return(0);
    }
    temp = weakfindfather(localreaper);
    subtreewrite(temp);  // ← Write modified subtree
}
```

#### B. Session Close or Idle

**File:** `/udanax-test-harness/backend/bed.c:104-108,134,183`

```c
for (;;) {
    if (n_players < 1) {
        diskflush();  // ← Write everything when no clients
        new_players(player, &n_players, TRUE, &task);
    }
    // ... process requests ...
    if (quitafteruser) {
        writeenfilades();  // ← SIGINT handler
        closediskfile();
        exit(0);
    }
}
```

**File:** `/udanax-test-harness/backend/corediskout.c:58-64,68-88`

```c
int diskflush(void) {
    writeenfilades();  // No fsync!
    initkluge(&granf, &spanf);
}

int writeenfilades(void) {
    // Write granfilade root
    temporgl.cinfo.granstuff.orglstuff.orglptr = (typecuc *)granf;
    orglwrite(&temporgl);

    // Write spanfilade root
    temporgl.cinfo.granstuff.orglstuff.orglptr = (typecuc *)spanf;
    orglwrite(&temporgl);
}
```

### 3. Disk Write Implementation

**File:** `/udanax-test-harness/backend/disk.c:300-338`

```c
void actuallywriteloaf(typeuberrawdiskloaf *loafptr, INT diskblocknumber) {
    if (lseek(enffiledes, (long)diskblocknumber*NUMBYTESINLOAF, 0) < 0) {
        gerror("lseek failed\n");
    }
    if (write(enffiledes, (char*)loafptr, sizeof(*loafptr)) <= 0) {
        qerror("write\n");
    }
    ++nolwrote;
    // NO fsync() call here!
}
```

**Critical:** There is **NO** `fsync()`, `fdatasync()`, or `sync()` call anywhere in the codebase. Writes are buffered by the OS and may not reach physical disk for seconds or minutes.

### 4. Subtree Write Order

**File:** `/udanax-test-harness/backend/corediskout.c:426-494`

When writing a modified subtree:

```c
static int subtreewriterecurs(typetask *taskptr, typecuc *father) {
    if (!father->modified) {
        loaffree(father);  // Already on disk
        return(0);
    }

    // 1. Write children first (bottom-up)
    for (ptr = father->leftson; ptr; ptr = ptr->rightbro) {
        if (ptr->height != 0) {
            subtreewriterecurs(taskptr, (typecuc*)ptr);
        } else if (ptr->cenftype == GRAN &&
                   ((typecbc*)ptr)->cinfo.infotype == GRANORGL) {
            orglwritepart2(taskptr, ptr);
        }
        ptr->modified = FALSE;  // Clear dirty flag
    }

    // 2. Increment refcounts for on-disk children
    for (ptr = father->leftson; ptr; ptr = ptr->rightbro) {
        if (ptr->height > 0 &&
            ((typecuc*)ptr)->sonorigin.diskblocknumber != DISKPTRNULL) {
            changerefcount(((typecuc*)ptr)->sonorigin, 1);
        }
    }

    // 3. Write parent node
    uniqueoutloaf(father, 0);
    loaffree(father);
}
```

**Write ordering:** Children → parent (bottom-up). This ensures parent pointers are valid if children exist on disk.

## Crash Recovery Analysis

### Scenario 1: Crash During Operation

Consider an INSERT that:
1. Allocates fresh I-address (in granfilade, modified=TRUE)
2. Inserts text into granfilade (knife cut, shift, modified=TRUE)
3. Inserts DOCISPAN into spanfilade (modified=TRUE)
4. Updates POOM (modified=TRUE)

**If crash occurs before next grim reaper or session close:**

- In-memory state: All four steps complete (Finding 042: atomic event loop)
- On-disk state: **None of the changes are written**
- Restart: Backend reads stale enfilade state from disk
- Result: **Complete rollback** — INSERT never happened

**If crash occurs during grim reaper while writing subtree:**

Example: Writing modified granfilade subtree with 3 levels:
1. Bottom nodes (leaves) written ✓
2. Middle node written ✓
3. **CRASH** — Root node NOT written

On restart:
- Root pointer on disk still points to old middle node
- New bottom/middle nodes exist on disk but are **unreachable** (orphaned)
- Enfilade structure is **corrupted** — old tree references deallocated blocks

**Finding 041** documents this: enfilade operations are **not** confluent if interleaved at sub-operation granularity. A crash mid-write is equivalent to interleaving the write with reads from other clients.

### Scenario 2: Crash Between Enfilades

**File:** `/udanax-test-harness/backend/corediskout.c:68-88`

`writeenfilades()` writes:
1. Granfilade root ← if crash here
2. Spanfilade root ← never written

On restart:
- Granfilade reflects latest state
- Spanfilade reflects old state
- **Invariant violation:** ISPACE entries in granf have no corresponding DOCISPAN entries in spanf

### Scenario 3: OS Buffer Cache

Even if `writeenfilades()` completes:
```c
writeenfilades();  // All write() calls succeed
closediskfile();   // close() returns success
exit(0);
// ← Power loss HERE
```

**NO guarantee data reached disk!** The OS may buffer writes in RAM for up to 30 seconds (default `vm.dirty_expire_centisecs` on Linux). A power failure loses everything since last OS-initiated flush.

## No Transaction Log

There is **no write-ahead log (WAL)** or redo/undo logging:

- No `enf.log`, `enf.wal`, or transaction file exists
- No sequence numbers or LSNs on nodes
- No checkpoint mechanism beyond "write everything now"
- No way to replay or roll back partial operations

**Recovery strategy:** None. Crash = data loss.

## Comparison to Modern Storage

| Feature | Udanax-Green | Modern DB (e.g., PostgreSQL) |
|---------|--------------|------------------------------|
| Write-ahead log | ✗ None | ✓ WAL records all changes |
| fsync on commit | ✗ Never | ✓ Configurable (default: ON) |
| Crash recovery | ✗ None | ✓ Replay WAL from last checkpoint |
| Dirty page tracking | ✓ `modified` flag | ✓ Buffer pool dirty bits |
| Write ordering | ✓ Bottom-up tree write | ✓ WAL before data pages |
| Partial write detection | ✗ None | ✓ CRC checksums on pages |
| Multi-version concurrency | ✗ Single version | ✓ MVCC |

## Design Rationale (Speculative)

Why no crash recovery?

1. **1980s context:** Crashes were rare; systems ran for weeks/months uninterrupted
2. **Single-user assumption:** Original design was single-user (`xumain`); `bed.c` multi-user daemon added later
3. **Simplicity:** No log = simpler code, no log replay complexity
4. **Performance:** Avoiding fsync on every operation = much faster (100x+ speedup)
5. **Backup strategy:** Assumption that periodic backups (`cp enf.enf enf.enf.backup`) are sufficient

## Operational Consequences

### Data Loss Windows

- **Normal operation:** Writes deferred until memory pressure or session idle
  - Typical window: Seconds to minutes of uncommitted work
- **Crash during operation:** Lose all work since last `diskflush()`
- **Crash during grim reaper:** Enfilade structure **corrupted**

### Recovery Procedure

**File:** `/udanax-test-harness/backend/disk.c:340-383`

On startup, `initenffile()`:
```c
bool initenffile(void) {
    fd = open("enf.enf", 2);
    if (fd == -1) {
        fd = creat("enf.enf", 0666);
        initheader();  // Create empty enfilade
        return FALSE;  // New state
    } else {
        ret = readallocinfo(fd);  // Read block allocation table
        return ret;  // Existing state
    }
}
```

**No validation!** The backend:
- Does NOT check enfilade consistency
- Does NOT detect partial writes
- Does NOT attempt repair
- Simply reads whatever is on disk and hopes it's valid

If corruption exists:
- Operations will fail with `gerror()` (abort)
- Or worse: silently return garbage data

## Recommendation for Robust Operation

Since udanax-green has **no crash recovery**, operators should:

1. **Frequent flushes:** Modify `bed.c:105` to call `diskflush()` after every N operations
2. **Graceful shutdown:** Always send SIGINT (Ctrl-C), never SIGKILL
3. **Backup before operations:** `cp enf.enf enf.enf.backup` before risky operations
4. **Run in VM/container:** Snapshot file system before starting backend
5. **Accept data loss:** Treat as **prototype system**, not production storage

## References

- `/udanax-test-harness/backend/enf.h:35,59` — Modified flag definition
- `/udanax-test-harness/backend/credel.c:106-330` — Grim reaper implementation
- `/udanax-test-harness/backend/corediskout.c:58-494` — Disk write logic
- `/udanax-test-harness/backend/disk.c:300-338` — Raw disk I/O (no fsync)
- `/udanax-test-harness/backend/bed.c:104-108,134,183` — Session-level flush points
- Finding 042 — Backend Event Loop Atomicity (operation-level atomicity, not durability)
- Finding 041 — Enfilade Insertion Order Dependency (structural corruption risk)
