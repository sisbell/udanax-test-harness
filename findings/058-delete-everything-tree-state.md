# Finding 058: DELETE All Content Tree State — Disabled levelpull Prevents Collapse

**Date:** 2026-02-10
**Status:** Confirmed by code inspection
**Category:** Enfilade Structure, Tree Management
**Sources:** `backend/credel.c:492-516`, `backend/genf.c:318-342`, `backend/recombine.c:66-68, 129-131`, `backend/edit.c:31-76`
**Related:** EWD-006 (Enfilade Structure), Finding 053 (V-Position Shifts)

## Summary

When DELETE removes **all content** from a document (deleting the entire V-span), the resulting tree state is **NOT** the same as the initial empty enfilade created by `createenf(POOM)`. The difference is caused by **`levelpull` being disabled** — the function exists but immediately returns 0 without performing any tree collapse operation.

As a result:
- **Initial empty state**: Height-1 tree with one zero-width bottom node
- **After delete-everything**: Variable height tree (depends on prior operations) with all bottom nodes disowned but the upper structure remaining

The empty tree is **never collapsed back to height-1** because `levelpull` is a no-op.

---

## Code Evidence

### 1. Initial Empty Enfilade Creation

From `credel.c:492-516` (`createenf`):

```c
typecuc *createenf(INT enftype)
{
  typecuc *fullcrumptr;
  typecorecrum *ptr;

    fullcrumptr = (typecuc *) createcrum(1,enftype);  // ← Height-1 fullcrum
    fullcrumptr->cenftype = enftype;
    fullcrumptr->isapex = TRUE;
    fullcrumptr->isleftmost = TRUE;
    adopt(ptr = createcrum(0, enftype), SON, (typecorecrum*)fullcrumptr);
    if (enftype == GRAN) {
        ((typecbc *)ptr)->cinfo.infotype = GRANNULL;  // ← Zero-width null node
    }
    ivemodified  (ptr);
    return (fullcrumptr);
}
```

**Initial structure:**
```
Fullcrum (height-1, isapex=TRUE)
  └─ Bottom node (height-0, width=0, infotype=GRANNULL for GRAN)
```

For GRAN enfilades: the bottom node has `infotype=GRANNULL`, representing zero width.
For POOM/SPAN: the bottom node has zero width and zero displacement.

### 2. DELETE Operation

From `edit.c:31-76` (`deletend`):

```c
int deletend(typecuc *fullcrumptr, tumbler *origin, tumbler *width, INT index)
{
  typeknives knives;
  typewid offset, grasp, reach;
  typecuc *father, *ptr, *next;
  typewid foffset, fgrasp;

    clear (&offset, sizeof(offset));
    prologuend ((typecorecrum*)fullcrumptr, &offset, &grasp, &reach);
    movetumbler (origin, &knives.blades[0]);
    tumbleradd (origin, width, &knives.blades[1]);
    knives.nblades = 2;
    knives.dimension = index;
    makecutsnd (fullcrumptr, &knives);
    newfindintersectionnd (fullcrumptr, &knives, &father, &foffset);
    prologuend ((typecorecrum*)father, &foffset, &fgrasp, (typedsp*)NULL);
    for (ptr = (typecuc *) findleftson (father); ptr; ptr = next) {
        next = (typecuc *) findrightbro((typecorecrum*)ptr);
        switch (deletecutsectionnd ((typecorecrum*)ptr, &fgrasp, &knives)) {
          case -1:
            gerror ("deletend can't classify crum\n");
          case 0:
            break;
          case 1:
            disown ((typecorecrum*)ptr);         // ← Bottom nodes are disowned
            subtreefree ((typecorecrum*)ptr);    // ← And freed
            break;
          case 2:
            tumblersub (&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);
            break;
        }
    }
    setwispupwards (father,1);
    recombine (father);  // ← Calls recombine on the father node
}
```

**Key operations:**
1. **makecutsnd**: Creates cuts to isolate the deletion range
2. **Loop through sons**: Each bottom node in the deletion range:
   - **Case 1**: Node is entirely within deletion range → `disown` + `subtreefree`
   - **Case 0**: Node is outside deletion range → no change
   - **Case 2**: Node is after deletion range → shift V-position (Finding 053)
