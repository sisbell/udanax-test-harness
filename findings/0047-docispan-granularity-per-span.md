# Finding 0047: DOCISPAN Granularity is Per-Span, Not Per-Byte

**Date discovered:** 2026-02-07
**Category:** Spanfilade indexing / Storage efficiency

## Summary

When INSERT or COPY creates k contiguous bytes, the spanfilade receives **ONE DOCISPAN entry** for the entire contiguous I-span, not k separate entries (one per byte). The granularity of DOCISPAN entries is **per-span**, determined by the consolidation that occurs in `vspanset2ispanset`.

## The Question

When a user INSERTs k contiguous bytes:
- Does `insertspanf(DOCISPAN)` create 1 entry for the span, or k entries (one per byte)?
- Similarly for COPY of k contiguous bytes?

This matters for storage efficiency: per-span is O(1) per operation; per-byte would be O(k).

## Answer: Per-Span (One Entry per Contiguous I-Span)

### Code Evidence

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/spanf1.c:15-53`:

```c
bool insertspanf(typetask *taskptr, typespanf spanfptr, typeisa *isaptr,
                 typesporglset sporglset, INT spantype)
{
  typedsp crumorigin;
  typewid crumwidth;
  tumbler lstream, lwidth;
  type2dbottomcruminfo linfo;

  prefixtumbler (isaptr, spantype, &crumorigin.dsas[ORGLRANGE]);
  tumblerclear (&crumwidth.dsas[ORGLRANGE]);
  clear (&linfo, sizeof(linfo));

  // Loop over each item in the ispanset (linked list)
  for (; sporglset; sporglset = (typesporglset)((typeitemheader *)sporglset)->next) {
    if (((typeitemheader *)sporglset)->itemid == ISPANID) {
      movetumbler (&((typeispan *)sporglset)->stream, &lstream);   // I-span start
      movetumbler (&((typeispan *)sporglset)->width, &lwidth);     // I-span width
      movetumbler (isaptr,&linfo.homedoc);
    } else if (...) {
      // SPORGLID or TEXTID cases
    }
    movetumbler (&lstream, &crumorigin.dsas[SPANRANGE]);
    movetumbler (&lwidth, &crumwidth.dsas[SPANRANGE]);
    insertnd(taskptr,(typecuc*)spanfptr,&crumorigin,&crumwidth,&linfo,SPANRANGE); // ← ONE call per item
  }
  return (TRUE);
}
```

**Key insight:** The loop iterates over the `ispanset` linked list. Each `typeispan` has:
- `stream`: Starting I-address
- `width`: Span width (number of contiguous bytes)

Each `typeispan` produces **one call to `insertnd`**, which inserts **one entry** into the spanfilade.

### Call Chain for INSERT

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/do1.c:91-127`:

