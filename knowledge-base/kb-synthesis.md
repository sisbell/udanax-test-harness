# Synthesis Knowledge Base
<!-- last-finding: 0078 -->

> Implementation knowledge about udanax-green, synthesized for specification writing.
> Cite entries as `[SS-ADDRESS-SPACE]`, `[ST-INSERT]`, `[FC-SUBSPACE]`, etc.

---

## State Structure

> What the state IS — types, address spaces, data model

### SS-TUMBLER

Tumblers are the fundamental address type. A tumbler is stored as a sign bit, a short exponent, and a fixed-length mantissa of `NPLACES` (16) digits. Zeros within the mantissa act as hierarchical separators — `1.1.0.2.0.5` means node `1.1`, account `1.1.0.2`, item `1.1.0.2.0.5`. The `.0.` field structure is convention, not enforcement; the backend treats tumblers as unconstrained digit sequences.

Tumblers use sign-magnitude representation. Subtraction is closed: `tumblersub(a, b)` always produces a valid tumbler, but may return a negative result when `b > a`. Negative tumblers sort before all positive tumblers and zero in `tumblercmp`. The `strongsub` function has an exponent guard: when `b.exp < a.exp`, it returns `a` unchanged — subtraction across exponent boundaries is a no-op.

Two tumblers are equal iff their sign, exponent, and all 16 mantissa digits match (after `tumblerjustify`). `tumblerlength()` returns significant digits: `nstories(t) - t.exp`.

**Why it matters for spec:** The formal type is `Tumbler = {sign: bool, exp: int, mantissa: seq<nat>[16]}`. The total order is: negative < zero < positive. The exponent guard in `strongsub` means operations with width tumblers at lower exponents than target displacements are no-ops — this is the mechanism behind subspace isolation in DELETE [FC-SUBSPACE].

**Code references:**
- `common.h:59-65` — struct definition
- `tumble.c:24-36` — `tumblereq` (equality)
- `tumble.c:72-85` — `tumblercmp` (total order)
- `tumble.c:406-440` — `tumblersub` (subtraction, sign negation)
- `tumble.c:534-547` — `strongsub` (exponent guard at line 544)
- `tumble.c:599-623` — `tumblerincrement`

**Example:**
```
Tumbler 1.1.0.2.0.5: exp=0, mantissa=[1,1,0,2,0,5,0,...,0]

strongsub(a={exp=0, mant=[2,1]}, b={exp=-1, mant=[3]}):
  b.exp (-1) < a.exp (0) → returns a unchanged: 2.1

tumblersub(1.2, 0.10):
  b > a in absolute → Result: sign=1, magnitude=0.8 (i.e., -0.8)
```

**Provenance:** Findings 0001, 0031, 0053, 0055

---

### SS-ADDRESS-SPACE

Documents have a multi-subspace virtual address space. Text content occupies subspace `1.x`, links occupy subspace `2.x` (stored as `0.2.x` internally, with the leading zero digit indicating subspace 2). A third subspace `3.x` is reserved for types. These subspaces are independent: insertions in one subspace do not renumber positions in the other [FC-SUBSPACE].

The document address hierarchy follows a tumbler convention: `Node.0.User.0.Doc.0.Element`. Document-level vs. element-level addressing is a predicate, not a type distinction. Document addresses like `1.1.0.1.0.2` have no element field; element addresses like `1.1.0.1.0.1.0.2.1` specify positions within a document.

Each document maintains a POOM (per-document orgl) that maps V-addresses (virtual positions) to I-addresses (immutable content identity). The POOM is a 2D enfilade indexed by both V-address and I-address dimensions. The V-dimension determines document order; the I-dimension identifies content origin.

**Why it matters for spec:** The address space model requires: `VAddress = Tumbler` restricted to positive values, `Subspace(v) = first_digit(v)` as a computed predicate, and the independence property `∀ op ∈ {INSERT, DELETE}: affects_only(op, subspace(op.target))`.

**Code references:**
- `do2.c:151-167` — `findnextlinkvsa` (link address allocation)
- `do1.c:199-225` — `docreatelink` (link creation in subspace 2)
- `orglinks.c:75-134` — `insertpm` (POOM entry creation)
- `orglinks.c:404-422` — `permute` (bidirectional V↔I mapping)

**Example:**
```
Document 1.1.0.1.0.1:
  V-address 1.1     → I-address 1.1.0.1.0.1.0.1.5   (text "Hello")
  V-address 1.6     → I-address 1.1.0.1.0.1.0.1.10  (text "World")
  V-address 0.2.1   → I-address 1.1.0.1.0.1.0.2.1   (link orgl)

Subspaces are independent:
  INSERT at V=1.3 shifts 1.6→1.11 but 0.2.1 is unchanged
```

**Provenance:** Findings 0009, 0010, 0031, 0038

---

### SS-DUAL-ENFILADE

The system maintains two global enfilades with distinct purposes:

1. **Granfilade** (`typegranf`): Content storage. A 1D B-tree indexed by I-address. Stores the permascroll — all content ever created. Append-only; content is never deleted from the granfilade.

2. **Spanfilade** (`typespanf`): Link search index. A 2D B-tree indexed by I-address span and document origin. Used for `find_links`, `retrieve_endsets`, and `find_documents_containing`. Write-only — entries are added but never removed, even when the referenced content is deleted from a document's POOM.

Each document also has a **POOM** (orgl): a 2D B-tree mapping V-addresses to I-addresses. The POOM is the sole locus of destructive mutation. INSERT, DELETE, COPY, and REARRANGE modify POOMs; the granfilade and spanfilade only grow.

The three-layer mutability model:
- Granfilade: **immutable** (append-only)
- Spanfilade: **immutable** (write-only, no delete function exists)
- POOMs: **mutable** (INSERT, DELETE, REARRANGE modify in-place)

**Why it matters for spec:** The state model has three tiers with different update rules. The spec must model granfilade and spanfilade as monotonically growing sets, while POOMs are mutable maps. Frame conditions differ by tier: operations never shrink the granfilade or spanfilade.

**Code references:**
- `xanadu.h:13,15` — type constants for granf/spanf
- `entexit.c:44-45` — initialization of both enfilades
- `spanf1.c:15-53` — `insertspanf` (write-only)
- `credel.c:492-516` — `createenf` (initial tree creation)
- `orglinks.c:145-152` — `deletevspanpm` (POOM mutation, no spanf cleanup)

**Provenance:** Findings 0012, 0057, 0072

---

### SS-CONTENT-IDENTITY

All content is stored in the granfilade with immutable I-addresses (identity addresses). When text is inserted, it receives a fresh I-address that never changes. Identical text created at different times or in different documents gets different I-addresses — identity is by origin, not by value.

Transclusion (COPY) creates new V→I mappings in the target document pointing to the same I-addresses as the source. This means multiple documents can share the same content identity without duplicating storage.

The backend stores raw bytes with no encoding interpretation. Each byte occupies one I-space position. UTF-8 works by accident — the backend is byte-opaque.

**Why it matters for spec:** Content identity is the foundation of link discovery, version comparison, and transclusion semantics. The formal model needs: `IAddress` as a unique identifier assigned at creation time, `content_of(i) = content_of(i)` permanently (immutability), and `create_new ≠ copy` (creation allocates new I-addresses; copy reuses existing ones).

**Code references:**
- `do1.c:27-43` — `doinsert` (always allocates fresh I-addresses)
- `do1.c:45-65` — `docopy` (reuses source I-addresses in target)
- `granf2.c:158-181` — `findisatoinsertmolecule` (I-address allocation)

