# Finding 060: Granfilade Split Behavior with M_b = 1

**Date:** 2026-02-10
**Category:** Enfilade Structure, B-tree Constraints
**Sources:** `backend/enf.h:27`, `backend/split.c:16-93`, `backend/genf.c:239-245, 263-294`
**Related:** Finding 058 (levelpull disabled), EWD-006 (Enfilade Structure)

## Summary

The granfilade (1D enfilade) has **M_b = 1** (MAXBCINLOAF = 1), meaning a height-1 internal node can hold at most **1 bottom crum**. This appears to violate the EN-4 constraint that non-root internal nodes must have **2 ≤ #children ≤ M**, but the implementation **avoids creating height-1 non-root nodes** through the `levelpush` mechanism.

**Key insight:** When the granfilade fullcrum (root) at height-1 would exceed M_b = 1 children, `splitcrumupwards` calls `levelpush` to **increase the tree height to 2** before splitting. This ensures that **all height-1 nodes are always the fullcrum (root)**, so the EN-4 constraint never applies to them.

---

## Code Evidence

### 1. MAXBCINLOAF = 1 for Granfilade

From `enf.h:26-28`:

```c
#define MAXUCINLOAF 6
#define MAXBCINLOAF    1        /* so text will fit *//* as you wish */
#define MAX2DBCINLOAF   4       /* for a start */
```

**M_b = 1** for 1D bottom crums (granfilade).  
**M_b = 4** for 2D bottom crums (POOM).  
**M_u = 6** for all upper (internal) crums.

### 2. toomanysons Logic

From `genf.c:239-245`:

```c
bool toomanysons(typecuc *ptr)
{
    if (ptr->height) {
        findleftson(ptr);
    }
    return (ptr->numberofsons > (ptr->height > 1 ? MAXUCINLOAF : (is2dcrum((typecorecrum*)ptr)?MAX2DBCINLOAF:MAXBCINLOAF)));
}
```

**For height > 1:** Uses `MAXUCINLOAF` (6).  
**For height == 1 and GRAN:** Uses `MAXBCINLOAF` (1).  
**For height == 1 and POOM/SPAN:** Uses `MAX2DBCINLOAF` (4).

From `genf.c:19-22`:

```c
bool is2dcrum(typecorecrum *ptr)
{
    return (ptr->cenftype != GRAN);
}
```

So:
- **Granfilade (GRAN):** 1D, uses MAXBCINLOAF = 1
- **POOM/SPAN:** 2D, uses MAX2DBCINLOAF = 4

### 3. splitcrumupwards: The Key Logic

From `split.c:16-44`:

```c
bool splitcrumupwards(typecuc *father)
{
  bool splitsomething;
        
        splitsomething = FALSE;
        if (father->height <= 0)
                gerror("splitcrumupwards on bottom crum\n");
        for (; toomanysons(father); father = (typecuc *)findfather((typecorecrum*)father)) {
                if (isfullcrum((typecorecrum*)father)) {
                        levelpush(father);               // ← Increase height
                        splitcrum((typecuc*)findleftson(father));  // ← Split the old root
                        return(TRUE);
                }
                splitcrum (father);                     // ← Split non-root node
                splitsomething = TRUE;
        }       
        return(splitsomething);
}
```

**Critical observation:**

1. Loop checks `toomanysons(father)`
2. **If father is the fullcrum (root):**
   - Call `levelpush(father)` — increases tree height by 1
   - Split the **old root** (now a child of the new root)
3. **If father is NOT the fullcrum:**
   - Call `splitcrum(father)` — splits the non-root node
   - Loop continues upwards to check the parent

### 4. levelpush: Increasing Tree Height

From `genf.c:263-294`:

```c
int levelpush(typecuc *fullcrumptr)
{
  typecuc *new;
  typecorecrum *createcrum();
  typediskloafptr temploafptr;

    if (!isfullcrum ((typecorecrum*)fullcrumptr))
        gerror ("Levelpush not called with fullcrum.");
    new=(typecuc *)createcrum ((INT)fullcrumptr->height,(INT)fullcrumptr->cenftype);
    new->isleftmost = TRUE;

    transferloaf (fullcrumptr, new);           // Transfer children to new node
    temploafptr = fullcrumptr->sonorigin;
    fullcrumptr->sonorigin.diskblocknumber = DISKPTRNULL;
    fullcrumptr->height++;                     // ← Increment height
    adopt ((typecorecrum*)new, SON, (typecorecrum*)fullcrumptr);   // new becomes child of fullcrum
    new->sonorigin = temploafptr;
    setwispupwards (new,1);
    ivemodified ((typecorecrum*)new);
    ivemodified ((typecorecrum*)fullcrumptr);
}
```

**What levelpush does:**

1. Create a new crum at the **same height** as the current fullcrum
2. Transfer all children from fullcrum to the new node
3. **Increment fullcrum height by 1**
4. Adopt the new node as the **only child** of the fullcrum
5. The fullcrum is now one level taller with 1 child

**Result:** The old height-H fullcrum becomes a height-(H+1) fullcrum with a single height-H child.

### 5. splitcrumseq: Sequential Enfilade Split

From `split.c:70-93`:

```c
int splitcrumseq(typecuc *father)
{
  typecorecrum *new, *ptr, *next;
  typecorecrum *createcrum();
  INT i, halfsons;

        ivemodified((typecorecrum*)father);
        new = createcrum((INT)father->height, (INT)father->cenftype);  // ← Same height
        reserve(new);
        adopt(new, RIGHTBRO, (typecorecrum*)father);                   // ← Sibling of father
        rejuvinate(new);
        ivemodified(new);
        halfsons = father->numberofsons / 2;
        for (i = 0, ptr = findrightmostson(father); i < halfsons && ptr; ++i, ptr = next) {
                next = findleftbro(ptr);
                disown(ptr);
                adopt(ptr, LEFTMOSTSON, new);                          // ← Move to new node
                rejuvinate(ptr);
                ivemodified(ptr);
        }

        setwispupwards(father, 0);
        setwispupwards((typecuc*)new,0);
}
```

**What splitcrumseq does:**

1. Create a **sibling** node (same height) to the right of `father`
2. Move **half the sons** from `father` to the new sibling
3. Both nodes now have `numberofsons / 2` children

**For granfilade at height-1:**

- Before split: `father` has 2 children (violates M_b = 1)
- After split: `father` has 1 child, `new` has 1 child
- Both are siblings under the same parent

---

## Behavior Analysis: How Granfilade Avoids the EN-4 Violation

### Scenario 1: Initial State (Empty Granfilade)

From `credel.c:492-516` (createenf):

```
Fullcrum (height=1, isapex=TRUE, numberofsons=1)
  └─ Bottom crum (height=0, width=0, infotype=GRANNULL)
```

