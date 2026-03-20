# Finding 0038: POOM Subspace Independence

**Date discovered:** 2026-02-06
**Category:** POOM architecture / V-space structure

## Summary

A document's POOM maintains two independent V-address subspaces for text (1.x) and links (2.x). Operations in one subspace do not affect V-positions in the other subspace. Each maintains its own contiguous numbering independently.

## V-Address Subspace Convention

Documents use two V-address ranges:
- **Text subspace**: V-positions 1.x (e.g., 1.1, 1.2, 1.50) — element field first component = 1
- **Link subspace**: V-positions 2.x (e.g., 2.1, 2.2) — element field first component = 2

Per T4, element field components must be strictly positive. The `0` in tumbler notation (e.g., `N.0.U.0.D.V.0.2.1`) is a field separator, not part of the subspace identifier. The element field starts at `2`.

### Output Normalization

**CAUTION:** `retrievedocvspanset` normalizes link V-positions to `0` in its output when text is also present. This is a display convention, NOT the internal V-address. The internal representation is always 2.x.

1. **In `retrievedocvspanset` output when document has both text and links**:
   - Links appear at V-position "0" with width indicating link count/extent
   - Text appears at V-position "1" with width indicating text extent
   - Example: `[{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]`

2. **In `retrievedocvspanset` output when document has ONLY links** (no text):
   - Links appear at V-position "2.1" with width "0.1" (for first link)
   - Example: `[{"start": "2.1", "width": "0.1"}]`

3. **In link I-addresses** (permanent identity):
   - Link ISAs contain ".0.2.x" component
   - Example: `1.1.0.1.0.1.0.2.1` (document address + link subspace marker + link number)

### Code Evidence

From `do2.c:169-183`, the `setlinkvsas()` function constructs link endpoint V-addresses:
```c
// FROM endpoint (source)
tumblerincrement(fromvsaptr, 0, 1, fromvsaptr);  // digit 0 = 1
tumblerincrement(fromvsaptr, 1, 1, fromvsaptr);  // digit 1 = 1
// Result: "1.1"

// TO endpoint (target)
tumblerincrement(tovsaptr, 0, 2, tovsaptr);      // digit 0 = 2
tumblerincrement(tovsaptr, 1, 1, tovsaptr);      // digit 1 = 1
// Result: "2.1"

// THREE endpoint (type)
tumblerincrement(threevsaptr, 0, 3, threevsaptr);// digit 0 = 3
tumblerincrement(threevsaptr, 1, 1, threevsaptr);// digit 1 = 1
// Result: "3.1"
```

This shows links are internally stored at V-position "2.1", "2.2", etc. But `retrievevspansetpm()` normalizes the output representation.

## Subspace Independence Verified

Test scenario: Create document with text, add link, insert more text.

### Initial State
- Insert "HelloWorld" (10 characters) at V-position 1.1
- Vspanset: `[{"start": "1.1", "width": "0.10"}]`
- Text occupies V-positions 1.1 through 1.11

### After Link Creation
- Create link with source at 1.1-1.5
- Link ISA: `1.1.0.1.0.1.0.2.1`
- Vspanset: `[{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]`
- Two independent spans: links at 2.x (reported as 0 in normalized output), text at 1.x

### After Text Insertion
- Insert "XXXXX" (5 characters) at V-position 1.5 (middle of existing text)
- Vspanset: `[{"start": "0", "width": "0.10"}, {"start": "1", "width": "1"}]`
- Link span UNCHANGED (still at "0")
- Text span encompasses 1.1 through 1.15
- Retrieved contents: "HellXXXXXoWorld" (verified correct insertion point)

### Multiple Links Test
- Starting with "ABC" at 1.1
- Add first link → vspanset shows links at 0.x
- Insert "XX" at 1.2 → text becomes "AXXBC"
- Vspanset after: `[{"start": "0", "width": "0.4"}, {"start": "1", "width": "1"}]`
- Add second link (ISA `1.1.0.1.0.1.0.2.2`)
- Vspanset still: `[{"start": "0", "width": "0.4"}, {"start": "1", "width": "1"}]`
- Insert "YY" at 1.1 → text becomes "YYAXXBC"
- Link span remains at 0.x throughout

## Key Observations

1. **Independent numbering**: Text V-positions (1.x) and link V-positions (2.x) are maintained separately. Inserting text at 1.5 does not shift link positions.

2. **Contiguous within subspace**: Text maintains contiguous V-position numbering from 1.1 onward. Links maintain their own contiguous numbering (2.1, 2.2, ...).

3. **No cross-subspace interference**: Operations in the text subspace (INSERT, DELETE) do not renumber or shift link V-positions. Each subspace evolves independently.

4. **Normalized output**: `retrievedocvspanset` normalizes link V-positions to `0` in output when text is also present. When only links are present, it reports the actual V-position (2.1). This is a display convention — the internal representation is always 2.x.

## Implementation Mechanism

The POOM (orgl enfilade) stores V→I mappings using a 2D tree structure where V-dimension positions encode subspace membership via the first mantissa digit:
- mantissa[0] = 1 → text subspace
- mantissa[0] = 2 → link subspace
- mantissa[0] = 3 → type subspace

When content is inserted at V-position 1.x, the `insertpm()` function operates only on crums in the 1.x range. Link crums (at 2.x) are structurally separate in the tree and unaffected.

From `orglinks.c:173-221`, `retrievevspansetpm()` extracts the two subspaces separately:
- Link span: Derived from root width by zeroing mantissa[1] and justifying
- Text span: Computed via `maxtextwid()` which recursively walks only text crums

## Architectural Significance

This design enables:
- **Concurrent editing**: Text can be edited without invalidating link positions
- **Link stability**: Link endpoints (stored as I-addresses) remain valid even as document V-structure changes
- **Efficient queries**: Link searches don't need to account for text insertion history

However, it creates:
- **Complexity in vspanset interpretation**: Callers must understand that `retrievedocvspanset` normalizes link V-positions to "0" in output, while the internal V-address is 2.x
- **Notation confusion**: I-addresses like `1.1.0.1.0.1.0.2.1` have the `0` as a field separator — the element field is `2.1`, not `0.2.1`

## Related Findings

- **Finding 0009**: Document address space structure (originally claimed 0.x for links, should be corrected)
- **Finding 0024**: Link deletion and orphaned links (correctly identifies 2.x for links in empty documents)
- **Finding 0035**: Five query operations (describes `retrievevspansetpm` output format)
- **Finding 0010**: Unified storage abstraction leaks (explains subspace filtering requirements)

## Test Scenarios

- `text_insert_preserves_link_vpositions.json` - Verifies link V-position stability during text insertion
- `multiple_text_insertions_with_links.json` - Tests multiple insertions with multiple links
- `link_home_document_content_deleted.json` - Shows 2.1 representation when text deleted

## Corrections to Prior Findings

**Finding 0009** should be updated:
- Link subspace is 2.x internally (not 0.x)
- But `retrievedocvspanset` reports it as 0.x when text is present (normalization)
- The 0.x representation is an output format convention, not the internal V-address

**Finding 0024** is correct:
- Links at 2.1 when document has no text
- Consistent with internal representation at V-position 2.x