**Example:**
```
Session:
  INSERT doc1 "Hello"  → I-addr 1.1.0.1.0.1.0.1.1 (5 bytes, contiguous)
  INSERT doc1 "World"  → I-addr 1.1.0.1.0.1.0.1.6 (next available)
  COPY doc1[1..5] → doc2  → doc2 V:1.1 maps to I:1.1.0.1.0.1.0.1.1 (shared!)
  INSERT doc2 "Hello"  → I-addr 1.1.0.1.0.2.0.1.1 (different identity!)

doc1 and doc2 share I-addresses for the copied "Hello"
doc2's separately inserted "Hello" has distinct identity
```

**Provenance:** Findings 0002, 0018, 0034

---

### SS-IADDRESS-ALLOCATION

I-address allocation is monotonic, per-document, and stateless. There is no global counter. Instead, allocation queries the granfilade for the current maximum I-address under a given parent and increments by 1.

For content (molecules): `findisatoinsertmolecule` searches within the document's I-address range and returns max+1.

For documents/links (non-molecules): `findisatoinsertnonmolecule` searches with a bounded upper limit (e.g., `docISA.2.3` for links) and returns max+1.

Sequential single-character inserts produce contiguous I-addresses that consolidate into one I-span, matching bulk-insert behavior. But CREATELINK advances the allocation counter past the text range, creating gaps — subsequent text inserts receive non-contiguous I-addresses.

CREATENEWVERSION does NOT advance content allocation. It only allocates a document address (via `findisatoinsertnonmolecule`) and copies SPAN metadata. Document and content allocation are separate mechanisms.

Version addresses are allocated as children of the source document: `docISA.0.1` for the first version, `docISA.0.2` for the second. When the versioning user doesn't own the source document, the version is allocated under their account instead.

**Why it matters for spec:** Allocation is a pure function of current granfilade state: `alloc(parent, bound) = max(existing under parent within bound) + 1`. The stateless query-and-increment model means there is no `Σ.next` counter to track.

**Code references:**
- `granf2.c:158-181` — `findisatoinsertmolecule` (content allocation)
- `granf2.c:203-242` — `findisatoinsertnonmolecule` (document/link allocation)
- `granf2.c:255-278` — `findpreviousisagr` (bounded tree traversal for max)
- `do1.c:264-303` — `docreatenewversion` (version address allocation)
- `do2.c:78-84` — `makehint` (ownership-sensitive allocation hint)

**Example:**
```
Document 1.1.0.1.0.1:
  INSERT "AB"  → I-addr .0.1.1 (content, 2 bytes contiguous)
  INSERT "CD"  → I-addr .0.1.3 (next available content)
  CREATELINK   → I-addr .0.2.1 (link, separate subspace)
  INSERT "EF"  → I-addr .0.1.5 (content, non-contiguous due to link gap)

  CREATENEWVERSION → doc 1.1.0.1.0.1.0.1 (child of source)
  CREATENEWVERSION → doc 1.1.0.1.0.1.0.2 (second child)
```

**Provenance:** Findings 0021, 0025, 0033, 0061, 0063, 0065, 0068, 0077

---

### SS-POOM-BOTTOM-CRUM

POOM bottom crums store the V→I mapping for a contiguous span. Each bottom crum contains a V-displacement (position in document), V-width (span length in V-space), I-displacement (content identity address), and I-width (span length in I-space).

V-width and I-width represent the same logical span width but are encoded with different tumbler exponents. The V-width exponent is computed from the V-address tumbler length; the I-width is copied directly from I-space. Comparisons between V-space and I-space coordinates must be by value, not by tumbler representation.

For granfilade bottom crums, occupancy is always exactly 1 (`MAXBCINLOAF=1`), making the height-1 layer a 1:1 pass-through. This is because "text must fit" in a single leaf node.

When copied content is contiguous with existing I-addresses in the target POOM, `isanextensionnd` detects the adjacency (reach == origin) and extends the existing mapping rather than creating a new entry. No duplicate checking occurs at insertion time.

**Why it matters for spec:** POOM entries are the atomic unit of the V→I mapping. The extension behavior means logically distinct copies may silently merge into a single POOM entry if they happen to be I-address-contiguous.

**Code references:**
- `orglinks.c:100-117` — `insertpm` bottom crum creation
- `orglinks.c:26-30` — V-width computation with `tumblerlength`
- `insertnd.c:293-301` — `isanextensionnd` (extension detection)
- `enf.h:26-28` — `MAXBCINLOAF=1`, `MAXUCINLOAF=6`, `MAX2DBCINLOAF=4`

**Provenance:** Findings 0046, 0060, 0070, 0076

---

### SS-SPAN-SPECSET

A VSpec is `(document_id, start_position, width)` — a contiguous range within one document's V-space. A SpecSet is an ordered collection of VSpecs, enabling multi-span, multi-document operations.

A Sporgl (span + orgl) packages content identity (I-address + width) with source document identity. The sporgl is the bridge between V-space operations and I-space content identity. `vspanset2sporglset` converts V-addresses to sporgls by walking the POOM; `linksporglset2specset` converts back.

DOCISPAN entries in the spanfilade track which documents contain which I-address ranges. Each contiguous I-span creates exactly one spanfilade entry, making storage O(operation count) not O(total bytes). INSERT creates DOCISPAN entries (via `insertspanf`); APPEND does not (the `insertspanf` call is commented out), making APPEND content undiscoverable via `find_documents`.

**Why it matters for spec:** SpecSet is the primary data exchange type for all multi-span operations. The sporgl mediates between the V-space and I-space views of content. DOCISPAN granularity determines findability.

**Code references:**
- `xanadu.h:115-121` — sporgl structure
- `sporgl.c:35-65` — `vspanset2sporglset` (V→sporgl conversion)
- `sporgl.c:97+` — `linksporglset2specset` (sporgl→specset)
- `spanf1.c:15-53` — `insertspanf` (one entry per I-span)
- `do1.c:27-43` — `doinsert` calls `insertspanf`; `doappend` does not

**Provenance:** Findings 0003, 0013, 0036, 0047

---

### SS-LINK-STRUCTURE

Links are permanent, immutable objects stored in the granfilade. Each link has three endsets: source (from), target (to), and type. Endsets contain I-address spans — they reference content by identity, not by position.

A link's address is allocated in the document's link subspace: `docISA.0.2.N` where N increments per document. The link's type is registered at `1.0.2.x` in the global type namespace. Link allocation is per-document — each document has an independent link counter.

Links are stored in two places: (1) the link orgl is created in the granfilade, and (2) the link's endset I-spans are indexed in the spanfilade for discovery. The POOM gets a V→I entry for the link orgl at the document's link subspace position.

There is no link deletion operation. Links persist in all storage layers permanently. An "orphaned" link (whose endpoint content has been deleted from all V-streams) becomes undiscoverable via `find_links` but remains accessible by link ID and is re-discoverable if its endpoint content reappears via transclusion.

**Why it matters for spec:** Links are immutable first-class objects with content-identity-based endpoints. The spec must model links as permanent entries in both granfilade and spanfilade. Discovery is via I-address overlap, not V-address proximity.

**Code references:**
- `do1.c:199-225` — `docreatelink` (creates link orgl + spanf entries)
- `do2.c:116-128` — `insertendsetsinspanf` (indexes endsets)
- `sporgl.c:67-95` — `link2sporglset` (extracts I-addresses from link)
- `do2.c:151-167` — `findnextlinkvsa` (per-document link counter)

