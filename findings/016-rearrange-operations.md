# Finding 016: Rearrange Operations (Pivot and Swap)

**Date:** 2026-01-30
**Status:** Validated via golden tests (9 scenarios)
**Tests:** `golden/rearrange/*.json`

## Summary

The REARRANGE operation (FEBE opcode 3) provides in-place content reordering without creating copies. Unlike delete+insert which loses content identity, rearrange preserves I-addresses while moving content to new V-addresses.

## Operations

### Pivot (3 cuts)

Swaps two **adjacent** regions around a pivot point.

```
pivot(doc, cut1, cut2, cut3)

Before: [... region1 ...][... region2 ...]
              ^cut1    ^cut2           ^cut3

After:  [... region2 ...][... region1 ...]
```

**Example:**
```
"ABCDE" with cuts at 1.2, 1.4, 1.6
Regions: "BC" (1.2-1.4) and "DE" (1.4-1.6)
Result: "ADEBC"
```

### Swap (4 cuts)

Swaps two **non-adjacent** regions.

```
swap(doc, cut1, cut2, cut3, cut4)

Before: [... region1 ...][middle][... region2 ...]
              ^cut1  ^cut2      ^cut3       ^cut4

After:  [... region2 ...][middle][... region1 ...]
```

**Example:**
```
"ABCDEFGH" with cuts at 1.2, 1.4, 1.6, 1.8
Regions: "BC" (1.2-1.4) and "FG" (1.6-1.8)
Result: "AFGDEBCH"
```

## Key Properties

### 1. Identity Preservation

Rearrange preserves content identity (I-addresses). The content at new V-addresses still has the same origin identity.

**Test:** `pivot_preserves_identity`

### 2. Link Survivability

Links bound to rearranged content remain discoverable because they're bound to I-addresses, not V-addresses.

**Test:** `swap_with_links`
```
Before swap: Link from "BC" to "FG"
After swap:  Same link still discoverable at new positions
```

### 3. Self-Inverse (Pivot)

Two identical pivots return content to original order:
```
ABCDE → pivot(1.2, 1.4, 1.6) → ADEBC → pivot(1.2, 1.4, 1.6) → ABCDE
```

**Test:** `double_pivot`

## Comparison with Copy+Delete

| Aspect | Rearrange | Copy + Delete |
|--------|-----------|---------------|
| Content identity | Preserved | Lost (new I-address) |
| Links | Follow content | Break (link to deleted content) |
| Transclusion chains | Maintained | Broken |
| Operations | 1 | 2+ |

## Use Cases

1. **Word reordering** - Move words within a sentence without breaking links
2. **Paragraph shuffling** - Reorganize sections while preserving transclusion
3. **Editor operations** - Implement drag-and-drop that preserves Xanadu semantics

## Implementation Notes

The backend implements rearrange in `edit.c:rearrangend()`. Cut points define boundaries between regions. The algorithm:

1. Identifies which "slice" each content span belongs to
2. Computes offset adjustments for each slice
3. Applies offsets to move content to new V-positions

## Related

- **Finding 002**: Content identity preservation (transclusion)
- **Finding 005**: Link survivability through edits
- **FEBE Protocol**: REARRANGE opcode 3
