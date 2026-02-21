# Finding 0072: No Automatic Edit History or Backtrack Capability

**Date:** 2026-02-14
**Status:** Confirmed by code analysis + test
**Category:** Architecture, Data Model
**Sources:** `backend/edit.c:31-76`, `backend/orglinks.c:145-152`, `backend/credel.c:413-436`
**Test:** `febe/tests/debug/test_edit_history.py`
**Related:** Finding 0064 (DELETE irreversible in I-space), Finding 0043 (CREATENEWVERSION semantics)

## Summary

Udanax-green does **not** store automatic edit history. There is no mechanism to reconstruct prior document states without explicit CREATENEWVERSION calls. Edits are destructive mutations of the POOM enfilade tree structure. While Nelson's writings describe "historical backtrack" as a theoretical capability, the implemented system achieves this **only through explicit versioning**, not through implicit edit logs or undo history.

## The Question

> Does udanax-green actually store the history of edits to a document, so that prior states can be reconstructed? Or is the only mechanism for preserving a prior state to explicitly call CREATENEWVERSION before editing?

**Answer:** The ONLY mechanism is explicit CREATENEWVERSION. There is no automatic history.

## Evidence from Code

### 1. DELETE Is Destructive Tree Surgery

From `edit.c:31-76` (`deletend`):

```c
int deletend(typecuc *fullcrumptr, tumbler *origin, tumbler *width, INT index)
{
  // ... cut the tree at deletion boundaries ...
  for (ptr = (typecuc *) findleftson (father); ptr; ptr = next) {
    next = (typecuc *) findrightbro((typecorecrum*)ptr);
    switch (deletecutsectionnd ((typecorecrum*)ptr, &fgrasp, &knives)) {
      case 1:
        disown ((typecorecrum*)ptr);      // Remove from tree
        subtreefree ((typecorecrum*)ptr); // Free the memory
        break;
      case 2:
        tumblersub (&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);
        // Shift displacement backward
        break;
    }
  }
  setwispupwards (father,1);  // Recalculate widths upward
  recombine (father);         // Rebalance tree
}
```

**Key operations:**
- `disown()` - Remove crum from parent/sibling pointers (genf.c:349)
- `subtreefree()` - Recursively free entire subtree (credel.c:413)

These are **permanent structural mutations**. Nodes are freed, memory is reclaimed. There is no "deleted but recoverable" state.

### 2. No History Log or Undo Stack

Searching the entire codebase for undo/history/backtrack mechanisms:
- No undo log structure
- No edit history enfilade
- No transaction journal
- No shadow copies maintained

The only data structures are:
- `granf` - Content storage (INSERT allocates, DELETE frees leaves)
- `spanf` - Link search index (updated on link creation)
- POOMs - Per-document V→I mappings (edited in place)

### 3. INSERT Always Allocates Fresh I-Addresses

From Finding 0064, `do1.c:27-43` (`doinsert`):

```c
bool doinsert(taskptr, docisaptr, vsaptr, textptr, nchars)
{
    return (
       inserttextingranf(...)  // Allocate NEW I-addresses
    && docopy(...)             // Map them into POOM
    );
}
```

`inserttextingranf` **always creates new granfilade entries**. There is no mechanism to "restore" previously deleted I-addresses. Once DELETE frees a POOM leaf, the I-addresses become unreferenced. Re-inserting the same text creates entirely new I-addresses.

### 4. The POOM Enfilade Is Mutated In-Place

From `orglinks.c:145-152` (`deletevspanpm`):

```c
bool deletevspanpm(typetask *taskptr, tumbler *docisaptr,
                   typeorgl docorgl, typevspan *vspanptr)
{
    if (iszerotumbler(&vspanptr->width))
        return (FALSE);
    deletend((typecuc*)docorgl, &vspanptr->stream, &vspanptr->width, V);
    logbertmodified(docisaptr, user);  // Log modification (access control)
    return (TRUE);
}
```