**Provenance:** Findings 0004, 0005, 0024, 0037, 0065

---

### SS-ENFILADE-BTREE

Enfilades are B-trees with hard-coded branching parameters: `MAXUCINLOAF=6` (upper crum max children), `MAX2DBCINLOAF=4` (2D bottom crum max children), `MAXBCINLOAF=1` (GRAN bottom crum max children). The `toomanysons` threshold triggers splitting.

The split algorithm (`splitcrumupwards`) has two cases: if the overfull node is the root (`isfullcrum`), it calls `levelpush` to increase tree height before splitting; otherwise it splits in-place, increasing sibling width. `levelpull` (the reverse — reducing height when underfull) is **disabled**: it returns 0 immediately with a comment noting it's disabled since development.

As a consequence, trees only grow in height — they never shrink. After DELETE removes all content, the tree retains intermediate nodes from prior growth. Empty trees are structurally taller than freshly created empty trees.

In 2D enfilades (POOM, SPAN), root displacement is NOT zero — it tracks the minimum child address via `setwispnd`. Children store relative coordinates. The grasp (logical position) at root equals offset + displacement.

The 2D rebalancing algorithm (`recombinend`) sorts children by the diagonal sum of their two displacement coordinates, then merges between pairs along this ordering. Unlike the 1D case, a single receiver can absorb multiple donors in one pass (the `break` statements are commented out).

**Why it matters for spec:** The spec should NOT assert tree minimality as an invariant. EN-4 (2≤children≤M) is violated for height-1 granfilade nodes where M_b=1. The representation independence property [INV-ENFILADE-CONFLUENCE] still holds — all valid tree shapes produce identical query results.

**Code references:**
- `enf.h:26-28` — branching constants
- `split.c:16-44` — `splitcrumupwards`
- `genf.c:263-294` — `levelpush` (height increase)
- `genf.c:318-342` — `levelpull` (disabled, returns 0)
- `recombine.c:104-131` — `recombinend` (2D merge with commented-out breaks)
- `recombine.c:278-311` — diagonal ordering sort
- `wisp.c:171-228` — `setwispnd` (root displacement tracking)

**Provenance:** Findings 0058, 0060, 0066, 0070, 0071, 0073

---

### SS-PERSISTENCE

Udanax-green uses lazy write-back caching with no transaction log, no `fsync`, and no crash recovery mechanism. The "grim reaper" (`grimlyreap`) evicts dirty cache entries to disk when memory pressure requires it. `writeenfilades` flushes all modified nodes at session end but without ordered writes or durability guarantees.

Durability boundary: data is durable after a clean `writeenfilades` call. Process crash at any other point leaves the disk enfilade in an inconsistent state with no recovery path.

Operations on one enfilade can trigger cache eviction affecting another enfilade through the shared grim reaper mechanism — loading spanfilade nodes for a link search may evict granfilade text atoms.

**Why it matters for spec:** The spec should model operation-level atomicity (guaranteed by single-threaded event loop [INV-ATOMICITY]) but NOT crash-recovery durability. Session-level persistence is best-effort.

**Code references:**
- `enf.h:35,59` — modified flag tracking
- `credel.c:106-162` — `grimlyreap` (cache eviction)
- `disk.c:300-338` — `actuallywriteloaf` (no fsync)
- `corediskout.c:68-88` — `writeenfilades` (session-end flush)

**Provenance:** Findings 0059

---

### SS-QUERY-OPERATIONS

Five query operations provide read-only access to system state:

1. **RETRIEVEDOCVSPAN**: Returns the raw root width of a document. Broken for documents with links — returns a bounding span covering both subspaces.
2. **RETRIEVEDOCVSPANSET**: Correctly separates text and link subspaces into distinct VSpecs. The preferred retrieval operation.
3. **RETRIEVEENDSETS**: Searches the spanfilade for a link's three endsets (source, target, type). Returns I-addresses; unreferenced addresses are silently filtered during I→V conversion.
4. **FINDNUMOFLINKSFROMTOTHREE** / **FINDNEXTNLINKSFROMTOTHREE**: Link search with cursor-based pagination. Performs full materialization into a transient list, then truncates — no incremental optimization.
5. **FINDDOCSCONTAINING**: Returns documents sharing I-addresses with a given specset, revealing transitive transclusion chains.

All query operations are read-only — no state transitions or side effects. `compare_versions` (SHOWRELATIONOF2VERSIONS) is also read-only: it returns shared span pairs filtered by specset boundaries.

**Why it matters for spec:** These are pure functions of current state. The spec can model them as mathematical functions over the state model without pre/postconditions on mutation.

**Code references:**
- `orglinks.c:158-200` — `retrievevspansetpm` (vspanset extraction)
- `spanf1.c:56-103` — `findlinksfromtothreesp` (link search)
- `retrie.c:56-85` — `retrieverestricted` (enfilade lookup)
- `correspond.c` — version comparison logic

**Provenance:** Findings 0015, 0017, 0035, 0048

---

### SS-BERT

BERT (Booking Entry Record Table) is the access control mechanism tracking which documents are open by which connection with what access level. Access levels are: `NOBERTREQUIRED` (no check), `READBERT` (read access), `WRITEBERT` (write access).

BERT is implemented as a hash table with open addressing. `checkforopen` enforces concurrent read sharing and write exclusivity. BERT is one of the few enforcement mechanisms in the system — most other validation relies on convention [INV-CONVENTION].

**Code references:**
- `common.h:165-167` — access level constants
- `bert.c:13-29` — BERT entry structure
- `bert.c:43-50` — `checkforopen` (access control state machine)

**Provenance:** Findings 0014

---

## Preconditions

> What must hold before an operation is valid

### PRE-DOCUMENT-OPEN

`retrieve_contents`, `find_links`, and other per-document operations require the referenced document to be in the caller's open document list. `findorgl` performs BERT checks; if the document is not open, the operation fails silently. Callers following links across documents must manage document lifecycle explicitly.

**Why it matters for spec:** Every operation that accesses a document's POOM has an implicit precondition: `document ∈ open_documents(session)`.

**Code references:**
- `do1.c` — `findorgl` (BERT-gated document lookup)
- `bert.c:52-87` — `checkforopen`

**Provenance:** Findings 0006, 0027b

---

### PRE-INSERT

INSERT has no V-position subspace validation. The backend accepts ANY V-position — `1.x`, `2.x`, `3.x` — without checking. `acceptablevsa()` always returns TRUE. The conventional restriction (text only in `1.x`) is a caller obligation, not a backend precondition.

**Why it matters for spec:** The spec must either: (a) model subspace restriction as a precondition that callers must satisfy (convention), or (b) accept that the backend permits cross-subspace insertion and guard against its consequences.

**Code references:**
- `do2.c:110-113` — `acceptablevsa` (always returns TRUE)
- `orglinks.c:75-134` — `insertpm` (uses V-position directly, no validation)

**Provenance:** Findings 0049, 0011

---

### PRE-DELETE

DELETE requires a valid V-span within the target document's current content. The span must reference existing POOM entries — deleting a range with no content is a no-op. DELETE does not validate subspace; deleting from the link subspace is possible and removes link orgl references from the POOM (though the link persists in granfilade and spanfilade) [ST-LINK-REMOVE].

**Code references:**
- `edit.c:31-76` — `deletend` (constructs knives from span boundaries)

**Provenance:** Findings 0053, 0040

---

### PRE-COPY

COPY (vcopy) requires: (1) source document open with at least read access, (2) target document open with write access, (3) source specset references existing V-content. COPY automatically splits V-spans that map to non-contiguous I-addresses via `vspanset2sporglset` — no front-end pre-splitting required.

