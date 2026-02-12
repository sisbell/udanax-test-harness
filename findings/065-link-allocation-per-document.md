# Finding 065: Link I-Address Allocation is Per-Document, Not Global

**Date discovered:** 2026-02-11
**Category:** Link allocation / I-address allocation
**Test scenarios:** `/udanax-test-harness/febe/scenarios/links/allocation.py`

## Summary

Link organizational I-address allocation is **per-document**, using a query-and-increment mechanism within each document's element subspace 2. When MAKELINK is called on document A, then document B, then document A again, document A's second link receives a consecutive element number with its first link. Document B's link allocation does not advance a global counter that would affect document A.

## The Question

EWD-006 states that "Link I-addresses occupy a distinct I-space subspace from text — the element field begins with 2 for link orgls versus 3 for text." The question is whether the allocation of link organizational addresses (the `a_ℓ` that becomes `d.link`) is:

1. **Per-document**: Each document has its own link counter within element subspace 2
2. **Global**: All documents share a single monotonic counter for link allocation

The behavior matters for understanding I-address structure and the independence of document operations.

## The Test

The test scenario `link_allocation_per_document` creates two documents A and B and performs:

1. MAKELINK on document A → creates link L1
2. MAKELINK on document B → creates link L2
3. MAKELINK on document A again → creates link L3

If allocation is per-document, L1 and L3 should have consecutive element numbers (e.g., `docA.2.1` and `docA.2.2`).

If allocation is global, L3 would be non-consecutive with L1 (e.g., `docA.2.1`, then `docB.2.2`, then `docA.2.3`).

## The Result: Per-Document Allocation

**Golden output:** `golden/links/link_allocation_per_document.json`

| Link | Document | Link I-address | Element subspace | Element number |
|------|----------|----------------|------------------|----------------|
| L1 | `1.1.0.1.0.1` (doc A) | `1.1.0.1.0.1.0.2.1` | 2 | **1** |
| L2 | `1.1.0.1.0.2` (doc B) | `1.1.0.1.0.2.0.2.1` | 2 | **1** |
| L3 | `1.1.0.1.0.1` (doc A) | `1.1.0.1.0.1.0.2.2` | 2 | **2** |

**Observation:** Link L3 has element number **2**, which is consecutive with L1's element number **1**. Link L2 in document B also has element number **1**, indicating it started its own independent counter within document B's address space.

**Conclusion:** Allocation is **per-document**. Each document maintains its own monotonic link I-address allocation within element subspace 2.

## Code Mechanism

The allocation mechanism is in `/udanax-test-harness/backend/granf2.c`:

### `findisatoinsertmolecule` (lines 158-181)

```c
static int findisatoinsertmolecule(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
  typeisa upperbound, lowerbound;

    tumblerincrement (&hintptr->hintisa, 2, hintptr->atomtype + 1, &upperbound);
    clear (&lowerbound, sizeof(lowerbound));
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);
    // ...
    else if (hintptr->atomtype == LINKATOM) {
        tumblerincrement (&hintptr->hintisa, 2, 2, isaptr);
        if (tumblercmp (&lowerbound, isaptr) == LESS)
            tumblerincrement (isaptr, 1, 1, isaptr);
        else
            tumblerincrement (&lowerbound , 0, 1, isaptr);
    }
}
```

**Key steps:**

1. **Line 162:** `tumblerincrement(&hintptr->hintisa, 2, hintptr->atomtype + 1, &upperbound)`
   - For `LINKATOM` (value 1), this creates `upperbound = hintisa.2.3`
   - The `hintisa` is the **document's I-address** (from `makehint(DOCUMENT, ATOM, LINKATOM, docisaptr, &hint)`)
   - This bounds the search to **within the document's address space**

2. **Line 164:** `findpreviousisagr((typecorecrum*)fullcrumptr, &upperbound, &lowerbound)`
   - Searches for the highest I-address **less than upperbound**
   - Because upperbound is `docISA.2.3`, the search is confined to this document's link subspace

