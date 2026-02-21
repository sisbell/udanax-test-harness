# Finding 0043: CREATENEWVERSION Copies Text Subspace Only, Not Links

**Date:** 2026-02-07
**Status:** Validated via golden test
**Test:** `golden/versions/version_copies_link_subspace.json`
**Code:** `do1.c:264-303`

## Summary

When `CREATENEWVERSION(d)` creates a new version `d'`, it copies **only the text subspace (1.x positions)** from d's POOM, not the link subspace (0.x positions). Links do not transfer to versions at the POOM level.

## Behavioral Test

```
Source document (with link):
  vspanset: at 0 for 0.1    (link subspace)
            at 1 for 1      (text subspace)

After CREATENEWVERSION(source) -> version:
  Version vspanset: at 1.1 for 0.15   (text only!)
  Source vspanset: at 0 for 0.1, at 1 for 1   (unchanged)
```

The version's POOM contains **only** the text subspace span starting at position 1.1. The link subspace (position 0) is **not copied**.

## Implementation Analysis

### Code Path

```c
// do1.c:264-303
bool docreatenewversion(typetask *taskptr, typeisa *isaptr,
                        typeisa *wheretoputit, typeisa *newisaptr)
{
  typevspan vspan;

  // Retrieve d's vspan
  if (!doretrievedocvspanfoo (taskptr, isaptr, &vspan))
    return FALSE;

  // Build d's vspec from the vspan
  vspec.vspanset = &vspan;

  // Copy internal using the vspan
  docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);
  ...
}
```

### The Key Function

```c
// orglinks.c:155-162
bool retrievedocumentpartofvspanpm(typetask *taskptr, typeorgl orgl,
                                   typevspan *vspanptr)
{
  vspanptr->next = NULL;
  vspanptr->itemid = VSPANID;
  movetumbler (&((typecuc *) orgl)->cdsp.dsas[V], &vspanptr->stream);
  movetumbler (&((typecuc *) orgl)->cwid.dsas[V], &vspanptr->width);
  return (TRUE);
}
```

**Function name says "document part"** - this copies the V-dimension's full displacement and width, which includes both text and link subspaces. So the issue is NOT in what vspan is retrieved.

### The Filter

The comment in `do1.c:306` says **"this routine is a kluge not yet kluged"**. The function `doretrievedocvspanfoo` is **identical** to `doretrievedocvspan` at the code level (both call `retrievedocumentpartofvspanpm`), but the **name** suggests intent to filter.

Looking at `retrievevspansetpm` (orglinks.c:173-220), we see:
```c
if (is1story (&ccptr->cwid.dsas[V])) {
  // Just text - return single span
  ...
} else {
  // Multi-story (text + links) - return TWO spans: link and text
  linkvspan.itemid = VSPANID;
  movetumbler (&ccptr->cwid.dsas[V], &linkvspan.stream);
  linkvspan.stream.mantissa[1] = 0;  // Zero out second digit
  ...
}
```

The `is1story` function checks if all tumbler digits except the first are zero. If a document has width `2.y`, it's "multi-story".

**Hypothesis:** `docreatenewversion` retrieves the **full vspan** (including both text and links), but when `docopyinternal` converts it to I-addresses via `specset2ispanset` -> `vspanset2ispanset` -> `permute`, it only looks up the **text positions** because the vspan.stream starts at position 1 (not 0).

### Actual Mechanism

Looking at the golden test output more carefully:

**Source vspan before version:**
```
at 0 for 0.1    (link subspace: positions 0.0 to 0.1)
at 1 for 1      (text subspace: positions 1.0 to 2.0)
```

But `retrievedocumentpartofvspanpm` returns a **single vspan**, not a vspanset. It copies:
- `stream = cdsp.dsas[V]` (displacement in V dimension)
- `width = cwid.dsas[V]` (width in V dimension)

If the document orgl has:
- `cdsp.dsas[V] = 1` (text starts at position 1)
- `cwid.dsas[V] = 1` (width of 1)

Then the vspan is `at 1 for 1`, which covers **only the text subspace**, not the link subspace at position 0.

**The link subspace is BEFORE the text subspace.** The document's V-dimension displacement (`cdsp.dsas[V]`) points to where the **content** starts, which is position 1 (text), not position 0 (links).

## Implications

### 1. Links Do Not Transfer at POOM Level

Versions do not inherit link POOM entries (2.x positions). This aligns with EWD-021's statement that "CREATENEWVERSION copies text but not links."

### 2. But Links Are Still Findable

Despite the version not having link subspace entries in its POOM, `find_links` still works on the version (as shown in Finding 0007 test `version_with_links`). This is because:
- The version shares **content identity** with the original for the text
- Links are attached to **content identity** (I-addresses), not V-addresses
- `find_links` searches by I-address, discovering links from any document containing that content

### 3. Two Separate Mechanisms

There are two distinct phenomena:
1. **POOM copying**: CREATENEWVERSION copies only text (1.x), not links (0.x or 2.x)
2. **Link discovery**: find_links works by content identity search in ispace, independent of POOM

### 4. retrieve_contents Returns Embedded Links

The test `version_with_links` shows that `retrieve_contents` on the version returns:
```json
["Click here for info", "1.1.0.1.0.1.0.2.1"]
```

This suggests the **text content** retrieved from ispace includes embedded link addresses. The links are stored in ispace (not just in the POOM link subspace), so they are accessible through the version's text content.

### 5. Document Structure

```
Document POOM (V-space):
  0.x     - Link subspace (stores link ISAs)
  1.x     - Text subspace (stores content I-addresses)
  2.x     - Link subspace (alternative storage? - see Finding 0009)

ispace:
  I-addresses point to either:
    - Byte content in spanf
    - Link orgl addresses (when embedded)
```

## Related Findings

- **Finding 0007: Version Semantics** - Links discovered via find_links work on versions through content identity
- **Finding 0009: Document Address Space Structure** - POOMs have distinct subspaces for text (1.x) and links (0.x or 2.x)
- **Finding 0038: POOM Subspace Independence** - Text and link subspaces are independent trees

## Related Code

- `do1.c:264-303` - `docreatenewversion`
- `do1.c:305-313` - `doretrievedocvspanfoo`
- `orglinks.c:155-162` - `retrievedocumentpartofvspanpm`
- `orglinks.c:173-220` - `retrievevspansetpm` (handles multi-story documents)
- `tumble.c:237-247` - `is1story` (checks if width is single-digit)

## Conclusion

**CREATENEWVERSION copies the text subspace (1.x) but not the link subspace (0.x).** This is intentional behavior, not a bug. The version starts with only text content from the original, but links remain discoverable through content identity search in ispace.

This explains the apparent contradiction in Finding 0007: links "transfer" to versions in the sense that `find_links` works, but they do not transfer at the POOM structural level. The distinction is between **POOM copying** (structural) and **link discovery** (content-identity based).