**Code references:**
- `do1.c:45-65` — `docopy` (reads source, writes target)
- `sporgl.c:35-65` — `vspanset2sporglset` (automatic splitting)

**Provenance:** Findings 0003, 0037

---

### PRE-CREATELINK

CREATELINK requires: (1) home document open with write access, (2) three endsets (source, target, type) as specsets. Endset V-spans are automatically converted to I-spans. Endsets referencing content across multiple I-address ranges are automatically split into multiple sporgl entries.

CREATELINK uses `insertpm` internally, which calls `makegappm` to shift existing POOM entries. The shift is invisible in practice because `findnextlinkvsa` places links at the document end (no entries beyond to shift).

**Code references:**
- `do1.c:199-225` — `docreatelink`
- `do2.c:151-167` — `findnextlinkvsa` (end-of-document allocation)
- `insertnd.c:124-172` — `makegappm` (shifting)

**Provenance:** Findings 0004, 0052

---

### PRE-REARRANGE

REARRANGE expects 3 cuts (pivot) or 4 cuts (swap) as V-positions within a single document. The cuts must be in ascending order and within the document's current V-span. REARRANGE does NOT validate subspace boundaries — content at `1.x` can be moved to `2.x`, violating content discipline [EC-REARRANGE-CROSS-SUBSPACE].

**Code references:**
- `edit.c:78-160` — `rearrangend` (core algorithm)
- `edit.c:164-183` — `makeoffsetsfor3or4cuts` (pure tumbler arithmetic, no boundary check)

**Provenance:** Findings 0016, 0051

---

### PRE-CREATENEWVERSION

CREATENEWVERSION requires: (1) source document exists. Ownership of the source document determines where the version is allocated — under the source document if owned, under the user's account if not. This is a branching postcondition, not a precondition that rejects the operation.

**Code references:**
- `do1.c:264-303` — `docreatenewversion` (ownership check)
- `do2.c:78-84` — `makehint` (ownership-sensitive allocation)

**Provenance:** Findings 0068, 0032

---

## State Transitions

> What an operation changes (postconditions)

### ST-INSERT

INSERT at V-position `v` in document `d` with text `t` (length `n`):

1. **I-space**: Allocates `n` fresh contiguous I-addresses starting at `max_existing + 1` within document's I-address range.
2. **V-space**: Creates a new POOM entry mapping `[v, v+n)` → the new I-addresses. All existing POOM entries with V-position ≥ v are shifted right by width `n` (via `makegappm` → `tumbleradd`).
3. **Spanfilade**: Creates a DOCISPAN entry recording that document `d` contains the new I-address span.
4. **Granfilade**: The text bytes are stored as a new leaf in the granfilade.

Interior typing optimization: The first character at position `v` costs +2 crums (split existing + new). Subsequent characters at `v+1, v+2, ...` cost +0 each — `isanextensionnd` coalesces them into the existing crum via the ONMYRIGHTBORDER case.

Multiple inserts at the same position produce LIFO ordering — the most recent insert appears first (prepend semantics).

**Why it matters for spec:** INSERT is the primary state transition. Postcondition: `POOM'(v) = new_iaddr`, `∀ v' ≥ v: POOM'(v' + n) = POOM(v')`, `granf' = granf ∪ {new_iaddr → t}`, `spanf' = spanf ∪ {DOCISPAN(d, new_iaddr, n)}`.

**Code references:**
- `do1.c:27-43` — `doinsert`
- `insertnd.c:15-111` — `insertnd` (POOM modification)
- `insertnd.c:124-172` — `makegappm` (V-position shifting)
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert` (subspace boundary)
- `insertnd.c:293-301` — `isanextensionnd` (coalesce optimization)
- `retrie.c:345-398` — `whereoncrum` (boundary classification)

**Example:**
```
Before: doc has "ABCDE" at V:[1.1,1.5] → I:[.0.1.1,.0.1.5]

INSERT "XY" at V:1.3:
After:
  V:[1.1,1.2] → I:[.0.1.1,.0.1.2]  (AB, unchanged)
  V:[1.3,1.4] → I:[.0.1.6,.0.1.7]  (XY, fresh I-addrs)
  V:[1.5,1.7] → I:[.0.1.3,.0.1.5]  (CDE, shifted right by 2)
```

**Provenance:** Findings 0027, 0030, 0033, 0036, 0062

---

### ST-DELETE

DELETE of V-span `[v, v+w)` in document `d`:

1. **POOM**: Removes the targeted entries. Entries entirely within the span are disowned and freed. Entries partially overlapping are sliced via `slicecbcpm`. Entries after the span are shifted left by width `w` (via `tumblersub`).
2. **Granfilade**: Unchanged — content persists permanently.
3. **Spanfilade**: Unchanged — DOCISPAN entries are NOT removed (no `deletespanf` function exists).

DELETE shifts can produce negative V-position tumblers when the deletion width exceeds an entry's position offset. Negative tumblers are valid in the tumbler type and sort before all positive values, but they violate the expected POOM bijectivity invariant [EC-NEGATIVE-VPOSITION].

Boundary-aligned deletes (where cut points exactly match existing crum boundaries) skip `slicecbcpm` entirely — the function is only invoked for interior cuts. Zero-width pieces cannot be produced.

DELETE followed by re-INSERT of identical text creates new I-addresses. The original identity is permanently lost — all transclusions, links, and version relationships referencing the original I-addresses are severed [INV-IADDR-IMMUTABILITY].

**Why it matters for spec:** DELETE is destructive in V-space and irreversible in I-space. The only way to preserve prior state is explicit CREATENEWVERSION [EC-NO-UNDO]. Postcondition: `POOM' = POOM minus [v,v+w)`, shifted. `granf' = granf`, `spanf' = spanf`.

**Code references:**
- `edit.c:31-76` — `deletend` (pruning via disown + subtreefree)
- `tumble.c:406-440` — `tumblersub` (V-position shifting, may produce negatives)
- `ndcuts.c:77-90` — `makecutsbackuptohere` (cut construction)
- `ndcuts.c:396` — `slicecbcpm` (only for interior cuts, `whereoncrum == THRUME`)

**Example:**
```
Before: doc has "ABCDE" at V:[1.1,1.5] → I:[.0.1.1,.0.1.5]

DELETE V:[1.2,1.4] (remove "BCD"):
After:
  V:[1.1,1.1] → I:[.0.1.1,.0.1.1]  (A)
  V:[1.2,1.2] → I:[.0.1.5,.0.1.5]  (E, shifted left by 3)

I-addresses .0.1.2-.0.1.4 still exist in granf/spanf but are unreachable
```

**Provenance:** Findings 0053, 0064, 0075

---

### ST-COPY

COPY of specset `S` from source to target at V-position `v`:

1. **Target POOM**: New entries mapping V-positions starting at `v` to the SAME I-addresses as the source. Existing entries at ≥ v are shifted right.
2. **Spanfilade**: DOCISPAN entry created for the target document, recording that it now contains these I-address spans.
3. **Granfilade**: Unchanged — no new content created.

Sequential single-character copies produce contiguous I-addresses that consolidate into a single I-span. COPY of a contiguous V-span always produces a contiguous I-span in the target.

**Why it matters for spec:** COPY is the mechanism for transclusion. Postcondition: `POOM_target'(v+i) = POOM_source(S.start+i)` for all `i` in range. Same I-addresses, different V-addresses.

**Code references:**
- `do1.c:45-65` — `docopy`

