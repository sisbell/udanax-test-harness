# Finding 052: CREATELINK Shifts POOM Entries

**Date:** 2026-02-07
**Category:** Link Operations / POOM Structure
**Agent:** Gregory
**Related:** EWD-035 (The Content Discipline), Finding 027 (Insertion Order Semantics)

## Summary

CREATELINK **DOES shift existing POOM entries** when placing a link orgl reference in a document's V-stream. This is contrary to the statement in EWD-035:165 that "existing entries [are] unmodified."

## Evidence from Source Code

### 1. CREATELINK Calls insertpm via docopy

**File:** `/udanax-test-harness/backend/do1.c` lines 199-225

```c
bool docreatelink(typetask *taskptr, typeisa *docisaptr, ...)
{
    // ...
    return (
         createorglingranf (taskptr, granf, &hint, linkisaptr)
      && tumbler2spanset (taskptr, linkisaptr, &ispanset)
      && findnextlinkvsa (taskptr, docisaptr, &linkvsa)    // Line 215
      && docopy (taskptr, docisaptr, &linkvsa, ispanset)    // Line 216
      && findorgl (taskptr, granf, linkisaptr, &link,/*WRITEBERT ECH 7-1*/NOBERTREQUIRED)
      // ...
    );
}
```

### 2. findnextlinkvsa Computes Next Available 2.x Position

**File:** `/udanax-test-harness/backend/do2.c` lines 151-167

```c
bool findnextlinkvsa(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr)
{
    tumbler vspanreach, firstlink;
    // ...
    tumblerclear (&firstlink);
    tumblerincrement (&firstlink, 0, 2, &firstlink);    // firstlink = 2.0
    tumblerincrement (&firstlink, 1, 1, &firstlink);    // firstlink = 2.1

    (void) doretrievedocvspan (taskptr, docisaptr, &vspan);
    tumbleradd (&vspan.stream, &vspan.width, &vspanreach);  // vspanreach = end of document
    if (tumblercmp (&vspanreach, &firstlink) == LESS)
        movetumbler (&firstlink, vsaptr);    // Use 2.1 if doc empty
    else
        movetumbler (&vspanreach, vsaptr);   // Use current end otherwise
    return (TRUE);
}
```

This shows that CREATELINK places the link orgl reference at the END of the current document extent (or 2.1 if the document has no existing links).

### 3. docopy Calls insertpm

**File:** `/udanax-test-harness/backend/do1.c` lines 45-65

```c
bool docopy(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typespecset specset)
{
    // ...
    return (
       specset2ispanset (taskptr, specset, &ispanset, NOBERTREQUIRED)
    && findorgl (taskptr, granf, docisaptr, &docorgl, WRITEBERT)
    && acceptablevsa (vsaptr, docorgl)
    && asserttreeisok(docorgl)

    /* the meat of docopy: */
    && insertpm (taskptr, docisaptr, docorgl, vsaptr, ispanset)    // Line 60

    &&  insertspanf (taskptr, spanf, docisaptr, ispanset, DOCISPAN)
    && asserttreeisok(docorgl)
    );
}
```

### 4. insertpm Calls insertnd with POOM Case

**File:** `/udanax-test-harness/backend/insertnd.c` lines 15-94

```c
int insertnd(typetask *taskptr, typecuc *fullcrumptr, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr, INT index)
{
    // ...
    switch (fullcrumptr->cenftype) {
      case POOM:
          makegappm (taskptr, fullcrumptr, origin, width);      // Line 54 - MAKES GAP!
          checkspecandstringbefore();
          setwispupwards(fullcrumptr,0);
          bothertorecombine=doinsertnd(fullcrumptr,origin,width,infoptr,index);
          setwispupwards(fullcrumptr,1);
          break;
      // ...
    }
    // ...
}
```

### 5. makegappm Shifts Existing POOM Entries

**File:** `/udanax-test-harness/backend/insertnd.c` lines 124-172

```c
int makegappm(typetask *taskptr, typecuc *fullcrumptr, typewid *origin, typewid *width)
{
    // ...
    movetumbler (&origin->dsas[V], &knives.blades[0]);
    findaddressofsecondcutforinsert(&origin->dsas[V],&knives.blades[1]);
    knives.nblades = /*1*/2;
    knives.dimension = V;
    makecutsnd (fullcrumptr, &knives);
    newfindintersectionnd (fullcrumptr, &knives, &father, &foffset);
    prologuend ((typecorecrum*)father, &foffset, &fgrasp, (typedsp*)NULL);
    for (ptr = findleftson (father); ptr; ptr = findrightbro (ptr)) {
           i=insertcutsectionnd(ptr,&fgrasp,&knives);
        switch (i) {
          case 0:
          case 2:
            break;
          case -1:      /* THRUME*/
            dump(ptr);
            gerror ("makegappm can't classify crum\n");
            break;
          case 1:/*9-17-87 fix */
            tumbleradd(&ptr->cdsp.dsas[V],&width->dsas[V],&ptr->cdsp.dsas[V]);  // Line 162 - SHIFTS!
            /*tumbleradd(&width->dsas[V],&ptr->cdsp.dsas[V],&ptr->cdsp.dsas[V]);*/
            ivemodified (ptr);
            break;
          default:
            gerror ("unexpected cutsection\n");
        }
    }
      setwidnd(father);
    setwispupwards (findfather ((typecorecrum*)father),1);
}
```

