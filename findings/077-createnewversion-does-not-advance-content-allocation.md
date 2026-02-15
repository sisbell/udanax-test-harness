# Finding 077: CREATENEWVERSION Does Not Advance Content Allocation (Σ.next)

**Date discovered:** 2026-02-15
**Category:** Address Allocation / Versioning / Granfilade
**Test:** `/udanax-test-harness/febe/tests/test_createnewversion_iaddress_allocation.py`

## Summary

**CREATENEWVERSION does NOT advance the content allocation counter (Σ.next)** for text bytes. When creating a version `d' = CREATENEWVERSION(d)`, the operation:

1. **Allocates a document address** `d'` via `findisatoinsertnonmolecule` (advances the document counter)
2. **Copies SPAN entries** from `d`'s spanfilade to `d'`'s spanfilade via `insertspanf`
3. **Does NOT allocate new content I-addresses** — no call to `findisatoinsertgr`

This means text inserted after CREATENEWVERSION allocates I-addresses contiguous with text inserted before CREATENEWVERSION, proving that document address allocation and content address allocation use **separate allocation mechanisms**.

## The Question

In udanax-green, is there a single "next" tumbler (Σ.next) used for all allocations, or are there separate allocation counters for:
- Content bytes (via `findisatoinsertgr` in the granfilade)
- Document addresses (via `findisatoinsertnonmolecule`)
- SPAN entries (via `insertspanf` in the spanfilade)

## The Answer: Separate Allocation Spaces

There is **no global Σ.next counter**. Instead, each allocation operation queries the relevant enfilade tree:

| Allocation Type | Function | Tree Queried | Counter Mechanism |
|----------------|----------|--------------|-------------------|
| **Content bytes** | `findisatoinsertgr` → `findisatoinsertmolecule` | **Granfilade** (content storage) | Query-and-increment via `findpreviousisagr` |
| **Document addresses** | `findisatoinsertnonmolecule` | **Granfilade** (same tree, different range) | Query-and-increment via `findpreviousisagr` |
| **SPAN entries** | `insertspanf` | **Spanfilade** (V→I mappings) | **No allocation** — uses provided I-addresses |

### Key Insight: SPAN Operations Don't Allocate I-Addresses

`insertspanf` does **not** allocate new I-addresses. It takes an I-span as input (from the caller) and inserts a mapping into the spanfilade. The function signature reveals this:

```c
// spanf1.c:15
bool insertspanf(typetask *taskptr, typespanf spanfptr, typeisa *isaptr, 
                 typesporglset sporglset, INT spantype)
```

The `sporglset` parameter contains the I-spans to be recorded. `insertspanf` uses `prefixtumbler` to construct the ORGLRANGE coordinate (document address prefixed with spantype), then calls `insertnd` to insert into the 2D spanfilade tree:

```c
// spanf1.c:22-51
prefixtumbler (isaptr, spantype, &crumorigin.dsas[ORGLRANGE]);
// ...
for (; sporglset; sporglset = ...) {
    movetumbler (&((typeispan *)sporglset)->stream, &lstream);
    movetumbler (&((typeispan *)sporglset)->width, &lwidth);
    movetumbler (isaptr, &linfo.homedoc);
    movetumbler (&lstream, &crumorigin.dsas[SPANRANGE]);
    movetumbler (&lwidth, &crumwidth.dsas[SPANRANGE]);
    insertnd(taskptr, (typecuc*)spanfptr, &crumorigin, &crumwidth, &linfo, SPANRANGE);
}
```

The I-span coordinates (`lstream`, `lwidth`) are **copied from the input**, not allocated.

## Test Evidence

### Experiment: INSERT → CREATENEWVERSION → INSERT

```python
# 1. Insert "ABC" into doc1
session.insert(doc1, Address(1, 1), ["ABC"])
# I-span: starts at some address I₀

# 2. Create version doc2
doc2 = session.create_version(doc1)

# 3. Insert "XYZ" into doc1
session.insert(doc1, Address(1, 4), ["XYZ"])
# I-span: starts at I₀ + 3 (contiguous with ABC)
```

**Result from test:**

```
After INSERT ABC: vspec = <VSpec in 1.1.0.1.0.1, at 1.1 for 0.3>
Created version: 1.1.0.1.0.1.2
After INSERT XYZ: vspec = <VSpec in 1.1.0.1.0.1, at 1.1 for 0.6>