**Example:**
```
doc1 has "Hello" at V:[1.1,1.5] → I:[.0.1.1,.0.1.5]
doc2 is empty

COPY doc1[1.1,1.5] → doc2 at V:1.1:
  doc2 POOM: V:[1.1,1.5] → I:[.0.1.1,.0.1.5]  (SAME I-addrs as doc1!)
  doc1 POOM: unchanged
  Granfilade: unchanged (no new content)
  Spanfilade: +1 DOCISPAN entry for doc2

Now doc1 and doc2 share content identity:
  find_links on doc2 discovers links from doc1
  compare_versions shows full overlap
```

**Provenance:** Findings 0002, 0003, 0033

---

### ST-REARRANGE

REARRANGE adds tumbler offsets to V-addresses based on pre-move cut points, preserving I-addresses. Two modes:

**Pivot (3 cuts)**: Swaps two adjacent regions. Cuts at `a, b, c` exchange region `[a,b)` and `[b,c)`.

**Swap (4 cuts)**: Exchanges two non-adjacent regions. Cuts at `a, b, c, d` exchange `[a,b)` and `[c,d)`, shifting the middle region `[b,c)`.

In both modes, content identity (I-addresses) is fully preserved — only V-positions change. All links referencing the rearranged content remain valid and discoverable.

**Why it matters for spec:** Postcondition: `∀ entry ∈ affected_region: POOM'(entry).iaddr = POOM(entry).iaddr`, `POOM'(entry).vaddr = POOM(entry).vaddr + offset(region)`.

**Code references:**
- `edit.c:78-160` — `rearrangend`
- `edit.c:164-183` — `makeoffsetsfor3or4cuts`
- `edit.c:235-248` — `rearrangecutsectionnd` (region classification)

**Example:**
```
doc has "ABCDE" at V:[1.1,1.5] → I:[.0.1.1,.0.1.5]

PIVOT(1.1, 1.3, 1.5) — swap "AB" and "CDE":
After:
  V:[1.1,1.3] → I:[.0.1.3,.0.1.5]  (CDE, moved left)
  V:[1.4,1.5] → I:[.0.1.1,.0.1.2]  (AB, moved right)
  I-addresses preserved — links to "AB" still valid

SWAP(1.1, 1.2, 1.4, 1.5) — swap "A" and "E":
After:
  V:1.1 → I:.0.1.5  (E)
  V:[1.2,1.4] → I:[.0.1.2,.0.1.4]  (BCD, shifted)
  V:1.5 → I:.0.1.1  (A)
```

**Provenance:** Findings 0016, 0056

---

### ST-CREATELINK

CREATELINK in document `d` with endsets (source, target, type):

1. **Link address**: Allocated at next available position in document's link subspace: `findnextlinkvsa` returns `max(existing_link_v_positions) + 1`.
2. **Granfilade**: Link orgl created with the three endsets stored as I-address spans.
3. **Spanfilade**: Endset I-spans indexed for link discovery.
4. **POOM**: New entry in link subspace mapping the link's V-position to its I-address (link orgl ISA).
5. **I-address allocation side effect**: Link orgl I-addresses advance the allocation counter, creating gaps for subsequent text inserts [SS-IADDRESS-ALLOCATION].

CREATELINK uses the same `insertpm` + `makegappm` machinery as text INSERT, so it shifts existing POOM entries at higher V-positions. In practice, links are always placed at document end, so nothing is shifted.

**Code references:**
- `do1.c:199-225` — `docreatelink`
- `do2.c:116-128` — `insertendsetsinspanf`

**Example:**
```
Before: doc has text "Hello" at V:1.1, no links

CREATELINK source=doc[1.1,1.5] target=doc2[1.1,1.3] type=T:
After:
  Link V:0.2.1 → I:doc.0.2.1 (link orgl)
  Spanfilade entries for source I-span, target I-span, type
  doc.0.2.1 contains the three endsets as I-address ranges
```

**Provenance:** Findings 0004, 0052, 0063

---

### ST-CREATENEWVERSION

CREATENEWVERSION of document `d`:

1. **New document address**: Allocated as child of source (`d.0.1`, `d.0.2`, etc.) if owned, or under user's account if not.
2. **POOM**: New document's POOM is a copy of source's **text subspace only** (`1.x`). Link subspace (`0.x`/`2.x`) is NOT copied.
3. **Spanfilade**: DOCISPAN entries created for the new document, recording its I-address spans.
4. **Granfilade**: Unchanged — no new content created. The version shares I-addresses with the original.
5. **I-address allocation**: NOT advanced — CREATENEWVERSION does not call `findisatoinsertgr`.

Links in the original are NOT copied to the version, but they remain discoverable from the version via shared content identity — `find_links` finds them through I-address overlap [INT-LINK-DISCOVERY].

**Why it matters for spec:** Postcondition: `POOM_new = text_subspace(POOM_source)`, `iaddrs(POOM_new) = iaddrs(text_subspace(POOM_source))`.

**Code references:**
- `do1.c:264-303` — `docreatenewversion`
- `do1.c:66-82` — `docopyinternal` (copies SPAN, no new I-addresses)
- `do1.c:376-384` — `doretrievedocvspanfoo` (extracts text-only span)

**Example:**
```
doc1 (1.1.0.1.0.1) has:
  Text "Hello" at V:[1.1,1.5] → I:[.0.1.1,.0.1.5]
  Link L1 at V:0.2.1 → I:[.0.2.1]

CREATENEWVERSION(doc1):
  New doc: 1.1.0.1.0.1.0.1 (child of doc1)
  Version POOM: V:[1.1,1.5] → I:[.0.1.1,.0.1.5]  (text copied)
  Link L1: NOT in version's POOM
  But: find_links(version, [1.1,1.5]) → finds L1 (shared I-addrs)
```

**Provenance:** Findings 0007, 0043, 0068, 0077

---

### ST-LINK-REMOVE

DELETEVSPAN on the link subspace (`2.x`) removes the link's V→I mapping from the document's POOM. The link orgl persists in the granfilade and its endsets remain in the spanfilade. This creates a "reverse orphaned" link: discoverable via `find_links` (through I-address overlap) but absent from the document's V-stream.

**Code references:**
- `orglinks.c:145-152` — `deletevspanpm` (POOM mutation only)

**Provenance:** Finding 0040

---

## Frame Conditions

> What an operation leaves unchanged

### FC-SUBSPACE

Text operations (INSERT, DELETE) in subspace `1.x` do not affect link subspace `2.x`, and vice versa. This isolation is achieved through two distinct mechanisms:

1. **INSERT**: Uses a "two-blade knife" — `findaddressofsecondcutforinsert` computes the boundary tumbler at the next subspace. POOM entries at or beyond the second blade are classified as case 2 (no shift), preserving link positions.

2. **DELETE**: Uses an accidental but effective "exponent guard" in `strongsub`. When the deletion width (exp=-1 for text-level widths) is subtracted from a link position (exp=0), the exponent mismatch causes `strongsub` to return the link position unchanged.

**Why it matters for spec:** This is a critical frame condition: `∀ op ∈ {INSERT, DELETE} on subspace S: POOM'(v) = POOM(v) for all v ∉ S`. The two mechanisms achieving this are structurally different but produce the same guarantee.

**Code references:**
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert` (INSERT blade)
- `edit.c:207-233` — `insertcutsectionnd` (two-blade classification)
- `tumble.c:534-547` — `strongsub` exponent guard (DELETE isolation)

**Example:**
```
Document with text at V:1.1-1.5 and link at V:0.2.1:

