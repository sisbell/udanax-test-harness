# Finding 041: Enfilade Insertion Order Dependency

**Date:** 2026-02-07
**Category:** Permanent Layer Structure
**Agent:** Gregory
**Related:** EWD-025 (Concurrency and the Permanent Layer)

## Summary

The permanent layer (ispace + spanf) does NOT behave as pure set union. The enfilade B-tree structure exhibits **order dependency** during concurrent insertions. While the LOGICAL CONTENT (set of I-address → data mappings) is order-independent, the PHYSICAL TREE STRUCTURE depends on insertion order.

## Evidence from Source Code

### 1. Insertion Creates Siblings in Fixed Position

**File:** `/udanax-test-harness/backend/insert.c` lines 43-46

```c
reserve ((typecorecrum*)ptr);
new = createcrum (0,(INT)ptr->cenftype);
reserve (new);
adopt (new, RIGHTBRO, (typecorecrum*)ptr);
```

New entries are always inserted as the RIGHT BROTHER of the retrieved position. This creates a **left-to-right ordering** in the sibling list.

### 2. Retrieval Determines Insertion Point

**File:** `/udanax-test-harness/backend/retrie.c` lines 167-188

```c
typecrumcontext *findcbcseqcrum(typecorecrum *ptr, typedsp *offsetptr, tumbler *address)
{
    for (; getrightbro (ptr); ptr = ptr->rightbro) {
        if (whereoncrum (ptr, offsetptr, address, WIDTH) <= THRUME)
            break;
        dspadd (offsetptr, &ptr->cwid, offsetptr, (INT)ptr->cenftype);
    }
    if (ptr->height != 0) {
        ptr = findleftson ((typecuc*)ptr);
        return (findcbcseqcrum (ptr, offsetptr, address));
    } else {
        return (createcrumcontext (ptr, offsetptr));
    }
}
```

The retrieval walks siblings **left to right** until finding the position. If two entries exist at the SAME I-address, which one is found depends on tree structure.

### 3. Split and Rebalance Are Order-Sensitive

**File:** `/udanax-test-harness/backend/split.c` lines 70-93

```c
int splitcrumseq(typecuc *father)
{
    // ...
    halfsons = father->numberofsons / 2;
    for (i = 0, ptr = findrightmostson(father); i < halfsons && ptr; ++i, ptr = next) {
        next = findleftbro(ptr);
        disown(ptr);
        adopt(ptr, LEFTMOSTSON, new);
        rejuvinate(ptr);
        ivemodified(ptr);
    }
    // ...
}
```

When a node overflows, it splits by moving the **rightmost half** of sons to a new sibling. The tree shape after split depends on the **order** siblings were inserted.

### 4. Tree Shape Example

Consider inserting two entries A and B at I-address `1.1.0.1.0.1`:

**Scenario 1: A then B**
```
Parent
  └─ Crum_A (contains A at 1.1.0.1.0.1)
      └─ rightbro → Crum_B (contains B at 1.1.0.1.0.1)
```

**Scenario 2: B then A**
```
Parent
  └─ Crum_B (contains B at 1.1.0.1.0.1)
      └─ rightbro → Crum_A (contains A at 1.1.0.1.0.1)
```

The logical content `{1.1.0.1.0.1 → A, 1.1.0.1.0.1 → B}` is the same, but the physical structure differs.

## Implications for EWD-025 CON0

### CON0 States

> **CON0 (Permanent layer confluence)**: The permanent layer is confluent under concurrent additions. If operations O₁ and O₂ independently add entries E₁ and E₂ to the permanent layer, the result is independent of execution order:
>
> `add(add(σ, E₁), E₂) = add(add(σ, E₂), E₁)`

### Verdict: **TRUE at the logical level, FALSE at the physical level**

The **LOGICAL CONTENT** is confluent:
- Both orders produce the same set of I-address mappings
- Queries (retrieve, retrieveinspan) return the same data regardless of tree shape
- The widdative summaries (cwid fields) maintain the same logical intervals

The **PHYSICAL STRUCTURE** is NOT confluent:
- Tree shape (sibling ordering, split points) depends on insertion order
- Disk layout would differ
- Cache behavior might differ
- But these are implementation details invisible to queries

## Critical Insight: Enfilade Abstraction Preserves Confluence

The enfilade data structure maintains confluence **at the abstraction boundary**:

1. **Below the boundary** (implementation): Tree structure is order-dependent
2. **At the boundary** (queries): Results are order-independent
3. **Above the boundary** (permanent layer semantics): Pure set union holds

This is analogous to hash tables:
- Internal bucket ordering depends on insertion order
- But the set membership query is order-independent
- The data structure implements set semantics despite internal ordering

## Relevance to Concurrency (EWD-025 CON5)

**Question:** Can two threads safely insert into the same enfilade concurrently?

**Answer:** No, without synchronization:

1. **Structural corruption risk**: `adopt(new, RIGHTBRO, ptr)` modifies shared pointers
2. **Lost updates**: Concurrent modifications to `father->numberofsons`
3. **Invalid tree invariants**: Split/rebalance operations assume exclusive access

But **serialization preserves logical confluence**:
- Thread 1: insert A at 1.1.0.1.0.1
- Thread 2: insert B at 1.1.0.1.0.1
- Either order produces the same queryable content

This supports EWD-025 CON5: Only **per-document POOM access** needs serialization (for I₁ maintenance). The **permanent layer can use any serialization strategy** because logical confluence holds.

## Correction to EWD-025

The statement "set union is commutative and associative" (CON0) is correct at the **semantic level** but potentially misleading at the **implementation level**.

**Recommended clarification:**

> CON0 (Permanent layer confluence): The permanent layer is confluent under concurrent additions because it implements set union semantics. While the internal enfilade tree structure depends on insertion order, the **queryable content** (set of I-address mappings) is order-independent. Both `retrieve` and `retrieveinspan` operations return the same results regardless of insertion order, preserving the commutative and associative properties of set union at the abstraction boundary.

## Open Questions

1. **Cache coherence:** Does tree shape affect query performance in observable ways?
2. **Disk fragmentation:** Does insertion order affect long-term storage efficiency?
3. **Deterministic builds:** Would a canonical tree shape (e.g., sorted insertion) be valuable for testing?

## References

- `/udanax-test-harness/backend/insert.c` — `insertseq()` function
- `/udanax-test-harness/backend/retrie.c` — `retrievecrums()` function
- `/udanax-test-harness/backend/split.c` — tree rebalancing
- `/udanax-test-harness/backend/genf.c:419` — `adopt()` sibling insertion
- EWD-025 — Concurrency and the Permanent Layer
