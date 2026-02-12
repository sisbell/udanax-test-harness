# Finding 068: VERSION Allocates Addresses as Children of the Source Document

**Date discovered:** 2026-02-12
**Category:** Address Allocation, Versioning
**Test scenarios:** `/udanax-test-harness/golden/versions/version_address_allocation.json`

## Summary

When `CREATENEWVERSION(d)` creates a new version `d'`, the new document's address is allocated **as a child of `d`**, not as a sibling under `d`'s parent account. The allocation uses the same monotonic query-and-increment mechanism as other document operations, searching the granfilade for the highest existing child under `d` and incrementing from there.

## The Question

When creating a version of document `d = 1.1.0.1.0.1`, does the system:
1. Allocate `d'` under `d`'s parent account (like CREATE), producing `1.1.0.1.0.2`, or
2. Allocate `d'` as a child of `d`, producing `1.1.0.1.0.1.1`?

And what mechanism guarantees freshness - is it the same monotonic query-and-increment as element allocation?

## The Answer: Child Allocation with Ownership Sensitivity

**VERSION allocates addresses as children of the source document**, using a context-sensitive hint mechanism:

```c
// do1.c:272-280
if (tumbleraccounteq(isaptr, wheretoputit) && isthisusersdocument(isaptr)) {
    makehint (DOCUMENT, DOCUMENT, 0, isaptr/*wheretoputit*/, &hint);
} else {
    /* This does the right thing for new version of someone else's document, as it
       duplicates the behavior of docreatenewdocument */
    makehint (ACCOUNT, DOCUMENT, 0, wheretoputit, &hint);
}
```

**Case 1: User owns the document** (`isaptr` and `wheretoputit` are in the same account)
- Hint: `makehint(DOCUMENT, DOCUMENT, 0, isaptr, &hint)`
- Result: Version allocated as **child of `isaptr`** (e.g., `1.1.0.1.0.1` → `1.1.0.1.0.1.1`)

