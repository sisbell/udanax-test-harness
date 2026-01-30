# Finding 009: Document Address Space Structure and Link Storage

**Date:** 2026-01-30
**Related:** Bug 009 investigation

## Summary

Documents in Udanax Green have a **two-dimensional virtual address space** with distinct subspaces for different content types. This architecture has significant implications for version comparison and content identity.

## Document V-Address Subspaces

A document's virtual address space is partitioned:

| V-Position | Subspace | Content |
|------------|----------|---------|
| 0.x | Link subspace | References to link orgls |
| 1.x | Text subspace | Actual document content |

### Evidence

From `findnextlinkvsa()` in do2.c:151-167:
```c
tumblerclear (&firstlink);
tumblerincrement (&firstlink, 0, 2, &firstlink);  // digit 0, value 2 → position 0
tumblerincrement (&firstlink, 1, 1, &firstlink);  // digit 1, value 1 → subposition .1
// First link position is 0.1
```

From debug output:
- Before link: `<VSpec in 1.1.0.1.0.1, at 1.1 for 0.16>`
- After link: `<VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>`

## How Links Are Stored

When a link is created (`docreatelink` in do1.c:199-225):

1. **Create link orgl**: `createorglingranf()` creates a new orgl with its own ISA (e.g., `1.1.0.1.0.2`)

2. **Convert ISA to ispanset**: `tumbler2spanset()` wraps the link's ISA as an ispan

3. **Find next link position**: `findnextlinkvsa()` returns the next available position in the 0.x subspace

4. **Copy link reference into document**: `docopy()` inserts the link's ISA at the 0.x position

```c
// From docreatelink() - do1.c:215-216
&& findnextlinkvsa (taskptr, docisaptr, &linkvsa)
&& docopy (taskptr, docisaptr, &linkvsa, ispanset)
```

### Critical Insight: Links Use the Same Storage as Transclusion

**Links are stored using `docopy()`** - the exact same function used for transclusion!

This means:
- A document's enfilade is a **unified store** for both content and link metadata
- Link references are treated as "content" at V-position 0.x
- The enfilade doesn't distinguish between "real content" and "link references" - it just maps V→I

| What's Stored | V-Position | I-Address Type | Stored Via |
|---------------|------------|----------------|------------|
| Text characters | 1.x | Permascroll address | `docopy` / `doinsert` |
| Link references | 0.x | Link orgl ISA | `docopy` |

This architectural unity is elegant but has consequences - it's a **leaky abstraction**.

## The Leaky Abstraction

### The Abstraction

The enfilade presents a simple, uniform model:

> "A document is a mapping from V-positions to I-addresses"

This abstraction is powerful because:
- All storage operations use the same mechanism (`docopy`, `insertpm`)
- All retrieval operations use the same mechanism (`retrieverestricted`, `permute`)
- The enfilade doesn't need special cases for different content types

### Where It Leaks

The abstraction breaks down when **semantic differences** between V-subspaces matter:

| Operation | Assumption | Reality | Consequence |
|-----------|------------|---------|-------------|
| `compare_versions` | All I-addresses represent shared content | Link ISAs ≠ text I-addresses | Crash or meaningless intersection |
| `retrieve_contents` | All I-addresses can be dereferenced to bytes | Link ISAs are references, not content | Would return gibberish for 0.x |
| `find_links` | Needs to search only link subspace | Must filter to 0.x | Extra complexity |
| I-span intersection | I-addresses are comparable | Different address spaces | Empty intersection or crash |

### The Core Problem

**Not all I-addresses are semantically equivalent:**

```
Permascroll I-address (text):     2.1.0.5.0.123
  → Dereferences to: actual character bytes
  → Meaning: "This is character #123 in the global content store"
  → Comparable with: other permascroll addresses

Link orgl ISA (link reference):   1.1.0.1.0.2
  → Dereferences to: a link orgl structure
  → Meaning: "This is the link object at this address"
  → Comparable with: nothing (unique identity)
```