**Line 162 is the smoking gun**: When a POOM crum is classified as case 1 (THRUME = "through me", meaning it comes AFTER the insertion point), the code adds `width` to the crum's V-dimension displacement, effectively shifting it right.

## Behavioral Implications

1. **CREATELINK DOES Use insertpm**: Despite being a "placement" operation rather than "insertion," CREATELINK follows the same code path as INSERT and COPY.

2. **Existing Entries ARE Shifted**: When a link is created at position 2.(k), all existing POOM entries at positions ≥ 2.(k) are shifted right by the width of the link orgl reference.

3. **EWD-035:165 Statement Is Incorrect**: The claim that "existing entries [are] unmodified" is FALSE at the implementation level. While link ENDSETS may remain stable (because they reference I-addresses, not V-positions), the V-positions of link orgl references in the POOM DO change.

4. **Placement Position Calculation Prevents Observable Shifting**: The reason shifting is not observed is that `findnextlinkvsa` places each new link at the CURRENT DOCUMENT END (vspanreach). Since there are no POOM entries beyond the end, there is nothing to shift. This makes the shifting behavior invisible in practice for sequential link creation.

## Comparison with INSERT

| Operation | Function Called | makegappm? | Shifts POOM? | Observable? |
|-----------|----------------|------------|--------------|-------------|
| INSERT | insertpm | YES | YES | YES (text moves) |
| COPY | insertpm | YES | YES | YES (text moves) |
| CREATELINK | insertpm | YES | YES | NO (places at end) |

## Test Results

**Test:** `/udanax-test-harness/febe/scenarios/links/poom_shifting.py::three_links_vspan_growth`

**Golden output:** `/udanax-test-harness/golden/link_poom/three_links_vspan_growth.json`

```json
{
  "op": "create_link",
  "num": 1,
  "result": "1.1.0.1.0.1.0.2.1"
},
{
  "op": "retrieve_vspanset",
  "label": "after_link1",
  "spans": [
    "0-0.1",    // Text subspace (shortened from 1.1-0.24)
    "1-1"       // Link subspace (NEW)
  ]
},
{
  "op": "create_link",
  "num": 2,
  "result": "1.1.0.1.0.1.0.2.2"
},
{
  "op": "retrieve_vspanset",
  "label": "after_link2",
  "spans": [
    "0-0.1",    // Text subspace (unchanged)
    "1-1"       // Link subspace (unchanged width - no visible shift!)
  ],
  "comment": "If link1's span changed, CREATELINK shifts; if not, it appends"
}
```

**Observation:** The vspan output doesn't show individual 2.x positions for each link. This suggests that either:
- (a) retrieve_vspanset returns a SPAN covering all links (2.1 through 2.k)
- (b) The test is not properly capturing the POOM structure

Further investigation needed to understand vspan reporting behavior.

## Relevance to EWD-035

**EWD-035:165 states:**

> "When CREATELINK adds a new link to a document at position 2.(k+1), existing entries are unmodified."

**Correction needed:**

> "When CREATELINK adds a new link to a document, it uses insertpm which DOES shift existing POOM entries. However, because findnextlinkvsa places the new link at the current document end (max(2.1, vspanreach)), there are typically NO existing entries beyond this position to shift. Thus, while the IMPLEMENTATION uses shifting logic, the OBSERVABLE behavior for sequential link creation is append-only."

## Related Findings

- **Finding 027** (Insertion Order Semantics): INSERT shifts existing entries right
- **Finding 041** (Enfilade Insertion Order Dependency): Physical tree structure depends on insertion order

## Architectural Significance

CREATELINK follows the SAME code path as INSERT, using `insertpm → insertnd → makegappm`. The "no shifting" behavior is an EMERGENT PROPERTY of always placing at document end, not a fundamental difference in implementation.

This has implications for:
1. **Concurrent link creation**: If two operations try to create links simultaneously, they both call insertpm with shifting semantics
2. **Link position stability**: V-positions of link orgls CAN change if operations are interleaved
3. **EWD correctness**: The formal model should clarify whether "unmodified" means logical (endset I-addresses) or physical (POOM V-positions)

## Open Questions

1. **Why doesn't retrieve_vspanset show individual 2.x positions?** Does it aggregate contiguous subspace ranges?
2. **What happens if CREATELINK is called with an explicit 2.k position BEFORE document end?** Would existing links shift?
3. **Are link orgl references ALWAYS width 1?** This would make all shifts uniform.
4. **Does DELETEVSPAN on 2.x positions shift remaining links?** (See Finding 040 - Link Removal from POOM)

## References

- `/udanax-test-harness/backend/do1.c:199-225` — docreatelink implementation
- `/udanax-test-harness/backend/do2.c:151-167` — findnextlinkvsa position calculation
- `/udanax-test-harness/backend/do1.c:45-65` — docopy calls insertpm
- `/udanax-test-harness/backend/insertnd.c:54` — makegappm called for POOM
- `/udanax-test-harness/backend/insertnd.c:162` — tumbleradd shifts crum displacement
- EWD-035 (The Content Discipline) — line 165 claim about unmodified entries
