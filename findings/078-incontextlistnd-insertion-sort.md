# Finding 078: incontextlistnd Performs Insertion-Sort by V-Address

**Date:** 2026-02-15
**Status:** Validated (code analysis)
**Category:** Retrieval Order Semantics

## Summary

`incontextlistnd` [context.c:75-111] performs **explicit insertion-sort by V-address** as contexts are discovered during tree traversal. The V-ordering of query results comes from this sorting algorithm, NOT from tree traversal order alone.

## Question Investigated

In the CREATENEWVERSION code path, `docreatenewversion` calls `docopyinternal` which calls `specset2ispanset`. The retrieval of source content goes through `retrieverestricted` → `findcbcinarea2d`.

**Question:** Does `incontextlistnd` perform insertion-sort by V-address (`grasp.dsas[index]`) as contexts are discovered during tree traversal? Or does V-ordering arise from tree traversal order alone?

## Implementation Analysis

### Code Path

The call chain for I→V mapping (e.g., `ispan2vspanset`) is:

1. `ispan2vspanset()` → [orglinks.c:389-394]
2. `permute()` → [orglinks.c:404-422]
3. `span2spanset()` → [orglinks.c:425-454]
4. `retrieverestricted()` → [retrie.c:56-85]
5. `retrieveinarea()` → [retrie.c:87-110]
6. `findcbcinarea2d()` → [retrie.c:229-268]
7. **`incontextlistnd()`** → [context.c:75-111]

### Tree Traversal in `findcbcinarea2d`

```c
// retrie.c:252-265
for (; crumptr; crumptr = getrightbro (crumptr)) {
    if (!crumqualifies2d (...)) {
        continue;
    }
    if (crumptr->height != 0) {
        // Recurse into subtree
        findcbcinarea2d (findleftson ((typecuc*)crumptr), &localoffset, ...);
    } else {
        // Leaf node: create context and add to result list
        context = makecontextfromcbc ((typecbc*)crumptr, (typewid*)offsetptr);
        incontextlistnd (headptr, context, index1);  // ← KEY LINE
    }
}
```

Tree traversal proceeds **left-to-right** through siblings (`getrightbro`), recursing depth-first. Contexts are discovered in **tree structure order**, which depends on:
- Insertion order (see Finding 041)
- Split/rebalance operations (see Finding 071)
- Diagonal ordering in 2D enfilades

### Insertion-Sort Algorithm in `incontextlistnd`

```c
// context.c:75-111
int incontextlistnd(typecontext **clistptr, typecontext *c, INT index)
{
  typecontext *clist, *nextc;
  typedsp grasp;

    prologuecontextnd (c, &grasp, (typedsp*)NULL);  // Extract c's V-address
    c->nextcontext = NULL;
    clist = *clistptr;

    // CASE 1: First insertion
    if (!clist) {
        *clistptr = c;
        return(0);
    }

    // CASE 2: Insert at beginning
    if (whereoncontext (clist, &grasp.dsas[index], index) < THRUME) {
        c->nextcontext = clist;
        *clistptr = c;
        return(0);
    } else {
        // CASE 3: Find insertion point in middle
        for (; nextc = clist->nextcontext; clist = nextc) {
            if ((whereoncontext (clist, &grasp.dsas[index], index) > ONMYLEFTBORDER)
                && (whereoncontext (nextc, &grasp.dsas[index], index) < ONMYLEFTBORDER)) {
                c->nextcontext = nextc;
                clist->nextcontext = c;
                return(0);
           }
        }
    }
    // CASE 4: Append to end
    c->nextcontext = NULL;
    clist->nextcontext = c;
}
```

### Comparison Logic: `whereoncontext`

```c
// context.c:124-149
INT whereoncontext(register typecontext *ptr, tumbler *address, INT index)
{
  tumbler left, right;

    switch (ptr->contexttype) {
      case POOM:
        movetumbler (&ptr->totaloffset.dsas[index], &left);
        tumbleradd (&left, &ptr->contextwid.dsas[index], &right);
        break;
      // ... other cases ...
    }
    return (intervalcmp (&left, &right, address));
}
```

This computes the interval `[left, right)` for the context in dimension `index`, then calls `intervalcmp` [retrie.c:401-418]:

```c
intervalcmp (left, right, address)
  tumbler *left, *right, *address;
{
  register INT cmp;

    cmp = tumblercmp (address, left);
    if (cmp == LESS)
        return (TOMYLEFT);      // -2
    else if (cmp == EQUAL)
        return (ONMYLEFTBORDER);  // -1
    cmp = tumblercmp (address, right);
    if (cmp == LESS)
        return (THRUME);          //  0  (inside interval)
    else if (cmp == EQUAL)
        return (ONMYRIGHTBORDER); //  1
    else
        return (TOMYRIGHT);       //  2
}
```

### Insertion-Sort Invariant

The algorithm maintains the invariant that contexts in the linked list are **sorted by their left boundary** in dimension `index`:

```
∀ contexts c1, c2 where c1 precedes c2 in the list:
  c1.totaloffset.dsas[index] ≤ c2.totaloffset.dsas[index]
```

**Proof sketch:**
- Case 2 (line 90): Insert at beginning if `whereoncontext(clist, &grasp.dsas[index], index) < THRUME`
  - This means `grasp.dsas[index] < clist.left`, so new context goes before current head
