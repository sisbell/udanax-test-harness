# Finding 012: Dual Enfilade Architecture (granf + spanf)

**Date:** 2026-01-30
**Category:** Architecture / Data Structures

## Summary

Udanax Green uses **two separate global enfilades** for different purposes:

1. **`granf`** (Gran Enfilade) - Content storage and document structure
2. **`spanf`** (Span Enfilade) - Link search index

## The Two Enfilades

### granf - The Content Enfilade

**Type:** `typegranf` (defined as `INT *` in xanadu.h:13)

**Purpose:** Stores all content and document structure:
- Permascroll (character identity)
- Document orgls (version history)
- Link orgls (link structures)
- V→I mappings for documents

**Key operations:**
```c
findorgl(taskptr, granf, &isa, &orgl, type)      // Find an orgl by ISA
inserttextingranf(taskptr, granf, hint, text, ispanset)  // Insert text
createorglingranf(taskptr, granf, hint, isa)    // Create new orgl
ispanset2vstuffset(taskptr, granf, ispanset, vstuffset)  // Dereference I-addrs to content
```

**Accessed by:** Most document operations

### spanf - The Link Search Enfilade

**Type:** `typespanf` (defined as `INT *` in xanadu.h:15)

**Purpose:** Index for finding links by content identity:
- Maps I-addresses to links that reference them
- Enables "find all links from/to this content" queries

**Key operations:**
```c
insertspanf(taskptr, spanf, isa, sporglset, spantype)  // Index link endpoint
findlinksfromtothreesp(taskptr, spanf, from, to, three, range, linkset)  // Find links
retrieveendsetsfromspanf(taskptr, specset, from, to, three)  // Get link endpoints
```

**Accessed by:** Link creation and search operations

## Initialization

From entexit.c:44-45:
```c
granf = (typegranf) createenf (GRAN);
spanf = (typespanf) createenf (SPAN);
```

Both are created with `createenf()` but with different type flags (GRAN vs SPAN), suggesting different internal structure.

## Why Two Enfilades?

### Different Access Patterns

| Operation | granf | spanf |
|-----------|-------|-------|
| Insert text | ✓ | - |
| Create document | ✓ | - |
| Read content | ✓ | - |
| Create link | ✓ (store link orgl) | ✓ (index endpoints) |
| Find links | - | ✓ |
| Follow link | ✓ (read link orgl) | - |

### Different Index Structures

**granf:** Indexed by document ISA and V-position
- Primary key: ISA (document identity)
- Secondary: V-position within document

**spanf:** Indexed by I-address (content identity)
- Primary key: I-address of content
- Returns: Links that reference that content

### Separation of Concerns

1. **Content operations** don't need link index overhead
2. **Link searches** don't need to scan all content
3. **Independent optimization** of each structure

## Link Creation Flow

When a link is created, both enfilades are updated:

```c
// From docreatelink() - do1.c:199-225
bool docreatelink(...) {
    // 1. Create link orgl in granf
    createorglingranf(taskptr, granf, &hint, linkisaptr)

    // 2. Copy link reference into document (granf)
    && docopy(taskptr, docisaptr, &linkvsa, ispanset)

    // 3. Index link endpoints in spanf
    && insertendsetsinspanf(taskptr, spanf, linkisaptr,
                            fromsporglset, tosporglset, threesporglset)
}
```

## Link Search Flow

Finding links uses spanf exclusively:

```c
// From dofindlinksfromtothree() - do1.c:386-391
bool dofindlinksfromtothree(...) {
    return findlinksfromtothreesp(taskptr, spanf,
                                  fromvspecset, tovspecset, threevspecset,
                                  orglrangeptr, linksetptr);
}
```

But following a link uses granf (to read the link orgl and its endpoints).

## Implications

### For Understanding

1. **Link creation is O(n)** where n = endpoints indexed
2. **Link search is efficient** via spanf index
3. **Content retrieval doesn't touch spanf**
4. **Consistency requires updating both** on link creation

### For Formal Specification

The spec needs to model:
1. Document state (granf structure)
2. Link index state (spanf structure)
3. Invariant: spanf is consistent with link orgls in granf

### Potential Bugs

If spanf and granf get out of sync:
- Links exist but aren't findable
- Links are findable but don't exist
- Would require transactional updates to prevent

## Related

- **Finding 009:** Document address space (how content is stored in granf)
- **Finding 004:** Link endpoint semantics (how links are indexed in spanf)
- **Finding 011:** Convention over enforcement (no transactional guarantees documented)

## Files

| File | Role |
|------|------|
| `xanadu.h:13-16` | Type definitions |
| `entexit.c:44-45` | Initialization |
| `granf1.c` | granf operations |
| `granf2.c` | granf operations (continued) |
| `spanf1.c` | spanf operations |
| `spanf2.c` | spanf operations (continued) |
| `corediskout.c:21-22` | Global variable definitions |
