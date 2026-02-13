# Finding 070: Enfilade Branching Parameters

## Summary

The udanax-green enfilade implementation has three hard-coded branching limits
that govern tree shape, split/merge thresholds, and maximum node occupancy.
These parameters are defined in `enf.h` and referenced throughout the tree
manipulation code.

## Parameters

| Constant | Value | Applies to |
|----------|-------|------------|
| `MAXUCINLOAF` | 6 | Upper crums (height > 1), all enfilade types |
| `MAX2DBCINLOAF` | 4 | Bottom crums (height 0-1) in 2D enfilades (SPAN, POOM) |
| `MAXBCINLOAF` | 1 | Bottom crums in 1D enfilades (GRAN) — "so text will fit" |

Source: `enf.h:26-28`

## Threshold Functions

Four functions in `genf.c` define the rebalancing envelope using these
parameters. All are height-aware and type-aware:

### `toomanysons(ptr)` — split trigger
```
numberofsons > (height > 1 ? MAXUCINLOAF : is2d ? MAX2DBCINLOAF : MAXBCINLOAF)
```
Returns TRUE when a node exceeds its limit. For upper crums: > 6. For 2D
bottom crums: > 4. `splitcrumupwards()` loops while this is true.

### `roomformoresons(ptr)` — insertion guard
```
numberofsons < (height > 1 ? MAXUCINLOAF : is2d ? MAX2DBCINLOAF : MAXBCINLOAF)
```
Returns TRUE when a node can accept another child. For upper crums: < 6. For 2D
bottom crums: < 4. Used by `insertcbcnd`, `takeovernephewsnd`, and recombine
to decide whether to add children.

### `toofewsons(ptr)` — merge trigger
```
numberofsons < (height > 1 ? MAXUCINLOAF - 1 : is2d ? MAX2DBCINLOAF : MAXBCINLOAF)
```
Returns TRUE when a node is underfull. For upper crums: < 5. Used by
`recombineseq` (1D) to decide whether to steal nephews.

### `isfullcrum(ptr)` — apex test
```c
#define isfullcrum(x) ((bool)((typecorecrum *)(x))->isapex)
```
Despite the name, this tests whether the crum is the fullcrum (root), not
whether it's "full" in the B-tree sense. `splitcrumupwards` checks this to
decide whether to `levelpush` (add a new root level) or `splitcrum` (split
within the current level).

## Valid Son Counts

For upper crums (the common case in a non-trivial enfilade):

| Sons | State |
|------|-------|
| 0 | Empty (only after delete-all, see Bug 019) |
| 1-4 | Underfull — `toofewsons` returns TRUE |
| 5 | Normal — neither too few nor full |
| 6 | Maximum valid — no room for more, but not yet "too many" |
| 7+ | Overfull — `toomanysons` triggers split |

The gap between `roomformoresons` (< 6) and `toomanysons` (> 6) means a node
at exactly 6 sons is in a stable state: it cannot accept more children, but it
won't be split either. This is the maximum occupancy for an upper crum.

## Implications

### Disk format
`MAXUCINLOAF` determines the loaf size on disk. `coredisk.h:56` declares
`ducarray[MAXUCINLOAF]` in the disk upper crum structure. Changing the branching
factor requires a new disk format.

### Tree depth
With branching factor 6, a SPAN enfilade holding N bottom crums has height
roughly log₆(N). A document with 1000 distinct content spans needs about
height 4. The logarithmic growth keeps all operations bounded.

### The MAXBCINLOAF = 1 case
Granfilade bottom crums hold exactly 1 entry ("so text will fit" per the
comment). This makes the granfilade effectively a list at the bottom level,
with tree structure only in upper levels. The 1D sequential structure of text
doesn't benefit from multi-way bottom crums.

## Source References

- `enf.h:26-28` — constant definitions
- `genf.c:239-261` — threshold functions
- `split.c:16-43` — `splitcrumupwards` loop
- `recombine.c:104-131` — `recombinend` rebalancing
- `insertnd.c:242-275` — `insertcbcnd` insertion with split
- `coredisk.h:50,56` — disk layout arrays
