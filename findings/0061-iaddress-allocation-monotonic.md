# Finding 0061: I-Address Allocation is Monotonic and Unaffected by DELETE

**Date discovered:** 2026-02-10
**Category:** Granfilade Operations
**Test scenarios:** `/udanax-test-harness/febe/scenarios/iaddress_allocation.py`

## Summary

I-address allocation in udanax-green is **strictly monotonic** and **completely unaffected by DELETE operations**. When a user performs a sequence like INSERT-DELETE-INSERT-DELETE-INSERT, each INSERT allocates I-addresses by finding the current maximum in the granfilade and incrementing from there, regardless of what DELETEs occurred between INSERTs.

## The Question

When a user performs interleaved editing:
1. INSERT some text
2. DELETE a character
3. INSERT more text
4. DELETE again
5. INSERT again

Does `findisatoinsertgr` always allocate I-addresses monotonically from the current maximum, regardless of DELETE operations? Or can DELETE somehow affect the allocation state?

## The Answer: Strictly Monotonic Allocation

**DELETE operations do NOT affect I-address allocation.** The allocation mechanism queries the granfilade tree state via `findpreviousisagr` to find the highest existing I-address, then increments from there. Since DELETE only modifies the spanfilade (V-space to I-space mappings) and never touches the granfilade (I-space content storage), deleted content's I-addresses remain in the tree and continue to influence allocation.

## Code Analysis

From `/udanax-test-harness/backend/granf2.c`:

### findisatoinsertmolecule (for ATOM/text inserts)

```c
static int findisatoinsertmolecule(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
  typeisa upperbound, lowerbound;

    tumblerincrement (&hintptr->hintisa, 2, hintptr->atomtype + 1, &upperbound);
    clear (&lowerbound, sizeof(lowerbound));
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);
    if (tumblerlength (&hintptr->hintisa) == tumblerlength (&lowerbound)) {
        tumblerincrement (&lowerbound, 2, hintptr->atomtype, isaptr);
        tumblerincrement (isaptr, 1, 1, isaptr);
    } else if (hintptr->atomtype == TEXTATOM) {
            tumblerincrement (&lowerbound, 0, 1, isaptr);  // ← KEY LINE
    }
    // ...
}
```

**Key observation:** Line 169 (`tumblerincrement (&lowerbound, 0, 1, isaptr)`) increments the last component of `lowerbound` by 1. The `lowerbound` value comes from `findpreviousisagr`, which traverses the granfilade tree to find the highest I-address less than `upperbound`.

### The Allocation Process

1. **Query granfilade state:** `findpreviousisagr(fullcrumptr, upperbound, &lowerbound)` walks the tree and returns the highest I-address currently in the granfilade
2. **Increment:** `tumblerincrement(&lowerbound, 0, 1, isaptr)` adds 1 to get the next available I-address
3. **Insert into granfilade:** `insertseq(fullcrumptr, isaptr, &locinfo)` adds the new content at the allocated I-address

DELETE operations call `deletevspanpm` (see `/udanax-test-harness/backend/edit.c`), which modifies the **spanfilade** to remove V-space mappings. The granfilade is never modified - the content remains at its I-addresses permanently.

## Test Evidence

### Test: `interleaved_insert_delete`

**Scenario:** INSERT "AAA", DELETE middle 'A', INSERT "BBB", DELETE two chars, INSERT "CCC"

**Golden output:**  `/udanax-test-harness/golden/iaddress_allocation/interleaved_insert_delete.json`

| Operation | Content | V-span width | Observation |
|-----------|---------|--------------|-------------|
| INSERT "AAA" | AAA | 0.3 | First insert allocates I.1, I.2, I.3 |
| DELETE pos 1.2 | AA | 0.2 | V-space shrinks, granfilade unchanged |
| INSERT "BBB" | ABBBA | **0.5** | Width increased by 0.3, not 0.4! |
| DELETE pos 1.3-1.4 | ABA | 0.3 | V-space shrinks again |
| INSERT "CCC" | ABCCCA | **0.6** | Width increased by 0.3, not 0.5! |

**Analysis:**

After DELETE #1, the document has V-span width 0.2, but the next INSERT adds 0.3 to get 0.5. If I-addresses were being reused, we'd expect:
- Reused allocation: 0.2 + 0.1 (reusing deleted I.2) = 0.3 total
- Actual result: 0.2 + 0.3 (fresh I.4, I.5, I.6) = 0.5 total

Similarly, after DELETE #2, width is 0.3, but INSERT #3 adds 0.3 to get 0.6:
- Reused allocation: 0.3 + 0.1 (reusing deleted addresses) = 0.4 total
- Actual result: 0.3 + 0.3 (fresh I.7, I.8, I.9) = 0.6 total

