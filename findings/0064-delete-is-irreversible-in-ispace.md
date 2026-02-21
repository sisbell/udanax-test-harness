# Finding 0064: DELETE Is Irreversible in I-Space

**Date:** 2026-02-11
**Status:** Confirmed by code trace + test
**Category:** Specification Semantics, Identity Model
**Sources:** `backend/edit.c:31-76`, `backend/insertnd.c:199-217`, `backend/do1.c:45-65`, Bug 0019
**Related:** Finding 0030 (INSERT allocates fresh I-addresses), Finding 0057 (Spanfilade write-only), Finding 0058 (Tree state after delete-all)

## Summary

DELETE followed by INSERT of identical text does **not** restore the original
document state. The V-space content is the same, but the I-space identity is
entirely different. Every transclusion, link endpoint, version relationship,
and provenance chain that referenced the original content through its
I-addresses is permanently severed.

This is the fundamental asymmetry of DELETE in the Xanadu model: **V-space is
reconstructible; I-space is not.**

---

## The Asymmetry

### What DELETE removes

DELETE (`deletend`) operates on the POOM enfilade only. It removes the V→I
mapping by pruning bottom crums (height-0 nodes) via `disown` + `subtreefree`:

```
Before DELETE "BC" (V-addresses 1.2–1.3):
  POOM: V(1.1)→I(5.1)  V(1.2)→I(5.2)  V(1.3)→I(5.3)  V(1.4)→I(5.4)
        "A"             "B"             "C"             "D"

After DELETE:
  POOM: V(1.1)→I(5.1)  V(1.2)→I(5.4)
        "A"             "D"
```

The bottom crums for I(5.2) and I(5.3) are freed. The mapping is gone.

### What DELETE does NOT remove

1. **Granfilade content**: I-addresses 5.2 and 5.3 still exist in the
   granfilade. The bytes "B" and "C" are permanently stored. The granfilade
   has no delete operation — content is permanent (the permascroll principle).

2. **Spanfilade entries**: The reverse index still records that this document
   once contained I-addresses 5.2–5.3 (Finding 0057). No `deletespanf` exists.

3. **Other documents' references**: If another document transcluded "BC" via
   COPY, it shares I-addresses 5.2–5.3. That transclusion is unaffected —
   the other document's POOM still maps to those I-addresses.

### What re-INSERT creates

INSERT always allocates **fresh** I-addresses from the granfilade (Finding 0030).
Typing "BC" again produces new I-addresses:

```
After INSERT "BC" at V(1.2):
  POOM: V(1.1)→I(5.1)  V(1.2)→I(5.5)  V(1.3)→I(5.6)  V(1.4)→I(5.4)
        "A"             "B"             "C"             "D"
```

I(5.5) and I(5.6) are **new** allocations. They have no relationship to the
original I(5.2) and I(5.3).

---

## What Is Lost

| Relationship | Before DELETE | After DELETE + re-INSERT |
|--------------|-------------|-------------------------|
| **Transclusion** | Other documents sharing I(5.2–5.3) are visibly linked | No connection — I(5.5–5.6) are unrelated identities |
| **Links** | Links with endpoints at I(5.2–5.3) resolve to this document | Links still reference I(5.2–5.3) but this document no longer maps them |
| **Version comparison** | `compare_versions` shows "BC" as shared content | `compare_versions` shows "BC" as different content (different I-addresses) |
| **Provenance** | `find_documents` traces I(5.2–5.3) back to original author | I(5.5–5.6) trace to whoever re-typed it |

The V-space looks identical. The I-space is completely disconnected.

---

## Why This Matters for Specification

### 1. DELETE cannot be modeled as INSERT's inverse

In a simple text editor, undo(delete("BC")) restores the document. In Xanadu,
there is no operation that restores deleted content **with its original
I-addresses**. The closest would be COPY from a version that still contains
the content — but that requires the version to exist and be accessible.

### 2. COPY is the identity-preserving operation, not INSERT

