# Finding 042: Backend Event Loop Atomicity

**Date:** 2026-02-07
**Category:** Concurrency Architecture
**Agent:** Gregory
**Related:** EWD-025 (Concurrency and the Permanent Layer)

## Summary

The `bed.c` event loop processes **one complete FEBE operation atomically** per iteration. Each operation runs to completion before the next `select()` call, implementing **run-to-completion scheduling**. This answers EWD-025's claim about single-threaded sequential execution.

## Event Loop Architecture

### Main Loop Structure

**File:** `/udanax-test-harness/backend/bed.c` lines 103-150

```c
for (;;) {
    // Wait for input from any connected frontend
    if (select(nfds+1, &inputfds2, 0, 0, &timeout) < 0) {
        // ... error handling ...
    } else {
        for (i = 0; i <= nfds; i++) {
            if ((1<<i) & inputfds2) {
                user = fdtoplayer[i];
                task.inp = player[user].inp;
                task.outp = player[user].outp;
                task.account = player[user].account;
                xanadu(&task);  // PROCESS ONE COMPLETE REQUEST
                // ... cleanup ...
            }
        }
    }
    // Handle player connect/disconnect
    leave(player, &n_players);
    new_players(player, &n_players, FALSE, &task);
}
```

### Request Processing

**File:** `/udanax-test-harness/backend/bed.c` lines 153-172

```c
int xanadu(typetask *taskptr)
{
    if (setjmp(frontendeof)) {
        dobertexit(user);
        player[user].wantsout = TRUE;
    } else if (getrequest(taskptr, &request)) {
        (*requestfns[request])(taskptr);  // EXECUTE OPERATION
        sendresultoutput(taskptr);        // SEND RESPONSE
        // ...
    }
    tfree(taskptr);  // FREE TASK MEMORY
}
```

## Atomicity Guarantees

### 1. One Operation Per Iteration

The event loop:
1. Calls `select()` to wait for any frontend ready to send
2. Reads ONE request from ONE frontend
3. Executes the ENTIRE operation (`requestfns[request]`)
4. Sends the response
5. Frees task memory
6. Returns to `select()`

**There is NO interleaving of operations.** Each request runs atomically from start to finish.

### 2. Multi-Step Operations Are Atomic

Operations like `INSERT`, `CREATENEWVERSION`, or `CREATELINK` involve multiple internal steps:

**Example: INSERT** (`/udanax-test-harness/backend/do1.c`)
1. Allocate fresh I-address via `findisatoinsertgr()`
2. Insert text into granfilade via `inserttextgr()`
3. Insert DOCISPAN into spanfilade via `insertdocispansp()`
4. Update POOM via `copyinspan()`

**All four steps execute atomically** because they're part of a single `requestfns[INSERT]` call. The event loop does NOT return to `select()` until the entire operation completes.

### 3. No Preemption

The backend is **single-threaded** with **no preemption**:
- No threads
- No signal handlers that modify state (SIGINT just sets a flag)
- No interrupts during operation processing

**Consequence:** An operation's view of shared state (ispace, spanf, POOMs) is consistent throughout its execution.

## Concurrency Implications

### Current Implementation: Sequential Execution

**File:** `/udanax-test-harness/backend/bed.c:118-128`

```c
for (i = 0; i <= nfds; i++) {
    if ((1<<i) & inputfds2) {
        user = fdtoplayer[i];
        // ... set up task ...
        xanadu(&task);  // BLOCKS until complete
        // ...
    }
}
```

Even if **multiple frontends** have requests ready, they are processed **sequentially**:
1. Frontend 1's request executes completely
2. Frontend 2's request executes completely
3. Frontend 3's request executes completely
4. Return to `select()`

**There is no parallelism.** The loop iterates over ready file descriptors, but each `xanadu(&task)` call is **synchronous and blocking**.

### P1 Achieved by Sequential Execution

**EWD-025 mentions:**
> P1 (Freshness): Freshly allocated I-addresses don't collide with existing addresses.

**Implementation:**
- Single-threaded execution means I-address allocation (`findisatoinsertgr()`) is **globally serialized**
- No concurrent allocations possible
- No locks needed—sequential execution IS the serialization

**File:** `/udanax-test-harness/backend/granf2.c:203-242` (I-address allocation)

The global search-and-increment for fresh I-addresses is **safe** because only one operation can execute at a time.

## Contrast with Concurrent Backend (Hypothetical)

If the backend were **multi-threaded**, the event loop would look like:

```c
// HYPOTHETICAL concurrent design (NOT the actual code)
for (i = 0; i <= nfds; i++) {
    if ((1<<i) & inputfds2) {
        user = fdtoplayer[i];
        spawn_thread(() => xanadu(&task));  // PARALLEL EXECUTION
    }
}
```

Then EWD-025 CON5's requirements would apply:
1. **Disjoint I-address allocation** — partitioning by account or locking
2. **Per-document POOM serialization** — locks or BERT-based mutual exclusion

But the **actual implementation avoids all this** by serializing everything.

## Answer to User's Question

> Does `bed.c` event loop truly process one full operation atomically, or could a multi-step operation be interrupted between steps?

**Answer:** One full operation is **atomically executed**. The event loop does NOT return to `select()` until `xanadu(&task)` completes. There is no interruption between steps of a multi-step operation.

## Performance Implications

### Throughput Limitation

With `n` frontends connected:
- Maximum throughput = `1 / (average operation latency)`
- Cannot exploit multi-core CPUs
- Long-running operations block all other clients

### Why This Design?

Likely reasons for single-threaded design:
1. **Simplicity** — No locks, no race conditions, no deadlocks
2. **1980s context** — Multi-core CPUs didn't exist; single-threaded was standard
3. **I/O bound** — Most operations read/write disk; parallelism wouldn't help much
4. **Correctness first** — Easier to verify invariants in single-threaded code

## Relation to EWD-025 CON5

**EWD-025 CON5:** Minimal serialization for concurrent Xanadu requires:
1. Disjoint I-address allocation
2. Per-document POOM access serialization

**Current implementation:** Achieves this via **global serialization** (stronger than necessary).

**Future concurrent implementation:** Could relax to per-document serialization, exploiting:
- Permanent layer confluence (Finding 041)
- POOM independence across documents
- Partitioned I-address allocation by account prefix

But would need to address:
- Enfilade structural corruption (Finding 041)
- BERT token management in parallel
- Disk I/O contention

## References

- `/udanax-test-harness/backend/bed.c:103-172` — Event loop and request processing
- `/udanax-test-harness/backend/granf2.c:203-242` — I-address allocation
- EWD-025 — Concurrency and the Permanent Layer
- Finding 041 — Enfilade Insertion Order Dependency
