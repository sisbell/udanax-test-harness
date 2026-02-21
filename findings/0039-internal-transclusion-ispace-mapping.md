# Finding 0039: Internal Transclusion and I→V Mapping

**Date:** 2026-02-07
**Status:** Validated
**Tests:** `internal/internal_transclusion_identity`, `internal/internal_transclusion_with_link`, `internal/internal_transclusion_multiple_copies`

## Summary

When content is transcluded within the same document (internal transclusion), the POOM's bidirectional index correctly handles the case where a single I-address maps to multiple V-positions. The `ispan2vspanset` function returns ALL V-positions that reference a given I-address, not just one.

## Question Investigated

When content is transcluded within the SAME document (COPY from d to d), the POOM will have two different V-positions mapping to the same I-address. Does the POOM's bidirectional index (the I→V direction) correctly handle this case? That is, given an I-address that appears at two V-positions within the same document, does `ispan2vspanset` return both V-positions?

## Implementation Analysis

### Code Path

The I→V mapping is implemented through the following call chain:

1. `ispan2vspanset()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/orglinks.c:389-394`
   ```c
   typevspanset *ispan2vspanset(typetask *taskptr, typeorgl orgl,
                                typeispan *ispanptr, typevspanset *vspansetptr)
   {
       return permute(taskptr, orgl, ispanptr, I, vspansetptr, V);
   }
   ```

2. `permute()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/orglinks.c:404-422`
   - Iterates through restriction spanset
   - Calls `span2spanset()` for each restriction span
   - Accumulates results in `targspansetptr`

3. `span2spanset()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/orglinks.c:425-454`
   - Calls `retrieverestricted()` to search the POOM enfilade
   - Converts each context to a span via `context2span()`
   - Adds each span to the target list via `onitemlist()`

4. `retrieverestricted()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/retrie.c:56-85`
   - Calls `retrieveinarea()` with span constraints

5. `retrieveinarea()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/retrie.c:87-110`
   - Calls `findcbcinarea2d()` for POOM enfilades

6. `findcbcinarea2d()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/retrie.c:229-268`
   - **Traverses the B-tree structure** recursively
   - For each qualifying crumb, calls `incontextlistnd()` to **accumulate** results
   - Iterates through siblings: `for (; crumptr; crumptr = getrightbro (crumptr))`

7. `incontextlistnd()` → `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/context.c:75-111`
   - **Inserts context into a sorted linked list**
   - Handles first insertion, beginning, middle, and end cases
   - Never replaces or overwrites—always adds to the list

### Key Insight

The critical function is `incontextlistnd()`, which inserts each found context into a **linked list in sorted order** (sorted by the index dimension). It does NOT replace existing entries; it always adds new entries. This means that if the same I-address appears at multiple V-positions, `findcbcinarea2d()` will find all matching entries in the POOM B-tree and accumulate them all in the context list.

## Empirical Validation

### Test 1: Identity Comparison

**Scenario:** Transclude "text" from position 1.10 to position 1.19 within the same document, then compare the two regions.

**Code:** `internal/internal_transclusion_identity`

**Result:**
```json
{
  "op": "compare_versions",
  "shared": [
    {
      "first": { "start": "1.10", "width": "0.4" },
      "second": { "start": "1.19", "width": "0.4" }
    }
  ]
}
```

**Interpretation:** Both V-positions (1.10 and 1.19) are recognized as sharing the same I-addresses. This confirms that the V→I→V round-trip works correctly: both positions map to the same I-addresses, and when querying those I-addresses, both V-positions are found.

### Test 2: Link Discovery

**Scenario:**
1. Create internal transclusion: "text" appears at positions 1.10 and 1.19
2. Create a link on the FIRST occurrence (1.10)
3. Search for links from the SECOND occurrence (1.19)

**Code:** `internal/internal_transclusion_with_link`

**Result:**
```json
{
  "op": "create_link",
  "from": "first occurrence of 'text' (1.10-1.13)",
  "result": "1.1.0.1.0.1.0.2.1"
},
{
  "op": "find_links",
  "from": "second occurrence of 'text' (1.19-1.22)",
  "result": [ "1.1.0.1.0.1.0.2.1" ]
}
```

**Interpretation:** The link created on the first occurrence IS found when searching from the second occurrence. This definitively proves that `ispan2vspanset` returns BOTH V-positions when given the shared I-address.

### Test 3: Multiple Copies

**Scenario:** Create three copies of the character "B" within the same document at positions 1.2, 1.4, and 1.5.

**Code:** `internal/internal_transclusion_multiple_copies`

**Result:**
```json
{
  "op": "compare_all_pairs",
  "positions": ["1.2", "1.4", "1.5"],
  "results": {
    "1_2": true,
    "1_3": true,
    "2_3": true
  }
}
```

**Interpretation:** All three V-positions share identity with each other, confirming that the I→V mapping correctly handles N-to-1 relationships (N V-positions mapping to 1 I-address).

