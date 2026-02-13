# Finding 071: 2D Recombine Uses Diagonal Ordering

## Summary

The 2D enfilade rebalancing algorithm (`recombinend`) sorts children by the sum
of their two displacement dimensions, then tries to merge or steal nephews
between pairs along this diagonal ordering. This is fundamentally different from
1D B-tree rebalancing, which uses a simple sequential order. The diagonal
approach optimizes for 2D spatial locality in the SPAN and POOM enfilades.

## The Algorithm

`recombinend()` in `recombine.c:104` implements 2D rebalancing in four steps:

### Step 1: Recursive descent
```c
for (ptr = getleftson(father); ptr; ptr = getrightbro(ptr))
    recombinend(ptr);
```
Recursively rebalance all children first (bottom-up).

### Step 2: Diagonal sort via `getorderedsons`
```c
getorderedsons(father, sons);
```
This calls `shellsort()` which orders children by the sum of their two
displacement coordinates (`cdsp.dsas[0] + cdsp.dsas[1]`):

```c
// shellsort, line 296-298:
for (i = 0; i < n; i++) {
    tumbleradd(&v[i]->cdsp.dsas[0], &v[i]->cdsp.dsas[1], &tarray[i]);
}
// then shellsort by tarray values
```

The comment calls this the "compare crums diagonally hack." For a 2D enfilade
where dimension 0 is ORGLRANGE (I-space) and dimension 1 is SPANRANGE (V-space),
this sorts children by their combined I+V position — a diagonal sweep across
the 2D address space.

### Step 3: Pairwise nephew-stealing
```c
for (i = 0; i < n-1; i++)
    for (j = i+1; sons[i] && j < n; j++)
        if (ishouldbother(sons[i], sons[j]))
            takeovernephewsnd(&sons[i], &sons[j]);
```
For each pair of nodes along the diagonal, check if they should merge
(`ishouldbother`), then either eat the sibling's entire subtree
(`eatbrossubtreend`) or steal individual nephews (`takenephewnd`).

### Step 4: Level pull
```c
if (father->isapex)
    levelpull(father);
```
If the root has only one child after merging, remove a tree level.

## Contrast with 1D Recombine

`recombineseq()` (for GRAN enfilades) uses a simpler strategy:

- Iterates children in sibling order (not sorted)
- Only considers adjacent pairs (`ptr` and `ptr->rightbro`)
- Either eats the right sibling's subtree or takes over its nephews
- Breaks after the first merge operation

The 1D algorithm preserves sequential ordering. The 2D algorithm must consider
all pairs because spatial proximity in 2D doesn't follow sibling order.

## Contrast with 2D Split

The split strategy is also dimension-aware but uses a different criterion:

- `splitcrumsp()` (SPAN): Peels off the child with the **largest diagonal**
  position (`comparecrumsdiagonally(ptr, correctone) == GREATER`)
- `splitcrumpm()` (POOM): Peels off the child with the **largest SPANRANGE**
  displacement (`cdsp.dsas[SPANRANGE]` only, not diagonal)

The asymmetry between SPAN split (diagonal) and POOM split (single-dimension)
is notable. The commented-out code in `splitcrumpm` shows that diagonal
splitting was tried for POOM but reverted:

```c
// splitcrumpm:
if (tumblercmp(&ptr->cdsp.dsas[SPANRANGE], ...) == GREATER)
/* if (comparecrumsdiagonally(ptr, correctone) == LESS) */
```

## The `ishouldbother` Guard

Merging only happens when the combined son count fits:
```c
dest->numberofsons + src->numberofsons <= (height > 1 ? MAXUCINLOAF : MAX2DBCINLOAF)
```
This prevents merges that would immediately trigger a split. The `randomness(.3)`
call always returns TRUE (the probabilistic path is commented out), so all
eligible pairs are merged.

Reserved crums (age == RESERVED) are skipped to avoid interfering with
in-progress operations.

## Why Diagonal Ordering

In a 2D enfilade, each bottom crum represents a rectangle in (ORGLRANGE,
SPANRANGE) space. The ORGLRANGE dimension is the document's I-space position;
the SPANRANGE dimension is the V-space position. Content that is "nearby" in
both dimensions should be stored in the same subtree for efficient retrieval.

The diagonal sum `dsp[0] + dsp[1]` is a rough L1-norm proxy for position in
the 2D space. Sorting by this value groups spatially close crums together,
making range queries in `findcbcinarea2d` more efficient — fewer subtrees need
to be visited when searching a 2D rectangle.

## Source References

- `recombine.c:104-131` — `recombinend` algorithm
- `recombine.c:278-311` — `getorderedsons` + `shellsort` with diagonal key
- `recombine.c:313-320` — `comparecrumsdiagonally`
- `recombine.c:150-163` — `ishouldbother` merge guard
- `recombine.c:165-203` — `takeovernephewsnd` (merge or steal)
- `recombine.c:205-233` — `eatbrossubtreend` (full merge)
- `split.c:95-106` — `splitcrumsp` (SPAN split by diagonal)
- `split.c:117-128` — `splitcrumpm` (POOM split by SPANRANGE only)
- `retrie.c:229` — `findcbcinarea2d` (2D range query that benefits from locality)
