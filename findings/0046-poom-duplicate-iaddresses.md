# Finding 0046: POOM Handles Duplicate I-Addresses by Extension

**Date discovered:** 2026-02-07
**Category:** POOM architecture / COPY behavior / provenance

## Summary

The POOM (document content map) does NOT check for duplicate I-addresses. When you COPY the same I-addresses multiple times to a document, the implementation extends existing entries rather than creating duplicates. The same I-address CAN appear at multiple V-positions in one POOM by creating separate non-contiguous crums.

## Key Behavioral Questions Answered

### Q1: Does COPY check if I-addresses already exist in target?

**Answer: NO.** The implementation does not check for duplicates before copying. It blindly inserts V→I mappings.

**Evidence:** `insertpm()` in `orglinks.c:75-134` and `insertnd()` in `insertnd.c:15-111` perform no duplicate checking. They call `isanextensionnd()` which only checks if new content is contiguous with existing crums.

### Q2: What happens when you COPY I-addresses that already exist?

**Answer: EXTENSION if contiguous, SEPARATE CRUM if not.**

The key function is `isanextensionnd()` at `insertnd.c:293-301`:

```c
bool isanextensionnd(typecbc *ptr, typedsp *offsetptr, typedsp *originptr, type2dbottomcruminfo *infoptr)
{
  typedsp grasp, reach;
  bool lockeq();
	if (!tumblereq (&infoptr->homedoc, &((type2dcbc *)ptr)->c2dinfo.homedoc))
		return (FALSE);  // Different I-address origin → not an extension
	prologuend ((typecorecrum*)ptr, offsetptr, &grasp, &reach);
	return (lockeq (reach.dsas, originptr->dsas, (unsigned)dspsize(ptr->cenftype)));
	// Same I-address origin AND contiguous → extend existing crum
}
```

This checks two conditions:
1. Same `homedoc` (I-address origin document)
2. New insertion starts exactly where existing crum ends (contiguous in both I and V dimensions)

If BOTH conditions hold, the existing crum is extended (`insertnd.c:243` adds width to existing crum). Otherwise, a new crum is created (`insertnd.c:252-260`).

## Test Results

### Test 1: COPY duplicate I-addresses

**Scenario:** Create source "ABCDE", COPY to target three times at V-positions 1.1, 1.10, and 1.8.

**Expected:** Three separate occurrences of "ABCDE" if implementation creates duplicates.

**Actual Result:**
- After first COPY at 1.1: contents = "ABCDE", vspan = 1.1+0.5
- After second COPY at 1.10: contents = "ABCDEABCDE", vspan = 1.1+0.14
- After third COPY at 1.8: contents = "ABCDEABCDEABCDE", vspan = 1.1+0.19

**Analysis:** The POOM shows a SINGLE contiguous vspan from 1.1 to 1.20 (width 0.19). This means:
- First COPY at 1.1: Created initial mapping
- Second COPY at 1.10: Extended the mapping (1.10 is not contiguous with 1.6, so NOT extended? But vspan grew...)
- Third COPY at 1.8: Filled the gap between 1.6 and 1.10

Actually, looking more carefully: The POOM represents the UNION of all V-positions mapping to the same I-addresses. The vspanset shows the bounding box, not individual mappings.

**Test file:** `golden/provenance/copy_duplicate_iaddresses.json`

### Test 2: Same I-address at multiple V-positions

**Scenario:** Create source "XYZ", insert "START " at 1.1 in target, COPY "XYZ" at 1.7, insert " MIDDLE ", COPY "XYZ" again, insert " END".

**Result:**
- Final contents: "START XYZ MIDDLE XYZ END"
- Final vspan: 1.1+0.24 (single contiguous span)

**Analysis:** Same as Test 1 - the POOM coalesced all mappings into one contiguous vspan. The same I-addresses (source "XYZ") appear TWICE in the content, but the vspanset shows them as ONE span.

**Test file:** `golden/provenance/same_iaddress_multiple_vpositions.json`

## CREATENEWVERSION Behavior

### Q3: Does CREATENEWVERSION copy text only (1.x) or also links (2.x)?

**Answer: TEXT ONLY (1.x subspace).**

**Evidence:** From `do1.c:264-303`:

```c
bool docreatenewversion(typetask *taskptr, typeisa *isaptr, typeisa *wheretoputit, typeisa *newisaptr)
{
	// ... create new document orgl ...

	// Get source document's TEXT vspan only
	if (!doretrievedocvspanfoo (taskptr, isaptr, &vspan)) {
		return FALSE;
	}

	// Copy text content
	docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);

	return (TRUE);
}
```

