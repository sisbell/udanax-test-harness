# Finding 0035: Five Query Operations -- Implementation Details

**Date:** 2026-02-06
**Status:** Traced from source code
**Category:** Query Operations
**Sources:** `backend/orglinks.c`, `backend/spanf1.c`, `backend/spanf2.c`, `backend/do1.c`, `backend/fns.c`, `backend/get1fe.c`, `backend/putfe.c`, `backend/init.c`

## Summary

Five FEBE query operations that were not analyzed in the existing specification are traced through their complete call chains. Three are retrieval operations (RETRIEVEDOCVSPAN, RETRIEVEDOCVSPANSET, RETRIEVEENDSETS) and two are link-counting/pagination operations (FINDNUMOFLINKSFROMTOTHREE, FINDNEXTNLINKSFROMTOTHREE).

---

## 1. RETRIEVEDOCVSPAN (Opcode 14)

### Call Chain

```
fns.c:retrievedocvspan()
  -> get1fe.c:getretrievedocvspan()     -- reads: docid
  -> do1.c:doretrievedocvspan()
       -> granf2.c:findorgl()            -- READBERT access
       -> orglinks.c:retrievevspanpm()   -- extracts V-dimension from orgl root
  -> putfe.c:putretrievedocvspan()       -- writes: span (start + width)
```

### What It Actually Does

`retrievevspanpm()` at `orglinks.c:165-172` copies two raw tumblers from the orgl root node:

```c
bool retrievevspanpm(typetask *taskptr, typeorgl orgl, typevspan *vspanptr)
{
    vspanptr->next = NULL;
    vspanptr->itemid = VSPANID;
    movetumbler (&((typecuc *) orgl)->cdsp.dsas[V], &vspanptr->stream);
    movetumbler (&((typecuc *) orgl)->cwid.dsas[V], &vspanptr->width);
    return (TRUE);
}
```

It reads `cdsp.dsas[V]` (the V-dimension displacement of the root) as the stream start, and `cwid.dsas[V]` (the V-dimension width of the root) as the span width. No processing, no filtering, no subspace awareness.

### Key Behaviors

1. **For text-only documents:** Returns a correct single span. E.g., "Hello World" yields `1.1 for 0.11`.

2. **For documents with links:** Returns a raw bounding-box width that spans both the 0.x (link) and 1.x (text) subspaces. E.g., a document with 10 chars of text and 1 link yields `1.1 for 1.2` -- which is neither the text span nor the link span, but an internal structural value. This is documented as Bug 0011.

3. **For empty documents:** Returns zeros (both cdsp and cwid are zero).

4. **Identical twin:** There is a second function, `retrievedocumentpartofvspanpm()` at `orglinks.c:155-162`, with identical logic but a different name. It is labeled `/* this is a kluge */` and used internally by `docreatenewversion()` (`do1.c:305-313`). The two functions have the same body.

### Verdict

This operation is **broken for documents containing links**. It is a raw dump of the V-dimension root width with no semantic processing. Use RETRIEVEDOCVSPANSET instead.

---

## 2. RETRIEVEDOCVSPANSET (Opcode 1)

### Call Chain

```
fns.c:retrievedocvspanset()
  -> get1fe.c:getretrievedocvspanset()   -- reads: docid
  -> do1.c:doretrievedocvspanset()
       -> granf2.c:findorgl()             -- READBERT access
       -> orglinks.c:isemptyorgl()        -- short-circuit for empty docs
       -> orglinks.c:retrievevspansetpm() -- subspace-aware extraction
  -> putfe.c:putretrievedocvspanset()     -- writes: itemset of spans
```

### What It Actually Does

`retrievevspansetpm()` at `orglinks.c:173-221` handles two cases:

**Case 1 -- Text only** (`is1story()` returns true):

If the root width's V-dimension has only one non-zero mantissa digit (i.e., it is a "1-story" tumbler like `0.11`), there are no links. Returns one span: the root's cdsp and cwid on the V dimension, same as RETRIEVEDOCVSPAN.

**Case 2 -- Has links** (`is1story()` returns false):

The function constructs **two separate spans**:

1. **Link subspace span** (0.x): Extracts from cwid by zeroing mantissa[1] and re-justifying. This gives the link-space extent.

2. **Text subspace span** (1.x): Calls `maxtextwid()` which recursively walks the orgl tree, visiting only non-link crums (`!islinkcrum()`), accumulating the maximum text V-position via `tumblermax()`. Then zeros mantissa[0] to strip the leading digit.

The two spans are added to the vspanset list via `putvspaninlist()`, which maintains a sorted, coalescing list (merges adjacent or overlapping spans).

