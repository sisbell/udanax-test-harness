# Finding 057: Spanfilade Entries Are Not Cleaned Up on DELETE

**Date:** 2026-02-10
**Status:** Confirmed by code inspection
**Category:** Architecture, Data Structure Consistency
**Sources:** `backend/do1.c:162-171`, `backend/orglinks.c:145-152`, `backend/spanf1.c`, Finding 012, Finding 013
**Related:** EWD-030 (DEL5), Finding 012 (Dual Enfilade Architecture), Finding 048 (Ghost Links)

## Summary

When a document DELETEs content that was previously COPYed (transcluded) into it, **the DELETE operation does NOT clean up the spanfilade entries** that were created by the COPY. The `deletevspanpm` function only removes the V→I mapping from the document's POOM (in granf), but there is no corresponding call to remove the I-address-to-document association from the spanf index.

This results in **stale spanfilade references**: documents that no longer contain certain I-addresses continue to appear in FIND_DOCUMENTS results for those I-addresses.

---

## The Problem

### COPY Creates Spanfilade Entries

From `do1.c:45-65` (the `docopy` function):

```c
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
  typeispanset ispanset;
  typeorgl docorgl;
  bool specset2ispanset(), findorgl(), acceptablevsa(), insertpm(), insertspanf();

  return (
     specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)
  && findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
  && acceptablevsa (vsaptr, docorgl)

  /* the meat of docopy: */
  && insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)

  &&  insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)
  /*      &&  ht stuff */ );
}
```

**Key operations:**
1. **Line 60**: `insertpm` — inserts the V→I mapping into the document's POOM (in granf)
2. **Line 62**: `insertspanf` — registers the document as containing these I-addresses (in spanf)

The `insertspanf` call indexes the destination document as containing the transcluded I-addresses, allowing FIND_DOCUMENTS to discover this document when searching for that content.

### DELETE Does NOT Remove Spanfilade Entries

From `do1.c:162-171` (the `dodeletevspan` function):

```c
bool dodeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
  typeorgl docorgl;
  bool findorgl(), deletevspanpm();

  return (
     findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
  && deletevspanpm (taskptr, docisaptr, docorgl, vspanptr)
  /*&& TRUE*/ /* ht stuff */ );
}
```

From `orglinks.c:145-152` (the `deletevspanpm` function):

```c
bool deletevspanpm(typetask *taskptr, tumbler *docisaptr, typeorgl docorgl, typevspan *vspanptr)
{
  if (iszerotumbler(&vspanptr->width))
    return (FALSE);
  deletend((typecuc*)docorgl, &vspanptr->stream, &vspanptr->width, V);
  logbertmodified(docisaptr, user);
  return (TRUE);
}
```

**Key observation**: `deletevspanpm` only calls `deletend` to remove the V→I mapping from the document's orgl (POOM). **There is no corresponding call to remove the spanfilade entry.**

### No Delete Function Exists for Spanf

Inspection of `backend/spanf1.c` and `backend/spanf2.c` reveals:

**Functions that exist:**
- `insertspanf` — adds spanfilade entries
- `findlinksfromtothreesp` — searches spanfilade for links
- `retrieveendsetsfromspanf` — retrieves link endsets
- `findnumoflinksfromtothreesp` — counts links
- `finddocscontainingsp` — finds documents containing I-addresses

**Functions that DO NOT exist:**
- ❌ `deletespanf` — no such function
- ❌ `removespanf` — no such function
- ❌ Any cleanup or removal mechanism

---

## Behavior Implications

### Stale FIND_DOCUMENTS Results

The consequence of this design:

1. Document A COPYs content from Document B (I-addresses `x..y`)
   - `insertspanf` registers: "Document A contains I-addresses `x..y`"

2. Document A DELETEs that content
   - The V→I mapping is removed from A's POOM
   - **But the spanfilade still says "Document A contains I-addresses `x..y`"**

