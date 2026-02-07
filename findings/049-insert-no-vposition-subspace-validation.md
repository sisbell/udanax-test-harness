# Finding 049: INSERT Does Not Validate V-Position Subspace

**Date discovered:** 2026-02-07
**Category:** Type enforcement / V-space validation

## Summary

The back end does NOT enforce subspace restrictions at the INSERT level. The caller can specify ANY V-position (1.x, 2.x, 3.x, etc.) and INSERT will place text bytes at that position without validation. This allows text content to be placed in the link subspace (2.x), violating the conventional subspace partition.

## Test Evidence

Test scenario: INSERT text at V-position 2.1 (link subspace)

```json
{
  "op": "insert",
  "doc": "1.1.0.1.0.1",
  "address": "2.1",
  "text": "TextAtLinkPosition",
  "succeeded": true,
  "error": null
}
```

Result: **Succeeded**

### Vspanset After INSERT

Before INSERT at 2.1:
```json
{
  "spans": [{"start": "1.1", "width": "0.10"}]
}
```

After INSERT at 2.1:
```json
{
  "spans": [
    {"start": "0", "width": "0.1"},
    {"start": "1", "width": "1"}
  ]
}
```

The vspanset shows TWO spans after the insert. The notation "start": "0" appears to be a normalized representation that encompasses the 2.x range (see Finding 038).

### Content Retrieval

```json
{
  "op": "retrieve_contents",
  "from": "2.1",
  "width": "0.19",
  "result": ["TextAtLinkPosition"],
  "succeeded": true
}
```

The text bytes are successfully stored and retrieved from V-position 2.1.

## Code Analysis

### acceptablevsa() Function

From `udanax-test-harness/backend/do2.c:110-113`:

```c
bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr)
{
    return (TRUE);
}
```

The function that validates V-positions **always returns TRUE**. No validation is performed.

### insertpm() Function

From `udanax-test-harness/backend/orglinks.c:75-134`:

```c
bool insertpm(typetask *taskptr, tumbler *orglisa, typeorgl orgl, tumbler *vsaptr, typesporglset sporglset)
{
    // ... setup code ...

    if (iszerotumbler (vsaptr)){
        fprintf(stderr,"insertpm inserting at 0 ---punt zzzz?");
        return (FALSE);
    }
    tumblerclear (&zero);
    if (tumblercmp (vsaptr, &zero) == LESS)
        gerror ("insertpm called with negative vsa.\n");

    logbertmodified(orglisa, user);
    for (; sporglset; sporglset = (typesporglset) sporglset->xxxxsporgl.next) {
        // ... unpack I-address and width ...
        movetumbler (vsaptr, &crumorigin.dsas[V]);  // <-- V-position used directly
        // ... insert into enfilade ...
    }
    return (TRUE);
}
```

The only checks are:
- Line 86-90: Reject if zero tumbler
- Line 93-98: Reject if negative

**No check that vsaptr is in the 1.x subspace** for text insertion. The V-position is copied directly to `crumorigin.dsas[V]` at line 113 and used for enfilade insertion.

### doinsert() Call Chain

From `udanax-test-harness/backend/do1.c:91-127`:

```c
bool doinsert(typetask *taskptr, typeisa *docisaptr, tumbler *vsaptr, typetextset textset)
{
    typehint hint;
    typespanset ispanset;
    INT ret;
    bool doretrievev(), inserttextingranf(), docopy();

    makehint(DOCUMENT, ATOM, TEXTATOM, docisaptr, &hint);
    ret = (inserttextingranf(taskptr, granf, &hint, textset, &ispanset)
        && docopy (taskptr, docisaptr, vsaptr, ispanset)
    );
    return(ret);
}
```

INSERT calls `docopy()` which calls `acceptablevsa()` (which returns TRUE) and then `insertpm()` (which uses vsaptr directly).

## Architectural Implications

### Conventional vs. Enforced Invariants

The subspace partition (text at 1.x, links at 2.x) is a **convention**, not an **enforced invariant**. The back end:

- **Does enforce**: Non-zero, non-negative V-positions
- **Does NOT enforce**: Subspace membership

This aligns with Finding 011 (Convention Over Enforcement Design) - the system relies on front end cooperation for many semantic invariants.

### ENF0 Predicate Scope

From EWD-033, the `may-modify` predicate (ENF0) only applies to **existing orgls**:

```
may-modify(orgl) ≡ element-type(orgl) ≠ LINKATOM
```

ENF0 prevents MODIFICATION of link orgls but does NOT prevent:
- Creating text content at arbitrary V-positions
- Placing text bytes in the 2.x subspace via INSERT

This finding shows ENF0 is a **target-type discipline** (what existing orgls can be modified) but NOT a **placement discipline** (where new content can be inserted).

### Element Type Assignment

From `udanax-test-harness/backend/xanadu.h:145-146`:

```c
#define TEXTATOM    1
#define LINKATOM    2
```

The element type (stored in hint) is set by the CALLER:
- `doinsert()` sets `TEXTATOM` (line 121)
- `CREATELINK` sets `LINKATOM` for link endsets

