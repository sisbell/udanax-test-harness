# FEBE Client API Reference

Python client API for the Udanax Green backend (`febe/client.py`).

## Setup

```python
from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)

BACKEND = "path/to/backend/build/backend"
stream = PipeStream(f"{BACKEND} --test-mode")
session = XuSession(XuConn(stream))
session.account(Address(1, 1, 0, 1))  # Required before any operations
```

**PipeStream caveat:** Uses a named FIFO `pyxi.<PID>`. Only one PipeStream
per process — creating a second will conflict on the same FIFO name.

---

## Types

### Address

A tumbler address in the Udanax object space.

```python
Address(1, 1)           # From integers
Address(1, 1, 0, 1)     # Account address
Address("1.1.0.1")      # From string
```

### Offset

A width/distance between addresses.

```python
Offset(0, 5)            # Width of 5 in V-space
Offset(0, 1)            # Single character/unit
```

### Span

A contiguous range: start address + width.

```python
Span(Address(1, 1), Offset(0, 5))           # Start + width
Span(Address(1, 1), Address(1, 6))           # Start + end (exclusive)
span.start   # → Address
span.width   # → Offset
span.end()   # → Address (start + width)
```

### VSpec

A set of spans within one document. Returned by `retrieve_vspanset`.

```python
VSpec(docid, [span1, span2, ...])
vspec.docid  # → Address (document address)
vspec.spans  # → tuple of Span
```

### SpecSet

A set of VSpecs, possibly across multiple documents.

```python
SpecSet(VSpec(docid, [span]))    # From a single VSpec
SpecSet([vspec1, vspec2])        # From a list
```

---

## Session Control

### `account(acctid)`

Set the account for this session. **Must be called before any other operation.**

```python
session.account(Address(1, 1, 0, 1))
```

### `quit()`

Close the session and the backend connection.

```python
session.quit()
```

---

## Document Lifecycle

### `create_document()` → Address

Create a new empty document. Returns the document address.

```python
docid = session.create_document()
# docid is something like Address(1, 1, 0, 1, 0, 2)
```

### `open_document(docid, access, copy)` → Address

Open a document and return an **opened document handle**. The handle (not the
docid) is used for all subsequent operations on the document.

```python
opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
```

**Parameters:**

| Parameter | Values | Description |
|-----------|--------|-------------|
| `access` | `READ_ONLY` (1) | Read-only access |
|           | `READ_WRITE` (2) | Read-write access |
| `copy` | `CONFLICT_FAIL` (1) | Fail if document already open with conflicting mode |
|        | `CONFLICT_COPY` (2) | Open a copy if conflict |
|        | `ALWAYS_COPY` (3) | Always open a copy |

**Rules:**
- Use `READ_WRITE, CONFLICT_FAIL` when you need to edit the document
- Use `READ_ONLY, CONFLICT_COPY` when you need to read while the document
  may already be open for writing
- A document cannot be open READ_WRITE and READ_ONLY with `CONFLICT_FAIL`
  simultaneously — the second open will fail
- **Close the READ_WRITE handle before opening READ_ONLY** if using
  `CONFLICT_FAIL` for both

### `close_document(docid)`

Close an opened document handle.

```python
session.close_document(opened)
```

**Close ordering matters.** Close handles in an order that won't conflict
with subsequent opens. If you need to transition from READ_WRITE to READ_ONLY
with CONFLICT_FAIL, close the write handle first.

### `create_version(docid)` → Address

Create a new version of a document. Returns the new version's address.
The new version is a snapshot that shares I-addresses with the original.

```python
version = session.create_version(opened)
```

**Note:** Pass the opened document handle, not the raw docid.

---

## Content Editing

### `insert(docid, vaddr, strings)`

Insert text at a V-address. `strings` is a list of strings.

```python
session.insert(opened, Address(1, 1), ["Hello World"])
```

- Allocates fresh I-addresses in the granfilade
- Shifts existing content after `vaddr` by the inserted width
- For first insert into a new document, use `Address(1, 1)`

### `vcopy(docid, vaddr, specset)`

Copy (transclude) content from another document. **Preserves I-addresses**
(unlike insert, which always creates new ones).

```python
source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
source_vs = session.retrieve_vspanset(source_ro)
source_specs = SpecSet(VSpec(source_ro, list(source_vs.spans)))
session.vcopy(target_opened, Address(1, 1), source_specs)
```