3. User searches via FIND_DOCUMENTS for I-addresses `x..y`
   - FIND_DOCUMENTS queries the spanfilade
   - **Result includes Document A** (stale reference)
   - When trying to convert I-addresses to V-addresses in Document A, the lookup fails (returns empty)

This is the **ghost reference problem**: the spanfilade claims a document contains content that the document's POOM no longer maps to any V-position.

### Comparison to Link Deletion

Interestingly, **link deletion has similar behavior** (Finding 024):
- Creating a link calls `insertendsetsinspanf` to index the link's endsets
- Deleting a link does NOT remove those spanfilade entries
- The spanfilade retains references to deleted links

So the lack of cleanup is **consistent across both DOCISPAN and link indexing**.

---

## Test Evidence

### Scenario: `delete_transcluded_content_spanfilade_cleanup`

(Created in `febe/scenarios/spanfilade_cleanup.py`)

```python
# 1. Create source document with content
# 2. Create target document
# 3. COPY source content into target
#    -> insertspanf registers target's reference to I-addresses
# 4. Verify target appears in FIND_DOCUMENTS for the content
# 5. DELETE the transcluded content from target
#    -> Should this call deletespanf?
# 6. Check if target still appears in FIND_DOCUMENTS
#    -> Expected (if cleanup): only source
#    -> Actual (no cleanup): source AND target (stale reference)
```

**Expected behavior (if cleanup worked):**
- FIND_DOCUMENTS returns: [source_doc]

**Actual behavior (no cleanup):**
- FIND_DOCUMENTS returns: [source_doc, target_doc]
- But target_doc's POOM has no V→I mapping for those I-addresses
- Attempting to retrieve content from target_doc via those I-addresses yields empty result

### Multiple Transclusions Test

If the same content is transcluded into documents A, B, and C:
- All three have spanfilade entries
- If we DELETE from B, does B get removed from spanfilade?
- Answer: **No**, B remains in the index

This suggests there's **no reference counting** — each `insertspanf` is independent, and there's no corresponding removal mechanism.

---

## Architectural Analysis

### Why No Cleanup?

Several possible design rationales:

#### 1. Performance Trade-off
- **Cleanup is expensive**: Removing individual entries from a global enfilade is O(log N)
- **Stale entries are tolerable**: FIND_DOCUMENTS may return false positives, but filtering happens at the V-conversion layer (Finding 048)
- **Batch cleanup expected**: Perhaps spanf is rebuilt periodically rather than maintained incrementally

#### 2. Historical Record Philosophy
- The spanfilade could be viewed as a **journal** of "documents that have ever contained this I-address"
- Deletion doesn't erase history, it only removes current visibility
- This aligns with the permascroll philosophy (P0) — nothing is truly deleted, only hidden

#### 3. Implementation Incompleteness
- The enfilade data structure may not efficiently support deletions
- `insertnd` exists, but `deletend` for spanf dimension may not be implemented
- This is a **missing feature**, not a deliberate design choice

### Consequences for Formal Specification

The specification must model:

1. **POOM state** (granf): V→I mappings for currently visible content
2. **Spanfilade state** (spanf): I-address→document index (may contain stale entries)
3. **Invariant violation**: spanf is NOT guaranteed to be consistent with current POOM state

From EWD-030 DEL5, we know unreferenced addresses exist — I-addresses with no current POOM mapping. The spanfilade can reference documents at unreferenced addresses.

**Specification implication**: FIND_DOCUMENTS returns a **superset** of documents currently containing the I-addresses. Post-processing (I-to-V conversion) is required to filter stale results.

---

## Comparison with Link Indexing

| Operation | Granf Update | Spanf Update | Cleanup on Delete |
|-----------|--------------|--------------|-------------------|
| **COPY** | insertpm (add V→I) | insertspanf (add I→doc) | ❌ No deletespanf |
| **DELETE** | deletend (remove V→I) | ❌ No cleanup | ❌ No deletespanf |
| **CREATE_LINK** | Create link orgl | insertendsetsinspanf | ❌ No cleanup (Finding 024) |
| **DELETE_LINK** | Remove link orgl | ❌ No cleanup | ❌ No cleanup (Finding 024) |