But the **V-position is also specified by the caller**, and there is no validation that element type matches V-position subspace.

### Implications for I₂ and I₄

From EWD-018, invariants I₂ (widdativity) and I₄ (link-orgl structure) rely on:
- Text content having element type TEXTATOM
- Link content having element type LINKATOM
- Each subspace containing only its designated type

This finding shows the back end does NOT structurally enforce the subspace-to-type mapping. A malicious or buggy front end could:
1. INSERT text at 2.1 (this test demonstrates it works)
2. Retrieve that content as if it were a link
3. Violate I₄ by having non-orgl data in the link subspace

The convention boundary (CB3 from EWD-022) includes this invariant, and ENF0 does NOT close the gap for initial placement.

## Comparison with CREATELINK

From Finding 033 (EWD-033), CREATELINK uses `NOBERTREQUIRED` when creating link orgls:

```c
// do1.c:199-225
findorgl (taskptr, granf, linkisaptr, &linkorgl, NOBERTREQUIRED)
```

Link orgls are created with element type LINKATOM and placed at V-positions 2.x in a single atomic operation. The fresh orgl has no prior state, so ENF0's "may-modify" predicate doesn't apply.

But INSERT operates similarly:
1. Allocates new I-addresses via `inserttextingranf()`
2. Places them at caller-specified V-position via `docopy()`
3. No validation that V-position matches element type

## Related Findings

- **Finding 011**: Convention Over Enforcement Design - system relies on front end for many invariants
- **Finding 033**: ENF0 predicate closes convention gap for MODIFICATION but not PLACEMENT
- **Finding 038**: POOM Subspace Independence - describes 1.x (text) and 2.x (link) subspaces
- **Finding 042**: BED Event Loop Atomicity - INSERT is atomic at operation level

## Consequences

### For Specification (EWD Series)

1. **CB3 qualified**: The convention "link orgls only in 2.x subspace" is conventional, not enforced
2. **ENF0 incomplete**: ENF0 prevents modification of existing link orgls but NOT placement of text in link subspace
3. **I₂/I₄ preservation requires front end cooperation**: A misbehaving front end can violate invariants by inserting wrong types at wrong V-positions

### For Front End Implementation

1. **Front end must validate V-positions**: When calling INSERT, ensure V-position is in 1.x subspace
2. **No back end safety net**: The back end will accept and store whatever V-position is specified
3. **Type-position consistency**: Front end responsible for ensuring element type matches V-position subspace

### For System Security

1. **No defense against malicious clients**: A client with WRITEBERT can corrupt document structure by inserting at arbitrary V-positions
2. **BERT is document-level**: WRITEBERT grants permission to modify ANY V-position within the document
3. **No operation-level access control**: BERT doesn't distinguish INSERT-TEXT from INSERT-AT-ARBITRARY-POSITION

## Open Questions

1. **Should acceptablevsa() validate subspace?** Currently returns TRUE; could check vsaptr[0] == 1 for text operations
2. **Is 0.x subspace also insertable?** This test only tried 2.x; what about 0.x?
3. **What about 3.x (type subspace)?** Can text be inserted there too?
4. **Does VCOPY validate subspace?** Or can it also copy content across subspace boundaries?
5. **Should ENF0 be extended?** Add `may-place-at(vpos, element-type)` predicate for placement validation

## Test Scenarios

- `links/insert_text_at_link_subspace.json` - Demonstrates INSERT at 2.1 succeeds
- Related: `links/copy_link_to_text_subspace.json` - Tests VCOPY cross-subspace operation

## Recommendations

### For Specification

Document this as a known gap in convention enforcement:
- CB3 (subspace partition) is conventional and requires front end cooperation
- ENF0 covers modification of existing orgls but NOT initial placement
- Consider defining `may-place-at` predicate as extension to ENF0

### For Implementation

Options for closing the gap:
1. **Modify acceptablevsa()**: Add V-position validation based on operation type
2. **Add operation-aware BERT**: Extend BERT to distinguish INSERT-TEXT from general WRITE
3. **Front end validation**: Document requirement and trust front end (current approach)

### For Front End

Best practice:
```python
# ALWAYS validate V-position before calling INSERT
def insert_text(session, doc_opened, vpos, text):
    if not vpos.startswith("1."):
        raise ValueError(f"Text must be inserted in 1.x subspace, got {vpos}")
    return session.insert(doc_opened, vpos, text)
```

## Correction to EWD-033

EWD-033 states:
> Under ENF0, all SYS invariants enforced — I₂, I₃, I₄ become structural

This finding shows that's incorrect for PLACEMENT operations. ENF0 makes link endsets immutable (I₄ holds for existing links) but does NOT prevent:
- Placing text bytes in link subspace via INSERT
- Potentially violating I₄ if those bytes are interpreted as links

The correct statement:
> Under ENF0, I₃ and I₄ become structural for MODIFICATION of existing orgls. I₂ and I₄ for PLACEMENT still require front end cooperation (CB3).