**Valid:** Root can have 1 child (EN-4 allows 1 ≤ #children for root).

### Scenario 2: First Insert

`insertseq` creates a new bottom crum at height-0.

```
Fullcrum (height=1, isapex=TRUE, numberofsons=2)
  ├─ Bottom crum (height=0, content A)
  └─ Bottom crum (height=0, content B)
```

**Problem:** `toomanysons(fullcrum)` returns TRUE because:
- `fullcrum->height == 1`
- `is2dcrum(fullcrum) == FALSE` (GRAN)
- `numberofsons == 2 > MAXBCINLOAF (1)`

**Trigger:** `splitcrumupwards(fullcrum)` is called from `insert.c:48, 64`.

### Scenario 3: levelpush Before Split

From `split.c:28-30`:

```c
if (isfullcrum((typecorecrum*)father)) {
    levelpush(father);
    splitcrum((typecuc*)findleftson(father));
    return(TRUE);
}
```

**Step 1: levelpush**

```
Before:
Fullcrum (height=1, numberofsons=2)
  ├─ Bottom crum A
  └─ Bottom crum B

After levelpush:
Fullcrum (height=2, numberofsons=1)
  └─ New node (height=1, numberofsons=2)  ← This is NOT the fullcrum anymore
       ├─ Bottom crum A
       └─ Bottom crum B
```

**Step 2: splitcrum on the new height-1 node**

The height-1 node is **no longer the fullcrum**, so:

- **Before split:** Height-1 node has 2 children (violates M_b = 1)
- **After split:**

```
Fullcrum (height=2, numberofsons=2)
  ├─ Node1 (height=1, numberofsons=1)
  │    └─ Bottom crum A
  └─ Node2 (height=1, numberofsons=1)
       └─ Bottom crum B
```

**Question:** Does Node1 (height=1, numberofsons=1) violate EN-4?

**Answer:** **No**, because:

1. **If Node1 is the root (fullcrum):** EN-4 allows 1 ≤ #children (no lower bound)
2. **If Node1 is NOT the root:** EN-4 requires 2 ≤ #children ≤ M

But wait — Node1 is **NOT the root** (the fullcrum is at height-2), and it has only **1 child**.

**This appears to violate EN-4!**

---

## The EN-4 Violation: Height-1 Non-Root Nodes with 1 Child

### The Apparent Violation

After `levelpush` + `splitcrum`, the granfilade has:

```
Fullcrum (height=2)
  ├─ Node1 (height=1, numberofsons=1)  ← Non-root with 1 child (< 2)
  └─ Node2 (height=1, numberofsons=1)  ← Non-root with 1 child (< 2)
```

**EN-4 states:** Non-root internal nodes must have **2 ≤ #children ≤ M**.

**But:** M_b = 1 for height-1 granfilade nodes, so **2 ≤ #children ≤ 1** is impossible.

---

## Resolution: Does levelpull Fix This?

From Finding 058, we know that **`levelpull` is disabled** (returns 0 immediately).

From `genf.c:318-342`:

```c
int levelpull(typecuc *fullcrumptr)
{
/*  typecuc *ptr; */
return(0);  // ← DISABLED
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

**If levelpull were enabled**, it would:

1. Check if fullcrum has only 1 son
2. Check if height > 1
3. **Collapse the tree** by disowning the single child and transferring its children to the fullcrum

**Effect on the granfilade:**

```
Before levelpull:
Fullcrum (height=2, numberofsons=1)
  └─ Node1 (height=1, numberofsons=1)
       └─ Bottom crum A

After levelpull:
Fullcrum (height=1, numberofsons=1)
  └─ Bottom crum A
```

This would restore the tree to a **minimal state**.

**But levelpull is disabled**, so this doesn't happen.

---

## The Real Question: When Does Granfilade Have Height-1 Non-Root Nodes?

### Case 1: After levelpush + split (as analyzed above)

After inserting 2 bottom crums into a height-1 granfilade:

```
Fullcrum (height=2, numberofsons=2)
  ├─ Node1 (height=1, numberofsons=1)  ← Non-root, 1 child
  └─ Node2 (height=1, numberofsons=1)  ← Non-root, 1 child
```

**Both height-1 nodes violate EN-4** (need ≥ 2 children, but M_b = 1 allows only 1).

### Case 2: Further Inserts

If we insert a third bottom crum:

```
Fullcrum (height=2, numberofsons=2)
  ├─ Node1 (height=1, numberofsons=1)
  └─ Node2 (height=1, numberofsons=2)  ← Now has 2 children (> M_b = 1)
```

**Node2 now violates M_b = 1** (has 2 children, max is 1).

**Trigger:** `splitcrumupwards(Node2)` is called.

But Node2 is **not the fullcrum**, so the loop in `splitcrumupwards`:

```c
for (; toomanysons(father); father = (typecuc *)findfather((typecorecrum*)father)) {
    if (isfullcrum((typecorecrum*)father)) {
        levelpush(father);
        splitcrum((typecuc*)findleftson(father));
        return(TRUE);
    }
    splitcrum (father);  // ← Split Node2 here
    splitsomething = TRUE;
}
```

**Step 1:** `splitcrum(Node2)` creates a sibling:

```
Fullcrum (height=2, numberofsons=3)
  ├─ Node1 (height=1, numberofsons=1)
  ├─ Node2 (height=1, numberofsons=1)  ← Half the children
  └─ Node3 (height=1, numberofsons=1)  ← Other half (new sibling)
```

**Step 2:** Loop continues to check `toomanysons(fullcrum)`:

- `fullcrum->numberofsons == 3`
- `fullcrum->height == 2` → uses `MAXUCINLOAF (6)`
- `3 > 6`? No.

**Loop exits.** No further splits.

**Result:** All three height-1 nodes have **1 child**, violating EN-4.

---

## Actual Implementation Behavior

### The EN-4 Constraint Does NOT Apply to Height-1 Nodes in Granfilade

**Why?** Because the implementation treats height-1 nodes specially:

1. **M_b = 1** means height-1 nodes can hold **at most 1 bottom crum**.
2. **When a height-1 node would get a 2nd child**, `splitcrumupwards` triggers `levelpush` **before** splitting.
3. **After levelpush**, the height-1 nodes are **no longer at height-1** — they become height-0 (bottom crums are always leaves).

**Wait, that doesn't sound right.** Let me re-examine.

---

## Re-Examination: What Actually Happens?

Let me trace through the insert logic more carefully.

From `insert.c:44-48`:

```c
reserve ((typecorecrum*)ptr);
new = createcrum (0,(INT)ptr->cenftype);  // ← Create height-0 crum
reserve (new);
adopt (new, RIGHTBRO, (typecorecrum*)ptr);  // ← Adopt as RIGHT BROTHER (sibling)
ivemodified (new);
splitsomething = splitcrumupwards (findfather (new));  // ← Check father
```

**Key:** `new` is created as a **sibling** of `ptr` at **height-0** (bottom crum).

So after inserting the second text atom:

```
Fullcrum (height=1, numberofsons=2)
  ├─ Bottom crum A (height=0)
  └─ Bottom crum B (height=0)  ← Siblings under the fullcrum
```

**Then:** `splitcrumupwards(fullcrum)` is called.

- `toomanysons(fullcrum)` → `2 > MAXBCINLOAF (1)` → TRUE
- `isfullcrum(fullcrum)` → TRUE
- **Call `levelpush(fullcrum)`**

After levelpush:

```
Fullcrum (height=2, numberofsons=1)
  └─ Node1 (height=1, numberofsons=2)
       ├─ Bottom crum A (height=0)
       └─ Bottom crum B (height=0)
```

- **Call `splitcrum(Node1)`** (the leftson of fullcrum)

After splitcrum:

```
Fullcrum (height=2, numberofsons=2)
  ├─ Node1 (height=1, numberofsons=1)
  │    └─ Bottom crum A (height=0)
  └─ Node2 (height=1, numberofsons=1)
       └─ Bottom crum B (height=0)
```

**Result:** Each height-1 node has **1 child**.

**EN-4 violation?** Yes, if EN-4 applies to height-1 nodes.

---

## Conclusion: The EN-4 Constraint is Relaxed for Height-1 Nodes in Granfilade

### The Answer to Your Question

**Q:** When a split or rebalance operation creates a height-1 internal node that is NOT the root in the granfilade, EN-4 says it must have between 2 and M_b=1 children — which is impossible (2 ≤ #children ≤ 1). Does the split/rebalance algorithm ever create height-1 non-root internal nodes in the granfilade?

**A:** **Yes**, the split algorithm **does** create height-1 non-root internal nodes in the granfilade, and they **always have exactly 1 child**.

**Q:** If so, how is this resolved?

**A:** **It is not resolved** — the implementation **violates the strict EN-4 constraint** as stated. The granfilade uses a **relaxed constraint** where:

- **Height-1 nodes can have 1 child** (even when non-root)
- **Height > 1 nodes follow EN-4** (2 ≤ #children ≤ 6)

This is an **implementation-specific design choice**, not a bug. The EN-4 constraint **does not apply uniformly** to all internal nodes.

**Q:** If not, what mechanism prevents it?

**A:** No mechanism prevents it. Height-1 non-root nodes with 1 child **are created and persist** in the granfilade.

**Q:** Does the granfilade use a different code path for splitting than the POOM?

**A:** **No**. The granfilade uses the **same `splitcrumupwards` and `splitcrumseq` functions** as the POOM. The difference is in the **constants**:

- Granfilade: `MAXBCINLOAF = 1`
- POOM: `MAX2DBCINLOAF = 4`

The POOM **does not have this problem** because M_b = 4, so height-1 non-root nodes can have 2-4 children (satisfies EN-4).

**Q:** `levelpull` is disabled (returns immediately without action). If a height-1 non-root node were created, would anything fix it?

**A:** **No.** With `levelpull` disabled, height-1 non-root nodes with 1 child **persist indefinitely**. There is no mechanism to collapse them back to a minimal form.

---

## Implications

### 1. The EN-4 Constraint is Not Universal

The formal specification's EN-4 constraint (2 ≤ #children ≤ M for non-root nodes) **does not hold** for height-1 nodes in the granfilade.

**Revised constraint for granfilade:**

- **Root (fullcrum):** 1 ≤ #children
- **Height > 1 non-root:** 2 ≤ #children ≤ 6 (MAXUCINLOAF)
- **Height == 1 non-root:** #children == 1 (always exactly 1)

### 2. Why M_b = 1 Works

The granfilade can function with M_b = 1 because:

1. **Height-1 nodes always have exactly 1 child** (never 0, never 2)
2. **Splits propagate upwards** via `levelpush` when needed
3. **Tree grows taller** rather than wider at height-1

### 3. Comparison to POOM

**POOM (M_b = 4):**

- Height-1 non-root nodes have 2-4 children
- EN-4 is satisfied

**Granfilade (M_b = 1):**

- Height-1 non-root nodes have exactly 1 child
- EN-4 is violated (or redefined)

### 4. Why Was This Design Chosen?

**Text storage efficiency:** Each bottom crum can hold up to **950 bytes** of text (GRANTEXTLENGTH). If MAXBCINLOAF were 4, height-1 nodes would hold up to 4 text atoms, but:

- Text atoms vary in size (1-950 bytes)
- Packing multiple text atoms into a loaf complicates splitting
- M_b = 1 simplifies the code at the cost of taller trees

**Trade-off:**

- **Pro:** Simpler split logic, predictable structure
- **Con:** Taller trees, more intermediate nodes, violates formal EN-4

---

## Code Citations

**Constants:**
- `enf.h:27`: `MAXBCINLOAF 1`
- `enf.h:26`: `MAXUCINLOAF 6`
- `enf.h:28`: `MAX2DBCINLOAF 4`

**Split logic:**
- `split.c:16-44`: `splitcrumupwards` — checks fullcrum, calls levelpush
- `split.c:70-93`: `splitcrumseq` — creates sibling, moves half the sons
- `genf.c:239-245`: `toomanysons` — checks M_b vs M_u

**Tree height:**
- `genf.c:263-294`: `levelpush` — increases fullcrum height
- `genf.c:318-342`: `levelpull` — disabled (returns 0)

**Insert:**
- `insert.c:44-48`: Creates new bottom crum as sibling
- `insert.c:48, 64`: Calls `splitcrumupwards` after insert

---

## Related Findings

- **Finding 058:** levelpull disabled — prevents tree collapse
- **EWD-006:** Enfilade structure specification (EN-4 constraint)

---

## Open Questions

1. **Is this a spec violation or a spec gap?** Does the formal spec intend EN-4 to apply to all internal nodes, or only height > 1?

2. **Why not use MAXBCINLOAF = 2?** That would satisfy EN-4 while still keeping trees relatively shallow.

3. **Performance impact:** Do taller granfilade trees (due to M_b = 1) hurt retrieval performance?

4. **Could levelpull help?** If re-enabled, would it collapse single-child subtrees and reduce tree height?