### The `is1story()` Test

`is1story()` in `tumble.c:237-247` checks whether a tumbler has at most one non-zero mantissa digit (mantissa[1] through mantissa[NPLACES-1] are all zero). A width like `0.11` is 1-story. A width like `1.2` (spanning 0.x and 1.x) is not.

### The `maxtextwid()` Traversal

`maxtextwid()` at `orglinks.c:224-245` recursively walks the orgl tree:

- If a crum is a "text crum" (V-displacement has mantissa[1]==0 AND width is 1-story), it adds the crum's V offset to its displacement and takes the max.
- If a crum is a "link crum" (V-displacement mantissa[0]==1 AND mantissa[1]!=0), it is skipped entirely.
- Otherwise it recurses into children.

### Key Behaviors

1. **Empty document:** Returns NULL (empty set). The `doretrievedocvspanset()` function short-circuits via `isemptyorgl()`.

2. **Text-only document:** Returns one span, same as RETRIEVEDOCVSPAN.

3. **Document with links:** Returns two spans -- e.g., `[{0, 0.1}, {1, 1}]` for a 10-char doc with 1 link. The first covers the link subspace, the second covers the text subspace.

4. **Output format:** Encoded as an itemset via `putitemset()`, which counts items then writes each span.

### Verdict

This is the **correct operation** for determining document extent. It handles the dual subspace structure properly.

---

## 3. RETRIEVEENDSETS (Opcode 28)

### Call Chain

```
fns.c:retrieveendsets()
  -> get1fe.c:getretrieveendsets()           -- reads: specset
  -> do1.c:doretrieveendsets()
       -> spanf1.c:retrieveendsetsfromspanf() -- the real work
  -> putfe.c:putretrieveendsets()             -- writes: fromset, toset, threeset
```

### What It Actually Does

This is NOT "FOLLOWLINK applied three times." It has different semantics -- it works through the spanfilade, not the link orgl.

`retrieveendsetsfromspanf()` at `spanf1.c:190-235`:

1. **Converts the input specset to a sporglset** via `specset2sporglset()`. This translates V-addresses to I-addresses (permascroll coordinates).

2. **Defines three search spaces** using the spanfilade's ORGLRANGE dimension:
   - `fromspace`: ORGLRANGE prefix = LINKFROMSPAN (1), width 1
   - `tospace`: ORGLRANGE prefix = LINKTOSPAN (2), width 1
   - `threespace`: ORGLRANGE prefix = LINKTHREESPAN (3), width 1

3. **For each endset type**, calls `retrievesporglsetinrange()` which:
   - Calls `retrieverestricted()` on the spanfilade using the sporglset as the SPANRANGE restriction and the from/to/three space as the ORGLRANGE restriction
   - Extracts matching sporgls from the context results
   - Then calls `linksporglset2specset()` to convert I-addresses back to V-specs (using the **querying document's** docid, not the link's home document)

4. **Three-endset handling**: The `threeset` is only retrieved if `threesetptr` is non-NULL. The code handles the three-endset fetch conditionally:
   ```c
   if (threesetptr) {
       temp = (retrievesporglsetinrange(...)
           && linksporglset2specset(...));
       return(temp);
   }
   return(TRUE);
   ```

### Key Difference from FOLLOWLINK

| Aspect | FOLLOWLINK | RETRIEVEENDSETS |
|--------|-----------|-----------------|
| Input | link ISA + which-end (1,2,3) | specset (V-spec of content region) |
| Lookup path | link orgl -> V-dimension -> I-spans | spanfilade -> SPANRANGE+ORGLRANGE search |
| Returns | One endset as V-specs | All three endsets simultaneously |
| Resolution | From link's perspective | From querying document's perspective |

FOLLOWLINK takes a specific link ID and asks "what is endset N of this link?" It reads from the link's orgl structure directly.

RETRIEVEENDSETS takes a content region and asks "what link endpoints intersect this content?" It searches the spanfilade, which indexes all link endpoints by their I-addresses. It returns all three endset types in a single call.

### Key Behaviors

1. **Returns three specsets simultaneously:** from-endset, to-endset, three-endset. This is visible in the output function:
   ```c
   putretrieveendsets(taskptr, fromset, toset, threeset)
   ```

2. **V-address resolution uses the querying document's docid:** The `linksporglset2specset()` call uses `&((typevspec *)specset)->docisa` as the home document for I-to-V translation. This means endsets are reported in terms of the querying document's V-space.

3. **Target endsets may be empty:** Finding 0019 notes that target endsets are often empty when querying from the source document. This is because the spanfilade stores endpoints by I-address, and the to-endset I-addresses may not be present in the source document's orgl.