**The source must be open** — you need a handle to build the SpecSet.

### `delete(docid, start, end)`

Delete content by start address and end/width.

```python
session.delete(opened, Address(1, 3), Offset(0, 5))    # Delete 5 chars at 1.3
session.delete(opened, Address(1, 3), Address(1, 8))    # Delete from 1.3 to 1.8
```

`end` can be an `Offset` (width) or an `Address` (exclusive end).
Internally constructs `Span(start, end)` and sends command 12.

### `remove(docid, span)`

Delete content by span. Same backend command as `delete`, different Python API.

```python
span = Span(Address(1, 3), Offset(0, 5))
session.remove(opened, span)
```

**`delete` vs `remove`:** Both send command 12. Use whichever is more
convenient:
- `delete(opened, addr, offset)` — when you know position and width
- `remove(opened, span)` — when you already have a Span (e.g., from
  `retrieve_vspanset`)

### `pivot(docid, start, pivot, end)`

Rearrange content: swap the portions before and after the pivot point.

```python
session.pivot(opened, Address(1, 1), Address(1, 4), Address(1, 8))
```

### `swap(docid, starta, enda, startb, endb)`

Swap two ranges of content.

```python
session.swap(opened, Address(1, 1), Address(1, 4),
                     Address(1, 6), Address(1, 9))
```

---

## Content Retrieval

### `retrieve_vspanset(docid)` → VSpec

Get all V-spans in a document. Returns a VSpec describing what content exists.

```python
vs = session.retrieve_vspanset(opened)
# vs.spans → tuple of Span objects
```

**Warning:** If the document has links, the returned spans include the
**link subspace** (addresses starting with `0.x`) before text spans
(starting with `1.x`). Filter accordingly:

```python
text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
```

### `retrieve_contents(specset)` → list

Retrieve the actual content (text/links) for a SpecSet.

```python
vs = session.retrieve_vspanset(opened)
specs = SpecSet(VSpec(opened, list(vs.spans)))
contents = session.retrieve_contents(specs)
# contents → ['Hello World'] (list of strings and/or link addresses)
```

**Common pattern:**

```python
vs = session.retrieve_vspanset(opened)
specs = SpecSet(VSpec(opened, list(vs.spans)))
contents = session.retrieve_contents(specs)
```

### `retrieve_endsets(specset)` → (source, target, type)

Retrieve the three endsets (source, target, type) for links in the given range.

```python
link_spans = [s for s in vs.spans if s.start.digits[0] == 0]
specs = SpecSet(VSpec(opened, link_spans))
source_endset, target_endset, type_endset = session.retrieve_endsets(specs)
```

Returns three SpecSets.

### `retrieve_vspan(docid)` → VSpan

Get the single bounding V-span for a document. Less useful than
`retrieve_vspanset` — prefer the latter.

```python
vspan = session.retrieve_vspan(opened)
```

---

## Links

### `create_link(docid, sourcespecs, targetspecs, typespecs)` → Address

Create a link between content. Returns the link address.

```python
source_specs = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
target_specs = SpecSet(VSpec(other_opened, [Span(Address(1, 1), Offset(0, 3))]))
type_specs = SpecSet([JUMP_TYPE])

link_id = session.create_link(opened, source_specs, target_specs, type_specs)
```

**Parameters:**
- `docid`: The opened handle of the document that will "own" the link
- `sourcespecs`: SpecSet identifying the link source content
- `targetspecs`: SpecSet identifying the link target content
- `typespecs`: SpecSet identifying the link type (use `JUMP_TYPE`, etc.)

**Available link types:**
- `JUMP_TYPE` — hyperlink/jump
- `QUOTE_TYPE` — quotation
- `FOOTNOTE_TYPE` — footnote
- `MARGIN_TYPE` — margin note

### `find_links(sourcespecs, targetspecs=None, typespecs=None, homedocids=None)` → list

Search for links matching the given criteria. Returns a list of link addresses.

```python
search_specs = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
links = session.find_links(search_specs)
```

Optional parameters narrow the search:
- `targetspecs` — filter by target content
- `typespecs` — filter by link type
- `homedocids` — filter by home document (Bug 015: this filter has no effect)

### `follow_link(linkid, linkend)` → SpecSet

Follow a link to retrieve one of its three endsets.

```python
source_content = session.follow_link(link_id, LINK_SOURCE)
target_content = session.follow_link(link_id, LINK_TARGET)
link_type = session.follow_link(link_id, LINK_TYPE)
```

