# Finding 048: FOLLOWLINK Returns I-Addresses, Filtering Unreferenced Addresses During V-Conversion

**Date:** 2026-02-07
**Status:** Traced from source code
**Category:** Query Operations, Ghost Links
**Sources:** `backend/sporgl.c:67-95`, `backend/orglinks.c:389-449`, `backend/do1.c:227-236`
**Related:** Finding 035 (Query Operations), EWD-030 (Deletion Problem, DEL5), EWD-032 (FEBE Contract, FE5)

## Summary

FOLLOWLINK returns endset I-addresses directly from the link orgl structure **without checking whether those I-addresses are currently in any document's POOM**. The back end always returns whatever endsets the link contains. However, when converting I-addresses to V-addresses for result presentation, **unreferenced I-addresses are silently filtered out** because they have no current POOM mapping. The operation succeeds but returns empty or partial results.

---

## The Question

When FOLLOWLINK returns link endsets, and the I-addresses in those endsets are not currently in any document's POOM (because the content was deleted from all documents), does the back end:
1. Return the endset I-addresses anyway (yes, it does this)
2. Check whether endset I-addresses are "live" before returning them (no, it does not)

The answer is: **The back end returns I-addresses unconditionally, but unreferenced addresses are filtered during I-to-V conversion.**

---

## Call Chain Analysis

### FOLLOWLINK Execution Path

```
fns.c:followlink()
  -> get1fe.c:getfollowlink()                -- reads: linkisa, whichend
  -> do1.c:dofollowlink()
       -> sporgl.c:link2sporglset()          -- extract I-addresses from link orgl
            -> findorgl()                     -- find the link orgl
            -> retrieverestricted()           -- read endset at V-position whichend (1/2/3)
            -> context -> sporglset           -- extract I-addresses
       -> sporgl.c:linksporglset2specset()   -- convert I-addresses to V-specs
            -> sporglset2vspanset()           -- the critical conversion
                 -> findorgl(homedoc)         -- find the HOME document's orgl (POOM)
                 -> ispan2vspanset()          -- map I-span to V-span via POOM
                      -> permute()
                           -> span2spanset()
                                -> retrieverestricted()  -- search POOM for I-address
  -> putfe.c:putfollowlink()                 -- write result to wire
```

### Key Observation at `sporgl.c:67-95`

```c
bool link2sporglset(typetask *taskptr, typeisa *linkisa,
                    typesporglset *sporglsetptr, INT whichend, int type)
{
  typeorgl orgl;
  tumbler zero;
  typevspan vspan;
  typecontext *context, *c, *retrieverestricted();
  typesporgl *sporglptr;

  // Step 1: Find the link orgl
  if (!findorgl (taskptr, granf, linkisa, &orgl,type)){
    return (FALSE);
  }

  // Step 2: Construct V-span for requested endset (0.1, 0.2, or 0.3)
  tumblerclear (&zero);
  tumblerincrement (&zero, 0, whichend, &vspan.stream);
  tumblerincrement (&zero, 0, 1, &vspan.width);

  // Step 3: Retrieve I-addresses from link orgl (NO POOM CHECK)
  if (context = retrieverestricted((typecuc*)orgl, &vspan, V,
                                    (typespan*)NULL, I, (typeisa*)NULL)) {
    for (c = context; c; c = c->nextcontext) {
      sporglptr = (typesporgl *)taskalloc(taskptr,sizeof (typesporgl));
      contextintosporgl ((type2dcontext*)c, (tumbler*)NULL, sporglptr, I);
      *sporglsetptr = (typesporglset)sporglptr;
      sporglsetptr = (typesporglset *)&sporglptr->next;
    }
    contextfree (context);
    return (TRUE);
  } else {
    return (FALSE);
  }
}
```

This function extracts I-addresses from the link orgl's V-dimension storage (endset positions 0.1, 0.2, 0.3). **It does not check whether these I-addresses are currently in any POOM**. It simply reads whatever is stored in the link orgl and returns it.