3. **setwispupwards**: Recalculate width/span upwards
4. **recombine**: Attempt to merge/clean up the tree

When **all content is deleted**, all bottom nodes match **Case 1** and are disowned/freed.

### 3. Recombine After Deletion

From `recombine.c:104-131` (`recombinend` for 2D enfilades like POOM):

```c
int recombinend(typecuc *father)
{

  typecorecrum *ptr;
  typecorecrum *sons[MAXUCINLOAF];
  INT i, j, n;
  bool ishouldbother();

    if (father->height < 2  || !father->modified)
        return(0);
    for (ptr = getleftson (father); ptr;ptr=(typecorecrum *)getrightbro (ptr)){
        recombinend (ptr);
    }

    getorderedsons (father, sons);
    n = father->numberofsons;
    for (i = 0; i < n-1; i++) {
        for (j = i+1; sons[i] && j < n; j++) {
            if(i != j && sons[j] && ishouldbother(sons[i],sons[j])){
                takeovernephewsnd (&sons[i], &sons[j]);
            }
        }
    }
    if (father->isapex)
        levelpull (father);  // ← Calls levelpull on the fullcrum
}
```

**Key observation**: `recombinend` only calls `levelpull` if `father->isapex` (i.e., the fullcrum).

### 4. levelpull Is Disabled

From `genf.c:318-342` (`levelpull`):

```c
int levelpull(typecuc *fullcrumptr)
{
/*  typecuc *ptr; */
return(0);  // ← DISABLED: immediately returns without doing anything
/*
    if (!isfullcrum (fullcrumptr))
        gerror ("Levelpull not called with fullcrum.");
    if (fullcrumptr->numberofsons > 1)
        return;
    if (fullcrumptr->height <= 1)
        return;
    ptr = (typecuc *) findleftson (fullcrumptr);
    dspadd (&fullcrumptr->cdsp, &ptr->cdsp, &fullcrumptr->cdsp, fullcrumptr->cenftype);

    disown (ptr);
    fullcrumptr->height--;
    transferloaf (ptr, fullcrumptr);
    setwispupwards (fullcrumptr,1);
    freecrum (ptr);
*/
}
```

**Critical finding**: The commented-out code shows what `levelpull` **should** do:
1. Check if fullcrum has only 1 son
2. Check if height > 1
3. Collapse the tree by one level:
   - Disown the single intermediate node
   - Decrement fullcrum height
   - Transfer the node's children to the fullcrum
   - Free the intermediate node

**But this code is disabled.** The function immediately returns 0.

---

## Behavior Analysis

### Case 1: Never-Filled Empty Document

```
createenf(POOM) produces:
  Fullcrum (height=1, numberofsons=1)
    └─ Bottom node (height=0, width=0, displacement=0)
```

### Case 2: After Inserting Content (Incremental Growth)

As content is added, the tree grows:
- Bottom nodes (height-0) store content mappings
- When a loaf overflows (MAXUCINLOAF or MAX2DBCINLOAF), `splitcrumupwards` is called
- If the fullcrum needs to split, `levelpush` increases tree height:

```c
int levelpush(typecuc *fullcrumptr)
{
  typecuc *new;
  // ...
    new=(typecuc *)createcrum ((INT)fullcrumptr->height,(INT)fullcrumptr->cenftype);
    new->isleftmost = TRUE;
    transferloaf (fullcrumptr, new);
    temploafptr = fullcrumptr->sonorigin;
    fullcrumptr->sonorigin.diskblocknumber = DISKPTRNULL;
    fullcrumptr->height++;  // ← Increment height
    adopt ((typecorecrum*)new, SON, (typecorecrum*)fullcrumptr);
    // ...
}
```

So after many inserts, the tree might look like:
```
Fullcrum (height=3, numberofsons=2)
  ├─ Height-2 node
  │    ├─ Height-1 node (many bottom nodes)
  │    └─ Height-1 node (many bottom nodes)
  └─ Height-2 node
       └─ Height-1 node (many bottom nodes)
```

