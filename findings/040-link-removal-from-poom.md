# Finding 040: Link Removal from POOM via DELETEVSPAN

**Date discovered:** 2026-02-07
**Category:** Link semantics / POOM architecture / Permanence
**Test scenario:** `links/delete_link_subspace.json`

## Summary

A front end CAN remove a link from a document's POOM by calling DELETEVSPAN on the link subspace (V-position 2.x). This removes the link's entry from the document's V-stream view while the link orgl itself persists permanently in I-space. The link remains discoverable via `find_links` and followable via `follow_link`.

---

## Test Results

### Initial State
Document contains text at V-position 1.x and a link at V-position 2.1:
```json
{
  "vspanset": {
    "spans": [
      {"start": "0", "width": "0.1"},   // Link subspace (normalized to 0)
      {"start": "1", "width": "1"}      // Text subspace
    ]
  }
}
```

### DELETE Operation
```
session.delete(doc, Address(2, 1), Offset(0, 1))
Result: SUCCESS
```

The DELETE targeting V-position 2.1 (link subspace) **succeeds**.

### After Deletion
```json
{
  "vspanset": {
    "spans": [
      {"start": "1.1", "width": "0.11"}  // Only text remains
    ]
  }
}
```

The link subspace (0.x/2.x) is **gone** from the vspanset. The document no longer "contains" the link in its V-stream view.

### Link Persistence

Despite removal from POOM:

1. **Link orgl persists in I-space**:
   - Link ID `1.1.0.1.0.1.0.2.1` remains valid
   - Link is stored at I-address, independent of any document's POOM

2. **Link remains discoverable**:
   - `find_links()` searching the source text **still finds the link**
   - Endsets in spanfilade (type 4 entries) persist independently

3. **Link remains followable**:
   - `follow_link(link_id, LINK_SOURCE)` **works**
   - Returns correct source endpoint specification
   - Direct access via link ID bypasses POOM

---

## Semantic Model

### Three Storage Layers

Links exist in three independent storage layers:

1. **I-space (link orgl)**:
   - Permanent storage of link object at I-address like `1.1.0.1.0.1.0.2.1`
   - Contains link's endset references (FROM, TO, TYPE)
   - **Cannot be deleted** (P0: permanence axiom)