INSERT "XY" at V:1.3:
  Second blade = 2.0 (start of next subspace)
  V:1.1-1.2 → case 0 (before insert, no shift)
  V:1.3-1.5 → case 1 (after insert, shift right by 2)
  V:0.2.1   → case 2 (at/beyond second blade, NO shift)

DELETE V:1.2-1.4:
  tumblersub(link_pos=0.2.1, width=0.3):
    width.exp=-1, link_pos.exp=0 → exponent guard fires
    Returns 0.2.1 unchanged
```

**Provenance:** Findings 0054, 0055, 0067

---

### FC-DOC-ISOLATION

Document operations (INSERT, DELETE, COPY, REARRANGE) modify only the target document's POOM. No mutations occur to other documents' POOMs, to the granfilade (except appending new content for INSERT), or to any other document's state. Frame axiom F0: cross-document side effects do not exist.

`docopy` reads the source document's POOM but writes only to the target. `insertnd` and `deletend` operate on a single `fullcrumptr` — there is no mechanism to access another document's tree.

**Why it matters for spec:** `∀ op, ∀ doc ≠ op.target: POOM_doc' = POOM_doc`. This is the strongest frame condition in the system.

**Code references:**
- `insertnd.c:15-111` — `insertnd` (operates on single fullcrumptr)
- `edit.c:30-75` — `deletend` (tree-local mutations)
- `do1.c:45-65` — `docopy` (reads source, writes target only)

**Example:**
```
doc1 has "Hello", doc2 has "World" (transcluded from doc1)

INSERT "XY" at doc1 V:1.3:
  doc1 POOM: modified (shift, new entry)
  doc2 POOM: UNCHANGED — still points to same I-addresses
  doc2 content: still "World" — V-positions unchanged

DELETE doc1 V:[1.1,1.2]:
  doc1 POOM: modified (entries removed/shifted)
  doc2 POOM: UNCHANGED
```

**Provenance:** Finding 0067

---

### FC-GRANFILADE-PERMANENT

The granfilade is append-only. No operation removes content from the granfilade. DELETE removes V→I mappings from the POOM but does not touch the granfilade entries. COPY reads but does not modify. INSERT only appends new entries.

This means: once content is stored, its I-address remains valid for all future queries, even if no POOM currently references it.

**Code references:**
- `credel.c:413-436` — `subtreefree` (POOM tree nodes only, not granfilade)

**Provenance:** Findings 0057, 0064, 0072

---

### FC-SPANFILADE-MONOTONIC

The spanfilade only grows. No `deletespanf` function exists. When content is deleted from a POOM, the corresponding DOCISPAN entries remain in the spanfilade as historical records. This means `find_documents_containing` returns documents that once contained the queried content, even if they no longer do.

**Why it matters for spec:** `∀ op: spanf' ⊇ spanf`. The spanfilade is a historical journal, not a current index. Consumers must verify results against current POOM state.

**Code references:**
- `spanf1.c` and `spanf2.c` — no delete function exists
- `orglinks.c:145-152` — `deletevspanpm` (calls `deletend` only, no spanf cleanup)

**Provenance:** Findings 0023, 0057

---

### FC-IADDR-PRESERVED

INSERT, DELETE, and COPY never change existing I-address assignments. An I-address, once assigned to content, permanently identifies that content. The V-address may change (INSERT shifts, DELETE shifts, REARRANGE moves), but the I-address mapping is immutable.

REARRANGE explicitly preserves I-addresses while changing V-addresses. COPY creates new V→I entries pointing to existing I-addresses. INSERT creates new I-addresses for new content.

**Why it matters for spec:** `∀ op, ∀ iaddr ∈ dom(granf): granf'(iaddr) = granf(iaddr)`.

**Example:**
```
"A" at I:.0.1.1

After INSERT "X" at V:1.1:   I:.0.1.1 still → "A" (V-addr shifted, I-addr unchanged)
After DELETE V:[1.1,1.1]:    I:.0.1.1 still → "A" (POOM entry removed, granf unchanged)
After REARRANGE(pivot):      I:.0.1.1 still → "A" (V-addr moved, I-addr unchanged)
After COPY to doc2:          I:.0.1.1 still → "A" (new V-entry, same I-addr)
```

**Provenance:** Findings 0002, 0016, 0030, 0056

---

## Invariants

> What always holds across all operations

### INV-IADDR-IMMUTABILITY

I-addresses are permanent content identifiers. Once content is stored at I-address `i`, that mapping never changes: `granf(i)` returns the same bytes forever. No operation modifies existing granfilade entries. This is the foundation for content identity — transclusion, link endpoints, and version comparison all depend on I-address stability.

DELETE does not affect I-addresses. It only removes V→I mappings from POOMs. The I-address and its content persist in the granfilade permanently.

**Example:**
```
INSERT "ABC" → I-addrs [.0.1.1, .0.1.2, .0.1.3]
DELETE "B" (I-addr .0.1.2)
INSERT "B" → I-addr .0.1.4 (NEW identity, not .0.1.2)

granf(.0.1.2) still returns "B" — content persists
But .0.1.2 ≠ .0.1.4: transclusions/links to old "B" are broken
```

**Provenance:** Findings 0002, 0030, 0064

---

### INV-IADDR-MONOTONIC

I-address allocation is strictly monotonic within each document's address range. New allocations always exceed all existing I-addresses under the same parent. DELETE does not affect allocation because it doesn't modify the granfilade — the "high water mark" only increases.

**Why it matters for spec:** `∀ alloc_sequence a₁, a₂: time(a₁) < time(a₂) → a₁ < a₂`.

**Code references:**
- `granf2.c:158-181` — `findisatoinsertmolecule` (query-and-increment)
- `granf2.c:255-278` — `findpreviousisagr` (finds current maximum)

**Provenance:** Findings 0061, 0033

---

### INV-LINK-PERMANENCE

Links are permanent. There is no link deletion operation. A link, once created, persists in both granfilade (orgl structure) and spanfilade (endset index) forever. Links can become undiscoverable (when all endpoint content is deleted from all V-streams) but they cannot be destroyed.

An orphaned link becomes discoverable again if its endpoint content reappears in any document via transclusion [INT-LINK-DISCOVERY].

**Provenance:** Findings 0024, 0029

---

### INV-LINK-CONTENT-IDENTITY

Links track content by I-address, not by V-position. A link created with source content at `V:1.3` in document A is discoverable from document B if B transcludes the same I-addresses. The link follows the content identity across all documents, versions, and transclusion chains.

This is validated empirically: all 17 link survivability scenarios pass — links survive source insertion, deletion, target modification, rearrangement, and transclusion. Links created in one version are discoverable from all versions sharing the linked content.

**Example:**
```
doc1: "Hello" at I:[.0.1.1,.0.1.5]
CREATELINK source=doc1[1.1,1.5] → link L1 references I:[.0.1.1,.0.1.5]

COPY doc1[1.1,1.5] → doc2 (transclusion)
  doc2 V:[1.1,1.5] → same I:[.0.1.1,.0.1.5]

find_links(doc2, [1.1,1.5]) → discovers L1!
  (doc2 shares I-addresses with L1's endset)

INSERT doc1 "XY" at V:1.3 (shifts content in doc1)
  L1 still found from doc1: I-addresses unchanged
  L1 still found from doc2: doc2 POOM unchanged
```

**Provenance:** Findings 0004, 0005, 0008, 0026

---

### INV-ATOMICITY