- Case 3 (lines 98-99): Insert between `clist` and `nextc` if:
  - `whereoncontext(clist, &grasp.dsas[index], index) > ONMYLEFTBORDER` → `grasp > clist.left`
  - `whereoncontext(nextc, &grasp.dsas[index], index) < ONMYLEFTBORDER` → `grasp < nextc.left`
  - Therefore: `clist.left < grasp < nextc.left`
- Case 4 (lines 109-110): Append to end if all existing contexts are before the new one

## Behavioral Consequence

**V-ordering of retrieval results is independent of tree traversal order.**

Even if the POOM B-tree structure places contexts in a different order due to:
- Out-of-order insertion (e.g., insert at 1.30, then 1.20, then 1.40)
- Split/rebalance operations reordering siblings
- Diagonal ordering in 2D enfilades (Finding 071)

The `incontextlistnd` function will **re-sort** them into V-address order before returning results to the caller.

### Example Scenario

Suppose internal transclusion creates POOM entries for the same I-address at V-positions 1.10, 1.30, 1.20, 1.40 (inserted in that order). The POOM B-tree might store them as:

```
Tree structure (left-to-right siblings):
  Context(V=1.10) → Context(V=1.30) → Context(V=1.20) → Context(V=1.40)
```

But `findcbcinarea2d` with `index1 = SPANRANGE` (V-dimension) will call `incontextlistnd` for each, producing:

```
Sorted result list:
  Context(V=1.10) → Context(V=1.20) → Context(V=1.30) → Context(V=1.40)
```

## Contrast with Sequential Retrieval

For comparison, `oncontextlistseq` [context.c:113-123] does NOT sort:

```c
int oncontextlistseq(typecontext **clistptr, typecontext *c)
{
    c->nextcontext = NULL;
    if (!*clistptr) { /* 1st insertion */
        *clistptr = c;
        c->lastcontext = c;
    } else {        /* on end */
        (*clistptr)->lastcontext->nextcontext = c;
        (*clistptr)->lastcontext = c;
    }
}
```

This simply appends to the end, preserving tree traversal order. This is used for 1D GRAN enfilades where sequential order is already maintained by tree structure.

## Implications

### For Query Correctness

Operations that rely on I→V mapping will return V-spans in **sorted V-address order**, regardless of:
1. The order in which content was transcluded
2. The physical tree structure
3. Concurrent modifications (subject to serialization)

This affects:
- **Q3 (compare_versions)**: Shared span pairs are V-sorted
- **Q6 (findlinks by source)**: Results are V-sorted
- **Q7 (findlinks by target)**: Results are V-sorted
- **Q8 (finddocscontaining)**: V-positions within each document are sorted

### For Performance

**Time complexity:** Insertion-sort is O(n²) in the worst case, where n is the number of contexts returned.

For internal transclusion scenarios where the same I-address appears at k V-positions, sorting costs O(k²) per query. However:
- k is typically small (most content is not heavily transcluded within one document)
- The linked list is built incrementally during tree traversal
- Early termination is possible if the search is restricted to a V-span range

**Space complexity:** O(n) for the linked list of contexts.

### For Formal Verification

The insertion-sort algorithm provides a **deterministic ordering guarantee** that can be verified:

**Property R1 (V-sorted retrieval):**
```
Given POOM P, I-span i, V-dimension index:
  contexts = ispan2vspanset(P, i)
  ⇒ ∀j < k : contexts[j].totaloffset.dsas[index] ≤ contexts[k].totaloffset.dsas[index]
```

This property holds **regardless of insertion order** or tree structure.

## Related Findings

- **Finding 039**: Internal transclusion I→V mapping - confirms that `incontextlistnd` accumulates all contexts
- **Finding 041**: Enfilade insertion order dependency - explains why tree structure is not V-sorted
- **Finding 071**: 2D recombine diagonal ordering - explains non-V-ordering in tree structure
- **Finding 027**: Insertion order semantics - discusses retrieval ordering for different operations

## Open Questions

1. **Optimality**: Could a different data structure (e.g., balanced BST instead of linked list) improve worst-case performance from O(n²) to O(n log n)?

2. **Early termination**: Does the comparison logic support skipping contexts that are guaranteed to be outside the query range?

3. **Consistency**: Are there any code paths that bypass `incontextlistnd` and return unsorted results?

## Conclusion

**`incontextlistnd` performs explicit insertion-sort by V-address.** The V-ordering of query results comes from this sorting algorithm, NOT from tree traversal order alone.

This design decision separates concerns:
- **Tree structure** optimizes for insertion, storage, and range queries
- **Result ordering** is enforced by insertion-sort during retrieval

The algorithm guarantees deterministic V-sorted results regardless of the physical tree structure, supporting the formal invariants required for content identity and link discovery.

## Source References

- `context.c:75-111` - `incontextlistnd()` insertion-sort implementation
- `context.c:124-149` - `whereoncontext()` interval comparison
- `context.c:216-221` - `prologuecontextnd()` extracts context V-address
- `retrie.c:229-268` - `findcbcinarea2d()` tree traversal
- `retrie.c:401-418` - `intervalcmp()` comparison logic
- `common.h:86-90` - Interval comparison constants
- `orglinks.c:389-454` - I→V mapping call chain
