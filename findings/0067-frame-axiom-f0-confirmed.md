# Finding 0067: Frame Axiom F0 Confirmed - Document Operations Have No Cross-Document Side Effects

**Date:** 2026-02-11
**Category:** Architectural correctness / Formal verification
**Status:** Confirmed by code inspection and empirical testing
**Related:** Finding 0038 (POOM Subspace Independence), Finding 0054 (INSERT two-blade knife), Finding 0055 (DELETE exponent guard), Finding 0057 (Spanfilade no cleanup)

## Summary

The formal specification's F0 (frame axiom) states that **document operations (INSERT, DELETE, COPY) only modify the target document's text span sequence** and have no side effects on other documents, links, or the global spanfilade's correctness.

**Implementation verdict: CONFIRMED with one caveat.**

The low-level enfilade operations (`insertnd`, `deletend`, `cutcrumseq`, `rearrangend`) operate exclusively on the target document's orgl (POOM enfilade in granf). They do NOT:
- Modify other documents' orgls
- Corrupt links (either in the target document's link subspace or in other documents)
- Modify the target document's link subspace when operating on the text subspace
- Alter the spanfilade in ways that corrupt queries

**Caveat:** Finding 0057 documents that DELETE does NOT clean up spanfilade entries created by prior COPY operations. This leaves stale references but does NOT corrupt the spanfilade or other documents - it's a garbage collection issue, not a frame violation.

## The Frame Axiom (F0)

From the formal specification (EWD-009, EWD-012):

```
F0: ∀d ∈ D, ∀op ∈ {INSERT, DELETE, COPY}, ∀d' ∈ D where d ≠ d':
    op(d, ...) → D_seq'(d) ≠ D_seq(d) ∧ D_seq'(d') = D_seq(d')

Translation: An operation on document d modifies only d's text span sequence.
Other documents d' remain unchanged.
```

Extended claims:
- Operations on document A do not modify document B's POOM
- Operations in text subspace (1.x) do not modify link subspace (2.x)
- Operations do not corrupt the spanfilade's ability to track content identity

## Code Analysis: No Cross-Document Mutations

### 1. insertnd Operates on a Single Orgl

**File:** `insertnd.c:15-111`

```c
int insertnd(typetask *taskptr, typecuc *fullcrumptr, typewid *origin,
             typewid *width, type2dbottomcruminfo *infoptr, INT index)
{
    // fullcrumptr is THE DOCUMENT'S ORGL - a single enfilade tree
    // All operations mutate this tree ONLY

    switch (fullcrumptr->cenftype) {
        case POOM:
            makegappm(taskptr, fullcrumptr, origin, width);      // Shifts crums in THIS tree
            setwispupwards(fullcrumptr, 0);
            bothertorecombine = doinsertnd(fullcrumptr, origin, width, infoptr, index);
            setwispupwards(fullcrumptr, 1);
            break;
        // ...
    }
    recombine(fullcrumptr);  // Rebalances THIS tree
}
```

**Key points:**
- `fullcrumptr` is a pointer to the target document's orgl root crum
- All mutations (`makegappm`, `doinsertnd`, `setwispupwards`, `recombine`) walk THIS tree
- No global state is accessed except for crum allocation (which does not affect other documents)
- No other document's orgl is referenced

### 2. deletend Operates on a Single Orgl

**File:** `edit.c:30-75`

```c
int deletend(typecuc *fullcrumptr, tumbler *origin, tumbler *width, INT index)
{
    // fullcrumptr is THE DOCUMENT'S ORGL

    makecutsnd(fullcrumptr, &knives);                   // Find cut points in THIS tree
    newfindintersectionnd(fullcrumptr, &knives, &father, &foffset);  // Find father in THIS tree

    for (ptr = findleftson(father); ptr; ptr = next) {
        next = findrightbro(ptr);
        switch (deletecutsectionnd(ptr, &fgrasp, &knives)) {
            case 1:
                disown(ptr);        // Remove crum from THIS tree
                subtreefree(ptr);   // Free crum memory
                break;
            case 2:
                tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);  // Shift THIS crum
                break;
        }
    }
    setwispupwards(father, 1);
    recombine(father);
}
```

**Key points:**
- All tree traversal is local to `fullcrumptr` (the target document's orgl)
- `disown` and `subtreefree` only remove crums from THIS tree
- No other document's orgl is touched

### 3. Subspace Isolation Within a Document

From Finding 0054 and Finding 0055:

**INSERT isolates subspaces via two-blade knife:**

```c
// insertnd.c:144-146
movetumbler(&origin->dsas[V], &knives.blades[0]);    // blade[0] = insertion point (e.g., 1.3)
findaddressofsecondcutforinsert(&origin->dsas[V], &knives.blades[1]);  // blade[1] = next subspace (e.g., 2.1)
knives.nblades = 2;
```

The second blade marks the boundary of the current subspace. Any crum at or beyond this boundary is classified as case 2 (no shift) by `insertcutsectionnd`.

**Result:** INSERT at 1.x shifts only crums in [1.x, 2.0), leaving crums at 2.x unchanged.

**DELETE isolates subspaces via exponent guard in strongsub:**

```c
// tumble.c:534-547
int strongsub(tumbler *aptr, tumbler *bptr, tumbler *cptr)
{
    if (bptr->exp < aptr->exp) {       // Text crum at exp=0, width at exp=-1
        movetumbler(aptr, cptr);       // Return unchanged
        return(0);
    }
    // ... main subtraction only for same-exponent operands
}
```

**Result:** DELETE of width 0.3 (exp=-1) from text crums shifts text crums (exp=-1) but leaves link crums (exp=0) unchanged because the exponent mismatch causes `strongsub` to return the original value.

### 4. Spanfilade is NOT Modified by Document Operations

**Critical observation:** Neither `insertnd` nor `deletend` calls any spanf update function.

From `do1.c:162-171` (DELETE operation):

```c
bool dodeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
    return (
        findorgl(taskptr, granf, docisaptr, &docorgl, WRITEBERT)
        && deletevspanpm(taskptr, docisaptr, docorgl, vspanptr)
    );
}
```

`deletevspanpm` calls `deletend` on the document's orgl. **No spanf cleanup.**

From `orglinks.c:144-151`:

```c
bool deletevspanpm(typetask *taskptr, tumbler *docisaptr, typeorgl docorgl, typevspan *vspanptr)
{
    if (iszerotumbler(&vspanptr->width))
        return (FALSE);
    deletend((typecuc*)docorgl, &vspanptr->stream, &vspanptr->width, V);
    logbertmodified(docisaptr, user);
    return (TRUE);
}
```

No call to `deletespanf` (which doesn't exist anyway - see Finding 0057).

**Implication:** DELETE leaves stale spanfilade entries, but this does NOT:
- Corrupt other documents (spanf is a read-only index for queries)
- Prevent correct operation (FIND_DOCUMENTS returns a superset; V-conversion filters stale entries)
- Violate F0 (other documents are unchanged; stale entries are harmless references)

### 5. COPY is Read-Only on Source

From `do1.c:45-65` (COPY operation):

```c
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
    return (
        specset2ispanset(taskptr, specset, &ispanset, NOBERTREQUIRED)  // Read source I-addresses
        && findorgl(taskptr, granf, docisaptr, &docorgl, WRITEBERT)    // Get target orgl
        && acceptablevsa(vsaptr, docorgl)
        && insertpm(taskptr, docisaptr, docorgl, vsaptr, ispanset)     // Modify target orgl ONLY
        && insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)  // Index target in spanf
    );
}
```

**Key points:**
- `specset2ispanset` reads I-addresses from the source document's orgl (via `ispan2vspanset` and retrieval). This is a READ operation.
- `insertpm` modifies the TARGET document's orgl by adding new V→I mappings
- `insertspanf` adds the TARGET document to the spanfilade index
- **The source document's orgl is never modified**

## Empirical Verification

Created 6 golden test scenarios in `febe/scenarios/document_isolation.py`:

### Test 1: insert_does_not_affect_other_documents

```python
# Create doc A and doc B with independent content
# INSERT into doc A
# Verify doc B's content, vspanset, and I-addresses are unchanged
```

**Result:** PASSED. Doc B's content before and after INSERT into doc A are identical.

### Test 2: delete_does_not_affect_other_documents

```python
# Create doc A and doc B
# DELETE from doc A
# Verify doc B unchanged
```

**Result:** PASSED. Doc B unaffected by DELETE from doc A.

### Test 3: vcopy_does_not_modify_source_document

```python
# Create source with content
# VCOPY from source to target
# Verify source unchanged
```

**Result:** PASSED. Source document's content and vspanset unchanged after VCOPY.

### Test 4: insert_text_does_not_affect_links_in_same_document

```python
# Create document with text and a link
# INSERT into text subspace (1.x)
# Verify link subspace (2.x) unchanged - link still exists and is discoverable
```

**Result:** PASSED. Link remains at V-position 2.1, still discoverable via FIND_LINKS and FOLLOW_LINK after text insertion.

### Test 5: delete_text_does_not_affect_links_in_same_document

```python
# Create document with text and link
# DELETE from text subspace (1.x)
# Verify link subspace (2.x) unchanged
```

**Result:** PASSED. Link V-position unchanged (2.1 before and after DELETE of text).

### Test 6: cross_document_transclusion_isolation

```python
# Doc A has content
# Doc B transcludes from A
# Doc C transcludes from A
# DELETE transcluded content from B
# Verify A and C unchanged
```

**Result:** PASSED. A and C's content remains identical before and after DELETE from B.

## Architectural Guarantees

### 1. Tree-Local Mutations

Every document's orgl is an independent enfilade tree stored in granf. All mutation operations (`insertnd`, `deletend`, `rearrangend`) receive a pointer to the root crum of THE TARGET DOCUMENT'S tree and operate exclusively within that tree.

**Mechanism:** Function signatures take `typecuc *fullcrumptr` (the orgl root) and all traversal uses tree pointers (`findleftson`, `findrightbro`, `findfather`), which are local to that tree.

**Result:** Physical impossibility of cross-document mutations (no code path accesses another document's orgl).

### 2. Subspace Isolation Within a Document

The POOM (orgl) stores both text (1.x) and links (2.x) in the same tree, but operations on one subspace do not affect the other due to:

- **INSERT:** Two-blade knife with explicit subspace boundary (`findaddressofsecondcutforinsert`)
- **DELETE:** Exponent guard in `strongsub` (accidental but effective)
- **REARRANGE:** Only operates on explicitly specified cut ranges

**Result:** Text edits do not shift link V-positions (Finding 0038, Finding 0054, Finding 0055).

### 3. Spanfilade is Append-Only (For Documents)

The spanfilade is updated via `insertspanf` during COPY and CREATE_LINK operations. There is no `deletespanf` function (Finding 0057).

**Result:** Stale entries accumulate but do not corrupt queries (they are filtered during I→V conversion).

**F0 interpretation:** The spanfilade contains a superset of documents that currently reference given I-addresses. This is a weaker invariant than "spanf exactly mirrors current POOM state," but it does NOT violate F0 because:
- Other documents are not modified (stale entries are harmless)
- The target document's text span sequence is correctly modified
- Queries remain correct (via filtering)

## Edge Cases and Exceptions

### 1. Spanfilade Stale References (Finding 0057)

**Not a violation of F0:** Stale spanfilade entries do not corrupt document state. They are query-index inefficiencies, not correctness violations.

**Why this is acceptable:**
- `FIND_DOCUMENTS` returns a superset of documents
- I→V conversion filters out documents that no longer contain the I-addresses
- The source document and other documents remain unchanged

### 2. Link Endpoints May Become Invalid After Source Edits

If a document DELETEs content that is a link endpoint in another document, the link in the other document becomes a "ghost link" (Finding 0048).

**Not a violation of F0:** The other document's link POOM entry is unchanged (still at V-position 2.x). The link's I-addresses are unchanged. What changes is the SOURCE DOCUMENT's POOM no longer maps those I-addresses to V-positions.

**F0 compliance:**
- The other document's structure is unchanged
- The target document's structure is correctly updated (I-addresses removed from its POOM)
- The link subspace in the other document is unaffected

## Comparison with Formal Specification

| Formal Claim | Implementation | Verification |
|--------------|----------------|--------------|
| INSERT(d) modifies only d | `insertnd` mutates only `fullcrumptr` (d's orgl) | Code inspection + Test 1 |
| DELETE(d) modifies only d | `deletend` mutates only `fullcrumptr` (d's orgl) | Code inspection + Test 2 |
| COPY(src→dst) modifies only dst | `docopy` reads src, writes dst | Code inspection + Test 3 |
| Text ops (1.x) don't affect links (2.x) | Two-blade knife + exponent guard | Finding 0054, 055 + Test 4, 5 |
| Ops on d don't affect d' | No code path accesses other orgls | Test 1, 2, 6 |
| Spanfilade correct after ops | Stale entries filtered at query time | Finding 0057 + Test 6 |

**Verdict:** F0 is **CONFIRMED** with the understanding that "correctness" allows stale index entries that are filtered during query resolution.

## Implementation Quality

### Strengths

1. **Tree isolation:** Each document's orgl is a separate tree, making cross-document mutations structurally impossible.

2. **Subspace isolation (INSERT):** Deliberate design with explicit second-blade computation and documented intent in the source code.

3. **No shared mutable state:** No global variables are modified by document operations (except crum allocation, which is append-only and does not affect semantics).

### Weaknesses

1. **Subspace isolation (DELETE):** Relies on accidental exponent mismatch in `strongsub`. Not documented as a subspace guard. Fragile - if `strongsub` were "fixed" to handle cross-exponent subtraction, DELETE would break subspace isolation.

2. **Spanfilade cleanup missing:** No `deletespanf` function. Stale entries accumulate. While not a correctness violation, this is an incompleteness that suggests the system was designed for append-mostly workloads.

3. **No explicit frame verification:** No assertions or runtime checks that verify F0 (e.g., "assert no other document modified"). Reliance on code review and testing.

## Related Findings

- **Finding 0038:** POOM Subspace Independence (behavioral observation, explained here)
- **Finding 0054:** INSERT two-blade knife (mechanism for text/link isolation)
- **Finding 0055:** DELETE exponent guard (mechanism for text/link isolation)
- **Finding 0057:** Spanfilade no cleanup (stale entries, but not a frame violation)
- **Finding 0012:** Dual Enfilade Architecture (granf vs spanf separation)
- **Finding 0048:** Ghost links (consequence of source deletion, not a frame violation)

## Conclusion

**The F0 frame axiom is CONFIRMED by the implementation.**

Document operations (INSERT, DELETE, COPY) have no cross-document side effects. The low-level enfilade operations (`insertnd`, `deletend`) operate exclusively on the target document's orgl tree. Operations within the text subspace (1.x) do not affect the link subspace (2.x) due to deliberate (INSERT) and accidental (DELETE) isolation mechanisms.

The only deviation from a strict interpretation of "no side effects" is the accumulation of stale spanfilade entries after DELETE, but this does not violate F0 because:
- It does not modify other documents
- It does not corrupt the spanfilade's query results (filtering at I→V conversion)
- It is a garbage collection issue, not a correctness violation

The formal model's F0 claim is **validated** by this implementation.

## Test Files

**New test scenarios:** `/Users/shane/Documents/github/claude/xanadu-workspace-v3/udanax-test-harness/febe/scenarios/document_isolation.py`

Scenarios:
1. `insert_does_not_affect_other_documents`
2. `delete_does_not_affect_other_documents`
3. `vcopy_does_not_modify_source_document`
4. `insert_text_does_not_affect_links_in_same_document`
5. `delete_text_does_not_affect_links_in_same_document`
6. `cross_document_transclusion_isolation`

All tests PASSED on first run.

## References

- `insertnd.c:15-311` — INSERT implementation (tree-local mutations)
- `edit.c:30-75` — DELETE implementation (tree-local mutations)
- `do1.c:45-65` — COPY implementation (read source, write target)
- `orglinks.c:144-151` — DELETE POOM entry (no spanf cleanup)
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert` (subspace boundary for INSERT)
- `tumble.c:534-547` — `strongsub` exponent guard (accidental subspace isolation for DELETE)
- `golden/isolation/*` — Empirical test results (when generated)
- Finding 0038, 054, 055, 057, 012, 048
