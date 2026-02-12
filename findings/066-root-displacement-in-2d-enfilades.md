# Finding 066: Root Node Displacement in 2D Enfilades

**Date:** 2026-02-11
**Category:** Enfilade Structure / POOM / Spanfilade
**Agent:** Gregory
**Related:** Finding 041 (Enfilade Insertion Order Dependency), Finding 052 (CREATELINK Shifts POOM Entries)

## Summary

In non-sequential (2D) enfilades like POOM and spanfilade, **the root node's displacement is NOT always zero**. The root's `cdsp` field dynamically reflects the **minimum tumbler address** across all content in the tree. When content is inserted at non-zero tumbler addresses (e.g., 2.1, 5.7), the root displacement adjusts upward to track this minimum, and children's displacements become **relative to the root**, not absolute.

This is fundamentally different from sequential enfilades (GRAN), where displacement represents a position offset and root displacement is always zero.

## Key Question Answered

**Q:** Is `grasp(root)` always zero, or can the root have a non-zero displacement?

**A:** For 2D enfilades (POOM, SPAN), `grasp(root)` is typically non-zero after the first insertion. The root's `cdsp` field tracks the minimum address across all content, making children's displacements relative rather than absolute.

## Code Evidence

### 1. Root Initialization: Displacement Starts at Zero

**File:** `/udanax-test-harness/backend/credel.c` lines 580-581

```c
typecorecrum *createcruminternal(INT crumheight, INT enftype, typecorecrum *allocated)
{
    // ...
    clear(&ptr->cdsp, sizeof(ptr->cdsp));  // All crums start with zero displacement
    clear(&ptr->cwid, sizeof(ptr->cwid));
    // ...
}
```

Every crum, including the root, is initialized with zero displacement.

### 2. First Insertion: Child Gets Absolute Position, Root Inherits It

**File:** `/udanax-test-harness/backend/insertnd.c` lines 199-218

```c
int firstinsertionnd(typecuc *father, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr)
{
    typecorecrum *ptr;

    ptr = findleftson (father);
    if (!ptr) {
        ptr = createcrum (0, (INT)father->cenftype);
        adopt (ptr, SON, (typecorecrum*)father);
    }
    movewisp (origin, &ptr->cdsp);    // Child's dsp = insertion position (e.g., 2.1)
    movewisp (width, &ptr->cwid);
    move2dinfo (infoptr, &((type2dcbc *)ptr)->c2dinfo);
    ivemodified (ptr);
    setwisp ((typecorecrum*)father);  // This updates the root!
    return(0);
}
```

**Critical insight:** The child's displacement is set to the **absolute insertion position** (e.g., if inserting at 2.1, the child gets `cdsp = 2.1`). Then `setwisp` is called on the root, which propagates this displacement upward.

### 3. Root Displacement Update: Tracks Minimum Child Position

**File:** `/udanax-test-harness/backend/wisp.c` lines 171-228

