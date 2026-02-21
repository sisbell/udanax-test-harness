# Finding 0063: CREATELINK Breaks I-Address Contiguity for Subsequent Text INSERTs

**Date discovered:** 2026-02-10
**Category:** Granfilade / I-address allocation / INSERT coalescing
**Test scenarios:** `/udanax-test-harness/febe/scenarios/insert_coalescing.py`

## Summary

CREATELINK breaks I-address contiguity between successive text INSERTs, while DELETE does not. After INSERT "ABC" → CREATELINK → INSERT "DEF", the DEF characters receive I-addresses that are NOT contiguous with ABC's I-addresses. `compare_versions` reports 2 shared span pairs instead of 1. This is because CREATELINK allocates I-address space in the granfilade (for the link orgl), advancing the "current maximum" I-address past the link's allocation range.

## The Experiment

Four golden scenarios test whether intervening operations create I-address gaps:

| Scenario | Sequence | Shared Span Pairs | I-Address Gap? |
|----------|----------|-------------------|----------------|
| Baseline | INSERT → INSERT | 1 | NO |
| DELETE | INSERT → DELETE → INSERT | 1 | NO |
| CREATELINK | INSERT → CREATELINK → INSERT | **2** | **YES** |
| REARRANGE | INSERT → REARRANGE → INSERT | 1 | N/A (rearrange not implemented) |

## Evidence

### Baseline: 1 Span Pair (No Gap)

**Golden:** `golden/internal/insert_only_baseline.json`

```json
{
  "shared_span_pairs": 1,
  "shared": [
    {"source": {"start": "1.1", "width": "0.6"}, "dest": {"start": "1.1", "width": "0.6"}}
  ]
}
```

INSERT "ABC" then INSERT "DEF" → all 6 characters have contiguous I-addresses. One span pair covers them all.

### DELETE: 1 Span Pair (No Gap)

**Golden:** `golden/internal/insert_delete_insert_iaddress_gap.json`

```json
{
  "shared_span_pairs": 1,
  "shared": [
    {"source": {"start": "1.1", "width": "0.5"}, "dest": {"start": "1.1", "width": "0.5"}}
  ]
}
```

INSERT "ABC" → DELETE "B" → INSERT "DEF" → still 1 span pair. DELETE modifies only the spanfilade (V→I mapping), not the granfilade. The deleted "B" retains its I-address in the granfilade, so the next INSERT allocates I-addresses continuing from where ABC left off. Width is 0.5 not 0.6 because "B" is no longer in the destination document's V-space.

### CREATELINK: 2 Span Pairs (Gap!)

**Golden:** `golden/internal/insert_link_insert_iaddress_gap.json`

```json
{
  "shared_span_pairs": 2,
  "shared": [
    {"source": {"start": "1.1", "width": "0.3"}, "dest": {"start": "1.1", "width": "0.3"}},
    {"source": {"start": "2", "width": "0.4"}, "dest": {"start": "1.4", "width": "0.4"}}
  ]
}
```

INSERT "ABC" → CREATELINK → INSERT "DEF" → **2 span pairs**. The ABC characters have I-addresses starting at 1.1 (width 0.3). The DEF characters have I-addresses starting at **2** (a different range entirely). The CREATELINK consumed I-address space between ABC and DEF.

### REARRANGE: Invalid Test

**Golden:** `golden/internal/insert_rearrange_insert_iaddress_gap.json`

The `rearrange` operation failed with `'XuSession' object has no attribute 'rearrange'`. The test gracefully continued, making it effectively a second baseline (1 span pair). The correct API would be `session.pivot()` or `session.swap()`.

## Why CREATELINK Creates a Gap

The mechanism follows from Finding 0052 and Finding 0061:

1. **I-address allocation is monotonic** (Finding 0061): Each INSERT calls `findpreviousisagr` to find the highest existing I-address, then increments.

2. **CREATELINK allocates in the granfilade** (Finding 0052): CREATELINK calls `createorglingranf` which creates a link orgl in the granfilade. This orgl gets an I-address via `findisatoinsertnonmolecule` (for non-ATOM/non-text entities).

3. **The gap**: After INSERT "ABC" (I-addresses ~1.1 to 1.3), CREATELINK's orgl gets an I-address in a HIGHER range. When the next INSERT "DEF" queries `findpreviousisagr`, it finds the link orgl's I-address as the highest, and allocates ABOVE it — creating a gap between ABC and DEF.

The link orgl's I-address at "2" (visible in the compare_versions source start) shows that the link was allocated in a different subspace of the document's I-space.

## Consequences

### 1. CREATELINK Breaks isanextensionnd Coalescing

`isanextensionnd` checks if the new insertion's I-address origin equals the existing crum's I-address reach. After CREATELINK, the new text I-addresses are no longer contiguous with the previous text I-addresses, so coalescing FAILS. This means the next INSERT after a CREATELINK always creates new crums, as if the cursor had been repositioned.

**Impact on crum proliferation:** Each CREATELINK followed by text INSERT costs the same as a cursor repositioning (+2 crums for the first character typed after the link). The EWD-022 bound `c ≤ 1 + 2C + 3R + 3P` should account for link creation in the C term (or add a separate L term for link-induced repositioning).

### 2. compare_versions Reports More Span Pairs

Documents with interleaved text typing and link creation will have fragmented I-address ranges. `compare_versions` will report more shared span pairs than a document with the same text but no link creation history. This is an observable consequence of link creation order.

### 3. DELETE is Truly "Weak", CREATELINK is Not

This confirms the I-space/V-space classification from Trial 021's EWDs:
- **DELETE**: Weak operation. Only touches V-space (spanfilade). No I-address consequences.
- **CREATELINK**: Touches BOTH spaces. Allocates in I-space (granfilade) AND V-space (POOM). Has I-address consequences for subsequent operations.

This distinction matters for Nelson's "bytes never die" principle: DELETE is strictly a V-space operation with no I-space side effects. CREATELINK has permanent I-space effects — the link orgl's I-address is allocated forever and cannot be reclaimed.

## Related Findings

- **Finding 0052**: CREATELINK uses insertpm, shifts POOM entries (the mechanism)
- **Finding 0061**: I-address allocation is monotonic, DELETE doesn't affect it (the contrast)
- **Finding 0033**: I-space consolidates adjacent addresses (what happens when no gap exists)
- **Finding 0062**: Interior typing coalescing via ONMYRIGHTBORDER (what coalescing looks like when it works)
- **Finding 0038**: POOM subspace independence (link subspace vs text subspace)

## Golden Output References

- `golden/internal/insert_only_baseline.json` — Control: 1 span pair
- `golden/internal/insert_delete_insert_iaddress_gap.json` — DELETE: 1 span pair (no gap)
- `golden/internal/insert_link_insert_iaddress_gap.json` — CREATELINK: 2 span pairs (gap!)
- `golden/internal/insert_rearrange_insert_iaddress_gap.json` — REARRANGE: invalid (no API method)

## Code References

- `granf2.c:130-181` — `findisatoinsertgr` / `findisatoinsertmolecule` (I-address allocation)
- `granf2.c:255-278` — `findpreviousisagr` (tree traversal to find highest I-address)
- `do1.c:199-225` — `docreatelink` calls `createorglingranf` (orgl I-address allocation)
- `insertnd.c:293-301` — `isanextensionnd` (coalescing check: reach == origin)
- `edit.c` — `deletevspanpm` (DELETE is spanfilade-only, no granfilade effect)