The document's POOM orgl (obtained via `findorgl(granf, docisa)`) is the **same tree structure** throughout the document's lifetime. Edits modify this tree directly. There are no shadow copies, no copy-on-write at the POOM level.

## Evidence from Test

From `febe/tests/debug/test_edit_history.py`:

```
State 1: Insert 'First'
  Content: ['First']
  V-spans: (Span(Address(1, 1), Offset(0, 5)),)

State 2: Insert ' Second'
  Content: ['First Second']
  V-spans: (Span(Address(1, 1), Offset(0, 12)),)

State 3: Insert ' Third'
  Content: ['First Second Third']
  V-spans: (Span(Address(1, 1), Offset(0, 18)),)

After DELETE ' Third' and ' Second':
  Content: ['First']
  V-spans: (Span(Address(1, 1), Offset(0, 5)),)
  → V-space looks identical to State 1
  → But I-addresses are DIFFERENT (new allocations)
```

**Key finding:** We can get back to the same V-space content, but the **I-space identity is lost**. All transclusion links, version comparisons, and provenance chains that referenced the original "First" are permanently broken.

## What About "Historical Backtrack"?

Nelson's writings describe the ability to view any prior state of a document. In udanax-green, this is achieved through:

1. **Explicit CREATENEWVERSION** - Captures a snapshot
2. **Content identity preservation** - Versions share I-addresses with the original
3. **compare_versions** - Finds shared content across time

But there is **no automatic state capture**. If you don't call CREATENEWVERSION before editing, the prior state is **lost forever**.

### Version Mechanism

From Finding 0043, `do1.c:264-303`:

```c
bool docreatenewversion(typetask *taskptr, typeisa *isaptr,
                        typeisa *wheretoputit, typeisa *newisaptr)
{
  typevspan vspan;

  // Retrieve source document's text content
  doretrievedocvspanfoo(taskptr, isaptr, &vspan);

  // Create new document
  createorglingranf(taskptr, granf, &hint, newisaptr);

  // Copy text content (shares I-addresses)
  docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);
}
```

CREATENEWVERSION creates a **new POOM** that shares I-addresses with the original for the text content. The original and version are separate tree structures. Editing one does not affect the other.

## Implications

### 1. Historical State Requires Explicit Discipline

To maintain document history, you must:
- Call CREATENEWVERSION before any edit you might want to undo
- Manage version proliferation (every edit = new version?)
- No automatic checkpoint/snapshot mechanism

### 2. DELETE + INSERT ≠ Identity

```
State A: "Original text" at I-addresses 5.1-5.13
DELETE "Original text"
INSERT "Original text"
State B: "Original text" at I-addresses 5.14-5.26
```