2. **Spanfilade (DOCISPAN entries)**:
   - Type 4 enfilade entries mapping I-addresses to documents
   - Enables `find_links()` and `finddocscontaining()` queries
   - **Append-only** (P0': spanfilade monotonicity)
   - Historical record persists even when link removed from POOM

3. **POOM (document V-stream)**:
   - V-position 2.x entries in document's orgl enfilade
   - Determines whether link "appears" in document's visible structure
   - **Mutable via DELETEVSPAN** (this finding)

### Removal Semantics

DELETEVSPAN on link subspace (2.x) operates **only** on layer 3 (POOM):
- Removes V→I mapping for the link from document's orgl
- Does NOT affect I-space (link orgl persists)
- Does NOT affect spanfilade (DOCISPAN entries persist)

This creates an **orphaned link in reverse**: the link orgl exists and references the document, but the document no longer references the link in its V-stream.

---

## Architectural Implications

### 1. Links are Semi-Permanent

Links have a **dual nature**:
- **Permanent** at I-space level (link orgl cannot be deleted)
- **Removable** from POOM level (V-stream association is mutable)

This differs from text content:
- Text: V→I mapping in POOM + content bytes in I-space
- Links: V→I mapping in POOM + link orgl in I-space + endsets in spanfilade

Removing link from POOM leaves two layers intact.

### 2. POOM is the "Presentation Layer"

The POOM determines what a document "shows" to viewers:
- Text at 1.x positions
- Links at 2.x positions
- Types at 3.x positions (likely)

DELETEVSPAN on any subspace removes that content from the document's visible structure without affecting underlying I-space permanence.

### 3. Discovery vs Direct Access Asymmetry

After link removal from POOM:
- Discovery: `find_links()` still works because spanfilade persists
- Direct access: `follow_link(link_id)` still works because link orgl persists
- But: `retrieve_vspanset()` no longer shows the link in document structure

This mirrors the orphaned link behavior (Finding 024) but in reverse:
- **Orphaned link**: Link exists in POOM but endpoints resolve to empty
- **Removed link**: Link doesn't exist in POOM but link orgl fully intact

---

## Code Evidence

From `orglinks.c:145-152`, `deletevspanpm()`:
```c
bool deletevspanpm(typetask *taskptr, tumbler *docisaptr,
                   typeorgl docorgl, typevspan *vspanptr)
{
    if (iszerotumbler(&vspanptr->width))
        return (FALSE);
    deletend((typecuc*)docorgl, &vspanptr->stream, &vspanptr->width, V);
    logbertmodified(docisaptr, user);
    return (TRUE);
}
```

The `deletend()` function (edit.c:31-76) operates on the document's orgl enfilade in the V-dimension, removing crums that cover the specified V-range. When targeting V-position 2.x, it removes link crums from the POOM without touching:
- The link orgl in I-space
- The DOCISPAN entries in spanfilade

---

## Comparison with Text Deletion

| Operation | POOM Effect | I-space Effect | Spanfilade Effect |
|-----------|-------------|----------------|-------------------|
| DELETE text (1.x) | Removes V→I mapping | Content bytes persist | DOCISPAN persists |
| DELETE link (2.x) | Removes V→I mapping | Link orgl persists | DOCISPAN persists |

Both operations have the same POOM-level semantics: remove V-stream presence while leaving I-space intact.

The difference:
- **Text**: After deletion, `retrieve_contents()` returns empty, `finddocscontaining()` returns historical superset
- **Links**: After deletion, `find_links()` still works (endsets in spanfilade), `follow_link()` still works (link orgl accessible)

---

## Implications for EWD Specifications

### Link Endset Permanence is Convention, Not Enforcement

[EWD-004] L4 states link endsets should not be modified after creation. This finding reveals that's a **convention**, not architectural enforcement:
- Front end CAN call `session.delete(doc, Address(2, 1), Offset(0, 1))`
- Backend WILL execute the delete successfully
- Link removed from POOM (violates conventional permanence)
- But link orgl and spanfilade entries persist (maintains storage-level permanence)

### I₂ (Link Referential Integrity) Qualified

[EWD-005] I₂ states: "Every link in `links` has valid, resolvable endpoint references"

This finding shows links can exist in `links` (spanfilade) but NOT in the home document's POOM. The invariant should be qualified:

**I₂ (revised)**: Every link in `links` has valid I-addresses for endpoints. If a link has home document D, then D's POOM **may or may not** contain a V-position for that link. The link is accessible via `follow_link(link_id)` regardless.

### Three-Layer Model for State

State Σ = (ispace, pooms, spanf) with links existing across all three:
- **ispace**: Link orgl at I-address (permanent)
- **pooms**: V-position entry at 2.x (mutable, removable via DELETEVSPAN)
- **spanf**: DOCISPAN entries for discovery (append-only)

Operations:
- `CREATELINK`: Adds to all three layers
- `DELETEVSPAN(2.x)`: Removes only from `pooms`
- No operation removes from `ispace` or `spanf` (P0 and P0')

---

## Related Findings

- **Finding 024**: Link permanence and orphaned links (links survive endpoint deletion)
- **Finding 029**: Link search endpoint removal (links undiscoverable when endpoints deleted)
- **Finding 038**: POOM subspace independence (2.x link subspace separate from 1.x text)

This finding completes the picture: links can be removed from POOM layer while persisting in I-space and spanfilade layers.

---

## Open Questions

1. **Can link be re-added to POOM?**
   - If we call `VCOPY` of the link's I-address back to the document at a new V-position 2.2, does it reappear?
   - Would this create a "duplicate" link entry, or is link-in-POOM identity based on I-address?

2. **What about deleting type subspace (3.x)?**
   - Can we remove link type references from POOM similarly?
   - Would link still have type accessible via `follow_link(link_id, LINK_TYPE)`?

3. **Historical queries after link removal**
   - Does `finddocscontaining(link_id)` still return the home document?
   - Yes, because DOCISPAN in spanfilade persists (verified in this test: `find_links` still works)

4. **Implications for front end UI**
   - Should front ends expose "remove link from document" as a feature?
   - Or should link removal be prevented by front end policy?
   - Current design allows it at backend level

5. **Re-insertion semantics**
   - If link removed from POOM then re-added via VCOPY, does it get same V-position or new one?
   - Test needed: `delete_and_reinsert_link_to_poom`

---

## Test Coverage

| Scenario | Status | Key Finding |
|----------|--------|-------------|
| `delete_link_subspace` | PASS | DELETEVSPAN(2.1) succeeds, removes link from POOM |
| `vspanset_before` | PASS | Link at 0.x (normalized), text at 1.x |
| `vspanset_after` | PASS | Only text remains (1.1 width 0.11) |
| `find_links_after` | PASS | Link still discoverable via content search |
| `follow_link_after` | PASS | Link still accessible via direct ID lookup |

---

## Conclusion

**Answer to original question:** YES, a front end can remove a link from a document's POOM by calling DELETEVSPAN on the link subspace (2.x positions). The link orgl itself persists permanently in I-space, and the link remains discoverable via `find_links` and followable via `follow_link`, but the document no longer "contains" the link in its V-stream view.

This reveals that link "containment" in a document is a **POOM-level association** (mutable) distinct from link **existence** in I-space (permanent). The three-layer architecture (I-space, POOM, spanfilade) provides different levels of persistence and mutability for links.