### The Filter at `orglinks.c:425-449`

The conversion from I-addresses to V-addresses happens in `span2spanset`:

```c
typespanset *span2spanset(typetask *taskptr, typeorgl orgl,
                          typespanset restrictionspanptr, INT restrictionindex,
                          typespanset *targspansetptr, INT targindex)
{
  typecontext *context, *c, *retrieverestricted();
  typespan foundspan;
  typespan *nextptr;

  // Try to find the I-span in the document's POOM
  context = retrieverestricted((typecuc*)orgl, restrictionspanptr,
                                restrictionindex, (typespan*)NULL,
                                targindex, (typeisa*)NULL);

  for (c = context; c; c = c->nextcontext) {
    context2span (c, restrictionspanptr, restrictionindex,
                  &foundspan, targindex);
    nextptr = (typespan *)onitemlist (taskptr, (typeitem*)&foundspan,
                                      (typeitemset*)targspansetptr);
  }

  // Key line: if context is NULL, no V-spans are added
  if(!context){
    return(targspansetptr);  // Return without modification
  }
  // ...
}
```

**Lines 446-448**: If `retrieverestricted` returns NULL (no matching I-address in the POOM), the function **returns the current targspansetptr without adding anything**. The I-address is silently dropped.

---

## Behavior Summary

| Condition | link2sporglset | linksporglset2specset | Result |
|-----------|----------------|----------------------|--------|
| Endset I-addresses in POOM | Returns I-addresses | Converts to V-addresses | Full endset returned |
| Endset I-addresses NOT in POOM | Returns I-addresses | Conversion finds nothing | Empty or partial result |
| Link does not exist | Returns FALSE | Not called | Operation fails |

### Three Cases

**Case 1: All endset I-addresses are live (in some POOM)**

FOLLOWLINK returns complete endset with V-addresses.

**Case 2: Some endset I-addresses are unreferenced (DEL5)**

FOLLOWLINK returns **partial endset** — only the I-addresses that have current POOM mappings are converted to V-addresses. Unreferenced addresses are silently filtered out.

**Case 3: All endset I-addresses are unreferenced**

FOLLOWLINK returns **empty result** `[]` — operation succeeds, but result is empty because no I-addresses map to current V-positions.

---

## Test Evidence

Golden test: `udanax-test-harness/golden/links/orphaned_link_target_all_deleted.json`

```json
{
  "op": "delete_all",
  "doc": "target",
  "comment": "Delete ALL content from target document"
},
{
  "op": "follow_link",
  "label": "after_delete",
  "end": "target",
  "result": [],
  "works": true,
  "comment": "follow_link to target should work but return empty"
}
```

**Observation**: After deleting all target content, FOLLOWLINK(link, TARGET) returns `[]` (empty), not an error. The operation succeeds (`"works": true`).

---

## Specification Context

### EWD-030 DEL5: Unreferenced Addresses

    (DEL5)  Define unreferenced(a) ≡ a ∈ dom.ispace ∧ ¬(∃d, v : poom.d(v) = a)
            An unreferenced address:
            (a) Has content: ispace(a) is defined (P0)
            (b) Has provenance: PROV0 gives native document and origin record
            (c) Has history: the journal records its creation and all placements/removals
            (d) Has no current view: no POOM maps any V-position to it
            (e) Is indexed: DOCISPAN entries record historical placements
            (f) May have links: link endsets in the spanfilade may reference it

**DEL5(f)** explicitly states that link endsets may contain unreferenced I-addresses — "ghost links" that point to content that was once visible but is not currently in any POOM.

