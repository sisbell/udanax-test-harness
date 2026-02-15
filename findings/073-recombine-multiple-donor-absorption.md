# Finding 073: Recombine Allows Multiple Donor Absorption Per Receiver

## Summary

In the POOM/SPAN 2D recombine algorithm (`recombinend`), a single receiver node **can** absorb multiple donors in one recombine pass. The nested loop structure iterates over all pairs (i, j) where i < j, and the inner loop continues even after receiver `sons[i]` has absorbed donor `sons[j]`. The algorithm marks absorbed/depleted donors as NULL in the sons array and checks `sons[j]` before each merge attempt.

## The Iteration Logic

The Phase 2 pairwise merge loop in `recombinend` (lines 120-128):

```c
for (i = 0; i < n-1; i++) {
    for (j = i+1; sons[i] && j < n; j++) {
        if(i != j && sons[j] && ishouldbother(sons[i],sons[j])){
            takeovernephewsnd (&sons[i], &sons[j]);
            /*break;*/
            /*break;//zzz6/16/84 reg//*/
        }
    }
}
```

### Key observations:

1. **No active break**: The two `break` statements are commented out (with a timestamp "6/16/84" suggesting this was intentional)
2. **Inner loop continues**: After `takeovernephewsnd(&sons[i], &sons[j])` is called, the inner `j` loop continues to `j+1`, `j+2`, etc.
3. **Receiver remains active**: The same `sons[i]` can be passed to subsequent `takeovernephewsnd` calls with different donors `sons[j+1]`, `sons[j+2]`, etc.
4. **NULL guards**: The conditions `sons[i] && sons[j]` prevent dereferencing NULL pointers when donors are depleted

## Donor Depletion Mechanism

When `takeovernephewsnd` fully absorbs a donor, it sets the donor pointer to NULL in the array:

```c
int takeovernephewsnd(typecuc **meptr, typecuc **broptr)
{
    me = *meptr;
    bro = *broptr;

    if (me->numberofsons + bro->numberofsons <= MAXUCINLOAF) {
        // Case 1: Full absorption
        eatbrossubtreend (me, bro);
        *broptr = NULL;  // Donor is freed and marked NULL
        return (TRUE);
    } else {
        // Case 2: Partial absorption (steal nephews)
        for (i = 0; i < n && roomformoresons (me); i++) {
            takenephewnd (me, sons[i]);
        }

        if (bro->numberofsons)
            setwispupwards (bro, 0);
        else {
            // All nephews stolen - donor is empty
            disown (bro);
            freecrum (bro);
            *broptr = NULL;  // Mark depleted donor as NULL
        }
    }
}
```

This means:
- Fully absorbed donors (via `eatbrossubtreend`) are immediately set to NULL
- Partially absorbed donors that become empty are also set to NULL
- Partially absorbed donors that still have children remain non-NULL and available for subsequent merges

## Example Scenario

Consider a diagonally-sorted array of 5 children: `[c0, c1, c2, c3, c4]`

**Iteration i=0:**
- j=1: `c0` absorbs `c1` completely → `[c0, NULL, c2, c3, c4]`
- j=2: `c0` steals some nephews from `c2` (c2 not fully depleted) → `[c0, NULL, c2, c3, c4]`
- j=3: `c0` steals remaining nephews from `c3`, depleting it → `[c0, NULL, c2, NULL, c4]`
- j=4: `c0` is full (`!roomformoresons(c0)` or `!ishouldbother(c0, c4)`), skips `c4`

**Iteration i=1:**
- `sons[1]` is NULL, skip entire inner loop (`sons[i] &&` fails)

**Iteration i=2:**
- j=3: `sons[3]` is NULL, skip
- j=4: `c2` absorbs `c4` → `[c0, NULL, c2, NULL, NULL]`

Final result: Two large nodes `c0` and `c2`, each having absorbed multiple donors.

## Why No Break?

The commented-out `break` statements suggest this was an intentional design choice made on June 16, 1984. Possible reasons:

1. **Maximize consolidation**: Allowing a receiver to absorb multiple donors in one pass reduces the number of recombine iterations needed to reach equilibrium
2. **Diagonal locality**: Since children are sorted diagonally, a receiver at position i may be spatially close to multiple donors at positions j, j+1, j+2, etc. Absorbing all of them improves 2D spatial locality
3. **Efficiency**: Fewer total nodes means shallower trees and faster lookups in `findcbcinarea2d`

## Contrast with GRAN Recombine

The 1D recombine algorithm (`recombineseq`, lines 50-65) **does** break after a single merge:

```c
for(ptr=(typecuc *)getleftson(father); ptr && ptr->rightbro; ptr=(typecuc *)findrightbro((typecorecrum *)ptr)){
    if (ptr->age == RESERVED)
        continue;
    if (ptr->leftson && roomformoresons (ptr)) {
        if (((typecuc *)ptr->rightbro)->leftson) {
            if (ptr->numberofsons + ((typecuc *)ptr->rightbro)->numberofsons <= MAXUCINLOAF) {
                eatbrossubtreeseq (ptr);
                break;  // ACTIVE BREAK!
            } else {
                takeovernephewsseq (ptr);
                break;  // ACTIVE BREAK!
            }
        }
    }
}
```

The GRAN algorithm breaks after the first successful merge, meaning a single receiver absorbs at most one donor per pass. Multiple passes are needed for full consolidation.

This is a fundamental difference between 1D and 2D recombine strategies.

## Saturation Limits

A receiver stops absorbing when:
1. `!ishouldbother(sons[i], sons[j])` returns FALSE because:
   - `sons[i]->numberofsons + sons[j]->numberofsons > MAXUCINLOAF` (height > 1)
   - `sons[i]->numberofsons + sons[j]->numberofsons > MAX2DBCINLOAF` (height == 1)
2. The receiver is RESERVED (`sons[i]->age == RESERVED`)
3. The donor is RESERVED or NULL
4. `!roomformoresons(sons[i])` in partial absorption path

Once a receiver reaches capacity, it skips all remaining donors in that outer loop iteration.

## Source References

- `recombine.c:104-131` — `recombinend` with nested pair iteration
- `recombine.c:120-128` — Phase 2 loop with commented-out `break` statements
- `recombine.c:165-203` — `takeovernephewsnd` sets `*broptr = NULL` when donor is depleted
- `recombine.c:180-182` — Full absorption path
- `recombine.c:194-200` — Partial absorption depletion path
- `recombine.c:150-163` — `ishouldbother` capacity guard
- `recombine.c:38-68` — `recombineseq` (GRAN) uses active `break` for comparison
- Finding 071 — Diagonal ordering context
