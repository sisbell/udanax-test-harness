# Finding 0013: The Sporgl - Content Provenance Tracking

**Date:** 2026-01-30
**Category:** Architecture / Data Structures

## Summary

The **sporgl** (span + orgl) is a data structure that tracks content provenance - where content came from. It's fundamental to transclusion tracking, link indexing, and version comparison.

## The Structure

From xanadu.h:115-121:
```c
typedef struct structsporgl {
    struct structsporgl *next;     // Linked list pointer
    typeitemid itemid;             // Type identifier (SPORGLID)
    tumbler sporglorigin;          // I-address (content identity)
    tumbler sporglwidth;           // Width of content span
    typeisa sporgladdress;         // Source document ISA
} typesporgl;
```

## What It Represents

A sporgl answers: **"This content (I-address range) came from this document."**

| Field | Meaning | Example |
|-------|---------|---------|
| `sporglorigin` | Start I-address in permascroll | `2.1.0.5.0.100` |
| `sporglwidth` | Width of content span | `0.15` (15 characters) |
| `sporgladdress` | Document where content resides | `1.1.0.1.0.1` |

## Why It Exists

### Problem: Content Identity vs. Location

In Xanadu:
- **I-address** = permanent content identity (position in permascroll)
- **V-address** = location within a document (can change)
- **Document ISA** = which document contains it

When you transclude content, you need to know:
1. What content? → I-address
2. How much? → width
3. Where from? → document ISA

A sporgl packages all three.

### The Name

**Sporgl** = **Sp**an + **Orgl**
- **Span**: I-address range (origin + width)
- **Orgl**: The document orgl it references

## How It's Used

### 1. Converting VSpecs to Sporgls

When you have a document reference (VSpec with V-addresses), convert to sporgls:

```c
// sporgl.c:35-65
typesporglset *vspanset2sporglset(taskptr, docisa, vspanset, sporglsetptr, type)
{
    // For each vspan in the document:
    for (; vspanset; vspanset = vspanset->next) {
        // Convert V-addresses to I-addresses
        vspanset2ispanset(taskptr, orgl, vspanset, &ispanset);

        // For each I-span, create a sporgl
        for (; ispanset; ispanset = ispanset->next) {
            sporglset->sporgladdress = docisa;     // Where from
            sporglset->sporglorigin = ispanset->stream;  // I-address
            sporglset->sporglwidth = ispanset->width;    // Width
        }
    }
}
```

### 2. Link Endpoint Indexing

Links are indexed in spanf using sporgls:

```c
// do2.c:116-128
bool insertendsetsinspanf(taskptr, spanf, linkisa,
                          fromsporglset, tosporglset, threesporglset)
{
    insertspanf(taskptr, spanf, linkisa, fromsporglset, LINKFROMSPAN);
    insertspanf(taskptr, spanf, linkisa, tosporglset, LINKTOSPAN);
    // ...
}
```

The spanf index maps: **I-address → links that reference that content**

### 3. Link Endpoint Retrieval

When following a link, convert sporgl back to specset:

```c
// sporgl.c:97+
bool linksporglset2specset(taskptr, homedoc, sporglset, specsetptr, type)
{
    // Convert each sporgl to a vspec
    // sporgl.sporgladdress → document
    // sporgl.sporglorigin/width → I-span → V-span
}
```

### 4. Content Copying (docopy)

When copying content, the flow is:
```
Source VSpec → Sporgls → insertpm into destination
```

The sporgl carries the provenance through the copy.

## Data Flow Diagram

```
┌─────────────┐     vspanset2sporglset     ┌─────────────┐
│   VSpec     │ ─────────────────────────► │   Sporgl    │
│ (V-address) │                            │(I-addr+doc) │
└─────────────┘                            └─────────────┘
       │                                          │
       │ retrieve_contents                        │ insertspanf
       ▼                                          ▼
┌─────────────┐                            ┌─────────────┐
│   Content   │                            │   Spanf     │
│   (bytes)   │                            │ (link index)│
└─────────────┘                            └─────────────┘
```

## Key Operations

| Operation | Input | Output | Purpose |
|-----------|-------|--------|---------|
| `specset2sporglset` | VSpec/ISpan | Sporglset | Add provenance to spans |
| `vspanset2sporglset` | VSpanset + docisa | Sporglset | Convert V→I with provenance |
| `linksporglset2specset` | Sporglset | VSpec | Convert I→V for display |
| `sporglset2linkset` | Sporglset | Links | Find links for content |
| `unpacksporgl` | Sporgl | origin, width, doc | Extract fields |

## The Union Type

Sporgls can be interchanged with ispans in some contexts:

```c
// xanadu.h:123-127
typedef union {
    typeispan xxxxispan;
    typesporgl xxxxsporgl;
} typesporglitem;
typedef typesporglitem * typesporglset;
```

This allows code to handle both "anonymous" I-spans and "provenanced" sporgls.

## Implications

### For Transclusion

When you vcopy from document A to document B:
1. A's V-span → sporgl (I-address + "from A")
2. sporgl inserted into B at new V-position
3. B now knows content came from A

### For Links

When you create a link from A to B:
1. A's endpoint → sporgl (I-address + "in A")
2. B's endpoint → sporgl (I-address + "in B")
3. Spanf indexes both sporgls → link

### For Version Comparison

When comparing versions:
1. Both documents' content → sporgls
2. Intersect by I-address (sporgls with same sporglorigin)
3. Result shows shared content provenance

## Related

- **Finding 0009:** Document address space (V-addresses)
- **Finding 0012:** Dual enfilade architecture (spanf uses sporgls)
- **Finding 0002:** Transclusion content identity (sporgl tracks this)

## Files

| File | Purpose |
|------|---------|
| `xanadu.h:115-127` | Structure definition |
| `sporgl.c` | All sporgl operations |
| `spanf1.c` | Uses sporgls for link indexing |
| `correspond.c` | Uses sporgls for version comparison |