When code treats these uniformly, it produces nonsense:
- Intersecting `2.1.0.5.0.123` with `1.1.0.1.0.2` → no match (correct but meaningless)
- Trying to find "shared content" between link ISAs → always empty
- Converting link ISA to "content bytes" → undefined behavior

### Analogy: Unix "Everything is a File"

This is similar to Unix's famous abstraction where "everything is a file":

| Unix | Xanadu |
|------|--------|
| Regular file, directory, socket, device → all "files" | Text, link refs → all "V→I mappings" |
| `read()` works on all | `retrieverestricted()` works on all |
| But `seek()` on a socket fails | But `compare_versions` on link subspace crashes |
| Need `stat()` to check type | Need to check V-position to know type |

The abstraction is useful for common operations but **leaks when type-specific behavior is needed**.

### Design Implications

The Xanadu architects had choices:

**Option A: Type-aware enfilade** (rejected)
- Store content type metadata with each V-range
- Operations check type before proceeding
- More complex but explicit

**Option B: Uniform enfilade + convention** (chosen)
- V-position encodes type (0.x = links, 1.x = text)
- Operations must "know" to filter appropriately
- Simpler storage but implicit contract

The chosen design (Option B) means:
1. **Callers must be type-aware** - Code calling `retrieve_vspanset` must know to filter
2. **V-position is overloaded** - It's both a position AND a type indicator
3. **Bugs arise from uniformity assumptions** - Like Bug 009

### The Right Fix for Bug 009

Given this understanding, the proper fix isn't just NULL-checking - it's **semantic filtering**:

```python
# Before compare_versions, filter to text subspace only
def get_text_vspanset(vspanset):
    """Filter vspanset to text subspace (V >= 1), excluding link subspace (V < 1)."""
    return [span for span in vspanset.spans
            if span.start.digits[0] >= 1]  # Position 1.x or higher
```

This respects the semantic boundary that the unified storage model obscures.

## I-Address Types

There are fundamentally different types of I-addresses in the system:

| Type | Source | Example | Meaning |
|------|--------|---------|---------|
| Permascroll I-address | Text insertion | `2.1.0.5.0.123` | Character identity in global permascroll |
| Document ISA | Link storage | `1.1.0.1.0.2` | Identity of a link orgl |

When `vspanset2ispanset()` converts V-spans to I-spans:
- Text at 1.x → Permascroll I-addresses
- Links at 0.x → Link orgl ISAs

## Implications for Version Comparison

The `compare_versions` operation assumes a uniform content model:
1. Convert V-spans to I-spans for both documents
2. Intersect I-spans to find shared content
3. Map back to V-spans

**The problem**: Link ISAs and text I-addresses are in completely different address spaces. They will never intersect, which is semantically correct. But the code paths don't handle the case where some V-spans produce no common I-spans gracefully.

### Semantic Question

Should `compare_versions` include link subspace content at all?

**Arguments for excluding**:
- Links are metadata, not content
- Link ISAs aren't "shared content" in the transclusion sense
- Comparing link references between versions is a different operation

**Arguments for including**:
- Links are stored in the document's V-space
- The vspanset returned by `retrieve_vspanset` includes links
- Excluding would require special-case filtering

## The vspanset Consolidation

When retrieving a document's vspanset:
- **Before link**: `at 1.1 for 0.16` - precise text range
- **After link**: `at 0 for 0.1, at 1 for 1` - consolidated spans

The change from `at 1.1 for 0.16` to `at 1 for 1` suggests the vspanset is **consolidated to cover the document extent** rather than precise content boundaries. This may be intentional (efficiency) or a side effect of link insertion.

## Architectural Observation

The code in `correspond.c` appears to assume a **1:1 correspondence** between:
- Common I-spans (shared content identity)
- V-specs (document regions)

The nested loop structure:
```c
for (; ispanset; ispanset = ispanset->next) {
    for (; specset; specset = ...) {
```