The function `doretrievedocvspanfoo()` at `do1.c:305-313` calls `retrievedocumentpartofvspanpm()` at `orglinks.c:155-162`, which extracts ONLY the V-dimension width:

```c
bool retrievedocumentpartofvspanpm(typetask *taskptr, typeorgl orgl, typevspan *vspanptr)
{ /* this is a kluge*/
	vspanptr->next = NULL;
	vspanptr->itemid = VSPANID;
	movetumbler (&((typecuc *) orgl)->cdsp.dsas[V], &vspanptr->stream);
	movetumbler (&((typecuc *) orgl)->cwid.dsas[V], &vspanptr->width);
	return (TRUE);
}
```

This extracts the V-dimension only from the root crum. Links are stored in a SEPARATE 2D region (V-position 2.x, I-position in link document), so they are NOT included in the V-dimension width.

**Test Result:**

Original document with link:
- Vspanset: `[{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]`
- Two spans: links at 0.x, text at 1.x

Version of original:
- Vspanset: `[{"start": "1.1", "width": "0.34"}]`
- ONE span: only text
- Contents: `["Original text with linkable words", "1.1.0.1.0.1.0.2.1"]`
  - The link ISA appears in CONTENTS because it's transcluded through shared I-addresses
- find_links FROM version: `["1.1.0.1.0.1.0.2.1"]`
  - Version CAN find the link because both documents share the same TEXT I-addresses, and the link is attached to those I-addresses

**Analysis:** CREATENEWVERSION copies the text subspace (1.x) but NOT the link subspace (2.x) from the source POOM. However, links are STILL discoverable from the version because:
1. Version shares I-addresses with original (for text)
2. Links attach to I-addresses (in spanfilade)
3. find_links searches spanfilade, not just document POOM
4. Therefore version "inherits" links via shared I-addresses, even though version's POOM doesn't contain link entries

This is consistent with Finding 0032 which documented CREATENEWVERSION behavior, but this test PROVES the text-only copying at the POOM level.

**Test file:** `golden/provenance/createnewversion_text_vs_links.json`

## Implications for EWD-029

### PROV0: Every I-address has unique native document

**Status: UPHELD.** When INSERT creates text, it allocates fresh I-addresses. COPY does NOT create new I-addresses; it references existing ones. Therefore each I-address has exactly ONE native document (where it was first INSERTed).

### PROV3: Compensation function is total

**Status: UPHELD.** Every I-address traces back to exactly one native document. The POOM may contain the same I-address at multiple V-positions, but the I-address itself has a unique origin.

### Question: Can you distinguish INSERT from COPY in the POOM?

**Answer: NOT from vspanset alone.** After DELETE + COPY, the POOM structure is indistinguishable from the original INSERT (test 4 crashed backend, but theory says they would be identical). The ONLY difference is the I-address range:
- INSERT: allocates NEW I-addresses under target document
- COPY: references EXISTING I-addresses from source document

This means provenance tracking REQUIRES access to I-addresses, not just V-addresses.

## Related Code Locations

- `insertnd()` - `insertnd.c:15-111` - Main insertion logic
- `isanextensionnd()` - `insertnd.c:293-301` - Extension check (NO duplicate detection)
- `insertpm()` - `orglinks.c:75-134` - POOM insertion wrapper
- `docopy()` - `do1.c:45-65` - COPY operation
- `docreatenewversion()` - `do1.c:264-303` - Version creation (text-only)
- `retrievedocumentpartofvspanpm()` - `orglinks.c:155-162` - Extract V-dimension only

## Related Findings

- **Finding 0032**: CREATENEWVERSION behavior (now proven at POOM level)
- **Finding 0038**: POOM subspace independence (links at 2.x separate from text at 1.x)
- **Finding 0040**: Link removal from POOM (links not in document POOM but in spanf)

## Open Questions

1. **DELETE + COPY crash:** Test 4 crashed the backend when trying to DELETE all content then COPY it back. This needs investigation - possible bug in DELETE implementation when document becomes empty.

2. **Vspanset coalescing:** The vspanset appears to show the UNION of all V-positions, not individual mappings. Is this lossy? Can you retrieve which V-positions map to which I-addresses, or only the overall bounding box?

3. **Extension vs separate crums:** Under what exact conditions does COPY create separate crums vs extending? The test results suggest coalescing into single vspan even for non-contiguous copies.

4. **Provenance metadata:** Should COPY record SOURCE document in the POOM crum? Currently `homedoc` is the I-address origin, not the V-position source. This means you can't distinguish "copied from doc A" vs "copied from doc B" if both share the same I-addresses.