V-space is identical, but I-space is completely different. All relationships indexed by I-address are severed:
- Transclusion (other docs referencing original I-addresses)
- Links (endpoints at original I-addresses)
- Version comparison (compare_versions won't find shared content)
- Provenance (find_documents won't trace to new I-addresses)

### 3. "Undo" Requires VCOPY from a Version

The only way to restore deleted content **with its original I-addresses**:

```python
# Create version before editing
version = session.create_version(doc)

# Edit document
session.delete(doc_opened, span)

# "Undo" by copying from version
ver_opened = session.open_document(version, READ_ONLY, CONFLICT_COPY)
ver_spans = session.retrieve_vspanset(ver_opened)
ver_specs = SpecSet(VSpec(ver_opened, list(ver_spans.spans)))
session.vcopy(doc_opened, Address(1, 1), ver_specs)
```

VCOPY preserves I-addresses. Re-INSERT does not.

### 4. Granfilade Is Permanent, POOMs Are Mutable

- **Granfilade:** Append-only permascroll. I-addresses are never reused or deleted.
- **POOMs:** Mutable tree structure. DELETE frees leaves, INSERT adds new ones.
- **No history log:** The only record of "what I-addresses existed at V-positions" is the current POOM state.

## Comparison to Other Systems

| System | History Mechanism | Granularity |
|--------|------------------|-------------|
| **udanax-green** | Explicit CREATENEWVERSION | Document-level snapshot |
| **Git** | Automatic commit-on-save | Repository-level commit |
| **Emacs** | Automatic undo ring | Character-level edit log |
| **Google Docs** | Automatic revision history | Per-edit snapshot |
| **Dropbox** | Automatic file versioning | File-level snapshot |

Udanax-green is **most restrictive** - you must explicitly version, and versioning is expensive (creates new POOM tree structure, allocates new document address).

## Theoretical vs. Implemented

### Nelson's Vision
"Every edit creates a version. Historical backtrack is always available. The entire edit history is preserved in the permascroll."

### Udanax-Green Reality
- Permascroll preserves **content** (I-addresses in granfilade)
- But not **mappings** (V→I in POOMs are mutable)
- Historical backtrack requires **explicit CREATENEWVERSION**
- No automatic versioning on every edit

The permascroll principle applies to **content identity**, not **document state**. Content is permanent (I-addresses never deleted), but which content appears at which V-position in which document is mutable.

## Formal Statement

Let `doc` be a document with POOM tree `T`.

**Edit operations mutate T destructively:**
```
INSERT(doc, vaddr, text):
  T' = T with new leaf at vaddr mapping to fresh I-addresses

DELETE(doc, vspan):
  T' = T with leaves in vspan disowned and freed

After DELETE, previous T is not recoverable from T'
```

**Version creation creates a snapshot:**
```
CREATENEWVERSION(doc) → version:
  version.POOM = copy of doc.POOM (shares I-addresses)

Subsequent edits to doc modify doc.POOM
Subsequent edits to version modify version.POOM
Neither affects the other
```

**Historical recovery:**
```
To recover doc's state from time t:
  REQUIRED: version created at time t via CREATENEWVERSION

If no version exists from time t:
  State is UNRECOVERABLE
```

## Conclusion

**Udanax-green does NOT provide automatic edit history or backtrack capability.**

The system achieves historical preservation through:
1. Explicit CREATENEWVERSION before editing
2. Content identity preservation (I-addresses shared across versions)
3. Separation of content storage (granf) from document structure (POOMs)

Edits are destructive mutations of the POOM tree. DELETE frees nodes. INSERT creates new nodes. There is no undo log, no edit history, no shadow copies. The ONLY way to preserve a prior state is to call CREATENEWVERSION before editing.

This is fundamentally different from the theoretical vision of "automatic versioning on every edit" described in Xanadu literature. The implemented system requires explicit discipline from users or higher-level software to maintain version history.

## Related Findings

- **Finding 0064:** DELETE Is Irreversible in I-Space - Explains why DELETE + re-INSERT breaks identity
- **Finding 0043:** CREATENEWVERSION Copies Text Only - Details version creation semantics
- **Finding 0007:** Version Semantics - How versions preserve content identity
- **Finding 0030:** INSERT Allocates Fresh I-Addresses - Why re-typing doesn't restore identity
- **Finding 0057:** Spanfilade Write-Only - Even the reverse index isn't cleaned up on DELETE

## Citations

- `edit.c:31-76` - `deletend`: Destructive tree surgery via disown + subtreefree
- `orglinks.c:145-152` - `deletevspanpm`: Calls deletend on POOM
- `credel.c:413-436` - `subtreefree`: Recursive memory deallocation
- `genf.c:349-380` - `disown`: Removes crum from tree structure
- `do1.c:27-43` - `doinsert`: Always allocates fresh I-addresses
- `do1.c:264-303` - `docreatenewversion`: Explicit snapshot mechanism
- `febe/tests/debug/test_edit_history.py` - Test demonstrating lack of automatic history