```c
bool setwispnd(typecuc *father)
{
    typecorecrum *ptr;
    typedsp newdsp, mindsp;
    typewid newwid,tempwid;

    if(father->height ==  0){
        return(FALSE);
    }

    if ((ptr = findleftson (father)) == NULL) {
        // All children deleted - clear width and mark modified
        clear (&father->cdsp, sizeof(father->cdsp));
        clear (&father->cwid, sizeof(father->cwid));
        ivemodified((typecorecrum*)father);
        return (TRUE);
    }

    // Find new upper-left corner (minimum displacement across all children)
    movewisp (&ptr->cdsp, &mindsp);
    for (ptr = getrightbro(ptr); ptr; ptr = getrightbro (ptr))   {
        lockmin ((tumbler*)&mindsp, (tumbler*)&ptr->cdsp, (tumbler*)&mindsp,
                 (unsigned)dspsize(ptr->cenftype));  // mindsp = min(child dsps)
    }

    lockiszerop = iszerolock((tumbler*)&mindsp, (unsigned)dspsize(father->cenftype));
    if(!lockiszerop){
        somethingchangedp = TRUE;
        dspadd (&father->cdsp, &mindsp, &newdsp, (INT)father->cenftype);  // Root dsp += mindsp
    }else{
        movewisp(&father->cdsp,&newdsp);
    }

    // Readjust children's dsps to be RELATIVE to new root displacement
    clear (&newwid, sizeof(newwid));
    for (ptr = findleftson (father); ptr; ptr = getrightbro (ptr)) {
        if (!lockiszerop) {
            ptr->modified = TRUE;
            dspsub(&ptr->cdsp, &mindsp, &ptr->cdsp, (INT)ptr->cenftype);  // Child becomes relative!
        }
        lockadd((tumbler*)&ptr->cdsp, (tumbler*)&ptr->cwid, (tumbler*)&tempwid,
                (unsigned)widsize(ptr->cenftype));
        lockmax((tumbler*)&newwid, (tumbler*)&tempwid, (tumbler*)&newwid,
                (unsigned)widsize(ptr->cenftype));
    }

    if(!somethingchangedp){
        return (FALSE);
    }
    movewisp (&newdsp, &father->cdsp);  // Root now has non-zero displacement!
    movewisp (&newwid, &father->cwid);
    ivemodified((typecorecrum*)father);
    return (TRUE);
}
```

**Critical operation at line 211:**
```c
dspsub(&ptr->cdsp, &mindsp, &ptr->cdsp, (INT)ptr->cenftype);
```

After finding the minimum displacement across all children, the root **absorbs** that minimum into its own `cdsp`, and all children's displacements are **adjusted downward** by subtracting the minimum. This makes children's displacements **relative to the root**.

### 4. Grasp Calculation: Offset + Displacement

**File:** `/udanax-test-harness/backend/retrie.c` lines 334-339

```c
/* sets grasp & reach from ptr & offset */
int prologuend(typecorecrum *ptr, typedsp *offset, typedsp *grasp, typedsp *reach)
{
    dspadd (offset, &ptr->cdsp, grasp, (INT)ptr->cenftype);  // grasp = offset + dsp
    if (reach)
        dspadd (grasp, &ptr->cwid, reach, (INT)ptr->cenftype);
}
```

When retrieving from the root (where `offset = 0`), the grasp equals the root's displacement:
```
grasp(root) = 0 + root.cdsp = root.cdsp
```

## Concrete Example: Inserting at 2.1

**Scenario:** Empty POOM, insert first link orgl reference at position 2.1.

### Step 1: First Insertion
```
firstinsertionnd() is called with origin = {V: 2.1, I: <some iaddr>}

Child (bottom crum):
  cdsp.dsas[V] = 2.1    (absolute position)
  cdsp.dsas[I] = <some iaddr>
  cwid.dsas[V] = 1      (width 1 in V-dimension)
  cwid.dsas[I] = <width in I-dimension>
```

### Step 2: Root Update via setwispnd()
```
setwispnd(root) is called:
  1. mindsp = child.cdsp = 2.1 (only one child, so it's the minimum)
  2. mindsp is non-zero, so:
     root.cdsp = root.cdsp + mindsp = 0 + 2.1 = 2.1
  3. Child's displacement is adjusted:
     child.cdsp = child.cdsp - mindsp = 2.1 - 2.1 = 0
```

### Final State
```
Root:
  cdsp.dsas[V] = 2.1    (tracks minimum address)
  cwid.dsas[V] = 1      (computed from child: 0 + 1 = 1)

Child:
  cdsp.dsas[V] = 0      (relative to root)
  cwid.dsas[V] = 1      (unchanged)

Grasp calculation:
  grasp(root) = offset + root.cdsp = 0 + 2.1 = 2.1
  grasp(child) = root.cdsp + child.cdsp = 2.1 + 0 = 2.1
```

The content spans from 2.1 to 2.2 in V-space, as expected.

## Why This Design?