### Case 3: After Deleting All Content

DELETE calls `disown` + `subtreefree` on all bottom nodes (height-0).

After all bottom nodes are removed:
```
Fullcrum (height=3, numberofsons=2)
  ├─ Height-2 node (numberofsons=0, leftson=NULL)
  └─ Height-2 node (numberofsons=0, leftson=NULL)
```

**Expected behavior** (if `levelpull` worked):
- Fullcrum has sons with `numberofsons=0`
- `recombinend` would call `levelpull`
- `levelpull` should detect height > 1 with no grandchildren, and collapse

**Actual behavior** (with `levelpull` disabled):
- Tree height remains at 3
- Intermediate nodes remain allocated but empty
- Tree structure is **not** collapsed back to height-1

---

## Comparison: Empty States

| State | Height | Structure | Sons of Fullcrum |
|-------|--------|-----------|------------------|
| **createenf(POOM)** | 1 | Fullcrum → 1 bottom node (zero-width) | 1 (bottom node) |
| **After delete-all** | 3+ | Fullcrum → intermediate nodes (empty) | 2+ (empty intermediate nodes) |

**Key difference**: The tree does **not** return to the initial empty form.

---

## Implications

### 1. Empty Trees Are Not Equivalent

A document that has **never had content** is structurally different from a document where **all content has been deleted**.

- Never-filled: Minimal height-1 tree
- Deleted-all: Taller tree with empty intermediate nodes

### 2. Reinsertion After Delete-All

When content is reinserted after deleting everything:
- The tree **reuses existing intermediate nodes** (if they have room)
- Or creates new nodes if needed
- The tree does **not** restart from the minimal height-1 form

### 3. Memory/Disk Usage