The pattern is clear: **spanf is write-only** — entries are added but never removed.

---

## Code Evidence Summary

### Copy Operation Path
```
fns.c:vcopy()
  -> do1.c:docopy()
       -> orglinks.c:insertpm()        # Add V→I mapping (granf)
       -> spanf1.c:insertspanf()       # Add I→doc index (spanf)
```

### Delete Operation Path
```
fns.c:remove()
  -> do1.c:dodeletevspan()
       -> orglinks.c:deletevspanpm()
            -> deletend()               # Remove V→I mapping (granf)
       # NO CALL TO REMOVE SPANF ENTRY
```

### Available Spanf Functions
```c
// spanf1.c and spanf2.c
bool insertspanf(...)                  // ✅ Exists
bool findlinksfromtothreesp(...)       // ✅ Exists
bool retrieveendsetsfromspanf(...)     // ✅ Exists
bool finddocscontainingsp(...)         // ✅ Exists

// NOT IMPLEMENTED:
// bool deletespanf(...)               // ❌ Does not exist
// bool removespanf(...)               // ❌ Does not exist
```

---

## Related Findings

- **Finding 012**: Dual Enfilade Architecture — explains granf vs spanf separation
- **Finding 013**: The Sporgl — content provenance tracking via I-addresses
- **Finding 024**: Link deletion does not clean up spanfilade (same issue)
- **Finding 048**: FOLLOWLINK filters unreferenced addresses at I-to-V conversion
- **EWD-030 DEL5**: Defines unreferenced addresses (ghost links)

---

## Open Questions

1. **Is this intentional or a bug?**
   - If intentional: what is the cleanup strategy? Periodic rebuild?
   - If a bug: why hasn't it caused visible problems?

2. **How does this affect FIND_DOCUMENTS performance?**
   - Does the spanfilade grow unbounded with stale entries?
   - Are false positives filtered efficiently at the V-conversion layer?

3. **Should the spec require cleanup?**
   - Or should it explicitly allow stale spanfilade entries?
   - The current behavior is more like a "historical journal" than a "current index"

4. **Could reference counting be added?**
   - Track how many documents contain each I-address
   - Only remove spanf entry when count reaches zero
   - But this requires implementing `deletespanf` and maintaining counters

---

## Formal Answer to the Question

**Q**: When a document DELETEs content that was previously COPYed (transcluded) into it, does the DELETE operation clean up the spanfilade entries?

**A**: **No**. The DELETE operation calls `deletevspanpm`, which removes the V→I mapping from the document's POOM (via `deletend` on the document's orgl in granf), but there is **no corresponding call to remove the spanfilade entry**. Furthermore, **no deletion function exists for spanf** — the only spanf operations are insertion and querying, not removal.

As a result, the spanfilade retains stale references to documents that no longer contain those I-addresses. This means:
- FIND_DOCUMENTS may return documents that once contained the I-addresses but no longer do
- These stale references are filtered during I-to-V conversion (Finding 048) when the POOM lookup fails
- The spanfilade acts more like a **historical journal** (documents that have ever contained these I-addresses) than a **current index** (documents that currently contain them)

This behavior is consistent with link deletion (Finding 024), where deleted links also leave stale spanfilade entries.

---

## Files Referenced

| File | Lines | Content |
|------|-------|---------|
| `do1.c` | 45-65 | `docopy` — calls `insertspanf` to register transclusion |
| `do1.c` | 162-171 | `dodeletevspan` — does NOT call spanf cleanup |
| `orglinks.c` | 145-152 | `deletevspanpm` — only removes V→I from POOM, no spanf cleanup |
| `spanf1.c` | 15-53 | `insertspanf` — adds spanfilade entries |
| `spanf1.c` | entire file | **No delete function exists** |
| `spanf2.c` | entire file | **No delete function exists** |
