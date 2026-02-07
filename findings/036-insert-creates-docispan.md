# Finding 036: INSERT Creates DOCISPAN Entries

**Date discovered:** 2026-02-06
**Category:** Content model / Spanfilade indexing

## Summary

The INSERT operation creates DOCISPAN entries (spanfilade type 4) for newly inserted content, making it discoverable via `find_documents`. This is accomplished through INSERT's call chain: `doinsert` → `inserttextingranf` → `docopy` → `insertspanf(..., DOCISPAN)`.

## Code Evidence

### INSERT Call Chain

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/do1.c`:

```c
// Line 91-127: INSERT implementation
bool doinsert(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typetextset textset)
{
  typehint hint;
  typespanset ispanset;
  ...

  makehint(DOCUMENT, ATOM, TEXTATOM, docisaptr, &hint);
  ret = (inserttextingranf(taskptr, granf, &hint, textset, &ispanset)
      && docopy (taskptr, docisaptr, vsaptr, ispanset)
  );
  return(ret);
}

// Line 45-65: COPY implementation (called by INSERT)
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
  typeispanset ispanset;
  typeorgl docorgl;
  ...

  return (
     specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)
  && findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
  && acceptablevsa (vsaptr, docorgl)
  && asserttreeisok(docorgl)

  /* the meat of docopy: */
  && insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)

  &&  insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)  // ← DOCISPAN creation
  && asserttreeisok(docorgl)
  );
}
```

The key insight: INSERT creates new content via `inserttextingranf`, which returns an `ispanset` (I-address spans). It then calls `docopy` with this ispanset, which calls `insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)` at line 62.

### Contrast with APPEND

From `/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/backend/do1.c` line 25-31:

```c
bool doappend(typetask *taskptr, typeisa *docptr, typetextset textset)
{
  bool appendpm(),insertspanf(); /*zzz dies this put in granf?*/

  return (appendpm (taskptr, docptr, textset)/*&&
       appendpm includes insertspanf!	 insertspanf(taskptr,spanf,docptr,textset,DOCISPAN)*/
  );
}
```

The comment indicates that the `insertspanf(taskptr,spanf,docptr,textset,DOCISPAN)` call is commented out for APPEND. This means **APPEND does NOT create DOCISPAN entries**.

## Behavioral Evidence

### Test 1: INSERT Creates DOCISPAN

From `golden/discovery/insert_creates_docispan.json`:

```
1. Create document 1.1.0.1.0.1
2. INSERT "Inserted text" at 1.1
3. find_documents(search for "Inserted") → [1.1.0.1.0.1]
```

Result: Document is discoverable via its own inserted content.

### Test 2: INSERT Content Discoverable via Transclusion

From `golden/discovery/insert_content_discoverable_elsewhere.json`:

```
1. Create source document 1.1.0.1.0.1
2. INSERT "Discover this" into source
3. Create dest document 1.1.0.1.0.2
4. VCOPY "Discover" from source to dest
5. find_documents(search for "Discover") → [1.1.0.1.0.1, 1.1.0.1.0.2]
```

Result: Both source (with INSERT) and dest (with VCOPY) are found, confirming that:
- INSERT creates DOCISPAN entries for the source
- VCOPY creates DOCISPAN entries for the dest

### Test 3: Multiple INSERTs Accumulate DOCISPAN

From `golden/discovery/insert_multiple_times_accumulates_docispan.json`:

```
1. Create document 1.1.0.1.0.1
2. INSERT "First " at 1.1
3. INSERT "Second " after First
4. INSERT "Third" after Second
5. find_documents(search for "First") → [1.1.0.1.0.1]
6. find_documents(search for "Second") → [1.1.0.1.0.1]
7. find_documents(search for "Third") → [1.1.0.1.0.1]
```

Result: All three insertions create discoverable DOCISPAN entries.

## Implications

### 1. INSERT vs APPEND Semantics

- **INSERT**: Creates DOCISPAN entries → content is discoverable
- **APPEND**: Does NOT create DOCISPAN entries (commented out in code)
- **COPY**: Creates DOCISPAN entries (both source and dest)

This suggests APPEND is intended for "private" content accumulation, while INSERT and COPY create "public" discoverable content.

### 2. Content Discovery Architecture

The dual enfilade architecture uses spanfilade type 4 (DOCISPAN) to maintain a reverse index:
- **Granfilade**: Maps documents → content (forward index)
- **Spanfilade type 4 (DOCISPAN)**: Maps I-addresses → documents (reverse index)

Operations that create DOCISPAN entries:
- INSERT (via `docopy`)
- COPY (via `insertspanf`)
- Not APPEND (commented out)

### 3. EWD-012 Confirmation

This finding confirms the operational semantics in EWD-012: The Operation Set:

> **INSERT**: Creates new content and places it in the document's POOM. The new content receives fresh I-addresses and is added to both the document's granf entry and the DOCISPAN index.

### 4. Design Question

Why is DOCISPAN insertion commented out for APPEND but active for INSERT? Possible reasons:
- Performance: APPEND is bulk operation, avoid index overhead
- Semantics: APPEND is "private accumulation", INSERT is "visible content"
- Historical: APPEND predates the DOCISPAN index

## Related Findings

- **Finding 018**: Content Identity Tracking (FINDDOCSCONTAINING and Sporgl)
- **Finding 023**: find_documents Returns Deleted Content (DOCISPAN persistence)
- **Finding 012**: Dual Enfilade Architecture (granf + spanf)

## Related EWDs

- **EWD-011**: The Dual Index (DOCISPAN as type 4 spanfilade)
- **EWD-012**: The Operation Set (INSERT semantics)

## Test Files

- `febe/scenarios/insert_docispan.py`
- `golden/discovery/insert_creates_docispan.json`
- `golden/discovery/insert_content_discoverable_elsewhere.json`
- `golden/discovery/insert_multiple_times_accumulates_docispan.json`