Empty intermediate nodes after delete-all:
- Remain allocated in memory (if modified=TRUE, they'll be written to disk)
- Waste tree structure space
- No cleanup/garbage collection for empty non-bottom nodes

### 4. Why Is levelpull Disabled?

Possible reasons:
1. **Incomplete implementation**: The commented-out code suggests it was planned but not finished
2. **Correctness concerns**: Perhaps collapsing the tree introduced bugs
3. **Performance trade-off**: Collapsing might be expensive, and empty trees are rare
4. **Disk I/O issues**: Collapsing might require rewriting many disk blocks

The comment `/*zzz...*/` patterns elsewhere suggest development notes — `levelpull` may have been disabled during debugging and never re-enabled.

### 5. Invariant Violations?

From EWD-006, the enfilade structure should maintain certain properties:
- **Minimality**: Tree should be as shallow as possible
- **Balance**: No unnecessary intermediate nodes

Disabled `levelpull` violates minimality — after delete-all, the tree is **not minimal**.

---

## Test Observations

From the test scenarios (pending execution):

**Scenario: `delete_all_content_simple`**
- Insert content → tree grows to height H
- Delete all content → all bottom nodes disowned
- Expected: `retrieve_vspanset` returns empty (zero-width)
- Expected: Tree height remains H (not collapsed to 1)
- Reinsert → should work, reuses existing structure

**Scenario: `delete_all_incrementally`**
- Incremental deletion (3 bytes, 3 bytes, 2 bytes)
- After last DELETE: same final state as deleting all at once
- Tree structure depends on prior splits, not deletion order

**Scenario: `empty_document_never_filled`**
- Baseline: `createenf(POOM)` produces height-1 tree
- First insert at 1.1 → may trigger `levelpush` if needed
- Initial structure is **minimal**

---

## Related Code: recombine Handling of Empty Nodes

From `recombine.c:150-163` (`ishouldbother`):

```c
bool ishouldbother(typecuc *dest, typecuc *src)
{
    ++noishouldbother;
    if(src->numberofsons == 0){
        if(src->sonorigin.diskblocknumber == DISKPTRNULL){
            check(src);  // ← Debugging check for empty in-core node
        }else{
            return(FALSE);
        }
    }
    if (dest->age == RESERVED || src->age == RESERVED)
        return (FALSE);
    return (dest->numberofsons + src->numberofsons <= (dest->height>1 ? MAXUCINLOAF : MAX2DBCINLOAF)&&randomness(.3));
}
```

**Observation**: `recombinend` checks for empty sons (`numberofsons == 0`) but only logs a check, it doesn't **remove** them.

From `recombine.c:194-202` (`takeovernephewsnd`):

```c
    if (bro->numberofsons)
        setwispupwards (bro,0);
    else {
        disown (bro);
        freecrum (bro);  // ← Empty bro nodes ARE freed during recombine
        *broptr = NULL;
    }
```

**Important**: `recombine` DOES free empty sibling nodes during merge operations.

So the question is: **why aren't empty intermediate nodes freed after delete-all?**

Answer: Because `recombinend` only merges **sibling pairs**. If the fullcrum has 2 empty sons, and they're both empty, `ishouldbother` may not trigger merging (because `numberofsons == 0` for both). The merge logic is designed for **consolidating sparse nodes**, not **removing completely empty levels**.

That's the job of `levelpull` — and it's disabled.

---

## Formal Answer to the Question

**Q**: When DELETE removes ALL content from a document (deleting the entire V-span), what is the resulting tree state? Does it return to the empty enfilade form (height-1, one zero-width bottom node) as created by `createenf(POOM)`?

**A**: **No**. The resulting tree state is **not** the same as the initial empty enfilade.

**Initial empty state** (`createenf(POOM)`):
- Height = 1
- Structure: Fullcrum → single bottom node (zero-width, GRANNULL for GRAN)

**After delete-everything**:
- Height = H (depends on prior insertions that caused tree growth via `levelpush`)
- Structure: Fullcrum → intermediate nodes (height 1 to H-1) with `numberofsons=0`
- All bottom nodes have been disowned and freed
- Intermediate nodes remain allocated but empty

**Why the difference?**

`levelpull` is **disabled** — the function immediately returns 0 without performing any tree collapse operation (`genf.c:318-342`). The commented-out code shows that `levelpull` was intended to:
1. Check if the fullcrum has only 1 son
2. Check if height > 1
3. Collapse the tree by disowning the single intermediate node, decrementing height, and transferring children

But this functionality is not active.

**Consequences:**
- Empty trees after delete-all retain their previous height
- Intermediate nodes remain allocated but have no children
- The tree is **not minimal** (violates enfilade minimality principle)
- Reinsertion after delete-all reuses the existing tall structure

**Is this a bug or a design choice?**

Likely **incomplete implementation** — the commented-out code and `/*zzz...*/` markers suggest `levelpull` was disabled during development, possibly due to correctness concerns or disk I/O issues, and never re-enabled.

---

## Citations

**Code References:**
- Initial empty: `credel.c:492-516` (createenf)
- Delete operation: `edit.c:31-76` (deletend)
- Recombine: `recombine.c:104-131` (recombinend)
- Disabled levelpull: `genf.c:318-342` (levelpull returns 0)
- Tree growth: `genf.c:263-294` (levelpush)
- Empty node handling: `recombine.c:150-163, 194-202`

**Related Findings:**
- Finding 053: V-position shifts during DELETE (tumblersub mechanics)
- Finding 057: Spanfilade entries not cleaned up on DELETE
- EWD-006: Enfilade structure specification

---

## Open Questions

1. **Why was levelpull disabled?** Was there a specific bug or correctness issue?
2. **Can we safely re-enable it?** What are the risks?
3. **Does this affect performance?** Do tall empty trees cause slowdowns?
4. **Disk space impact?** Do empty intermediate nodes get written to disk unnecessarily?
5. **Could recombine be enhanced?** Add logic to detect fully-empty levels and collapse them?

## Updates

- **2026-02-11**: Finding 064 confirms that the empty-after-delete state causes
  INSERT/VCOPY to crash (Bug 019). The crash was in `firstinsertionnd()` which
  assumed a bottom crum always exists. Fixed by creating a new bottom crum when
  `findleftson()` returns NULL. See Finding 064 for full analysis including the
  `reserve`/`rejuvinate` mismatch that complicated the fix.
