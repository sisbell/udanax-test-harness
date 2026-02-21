# Finding 0010: Unified Storage Abstraction Leaks

**Date:** 2026-01-30
**Related:** Finding 0009 (Document Address Space Structure), Bug 0009

## Summary

The Udanax Green backend uses a unified enfilade model where all document content (text, link references) is stored as V→I mappings. This elegant abstraction leaks in multiple places where **semantic differences between V-subspaces matter**.

## The Unified Model

```
Document Enfilade: V-position → I-address
                   (uniform storage, no type distinctions)
```

All content uses the same storage operations (`insertpm`, `docopy`) and retrieval operations (`retrieverestricted`, `permute`). The enfilade doesn't distinguish content types.

## Identified Abstraction Leaks

### 1. Version Comparison (`compare_versions` / Bug 0009)

**Operation:** Find shared content between two document versions

**Assumption:** All I-addresses represent comparable content

**Reality:** Link ISAs (document addresses) ≠ text I-addresses (permascroll)

**Consequence:** Crash when comparing documents with links

**Evidence:** Bug 0009 - SIGABRT when link subspace spans are processed

---

### 2. Content Retrieval (`retrieve_contents` / `doretrievev`)

**Code:** do1.c:376-384
```c
bool doretrievev(typetask *taskptr, typespecset specset, typevstuffset *vstuffsetptr)
{
    return
       specset2ispanset (taskptr, specset, &ispanset, READBERT)
    && ispanset2vstuffset (taskptr, granf, ispanset, vstuffsetptr);
}
```

**Assumption:** All I-addresses can be dereferenced in the permascroll (`granf`)

**Reality:** Link ISAs point to link orgls, not permascroll entries

**Consequence:** If specset includes V-position 0.x (link subspace):
- `ispanset2vstuffset` searches permascroll for link ISA
- Returns NULL/garbage (ISA not in permascroll)
- Client receives empty or corrupt content

**Likely behavior:** Silent failure or gibberish bytes for link subspace

---

### 3. No V-Position Validation (`acceptablevsa`)

**Code:** do2.c:110-113
```c
bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr)
{
    return (TRUE);  // ALWAYS accepts!
}
```

**Assumption:** Callers know the correct V-position conventions

**Reality:** No enforcement of 0.x for links, 1.x for text

**Consequence:** Possible to:
- Insert text at position 0.x (corrupting link subspace)
- Insert link references at position 1.x (corrupting text subspace)
- Create semantically invalid documents

**Status:** Convention-only enforcement - works if all code follows rules

---

### 4. Delete Operations (`dodeletevspan`)

**Code:** do1.c:162-171
```c
bool dodeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
    return (
       findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
    && deletevspanpm (taskptr, docisaptr, docorgl, vspanptr)
    );
}
```

**Assumption:** Callers know what they're deleting

**Reality:** No check for whether vspan is in link or text subspace

**Consequence:** Deleting V-range 0.x:
- Removes link references from document
- Links still exist but document loses its references
- Orphaned links (document can no longer find them)

**Status:** Valid operation but potentially dangerous without understanding

---

### 5. Copy/Transclusion (`docopy`)

**Code:** do1.c:45-65
```c
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
    return (
       specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)
    && findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
    && acceptablevsa (vsaptr, docorgl)  // Always TRUE!
    && insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)
    // ...
    );
}
```

**Assumption:** Source specset contains appropriate I-addresses for destination

**Reality:** No validation that:
- Text is being copied to text subspace (1.x)
- Link refs are being copied to link subspace (0.x)

**Consequence:** Can copy:
- Link ISAs into text subspace → appears as "content" but isn't text
- Text I-addresses into link subspace → broken link references

**Status:** Caller must ensure correct subspace matching

---

### 6. Transclusion From Documents With Links

**Scenario:** Document A has links. User vcopies from A to B.

**What happens:**
1. `retrieve_vspanset(A)` returns spans for BOTH 0.x and 1.x
2. User creates specset from full vspanset
3. `vcopy` to B copies ALL content including link references

**Reality:** Link references at 0.x in A become content at 1.x in B (or wherever copied)

**Consequence:**
- B now contains link ISA bytes as "text"
- Semantically meaningless
- No error raised

**Proper behavior:** Filter to text subspace before transclusion

---

### 7. `retrieve_vspanset` Returns Both Subspaces

**Operation:** Get the V-span extent of a document

**Assumption:** Callers understand the subspace structure

**Reality:** Returns unified view including link subspace

**Evidence:** Debug output shows:
```
Before link: <VSpec in 1.1.0.1.0.1, at 1.1 for 0.16>
After link:  <VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>
```

**Consequence:** Any operation using "full document extent" includes links

---

### 8. Link Search Must Know Subspace

**Operation:** `find_links` searches for links in content

**Implementation:** Searches the span-f (link enfilade) by I-address

**Reality:** Must search using I-addresses from text subspace (1.x) to find links attached to that content. Searching with link ISAs (from 0.x) is meaningless.

**Status:** Works correctly but requires caller understanding

---

## Pattern of Failures

All leaks share a common pattern:

| Layer | Assumes | Reality |
|-------|---------|---------|
| Storage | All V→I mappings are equivalent | Different subspaces have different semantics |
| Operations | I-addresses are interchangeable | Permascroll ≠ document ISAs |
| Callers | Functions handle type differences | Functions are type-agnostic |

## Mitigation Strategies

### At the Frontend/Client Level

```python
def filter_to_text_subspace(vspanset):
    """Filter vspanset to text content only (V >= 1)."""
    return [s for s in vspanset.spans if s.start.digits[0] >= 1]

# Before compare_versions:
o_text = filter_to_text_subspace(orig_vspanset)
v_text = filter_to_text_subspace(ver_vspanset)

# Before vcopy:
source_text = filter_to_text_subspace(source_vspanset)

# Before retrieve_contents:
content_spans = filter_to_text_subspace(doc_vspanset)
```

### At the Backend Level (Potential Fixes)

1. **Add type field to spans:**
   ```c
   typespan {
       tumbler stream;
       tumbler width;
       INT subspace_type;  // TEXT=1, LINK=0
   }
   ```

2. **Validate V-positions:**
   ```c
   bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr, INT expected_subspace)
   {
       INT actual = vsaptr->digits[0];
       return (actual >= expected_subspace);  // 1 for text, 0 for links
   }
   ```

3. **Type-aware retrieval:**
   ```c
   bool doretrievev_text(taskptr, specset, vstuffsetptr)
   {
       // Filter specset to text subspace before processing
   }
   ```

## Architectural Insight

The Xanadu designers chose **convention over enforcement**:

| Aspect | Chosen Approach | Alternative |
|--------|-----------------|-------------|
| Type safety | Trust callers | Enforce in storage |
| Subspace semantics | V-position encodes type | Explicit type field |
| Validation | None | Position range checks |

This was likely intentional - 1970s-80s systems favored minimal overhead and trusted code. But it creates a maintenance burden where every caller must understand the implicit contract.

## Related

- **Finding 0009:** Document address space structure (defines the subspaces)
- **Finding 0011:** Convention over enforcement design philosophy (why validation is missing)
- **Bug 0009:** Crash demonstrating compare_versions leak
- **Bug 0010:** acceptablevsa always returns TRUE (no V-position validation)
- **Finding 0004:** Link endpoint semantics (links attach to content identity)