The backend event loop (`bed.c`) processes one complete FEBE operation per iteration with run-to-completion scheduling. There is no interleaving or preemption between operations. Multiple FEBE sessions share global state (documents, links, content identity) while maintaining isolated session context.

**Why it matters for spec:** Each operation sees a consistent snapshot and produces a complete transition. The spec can treat operations as atomic transformations. But atomicity is operation-level only — there is no transaction grouping or crash recovery [SS-PERSISTENCE].

**Code references:**
- `bed.c:103-150` — event loop with `select()` multiplexing
- `bed.c` — `xanadu()` synchronous processing

**Provenance:** Findings 0042, 0022

---

### INV-CONVENTION

Udanax-green follows a "convention over enforcement" design philosophy. The backend performs minimal validation — callers must follow implicit contracts:

1. **Subspace convention**: Text at `1.x`, links at `2.x` — not enforced by `acceptablevsa()` (always TRUE)
2. **Address convention**: `.0.` field separators — not structurally enforced
3. **Access convention**: BERT tokens — checked but enforcement is leaky [EC-BERT-ENFORCEMENT]

The backend prioritizes uniform primitives and simplicity over type safety. The enfilade operations treat all V→I mappings uniformly, leaking in at least 8 identified places where semantic differences between subspaces matter.

**Why it matters for spec:** The formal spec must model two levels: (a) what the backend actually enforces (nearly nothing), and (b) what the caller contract requires (subspace discipline, valid addresses, proper access control).

**Provenance:** Findings 0010, 0011, 0049

---

### INV-ENFILADE-CONFLUENCE

All valid enfilade tree shapes encoding the same logical content produce identical query results. Physical tree structure (sibling ordering, split history, tree height) depends on insertion order, but the logical content accessible through queries is order-independent.

This is maintained by `incontextlistnd`, which performs explicit insertion-sort by V-address as contexts are discovered during tree traversal. V-ordering of retrieval results comes from this sorting, not from tree traversal order — ensuring deterministic results regardless of physical tree structure.

**Why it matters for spec:** The spec can abstract over tree structure entirely. The representation invariant is: `∀ tree₁, tree₂: logical_content(tree₁) = logical_content(tree₂) → query(tree₁, q) = query(tree₂, q)`.

**Code references:**
- `context.c:75-111` — `incontextlistnd` (insertion-sort by V-address)
- `context.c:124-149` — `whereoncontext` (interval comparison)
- `retrie.c:229-268` — `findcbcinarea2d` (tree traversal calling incontextlistnd)

**Provenance:** Findings 0041, 0078

---

### INV-TUMBLER-TOTAL-ORDER

Tumblers have a total order: negative < zero < positive, with sign-aware absolute comparison within each sign class. This order is used throughout for POOM traversal, range queries, and sorting. The order is consistent with hierarchical structure — parent tumblers sort before their children.

**Code references:**
- `tumble.c:72-85` — `tumblercmp`
- `retrie.c:401-418` — `intervalcmp` (comparison logic)

**Provenance:** Findings 0031, 0053

---

### INV-BYTE-OPAQUE

The backend stores and retrieves raw bytes with no encoding interpretation. Each byte occupies exactly one I-space position. The system supports UTF-8 by accident — multi-byte characters span multiple I-positions, and partial retrievals can split characters.

**Provenance:** Finding 0034

---

## Interactions

> How subsystems affect each other

### INT-LINK-DISCOVERY

Links are discoverable from any document sharing content identity (I-addresses) with a link endpoint. The discovery chain is:

1. `find_links(doc, specset)` converts V-spans to I-spans via POOM
2. Searches the spanfilade for links whose endsets overlap those I-spans
3. Returns links regardless of which document originally created them

This means: if document A creates a link to content X, and document B transcludes content X, then `find_links(B, X_vspan)` discovers A's link. The discovery is transitive through any chain of transclusions and versions. Empirically validated: 6 of 7 complex interaction scenarios pass.

FOLLOWLINK returns endset I-addresses unconditionally, but unreferenced I-addresses (DEL5 — those not in any current POOM) are silently filtered during I→V conversion. This produces partial or empty endset results for "ghost links" whose content has been deleted.

**Why it matters for spec:** Link discovery is a pure I-address set intersection. The spec models it as: `find_links(doc, vs) = {L | endsets(L) ∩ iaddrs(POOM_doc, vs) ≠ ∅}`.

**Code references:**
- `sporgl.c:67-95` — `link2sporglset` (extracts I-addresses from link)
- `orglinks.c:389-454` — I→V mapping call chain
- `spanf1.c:56-103` — `findlinksfromtothreesp` (spanfilade search)

**Provenance:** Findings 0008, 0026, 0028b, 0029, 0048

---

### INT-LINK-INSERT-INTERACTION

INSERT in a document shifts V-positions of content after the insertion point. Links track I-addresses, not V-positions, so links are unaffected by INSERT — they continue to reference the same content. However, the link's endsets (when resolved to V-addresses) will report shifted V-positions reflecting the new layout.

Endsets use V-addresses that shift with edits. Pivot operations can fragment endsets — a single-span endset may become multi-span after rearrangement if the linked content is split across non-contiguous V-positions.

**Provenance:** Findings 0005, 0019, 0030

---

### INT-VERSION-LINK

CREATENEWVERSION copies only text, not links. But links remain discoverable from versions because:

1. Version shares I-addresses with original (via text copy)
2. Links reference I-addresses, not documents
3. `find_links` on version finds original's links through shared I-addresses

A link created on the original after versioning is also discoverable from the version if the linked content was part of the shared text. A link created on a version is discoverable from the original for the same reason.

**Provenance:** Findings 0007, 0008, 0043

---

### INT-DELETE-SUBSPACE-ASYMMETRY

INSERT and DELETE achieve subspace isolation through structurally different mechanisms:

- INSERT: explicit second-blade computation (intentional design)
- DELETE: accidental exponent guard in `strongsub` (emergent property)

Both produce the same guarantee, but the asymmetry matters for spec writing: INSERT's isolation can be specified directly as a blade-based partitioning rule, while DELETE's isolation is an emergent property of tumbler arithmetic that would need to be proven as a theorem.

**Provenance:** Findings 0054, 0055

---

### INT-TRANSCLUSION-IDENTITY

COPY (transclusion) creates shared I-address references. Multiple documents can share the same content identity. Operations on a transcluded document (INSERT, DELETE) affect only that document's POOM — the source document and all other transcluding documents are unaffected [FC-DOC-ISOLATION].

The POOM's I→V mapping correctly returns ALL V-positions mapping to a shared I-address via `incontextlistnd`, enabling link discovery across all copies within a single document. Self-transclusion (copying within the same document) is supported and creates multiple V-positions for the same I-addresses.

**Code references:**
- `context.c:75-111` — `incontextlistnd` (accumulates all V-positions)
- `retrie.c:229-268` — `findcbcinarea2d` (2D tree traversal)

**Provenance:** Findings 0002, 0028, 0039

---

### INT-CACHE-EVICTION

Operations on one enfilade can trigger cache eviction affecting another enfilade through the shared "grim reaper" mechanism. For example, loading spanfilade nodes during a link search may evict granfilade text atoms from the cache, requiring disk reads on subsequent text retrieval.

**Provenance:** Finding 0059

---

### INT-MULTI-SESSION

Multiple FEBE sessions share global state: documents, links, content identity, the granfilade, and the spanfilade. Sessions have isolated account context but not isolated document views. Changes by one session are immediately visible to all others after the operation completes (run-to-completion scheduling [INV-ATOMICITY]).

