# FEBE Protocol: Literary Machines vs Actual Implementation

The FEBE protocol documented in Literary Machines 87.1 differs from what udanax-green actually implements. This document maps the spec to reality.

## Opcode Comparison

### Document Operations

| Operation | LM Spec | Backend | Status |
|-----------|---------|---------|--------|
| INSERT | 0 | 0 | ✓ Same |
| COPY (transclusion) | 2 | 2 | ✓ Same |
| REARRANGE (pivot/swap) | 3 | 3 | ✓ Same |
| DELETEVSPAN | 12 | 12 | ✓ Same |
| CREATENEWDOCUMENT | 11 | 11 | ✓ Same |
| CREATENEWVERSION | 13 | 13 | ✓ Same |
| APPEND | 19 | — | Not implemented |

### Retrieval Operations

| Operation | LM Spec | Backend | Status |
|-----------|---------|---------|--------|
| RETRIEVEDOCVSPANSET | 1 | 1 | ✓ Same |
| RETRIEVEV | 5 | 5 | ✓ Same |
| RETRIEVEDOCVSPAN | 14 | 14 | ✓ Same |
| SHOWRELATIONOF2VERSIONS | 10 | 10 | ✓ Same |
| FINDDOCSCONTAINING | 22 | 22 | ✓ Same |

### Link Operations (Different Opcodes)

| Operation | LM Spec | Backend | Notes |
|-----------|---------|---------|-------|
| MAKELINK / CREATELINK | 4 | 27 | Renamed, different opcode |
| RETRIEVEENDSETS | 26 | 28 | Different opcode |
| FINDLINKSFROMTOTHREE | 7 | 30 | Different opcode |
| FINDNUMOFLINKSFROMTOTHREE | 6 | 29 | Different opcode |
| FINDNEXTNLINKSFROMTOTHREE | 8 | 31 | Different opcode |
| FOLLOWLINK | — | 18 | Not in LM spec |

### Session/Admin Operations

| Operation | LM Spec | Backend | Notes |
|-----------|---------|---------|-------|
| QUIT | — | 16 | Not in LM spec |
| OPEN | — | 35 | Not in LM spec |
| CLOSE | — | 36 | Not in LM spec |
| XACCOUNT | — | 34 | Not in LM spec |
| CREATENODE_OR_ACCOUNT | — | 38 | Not in LM spec |

### Debug Operations (Backend Only)

| Operation | Opcode | Notes |
|-----------|--------|-------|
| SETDEBUG | 15 | Debug mode |
| SHOWENFILADES | 17 | Dump enfilades |
| EXAMINE | 20 | Examine internals |
| DUMPGRANFWIDS | 23 | Dump granf wids |
| JUSTEXIT | 24 | Exit immediately |
| IOINFO | 25 | I/O information |
| SETMAXIMUMSETUPSIZE | 32 | Config |
| PLAYWITHALLOC | 33 | Allocation testing |
| DUMPSTATE | 39 | Dump internal state |

## Operations Not Implemented

### APPEND (LM opcode 19)

**Spec:**
```
APPEND ::= <appendrequest> <text set> <doc id>
    returns <appendrequest>

Appends <text set> onto the end of the text space of the document.
```

**Status:** Not implemented in backend.

**Why it doesn't matter:** This is a convenience operation. The same result is achieved by:
1. Call `RETRIEVEDOCVSPANSET` to get document extent
2. Call `INSERT` at the end position

The backend never implemented this shortcut - you just use INSERT at the right position.

## Operations Added by Implementation

### FOLLOWLINK (opcode 18)

Not in Literary Machines spec. Retrieves the content at one end of a link.

```
FOLLOWLINK ::= <followlinkrequest> <link end> <link id>
    returns <followlinkrequest> <spec set>

<link end> ::= 0 (source) | 1 (target) | 2 (type)
```

### Session Management (opcodes 35, 36)

The spec assumes documents are always accessible. The implementation adds explicit open/close:

- **OPEN (35):** Open a document with access mode and conflict handling
- **CLOSE (36):** Close an open document

### Account Operations (opcodes 34, 38)

- **XACCOUNT (34):** Set current account for document creation
- **CREATENODE_OR_ACCOUNT (38):** Create a new node/account

## Client Coverage

The Python client (`febe/client.py`) implements:

| Client Method | Backend Opcode | Tested |
|---------------|----------------|--------|
| `insert()` | 0 | ✓ |
| `retrieve_vspanset()` | 1 | ✓ |
| `vcopy()` | 2 | ✓ |
| `pivot()` | 3 | ✓ |
| `swap()` | 3 | ✓ |
| `retrieve_contents()` | 5 | ✓ |
| `compare_versions()` | 10 | ✓ |
| `create_document()` | 11 | ✓ |
| `delete()` / `remove()` | 12 | ✓ |
| `create_version()` | 13 | ✓ |
| `retrieve_vspan()` | 14 | No |
| `quit()` | 16 | N/A |
| `follow_link()` | 18 | ✓ |
| `find_documents()` | 22 | ✓ |
| `create_link()` | 27 | ✓ |
| `retrieve_endsets()` | 28 | ✓ |
| `find_links()` | 30 | ✓ |
| `account()` | 34 | N/A |
| `open_document()` | 35 | ✓ |
| `close_document()` | 36 | ✓ |
| `create_node()` | 38 | No |
| `dump_state()` | 39 | Internal |

### Not in Client (but in backend)

| Operation | Opcode | Notes |
|-----------|--------|-------|
| FINDNUMOFLINKSFROMTOTHREE | 29 | Convenience: count of find_links results |
| FINDNEXTNLINKSFROMTOTHREE | 31 | Convenience: paginated find_links |
| NAVIGATEONHT | 9 | Unknown purpose |
| SOURCEUNIXCOMMAND | 21 | Shell escape (security risk) |

These are either convenience operations (count/pagination can be done client-side) or debug/admin features not needed for semantic testing.

## Summary

The Literary Machines spec is a historical document. The actual implementation:

1. **Moved link opcodes** to 27-31 range (from 4-8)
2. **Added session management** (open/close documents)
3. **Added FOLLOWLINK** for navigating links
4. **Never implemented APPEND** (use INSERT instead)
5. **Added debug/admin operations** not in spec

For golden tests, we test against the **actual backend**, not the LM spec. The client correctly uses the backend's opcodes.