**Case 2: User does NOT own the document** (creating version of someone else's document)
- Hint: `makehint(ACCOUNT, DOCUMENT, 0, wheretoputit, &hint)`
- Result: Version allocated **under user's account** (like CREATE)

## Test Evidence

From `/udanax-test-harness/golden/versions/version_address_allocation.json`:

| Operation | Source Document | Result Address | Pattern |
|-----------|----------------|----------------|---------|
| create_document (doc1) | - | **1.1.0.1.0.1** | First document under account |
| create_document (doc2) | - | **1.1.0.1.0.2** | Second document under account |
| create_version (doc1) | 1.1.0.1.0.1 | **1.1.0.1.0.1.1** | Child of doc1 |
| create_version (doc1) | 1.1.0.1.0.1 | **1.1.0.1.0.1.2** | Second child of doc1 |
| create_version (doc2) | 1.1.0.1.0.2 | **1.1.0.1.0.2.1** | Child of doc2 |
| create_version (version1) | 1.1.0.1.0.1.1 | **1.1.0.1.0.1.1.1** | Child of version1 |

**Key observations:**

1. **Child allocation**: Version of `1.1.0.1.0.1` is `1.1.0.1.0.1.1`, not `1.1.0.1.0.2`
2. **Monotonic increment**: Second version of same document is `1.1.0.1.0.1.2` (not `.1` again)
3. **Version chains**: Versions can be versioned using the same mechanism (`.1.1.1`)
4. **Per-document namespace**: Versions of different documents have independent counters

## Implementation: Hint-Based Allocation

### Step 1: Create Hint

```c
// do1.c:275 (ownership case)
makehint (DOCUMENT, DOCUMENT, 0, isaptr, &hint);
```

This creates a hint with:
- `supertype = DOCUMENT` (parent is a document)
- `subtype = DOCUMENT` (child is a document)
- `hintisa = isaptr` (the source document address)

From Finding 021, we know `depth = (supertype == subtype) ? 1 : 2`, so for `DOCUMENT, DOCUMENT`, **depth = 1**.

### Step 2: Allocate Address

```c
// granf2.c:130-155
bool findisatoinsertgr(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    // For non-ATOM types (DOCUMENT, ACCOUNT, NODE), use findisatoinsertnonmolecule
    findisatoinsertnonmolecule (fullcrumptr, hintptr, isaptr);
    tumblerjustify(isaptr);
    return (TRUE);
}
```

### Step 3: Query and Increment

```c
// granf2.c:203-242
static int findisatoinsertnonmolecule(typecuc *fullcrumptr, typehint *hintptr, typeisa *isaptr)
{
    depth = hintptr->supertype == hintptr->subtype ? 1 : 2;  // depth = 1 for VERSION

    // Compute upperbound: hintisa + 1 at depth-1 position
    tumblerincrement (&hintptr->hintisa, depth - 1, 1, &upperbound);
    // For hintisa = 1.1.0.1.0.1 with depth=1: upperbound = 1.1.0.1.0.2

    // Find highest existing item under upperbound
    findpreviousisagr ((typecorecrum*)fullcrumptr, &upperbound, &lowerbound);

    // Check if found item is actually under hintisa (not from different account)
    if (!iszerotumbler(&lowerbound)) {
        tumblertruncate(&lowerbound, hintlength, &truncated);
        lowerbound_under_hint = tumblereq(&truncated, &hintptr->hintisa);
    }

    if (iszerotumbler(&lowerbound) || !lowerbound_under_hint) {
        // Nothing under this hint - create first child as hintisa.0.1
        tumblerincrement(&hintptr->hintisa, depth, 1, isaptr);
        // For hintisa = 1.1.0.1.0.1 with depth=1: result = 1.1.0.1.0.1.1
    } else {
        // Found existing child - truncate and increment
        tumblertruncate (&lowerbound, hintlength + depth, isaptr);
        tumblerincrement(isaptr, tumblerlength(isaptr)==hintlength?depth:0, 1, isaptr);
    }
}
```

**Example trace for second version of `1.1.0.1.0.1`:**
1. `hintisa = 1.1.0.1.0.1`, `depth = 1`
2. `upperbound = tumblerincrement(1.1.0.1.0.1, 0, 1) = 1.1.0.1.0.2`
3. `findpreviousisagr` finds `lowerbound = 1.1.0.1.0.1.1` (first version)
4. Truncate `1.1.0.1.0.1.1` to length 6+1=7: `isaptr = 1.1.0.1.0.1.1`
5. Increment: `1.1.0.1.0.1.1 + 1 = 1.1.0.1.0.1.2`

## Comparison with CREATE

| Operation | Hint | Allocation Prefix | First Address | Second Address |
|-----------|------|-------------------|---------------|----------------|
| **CREATE** | `makehint(ACCOUNT, DOCUMENT, 0, account, &hint)` | Under **account** | `1.1.0.1.0.1` | `1.1.0.1.0.2` |
| **VERSION (owned)** | `makehint(DOCUMENT, DOCUMENT, 0, isaptr, &hint)` | Under **source document** | `1.1.0.1.0.1.1` | `1.1.0.1.0.1.2` |
| **VERSION (unowned)** | `makehint(ACCOUNT, DOCUMENT, 0, wheretoputit, &hint)` | Under **user's account** | `1.1.0.1.0.1` | `1.1.0.1.0.2` |

## Freshness Guarantee: Same Mechanism as Element Allocation

Like element (ATOM) allocation documented in Finding 061, VERSION uses **stateless query-and-increment**:

1. **Query granfilade tree**: `findpreviousisagr` walks the tree to find the highest existing address under the hint
2. **Increment**: Add 1 to the found address (or create first child if none found)
3. **No session-local counter**: Each VERSION operation independently queries the tree

This ensures:
- **Monotonic allocation**: Addresses never reuse deleted documents
- **Consistency**: Works correctly across multiple sessions or concurrent operations
- **Prefix containment**: All versions of `d` are allocated under `d.x`

## Semantic Implications

### 1. Version Trees

Documents form **hierarchical version trees**:
```
1.1.0.1.0.1              (doc1)
├── 1.1.0.1.0.1.1        (version1 of doc1)
│   └── 1.1.0.1.0.1.1.1  (version of version1)
└── 1.1.0.1.0.1.2        (version2 of doc1)

1.1.0.1.0.2              (doc2)
└── 1.1.0.1.0.2.1        (version1 of doc2)
```

Each document is the **root of its own version tree**. The address structure explicitly encodes the version lineage.

### 2. Version Chains Are Nested

Creating a version of a version produces **nested addresses**:
- `d = 1.1.0.1.0.1`
- `v1 = VERSION(d) = 1.1.0.1.0.1.1`
- `v2 = VERSION(v1) = 1.1.0.1.0.1.1.1`

This is different from a "sibling" model where all versions would be flat children of the account.

### 3. Cross-User Versioning

The ownership check (`tumbleraccounteq` and `isthisusersdocument`) enables **cross-user versioning**:
- User A creates `1.1.0.1.0.1`
- User B (with account `1.1.0.2`) creates a version
- Result: `1.1.0.2.0.1` (allocated under User B's account, not under User A's document)

This allows users to create their own versions of shared documents without modifying the original's version tree.

### 4. Deletion Does Not Affect Allocation

Like Finding 061 for elements, **deleting a version does not free its address**. The granfilade tree retains all allocated addresses permanently, so:
- Create `1.1.0.1.0.1.1`
- Delete `1.1.0.1.0.1.1`
- Create another version → `1.1.0.1.0.1.2` (not `.1` reused)

## Related Findings

- **Finding 021: Address Allocation and Account Boundaries** - Documents how `findisatoinsertnonmolecule` works for DOCUMENT allocation
- **Finding 061: I-Address Allocation is Monotonic** - Explains the stateless query-and-increment mechanism used for elements
- **Finding 007: Version Semantics** - Documents version behavior at the operational level (this finding explains the underlying allocation mechanism)
- **Finding 043: CREATENEWVERSION Copies Text Only** - Documents what content is copied (this finding explains where the new document is allocated)

## Code References

- `do1.c:264-303` - `docreatenewversion` (main VERSION entry point)
- `do1.c:272-280` - Ownership-sensitive hint creation
- `do2.c:78-84` - `makehint` (encodes hierarchy levels)
- `granf2.c:111-128` - `createorglgr` (creates document at allocated address)
- `granf2.c:130-156` - `findisatoinsertgr` (allocation dispatcher)
- `granf2.c:203-242` - `findisatoinsertnonmolecule` (query-and-increment allocation logic)
- `granf2.c:255-278` - `findpreviousisagr` (tree traversal to find highest address)

## Conclusion

**VERSION allocates addresses as children of the source document** (when owned by the user), using the **same monotonic query-and-increment mechanism** as element allocation. This produces a **hierarchical version tree** structure where:

1. Each document is the root of its own version namespace
2. Versions are numbered monotonically: `.1`, `.2`, `.3`, etc.
3. Version chains create nested addresses: `.1.1`, `.1.2`, etc.
4. Cross-user versions allocate under the creating user's account, not under the source document

The allocation is stateless (queries the granfilade tree on each operation) and guarantees freshness through monotonic increment, never reusing deleted addresses.