`linkend` is `LINK_SOURCE` (1), `LINK_TARGET` (2), or `LINK_TYPE` (3).

---

## Version Comparison

### `compare_versions(specseta, specsetb)` → list

Compare two document versions to find shared content (same I-addresses).

```python
ver_ro = session.open_document(version, READ_ONLY, CONFLICT_COPY)
orig_ro = session.open_document(original, READ_ONLY, CONFLICT_COPY)

vs_ver = session.retrieve_vspanset(ver_ro)
vs_orig = session.retrieve_vspanset(orig_ro)

spec_ver = SpecSet(VSpec(ver_ro, list(vs_ver.spans)))
spec_orig = SpecSet(VSpec(orig_ro, list(vs_orig.spans)))

shared = session.compare_versions(spec_ver, spec_orig)
# shared → [(VSpan_in_ver, VSpan_in_orig), ...]
```

Returns a list of (VSpan, VSpan) tuples showing which ranges in each
document share I-addresses.

### `find_documents(specset)` → list

Find all documents containing the given I-addresses.

```python
docs = session.find_documents(specset)
# docs → [Address(...), Address(...), ...]
```

**Note:** May return stale results — documents that once contained the
I-addresses but no longer do (Finding 057: spanfilade is write-only).

---

## Administration

### `create_node(acctid)` → Address

Create a new node in the account tree.

```python
node = session.create_node(Address(1, 1, 0, 1))
```

---

## Common Patterns

### Full document read

```python
docid = session.create_document()
opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
session.insert(opened, Address(1, 1), ["Hello World"])

vs = session.retrieve_vspanset(opened)
specs = SpecSet(VSpec(opened, list(vs.spans)))
contents = session.retrieve_contents(specs)
# contents → ['Hello World']

session.close_document(opened)
```

### Delete all content

```python
vs = session.retrieve_vspanset(opened)
for span in vs.spans:
    session.remove(opened, span)
```

Or if you know the full span:

```python
vs = session.retrieve_vspanset(opened)
session.remove(opened, vs.spans[0])  # If single contiguous span
```

### Transclude between documents

```python
# Source must be open for reading
source_ro = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
source_vs = session.retrieve_vspanset(source_ro)
source_specs = SpecSet(VSpec(source_ro, list(source_vs.spans)))

# Target must be open for writing
target_rw = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
session.vcopy(target_rw, Address(1, 1), source_specs)

session.close_document(source_ro)
session.close_document(target_rw)
```

### Read-write to read-only transition

```python
# If using CONFLICT_FAIL, close write handle before opening read-only
opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
session.insert(opened, Address(1, 1), ["text"])
session.close_document(opened)

read = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
# ... read operations ...
session.close_document(read)
```

Or use `CONFLICT_COPY` for the read-only open to avoid the conflict entirely.

---

## Known Bugs and Limitations

| Bug | Description | Workaround |
|-----|-------------|------------|
| 015 | `find_links` homedocids filter has no effect | Filter client-side |
| 016 | Link count limit causes crash | Varies with doc count |
| 017 | Zero-width link endpoint crashes | Use non-zero spans |
| 018 | Large insert crashes (~10KB limit) | Split into smaller inserts |

See `bugs/README.md` for the full index.

---

## FEBE Protocol Commands

For reference, the underlying protocol command codes:

| Code | Method | Description |
|------|--------|-------------|
| 0 | `insert` | Insert text |
| 1 | `retrieve_vspanset` | Get V-spans |
| 2 | `vcopy` | Copy/transclude |
| 3 | `pivot` / `swap` | Rearrange |
| 5 | `retrieve_contents` | Get content |
| 10 | `compare_versions` | Compare versions |
| 11 | `create_document` | Create document |
| 12 | `delete` / `remove` | Delete content |
| 13 | `create_version` | Create version |
| 14 | `retrieve_vspan` | Get single V-span |
| 16 | `quit` | End session |
| 18 | `follow_link` | Follow link end |
| 22 | `find_documents` | Find docs by I-address |
| 27 | `create_link` | Create link |
| 28 | `retrieve_endsets` | Get link endsets |
| 30 | `find_links` | Search links |
| 34 | `account` | Set account |
| 35 | `open_document` | Open document |
| 36 | `close_document` | Close document |
| 38 | `create_node` | Create account node |
| 39 | `dump_state` | Dump internal state |