### EWD-032 FE5: Ghost Link Handling

    (FE5)  When FOLLOWLINK returns endset I-addresses that have no current V-position
           in any document (unreferenced addresses — DEL5), the front end
           MUST handle the absence gracefully.

           The I-to-V conversion for an unreferenced address yields no V-position.
           The front end should:
           (a) Indicate that the link endpoint exists but the content is not
               currently visible in any document
           (b) Optionally offer reconstitution: COPY the unreferenced content
               into a new document (DEL7)

The specification **expects** FOLLOWLINK to return I-addresses that may not be in any current POOM. The front end is responsible for interpreting empty results as ghost links.

---

## Architectural Implications

### 1. Back End Does Not Filter

The back end's job is to return **what the permanent layer stores** (I-addresses in link endsets). It does NOT make policy decisions about whether those I-addresses are "live" or "useful."

### 2. I-to-V Conversion is POOM-Dependent

The conversion from I-addresses to V-addresses **necessarily depends on which document's POOM is queried**. The same I-address might:
- Be unreferenced in document A (returns empty)
- Be at V-position 1.15 in document B (returns that position)
- Be at V-position 1.42 in document C (returns different position)

This is why `linksporglset2specset` takes a `homedoc` parameter (line 97 of sporgl.c) — it specifies which document's POOM to use for the conversion.

### 3. Front End Must Interpret Empty Results

An empty result from FOLLOWLINK does NOT mean:
- The link doesn't exist (operation would fail)
- The endset is empty (link creation requires non-empty endsets)
- The I-addresses are invalid (they exist in ispace)

It means: **The endset I-addresses have no current V-position in the querying document.**

The front end must distinguish:
- **Error**: Link does not exist (operation fails)
- **Ghost link**: Link exists, endset exists, but I-addresses are unreferenced (operation succeeds, empty result)
- **Normal link**: I-addresses have V-positions (operation succeeds, non-empty result)

### 4. Reconstitution is Always Possible

Because the I-addresses are permanent (P0), the front end can always:
1. Note that I-address `a` is in the endset (from examining the link orgl directly, or from spanfilade)
2. COPY that I-address into a new document
3. The I-address becomes referenced again (DEL7 — reconstitution)

---

## Comparison: FOLLOWLINK vs RETRIEVEENDSETS

| Operation | Input | Lookup Path | Filtering |
|-----------|-------|-------------|-----------|
| FOLLOWLINK | Link ID + whichend | Link orgl → I-addresses → POOM → V-addresses | Unreferenced filtered at I-to-V conversion |
| RETRIEVEENDSETS | Content V-spec | Spanfilade → I-addresses → POOM → V-addresses | Same filtering (Finding 035) |

Both operations:
1. Retrieve I-addresses from permanent storage (link orgl or spanfilade)
2. Convert to V-addresses using a document's POOM
3. Silently filter I-addresses with no current POOM mapping

The difference is the **starting point** (known link ID vs content region search), not the filtering behavior.

---

## The Formal Answer

**Q**: Does FOLLOWLINK check whether endset I-addresses are "live" before returning them?

**A**: The back end retrieves I-addresses from the link orgl **without checking POOM liveness**. During I-to-V conversion, unreferenced I-addresses (DEL5) are silently filtered because they have no current POOM mapping. The operation succeeds but may return empty or partial results. The front end (FE5) is responsible for interpreting empty results as ghost links.

---

## Related Findings

- **Finding 035**: RETRIEVEENDSETS also filters unreferenced addresses during I-to-V conversion
- **EWD-030 DEL5**: Definition of unreferenced addresses (ghost links)
- **EWD-032 FE5**: Front end obligation to handle ghost links gracefully

---

## Open Questions

1. Should the back end provide a separate operation that returns **raw I-addresses** without V-conversion, so front ends can detect ghost links before attempting POOM lookup?

2. Could FOLLOWLINK return a status flag indicating "endset contains unreferenced addresses" to help front ends distinguish ghost links from genuinely empty results?

3. Should there be a query operation to test whether a specific I-address is currently referenced in any POOM (liveness check)?