### 1. Efficient Bounding Box
The root's `cdsp` and `cwid` together form a **bounding box** for all content:
- `root.cdsp` = upper-left corner (minimum address)
- `root.cdsp + root.cwid` = lower-right corner (maximum address)

This allows quick checks like "does this enfilade contain any content in range X to Y?"

### 2. Relative Addressing Stability
By making children's displacements relative to the root, the system can:
- Shift the entire tree's coordinate system by updating just the root
- Handle sparse address spaces efficiently (e.g., links at 2.1, 2.5, 2.9 don't need intermediate zero-width gaps)

### 3. Empty Enfilade Detection

**File:** `/udanax-test-harness/backend/genf.c` lines 97-116

```c
bool isemptyenfilade(typecuc *ptr)
{
    if (!isfullcrum((typecorecrum*)ptr))
        return (FALSE);
    switch (ptr->cenftype) {
      case GRAN :
        return (iszerolock(ptr->cwid.dsas, (unsigned)widsize(ptr->cenftype)));
      case SPAN :
      case POOM :
        return (
           iszerolock(ptr->cwid.dsas, (unsigned)widsize(ptr->cenftype))
        && iszerolock(ptr->cdsp.dsas, (unsigned)dspsize(ptr->cenftype)));
      default :
        return (gerror("isempytenfilade - bad enftype"));
    }
}
```

For 2D enfilades, an empty enfilade is detected by checking if **both** width and displacement are zero. This is consistent with the behavior that when all children are deleted, `setwispnd` clears both fields (line 187-189 of wisp.c).

## Implications for Understanding the System

### 1. Displacement Has Different Semantics by Enfilade Type

| Enfilade Type | Root Displacement | Child Displacement | Semantic Meaning |
|---------------|-------------------|--------------------|--------------------|
| GRAN (1D)     | Always 0          | Absolute position  | Sequential offset |
| POOM (2D)     | Minimum address   | Relative to root   | Coordinate transformation |
| SPAN (2D)     | Minimum address   | Relative to root   | Coordinate transformation |

### 2. Grasp Is NOT Always Zero at Root

When you call `prologuend(root, offset, &grasp, &reach)` with `offset = 0`:
```
grasp = 0 + root.cdsp
```

For 2D enfilades, this is typically the minimum address in the tree, not zero.

### 3. Insertions Can Change Root Displacement

When inserting at a position **less than** the current root displacement:
1. The new child gets an absolute position
2. `setwispnd` finds the new minimum across all children
3. The root's displacement increases to this new minimum
4. **All existing children's displacements decrease** (they become more negative relative to the new root)

Example:
```
Initial state: content at 5.0, root.cdsp = 5.0
Insert at 2.0:
  - New child.cdsp = 2.0
  - setwispnd finds mindsp = 2.0
  - root.cdsp = 2.0
  - Old child.cdsp = 5.0 - 2.0 = 3.0 (now relative!)
```

### 4. This Explains makegappm Behavior

**File:** `/udanax-test-harness/backend/insertnd.c` line 162

```c
case 1:/*9-17-87 fix */
    tumbleradd(&ptr->cdsp.dsas[V],&width->dsas[V],&ptr->cdsp.dsas[V]);
    ivemodified (ptr);
    break;
```

When `makegappm` shifts crums that come AFTER an insertion point, it's shifting their **relative displacements**. The subsequent call to `setwispupwards` recalculates the root's displacement and may adjust all children again.

## Testing Strategy

To verify this behavior, one would need to:

1. **Dump tree structure after insertions** - Check root.cdsp values at different states
2. **Insert at non-contiguous positions** - e.g., 2.1, 2.5, 2.9 and observe root.cdsp = 2.1
3. **Insert before existing content** - e.g., insert at 1.5 when content exists at 2.1, verify root.cdsp becomes 1.5
4. **Delete leftmost content** - Verify root.cdsp updates to next minimum

These tests would require either:
- Backend debugging with gdb/lldb to inspect crum structures
- Adding debug output to the C code
- Modifying the backend to expose internal tree structure

The FEBE protocol does not provide visibility into internal enfilade structure, so this finding is based on **source code analysis** rather than behavioral testing.

## Comparison with Sequential Enfilades (GRAN)

For GRAN enfilades, displacement has a different meaning:

**File:** `/udanax-test-harness/backend/wisp.c` lines 150-168

```c
bool setwidseq(typecuc *father)
{
    typecorecrum *ptr;
    typewid sum;

    if (father->height == 0) {
        return (FALSE);
    }
    clear (&sum, sizeof (sum));
    for (ptr = findleftson (father); ptr; ptr = getrightbro (ptr)){
        widopseq (&sum, &ptr->cwid, &sum);  // Sum widths, NOT min/max displacements
    }
    if (lockeq (sum.dsas, father->cwid.dsas, (unsigned)widsize(father->cenftype)))
        return (FALSE);
    movewisp (&sum, &father->cwid);
    ivemodified ((typecorecrum*)father);
    return (TRUE);
}
```

GRAN uses **widdative summation** (adding widths), not displacement tracking. The root's width is the sum of children's widths, and displacement remains zero.

## Formal Specification Implications

### EWD Model Should Clarify

1. **Root invariant for 2D enfilades:**
   ```
   root.cdsp = min({child.cdsp + parent_offset(child) | child in all_descendants})
   ```

2. **Grasp at root:**
   ```
   grasp(root) = root.cdsp  (for 2D enfilades)
   grasp(root) = 0          (for 1D enfilades)
   ```

3. **Child displacement interpretation:**
   ```
   absolute_position(child) = sum_of_ancestor_displacements(child) + child.cdsp
   ```

### Invariant: Relative Addressing

For any 2D enfilade crum with father:
```
absolute_grasp(crum) = absolute_grasp(father) + crum.cdsp
```

This holds recursively up to the root, where:
```
absolute_grasp(root) = root.cdsp
```

## Open Questions

1. **Does root.cdsp ever decrease?** When the minimum-address content is deleted, does the root's displacement drop to the next minimum, or does it stay at the old value?

2. **What happens with very sparse addressing?** If content exists at 2.1 and 1000.1, does root.cdsp = 2.1 and child.cdsp = 998.0? Are there overflow risks?

3. **Is there a performance implication?** Does non-zero root displacement affect retrieval performance, or is it purely a storage optimization?

4. **Why was this design chosen over absolute coordinates?** Was it for compression (avoiding large absolute addresses), or for some other structural reason?

## References

- `/udanax-test-harness/backend/credel.c:580-581` — `createcruminternal` initializes all crums with zero displacement
- `/udanax-test-harness/backend/insertnd.c:199-218` — `firstinsertionnd` sets child to absolute position, then updates root
- `/udanax-test-harness/backend/wisp.c:171-228` — `setwispnd` implements min-tracking and relative adjustment
- `/udanax-test-harness/backend/retrie.c:334-339` — `prologuend` computes grasp as offset + displacement
- `/udanax-test-harness/backend/genf.c:97-116` — `isemptyenfilade` checks both width and displacement for 2D enfilades
- `/udanax-test-harness/backend/wisp.c:150-168` — `setwidseq` shows different behavior for GRAN (1D) enfilades

## Architectural Significance

This finding reveals that **2D enfilades use coordinate transformations** rather than absolute addressing. The root acts as an **origin** for the entire tree's coordinate system, and all descendants use relative coordinates. This is fundamentally different from the sequential (GRAN) case, where the root is always at position zero and children use absolute widths.

Understanding this is critical for:
1. **Debugging POOM issues** - Expecting zero root displacement will lead to confusion
2. **Formal verification** - The invariant `grasp(root) = 0` does NOT hold for 2D enfilades
3. **Performance analysis** - Insertions may cause cascading displacement adjustments
4. **Concurrency reasoning** - Multiple insertions could cause "displacement races" where the root's minimum keeps changing