Number of shared I-span pairs: 1
✓ CREATENEWVERSION did NOT advance Σ.next (content allocation counter)
  XYZ I-addresses are contiguous with ABC
  Combined I-span: 1.1.0.1.0.1.3.0.1.1 + 0.6
```

The `compare_versions` result shows **1 shared span pair** covering all 6 characters. If CREATENEWVERSION had consumed I-addresses, we would see **2 shared span pairs** (one for ABC, one for XYZ with a gap between them).

### Comparison with CREATELINK

From Finding 063, we know that CREATELINK **does** advance the content allocation counter:

```
INSERT "ABC" → CREATELINK → INSERT "DEF"
Result: 2 shared span pairs (gap between ABC and DEF)
```

This is because `CREATELINK` calls `createorglingranf`, which allocates an I-address for the link orgl via `findisatoinsertgr`.

## Implementation Analysis

### CREATENEWVERSION Call Chain

```c
// do1.c:260-299
bool docreatenewversion(typetask *taskptr, typeisa *isaptr, typeisa *wheretoputit, typeisa *newisaptr)
{
    // 1. Allocate document address for d'
    makehint (DOCUMENT, DOCUMENT, 0, isaptr, &hint);
    createorglingranf(taskptr, granf, &hint, newisaptr);  // ← Allocates document address
    
    // 2. Retrieve d's V-span
    doretrievedocvspanfoo (taskptr, isaptr, &vspan);
    
    // 3. Copy d's content to d' (SPAN entries only, no new I-addresses)
    addtoopen(newisaptr, user, TRUE, WRITEBERT);
    docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);  // ← Calls insertspanf
    logbertmodified(newisaptr, user);
    doclose(taskptr, newisaptr, user);
    
    return (TRUE);
}
```

### docopyinternal Call Chain

```c
// do1.c:66-82
bool docopyinternal(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
    specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED);
    findorgl (taskptr, granf, docisaptr, &docorgl, NOBERTREQUIRED);
    insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset);     // ← Updates POOM
    insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN);  // ← Records SPAN entries
    return TRUE;
}
```

**Key observation:** `docopyinternal` receives an `ispanset` containing the I-addresses from the source document. These I-addresses are **not freshly allocated** — they are the same I-addresses that already exist in the granfilade. The operation merely creates new V→I mappings in `d'`'s POOM and spanfilade.

## Allocation Mechanism Summary

### Content Allocation (findisatoinsertgr)

Used by:
- `inserttextgr` (INSERT operation)
- `createorglingranf` when allocating **content** (link orgls, text bytes)

Mechanism:
```c
// granf2.c:130-156
bool findisatoinsertgr(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    if (hintptr->subtype == ATOM) {
        findisatoinsertmolecule (fullcrumptr, hintptr, isaptr);  // ← For text/link content
    } else {
        findisatoinsertnonmolecule (fullcrumptr, hintptr, isaptr);  // ← For documents
    }
    return (TRUE);
}
```

Both `findisatoinsertmolecule` and `findisatoinsertnonmolecule` query the granfilade tree via `findpreviousisagr` and increment from the highest existing address.

### Document Allocation (findisatoinsertnonmolecule)

Used by:
- `docreatenewdocument` (CREATE operation)
- `docreatenewversion` (VERSION operation)
- `createorglingranf` when allocating **documents** (not content)

Mechanism:
```c
// granf2.c:203-242
static int findisatoinsertnonmolecule(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    depth = hintptr->supertype == hintptr->subtype ? 1 : 2;
    tumblerincrement (&hintptr->hintisa, depth - 1, 1, &upperbound);
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);
    
    // Allocate first child or increment from found address
    if (iszerotumbler(&lowerbound) || !lowerbound_under_hint) {
        tumblerincrement(&hintptr->hintisa, depth, 1, isaptr);  // First: hintisa.0.1
    } else {
        tumblertruncate (&lowerbound, hintlength + depth, isaptr);
        tumblerincrement(isaptr, ..., 1, isaptr);  // Subsequent: increment
    }
}
```

This queries the **same granfilade tree** as content allocation, but searches a different tumbler range (under the parent document/account, not under the content subspace).

### SPAN Recording (insertspanf)

Used by:
- `docopy` / `docopyinternal` (COPY and VERSION operations)
- `insertendsetsinspanf` (CREATELINK operation for link endsets)