**Code references:**
- `bed.c` — event loop with player array and `select()` multiplexing

**Provenance:** Finding 0022

---

## Edge Cases

> Boundary and unusual behavior

### EC-SELF-TRANSCLUSION

Copying content within the same document is supported. The copy creates a new V-range pointing to the same I-addresses. Both the original and copied positions are discoverable via I→V mapping, enabling link discovery from either position. Overlapping transclusions (where source and target ranges overlap) also work correctly.

**Provenance:** Findings 0028, 0039

---

### EC-ZERO-WIDTH

Zero-width queries return empty results without error. Zero-width pieces cannot be created by DELETE — boundary-aligned cuts skip the slicing function entirely (`slicecbcpm` is only called for interior cuts where `whereoncrum == THRUME`).

**Code references:**
- `ndcuts.c:396` — `slicecbcpm` guard
- `retrie.c:345-372` — `whereoncrum` classification

**Provenance:** Findings 0028, 0075

---

### EC-NEGATIVE-VPOSITION

DELETE shifting via `tumblersub` can produce negative V-position tumblers when the deletion width exceeds an entry's position offset within the same exponent class. Negative tumblers are valid in the tumbler type and sort before all positive values in `tumblercmp`, but they violate the expected POOM bijectivity invariant I₁ from EWD-018.

In practice, the exponent guard in `strongsub` prevents most cross-subspace negative results [FC-SUBSPACE]. Negative V-positions can only arise from same-subspace operations where the deletion width exceeds the surviving entry's relative position.

**Provenance:** Findings 0053, 0055

---

### EC-REARRANGE-CROSS-SUBSPACE

REARRANGE uses pure tumbler arithmetic without subspace boundary checks. Content at `1.x` can be moved to position `2.x` (and vice versa) via REARRANGE, violating the content discipline convention. This is because `makeoffsetsfor3or4cuts` adds offsets without checking whether the result crosses a subspace boundary.

**Why it matters for spec:** Unlike INSERT and DELETE (which have isolation mechanisms [FC-SUBSPACE]), REARRANGE has NO subspace guard. The spec must either restrict REARRANGE to within-subspace operations or document the cross-subspace possibility.

**Code references:**
- `edit.c:164-183` — `makeoffsetsfor3or4cuts` (no boundary check)

**Provenance:** Finding 0051

---

### EC-ORPHANED-LINK

A link whose endpoint content has been deleted from all documents becomes "orphaned" — undiscoverable via `find_links` but still accessible by direct link ID. The link persists in granfilade and spanfilade permanently. If the endpoint content reappears (via transclusion from any source), the link becomes discoverable again.

A "reverse orphaned" link occurs when a link's POOM entry is deleted (DELETEVSPAN on link subspace) — the link remains in granfilade/spanfilade and is discoverable via `find_links`, but is absent from the document's V-stream.

**Provenance:** Findings 0024, 0029, 0040

---

### EC-BERT-ENFORCEMENT

BERT access control has an enforcement gap: several operations send success responses BEFORE checking BERT tokens. `putXXX()` sends the success response, then `doXXX()` checks BERT. If the check fails, the operation is silently skipped — but the client already received a success response.

The correct pattern (check first, respond after) is used in some operations like `createlink`. The inconsistency makes BERT advisory rather than strictly enforced.

**Code references:**
- `fns.c:84-98` — `insert()` (putinsert before doinsert — incorrect order)
- `fns.c:100-115` — `createlink()` (check first — correct order)
- `do1.c:162-171` — `dodeletevspan` (findorgl checks BERT after response)

**Provenance:** Findings 0050, 0014

---

### EC-FIND-LINKS-GLOBAL

`find_links` always searches globally because the orgl range parameter is ignored. In `sporglset2linkset`, the condition `TRUE||!homeset` is always true, overriding the orgl filter with a hardcoded width of 100. The `homedocids` filtering mechanism is non-functional.

**Why it matters for spec:** The spec should model `find_links` as a global I-address intersection, not a document-scoped query, matching the actual implementation behavior.

**Code references:**
- `sporgl.c:222-237` — `sporglset2linkset` (`TRUE||` override)
- `spanf1.c:56-103` — `findlinksfromtothreesp` (caller)

**Provenance:** Finding 0069

---

### EC-OPENCOPY-UNIMPLEMENTED

OPENCOPY (documented in protocol specs) is not implemented. CREATENEWVERSION is the only version-creation mechanism. Unlike a hypothetical open-then-copy workflow, CREATENEWVERSION performs atomic create-and-copy with subordinate addressing.

**Provenance:** Finding 0032

---

### EC-NO-UNDO

There is no automatic edit history. DELETE is destructive — it permanently mutates the POOM. The only way to preserve prior state is explicit CREATENEWVERSION before editing. The system provides the mechanism for manual history (version snapshots) but no automatic undo, redo, or history tracking.

**Why it matters for spec:** The spec should not assume recoverable state after DELETE. If undo semantics are desired, they must be built at the client level using CREATENEWVERSION.

**Provenance:** Findings 0064, 0072

---

### EC-COMPARE-CRASH

`compare_versions` (SHOWRELATIONOF2VERSIONS) crashes when either document contains links. The version comparison logic in `correspond.c` does not handle link subspace entries correctly — it assumes all POOM entries are text content with permascroll I-addresses, but link orgls have different address structure.

The fix requires restricting comparison to text subspace only (`V ≥ 1`), excluding the link subspace (`0.x`).

**Provenance:** Findings 0015, 0010 (Bug 0009)

---

### EC-APPEND-NO-DOCISPAN

APPEND (doappend) does not create DOCISPAN entries — the `insertspanf` call is commented out in the source. This means content added via APPEND is not discoverable through `find_documents_containing`, unlike content added via INSERT.

**Why it matters for spec:** APPEND and INSERT have different discoverability postconditions despite both adding content.

**Code references:**
- `do1.c` — `doappend` (commented-out `insertspanf`)

**Provenance:** Finding 0036

---

### EC-INTERNAL-LINK

Links where both source and target reference the same document are supported. Internal links enable self-annotation and internal cross-references. Follow-link works bidirectionally for internal links.

**Provenance:** Finding 0020

---

### EC-EMPTY-DELETE-TREE

After DELETE removes all content, the enfilade tree retains intermediate nodes from prior growth (because `levelpull` is disabled). The empty-after-delete tree state is structurally taller than a freshly created empty tree. This is a representation artifact — query results are identical (empty) regardless of tree height [INV-ENFILADE-CONFLUENCE].

**Provenance:** Finding 0058

---

### EC-INSERTION-ORDER

Multiple inserts at the same V-position produce LIFO ordering — the most recently inserted text appears first. This is consistent with cursor-between-characters semantics.

**Provenance:** Finding 0027

---

### EC-STALE-SPANFILADE

DELETE removes V→I mappings from the POOM but not from the spanfilade [FC-SPANFILADE-MONOTONIC]. Consumers of spanfilade results (find_documents, find_links) may receive stale entries. FOLLOWLINK filters unreferenced I-addresses during I→V conversion via `span2spanset`, producing partial or empty endset results for ghost links.

**Provenance:** Findings 0023, 0048, 0057

---

### EC-DEEPLY-ORPHANED-LINK

A link whose endpoint content has been deleted from all V-streams is unreachable via `find_links`. But it remains permanently stored and accessible by link ID. If the content's I-addresses are transcluded into any document in the future, the link becomes discoverable again. The link's permanence means discovery is a function of current state, not creation-time state.

**Provenance:** Findings 0024, 0029