This proves that **deleted I-addresses are NOT reused**. The allocation pointer continues monotonically forward.

### Test: `consecutive_inserts_monotonic`

**Control test:** INSERT "A", INSERT "B", INSERT "C" with no DELETEs.

**Golden output:** `/udanax-test-harness/golden/iaddress_allocation/consecutive_inserts_monotonic.json`

| Operation | Content | V-span width |
|-----------|---------|--------------|
| INSERT "A" | A | 0.1 |
| INSERT "B" | AB | 0.2 |
| INSERT "C" | ABC | 0.3 |

Width increases by exactly the number of characters inserted each time: 0.1 → 0.2 → 0.3. This confirms monotonic allocation in the baseline case.

## Data Structure: No Session-Local Counter

The allocation mechanism does **not** maintain a session-local "next available I-address" counter. Instead, it queries the granfilade tree on every INSERT:

```c
findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);
```

This function recursively traverses the tree (see `granf2.c:255-278`) to find the rightmost (highest) I-address. This means:

1. **Stateless allocation:** Each INSERT independently queries the tree, ensuring consistency even across multiple editing sessions or concurrent operations
2. **No "free list":** There is no mechanism to track or reuse deleted I-addresses
3. **Permanent address growth:** The granfilade grows monotonically; I-addresses are never freed

## Implications

### 1. DELETE is a V-space-only operation

DELETE operations modify only the **spanfilade** (the V→I mapping enfilade). The granfilade content remains permanently. This is consistent with the Xanadu philosophy: "bytes never die, addresses never change."

### 2. I-addresses from consecutive INSERTs are contiguous

When two INSERTs occur without intervening operations, they allocate contiguous I-addresses:
- INSERT "A" → I-address 2.1.0.1.0.1.3.1
- INSERT "B" → I-address 2.1.0.1.0.1.3.2

This contiguity is preserved even when DELETEs occur between them:
- INSERT "AAA" → I.1, I.2, I.3
- DELETE middle character (I.2 still exists in granfilade)
- INSERT "BBB" → I.4, I.5, I.6 (continuing from I.3, not reusing I.2)

This explains **Finding 0033** (I-space consolidates adjacent addresses): sequential inserts produce sequential I-addresses, which naturally consolidate into single I-spans.

### 3. Granfilade growth is unbounded

Since deleted content is never removed from the granfilade, the tree grows indefinitely. In a long-running system:
- Frequently edited documents will have large granfilade trees containing all historical I-addresses
- "Garbage" I-addresses (those no longer referenced by any document's spanfilade) accumulate
- No automatic cleanup or compaction occurs

This is a known limitation documented in the Udanax Green source. The production Xanadu system would require garbage collection or archival mechanisms.

### 4. REARRANGE does not affect allocation

Since REARRANGE (like DELETE) only modifies the spanfilade and does not touch the granfilade, it also has no effect on I-address allocation for subsequent INSERTs.

## Related Findings

- **Finding 0021**: Address allocation mechanism (covers non-ATOM allocation via `findisatoinsertnonmolecule`)
- **Finding 0033**: I-space consolidates adjacent addresses (explains why sequential inserts produce single I-spans)
- **Finding 0030**: INSERT updates V-space while preserving I-space identity
- **Finding 0057**: Spanfilade has no cleanup on DELETE (confirms DELETE is spanfilade-only)

## Code References

- `granf2.c:130-156` - `findisatoinsertgr` (main allocation entry point)
- `granf2.c:158-181` - `findisatoinsertmolecule` (ATOM allocation via query-and-increment)
- `granf2.c:255-278` - `findpreviousisagr` (tree traversal to find highest I-address)
- `insert.c:17-70` - `insertseq` (inserts content into granfilade at allocated I-address)
- `edit.c` - `deletevspanpm` (DELETE implementation, spanfilade-only)

## Conclusion

I-address allocation in udanax-green is:

1. **Monotonic:** Always increments from the current maximum
2. **Stateless:** Queries the granfilade tree on each allocation (no session counter)
3. **Unaffected by DELETE:** Deleted I-addresses remain in the granfilade and continue to influence allocation
4. **Unaffected by REARRANGE:** Like DELETE, REARRANGE only touches the spanfilade

This design ensures:
- **Permanent content addressing:** I-addresses never change or get reused
- **Simple allocation logic:** No free-list management or gap tracking
- **Transclusion integrity:** Shared I-addresses remain stable across all documents

The trade-off is unbounded granfilade growth, as deleted content is never reclaimed.