Mechanism:
- **No allocation** — takes I-spans as input parameters
- Inserts mappings into the **spanfilade** (a separate 2D enfilade from the granfilade)
- The spanfilade maps `(document, V-span)` → `I-span`

## Consequences

### 1. CREATENEWVERSION is a "Weak" Operation for Content Allocation

Like DELETE (Finding 061), CREATENEWVERSION does **not** affect the content allocation counter. It only:
- Allocates a new document address (in the document subspace)
- Copies SPAN entries (metadata, not content)

This means:
```
INSERT "ABC" → CREATENEWVERSION → INSERT "XYZ"
Result: ABC and XYZ have contiguous I-addresses (no gap)
```

Contrast with:
```
INSERT "ABC" → CREATELINK → INSERT "XYZ"
Result: ABC and XYZ have non-contiguous I-addresses (gap from link orgl)
```

### 2. Document Address Space is Separate from Content Address Space

The granfilade stores both documents and content, but they are allocated from **different tumbler ranges**:

```
1.1.0.1           (account)
├── 1.1.0.1.0.1   (document d₁)
│   ├── 1.1.0.1.0.1.1  (version v₁ of d₁)
│   └── 1.1.0.1.0.1.2  (version v₂ of d₁)
└── 1.1.0.1.0.2   (document d₂)

1.1.0.1.0.1.3.0.1.1   (content I-address for text in d₁)
1.1.0.1.0.1.3.0.1.2   (next content I-address)
```

Document addresses are allocated under the parent account/document (depth 1 or 2), while content addresses are allocated under the document's content subspace (depth 3+).

### 3. Σ.next is Not a Single Counter

The term "Σ.next" from EWDs suggests a single high-water mark for all allocations. But the implementation uses **stateless query-and-increment** on different tumbler ranges:

- **No session-local counter** — each allocation queries the tree
- **No global "next" field** — allocation is determined by `findpreviousisagr` results
- **Multiple allocation spaces** — documents, content, links, etc. have independent counters

### 4. SPAN Operations are Pure Metadata

`insertspanf` does not allocate addresses — it records existing I-addresses in the spanfilade. This makes SPAN operations "metadata-only":
- COPY → records existing I-addresses in a new document's spanfilade
- CREATENEWVERSION → same as COPY (no new content allocation)
- DELETE → removes V→I mappings from spanfilade (no granfilade changes)

## Related Findings

- **Finding 061: I-Address Allocation is Monotonic** — Documents stateless query-and-increment for content
- **Finding 063: CREATELINK Breaks I-Address Contiguity** — Contrast: CREATELINK **does** advance content allocation
- **Finding 068: VERSION Allocates Addresses as Children** — Documents document address allocation (this finding documents content allocation)
- **Finding 021: Address Allocation and Account Boundaries** — Documents `findisatoinsertnonmolecule` mechanism

## Code References

- `do1.c:260-299` — `docreatenewversion` (VERSION entry point)
- `do1.c:66-82` — `docopyinternal` (calls `insertspanf`, not `findisatoinsertgr`)
- `spanf1.c:15-54` — `insertspanf` (records SPAN entries without allocating I-addresses)
- `granf2.c:130-156` — `findisatoinsertgr` (content allocation dispatcher)
- `granf2.c:158-181` — `findisatoinsertmolecule` (ATOM/text content allocation)
- `granf2.c:203-242` — `findisatoinsertnonmolecule` (document allocation)
- `granf2.c:255-278` — `findpreviousisagr` (tree traversal to find highest address)

## Conclusion

**CREATENEWVERSION does NOT advance Σ.next** (the content allocation counter). The operation:

1. **Allocates** a new document address `d'` via `findisatoinsertnonmolecule` (in the document address space)
2. **Copies** SPAN entries from `d` to `d'` via `insertspanf` (metadata only, no new I-addresses)
3. **Does NOT call** `findisatoinsertgr` (no content allocation)

This proves that **document address allocation and content address allocation are separate**:
- Document addresses: allocated via `findisatoinsertnonmolecule` under parent account/document
- Content addresses: allocated via `findisatoinsertmolecule` under document's content subspace
- SPAN entries: recorded via `insertspanf` (no allocation, pure metadata)

The concept of "Σ.next" as a single counter is a simplification. The actual implementation uses **stateless query-and-increment** on different tumbler ranges within the granfilade tree.
