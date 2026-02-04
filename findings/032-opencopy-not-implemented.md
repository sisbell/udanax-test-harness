# Finding 032: OPENCOPY Does Not Exist in udanax-green

**Date discovered:** 2026-02-03
**Category:** interface, versions, documentation

## Summary

The FEBE interface documentation lists "OPENCOPY" as one of 17 operations, but this command does not exist in the udanax-green backend. Version creation is handled by CREATENEWVERSION (command 13), which performs an atomic create-and-copy operation.

## Key Behaviors Verified

### 1. No OPENCOPY Command

Searching the backend source code reveals no OPENCOPY command:

```c
// From requests.h - all defined commands:
#define CREATENEWDOCUMENT 11
#define CREATENEWVERSION 13
#define OPEN 35
#define COPY 2
// No OPENCOPY defined
```

The `requestfns` array in init.c maps all implemented commands. OPENCOPY is absent.

**Evidence:** Backend source code at `backend/requests.h` and `backend/init.c`

### 2. CREATENEWVERSION Does Atomic Create + Copy

The `docreatenewversion` function in `do1.c` performs:
1. Creates a new document orgl with appropriate hint
2. Retrieves the source document's vspanset
3. Uses `docopyinternal` to copy all content (preserving I-addresses)
4. Returns the new document address

```c
bool docreatenewversion(typetask *taskptr, typeisa *isaptr, typeisa *wheretoputit, typeisa *newisaptr)
{
    // Create new orgl under appropriate parent
    if (!createorglingranf(taskptr, granf, &hint, newisaptr)) {
        return (FALSE);
    }

    // Get source document's content span
    if (!doretrievedocvspanfoo (taskptr, isaptr, &vspan)) {
        return FALSE;
    }

    // Copy content (sharing I-addresses, not duplicating)
    docopyinternal(taskptr, newisaptr, &vspan.stream, &vspec);

    return (TRUE);
}
```

**Test:** `golden/versions/create_version.json`

### 3. Version Addresses Show Hierarchy

Version addresses are subordinate to the source document:
- Original: `1.1.0.1.0.1`
- Version: `1.1.0.1.0.1.1`
- Version of version: `1.1.0.1.0.1.1.1`

This is NOT the case for CREATEDOCUMENT + COPY:
- Doc 1: `1.1.0.1.0.1`
- Doc 2: `1.1.0.1.0.2` (sibling, not subordinate)

**Test:** `golden/versions/version_chain.json`

### 4. Content is Shared (Same I-addresses)

When comparing a version with its source, `compare_versions` finds shared content because they reference the same I-space addresses:

```json
{
  "op": "compare_versions",
  "result": [
    {
      "a": { "start": "1.1", "width": "0.31" },
      "b": { "start": "1.1", "width": "0.31" }
    }
  ]
}
```

**Test:** `golden/versions/compare_versions.json`

### 5. Transclusions Are Preserved Through Versioning

If document A transcludes from B, and you create a version of A, the version also shares I-addresses with B:

```json
{
  "op": "compare",
  "docs": ["version", "source"],
  "shared": [
    { "version": {"start": "1.9"}, "source": {"start": "1.1"} }
  ],
  "comment": "Version should share 'Shared' with source (transclusion preserved)"
}
```

**Test:** `golden/versions/version_preserves_transclusion.json`

### 6. Links Are Accessible From Versions

Finding links from a version returns the same link addresses as from the original:

```json
{
  "op": "find_links",
  "from": "version",
  "result": ["1.1.0.1.0.1.0.2.1"],
  "comment": "Do links transfer to version? (tests link-to-content binding)"
}
```

This works because links attach to I-addresses, and the version shares those I-addresses.

**Test:** `golden/versions/version_with_links.json`

## Implications

### How CREATENEWVERSION Differs from CREATEDOCUMENT + COPY

| Aspect | CREATENEWVERSION | CREATEDOCUMENT + COPY |
|--------|------------------|----------------------|
| Address hierarchy | Subordinate to source | Sibling to source |
| Atomicity | Single operation | Two operations |
| Version tracking | Backend knows relationship | No inherent relationship |
| Empty source | Handles correctly | COPY has nothing to copy |

### The "OPENCOPY" Documentation

The EWD-028 FEBE interface document lists OPENCOPY but this appears to be:
- A conceptual operation from specification
- Never implemented in udanax-green
- Functionally equivalent to CREATENEWVERSION

## Related Tests

- `golden/versions/create_version.json`
- `golden/versions/version_chain.json`
- `golden/versions/compare_versions.json`
- `golden/versions/version_preserves_transclusion.json`
- `golden/versions/version_with_links.json`
