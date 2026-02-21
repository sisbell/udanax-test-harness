# Finding 0033: I-Space Consolidates Adjacent Addresses

**Date discovered:** 2026-02-03
**Category:** Address Structure

## Summary

When multiple single-character inserts are performed sequentially, the resulting I-addresses ARE contiguous and ARE consolidated into a single I-span. This means `vspanset2ispanset` on a consolidated V-span returns 1 I-span, not N I-spans.

## The Question

The original question was: When 100 single-character inserts result in 1 V-span (consolidation observed), does `vspanset2ispanset` return:
- (A) 1 I-span (I-space also consolidated), or
- (B) 100 I-spans (I-space fragmented but V-space consolidated)?

## Answer: (A) - Both V-space and I-space Are Consolidated

The I-addresses allocated for sequential inserts are **contiguous in the permascroll**, so they naturally form a single I-span when converted.

## Key Behaviors Verified

### 1. Fragmented inserts produce contiguous I-addresses

10 separate single-character inserts produce content that, when compared via `compare_versions`, returns **1 shared span pair**, not 10.

**Test:** `ispan_consolidation_fragmented`
```json
{
  "shared_span_pairs": 1,
  "shared": [{
    "source": {"start": "1.1", "width": "0.10"},
    "dest": {"start": "1.1", "width": "0.10"}
  }]
}
```

### 2. Bulk inserts behave identically

A single insert of "ABCDEFGHIJ" also produces 1 span pair, confirming there's no difference in I-space structure between bulk and fragmented inserts.

**Test:** `ispan_consolidation_bulk`
```json
{
  "shared_span_pairs": 1
}
```

### 3. Partial overlaps also consolidated

When vcopying only positions 3-7 (CDEFG) from a fragmented-insert document, the result is still 1 span pair, not 5.

**Test:** `ispan_partial_overlap`
```json
{
  "shared_span_pairs": 1,
  "shared": [{
    "source": {"start": "1.3", "width": "0.5"},
    "dest": {"start": "1.1", "width": "0.5"}
  }]
}
```

## Mechanism

Looking at `findisatoinsertmolecule` in granf2.c:

```c
} else if (hintptr->atomtype == TEXTATOM) {
    tumblerincrement (&lowerbound, 0, 1, isaptr);
}
```

Each text insert finds the **previous highest I-address** and increments by 1. This means sequential inserts get sequential I-addresses:

- Insert "A" -> I-address 2.1.0.1.0.1.3.1
- Insert "B" -> I-address 2.1.0.1.0.1.3.2
- Insert "C" -> I-address 2.1.0.1.0.1.3.3
- ...

These form a contiguous range: `2.1.0.1.0.1.3.1` to `2.1.0.1.0.1.3.10`, width `0.10`.

## Implications

1. **V-space and I-space consolidation are coupled** - when V-addresses are contiguous and map to contiguous I-addresses, both spaces consolidate

2. **No "fragmentation penalty"** - there's no storage or comparison overhead from making many small inserts vs. one large insert

3. **The enfilade efficiently represents sequential content** - the tree structure naturally merges adjacent regions

4. **`compare_versions` efficiency** - comparing documents with fragmented insertion history is no more expensive than comparing bulk-inserted documents

## Related Tests

- `golden/internal/ispan_consolidation_fragmented.json`
- `golden/internal/ispan_consolidation_bulk.json`
- `golden/internal/ispan_partial_overlap.json`
- `golden/edgecases/many_small_inserts.json`

## Related Findings

- **Finding 0009**: Document address space structure
- **Finding 0030**: Insert V-space and I-space mapping