4. **Content-identity based:** Because the search goes through I-addresses, links are discoverable from any document that shares content identity (transclusion, versioning).

### Verdict

RETRIEVEENDSETS is a **spanfilade-based search** that returns all three endsets at once, resolved against the querying document. It is fundamentally different from calling FOLLOWLINK three times.

---

## 4. FINDNUMOFLINKSFROMTOTHREE (Opcode 29)

### Call Chain

```
fns.c:findnumoflinksfromtothree()
  -> get1fe.c:getfindnumoflinksfromtothree()  -- reads: from, to, three, homeset
       -> get1fe.c:getfindlinksfromtothree()   -- SAME parser as full search!
  -> do1.c:dofindnumoflinksfromtothree()
       -> spanf1.c:findnumoflinksfromtothreesp()
            -> spanf1.c:findlinksfromtothreesp()  -- FULL materialization
            -> linked list count loop
  -> putfe.c:putfindnumoflinksfromtothree()    -- writes: count
```

### What It Actually Does

`findnumoflinksfromtothreesp()` at `spanf1.c:105-115`:

```c
bool findnumoflinksfromtothreesp(taskptr, spanfptr, fromvspecset,
    tovspecset, threevspecset, orglrange, numptr)
{
  typelinkset linkset;
  INT n;

    if (!findlinksfromtothreesp(taskptr, spanfptr, fromvspecset,
            tovspecset, threevspecset, orglrange, &linkset))
        return(FALSE);
    for (n = 0; linkset; linkset = linkset->next, ++n);
    *numptr = n;
    return (TRUE);
}
```

It calls `findlinksfromtothreesp()` -- the exact same function used by FINDLINKSFROMTOTHREE -- to materialize the **complete linked list of matching links**, then walks that list counting elements.

### There Is No Optimized Path

This is definitively not a count-only optimization. The full search executes:

1. Convert from/to/three specsets to sporglsets (V-to-I translation)
2. For each non-null endset, call `sporglset2linkset()` which searches the spanfilade
3. If any endset search returns empty, short-circuit with empty result
4. Intersect all non-null linksets via `intersectlinksets()`
5. Then count the resulting linked list by walking it

The intersection itself in `spanf2.c:46-120` is O(n*m) or O(n*m*p) for 2 or 3 endset constraints.

### Key Behaviors

1. **Full materialization:** All matching link ISAs are allocated on the task allocator, assembled into a linked list, then merely counted.

2. **FEBE input reuse:** The `get` function explicitly delegates to `getfindlinksfromtothree()` -- same wire format.

3. **Output is a single integer:** `putfindnumoflinksfromtothree()` writes opcode + count.

4. **Safe mode disables it:** In `init.c:75`, safe mode sets `requestfns[FINDNUMOFLINKSFROMTOTHREE] = nullfun`. This means in safe mode the operation returns a failure rather than executing.

### Verdict

FINDNUMOFLINKSFROMTOTHREE is a **trivial wrapper** around FINDLINKSFROMTOTHREE. There is no count optimization. The full result set is materialized and then its length is measured by walking the linked list.

---

## 5. FINDNEXTNLINKSFROMTOTHREE (Opcode 31)

### Call Chain

```
fns.c:findnextnlinksfromtothree()
  -> get1fe.c:getfindnextnlinksfromtothree()   -- reads: from, to, three, homeset,
                                                --        lastlink (tumbler), n (int)
       -> get1fe.c:getfindlinksfromtothree()    -- SAME parser for search params
       -> gettumbler() for lastlink cursor
       -> getnumber() for page size n
  -> do1.c:dofindnextnlinksfromtothree()
       -> spanf1.c:findnextnlinksfromtothreesp()
  -> putfe.c:putfindnextnlinksfromtothree()     -- writes: itemset of links
```

### What It Actually Does

`findnextnlinksfromtothreesp()` at `spanf1.c:117-149`:

```c
bool findnextnlinksfromtothreesp(taskptr, fromvspecset, tovspecset,
    threevspecset, orglrangeptr, lastlinkisaptr, nextlinksetptr, nptr)
{
  INT n;
  typelinkset linkset;

    n = 0;
    *nextlinksetptr = NULL;
    /* Step 1: Re-execute the FULL search */
    if (!findlinksfromtothreesp(taskptr, spanf, fromvspecset,
            tovspecset, threevspecset, orglrangeptr, &linkset))
        return (FALSE);

    /* Step 2: Find the cursor position */
    if (iszerotumbler(lastlinkisaptr)) {
        /* Zero cursor = start from beginning */
        *nextlinksetptr = linkset;
    } else {
        /* Walk list to find cursor match */
        for (; linkset; linkset = linkset->next) {
            if (tumblereq(&linkset->address, lastlinkisaptr)) {
                *nextlinksetptr = linkset->next;
                break;
            }
        }
    }

    /* Step 3: If cursor not found, return empty */
    if (!linkset) {
        *nextlinksetptr = NULL;
        *nptr = 0;
        return (TRUE);
    }

    /* Step 4: Truncate list to N items */
    for (linkset = *nextlinksetptr; linkset; linkset = linkset->next) {
        if (++n >= *nptr) {
            linkset->next = NULL;  /* Destructively truncate! */
            break;
        }
    }
    *nptr = n;
    return (TRUE);
}
```

### Cursor Format

The cursor is a **link ISA tumbler** -- the address of the last link seen. It is read via `gettumbler()` in the input parser.

- **Zero tumbler** (all mantissa digits zero): Means "start from the beginning." The `iszerotumbler()` check at line 126 detects this.
- **Non-zero tumbler**: The specific link ISA to resume after.

### How It Skips

It does NOT use an index or offset. It walks the full result list looking for an exact tumbler match:

```c
for (; linkset; linkset = linkset->next) {
    if (tumblereq(&linkset->address, lastlinkisaptr)) {
        *nextlinksetptr = linkset->next;
        break;
    }
}
```

This is O(total_results) to find the cursor position on every page request.

### Truncation

The list is **destructively truncated** by setting `linkset->next = NULL` at the N-th item. This is safe because the linked list is on the task allocator and will be freed when the request completes.

### No Caching

There is no caching of previous results between calls. Each pagination request:
1. Re-executes the full spanfilade search
2. Re-materializes the complete linked list
3. Linearly scans to find the cursor
4. Truncates to N items

### Key Behaviors

1. **O(total) per page:** Every page request pays the full cost of the initial search plus a linear scan to the cursor position. Page K costs O(total + K*page_size) for the cursor walk.

2. **Cursor is a link ISA, not a position number:** If the cursor link has been deleted between paginated calls, the cursor will not be found, and the function returns an empty set with `*nptr = 0`.

3. **Page size is an input/output parameter:** `nptr` is passed as a pointer. The input value is the requested page size; the output value is the actual number of results returned (which may be less if the end of the list is reached).

4. **Safe mode disables it:** Like FINDNUMOFLINKSFROMTOTHREE, this is disabled in safe mode via `init.c:76`.

5. **Wire format:** Input is the standard from/to/three/home search params, then lastlink tumbler, then count integer. Output is an itemset of link addresses.

### Verdict

FINDNEXTNLINKSFROMTOTHREE is a **stateless pagination mechanism** with no caching, no indexing, and no incremental execution. It re-runs the full query on every call and linearly scans to the cursor position.

---

## Comparative Summary

| Operation | Opcode | Input | Output | Complexity |
|-----------|--------|-------|--------|------------|
| RETRIEVEDOCVSPAN | 14 | docid | 1 span (raw root) | O(1) |
| RETRIEVEDOCVSPANSET | 1 | docid | N spans (subspace-aware) | O(tree_depth) for maxtextwid |
| RETRIEVEENDSETS | 28 | specset | 3 specsets (from,to,three) | O(spanf_search) |
| FINDNUMOFLINKSFROMTOTHREE | 29 | from,to,three,home | integer count | O(full_search + count) |
| FINDNEXTNLINKSFROMTOTHREE | 31 | from,to,three,home,cursor,n | N links | O(full_search + cursor_walk) |

## Architectural Observations

1. **No query optimization:** Both the count and pagination operations re-execute the full link search. The system was clearly designed for small result sets.

2. **Stateless protocol:** The FEBE protocol has no session state for query cursors. Each pagination call is fully self-contained.

3. **Safe mode concerns:** Both FINDNUMOFLINKSFROMTOTHREE and FINDNEXTNLINKSFROMTOTHREE are disabled in safe mode (`init.c:71-76`), suggesting they were considered potentially expensive or dangerous.

4. **RETRIEVEENDSETS is the powerful query:** It searches by content identity through the spanfilade and returns all three endset types in one call. FOLLOWLINK works from a known link ID; RETRIEVEENDSETS discovers link endpoints from content regions.

## Related

- **Finding 0017**: vspan vs vspanset differences
- **Finding 0019**: Endset operation semantics (behavioral observations)
- **Finding 0009**: Document address space structure (0.x vs 1.x subspaces)
- **Bug 0011**: retrieve_vspan broken with links