## Behavior Specification

**Given:**
- A document d with POOM P
- Content at I-address i
- V-positions v₁, v₂, ..., vₙ within d that all reference i

**Then:**
```
ispan2vspanset(P, i) = {v₁, v₂, ..., vₙ}
```

The function returns ALL V-positions that map to the given I-address, regardless of how many there are.

## Implementation Details

### Data Structure

The POOM is a 2D enfilade (B-tree) that stores mappings:
```
(V-position, I-address) → stored as 2D entry
```

When searching by I-address (the I dimension), the B-tree traversal finds all entries where the I-address matches, regardless of their V-position.

### Search Algorithm

`findcbcinarea2d()` at `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/retrie.c:229`:

```c
for (; crumptr; crumptr = getrightbro (crumptr)) {
    if (!crumqualifies2d (crumptr, offsetptr, span1start, span1end, index1,
                          span2start, span2end, index2, infoptr)) {
        continue;
    }
    if (crumptr->height != 0) {
        // Recurse into subtree
        findcbcinarea2d (findleftson ((typecuc*)crumptr), &localoffset,
                        span1start, span1end, index1, span2start, span2end,
                        index2, headptr, infoptr);
    } else {
        // Leaf node: add to result list
        context = makecontextfromcbc ((typecbc*)crumptr, (typewid*)offsetptr);
        incontextlistnd (headptr, context, index1);
    }
}
```

**Key properties:**
1. Iterates through ALL siblings at each level (`getrightbro`)
2. Recursively descends into ALL qualifying subtrees
3. Accumulates ALL leaf nodes that match the search criteria
4. `incontextlistnd()` adds to a linked list—never replaces

## Contrast with Other Systems

This behavior differs from systems that maintain a primary key constraint where each key maps to at most one value. The POOM is more like a **multimap** or **secondary index** where:
- One I-address can map to many V-positions (one-to-many)
- The query returns ALL matching entries

This is essential for Xanadu semantics where:
- Content can be transcluded multiple times within the same document
- Links are bound to content identity (I-addresses), not positions
- A link on one occurrence must be discoverable from all other occurrences

## Implications

### For Content Identity (I₁)

Internal transclusion creates multiple "views" of the same content identity within a single document. The POOM correctly maintains the invariant:

```
∀v ∈ V-space(d), iaddrs(d, v) ⊆ I-space(d)
```

When v₁ and v₂ both reference the same I-address i:
```
iaddrs(d, v₁) ∩ iaddrs(d, v₂) ⊇ {i}
```

### For Link Discovery (I₃)

Given a link `l = (from, to, type)` where `from` references I-addresses F:

```
findlinks(d, v) finds l  ⟺  iaddrs(d, v) ∩ F ≠ ∅
```

When v₁ and v₂ both reference the same I-addresses:
```
findlinks(d, v₁) = findlinks(d, v₂)
```

This was empirically validated by test 2.

### For Query Correctness

The I→V mapping's correctness is essential for:

1. **Q3 (compare_versions)**: Maps common I-spans to both documents' V-spans
2. **Q6 (findlinks by source)**: Maps link source I-addresses to all V-positions containing them
3. **Q7 (findlinks by target)**: Maps link target I-addresses to all V-positions containing them
4. **Q8 (finddocscontaining)**: Maps I-addresses to all documents (and positions) containing them

Internal transclusion is a special case of the general property: **one I-address can appear in multiple contexts** (different V-positions in the same document, or different documents entirely).

## Related Findings

- **Finding 0002**: Transclusion content identity - establishes that vcopy preserves I-addresses
- **Finding 0008**: Complex interactions - links follow content through transclusion (between documents)
- **Finding 0009**: Document address space structure - POOM as unified V→I storage
- **Finding 0013**: Sporgl provenance tracking - how I-addresses are propagated during vcopy
- **Finding 0033**: I-space consolidates adjacent addresses - affects the granularity of I-address regions
- **Finding 0037**: Link endsets split on discontiguous I-addresses - related V→I conversion behavior

## Open Questions

1. **Performance**: When an I-address appears at N V-positions, does `ispan2vspanset` have O(N) search complexity or O(log N) with the B-tree structure?

2. **Ordering**: The results are sorted by index dimension (V-position in this case). Does this ordering matter semantically, or is it just an implementation detail?

3. **Practical limit**: Is there a practical limit to how many times the same content can be transcluded within one document before performance degrades?

## Conclusion

**The POOM's bidirectional index correctly handles internal transclusion.** When the same I-address appears at multiple V-positions within a document, `ispan2vspanset` returns ALL matching V-positions. This is implemented through:

1. B-tree traversal that visits all matching nodes
2. Context accumulation via linked list insertion (never replacement)
3. Sorted ordering by the query dimension (V-position)

This behavior is essential for Xanadu's content-identity-based link discovery and has been empirically validated through three test scenarios demonstrating identity comparison, link discovery, and multiple copies.