3. **Lines 171-175:** Allocate next link I-address
   - If `lowerbound < docISA.2.2`, allocate at `docISA.2.2.1` (first link)
   - Otherwise, increment from `lowerbound` (consecutive allocation)

### Why Per-Document?

The `upperbound` is constructed from `hintptr->hintisa`, which is the **document's I-address**. This creates a search boundary that confines `findpreviousisagr` to the document's address space.

The global `granf` (granfilade) stores all documents and links in one tree, but the allocation logic uses **bounded queries** to find the highest existing link within each document's subspace.

## Comparison with Text Allocation

This is consistent with text I-address allocation (Finding 061), which also uses query-and-increment within a bounded region. For text:
- Upperbound: `docISA.2.4` (element subspace 3 for text)
- Search finds highest text I-address within the document

For links:
- Upperbound: `docISA.2.3` (element subspace 2 for links)
- Search finds highest link I-address within the document

Both use the same `findpreviousisagr` function with different bounds.

## Implications

### 1. Document Independence

Link creation in one document does NOT affect link I-address allocation in other documents. Each document can allocate link I-addresses `docISA.2.1`, `docISA.2.2`, ... independently.

This means:
- Parallel link creation across documents is safe (no global allocation bottleneck)
- Link I-addresses are predictable within a document
- No "leakage" of allocation state between documents

### 2. I-Address Structure Consistency

The per-document allocation confirms the hierarchical structure of I-addresses:

```
account.0.document.0.element_field.element_number
```

Where `element_field` is:
- `2` for links
- `3` for text

And `element_number` is allocated monotonically within each (document, element_field) pair.

### 3. Global Granfilade with Local Allocation

The `granf` is a **single global enfilade** (Finding 012), but allocation queries are **bounded by document**. This is the same pattern as document allocation under accounts (Finding 021):

- Global storage: Single granfilade tree holds all content
- Local allocation: Bounded queries ensure hierarchical address allocation

### 4. EWD-006 Correctness

EWD-006's statement that "Link I-addresses occupy a distinct I-space subspace from text — the element field begins with 2 for link orgls versus 3 for text" is correct, and the allocation is **scoped to each document**, not global across all documents.

## Contrast with a Hypothetical Global Allocator

If allocation were global, we would expect:
- A single monotonic counter for all links across all documents
- Link addresses like `1.1.0.1.0.1.0.2.1`, `1.1.0.1.0.2.0.2.2`, `1.1.0.1.0.1.0.2.3` (non-consecutive within a document)
- Cross-document contention during link creation

This is **not** what we observe.

## Related Findings

- **Finding 061**: I-address allocation is monotonic (for text, same mechanism applies to links)
- **Finding 063**: CREATELINK breaks I-address contiguity (for text inserts after link creation)
- **Finding 021**: Address allocation and account boundaries (hierarchical allocation with bounded queries)
- **Finding 012**: Dual enfilade architecture (global granf with per-document operations)

## Code References

- `granf2.c:158-181` — `findisatoinsertmolecule` (link I-address allocation)
- `granf2.c:255-278` — `findpreviousisagr` (bounded tree search)
- `do1.c:211` — `makehint(DOCUMENT, ATOM, LINKATOM, docisaptr, &hint)` (sets document boundary)
- `do2.c:78-84` — `makehint` (copies `docisaptr` to `hintptr->hintisa`)

## Golden Output

`golden/links/link_allocation_per_document.json` — Test showing consecutive allocation within document A despite intervening link creation in document B

## Conclusion

Link organizational I-address allocation is **per-document**, using query-and-increment within each document's element subspace 2. The `upperbound` constraint in `findisatoinsertmolecule` confines the search to the document's address space, ensuring independent allocation across documents.

This confirms the hierarchical I-address structure described in EWD-006 and maintains document operation independence.