```c
bool doinsert(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typetextset textset)
{
  typehint hint;
  typespanset ispanset;

  makehint(DOCUMENT, ATOM, TEXTATOM, docisaptr, &hint);
  ret = (inserttextingranf(taskptr, granf, &hint, textset, &ispanset)  // ← allocates I-addresses
      && docopy (taskptr, docisaptr, vsaptr, ispanset)                 // ← calls insertspanf
  );
  return(ret);
}
```

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/do1.c:45-65`:

```c
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
  typeispanset ispanset;
  typeorgl docorgl;

  return (
     specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)   // ← converts to ispanset
  && findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
  && acceptablevsa (vsaptr, docorgl)
  && asserttreeisok(docorgl)
  && insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)        // ← updates POOM
  && insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)     // ← creates DOCISPAN entries
  && asserttreeisok(docorgl)
  );
}
```

### I-Span Consolidation (Finding 0033)

From Finding 0033: I-Space Consolidates Adjacent Addresses:

> When multiple single-character inserts are performed sequentially, the resulting I-addresses ARE contiguous and ARE consolidated into a single I-span. This means `vspanset2ispanset` on a consolidated V-span returns 1 I-span, not N I-spans.

The mechanism (from `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/granf2.c`):

```c
} else if (hintptr->atomtype == TEXTATOM) {
    tumblerincrement (&lowerbound, 0, 1, isaptr);
}
```

Each text insert finds the previous highest I-address and increments by 1. Sequential inserts get sequential I-addresses, which consolidate into a single I-span.

## Implications

### 1. Storage Efficiency

**Per-span granularity is O(1) per INSERT/COPY operation**, not O(k) where k = number of bytes.

- INSERT 10 bytes: 1 DOCISPAN entry
- INSERT 1000 bytes: 1 DOCISPAN entry
- COPY 10 bytes: 1 DOCISPAN entry per contiguous I-span in source

### 2. Spanfilade Growth Rate

The spanfilade grows with the **number of distinct content placements**, not the **total byte count**.

- 1000 documents, each with 1 INSERT of 1000 bytes: ~1000 DOCISPAN entries
- 1000 documents, each with 1000 single-byte INSERTs: ~1,000,000 DOCISPAN entries (if fragmented)
- But Finding 0033 says sequential inserts consolidate, so actually ~1000 entries

### 3. Transclusion Impact

Each COPY creates DOCISPAN entries proportional to the **number of I-spans** in the copied content:

- COPY of contiguous content: 1 entry
- COPY of fragmented content (e.g., 3 separate regions): 3 entries

### 4. Query Performance

Queries like `find_documents` traverse the spanfilade using range queries (enfilade tree structure). Per-span granularity means:

- Fewer nodes to traverse
- More efficient range intersection
- No difference in query results (range-based regardless)

### 5. EWD-031 Storage Growth

From EWD-031: The Storage Problem, this confirms that spanfilade growth is driven by:

- **Content creation**: Each INSERT creates fresh I-addresses → new DOCISPAN entries
- **Transclusion**: Each COPY creates DOCISPAN entries linking dest document to source I-addresses
- **Fragmentation**: Editing operations that disrupt contiguity increase entry count

The storage model is:
```
S(t) = Σ (number of I-spans placed into document d at time t)
```

NOT:
```
S(t) ≠ Σ (total bytes in document d at time t)
```

## Behavioral Evidence

From test `docispan_granularity_insert_contiguous.json`:

```json
{
  "operations": [
    {"op": "insert", "text": "ABCDEFGHIJ (10 bytes)"},
    {"op": "find_documents", "search": "A (1 byte)", "result": ["1.1.0.1.0.1"]},
    {"op": "find_documents", "search": "ABC (3 bytes)", "result": ["1.1.0.1.0.1"]},
    {"op": "find_documents", "search": "ABCDEFGHIJ (all 10 bytes)", "result": ["1.1.0.1.0.1"]}
  ]
}
```

All queries succeed regardless of span size, confirming that:
1. The 10-byte INSERT created discoverable content
2. Queries work at any granularity (range-based)
3. The spanfilade structure supports efficient range queries

## Related Findings

- **Finding 0033**: I-Space Consolidates Adjacent Addresses (explains I-span consolidation)
- **Finding 0036**: INSERT Creates DOCISPAN Entries (documents INSERT → DOCISPAN path)
- **Finding 0012**: Dual Enfilade Architecture (granf + spanf separation)

## Related EWDs

- **EWD-011**: The Dual Index (DOCISPAN as spanfilade type 4)
- **EWD-031**: The Storage Problem (spanfilade growth model)
- **EWD-008**: The Enfilade Invariant (widdative property enables range queries)

## Test Files

- `febe/scenarios/docispan_granularity.py`
- `golden/internal/docispan_granularity_insert_contiguous.json`

## Data Structures

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/xanadu.h:65-76`:

```c
typedef struct structtypespan{
    struct structtypespan *next;   // Linked list pointer
    typeitemid      itemid;        // ISPANID for I-spans
    tumbler stream;                // Starting I-address
    tumbler width;                 // Span width (number of bytes)
} typespan;
typedef typespan * typespanset;

typedef typespan typeispan;
typedef typeispan * typeispanset;
```

An `ispanset` is a linked list of `typeispan` structs, each representing a **contiguous range** of I-addresses.