This clarifies the role of each operation:
- **INSERT**: Creates new content identity (fresh I-addresses)
- **COPY**: Preserves existing content identity (shares I-addresses)
- **DELETE**: Destroys the V→I mapping (I-addresses become unreferenced in this document)

To "undelete" while preserving identity, you must COPY from a source that
still references the original I-addresses (another document, or a previous
version). Re-typing the text via INSERT creates an identity-disconnected copy.

### 3. The "withdrawal" problem

Nelson's withdrawal concept (removing content from all documents) becomes
even more significant in this light. If withdrawal could be implemented, it
would sever I-addresses across ALL documents simultaneously — and since
I-space identity can't be reconstructed, withdrawal would be truly permanent.

---

## Code Evidence

### DELETE prunes leaves

From `edit.c:76-84` (inside `deletend`'s loop over sons):

```c
case 1:
    disown ((typecorecrum*)ptr);      // Remove from tree
    subtreefree ((typecorecrum*)ptr); // Free the memory
    break;
```

Bottom crums (height-0) containing V→I mappings are freed. This is
**structural removal**, not value-nulling — the node ceases to exist.

### INSERT always allocates fresh I-addresses

From `do1.c:27-43` (`doinsert`):

```c
bool doinsert(taskptr, docisaptr, vsaptr, textptr, nchars)
{
    return (
       inserttextingranf(...)  // ← Allocate NEW I-addresses in granfilade
    && docopy(...)             // ← Copy those I-addresses into document's POOM
    );
}
```

`inserttextingranf` always creates new granfilade entries. There is no
mechanism to "reuse" freed I-addresses — the granfilade is append-only.

### Empty-after-delete is a distinct state

From Bug 0019: after DELETE removes all content, `findleftson(father)` returns
NULL. The tree has internal structure but no leaves. This state differs from a
never-filled document (which has one zero-width bottom crum from `createenf`).
Both are "empty" to queries, but structurally distinct — evidence that DELETE
is a destructive pruning operation, not a reset.

---

## Test Evidence

From `febe/scenarios/provenance.py::scenario_delete_then_recopy`:

```python
# 1. Source creates "Hello World"
# 2. Target copies "World" from source (shares I-addresses)
# 3. Target deletes "World"
# 4. Target re-copies "World" from source
# Result: I-addresses match source again — identity restored via COPY
```

And the implicit counter-test: if step 4 used INSERT "World" instead of COPY,
the I-addresses would NOT match — identity would be permanently lost despite
identical V-space content.

---

## Formal Statement

Let `doc` be a document, `v` a V-span, `content(v)` the text at that V-span,
and `iaddr(v)` the I-addresses mapped by that V-span.

**DELETE followed by INSERT is not identity:**

```
Let s = content(v) and i = iaddr(v)
After DELETE(doc, v):     iaddr(v) = ∅
After INSERT(doc, v, s):  iaddr(v) = i' where i' ≠ i
```

Even though `content(v) = s` in both the original and restored states,
`iaddr(v)` differs. All relationships indexed by I-address are severed.

**COPY preserves identity:**

```
Let source still map i to some V-span v_s
After DELETE(doc, v):           iaddr(v) = ∅
After COPY(doc, v, source, v_s): iaddr(v) = i
```

COPY from a document that still references the original I-addresses restores
both content AND identity.

---

## Citations

- `edit.c:31-76` — `deletend`: leaf-pruning via disown + subtreefree
- `do1.c:27-43` — `doinsert`: always calls `inserttextingranf` for fresh I-addresses
- `do1.c:45-65` — `docopy`: shares existing I-addresses via `insertpm`
- `insertnd.c:199-217` — `firstinsertionnd`: Bug 0019 fix reveals empty-after-delete state
- Finding 0030 — INSERT allocates fresh I-addresses
- Finding 0057 — Spanfilade is write-only, no cleanup on DELETE
- Finding 0058 — Tree state after delete-all (levelpull disabled)
- Bug 0019 — INSERT/VCOPY crash after delete-all (triggered this investigation)