This pattern suggests the original design expected each ispan to match at most one vspec. The link subspace violates this assumption because:
- Multiple ispans might match the same vspec
- Some vspecs (link subspace) might not match any common ispans

## Recommendations

1. **Document the subspace convention**: Position 0.x for links, 1.x for text should be formally documented

2. **Consider filtering**: Version comparison should probably filter to text subspace only, as comparing link references is semantically different from comparing content

3. **Fix the nested loop**: The loop should properly handle multiple vspecs per ispan and ispans that match no vspecs

4. **Add ispan type awareness**: The system could benefit from distinguishing permascroll I-addresses from document ISAs

## Technical Details: Address Conversion Functions

The system uses a **bidirectional mapping** between V-addresses and I-addresses:

### The `permute()` Function (orglinks.c:404-422)

Central to the address model is `permute()`, which generalizes V↔I conversion:

```c
permute(taskptr, orgl, spanset, fromIndex, targetPtr, toIndex)
```

- `fromIndex` = V means input is V-addresses, output is I-addresses
- `fromIndex` = I means input is I-addresses, output is V-addresses

Two convenience wrappers:
- `vspanset2ispanset()` - V→I (what I-addresses does this V-range contain?)
- `ispan2vspanset()` - I→V (where in V-space is this I-address?)

### The `retrieverestricted()` Function (retrie.c:56-85)

Searches the enfilade for content matching address criteria:
- Given a V-range, find all I-addresses stored there
- Given an I-range, find all V-positions containing those I-addresses
- Returns a `context` list that can be converted to spans

This is the fundamental lookup operation that makes transclusion tracking possible.

### The `sporgl` Data Structure

A "sporgl" (span + orgl) tracks content origin:
```c
typedef struct {
    tumbler sporgladdress;  // Document ISA where content came from
    tumbler sporglorigin;   // I-address within that document
    tumbler sporglwidth;    // Width of content
} typesporgl;
```

Used when copying content to remember its provenance, enabling:
- Transclusion tracking
- Link endpoint resolution
- Version comparison

## Semantic Model Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Address Space                    │
├─────────────────────────────────────────────────────────────┤
│  V-Position 0.x                    V-Position 1.x           │
│  ┌─────────────┐                   ┌─────────────────────┐  │
│  │ Link        │                   │ Text Content        │  │
│  │ Subspace    │                   │                     │  │
│  │             │                   │                     │  │
│  │ I-addr:     │                   │ I-addr:             │  │
│  │ Link ISAs   │                   │ Permascroll addrs   │  │
│  │ (doc refs)  │                   │ (content identity)  │  │
│  └─────────────┘                   └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  I-Address Space      │
              │                       │
              │  • Permascroll:       │
              │    2.1.0.x.x.x        │
              │    (immutable chars)  │
              │                       │
              │  • Document ISAs:     │
              │    1.1.0.x.x.x        │
              │    (orgl references)  │
              └───────────────────────┘
```

## Related Findings

- **Finding 002**: Transclusion preserves immutable content identity (I-addresses)
- **Finding 004**: Links track content identity (uses same I-address mechanism)
- **Finding 007**: Versions preserve content identity (same transitive through I-addresses)
- **Finding 010**: Unified storage abstraction leaks (comprehensive list of where this breaks)
- **Finding 011**: Convention over enforcement design philosophy (why the system works this way)

## Related Bugs

- **Bug 009**: compare_versions crashes with links - root cause is that link subspace introduces I-addresses (link ISAs) that don't participate in text content comparison

## Related Files

- `do1.c:199-225` - docreatelink implementation
- `do2.c:151-167` - findnextlinkvsa (link positioning)
- `do2.c:48-61` - tumbler2spanset (ISA to ispan conversion)
- `correspond.c` - version comparison logic
- `orglinks.c:389-422` - permute and address conversion functions
- `retrie.c:56-85` - retrieverestricted enfilade lookup
