# Formal Properties Knowledge Base
<!-- last-finding: 0078 -->

> Formal properties of udanax-green, extracted from implementation findings.
> Each entry preserves all contributing findings separately — no merging, no synthesis.
> Contradictions between findings are preserved for the spec-writing agent to resolve.
> Cite entries as `[SS-ADDRESS-SPACE]`, `[ST-INSERT]`, `[FC-SUBSPACE]`, etc.

## State Structure

> What the state IS — types, address spaces, data model

### SS-TUMBLER

**Sources:** Findings 0001, 0031, 0053, 0055

#### Finding 0001

**What happens:** Tumblers are digit sequences with no inherent structure requirements. The `.0.` field dividers are a docuverse convention for addresses starting with `1`, giving the pattern `Node.0.User.0.Doc.0.Element`. A tumbler like `1.1.0.1.0.2` is valid — it represents a document address without element-level fields. A tumbler like `1.1.0.1.0.1.0.2.1` addresses a specific element within a document. The distinction between document-level and element-level addressing is convention, not type enforcement.

**Why it matters for spec:** The type model for tumblers must represent them as unconstrained digit sequences. The document/element decomposition is a predicate over tumblers, not a structural subtype. Formal spec needs: a base type `Tumbler = seq<nat>`, a predicate `IsDocAddress(t)` vs `IsElementAddress(t)`, and the convention that `.0.` separates fields in docuverse addresses.

**Concrete example:**
- `1.1.0.1.0.2` — valid tumbler, addresses document 2 (no element field)
- `1.1.0.1.0.1.0.2.1` — valid tumbler, addresses element 1 within document 1 link 2

**Provenance:** Finding 0001

#### Finding 0031

**What happens:** A tumbler is stored as a sign bit, a short exponent, and a fixed-length mantissa of `NPLACES` (16) digits. The exponent shifts the mantissa: `exp = 0` means the first mantissa digit is the most-significant; negative exponent represents fractional/sub-positions. Zeros within the mantissa act as hierarchical separators (e.g., `1.1.0.2.0.5` = node `1.1`, account `1.1.0.2`, item `1.1.0.2.0.5`). `tumblerlength()` returns the number of significant digits: `nstories(t) - t.exp`.

**Why it matters for spec:** The concrete representation constrains the formal type. A tumbler is not an arbitrary rational — it is a fixed-precision hierarchical number with at most 16 digits. The exponent/mantissa encoding means two tumblers are equal iff their sign, exponent, and all 16 mantissa digits match (no normalization ambiguity after `tumblerjustify`). The zero-separator convention is semantic, not structural — the data type itself does not enforce hierarchy boundaries.

**Code references:** `common.h:59-65` (struct definition), `tumble.c:24-36` (`tumblereq`), `tumble.c:599-623` (`tumblerincrement`).

**Concrete example:**
- Tumbler `1.1.0.2.0.5`: `exp=0`, `mantissa=[1,1,0,2,0,5,0,0,...,0]`
- Tumbler zero: all mantissa digits zero, detected by `iszerotumbler()`

**Provenance:** Finding 0031

#### Finding 0053

**What happens:** Tumblers use sign-magnitude representation. The `sign` field is 0 (positive) or 1 (negative). `tumblersub` (subtraction) implements `a - b` as `a + (-b)` by negating `b`'s sign and calling `tumbleradd`. When `b > a`, the result is a negative tumbler — not an underflow or error, but a valid tumbler with `sign=1` and positive magnitude. The representation is sign-magnitude, not two's complement: `1.2 - 0.10 = -0.8` (sign=1, mantissa=[8], exp=-1).

`tumblercmp` treats negative tumblers as strictly less than all positive tumblers and zero, regardless of magnitude. A negative tumbler sorts before all valid V-addresses.

**Why it matters for spec:** The tumbler type must include a sign field: `Tumbler = {sign: bool, digits: seq<nat>}`. The total order over tumblers is: all negative tumblers < zero < all positive tumblers, with sign-aware absolute comparison within each sign class. Subtraction is closed over the tumbler type (always produces a valid tumbler), but the result may be negative even when both operands are positive. This is critical because the POOM and other data structures do not guard against negative tumblers being stored.

**Code references:**
- `tumble.c:406-440` — `tumblersub` implementation, sign negation at lines 424 and 427
- `tumble.c:72-85` — `tumblercmp`, negative tumblers always compare as LESS

**Concrete example:**
```
tumblersub(1.2, 0.10):
  b (0.10) > a (1.2) in absolute value
  Result: sign=1, magnitude=0.8  (i.e., -0.8)

tumblercmp(-0.8, 0.0):  → LESS
tumblercmp(-0.8, 1.1):  → LESS
tumblercmp(-0.8, -0.3): → GREATER (larger absolute value = more negative)
```

**Provenance:** Finding 0053

#### Finding 0055

**What happens:** Tumbler subtraction via `strongsub` has an exponent guard: when the subtrahend's exponent is strictly less than the minuend's exponent, `strongsub` returns the minuend unchanged without performing any subtraction. This is not a deliberate subspace guard — it is a property of how `strongsub` handles cross-exponent arithmetic. The effect is that `tumblersub(a, b)` where `a.exp > b.exp` is a no-op (returns `a`).

This corrects Finding 0053's claim that `tumblersub` can produce negative tumblers from cross-subspace subtraction. The exponent mismatch prevents the subtraction from occurring at all. Negative tumblers from `tumblersub` can only arise when both operands share the same exponent and `b > a` in absolute value.

**Why it matters for spec:** The tumbler subtraction function has a partial behavior: `tumblersub(a, b) = a` when `b.exp < a.exp`. Formally: `strongsub(a, b, c) : b.exp < a.exp ==> c = a`. This must be modeled in any Dafny specification of tumbler arithmetic. It has downstream effects on which POOM operations can actually modify which entries — operations whose width tumbler has a lower exponent than the target entry's displacement tumbler are no-ops on that entry.

**Code references:**
- `tumble.c:534-547` — `strongsub`, exponent guard at line 544: `if (bptr->exp < aptr->exp) { movetumbler(aptr, cptr); return(0); }`
- `tumble.c:406-430` — `tumblersub` delegates to `strongsub` via negated `tumbleradd`

**Concrete example:**
```
strongsub(a={exp=0, mant=[2,1]}, b={exp=-1, mant=[3]}):
  b.exp (-1) < a.exp (0) → TRUE
  Returns a unchanged: {exp=0, mant=[2,1]} = tumbler 2.1

strongsub(a={exp=-1, mant=[4]}, b={exp=-1, mant=[3]}):
  b.exp (-1) < a.exp (-1) → FALSE
  Proceeds to main subtraction: result = {exp=-1, mant=[1]} = tumbler 0.1
```

**Provenance:** Finding 0055

**Co-occurring entries:** [SS-INTERVAL-CMP], [SS-SPAN], [PRE-DELETE], [PRE-SPECSET], [ST-DELETE], [ST-INSERT], [FC-SUBSPACE], [INV-IADDR-IMMUTABILITY], [INV-POOM-BIJECTIVITY], [INV-TUMBLER-TOTAL-ORDER], [INT-CLIENT-VALIDATION], [INT-DELETE-SUBSPACE-ASYMMETRY], [EC-DEEPLY-ORPHANED-LINK]

---

### SS-CONTENT-IDENTITY

**Sources:** Findings 0002, 0009, 0015, 0018, 0034

#### Finding 0002

**What happens:** Content in udanax-green has permanent, immutable identity. Documents are not containers of mutable text; they are collections of references to content identities. When a user "edits" a document, the system creates new content for the inserted material — it does not modify existing content in place. A document's view is the set of content identities it currently references.

**Why it matters for spec:** This is the foundational state structure for the content model. The formal spec needs: a type `ContentId` that is unique and permanent, a document state `Document = set<ContentRef>` where each `ContentRef` maps a position to a `ContentId`, and the invariant that `ContentId` values are never reused or mutated. All operations (insert, remove, vcopy) manipulate which `ContentId` values a document references, not the content itself.

**Concrete example:**
- Before: Source document references content identities for "Original content here"
- After insert at beginning: Source now references NEW content identities for "NEW: " plus the SAME identities for "Original content here"
- The string "Original content here" still has the same content identities — the insert created new identities only for "NEW: "

**Code references:** `scenario_vcopy_source_modified` in `febe/scenarios/content/vcopy.py:271-338`

**Provenance:** Finding 0002

#### Finding 0009

**What happens**: There are two fundamentally different types of I-addresses in the system. **Permascroll I-addresses** (e.g., `2.1.0.5.0.123`) dereference to character bytes in the global immutable permascroll and represent content identity — two documents sharing the same permascroll I-address share the same content. **Link orgl ISAs** (e.g., `1.1.0.1.0.2`) dereference to link orgl structures and represent object identity — they are unique references, not shareable content.

**Why it matters for spec**: The I-address space must be modeled with at least two sorts (permascroll addresses and document ISAs). Operations like `compare_versions` that compute I-span intersections are only meaningful over permascroll addresses. A formal spec must capture that I-address comparability is type-dependent.

**Code references**:
- `orglinks.c:389-422` — `permute()` generalizes V↔I conversion without type distinction
- `retrie.c:56-85` — `retrieverestricted()` looks up content by address range, type-agnostic

**Provenance**: Finding 0009

#### Finding 0015

**What happens**: "Common origin" in the context of `compare_versions` means shared **permascroll content identity** — I-addresses that point to immutable characters in the global permascroll. Link orgl ISAs are unique object identities, not content origins. Two documents cannot "share" a link ISA via transclusion because each link is a distinct object. The finding makes explicit that the I-address space has two non-comparable sorts: permascroll addresses (content-bearing, shareable) and link orgl ISAs (identity-bearing, unique).

**Why it matters for spec**: The formal model must distinguish these two I-address sorts. A function `ContentOrigin(doc, span) -> Option<IAddressRange>` returns `Some(ispan)` only for text subspace spans (`V >= 1.0`) and `None` for link subspace spans. I-span intersection — the core of `compare_versions` — is only defined over permascroll addresses. The spec needs a predicate `IsPermascrollAddress(iaddr)` that partitions the I-address space.

**Code references**:
- `correspond.c` — performs I-span intersection without distinguishing address types
- `orglinks.c:389-422` — `permute()` converts V↔I without type metadata

**Provenance**: Finding 0015, also Finding 0009

#### Finding 0018

**What happens:** Content identity in udanax-green is based on I-addresses (immutable positions in the permascroll), not textual value. Two documents containing identical text created independently do NOT share content identity — `compare_versions` returns an empty result. Identity is determined by *when and where* content was created.

**Why it matters for spec:** This is a foundational state-structure property: content identity is intensional (by origin), not extensional (by value). Any spec modeling content comparison or transclusion must use I-address equality, never string equality.

**Concrete example:**
```
Source1: "From source one"  → I-address X
Source2: "From source two"  → I-address Y
compare_versions(source1, source2) → []   # empty, no shared content
```

Even if both contained "same text", independently created content has distinct I-addresses.

**Code references:** Test `identity_mixed_sources` in scenarios.

**Provenance:** Finding 0018, Key Finding 1.

#### Finding 0034

**Detail level:** Essential

Content in udanax-green is stored as opaque bytes with no encoding semantics. The storage unit is `typegrantext`, a fixed-size byte buffer with a length counter:

```c
typedef struct structgrantext {
    char textstring[GRANTEXTLENGTH];  // GRANTEXTLENGTH = 950 bytes
    unsigned textlength;              // byte count, not character count
} typegrantext;
```

`char` is a single byte (8 bits). The system stores, copies, and retrieves raw bytes with no encoding interpretation or validation. Content retrieval uses `movmem` (mapped to `memmove`) — a raw byte copy with no encoding conversion or character boundary checking. Length is computed via `strlen()`, which returns byte count.

**Why it matters for spec:** The fundamental content type in the formal model is `seq<byte>`, not `seq<char>` or `string`. V-space width equals byte count, not character count. All address arithmetic operates on byte offsets. A 5-character UTF-8 string using 10 bytes occupies 10 V-space positions.

**Code references:**
- `wisp.h:76` — `char textstring[GRANTEXTLENGTH]` byte array storage
- `wisp.h:77` — `unsigned textlength` byte count field
- `common.h:115` — `#define GRANTEXTLENGTH 950` max bytes per atom
- `context.c:308` — `movmem()` raw byte copy on retrieval
- `corediskout.c:242` — `movmem()` raw byte copy for disk persistence
- `xumain.c:143` — `strlen()` for byte-count length

**Concrete example:**
- Insert "caf\xc3\xa9" (UTF-8 cafe with e-acute): 5 bytes stored, V-space width = 5
- Insert "hello" (ASCII): 5 bytes stored, V-space width = 5
- Insert "\xf0\x9f\x98\x80" (UTF-8 emoji): 4 bytes stored, V-space width = 4

**Provenance:** Finding 0034

**Co-occurring entries:** [SS-DUAL-ENFILADE], [PRE-COMPARE-VERSIONS], [ST-COMPARE-VERSIONS], [ST-INSERT], [ST-REARRANGE], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-DOC-ISOLATION], [FC-SUBSPACE], [INV-CONTENT-IMMUTABILITY], [INV-REARRANGE-IDENTITY], [INV-SINGLE-CHAR-GRANULARITY], [INV-SUBSPACE-CONVENTION], [INV-TRANSITIVE-IDENTITY], [INT-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-ENCODING-BOUNDARY-SPLIT]

---

### SS-SPECSET

**Source:** Finding 0003

**What happens:** A SpecSet is an ordered collection of VSpecs. Each VSpec identifies a span within a document via three components: a document ID (tumbler address), a start position (tumbler), and a width (tumbler representing span size). A SpecSet can contain VSpecs referencing different documents and non-contiguous regions within the same document. The ordering of VSpecs within a SpecSet is significant — results reflect the order in which VSpecs are specified.

**Why it matters for spec:** The formal spec needs: `VSpec = (doc: Tumbler, start: Tumbler, width: Tumbler)` and `SpecSet = seq<VSpec>` (a sequence, not a set, because order matters). The sequence semantics are operationally significant — retrieve concatenates in VSpec order, vcopy places content in VSpec order. The cross-document capability means SpecSet operations are not scoped to a single document: `forall ss : SpecSet :: |{v.doc | v in ss}| >= 1` (a SpecSet can reference one or many documents).

**Concrete example:**
- Document: "The quick brown fox jumps over the lazy dog"
- SpecSet with two VSpecs: chars 5-9 ("quick"), chars 36-39 ("lazy")
- Retrieve returns: "quicklazy" — concatenated in VSpec order

**Code references:** Tests `retrieve_noncontiguous_spans`, `retrieve_multiple_documents`

**Provenance:** Finding 0003
**Co-occurring entries:** [ST-VCOPY], [FC-SPECSET-COMPARE], [INV-SPECSET-ORDER]

---

### SS-LINK-ENDPOINT

**Sources:** Findings 0004, 0005, 0019, 0020, 0024, 0028, 0037

#### Finding 0004

**What happens:** Link endpoints in udanax-green are stored by content identity, not by document position. A link's endpoint references the same content identity system used by transclusion (vcopy). This means a link endpoint is structurally equivalent to a content identity reference — it names immutable content, not a mutable document offset.

**Why it matters for spec:** The formal spec needs: `LinkEndpoint = ContentId` (or a reference to content identity), NOT `LinkEndpoint = (doc: DocId, offset: Nat)`. This aligns the link model with the content identity model from SS-CONTENT-IDENTITY. The link state structure is: `Link = (source: set<ContentId>, target: set<ContentId>, type: Tumbler)`. Link resolution is a lookup in the content-identity-to-document mapping, not a fixed document-position dereference.

**Code references:** Tests `link_survives_source_insert`, `link_survives_source_delete_adjacent`, `link_with_vcopy_source`, `link_survives_target_modify`

**Provenance:** Finding 0004

#### Finding 0005

**What happens:** Links are bidirectional — they have both source and target endpoints, and can be discovered by searching either endpoint. The `find_links` operation accepts source specs, target specs, or both. Searching `find_links(source_specs)` finds links by source content identity; searching `find_links(NOSPECS, target_specs)` finds links by target content identity. This confirms that both endpoints are indexed by content identity.

**Why it matters for spec:** The link state structure must reflect bidirectional indexing: `Link = (source: set<ContentId>, target: set<ContentId>, type: Tumbler)`. The `find_links` operation has two modes: `find_links(specset, NOSPECS) = {link | content_ids(link.source) ∩ content_ids(specset) ≠ ∅}` and `find_links(NOSPECS, specset) = {link | content_ids(link.target) ∩ content_ids(specset) ≠ ∅}`. Both endpoints participate symmetrically in discovery.

**Code references:** Test `find_links_by_target` (PASS), test `bidirectional_links` (PASS)

**Provenance:** Finding 0005

#### Finding 0019

Endsets are the mechanism for querying the V-address spans that constitute a link's source and target endpoints. The `retrieve_endsets` operation (FEBE opcode 28) returns specsets describing where a link's endpoints currently exist in V-space.

Endsets are **dynamic** — they reflect current V-positions after edits, not the positions at link creation time. This is a consequence of the dual-enfilade architecture: links are stored via I-addresses internally, but endsets are reported in V-address terms relative to the queried document.

Key structural facts:
- Endsets contain a `source` specset and a `target` specset
- Target specsets are often empty when querying from the source document, suggesting the API returns only endpoints that intersect the query specset
- When queried from a version, endsets report the version's docid rather than the original's

**Why it matters for spec**: Defines the return type and semantics of endset retrieval — the fundamental link query operation.

**Provenance**: Finding 0019, sections 1, 5, 6

#### Finding 0020

Links do not require distinct source and target documents. Both endpoints of a link may reside within the same document (internal/self-referential links). The link state structure `Link = (source: set<ContentId>, target: set<ContentId>, type: Tumbler)` does not impose a constraint `doc(source) != doc(target)`. The only structural requirement is that source and target name valid content identities; they may name content within the same document.

This corrects a prior assumption that internal links would be rejected. The backend creates the link successfully and returns a valid link address.

**Why it matters for spec:** The precondition for `create_link` must NOT include `doc(source) != doc(target)`. The link endpoint type is unconstrained with respect to document identity: `forall link : Link :: doc(link.source) == doc(link.target)` is a valid state. Any spec predicate that assumes links are cross-document must be relaxed.

**Code references:** Test `links/self_referential_link`

**Provenance:** Finding 0020

#### Finding 0024

**What happens:** Link types are stored as VSpec references to a type registry in the bootstrap document (doc 1), not as simple enums or flags. The type endset of a link points to a specific address in the bootstrap document's type subspace at `1.0.2.x`. The type system is hierarchical: MARGIN (`1.0.2.6.2`) is nested under FOOTNOTE (`1.0.2.6`), suggesting a subtype relationship.

Known type registry addresses:
| Type     | Local Address | Structure         |
|----------|--------------|-------------------|
| JUMP     | `1.0.2.2`    | version.0.types.2 |
| QUOTE    | `1.0.2.3`    | version.0.types.3 |
| FOOTNOTE | `1.0.2.6`    | version.0.types.6 |
| MARGIN   | `1.0.2.6.2`  | version.0.types.6.subtype.2 |

**Why it matters for spec:** Link types are content references, not metadata — they participate in the same address/identity system as all other content. The type hierarchy encoded by tumbler containment (`1.0.2.6.2` is contained in `1.0.2.6`) enables type queries like "find all footnote-family links" via address-range matching. The state structure for link types is: `link.type : VSpec` where `VSpec.docid = bootstrap_doc ∧ VSpec.spans ⊆ addresses(1.0.2.*)`.

**Code references:** `QUOTE_TYPE` and `MARGIN_TYPE` definitions in `febe/client.py` (VSpec construction with bootstrap document references).

**Provenance:** Finding 0024, Technical Discovery section 5.

#### Finding 0028

**What happens**: Link endpoints are immutable V-spans fixed at creation time. A link records its source and target as specific V-spans in specific documents (e.g., source = Document A at V 1.4 for 0.3, target = Document B at V 1.1 for 0.6). These endpoint references never change after link creation. However, link *discovery* operates on I-addresses, not V-addresses — a link is discoverable from any document whose content shares I-address overlap with the link's endpoint content.

**Why it matters for spec**: The link data structure stores fixed V-span endpoints, but the discovery mechanism uses I-addresses derived from those endpoints. This means: `Link = { source: VSpan, target: VSpan, type: Tumbler }` where VSpan = `(doc: DocId, pos: Tumbler, width: Tumbler)`. The `find_links` operation does NOT compare V-spans — it converts the search specset to I-addresses and checks for I-address intersection with the link's endpoint I-addresses. This is why links "follow" content through transclusion without being modified: the I-addresses of the endpoint content are shared by all documents that transclude that content.

**Code references**: Test `partial_vcopy_of_linked_span` — link created with source "hyperlink text", discovered via partial transclusion of "link" (4 chars from the 14-char source)

**Concrete example**:
```
Link created:
  Source: Document A, V-span 1.4 for 0.3 ("DEF"), I-addresses I.4, I.5, I.6
  Target: Document B, V-span 1.1 for 0.6 ("Target")

After link creation, these V-span endpoints are permanently fixed.
follow_link(link_id, SOURCE) always returns the original VSpan referencing A at 1.4 for 0.3.
```

**Provenance**: Finding 0028b §1, §3

#### Finding 0037

**What happens:** A link endset is not simply a set of V-spans; internally it is a set of I-spans (sporgls). A single user-visible V-span may correspond to multiple I-spans in the endset when the V-span covers content transcluded from multiple sources. Each I-span independently tracks its content identity. This means the endset structure reflects the content identity graph, not the visual layout.

**Why it matters for spec:** The link endpoint model must be: `Endset = set<Sporgl>` where `|Endset| >= |input_vspans|`. The endset cardinality is determined by the I-address structure of the referenced content, not by the number of V-spans provided at link creation time. When retrieving endsets, `retrieve_endsets` reports multiple V-spans corresponding to the stored I-spans, one per contiguous I-region.

**Code references:**
- `sporgl.c:35-65` — `vspanset2sporglset` produces the multi-sporgl endset
- `sporgl.c:97+` — `linksporglset2specset` converts back to V-spans for retrieval

**Provenance:** Finding 0037

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-DELETE], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-LINK-CREATE], [ST-REMOVE], [FC-DOC-ISOLATION], [FC-LINK-PERSISTENCE], [INV-IDENTITY-OVERLAP], [INV-LINK-CONTENT-TRACKING], [INV-LINK-PERMANENCE], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [EC-LINK-PARTIAL-SURVIVAL], [EC-MULTISPAN-LINK-DUPLICATION], [EC-ORPHANED-LINK], [EC-PIVOT-LINK-FRAGMENTATION], [EC-SELF-COMPARISON], [EC-SELF-LINK], [EC-SELF-TRANSCLUSION]

---

### SS-VERSION-ADDRESS

**Sources:** Findings 0007, 0032, 0068

#### Finding 0007

**What happens:** A version's address extends the original document's address by appending a child component. For example, if the original document is at `1.1.0.1.0.1`, a version of it is at `1.1.0.1.0.1.1`. The version is a child in the address space of the original, but operationally it is an independent document — modifications to either do not affect the other.

**Why it matters for spec:** The formal spec needs: `version_address(doc) = doc.address ++ child_component`. This defines the address-space structure for versioning. Importantly, the parent-child address relationship is purely structural — it does NOT imply operational coupling. The spec must distinguish address ancestry from content dependency.

**Code references:** Address structure documented in Finding 0007 "Address Structure" section

**Provenance:** Finding 0007

#### Finding 0032

**What happens:** Version addresses are structurally subordinate to the source document's address, forming a parent-child hierarchy. Original at `1.1.0.1.0.1` produces version at `1.1.0.1.0.1.1`, and a version of that version at `1.1.0.1.0.1.1.1`. This contrasts with CREATEDOCUMENT + COPY, which produces sibling addresses (e.g., `1.1.0.1.0.1` and `1.1.0.1.0.2`). The address hierarchy is the structural signal that distinguishes a "version" relationship from an independent copy.

**Why it matters for spec:** The spec must distinguish two copy mechanisms by their address-allocation rule: `version_address(doc) = doc.address ++ child_component` (subordinate) vs `new_doc_address(session) = session.next_sibling()` (sibling). This is the only structural difference — both produce documents with shared I-addresses. The address hierarchy enables version-chain traversal without additional metadata.

**Code references:** `backend/do1.c:docreatenewversion` — calls `createorglingranf` with a hint derived from the source document's granf, producing a child address. Address structure confirmed in `golden/versions/version_chain.json`.

**Concrete example:**
```
Original:          1.1.0.1.0.1
Version:           1.1.0.1.0.1.1       (child)
Version of version: 1.1.0.1.0.1.1.1    (grandchild)

Separate doc+copy: 1.1.0.1.0.2         (sibling)
```

**Provenance:** Finding 0032

#### Finding 0068

**What happens:** VERSION allocates the new document's address as a child of the source document, not as a sibling under the parent account. This produces a hierarchical version tree encoded directly in the address structure. The allocation uses a context-sensitive hint: when the user owns the source document, `makehint(DOCUMENT, DOCUMENT, 0, isaptr, &hint)` sets depth=1, placing the version under the source document's address prefix. When the user does NOT own the source document, `makehint(ACCOUNT, DOCUMENT, 0, wheretoputit, &hint)` sets depth=2, placing the version under the creating user's account instead (identical to CREATE behavior).

The ownership check uses `tumbleraccounteq(isaptr, wheretoputit) && isthisusersdocument(isaptr)`.

**Why it matters for spec:** The formal spec needs two address allocation rules for VERSION:
- Owned: `version_address(doc) ∈ children(doc)` — i.e., `prefix(version_address, length(doc)) = doc`
- Unowned: `version_address(doc) ∈ children(user_account)` — i.e., `prefix(version_address, length(account)) = account`

This extends SS-VERSION-ADDRESS from Finding 0007 with the ownership-sensitive allocation mechanism. The address hierarchy encodes version lineage only for owned documents; cross-user versions break the address-based lineage.

**Code references:** `do1.c:272-280` — ownership-sensitive hint creation in `docreatenewversion`. `do2.c:78-84` — `makehint` encodes hierarchy levels.

**Concrete example:**
- User owns doc `1.1.0.1.0.1` → version at `1.1.0.1.0.1.1` (child of doc)
- User owns doc `1.1.0.1.0.1`, second version → `1.1.0.1.0.1.2` (next child)
- User B (account `1.1.0.2`) versions User A's doc `1.1.0.1.0.1` → version at `1.1.0.2.0.1` (under User B's account)

**Provenance:** Finding 0068

**Co-occurring entries:** [SS-ADDRESS-SPACE], [PRE-VERSION-OWNERSHIP], [ST-ADDRESS-ALLOC], [ST-INSERT], [ST-VERSION-CREATE], [FC-DOC-ISOLATION], [FC-GRANF-ON-DELETE], [INV-ATOMICITY], [INV-MONOTONIC], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [INT-VERSION-TRANSCLUSION], [EC-EMPTY-DOC]

---

### SS-DUAL-ENFILADE

**Sources:** Findings 0009, 0011, 0012, 0023, 0038, 0041, 0043

#### Finding 0009

**What happens**: A document's virtual address space is partitioned into two subspaces distinguished by the first tumbler digit. V-position `0.x` is the **link subspace** (stores references to link orgls). V-position `1.x` is the **text subspace** (stores actual document content mapped to permascroll I-addresses). The enfilade itself is uniform — it stores V-to-I mappings without type metadata. The subspace identity is encoded purely by V-position convention.

**Why it matters for spec**: This is the fundamental state structure that all document operations act on. A document is not simply a sequence of characters; it is a two-subspace mapping. Any specification of document state must model these subspaces explicitly. The type of the I-address (permascroll address vs. link orgl ISA) is determined by which V-subspace it falls in — this is an implicit invariant that the storage layer does not enforce.

**Code references**:
- `do2.c:151-167` — `findnextlinkvsa()` constructs first link position at `0.1`
- `do1.c:199-225` — `docreatelink()` stores link references via `docopy()` into `0.x`

**Concrete example**:

Before link creation:
```
Document vspanset: <VSpec in 1.1.0.1.0.1, at 1.1 for 0.16>
  V-range 1.1..1.16 → permascroll I-addresses (text content only)
```

After link creation:
```
Document vspanset: <VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>
  V-range 0.x → link orgl ISA (link reference)
  V-range 1.x → permascroll I-addresses (text content)
```

**Provenance**: Finding 0009

#### Finding 0011

**What happens:** The enfilade storage is unified — a single data structure stores both text content and links. V-position subspace (0.x vs 1.x) is the only discriminator, and it is a convention, not a type. I-addresses likewise have no type distinction: permascroll I-addresses (content) and document ISAs (references) are both tumblers with no runtime type tag.

**Why it matters for spec:** The specification must introduce type distinctions that the implementation lacks. The dual-enfilade model should formally distinguish between content-bearing I-addresses and reference I-addresses, and between link V-spans and text V-spans, even though the implementation represents all of these as untyped tumblers. This is the central modeling challenge: adding types to a typeless system.

**Code references:**
- `do2.c:110-113` — `acceptablevsa` does not discriminate
- `specset2ispanset` — uniform I-address handling
- `ispanset2vstuffset` — assumes I-addresses are permascroll content

**Provenance:** Finding 0011

#### Finding 0012

**What happens:** The system maintains two separate global enfilades with distinct roles. **`granf`** (type `typegranf`, `INT *`) stores all content and document structure — the permascroll, document orgls, link orgls, and V→I mappings. **`spanf`** (type `typespanf`, `INT *`) is a link search index that maps I-addresses to the links that reference them. Both are created at initialization via `createenf()` with different type flags (`GRAN` vs `SPAN`), indicating different internal structure. The granf is indexed by document ISA and V-position; the spanf is indexed by content I-address and returns links.

**Why it matters for spec:** The formal state model requires two top-level structures, not one. `SystemState = (granf: GranEnfilade, spanf: SpanEnfilade)`. Operations must specify which enfilade(s) they read and write. Content operations (insert, read, create document) access only `granf`. Link search (`find_links`) accesses only `spanf`. Link creation is the critical compound operation that writes to both. This factoring determines which frame conditions are possible — content operations cannot affect link findability (they don't touch `spanf`), and link searches cannot affect content (they don't touch `granf`).

**Code references:**
- `xanadu.h:13` — `typegranf` definition (`INT *`)
- `xanadu.h:15` — `typespanf` definition (`INT *`)
- `entexit.c:44-45` — initialization: `granf = createenf(GRAN); spanf = createenf(SPAN)`
- `corediskout.c:21-22` — global variable definitions

**Concrete example:**
```
Initialization:
  granf = createenf(GRAN)  — empty content enfilade
  spanf = createenf(SPAN)  — empty link index

After inserting text into document 1.1.0.1.0.1:
  granf: contains document orgl with V→I mapping for text content
  spanf: unchanged (no links created)

After creating a link:
  granf: new link orgl + link reference in document's 0.x subspace
  spanf: new index entries mapping endpoint I-addresses → link
```

**Provenance:** Finding 0012

#### Finding 0023

**What happens:** The finding confirms the dual-enfilade architecture: documents have both a V-stream (current visible content, affected by delete) and an I-stream (historical content identity, unaffected by delete). `retrieve_contents` reads the V-stream; `find_documents` reads the I-stream/spanf index. These are distinct data structures with different semantics.

**Why it matters for spec:** The state model must represent documents as having two separate mappings:
- V-mapping: `V-address → character` (mutable, reflects current content)
- I-association: `set of I-addresses` (monotonically growing, reflects all content ever placed)

Operations modify these independently: insert/vcopy adds to both; delete removes from V-mapping only; `retrieve` reads V-mapping; `find_documents` reads I-association.

**Code references:** Observed via `retrieve_contents` vs `find_documents` divergence after delete in golden/discovery/find_documents_after_delete.json.

**Provenance:** Finding 0023, Interpretation section.

#### Finding 0038

**What happens**: The POOM enfilade partitions V-space into three subspaces distinguished by the first mantissa digit: `1.x` for text, `2.x` for links, and `3.x` for link type endpoints. Internally, `setlinkvsas()` constructs link V-addresses by incrementing digit 0 to 2 (yielding `2.1`, `2.2`, etc.) and type endpoints by incrementing digit 0 to 3 (yielding `3.1`, etc.). However, the output representation differs from internal storage: `retrievedocvspanset` normalizes the link subspace to `0.x` when the document also contains text, but reports the actual `2.x` position when the document contains only links.

**Why it matters for spec**: The formal model must distinguish between internal V-addresses (always `2.x` for links) and the normalized output representation (sometimes `0.x`). Finding 0009 originally described the link subspace as `0.x`; this finding corrects that: `0.x` is an output convention of `retrievevspansetpm`, while `2.x` is the actual stored position. The spec should model internal state with `2.x` and treat normalization as a presentation function.

**Code references**:
- `do2.c:169-183` — `setlinkvsas()` constructs link endpoints at `2.1` and type at `3.1`
- `orglinks.c:173-221` — `retrievevspansetpm()` normalizes output: zeroes mantissa[1] for links, uses `maxtextwid()` for text

**Concrete example**:
```
Internal state after link creation:
  V-position 2.1 → link orgl ISA (stored internally)
  V-positions 1.1..1.10 → permascroll addresses (text)

retrievedocvspanset output (document has text + links):
  [{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]
  Links normalized from 2.x → 0.x

retrievedocvspanset output (document has links only, no text):
  [{"start": "2.1", "width": "0.1"}]
  Links reported at actual internal position 2.x
```

**Provenance**: Finding 0038

#### Finding 0041

The enfilade B-tree used by the permanent layer (ispace + spanf) stores I-address to data mappings in a sibling-linked tree structure. New entries are inserted as the RIGHT BROTHER of the retrieval position via `adopt(new, RIGHTBRO, ptr)`. Siblings are walked left-to-right during retrieval (`findcbcseqcrum`), and nodes split by moving the rightmost half of sons to a new sibling when overflow occurs (`splitcrumseq`).

**Why it matters for spec:** The physical tree structure is an implementation detail below the abstraction boundary. The spec should model the enfilade as a set/multimap of I-address mappings, not as a tree with sibling ordering. The tree details are relevant only for proving that the implementation correctly refines the abstract spec.

**Code references:**
- `backend/insert.c:43-46` — `insertseq()`, new crum adopted as RIGHTBRO
- `backend/retrie.c:167-188` — `findcbcseqcrum()`, left-to-right sibling walk
- `backend/split.c:70-93` — `splitcrumseq()`, rightmost-half split policy
- `backend/genf.c:419` — `adopt()` sibling insertion

**Provenance:** Finding 0041

#### Finding 0043

**What happens**: The document POOM V-space displacement (`cdsp.dsas[V]`) points to the start of the text subspace at position `1`, not to position `0` (the link subspace). The link subspace occupies V-positions before the document's recorded displacement. This means `retrievedocumentpartofvspanpm` — which reads `cdsp.dsas[V]` and `cwid.dsas[V]` — returns a vspan covering only the text region. The link subspace is structurally "outside" the document's primary vspan as returned by this function, accessible only through `retrievevspansetpm` which explicitly constructs separate link and text spans.

**Why it matters for spec**: The state structure has an asymmetry: the document's V-dimension displacement/width pair describes the text subspace only. The link subspace exists at lower V-positions but is not captured by the document's primary vspan. Two different retrieval functions expose different views: `retrievedocumentpartofvspanpm` returns text-only, `retrievevspansetpm` returns both subspaces. The formal model should note that the "document extent" (displacement + width) covers text, while links are a separate structural component at lower V-addresses.

**Code references**:
- `orglinks.c:155-162` — `retrievedocumentpartofvspanpm()` reads `cdsp.dsas[V]` (text start) and `cwid.dsas[V]` (text width)
- `orglinks.c:173-220` — `retrievevspansetpm()` constructs separate link and text spans using `is1story` check

**Provenance**: Finding 0043

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-GRANF-OPERATIONS], [SS-SPANF-OPERATIONS], [PRE-COMPARE-VERSIONS], [PRE-CONCURRENT-INSERT], [PRE-INSERT], [ST-CREATE-LINK], [ST-DELETE], [ST-INSERT], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-ENFILADE-QUERY-INDEPENDENCE], [FC-SUBSPACE], [INV-DUAL-ENFILADE-CONSISTENCY], [INV-ENFILADE-CONFLUENCE], [INV-IADDRESS-PERMANENT], [INV-SUBSPACE-CONVENTION], [INT-LINK-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-ERROR-ABORT], [EC-VSPAN-NORMALIZATION]

---

### SS-GRANF-OPERATIONS

**Source:** Finding 0012

**What happens:** The `granf` enfilade supports four key operation classes: (1) `findorgl()` — locates an orgl by its ISA; (2) `inserttextingranf()` — inserts text content; (3) `createorglingranf()` — creates a new orgl (used for documents and links); (4) `ispanset2vstuffset()` — dereferences I-addresses to their content bytes. These operations cover the full lifecycle of content: creation, storage, and retrieval.

**Why it matters for spec:** These operations define the interface of the `GranEnfilade` abstract data type. The spec should model `granf` as supporting at minimum: `find(isa) → Orgl`, `insert_text(text) → ISpanSet`, `create_orgl() → ISA`, and `deref(ispanset) → content`. All document-level operations (`doinsert`, `docopy`, `docreatelink`) are composed from these primitives.

**Code references:**
- `granf1.c`, `granf2.c` — granf operation implementations
- `do1.c:199` — `createorglingranf()` called during link creation
- Various retrieval paths through `ispanset2vstuffset()`

**Provenance:** Finding 0012
**Co-occurring entries:** [SS-DUAL-ENFILADE], [SS-SPANF-OPERATIONS], [ST-CREATE-LINK], [FC-CONTENT-SPANF-ISOLATION], [INV-DUAL-ENFILADE-CONSISTENCY]

---

### SS-SPANF-OPERATIONS

**Sources:** Findings 0012, 0069

#### Finding 0012

**What happens:** The `spanf` enfilade supports two key operation classes: (1) `insertspanf()` / `insertendsetsinspanf()` — indexes link endpoints by their content I-addresses; (2) `findlinksfromtothreesp()` / `retrieveendsetsfromspanf()` — queries for links whose endpoints intersect with given I-address ranges. The spanf is a pure index — it does not store link content, only the mapping from I-addresses to links.

**Why it matters for spec:** The `SpanEnfilade` is a secondary index: `SpanEnfilade = Map<IAddress, Set<LinkISA>>`. It is derived state — its content is fully determined by the link orgls in `granf`. The spec should model spanf queries as: `find_links(from, to, three) = {link ∈ all_links | endpoints(link) ∩ query_range ≠ ∅}`. The insert operations maintain this index in sync with link creation.

**Code references:**
- `spanf1.c`, `spanf2.c` — spanf operation implementations
- `do1.c:386-391` — `dofindlinksfromtothree()` delegates entirely to `findlinksfromtothreesp()`

**Provenance:** Finding 0012

#### Finding 0069

**What happens:** The spanfilade search operates in two dimensions: the span dimension (I-address content matching) and the orgl dimension (document/link origin scoping). The span dimension filter works correctly — `find_links` returns only links whose endpoints share I-addresses with the query. However, the orgl dimension filter is disabled by a code bug (`TRUE||!homeset` in `sporglset2linkset`). The actual search boundary in the orgl dimension is a hardcoded width of 100 tumbler digits starting from zero, set via `nullhomeset.width.mantissa[0] = 100`. This is effectively unbounded for any realistic deployment.

**Why it matters for spec:** The `SpanEnfilade` query model from Finding 0012 (`find_links(specset) = {link | endpoints(link) ∩ query_range ≠ ∅}`) is correct for the span dimension. But the intended 2D query — filtering by both content identity AND orgl origin — is reduced to a 1D query on content identity alone. The spec should model `find_links` as: `find_links(from, to, three) = {link ∈ all_links | endpoint_iaddrs(link) ∩ query_iaddrs ≠ ∅}` with no orgl scoping, reflecting the actual implementation. If the spec intends to model the design rather than the code, the orgl-range parameter should be included but annotated as unimplemented.

**Code references:**
- `sporgl.c:222-237` — `sporglset2linkset()` replaces homeset with hardcoded range
- `sporgl.c:239-269` — `sporglset2linksetinrange()` performs actual search using the overridden range

**Provenance:** Finding 0069

**Co-occurring entries:** [SS-DUAL-ENFILADE], [SS-GRANF-OPERATIONS], [PRE-FIND-LINKS], [ST-CREATE-LINK], [FC-CONTENT-SPANF-ISOLATION], [INV-DUAL-ENFILADE-CONSISTENCY], [EC-FIND-LINKS-GLOBAL]

---

### SS-SPORGL

**Source:** Finding 0013

**What happens:** The **sporgl** (span + orgl) is the fundamental provenance-carrying data structure. It packages three pieces of information: (1) `sporglorigin` — an I-address identifying content in the permascroll; (2) `sporglwidth` — the width of the content span; (3) `sporgladdress` — the ISA of the document where the content resides. A sporgl answers: "this I-address range came from this document." Sporgls are stored as a linked list (`typesporglset`) and can be interchanged with ispans via a union type (`typesporglitem`), allowing code to handle both "anonymous" I-spans (no provenance) and "provenanced" sporgls uniformly.

**Why it matters for spec:** The sporgl is the intermediate representation between V-address space and I-address space that carries document provenance. The formal type is: `Sporgl = { origin: IAddress, width: TumblerWidth, source_doc: ISA }`. A `SporglSet` extends `ISpanSet` with provenance — the union type means any operation that accepts an `ISpanSet` can also accept a `SporglSet`. The spec must model this as a subtype or tagged union: `SporglItem = ISpan | Sporgl`. This structure is consumed by the spanf index (for link indexing), by docopy (for transclusion), and by correspond (for version comparison).

**Code references:**
- `xanadu.h:115-121` — `typesporgl` struct definition
- `xanadu.h:123-127` — `typesporglitem` union with `typeispan`
- `sporgl.c` — all sporgl operations

**Concrete example:**
```
After vspanset2sporglset on a document with text "Hello World" at V-positions 1.1..1.11:

Sporgl:
  sporglorigin = 2.1.0.5.0.100    (I-address: permascroll position of "Hello World")
  sporglwidth  = 0.11              (11 characters)
  sporgladdress = 1.1.0.1.0.1     (source document ISA)
```

**Provenance:** Finding 0013
**Co-occurring entries:** [ST-VSPAN-TO-SPORGL], [INT-SPORGL-LINK-INDEX], [INT-SPORGL-TRANSCLUSION], [INT-SPORGL-VERSION-COMPARE]

---

### SS-BERT

**Sources:** Findings 0014, 0050

#### Finding 0014

**What happens:** BERT (Booking Entry Record Table) is the access control state for document operations. It is a hash table of entries, each recording: a connection identifier, a document tumbler, access type (READBERT=1 or WRITEBERT=2), a reference count, and created/modified flags. NOBERTREQUIRED (0) is a sentinel that bypasses the table entirely for internal operations.

**Why it matters for spec:** BERT defines the access-control layer of the state model. Every document operation passes through `findorgl` with an access type parameter, making the BERT state a precondition for all document reads and writes. The spec must model this as a mapping from `(connection, document) -> access_level` with reference counting.

**State structure:**
```
BertEntry = { connection: ConnectionId, document: Tumbler, type: {READ, WRITE}, count: Nat }
BertTable: Map<(ConnectionId, Tumbler), BertEntry>
```

**Code references:** `bert.c:13-29` (struct definition), `common.h:165-167` (access level constants)

**Provenance:** Finding 0014

#### Finding 0050

**What happens:** The BERT access control mechanism is architecturally advisory, not enforced. The back end contains the `checkforopen`/`findorgl` machinery described in Finding 0014, but for state-modifying operations (INSERT, DELETEVSPAN, REARRANGE, COPY), the BERT check occurs *after* the success response has already been sent to the front end. The BERT table exists as state, but it functions as a coordination hint rather than an access gate.

The back end handler pattern for mutations is:
1. `getXXX()` — parse the request
2. `putXXX()` — send success response to front end
3. `doXXX()` — attempt the actual operation (which calls `findorgl(..., WRITEBERT)`)

When `findorgl` returns FALSE (BERT check fails), the operation is silently skipped — the front end has already received success. This means the BERT table's state does not actually gate mutations; it only determines whether the `doXXX` path executes internally.

**Why it matters for spec:** The specification must model two distinct things: (1) the BERT state structure (as in Finding 0014), and (2) the fact that BERT enforcement is a front-end protocol obligation, not a back-end invariant. The spec should distinguish between the *intended* access control semantics (which BERT represents) and the *actual* enforcement boundary (which is the front end). A formal model might express this as: the back end's postconditions for mutations hold *only if* the front end has satisfied BERT preconditions — they are conditional postconditions, not unconditional guarantees.

**Code references:**
- `fns.c:84-98` — `insert()` handler: `putinsert()` before `doinsert()`
- `fns.c:333-347` — `deletevspan()` handler: same response-before-check pattern
- `granf1.c:17-41` — `findorgl()` checks BERT via `checkforopen()`, returns FALSE on failure
- `bert.c:52-87` — `checkforopen()` actual BERT checking logic

**Concrete example:**
- Before: Front end sends INSERT without acquiring WRITEBERT token
- Expected (if enforced): Back end rejects the operation, sends failure response
- Actual: Back end sends success response immediately via `putinsert()`, then `doinsert()` calls `findorgl()` which returns FALSE, operation is silently skipped. Front end believes the insert succeeded. Document is unchanged.

**Provenance:** Finding 0050

**Co-occurring entries:** [PRE-INSERT], [PRE-OPEN-DOC], [INV-READ-SHARING], [INV-WRITE-EXCLUSIVITY], [INT-BERT-FEBE], [INT-BERT-VERSION], [EC-RESPONSE-BEFORE-CHECK]

---

### SS-VSPAN-VS-VSPANSET

**Sources:** Findings 0017, 0035

#### Finding 0017

**What happens**: The system provides two distinct retrieval operations for querying a document's virtual extent. `RETRIEVEDOCVSPAN` (opcode 14) returns a single span — a bounding range that covers the entire document's V-space. `RETRIEVEDOCVSPANSET` (opcode 1) returns a set of spans, one per occupied subspace region. For text-only documents, the two operations return equivalent results (a single span covering `1.x`). For documents with mixed content (text + links), the results diverge: `retrieve_vspan` returns a single span that attempts to bridge both subspaces (e.g., `1.1 for 1.2`), while `retrieve_vspanset` returns separate spans for each subspace (e.g., `{0.1 for 0.1, 1.1 for 0.11}`).

**Why it matters for spec**: These two operations have different return types with different information content. The single-span result from `retrieve_vspan` is lossy — it represents a bounding box over a potentially discontiguous address space, hiding the gap between the `0.x` and `1.x` subspaces. The spanset result preserves the subspace partition. Any specification of document extent querying must model both operations and note that the single-span result is an approximation that discards structural information. Operations that need accurate content enumeration (iteration, size calculation, content retrieval) require the spanset form.

**Code references**:
- Golden tests: `golden/documents/retrieve_vspan*.json`

**Concrete example**:
```
Document with "Hello World" (text only):
  retrieve_vspan:    1.1 for 0.11
  retrieve_vspanset: [{start: 1.1, width: 0.11}]
  → Equivalent: single text span

Document with "Click here" + one link:
  retrieve_vspan:    1.1 for 1.2   (bounding span across both subspaces)
  retrieve_vspanset: [{start: 0, width: 0.1}, {start: 1, width: 1}]
  → Different: spanset reveals 0.x (link) and 1.x (text) separately
```

**Provenance**: Finding 0017

#### Finding 0035

**What happens:** Two distinct operations retrieve document extent in V-space. RETRIEVEDOCVSPAN (opcode 14) reads the raw root node's V-dimension displacement and width directly via `retrievevspanpm()` — no processing, no subspace awareness. RETRIEVEDOCVSPANSET (opcode 1) uses `retrievevspansetpm()` which tests `is1story()` to detect whether content spans multiple subspaces. For text-only documents both return the same single span. For documents containing links, RETRIEVEDOCVSPAN returns a meaningless bounding-box width spanning both 0.x and 1.x subspaces, while RETRIEVEDOCVSPANSET correctly decomposes into separate link-subspace and text-subspace spans.

**Why it matters for spec:** The state model must distinguish between raw root extent (an internal structural value) and semantic document extent (a set of per-subspace spans). Specs should use RETRIEVEDOCVSPANSET semantics for document extent queries. RETRIEVEDOCVSPAN's output is not a valid V-span for documents containing links — it violates the subspace convention.

**Code references:**
- `retrievevspanpm()`: `backend/orglinks.c:165-172` — raw root copy
- `retrievevspansetpm()`: `backend/orglinks.c:173-221` — subspace-aware extraction
- `is1story()`: `backend/tumble.c:237-247` — checks single-subspace width
- `maxtextwid()`: `backend/orglinks.c:224-245` — recursive text-extent traversal

**Concrete example:**
- Document with 10 chars of text and 1 link:
  - RETRIEVEDOCVSPAN returns: `1.1 for 1.2` (meaningless bounding box, Bug 0011)
  - RETRIEVEDOCVSPANSET returns: `[{0, 0.1}, {1, 1}]` (correct: link subspace + text subspace)
- Text-only "Hello World": both return `1.1 for 0.11`
- Empty document: RETRIEVEDOCVSPAN returns zeros; RETRIEVEDOCVSPANSET returns NULL (empty set)

**Provenance:** Finding 0035 (sections 1-2)

**Co-occurring entries:** [PRE-CONTENT-ITERATION], [ST-FIND-LINKS], [ST-PAGINATE-LINKS], [ST-RETRIEVE-ENDSETS], [INT-SPORGL-LINK-INDEX], [EC-CURSOR-INVALIDATION], [EC-VSPAN-MISLEADING-SIZE]

---

### SS-ADDRESS-SPACE

**Sources:** Findings 0021, 0024, 0027, 0028, 0033, 0061, 0065, 0068, 0077

#### Finding 0021

**What happens**: Tumbler addresses encode a containment hierarchy. Accounts are namespaces within the address space; documents live under accounts; nodes live under nodes. The hierarchy level is encoded by the number of `.0.` boundaries in the address:

- Account address: `1.1.0.2`
- First document under that account: `1.1.0.2.0.1`
- Nodes under a node: `1.1.0.1.1`, `1.1.0.1.2` (no `.0.` boundary)

The `makehint` function encodes the hierarchy depth:

| supertype | subtype | depth | Meaning |
|-----------|---------|-------|---------|
| NODE | NODE | 1 | Node under node |
| ACCOUNT | DOCUMENT | 2 | Document under account |
| DOCUMENT | DOCUMENT | 1 | Version under document |
| DOCUMENT | ATOM | - | Content in document |

`depth = (supertype == subtype) ? 1 : 2`

**Why it matters for spec**: Defines the address type hierarchy that all operations reference. The depth calculation determines the `.0.` boundary structure, which is essential for containment checks and address allocation correctness.

**Code references**: `makehint` in granf allocation logic; `granf2.c:findisatoinsertnonmolecule` for allocation.

**Concrete example**:
- Account `1.1.0.2` → first document is `1.1.0.2.0.1` (depth=2, crosses one `.0.` boundary)
- Node `1.1.0.1` → next node is `1.1.0.1.1` (depth=1, no `.0.` boundary)

**Provenance**: Finding 0021

#### Finding 0024

**What happens:** Links occupy a separate address subspace (0.2.x) within their home document, distinct from the text subspace (1.x). A link address is structured as `{home_doc}.0.2.{link_number}`. For example, document `1.1.0.1.0.1` contains link `1.1.0.1.0.1.0.2.1` — the home document ID followed by `.0.2.1` identifying link subspace entry 1.

Links appear in the document's vspanset alongside text spans. After deleting all text from a document containing a link, the vspanset still reports a span `{"start": "2.1", "width": "0.1"}` — the link. Similarly, `retrieve_contents` returns the link as content: `{"link_id": "1.1.0.1.0.1.0.2.1"}`. This means a document with all text deleted is not "empty" if it contains links.

**Why it matters for spec:** The state model for documents must represent two content subspaces: text at 1.x and links at 0.2.x. Any predicate `is_empty(doc)` must check both subspaces. The vspanset type must accommodate both text spans and link spans. Formally: `doc_content(D) = text_spans(D) ∪ link_spans(D)`, where `text_spans` use addresses in the 1.x range and `link_spans` use addresses in the 0.2.x range.

**Concrete example:**
```
Document 1.1.0.1.0.1 with link and text:
  vspanset: [{start: 1.1, width: 0.5},     # text: 5 chars
             {start: 2.1, width: 0.1}]      # link: 1 link

After deleting all text:
  vspanset: [{start: 2.1, width: 0.1}]      # link still present
  retrieve_contents: [{link_id: "1.1.0.1.0.1.0.2.1"}]
```

**Provenance:** Finding 0024, Technical Discoveries sections 1-3.

#### Finding 0027

**What happens**: V-stream positions identify points **between** characters, not the characters themselves. Position 1 is before the first character, position 2 is between the first and second characters, and so on. Insert at position N means "insert before the character currently at position N." This is a cursor-gap model: positions are inter-character gaps.

**Why it matters for spec**: The V-address model must be defined as an interleaving of gaps and characters, not as character indices. This distinction is critical for formalizing insert: the precondition references a gap position, and the postcondition shifts all subsequent character positions. Formalizing V-addresses as character indices (off-by-one) would misspecify every insert operation.

**Code references**: Observed via `edgecases/multiple_inserts_same_position` test scenario using `session.insert(opened, Address(1, 1), ...)`.

**Concrete example**:
```
V-stream state: "ABC"
  Position 1 = gap before 'A'
  Position 2 = gap before 'B'
  Position 3 = gap before 'C'
  Position 4 = gap after 'C'

Insert("X", position=2) → "AXBC"
  'X' inserted before 'B', pushing 'B' and 'C' to positions 3 and 4.
```

**Provenance**: Finding 0027a

#### Finding 0028

**What happens**: V-positions are inter-character cursors (gaps between characters), not character indices. Insert at position P means "insert before the character currently at position P." Multiple inserts at the same position produce LIFO ordering: the most recently inserted content appears first.

**Why it matters for spec**: Confirms the cursor-gap model from Finding 0027. No new structural facts, but the edge-case test suite validates this model under repeated same-position insertion.

**Code references**: Test `edgecases/multiple_inserts_same_position`

**Provenance**: Finding 0028 §1

#### Finding 0033

**What happens:** Sequential single-character inserts receive contiguous I-addresses in the permascroll. The I-address allocation mechanism finds the previous highest I-address and increments by 1, so inserts performed in sequence always occupy an adjacent range. For example, 10 separate character inserts produce I-addresses `2.1.0.1.0.1.3.1` through `2.1.0.1.0.1.3.10`, forming a single contiguous range of width `0.10`.

**Why it matters for spec:** Defines the I-address allocation policy as a monotonically incrementing counter within a document's I-space. This is a structural property of how the permascroll grows: new content always appends at the next available I-address. This means I-space ordering reflects insertion chronology.

**Code references:** `findisatoinsertmolecule` in `backend/green/granf2.c` — the `TEXTATOM` branch calls `tumblerincrement(&lowerbound, 0, 1, isaptr)` to compute the next I-address by incrementing the previous highest by 1.

**Concrete example:**
- Before: I-space has highest address `2.1.0.1.0.1.3.0`
- Insert "A": allocates `2.1.0.1.0.1.3.1`
- Insert "B": allocates `2.1.0.1.0.1.3.2`
- Insert "C": allocates `2.1.0.1.0.1.3.3`
- Result: range `2.1.0.1.0.1.3.1` to `2.1.0.1.0.1.3.3`, width `0.3`

**Provenance:** Finding 0033

#### Finding 0061

**What happens:** I-address allocation does not use a session-local counter. Each INSERT queries the granfilade tree via `findpreviousisagr` to find the highest existing I-address below an upper bound, then increments by 1. The allocation is purely derived from current tree state — there is no cached "next available" pointer. This means allocation is stateless with respect to the session: any session querying the same granfilade tree will allocate identically.

**Why it matters for spec:** The allocation function can be modeled as a pure function of the granfilade state: `next_iaddr(granf) = max_iaddr(granf) + 1`. No hidden session state participates in allocation. This simplifies formal reasoning because the precondition for allocation depends only on the granfilade, not on session history.

**Code references:** `findisatoinsertmolecule` in `backend/granf2.c:158-181` — calls `findpreviousisagr` then `tumblerincrement(&lowerbound, 0, 1, isaptr)`. `findpreviousisagr` in `backend/granf2.c:255-278` — tree traversal to find highest I-address.

**Concrete example:**
- Granfilade contains I-addresses I.1, I.2, I.3 (even if I.2 was deleted from V-space)
- `findpreviousisagr` returns I.3 as the highest
- `tumblerincrement` produces I.4 as the next allocation
- Session state plays no role; any INSERT in any session would allocate I.4

**Provenance:** Finding 0061

#### Finding 0065

**Detail level: Essential**

Link I-addresses are allocated per-document within element subspace 2. The full structure is:

```
account.0.document.0.element_field.element_number
```

Where `element_field` is 2 for links and 3 for text, and `element_number` is allocated monotonically within each (document, element_field) pair.

**Why it matters for spec:** Defines the address namespace partitioning — each document has an independent link allocation subspace. The element field distinguishes content types, and the element number is scoped to the document, not global.

**Concrete example:**
- Document A = `1.1.0.1.0.1`
- First link in A: `1.1.0.1.0.1.0.2.1` (element field 2, element number 1)
- Second link in A: `1.1.0.1.0.1.0.2.2` (element field 2, element number 2)
- First link in B (`1.1.0.1.0.2`): `1.1.0.1.0.2.0.2.1` (independent counter, also starts at 1)

**Code references:**
- `backend/granf2.c:158-181` — `findisatoinsertmolecule` constructs upperbound from document ISA
- `backend/do1.c:211` — `makehint(DOCUMENT, ATOM, LINKATOM, docisaptr, &hint)` sets document scope
- `backend/do2.c:78-84` — `makehint` copies `docisaptr` to `hintptr->hintisa`

**Provenance:** Finding 0065

#### Finding 0068

**What happens:** Documents form hierarchical version trees encoded in the address structure. Each document is the root of its own version namespace. Versions of versions produce nested addresses, creating unbounded-depth trees:

```
1.1.0.1.0.1              (doc1)
├── 1.1.0.1.0.1.1        (version1 of doc1)
│   └── 1.1.0.1.0.1.1.1  (version of version1)
└── 1.1.0.1.0.1.2        (version2 of doc1)
```

The depth of version nesting is unlimited — the address simply grows by one component per version level.

**Why it matters for spec:** The address space model must accommodate arbitrary-depth version trees. The type hierarchy is recursive: `DOCUMENT → DOCUMENT → DOCUMENT → ...` with depth=1 at each level. The `makehint(DOCUMENT, DOCUMENT, ...)` case with depth=1 is the recursive step that enables this nesting.

**Code references:** `granf2.c:203-242` — `findisatoinsertnonmolecule`, depth=1 for DOCUMENT→DOCUMENT. Test evidence in `golden/versions/version_address_allocation.json`.

**Concrete example:**
- `d = 1.1.0.1.0.1`, `v1 = VERSION(d) = 1.1.0.1.0.1.1`, `v2 = VERSION(v1) = 1.1.0.1.0.1.1.1`
- Each level adds one component; no `.0.` boundary is crossed (depth=1)

**Provenance:** Finding 0068

#### Finding 0077

**What happens:** The granfilade contains both document addresses and content I-addresses, but they occupy separate tumbler ranges and are allocated independently. Document addresses are allocated under the parent account/document via `findisatoinsertnonmolecule` (depth 1 or 2), while content I-addresses are allocated under the document's content subspace via `findisatoinsertmolecule` (depth 3+). The address layout:

```
1.1.0.1                      (account)
├── 1.1.0.1.0.1              (document d1)
│   ├── 1.1.0.1.0.1.1        (version v1 — document address)
│   └── 1.1.0.1.0.1.2        (version v2 — document address)
├── 1.1.0.1.0.2              (document d2)
└── 1.1.0.1.0.1.3.0.1.1      (content I-address for text in d1)
    1.1.0.1.0.1.3.0.1.2      (next content I-address)
```

There is no single global "next" counter (no Σ.next). Allocation is stateless query-and-increment on different tumbler ranges via `findpreviousisagr`.

**Why it matters for spec:** The formal model should NOT use a single `Σ.next` counter. Instead, allocation is a family of independent functions partitioned by tumbler range: `next_doc_addr(granf, parent) = max_child(granf, parent) + 1` and `next_content_addr(granf, doc) = max_content(granf, doc) + 1`. Both query the same granfilade tree but search different subtrees. The EWD simplification of a single counter does not match the implementation.

**Code references:** `findisatoinsertgr` in `backend/granf2.c:130-156` — dispatches to molecule (content) vs non-molecule (document) allocation. `findisatoinsertmolecule` in `backend/granf2.c:158-181` — content allocation. `findisatoinsertnonmolecule` in `backend/granf2.c:203-242` — document allocation.

**Concrete example:**
- INSERT "ABC" allocates content I-addresses I.1, I.2, I.3 (via `findisatoinsertmolecule`)
- CREATENEWVERSION allocates document address `1.1.0.1.0.1.2` (via `findisatoinsertnonmolecule`)
- INSERT "XYZ" allocates content I-addresses I.4, I.5, I.6 (via `findisatoinsertmolecule` — contiguous with ABC, unaffected by document allocation)

**Provenance:** Finding 0077

**Co-occurring entries:** [SS-DOCUMENT-LIFECYCLE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [SS-TUMBLER-CONTAINMENT], [SS-VERSION-ADDRESS], [PRE-ADDRESS-ALLOC], [PRE-LINK-CREATE], [PRE-RETRIEVE-CONTENTS], [PRE-VERSION-OWNERSHIP], [PRE-ZERO-WIDTH], [ST-ADDRESS-ALLOC], [ST-DELETE], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-INSERT], [ST-VERSION], [FC-DOC-ISOLATION], [FC-GRANF-ON-DELETE], [FC-GRANF-ON-VERSION], [FC-LINK-PERSISTENCE], [INV-ACCOUNT-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-LINK-PERMANENCE], [INV-MONOTONIC], [INV-NO-IADDR-REUSE], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-FOLLOW-LIFECYCLE], [INT-LINK-TRANSCLUSION], [INT-TRANSCLUSION-INSERT-ORDER], [EC-ORPHANED-LINK], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### SS-TUMBLER-CONTAINMENT

**Source:** Finding 0021

**What happens**: Containment of address A under prefix B is checked by truncating A to the length of B and comparing for equality:

```c
tumblertruncate(&A, tumblerlength(&B), &truncated);
tumblereq(&truncated, &B);  // TRUE if A is under B
```

**Why it matters for spec**: This is the fundamental predicate for hierarchical address space queries. It defines what "under" means for tumbler addresses — pure prefix matching on the digit sequence. This predicate is used to enforce account boundaries during allocation and would appear in preconditions and invariants involving address containment.

**Code references**: `tumblertruncate`, `tumblerlength`, `tumblereq` — tumbler utility functions.

**Concrete example**:
- Is `1.1.0.1.0.1` under `1.1.0.2`? Truncate to length 4: `1.1.0.1`. Compare: `1.1.0.1 ≠ 1.1.0.2` → NO.
- Is `1.1.0.2.0.1` under `1.1.0.2`? Truncate to length 4: `1.1.0.2`. Compare: `1.1.0.2 = 1.1.0.2` → YES.

**Provenance**: Finding 0021
**Co-occurring entries:** [SS-ADDRESS-SPACE], [PRE-ADDRESS-ALLOC], [ST-ADDRESS-ALLOC], [INV-ACCOUNT-ISOLATION]

---

### SS-SESSION-STATE

**Source:** Finding 0022

**What happens:** The backend daemon maintains two tiers of state. Global state (enfilades, document storage, link storage, content identity/SPORGL) is shared across all connected sessions. Per-session state (current account, open document handles, connection socket) is isolated to each session. The daemon supports up to 25 concurrent connections (MAX_PLAYERS) via a `player[]` array, multiplexed with `select()`.

**Why it matters for spec:** Defines the boundary between shared and isolated state. Any formal model of multi-session behavior must partition the system state into a global component (documents, links, content identity) and per-session components (account context, open handles). This partition determines which operations have cross-session visibility.

**Code references:** `backend/bed.c` (player array, MAX_PLAYERS), `backend/socketbe.c` (connection multiplexing, select loop)

**Concrete example:**
- Session A sets `account(1.1.0.1)`, Session B sets `account(1.1.0.1)`
- Session A switches to `account(1.1.0.2)` — Session B remains on `1.1.0.1`
- Session A creates doc → `1.1.0.2.0.1`; Session B creates doc → `1.1.0.1.0.2`

**Provenance:** Finding 0022, sections 1 and Architecture
**Co-occurring entries:** [ST-CROSS-SESSION-VERSIONING], [ST-LINK-GLOBAL-VISIBILITY], [FC-SESSION-ACCOUNT-ISOLATION], [INV-GLOBAL-ADDRESS-UNIQUENESS], [INT-CROSS-SESSION-TRANSCLUSION], [EC-CONFLICT-COPY-NO-MERGE]

---

### SS-LINK-HOME-DOCUMENT

**Source:** Finding 0025

**What happens**: Every link has a "home document" — the first parameter to `create_link(home_doc, source_specs, target_specs, type_specs)`. The home document determines where the link's address is allocated. A link created with home document `1.1.0.1.0.1` receives an ID like `1.1.0.1.0.1.0.2.1`, where the link address is a child of the home document address. Multiple links created in the same home document get sequential suffixes under that document's address space.

The home document is distinct from the source document — a link's home document need not be the document containing the link's source endpoint.

Address structure:
```
1.1.0.1.0.1.0.2.1
└─────┬────┘ └┬┘
  home doc   link suffix
```

**Why it matters for spec**: The link state structure should be extended: `Link = (home: DocId, source: set<ContentId>, target: set<ContentId>, type: Tumbler)` where `address(link)` is allocated under `home`. This is a structural property: `forall link : Link :: contains(link.home, address(link))`. The home document is the owner/container of the link for allocation purposes, independent of where the link's endpoints point.

**Code references**: Test `links/find_links_filter_by_homedocid`; `do1.c:199-225` — `docreatelink()` takes home document as first parameter.

**Concrete example**:
| Link | Home Doc | Source Doc | Link ID |
|------|----------|------------|---------|
| Link1 | `1.1.0.1.0.1` | `1.1.0.1.0.1` | `1.1.0.1.0.1.0.2.1` |
| Link2 | `1.1.0.1.0.2` | `1.1.0.1.0.2` | `1.1.0.1.0.2.0.2.1` |
| Link3 | `1.1.0.1.0.1` | `1.1.0.1.0.1` | `1.1.0.1.0.1.0.2.2` |

Links 1 and 3 share home doc `1.1.0.1.0.1` and get sequential suffixes `.0.2.1` and `.0.2.2` under it. Link2 has a different home doc and gets `.0.2.1` under that document's space.

**Provenance**: Finding 0025
**Co-occurring entries:** [PRE-FIND-LINKS], [ST-ADDRESS-ALLOC], [EC-HOMEDOCIDS-FILTER-BROKEN]

---

### SS-DOCUMENT-LIFECYCLE

**Source:** Finding 0027

**What happens**: Documents in the backend have an explicit open/closed lifecycle state. A document must be in the "open list" (maintained by the backend) before operations that access its content can succeed. Operations that work through I-address lookup (e.g., `find_links` via span-f) do not require the referenced document to be open. Operations that resolve V→I mappings within a specific document orgl (e.g., `retrieve_contents` via `findorgl`) do require it to be open. `follow_link` returns SpecSets containing document references without requiring those documents to be open — the SpecSet is a deferred reference, not a content retrieval.

**Why it matters for spec**: The formal state model must include a set of currently-open document handles as part of the session state. Operations partition into two classes: (a) those that consult the open list (content retrieval, specset resolution) and (b) those that operate on global indices (link discovery). This open-set membership becomes a precondition for class (a) operations.

**Code references**:
- `findorgl` — checks if document orgl is in the open list; returns FALSE if not, causing the calling operation to fail
- `do1.c` — `doretrievev` calls `specset2ispanset` which calls `findorgl`
- Backend log: `orgl for 0.1.1.0.1.0.1~ not open in findorgl temp = 0`

**Concrete example**:
```
Session state: open_docs = {doc_B}
  doc_A exists but is closed
  doc_B transcludes content from doc_A

find_links(doc_B, span) → succeeds (uses span-f I-address index, no findorgl)
follow_link(link_id, LINK_SOURCE) → succeeds, returns SpecSet referencing doc_A
retrieve_contents(specset_referencing_A) → FAILS ("error response from back-end")
  because findorgl(doc_A) returns FALSE — doc_A not in open list

After: open_document(doc_A)
  open_docs = {doc_A, doc_B}
retrieve_contents(specset_referencing_A) → succeeds
```

**Provenance**: Finding 0027b
**Co-occurring entries:** [SS-ADDRESS-SPACE], [PRE-RETRIEVE-CONTENTS], [ST-INSERT], [INT-LINK-FOLLOW-LIFECYCLE], [INT-TRANSCLUSION-INSERT-ORDER]

---

### SS-LINK-SPACE

**Source:** Finding 0028

**What happens**: Links are stored in a separate address space (the span-f enfilade / link space) distinct from document content. A link does not "belong to" any single document. It is an independent entity that references documents via its endpoints but exists outside the document enfilade. This means a link can be created from one document, discovered from another (via transclusion), and its endpoints can reference content in multiple documents.

**Why it matters for spec**: The system state includes a link store separate from the document store: `System = { documents: Map<DocId, Enfilade>, links: Set<Link>, ... }`. Links are not nested within documents. The link store is indexed by I-address for efficient discovery (this is the span-f enfilade). Operations that modify documents have no direct effect on the link store (FC-LINK-PERSISTENCE). Only `create_link` adds to the link store. This architectural separation is why document operations cannot corrupt or destroy links.

**Code references**: Finding 0028b semantic model diagram; Finding 0010 (unified storage with subspace convention)

**Concrete example**:
```
LINK SPACE (span-f):
  Link L1: Source(A, 1.4, 0.3) → Target(B, 1.1, 0.6)
           Indexed by I-addresses: I.4, I.5, I.6

DOCUMENT SPACE:
  Document A: "ABCDEFGHIJ" (I.1-I.10)  — find_links → L1 (direct match on I.4-I.6)
  Document B: "Target..."             — link target lives here
  Document C: "Copy: EF" (I.5, I.6)   — find_links → L1 (I-address overlap)

L1 exists independently of A, B, and C. Deleting A does not destroy L1.
```

**Provenance**: Finding 0028b §5
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### SS-SPAN

**Source:** Finding 0031

**What happens:** A span (`typespan`) consists of a linked-list pointer, an item ID, a start tumbler (`stream`), and a width tumbler (`width`). Width is computed as `end - start` via tumbler subtraction. The same struct is used for both I-space spans (`typeispan`) and V-space spans (`typevspan`) — they are typedefs, not distinct types.

**Why it matters for spec:** Span is the fundamental unit of content reference. The formal type is `Span(itemid, start: Tumbler, width: Tumbler)` where `end = tumbleradd(start, width)`. The I-span/V-span distinction is semantic (which address space), not structural. Width being a tumbler (not an integer) means hierarchical widths are representable, though text content uses flat numeric widths where width equals character count.

**Code references:** `xanadu.h:65-76` (struct definition), `granf2.c:106` (`tumblersub(&lsa, &spanorigin, &ispanptr->width)`).

**Concrete example:**
- Insert "Hello" (5 chars) at I-address `2.1.0.5.0.100`: end address is `2.1.0.5.0.105`, width represents 5 positions.
- Width = `tumblersub(endAddr, startAddr)`

**Provenance:** Finding 0031
**Co-occurring entries:** [SS-INTERVAL-CMP], [SS-TUMBLER], [ST-INSERT], [INV-IADDR-IMMUTABILITY], [INV-TUMBLER-TOTAL-ORDER]

---

### SS-INTERVAL-CMP

**Source:** Finding 0031

**What happens:** `intervalcmp(left, right, address)` classifies an address relative to a half-open-ish interval `[left, right]`. It returns five spatial relationships: `TOMYLEFT` (address < left), `ONMYLEFTBORDER` (address == left), `THRUME` (left < address < right), `ONMYRIGHTBORDER` (address == right), `TOMYRIGHT` (address > right). The borders are distinguished from the interior, making this a closed-interval test with explicit border detection.

**Why it matters for spec:** This is the primitive for all span-containment and overlap checks. The five-way result (not just boolean in/out) is essential — operations behave differently at span borders vs. interior. The spec needs: `IntervalPos = ToLeft | OnLeft | Through | OnRight | ToRight` with `IntervalCmp(left, right, addr) -> IntervalPos` as a derived function from the tumbler total order.

**Code references:** `tumble.c:144-160` (`intervalcmp`).

**Concrete example:**
- `intervalcmp(10, 20, 5)` → `TOMYLEFT` (-2)
- `intervalcmp(10, 20, 10)` → `ONMYLEFTBORDER` (-1)
- `intervalcmp(10, 20, 15)` → `THRUME` (0)
- `intervalcmp(10, 20, 20)` → `ONMYRIGHTBORDER` (1)
- `intervalcmp(10, 20, 25)` → `TOMYRIGHT` (2)

**Provenance:** Finding 0031
**Co-occurring entries:** [SS-SPAN], [SS-TUMBLER], [ST-INSERT], [INV-IADDR-IMMUTABILITY], [INV-TUMBLER-TOTAL-ORDER]

---

### SS-DOCISPAN

**Sources:** Findings 0036, 0047

#### Finding 0036

**What happens:** The spanf enfilade contains a type 4 index called DOCISPAN that maps I-addresses to the documents containing them. This is distinct from the link-search function of the spanf (which maps I-addresses to links). DOCISPAN is a reverse index: given an I-address range, it returns which documents hold content at those addresses, enabling `find_documents` / `FINDDOCSCONTAINING` queries. DOCISPAN entries are created by `insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)`, where the `DOCISPAN` constant selects the type 4 spanfilade.

**Why it matters for spec:** The state model for `spanf` must include a DOCISPAN component separate from the link index: `SpanEnfilade = { link_index: Map<IAddress, Set<LinkISA>>, docispan: Map<IAddress, Set<DocISA>> }`. The `find_documents` operation queries `docispan`, not the link index. Operations that create DOCISPAN entries must be distinguished from those that don't — this determines which operations make content discoverable.

**Code references:**
- `do1.c:62` — `insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)` in `docopy()`
- `do1.c:45-65` — `docopy()` full implementation showing DOCISPAN insertion as final step

**Provenance:** Finding 0036.

#### Finding 0047

**What happens:** DOCISPAN entries in the spanfilade have per-span granularity, not per-byte. When `insertspanf` is called, it iterates over the `ispanset` linked list and makes one `insertnd` call per `typeispan` struct. Each `typeispan` represents a contiguous range of I-addresses (with a `stream` start and `width` size), so inserting 10 contiguous bytes creates 1 DOCISPAN entry, not 10. The granularity is determined by how `vspanset2ispanset` consolidates V-spans into I-spans before they reach `insertspanf`.

**Why it matters for spec:** The DOCISPAN sub-index should be modeled as `Map<ISpan, DocISA>` where `ISpan = (start: IAddress, width: Nat)`, not as `Map<IAddress, DocISA>` with per-byte entries. This affects the storage complexity model: the number of DOCISPAN entries is proportional to the number of distinct content placements (INSERT/COPY operations), not total byte count. Formally: `|DOCISPAN_entries(doc)| = O(num_operations)`, not `O(total_bytes)`.

**Code references:**
- `spanf1.c:15-53` — `insertspanf` loops over `ispanset`, one `insertnd` call per `typeispan`
- `xanadu.h:65-76` — `typeispan` struct: `stream` (start I-address) + `width` (contiguous byte count)

**Concrete example:**
```
INSERT "ABCDEFGHIJ" (10 bytes) into document D:
  inserttextingranf → allocates I-addresses α₁..α₁₀ as one contiguous range
  docopy → specset2ispanset returns 1 I-span: {stream: α₁, width: 10}
  insertspanf → 1 insertnd call → 1 DOCISPAN entry: (α₁, width 10) → D

NOT:
  10 insertnd calls → 10 DOCISPAN entries: α₁→D, α₂→D, ..., α₁₀→D
```

**Provenance:** Finding 0047

**Co-occurring entries:** [PRE-INSERT], [ST-COPY], [ST-INSERT], [ST-INSERT-ACCUMULATE], [FC-CONTENT-SPANF-ISOLATION], [INV-SPANF-GROWTH], [EC-APPEND-NO-DOCISPAN]

---

### SS-POOM-MULTIMAP

**Source:** Finding 0039

**What happens:** The POOM (Permutation Of Ordered Mappings) is a 2D enfilade (B-tree) that stores `(V-position, I-address)` entries. Critically, it functions as a **multimap**: a single I-address can map to multiple V-positions within the same document. The search algorithm `findcbcinarea2d()` traverses all siblings at each B-tree level and recursively descends into all qualifying subtrees, accumulating every matching leaf node. The accumulation function `incontextlistnd()` inserts each found context into a sorted linked list, never replacing existing entries. This means a query by I-address returns ALL V-positions referencing that address.

**Why it matters for spec:** The POOM's type must be modeled as `POOM = Multimap<(VPosition, IAddress)>`, not a bijection or function. The `ispan2vspanset` operation returns a set, not a single value: `ispan2vspanset(poom, i) : Set<VSpan>`. This is structurally necessary for internal transclusion — without multimap semantics, a document could not reference the same content identity at multiple positions. The Dafny model should define `ispan2vspanset` with return type `set<VSpan>` and prove `|result| >= 1` when the I-address exists in the POOM.

**Code references:**
- `orglinks.c:389-394` — `ispan2vspanset()` delegates to `permute()` with direction I→V
- `orglinks.c:404-422` — `permute()` iterates restriction spanset, calls `span2spanset()` per span
- `retrie.c:229-268` — `findcbcinarea2d()` B-tree traversal: iterates siblings, recurses into subtrees
- `context.c:75-111` — `incontextlistnd()` inserts into sorted linked list, never replaces

**Concrete example:**
```
Document has "B" at V-positions 1.2, 1.4, and 1.5, all referencing I-address i_B.

ispan2vspanset(poom, i_B) = {
  VSpan(1.2, width=0.1),
  VSpan(1.4, width=0.1),
  VSpan(1.5, width=0.1)
}

Result set cardinality = 3 (one per V-position referencing i_B)
```

**Provenance:** Finding 0039
**Co-occurring entries:** [ST-VCOPY], [INV-LINK-IDENTITY-DISCOVERY], [EC-SELF-TRANSCLUSION]

---

### SS-THREE-LAYER-MODEL

**Source:** Finding 0040

**What happens:** Links exist across three independent storage layers with distinct persistence and mutability characteristics:

1. **I-space (link orgl):** The link object at a permanent I-address (e.g., `1.1.0.1.0.1.0.2.1`). Contains the link's endset references (FROM, TO, TYPE). Cannot be deleted (permanence axiom P0).
2. **Spanfilade (DOCISPAN entries):** Type 4 enfilade entries mapping I-addresses to documents. Enables `find_links()` and `finddocscontaining()` queries. Append-only (monotonicity P0').
3. **POOM (document V-stream):** V-position 2.x entries in the document's orgl enfilade. Determines whether the link "appears" in the document's visible structure. Mutable via DELETEVSPAN.

`CREATELINK` writes to all three layers. `DELETEVSPAN(2.x)` removes only the POOM entry. No operation removes from I-space or spanfilade.

**Why it matters for spec:** The formal state model must represent links as distributed across three layers: `State = (ispace, pooms, spanfilade)`. Each layer has a distinct persistence property. The key formalization is that link "existence" (I-space), link "discoverability" (spanfilade), and link "containment in document" (POOM) are three independent predicates. A link can be discoverable and followable even when removed from its home document's POOM.

**Code references:**
- `orglinks.c:145-152` — `deletevspanpm()` operates only on the document's orgl enfilade (POOM layer)
- `edit.c:31-76` — `deletend()` removes crums in V-dimension without affecting I-space or spanfilade

**Concrete example:**
```
Before DELETEVSPAN(2.1):
  I-space:     link orgl at 1.1.0.1.0.1.0.2.1 (permanent)
  Spanfilade:  DOCISPAN entry mapping link to doc (append-only)
  POOM:        V-position 2.1 → link orgl (present)
  vspanset:    [{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]

After DELETEVSPAN(2.1):
  I-space:     link orgl at 1.1.0.1.0.1.0.2.1 (unchanged)
  Spanfilade:  DOCISPAN entry still present (unchanged)
  POOM:        V-position 2.1 removed
  vspanset:    [{"start": "1.1", "width": "0.11"}]
  find_links(source_specs) → still finds the link
  follow_link(link_id, SOURCE) → still works
```

**Provenance:** Finding 0040, Semantic Model and Architectural Implications sections.
**Co-occurring entries:** [PRE-DELETE], [ST-DELETE], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE], [EC-REVERSE-ORPHAN]

---

### SS-LINK-SUBSPACE

**Source:** Finding 0052

**What happens:** Link orgl references occupy a separate subspace in the document's V-stream. The first link is placed at V-position `2.1`, computed by `findnextlinkvsa` which initializes `firstlink` by incrementing tumbler coordinates: first to `2.0`, then to `2.1`. Subsequent links are placed at `vspanreach` (the current end of the document extent). This `2.x` subspace is distinct from the text content subspace (`1.x`), and link positions grow monotonically for sequential creation.

**Why it matters for spec:** The V-address space has at least two subspaces: text content at `1.x` and link orgls at `2.x`. The state structure should model: `Document.vstream = TextSubspace(1.x) ∪ LinkSubspace(2.x)`. The link subspace starts at `2.1` and grows by append. The `retrieve_vspanset` operation returns spans covering each subspace separately.

**Code references:**
- `backend/do2.c:151-167` — `findnextlinkvsa` initializes to `2.1` and uses `vspanreach` for subsequent links

**Provenance:** Finding 0052
**Co-occurring entries:** [ST-CREATE-LINK], [ST-INSERT], [EC-CONCURRENT-LINK-CREATION]

---

### SS-TWO-BLADE-KNIFE

**Source:** Finding 0054

**What happens:** INSERT constructs a two-blade knife to partition the POOM tree into shift and no-shift regions. `makegappm()` sets `blade[0]` to the insertion V-position and `blade[1]` to the start of the next subspace, computed by `findaddressofsecondcutforinsert()`. For an insertion at `N.x`, the second blade is always `(N+1).1`. The knife has exactly 2 blades (`knives.nblades = 2`).

The second blade computation uses tumbler arithmetic:
1. Increment first digit: `N.x → (N+1).x`
2. Behead to get fractional tail: `N.x → 0.x`
3. Subtract fractional part: `(N+1).x - 0.x = (N+1).0`
4. Add 1 at second digit: `(N+1).0 → (N+1).1`

The source comment confirms design intent: "needs this to give it a place to find intersectionof for text is 2.1".

**Why it matters for spec:** The two-blade knife is the data structure that implements subspace isolation for INSERT. The formal model of INSERT must include the knife construction as part of the operation's mechanism. The knife defines a bounded shift region `[blade[0], blade[1])` — only POOM entries within this half-open interval are shifted. This is the structural reason why INSERT at `1.x` cannot affect `2.x` entries.

**Code references:**
- `insertnd.c:144-146` — `makegappm()` knife construction with 2 blades
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert()` computes second blade

**Concrete example:**
```
INSERT at V-position 1.3:
  blade[0] = 1.3  (insertion point)
  blade[1] = 2.1  (next subspace boundary)
  Shift region: [1.3, 2.1)

INSERT at V-position 2.5:
  blade[0] = 2.5  (insertion point)
  blade[1] = 3.1  (next subspace boundary)
  Shift region: [2.5, 3.1)
```

**Provenance:** Finding 0054
**Co-occurring entries:** [ST-INSERT], [FC-SUBSPACE], [INV-SUBSPACE-CONVENTION]

---

### SS-ENFILADE-TREE

**Sources:** Findings 0058, 0060, 0066, 0071

#### Finding 0058

**What happens:** Enfilade trees have a `height` field on the fullcrum (apex node) that tracks tree depth. `createenf(POOM)` produces a minimal height-1 tree: a fullcrum with `isapex=TRUE`, `height=1`, containing a single bottom node (height-0) with zero width. For GRAN enfilades, the bottom node has `infotype=GRANNULL`. As content is inserted, loaf overflow triggers `splitcrumupwards`, and when the fullcrum itself overflows, `levelpush` increments the fullcrum's height and pushes existing children down one level. The inverse operation `levelpull` — which should collapse a height-H tree back to height H-1 when the fullcrum has only one child — exists in code but is disabled: it immediately returns 0 without executing the commented-out collapse logic.

Tree height can increase (via `levelpush`) but never decrease. The fullcrum height is a monotonically non-decreasing value over the lifetime of a document's enfilade.

**Why it matters for spec:** The state structure for enfilades must include `height: nat` on the fullcrum node, and the model must capture that height increases are permanent in the current implementation. The initial state constructor produces `height = 1`; `levelpush` is the only transition that modifies height, and it only increments. This is not the intended design — `levelpull` was meant to provide the inverse — but it is the actual invariant: `∀ t₁ < t₂ : enf.height(t₁) ≤ enf.height(t₂)`.

**Code references:**
- `backend/credel.c:492-516` — `createenf`: creates height-1 fullcrum with one bottom node
- `backend/genf.c:263-294` — `levelpush`: increments fullcrum height, pushes children down
- `backend/genf.c:318-342` — `levelpull`: disabled, immediately returns 0

**Concrete example:**
```
createenf(POOM):
  Fullcrum (height=1, isapex=TRUE, numberofsons=1)
    └─ Bottom node (height=0, width=0)

After many inserts (tree has grown):
  Fullcrum (height=3, isapex=TRUE, numberofsons=2)
    ├─ Height-2 node
    │    ├─ Height-1 node (bottom nodes...)
    │    └─ Height-1 node (bottom nodes...)
    └─ Height-2 node
         └─ Height-1 node (bottom nodes...)

levelpush incremented height from 1→2→3. levelpull would reverse this but is disabled.
```

**Provenance:** Finding 0058

#### Finding 0060

**What happens:** The three enfilade types use different branching factor constants at height-1 (bottom crum capacity), determined by the `toomanysons` function:

| Enfilade type | `is2dcrum` | Height-1 max (`M_b`) | Height > 1 max (`M_u`) |
|---------------|------------|----------------------|------------------------|
| GRAN (granfilade) | FALSE | `MAXBCINLOAF = 1` | `MAXUCINLOAF = 6` |
| POOM | TRUE | `MAX2DBCINLOAF = 4` | `MAXUCINLOAF = 6` |
| SPAN | TRUE | `MAX2DBCINLOAF = 4` | `MAXUCINLOAF = 6` |

The `toomanysons` check dispatches on `height > 1` (uses M_u) vs `height == 1` (uses M_b, with 1D vs 2D distinguished by `is2dcrum`). All enfilade types share the same `splitcrumupwards`, `splitcrumseq`, and `levelpush` code paths — the difference is purely in these constants.

Because `MAXBCINLOAF = 1`, the granfilade triggers `toomanysons` as soon as any height-1 node holds 2 bottom crums. The POOM does not trigger until a height-1 node exceeds 4 children.

**Why it matters for spec:** The state structure for enfilades must parameterize the branching factor by both height level and enfilade type. A single `M` parameter is insufficient; the model needs `M_b(enftype)` and `M_u` as separate constants. The `toomanysons` predicate is: `node.numberofsons > (node.height > 1 ? M_u : M_b(enftype))`.

**Code references:**
- `backend/enf.h:26-28` — constant definitions: `MAXUCINLOAF 6`, `MAXBCINLOAF 1`, `MAX2DBCINLOAF 4`
- `backend/genf.c:239-245` — `toomanysons`: dispatches on height and `is2dcrum`
- `backend/genf.c:19-22` — `is2dcrum`: returns `cenftype != GRAN`

**Concrete example:**
```
Granfilade, height-1 node with 2 bottom crums:
  toomanysons → 2 > MAXBCINLOAF(1) → TRUE → split triggered

POOM, height-1 node with 2 bottom crums:
  toomanysons → 2 > MAX2DBCINLOAF(4) → FALSE → no split

POOM, height-2 node with 4 upper crums:
  toomanysons → 4 > MAXUCINLOAF(6) → FALSE → no split
```

**Provenance:** Finding 0060

#### Finding 0066

**What happens:** 2D enfilades (POOM, SPAN) use coordinate-transform-based displacement, fundamentally different from 1D enfilades (GRAN). In 2D enfilades, the root node's `cdsp` field dynamically tracks the minimum tumbler address across all content in the tree. Children's displacements are stored relative to the root, not as absolute positions. In contrast, GRAN enfilades keep root displacement at zero and use width-summation (`widopseq`) rather than min-tracking.

The three enfilade types differ in their root-level semantics:

| Enfilade Type | Root `cdsp` | Child `cdsp` | Wisp Operation |
|---------------|-------------|--------------|----------------|
| GRAN (1D) | Always 0 | Absolute position | `setwidseq` — sum widths |
| POOM (2D) | Minimum address | Relative to root | `setwispnd` — min-track + adjust |
| SPAN (2D) | Minimum address | Relative to root | `setwispnd` — min-track + adjust |

For 2D enfilades, `root.cdsp` and `root.cwid` together form a bounding box: `root.cdsp` is the upper-left corner (minimum address), `root.cdsp + root.cwid` is the lower-right corner (maximum extent).

**Why it matters for spec:** The spec must parameterize enfilade behavior by type. The grasp function has different semantics at the root: `grasp(root) = root.cdsp` for 2D (typically non-zero), vs `grasp(root) = 0` for 1D. Any enfilade invariant must be qualified by enfilade type. The relative-displacement design means `absolute_grasp(node) = sum_of_ancestor_displacements + node.cdsp`, which holds recursively for all enfilade types but starts from different root values.

**Code references:**
- `backend/wisp.c:171-228` — `setwispnd`: finds minimum child displacement, absorbs it into root, adjusts children to relative
- `backend/wisp.c:150-168` — `setwidseq`: GRAN width-summation (no displacement tracking)
- `backend/credel.c:580-581` — `createcruminternal`: all crums initialized with zero displacement
- `backend/retrie.c:334-339` — `prologuend`: `grasp = offset + ptr->cdsp`
- `backend/genf.c:97-116` — `isemptyenfilade`: 2D checks both width AND displacement are zero; GRAN checks only width

**Concrete example:** Empty POOM, insert at position 2.1:

Before: `root.cdsp = 0, root.cwid = 0` (empty)

After first insertion:
1. `firstinsertionnd` sets child `cdsp = 2.1` (absolute)
2. `setwispnd` finds `mindsp = 2.1`, absorbs: `root.cdsp = 0 + 2.1 = 2.1`
3. Child adjusted: `child.cdsp = 2.1 - 2.1 = 0` (now relative)
4. Final: `root.cdsp = 2.1, root.cwid = 1; child.cdsp = 0, child.cwid = 1`
5. `grasp(root) = 0 + 2.1 = 2.1` (non-zero)

**Provenance:** Finding 0066

#### Finding 0071

**What happens:** The 2D enfilade rebalancing algorithm (`recombinend`) differs fundamentally from the 1D algorithm (`recombineseq`) in how it orders children for merge consideration. `recombinend` at `recombine.c:104-131` works in four steps:

1. **Recursive descent:** Bottom-up rebalancing — recursively rebalance all children before the parent.
2. **Diagonal sort:** `getorderedsons` at `recombine.c:278-311` calls `shellsort`, which orders children by the sum of their two displacement coordinates (`cdsp.dsas[0] + cdsp.dsas[1]`). The code comment calls this the "compare crums diagonally hack." For SPAN enfilades, dimension 0 is ORGLRANGE (I-space) and dimension 1 is SPANRANGE (V-space), so sorting is by combined I+V position — an L1-norm diagonal sweep across the 2D address space.
3. **Pairwise nephew-stealing:** All O(n^2) pairs along the diagonal order are considered for merging, guarded by `ishouldbother`.
4. **Level pull:** If the root has only one child after merges, `levelpull` removes a tree level.

The 1D algorithm (`recombineseq`) is simpler: it iterates children in sibling order (not sorted), only considers adjacent pairs, and breaks after the first merge operation. The 2D algorithm must consider all pairs because spatial proximity in 2D does not follow sibling order.

**Why it matters for spec:** The rebalancing strategy is part of the enfilade's structural maintenance. A formal model of 2D enfilades must acknowledge that the child ordering used during rebalancing is not the storage order but a computed diagonal ordering. This affects what "adjacent" means for merge candidates: two nodes far apart in sibling order may be merged if they are close on the diagonal. The formal invariant is that after `recombinend`, no pair of children whose combined son count fits within `max_children` should remain separate — the algorithm is greedy over all pairs, not just adjacent ones.

**Code references:**
- `backend/recombine.c:104-131` — `recombinend` algorithm (4-step structure)
- `backend/recombine.c:278-311` — `getorderedsons` + `shellsort` with diagonal key
- `backend/recombine.c:313-320` — `comparecrumsdiagonally` (L1-norm comparison)
- `backend/recombine.c:57-102` — `recombineseq` (1D contrast: adjacent pairs only)

**Concrete example:**
```
2D enfilade with 4 children having displacements:
  Child A: dsas[0]=1, dsas[1]=5  → diagonal key = 6
  Child B: dsas[0]=3, dsas[1]=2  → diagonal key = 5
  Child C: dsas[0]=4, dsas[1]=4  → diagonal key = 8
  Child D: dsas[0]=2, dsas[1]=1  → diagonal key = 3

Diagonal sort order: D(3), B(5), A(6), C(8)

Pairwise merge consideration:
  (D,B), (D,A), (D,C), (B,A), (B,C), (A,C)
  — all pairs checked via ishouldbother, not just adjacent siblings
```

**Provenance:** Finding 0071

**Co-occurring entries:** [ST-DELETE], [ST-INSERT], [ST-REBALANCE-2D], [ST-SPLIT-2D], [FC-RESERVED-CRUM], [INV-ENFILADE-MINIMALITY], [INV-ENFILADE-OCCUPANCY], [INV-ENFILADE-RELATIVE-ADDRESSING], [EC-EMPTY-DOC], [EC-GRAN-MB-ONE]

---

### SS-UNIFIED-STORAGE

**Source:** Finding 0059

**What happens:** All persistent state — granfilade (content store), spanfilade (link index), and POOM enfilades (document structure) — resides in a single disk file `enf.enf`. The file has a fixed layout: header blocks containing a bitmap and metadata, then fixed locations for the granfilade root (`GRANFDISKLOCATION`) and spanfilade root (`SPANFDISKLOCATION`), followed by dynamically allocated blocks (loaves). Each block is `NUMBYTESINLOAF` bytes (typically 1024). Blocks are typed by `denftype` field (GRAN, SPAN, or POOM) in their header, but share the same allocator and on-disk format.

**Block header structure:**
```c
typedef struct structdiskloafhedr {
    INT sizeofthisloaf;
    SINT isapex;           // TRUE if top of orgl
    SINT height;           // 0 = bottom crum (leaf)
    SINT denftype;         // GRAN, SPAN, or POOM
    SINT numberofcrums;
    SINT refcount;         // For subtree sharing / GC
    SINT allignmentdummy;
} typediskloafhedr;
```

Leaf nodes for text content (`GRANTEXT` type) hold up to 950 bytes (`GRANTEXTLENGTH`). Multiple sub-loaves can be packed into a single uber-loaf block.

**Why it matters for spec:** The unified storage means the state space is a single allocation domain. There is no physical isolation between the granfilade and spanfilade — a corrupted block allocator affects all enfilades. For specification, the persistent state is: `Disk = {header, granf_root, spanf_root, blocks: BlockNum → Loaf}` where `Loaf` is tagged by `denftype`. The permascroll (σ : I → B) is implemented as a B-tree of crums, not a flat byte array — retrieval at I-address X requires tree traversal, not direct lookup.

**Code references:**
- `backend/disk.c:364-382` — open/create `enf.enf`
- `backend/coredisk.h:117-120` — `GRANFDISKLOCATION`, `SPANFDISKLOCATION` fixed locations
- `backend/coredisk.h:11-21` — `typediskloafhedr` structure
- `backend/coredisk.h:66-71` — `typeuberdiskloaf` (uber-loaf packing)

**Concrete example:**
```
enf.enf layout:
  Block 0..N:    Disk header (bitmap + metadata)
  Block N+1:     granf root (fixed at GRANFDISKLOCATION)
  Block N+2:     spanf root (fixed at SPANFDISKLOCATION)
  Block N+3...:  Allocated loaves — mix of GRAN, SPAN, POOM blocks
```

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-CACHE-MECHANISM], [ST-INSERT], [INV-DURABILITY-BOUNDARY], [EC-CRASH-MID-WRITE], [EC-CROSS-ENFILADE-EVICTION], [EC-NO-STARTUP-VALIDATION]

---

### SS-CACHE-MECHANISM

**Source:** Finding 0059

**What happens:** All in-memory crums (GRAN, SPAN, POOM) participate in a single shared cache managed by the `grimreaper` global pointer. This forms a circular doubly-linked list of all crums currently in memory. There is no separate write-back buffer — the in-memory enfilade tree IS the cache. Each crum has an `age` counter and `modified` flag. When memory allocation fails, the grim reaper scans for crums with `age >= OLD` and not `RESERVED`, writes modified ones to disk via `orglwrite()`, then frees them.

**Why it matters for spec:** The cache is a shared resource across all enfilades. Memory pressure from one subsystem (e.g., a large link search loading many spanfilade crums) can evict modified crums from another subsystem (e.g., recently inserted text atoms). For spec purposes, the observable state includes both in-memory and on-disk crums. The invariant is: for any crum C, either C is in the grim reaper list (in-memory, possibly modified) or C is on disk at its assigned block number, but never neither (that would be data loss).

**Code references:**
- `backend/credel.c:15` — `typecorecrum *grimreaper` global
- `backend/credel.c:518-532` — `createcrum` adds new crum to circular list
- `backend/credel.c:54-76` — `ealloc` triggers `grimlyreap()` on allocation failure
- `backend/credel.c:106-162` — grim reaper eviction: age-based scan, write modified, free

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-UNIFIED-STORAGE], [ST-INSERT], [INV-DURABILITY-BOUNDARY], [EC-CRASH-MID-WRITE], [EC-CROSS-ENFILADE-EVICTION], [EC-NO-STARTUP-VALIDATION]

---

### SS-WHEREONCRUM

**Source:** Finding 0062

**What happens:** `whereoncrum()` classifies a tumbler address relative to a POOM crum's interval [grasp, reach). It computes `left = offset + cdsp` (the grasp) and `right = left + cwid` (the reach), then returns a five-way spatial classification:
- `TOMYLEFT` (-2): address < grasp
- `ONMYLEFTBORDER` (-1): address == grasp
- `THRUME` (0): grasp < address < reach (interior)
- `ONMYRIGHTBORDER` (1): address == reach (right boundary)
- `TOMYRIGHT` (2): address > reach

The critical distinction is that `address == reach` returns ONMYRIGHTBORDER, not THRUME. The reach is the exclusive endpoint of the half-open interval, so a position at the reach is classified as "on the boundary" rather than "inside." This five-way classification (identical to `intervalcmp` from SS-INTERVAL-CMP) drives all downstream insertion logic — different classifications trigger fundamentally different code paths in `findsontoinsertundernd` and `makegappm`.

**Why it matters for spec:** `whereoncrum` is the decision function for INSERT's tree traversal and knife-cutting logic. The formal model needs: `whereoncrum(crum, addr) : IntervalPos` where `IntervalPos = {ToLeft, OnLeft, Through, OnRight, ToRight}`. The ONMYRIGHTBORDER case is the linchpin for coalescing — it prevents splits and enables extension. A Dafny model should define this as a pure function and prove that it is consistent with the half-open interval semantics: `whereoncrum(crum, crum.reach) == OnRight`.

**Code references:**
- `retrie.c:345-372` — `whereoncrum()` full implementation with five-way switch
- `common.h:86-90` — constant definitions: TOMYLEFT=-2, ONMYLEFTBORDER=-1, THRUME=0, ONMYRIGHTBORDER=1, TOMYRIGHT=2

**Concrete example:**
```
Crum covers [v, v+1) (grasp=v, width=1, reach=v+1):

whereoncrum(crum, v-1) → TOMYLEFT (-2)
whereoncrum(crum, v)   → ONMYLEFTBORDER (-1)
whereoncrum(crum, v+0.5) → THRUME (0)
whereoncrum(crum, v+1) → ONMYRIGHTBORDER (1)   ← NOT THRUME
whereoncrum(crum, v+2) → TOMYRIGHT (2)
```

**Provenance:** Finding 0062
**Co-occurring entries:** [PRE-INSERT], [ST-INSERT], [INV-CRUM-BOUND], [EC-BOUNDARY-INSERT-CLASSIFICATION]

---

### SS-ENFILADE-BRANCHING

**Source:** Finding 0070

**What happens:** Enfilade tree shape is governed by three hard-coded branching constants in `enf.h` that set maximum children per node. The limits are type-aware and height-aware:

| Constant | Value | Scope |
|----------|-------|-------|
| `MAXUCINLOAF` | 6 | Upper crums (height > 1), all enfilade types |
| `MAX2DBCINLOAF` | 4 | Bottom crums (height 0-1) in 2D enfilades (SPAN, POOM) |
| `MAXBCINLOAF` | 1 | Bottom crums in 1D enfilades (GRAN) |

The GRAN bottom limit of 1 means granfilades are effectively lists at the bottom level, with B-tree structure only in upper levels. The comment "so text will fit" indicates this is a deliberate design choice tied to the data model, not a tuning parameter.

These constants are baked into the on-disk format: `coredisk.h:56` declares `ducarray[MAXUCINLOAF]` in the disk upper crum structure, so changing the branching factor requires a format migration.

**Why it matters for spec:** The branching constants define the domain of valid node states. Any enfilade invariant about node occupancy must reference these type-dependent and height-dependent bounds. A formal model needs a function `max_children(height, enfilade_type) -> nat` that returns the correct limit for each context. Tree depth is bounded by `O(log_6(N))` for upper levels.

**Code references:**
- `backend/enf.h:26-28` — constant definitions
- `backend/coredisk.h:50,56` — disk layout arrays sized by `MAXUCINLOAF`

**Provenance:** Finding 0070
**Co-occurring entries:** [PRE-SPLIT], [INV-ENFILADE-OCCUPANCY], [EC-GRAN-BOTTOM-SINGLETON]

---

### SS-POOM-MUTABILITY

**Source:** Finding 0072

**What happens**: The POOM (Permutation of the Original Material) enfilade for each document is a mutable tree structure. It is the only mutable layer in the data model — the granfilade is append-only and the spanfilade is write-only. The POOM maps V-addresses to I-addresses and is modified in-place by INSERT (adds new leaf nodes), DELETE (removes and frees leaf nodes), and REARRANGE (restructures mappings). There are no copy-on-write semantics, no shadow copies, and no journaling at the POOM level.

**Why it matters for spec**: The state model must distinguish mutable from immutable components:

```
State = {
  granfilade: I-addr → byte          -- immutable, append-only
  spanfilade: I-addr → {doc-ISA}     -- immutable, write-only (no delete)
  pooms: doc-ISA → (V-addr → I-addr) -- MUTABLE, modified in-place
}
```

The POOM is the sole locus of destructive mutation. All state transitions (ST-INSERT, ST-DELETE, ST-REARRANGE) operate on POOMs. Invariants about content permanence (INV-IADDR-IMMUTABILITY) hold because they apply to the granfilade, not the POOM.

**Code references**:
- `backend/orglinks.c:145-152` — `deletevspanpm`: calls `deletend` on the document's POOM orgl directly
- `backend/edit.c:31-76` — `deletend`: mutates the POOM tree in-place

**Provenance**: Finding 0072
**Co-occurring entries:** [ST-DELETE], [ST-VERSION-CREATE], [FC-VERSION-ISOLATION], [INV-DELETE-NOT-INVERSE]

---

### SS-POOM-BOTTOM-CRUM

**Source:** Finding 0076

**What happens:** POOM bottom crums store dual-space coordinates with asymmetric tumbler precision. Each crum contains an origin and width in both V-space and I-space, but the tumbler representations have different lengths: I-addresses use 6-9 tumbler digits (e.g., `0.0.0.0.0.0.0.0.11`), while V-addresses use 2 tumbler digits (e.g., `0.5`, `1.1`). The widths mirror their respective address-space precision — an I-width is a full-length I-space tumbler, while a V-width is encoded at V-space precision using the V-address tumbler length as the exponent.

A POOM bottom crum has the structure:
```
BottomCrum = {
  origin: { dsas[I]: Tumbler,  dsas[V]: Tumbler },
  width:  { dsas[I]: Tumbler,  dsas[V]: Tumbler }
}
```

Where `tumblerlength(origin.dsas[I]) >> tumblerlength(origin.dsas[V])` in practice (9 vs 2 digits).

**Why it matters for spec:** The state structure for POOM crums must model each dimension's precision independently. A formal `BottomCrum` type cannot use a single tumbler type for both dimensions — the V and I components have structurally different representations of the same numeric width value. Any spec that models POOM crums must account for this precision asymmetry, particularly in width fields.

**Code references:**
- `orglinks.c:100-117` — `insertpm` creates bottom crums with asymmetric V/I encoding
- `tumble.c:259-262` — `tumblerlength()` returns `nstories(t) - t->exp`

**Concrete example:**
```
After inserting 11 characters at V-position 1.1:
  Crum I-origin: 0.0.0.0.0.0.0.0.11  (9 digits)
  Crum I-width:  0.0.0.0.0.0.0.0.11  (9 digits, direct copy from I-space span)
  Crum V-origin: 0.5                  (2 digits)
  Crum V-width:  0.11                 (2 digits, re-encoded at V-space precision)

Both widths represent the value 11, but at different tumbler precisions.
```

**Provenance:** Finding 0076
**Co-occurring entries:** [ST-INSERT-VWIDTH-ENCODING], [INV-WIDTH-VALUE-EQUIVALENCE], [EC-VWIDTH-ZERO-ADDRESS]

---

### SS-CONTEXT-LIST

**Source:** Finding 0078

**What happens:** Contexts discovered during B-tree retrieval are accumulated into a singly-linked list via `nextcontext` pointers. Two distinct accumulation strategies exist: `incontextlistnd()` maintains sorted order by insertion-sort (used for N-dimensional enfilades where tree order does not guarantee V-order), and `oncontextlistseq()` appends to the end preserving tree traversal order (used for 1D GRAN enfilades where sequential order is maintained by tree structure). The choice of accumulation function depends on the enfilade type being queried.

**Why it matters for spec:** The formal model needs two distinct list-building strategies. For POOM (2D) queries, the result type is `SortedSeq<Context>` with the V-sorted invariant. For GRAN (1D) queries, the result type is `Seq<Context>` where order reflects tree traversal. This distinction matters because GRAN tree structure preserves sequential order (by design of 1D enfilades), while POOM tree structure does not preserve V-order (due to 2D diagonal ordering per Finding 0071). The spec should not assume a single uniform ordering guarantee across all enfilade types.

**Code references:**
- `context.c:75-111` — `incontextlistnd()` sorted insertion for N-dimensional enfilades
- `context.c:113-123` — `oncontextlistseq()` sequential append for 1D enfilades

**Provenance:** Finding 0078
**Co-occurring entries:** [FC-RETRIEVAL-TREE-INDEPENDENCE], [INV-RETRIEVAL-V-SORTED]

---

## Preconditions

> When an operation is valid — what must hold before

### PRE-SPECSET

**Source:** Finding 0001

**What happens:** The backend's `specset2sporglset()` validates specsets at document granularity only. It checks that the referenced document exists but does not enforce element-level tumbler structure. A specset referencing a valid document but with missing or malformed element fields is accepted without error.

**Why it matters for spec:** This defines the precondition boundary for specset-consuming operations (link retrieval, etc.). The precondition is: `exists doc : doc_id(tumbler) in created_documents`. There is explicitly no precondition requiring well-formed element addressing — that responsibility falls to the client. This means the backend's validation is weaker than the full docuverse convention would imply.

**Code references:** `specset2sporglset()` in the backend performs the document-existence check.

**Concrete example:**
- `VSpec(Address(1,1,0,1,0,2), [...])` — accepted if document 2 exists, even though this is a document-level address rather than an element address
- `VSpec(Address(1,1,0,1,0,1,0,2,N), [...])` — the correctly formed element-level address for document 1, link N

**Provenance:** Finding 0001
**Co-occurring entries:** [SS-TUMBLER], [INT-CLIENT-VALIDATION]

---

### PRE-REARRANGE

**Sources:** Findings 0006, 0051, 0056

#### Finding 0006

**What happens:** The REARRANGE operation rejects invalid cut counts. Providing 2 cuts (which would be ambiguous — not enough to define either a pivot or a swap) causes the backend to abort with the error message "Wrong number of cuts". The valid cut counts are exactly 3 (pivot) and 4 (swap).

**Why it matters for spec:** Precondition for REARRANGE: `pre_rearrange(doc, cuts) ≡ |cuts| = 3 ∨ |cuts| = 4`. Violations produce an error rather than undefined behavior. This is explicit input validation at the backend level.

**Provenance:** Finding 0006

#### Finding 0051

**What happens:** REARRANGE (pivot/swap) does not validate whether the computed offsets would move content across subspace boundaries. The `rearrangend()` function in `edit.c:78-160` calls `makeoffsetsfor3or4cuts()` to compute displacement vectors from the cut points, then applies `tumbleradd` to shift each orgl's V-position by the computed offset. There is no check that the resulting V-position shares the same leading digit (subspace) as the original. With cuts at 1.1, 1.4, and 2.5, `diff[1] = 2.5 - 1.4 = 1.1`, so content at V:1.1–1.3 is displaced to V:2.2–2.4, crossing from text subspace (1.x) to link subspace (2.x).

**Why it matters for spec:** REARRANGE has a missing precondition: all cut points must lie within the same subspace, OR the resulting displacements must preserve subspace membership for every affected orgl. Formally: `requires ∀ orgl ∈ affected(cuts): subspace(vpos(orgl) + diff[section(orgl)]) == subspace(vpos(orgl))`. Without this, REARRANGE provides a second path (after INSERT, per finding 0049) to violate the content discipline. The spec's `pre(REARRANGE)` must include a subspace-preservation clause even though the implementation does not enforce it.

**Code references:**
- `backend/edit.c:78-160` — `rearrangend()` applies `tumbleradd` without subspace check
- `backend/edit.c:125` — `tumbleradd(&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index])` — the displacement add
- `backend/edit.c:164-183` — `makeoffsetsfor3or4cuts()` computes offsets purely from cut-point differences

**Concrete example:**
```
Pre-state:
  Document with text "ABC" at V:1.1–1.3 and "DEF" at V:1.5–1.7

REARRANGE pivot with cuts at [1.1, 1.4, 2.5]

Offset computation:
  diff[1] = 2.5 - 1.4 = 1.1   (section 1: content between cut[0] and cut[1])
  diff[2] = -(1.4 - 1.1) = -0.3  (section 2: content between cut[1] and cut[2])

Post-state:
  "ABC" (originally at V:1.1–1.3) now at V:2.2–2.4  ← crossed to link subspace
  "DEF" (at V:1.5–1.7) remains at V:1.5–1.7          ← outside cut range, unchanged
  vspanset: {at 0 for 0.2, at 1 for 1}
  retrieve at 2.x returns "ABC" — text bytes in link subspace
```

**Provenance:** Finding 0051

#### Finding 0056

**What happens:** Cut points are specified in the **pre-move address space**. The algorithm reads current V-positions, computes offsets from the cut positions via `makeoffsetsfor3or4cuts()` (which takes only `knives->blades[]`), and applies offsets — no reference to post-move state exists. Additionally, `sortknives()` reorders cuts into ascending order, so misordered inputs are silently accepted and normalized rather than rejected.

**Why it matters for spec:** The precondition domain is the current document state: `∀ i: cuts[i] ∈ v_space(doc_before)`. The sort-before-use behavior means the precondition does not require ordered input: `pre_rearrange(doc, cuts) ≡ |cuts| ∈ {3,4}` — ordering is not a precondition because the implementation normalizes it. This is a robustness property that the spec should capture: the operation is commutative in its cut arguments (up to sorting).

**Code references:** `backend/edit.c:107` — `sortknives(&knives)`; `backend/edit.c:164-184` — offset computation references only `knives->blades[]`

**Provenance:** Finding 0056 (extends Finding 0006)

**Co-occurring entries:** [PRE-OPEN-DOC], [ST-REARRANGE], [ST-REMOVE], [INV-REARRANGE-IDENTITY], [INV-SUBSPACE-CONVENTION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-REARRANGE-CROSS-SUBSPACE], [EC-REARRANGE-EMPTY-REGION]

---

### PRE-OPEN-DOC

**Sources:** Findings 0006, 0014

#### Finding 0006

**What happens:** The backend rejects attempts to open a document that is already open in the current session, even if the requested access mode differs (e.g., opening as READ_WRITE then attempting READ_ONLY). Only one handle per document is permitted at a time. To change access mode, the document must be closed and reopened.

**Why it matters for spec:** Precondition for open: `pre_open(session, docid, mode) ≡ docid ∉ open_docs(session)`. This is a session-level constraint, not a document-level one — multiple sessions could each have the same document open (not tested here, but the constraint is per-session). The spec must model an open-document set per session: `session.open_docs : set<DocId>`, with open adding to and close removing from this set.

**Code references:** Backend error on duplicate open; `addtoopen` in backend stderr

**Provenance:** Finding 0006

#### Finding 0014

**What happens:** The `checkforopen` function implements an access control state machine that determines whether a document open request is granted, denied, or requires opening the document first. The decision depends on: (1) whether the document is already open, (2) the existing access level, (3) whether the request comes from the same connection, and (4) the requested access level.

The state machine returns:
- `>0` (access type): access granted
- `0`: document needs to be opened first
- `-1`: access denied (client should create a new version instead)

Key rules:
- READ request on a document not yet open → 0 (need to open)
- READ request on a document already open for READ by same connection → READ (granted)
- READ request on a document open for WRITE by same connection → WRITE (upgraded, granted)
- READ request on a document open for WRITE by different connection → -1 (denied)
- WRITE request on an unowned document that is not open → -1 (denied)
- WRITE request on an owned document that is not open → 0 (need to open)
- WRITE request on a document open for READ by any connection → -1 (denied)
- WRITE request on a document open for WRITE by same connection → WRITE (granted)
- WRITE request on a document open for WRITE by different connection → -1 (denied)

**Why it matters for spec:** This is the core precondition for all document mutation. The access control matrix fully determines which operations can proceed. The -1 return value ties directly into the versioning model — denied writes are redirected to version creation, supporting non-destructive editing.

**Concrete example:**
- Connection A opens doc 1.0.1.0.1 for WRITE → granted
- Connection B requests READ on doc 1.0.1.0.1 → denied (-1), B should create a version
- Connection A requests READ on doc 1.0.1.0.1 → returns WRITE (existing higher access)

**Code references:** `bert.c:43-50` (`checkforopen`), `do2.c` (`doopen`, `doclose`)

**Provenance:** Finding 0014

**Co-occurring entries:** [SS-BERT], [PRE-REARRANGE], [ST-REARRANGE], [ST-REMOVE], [INV-READ-SHARING], [INV-WRITE-EXCLUSIVITY], [INT-BERT-VERSION], [EC-COMPARE-VERSIONS-LINK-CRASH]

---

### PRE-COMPARE-VERSIONS

**Sources:** Findings 0009, 0011, 0015

#### Finding 0009

**What happens**: For `compare_versions` to operate correctly, the input V-span sets must be restricted to the text subspace (`V >= 1.0`). The operation's logic — I-span intersection to find shared content — is only semantically valid for permascroll I-addresses. Including the link subspace (`V < 1.0`) introduces link orgl ISAs that are identity-bearing (unique, non-comparable) rather than content-bearing (shared via transclusion).

**Why it matters for spec**: This is a missing precondition. The implementation does not validate that input V-spans exclude the link subspace. A formal spec should either: (a) state `compare_versions` requires text-subspace-only input, or (b) specify that the implementation filters to text subspace as its first step.

**Code references**:
- `correspond.c` — no filtering of V-spans before I-span conversion

**Provenance**: Finding 0009

#### Finding 0011

**What happens:** `compare_versions` assumes its inputs follow conventions — specifically that V-spans are in the text subspace. When link-subspace spans are passed (violating the convention), the operation crashes (Bug 0009). This is a direct consequence of the convention-over-enforcement philosophy: the operation has an implicit precondition that inputs are text-subspace spans.

**Why it matters for spec:** The precondition for `compare_versions` must explicitly require that input V-spans are in the text subspace (V-position 1.x). This precondition is not checked at runtime but is necessary for correct behavior.

**Code references:**
- Bug 0009 — crash when compare_versions receives link-subspace spans
- `correspond.c` — iteration assumes text-subspace data layout

**Provenance:** Finding 0011

#### Finding 0015

**What happens**: The `compare_versions` operation requires that input V-span sets be restricted to the text subspace (`V >= 1.0`). The finding specifies a concrete missing step: between retrieving V-spans and converting them to I-spans, the implementation must **filter to text subspace only**. Without this filter, link subspace V-spans (`0.x`) produce link orgl ISAs that are in a different address space from permascroll I-addresses. These will never intersect with text I-addresses (correct) but the code paths in `correspond.c` do not handle empty intersections gracefully (crash).

The finding frames this not as a defensive workaround but as the **semantically correct behavior**: the operation is defined over text content with common origin, and links have no "common origin" in this sense.

**Why it matters for spec**: The precondition can be expressed two equivalent ways: (a) `requires forall span :: span in input_vspanset ==> span.start >= V_TEXT_START`, placing the obligation on the caller; or (b) the operation's first step is `vspanset = filter_to_text_subspace(vspanset)`, internalizing the constraint. The finding argues for (b) — filtering is part of the operation's definition, not an external precondition.

**Code references**:
- `correspond.c` — retrieves ALL V-spans including `0.x`, no filtering step before `vspanset2ispanset`

**Concrete example**:
```dafny
method CompareVersions(doc_a: DocumentId, doc_b: DocumentId)
  requires ValidDocument(doc_a) && ValidDocument(doc_b)
  returns (correspondences: seq<(VSpan, VSpan)>)
  ensures forall (span_a, span_b) in correspondences ::
    span_a.start >= V_TEXT_START &&
    span_b.start >= V_TEXT_START &&
    ContentOrigin(doc_a, span_a) == ContentOrigin(doc_b, span_b)
```

Correct algorithm:
1. Retrieve V-spans from both documents (current behavior)
2. **Filter to text subspace only (V >= 1)** (missing step)
3. Convert V-spans to I-spans (current behavior)
4. Find common I-addresses (current behavior)
5. Map back to V-spans in each document (current behavior)

**Provenance**: Finding 0015, also Finding 0009

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DUAL-ENFILADE], [PRE-INSERT], [ST-COMPARE-VERSIONS], [ST-INSERT], [FC-SUBSPACE], [INV-SUBSPACE-CONVENTION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-ERROR-ABORT]

---

### PRE-RETRIEVE-CONTENTS

**Sources:** Findings 0010, 0027

#### Finding 0010

**What happens**: The `doretrievev` operation (`do1.c:376-384`) converts a specset to I-spans via `specset2ispanset`, then looks up content in the permascroll via `ispanset2vstuffset(taskptr, granf, ispanset, vstuffsetptr)`. It passes `granf` (the global enfilade) which expects permascroll I-addresses. If the specset includes V-positions from the link subspace (`0.x`), the corresponding I-addresses are link orgl ISAs, not permascroll addresses. Looking up a link ISA in the permascroll produces NULL or garbage bytes — a silent failure.

**Why it matters for spec**: This is a missing precondition. `doretrievev` requires that the input specset be restricted to the text subspace (`V >= 1.0`). The spec should either: (a) state this as a precondition, or (b) require the implementation to filter specset to text subspace before permascroll lookup. The silent failure mode (returning garbage rather than an error) makes this especially important for formal verification — an uncaught precondition violation produces unsound results rather than crashing.

**Code references**:
- `do1.c:376-384` — `doretrievev()` passes all I-addresses to permascroll lookup
- `orglinks.c:389-422` — `permute()` type-agnostic V↔I conversion

**Concrete example**:
```
Document has: V 0.1 → I 1.1.0.1.0.2 (link ISA)
              V 1.1..1.16 → I 2.1.0.5.0.1.. (permascroll)

doretrievev(specset covering V 0.0..2.0):
  specset2ispanset → includes I-address 1.1.0.1.0.2 from link subspace
  ispanset2vstuffset(granf, {1.1.0.1.0.2, 2.1.0.5.0...}):
    permascroll lookup of 1.1.0.1.0.2 → not a permascroll address → NULL/garbage
    permascroll lookup of 2.1.0.5.0.1 → valid text bytes
  Result: client receives corrupt content (garbage mixed with valid text)
```

**Provenance**: Finding 0010

#### Finding 0027

**What happens**: `retrieve_contents` (FEBE opcode 5) requires that every document referenced by the input SpecSet is currently open. The operation calls `doretrievev`, which calls `specset2ispanset`, which calls `findorgl` for each document orgl referenced in the specset. If `findorgl` finds the orgl is not in the open list, the operation fails with a backend error. This is distinct from the subspace precondition (Finding 0010): even with correct text-subspace V-addresses, the operation fails if the target document is closed.

**Why it matters for spec**: The precondition for `retrieve_contents` must include: `forall doc in specset.referenced_documents: doc in open_docs`. This is a session-state precondition (depends on which documents the caller has opened), not a structural precondition (the specset itself is well-formed). Combined with Finding 0010's subspace precondition, the full precondition is: all referenced documents open AND all V-addresses in text subspace.

**Code references**:
- `do1.c` — `doretrievev` → `specset2ispanset` → `findorgl`
- `findorgl` — checks open document list, returns FALSE if not found
- Backend log: `orgl for 0.1.1.0.1.0.1~ not open in findorgl temp = 0`

**Concrete example**:
```
Pre-state:
  open_docs = {doc_B}
  doc_A is closed
  follow_link returned SpecSet S referencing spans in doc_A

retrieve_contents(S):
  specset2ispanset(S) calls findorgl(doc_A_orgl)
  findorgl checks open list → doc_A not found → returns FALSE
  Operation fails with "error response from back-end"

After open_document(doc_A):
  open_docs = {doc_A, doc_B}
  retrieve_contents(S) → succeeds, returns content bytes
```

**Provenance**: Finding 0027b

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-DOCUMENT-LIFECYCLE], [PRE-DELETE], [PRE-VCOPY], [ST-INSERT], [INV-SUBSPACE-CONVENTION], [INT-LINK-FOLLOW-LIFECYCLE], [INT-LINK-RETRIEVAL], [INT-TRANSCLUSION-INSERT-ORDER], [EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES]

---

### PRE-VCOPY

**Source:** Finding 0010

**What happens**: The `docopy` operation (`do1.c:45-65`) copies I-spans from a source specset into a destination document at V-position `vsaptr`. It performs no validation that the source I-address types match the destination subspace. Text I-addresses (permascroll) can be copied into the link subspace (`0.x`), and link ISAs can be copied into the text subspace (`1.x`). The `acceptablevsa` check is a no-op. This is especially dangerous during transclusion from documents with links: `retrieve_vspanset` returns spans for both `0.x` and `1.x`, and if a caller creates a specset from the full vspanset, `vcopy` copies ALL content including link references to the destination.

**Why it matters for spec**: The formal spec for `docopy` must include a precondition that the I-address types in the source specset are compatible with the destination V-subspace. Specifically: if `vsaptr` is in the text subspace (`>= 1.0`), all source I-addresses must be permascroll addresses; if in the link subspace (`< 1.0`), they must be link orgl ISAs. Without this, transclusion from a document with links silently copies link ISAs as text content, producing semantically meaningless bytes.

**Code references**:
- `do1.c:45-65` — `docopy()` with no type validation
- `do1.c:57` — `acceptablevsa(vsaptr, docorgl)` always returns TRUE
- `do2.c:110-113` — `acceptablevsa()` stub

**Concrete example**:
```
Document A: V 0.1 → link ISA 1.1.0.1.0.2
            V 1.1..1.16 → permascroll text

User vcopies full content of A into document B at V 1.1:
  retrieve_vspanset(A) → {0.1 for 0.1, 1.1 for 0.16}  (both subspaces)
  specset from full vspanset includes link ISA
  docopy(B, vsa=1.1, specset) → copies link ISA 1.1.0.1.0.2 into B's text subspace
  B now contains: V 1.1 → I 1.1.0.1.0.2 (link ISA masquerading as text)
  retrieve_contents(B) → dereferences link ISA in permascroll → garbage bytes
```

**Provenance**: Finding 0010
**Co-occurring entries:** [PRE-DELETE], [PRE-RETRIEVE-CONTENTS], [INV-SUBSPACE-CONVENTION], [INT-LINK-RETRIEVAL], [EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES]

---

### PRE-DELETE

**Sources:** Findings 0010, 0040, 0053, 0055, 0075

#### Finding 0010

**What happens**: The `dodeletevspan` operation (`do1.c:162-171`) deletes a V-span from a document without checking which subspace the span falls in. Deleting V-range `0.x` removes link references from the document — the link orgls still exist in the system, but the document loses its references to them, creating orphaned links. The operation is technically valid but semantically dangerous: the document can no longer find its own links.

**Why it matters for spec**: The spec should note that `dodeletevspan` on the link subspace severs the document-to-link association without destroying the link itself. This is a weaker deletion than destroying the link — the link's endpoints still reference content, but the document has no record of the link. A formal model should distinguish: (a) deleting text content (removes V→I mappings for permascroll addresses), (b) deleting link references (removes V→I mappings for link ISAs, orphaning links).

**Code references**:
- `do1.c:162-171` — `dodeletevspan()` no subspace check

**Concrete example**:
```
Pre-state:
  Document has: V 0.1 → link ISA 1.1.0.1.0.2
                V 1.1..1.16 → permascroll text
  Link orgl 1.1.0.1.0.2 exists with endpoints

dodeletevspan(doc, vspan={0.1 for 0.1}):
  Removes V 0.1 → I 1.1.0.1.0.2 mapping from document

Post-state:
  Document has: V 1.1..1.16 → permascroll text (links gone)
  Link orgl 1.1.0.1.0.2 still exists (orphaned — no document references it)
  find_links on document → finds nothing
  Link's endpoints still reference content positions
```

**Provenance**: Finding 0010

#### Finding 0040

**What happens:** `DELETEVSPAN` accepts link subspace addresses (V-position 2.x) as valid targets. The only precondition enforced by `deletevspanpm()` is that the width is non-zero — `iszerotumbler(&vspanptr->width)` returns FALSE. There is no check preventing deletion of the link subspace. The backend treats link positions identically to text positions for deletion purposes.

This means link "permanence" within a document's POOM is a front-end convention, not a backend enforcement. The backend will execute `DELETEVSPAN(2.1)` just as readily as `DELETEVSPAN(1.5)`.

**Why it matters for spec:** The precondition for DELETE does not distinguish subspaces: `pre_delete(D, addr, width) ≡ width ≠ 0`. There is no predicate `addr.subspace ≠ LINK_SUBSPACE` guarding the operation. If the spec wants to preserve link-in-POOM permanence, it must be modeled as a front-end-enforced policy, not a backend invariant.

**Code references:**
- `orglinks.c:145-152` — `deletevspanpm()` only checks for zero-width, no subspace guard

**Provenance:** Finding 0040, Code Evidence section and EWD Specifications section.

#### Finding 0053

**What happens:** DELETE does not validate whether V-position shifting will produce negative tumblers. The `deletend()` function processes all POOM entries after the deletion point uniformly — it subtracts the deletion width without checking whether the result would be negative. The only existing precondition for DELETE is non-zero width (checked in `deletevspanpm()`). There is no guard of the form `entry.vpos >= delete_width` for shifted entries.

This is a missing precondition: the backend accepts DELETE operations that corrupt POOM entries by shifting them to negative V-positions. The corruption is silent — no error is returned, and the entries become invisible rather than being removed or flagged.

**Why it matters for spec:** A complete precondition for DELETE should include: `∀ entry ∈ poom(doc) : entry.vpos > delete_end ⟹ entry.vpos - delete_width ≥ 0`. The current implementation does not enforce this. For formal verification, this is a case where the spec should document both the ideal precondition (what should hold) and the actual behavior (what happens when it's violated — negative tumblers, invisible entries).

**Code references:**
- `orglinks.c:145-152` — `deletevspanpm()` only checks zero-width
- `edit.c:31-76` — `deletend()` Case 2, no bounds check before subtraction

**Provenance:** Finding 0053

#### Finding 0055

**What happens:** Finding 0053's claim that DELETE lacks a guard against negative V-positions for cross-subspace entries is incorrect. The `strongsub` exponent guard acts as an implicit precondition that prevents cross-exponent subtraction from occurring at all. For same-exponent entries within the deletion subspace, the question of negative V-positions producing invisible entries remains open — but this is constrained to within-subspace entries only, not cross-subspace entries.

The missing precondition concern from Finding 0053 is narrower than claimed: it only applies to entries within the same subspace and at the same exponent level as the deletion width. Cross-subspace entries (links at exp=0 vs text deletion width at exp=-1) are categorically unaffected.

**Why it matters for spec:** The precondition for DELETE need not guard against cross-subspace corruption because `strongsub` makes such corruption impossible. Any formal precondition about negative V-positions should be scoped to same-exponent entries: `∀ entry : entry.vpos > delete_end ∧ entry.vpos.exp = width.exp ==> entry.vpos - delete_width ≥ 0` (if this is desired as a safety invariant).

**Code references:**
- `tumble.c:534-547` — `strongsub` exponent guard provides implicit precondition
- `edit.c:63` — Case 2 subtraction, the only site where negative V-positions could arise

**Provenance:** Finding 0055

#### Finding 0075

**What happens:** The DELETE Phase 1 cutting mechanism (`slicecbcpm`) has an enforced precondition: it is only invoked when the cut point falls strictly in the interior of a bottom crum. The `makecutsbackuptohere()` function in `ndcuts.c:77-90` checks `whereoncrum() == THRUME` before calling `slicecbcpm`. The `whereoncrum()` function (`retrie.c:345-372`) classifies cut positions into five categories: `TOMYLEFT` (-2), `ONMYLEFTBORDER` (-1), `THRUME` (0), `ONMYRIGHTBORDER` (1), `TOMYRIGHT` (2). Only `THRUME` — meaning `grasp < cut < reach` with both strict inequalities — triggers a call to `slicecbcpm`.

When a DELETE boundary aligns exactly with a crum's grasp, `whereoncrum` returns `ONMYLEFTBORDER`; when it aligns with a crum's reach, it returns `ONMYRIGHTBORDER`. In both cases, `slicecbcpm` is skipped. The crum is instead handled whole in Phase 2 (classify and remove/shift).

**Why it matters for spec:** This establishes a precondition on the `slicecbcpm` operation: `pre_slicecbcpm(cut, crum) ≡ crum.grasp < cut < crum.reach`. The precondition is enforced by the caller (`makecutsbackuptohere`), not by `slicecbcpm` itself. For a formal DELETE model, the cutting step can be specified as: `∀ blade ∈ knives, ∀ crum ∈ bottom_crums : whereoncrum(blade, crum) = THRUME ⟹ split(crum, blade)`. Boundary-aligned blades do not trigger splits.

**Code references:**
- `ndcuts.c:77-90` — `makecutsbackuptohere()`: guard `whereoncrum() == THRUME` before `slicecbcpm`
- `retrie.c:345-372` — `whereoncrum()`: five-valued classification of cut position relative to crum
- `common.h:86-90` — Constants: `TOMYLEFT=-2, ONMYLEFTBORDER=-1, THRUME=0, ONMYRIGHTBORDER=1, TOMYRIGHT=2`

**Concrete example:**
```
Crum: [1.1, 1.4)  (grasp=1.1, reach=1.4, content="ABC")

DELETE [1.1, 1.4):   (exact alignment on both sides)
  whereoncrum(1.1, crum) → ONMYLEFTBORDER  → no cut
  whereoncrum(1.4, crum) → ONMYRIGHTBORDER → no cut
  slicecbcpm NOT called; crum handled whole in Phase 2

DELETE [1.1, 1.3):   (start aligned, end interior)
  whereoncrum(1.1, crum) → ONMYLEFTBORDER  → no cut
  whereoncrum(1.3, crum) → THRUME          → slicecbcpm called
  localcut = 1.3 - 1.1 = 0.2 (strictly positive, strictly < cwid 0.3)

DELETE [1.2, 1.4):   (start interior, end aligned)
  whereoncrum(1.2, crum) → THRUME          → slicecbcpm called
  whereoncrum(1.4, crum) → ONMYRIGHTBORDER → no cut
  localcut = 1.2 - 1.1 = 0.1 (strictly positive, strictly < cwid 0.3)
```

**Provenance:** Finding 0075

**Co-occurring entries:** [SS-THREE-LAYER-MODEL], [SS-TUMBLER], [PRE-RETRIEVE-CONTENTS], [PRE-VCOPY], [ST-DELETE], [FC-LINK-DELETE-ISOLATION], [FC-SUBSPACE], [INV-LINK-PERMANENCE], [INV-NO-ZERO-WIDTH-CRUM], [INV-POOM-BIJECTIVITY], [INV-SUBSPACE-CONVENTION], [INT-DELETE-SUBSPACE-ASYMMETRY], [INT-LINK-RETRIEVAL], [EC-DEEPLY-ORPHANED-LINK], [EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES], [EC-REVERSE-ORPHAN]

---

### PRE-INSERT

**Sources:** Findings 0011, 0036, 0042, 0049, 0050, 0062

#### Finding 0011

**What happens:** Preconditions for operations like insert, copy, and rearrange are implicit conventions, not enforced at runtime. The `acceptablevsa` function in `do2.c:110-113` always returns `TRUE`, meaning any V-position is accepted regardless of whether it follows the subspace convention (0.x for links, 1.x for text). Callers must know and follow the convention; the system does not validate.

**Why it matters for spec:** Formal preconditions must be explicitly stated in the specification even though the implementation does not enforce them. Every operation that accepts a V-position has an implicit precondition that the V-position falls within the appropriate subspace for the data type being stored. Dafny `requires` clauses must capture what the C code merely assumes.

**Code references:**
- `backend/green/do2.c:110-113` — `acceptablevsa` always returns TRUE
- Caller conventions for `docopy`, insert operations

**Concrete example:**
- Before: System receives a store operation with V-position `0.1.5` and text content
- Expected: Validation rejects (0.x is link subspace, not text)
- Actual: Operation succeeds silently, placing text in the link subspace, corrupting the document's semantic structure

**Provenance:** Finding 0011

#### Finding 0036

**What happens:** INSERT's call chain through `docopy` includes several precondition checks before DOCISPAN creation: `findorgl(taskptr, granf, docisaptr, &docorgl, WRITEBERT)` verifies the document exists and is writable; `acceptablevsa(vsaptr, docorgl)` validates the V-address is acceptable for the document's current state; `asserttreeisok(docorgl)` validates structural integrity. All must succeed (boolean AND chain) before `insertpm` and `insertspanf` execute.

**Why it matters for spec:** INSERT precondition: the document ISA must exist in granf, the document must be writable, and the target V-address must be valid for the document. Formally: `pre(INSERT(doc, vsa, text)) = doc ∈ granf ∧ writable(doc) ∧ valid_vsa(vsa, doc)`.

**Code references:**
- `do1.c:45-65` — `docopy()` precondition chain: `findorgl`, `acceptablevsa`, `asserttreeisok`
- `do1.c:91-127` — `doinsert()` also calls `makehint(DOCUMENT, ATOM, TEXTATOM, ...)` before `inserttextingranf`

**Provenance:** Finding 0036.

#### Finding 0042

**What happens:** I-address allocation via `findisatoinsertgr()` uses a global search-and-increment to find fresh addresses. This is safe without locking because the single-threaded event loop guarantees no concurrent allocations.

**Why it matters for spec:** The precondition for INSERT includes that the allocated I-address is globally unique. This property (called P1/Freshness in EWD-025) is guaranteed by sequential execution rather than by an explicit uniqueness check. A formal spec should state the freshness precondition explicitly even though the implementation achieves it structurally.

**Code references:**
- `backend/granf2.c:203-242` — I-address allocation via search-and-increment

**Provenance:** Finding 0042

#### Finding 0049

**What happens:** INSERT does not validate that the caller-specified V-position falls within the text subspace (1.x). The `acceptablevsa()` function in `do2.c:110-113` unconditionally returns `TRUE`. The only V-position checks in `insertpm()` are: (1) reject zero tumbler (lines 86-90), (2) reject negative tumbler (lines 93-98). Text content can be placed at V-position 2.1 (link subspace) via INSERT and it succeeds silently. The text is stored and retrievable at that position.

**Why it matters for spec:** INSERT has a missing precondition: `vsa ∈ text_subspace(1.x)`. The formal spec must add `requires vsa.head == 1` for text insertion. This is the placement-side gap — ENF0 prevents modification of existing link orgls but does not prevent placing new text content at arbitrary V-positions. The spec's `pre(INSERT)` must include subspace membership even though the implementation does not enforce it.

**Code references:**
- `backend/do2.c:110-113` — `acceptablevsa()` always returns TRUE
- `backend/orglinks.c:86-98` — `insertpm()` checks only zero and negative, not subspace
- `backend/do1.c:91-127` — `doinsert()` sets TEXTATOM hint but does not validate V-position subspace

**Concrete example:**
```
Pre-state:
  Document 1.1.0.1.0.1 with text at V:1.1..1.10

INSERT(doc=1.1.0.1.0.1, vsa=2.1, text="TextAtLinkPosition")

Post-state:
  INSERT succeeds (no error)
  vspanset now has TWO spans: {start:0, width:0.1} and {start:1, width:1}
  retrieve_contents(from=2.1, width=0.19) returns ["TextAtLinkPosition"]
  Text bytes are stored in link subspace — subspace convention violated
```

**Provenance:** Finding 0049

#### Finding 0050

**What happens:** The WRITE BERT precondition for INSERT (and all other state-modifying operations) is not enforced by the back end. `doinsert()` calls `findorgl(taskptr, granf, &docisa, &docorgl, WRITEBERT)`, which checks `checkforopen()`. If the check fails (`<= 0`), `findorgl` returns FALSE, and the operation silently does nothing. But the front end has already received a success response from `putinsert()`, which was called before `doinsert()`.

This means the precondition "caller holds WRITEBERT for the target document" is a *protocol obligation* that the front end must satisfy voluntarily. The back end does not reject operations that violate this precondition — it accepts them (sends success) and then silently discards them.

**Why it matters for spec:** The Dafny `requires` clause for INSERT (and DELETEVSPAN, REARRANGE, COPY) must state that the caller holds WRITEBERT. But the spec must also note that this precondition is *not validated* — violating it produces silent data loss (the operation appears to succeed but has no effect). This is a stronger claim than "convention over enforcement" from Finding 0011: the system actively misleads the caller about operation success.

**Code references:**
- `fns.c:84-98` — `insert()`: response sent at line ~90, operation attempted at line ~92
- `do1.c:162-171` — `dodeletevspan()`: `findorgl(..., WRITEBERT)` call
- `do1.c:34-43` — `dorearrange()`: same pattern
- `do1.c:45-65` — `docopy()`: same pattern

**Concrete example:**
- INSERT without WRITEBERT: front end receives success response, but `doinsert()` returns FALSE and document content is unchanged
- DELETEVSPAN without WRITEBERT: front end receives success response, but `dodeletevspan()` returns FALSE and no v-span is deleted

**Provenance:** Finding 0050

#### Finding 0062

**What happens:** `makegappm()` performs an early-exit check before constructing the two-blade knife: if the insertion point equals or exceeds the crum's reach, the knife cut is SKIPPED entirely. The condition `tumblercmp(&origin->dsas[V], &reach.dsas[V]) != LESS` evaluates to TRUE when origin >= reach. When origin == reach (the ONMYRIGHTBORDER case), this means `makegappm` returns 0 without cutting. The knife is never constructed, `makecutsnd` is never called, and the crum is not split.

This is the mechanism by which consecutive interior typing avoids crum proliferation. After an initial insert at position v creates a crum [v, v+1), a subsequent insert at v+1 triggers the early exit because v+1 == reach. No split occurs, and the insertion proceeds directly to the extension check.

**Why it matters for spec:** The precondition for the knife-cut sub-operation within INSERT is: `pre_knife_cut(crum, origin) = origin >= crum.grasp ∧ origin < crum.reach`. Equivalently, `whereoncrum(crum, origin) ∈ {ONMYLEFTBORDER, THRUME}`. When `whereoncrum(crum, origin) == ONMYRIGHTBORDER`, no knife cut is performed — this is an explicit guard, not an omission. For Dafny, this can be modeled as: `method makegappm(crum, origin) requires crum.grasp <= origin < crum.reach`.

**Code references:**
- `insertnd.c:137-143` — Early exit condition in `makegappm()`: `if (iszerotumbler(&fullcrumptr->cwid.dsas[V]) || tumblercmp(&origin->dsas[V], &grasp.dsas[V]) == LESS || tumblercmp(&origin->dsas[V], &reach.dsas[V]) != LESS) return(0);`

**Concrete example:**
```
Crum covers [1.3, 1.4) (grasp=1.3, width=0.1, reach=1.4)

INSERT at 1.3:  origin < reach → KNIFE CUT occurs (splits crum)
INSERT at 1.35: origin < reach → KNIFE CUT occurs (splits crum)
INSERT at 1.4:  origin == reach → NO knife cut (early exit, return 0)
INSERT at 1.5:  origin > reach  → NO knife cut (early exit, return 0)
```

**Provenance:** Finding 0062

**Co-occurring entries:** [SS-BERT], [SS-DOCISPAN], [SS-DUAL-ENFILADE], [SS-WHEREONCRUM], [PRE-COMPARE-VERSIONS], [PRE-ENF0-PLACEMENT-GAP], [ST-INSERT], [ST-INSERT-ACCUMULATE], [FC-CONTENT-SPANF-ISOLATION], [INV-ATOMICITY], [INV-CRUM-BOUND], [INV-SEQUENTIAL-DISPATCH], [INV-SUBSPACE-CONVENTION], [INV-WRITE-EXCLUSIVITY], [INT-BERT-FEBE], [EC-APPEND-NO-DOCISPAN], [EC-BOUNDARY-INSERT-CLASSIFICATION], [EC-ERROR-ABORT], [EC-RESPONSE-BEFORE-CHECK]

---

### PRE-CONTENT-ITERATION

**Source:** Finding 0017

**What happens**: To correctly iterate over all content in a document, callers must use `retrieve_vspanset` and process each span individually. Using the single bounding span from `retrieve_vspan` as a retrieval range will attempt to dereference V-positions in the gap between subspaces (producing empty or undefined results) and will mix link references (`0.x`) with text content (`1.x`) without distinguishing them. The finding prescribes per-span iteration as the correct access pattern.

**Why it matters for spec**: This establishes a usage precondition for document content access: correct iteration requires the spanset form, not the single-span form. Combined with the subspace convention (INV-SUBSPACE-CONVENTION), this means a caller must (1) retrieve the vspanset, (2) identify spans by subspace (`V < 1.0` → links, `V >= 1.0` → text), and (3) use appropriate retrieval operations per subspace. The spec for any "retrieve all content" operation should reference this two-step pattern.

**Code references**:
- Golden tests: `golden/documents/retrieve_vspan*.json`

**Provenance**: Finding 0017, also relates to Finding 0009 (SS-DUAL-ENFILADE) and Finding 0010 (EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES)
**Co-occurring entries:** [SS-VSPAN-VS-VSPANSET], [EC-VSPAN-MISLEADING-SIZE]

---

### PRE-LINK-CREATE

**Sources:** Findings 0020, 0028

#### Finding 0020

The precondition for link creation does not require source and target to be in different documents. An internal link where `home_doc == source_doc == target_doc` is valid. The operation succeeds, returning a link address under the home document's address space.

Concrete example:
- Document `1.1.0.1.0.1` contains text including "glossary" and "Glossary"
- `create_link(home_doc=1.1.0.1.0.1, source="glossary", target="Glossary", type="jump")`
- Result: success, link address `1.1.0.1.0.1.0.2.1`

**Why it matters for spec:** Defines the valid input domain for link creation. The precondition is: source content exists AND target content exists AND home_doc is valid. No cross-document constraint.

**Code references:** Test `links/self_referential_link`

**Provenance:** Finding 0020

#### Finding 0028

**What happens**: Links with single-character (width=1) endpoints are valid and succeed. Links with zero-width endpoints crash (Bug 0017). The minimum valid endpoint width for link creation is 1.

**Why it matters for spec**: Refines the link creation precondition: `link.source.width >= 1 AND link.target.width >= 1`. There is no minimum width greater than 1. Combined with Finding 0020 (no cross-document constraint), the full structural precondition for `create_link` is: source content exists AND target content exists AND both endpoint widths >= 1 AND home_doc is valid.

**Code references**: Tests `edgecases/minimum_width_link`, `edgecases/zero_width_link`; Bug 0017

**Concrete example**:
```
Valid (width=1):
  create_link(home, source=Span(1.1, 0.1), target=Span(1.12, 0.1), type=T) → success

Invalid (width=0):
  create_link(home, source=Span(1.1, 0.0), target=Span(1.12, 0.0), type=T) → CRASH
```

**Provenance**: Finding 0028 §10

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-LINK-CREATE], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-LINK], [EC-SELF-TRANSCLUSION]

---

### PRE-ADDRESS-ALLOC

**Source:** Finding 0021

**What happens**: The allocation search via `findpreviousisagr` must find only addresses that are actually under the target parent. Bug 0013 showed that without a containment check, the search crosses account boundaries: when allocating under account `1.1.0.2`, the search finds `1.1.0.1.0.1` (under a different account) and incorrectly increments from it, producing `1.1.0.1.0.2` — an address under the wrong account.

The fix adds a prefix-match check: after finding the highest address below the upper bound, verify it is actually contained under the target parent using tumbler truncation/comparison.

**Why it matters for spec**: This is a precondition on the allocation algorithm: the candidate address used as an increment base must be under the target parent. Without this, the monotonic allocation invariant holds locally but violates account isolation. This is a concrete example of flat storage requiring explicit hierarchical enforcement.

**Code references**: `granf2.c:findisatoinsertnonmolecule`, `findpreviousisagr`; Bug 0013.

**Concrete example**:
- Before fix: Allocating under `1.1.0.2` finds `1.1.0.1.0.1`, increments to `1.1.0.1.0.2` (WRONG — under account `1.1.0.1`).
- After fix: Allocating under `1.1.0.2` finds `1.1.0.1.0.1`, rejects it via containment check, falls back to first-child `1.1.0.2.0.1` (CORRECT).

**Provenance**: Finding 0021
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-TUMBLER-CONTAINMENT], [ST-ADDRESS-ALLOC], [INV-ACCOUNT-ISOLATION]

---

### PRE-FIND-LINKS

**Sources:** Findings 0025, 0029, 0069

#### Finding 0025

**What happens**: The `find_links` operation accepts a `homedocids` filter parameter. This parameter must be passed as I-spans (identity spans with start address + width), not as plain addresses. Passing a plain address causes a protocol hang. This is consistent with other query mechanisms in Xanadu — all filtering uses span-based specifications.

Correct usage:
```python
home_span = Span(doc_address, Offset(0, 1))
results = session.find_links(source_specs, NOSPECS, NOSPECS, [home_span])
```

**Why it matters for spec**: The precondition for `find_links` with home document filtering requires: `forall spec ∈ homedocids :: spec is ISpan`. This is a type constraint on the query interface. The spec should model query filters uniformly as span-based specifications rather than bare addresses.

**Code references**: Test `links/find_links_filter_by_homedocid`; `do1.c:386-391` — `dofindlinksfromtothree()`.

**Provenance**: Finding 0025

#### Finding 0029

**What happens:** `find_links()` requires that the searched endpoint content exists in the V-stream (visible view) to discover a link. The operation performs an intersection between the search specset and the link's endpoint specset; if the linked content has been deleted from the V-stream, the intersection is empty and the link is not found. Partial deletion is tolerated — as long as any portion of the original linked span remains, the link is discoverable.

**Why it matters for spec:** Defines the precondition for link discoverability. A link exists permanently but is only discoverable via `find_links()` when its endpoint content is present in the V-stream. This is not a precondition for validity (the call succeeds either way), but a precondition for non-empty results. Formalizable as: `find_links(spec) ≠ ∅ → ∃ overlap(spec ∩ V-stream, link.endpoint ∩ V-stream)`.

**Code references:** Test scenarios in `febe/scenarios/links/search_endpoint_removal.py`. Golden files in `golden/links/search_*.json`.

**Concrete example:**
- Before delete: `find_links(source_spec)` → `[link_id]`
- After deleting source content: `find_links(source_spec)` → `[]`
- Partial delete ("hyper" from "hyperlink"): remaining "link" still in V-stream → `[link_id]` still returned

**Provenance:** Finding 0029, sections 1, 3, 8

#### Finding 0069

**What happens:** The `find_links` operation accepts an orgl range parameter that is supposed to restrict which orgls (documents/links) are searched. However, `sporglset2linkset()` in `sporgl.c:222-237` contains a dead-code guard `if (TRUE||!homeset)` that always evaluates true, replacing whatever orgl range the caller provides with a hardcoded range of width 100 starting at tumbler zero. The original intent was `if (!homeset)` — supply a default range only when none is specified — but the `TRUE||` prefix makes the parameter permanently ignored. The caller `findlinksfromtothreesp()` in `spanf1.c:56-103` faithfully passes its `orglrange` argument through, but the callee discards it.

**Why it matters for spec:** The spec must document that `find_links` has no effective orgl-dimension precondition in the implementation. A formal spec could define `find_links(from_spec, to_spec, three_spec, orgl_range)` where `orgl_range` constrains results, but the implementation behaves as `find_links(from_spec, to_spec, three_spec, _)` — the orgl range is accepted syntactically but has no semantic effect. This is a known deviation: the specified interface promises scoping that the implementation does not deliver. A spec should either (a) model the intended behavior (orgl filtering works) and flag this as a known bug, or (b) model the actual behavior (orgl range ignored, search is global in the orgl dimension).

**Code references:**
- `sporgl.c:220-230` — `sporglset2linkset()` with the `TRUE||` always-true guard
- `spanf1.c:56-103` — `findlinksfromtothreesp()` passes `orglrange` to `sporglset2linkset`
- `retrie.c:56-85` — `retrieverestricted()` converts range to start/end spans (downstream of the override)

**Concrete example:**
```
Caller requests: find_links(orgl_range = document 1.1.0.1.0.1 only)

Expected behavior:
  Search restricted to links whose orgls are within document 1.1.0.1.0.1

Actual behavior:
  homeset parameter replaced with {stream: 0, width: 100}
  Search covers all orgls from 0 to 100 in the orgl dimension
  Links from any document are returned if they match on the span dimension
```

**Provenance:** Finding 0069

**Co-occurring entries:** [SS-LINK-HOME-DOCUMENT], [SS-SPANF-OPERATIONS], [ST-ADDRESS-ALLOC], [ST-FIND-LINKS], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE], [INT-TRANSCLUSION-LINK-SEARCH], [EC-FIND-LINKS-GLOBAL], [EC-HOMEDOCIDS-FILTER-BROKEN], [EC-SEARCH-SPEC-BEYOND-BOUNDS], [EC-TYPE-FILTER-NONFUNCTIONAL]

---

### PRE-ZERO-WIDTH

**Source:** Finding 0028

**What happens**: Zero-width (empty) spans have different validity depending on whether the operation is a query or a mutation:
- **Queries accept zero-width**: `retrieve_contents(Span(1.1, 0.0))` returns an empty list (success). `retrieve_contents(SpecSet())` returns an empty list (success).
- **Mutations reject zero-width**: `create_link` with zero-width endpoints crashes the backend (Bug 0017).

**Why it matters for spec**: The precondition for query operations (retrieve) permits zero-width spans: `span.width >= 0`. The precondition for mutation operations (at minimum link creation) requires non-zero width: `span.width > 0`. This is a query/mutation asymmetry in the validity domain. The spec should partition operations into these two classes and define appropriate width preconditions for each. Note: the crash behavior (rather than error return) for zero-width link creation indicates a missing precondition check in the implementation, not intended semantics.

**Code references**: Tests `edgecases/empty_span_retrieval`, `edgecases/zero_width_link`; Bug 0017

**Concrete example**:
```
Query (succeeds):
  retrieve_contents(Span(1.1, 0.0)) → [] (empty result, no error)

Mutation (crashes):
  create_link(home, source=Span(1.1, 0.0), target=Span(1.5, 0.0), type=T) → CRASH
```

**Provenance**: Finding 0028 §5
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### PRE-CONCURRENT-INSERT

**Source:** Finding 0041

Concurrent unsynchronized insertion into the same enfilade is unsafe. The `adopt(new, RIGHTBRO, ptr)` call modifies shared pointers, `father->numberofsons` can suffer lost updates, and split/rebalance operations assume exclusive access. Serialization is required for structural integrity.

**Why it matters for spec:** This is a precondition for safe multi-threaded permanent layer access. The spec should require mutual exclusion (or equivalent) around enfilade modification operations. However, since logical confluence holds (INV-ENFILADE-CONFLUENCE), any serialization order produces correct results — the choice of serialization strategy is an implementation freedom.

**Code references:**
- `backend/insert.c:43-46` — shared pointer modification in `adopt()`
- `backend/split.c:70-93` — `splitcrumseq()` assumes exclusive access to `father->numberofsons`

**Provenance:** Finding 0041
**Co-occurring entries:** [SS-DUAL-ENFILADE], [FC-ENFILADE-QUERY-INDEPENDENCE], [INV-ENFILADE-CONFLUENCE]

---

### PRE-COPY

**Source:** Finding 0046

**What happens:** The COPY operation performs NO duplicate checking before inserting V→I mappings into the target document's POOM. The `insertpm()` function in `orglinks.c:75-134` delegates to `insertnd()` in `insertnd.c:15-111`, which calls `isanextensionnd()` to check only whether the new content is contiguous with an existing crum — never whether the I-address already exists in the target. A COPY of I-addresses that already exist at some V-position in the target document is unconditionally accepted.

**Why it matters for spec:** The precondition for COPY does NOT include `iaddrs(source) ∩ iaddrs(target) = ∅`. A formal precondition should state: `pre_copy(source_doc, source_vspan, target_doc, target_vpos) = is_valid_doc(source_doc) ∧ is_valid_doc(target_doc) ∧ content_exists(source_doc, source_vspan)`. There is no uniqueness guard — the same I-address can intentionally appear at multiple V-positions via repeated COPY.

**Code references:**
- `insertpm()` — `orglinks.c:75-134` — POOM insertion wrapper, no duplicate guard
- `insertnd()` — `insertnd.c:15-111` — Main insertion logic, no duplicate guard
- `isanextensionnd()` — `insertnd.c:293-301` — Checks contiguity only, not uniqueness

**Concrete example:**
```
Source doc has "ABCDE" at I-addresses i₁..i₅.

COPY to target at V=1.1:  target POOM gets V 1.1..1.5 → i₁..i₅
COPY to target at V=1.10: target POOM gets V 1.10..1.14 → i₁..i₅  (no rejection)
COPY to target at V=1.8:  target POOM gets V 1.8..1.12 → i₁..i₅   (no rejection)

All three COPYs succeed. Same I-addresses now at three V-positions.
```

**Provenance:** Finding 0046
**Co-occurring entries:** [ST-VCOPY], [ST-VERSION-CREATE], [INV-IADDR-PROVENANCE], [INT-LINK-VERSION]

---

### PRE-FOLLOWLINK

**Source:** Finding 0048

**What happens:** FOLLOWLINK requires: (1) the link ISA must reference an existing link orgl — if `findorgl()` returns FALSE, the operation fails; (2) the `whichend` parameter selects endset position 1, 2, or 3. There is no precondition requiring that endset I-addresses be currently referenced in any POOM. The operation succeeds even when all endset I-addresses are unreferenced, returning an empty result rather than an error.

**Why it matters for spec:** The precondition is strictly about link existence, not about liveness of the content the link points to. This is a design choice: the back end returns what permanent storage contains, and the I-to-V conversion filters based on current POOM state. A spec must not add a "liveness" precondition — empty results from unreferenced I-addresses are valid successful outcomes, not errors.

**Code references:**
- `findorgl()` check: `backend/sporgl.c:76-78` — returns FALSE if link orgl not found
- No POOM check in `link2sporglset()`: `backend/sporgl.c:67-95`

**Provenance:** Finding 0048
**Co-occurring entries:** [ST-FOLLOWLINK], [INV-ITOV-FILTERING], [EC-GHOST-LINK]

---

### PRE-ENF0-PLACEMENT-GAP

**Source:** Finding 0049

**What happens:** ENF0 (`may-modify(orgl) ≡ element-type(orgl) ≠ LINKATOM`) prevents modification of existing link orgls but does not constrain where new content is placed. INSERT allocates fresh I-addresses via `inserttextingranf()` and places them at the caller-specified V-position via `docopy()`. Since the fresh orgl has no prior state, ENF0's target-type discipline does not apply. The element type (TEXTATOM) is set by `doinsert()` at `do1.c:121` via `makehint(DOCUMENT, ATOM, TEXTATOM, ...)`, but there is no validation that TEXTATOM content targets a 1.x V-position.

**Why it matters for spec:** ENF0 is a necessary but insufficient guard for I2/I4 preservation. The spec must distinguish two predicates: (1) `may-modify(orgl)` — existing ENF0, prevents mutation of link orgls; (2) `may-place-at(vpos, element_type)` — missing predicate, would enforce `element_type == TEXTATOM ⟹ vpos.head == 1` and `element_type == LINKATOM ⟹ vpos.head == 2`. Without the placement predicate, a misbehaving front end can violate I4 by inserting non-link data in the link subspace.

**Code references:**
- `backend/do1.c:91-127` — `doinsert()` sets TEXTATOM, calls `docopy()` with unchecked V-position
- `backend/do1.c:199-225` — CREATELINK uses LINKATOM with 2.x positions (correct pairing, but also unenforced)
- `backend/xanadu.h:145-146` — `TEXTATOM=1`, `LINKATOM=2` element type constants

**Concrete example:**
```
ENF0 predicate: may-modify(orgl) ≡ element-type(orgl) ≠ LINKATOM

INSERT at V:2.1 with text "Hello":
  1. inserttextingranf → fresh I-addresses α (element-type = TEXTATOM)
  2. docopy(doc, vsa=2.1, {α}) → acceptablevsa returns TRUE
  3. insertpm places α at V:2.1
  4. ENF0 not triggered — α is new, has no prior element-type to check

Result: TEXTATOM content at V:2.1 (link subspace)
  → I4 violation: link subspace contains non-link data
  → ENF0 did not prevent this because ENF0 is a modification guard, not a placement guard
```

**Provenance:** Finding 0049, also Finding 0033
**Co-occurring entries:** [PRE-INSERT], [INV-SUBSPACE-CONVENTION]

---

### PRE-VERSION-OWNERSHIP

**Source:** Finding 0068

**What happens:** The VERSION operation checks ownership before choosing the allocation strategy. The predicate `tumbleraccounteq(isaptr, wheretoputit) && isthisusersdocument(isaptr)` determines whether the version is allocated under the source document (owned) or under the creating user's account (unowned). This is not a precondition that rejects the operation — both paths succeed — but it is a precondition on the allocation path that determines where the new address lands.

**Why it matters for spec:** The allocation rule is conditional: `if owns(user, doc) then allocate_under(doc) else allocate_under(user.account)`. This is a branching postcondition keyed on the ownership predicate. The spec must model both paths. The ownership check uses account-level tumbler comparison (`tumbleraccounteq`), meaning ownership is determined by account prefix matching, not by an explicit permissions table.

**Code references:** `do1.c:272-280` — ownership branch in `docreatenewversion`. `tumbleraccounteq` — compares account components of two tumbler addresses. `isthisusersdocument` — verifies the document belongs to the current user.

**Concrete example:**
- User A (account `1.1.0.1`) versions own doc `1.1.0.1.0.1` → ownership check passes → child allocation `1.1.0.1.0.1.1`
- User B (account `1.1.0.2`) versions A's doc `1.1.0.1.0.1` → ownership check fails → account allocation `1.1.0.2.0.1`

**Provenance:** Finding 0068
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-VERSION-ADDRESS], [ST-ADDRESS-ALLOC], [FC-GRANF-ON-DELETE], [INV-MONOTONIC]

---

### PRE-SPLIT

**Source:** Finding 0070

**What happens:** `splitcrumupwards` at `split.c:16-43` loops while `toomanysons(ptr)` returns TRUE. Before each iteration, the function checks `isfullcrum(ptr)` to decide the split strategy:

- If `isfullcrum` is TRUE (node is the root/apex): calls `levelpush` to create a new root level above, then splits the old root into children of the new root.
- If `isfullcrum` is FALSE (node is internal): calls `splitcrum` to split the node within its current level, distributing children between the original node and a new sibling.

Despite its name, `isfullcrum` tests whether the crum is the **fullcrum** (root/apex node), not whether it is "full" in the occupancy sense. It is implemented as `((typecorecrum *)(x))->isapex`.

**Why it matters for spec:** The split operation has a branching precondition: at the root it changes tree height (structural), while at internal nodes it changes tree width (local). The formal model needs both cases:
- `split_root(tree)`: height' = height + 1, new root has 2 children
- `split_internal(node)`: parent gains one child, node loses some children to new sibling

**Code references:**
- `backend/split.c:16-43` — `splitcrumupwards` loop with `isfullcrum` dispatch
- `backend/genf.c:239-242` — `toomanysons` predicate (loop guard)

**Provenance:** Finding 0070
**Co-occurring entries:** [SS-ENFILADE-BRANCHING], [INV-ENFILADE-OCCUPANCY], [EC-GRAN-BOTTOM-SINGLETON]

---

## State Transitions

> What an operation changes — postconditions

### ST-INSERT

**Sources:** Findings 0002, 0007, 0009, 0027, 0030, 0031, 0033, 0036, 0047, 0052, 0054, 0059, 0060, 0062, 0066

#### Finding 0002

**What happens:** Insert creates new content identities for the inserted text and adds them to the document's reference set at the specified position. Existing content identities in the document are not modified — their positions may shift but their identities remain the same. Documents that transclude content from this document are unaffected because they reference the original content identities, which are unchanged.

**Why it matters for spec:** The postcondition for insert is: (1) new `ContentId` values are created for the inserted material, (2) the document's reference set grows by those new identities, (3) no existing `ContentId` in any document is modified. This is the key distinction from a mutable-string model: insert does not mutate, it extends.

**Concrete example:**
- Before insert: Source references identities for "Original content here"
- After `insert(source, Address(1,1), ["NEW: "])`: Source references identities for "NEW: " (new) + "Original content here" (same identities as before)
- Target that transcluded "Original content" still reads the same — unaffected

**Code references:** `scenario_vcopy_source_modified` in `febe/scenarios/content/vcopy.py:306-310`

**Provenance:** Finding 0002

#### Finding 0007

**What happens:** Inserting text in the middle of content that has shared identity (from versioning or vcopy) splits the shared identity into two regions. The original content identities are preserved on both sides of the insertion point; only the inserted material has new content identities. After insertion, `compare_versions` reports two separate shared regions instead of one contiguous region. This confirms and extends the ST-INSERT entry from Finding 0002 with a concrete split-identity example.

**Why it matters for spec:** The postcondition for mid-span insert on shared content is: if content identities [C₁..Cₙ] are at positions [p..p+n] and an insert of width w occurs at position p+k (where 0 < k < n), then after the insert: [C₁..Cₖ] are at positions [p..p+k] and [Cₖ₊₁..Cₙ] are at positions [p+k+w..p+n+w]. The content identities are unchanged; only their positions in the document shift. The formal spec should model positions as derived from content identity ordering, not as fixed offsets.

**Concrete example:**
- Original: "FirstSecond" (single shared region with version)
- Version: insert " MIDDLE " at position 6 → "First MIDDLE Second"
- `compare_versions()` reports two shared regions:
  - "First" (width 5) at original:1.1, version:1.1
  - "Second" (width 6) at original:1.6, version:1.14

**Code references:** Test `version_insert_in_middle`

**Provenance:** Finding 0007

#### Finding 0009

**What happens**: When a link is created via `docreatelink`, the operation: (1) creates a new link orgl via `createorglingranf()`, yielding a fresh ISA; (2) converts that ISA to an ispanset via `tumbler2spanset()`; (3) finds the next available V-position in the `0.x` subspace via `findnextlinkvsa()`; (4) copies the link's ISA into the document at that position via `docopy()`. This means link creation is a state transition that modifies **both** the link orgl space (new orgl) and the document's V-space (new entry in `0.x` subspace).

**Why it matters for spec**: Link creation is a compound state transition — it creates a new object AND modifies an existing document. The postcondition must specify both effects. Notably, `docopy()` is the same function used for text transclusion, so the spec for `docopy` must be parameterized over both text and link-reference use cases.

**Code references**:
- `do1.c:199-225` — `docreatelink()` full sequence
- `do2.c:48-61` — `tumbler2spanset()` ISA-to-ispan conversion
- `do2.c:151-167` — `findnextlinkvsa()` next available link position

**Concrete example**:
```
Pre-state:
  Document 1.1.0.1.0.1 has text at V-positions 1.1..1.16
  No links exist

docreatelink(doc=1.1.0.1.0.1, ...)

Post-state:
  New link orgl created at ISA 1.1.0.1.0.2
  Document 1.1.0.1.0.1 now has:
    V-position 0.1 → I-address 1.1.0.1.0.2 (link reference)
    V-positions 1.x → permascroll I-addresses (text, unchanged)
```

**Provenance**: Finding 0009

#### Finding 0027

**What happens**: When multiple inserts target the same V-position, each new insertion appears **before** existing content at that position. This produces LIFO (last-in-first-out) ordering: the most recently inserted text appears first. Specifically:

1. Insert "First" at position 1.1 → document contains "First"
2. Insert "Second" at position 1.1 → document contains "SecondFirst"
3. Insert "Third" at position 1.1 → document contains "ThirdSecondFirst"

Each insert at position P places new content at P and shifts all existing content (including previously inserted content at P) to higher positions.

**Why it matters for spec**: The insert postcondition must specify that new content occupies the target position and all content previously at or after that position is shifted forward by the length of the inserted content. For repeated inserts at the same position, this implies a prepend-at-position semantic. This is the standard text-editor cursor model (typing at a fixed cursor position builds text left-to-right only if the cursor advances; re-inserting at the same position prepends). The formal spec for insert must capture: `forall i >= P: V'[i + len(new)] = V[i]` and `V'[P..P+len(new)] = new`.

**Code references**: Observed via `edgecases/multiple_inserts_same_position` test scenario; insert implemented through the FEBE `insert` operation targeting `Address(1, 1)`.

**Concrete example**:
```
Pre-state:  V-stream = "First" (positions 1.1..1.5)
Operation:  insert(doc, Address(1, 1), ["Second"])
Post-state: V-stream = "SecondFirst" (positions 1.1..1.11)
  "Second" occupies positions 1.1..1.6
  "First" shifted to positions 1.7..1.11

Pre-state:  V-stream = "SecondFirst"
Operation:  insert(doc, Address(1, 1), ["Third"])
Post-state: V-stream = "ThirdSecondFirst"
  "Third" occupies positions 1.1..1.5
  "SecondFirst" shifted to 1.6..1.16
```

**Provenance**: Finding 0027a

#### Finding 0030

**What happens**: INSERT at V-position `p` of text with length `n` produces the following state transition on the document's V-to-I mapping:

1. **Before insertion point** (V-addr < p): V-to-I mappings are unchanged — same V-address, same I-address.
2. **At insertion point** (V-addr p through p+n-1): Fresh I-addresses are allocated for the new content. These I-addresses have no prior identity relationship with any existing content.
3. **After insertion point** (V-addr >= p, pre-insert): Each character's V-address shifts by +n. Its I-address is unchanged.

Formally, for a document state `D : VAddr -> IAddr`:
```
D'(v) =
  D(v)           if v < p
  fresh_iaddr(v) if p <= v < p + n
  D(v - n)       if v >= p + n
```

The `compare_versions` operation confirms this: it returns spans pairing old V-ranges to new V-ranges where I-addresses match. Content before the insertion point maps 1:1 at the same positions. Content after maps with a +n offset. Inserted content has no corresponding span in the prior version.

**Why it matters for spec**: This is the complete postcondition for INSERT on the V-to-I mapping. The key formal properties are: (1) the I-address set of existing content is invariant under INSERT — no existing I-address is destroyed or reassigned; (2) V-address shift is exactly the length of the inserted text; (3) fresh I-addresses are disjoint from all previously allocated I-addresses. This distinguishes INSERT from a mutable-buffer model: it extends the identity space rather than modifying it.

**Code references**: Test scenario `insert_vspace_mapping.py` — verifies V-to-I mapping before and after insertion

**Concrete example**:

Before INSERT at V-position 1.3:
```
V-addr: 1.1  1.2  1.3  1.4  1.5
Content: A    B    C    D    E
I-addr: I.1  I.2  I.3  I.4  I.5
```

After INSERT "XY" at 1.3:
```
V-addr: 1.1  1.2  1.3  1.4  1.5  1.6  1.7
Content: A    B    X    Y    C    D    E
I-addr: I.1  I.2  I.6  I.7  I.3  I.4  I.5
```

`compare_versions` returns:
```
[{version_before: 1.1 for 0.2, current: 1.1 for 0.2},   // "AB" same position
 {version_before: 1.3 for 0.3, current: 1.5 for 0.3}]   // "CDE" shifted +2
```

No span for positions 1.3-1.4 in current — "XY" has no shared I-addresses with any prior version.

**Provenance**: Finding 0030

#### Finding 0031

**What happens:** During text insertion (`inserttextgr`), I-addresses are allocated contiguously: the start address is found via `findisatoinsertgr`, then advanced by text length using `tumblerincrement(&lsa, 0, textset->length, &lsa)`. The `rightshift=0` parameter means the increment is applied at the last significant digit of the current address. The resulting I-span width is `tumblersub(endAddr, startAddr)`, which equals the character count for text content.

**Why it matters for spec:** This defines the state transition for insert: `I_next = tumblerincrement(I_current, 0, len)` and `width = I_next - I_current`. The `rightshift=0` semantics of `tumblerincrement` means new content extends at the same hierarchy level as the insertion point. One I-address per character is the granularity invariant for text.

**Code references:** `granf2.c:83-108` (`inserttextgr`), `granf2.c:100` (increment), `granf2.c:106` (width computation).

**Concrete example:**
- Insert "Hello" at `2.1.0.5.0.100`: `tumblerincrement(2.1.0.5.0.100, 0, 5)` → `2.1.0.5.0.105`
- Width: `tumblersub(2.1.0.5.0.105, 2.1.0.5.0.100)` → represents 5 positions

**Provenance:** Finding 0031

#### Finding 0033

**What happens:** When multiple single-character inserts are performed sequentially, the resulting I-addresses are contiguous. This means that bulk insertion of "ABCDEFGHIJ" and 10 sequential single-character inserts of "A", "B", ..., "J" produce identical I-space structure: both yield a single I-span of width 10. The `vspanset2ispanset` mapping returns 1 I-span, not N.

**Why it matters for spec:** The postcondition for insert can state that the new content occupies `[prev_max_iaddr + 1, prev_max_iaddr + len]` in I-space, where `len` is the number of characters inserted. For a sequence of single-character inserts, the composite postcondition is equivalent to a single bulk insert postcondition. This equivalence is a key property for reasoning about insert decomposition.

**Code references:** `findisatoinsertmolecule` in `backend/green/granf2.c`.

**Concrete example:**
- Fragmented: 10 inserts of single characters → `compare_versions` returns 1 shared span pair with `source: {start: "1.1", width: "0.10"}`, `dest: {start: "1.1", width: "0.10"}`
- Bulk: 1 insert of "ABCDEFGHIJ" → `compare_versions` also returns 1 shared span pair
- Both are structurally identical in I-space

**Provenance:** Finding 0033

#### Finding 0036

**What happens:** INSERT creates new content in the granf (via `inserttextingranf`) which returns fresh I-addresses as an `ispanset`, then calls `docopy` with that ispanset. `docopy` places the content into the document's V-stream (via `insertpm`) and creates DOCISPAN entries in the spanf (via `insertspanf(..., DOCISPAN)`). The call chain is: `doinsert` → `inserttextingranf` → `docopy` → `insertpm` + `insertspanf(..., DOCISPAN)`.

**Why it matters for spec:** INSERT postcondition must specify effects on both enfilades:
1. `granf'`: new I-addresses allocated in permascroll; document orgl updated with V→I mapping
2. `spanf'`: new DOCISPAN entries mapping the fresh I-addresses → document ISA

This means INSERT makes content immediately discoverable via `find_documents`. The postcondition is: `∀ α ∈ new_i_addresses: doc ∈ FINDDOCSCONTAINING(α)`.

**Concrete example:**
```
Pre-state:
  Document 1.1.0.1.0.1 exists, empty
  FINDDOCSCONTAINING("Inserted") → []

doinsert(doc=1.1.0.1.0.1, vsa=1.1, text="Inserted text")

Post-state:
  granf: new I-addresses α₁..αₙ allocated for "Inserted text"
         document orgl maps V:1.1..1.13 → α₁..αₙ
  spanf: DOCISPAN entries α₁..αₙ → {1.1.0.1.0.1}
  FINDDOCSCONTAINING("Inserted") → [1.1.0.1.0.1]
```

**Code references:**
- `do1.c:91-127` — `doinsert()` implementation
- `do1.c:45-65` — `docopy()` called by `doinsert`, performs `insertspanf(..., DOCISPAN)`
- Test: `golden/discovery/insert_creates_docispan.json`

**Provenance:** Finding 0036.

#### Finding 0047

**What happens:** INSERT of k contiguous bytes creates exactly 1 DOCISPAN entry in the spanfilade. The call chain `doinsert` → `inserttextingranf` → `docopy` → `insertspanf(..., DOCISPAN)` passes a single I-span (the freshly allocated contiguous I-address range) to `insertspanf`, which makes 1 `insertnd` call. Combined with Finding 0033 (sequential single-character inserts get contiguous I-addresses that consolidate), even k sequential single-character inserts produce a single I-span when later queried, because the I-addresses are contiguous.

**Why it matters for spec:** Refines the INSERT postcondition's effect on spanf. For a single INSERT of k bytes: `|new_DOCISPAN_entries| = 1`. For k sequential single-character inserts: the individual operations each create 1 DOCISPAN entry, but the entries are on contiguous I-address ranges. The storage cost of INSERT is O(1) per operation with respect to DOCISPAN, regardless of byte count.

**Code references:**
- `do1.c:91-127` — `doinsert()` → `inserttextingranf` returns one contiguous ispanset → `docopy`
- `do1.c:45-65` — `docopy()` → `insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)`
- `spanf1.c:48` — `insertnd(taskptr, spanfptr, &crumorigin, &crumwidth, &linfo, SPANRANGE)` — one call per I-span

**Provenance:** Finding 0047

#### Finding 0052

**What happens:** INSERT, COPY, and CREATELINK all share the same POOM insertion mechanism: `insertpm` → `insertnd` → `makegappm`. The `makegappm` function classifies existing POOM crums relative to the insertion point using `insertcutsectionnd`: case 0/2 (before or at boundary) are left unchanged, case 1 (THRUME — beyond insertion point) are shifted by adding the insertion width to their V-dimension displacement. This is the same shifting behavior documented in Finding 0027 for INSERT, now confirmed to be shared across all three operations.

**Why it matters for spec:** The shift postcondition `forall v >= P: v' = v + width` is a property of `insertpm`, not of any individual operation. The spec should define a shared `poom_insert(poom, position, width)` primitive with this postcondition, then define INSERT, COPY, and CREATELINK as calling this primitive with different position-selection strategies. INSERT and COPY use user-specified positions; CREATELINK uses `findnextlinkvsa` which always selects the document end.

**Code references:**
- `backend/insertnd.c:54` — `makegappm` called for POOM case in `insertnd`
- `backend/insertnd.c:162` — `tumbleradd(&ptr->cdsp.dsas[V], &width->dsas[V], &ptr->cdsp.dsas[V])` performs the shift

**Provenance:** Finding 0052

#### Finding 0054

**What happens:** INSERT shifts only POOM entries within the bounded region `[blade[0], blade[1])`. The two-blade knife restricts the shift to entries between the insertion point and the next subspace boundary. `insertcutsectionnd()` classifies each POOM crum into three cases:
- Case 0: crum is before `blade[0]` — no shift
- Case 1: crum is between `blade[0]` and `blade[1]` — shift right by insertion width
- Case 2: crum is at or beyond `blade[1]` — no shift

This corrects EWD-037's claim that `insertcutsectionnd` shifts ALL crums after the insertion point via lexicographic comparison. The actual behavior is bounded: only crums in the same subspace as the insertion point are affected.

**Why it matters for spec:** The postcondition for INSERT's V-position shifting is bounded, not global: `∀ entry ∈ poom(doc) : blade[0] ≤ entry.vpos < blade[1] ⟹ entry.vpos' = entry.vpos + insert_width`. Entries outside this range are unchanged. This is a stronger (more precise) postcondition than "all entries after insertion point shift," and it is what the implementation actually enforces.

**Code references:**
- `edit.c:207-233` — `insertcutsectionnd()` three-case classification
- `insertnd.c:124-172` — `makegappm()` with two-blade knife

**Provenance:** Finding 0054

#### Finding 0059

**What happens:** On INSERT, text is copied into an in-memory bottom crum (`typecbc`), and the crum plus its ancestors are marked `modified = TRUE` via `ivemodified()`. The text is NOT immediately written to disk. The crum remains in the grim reaper cache until evicted by memory pressure or flushed at session exit.

**Why it matters for spec:** The postcondition of INSERT includes the text being retrievable (via the in-memory cache), but does NOT include the text being durable on disk. This is a weaker postcondition than a specification might assume. Formally: after INSERT, `RETRIEVE(addr)` returns the text (from cache), but `crash(); restart(); RETRIEVE(addr)` may fail.

**Code references:**
- `backend/insert.c:17-70` — `insertseq` creates leaf crum with text
- `backend/genf.c:522-544` — `ivemodified` marks crum and ancestors as modified

**Provenance:** Finding 0059

#### Finding 0060

**What happens:** When `insertseq` adds a new bottom crum to a granfilade, the new crum is adopted as a right sibling of the existing bottom crum at height-0. Then `splitcrumupwards(father)` checks whether the father (height-1) has too many children. Because `MAXBCINLOAF = 1`, any height-1 node with 2+ children triggers a split. If the father is the fullcrum, `levelpush` first increases the tree height, then `splitcrum` splits the demoted former root. If the father is not the fullcrum, `splitcrum` creates a sibling and the split may propagate upwards.

The granfilade grows taller with each insert of a new bottom crum when the target height-1 node is the fullcrum — the tree effectively adds a new level for every second bottom crum at the root level. Subsequent inserts into non-root height-1 nodes split horizontally (creating sibling height-1 nodes), increasing the parent's child count instead of increasing tree height.

**Why it matters for spec:** The ST-INSERT postcondition for granfilades must account for tree height growth. After inserting into a height-1 fullcrum that already has 1 child: `enf.height_after = enf.height_before + 1`. For inserts into non-root height-1 nodes: height unchanged, parent gains one additional child. The formal model of insert must compose the content-level change (new V-address mapped) with the structural change (tree may grow taller).

**Code references:**
- `backend/insert.c:44-48` — `insertseq`: creates height-0 crum, adopts as right sibling, calls `splitcrumupwards`
- `backend/split.c:16-44` — `splitcrumupwards`: levelpush at fullcrum, splitcrum at non-root
- `backend/split.c:70-93` — `splitcrumseq`: halves children between original and new sibling

**Concrete example:**
```
Insert 3rd bottom crum into granfilade (tree already at height=2):
  Fullcrum (height=2, numberofsons=2)
    ├─ Node1 (height=1, numberofsons=1)
    │    └─ Bottom crum A
    └─ Node2 (height=1, numberofsons=1)
         └─ Bottom crum B

New bottom crum C adopted as sibling of B under Node2:
  Node2 (height=1, numberofsons=2)  ← toomanysons → TRUE

splitcrum(Node2) → not fullcrum, split into siblings:
  Fullcrum (height=2, numberofsons=3)
    ├─ Node1 (height=1, numberofsons=1) → Bottom A
    ├─ Node2 (height=1, numberofsons=1) → Bottom B
    └─ Node3 (height=1, numberofsons=1) → Bottom C

Fullcrum: toomanysons → 3 > 6? No. Loop exits. Height unchanged.
```

**Provenance:** Finding 0060

#### Finding 0062

**What happens:** When an INSERT at position v+1 encounters a crum whose reach equals v+1 (ONMYRIGHTBORDER), the system performs rightward extension instead of splitting. The function `isanextensionnd()` checks two conditions: (1) the new content has the same `homedoc` as the existing crum, and (2) the new content's origin equals the existing crum's reach. When both hold, the existing crum's width is extended in place — no new crum is allocated.

For interior typing, this produces the following sequence:
1. First insert at v: splits existing crum into [left, v) and [v+1, ...); creates new crum [v, v+1). Cost: +2 crums (split creates two halves, minus the one destroyed, plus one new = net +2).
2. Second insert at v+1: new_crum's reach is v+1, origin is v+1 → ONMYRIGHTBORDER → no split. `isanextensionnd` succeeds → crum extended to [v, v+2). Cost: +0 crums.
3. Third insert at v+2: extended crum's reach is v+2, origin is v+2 → same pattern. Cost: +0.
4. N-th insert: always +0.

The extension is asymmetric: crums grow rightward only. `isanextensionnd` checks if reach == origin (right extension), not if grasp == origin + width (left extension).

**Why it matters for spec:** This refines the ST-INSERT postcondition for the coalescing case. When the insertion point equals an existing crum's reach and homedoc matches: `post_insert_coalesce(crum, content) = crum.width' = crum.width + content.width ∧ crum.grasp' = crum.grasp ∧ num_crums' = num_crums`. The state transition creates no new crums — the content is absorbed into the existing crum. This is distinct from the splitting case (where Δcrums = +2) and the append case (where Δcrums may be 0 or +1 depending on contiguity).

**Code references:**
- `insertnd.c:293-301` — `isanextensionnd()`: checks homedoc match AND reach == origin
- `insertnd.c:243` — Width extension: existing crum grows in place
- `insertnd.c:252-260` — New crum creation (when extension fails)

**Concrete example:**
```
Before: doc = "ABCDE", crums = [crum₁: V 1.1..1.6]
INSERT "X" at 1.3:
  Knife cuts crum₁ → [crum₂: 1.1..1.3, crum₃: 1.4..1.6]
  New crum₄: [1.3..1.4) for "X"
  crums = 3 (Δ = +2)

INSERT "Y" at 1.4:
  crum₄.reach = 1.4, origin = 1.4 → ONMYRIGHTBORDER → no knife cut
  isanextensionnd(crum₄, "Y") → TRUE (same homedoc, reach == origin)
  crum₄ extended: [1.3..1.5) for "XY"
  crums = 3 (Δ = 0)

INSERT "Z" at 1.5:
  crum₄.reach = 1.5, origin = 1.5 → ONMYRIGHTBORDER → no knife cut
  isanextensionnd(crum₄, "Z") → TRUE
  crum₄ extended: [1.3..1.6) for "XYZ"
  crums = 3 (Δ = 0)
```

**Provenance:** Finding 0062

#### Finding 0066

**What happens:** In 2D enfilades, `firstinsertionnd` (for first child) sets the child's `cdsp` to the absolute insertion position, then calls `setwisp` on the parent. For subsequent insertions, `makegappm` shifts existing crums whose V-position follows the insertion point by adding the width to their displacement (`insertnd.c:162`: `tumbleradd(&ptr->cdsp.dsas[V], &width->dsas[V], &ptr->cdsp.dsas[V])`). After any insertion, `setwispupwards` recalculates the root's displacement by finding the new minimum across all children.

When inserting at a position less than the current root displacement, the root's `cdsp` decreases to the new minimum, and all existing children's displacements increase (they shift upward relative to the new, lower origin).

**Why it matters for spec:** Insert into a 2D enfilade has a cascade effect: the insertion may change the root's displacement, which changes the relative displacements of all siblings. The postcondition must account for this: after insert, `root.cdsp = min(old_root.cdsp, new_position)`, and all children's relative displacements are adjusted accordingly.

**Code references:**
- `backend/insertnd.c:199-218` — `firstinsertionnd`: child gets absolute position, then `setwisp(root)`
- `backend/insertnd.c:162` — `makegappm`: shifts crums after insertion point
- `backend/wisp.c:171-228` — `setwispnd`: recalculates root displacement after insertion

**Concrete example:** Content at 5.0 (`root.cdsp = 5.0, child_A.cdsp = 0`). Insert at 2.0:
- New `child_B.cdsp = 2.0` (absolute)
- `setwispnd` finds `mindsp = min(0, 2.0) = 0`... but wait, child_A is relative (0) and child_B is absolute (2.0). After `makegappm` and `setwispupwards`, the root recalculates: `mindsp` across children, root absorbs it, children adjust. Net result: `root.cdsp = 2.0`, `child_A.cdsp = 3.0` (was at absolute 5.0, now relative to root 2.0), `child_B.cdsp = 0` (at the new minimum).

**Provenance:** Finding 0066

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-CACHE-MECHANISM], [SS-CONTENT-IDENTITY], [SS-DOCISPAN], [SS-DOCUMENT-LIFECYCLE], [SS-DUAL-ENFILADE], [SS-ENFILADE-TREE], [SS-INTERVAL-CMP], [SS-LINK-SUBSPACE], [SS-SPAN], [SS-TUMBLER], [SS-TWO-BLADE-KNIFE], [SS-UNIFIED-STORAGE], [SS-VERSION-ADDRESS], [SS-WHEREONCRUM], [PRE-COMPARE-VERSIONS], [PRE-INSERT], [PRE-RETRIEVE-CONTENTS], [ST-COPY], [ST-CREATE-LINK], [ST-INSERT-ACCUMULATE], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-DOC-ISOLATION], [FC-INSERT-IADDR], [FC-SUBSPACE], [INV-CONTENT-IMMUTABILITY], [INV-CRUM-BOUND], [INV-DURABILITY-BOUNDARY], [INV-ENFILADE-MINIMALITY], [INV-ENFILADE-RELATIVE-ADDRESSING], [INV-IADDR-IMMUTABILITY], [INV-MONOTONIC], [INV-SPANF-GROWTH], [INV-SUBSPACE-CONVENTION], [INV-TRANSITIVE-IDENTITY], [INV-TUMBLER-TOTAL-ORDER], [INT-LINK-FOLLOW-LIFECYCLE], [INT-LINK-INSERT], [INT-LINK-TRANSCLUSION], [INT-TRANSCLUSION], [INT-TRANSCLUSION-INSERT-ORDER], [INT-VERSION-TRANSCLUSION], [EC-APPEND-NO-DOCISPAN], [EC-BOUNDARY-INSERT-CLASSIFICATION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-CONCURRENT-LINK-CREATION], [EC-CRASH-MID-WRITE], [EC-CROSS-ENFILADE-EVICTION], [EC-EMPTY-DOC], [EC-GRAN-MB-ONE], [EC-NO-STARTUP-VALIDATION]

---

### ST-VCOPY

**Sources:** Findings 0002, 0003, 0018, 0039, 0046

#### Finding 0002

**What happens:** The vcopy (virtual copy / transclusion) operation adds references to existing content identities into the target document. It does not copy the content itself — it creates new references to the same identities that the source document references. After vcopy, `compare_versions` between source and target reports shared content, confirming that both documents reference the same content identities.

**Why it matters for spec:** The postcondition for vcopy is: `references(target) = references(target_before) ∪ {content_ids referenced by source_specset}`. No new content identities are created. The target gains references to exactly the content identities specified in the source specset. This makes vcopy fundamentally different from insert — insert creates new identities, vcopy shares existing ones.

**Concrete example:**
- Source references identities for "Shared content that will be transcluded"
- After `vcopy(target, position, specset_referencing_source["Shared content"])`:
  - Target now references both its own "Prefix: " identities AND the source's "Shared content" identities
  - `compare_versions(source, target)` returns the shared span

**Code references:** `scenario_vcopy_preserves_identity` in `febe/scenarios/content/vcopy.py:61-128`

**Provenance:** Finding 0002

#### Finding 0003

**What happens:** When vcopy operates on a SpecSet containing multiple non-contiguous spans, each span is copied independently and each gets its own identity mapping in the target document. The compare operation subsequently returns multiple shared regions — one per copied span — confirming that per-span identity is preserved, not merged into a single region. Cross-document vcopy (SpecSet referencing spans from multiple source documents) works atomically; all spans are placed into the target in a single operation.

**Why it matters for spec:** This extends the vcopy postcondition: `references(target) = references(target_before) ∪ ⋃{content_ids(vspec) | vspec in specset}`. Crucially, identity is preserved per-VSpec, not per-SpecSet: each VSpec's content identities remain independently trackable. The atomicity property means multi-span vcopy either completes for all VSpecs or none — there is no partial copy state. For formal spec: `|shared_regions(compare(source, target))| >= |specset|` when all spans have distinct content.

**Concrete example:**
- Source: "First part. Middle part. Last part."
- vcopy SpecSet with two VSpecs: "First part" (pos 1-10), "Last part" (pos 26-35), skipping middle
- Target: "Copied: First partLast part."
- compare returns TWO shared regions:
  - "First part" (source 1-10 <-> target 9-18)
  - "Last part" (source 26-35 <-> target 19-28)

**Code references:** Tests `vcopy_multiple_spans`, `vcopy_from_multiple_documents`

**Provenance:** Finding 0003

#### Finding 0018

**What happens:** Vcopy (transclusion) preserves I-addresses from the source. The copied content in the target document has the same I-addresses as the original, enabling content identity tracking across documents. Partial transclusion also preserves identity — copying a subset of already-transcluded content maintains the I-address chain back to the original source.

**Why it matters for spec:** Vcopy postcondition: for the copied span, `I-addresses(target[v_target..v_target+len]) = I-addresses(source[v_source..v_source+len])`. This is what makes transitive identity work and distinguishes vcopy from insert (which creates new I-addresses).

**Concrete example:**
```
C: "ABCDEFGHIJ"         # I-addresses α₁..α₁₀
B: vcopy(all of C)       # B contains I-addresses α₁..α₁₀
A: vcopy("DEFGH" from B) # A contains I-addresses α₄..α₈

compare_versions(A, C) → "DEFGH" shared (same I-addresses α₄..α₈)
```

**Code references:** Tests `identity_partial_transclusion`, `find_documents_transitive`.

**Provenance:** Finding 0018, Key Findings 2 and 6.

#### Finding 0039

**What happens:** When vcopy copies content within the same document (internal transclusion), it creates a new V-position that references the same I-address as the source position. After the operation, the document's POOM contains multiple `(V-position, I-address)` entries with the same I-address but different V-positions. This is the same mechanism as cross-document transclusion — the POOM's multimap structure handles intra-document sharing identically to inter-document sharing.

**Why it matters for spec:** The ST-VCOPY postcondition from Finding 0002 (`references(target) = references(target_before) ∪ source_content_ids`) applies unchanged for internal transclusion. When `target = source`, the postcondition becomes `references(doc) = references(doc_before) ∪ { existing_content_ids_at_new_positions }`. No special case is needed — the same postcondition covers both internal and external transclusion because the POOM is a multimap that naturally accommodates duplicate I-addresses at different V-positions.

**Concrete example:**
```
Before: doc has "text" at V 1.10..1.13, mapped to I-addresses i₁..i₄
After vcopy(doc, V=1.19, specset=V 1.10..1.13):
  doc has "text" at V 1.10..1.13 → i₁..i₄ (original, unchanged)
  doc has "text" at V 1.19..1.22 → i₁..i₄ (new positions, same I-addresses)

compare_versions on those two regions reports shared content:
  shared = [{first: {start: 1.10, width: 0.4}, second: {start: 1.19, width: 0.4}}]
```

**Code references:** Tests `internal/internal_transclusion_identity`, `internal/internal_transclusion_multiple_copies`

**Provenance:** Finding 0039

#### Finding 0046

**What happens:** When COPY inserts V→I mappings into a POOM, the insertion follows an extension-or-create rule. The function `isanextensionnd()` at `insertnd.c:293-301` checks two conditions: (1) the new mapping has the same `homedoc` (I-address origin document) as an existing crum, and (2) the new mapping starts exactly where the existing crum ends (contiguous in both V and I dimensions). If both hold, the existing crum's width is extended in place (`insertnd.c:243`). Otherwise, a new crum is created (`insertnd.c:252-260`). This means repeated COPYs of the same I-addresses produce either extended crums or separate crums depending on contiguity, never duplicated entries within a single crum.

**Why it matters for spec:** The COPY postcondition should account for POOM compaction: `post_copy(target, vpos, ispan) = forall offset in 0..|ispan| :: poom(target, vpos + offset) = ispan.start + offset`. The implementation may merge this mapping with adjacent crums, but the logical mapping is the same regardless. For spec purposes, the crum structure is an implementation detail — the observable effect is the V→I mapping. However, the extension check's `homedoc` condition means crums from different source documents are never merged, which constrains how the POOM partitions its internal structure.

**Code references:**
- `isanextensionnd()` — `insertnd.c:293-301` — Extension check: same homedoc AND contiguous
- `insertnd.c:243` — Extends existing crum width
- `insertnd.c:252-260` — Creates new crum when not an extension
- `docopy()` — `do1.c:45-65` — COPY operation entry point

**Concrete example:**
```
Before: target POOM has crum [V 1.1..1.5 → i₁..i₅] (from first COPY)

COPY same source at V=1.6 (contiguous, same homedoc):
  isanextensionnd() → TRUE
  Result: crum extended to [V 1.1..1.10 → i₁..i₁₀]

COPY same source at V=1.20 (non-contiguous):
  isanextensionnd() → FALSE
  Result: new crum created [V 1.20..1.24 → i₁..i₅]
```

**Provenance:** Finding 0046

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-POOM-MULTIMAP], [SS-SPECSET], [PRE-COPY], [ST-INSERT], [ST-REARRANGE], [ST-REMOVE], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-DOC-ISOLATION], [FC-SPECSET-COMPARE], [INV-CONTENT-IMMUTABILITY], [INV-IADDR-PROVENANCE], [INV-LINK-IDENTITY-DISCOVERY], [INV-REARRANGE-IDENTITY], [INV-SPECSET-ORDER], [INV-TRANSITIVE-IDENTITY], [INT-LINK-VERSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-SELF-TRANSCLUSION]

---

### ST-REMOVE

**Sources:** Findings 0002, 0004, 0005, 0006

#### Finding 0002

**What happens:** Remove (deletion) removes content references from a document's reference set at the specified span. The content identities themselves are not destroyed. Other documents that reference the same content identities are unaffected.

**Why it matters for spec:** The postcondition for remove is: `references(doc) = references(doc_before) \ {content_ids at specified span}`. Combined with INV-CONTENT-IMMUTABILITY, the full postcondition is: the document loses references, but global content state is unchanged. This makes remove a local operation on the document's reference set with no global side effects.

**Concrete example:**
- Source: references identities for "Keep this. Delete this. Keep end."
- After `remove(source, span_of("Delete this. "))`: Source references only "Keep this. " and "Keep end."
- The content identities for "Delete this." still exist globally (target still references them)

**Code references:** `scenario_vcopy_source_deleted` in `febe/scenarios/content/vcopy.py:383-387`

**Provenance:** Finding 0002

#### Finding 0004

**What happens:** When the linked span itself is deleted from a document, the link continues to exist but points to empty content. When a partial deletion removes part of a linked span, the link points to the remainder. This extends the ST-REMOVE postcondition: removal of content from a document removes that document's reference but does not invalidate links — the link's endpoint adjusts to reflect whatever content identities remain reachable.

**Why it matters for spec:** The postcondition for remove, with respect to links, is: `link.source = link.source_before ∩ all_referenced_content(system_after)`. If all content identities in a link's source endpoint are removed from every document, the link exists but its source resolves to empty. If only some are removed, the link resolves to the remaining subset. The link itself is never destroyed by remove — only its effective resolution changes.

**Concrete example:**
- Link on "here" (content identities C₁C₂C₃C₄) in document A
- Delete entire "here": link exists, source resolves to empty (no document references C₁-C₄)
- Delete "he" only: link exists, source resolves to "re" (C₃C₄ still referenced by A)

**Code references:** Tests `link_when_source_span_deleted` (PASS), `link_source_partial_delete` (PASS), `link_when_target_span_deleted` (PASS)

**Provenance:** Finding 0004

#### Finding 0005

**What happens:** Deletion interacts with link endpoints in two distinct ways depending on overlap:

1. **Partial deletion of linked span:** The link survives and its source resolves to the remaining content. Deleting "hyper" from a link on "hyperlink" (9 chars) leaves the link pointing to "link" (4 chars). The link endpoint adjusts to the subset of content identities that remain referenced.

2. **Full deletion of linked span:** The link object still exists in the link enfilade. `follow_link()` succeeds but returns an empty span. However, `find_links()` on the document no longer returns the link — there are no content identities left in the document to match against.

**Why it matters for spec:** Extends the ST-REMOVE postcondition for links. After remove: `effective_source(link) = content_ids(link.source) ∩ all_referenced_content(system_after)`. When this intersection is empty, the link exists but is undiscoverable via content-based search. The asymmetry between `follow_link` (traverses the link object directly, always works) and `find_links` (searches by content identity intersection, fails when no content remains) is a key behavioral distinction the spec must capture.

**Concrete example:**
- Partial delete: Link on "hyperlink" (C₁..C₉) → delete "hyper" (C₁..C₅) → link resolves to "link" (C₆..C₉)
- Full delete: Link on "here" (C₁..C₄) → delete "here" → `follow_link()` returns empty, `find_links(doc)` returns nothing

**Code references:** Tests `link_source_partial_delete` (PASS), `link_when_source_span_deleted` (PASS), `link_when_target_span_deleted` (PASS)

**Provenance:** Finding 0005

#### Finding 0006

**What happens:** Deletion uses the DELETEVSPAN operation (FEBE command 12), which takes a vspan (start address + width offset). This is the correct and only mechanism for removing content from a document. REARRANGE (command 3) cannot be used for deletion despite its name suggesting content restructuring.

**Why it matters for spec:** Confirms that content removal is a single atomic operation taking a contiguous vspan. The postcondition removes exactly the content identities within the specified span: `content_ids(doc_after) = content_ids(doc_before) \ content_ids(vspan)`. The spec should not model deletion as a special case of rearrangement — they are distinct operations with different postconditions (REARRANGE preserves content identity count, REMOVE reduces it).

**Code references:** FEBE command 12 (backend); `session.remove()`, `session.delete()` (febe/client.py)

**Provenance:** Finding 0006

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-LINK-ENDPOINT], [PRE-OPEN-DOC], [PRE-REARRANGE], [ST-INSERT], [ST-REARRANGE], [ST-VCOPY], [FC-DOC-ISOLATION], [FC-LINK-PERSISTENCE], [INV-CONTENT-IMMUTABILITY], [INV-LINK-CONTENT-TRACKING], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-ORPHANED-LINK]

---

### ST-REARRANGE

**Sources:** Findings 0006, 0016, 0018, 0051, 0056

#### Finding 0006

**What happens:** The REARRANGE operation (FEBE command 3) restructures content within a document without deleting it. It has two modes based on the number of cut positions provided:

1. **Pivot (3 cuts):** `pivot(doc, start, pivot, end)` — rotates the content around a pivot point within the range `[start, end)`.
2. **Swap (4 cuts):** `swap(doc, starta, enda, startb, endb)` — exchanges two subranges within the document.

The backend enforces the cut count strictly: providing 2 cuts aborts with "Wrong number of cuts". This is a content-preserving operation — no content identities are created or destroyed.

**Why it matters for spec:** REARRANGE is a distinct state transition from INSERT and DELETE. Its postcondition preserves the set of content identities: `content_ids(doc_after) = content_ids(doc_before)`. Only the v-ordering changes. The spec must model pivot and swap as permutations of the document's content sequence, not as delete-then-insert pairs. The strict cut-count validation is a precondition: `|cuts| ∈ {3, 4}`.

**Code references:** FEBE command 3 (backend); `session.pivot()`, `session.swap()` (febe/client.py)

**Provenance:** Finding 0006

#### Finding 0016

**What happens:** REARRANGE has two modes defined by cut-point geometry:

1. **Pivot (3 cuts):** `pivot(doc, cut1, cut2, cut3)` swaps two adjacent regions. Region1 spans `[cut1, cut2)`, region2 spans `[cut2, cut3)`. After pivot, the document content outside these regions is unchanged, and the two regions exchange positions.

2. **Swap (4 cuts):** `swap(doc, cut1, cut2, cut3, cut4)` swaps two non-adjacent regions. Region1 spans `[cut1, cut2)`, region2 spans `[cut3, cut4)`. The middle segment `[cut2, cut3)` remains in place between the swapped regions.

**Why it matters for spec:** These are permutations on the document's content sequence. The postcondition for pivot is:
- `doc_after[..cut1] = doc_before[..cut1]` (prefix unchanged)
- `doc_after[cut1..cut1+(cut3-cut2)] = doc_before[cut2..cut3]` (region2 moves left)
- `doc_after[cut1+(cut3-cut2)..] = doc_before[cut1..cut2] ++ doc_before[cut3..]` (region1 moves right, suffix unchanged)

For swap, the middle segment is a frame condition:
- `doc_after[cut2'..cut3'] = doc_before[cut2..cut3]` (middle preserved, though its v-addresses shift if regions differ in size)

Both modes preserve `|content(doc)|` — no content is created or destroyed.

**Concrete example (pivot):**
- Before: `"ABCDE"`, cuts at `1.2, 1.4, 1.6`
- Regions: `"BC"` (1.2–1.4) and `"DE"` (1.4–1.6)
- After: `"ADEBC"`

**Concrete example (swap):**
- Before: `"ABCDEFGH"`, cuts at `1.2, 1.4, 1.6, 1.8`
- Regions: `"BC"` (1.2–1.4) and `"FG"` (1.6–1.8)
- Middle: `"DE"` (1.4–1.6) unchanged
- After: `"AFGDEBCH"`

**Code references:** `edit.c:rearrangend()` (backend); `session.pivot()`, `session.swap()` (febe/client.py)

**Provenance:** Finding 0016 (extends Finding 0006)

#### Finding 0018

**What happens:** Pivot and swap rearrange operations change V-positions but preserve I-addresses. After rearrangement, all content retains its original identity — `compare_versions` between pre- and post-rearrange states returns all content as shared.

**Why it matters for spec:** Rearrange postcondition: the multiset of I-addresses in the document is unchanged. Only the V-address mapping changes. This means rearrange is a pure structural permutation with no content creation.

**Concrete example:**
```
Before pivot: "First Second"
  "First " at V:1.1, I-address α
  "Second" at V:1.7, I-address β

After pivot: "SecondFirst "
  "Second" at V:1.1, I-address β  (same I-address)
  "First " at V:1.7, I-address α  (same I-address)

compare_versions(before, after) → all content shared
```

**Code references:** Tests `identity_through_rearrange_pivot`, `identity_through_rearrange_swap` in scenarios.

**Provenance:** Finding 0018, Key Finding 3.

#### Finding 0051

**What happens:** When REARRANGE pivot is given cut points that span subspace boundaries, the displacement arithmetic works without error. The `tumbleradd` operation treats tumblers as pure arithmetic values — adding offset 1.1 to V-position 1.1 yields 2.2 regardless of subspace semantics. The rearrangement loop in `rearrangend()` iterates over all orgls in the affected range, classifies each into a cut section (1, 2, or 3) via `rearrangecutsectionnd()`, and applies the corresponding displacement. No section is skipped or rejected based on the resulting position.

**Why it matters for spec:** The state transition for REARRANGE must specify either (a) the postcondition `∀ orgl: subspace(vpos'(orgl)) == subspace(vpos(orgl))` as a maintained invariant, or (b) acknowledge that subspace can change and update the content discipline accordingly. Currently the implementation follows (b) silently — it permits cross-subspace movement. The formal spec must choose one and enforce it.

**Code references:**
- `backend/edit.c:78-160` — `rearrangend()` main loop applying displacements
- `backend/edit.c:164-183` — `makeoffsetsfor3or4cuts()` offset computation

**Concrete example:**
```
Pivot with cuts [1.1, 1.4, 2.5]:
  Section 1 (V:1.1 ≤ v < V:1.4): displaced by +1.1 → moved to 2.x
  Section 2 (V:1.4 ≤ v < V:2.5): displaced by -0.3 → stays in 1.x (or moves within)
  Section 3 (v ≥ 2.5): no displacement

Result: content crosses from subspace 1 to subspace 2
  No error returned, modification flagged via ivemodified()
```

**Provenance:** Finding 0051

#### Finding 0056

**What happens:** The rearrange algorithm operates in four steps on the POOM enfilade:

1. **Sort cuts** — `sortknives()` reorders cut points into ascending order regardless of input order.
2. **Compute offsets** — `makeoffsetsfor3or4cuts()` derives a tumbler offset for each region from the cut positions alone.
3. **Classify spans** — `rearrangecutsectionnd()` determines which region (0–4) each content span belongs to.
4. **Apply offsets** — `tumbleradd()` adds the computed offset to each span's V-address in place.

For **pivot (3 cuts)** at positions `cut0 < cut1 < cut2`:
- `diff[1] = cut2 - cut1` (region 1 moves forward by size of region 2)
- `diff[2] = -(cut1 - cut0)` (region 2 moves backward by size of region 1)

For **swap (4 cuts)** at positions `cut0 < cut1 < cut2 < cut3`:
- `diff[1] = cut2 - cut0` (region 1 moves to region 3's position)
- `diff[2] = (cut3 - cut2) - (cut1 - cut0)` (middle shifts by size difference)
- `diff[3] = -(cut2 - cut0)` (region 3 moves to region 1's position)

The operation modifies V-addresses exclusively — it calls `tumbleradd(&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index])` which updates the displacement's V-address component. No I-addresses are touched, no content is copied, no new permascroll entries are created.

**Why it matters for spec:** This confirms rearrange is a pure V-address permutation. The state transition can be modeled as: for each content unit `c`, `v_after(c) = v_before(c) + offset(region(c))`, where `offset` is determined by the cut geometry. All cuts are in the **pre-move** address space — offsets are computed from pre-move positions with no reference to post-move state.

**Concrete example (pivot):** `"ABCDE"` with cuts at `1.2, 1.4, 1.6`:
- Region 1 (`[1.2, 1.4)` = "BC"): offset = `1.6 - 1.4` = `+0.2`, moves to `[1.4, 1.6)`
- Region 2 (`[1.4, 1.6)` = "DE"): offset = `-(1.4 - 1.2)` = `-0.2`, moves to `[1.2, 1.4)`
- Result: `"ADEBC"`

**Concrete example (swap):** `"ABCDEFGH"` with cuts at `1.2, 1.4, 1.6, 1.8`:
- Region 1 (`[1.2, 1.4)` = "BC"): offset = `1.6 - 1.2` = `+0.4`, moves to `[1.6, 1.8)`
- Region 2 (`[1.4, 1.6)` = "DE"): offset = `(1.8 - 1.6) - (1.4 - 1.2)` = `0`, stays
- Region 3 (`[1.6, 1.8)` = "FG"): offset = `-(1.6 - 1.2)` = `-0.4`, moves to `[1.2, 1.4)`
- Result: `"AFGDEBCH"`

**Code references:** `backend/edit.c:78-184` — `rearrangend()`, `makeoffsetsfor3or4cuts()`, `rearrangecutsectionnd()`, `tumbleradd()`

**Provenance:** Finding 0056 (extends Findings 0006, 0016)

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [PRE-OPEN-DOC], [PRE-REARRANGE], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-REARRANGE-EXTERIOR], [INV-PIVOT-SELF-INVERSE], [INV-REARRANGE-IDENTITY], [INV-REARRANGE-LINK-SURVIVAL], [INV-SUBSPACE-CONVENTION], [INV-TRANSITIVE-IDENTITY], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-REARRANGE-CROSS-SUBSPACE], [EC-REARRANGE-EMPTY-REGION]

---

### ST-VERSION-CREATE

**Sources:** Findings 0007, 0018, 0032, 0043, 0046, 0072

#### Finding 0007

**What happens:** Creating a version produces a new, independent document whose content references share identity with the original's content references. This is copy-on-write at the content-identity level: the version starts with references to the same `ContentId` values as the original, but subsequent edits to either document create new content identities without affecting the other. The version operation is equivalent to a full-document vcopy into a new document in the original's address subspace.

**Why it matters for spec:** The postcondition for version creation is: `references(version) = references(original)` at creation time, where equality means the same set of `ContentId` values. Combined with FC-DOC-ISOLATION, all subsequent operations on either document are independent. The precondition is minimal — even empty documents can be versioned (the resulting version has an empty reference set). The formal spec should model version-create as: allocate new document at child address, copy the reference set, done.

**Concrete example:**
- Before: Original references content identities for "Shared base content"
- After `create_version(original)`: Version references the SAME content identities for "Shared base content"
- After insert to version: Version references new identities for "version-only " + same identities for "Shared base content"
- Original: still references only identities for "Shared base content" (unchanged)

**Code references:** Tests `create_version`, `version_of_empty_document`

**Provenance:** Finding 0007

#### Finding 0018

**What happens:** Version creation preserves content identity — the new version shares I-addresses with its parent for all inherited content. `compare_versions` between original and version returns the shared content, and `FINDDOCSCONTAINING` finds both.

**Why it matters for spec:** Version-create postcondition: all I-addresses present in the original are also present in the new version at creation time. Subsequent edits to the version create new I-addresses only for newly inserted content.

**Concrete example:**
```
Original: "Original text"             # I-addresses α₁..αₙ
Version:  "Original text v2 additions" # I-addresses α₁..αₙ + β₁..βₘ

compare_versions(original, version) → "Original text" shared
find_documents("Original" from original) → [original, version]
```

**Code references:** Test `identity_through_version_chain` in scenarios.

**Provenance:** Finding 0018, Key Finding 5.

#### Finding 0032

**What happens:** CREATENEWVERSION (command 13) is an atomic operation that creates a new document and copies all content in a single call. Internally, `docreatenewversion` performs three steps: (1) allocate a new orgl under the source's address space via `createorglingranf`, (2) retrieve the source document's full vspanset via `doretrievedocvspanfoo`, (3) copy all content preserving I-addresses via `docopyinternal`. The documented "OPENCOPY" command does not exist in the implementation — CREATENEWVERSION is its functional replacement.

**Why it matters for spec:** The version-create operation has a single-step atomicity guarantee: there is no observable intermediate state where the version exists but has no content. The precondition is simply that the source document exists (even empty documents can be versioned). The postcondition is: `references(new_version) = references(source)` with the new version at a child address. This atomicity distinguishes it from the two-step CREATEDOCUMENT + COPY sequence, which has an observable intermediate state (empty document exists).

**Code references:** `backend/do1.c:docreatenewversion` — full implementation. `backend/requests.h` — defines `CREATENEWVERSION 13`, no OPENCOPY defined. `backend/init.c:requestfns` — command dispatch table confirms OPENCOPY absent.

**Concrete example:**
```
Before: doc at 1.1.0.1.0.1 contains "Hello world" (I-addresses α₁..α₁₁)
CREATENEWVERSION(doc) →
After:  version at 1.1.0.1.0.1.1 contains "Hello world" (same I-addresses α₁..α₁₁)
        No intermediate state observable
```

**Provenance:** Finding 0032

#### Finding 0043

**What happens**: `CREATENEWVERSION(d)` copies only the text subspace (`1.x` V-positions) from the source document's POOM into the new version. The link subspace (`0.x` / internally `2.x`) is not copied. The mechanism is in `docreatenewversion` which calls `doretrievedocvspanfoo` to obtain a single vspan, then passes it to `docopyinternal`. The function `retrievedocumentpartofvspanpm` returns only the document's V-dimension displacement and width — `cdsp.dsas[V]` and `cwid.dsas[V]` — which point to position `1` (the text subspace start). The link subspace at positions before `1` is structurally outside this vspan.

**Why it matters for spec**: This refines the ST-VERSION-CREATE postcondition from finding 0007. The postcondition is not `references(version) = references(original)` unconditionally — it is `text_references(version) = text_references(original) AND link_references(version) = {}`. The version starts with all text content identity from the original but an empty link subspace. This is intentional behavior per EWD-021. The formal spec must distinguish between text-subspace copying (which happens) and link-subspace copying (which does not).

**Concrete example**:
```
Pre-state:
  Source document vspanset:
    at 0 for 0.1    (link subspace — link orgl ISA)
    at 1 for 1      (text subspace — permascroll I-addresses)

CREATENEWVERSION(source) → version

Post-state:
  Version vspanset: at 1.1 for 0.15   (text subspace only)
  Source vspanset:  at 0 for 0.1, at 1 for 1   (unchanged)
```

**Code references**:
- `do1.c:264-303` — `docreatenewversion()` retrieves vspan and calls `docopyinternal`
- `do1.c:305-313` — `doretrievedocvspanfoo()` (identical to `doretrievedocvspan`)
- `orglinks.c:155-162` — `retrievedocumentpartofvspanpm()` returns V-displacement and width starting at text position

**Provenance**: Finding 0043

#### Finding 0046

**What happens:** `CREATENEWVERSION` copies ONLY the text subspace (V-dimension 1.x) from the source document's POOM, not the link subspace (2.x). The function `docreatenewversion()` at `do1.c:264-303` calls `doretrievedocvspanfoo()` which delegates to `retrievedocumentpartofvspanpm()` at `orglinks.c:155-162`. That function extracts only the V-dimension width from the root crum, which covers the 1.x text subspace. Links stored at 2.x V-positions are excluded because they fall outside this V-dimension width. The version's POOM therefore contains only text V→I mappings.

**Why it matters for spec:** The postcondition for CREATENEWVERSION is: `poom(new_doc) = { (v, i) ∈ poom(source) | v.subspace = 1 }`. The version shares I-addresses with the source for text content but has NO link entries in its own POOM. Despite this, links ARE discoverable from the version because `find_links` operates in I-space via the spanf index — shared I-addresses cause the version to "inherit" links. This separates the document-level model (POOM contains text only) from the system-level model (links discoverable via shared I-addresses).

**Code references:**
- `docreatenewversion()` — `do1.c:264-303` — Version creation, text-only copy
- `doretrievedocvspanfoo()` — `do1.c:305-313` — Extracts text V-span
- `retrievedocumentpartofvspanpm()` — `orglinks.c:155-162` — V-dimension extraction (self-described as "a kluge")
- `docopyinternal()` — called from `docreatenewversion()` to copy text content

**Concrete example:**
```
Original document:
  vspanset = [{start: "0", width: "0.1"}, {start: "1", width: "1"}]
  (links at 0.x, text at 1.x)

After CREATENEWVERSION:
  Version vspanset = [{start: "1.1", width: "0.34"}]
  (text only, no link subspace)

  find_links FROM version → ["1.1.0.1.0.1.0.2.1"]
  (link discovered via shared I-addresses, not via version's POOM)
```

**Provenance:** Finding 0046

#### Finding 0072

**What happens**: `CREATENEWVERSION` is the sole mechanism for preserving a document's state before editing. It creates a new POOM tree that shares I-addresses with the original for text content. The original and version are separate tree structures — editing one does not affect the other. Critically, there is no automatic invocation of this operation; it must be called explicitly before any edit whose prior state might need recovery.

The mechanism: `docreatenewversion` calls `doretrievedocvspanfoo` to obtain the source document's text vspan, creates a new orgl in the granfilade via `createorglingranf`, then copies text content via `docopyinternal`. The copy shares I-addresses (identity-preserving), so version comparison and provenance chains work across the original and its version.

**Why it matters for spec**: The precondition for historical recovery is the prior existence of a version:

```
recoverable(D, state_at_t) ⟺ ∃ V : CREATENEWVERSION(D) executed at time t, producing V
```

Without an explicit version, no prior state is recoverable. This is a hard constraint — not a soft degradation. The spec must not assume automatic history.

**Code references**:
- `backend/do1.c:264-303` — `docreatenewversion`: retrieves vspan, creates new orgl, copies text via `docopyinternal`
- `backend/do1.c:305-313` — `doretrievedocvspanfoo`: returns text subspace vspan

**Provenance**: Finding 0072

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DUAL-ENFILADE], [SS-POOM-MUTABILITY], [SS-VERSION-ADDRESS], [PRE-COPY], [ST-DELETE], [ST-INSERT], [ST-REARRANGE], [ST-VCOPY], [FC-CONTENT-SPANF-ISOLATION], [FC-DOC-ISOLATION], [FC-SUBSPACE], [FC-VERSION-ISOLATION], [INV-ATOMICITY], [INV-DELETE-NOT-INVERSE], [INV-IADDR-PROVENANCE], [INV-REARRANGE-IDENTITY], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [INT-VERSION-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-EMPTY-DOC]

---

### ST-CREATE-LINK

**Sources:** Findings 0012, 0052

#### Finding 0012

**What happens:** Link creation (`docreatelink`) is a compound state transition that updates both enfilades atomically: (1) create a link orgl in `granf` via `createorglingranf()`; (2) copy the link's ISA reference into the document's link subspace (`0.x`) via `docopy()`; (3) index all link endpoints in `spanf` via `insertendsetsinspanf()`. This three-step sequence modifies both `granf` (new orgl + document modification) and `spanf` (new index entries).

**Why it matters for spec:** This is the only documented operation that writes to both enfilades. The postcondition must specify effects on both: `granf' = granf + {new_link_orgl} + doc_updated` AND `spanf' = spanf + {endpoint_i_addrs → new_link}`. The precondition is that the document and endpoint content must exist in `granf`. This compound transition is where the dual-enfilade consistency invariant (INV-DUAL-ENFILADE-CONSISTENCY) is most at risk.

**Code references:**
- `do1.c:199-225` — `docreatelink()` full three-step sequence

**Concrete example:**
```
Pre-state:
  granf: document orgl at ISA 1.1.0.1.0.1 with text content
  spanf: empty

docreatelink(doc=1.1.0.1.0.1, from=..., to=..., three=...)

Post-state:
  granf: document orgl updated (0.1 → link ISA 1.1.0.1.0.2)
       + new link orgl at ISA 1.1.0.1.0.2
  spanf: from-endpoint I-addrs → 1.1.0.1.0.2
       + to-endpoint I-addrs → 1.1.0.1.0.2
       + three-endpoint I-addrs → 1.1.0.1.0.2
```

**Provenance:** Finding 0012

#### Finding 0052

**What happens:** CREATELINK uses the same insertion code path as INSERT and COPY: `docreatelink` → `docopy` → `insertpm` → `insertnd` → `makegappm`. The `makegappm` function shifts existing POOM entries at or beyond the insertion point by adding the insertion width to their V-dimension displacement (case 1 / "THRUME" in `insertnd`). This means CREATELINK has shifting semantics identical to INSERT for any POOM entries beyond the insertion point.

However, this shifting is not observable in practice because `findnextlinkvsa` always places the new link orgl at the current document end (`vspanreach`) or at `2.1` if no links exist yet. Since no POOM entries exist beyond the document end, there is nothing to shift. The "no shifting" behavior of CREATELINK is an emergent property of append-at-end placement, not a fundamental property of the operation.

**Why it matters for spec:** The postcondition for `create_link` must technically include the same shifting semantics as `insert`: `forall v in POOM : v >= insertion_point ==> v' = v + width`. However, the precondition established by `findnextlinkvsa` guarantees `insertion_point = max(2.1, vspanreach)`, which means `{v in POOM : v >= insertion_point} = {}`. The spec can model CREATELINK as append-only for sequential operation, but the underlying mechanism permits shifting if the insertion point were placed before existing entries.

**Code references:**
- `backend/do1.c:199-225` — `docreatelink` calls `docopy` at line 216
- `backend/do1.c:45-65` — `docopy` calls `insertpm` at line 60
- `backend/insertnd.c:15-94` — `insertnd` dispatches to `makegappm` for POOM case at line 54
- `backend/insertnd.c:124-172` — `makegappm` shifts entries via `tumbleradd` at line 162
- `backend/do2.c:151-167` — `findnextlinkvsa` computes append-at-end position

**Concrete example:**
```
Pre-state: Document with text at V 1.1..1.24, link1 orgl at V 2.1
  POOM contains entry for link1 at V-displacement 2.1

Operation: create_link (second link)
  findnextlinkvsa computes insertion point = vspanreach (beyond 2.1)
  makegappm scans POOM entries: link1 at 2.1 is BEFORE insertion point (case 0/2)
  No entries are shifted

Post-state: link2 orgl appended at end, link1 V-position unchanged
  POOM: link1 at 2.1 (unchanged), link2 at 2.2

Hypothetical: If insertion point were forced to 2.1 (before link1):
  makegappm would classify link1 as case 1 (THRUME)
  link1's V-displacement would be shifted: 2.1 + width → higher position
```

**Provenance:** Finding 0052

**Co-occurring entries:** [SS-DUAL-ENFILADE], [SS-GRANF-OPERATIONS], [SS-LINK-SUBSPACE], [SS-SPANF-OPERATIONS], [ST-INSERT], [FC-CONTENT-SPANF-ISOLATION], [INV-DUAL-ENFILADE-CONSISTENCY], [EC-CONCURRENT-LINK-CREATION]

---

### ST-VSPAN-TO-SPORGL

**Source:** Finding 0013

**What happens:** The function `vspanset2sporglset()` converts a set of V-address spans within a document into sporgls. For each vspan, it: (1) converts V-addresses to I-addresses via the document's enfilade (`vspanset2ispanset`); (2) attaches the source document ISA to each resulting I-span, producing a sporgl. The output sporglset preserves the content identity (I-address) while adding provenance (which document). The reverse operation `linksporglset2specset()` converts sporgls back to V-address specs for display or user-facing operations.

**Why it matters for spec:** This is a key state transition in many compound operations. The conversion is: `vspan_to_sporgl(doc, vspan) = { origin: V_to_I(doc, vspan.start), width: vspan.width, source_doc: doc.isa }`. The postcondition is that the I-address range in the sporgl exactly corresponds to the content at the given V-positions in the document. This conversion is a pure function over the document's current V→I mapping — it reads the enfilade but does not modify it. The inverse `linksporglset2specset` is also pure: it looks up the sporgl's I-address in the source document's enfilade to recover V-positions.

**Code references:**
- `sporgl.c:35-65` — `vspanset2sporglset()` implementation
- `sporgl.c:97+` — `linksporglset2specset()` reverse conversion

**Concrete example:**
```
Input:
  doc ISA = 1.1.0.1.0.1
  vspan = V-range 1.1..1.15 (first 15 characters)

vspanset2sporglset(doc, vspan):
  Step 1: vspanset2ispanset → I-span at 2.1.0.5.0.100 for 0.15
  Step 2: attach doc ISA → sporgl(origin=2.1.0.5.0.100, width=0.15, doc=1.1.0.1.0.1)

Output: sporglset with one sporgl carrying both I-address and document provenance
```

**Provenance:** Finding 0013
**Co-occurring entries:** [SS-SPORGL], [INT-SPORGL-LINK-INDEX], [INT-SPORGL-TRANSCLUSION], [INT-SPORGL-VERSION-COMPARE]

---

### ST-COMPARE-VERSIONS

**Source:** Finding 0015

**What happens**: The `compare_versions` operation (FEBE opcode 10: SHOWRELATIONOF2VERSIONS) answers the question: "What text content do these two documents share by common origin?" The operation produces a list of ordered pairs of V-spans — one from each document — where the paired spans reference the same permascroll I-address range. The semantic definition is: two spans correspond if and only if they map to the same permascroll content identities.

**Why it matters for spec**: This is the postcondition for `compare_versions`. Each pair `(span_a, span_b)` in the result satisfies: `VSpanToISpan(doc_a, span_a) == VSpanToISpan(doc_b, span_b)` where both I-spans are permascroll addresses. The result is complete: every shared permascroll address range appears in exactly one pair. The result covers only text content — link references are excluded by definition, not by accident.

**Code references**:
- `correspond.c` — nested loop computing I-span intersections and mapping back to V-spans

**Concrete example**:
```
Document A: "Hello World" (text at V 1.1..1.11, permascroll I-addrs P₁..P₁₁)
Document B: version of A, then insert "Dear " at position 6
  → "Hello Dear World" (V 1.1..1.16)
  → "Hello" has permascroll I-addrs P₁..P₅, "World" has P₆..P₁₁

compare_versions(A, B) returns:
  [(A: V 1.1 for 5, B: V 1.1 for 5),     // "Hello" — same P₁..P₅
   (A: V 1.6 for 6, B: V 1.11 for 6)]    // "World" — same P₆..P₁₁
```

**Provenance**: Finding 0015
**Co-occurring entries:** [SS-CONTENT-IDENTITY], [PRE-COMPARE-VERSIONS], [INV-SUBSPACE-CONVENTION]

---

### ST-LINK-CREATE

**Sources:** Findings 0020, 0037

#### Finding 0020

When an internal link is created, it is bidirectionally traversable just like cross-document links. `follow_link(link, "target")` returns the target text and `follow_link(link, "source")` returns the source text, regardless of whether both endpoints are in the same document.

Concrete example:
- Before: Document contains "glossary" and "Glossary", no links
- Operation: `create_link(source="glossary", target="Glossary", same_document=true, type="jump")`
- After: Link exists; `follow_link(link, "target")` returns "Glossary"; `follow_link(link, "source")` returns "glossary"

**Why it matters for spec:** The postcondition for link creation is uniform — internal and cross-document links have identical traversal semantics. No special case is needed in the spec for same-document links.

**Code references:** Test `links/self_referential_link`

**Provenance:** Finding 0020

#### Finding 0037

**What happens:** When `domakelink` receives a V-span that maps to non-contiguous I-addresses (due to transclusion from multiple sources), the backend automatically splits the V-span into multiple I-spans (sporgls) in the link endset — one per contiguous I-address region. The front end does NOT need to pre-split the V-span. The critical mechanism is the inner loop in `vspanset2sporglset` (sporgl.c:49-58), which iterates over every I-span returned by `vspanset2ispanset` and creates a separate sporgl for each.

The conversion chain is: V-span → `vspanset2ispanset` → `permute` → `span2spanset` → `retrieverestricted` to find all context entries → separate I-span per contiguous I-address region → separate sporgl per I-span.

**Why it matters for spec:** The postcondition for `create_link` must specify that one V-span input may produce multiple I-span entries in the link endset. Formally: `create_link(home, source_vspan, target_vspan, type)` yields `link.source_endset = { sporgl(origin=i.start, width=i.width, doc=source_doc) | i ∈ V_to_ISpans(source_doc, source_vspan) }` where `V_to_ISpans` returns one I-span per contiguous I-address region. The cardinality of `link.source_endset` may exceed the cardinality of the input vspan set. This is a pure consequence of the V→I mapping; the operation does not modify any document state.

**Code references:**
- `do1.c:173-197` — `domakelink`, main link creation entry point
- `sporgl.c:35-65` — `vspanset2sporglset`, V-span to sporgl conversion with splitting
- `sporgl.c:49-58` — inner loop creating one sporgl per I-span
- `orglinks.c:397-402` — `vspanset2ispanset`, delegates to `permute`
- `orglinks.c:404-422` — `permute`, finds all contiguous I-regions
- `orglinks.c:425-454` — `span2spanset`, uses `retrieverestricted` to get contexts

**Concrete example:**
```
Document C contains "AABB" at V 1.1..1.4 where:
  "AA" was transcluded from document A (I-addresses from A's permascroll region)
  "BB" was transcluded from document B (I-addresses from B's permascroll region)

create_link(source = V-span 1.1 width 0.4 in doc C, ...)

Input:  1 V-span covering all of "AABB"
Output: 2 sporgls in source endset:
  sporgl₁: origin = I-addr(A,"AA"), width = 0.2, doc = C
  sporgl₂: origin = I-addr(B,"BB"), width = 0.2, doc = C

The I-addresses for A and B are non-contiguous in the permascroll,
so they cannot be represented as a single I-span.
```

**Provenance:** Finding 0037

**Co-occurring entries:** [SS-LINK-ENDPOINT], [PRE-LINK-CREATE], [INT-LINK-TRANSCLUSION], [EC-LINK-PARTIAL-SURVIVAL], [EC-SELF-LINK]

---

### ST-ADDRESS-ALLOC

**Sources:** Findings 0021, 0025, 0065, 0068

#### Finding 0021

**What happens**: New addresses are allocated by `findisatoinsertnonmolecule` in `granf2.c`:

1. Compute upper bound from the parent (hint) address: `upperbound = tumblerincrement(hintisa, depth-1, 1)` — the next sibling of the parent.
2. Find the highest existing address below upperbound via `findpreviousisagr`.
3. If nothing found under the parent, create the first child: `hintisa.0.1`.
4. Otherwise, truncate the found item and increment to produce the next sibling.

The entire granf (global address enfilade) is a single flat tree; the allocation algorithm enforces hierarchical structure by bounding searches to the parent's address range.

**Why it matters for spec**: Defines the postcondition for address allocation — the allocated address must be (a) under the parent, (b) greater than all existing addresses under the parent, and (c) unique. The first-child convention (`parent.0.1`) is a concrete invariant.

**Code references**: `granf2.c:findisatoinsertnonmolecule`, `findpreviousisagr`, `tumblerincrement`.

**Concrete example**:
- Parent account `1.1.0.2`, no existing documents → allocates `1.1.0.2.0.1`
- Parent account `1.1.0.2`, existing document `1.1.0.2.0.1` → allocates `1.1.0.2.0.2`

**Provenance**: Finding 0021

#### Finding 0025

**What happens**: Link address allocation follows the same hierarchical allocation pattern as document addresses. When a link is created with a given home document, its address is allocated as the next available child under that home document's address. The first link under a home document gets suffix `.0.2.1`, subsequent links get `.0.2.2`, `.0.2.3`, etc. This confirms that the general address allocation mechanism (documented for documents under accounts) also governs link allocation under documents.

**Why it matters for spec**: The postcondition for `create_link` includes an address allocation step: `address(new_link) = next_child(home_doc, link_subspace)`. This unifies link and document allocation under the same allocation model — the allocator is agnostic to what kind of entity is being allocated; it only cares about the parent address and the allocation depth.

**Code references**: Test `links/find_links_filter_by_homedocid`; `granf2.c:findisatoinsertnonmolecule` for the general allocation mechanism.

**Provenance**: Finding 0025

#### Finding 0065

**Detail level: Essential**

MAKELINK allocates link I-addresses using query-and-increment within a document-bounded region of the global granfilade. The allocation uses the same `findisatoinsertmolecule` mechanism as text allocation but with different bounds.

**What happens:**
1. `upperbound` is set to `docISA.2.3` (bounding search to the document's link subspace)
2. `findpreviousisagr` finds the highest existing link I-address below that bound
3. If no links exist yet (`lowerbound < docISA.2.2`), allocate at `docISA.2.2.1`
4. Otherwise, increment from `lowerbound` (the highest existing link's address) by `0.1`

**Why it matters for spec:** The allocation postcondition for MAKELINK is: the new link's I-address is strictly greater than all existing link I-addresses in the same document, and independent of link I-addresses in other documents.

**Concrete example (before/after):**
- Before: Document A has link at `docA.2.1`; Document B has no links
- MAKELINK on B → B gets link at `docB.2.1` (B's own first link)
- MAKELINK on A → A gets link at `docA.2.2` (consecutive with A's existing link, unaffected by B)

**Code references:**
- `backend/granf2.c:162` — `tumblerincrement(&hintptr->hintisa, 2, hintptr->atomtype + 1, &upperbound)` sets document-scoped bound
- `backend/granf2.c:164` — `findpreviousisagr` performs bounded search
- `backend/granf2.c:171-175` — allocation logic: first-link vs increment cases

**Provenance:** Finding 0065

#### Finding 0068

**What happens:** VERSION uses the same stateless query-and-increment allocation mechanism as CREATE and INSERT. For owned-document versions, the algorithm:

1. Computes upper bound: `tumblerincrement(source_doc, depth-1=0, 1)` — the next sibling of the source document (e.g., `1.1.0.1.0.2` for source `1.1.0.1.0.1`).
2. Calls `findpreviousisagr` to find the highest existing address below the upper bound.
3. Applies containment check: verifies the found address is actually under the source document.
4. If no child exists: allocates first child as `source_doc.1` (e.g., `1.1.0.1.0.1.1`).
5. If child exists: truncates and increments to produce next sibling (e.g., `1.1.0.1.0.1.2`).

This extends ST-ADDRESS-ALLOC from Finding 0021 with the VERSION-specific hint parameters.

**Why it matters for spec:** The postcondition for owned-version allocation is: `allocated = max_child(source_doc, granf) + 1`, where `max_child` returns the highest existing address under `source_doc`. If no children exist: `allocated = source_doc.1`. The allocation is a pure function of granfilade state, with no session-local counter.

**Code references:** `granf2.c:203-242` — `findisatoinsertnonmolecule` (query-and-increment). `granf2.c:255-278` — `findpreviousisagr` (tree traversal). `granf2.c:130-156` — `findisatoinsertgr` (allocation dispatcher).

**Concrete example:**
Second version of `1.1.0.1.0.1`:
1. `hintisa = 1.1.0.1.0.1`, depth=1
2. `upperbound = 1.1.0.1.0.2`
3. `findpreviousisagr` finds `1.1.0.1.0.1.1` (first version)
4. Truncate to length 7: `1.1.0.1.0.1.1`, increment: `1.1.0.1.0.1.2`

**Provenance:** Finding 0068

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-HOME-DOCUMENT], [SS-TUMBLER-CONTAINMENT], [SS-VERSION-ADDRESS], [PRE-ADDRESS-ALLOC], [PRE-FIND-LINKS], [PRE-VERSION-OWNERSHIP], [FC-DOC-ISOLATION], [FC-GRANF-ON-DELETE], [INV-ACCOUNT-ISOLATION], [INV-MONOTONIC], [EC-HOMEDOCIDS-FILTER-BROKEN]

---

### ST-LINK-GLOBAL-VISIBILITY

**Source:** Finding 0022

**What happens:** Links created in any session are immediately visible to all other sessions. `find_links()` from session B returns links created by session A without any synchronization or coordination step.

**Why it matters for spec:** Postcondition of link creation: after `create_link(source, target)` succeeds in any session, `find_links(source)` in any session (including others) includes the new link. Link storage is part of global state.

**Concrete example:**
- Session A: `create_link(source, target)` → `link_id`
- Session B: `find_links(source)` → `[link_id]`

**Provenance:** Finding 0022, section 3
**Co-occurring entries:** [SS-SESSION-STATE], [ST-CROSS-SESSION-VERSIONING], [FC-SESSION-ACCOUNT-ISOLATION], [INV-GLOBAL-ADDRESS-UNIQUENESS], [INT-CROSS-SESSION-TRANSCLUSION], [EC-CONFLICT-COPY-NO-MERGE]

---

### ST-CROSS-SESSION-VERSIONING

**Source:** Finding 0022

**What happens:** When multiple sessions create versions of the same document, each version gets a unique address. The versions can be modified independently while sharing content identity with the original.

**Why it matters for spec:** Postcondition of `create_version`: the resulting version address is globally unique (ties to INV-GLOBAL-ADDRESS-UNIQUENESS). Multiple sessions versioning the same document produce distinct version addresses that each maintain independent state while preserving content identity with the source.

**Concrete example:**
- Session A: `create_version(original)` → `version_a`
- Session B: `create_version(original)` → `version_b`
- `version_a ≠ version_b`, both share content identity with `original`

**Provenance:** Finding 0022, section 6
**Co-occurring entries:** [SS-SESSION-STATE], [ST-LINK-GLOBAL-VISIBILITY], [FC-SESSION-ACCOUNT-ISOLATION], [INV-GLOBAL-ADDRESS-UNIQUENESS], [INT-CROSS-SESSION-TRANSCLUSION], [EC-CONFLICT-COPY-NO-MERGE]

---

### ST-DELETE

**Sources:** Findings 0023, 0024, 0040, 0053, 0055, 0057, 0058, 0064, 0072, 0075

#### Finding 0023

**What happens:** Delete removes content from a document's V-stream (visible content) but does NOT remove the content's I-address from the document's address space or from the spanf index. After deletion, `retrieve_contents` no longer returns the deleted content, but `find_documents` still reports the document as containing that content identity.

**Why it matters for spec:** Delete postcondition must be stated precisely in two parts:
1. V-stream effect: the deleted span is removed from the document's visible content
2. I-stream non-effect: the I-address association is preserved — `FINDDOCSCONTAINING` results are unchanged

This dual nature means the delete postcondition is: `retrieve(D_after) = retrieve(D_before) \ deleted_span` AND `FINDDOCSCONTAINING(α) = FINDDOCSCONTAINING(α)_before` for all I-addresses `α` in the deleted span.

**Concrete example:**
```
Before: Dest contains "Prefix: Findable"
  V-stream: "Prefix: Findable"
  I-address associations: {α_P, α_r, ..., α_e (for "Prefix: "), β_F, β_i, ..., β_e (for "Findable")}

After DELETE("Findable" from Dest):
  V-stream: "Prefix: "           # β addresses gone from V-stream
  I-address associations: unchanged — β addresses still in spanf index for Dest
```

**Code references:** Test `find_documents_after_delete` in golden/discovery/.

**Provenance:** Finding 0023.

#### Finding 0024

**What happens:** Finding 0024 confirms and extends the delete postcondition: deletion removes content from the V-stream but preserves link objects in the 0.2.x subspace. After deleting all text from a document that contains links, the links remain accessible. The document's vspanset still shows link spans even when all text spans are gone.

This is consistent with Finding 0023's characterization of delete as V-stream-only, and adds the link dimension: delete affects neither I-address associations (Finding 0023) nor link objects stored in the document (Finding 0024).

**Why it matters for spec:** Extends the ST-DELETE postcondition: `delete(D, span) ⟹ link_spans(D)_after = link_spans(D)_before`. Delete operates exclusively on the text subspace (1.x); the link subspace (0.2.x) is a frame condition for delete.

**Provenance:** Finding 0024, Semantic Insight 2 and Technical Discovery 2.

#### Finding 0040

**What happens:** `DELETEVSPAN` targeting the link subspace (V-position 2.x) removes the link's V-to-I mapping from the document's POOM. The operation succeeds when the width is non-zero. After deletion, the document's vspanset no longer includes the link span. The `deletevspanpm()` function calls `deletend()` on the document's orgl enfilade in the V-dimension, then logs the document as modified.

This extends the known DELETE behavior: just as deleting text at 1.x removes text from the V-stream but preserves I-space content, deleting links at 2.x removes the link's POOM presence but preserves the link orgl in I-space and DOCISPAN entries in the spanfilade.

**Why it matters for spec:** The postcondition for DELETE must cover all subspaces uniformly. For any subspace `s` and V-range `r`: `delete(D, s, r) ⟹ vspanset(D)_after ∩ (s, r) = ∅`. The frame conditions differ by what persists: text deletion preserves I-space content bytes; link deletion preserves I-space link orgl AND spanfilade entries. Formally: `delete(D, 2.x, r) ⟹ link_orgl(link) unchanged ∧ spanfilade_entries(link) unchanged`.

**Code references:**
- `orglinks.c:145-152` — `deletevspanpm()` checks for zero-width, calls `deletend()`, logs modification
- `edit.c:31-76` — `deletend()` removes crums covering the specified V-range

**Concrete example:**
```
Pre-state:
  doc vspanset: [{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]

Operation: session.delete(doc, Address(2, 1), Offset(0, 1))
Result: SUCCESS

Post-state:
  doc vspanset: [{"start": "1.1", "width": "0.11"}]
  Link subspace gone from vspanset; text subspace unchanged.
```

**Provenance:** Finding 0040, Test Results and Code Evidence sections.

#### Finding 0053

**What happens:** DELETE shifts V-positions of POOM entries after the deletion range. In `deletend()` (edit.c:31-76), Case 2 handles entries positioned entirely after the deletion: their V-position is reduced by the deletion width via `tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index])`. There is no bounds check — if the deletion width exceeds the entry's current V-position, the result is a negative tumbler that is stored directly back into the POOM entry.

This means DELETE can produce POOM entries whose V-positions are negative. These entries remain in the POOM tree but become invisible: negative tumblers sort before all positive tumblers, placing them outside the valid V-address range. Link endsets at such positions return empty results from FOLLOWLINK.

**Why it matters for spec:** The postcondition for DELETE's V-position shifting must account for the possibility of negative results. Formally: `∀ entry ∈ poom(doc) : entry.vpos > delete_end ⟹ entry.vpos' = entry.vpos - delete_width`. When `delete_width > entry.vpos`, the result `entry.vpos'` is negative, creating a state where the entry exists in the POOM but maps to no valid V-address. The current implementation has no precondition preventing this — `pre_delete` does not check whether the shift would push entries negative.

**Code references:**
- `edit.c:63` — Case 2 subtraction: `tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index])`
- `edit.c:31-76` — `deletend()` full case analysis

**Concrete example:**
```
Pre-state:
  Document text at 1.1-1.15, link endset at V-position 1.5 (after POOM creation)

Operation: DELETE 3 bytes at 1.1
  Case 2 shift: 1.5 - 0.3 = 1.2 (valid, positive)
  Link endset now at 1.2

Operation: DELETE 10 bytes at 1.1
  Case 2 shift: 1.2 - 0.10 = -0.8 (negative!)
  Link endset stored at V-position -0.8

Post-state:
  POOM entry exists with sign=1 V-position
  FOLLOWLINK returns empty endsets []
  FINDLINKS cannot locate the link
```

**Provenance:** Finding 0053

#### Finding 0055

**What happens:** DELETE's V-position shifting via `tumblersub` only affects entries whose displacement tumbler shares the same exponent as the deletion width. Text crums within the deletion's subspace have displacements at exp=-1 (same level as the width), so `strongsub` proceeds to the main subtraction path and they shift. Link crums at exp=0 are unaffected because `strongsub` returns them unchanged.

This corrects Finding 0053's ST-DELETE entry. The postcondition for DELETE is not "all entries after the deletion point shift" — it is "only entries after the deletion point whose V-displacement exponent matches the width exponent shift." Entries at higher hierarchy levels (higher exponent) are immune to the shift.

**Why it matters for spec:** The corrected postcondition for DELETE: `∀ entry ∈ poom(doc) : entry.vpos > delete_end ∧ entry.vpos.exp = width.exp ==> entry.vpos' = entry.vpos - delete_width`. Entries where `entry.vpos.exp > width.exp` satisfy the frame condition `entry.vpos' = entry.vpos`. The exponent match condition is the discriminator, not a subspace check or type check.

**Code references:**
- `edit.c:63` — Case 2: `tumblersub(&ptr->cdsp.dsas[V], width, &ptr->cdsp.dsas[V])`
- `tumble.c:534-547` — `strongsub` exponent guard determines whether subtraction occurs

**Concrete example:**
```
Pre-state:
  Text crum at V-displacement 0.4 (exp=-1)
  Link crum at V-displacement 2.1 (exp=0)
  Deletion width: 0.3 (exp=-1)

Text crum: strongsub(0.4, 0.3) → exp match → subtraction proceeds → 0.1
Link crum: strongsub(2.1, 0.3) → exp mismatch → returns 2.1 unchanged
```

**Provenance:** Finding 0055

#### Finding 0057

**What happens:** DELETE (`dodeletevspan`) removes the V-to-I mapping from the document's POOM via `deletevspanpm` → `deletend`, but does NOT remove the corresponding spanfilade entry created by the original COPY/INSERT. The spanfilade continues to assert that the document contains I-addresses that the document's POOM no longer maps. Specifically, `deletevspanpm` calls only `deletend` on the document's orgl in granf and `logbertmodified` — there is no call to any spanf function.

**Why it matters for spec:** Extends ST-DELETE postcondition with an explicit frame condition on spanf: `delete(D, vspan) ⟹ spanf_entries_after = spanf_entries_before`. DELETE modifies only the POOM (granf layer) — the spanfilade is completely untouched. This means the postcondition of DELETE includes: (1) V-to-I mapping removed from POOM, (2) spanf unchanged. The formal model must track POOM state and spanf state independently, as they can diverge after DELETE.

**Concrete example:**
```
Before:
  POOM(D): v₁ → i₁  (content visible at position v₁)
  spanf: i₁ → {D}   (D indexed as containing i₁)

After DELETE(D, v₁):
  POOM(D): ∅          (v₁ mapping removed)
  spanf: i₁ → {D}    (UNCHANGED — D still indexed as containing i₁)
```

**Code references:**
- `backend/do1.c:162-171` — `dodeletevspan`: calls `findorgl` + `deletevspanpm`, no spanf call
- `backend/orglinks.c:145-152` — `deletevspanpm`: calls `deletend` (granf only) + `logbertmodified`
- Contrast with `backend/do1.c:45-65` — `docopy`: calls both `insertpm` AND `insertspanf`

**Provenance:** Finding 0057

#### Finding 0058

**What happens:** When DELETE removes all content from a document, the operation disowns and frees all bottom nodes (height-0) via `disown` + `subtreefree`, then calls `setwispupwards` and `recombine` on the father node. The `recombinend` function processes sibling pairs: `ishouldbother` checks if two siblings can be merged, and `takeovernephewsnd` transfers children between them (freeing empty siblings in the process). Finally, if `father->isapex`, `recombinend` calls `levelpull` — but since `levelpull` is disabled, the tree height is never reduced.

The result: after delete-everything, the tree retains its prior height with empty intermediate nodes (numberofsons=0) still allocated. The POOM returns zero-width content (functionally empty), but the tree structure is not collapsed.

**Why it matters for spec:** The ST-DELETE postcondition must include: after deleting the entire V-span, `poom(doc)` maps no V-addresses (retrieve returns empty), BUT the enfilade tree height is unchanged: `enf.height_after = enf.height_before`. The tree's structural state is NOT equivalent to `createenf()` output. This means `delete_all` is not the inverse of the cumulative inserts — it removes the mapping but not the structural growth. Formally: `delete_all(doc) ⟹ dom(poom(doc)) = ∅ ∧ enf.height(doc) = enf.height_before(doc)`.

**Code references:**
- `backend/edit.c:31-76` — `deletend`: Case 1 disowns/frees bottom nodes, calls `recombine`
- `backend/recombine.c:104-131` — `recombinend`: processes siblings, calls `levelpull` on apex
- `backend/recombine.c:194-202` — `takeovernephewsnd`: frees empty sibling nodes during merge
- `backend/genf.c:318-342` — `levelpull`: disabled, returns 0

**Concrete example:**
```
Before DELETE (8 bytes at 1.1, tree height=3):
  Fullcrum (height=3, numberofsons=2)
    ├─ Height-2 node (numberofsons=2)
    │    ├─ Height-1 node (bottom nodes with content)
    │    └─ Height-1 node (bottom nodes with content)
    └─ Height-2 node (numberofsons=1)
         └─ Height-1 node (bottom nodes with content)

After DELETE(doc, 1.1, 0.8):
  Fullcrum (height=3, numberofsons=2)    ← height unchanged
    ├─ Height-2 node (numberofsons=0)    ← empty, not freed
    └─ Height-2 node (numberofsons=0)    ← empty, not freed

  retrieve_vspanset → empty (zero-width)
  Tree height remains 3, not collapsed to 1
```

**Provenance:** Finding 0058

#### Finding 0064

**What happens**: DELETE operates exclusively on the POOM enfilade — it removes V-to-I mappings by pruning bottom crums (height-0 nodes) via `disown` + `subtreefree`. The I-addresses themselves continue to exist in the granfilade (which is append-only) and in the spanfilade (which has no delete operation). Other documents that reference the same I-addresses through transclusion are completely unaffected — their POOM mappings remain intact.

The critical consequence: after DELETE removes a V-span, the I-addresses that were mapped become unreferenced *in this document only*. The content bytes persist in the granfilade, the spanfilade still indexes them, and any other document sharing those I-addresses retains its mapping.

**Why it matters for spec**: Extends the ST-DELETE postcondition with explicit I-space semantics. DELETE destroys the local V-to-I mapping but does NOT destroy the I-addresses themselves. Formally:

```
delete(D, vspan) ⟹
  (1) ∀ v ∈ vspan : v ∉ dom(poom(D))          -- V-to-I mapping removed
  (2) ∀ i ∈ iaddrs(vspan) : i ∈ granfilade    -- content bytes persist
  (3) ∀ D' ≠ D : poom(D') unchanged           -- other documents unaffected
```

**Code references**:
- `backend/edit.c:76-84` — `deletend` case 1: `disown` + `subtreefree` on bottom crums
- `backend/do1.c:162-171` — `dodeletevspan`: calls `deletevspanpm` (granf only, no spanf call)

**Concrete example**:
```
Before DELETE "BC" (V-addresses 1.2-1.3):
  POOM(D): V(1.1)→I(5.1)  V(1.2)→I(5.2)  V(1.3)→I(5.3)  V(1.4)→I(5.4)
  Granfilade: I(5.1)="A"  I(5.2)="B"  I(5.3)="C"  I(5.4)="D"
  Other doc T (transcluded "BC"): V(2.1)→I(5.2)  V(2.2)→I(5.3)

After DELETE(D, 1.2, 0.2):
  POOM(D): V(1.1)→I(5.1)  V(1.2)→I(5.4)
  Granfilade: I(5.1)="A"  I(5.2)="B"  I(5.3)="C"  I(5.4)="D"  ← UNCHANGED
  Other doc T: V(2.1)→I(5.2)  V(2.2)→I(5.3)                    ← UNCHANGED
```

**Provenance**: Finding 0064

#### Finding 0072

**What happens**: DELETE is a destructive mutation of the POOM enfilade tree. The `deletend` function performs tree surgery: nodes falling entirely within the deletion range are `disown`ed (removed from parent/sibling pointers) and then `subtreefree`d (recursively freed). Nodes partially overlapping the deletion boundary have their V-displacement shifted backward. After pruning, `setwispupwards` recalculates widths up the tree and `recombine` rebalances. No copy of the pre-deletion tree state is preserved anywhere — there is no undo log, edit history, shadow copy, or transaction journal.

**Why it matters for spec**: Strengthens ST-DELETE with an explicit non-recoverability postcondition. The pre-mutation POOM tree `T` cannot be reconstructed from the post-mutation tree `T'`:

```
delete(D, vspan) ⟹
  (1) T' = mutate(T, vspan)          -- tree is structurally modified
  (2) ¬∃ f : T' → T                  -- no recovery function from T' alone
  (3) recovery(D, t) requires ∃ V : created_before(V, t) ∧ V = snapshot(D, t)
```

**Code references**:
- `backend/edit.c:31-76` — `deletend`: `disown` + `subtreefree` on nodes within deletion range, displacement shift on partial overlaps
- `backend/credel.c:413-436` — `subtreefree`: recursive memory deallocation
- `backend/genf.c:349-380` — `disown`: removes crum from tree structure

**Concrete example**:
```
Before: doc contains "First Second Third"
  POOM maps V(1.1)-V(1.18) → I-addresses

After DELETE " Third" then DELETE " Second":
  POOM maps V(1.1)-V(1.5) → I-addresses for "First"
  The intermediate state (containing " Second") is gone — the POOM nodes
  were freed by subtreefree. No mechanism exists to recover "First Second"
  or "First Second Third" from the current POOM state alone.
```

**Provenance**: Finding 0072

#### Finding 0075

**What happens:** When DELETE boundaries align exactly with existing bottom crum boundaries, the cutting phase (Phase 1) is bypassed entirely for those boundaries. The crum is instead processed whole in Phase 2, where it is classified and either removed entirely (Case 1: crum falls within the deletion range) or left intact (Case 0: crum is outside the deletion range). This is an optimization: boundary-aligned deletions require no splitting, only classification.

For a deletion that spans exactly one crum from grasp to reach, neither boundary triggers `slicecbcpm`. The crum is classified as type 1 (fully within deletion range) and removed as a unit. No new crums are created.

**Why it matters for spec:** The DELETE state transition has two sub-paths depending on boundary alignment. For a formal model: `delete(doc, start, end)` produces cutting only at boundaries where `∃ crum : crum.grasp < boundary < crum.reach`. At boundaries coinciding with crum edges, no structural modification occurs in Phase 1 — the tree topology is unchanged until Phase 2 classification. This simplifies reasoning about DELETE: boundary-aligned deletions can be modeled as pure removal without intermediate split states.

**Code references:**
- `ndcuts.c:77-90` — `makecutsbackuptohere()`: only calls `slicecbcpm` for `THRUME`
- `edit.c:31-76` — `deletend()`: Phase 2 classification after Phase 1 cutting

**Provenance:** Finding 0075

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-DUAL-ENFILADE], [SS-ENFILADE-TREE], [SS-LINK-ENDPOINT], [SS-POOM-MUTABILITY], [SS-THREE-LAYER-MODEL], [SS-TUMBLER], [PRE-DELETE], [ST-COPY], [ST-VERSION-CREATE], [FC-DELETE-CROSS-DOC], [FC-LINK-DELETE-ISOLATION], [FC-LINK-PERSISTENCE], [FC-SUBSPACE], [FC-VERSION-ISOLATION], [INV-DELETE-NOT-INVERSE], [INV-ENFILADE-MINIMALITY], [INV-IADDR-IMMUTABILITY], [INV-IADDRESS-PERMANENT], [INV-LINK-PERMANENCE], [INV-NO-ZERO-WIDTH-CRUM], [INV-POOM-BIJECTIVITY], [INV-SPANF-WRITE-ONLY], [INT-DELETE-SPANF-DIVERGENCE], [INT-DELETE-SUBSPACE-ASYMMETRY], [EC-DEEPLY-ORPHANED-LINK], [EC-EMPTY-DOC], [EC-ORPHANED-LINK], [EC-REVERSE-ORPHAN], [EC-STALE-SPANF-REFERENCE]

---

### ST-FIND-LINKS

**Sources:** Findings 0028, 0029, 0035

#### Finding 0028

**What happens**: `find_links(search_specset)` discovers links by I-address intersection, not by document or V-address matching. The search specset is converted to I-addresses, and links are returned if any I-address in the search overlaps with I-addresses in a link endpoint. Partial overlap suffices — a search specset that shares even one I-address with a link endpoint will discover that link. The search is purely set-intersection on I-addresses: `find_links(S) = { L | I-addresses(S) ∩ I-addresses(L.source) ≠ ∅ }`.

**Why it matters for spec**: The postcondition for `find_links` is: return the set of all links whose source endpoint I-addresses have non-empty intersection with the search specset's I-addresses. Document identity plays no role — a document that was not involved in link creation can discover the link if it shares content identity (via transclusion) with an endpoint. This is the formal mechanism by which transclusion enables link discovery.

**Code references**: Test `partial_vcopy_of_linked_span` — `find_links` on a document containing only "link" (4 chars transcluded from "hyperlink text") discovers the link created on "hyperlink text"

**Concrete example**:
```
Document A: "ABCDEFGHIJ" (I-addresses I.1 through I.10)
Link source: "DEF" (I-addresses I.4, I.5, I.6)

Document C transcludes "EF" from A via vcopy:
  C contains: "Copy: EF"
  C's "EF" has I-addresses I.5, I.6 (shared with A)

find_links(specset covering C's "EF"):
  I-addresses of search: {I.5, I.6}
  I-addresses of link source: {I.4, I.5, I.6}
  Intersection: {I.5, I.6} ≠ ∅
  → Link returned (partial overlap is sufficient)
```

**Provenance**: Finding 0028b §2

#### Finding 0029

**What happens:** `find_links()` uses AND semantics when called with multiple criteria. When both source and target specs are provided, both endpoints must have V-stream presence for the link to be found. Single-endpoint search (passing NOSPECS for the other) requires only that endpoint's presence.

Cross-endpoint search matrix:

| Source State | Target State | Search by Source | Search by Target |
|--------------|--------------|------------------|------------------|
| Intact       | Intact       | Found            | Found            |
| Deleted      | Intact       | Not found        | Found            |
| Intact       | Deleted      | Found            | Not found        |
| Deleted      | Deleted      | Not found        | Not found        |

When multiple links share a target, deleting one source removes only that link from source-based search; target-based search still finds all links (the link objects themselves are unaffected).

**Why it matters for spec:** Defines the state-transition semantics of `find_links()` — specifically how delete operations on document content transitively affect link discoverability without modifying the links themselves. The AND semantics for multi-criteria search is a key behavioral property: `find_links(source_spec, target_spec)` ≡ `find_links(source_spec) ∩ find_links(target_spec)`.

**Code references:** Tests `search_by_both_endpoints_one_removed`, `search_multiple_links_selective_removal` in `febe/scenarios/links/search_endpoint_removal.py`.

**Concrete example:**
- `find_links(source, target)` before delete → `[link_id]`
- Delete source content
- `find_links(source, target)` → `[]` (AND fails)
- `find_links(NOSPECS, target)` → `[link_id]` (target-only still works)

**Provenance:** Finding 0029, sections 2, 5, 7

#### Finding 0035

**What happens:** FINDNUMOFLINKSFROMTOTHREE (opcode 29) is a trivial wrapper around FINDLINKSFROMTOTHREE. It calls `findlinksfromtothreesp()` to materialize the complete linked list of matching links, then walks the list counting elements. There is no count-only optimization — the full search executes (V-to-I translation, spanfilade search per endset, intersection of result sets), then the list is linearly counted.

**Why it matters for spec:** For formal specification, FINDNUMOFLINKSFROMTOTHREE has identical preconditions and search semantics to FINDLINKSFROMTOTHREE. Its postcondition is simply `|result| = count` where `result` is the set FINDLINKSFROMTOTHREE would return. No additional state transitions or side effects. Both operations are disabled in safe mode (`init.c:75`).

**Code references:**
- `findnumoflinksfromtothreesp()`: `backend/spanf1.c:105-115` — calls full search then counts
- `findlinksfromtothreesp()`: shared search implementation
- `intersectlinksets()`: `backend/spanf2.c:46-120` — O(n*m) or O(n*m*p) intersection
- Safe mode disable: `backend/init.c:75`

**Provenance:** Finding 0035 (section 4)

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [SS-VSPAN-VS-VSPANSET], [PRE-FIND-LINKS], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FOLLOW-LINK], [ST-PAGINATE-LINKS], [ST-RETRIEVE-ENDSETS], [FC-DOC-ISOLATION], [FC-LINK-DELETE-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-LINK-PERMANENCE], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [INT-SPORGL-LINK-INDEX], [INT-TRANSCLUSION-LINK-SEARCH], [EC-CURSOR-INVALIDATION], [EC-SEARCH-SPEC-BEYOND-BOUNDS], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION], [EC-TYPE-FILTER-NONFUNCTIONAL], [EC-VSPAN-MISLEADING-SIZE]

---

### ST-FOLLOW-LINK

**Source:** Finding 0028

**What happens**: `follow_link(link_id, endpoint)` returns the complete, original SpecSet for the requested endpoint, regardless of how the link was discovered. Even when a link is found via partial I-address overlap from a transclusion, `follow_link` returns the full endpoint as it was specified at link creation time. The link is an immutable entity that does not adapt to the discovery context.

**Why it matters for spec**: The postcondition for `follow_link` is: `follow_link(L, SOURCE) == L.source_specset` and `follow_link(L, TARGET) == L.target_specset`, where these specsets are the exact values provided at `create_link` time. There is no filtering, subsetting, or adaptation based on the caller's document or the search that discovered the link. This is a direct consequence of link immutability (SS-LINK-ENDPOINT).

**Code references**: Test `partial_vcopy_of_linked_span` — document contains "link" (4 chars), `follow_link` returns "hyperlink text" (14 chars, the full original source)

**Concrete example**:
```
Link L created with source = "hyperlink text" (14 chars) in Document A
Document C transcludes "link" (4 chars) from A

find_links(C) → {L}  (discovered via partial I-address overlap)
follow_link(L, SOURCE) → SpecSet referencing A at original position for 14 chars
retrieve_contents(follow_link result) → "hyperlink text"  (NOT "link")

The link returns its full source, not the subset that enabled discovery.
```

**Provenance**: Finding 0028b §3
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### ST-RETRIEVE-ENDSETS

**Source:** Finding 0035

**What happens:** RETRIEVEENDSETS (opcode 28) takes a specset (V-spec of a content region) and returns three specsets simultaneously: from-endset, to-endset, and three-endset. It works through the spanfilade, not the link orgl. The call chain: `retrieveendsetsfromspanf()` converts the input specset to a sporglset (V-to-I translation), defines three search spaces using ORGLRANGE prefixes (LINKFROMSPAN=1, LINKTOSPAN=2, LINKTHREESPAN=3), then for each endset type calls `retrievesporglsetinrange()` which searches the spanfilade with SPANRANGE and ORGLRANGE restrictions.

**Why it matters for spec:** RETRIEVEENDSETS is fundamentally different from FOLLOWLINK. FOLLOWLINK takes a known link ID and reads one endset from the link's orgl. RETRIEVEENDSETS searches by content identity through the spanfilade, discovering all link endpoints that intersect a content region. This is the content-identity-based link discovery mechanism — links are discoverable from any document sharing content identity (transclusion, versioning). The three-endset is conditionally retrieved (only if requested).

**Code references:**
- `retrieveendsetsfromspanf()`: `backend/spanf1.c:190-235`
- `specset2sporglset()`: converts V-addresses to I-addresses
- `linksporglset2specset()`: converts I-addresses back to V-specs using querying document's docid

**Concrete example:**
- Input: specset describing a text region in document D1
- Output: three specsets — from-endset (links whose from-end intersects the region), to-endset (links whose to-end intersects), three-endset (links whose three-end intersects)
- Key: endsets are resolved in terms of the querying document's V-space, not the link's home document

| Aspect | FOLLOWLINK | RETRIEVEENDSETS |
|--------|-----------|-----------------|
| Input | link ISA + which-end | specset (content region) |
| Lookup | link orgl direct | spanfilade search |
| Returns | one endset | all three endsets |
| Resolution | link's perspective | querying document's perspective |

**Provenance:** Finding 0035 (section 3)
**Co-occurring entries:** [SS-VSPAN-VS-VSPANSET], [ST-FIND-LINKS], [ST-PAGINATE-LINKS], [INT-SPORGL-LINK-INDEX], [EC-CURSOR-INVALIDATION], [EC-VSPAN-MISLEADING-SIZE]

---

### ST-PAGINATE-LINKS

**Source:** Finding 0035

**What happens:** FINDNEXTNLINKSFROMTOTHREE (opcode 31) implements stateless cursor-based pagination over link search results. On each call it: (1) re-executes the full `findlinksfromtothreesp()` search, (2) if cursor is zero-tumbler, starts from beginning; otherwise linearly scans the result list for an exact tumbler match, (3) if cursor not found, returns empty set with count=0, (4) destructively truncates the list at N items by setting `linkset->next = NULL`.

**Why it matters for spec:** The pagination cursor is a link ISA tumbler, not a positional offset. This means: if the cursor link is deleted between calls, the cursor becomes invalid and an empty result is returned (not an error). The operation is stateless — no server-side cursor state persists between calls. The page size parameter is input/output: input is requested size, output is actual count returned. For specification, the postcondition is: `result = take(N, dropUntilAfter(cursor, fullSearchResult))` where `fullSearchResult` is identical to what FINDLINKSFROMTOTHREE would return. Disabled in safe mode (`init.c:76`).

**Code references:**
- `findnextnlinksfromtothreesp()`: `backend/spanf1.c:117-149`
- Cursor check: `iszerotumbler()` at line 126
- Cursor walk: linear scan with `tumblereq()` match
- Destructive truncation: `linkset->next = NULL` at the N-th item
- Safe mode disable: `backend/init.c:76`

**Concrete example:**
- Full search returns links [L1, L2, L3, L4, L5], cursor=L2, N=2
- Result: [L3, L4], actual count=2
- If cursor=L_deleted (not in result set): returns [], count=0
- If cursor=zero: returns [L1, L2], count=2

**Provenance:** Finding 0035 (section 5)
**Co-occurring entries:** [SS-VSPAN-VS-VSPANSET], [ST-FIND-LINKS], [ST-RETRIEVE-ENDSETS], [INT-SPORGL-LINK-INDEX], [EC-CURSOR-INVALIDATION], [EC-VSPAN-MISLEADING-SIZE]

---

### ST-INSERT-ACCUMULATE

**Source:** Finding 0036

**What happens:** Multiple INSERT operations on the same document each create their own DOCISPAN entries. Each insertion allocates fresh I-addresses and adds corresponding DOCISPAN mappings. The DOCISPAN entries from earlier inserts are not disturbed by later ones — they accumulate monotonically.

**Why it matters for spec:** This confirms that INSERT's DOCISPAN creation is additive: `DOCISPAN_after = DOCISPAN_before ∪ {new_i_addrs → doc}`. Combined with INV-IADDRESS-PERMANENT (from Finding 0023), the DOCISPAN index for a document only grows.

**Concrete example:**
```
INSERT "First " at V:1.1  → DOCISPAN: {α₁..α₆ → doc}
INSERT "Second " after     → DOCISPAN: {α₁..α₆ → doc, β₁..β₇ → doc}
INSERT "Third" after       → DOCISPAN: {α₁..α₆ → doc, β₁..β₇ → doc, γ₁..γ₅ → doc}

find_documents("First")  → [doc]
find_documents("Second") → [doc]
find_documents("Third")  → [doc]
```

**Code references:**
- Test: `golden/discovery/insert_multiple_times_accumulates_docispan.json`

**Provenance:** Finding 0036.
**Co-occurring entries:** [SS-DOCISPAN], [PRE-INSERT], [ST-INSERT], [FC-CONTENT-SPANF-ISOLATION], [EC-APPEND-NO-DOCISPAN]

---

### ST-COPY

**Sources:** Findings 0047, 0064

#### Finding 0047

**What happens:** COPY creates DOCISPAN entries proportional to the number of contiguous I-spans in the source content, not the number of bytes. COPY of contiguous source content (1 I-span) creates 1 DOCISPAN entry. COPY of fragmented source content (e.g., 3 non-contiguous regions) creates 3 DOCISPAN entries. The `specset2ispanset` conversion determines how many I-spans the source content maps to, and `insertspanf` makes one `insertnd` call per I-span.

**Why it matters for spec:** COPY postcondition for DOCISPAN: `|new_DOCISPAN_entries| = |ispanset(source_content)|`. The number of new index entries depends on the I-space fragmentation of the copied content, not its V-space extent. This means copying heavily-edited content (many small I-spans) is more expensive in spanfilade entries than copying pristine content (one large I-span).

**Concrete example:**
```
COPY of contiguous content (1 I-span in source):
  insertspanf receives 1 I-span → 1 insertnd → 1 DOCISPAN entry

COPY of fragmented content (3 I-spans in source):
  insertspanf receives 3 I-spans → 3 insertnd calls → 3 DOCISPAN entries
```

**Code references:**
- `do1.c:45-65` — `docopy()` calls `specset2ispanset` then `insertspanf`
- `spanf1.c:38-48` — loop in `insertspanf`: `for (; sporglset; sporglset = next) { ... insertnd(...); }`

**Provenance:** Finding 0047

#### Finding 0064

**What happens**: COPY is the identity-preserving operation. Unlike INSERT (which allocates fresh I-addresses), COPY shares the source's existing I-addresses in the target document's POOM via `insertpm`. When used to "undelete" content — by copying from a document that still references the original I-addresses — COPY restores both the V-space content AND the I-space identity.

This establishes a clear operational taxonomy:
- **INSERT**: Creates new content identity (fresh I-addresses from granfilade)
- **COPY**: Preserves existing content identity (shares I-addresses via POOM)
- **DELETE**: Destroys the local V-to-I mapping (I-addresses become unreferenced in this document)

**Why it matters for spec**: COPY is the only mechanism for identity-preserving content restoration after DELETE. Formally:

```
Let source still map i to some V-span v_s
After DELETE(doc, v):              iaddr_doc(v) = ∅
After COPY(doc, v, source, v_s):   iaddr_doc(v) = i    -- identity restored
```

This means "undo delete" in the Xanadu model is not `INSERT(deleted_text)` but `COPY(from_version_with_original_iaddrs)`. The precondition for identity-preserving restoration is that some accessible document still references the original I-addresses.

**Code references**:
- `backend/do1.c:45-65` — `docopy`: calls `insertpm` (shares existing I-addresses) + `insertspanf`
- `febe/scenarios/provenance.py::scenario_delete_then_recopy` — demonstrates COPY restoring identity after DELETE

**Provenance**: Finding 0064

**Co-occurring entries:** [SS-DOCISPAN], [ST-DELETE], [ST-INSERT], [FC-DELETE-CROSS-DOC], [INV-DELETE-NOT-INVERSE], [INV-IADDR-IMMUTABILITY], [INV-SPANF-GROWTH]

---

### ST-FOLLOWLINK

**Source:** Finding 0048

**What happens:** FOLLOWLINK retrieves link endset I-addresses from the link orgl, then converts them to V-addresses using a specified document's POOM. The call chain is: `link2sporglset()` extracts I-addresses from the link orgl at the requested endset position (0.1, 0.2, or 0.3) via `retrieverestricted()` — no POOM check occurs at this stage. Then `linksporglset2specset()` converts I-addresses to V-addresses by looking them up in the specified `homedoc`'s POOM. The conversion calls `span2spanset()` which uses `retrieverestricted()` against the document's orgl. If an I-address has no POOM mapping, `retrieverestricted` returns NULL and the I-address is silently dropped — no V-span is added to the result.

**Why it matters for spec:** FOLLOWLINK's postcondition is not simply "return the endset" — it is filtered through a specific document's POOM. The result depends on which document's POOM is queried (the `homedoc` parameter). The same link endset can produce different V-address results (or empty results) depending on which document context is used. Formally: `followlink(link, whichend, homedoc) = { v | ∃ i ∈ endset(link, whichend) : poom.homedoc(v) = i }`. If no such v exists for any i, the result is empty.

**Code references:**
- `link2sporglset()`: `backend/sporgl.c:67-95` — extracts I-addresses from link orgl, no POOM check
- `linksporglset2specset()`: `backend/sporgl.c:97+` — converts I-addresses to V-specs via homedoc POOM
- `span2spanset()`: `backend/orglinks.c:425-449` — if `retrieverestricted` returns NULL, I-address silently dropped (lines 446-448)
- `dofollowlink()`: `backend/do1.c:227-236` — orchestrates the two-phase process

**Concrete example:**
- Link L has to-endset containing I-address `a`
- Document D1 has `poom.D1(1.5) = a` → FOLLOWLINK(L, TO, D1) returns `[1.5]`
- Document D2 has no POOM mapping for `a` → FOLLOWLINK(L, TO, D2) returns `[]`
- Content deleted from all documents → FOLLOWLINK(L, TO, any) returns `[]`, operation succeeds

**Provenance:** Finding 0048
**Co-occurring entries:** [PRE-FOLLOWLINK], [INV-ITOV-FILTERING], [EC-GHOST-LINK]

---

### ST-REBALANCE-2D

**Sources:** Findings 0071, 0073

#### Finding 0071

**What happens:** The `recombinend` rebalancing operation modifies 2D enfilade tree structure through two mechanisms:

1. **Full merge** (`eatbrossubtreend` at `recombine.c:205-233`): One node absorbs all children from another node, which is then deleted. This happens when the combined son count fits within the branching limit.
2. **Nephew stealing** (`takenephewnd` at `recombine.c:165-203`): Individual children are moved from an overpopulated sibling to an underpopulated one without deleting either node.

The merge guard `ishouldbother` at `recombine.c:150-163` checks:
- Combined son count: `dest->numberofsons + src->numberofsons <= (height > 1 ? MAXUCINLOAF : MAX2DBCINLOAF)`
- Reserved crums are skipped (age == RESERVED) to avoid interfering with in-progress operations
- `randomness(.3)` always returns TRUE (probabilistic path commented out), so all eligible pairs are merged

**Postconditions:**
- After `recombinend`, no pair of children in the node can be merged without exceeding `max_children`
- If the root ends up with exactly one child, `levelpull` removes the root level, decreasing tree height by 1
- Reserved crums are never disturbed

**Why it matters for spec:** The state transition for 2D rebalancing has a frame condition: reserved crums are untouched. The postcondition is a saturation property — no further merges are possible among children. This differs from 1D rebalancing which only attempts one merge per call. The formal model should express: `post(recombinend(node)) ⟹ ∀ i,j ∈ children(node): i ≠ j ⟹ ¬ishouldbother(i,j)`.

**Code references:**
- `backend/recombine.c:150-163` — `ishouldbother` merge guard
- `backend/recombine.c:165-203` — `takeovernephewsnd` (dispatch between merge and steal)
- `backend/recombine.c:205-233` — `eatbrossubtreend` (full subtree merge)
- `backend/recombine.c:104-131` — `recombinend` outer loop

**Provenance:** Finding 0071

#### Finding 0073

**What happens:** In the 2D pairwise merge loop (`recombinend` at `recombine.c:120-128`), a single receiver node can absorb multiple donors in one pass. The inner `j` loop does **not** break after a successful merge — two `break` statements are commented out with the annotation "6/16/84", indicating an intentional design choice. After `takeovernephewsnd(&sons[i], &sons[j])` completes, the loop continues to `j+1, j+2, ...`, allowing `sons[i]` to absorb further donors.

Donor depletion uses NULL-marking in the sons array:
- **Full absorption** (`eatbrossubtreend`): All children transferred, donor freed, `*broptr = NULL` (recombine.c:180-182)
- **Partial absorption with depletion** (`takeovernephewsnd` stealing path): All nephews stolen one-by-one, donor becomes empty, freed, `*broptr = NULL` (recombine.c:194-200)
- **Partial absorption without depletion**: Donor retains some children, remains non-NULL, available for subsequent merge attempts by other receivers

The NULL guards in the loop (`sons[i] &&` and `sons[j] &&`) prevent dereferencing depleted donors. If a receiver itself becomes NULL (via being absorbed if the algorithm were symmetric — but it is not: `sons[i]` is always the receiver), the outer loop skips it.

This contrasts with 1D rebalancing (`recombineseq` at `recombine.c:38-68`), which uses **active** `break` statements after both `eatbrossubtreeseq` and `takeovernephewsseq`. The 1D algorithm absorbs at most one donor per pass; multiple passes are needed for full consolidation.

**Why it matters for spec:** The multi-donor absorption makes the 2D rebalance postcondition achievable in a single call: `post(recombinend(node)) ⟹ ∀ i,j ∈ children(node): i ≠ j ⟹ ¬ishouldbother(i,j)`. The 1D algorithm only guarantees progress (at least one merge per call if one is possible), not saturation. The formal model must distinguish these:
- `recombinend`: greedy saturation — single pass exhausts all merge opportunities
- `recombineseq`: incremental — one merge per invocation, requires repeated calls

The NULL-marking mechanism is the algorithm's bookkeeping for tracking which donors have been consumed. The formal model can abstract this as a set that shrinks: `active_children' ⊆ active_children` after each merge step.

**Code references:**
- `backend/recombine.c:120-128` — Phase 2 pairwise loop with commented-out `break` statements
- `backend/recombine.c:165-203` — `takeovernephewsnd`: sets `*broptr = NULL` on donor depletion
- `backend/recombine.c:180-182` — Full absorption path (`eatbrossubtreend` + NULL)
- `backend/recombine.c:194-200` — Partial absorption depletion path (all nephews stolen + NULL)
- `backend/recombine.c:38-68` — `recombineseq` (1D) with active `break` for contrast

**Concrete example:**
```
Initial diagonally-sorted sons: [c0, c1, c2, c3, c4]

Pass with i=0 (c0 is receiver):
  j=1: c0 absorbs c1 fully     → [c0, NULL, c2, c3, c4]
  j=2: c0 steals from c2       → [c0, NULL, c2', c3, c4]  (c2 retains some children)
  j=3: c0 steals from c3, depletes it → [c0, NULL, c2', NULL, c4]
  j=4: c0 full, ishouldbother=FALSE, skip

Pass with i=1: sons[1]=NULL, skip

Pass with i=2 (c2' is receiver):
  j=3: sons[3]=NULL, skip
  j=4: c2' absorbs c4           → [c0, NULL, c2', NULL, NULL]

Result: 2 nodes (c0, c2'), each having absorbed multiple donors.
Saturation: ishouldbother(c0, c2') = FALSE (combined sons exceed limit).
```

**Provenance:** Finding 0073 (extends Finding 0071 ST-REBALANCE-2D with multi-donor absorption detail)

**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-SPLIT-2D], [FC-RESERVED-CRUM], [INV-ENFILADE-OCCUPANCY], [EC-RECOMBINE-RECEIVER-SATURATION]

---

### ST-SPLIT-2D

**Source:** Finding 0071

**What happens:** The 2D split strategy is dimension-aware and asymmetric between SPAN and POOM enfilades:

- **SPAN split** (`splitcrumsp` at `split.c:95-106`): Peels off the child with the largest diagonal position, using `comparecrumsdiagonally(ptr, correctone) == GREATER`. This matches the diagonal ordering used in `recombinend`, making split and merge complementary operations in the same ordering space.
- **POOM split** (`splitcrumpm` at `split.c:117-128`): Peels off the child with the largest SPANRANGE displacement only (`cdsp.dsas[SPANRANGE]`), ignoring the ORGLRANGE dimension entirely. Commented-out code shows diagonal splitting was tried for POOM but reverted.

The asymmetry is notable: SPAN uses the same L1-norm diagonal for both split and rebalance, while POOM uses diagonal for rebalance but single-dimension for split.

**Why it matters for spec:** The split operation is the inverse of merge for maintaining tree balance, but the two 2D enfilade types use different split criteria. A formal model needs separate split predicates:
- `split_span(node) → peel child c where diag(c) = max(diag(children(node)))`
- `split_poom(node) → peel child c where c.dsas[SPANRANGE] = max over children`

The asymmetry means the POOM tree shape may differ from SPAN even with identical data distributions, because split and rebalance use different orderings.

**Code references:**
- `backend/split.c:95-106` — `splitcrumsp` (SPAN split by diagonal)
- `backend/split.c:117-128` — `splitcrumpm` (POOM split by SPANRANGE only)
- `backend/recombine.c:313-320` — `comparecrumsdiagonally` (shared with rebalance)

**Concrete example:**
```
SPAN enfilade node with children at diagonals [3, 5, 6, 8, 9]:
  splitcrumsp peels child with diagonal 9

POOM enfilade node with children:
  A: dsas[SPANRANGE]=7, dsas[ORGLRANGE]=2  (diagonal=9)
  B: dsas[SPANRANGE]=8, dsas[ORGLRANGE]=1  (diagonal=9)
  splitcrumpm peels B (largest SPANRANGE=8), NOT based on diagonal
```

**Provenance:** Finding 0071
**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-REBALANCE-2D], [FC-RESERVED-CRUM], [INV-ENFILADE-OCCUPANCY]

---

### ST-INSERT-VWIDTH-ENCODING

**Source:** Finding 0076

**What happens:** During INSERT, `insertpm` computes the V-width of a POOM bottom crum by extracting the integer value from the I-width and re-encoding it as a tumbler at V-space precision. The three-step process is:

1. `shift = tumblerlength(vsaptr) - 1` — compute exponent from V-address length
2. `inc = tumblerintdiff(&lwidth, &zero)` — extract integer value from I-width
3. `tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V])` — create V-width tumbler with `exp = -shift`, `mantissa[0] = inc`

This produces a tumbler representing `inc * 10^(-shift)`. The I-width is copied directly without transformation: `movetumbler(&lwidth, &crumwidth.dsas[I])`.

**Why it matters for spec:** The INSERT postcondition on POOM crums must specify that V-width and I-width are not equal as tumblers, even though they encode the same numeric width. Formally: `value(crum.width.dsas[V]) == value(crum.width.dsas[I])` but `crum.width.dsas[V] != crum.width.dsas[I]` as tumbler representations. The V-width exponent is determined by the V-address length, not the I-address length. This is a derived encoding, not a copy.

**Code references:**
- `orglinks.c:105-117` — V-width computation in `insertpm`
- `tumble.c:599-623` — `tumblerincrement` zero-tumbler special case: sets `exp = -rightshift`, `mantissa[0] = bint`

**Concrete example:**
```
Input: vsaptr = "1.1" (tumblerlength = 2), lwidth represents 11 characters

Step 1: shift = tumblerlength("1.1") - 1 = 2 - 1 = 1
Step 2: inc = tumblerintdiff(lwidth, zero) = 11
Step 3: tumblerincrement(zero, 1, 11, &V-width)
        → V-width tumbler: exp = -1, mantissa[0] = 11
        → Tumbler notation: 0.11

Meanwhile: I-width = 0.0.0.0.0.0.0.0.11 (copied directly)
```

**Provenance:** Finding 0076
**Co-occurring entries:** [SS-POOM-BOTTOM-CRUM], [INV-WIDTH-VALUE-EQUIVALENCE], [EC-VWIDTH-ZERO-ADDRESS]

---

### ST-VERSION

**Source:** Finding 0077

**What happens:** CREATENEWVERSION(d) performs exactly two effects: (1) allocates a new document address d' via `createorglingranf` with a DOCUMENT hint (which calls `findisatoinsertnonmolecule`), and (2) copies SPAN entries from d's spanfilade to d' via `docopyinternal` → `insertspanf`. It does NOT allocate any new content I-addresses — no call to `findisatoinsertgr` for content. The copied SPANs reuse the source document's existing I-addresses; `insertspanf` takes I-spans as input parameters and records them without allocation.

Call chain: `docreatenewversion` → `createorglingranf` (doc address) → `doretrievedocvspanfoo` (get d's V-span) → `docopyinternal` → `specset2ispanset` (convert V-spans to I-spans from source) → `insertpm` (update POOM) → `insertspanf` (record SPAN entries).

**Why it matters for spec:** Postcondition for VERSION: `granf_content_after = granf_content_before` (no new content entries). Only `granf_doc_after = granf_doc_before ∪ {d'}` (one new document entry). The new document d' shares I-addresses with the source d — this is how version content identity is established. Formally: `ispans(d') = ispans(d)` immediately after VERSION.

**Code references:** `docreatenewversion` in `backend/do1.c:260-299` — entry point. `docopyinternal` in `backend/do1.c:66-82` — calls `insertspanf`, not `findisatoinsertgr`. `insertspanf` in `backend/spanf1.c:15-54` — records SPAN entries with provided I-addresses (no allocation).

**Concrete example:**
```
Before: doc1 has "ABC" at I-addresses I.1, I.2, I.3
VERSION(doc1) → doc2
After:  doc2 has "ABC" mapped to SAME I-addresses I.1, I.2, I.3
        No new content I-addresses allocated
        INSERT "XYZ" into doc1 → allocates I.4, I.5, I.6 (contiguous with ABC)
        compare_versions(doc1, doc2) → 1 shared span pair (all 6 chars contiguous)
```

**Provenance:** Finding 0077
**Co-occurring entries:** [SS-ADDRESS-SPACE], [FC-GRANF-ON-VERSION], [INV-MONOTONIC]

---

## Frame Conditions

> What an operation leaves unchanged

### FC-DOC-ISOLATION

**Sources:** Findings 0002, 0007, 0028, 0033, 0065, 0067

#### Finding 0002

**What happens:** Modifications to a source document (both insertions and deletions) do not affect documents that have transcluded content from it. After vcopy, the target holds its own references to the content identities. Subsequent changes to the source document's reference set have no effect on the target's reference set. Each document's view is independent.

**Why it matters for spec:** This is a frame condition on insert and remove: `forall doc_other != doc_modified :: references(doc_other) is unchanged`. The formal spec must assert that insert and remove operations on one document do not alter any other document's reference set. This is a direct consequence of content immutability — since operations create/remove references rather than mutating content, and each document has its own reference set, cross-document interference is impossible.

**Concrete example:**
- Source: "Original content here", Target transcluded "Original content"
- Insert "NEW: " at start of source → Source: "NEW: Original content here"
- Target: still "Target: Original content" (unchanged)
- Delete "Delete this." from source → Source loses that reference
- Target that transcluded "Delete this." still has it (its reference is independent)

**Code references:** `scenario_vcopy_source_modified` at `febe/scenarios/content/vcopy.py:312-317`, `scenario_vcopy_source_deleted` at `febe/scenarios/content/vcopy.py:388-395`

**Provenance:** Finding 0002

#### Finding 0007

**What happens:** Once a version is created, modifications to either the original or the version do not affect the other. This holds for all mutation operations: insertion into the version leaves the original unchanged, deletion from the version leaves the original unchanged, insertion into the original leaves the version unchanged, deletion from the original leaves the version unchanged. Both documents can be modified independently and concurrently. This extends the FC-DOC-ISOLATION frame condition from Finding 0002 to cover versioning specifically.

**Why it matters for spec:** The frame condition is: `forall op on doc_A where doc_B = version_of(doc_A) or doc_A = version_of(doc_B) :: references(doc_B) is unchanged`. This is not a new axiom — it follows from FC-DOC-ISOLATION and the fact that version-create produces a document with its own independent reference set. But the finding confirms it holds for the full matrix of scenarios (insert/delete on original/version, both modified).

**Concrete example:**
- Original: "Shared base content", Version: "Shared base content" (same identities)
- Delete from version: Original still reads "Shared base content"
- Delete from original: Version still reads "Shared base content"
- Modify both independently: each has its own state, neither affected by the other

**Code references:** Tests `version_delete_preserves_original`, `delete_from_original_check_version`, `modify_original_after_version`, `both_versions_modified`

**Provenance:** Finding 0007

#### Finding 0028

**What happens**: Documents created independently (not via version or vcopy) share no content identity, even if they contain identical text. `compare_versions` between two independently-created documents with different text returns an empty list. The I-positions assigned to typed content are unique per insertion event.

**Why it matters for spec**: Reinforces the identity-by-origin invariant: `forall doc1, doc2 : Document :: independent(doc1, doc2) => compare_versions(doc1, doc2) == []`. "Independent" means no version or transclusion relationship exists between them. Even character-for-character identical text produces distinct I-positions when typed independently. This is a frame condition on document creation: `create_document` produces a document with I-positions disjoint from all existing I-positions.

**Code references**: Test `edgecases/disjoint_documents_comparison`

**Concrete example**:
```
doc1 = create_document(); insert(doc1, "First content")
doc2 = create_document(); insert(doc2, "Second content")
compare_versions(doc1, doc2) → []  — no shared identity despite both being text
```

**Provenance**: Finding 0028 §8

#### Finding 0033

**What happens:** When a partial vcopy is performed from a fragmented-insert document (e.g., copying only positions 3–7 from a 10-character document), the result is still 1 I-span in the target, not 5. The I-space contiguity of the source is preserved through the vcopy into the target's V-to-I mapping.

**Why it matters for spec:** Frame condition: vcopy of a contiguous V-span that maps to contiguous I-addresses produces a contiguous I-span mapping in the target. The vcopy operation preserves the consolidation structure of the source's I-space mapping. This means subranges of consolidated spans remain consolidated.

**Concrete example:**
- Source doc has 10 characters at V-positions 1–10, all mapping to contiguous I-addresses
- Vcopy positions 3–7 to new document
- Result: 1 shared span pair with `source: {start: "1.3", width: "0.5"}`, `dest: {start: "1.1", width: "0.5"}`

**Provenance:** Finding 0033

#### Finding 0065

**Detail level: Essential**

MAKELINK on document B does not affect the link I-address allocation state of document A. The allocation counter is implicit (derived from bounded query), and the query bound is constructed from the target document's own I-address. Therefore, link creation in one document is a no-op with respect to all other documents' link allocation state.

**What happens:** The `upperbound` in `findisatoinsertmolecule` is derived from `hintptr->hintisa` (the document's I-address), not from any global state. The `findpreviousisagr` search is bounded to `[lowerbound, docISA.2.3)`, so it only sees entries in the target document's link subspace.

**Why it matters for spec:** Frame condition for MAKELINK: `forall d': Document | d' != d => link_state(d') unchanged after MAKELINK(d)`. This enables independent reasoning about per-document operations and confirms there is no global link allocation bottleneck or shared mutable state.

**Code references:**
- `backend/granf2.c:162` — upperbound constructed from document-specific `hintisa`
- `backend/granf2.c:164` — `findpreviousisagr` confined to document's address subspace
- `backend/do1.c:211` — `makehint` binds allocation to specific document

**Provenance:** Finding 0065

#### Finding 0067

**What happens:** Document operations (INSERT, DELETE, COPY) have no cross-document side effects. Each document's orgl is an independent enfilade tree stored in granf. All mutation functions (`insertnd`, `deletend`, `rearrangend`) receive `typecuc *fullcrumptr` — a pointer to the target document's orgl root crum — and all tree traversal uses local pointers (`findleftson`, `findrightbro`, `findfather`). No code path in any mutation function accesses another document's orgl. This was confirmed both by code inspection and by 6 empirical test scenarios covering INSERT, DELETE, and COPY across multiple documents with transclusions.

COPY (`docopy`) reads the source document's I-addresses via `specset2ispanset` (a read-only operation) and writes only to the target document's orgl via `insertpm`. The source document's orgl is never modified.

**Why it matters for spec:** This is the central frame axiom F0: `∀d ∈ D, ∀op ∈ {INSERT, DELETE, COPY}, ∀d' ∈ D where d ≠ d': op(d, ...) ⟹ D_seq'(d') = D_seq(d')`. The implementation guarantees this structurally — cross-document mutation is physically impossible because mutation functions only receive and traverse a single orgl tree. For Dafny verification, this can be expressed as: `forall d' :: d' != d ==> poom(d') == old(poom(d'))` as a postcondition on all document operations. No global mutable state is shared between documents (crum allocation is append-only and semantics-free).

**Code references:**
- `insertnd.c:15-111` — `insertnd` takes single `fullcrumptr`, all mutations local to that tree
- `edit.c:30-75` — `deletend` takes single `fullcrumptr`, traversal via `findleftson`/`findrightbro`
- `do1.c:45-65` — `docopy` reads source (via `specset2ispanset`), writes target only (via `insertpm` + `insertspanf`)
- `orglinks.c:144-151` — `deletevspanpm` calls `deletend` on single orgl, no spanf call

**Concrete example:**
```
Pre-state:
  Doc A: text "Hello" at 1.1-1.5
  Doc B: text "World" at 1.1-1.5

Operation: INSERT "XYZ" into Doc A at 1.3

Post-state:
  Doc A: text "HeXYZllo" at 1.1-1.8 (modified)
  Doc B: text "World" at 1.1-1.5 (UNCHANGED — identical content and vspanset)

Operation: COPY from Doc A to Doc C
Post-state:
  Doc A: UNCHANGED (read-only access to source)
  Doc C: contains transcluded content from A
```

**Provenance:** Finding 0067

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-CONTENT-IDENTITY], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [SS-VERSION-ADDRESS], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-ADDRESS-ALLOC], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-INSERT], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-SUBSPACE], [INV-CONTENT-IMMUTABILITY], [INV-IDENTITY-OVERLAP], [INV-MONOTONIC], [INV-SINGLE-CHAR-GRANULARITY], [INV-SPANF-WRITE-ONLY], [INV-TRANSITIVE-IDENTITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [INT-VERSION-TRANSCLUSION], [EC-EMPTY-DOC], [EC-GHOST-LINK-ENDPOINT], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### FC-SPECSET-COMPARE

**Source:** Finding 0003

**What happens:** When comparing documents using SpecSets, only the specified spans are considered for identity matching. Content outside the SpecSet boundaries is excluded from comparison results. This means compare is not a whole-document operation — it respects the SpecSet as a filter on which content participates.

**Why it matters for spec:** This defines a frame condition on compare: `compare(specset_A, specset_B)` reports only identity overlaps between content referenced by specset_A and content referenced by specset_B. Content in either document but outside the specified spans does not appear in results. Formally: `shared_regions(compare(ss_A, ss_B)) ⊆ {c | c in content_ids(ss_A) ∩ content_ids(ss_B)}`. This is a significant constraint — compare is a filtered operation, not a global one.

**Concrete example:**
- DocA: "Shared prefix. A middle. Shared suffix."
- DocB: "Shared prefix. B middle. Shared suffix."
- Compare full documents: reports "Shared prefix. " and " Shared suffix." as shared
- Compare only middles ("A middle" vs "B middle"): no shared content reported

**Code references:** Test `compare_multispan_specsets`

**Provenance:** Finding 0003
**Co-occurring entries:** [SS-SPECSET], [ST-VCOPY], [INV-SPECSET-ORDER]

---

### FC-LINK-PERSISTENCE

**Sources:** Findings 0004, 0008, 0024

#### Finding 0004

**What happens:** Document modifications (insert, delete, vcopy) never destroy links. Links are not stored within documents — they exist in a separate link subsystem (the link enfilade / orgl) indexed by content identity. Therefore, no document-level operation can remove or corrupt a link. The only change a document operation can make to a link's effective behavior is to alter which documents reference the link's endpoint content identities.

**Why it matters for spec:** This is a frame condition on all document operations: `forall op in {insert, remove, vcopy}, link : Link :: links(system_after_op) ⊇ links(system_before_op)`. The set of links is monotonically growing — links are created but never destroyed by document operations. Combined with INV-CONTENT-IMMUTABILITY, this means the link set is a permanent, append-only structure. The formal spec should assert that document operations have no write access to the link store except through explicit link creation.

**Code references:** All seven `link_survives_*` and `link_when_*` tests (all PASS)

**Provenance:** Finding 0004

#### Finding 0008

**What happens:** Links on transcluded content survive versioning of the containing document. When a document transcludes linked content and is then versioned, the version can discover the link. The link persists across the full chain: source document → transcluding document → version of transcluding document. This extends the FC-LINK-PERSISTENCE entry from Finding 0004 to combined transclusion+versioning scenarios.

**Why it matters for spec:** The frame condition `forall op in {version_create}, link : Link :: links(system_after) ⊇ links(system_before)` is confirmed to hold when the version's content includes transcluded linked material. Since version-create copies the reference set (which includes transcluded content identity references), and links are indexed by content identity, the version inherits link discoverability for all content — both native and transcluded.

**Concrete example:**
- Source: "Source with linked text here" — link on "linked"
- Doc: "Doc prefix: " + transclude("linked text" from Source)
- Version: version of Doc
- `find_links(Source)` → [link_id]
- `find_links(Doc)` → [link_id]
- `find_links(Version)` → [link_id] (survives versioning of transcluding document)

**Code references:** Test `version_transcluded_linked_content`

**Provenance:** Finding 0008

#### Finding 0024

**What happens:** The home document of a link (where the link is stored) is independent from the documents whose content the link's endpoints reference. Deleting all text from the home document has zero effect on link functionality — the link's source, target, and type endsets remain fully operational.

This separation enables third-party linking: a link can be stored in document A while connecting content in documents B and C. The home document is the link's container, not its subject.

**Why it matters for spec:** Frame condition for delete operations: `∀ link, D_home :: delete_text(D_home) ⟹ link.source_unchanged ∧ link.target_unchanged ∧ link.type_unchanged` when the deletion targets D_home's text subspace (1.x) rather than its link subspace (0.2.x). This is a consequence of subspace isolation — operations on text spans cannot affect link spans.

**Concrete example:**
```
Before: Link in doc_A, source in doc_B, target in doc_C
  follow_link(link, SOURCE) → content in doc_B
  follow_link(link, TARGET) → content in doc_C

After deleting ALL text from doc_A:
  follow_link(link, SOURCE) → same content in doc_B  (unchanged)
  follow_link(link, TARGET) → same content in doc_C  (unchanged)
  find_links(doc_B content) → still finds the link   (unchanged)
```

**Code references:** Test `link_home_document_content_deleted` (PASS).

**Provenance:** Finding 0024, Semantic Insight 3.

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [ST-DELETE], [ST-REMOVE], [INV-LINK-CONTENT-TRACKING], [INV-LINK-GLOBAL-VISIBILITY], [INV-LINK-PERMANENCE], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [EC-ORPHANED-LINK]

---

### FC-SUBSPACE

**Sources:** Findings 0009, 0038, 0043, 0054, 0055, 0067

#### Finding 0009

**What happens**: The link subspace (`0.x`) and text subspace (`1.x`) are independent partitions of the document's V-space. Operations on one subspace should not affect the other. Evidence: after link creation, text content at `1.x` is preserved while a new entry appears at `0.x`. The `findnextlinkvsa()` function only considers positions in the `0.x` range, and text insertion only considers positions in the `1.x` range.

**Why it matters for spec**: This is a frame condition — link creation does not modify text content, and text insertion does not modify link references. The spec should state that operations on one subspace preserve the other subspace unchanged.

**Code references**:
- `do2.c:151-167` — `findnextlinkvsa()` scoped to `0.x`
- `do1.c:199-225` — `docreatelink()` writes only to `0.x`

**Concrete example**:
```
Before: V-range 1.1..1.16 → permascroll addresses (text)
After docreatelink:
  V-range 0.1 → link ISA (new)
  V-range 1.x → permascroll addresses (unchanged)
```

**Provenance**: Finding 0009

#### Finding 0038

**What happens**: Text insertions at V-positions `1.x` do not affect link positions at `2.x` (internally) or `0.x` (in output). This independence was verified through concrete scenarios: inserting 5 characters at V-position 1.5 in a document with a link changed the text vspan width but left the link span unchanged. Multiple rounds of text insertion and link creation were tested — link spans remained stable throughout. The `insertpm()` function operates only on crums in the target V-range, so inserting at `1.x` structurally cannot reach `2.x` crums in the enfilade tree.

**Why it matters for spec**: This strengthens the frame condition from finding 0009 with concrete verified examples. The frame condition is not just a design intent but a structural property of the tree: text crums and link crums occupy disjoint branches. For Dafny verification, this can be stated as: for all operations `op` on subspace `s`, the projection of the document state onto subspace `s' != s` is unchanged.

**Code references**:
- `insertpm()` — operates only on crums matching the target V-range
- `orglinks.c:173-221` — `retrievevspansetpm()` extracts subspaces independently

**Concrete example**:
```
Pre-state:
  Text at 1.1..1.10 ("HelloWorld"), link at 0.x
  Vspanset: [{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]

doinsert("XXXXX", at V-position 1.5)

Post-state:
  Text at 1.1..1.15 ("HellXXXXXoWorld")
  Vspanset: [{"start": "0", "width": "0.10"}, {"start": "1", "width": "1"}]
  Link span UNCHANGED — still "0" with width "0.10"
```

**Provenance**: Finding 0038

#### Finding 0043

**What happens**: CREATENEWVERSION preserves the source document's link subspace unchanged while copying the text subspace to the version. The source document's vspanset (including its `0.x` link entries) is unmodified after version creation. The version receives a new, empty link subspace — it has no POOM-level link entries. This is an asymmetric frame condition: the source's link subspace is preserved (standard frame condition), and the version's link subspace is initialized to empty (postcondition on the new document).

**Why it matters for spec**: This extends FC-SUBSPACE beyond single-document operations to cover version creation. The frame condition is: `link_subspace(source)` is unchanged by `CREATENEWVERSION(source)`. The postcondition adds: `link_subspace(version) = {}`. For Dafny, this can be verified as part of the version-create postcondition — the version's POOM projection onto subspace `0.x`/`2.x` is empty.

**Code references**:
- `do1.c:264-303` — `docreatenewversion()` only copies the vspan from `retrievedocumentpartofvspanpm`, which excludes links
- `orglinks.c:155-162` — `retrievedocumentpartofvspanpm()` returns displacement starting at text position 1, not 0

**Provenance**: Finding 0043

#### Finding 0054

**What happens:** INSERT at V-position `1.x` does not shift link entries at `2.x`. The mechanism is the two-blade knife in `insertcutsectionnd()` (edit.c:207-233). When the knife has 2 blades, the function first checks each POOM crum against `blade[1]` (the subspace boundary). For a link crum at `2.1` with `blade[1] = 2.1`, `whereoncrum` returns `ONMYLEFTBORDER` (-1). Since `cmp <= ONMYLEFTBORDER`, the crum is classified as **case 2** (no shift) and the `blade[0]` check is never reached.

The classification logic for blades `[1.3, 2.1]`:
- Crums at `< 1.3`: case 0 (before insertion, no shift)
- Crums in `[1.3, 2.1)`: case 1 (shifted right by insertion width)
- Crums at `>= 2.1`: case 2 (beyond second blade, no shift)

This confirms and explains the behavioral observation in Finding 0038 with the precise code-level mechanism.

**Why it matters for spec:** The frame condition `∀ op ∈ {INSERT, DELETE} on subspace s, ∀ entry ∈ poom(doc) : entry.vpos.mantissa[0] ≠ s ⟹ entry.vpos' = entry.vpos` is enforced structurally by the two-blade knife, not by per-entry type checking. The knife partitions by V-position range, and subspace boundaries happen to align with knife blade positions. For Dafny, this can be stated: `forall e :: e in poom(doc) && e.vpos >= blade[1] ==> e.vpos == old(e.vpos)`.

**Code references:**
- `edit.c:207-233` — `insertcutsectionnd()` classification logic
- `retrie.c:345-391` — `whereoncrum()` spatial relationship check
- `common.h:86-90` — `TOMYLEFT`, `ONMYLEFTBORDER`, `THRUME`, `ONMYRIGHTBORDER`, `TOMYRIGHT`

**Concrete example:**
```
Pre-state:
  Text "ABCDE" at V-positions 1.1-1.5
  Link at V-position 2.1 (ISA: 1.1.0.1.0.1.0.2.1)

Operation: INSERT "XY" at V-position 1.3
  Knife blades: [1.3, 2.1]

Post-state:
  Text "ABXYCDE" at V-positions 1.1-1.7 (text shifted within 1.x)
  Link STILL at V-position 2.1 (unchanged — case 2, no shift)
  V-position 2.3 is empty (nothing shifted into link subspace)
  FINDLINKS still discovers link; FOLLOWLINK still resolves
```

**Provenance:** Finding 0054

#### Finding 0055

**What happens:** DELETE at V-position `1.x` does NOT shift link entries at V-position `2.x`. Although `deletecutsectionnd` classifies the link crum as case 2 (shift) — because both knife blades `[1.1, 1.4]` are to the left of crum `2.1` — the actual `tumblersub(2.1, 0.3)` call is a no-op. The reason: the deletion width `0.3` has exponent `-1`, while the link displacement `2.1` has exponent `0`. The `strongsub` exponent guard returns `2.1` unchanged.

This is a different mechanism from INSERT's subspace isolation. INSERT uses an explicit two-blade knife with a second blade at the subspace boundary (Finding 0054). DELETE has no such explicit guard — its knife blades are simply `[origin, origin + width]`, with no subspace-boundary computation. Subspace isolation for DELETE is an accidental consequence of the `strongsub` exponent check.

Both INSERT and DELETE preserve the frame condition, but through fundamentally different mechanisms:
- INSERT: deliberate structural guard (two-blade knife with subspace boundary)
- DELETE: incidental arithmetic guard (exponent mismatch in `strongsub`)

**Why it matters for spec:** The frame condition `∀ op ∈ {DELETE} on subspace s, ∀ entry ∈ poom(doc) : entry.vpos.mantissa[0] ≠ s ==> entry.vpos' = entry.vpos` holds, but its enforcement mechanism differs from INSERT. For DELETE, the frame condition depends on the invariant that deletion widths always have a lower tumbler exponent than cross-subspace entry displacements. If `strongsub` were modified to handle cross-exponent subtraction, DELETE would break subspace isolation. A formal spec should document this as a fragile invariant.

**Code references:**
- `edit.c:40-43` — `deletend` knife construction: `blade[0] = origin`, `blade[1] = origin + width` (no subspace boundary)
- `edit.c:235-248` — `deletecutsectionnd` classifies link crum at `2.1` as case 2 (shift)
- `edit.c:63` — Case 2 calls `tumblersub(&ptr->cdsp.dsas[V], width, ...)`
- `tumble.c:534-547` — `strongsub` exponent guard prevents actual modification

**Concrete example:**
```
Pre-state:
  Text "ABCDEFGHIJ" at V-positions 1.1-1.10
  Link at V-position 2.1

Operation: DELETE 3 bytes at 1.1 (width = 0.3)
  Knife blades: [1.1, 1.4]
  Link crum at 2.1: classified as case 2 (shift)
  tumblersub(2.1, 0.3) called
  strongsub(2.1, 0.3): exp check → 0.3.exp(-1) < 2.1.exp(0) → no-op
  Link remains at 2.1

Post-state:
  Text shifted: 1.1=D, 1.2=E, ..., 1.7=J
  Link STILL at V-position 2.1 (unchanged)
  FOLLOWLINK still works

Operation: DELETE all remaining 7 bytes at 1.1
Post-state:
  Only link remains: vspanset shows "at 2.1 for 0.1"
  Link STILL at V-position 2.1
  FOLLOWLINK still works
```

**Provenance:** Finding 0055

#### Finding 0067

**What happens:** Finding 0067 synthesizes the subspace isolation evidence from Findings 0054 and 0055, confirming that operations within the text subspace (1.x) do not affect the link subspace (2.x) within the same document. Two distinct mechanisms enforce this:

1. **INSERT** uses a deliberate two-blade knife with `blade[1]` at the next subspace boundary (`findaddressofsecondcutforinsert` computes `(N+1).1`). Crums at or beyond this boundary are classified as case 2 (no shift).

2. **DELETE** relies on an incidental arithmetic guard: `strongsub`'s exponent check returns the minuend unchanged when `width.exp < entry.vpos.exp`, which holds for cross-subspace entries.

Empirical tests confirm: after INSERT at 1.x, links at 2.1 remain discoverable via FIND_LINKS and FOLLOW_LINK. After DELETE at 1.x (including deletion of all text), links at 2.1 remain at their original V-position.

**Why it matters for spec:** Strengthens the frame condition to cover intra-document subspace isolation: `∀ op on subspace s, ∀ entry ∈ poom(doc) : entry.vpos.mantissa[0] ≠ s ⟹ entry.vpos' = entry.vpos`. This is enforced by two different mechanisms (structural for INSERT, arithmetic for DELETE), requiring different proof strategies in formal verification.

**Code references:**
- `insertnd.c:144-146` — two-blade knife construction for INSERT
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert` computes subspace boundary
- `tumble.c:534-547` — `strongsub` exponent guard protects DELETE
- `edit.c:207-233` — `insertcutsectionnd` three-case classification

**Provenance:** Finding 0067 (synthesizing Findings 0054, 0055)

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DUAL-ENFILADE], [SS-TUMBLER], [SS-TWO-BLADE-KNIFE], [PRE-COMPARE-VERSIONS], [PRE-DELETE], [ST-DELETE], [ST-INSERT], [ST-VERSION-CREATE], [FC-DOC-ISOLATION], [INV-SPANF-WRITE-ONLY], [INV-SUBSPACE-CONVENTION], [INT-DELETE-SUBSPACE-ASYMMETRY], [INT-LINK-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-DEEPLY-ORPHANED-LINK], [EC-GHOST-LINK-ENDPOINT], [EC-VSPAN-NORMALIZATION]

---

### FC-CONTENT-SPANF-ISOLATION

**Sources:** Findings 0012, 0018, 0036

#### Finding 0012

**What happens:** Content operations (text insertion, document creation, text retrieval) access only `granf` and never modify `spanf`. Link search operations access only `spanf` and never modify `granf`. This separation is structural — the operation implementations reference different global variables. The access pattern table from the finding confirms: insert text (granf only), create document (granf only), read content (granf only), find links (spanf only). Only link creation and link following cross the boundary.

**Why it matters for spec:** This is a frame condition that enables modular reasoning. For any content-only operation `op`: `spanf' = spanf` (link findability unchanged). For any link-search operation `op`: `granf' = granf` (content unchanged). The spec can verify content operations and link search operations independently, only needing cross-structure reasoning for `docreatelink` and link-following operations.

**Code references:**
- `granf1.c`, `granf2.c` — content operations, no `spanf` references
- `spanf1.c`, `spanf2.c` — link index operations, no `granf` references
- `do1.c:386-391` — `dofindlinksfromtothree()` uses only `spanf`

**Provenance:** Finding 0012

#### Finding 0018

**What happens:** Deleting content from one document does not affect its I-address presence in other documents or in the spanf index. After deletion from the source, `FINDDOCSCONTAINING` still finds the content via any remaining document that holds the same I-addresses. The spanf index retains the I-address mapping even after deletion from a document's V-stream.

**Why it matters for spec:** Frame condition: `REMOVE(doc_A, span)` does not modify I-address mappings in any other document, and the spanf index continues to track the I-address for documents that still contain it. Deletion is per-document, not per-I-address.

**Concrete example:**
```
Source: "Keep. Transclude this. End."
Target: "Target has: Transclude this"  (vcopied from Source)

After DELETE("Transclude this" from Source):
  Source: "Keep.  End."
  Target: "Target has: Transclude this"  (unchanged)
  find_documents("Transclude this" from Target) → [Source, Target]
```

Note: even Source is still found — the spanf index retains the mapping despite deletion from the V-stream.

**Code references:** Test `find_documents_after_source_deletion` in scenarios.

**Provenance:** Finding 0018, Key Finding 4.

#### Finding 0036

**What happens:** Finding 0036 refines the granf/spanf isolation picture from Finding 0012. While Finding 0012 established that content operations access only granf and link operations access only spanf, this finding shows that INSERT (a content operation) actually DOES write to spanf — specifically the DOCISPAN portion. The corrected access pattern is: INSERT writes to both granf (new content) and spanf (DOCISPAN index). APPEND writes only to granf. This means FC-CONTENT-SPANF-ISOLATION from Finding 0012 is too strong: it should be restated as "content operations do not affect the *link index* portion of spanf" rather than "content operations do not touch spanf at all."

**Why it matters for spec:** The frame condition must be refined: for INSERT, `spanf.link_index' = spanf.link_index` (link findability unchanged), but `spanf.docispan' ≠ spanf.docispan` (document findability changes). This requires the spec to model spanf as having two independent sub-indices. Content operations may modify the DOCISPAN sub-index without affecting the link sub-index.

**Code references:**
- `do1.c:62` — INSERT path calls `insertspanf(..., DOCISPAN)` — writes to spanf
- `do1.c:386-391` — `dofindlinksfromtothree()` uses spanf for links (separate sub-index)

**Provenance:** Finding 0036, cross-referenced with Finding 0012.

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DOCISPAN], [SS-DUAL-ENFILADE], [SS-GRANF-OPERATIONS], [SS-SPANF-OPERATIONS], [PRE-INSERT], [ST-CREATE-LINK], [ST-INSERT], [ST-INSERT-ACCUMULATE], [ST-REARRANGE], [ST-VCOPY], [ST-VERSION-CREATE], [INV-DUAL-ENFILADE-CONSISTENCY], [INV-REARRANGE-IDENTITY], [INV-TRANSITIVE-IDENTITY], [EC-APPEND-NO-DOCISPAN], [EC-COMPARE-VERSIONS-LINK-CRASH]

---

### FC-REARRANGE-EXTERIOR

**Source:** Finding 0016

**What happens:** Content outside the cut-point range is unaffected by rearrange. For pivot with cuts `(c1, c2, c3)`, content before `c1` and after `c3` is unchanged. For swap with cuts `(c1, c2, c3, c4)`, content before `c1` and after `c4` is unchanged, and the middle segment between `c2` and `c3` is also preserved (though its V-addresses may shift if swapped regions differ in size).

**Why it matters for spec:** Frame condition for REARRANGE: `doc_after[..c1] = doc_before[..c1]` and `doc_after[c_last..] = doc_before[c_last..]`. For swap, additionally: the middle content is preserved in sequence. The spec must distinguish between content preservation (the characters/identities are the same) and address preservation (V-addresses may shift for the middle segment if regions differ in size).

**Code references:** `edit.c:rearrangend()` (backend); visible in all rearrange golden tests

**Provenance:** Finding 0016

## Omit

The following sections of Finding 0016 are omitted:

- **Use Cases:** Application-level usage suggestions (word reordering, paragraph shuffling, drag-and-drop) are design motivations, not behavioral properties.
- **Implementation Notes:** The algorithm description (slice identification, offset computation) is an implementation strategy, not a formalizable property.
- **Comparison table with Copy+Delete:** Useful for motivation but the individual properties (identity preservation, link survival) are already captured in dedicated entries above.
**Co-occurring entries:** [ST-REARRANGE], [INV-PIVOT-SELF-INVERSE], [INV-REARRANGE-IDENTITY], [INV-REARRANGE-LINK-SURVIVAL]

---

### FC-SESSION-ACCOUNT-ISOLATION

**Source:** Finding 0022

**What happens:** Changing the current account in one session does not affect any other session's account context. The account is strictly per-session state.

**Why it matters for spec:** Frame condition: for any session S1 that executes `account(X)`, for all other sessions S2 where S2 ≠ S1, S2's current account is unchanged. This confirms accounts are session-local namespace selectors, not authentication credentials with shared side effects.

**Concrete example:**
- Session A: `account(1.1.0.1)`, Session B: `account(1.1.0.1)`
- Session A: `account(1.1.0.2)` — only A's account changes
- Session B: `create_document()` → `1.1.0.1.0.2` (still uses `1.1.0.1`)

**Provenance:** Finding 0022, section 1
**Co-occurring entries:** [SS-SESSION-STATE], [ST-CROSS-SESSION-VERSIONING], [ST-LINK-GLOBAL-VISIBILITY], [INV-GLOBAL-ADDRESS-UNIQUENESS], [INT-CROSS-SESSION-TRANSCLUSION], [EC-CONFLICT-COPY-NO-MERGE]

---

### FC-LINK-DELETE-ISOLATION

**Sources:** Findings 0029, 0040

#### Finding 0029

**What happens:** Deleting content from a document's V-stream does not modify any link objects. Links are stored in their home document, separate from the endpoint documents. Delete affects discoverability (find_links results change) but not link state (follow_link results unchanged). Deleting one source in a multi-link scenario affects only that source's findability — other links to the same target are unaffected.

**Why it matters for spec:** Frame condition for delete operations: delete modifies only the target document's V-stream; it preserves all link objects, their endpoint specifications, and their I-stream addresses. Formalizable as: `∀ delete(doc, span) : ∀ link ∈ links : link.source_spec' = link.source_spec ∧ link.target_spec' = link.target_spec`.

**Code references:** Tests `search_multiple_links_selective_removal`, `search_by_source_after_source_removed` in `febe/scenarios/links/search_endpoint_removal.py`.

**Provenance:** Finding 0029, sections 5, 6

#### Finding 0040

**What happens:** `DELETEVSPAN(2.x)` on a document's link subspace affects ONLY the POOM layer. It does not modify the link orgl in I-space, the DOCISPAN entries in the spanfilade, or the link's endset references. After removing a link from a document's POOM:
- `find_links()` searching by source content still finds the link (spanfilade intact)
- `follow_link(link_id, LINK_SOURCE)` returns the correct source endpoint (link orgl intact)
- Direct link ID access bypasses POOM entirely

This is the converse of the text-delete frame condition: where text deletion preserves link objects in the 0.2.x subspace (Finding 0024), link-subspace deletion preserves link objects in I-space and spanfilade.

**Why it matters for spec:** Frame condition: `delete(D, 2.x, r) ⟹ ispace' = ispace ∧ spanfilade' = spanfilade`. The POOM is the only mutable layer for links. This is the critical frame condition distinguishing POOM removal from link destruction — the two are not equivalent.

**Code references:**
- `edit.c:31-76` — `deletend()` operates on the document's orgl only; no code path touches the link orgl or spanfilade entries

**Concrete example:**
```
After DELETEVSPAN(2.1) on document:
  find_links(source_specs) → [link_id]    (spanfilade intact)
  follow_link(link_id, LINK_SOURCE) → works  (link orgl intact)
  retrieve_vspanset(doc) → no link span     (POOM entry removed)
```

**Provenance:** Finding 0040, Link Persistence section and Comparison with Text Deletion.

**Co-occurring entries:** [SS-THREE-LAYER-MODEL], [PRE-DELETE], [PRE-FIND-LINKS], [ST-DELETE], [ST-FIND-LINKS], [INV-LINK-PERMANENCE], [INT-TRANSCLUSION-LINK-SEARCH], [EC-REVERSE-ORPHAN], [EC-SEARCH-SPEC-BEYOND-BOUNDS], [EC-TYPE-FILTER-NONFUNCTIONAL]

---

### FC-INSERT-IADDR

**Source:** Finding 0030

**What happens**: INSERT does not modify the I-address of any pre-existing content, in the target document or in any other document. The operation's effect on the identity layer is purely additive: it allocates fresh I-addresses for inserted material. All existing V-to-I mappings outside the target document are completely untouched. Within the target document, existing I-addresses are preserved — only V-addresses change.

**Why it matters for spec**: Frame condition for INSERT on the identity layer: `forall doc d != target, forall v in d :: d.mapping(v) is unchanged`. And within the target: `forall v in target where v mapped to I before INSERT :: exists v' in target' where target'.mapping(v') == I`. No I-address is lost; they may appear at different V-positions but the I-address itself is invariant.

**Provenance**: Finding 0030
**Co-occurring entries:** [ST-INSERT], [INV-IADDR-IMMUTABILITY], [INT-LINK-INSERT], [INT-TRANSCLUSION]

---

### FC-ENFILADE-QUERY-INDEPENDENCE

**Source:** Finding 0041

Query operations (`retrieve`, `retrieveinspan`) return results that are independent of the physical tree structure. Different insertion orderings produce different tree shapes (sibling ordering, split points, disk layout) but identical query results. The widdative summaries (`cwid` fields) maintain the same logical intervals regardless of tree shape.

**Why it matters for spec:** This is a frame condition on the observation functions — the physical tree structure is not observable through the query interface. The spec can treat the enfilade as an abstract set without modeling tree internals, and refinement proofs need only show that queries over any valid tree shape produce the same results.

**Code references:**
- `backend/retrie.c:167-188` — `findcbcseqcrum()` returns same logical content regardless of sibling order

**Provenance:** Finding 0041
**Co-occurring entries:** [SS-DUAL-ENFILADE], [PRE-CONCURRENT-INSERT], [INV-ENFILADE-CONFLUENCE]

---

### FC-GRANF-ON-DELETE

**Sources:** Findings 0061, 0063, 0068

#### Finding 0061

**What happens:** DELETE and REARRANGE are frame-condition-preserving with respect to the granfilade. These operations modify only the spanfilade (V-to-I mappings) and leave the granfilade (I-space content storage) completely unchanged. Content inserted into the granfilade persists permanently at its I-address regardless of subsequent V-space operations.

**Why it matters for spec:** Frame condition: `∀ op ∈ {DELETE, REARRANGE} : granf_after(op) = granf_before(op)`. The granfilade is write-once-never-delete: only INSERT adds entries, and no operation removes them. This is the mechanism underlying the Xanadu principle "bytes never die, addresses never change." For the formal model, the granfilade state can be modeled as a monotonically growing set: `granf(t+1) ⊇ granf(t)` for all timesteps t.

**Code references:** `deletevspanpm` in `backend/edit.c` — calls only spanfilade operations, no granfilade modification. `dodeletevspan` in `backend/do1.c:162-171` — no call to any granf insertion or deletion function. Contrast with `insertseq` in `backend/insert.c:17-70` which does modify the granfilade.

**Provenance:** Finding 0061

#### Finding 0063

**What happens:** This finding confirms and contrasts the frame condition from Finding 0061: DELETE is a pure V-space (spanfilade) operation with no I-space (granfilade) effect, while CREATELINK modifies the granfilade. The experimental evidence is direct:
- INSERT "ABC" → DELETE "B" → INSERT "DEF": 1 shared span pair (no I-address gap). DELETE's frame condition preserves granfilade state.
- INSERT "ABC" → CREATELINK → INSERT "DEF": 2 shared span pairs (I-address gap). CREATELINK violates the granfilade frame condition.

This establishes the operation classification: `{DELETE, REARRANGE}` are granfilade-preserving (weak operations); `{INSERT, COPY, CREATELINK}` are granfilade-modifying (strong operations).

**Why it matters for spec:** Strengthens the frame condition: `∀ op ∈ {DELETE} : granf_after(op) = granf_before(op)`. Explicitly excludes CREATELINK from the frame-preserving set. The Xanadu principle "bytes never die" applies to DELETE (V-space only, I-space untouched) but CREATELINK has permanent I-space effects — the link orgl's I-address is allocated forever and influences all future text I-address allocation.

**Code references:**
- `edit.c` — `deletevspanpm` modifies spanfilade only (no granfilade calls)
- `do1.c:199-225` — `docreatelink` calls `createorglingranf` (granfilade modification)

**Concrete example:**
```
DELETE path:      INSERT "ABC" → DELETE "B" → INSERT "DEF"
  Granfilade: I.1, I.2, I.3 (DELETE leaves all three), then I.4, I.5, I.6
  compare_versions: 1 span pair (contiguous I-addresses for remaining text)

CREATELINK path:  INSERT "ABC" → CREATELINK → INSERT "DEF"
  Granfilade: I.1, I.2, I.3, then link orgl at ~I.2.0, then I.2.1+
  compare_versions: 2 span pairs (gap between ABC and DEF I-addresses)
```

**Provenance:** Finding 0063

#### Finding 0068

**What happens:** Deleting a version does not remove its address from the granfilade. The version's address persists permanently in the granfilade tree and continues to influence subsequent version allocation (the next version will be allocated after the deleted one, not in its place). This is the same frame condition as for I-address deletion documented in Finding 0061.

**Why it matters for spec:** Frame condition for VERSION addresses: `∀ op ∈ {DELETE_VERSION} : granf_after(op) = granf_before(op)`. Version addresses, like I-addresses, are write-once in the granfilade. This ensures version address stability for any external references to the version.

**Code references:** `granf2.c:203-242` — allocation queries granfilade tree which retains all addresses.

**Provenance:** Finding 0068

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-VERSION-ADDRESS], [PRE-VERSION-OWNERSHIP], [ST-ADDRESS-ALLOC], [INV-CRUM-BOUND], [INV-MONOTONIC], [INV-NO-IADDR-REUSE], [INT-LINK-INSERT]

---

### FC-DELETE-CROSS-DOC

**Source:** Finding 0064

**What happens**: DELETE in one document has zero effect on any other document's POOM mappings. If document T transcluded content from document D (sharing I-addresses via COPY), and D subsequently deletes that content, T's POOM still maps to the shared I-addresses. T's content is unaffected — the transclusion survives the source document's deletion.

This is because DELETE operates on a single document's POOM tree only. It calls `deletend` on the target document's orgl, freeing bottom crums from that tree. Other documents' trees are separate data structures and are not touched.

**Why it matters for spec**: Frame condition for DELETE across documents: `∀ D' ≠ D : delete(D, vspan) ⟹ poom(D') = poom_before(D')`. Combined with granfilade immutability, this means the content bytes remain accessible through any other document that still references those I-addresses. A document cannot "retract" content from other documents by deleting it locally.

**Code references**:
- `backend/edit.c:31-76` — `deletend`: operates on a single orgl (document enfilade)
- `backend/orglinks.c:145-152` — `deletevspanpm`: passes a specific document's orgl to `deletend`

**Concrete example**:
```
D has "ABCD", T transcluded "BC" from D (sharing I(5.2), I(5.3))

After DELETE "BC" from D:
  D's POOM: V(1.1)→I(5.1) V(1.2)→I(5.4)          -- "BC" mapping gone from D
  T's POOM: V(2.1)→I(5.2) V(2.2)→I(5.3)          -- UNCHANGED, T still has "BC"
  Granfilade: I(5.2)="B" I(5.3)="C"               -- content bytes persist
```

**Provenance**: Finding 0064
**Co-occurring entries:** [ST-COPY], [ST-DELETE], [INV-DELETE-NOT-INVERSE], [INV-IADDR-IMMUTABILITY]

---

### FC-RESERVED-CRUM

**Source:** Finding 0071

**What happens:** During 2D rebalancing, `ishouldbother` at `recombine.c:150-163` skips any crum with `age == RESERVED`. Reserved crums are in-progress or held by other operations. The rebalancing algorithm treats them as immovable: they cannot be merged into another node, nor can another node steal their children.

**Why it matters for spec:** This is a frame condition on the rebalance operation: reserved crums and their subtrees are invariant under rebalancing. The formal model should express: `∀ node with age = RESERVED: recombinend(parent) does not modify node or node's children`. This ensures concurrent operations that have "reserved" a crum are not disrupted by tree restructuring.

**Code references:**
- `backend/recombine.c:150-163` — `ishouldbother` checks `age == RESERVED` and skips

**Provenance:** Finding 0071
**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-REBALANCE-2D], [ST-SPLIT-2D], [INV-ENFILADE-OCCUPANCY]

---

### FC-VERSION-ISOLATION

**Source:** Finding 0072

**What happens**: Once a version is created via `CREATENEWVERSION`, it is a fully independent document with its own POOM tree. Edits to the original document (INSERT, DELETE, REARRANGE) modify only the original's POOM. Edits to the version modify only the version's POOM. Neither affects the other. The shared I-addresses in the granfilade are immutable and unaffected by either document's mutations.

**Why it matters for spec**: Frame condition for edits on versioned documents:

```
Let V = CREATENEWVERSION(D)
∀ op applied to D : poom(V) unchanged
∀ op applied to V : poom(D) unchanged
∀ op applied to D or V : granfilade unchanged (I-addresses immutable)
```

This is what makes versions useful as recovery snapshots — the version's state is frozen with respect to edits on the original.

**Code references**:
- `backend/do1.c:264-303` — `docreatenewversion`: creates a new, separate orgl
- `backend/edit.c:31-76` — `deletend`: operates on a single document's orgl only

**Provenance**: Finding 0072
**Co-occurring entries:** [SS-POOM-MUTABILITY], [ST-DELETE], [ST-VERSION-CREATE], [INV-DELETE-NOT-INVERSE]

---

### FC-GRANF-ON-VERSION

**Source:** Finding 0077

**What happens:** CREATENEWVERSION does not modify the content portion of the granfilade. Like DELETE and REARRANGE, it is content-allocation-neutral. However, unlike DELETE, it DOES modify the granfilade by adding a document address entry. This places VERSION in a middle category:

| Operation | Content granfilade | Document granfilade |
|-----------|-------------------|-------------------|
| INSERT | Modified (new content) | Unchanged |
| DELETE | Unchanged | Unchanged |
| CREATELINK | Modified (link orgl) | Unchanged |
| CREATENEWVERSION | **Unchanged** | **Modified** (new doc addr) |

**Why it matters for spec:** Frame condition: `∀ op ∈ {VERSION} : granf_content_after(op) = granf_content_before(op)`. But NOT `granf_after(op) = granf_before(op)` (because a document address is allocated). This refines the operation classification from Finding 0063: `{DELETE, REARRANGE}` are fully granfilade-preserving; `{VERSION}` is content-granfilade-preserving but document-granfilade-modifying; `{INSERT, CREATELINK}` are content-granfilade-modifying.

**Code references:** `docreatenewversion` in `backend/do1.c:260-299` — calls `createorglingranf` (document allocation) but NOT `findisatoinsertgr` for content. `docopyinternal` in `backend/do1.c:66-82` — only spanfilade operations.

**Provenance:** Finding 0077
**Co-occurring entries:** [SS-ADDRESS-SPACE], [ST-VERSION], [INV-MONOTONIC]

---

### FC-RETRIEVAL-TREE-INDEPENDENCE

**Source:** Finding 0078

**What happens:** The V-ordering of retrieval results is independent of the internal B-tree structure. Even if split/rebalance operations (Finding 0071) or out-of-order insertions (Finding 0041) produce a tree where sibling order does not match V-address order, the `incontextlistnd` insertion-sort re-establishes V-ordering during retrieval. Tree structure affects storage and traversal efficiency, but not the ordering of results.

**Why it matters for spec:** This is a frame condition: tree-internal reorganization (splits, rebalances, rotations) does not change the observable result ordering of retrieval operations. The formal spec can abstract away tree structure entirely for correctness proofs — the sorted-result postcondition holds for any tree that stores the same set of `(V-position, I-address)` entries. This simplifies verification: one need only prove that `incontextlistnd` produces a sorted list from any input order, not that the tree itself maintains any particular sibling ordering.

**Code references:**
- `context.c:75-111` — `incontextlistnd()` sorts independently of discovery order
- `retrie.c:252-265` — `findcbcinarea2d()` traverses left-to-right via `getrightbro`, but this order is not guaranteed to be V-sorted

**Provenance:** Finding 0078
**Co-occurring entries:** [SS-CONTEXT-LIST], [INV-RETRIEVAL-V-SORTED]

---

## Invariants

> What always holds across all operations

### INV-CONTENT-IMMUTABILITY

**Source:** Finding 0002

**What happens:** Content identities, once created, are never modified or destroyed. Deletion from a document removes that document's reference to the content, but the content identity persists as long as any document in the system references it. Insertion into a document creates new content identities without affecting existing ones. This holds across all operations tested: insert, remove, and vcopy.

**Why it matters for spec:** This is a global invariant: `forall c : ContentId, t1 t2 : Time :: exists_at(c, t1) && referenced(c, t2) ==> exists_at(c, t2)` — content that exists and is referenced is never destroyed. More strongly, content identity is eternal: once created, the identity exists permanently in the system regardless of reference count (the system does not garbage-collect content). The formal spec should assert that the set of all content identities is monotonically growing.

**Concrete example:**
- Source: "Keep this. Delete this. Keep end."
- Target vcopies "Delete this." from source
- "Delete this." is removed from source: Source becomes "Keep this. Keep end."
- Target still reads "Transcluded: Delete this." — the content identity persists

**Code references:** `scenario_vcopy_source_deleted` in `febe/scenarios/content/vcopy.py:341-417`

**Provenance:** Finding 0002
**Co-occurring entries:** [SS-CONTENT-IDENTITY], [ST-INSERT], [ST-REMOVE], [ST-VCOPY], [FC-DOC-ISOLATION], [INV-TRANSITIVE-IDENTITY]

---

### INV-TRANSITIVE-IDENTITY

**Sources:** Findings 0002, 0007, 0008, 0018

#### Finding 0002

**What happens:** Content identity is preserved transitively through chains of transclusion. If document B transcludes from C, and document A transcludes from B, then A and C share content identity even though A never directly referenced C. The `compare_versions` operation between A and C correctly reports the shared content.

**Why it matters for spec:** This is an invariant on identity propagation: `shares_identity(A, B) && shares_identity(B, C) ==> shares_identity(A, C)`. It follows from the vcopy semantics — since vcopy shares the actual content identity (not a copy), chains of vcopy naturally preserve identity. The formal spec need not add a special transitivity rule; it falls out of the state-transition definition of vcopy.

**Concrete example:**
- C: "Original from C"
- B: "B prefix: " + vcopy("Original" from C) → B references C's content identity for "Original"
- A: "A prefix: " + vcopy(all of B) → A references B's "B prefix: " identities AND C's "Original" identity
- `compare_versions(A, C)` reports shared content "Original"

**Code references:** `scenario_nested_vcopy` in `febe/scenarios/content/vcopy.py:180-268`

**Provenance:** Finding 0002

#### Finding 0007

**What happens:** Content identity is preserved transitively through version chains. If v2 is a version of v1, and v3 is a version of v2, then v1 and v3 share content identity for the text that originated in v1 — even though v3 was never directly versioned from v1. The `compare_versions` operation between v1 and v3 correctly reports shared content. This extends the INV-TRANSITIVE-IDENTITY invariant from Finding 0002 (which covered transclusion chains) to version chains.

**Why it matters for spec:** The invariant `shares_identity(A, B) && shares_identity(B, C) ==> shares_identity(A, C)` holds for version chains just as it does for vcopy chains. This follows from the version-create postcondition: since version-create copies content identity references (not content), chained versions naturally inherit all ancestral identities. No special transitivity rule is needed for versions — it falls out of ST-VERSION-CREATE.

**Concrete example:**
- v1: "Original from v1"
- v2: version of v1, then append " plus v2" → "Original from v1 plus v2"
- v3: version of v2, then append " plus v3" → "Original from v1 plus v2 plus v3"
- `compare_versions(v1, v3)` reports "Original from v1" as shared content

**Code references:** Test `compare_across_version_chain`

**Provenance:** Finding 0007

#### Finding 0008

**What happens:** Content identity transitivity, established in Findings 0002 (transclusion chains) and 0007 (version chains), holds for MIXED chains of versioning and transclusion. If C has content with a link, B is a version of C, and A transcludes from B, then A can discover C's link — even though A never interacted with C. The chain version→transclusion preserves content identity just as pure version or pure transclusion chains do.

**Why it matters for spec:** The invariant `shares_identity(A, B) ∧ shares_identity(B, C) ⟹ shares_identity(A, C)` is confirmed for heterogeneous chains (version + transclusion mixed). Since both ST-VERSION-CREATE and ST-VCOPY operate on the same content identity system (neither copies content, both share content identity references), mixed chains are a natural consequence. The formal spec needs no additional transitivity axiom for mixed chains — it falls out of the existing postconditions.

**Concrete example:**
- C: "Original content in C" — link on "content"
- B: version of C → B shares content identity with C
- A: transcludes from B → A shares content identity with B (and transitively with C)
- `find_links(C)` → [link_id]
- `find_links(B)` → [link_id]
- `find_links(A)` → [link_id] (A found C's link via B)

**Code references:** Test `transitive_link_discovery`

**Provenance:** Finding 0008

#### Finding 0018

**What happens:** Content identity flows transitively through transclusion chains. If A transcludes from B, and B transcludes from C, then A and C share content identity for the transcluded portion — even though A never directly referenced C. `FINDDOCSCONTAINING` and `compare_versions` both respect this transitivity.

**Why it matters for spec:** Invariant: I-address sharing is transitive. If doc A contains I-address range R (via vcopy from B), and B contains R (via vcopy from C), then A and C share R. This follows from the fact that vcopy preserves I-addresses rather than creating new ones.

**Concrete example:**
```
C: "ABCDEFGHIJ"
B: vcopies all of C
A: vcopies "DEFGH" from B

compare_versions(A, C) → "DEFGH" shared
find_documents("DEF" from C) → [A, B, C]
```

**Code references:** Tests `find_documents_transitive`, `identity_partial_transclusion` in scenarios.

**Provenance:** Finding 0018, Key Findings 2 and 6.

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-VERSION-ADDRESS], [ST-INSERT], [ST-REARRANGE], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-DOC-ISOLATION], [FC-LINK-PERSISTENCE], [INV-CONTENT-IMMUTABILITY], [INV-LINK-GLOBAL-VISIBILITY], [INV-REARRANGE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [INT-VERSION-TRANSCLUSION], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-EMPTY-DOC]

---

### INV-SPECSET-ORDER

**Source:** Finding 0003

**What happens:** SpecSet operations preserve VSpec ordering in their results. Retrieve concatenates content in VSpec order. Vcopy places content in VSpec order. This is consistent across all multi-span operations tested: retrieve, vcopy, and compare all respect the sequence ordering of the SpecSet.

**Why it matters for spec:** This is an invariant on SpecSet processing: `forall op in {retrieve, vcopy} :: result_order(op(specset)) = vspec_order(specset)`. The formal spec must model SpecSet as a sequence (not a set or bag) and all SpecSet-consuming operations must process VSpecs in sequence order. This ensures deterministic behavior — the same SpecSet always produces the same result regardless of implementation details.

**Code references:** Tests `retrieve_noncontiguous_spans`, `retrieve_multiple_documents`

**Provenance:** Finding 0003
**Co-occurring entries:** [SS-SPECSET], [ST-VCOPY], [FC-SPECSET-COMPARE]

---

### INV-LINK-CONTENT-TRACKING

**Sources:** Findings 0004, 0005, 0019, 0026

#### Finding 0004

**What happens:** Links track content identity across all document modifications. Insertions before a linked span, deletions of adjacent text, and modifications to target documents all leave links valid and findable. This holds universally — all seven survivability tests pass. The invariant is: once a link is created referencing content identities, it remains valid as long as those content identities exist in the system (in any document).

**Why it matters for spec:** This is a global invariant: `forall link : Link, op : Operation :: content_ids(link.source) ⊆ all_content_ids(system) ==> findable(link)`. Link validity depends on content existence, not document structure. Since INV-CONTENT-IMMUTABILITY guarantees content identities are never destroyed while referenced, and links reference content identities, links are inherently persistent. The formal spec should derive link persistence from content immutability rather than stating it as an independent axiom.

**Concrete example:**
- Before: Document A has "Click [here] for details", link on "here" (content identity C₁)
- After insert at beginning of A: A becomes "PREFIX Click [here] for details"
- Link on "here" still valid — it references C₁, which still exists at a shifted position
- After delete of "Click ": A becomes "PREFIX [here] for details"
- Link still valid — C₁ still in A's reference set

**Code references:** Tests `link_survives_source_insert` (PASS), `link_survives_source_delete_adjacent` (PASS), `link_survives_target_modify` (PASS)

**Provenance:** Finding 0004

#### Finding 0005

**What happens:** Links track content identity across all document modifications — insertions before a linked span, deletions of adjacent text, and modifications to target documents all leave links valid and findable. This finding confirms the invariant with a full matrix: all 17 link scenarios pass after Bug 0008 client fixes. Specifically, three survivability scenarios validate that non-overlapping edits never invalidate links: inserting before the linked span, deleting adjacent (non-overlapping) text, and modifying the target document.

**Why it matters for spec:** Confirms the invariant from Finding 0004: `forall link : Link, op : Operation :: content_ids(link.source) ⊆ all_content_ids(system) ==> findable(link)`. The 17-scenario pass provides stronger empirical backing — the invariant holds across insert, remove, vcopy, and their combinations with links on both source and target endpoints.

**Code references:** Tests `link_survives_source_insert`, `link_survives_source_delete_adjacent`, `link_survives_target_modify` (all PASS)

**Provenance:** Finding 0005

#### Finding 0019

Links track content by identity (I-address), not by position (V-address). This has three observable consequences:

1. **V-address shifts**: When content is inserted within or before a linked region, the endset V-addresses shift to reflect the new positions:
   ```
   Before: "Click here for info" — link on "here" at V 1.7 width 0.4
   Insert: "right " at position 1.7
   After:  "Click right here for info" — link reports 1.13 width 0.4
   ```

2. **Partial deletion shrinks endsets**: When part of a linked region is deleted, the link shrinks to cover only the surviving content:
   ```
   Before: "Click right here for info" — link on "right here" at V 1.7 width 0.10
   Delete: "right " (6 chars)
   After:  "Click here for info" — link reports 1.7 width 0.4
   ```

3. **Cross-document discovery**: A link on transcluded content is discoverable by searching the original document's I-address region:
   ```
   Doc 1: "Original shared text"
   Doc 2: "Prefix: " + vcopy("shared" from doc 1)
   Link created on "shared" in doc 2
   find_links(doc 1, "shared" region) → finds the link in doc 2
   ```

The invariant: a link's endset always covers exactly the surviving content that was originally linked, regardless of insertions, deletions, or transclusions that have occurred.

**Why it matters for spec**: This is the central invariant for link behavior — links are anchored to content identity, not positional slots. All postconditions for insert, delete, and vcopy must preserve this property.

**Code references**: Tested via `endsets/endsets_after_source_insert`, `endsets/endsets_after_source_delete`, `endsets/endsets_transcluded_source` scenarios.

**Provenance**: Finding 0019, sections 1, 2, 4

#### Finding 0026

**What happens:** Link discovery through content identity is confirmed to work for the target endpoint of a link, not just the source endpoint. When a link's target is transcluded content, searching the transclusion origin's content identities discovers the link. The link ID `1.1.0.1.0.3.0.2.1` (created pointing at document A) appears in `find_links` results when querying document B's original content — confirming that `find_links` indexes link targets by I-address, and transclusion preserves I-address sharing.

**Why it matters for spec:** Strengthens the invariant that links track content by identity rather than position. The formal property `find_links(specset) = {link | content_ids(link.target) ∩ content_ids(specset) ≠ ∅ ∨ content_ids(link.source) ∩ content_ids(specset) ≠ ∅}` is validated for the target-side intersection via a transclusion chain.

**Code references:** Golden evidence in `golden/links/link_to_transcluded_content.json` — `find_links` with `to` set to B's original content returns the link created on A's transcluded copy.

**Provenance:** Finding 0026

**Co-occurring entries:** [SS-LINK-ENDPOINT], [ST-REMOVE], [FC-LINK-PERSISTENCE], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [EC-LINK-TOPOLOGY], [EC-MULTISPAN-LINK-DUPLICATION], [EC-ORPHANED-LINK], [EC-PIVOT-LINK-FRAGMENTATION]

---

### INV-LINK-GLOBAL-VISIBILITY

**Source:** Finding 0008

**What happens:** Links in udanax-green are globally visible through content identity. A link created in any document is discoverable from every document in the system that shares the linked content's identity. This holds regardless of how the content identity was shared — transclusion, versioning, or transitive chains of both. This is not a new mechanism but an emergent invariant of the content-identity-based link model.

**Why it matters for spec:** This is a derived invariant that should be provable from existing axioms: `forall link, doc :: content_ids(link.source) ∩ content_ids(doc) ≠ ∅ ⟹ findable(link, doc)`. The formal spec should state this as a theorem rather than an axiom, since it follows from: (1) SS-LINK-ENDPOINT (links reference content identities), (2) SS-CONTENT-IDENTITY (content identity is shared, not copied), and (3) the definition of `find_links` as content-identity intersection. Finding 0008 provides the empirical confirmation across six scenarios covering transclusion, versioning, mixed chains, and multi-endpoint links.

**Code references:** All six passing scenarios in `golden/interactions/`: `transclude_linked_content`, `link_to_transcluded_then_version`, `version_add_link_check_original`, `transitive_link_discovery`, `link_both_endpoints_transcluded`, `version_transcluded_linked_content`

**Provenance:** Finding 0008
**Co-occurring entries:** [FC-LINK-PERSISTENCE], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION]

---

### INV-SUBSPACE-CONVENTION

**Sources:** Findings 0009, 0010, 0011, 0015, 0038, 0049, 0051, 0054

#### Finding 0009

**What happens**: The system enforces by convention (not by runtime check) that V-positions `0.x` contain only link orgl ISAs as I-addresses, and V-positions `1.x` contain only permascroll I-addresses. No code in the enfilade storage path validates this invariant — it is maintained by callers (`docreatelink` writes to `0.x`, `doinsert`/`docopy` for text writes to `1.x`). The `permute()`, `retrieverestricted()`, and `docopy()` functions are all type-agnostic.

**Why it matters for spec**: This is a convention-over-enforcement invariant. The spec should state it as a property that holds across all well-formed operations, but note that the storage layer does not enforce it. This is the kind of invariant that Dafny can verify as a postcondition of each operation rather than as a storage-layer check.

**Code references**:
- `do1.c:215-216` — `findnextlinkvsa` + `docopy` for link storage (caller ensures `0.x`)
- `do2.c:151-167` — `findnextlinkvsa` hardcodes first link at `0.1`

**Provenance**: Finding 0009

#### Finding 0010

**What happens**: The unified enfilade storage model treats all V→I mappings identically — `insertpm`, `docopy`, `retrieverestricted`, and `permute` are all type-agnostic. The convention that V-position `0.x` holds link orgl ISAs and `1.x` holds permascroll I-addresses is enforced solely by callers. The validation function `acceptablevsa()` in `do2.c:110-113` unconditionally returns `TRUE`, providing no runtime enforcement. This means it is possible to: (a) insert text at position `0.x`, corrupting the link subspace; (b) insert link references at position `1.x`, corrupting the text subspace; (c) create semantically invalid documents that violate the subspace convention.

**Why it matters for spec**: The convention-over-enforcement design means the subspace invariant is not a storage-layer property but a property that must be verified as a postcondition of every well-formed operation. In Dafny, this would be modeled as a `requires` clause on document mutation operations asserting that text content targets `V >= 1.0` and link references target `V < 1.0`. The `acceptablevsa` stub is a clear signal that enforcement was intended but never implemented.

**Code references**:
- `do2.c:110-113` — `acceptablevsa()` always returns `TRUE`
- `do1.c:45-65` — `docopy()` calls `acceptablevsa()` but gets no validation
- `do1.c:162-171` — `dodeletevspan()` performs no subspace check

**Concrete example**:
```
acceptablevsa(vsaptr, orglptr) always returns TRUE

Consequence: docopy(doc, vsa=0.5, text_ispanset) succeeds
  → permascroll I-address stored in link subspace
  → retrieve_contents on 0.x returns garbage (permascroll addr treated as link ISA)
  → find_links on 0.x finds no valid link orgl

Similarly: docopy(doc, vsa=1.5, link_ispanset) succeeds
  → link orgl ISA stored in text subspace
  → retrieve_contents on 1.x dereferences link ISA in permascroll → NULL/garbage
```

**Provenance**: Finding 0010, also Finding 0009

#### Finding 0011

**What happens:** The subspace convention (V-position 0.x = links, 1.x = text) is a social contract enforced by convention, not by runtime checks. The unified enfilade storage treats all data uniformly — the system does not distinguish between link I-addresses and content I-addresses at the type level. Both are just tumblers. Dereferencing a link ISA as content produces garbage, but no error is raised.

**Why it matters for spec:** The formal specification must model subspace membership as a type-level distinction even though the implementation uses untyped tumblers. This invariant — that data at 0.x V-positions are links and data at 1.x V-positions are text — must be stated as a global invariant in the spec. Every operation that reads or writes V-positions should preserve this invariant. The spec makes explicit what the code leaves implicit.

**Code references:**
- `backend/green/do2.c:110-113` — `acceptablevsa` does not enforce subspace rules
- `specset2ispanset` and `ispanset2vstuffset` treat all I-addresses uniformly

**Provenance:** Finding 0011

#### Finding 0015

**What happens**: The finding provides a decision table confirming the subspace convention's implications for `compare_versions`:

| V-Position | Contains | I-Address Type | Has "Common Origin"? | Included in compare_versions? |
|------------|----------|----------------|---------------------|-------------------------------|
| 0.x | Link references | Link orgl ISAs | No | No |
| 1.x | Text content | Permascroll addresses | Yes | Yes |

Links have no "common origin" for three reasons: (1) link ISAs are unique identities, not content origins — two documents cannot share the same link ISA via transclusion; (2) links are metadata about content, not content itself; (3) comparing link ISAs is semantically undefined — even if they matched, it wouldn't mean "shared content."

**Why it matters for spec**: This strengthens the subspace convention invariant with a semantic justification: the link/text partition is not merely a storage convention but reflects a fundamental type distinction. Operations defined over "content with common origin" (compare_versions, and potentially others) must be restricted to the text subspace by definition, not by workaround.

**Code references**:
- `correspond.c` — does not implement subspace filtering
- `do1.c:199-225` — `docreatelink()` creates unique link ISAs (non-shareable)

**Provenance**: Finding 0015, also Finding 0009

#### Finding 0038

**What happens**: The three-subspace convention uses mantissa[0] to encode content type: `1` = text, `2` = link, `3` = link type endpoint. This is constructed in `setlinkvsas()` which hardcodes digit-0 values of 1, 2, and 3 for the FROM, TO, and THREE endpoints respectively. The convention extends beyond the two-subspace model (text vs. links) documented in finding 0009 to include a third subspace for type endpoints. Each subspace maintains its own contiguous numbering independently (links at 2.1, 2.2, ...; text at 1.1, 1.2, ...).

**Why it matters for spec**: The formal model of V-address space needs three partitions, not two. The invariant is: `mantissa[0] in {1, 2, 3}` for all valid V-addresses, with each value mapping to a distinct content type. Contiguity within each subspace is maintained independently — inserting at 1.5 shifts 1.6+ but does not affect 2.x numbering.

**Code references**:
- `do2.c:169-183` — `setlinkvsas()` constructs all three subspace positions

**Provenance**: Finding 0038

#### Finding 0049

**What happens:** Finding 0049 provides direct experimental confirmation that the subspace partition (text at 1.x, links at 2.x) is not enforced. INSERT at V-position 2.1 with text content succeeds, and the content is stored and retrievable. The vspanset after insertion shows two disjoint spans crossing subspace boundaries. This demonstrates the convention is purely caller-enforced — the back end treats all V-positions uniformly.

**Why it matters for spec:** The subspace convention must be modeled as a precondition on every V-position-accepting operation, not as a storage-layer invariant. The spec invariant `INV-SUBSPACE: ∀ v ∈ doc.vspan_set: (type(content_at(v)) == TEXT) ⟹ v.head == 1` holds only if all callers cooperate. A well-formed system state requires this invariant, but the implementation provides no enforcement. For Dafny, this means the invariant must appear as a `requires` clause on every public operation, with a proof obligation that each operation preserves it.

**Code references:**
- `backend/do2.c:110-113` — `acceptablevsa()` stub that was presumably intended for validation
- `backend/do1.c:121-124` — `doinsert()` sets `TEXTATOM` element type but V-position is independent

**Concrete example:**
```
INSERT text at V:2.1 → succeeds
retrieve_contents(V:2.1, width:0.19) → "TextAtLinkPosition"
  → text bytes occupying link subspace
  → no error, no warning, no distinction from normal text insertion
```

**Provenance:** Finding 0049

#### Finding 0051

**What happens:** Finding 0051 demonstrates a second violation path for the subspace convention. While finding 0049 showed INSERT can place text at link-subspace positions, finding 0051 shows REARRANGE can *move* previously correctly-placed text into the wrong subspace. After a pivot with cross-subspace cuts, `retrieve_contents` at 2.x returns text bytes ("ABC") — identical behavior to a direct misplacement via INSERT. The back end draws no distinction between content that was placed at 2.x directly vs. content that was moved there by rearrangement.

**Why it matters for spec:** The subspace invariant `∀ v ∈ doc.vspan_set: type(content_at(v)) == TEXT ⟹ v.head == 1` can be violated by at least two operations: INSERT (finding 0049) and REARRANGE (this finding). For Dafny verification, the proof that this invariant is preserved must cover every V-position-mutating operation, not just content-placing ones. REARRANGE is particularly insidious because content may be correctly placed initially and only later displaced across the boundary. The preservation proof must show that the displacement arithmetic for every affected orgl stays within the original subspace.

**Code references:**
- `backend/edit.c:125` — `tumbleradd` displaces V-position without subspace guard
- `backend/do2.c:110-113` — `acceptablevsa()` (from finding 0049) — even if this were fixed, REARRANGE would bypass it since it modifies V-positions in-place rather than going through `acceptablevsa()`

**Concrete example:**
```
Initial state: "ABC" correctly at V:1.1–1.3 (text subspace) — invariant holds
After pivot [1.1, 1.4, 2.5]: "ABC" at V:2.2–2.4 (link subspace) — invariant violated

Two violation paths now known:
  1. INSERT at V:2.1 with text  (finding 0049) — direct misplacement
  2. REARRANGE pivot across subspace boundary (finding 0051) — displacement into wrong subspace
```

**Provenance:** Finding 0051, also Finding 0049

#### Finding 0054

**What happens:** The subspace isolation property generalizes across all three subspaces. For ANY insertion at `N.x` (where `N` is the subspace digit), the second blade is `(N+1).1`, restricting shifts to the `N.x` subspace only:
- INSERT at `1.x` → blades `[1.x, 2.1)` → shifts only text
- INSERT at `2.x` → blades `[2.x, 3.1)` → shifts only links
- INSERT at `3.x` → blades `[3.x, 4.1)` → shifts only type endpoints

Each subspace is a self-contained shift domain. This is a structural consequence of `findaddressofsecondcutforinsert()` computing `(N+1).1` regardless of the fractional part of the insertion position.

**Why it matters for spec:** The invariant `∀ N ∈ {1,2,3}, ∀ op = INSERT(N.x) : shift_region(op) ⊆ [N.1, (N+1).1)` holds for all insertions. This can be verified in Dafny as a lemma about `findaddressofsecondcutforinsert`: for input `N.x`, the output is always `(N+1).1`, which combined with the knife classification logic guarantees subspace isolation.

**Code references:**
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert()` generalizes across subspaces

**Provenance:** Finding 0054

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DUAL-ENFILADE], [SS-TWO-BLADE-KNIFE], [PRE-COMPARE-VERSIONS], [PRE-DELETE], [PRE-ENF0-PLACEMENT-GAP], [PRE-INSERT], [PRE-REARRANGE], [PRE-RETRIEVE-CONTENTS], [PRE-VCOPY], [ST-COMPARE-VERSIONS], [ST-INSERT], [ST-REARRANGE], [FC-SUBSPACE], [INT-LINK-RETRIEVAL], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-ERROR-ABORT], [EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES], [EC-VSPAN-NORMALIZATION]

---

### INV-DUAL-ENFILADE-CONSISTENCY

**Source:** Finding 0012

**What happens:** The `spanf` index must be consistent with the link orgls stored in `granf`. For every link orgl in `granf`, its endpoints must be indexed in `spanf` (otherwise the link exists but is not findable). Conversely, every entry in `spanf` must correspond to an existing link orgl in `granf` (otherwise queries return phantom links). This consistency is maintained by `docreatelink()` updating both enfilades in sequence, but there is no transactional mechanism documented — if the sequence is interrupted partway, the enfilades can desynchronize.

**Why it matters for spec:** This is a cross-structure invariant: `forall link_isa ∈ granf.link_orgls :: endpoints(link_isa) ⊆ spanf.indexed_endpoints(link_isa)` AND `forall (i_addr, link_isa) ∈ spanf :: link_isa ∈ granf.link_orgls`. The spec should state this as an invariant that holds before and after every complete operation. It should also note the absence of transactional guarantees — partial failures during `docreatelink` could violate this invariant. Dafny verification should prove that each operation's postcondition preserves this invariant assuming no interruption.

**Code references:**
- `do1.c:199-225` — `docreatelink()` updates both enfilades sequentially, no rollback on failure

**Provenance:** Finding 0012
**Co-occurring entries:** [SS-DUAL-ENFILADE], [SS-GRANF-OPERATIONS], [SS-SPANF-OPERATIONS], [ST-CREATE-LINK], [FC-CONTENT-SPANF-ISOLATION]

---

### INV-READ-SHARING

**Source:** Finding 0014

**What happens:** Multiple connections can hold READBERT access to the same document simultaneously. There is no limit on concurrent readers. However, the presence of any WRITEBERT holder on a document blocks new READ access from other connections.

**Why it matters for spec:** This is a classic readers-writer lock invariant. Formalizable as: `forall d: Document, c1 c2: Connection | bert(c1, d) = READ ∧ bert(c2, d) = READ → c1 ≠ c2 is permitted`. And: `bert(c1, d) = WRITE → forall c2 ≠ c1 | bert(c2, d) = NONE`.

**Code references:** `bert.c:43-50` (access matrix), `bert.c` (BERT table implementation)

**Provenance:** Finding 0014
**Co-occurring entries:** [SS-BERT], [PRE-OPEN-DOC], [INV-WRITE-EXCLUSIVITY], [INT-BERT-VERSION]

---

### INV-WRITE-EXCLUSIVITY

**Sources:** Findings 0014, 0050

#### Finding 0014

**What happens:** At most one connection can hold WRITEBERT access to any given document. If connection A holds WRITE, all WRITE requests from other connections return -1. Additionally, all READ requests from other connections also return -1.

**Why it matters for spec:** This is the mutual exclusion invariant for document writes: `forall d: Document | |{c: Connection | bert(c, d) = WRITE}| <= 1`. Combined with the read-blocking rule: if any connection holds WRITE, no other connection holds any access. This guarantees single-writer consistency without requiring merge conflict resolution.

**Code references:** `bert.c:43-50` (access matrix shows -1 for cross-connection WRITE conflicts)

**Provenance:** Finding 0014

#### Finding 0050

**What happens:** The write exclusivity invariant (at most one connection holds WRITEBERT for a document) is a *logical* invariant of the BERT table state, but it is not an *enforced* invariant of document mutation. Because the back end does not gate mutations on BERT checks (response is sent before the check), a front end that ignores the BERT protocol can write to any document regardless of who holds the WRITE token. Multiple front ends could concurrently mutate the same document if they bypass BERT token acquisition.

**Why it matters for spec:** The formal invariant `|{c: Connection | bert(c, d) = WRITE}| <= 1` (from Finding 0014) holds for the BERT table itself but does not imply single-writer access to document content. The spec must distinguish between the BERT-table invariant (which the back end does maintain) and the document-mutation invariant (which requires front-end compliance). In a threat model with untrusted front ends, write exclusivity is not guaranteed.

**Code references:**
- `bert.c:43-50` — access matrix enforces exclusivity *within the BERT table*
- `fns.c:84-98` — mutation handler bypasses BERT check in the response path

**Provenance:** Finding 0050

**Co-occurring entries:** [SS-BERT], [PRE-INSERT], [PRE-OPEN-DOC], [INV-READ-SHARING], [INT-BERT-FEBE], [INT-BERT-VERSION], [EC-RESPONSE-BEFORE-CHECK]

---

### INV-REARRANGE-IDENTITY

**Sources:** Findings 0016, 0018, 0056

#### Finding 0016

**What happens:** Rearrange preserves content identity (I-addresses). After a pivot or swap, the moved content retains the same I-addresses it had before. Only V-addresses change — the content's position in the document is different, but its origin identity is the same.

**Why it matters for spec:** This is a key invariant distinguishing REARRANGE from a delete-then-insert sequence. Formally: `i_addresses(doc_after) = i_addresses(doc_before)` — the multiset of I-addresses is identical before and after. This is stronger than just preserving document length; it preserves the specific identity of each content unit. A delete+insert would destroy the original I-address and create a new one, breaking this invariant.

**Concrete example:**
- Content `"BC"` at V-address 1.2 has I-address `I_bc`
- After `pivot(doc, 1.2, 1.4, 1.6)`, `"BC"` is at a new V-address but still has I-address `I_bc`

**Code references:** `edit.c:rearrangend()` (backend); test `pivot_preserves_identity`

**Provenance:** Finding 0016

#### Finding 0018

**What happens:** Rearrange operations (pivot, swap) are identity-preserving: the set of I-addresses in a document is invariant across rearrangement. No new I-addresses are created and none are destroyed.

**Why it matters for spec:** Invariant: for any document D, `I-addresses(D_before_rearrange) = I-addresses(D_after_rearrange)`. This is a multiset equality — the same I-addresses exist with the same multiplicities, only V-position mappings change.

**Code references:** Tests `identity_through_rearrange_pivot`, `identity_through_rearrange_swap`.

**Provenance:** Finding 0018, Key Finding 3.

#### Finding 0056

**What happens:** Rearrange preserves I-addresses exactly. The code modifies only `ptr->cdsp.dsas[index]` (the V-address component of the displacement). The I-address, stored separately, is never touched. No new I-addresses are allocated, no content is duplicated in the permascroll, and the same enfilade nodes (crums) are retained.

**Why it matters for spec:** Formally: `∀ c ∈ content(doc): i_addr(c, doc_after) = i_addr(c, doc_before)`. This is what makes rearrange the **unique** identity-preserving move operation. A delete+insert would: (1) destroy the original I-address, (2) allocate a new I-address, (3) break all links bound to the original content, (4) break all cross-document transclusion references.

**Concrete example:**
- Content "BC" at V-address 1.2 has I-address `I_bc`
- After `pivot(1.2, 1.4, 1.6)`, "BC" is at V-address 1.4 but still has I-address `I_bc`
- Links bound to `I_bc` still resolve; transclusions referencing `I_bc` still find the content

**Code references:** `backend/edit.c:125` — `tumbleradd(&ptr->cdsp.dsas[index], &diff[i], &ptr->cdsp.dsas[index])`

**Provenance:** Finding 0056 (extends Findings 0016, 0002)

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [PRE-REARRANGE], [ST-REARRANGE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-REARRANGE-EXTERIOR], [INV-PIVOT-SELF-INVERSE], [INV-REARRANGE-LINK-SURVIVAL], [INV-TRANSITIVE-IDENTITY], [EC-COMPARE-VERSIONS-LINK-CRASH], [EC-REARRANGE-CROSS-SUBSPACE], [EC-REARRANGE-EMPTY-REGION]

---

### INV-REARRANGE-LINK-SURVIVAL

**Source:** Finding 0016

**What happens:** Links bound to rearranged content remain discoverable after pivot or swap. Because links are bound to I-addresses (not V-addresses), moving content to new V-positions does not break link bindings. The link still resolves to the same content at its new location.

**Why it matters for spec:** This is a consequence of INV-REARRANGE-IDENTITY combined with the link binding model (links bind to I-addresses, per SS-LINK-ENDPOINT). Formally: for any link `L` bound to content `C`, if `C` is moved by rearrange, then `L` is still discoverable via the content's new V-address. The spec should verify: `∀ L ∈ links(doc), ∀ rearrange R: findlinks(doc_after_R, endpoint(L)) ≠ ∅` — links don't become orphaned through rearrangement.

**Concrete example:**
- Before swap: link from `"BC"` to `"FG"`
- After swap: same link still discoverable at the new positions of `"BC"` and `"FG"`

**Code references:** Test `swap_with_links`

**Provenance:** Finding 0016
**Co-occurring entries:** [ST-REARRANGE], [FC-REARRANGE-EXTERIOR], [INV-PIVOT-SELF-INVERSE], [INV-REARRANGE-IDENTITY]

---

### INV-PIVOT-SELF-INVERSE

**Source:** Finding 0016

**What happens:** Applying the same pivot operation twice with identical cut points restores the document to its original state. This means pivot is its own inverse: `pivot(pivot(doc, c1, c2, c3), c1, c2, c3) = doc`.

**Why it matters for spec:** This is a strong algebraic property of the pivot operation. It confirms that pivot is a transposition (order-2 permutation) on the document's content sequence. The spec can express this as: `∀ doc, c1, c2, c3: rearrange(rearrange(doc, [c1,c2,c3]), [c1,c2,c3]) = doc`. Note this holds only when the two regions are the same size; since pivot swaps adjacent regions around the same cut points, the cut points remain valid after the first application only if the regions don't change the document's length (which they don't — rearrange is length-preserving). This property does NOT necessarily hold for swap with 4 cuts when the swapped regions differ in size, because the cut points may refer to different content after the first swap.

**Concrete example:**
- `"ABCDE"` → `pivot(1.2, 1.4, 1.6)` → `"ADEBC"` → `pivot(1.2, 1.4, 1.6)` → `"ABCDE"`

**Code references:** Test `double_pivot`

**Provenance:** Finding 0016
**Co-occurring entries:** [ST-REARRANGE], [FC-REARRANGE-EXTERIOR], [INV-REARRANGE-IDENTITY], [INV-REARRANGE-LINK-SURVIVAL]

---

### INV-ACCOUNT-ISOLATION

**Source:** Finding 0021

**What happens**: Documents allocated under one account must have addresses that are proper descendants of that account's address. The first document under any account is always `account.0.1`. Subsequent documents increment monotonically within the account's address range.

**Why it matters for spec**: This is a global invariant: for all documents D and accounts A, if D was created under A, then `contains(A, address(D))` must be true. Bug 0013 showed this invariant was violated by the original allocation algorithm, confirming it is not automatically enforced by the flat storage structure and must be explicitly maintained.

**Code references**: `granf2.c:findisatoinsertnonmolecule`; test scenarios `febe/scenarios/accounts.py:account_switch`.

**Provenance**: Finding 0021
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-TUMBLER-CONTAINMENT], [PRE-ADDRESS-ALLOC], [ST-ADDRESS-ALLOC]

---

### INV-GLOBAL-ADDRESS-UNIQUENESS

**Source:** Finding 0022

**What happens:** Document addresses are globally unique even when multiple sessions use the same account. The backend maintains a per-account counter shared across all sessions, so concurrent `create_document()` calls from different sessions on the same account produce distinct, sequential addresses.

**Why it matters for spec:** This is a system-wide invariant: for all sessions S1, S2 and any `create_document()` calls, the resulting addresses are always distinct. The per-account counter is part of global state, not session state, preventing duplicate allocation.

**Code references:** `backend/disk.c` (document storage, address allocation)

**Concrete example:**
- Both sessions: `account(1.1.0.1)`
- Session A: `create_document()` → `1.1.0.1.0.1`
- Session B: `create_document()` → `1.1.0.1.0.2`

**Provenance:** Finding 0022, section 2
**Co-occurring entries:** [SS-SESSION-STATE], [ST-CROSS-SESSION-VERSIONING], [ST-LINK-GLOBAL-VISIBILITY], [FC-SESSION-ACCOUNT-ISOLATION], [INT-CROSS-SESSION-TRANSCLUSION], [EC-CONFLICT-COPY-NO-MERGE]

---

### INV-IADDRESS-PERMANENT

**Source:** Finding 0023

**What happens:** Once an I-address is associated with a document (via insert or vcopy), `find_documents` continues to report that document even after the content is deleted from the document's V-stream. Deletion removes content from the visible view but does not remove the I-address association from the document's address space. This is a permanent, monotonic property — documents only accumulate I-address associations over their lifetime.

**Why it matters for spec:** Invariant: for any document D, if I-address `α` was ever present in D, then `FINDDOCSCONTAINING(α) ⊇ {D}` for all future states, regardless of deletions. Formally: `∀ D, α: α ∈ I-addresses-ever(D) ⟹ D ∈ FINDDOCSCONTAINING(α)`. This is a monotonicity invariant — the set of documents returned by `FINDDOCSCONTAINING` for a given I-address can only grow, never shrink.

**Concrete example:**
```
Source: "Findable content"          # I-addresses α₁..αₙ
Dest:   "Prefix: " + vcopy("Findable") → "Prefix: Findable"

Before delete:
  find_documents("Findable") → [Source, Dest]   # 2 documents

After delete("Findable" from Dest):
  retrieve(Dest) → "Prefix: "                   # content gone from V-stream
  find_documents("Findable") → [Source, Dest]    # still 2 documents
```

The document `Dest` no longer contains "Findable" in its V-stream, but the I-address association persists in the spanf index.

**Code references:** Test `find_documents_after_delete` in golden/discovery/. Related: `FC-CONTENT-SPANF-ISOLATION` from Finding 0018 (deletion from one doc doesn't affect other docs; this finding shows deletion doesn't even affect the *same* doc's findability).

**Provenance:** Finding 0023.
**Co-occurring entries:** [SS-DUAL-ENFILADE], [ST-DELETE]

---

### INV-LINK-PERMANENCE

**Sources:** Findings 0024, 0029, 0040

#### Finding 0024

**What happens:** Links are permanent objects — there is no DELETELINK operation in the FEBE protocol. Once created, a link exists forever. Deleting the content at a link's endpoints does not delete the link itself. Deleting all text from a link's home document does not affect the link. The link object persists independently of any content it references.

This is consistent with the broader Xanadu permanence model: I-addresses are permanent (INV-IADDRESS-PERMANENT), and links — which are indexed by I-address — inherit this permanence.

**Why it matters for spec:** Invariant: `∀ link ∈ links(system) :: once_created(link) ⟹ link ∈ links(system_future)` for all future states. The set of links in the system is monotonically growing. No operation in the system can remove a link. Combined with INV-IADDRESS-PERMANENT, this means the graph of links over content identities is append-only.

**Code references:** Test `link_permanence_no_delete_operation` (PASS). No DELETELINK opcode exists in the FEBE protocol.

**Provenance:** Finding 0024, Summary and Semantic Insight 1.

#### Finding 0029

**What happens:** Links are permanent objects. Even when a link cannot be discovered via `find_links()` because its endpoint content has been deleted, the link still exists and is directly accessible via its link ID. `follow_link(link_id, endpoint)` works for source, target, and type regardless of V-stream state.

**Why it matters for spec:** Core invariant of the Xanadu model — links cannot be deleted, only orphaned. This separates link existence (permanent, in the link's home document) from link discoverability (contingent on V-stream content). Formalizable as: `∀ link_id ∈ created_links : follow_link(link_id, LINK_SOURCE) succeeds ∧ follow_link(link_id, LINK_TARGET) succeeds ∧ follow_link(link_id, LINK_TYPE) succeeds`, regardless of any delete operations on endpoint documents.

**Code references:** Test `search_by_source_after_source_removed` in `febe/scenarios/links/search_endpoint_removal.py`.

**Concrete example:**
- `link_id = create_link(...)`
- Delete source content
- `find_links(source)` → `[]` (not discoverable)
- `follow_link(link_id, LINK_SOURCE)` → works
- `follow_link(link_id, LINK_TARGET)` → works
- `follow_link(link_id, LINK_TYPE)` → works

**Provenance:** Finding 0029, section 6

#### Finding 0040

**What happens:** Removing a link from a document's POOM via `DELETEVSPAN(2.x)` does NOT delete the link object. The link orgl persists at its I-address, remains discoverable via `find_links()` (because spanfilade DOCISPAN entries persist), and remains followable via `follow_link(link_id)` (because the link orgl is directly accessible by I-address). The permanence invariant holds at the I-space and spanfilade levels even though the POOM association is severed.

This qualifies the permanence invariant: link permanence means permanent existence and discoverability, not permanent association with a particular document's V-stream. A front end CAN call `DELETEVSPAN` to remove a link from a document — the backend does not prevent this — but the link itself survives.

**Why it matters for spec:** Refines the permanence invariant to distinguish layers: `∀ link ∈ created_links : link ∈ ispace(system) ∧ link ∈ spanfilade(system)` holds unconditionally across all operations. But `link ∈ poom(doc)` is mutable — DELETEVSPAN can remove it. The invariant `once_created(link) ⟹ link ∈ links(system_future)` holds for I-space and spanfilade but NOT for POOM containment.

**Code references:**
- Test `find_links_after` — confirms link discovery survives POOM removal
- Test `follow_link_after` — confirms direct access survives POOM removal

**Provenance:** Finding 0040, Link Persistence section and Architectural Implications section 1.

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-THREE-LAYER-MODEL], [PRE-DELETE], [PRE-FIND-LINKS], [ST-DELETE], [ST-FIND-LINKS], [FC-LINK-DELETE-ISOLATION], [FC-LINK-PERSISTENCE], [INT-TRANSCLUSION-LINK-SEARCH], [EC-ORPHANED-LINK], [EC-REVERSE-ORPHAN], [EC-SEARCH-SPEC-BEYOND-BOUNDS], [EC-TYPE-FILTER-NONFUNCTIONAL]

---

### INV-IDENTITY-OVERLAP

**Source:** Finding 0028

**What happens**: When transcluding overlapping regions from the same source, the overlapping characters in the destination share I-position identity with the corresponding source characters. Both copies of shared characters reference the same I-position, even though they appear at different V-positions.

**Why it matters for spec**: The identity-preservation invariant holds at character granularity even when transclusion regions overlap. Formally: if `vcopy(src, Span(a, len1), dst, P1)` and `vcopy(src, Span(b, len2), dst, P2)` where `[a, a+len1) ∩ [b, b+len2) ≠ ∅`, then for every position `c` in the overlap, `I(dst, P1 + (c-a)) == I(dst, P2 + (c-b)) == I(src, c)`. The enfilade correctly tracks that multiple V-positions can map to the same I-position.

**Code references**: Test `edgecases/overlapping_transclusions`

**Concrete example**:
```
Source doc: "ABCDEFGH"
Operation 1: vcopy(src, Span(1.1, 0.4), dst, end)  — copy "ABCD"
  dst = "ABCD"
Operation 2: vcopy(src, Span(1.3, 0.4), dst, end)  — copy "CDEF"
  dst = "ABCDCDEF"

Identity mapping:
  dst positions 1.3, 1.4 ("CD" from first copy) share I-positions with
  dst positions 1.5, 1.6 ("CD" from second copy) — both map to
  src positions 1.3, 1.4 ("CD" in source)
```

**Provenance**: Finding 0028 §3
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### INV-SINGLE-CHAR-GRANULARITY

**Sources:** Findings 0028, 0034

#### Finding 0028

**What happens**: All core operations work at single-character granularity with no special cases. Specifically: insert of one character succeeds; delete of one character (at first, middle, or last position) succeeds; vcopy of one character succeeds and maintains I-position identity; pivot of two single characters succeeds (swaps their positions). There is no minimum span width greater than one character for any operation.

**Why it matters for spec**: Operation preconditions need no minimum-length constraint beyond `length >= 1` (or `length >= 0` for queries — see below). The spec should define operations over arbitrary non-empty spans without special-casing single-character inputs. This confirms that the enfilade and all orgl operations handle the degenerate single-character case correctly.

**Code references**: Tests `edgecases/single_character_insert`, `edgecases/single_character_delete`, `edgecases/single_character_vcopy`, `edgecases/single_character_pivot`

**Provenance**: Finding 0028 §4

#### Finding 0034

**Detail level:** Essential

The granularity of all address operations is the single byte, not the character. Each byte position in content receives exactly one I-space address. V-space positions correspond 1:1 with bytes. This is an invariant: no operation in the system aggregates bytes into multi-byte units.

**Why it matters for spec:** The invariant `forall content c, vspan_width(c) == byte_length(c)` holds unconditionally. The formal model must use byte indexing, not character indexing. Operations like partial retrieval, deletion, and link endpoint addressing all resolve to individual byte positions. No character-boundary-aware operation exists in the backend.

**Concrete example:**
- Content "caf\xc3\xa9" has byte_length = 5 and vspan_width = 5
- Byte at position 4 is `\xc3`, byte at position 5 is `\xa9` — each has its own I-address
- These are the two bytes of a single UTF-8 character, but the system treats them as independent units

**Provenance:** Finding 0034

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-CONTENT-IDENTITY], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [INT-TRANSCLUSION], [EC-ENCODING-BOUNDARY-SPLIT], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### INV-VSPAN-CONSOLIDATION

**Source:** Finding 0028

**What happens**: The enfilade consolidates logically contiguous V-space regions into a single span regardless of insertion history. After 100 separate single-character inserts (A, B, C, ...), `retrieve_vspanset` returns `span_count: 1` — a single contiguous span covering all content. Fragmented inserts do not produce fragmented span representations.

**Why it matters for spec**: An invariant of the enfilade data structure: `forall doc : Document :: contiguous_vrange(doc) => vspanset(doc).size == 1`. More generally, the span representation returned by `retrieve_vspanset` is always maximally consolidated — adjacent spans with consecutive V-positions are merged. This is a representation invariant, not a behavioral one: the logical content is the same either way, but the enfilade guarantees minimal span decomposition. For formal verification, this means span-count assertions can be used as oracles for contiguity.

**Code references**: Test `edgecases/many_single_inserts`

**Concrete example**:
```
100 sequential inserts: insert("A"), insert("B"), ..., insert("Z"), insert("A"), ...
retrieve_vspanset(doc) → {Span(1.1, 0.100)}  — single span, not 100 fragments
```

**Provenance**: Finding 0028 §6
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### INV-IADDR-IMMUTABILITY

**Sources:** Findings 0030, 0031, 0064

#### Finding 0030

**What happens**: I-addresses, once assigned to content, never change. INSERT shifts V-addresses but preserves every existing I-address assignment. Content "C" that had I-address I.3 before insertion still has I-address I.3 after insertion, even though its V-address moved from 1.3 to 1.5. This holds for all content in the document, regardless of position relative to the insertion point.

**Why it matters for spec**: This is the core immutability invariant for the identity layer: `forall content c, operation op :: iaddr(c, before(op)) == iaddr(c, after(op))`. No operation in the system reassigns or destroys an I-address. This is what makes cross-document identity (transclusion) and version comparison possible — both depend on I-addresses being stable reference points. This invariant should be asserted universally across all state transitions, not just INSERT.

**Code references**: `insert_vspace_mapping.py` — `compare_versions` output confirms I-address stability by showing before/after V-span pairs that share identity

**Provenance**: Finding 0030

#### Finding 0031

**What happens:** `tumblerintdiff` extracts the integer value from a tumbler width, but only when the width is "flat" (no hierarchical structure). This is used in `insertpm` (`orglinks.c:116-117`) to convert a tumbler width back to an integer count. The permascroll is append-only: text characters occupy contiguous I-addresses, and these allocations are permanent.

**Why it matters for spec:** Confirms that I-address allocation is monotonic and append-only. The `tumblerintdiff` function acts as a witness that text widths are always flat integers at the implementation level, supporting the invariant that text content occupies exactly one I-address per character with no gaps.

**Code references:** `orglinks.c:116-117` (`tumblerintdiff` and `tumblerincrement` in `insertpm`).

**Provenance:** Finding 0031

#### Finding 0064

**What happens**: I-addresses, once allocated in the granfilade, are permanent and immutable. The granfilade is append-only — `inserttextingranf` always allocates fresh addresses at the end. There is no mechanism to reuse, reassign, or deallocate I-addresses. DELETE frees the POOM bottom crums that *reference* I-addresses, but the I-addresses themselves persist in the granfilade unconditionally.

This means: (1) the set of allocated I-addresses grows monotonically, (2) the content associated with any I-address never changes, and (3) no operation can cause two distinct I-addresses to become identical or one I-address to refer to different content over time.

**Why it matters for spec**: Strengthens the immutability invariant with granfilade-level evidence. The invariant is: `∀ i, t₁ < t₂ : i ∈ granfilade(t₁) ⟹ i ∈ granfilade(t₂) ∧ content(i, t₁) = content(i, t₂)`. No operation in the system — including DELETE — can remove an I-address from existence. DELETE only severs one document's *reference* to an I-address.

**Code references**:
- `backend/do1.c:27-43` — `doinsert`: calls `inserttextingranf` (append-only allocation)
- `backend/edit.c:76-84` — `deletend`: frees POOM nodes, not granfilade entries

**Provenance**: Finding 0064

**Co-occurring entries:** [SS-INTERVAL-CMP], [SS-SPAN], [SS-TUMBLER], [ST-COPY], [ST-DELETE], [ST-INSERT], [FC-DELETE-CROSS-DOC], [FC-INSERT-IADDR], [INV-DELETE-NOT-INVERSE], [INV-TUMBLER-TOTAL-ORDER], [INT-LINK-INSERT], [INT-TRANSCLUSION]

---

### INV-TUMBLER-TOTAL-ORDER

**Source:** Finding 0031

**What happens:** `tumblercmp` defines a total order over tumblers. Comparison proceeds: (1) check for zero tumblers, (2) compare signs, (3) compare absolute values via `abscmp`. `abscmp` first compares exponents — a larger exponent means a larger absolute value — then compares mantissa digits lexicographically left-to-right. The result is always `LESS`, `EQUAL`, or `GREATER`.

**Why it matters for spec:** The total order on tumblers is a foundational invariant. All interval checks, span containment tests, and enfilade traversals depend on this ordering being total, antisymmetric, and transitive. The ordering is lexicographic after exponent alignment, which means the zero-separator hierarchy is respected: `1.1.0.2` < `1.1.0.2.0.1` because the shorter tumbler has trailing zeros that are less than the non-zero continuation.

**Code references:** `tumble.c:72-85` (`tumblercmp`), `tumble.c:87-111` (`abscmp`).

**Concrete example:**
- `tumblercmp(1.1.0.2, 1.1.0.2.0.1)` → `LESS` (trailing zeros vs non-zero digits)
- `tumblercmp(zero, any_positive)` → `LESS`
- `tumblercmp(negative, positive)` → `LESS`

**Provenance:** Finding 0031
**Co-occurring entries:** [SS-INTERVAL-CMP], [SS-SPAN], [SS-TUMBLER], [ST-INSERT], [INV-IADDR-IMMUTABILITY]

---

### INV-ATOMICITY

**Sources:** Findings 0032, 0042

#### Finding 0032

**What happens:** CREATENEWVERSION is atomic — the new document and its content appear together. There is no window where the version document exists without its content. This follows from the implementation: `docreatenewversion` creates the orgl, retrieves the source vspanset, and copies content in a single request handler invocation before returning the new address.

**Why it matters for spec:** The spec should model version-create as an atomic state transition: `state' = state[new_addr -> copy_refs(state[source_addr])]`. The two-step alternative (CREATEDOCUMENT then COPY) does NOT have this atomicity — the intermediate state with an empty document is observable. This matters for any invariant that depends on document non-emptiness or content-presence after creation.

**Code references:** `backend/do1.c:docreatenewversion` — single function, no intermediate return points between orgl creation and content copy.

**Provenance:** Finding 0032

#### Finding 0042

**What happens:** The `bed.c` event loop processes each FEBE operation atomically via run-to-completion scheduling. The `xanadu(&task)` call executes the entire operation — request parsing, state mutation, response sending, and memory cleanup — before returning to `select()`. Multi-step operations like INSERT (which involves I-address allocation, granfilade insertion, spanfilade update, and POOM update) execute as a single uninterruptible unit. There are no threads, no state-modifying signal handlers, and no preemption.

**Why it matters for spec:** This is the foundational atomicity invariant: every operation's view of shared state (ispace, spanfilade, POOMs) is consistent throughout execution. No interleaving is possible. This means all state transitions documented in other findings are truly atomic — there is no partial-execution state observable by any frontend. Any formal spec can model operations as atomic transitions without reasoning about interleavings.

**Code references:**
- `backend/bed.c:103-150` — main event loop with `select()` and sequential `xanadu()` dispatch
- `backend/bed.c:153-172` — `xanadu()` function: `getrequest` -> `requestfns[request]` -> `sendresultoutput` -> `tfree`

**Concrete example:**
- Before: Two frontends (FE1, FE2) both have pending INSERT requests ready on their file descriptors
- During: `select()` returns with both FDs ready. The loop iterates: FE1's INSERT runs to completion (all four internal steps: allocate I-address, insert text, insert DOCISPAN, update POOM), response sent. Then FE2's INSERT runs to completion. No interleaving occurs.
- After: Both INSERTs have executed sequentially; each saw a consistent snapshot of state.

**Provenance:** Finding 0042

**Co-occurring entries:** [SS-VERSION-ADDRESS], [PRE-INSERT], [ST-VERSION-CREATE], [INV-SEQUENTIAL-DISPATCH], [INT-LINK-VERSION], [INT-VERSION-TRANSCLUSION]

---

### INV-MONOTONIC

**Sources:** Findings 0033, 0061, 0063, 0065, 0068, 0077

#### Finding 0033

**What happens:** I-address allocation is strictly monotonically increasing within a document. Each new text insert receives an I-address exactly 1 greater than the previous allocation, regardless of where the content is inserted in V-space. This is an invariant of the insert operation.

**Why it matters for spec:** Formalizable as: for any two inserts where insert_A happens before insert_B chronologically, `i_address(insert_B) > i_address(insert_A)`. This is a global invariant on the I-space — it can never decrease or have gaps under normal sequential insertion.

**Code references:** `findisatoinsertmolecule` in `backend/green/granf2.c` — `tumblerincrement(&lowerbound, 0, 1, isaptr)`.

**Provenance:** Finding 0033

#### Finding 0061

**What happens:** I-address allocation is strictly monotonically increasing and completely unaffected by DELETE or REARRANGE operations. Since DELETE modifies only the spanfilade (V-to-I mappings via `deletevspanpm`) and never touches the granfilade, deleted content's I-addresses remain in the granfilade tree and continue to influence allocation. Interleaved INSERT-DELETE-INSERT sequences produce contiguous, gap-free I-address sequences: INSERT "AAA" allocates I.1–I.3, DELETE removes a character (V-space only), INSERT "BBB" allocates I.4–I.6 (not reusing I.2).

**Why it matters for spec:** Strengthens the monotonic invariant: `∀ alloc_a, alloc_b : time(alloc_a) < time(alloc_b) ⟹ iaddr(alloc_b) > iaddr(alloc_a)`, and this holds regardless of intervening DELETE or REARRANGE operations. No operation in the system can cause an I-address to be freed or reused. Formally: `∀ op ∈ {DELETE, REARRANGE} : granf_state_after(op) = granf_state_before(op)`. The monotonic invariant is unconditional — it holds across all operation interleavings.

**Code references:** `findisatoinsertmolecule` in `backend/granf2.c:158-181` — allocation by query-and-increment. `deletevspanpm` in `backend/edit.c` — DELETE modifies spanfilade only. `insertseq` in `backend/insert.c:17-70` — inserts content at allocated I-address.

**Concrete example:**
```
INSERT "AAA" → allocates I.1, I.2, I.3; V-span width 0.3
DELETE pos 1.2 → V-span shrinks to 0.2; granfilade still has I.1, I.2, I.3
INSERT "BBB" → allocates I.4, I.5, I.6 (NOT reusing I.2); V-span width 0.5
DELETE pos 1.3-1.4 → V-span shrinks to 0.3; granfilade has I.1–I.6
INSERT "CCC" → allocates I.7, I.8, I.9; V-span width 0.6
```
Each INSERT always continues from the granfilade maximum, never filling gaps.

**Provenance:** Finding 0061

#### Finding 0063

**What happens:** The monotonic I-address invariant holds across CREATELINK: all allocations (text and non-text) draw from the same monotonically increasing sequence. CREATELINK does not violate monotonicity — it consumes I-address space in the same forward-only manner as INSERT. However, because link orgls and text characters share the same allocation sequence, CREATELINK introduces non-contiguity in the *text-only* I-address subsequence. The overall sequence remains monotonic: text I.1–I.3, link orgl at ~I.2.0, text at I.2.1+.

This refines the invariant from Finding 0061: `∀ op ∈ {DELETE, REARRANGE} : granf_state_after(op) = granf_state_before(op)` holds, but CREATELINK is NOT in this set. CREATELINK, like INSERT, adds entries to the granfilade. The granfilade growth set is `{INSERT, COPY, CREATELINK}`, not just `{INSERT, COPY}`.

**Why it matters for spec:** The monotonic invariant `∀ alloc_a, alloc_b : time(a) < time(b) ⟹ iaddr(b) > iaddr(a)` remains valid but must be understood as spanning ALL entity types. The spec should distinguish: (1) the global monotonic invariant (holds for all allocations), (2) text-contiguity (holds only when no non-text allocation intervenes). Formally: `text_contiguous(insert_a, insert_b) ⟺ ¬∃ alloc_c : time(a) < time(c) < time(b) ∧ type(c) ≠ TEXT`.

**Code references:**
- `granf2.c:158-181` — `findisatoinsertmolecule` for text (molecules)
- `granf2.c:130-157` — `findisatoinsertnonmolecule` for non-text entities (link orgls) — same tree, same allocation logic

**Provenance:** Finding 0063

#### Finding 0065

**Detail level: Essential**

Link I-address allocation within a document is strictly monotonically increasing. Each MAKELINK on document D produces an I-address greater than all previous link I-addresses in D. This holds independently per document — interleaving MAKELINK calls across documents does not break monotonicity within any single document.

**Why it matters for spec:** Strengthens the monotonicity invariant: it holds per-(document, element_field) partition, not just globally. The invariant is `forall d: Document, forall l1 l2: Link | l1 created before l2 in d => iaddr(l1) < iaddr(l2)`.

**Concrete example:**
- MAKELINK(docA) → `docA.2.1`
- MAKELINK(docB) → `docB.2.1`
- MAKELINK(docA) → `docA.2.2` (monotonic within A despite intervening B operation)

**Code references:**
- `backend/granf2.c:174` — `tumblerincrement(&lowerbound, 0, 1, isaptr)` guarantees increment from highest existing

**Provenance:** Finding 0065

#### Finding 0068

**What happens:** Version address allocation is monotonically increasing within each document's version namespace, using the same mechanism as I-address allocation. Deleting a version does not free its address — the granfilade retains all allocated addresses permanently. The sequence `.1`, `.2`, `.3` under a document never reuses a previously allocated version address.

**Why it matters for spec:** Extends INV-MONOTONIC from Finding 0061 to document-level allocation: `∀ version_alloc_a, version_alloc_b under doc D : time(a) < time(b) ⟹ addr(b) > addr(a)`. Combined with INV-NO-IADDR-REUSE, version addresses are permanent and gap-free within each document's child namespace.

**Code references:** `granf2.c:203-242` — same `findisatoinsertnonmolecule` as element allocation; queries granfilade maximum and increments.

**Concrete example:**
- Create version of `1.1.0.1.0.1` → `1.1.0.1.0.1.1`
- Delete `1.1.0.1.0.1.1`
- Create another version → `1.1.0.1.0.1.2` (not `.1` reused)

**Provenance:** Finding 0068

#### Finding 0077

**What happens:** CREATENEWVERSION does NOT break I-address contiguity for subsequent text INSERTs. Unlike CREATELINK (Finding 0063), which allocates a link orgl in the content region of the granfilade and disrupts text I-address contiguity, VERSION allocates only a document address in a separate tumbler range. The content allocation counter is unaffected.

Test evidence: INSERT "ABC" → CREATENEWVERSION → INSERT "XYZ" yields 1 shared span pair covering all 6 characters with contiguous I-addresses. Contrast with INSERT "ABC" → CREATELINK → INSERT "XYZ" which yields 2 shared span pairs (gap from link orgl).

**Why it matters for spec:** Refines the contiguity-breaking predicate from Finding 0063: `text_contiguous(insert_a, insert_b) ⟺ ¬∃ alloc_c : time(a) < time(c) < time(b) ∧ alloc_c ∈ content_allocations`. CREATENEWVERSION is NOT a content allocation, so it does not break contiguity. The set of contiguity-breaking operations is `{INSERT, CREATELINK}` (operations that call `findisatoinsertmolecule` or `findisatoinsertgr` for content), not `{INSERT, CREATELINK, VERSION}`.

**Code references:** `docreatenewversion` in `backend/do1.c:260-299` — no call to `findisatoinsertgr` for content. Contrast with `docreatelink` in `backend/do1.c:199-225` — calls `createorglingranf` for content (link orgl).

**Concrete example:**
```
INSERT "ABC"        → I.1, I.2, I.3
CREATENEWVERSION    → doc address allocated (separate range), content counter unchanged
INSERT "XYZ"        → I.4, I.5, I.6 (contiguous with ABC)
compare_versions    → 1 shared span pair, combined I-span width 0.6

vs.

INSERT "ABC"        → I.1, I.2, I.3
CREATELINK          → link orgl at ~I.2.0 (content range), content counter advanced
INSERT "DEF"        → I.2.1+ (non-contiguous with ABC)
compare_versions    → 2 shared span pairs (gap)
```

**Provenance:** Finding 0077

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-VERSION-ADDRESS], [PRE-VERSION-OWNERSHIP], [ST-ADDRESS-ALLOC], [ST-INSERT], [ST-VERSION], [FC-DOC-ISOLATION], [FC-GRANF-ON-DELETE], [FC-GRANF-ON-VERSION], [INV-CRUM-BOUND], [INV-NO-IADDR-REUSE], [INT-LINK-INSERT]

---

### INV-LINK-IDENTITY-DISCOVERY

**Source:** Finding 0039

**What happens:** Links bound to an I-address are discoverable from ALL V-positions that reference that I-address, including multiple positions within the same document created by internal transclusion. When a link is created on the first occurrence of content (V=1.10), `find_links` on the second occurrence (V=1.19) returns the same link. This is because link discovery operates in I-space: `find_links` converts the query V-span to I-spans, then searches the spanf index by I-address. Since both V-positions map to the same I-address, both resolve to the same link.

**Why it matters for spec:** This confirms the invariant: `forall v1 v2 : VPos, doc : Doc :: iaddrs(doc, v1) = iaddrs(doc, v2) ==> findlinks(doc, v1) = findlinks(doc, v2)`. Link discovery is a function of content identity, not position. The formal spec should state that `findlinks` factors through I-space: `findlinks(doc, vspan) = findlinks_by_iaddr(vspan2ispan(doc, vspan))`. This is the same INV-LINK-GLOBAL-VISIBILITY from Finding 0008, applied to the special case of intra-document sharing.

**Concrete example:**
```
doc has "text" at V 1.10 and V 1.19, both referencing I-addresses i₁..i₄
create_link(from=V 1.10..1.13) → link_id

find_links(from=V 1.10..1.13) → [link_id]  (direct: link on this position)
find_links(from=V 1.19..1.22) → [link_id]  (indirect: same I-addresses)
```

**Code references:** Test `internal/internal_transclusion_with_link`

**Provenance:** Finding 0039
**Co-occurring entries:** [SS-POOM-MULTIMAP], [ST-VCOPY], [EC-SELF-TRANSCLUSION]

---

### INV-ENFILADE-CONFLUENCE

**Source:** Finding 0041

The permanent layer is logically confluent under concurrent additions: if operations O1 and O2 independently add entries E1 and E2 to the permanent layer, the queryable content is independent of execution order. Formally: `add(add(sigma, E1), E2)` and `add(add(sigma, E2), E1)` produce the same set of I-address mappings and the same results for `retrieve` and `retrieveinspan` queries.

This confluence holds at the abstraction boundary (query results) but NOT at the physical level (tree shape, sibling ordering, split points differ based on insertion order).

**Why it matters for spec:** This is a key commutativity invariant for the permanent layer. It means the spec can model permanent layer additions as set union without worrying about ordering. It also means serialization strategy for concurrent access is a correctness concern only for structural integrity, not for logical content.

**Concrete example:**
Inserting A then B at I-address `1.1.0.1.0.1`:
- Before: empty enfilade
- After (A then B): `{1.1.0.1.0.1 -> A, 1.1.0.1.0.1 -> B}`, tree has Crum_A as left sibling of Crum_B
- After (B then A): `{1.1.0.1.0.1 -> A, 1.1.0.1.0.1 -> B}`, tree has Crum_B as left sibling of Crum_A
- Query results: identical in both cases

**Code references:**
- `backend/insert.c:43-46` — insertion always as RIGHTBRO determines physical ordering
- `backend/retrie.c:167-188` — retrieval walks left-to-right but returns same logical content regardless of tree shape

**Provenance:** Finding 0041
**Co-occurring entries:** [SS-DUAL-ENFILADE], [PRE-CONCURRENT-INSERT], [FC-ENFILADE-QUERY-INDEPENDENCE]

---

### INV-SEQUENTIAL-DISPATCH

**Source:** Finding 0042

**What happens:** Even when multiple frontends have requests ready simultaneously (multiple FDs set in `select()`'s result), the event loop processes them strictly sequentially by iterating over file descriptors in order. Frontend i's request completes entirely before frontend i+1's request begins.

**Why it matters for spec:** The system's concurrency model is total serialization. For specification purposes, the system behaves as if there is a single global operation queue. This is stronger than per-document serialization — it means cross-document operations are also serialized. Any linearizability argument is trivially satisfied.

**Code references:**
- `backend/bed.c:118-128` — sequential iteration over ready FDs with blocking `xanadu(&task)` per iteration

**Provenance:** Finding 0042
**Co-occurring entries:** [PRE-INSERT], [INV-ATOMICITY]

---

### INV-IADDR-PROVENANCE

**Source:** Finding 0046

**What happens:** Every I-address has exactly one native document — the document where INSERT first allocated it. COPY does not allocate new I-addresses; it creates V→I mappings that reference existing ones. The `homedoc` field in each POOM crum records the I-address origin document, not the document from which content was most recently copied. This means provenance (which document originally created the content) is permanently encoded in the I-address itself and is not affected by subsequent COPY operations.

**Why it matters for spec:** This is a system-wide invariant: `forall i : IAddress :: |{ d : Doc | is_native(d, i) }| = 1`. Each I-address has a unique native document. The compensation function (mapping any I-address to its origin) is total. INSERT allocates fresh I-addresses under the target document; COPY references existing ones. Provenance tracking requires I-address inspection — from V-addresses alone, INSERT and COPY produce indistinguishable POOM structures.

**Code references:**
- `insertnd.c:293-301` — `isanextensionnd()` checks `homedoc` to verify I-address origin
- `do1.c:45-65` — `docopy()` references existing I-addresses
- INSERT allocates fresh I-addresses under target document's address space

**Concrete example:**
```
doc_A: INSERT "hello" → allocates I-addresses i₁..i₅ (native to doc_A)
doc_B: COPY from doc_A → maps V-positions to i₁..i₅ (native to doc_A, not doc_B)
doc_C: COPY from doc_B → maps V-positions to i₁..i₅ (still native to doc_A)

is_native(doc_A, i₁) = true
is_native(doc_B, i₁) = false  (doc_B only references i₁)
is_native(doc_C, i₁) = false  (doc_C only references i₁)
```

**Provenance:** Finding 0046
**Co-occurring entries:** [PRE-COPY], [ST-VCOPY], [ST-VERSION-CREATE], [INT-LINK-VERSION]

---

### INV-SPANF-GROWTH

**Source:** Finding 0047

**What happens:** The spanfilade (DOCISPAN portion) grows with the number of distinct content placements, not total byte count. The storage model is `S(t) = Σ |ispanset placed into doc d|` across all INSERT and COPY operations up to time t. This is because each operation creates entries proportional to the number of I-spans, not the number of bytes per I-span.

**Why it matters for spec:** This is a complexity invariant on the spanfilade data structure. It bounds the growth rate: `|DOCISPAN| ≤ Σ_{all INSERT/COPY ops} |ispanset(op)|`. For a system with N insert/copy operations each on contiguous content, `|DOCISPAN| ≤ N`. This rules out pathological O(total_bytes) growth and means the spanfilade size tracks editorial activity, not content volume.

**Code references:**
- `spanf1.c:38-48` — one `insertnd` per I-span, not per byte
- Finding references EWD-031 (The Storage Problem) as confirming this storage model

**Provenance:** Finding 0047
**Co-occurring entries:** [SS-DOCISPAN], [ST-COPY], [ST-INSERT]

---

### INV-ITOV-FILTERING

**Source:** Finding 0048

**What happens:** Both FOLLOWLINK and RETRIEVEENDSETS share the same I-to-V conversion path that silently filters unreferenced I-addresses. The mechanism is identical: `linksporglset2specset()` calls `sporglset2vspanset()` which calls `ispan2vspanset()` → `permute()` → `span2spanset()`. At `span2spanset()`, `retrieverestricted()` searches the target document's POOM for the I-address. If not found (returns NULL), the I-address is dropped from the result without error.

**Why it matters for spec:** This is a universal invariant of all operations that convert I-addresses to V-addresses: **unreferenced I-addresses are silently excluded from V-address results**. No operation that performs I-to-V conversion will ever return a V-address for an unreferenced I-address. This is not operation-specific behavior but a property of the conversion layer itself. Formally: `∀ op returning V-addresses: v ∈ result(op) → ∃ d, i : poom.d(v) = i ∧ i ∈ dom.ispace`.

**Code references:**
- Common path: `sporglset2vspanset()` in `backend/sporgl.c` → `span2spanset()` in `backend/orglinks.c:425-449`
- FOLLOWLINK uses this via `linksporglset2specset()`: `backend/sporgl.c:97+`
- RETRIEVEENDSETS uses same via `linksporglset2specset()`: `backend/spanf1.c:190-235`

**Provenance:** Finding 0048 (sections on call chain and comparison), Finding 0035
**Co-occurring entries:** [PRE-FOLLOWLINK], [ST-FOLLOWLINK], [EC-GHOST-LINK]

---

### INV-POOM-BIJECTIVITY

**Source:** Finding 0053

**What happens:** The POOM is designed to maintain a bijection between V-addresses and I-addresses (EWD-018 invariant I₁: `poom_d` is a bijection). DELETE can violate this invariant by creating POOM entries with negative V-positions. A negative V-position is in the domain of the stored POOM map but does not correspond to any valid V-address in the document's V-stream (which is defined over non-negative tumblers only). The entry occupies tree space and has a valid I-address target, but its V-address key is outside the legal V-space.

The system allows these I₁ violations to persist — there is no integrity check or cleanup mechanism. The violations are silent: no error is raised, and the entries are simply unreachable by any V-space query.

**Why it matters for spec:** Invariant I₁ as written (`poom_d` is a bijection from V-addresses to I-addresses) does not hold after certain DELETE sequences. The formal spec must either: (a) strengthen the DELETE precondition to prevent negative V-positions, or (b) weaken I₁ to: `poom_d restricted to non-negative V-addresses is a bijection`. Option (b) matches the actual implementation. The negative-position entries are effectively dead state — formally present but operationally unreachable.

**Code references:**
- `edit.c:63` — the subtraction that can violate I₁
- `tumble.c:72-85` — comparison semantics that make negative entries unreachable

**Provenance:** Finding 0053
**Co-occurring entries:** [SS-TUMBLER], [PRE-DELETE], [ST-DELETE], [EC-DEEPLY-ORPHANED-LINK]

---

### INV-SPANF-WRITE-ONLY

**Sources:** Findings 0057, 0067

#### Finding 0057

**What happens:** The spanfilade is a write-only (append-only) index. Entries are added by `insertspanf` during COPY and INSERT operations, but no deletion function exists anywhere in the spanf codebase. Inspection of `spanf1.c` and `spanf2.c` reveals `insertspanf`, `findlinksfromtothreesp`, `retrieveendsetsfromspanf`, `finddocscontainingsp`, and `findnumoflinksfromtothreesp` — all insertion and query functions. No `deletespanf`, `removespanf`, or any removal mechanism exists. This applies to both DOCISPAN entries (content indexing) and link endset entries (link indexing).

**Why it matters for spec:** This is a structural invariant of the spanfilade: `∀ t₁ < t₂ : spanf_entries(t₁) ⊆ spanf_entries(t₂)`. The set of spanfilade entries is monotonically non-decreasing. No operation in the system can remove a spanfilade entry. This means the spanfilade is not a current-state index but a historical journal of all content placements that have ever occurred. Combined with INV-SPANF-GROWTH (Finding 0047), the growth bound becomes permanent: every DOCISPAN entry ever created persists indefinitely.

**Code references:**
- `backend/spanf1.c` — `insertspanf` exists; no delete function exists in entire file
- `backend/spanf2.c` — query functions only; no delete function exists in entire file
- `backend/do1.c:162-171` — `dodeletevspan` has no call to any spanf removal function

**Provenance:** Finding 0057

#### Finding 0067

**What happens:** Finding 0067 confirms that neither `insertnd` nor `deletend` calls any spanfilade update function. The DELETE path (`dodeletevspan` → `deletevspanpm` → `deletend`) modifies only the document's POOM in granf. No `deletespanf` function exists. Stale spanfilade entries accumulate after DELETE but do not corrupt queries — FIND_DOCUMENTS returns a superset, and I→V conversion filters stale entries at query time.

**Why it matters for spec:** Reinforces the monotonicity invariant `∀ t₁ < t₂ : spanf_entries(t₁) ⊆ spanf_entries(t₂)` from Finding 0057. Critically, stale spanfilade entries do NOT violate F0 because: (1) they do not modify other documents, (2) they do not corrupt query correctness (filtering at I→V conversion), (3) the target document's POOM is correctly updated. The spec should model spanf staleness as an acceptable weakening: `actual_docs(i) ⊆ find_documents(i)`.

**Code references:**
- `do1.c:162-171` — `dodeletevspan` has no spanf call
- `orglinks.c:144-151` — `deletevspanpm` calls only `deletend` + `logbertmodified`

**Provenance:** Finding 0067 (confirming Finding 0057)

**Co-occurring entries:** [ST-DELETE], [FC-DOC-ISOLATION], [FC-SUBSPACE], [INT-DELETE-SPANF-DIVERGENCE], [EC-GHOST-LINK-ENDPOINT], [EC-STALE-SPANF-REFERENCE]

---

### INV-ENFILADE-MINIMALITY

**Sources:** Findings 0058, 0060

#### Finding 0058

**What happens:** The enfilade design (per EWD-006) calls for tree minimality: the tree should be as shallow as possible, with no unnecessary intermediate nodes. `levelpull` was intended to enforce this by collapsing the tree when the fullcrum has only one child and height > 1. The commented-out code in `genf.c:318-342` shows the algorithm: check `numberofsons > 1` (if so, no pull needed), check `height <= 1` (if so, already minimal), then disown the single child, decrement height, transfer grandchildren up, and free the former child.

Because `levelpull` is disabled, minimality is violated after any delete-everything operation. The tree retains whatever height it reached during content growth, even when all content is removed.

**Why it matters for spec:** The formal spec should NOT assert tree minimality as an invariant — the implementation violates it. Instead, the spec should note: (a) `levelpush` ensures height is sufficient for the current fan-out, (b) `levelpull` (tree height reduction) is not implemented, (c) the actual invariant is: `enf.height ≥ 1` (lower bound only, no upper bound tightness guarantee). The intended invariant `enf.height = min_height(content)` does not hold. This is relevant for any bounded-model checking (Alloy) that models tree structure — the height dimension is monotonic, not minimal.

**Code references:**
- `backend/genf.c:318-342` — `levelpull`: commented-out collapse algorithm, function returns 0
- `backend/genf.c:263-294` — `levelpush`: the only height-changing operation (increment only)
- `backend/recombine.c:136-137` — `recombinend` calls `levelpull` on apex (but it's a no-op)

**Provenance:** Finding 0058

#### Finding 0060

**What happens:** The EN-4 invariant (non-root internal nodes must have `2 ≤ #children ≤ M`) is violated for height-1 non-root nodes in the granfilade. Because `M_b = 1`, the constraint `2 ≤ #children ≤ 1` is unsatisfiable. After `levelpush` + `splitcrumseq`, height-1 non-root nodes have exactly 1 child each — they are created this way and remain this way. No mechanism corrects this: `levelpull` is disabled (returns 0 immediately).

The actual invariant for the granfilade differs by node position:
- **Root (fullcrum):** `1 ≤ #children` (no upper bound enforced at root)
- **Height > 1 non-root:** `⌈M_u/2⌉ ≤ #children ≤ M_u` (standard B-tree, M_u = 6)
- **Height == 1 non-root:** `#children = 1` (always exactly one bottom crum)

The POOM and SPAN enfilades do NOT exhibit this violation because `M_b = 4` permits 2-4 children at height-1, satisfying EN-4.

**Why it matters for spec:** The formal EN-4 constraint must be conditioned on enfilade type. For GRAN enfilades, height-1 non-root nodes are exempt from the lower bound. The spec invariant should be:
```
∀ node ∈ internal_nodes(enf) :
  ¬is_root(node) ⟹
    if enf.type = GRAN ∧ node.height = 1 then
      node.#children = 1
    else
      2 ≤ node.#children ≤ M(node.height, enf.type)
```
Any Alloy bounded-model check or Dafny verification asserting a uniform `2 ≤ #children` for all non-root internal nodes will produce spurious counterexamples for the granfilade.

**Code references:**
- `backend/split.c:16-44` — `splitcrumupwards`: checks `isfullcrum`, calls `levelpush` then `splitcrum`
- `backend/split.c:70-93` — `splitcrumseq`: creates sibling, moves `numberofsons/2` children
- `backend/genf.c:263-294` — `levelpush`: increments fullcrum height, creates single-child intermediate
- `backend/genf.c:318-342` — `levelpull`: disabled, returns 0

**Concrete example:**
```
Before: insert 2nd bottom crum into granfilade
  Fullcrum (height=1, numberofsons=2)
    ├─ Bottom crum A (height=0)
    └─ Bottom crum B (height=0)

  toomanysons(fullcrum) → 2 > 1 → TRUE
  isfullcrum → TRUE → levelpush + splitcrum

After levelpush:
  Fullcrum (height=2, numberofsons=1)
    └─ Node1 (height=1, numberofsons=2)
         ├─ Bottom crum A
         └─ Bottom crum B

After splitcrum(Node1):
  Fullcrum (height=2, numberofsons=2)
    ├─ Node1 (height=1, numberofsons=1)   ← non-root, 1 child (violates strict EN-4)
    │    └─ Bottom crum A
    └─ Node2 (height=1, numberofsons=1)   ← non-root, 1 child (violates strict EN-4)
         └─ Bottom crum B
```

**Provenance:** Finding 0060

**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-DELETE], [ST-INSERT], [EC-EMPTY-DOC], [EC-GRAN-MB-ONE]

---

### INV-DURABILITY-BOUNDARY

**Source:** Finding 0059

**What happens:** Durability guarantees depend on session lifecycle, not on individual operations:

1. **On clean session exit:** `writeenfilades()` recursively writes all modified crums from both granfilade and spanfilade to disk. This is called from `bed.c:134` during daemon shutdown.
2. **On crash/kill:** Only crums previously evicted by the grim reaper survive. Recent INSERTs still in cache are lost.
3. **No fsync:** `write()` syscalls go to OS buffers; no explicit `fsync()` guarantees.
4. **No transaction log:** Within-session consistency comes from the in-memory cache, not from disk state.

**Why it matters for spec:** A formal specification must distinguish between "operation completed" (in-memory postcondition holds) and "operation is durable" (survives crash). The system provides session-level durability (all-or-nothing at session boundary), not operation-level durability. This is the key durability invariant: `writeenfilades() → ∀ modified crums c: c is on disk`. But absent `writeenfilades()`, durability is best-effort via grim reaper eviction.

**Code references:**
- `backend/corediskout.c:68-88` — `writeenfilades()` writes granf and spanf roots
- `backend/bed.c:134,183` — daemon exit calls `writeenfilades(); closediskfile()`
- `backend/disk.c:300-338` — `actuallywriteloaf` does synchronous `write()` with no `fsync`

**Concrete example:**
```
Session timeline:
  t0: INSERT("hello") → crum in RAM, modified=TRUE
  t1: RETRIEVE → "hello" (from cache) ✓
  t2: [crash]
  t3: restart, RETRIEVE → fails (crum never written to disk)

vs.

  t0: INSERT("hello") → crum in RAM, modified=TRUE
  t1: RETRIEVE → "hello" (from cache) ✓
  t2: clean exit → writeenfilades() flushes to disk
  t3: restart, RETRIEVE → "hello" ✓
```

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-CACHE-MECHANISM], [SS-UNIFIED-STORAGE], [ST-INSERT], [EC-CRASH-MID-WRITE], [EC-CROSS-ENFILADE-EVICTION], [EC-NO-STARTUP-VALIDATION]

---

### INV-NO-IADDR-REUSE

**Source:** Finding 0061

**What happens:** Deleted I-addresses are never reused. Since the granfilade is never modified by DELETE, and allocation always queries the granfilade for the current maximum, "gaps" in V-space created by DELETE do not create "gaps" in I-space. The I-address space grows strictly monotonically and permanently. There is no free-list, no gap-tracking, and no garbage collection of I-addresses.

**Why it matters for spec:** Formalizable as: `∀ i ∈ I-space : once_allocated(i) ⟹ always_allocated(i)`. Combined with INV-MONOTONIC, this means I-addresses form a contiguous, ever-growing sequence within each document's allocation range. The no-reuse guarantee is essential for transclusion integrity: if document B transcludes content from document A via shared I-addresses, deleting that content from A's V-space cannot cause the I-addresses to be reallocated to different content in a later INSERT.

**Code references:** `findisatoinsertmolecule` in `backend/granf2.c:158-181` — no free-list consulted, always queries tree maximum. `findpreviousisagr` in `backend/granf2.c:255-278` — returns the highest existing I-address, including those of deleted-from-V-space content.

**Concrete example:**
- Document has I.1, I.2, I.3. Delete the character at I.2 from V-space.
- Granfilade still contains I.1, I.2, I.3 (all three entries persist).
- Next allocation: `findpreviousisagr` returns I.3 → allocates I.4.
- I.2 is never reused, even though it is no longer mapped in any V-space.

**Provenance:** Finding 0061
**Co-occurring entries:** [SS-ADDRESS-SPACE], [FC-GRANF-ON-DELETE], [INV-MONOTONIC]

---

### INV-CRUM-BOUND

**Sources:** Findings 0062, 0063

#### Finding 0062

**What happens:** Continuous interior typing at a single cursor position costs exactly +2 crums for the first character, then +0 for every subsequent character. This gives a tight upper bound on crum count: `c ≤ 1 + 2C + 3R + 3P`, where C is the number of distinct cursor repositionings (each incurs the +2 split cost once), R is the number of rearrangements (cut-paste), and P is the number of pastes. The coefficient 2 for C reflects the verified cost: each new typing position pays the split penalty exactly once, after which all further characters at that position coalesce at zero cost.

This bound is tight because:
- The initial document has 1 crum (the original content)
- Each cursor repositioning to a new interior position creates a split (+2 crums)
- Sequential typing at the same cursor position coalesces (+0 crums per character)
- The ONMYRIGHTBORDER + isanextensionnd mechanism is what makes the coefficient 2 (not 2N for N characters)

**Why it matters for spec:** This is a universally quantified complexity invariant: `forall doc : Doc, ops : Seq<Op> :: crum_count(apply(doc, ops)) ≤ 1 + 2*cursor_repositions(ops) + 3*rearrangements(ops) + 3*pastes(ops)`. It can be verified in Dafny as a lemma over operation sequences, with the coalescing behavior (ST-INSERT above) as the key inductive step. The invariant depends on three verified facts: (1) ONMYRIGHTBORDER prevents knife cuts at crum boundaries, (2) `isanextensionnd` merges contiguous same-homedoc insertions, (3) extension is rightward-only.

**Code references:**
- `retrie.c:345-372` — `whereoncrum()` boundary classification
- `insertnd.c:137-143` — `makegappm()` early exit at boundary
- `insertnd.c:293-301` — `isanextensionnd()` extension check

**Concrete example:**
```
Start: "ABCDEFGH" → 1 crum
Type "12345" at position 5 (interior):
  "1" at 1.5: +2 crums → 3 crums  (split + new)
  "2" at 1.6: +0 crums → 3 crums  (coalesce)
  "3" at 1.7: +0 crums → 3 crums  (coalesce)
  "4" at 1.8: +0 crums → 3 crums  (coalesce)
  "5" at 1.9: +0 crums → 3 crums  (coalesce)
Result: "ABCD12345EFGH" with 3 crums, matching 1 + 2*1 = 3

Verified by golden test: single contiguous vspan from 1.1 with width 0.13.
```

**Provenance:** Finding 0062

#### Finding 0063

**What happens:** CREATELINK breaks `isanextensionnd` coalescing for subsequent text INSERTs. After CREATELINK consumes I-address space, the next INSERT's text I-addresses are non-contiguous with the previous INSERT's text I-addresses. When `isanextensionnd` checks whether the new content's origin equals the existing crum's reach, the check fails — the new text I-addresses start in a different range from the link orgl allocation. This forces creation of new crums, equivalent to a cursor repositioning.

Each CREATELINK followed by text INSERT incurs the same +2 crum cost as a cursor repositioning. The crum bound `c ≤ 1 + 2C + 3R + 3P` from Finding 0062 should account for link creation events either in the C term (treating CREATELINK as an implicit repositioning) or via a separate L term: `c ≤ 1 + 2C + 2L + 3R + 3P`, where L is the number of CREATELINK operations interleaved with text INSERTs.

**Why it matters for spec:** The crum bound invariant needs refinement. CREATELINK is an "invisible cursor repositioning" from the I-address perspective — it does not change the V-space insertion point, but it disrupts I-space contiguity required for coalescing. The Dafny lemma for crum bound must include CREATELINK in the set of coalescing-breaking operations: `coalesce_breakers = cursor_repositions ∪ createlink_events`.

**Code references:**
- `insertnd.c:293-301` — `isanextensionnd()` checks reach == origin; fails after CREATELINK because origin jumps past link orgl's I-address range

**Concrete example:**
```
INSERT "ABC" at v:    crum₁ [v, v+0.3), I-addr 1.1–1.3. crums = 1
CREATELINK:           link orgl allocated at I-addr ~2. No V-space text effect.
INSERT "DEF" at v+0.3:
  isanextensionnd checks: crum₁.reach (I-addr 1.4) == new origin (I-addr 2.1)?
  FALSE — link orgl consumed I-space between 1.3 and 2.1
  New crum₂ created: +2 crums → 3 crums
  (Same cost as if user had repositioned cursor)
```

**Provenance:** Finding 0063

**Co-occurring entries:** [SS-WHEREONCRUM], [PRE-INSERT], [ST-INSERT], [FC-GRANF-ON-DELETE], [INV-MONOTONIC], [INT-LINK-INSERT], [EC-BOUNDARY-INSERT-CLASSIFICATION]

---

### INV-DELETE-NOT-INVERSE

**Sources:** Findings 0064, 0072

#### Finding 0064

**What happens**: DELETE followed by INSERT of identical text does NOT restore the original document state. The V-space content is reconstructed (same characters at the same positions), but the I-space identity is entirely different. INSERT always allocates fresh I-addresses from the granfilade — it has no mechanism to reuse previously freed I-addresses. The result is that the re-inserted text has new I-addresses with no relationship to the original ones.

All relationships indexed by I-address are permanently severed: transclusions, link endpoints, version comparison results, and provenance chains. The document *looks* the same in V-space but is identity-disconnected in I-space.

**Why it matters for spec**: DELETE and INSERT are not algebraic inverses. Formally:

```
Let s = content(v) and i = iaddr(v) in state S₀
After DELETE(doc, v):            S₁ where iaddr(v) = ∅
After INSERT(doc, v, s):         S₂ where iaddr(v) = i' and i' ≠ i
                                 and content(v) = s (V-space restored)
                                 but i' ∩ i = ∅ (I-space disconnected)
```

This non-invertibility is fundamental, not a bug. It follows from the append-only granfilade: once I-addresses are allocated, the allocator has moved past them and will never return them.

**Code references**:
- `backend/do1.c:27-43` — `doinsert`: always calls `inserttextingranf` for fresh I-addresses
- `backend/edit.c:31-76` — `deletend`: frees POOM mappings (V→I references), not the I-addresses themselves
- Test scenario: `febe/scenarios/provenance.py::scenario_delete_then_recopy`

**Concrete example**:
```
State S₀:
  POOM: V(1.1)→I(5.1) V(1.2)→I(5.2) V(1.3)→I(5.3) V(1.4)→I(5.4)
        "A"            "B"            "C"            "D"

After DELETE "BC":
  POOM: V(1.1)→I(5.1) V(1.2)→I(5.4)
        "A"            "D"

After INSERT "BC" at V(1.2):
  POOM: V(1.1)→I(5.1) V(1.2)→I(5.5) V(1.3)→I(5.6) V(1.4)→I(5.4)
        "A"            "B"            "C"            "D"

V-space content identical to S₀, but I(5.5) ≠ I(5.2) and I(5.6) ≠ I(5.3).
compare_versions(S₀, S₂) reports "BC" as different content.
```

**Provenance**: Finding 0064

#### Finding 0072

**What happens**: DELETE followed by re-INSERT of identical text does not restore document identity. V-space content matches the original, but I-addresses are entirely new allocations. This means all I-address-indexed relationships are severed: transclusion links pointing to the original I-addresses no longer intersect the document's content, `compare_versions` reports no shared content between the original state and the re-inserted state, and `find_documents` provenance queries return different results.

The only identity-preserving restoration is VCOPY from a document (typically a version) that still references the original I-addresses. VCOPY shares existing I-addresses rather than allocating new ones.

**Why it matters for spec**: Reinforces the non-invertibility property with concrete relationship consequences:

```
State A: "Original text" at I(5.1)-I(5.13)
DELETE → INSERT same text:
State B: "Original text" at I(5.14)-I(5.26)

Broken: transclusions referencing I(5.1)-I(5.13)
Broken: compare_versions(A, B) finds no shared I-addresses
Broken: find_documents queries for I(5.1)-I(5.13) no longer find this document

Preserved: VCOPY from version sharing I(5.1)-I(5.13) restores identity
```

**Code references**:
- `backend/do1.c:27-43` — `doinsert`: always calls `inserttextingranf` for fresh I-addresses
- `backend/do1.c:45-65` — `docopy`/VCOPY: calls `insertpm` sharing existing I-addresses
- `febe/tests/debug/test_edit_history.py` — demonstrates identical V-space content with different I-addresses

**Provenance**: Finding 0072

**Co-occurring entries:** [SS-POOM-MUTABILITY], [ST-COPY], [ST-DELETE], [ST-VERSION-CREATE], [FC-DELETE-CROSS-DOC], [FC-VERSION-ISOLATION], [INV-IADDR-IMMUTABILITY]

---

### INV-ENFILADE-RELATIVE-ADDRESSING

**Source:** Finding 0066

**What happens:** For all 2D enfilade nodes, the absolute grasp of any node equals the sum of ancestor displacements plus its own displacement:

```
absolute_grasp(node) = absolute_grasp(parent) + node.cdsp
absolute_grasp(root) = root.cdsp
```

This is maintained by `setwispnd`, which after every modification: (1) finds the minimum displacement `mindsp` across all children, (2) adds `mindsp` to the parent's `cdsp`, and (3) subtracts `mindsp` from every child's `cdsp`. The operation at `wisp.c:211` — `dspsub(&ptr->cdsp, &mindsp, &ptr->cdsp, ...)` — is the critical step converting children from absolute to relative.

This invariant is type-specific: it holds for POOM and SPAN enfilades. GRAN enfilades use a different scheme where root displacement is always zero and `setwidseq` sums widths instead of tracking displacements.

**Why it matters for spec:** This is a core structural invariant for 2D enfilades. Any formal model must capture that displacement is relative, not absolute, and that the root's displacement equals the minimum address in the tree. The grasp calculation `grasp = offset + dsp` at `retrie.c:337` depends on this invariant being maintained.

**Code references:**
- `backend/wisp.c:196` — `dspadd(&father->cdsp, &mindsp, &newdsp, ...)` — root absorbs minimum
- `backend/wisp.c:211` — `dspsub(&ptr->cdsp, &mindsp, &ptr->cdsp, ...)` — children become relative
- `backend/retrie.c:337` — `dspadd(offset, &ptr->cdsp, grasp, ...)` — grasp from displacement

**Provenance:** Finding 0066
**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-INSERT], [EC-EMPTY-DOC]

---

### INV-ENFILADE-OCCUPANCY

**Sources:** Findings 0070, 0071

#### Finding 0070

**What happens:** Four threshold functions in `genf.c:239-261` define a rebalancing envelope that maintains node occupancy within valid bounds. For upper crums (branching factor B = `MAXUCINLOAF` = 6):

| Predicate | Condition | Upper crum threshold | Triggers |
|-----------|-----------|---------------------|----------|
| `toomanysons(ptr)` | `sons > B` | > 6 | Split via `splitcrumupwards` |
| `roomformoresons(ptr)` | `sons < B` | < 6 | Allows insertion of another child |
| `toofewsons(ptr)` | `sons < B - 1` | < 5 | Merge/steal via `recombinend` |

The thresholds create three occupancy zones:
- **Underfull** (1..B-2 = 1..4): `toofewsons` is TRUE, node tries to steal nephews
- **Normal** (B-1 = 5): Neither underfull nor at capacity
- **At capacity** (B = 6): `roomformoresons` is FALSE (cannot accept more), but `toomanysons` is also FALSE (no split needed) — this is the stable maximum
- **Overfull** (> B = 7+): `toomanysons` triggers split

The gap between `roomformoresons` (strict <) and `toomanysons` (strict >) at exactly B sons creates a stable equilibrium state. A node at exactly B children is full but valid.

All four functions select their threshold using the same height-aware, type-aware dispatch: `height > 1 ? MAXUCINLOAF : is2d ? MAX2DBCINLOAF : MAXBCINLOAF`.

**Why it matters for spec:** This defines the core B-tree invariant for enfilades. For every non-root internal node, the occupancy must satisfy `1 <= sons <= B` where B = `max_children(height, type)`. The rebalancing operations (split, merge, steal) maintain this invariant as a postcondition. The invariant can be stated:

```
forall node in enfilade:
  node.sons >= 1  (except empty root, see Bug 0019)
  node.sons <= max_children(node.height, enfilade.type)
```

The split precondition is `sons > B`; the merge precondition is `sons < B - 1` (for upper crums).

**Code references:**
- `backend/genf.c:239-261` — `toomanysons`, `roomformoresons`, `toofewsons` threshold functions
- `backend/split.c:16-43` — `splitcrumupwards` loop (splits while `toomanysons`)
- `backend/recombine.c:104-131` — `recombinend` rebalancing (steals while `toofewsons`)
- `backend/insertnd.c:242-275` — `insertcbcnd` checks `roomformoresons` before adding child

**Concrete example:** Upper crum with 6 children (at capacity):
- `toomanysons` → FALSE (6 is not > 6)
- `roomformoresons` → FALSE (6 is not < 6)
- `toofewsons` → FALSE (6 is not < 5)
- State: stable, no rebalancing triggered

Insert a 7th child:
- `toomanysons` → TRUE (7 > 6)
- `splitcrumupwards` splits the node into two nodes (e.g., 4+3 or 3+4)
- If node is the fullcrum (root), `levelpush` adds a new root level
- If node is not root, `splitcrum` splits within the current level

**Provenance:** Finding 0070

#### Finding 0071

**What happens:** The `ishouldbother` merge guard in `recombinend` enforces that merges only occur when the result stays within branching bounds: `dest->numberofsons + src->numberofsons <= (height > 1 ? MAXUCINLOAF : MAX2DBCINLOAF)`. This ensures the merge-then-no-split property: a rebalancing merge never immediately triggers a split. The `randomness(.3)` probabilistic guard is effectively disabled (always returns TRUE), meaning all occupancy-eligible pairs are deterministically merged.

**Why it matters for spec:** The occupancy invariant is maintained through rebalancing as a postcondition: after `recombinend`, every node satisfies `1 <= sons <= max_children(height, type)`. The merge guard is the mechanism that prevents rebalancing from violating the upper bound. The deterministic behavior (no randomness) simplifies formal verification — the algorithm is fully determined by node occupancy counts.

**Code references:**
- `backend/recombine.c:150-163` — `ishouldbother` with occupancy check and reserved-crum guard

**Provenance:** Finding 0071

**Co-occurring entries:** [SS-ENFILADE-BRANCHING], [SS-ENFILADE-TREE], [PRE-SPLIT], [ST-REBALANCE-2D], [ST-SPLIT-2D], [FC-RESERVED-CRUM], [EC-GRAN-BOTTOM-SINGLETON]

---

### INV-NO-ZERO-WIDTH-CRUM

**Source:** Finding 0075

**What happens:** The DELETE Phase 1 cutting mechanism cannot produce zero-width bottom crums. Because `slicecbcpm` is only called when the cut is strictly interior to a crum (`grasp < cut < reach`), the local cut offset satisfies `0 < localcut.mantissa[0] < cwid.mantissa[0]` — both strict inequalities. When `slicecbcpm` splits a crum at `ndcuts.c:396-444`, it creates two pieces: the original crum retains width `localcut` (positive) and the new crum receives width `cwid - localcut` (also positive, via `locksubtract` at `ndcuts.c:444`). Both resulting crums have strictly positive width.

This invariant is enforced structurally by the `whereoncrum` guard, not by explicit assertions in `slicecbcpm`. However, assertions at `ndcuts.c:398` and `ndcuts.c:410` would fail if a zero-width cut were somehow passed in.

**Why it matters for spec:** This is a structural invariant of the enfilade after any DELETE Phase 1: `∀ crum ∈ bottom_crums(enf) : crum.width > 0`. No cutting operation can produce a degenerate zero-width crum. This invariant supports leaf linearity enforcement (DN-0011) and can be assumed in all postconditions for DELETE. For bounded model checking, the width of every bottom crum is in `{w : Tumbler | w > 0}` after any sequence of operations.

**Code references:**
- `ndcuts.c:396` — `tumblersub(cut, &grasp, &localcut)`: computes local offset, guaranteed positive
- `ndcuts.c:444` — `locksubtract`: computes remaining width, guaranteed positive
- `ndcuts.c:398, 410` — assertions that would catch zero-width violations
- `retrie.c:345-372` — `whereoncrum()`: structural guard ensuring strict interiority

**Concrete example:**
```
Crum: grasp=1.1, cwid=0.6  (reach=1.7)
Cut at 1.4 (interior, THRUME):
  localcut = 1.4 - 1.1 = 0.3
  Original crum: width = 0.3  (> 0 ✓)
  New crum:      width = 0.6 - 0.3 = 0.3  (> 0 ✓)

Cross-crum DELETE [1.2, 1.6) across two crums:
  Crum1 [1.1, 1.4): cut at 1.2 → localcut=0.1, remaining=0.2  (both > 0 ✓)
  Crum2 [1.4, 1.7): cut at 1.6 → localcut=0.2, remaining=0.1  (both > 0 ✓)
```

**Provenance:** Finding 0075
**Co-occurring entries:** [PRE-DELETE], [ST-DELETE]

---

### INV-WIDTH-VALUE-EQUIVALENCE

**Source:** Finding 0076

**What happens:** For any POOM bottom crum, the integer value encoded in the V-width always equals the integer value encoded in the I-width. The tumbler representations differ (different exponents, different digit counts), but extracting the numeric value via `tumblerintdiff` yields the same integer from both. This holds because the V-width is constructed from the I-width's integer value — the construction preserves the value while changing the encoding precision.

**Why it matters for spec:** This is a structural invariant on POOM crums: `forall crum c :: tumblerintdiff(c.width.dsas[V], zero) == tumblerintdiff(c.width.dsas[I], zero)`. This invariant must hold after every operation that creates or modifies bottom crums. It enables value-based width comparison across address spaces — code that needs to compare V-widths with I-widths must use `tumblerintdiff` to extract values rather than `tumblercmp` on the raw tumblers.

**Code references:**
- `orglinks.c:105-117` — V-width construction preserves I-width value
- `tumble.c:599-623` — `tumblerincrement` encodes the same integer at a different exponent

**Provenance:** Finding 0076
**Co-occurring entries:** [SS-POOM-BOTTOM-CRUM], [ST-INSERT-VWIDTH-ENCODING], [EC-VWIDTH-ZERO-ADDRESS]

---

### INV-RETRIEVAL-V-SORTED

**Source:** Finding 0078

**What happens:** `incontextlistnd()` performs explicit insertion-sort by V-address as contexts are discovered during B-tree traversal. Each leaf node found by `findcbcinarea2d()` is inserted into a linked list at the position that maintains ascending order of `totaloffset.dsas[index]` (the left boundary in the specified dimension). The algorithm has four cases: (1) first insertion, (2) insert before head if new context precedes it, (3) insert between two adjacent contexts when the new context falls between their left boundaries, (4) append to end. The comparison uses `whereoncontext()` which computes the interval `[left, right)` for each context and calls `intervalcmp()` to classify the new address relative to that interval.

**Why it matters for spec:** This establishes a postcondition on all retrieval operations that use `incontextlistnd`: the result list is sorted by left boundary in the queried dimension. Formally:

```
forall poom : POOM, ispan : ISpan, index : Dimension ::
  let contexts = ispan2vspanset(poom, ispan, index) in
  forall j, k :: 0 <= j < k < |contexts| ==>
    contexts[j].totaloffset.dsas[index] <= contexts[k].totaloffset.dsas[index]
```

This ordering is **independent of tree structure** — it holds regardless of insertion order, split/rebalance operations, or diagonal ordering in 2D enfilades. The Dafny spec should include this as a postcondition on `ispan2vspanset` and all operations that return V-span results (Q3 compare_versions, Q6/Q7 findlinks, Q8 finddocscontaining).

**Code references:**
- `context.c:75-111` — `incontextlistnd()` insertion-sort implementation
- `context.c:124-149` — `whereoncontext()` computes interval and classifies address position
- `retrie.c:401-418` — `intervalcmp()` returns TOMYLEFT/ONMYLEFTBORDER/THRUME/ONMYRIGHTBORDER/TOMYRIGHT
- `retrie.c:229-268` — `findcbcinarea2d()` traverses B-tree left-to-right, calls `incontextlistnd` per leaf

**Concrete example:**
```
POOM B-tree contains contexts for V-positions 1.10, 1.30, 1.20, 1.40
(tree sibling order reflects insertion order, not V-address order)

Tree traversal discovers them in tree order:
  Context(V=1.10) → Context(V=1.30) → Context(V=1.20) → Context(V=1.40)

incontextlistnd insertion-sort produces:
  Context(V=1.10) → Context(V=1.20) → Context(V=1.30) → Context(V=1.40)

Result is V-sorted regardless of tree structure.
```

**Provenance:** Finding 0078
**Co-occurring entries:** [SS-CONTEXT-LIST], [FC-RETRIEVAL-TREE-INDEPENDENCE]

---

## Interactions

> How subsystems affect each other

### INT-CLIENT-VALIDATION

**Source:** Finding 0001

**What happens:** Because the backend does not enforce element-level tumbler structure, clients must construct correct element addresses themselves. Malformed addresses (e.g., document-level tumblers used where element-level are expected) are silently accepted by the backend. Bug 0005 documented a case where pyxi used document-level addresses for link types, which the backend accepted without error.

**Why it matters for spec:** This defines an interaction boundary: the backend provides document-existence validation, and the client is responsible for element-level correctness. In a formal model, this means the system-level correctness property requires a conjunction of backend invariants AND client-side address construction rules. The backend alone does not guarantee well-formed specsets.

**Provenance:** Finding 0001
**Co-occurring entries:** [SS-TUMBLER], [PRE-SPECSET]

---

### INT-LINK-TRANSCLUSION

**Sources:** Findings 0004, 0005, 0007, 0008, 0026, 0028, 0037, 0043

#### Finding 0004

**What happens:** When content with a link is transcluded (vcopy'd) to another document, the link can be found from the copy. Calling `find_links` with a search specifying the target document returns the original link. This is because the vcopy shares the content identities, and the link is indexed by content identity — so any document referencing those identities can discover the link.

**Why it matters for spec:** This defines a key interaction between the link and transclusion subsystems: `forall link, doc_source, doc_target :: vcopy(content_ids(link.source), doc_source, doc_target) ==> findable(link, doc_target)`. Link discovery is a function of content identity presence, not document membership at link creation time. The formal spec should define `find_links(specset)` as: return all links whose source or target content identities intersect with the content identities referenced by the specset. This makes link discovery emergent from content identity sharing.

**Concrete example:**
- Document A: "Click [here] for details" — link on "here" (content identity C₁)
- Document C: vcopy "here" from A → C references C₁
- `find_links(search in C)` → returns the original link from A
- Both A and C can discover the link because both reference C₁

**Code references:** Test `link_with_vcopy_source` (PASS)

**Provenance:** Finding 0004

#### Finding 0005

**What happens:** When content with a link is transcluded (vcopy'd) to another document, the link is discoverable from the new location. Creating a link on "here" in document A, then vcopy'ing "here" to document C, makes `find_links()` on document C return the original link. This works because vcopy shares content identities, and link discovery is indexed by content identity.

**Why it matters for spec:** Confirms the interaction property from Finding 0004: `vcopy(content_ids(link.source), doc_source, doc_target) ==> findable(link, doc_target)`. Link discovery is a function of content identity presence in a document, not of which document was active when the link was created. The spec should define `find_links(specset)` as returning all links whose endpoint content identities intersect with the content identities referenced by the specset.

**Concrete example:**
- Document A: "Click [here] for details", link on "here" (content identity C₁)
- Document C: vcopy "here" from A → C references C₁
- `find_links(C)` → returns the link originally created in A's context

**Code references:** Test `link_with_vcopy_source` (PASS)

**Provenance:** Finding 0005

#### Finding 0007

**What happens:** Links follow content identity through versioning. When a document with linked content is versioned, the version inherits the ability to discover those links — because the version shares the same content identities as the original, and links are indexed by content identity. Calling `find_links` on the version returns the same link objects as calling `find_links` on the original. This extends INT-LINK-TRANSCLUSION from Finding 0004 to cover version-created documents in addition to vcopy-created references.

**Why it matters for spec:** The existing specification for link discovery — `find_links(specset)` returns links whose endpoint content identities intersect the specset — already covers this case. Since ST-VERSION-CREATE copies content identity references, versioned documents automatically satisfy the content-identity intersection condition for any links attached to the original's content. No new rule is needed; the finding confirms that the link discovery mechanism generalizes to versions.

**Concrete example:**
- Source: "Click here for info" — link on "here" (content identity C₁)
- Version: version of Source → "Click here for info" (same C₁)
- `find_links(Source)` → [link_id]
- `find_links(Version)` → [link_id] (same link, because Version references C₁)

**Code references:** Test `version_with_links`

**Provenance:** Finding 0007

#### Finding 0008

**What happens:** Links are discoverable from ANY document that shares content identity with a link's endpoint — whether through transclusion, versioning, or chains of both. When content with a link is transcluded to another document, `find_links` on the copy returns the same link as on the source. When both endpoints of a link are transcluded content, all three documents (source origin, target origin, link document) can discover the link. This extends the INT-LINK-TRANSCLUSION entries from Findings 0004 and 0007 with multi-endpoint and chain scenarios.

**Why it matters for spec:** The link discovery specification `find_links(specset) = {link | content_ids(link.source) ∩ content_ids(specset) ≠ ∅ ∨ content_ids(link.target) ∩ content_ids(specset) ≠ ∅}` is confirmed to work bidirectionally and for links with transcluded endpoints. When both endpoints are transcluded, the link is findable from any document referencing either endpoint's content identities. The formal spec need not special-case multi-transclusion — the existing content-identity intersection rule handles it.

**Concrete example:**
- source_origin: "Clickable source text", target_origin: "Target destination text"
- link_doc: transcludes "Clickable" from source_origin and "Target" from target_origin
- Create link from "Clickable" to "Target" in link_doc
- `find_links(link_doc)` → [link_id]
- `find_links(source_origin)` → [link_id] (source_origin references the link's source content identity)
- `find_links(target_origin)` → [link_id] (target_origin references the link's target content identity)

**Code references:** Tests `transclude_linked_content`, `link_both_endpoints_transcluded`

**Provenance:** Finding 0008

#### Finding 0026

**What happens:** When a link targets transcluded content, `find_links` discovers the link through both the document containing the transclusion AND the original source document. Specifically: if B contains "important text", A transcludes "important text" from B, and C links to A's transcluded copy, then `find_links(target=A)` finds the link AND `find_links(target=B)` also finds the link. The link was created pointing at A, but B discovers it because A's transcluded content shares identity with B's original content.

This extends previous INT-LINK-TRANSCLUSION entries (Findings 0004, 0005, 0007, 0008) with a concrete three-document scenario where the link target (not just source) is transcluded content, and discovery works from the transclusion origin.

**Why it matters for spec:** Confirms the `find_links` content-identity intersection rule works symmetrically for link targets: `content_ids(link.target) ∩ content_ids(B) ≠ ∅ ⟹ link ∈ find_links(B)`. Since A's transcluded region shares I-addresses with B, searching B's I-address space intersects the link's target endpoint. No special-case rule is needed — the existing content-identity model handles it.

**Concrete example:**
- B: "Source content in B: important text here"
- A: "A contains: " + vcopy("important text" from B)
- C: "C references: see the important text"
- Link created: C's "important text" → A's transcluded "important text"
- `find_links(target=A's transcluded content)` → [link_id] (direct target)
- `find_links(target=B's original content)` → [link_id] (discovered via shared content identity)

**Code references:** Test `links/link_to_transcluded_content`, golden file `golden/links/link_to_transcluded_content.json`

**Provenance:** Finding 0026

#### Finding 0028

**What happens**: Transclusion (vcopy) creates shared content identity between documents. It does NOT copy links, create new links, or modify existing links. The only link-relevant effect of transclusion is sharing I-addresses, which enables link discovery from the destination document. The link itself is unmodified — only its discoverability expands to include any document sharing its endpoint's I-addresses.

**Why it matters for spec**: The frame condition for vcopy with respect to links is: `links(system_after_vcopy) == links(system_before_vcopy)`. No links are created, modified, or destroyed by vcopy. The interaction property is: `vcopy(content, src_doc, dst_doc) => (forall L :: I-addresses(L.source) ∩ I-addresses(content) ≠ ∅ => findable(L, dst_doc))`. This is emergent behavior: vcopy's postcondition (sharing I-addresses) combined with find_links' I-address-based search yields link discoverability without any link-specific logic in vcopy.

**Code references**: Test `partial_vcopy_of_linked_span` — vcopy of "link" from linked "hyperlink text", then `find_links` on copy finds the link

**Concrete example**:
```
Pre-state:
  Document A: "hyperlink text" with link L on this content
  Document C: empty

vcopy("link" from A to C):
  Post-state:
    Document C: "link" (I-addresses shared with A's "link" substring)
    Link L: UNCHANGED (same source endpoint, same target endpoint)
    find_links(C) → {L}  (new — C can now discover L)
    find_links(A) → {L}  (unchanged — A still discovers L)

What vcopy did NOT do:
  - Did not create a new link in C
  - Did not copy L to C
  - Did not modify L's endpoints
```

**Provenance**: Finding 0028b §4

#### Finding 0037

**What happens:** The automatic splitting of V-spans into I-spans at link creation time is a direct consequence of how transclusion composes content from multiple sources. When document C transcludes "AA" from A and "BB" from B, the contiguous V-span 1.1..1.4 in C maps to two disjoint I-address regions. The link subsystem handles this transparently: `vspanset2sporglset` calls `vspanset2ispanset` which walks the POOM (permutation matrix) to discover all I-address regions, producing one I-span per contiguous region. The front end sees a simple contiguous selection; the backend decomposes it into identity-preserving references.

This is the same mechanism that causes endset fragmentation after pivot operations (EC-PIVOT-LINK-FRAGMENTATION from finding 0019): any operation that makes previously contiguous I-addresses non-contiguous in V-space triggers the same splitting logic in `vspanset2sporglset`.

**Why it matters for spec:** The interaction between transclusion and link creation is: `create_link` is compositional over the content identity structure. The spec must model `V_to_ISpans(doc, vspan)` as returning the partition of the vspan's content into maximal contiguous I-address runs. This function is shared between link creation and endset reporting, ensuring round-trip consistency.

**Code references:**
- `sporgl.c:35-65` — shared splitting logic used by both link creation and other operations
- `orglinks.c:397-454` — `vspanset2ispanset` → `permute` → `span2spanset` chain

**Provenance:** Finding 0037

#### Finding 0043

**What happens**: Despite CREATENEWVERSION not copying link subspace entries to the version's POOM, `find_links` still works on the version. This is because link discovery operates on content identity (I-addresses), not POOM structure. The version shares permascroll I-addresses with the source (via the text subspace copy), and links are indexed by those I-addresses. The `find_links` operation searches I-space for links whose endpoints intersect the query's I-addresses, so any document sharing content identity with a linked document will discover those links — regardless of whether that document has link subspace entries in its own POOM.

**Why it matters for spec**: The formal spec must model two completely independent mechanisms: (1) POOM link storage — the `0.x`/`2.x` subspace storing link orgl ISAs within a document, and (2) link discovery — the `find_links` operation that searches by content identity intersection. These are decoupled: a document can have no link subspace entries but still return links via `find_links`, because link discovery is content-identity-based. The spec should state: `find_links(doc) = {L | L.endpoint_content ∩ content_ids(doc) ≠ ∅}`, independent of `link_subspace(doc)`.

**Concrete example**:
```
Source (has link "here" on "Click here for info"):
  POOM: at 0 for 0.1 (link), at 1 for 1 (text)
  find_links → [link_id]

Version of source:
  POOM: at 1.1 for 0.15 (text only, no link subspace)
  find_links → [link_id]  (SAME result, via content identity)

retrieve_contents on version returns:
  ["Click here for info", "1.1.0.1.0.1.0.2.1"]
  (text content includes embedded link address from I-space)
```

**Code references**:
- `find_links` searches by I-address intersection (content identity based)
- Golden test `version_with_links` verifies link discovery works on versions

**Provenance**: Finding 0043

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-DUAL-ENFILADE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [SS-VERSION-ADDRESS], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-INSERT], [ST-LINK-CREATE], [ST-REMOVE], [ST-VERSION-CREATE], [FC-DOC-ISOLATION], [FC-LINK-PERSISTENCE], [FC-SUBSPACE], [INV-IDENTITY-OVERLAP], [INV-LINK-CONTENT-TRACKING], [INV-LINK-GLOBAL-VISIBILITY], [INV-SINGLE-CHAR-GRANULARITY], [INV-TRANSITIVE-IDENTITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-VERSION], [INT-VERSION-TRANSCLUSION], [EC-EMPTY-DOC], [EC-LINK-PARTIAL-SURVIVAL], [EC-LINK-TOPOLOGY], [EC-ORPHANED-LINK], [EC-SELF-COMPARISON], [EC-SELF-TRANSCLUSION]

---

### INT-VERSION-TRANSCLUSION

**Sources:** Findings 0007, 0032

#### Finding 0007

**What happens:** Transclusion relationships are inherited through versioning. If document A transcludes content from document B (via vcopy), and a version of A is created, the version also shares content identity with B. The `compare_versions` operation between the version and B correctly reports shared content. This means versioning preserves not just direct content identity but also transclusive content identity.

**Why it matters for spec:** This is an interaction property: `vcopy(B, A) && version_of(A, V) ==> shares_identity(V, B)`. It follows from the transitivity of content identity: A shares identity with B (via vcopy), V shares identity with A (via version-create), therefore V shares identity with B. The formal spec does not need a special version-transclusion rule — it is a consequence of ST-VERSION-CREATE and ST-VCOPY operating on the same content identity system.

**Concrete example:**
- Source: "Shared transcluded content"
- Doc: "Prefix: " + vcopy("Shared" from Source) → Doc shares identity with Source for "Shared"
- Version: version of Doc → Version shares identity with Doc (and transitively with Source)
- `compare_versions(Version, Source)` finds "Shared" as shared content

**Code references:** Test `version_preserves_transclusion`

**Provenance:** Finding 0007

#### Finding 0032

**What happens:** When a document contains transcluded content (shared I-addresses from another document via COPY), creating a version preserves those transclusion relationships. The version shares the same I-addresses as the original, including any that originated from third-party documents. `compare_versions` between the version and the third-party source correctly reports shared content.

**Why it matters for spec:** This follows from ST-VERSION-CREATE's postcondition (`references(version) = references(source)`) combined with INV-TRANSITIVE-IDENTITY. No special transclusion-preservation rule is needed — it is a consequence of copying I-address references rather than content. The spec should verify: `forall iaddr in references(source) :: iaddr in references(version)`, which automatically covers transcluded I-addresses.

**Code references:** Test `golden/versions/version_preserves_transclusion.json`.

**Concrete example:**
```
Doc A: "Hello"          (I-addresses α₁..α₅)
Doc B: "Hello world"    (α₁..α₅ from copy of A, plus β₁..β₆ new)
Version of B: "Hello world"  (same α₁..α₅ and β₁..β₆)

compare(Version_of_B, A) → "Hello" shared (via α₁..α₅)
```

**Provenance:** Finding 0032

**Co-occurring entries:** [SS-VERSION-ADDRESS], [ST-INSERT], [ST-VERSION-CREATE], [FC-DOC-ISOLATION], [INV-ATOMICITY], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-LINK-VERSION], [EC-EMPTY-DOC]

---

### INT-LINK-VERSION

**Sources:** Findings 0008, 0019, 0032, 0046

#### Finding 0008

**What happens:** Links added to a version are discoverable from the original document, and vice versa. If a link is created on a version (targeting content with shared identity), the original can discover that link through `find_links`. This is bidirectional — links created on either document are discoverable from both. This extends INT-LINK-TRANSCLUSION to confirm that link creation on a version has global visibility through content identity.

**Why it matters for spec:** The interaction property is: `version_of(orig, ver) ∧ create_link(ver, content_ids) ⟹ findable(link, orig)`. This is not a new axiom — it follows from ST-VERSION-CREATE (version shares content identity with original) and the content-identity-based link discovery rule. But the finding confirms the surprising consequence: creating a link in a private version makes it visible to anyone referencing the same content. The spec should note this as a semantic consequence rather than a special rule.

**Concrete example:**
- Original: "Shared content here"
- Version: version of Original → "Shared content here" (same content identities)
- Create link on "content" in Version
- `find_links(Version)` → [link_id]
- `find_links(Original)` → [link_id] (discovers link created in version)

**Code references:** Test `version_add_link_check_original`

**Provenance:** Finding 0008

#### Finding 0019

Links created on original documents are discoverable from versions through shared content identity. When a version is created, it shares I-addresses with the original, so `find_links` on the version returns links created against the original.

Concrete example:
```
Original doc: 1.1.0.1.0.1 with link at V 1.17 width 0.4
Version:      1.1.0.1.0.1.1
find_links(version) → finds original's link
retrieve_endsets(version) → endsets report version's docid (1.1.0.1.0.1.1)
```

The endset docid is rewritten to the queried document's address, even though the link was created against the original. This means endsets are relative to the query context, not absolute.

**Why it matters for spec**: Version creation must preserve I-address sharing such that link discovery is inherited. The endset retrieval postcondition must specify docid rewriting relative to the query document.

**Provenance**: Finding 0019, section 5

#### Finding 0032

**What happens:** Links are discoverable from versions because link lookup is indexed by I-address, and versions share I-addresses with their source. Calling `find_links` on a version returns the same link objects as calling it on the original document. The links themselves are not copied — the version simply inherits link visibility through shared content identity.

**Why it matters for spec:** This is a consequence of the link-discovery rule (`find_links(specset)` returns links whose endpoints intersect the specset's I-addresses) combined with ST-VERSION-CREATE. No version-specific link rule is needed. The spec should verify: `find_links(version) = find_links(source)` at creation time, diverging only as edits create new I-addresses in either document.

**Code references:** Test `golden/versions/version_with_links.json`.

**Concrete example:**
```
Source: "Click here" with link on "here" (I-addresses γ₃..γ₆)
Version of Source: "Click here" (same I-addresses γ₃..γ₆)

find_links(Source)  → [link₁]
find_links(Version) → [link₁]  (same link, via shared I-addresses)
```

**Provenance:** Finding 0032

#### Finding 0046

**What happens:** A version created by CREATENEWVERSION discovers links from the original document even though the version's POOM contains no link entries. This works because: (1) the version shares text I-addresses with the original, (2) links are stored in the spanf (span enfilade) index keyed by I-address, and (3) `find_links` converts V-spans to I-spans then searches the spanf. Since the version's text maps to the same I-addresses as the original, the same spanf entries match. The link "inheritance" is not an explicit mechanism — it is an emergent consequence of identity-based link indexing.

**Why it matters for spec:** The version-link relationship can be derived from more primitive facts: `findlinks(version, vspan) = findlinks_by_iaddr(vspan2ispan(version, vspan))`, and `vspan2ispan(version, v) ⊆ vspan2ispan(original, v')` for corresponding positions. No special version-link rule is needed in the spec — the general link discovery mechanism (INT-LINK-TRANSCLUSION) covers this case because versioning IS transclusion of the text subspace.

**Code references:**
- Test result: version with `find_links FROM version → ["1.1.0.1.0.1.0.2.1"]`
- `docreatenewversion()` — `do1.c:264-303` — copies text I-addresses
- Link discovery via spanf operates in I-space, not document POOM

**Provenance:** Finding 0046

**Co-occurring entries:** [SS-LINK-ENDPOINT], [SS-VERSION-ADDRESS], [PRE-COPY], [ST-VCOPY], [ST-VERSION-CREATE], [FC-LINK-PERSISTENCE], [INV-ATOMICITY], [INV-IADDR-PROVENANCE], [INV-LINK-CONTENT-TRACKING], [INV-LINK-GLOBAL-VISIBILITY], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-VERSION-TRANSCLUSION], [EC-MULTISPAN-LINK-DUPLICATION], [EC-PIVOT-LINK-FRAGMENTATION]

---

### INT-LINK-RETRIEVAL

**Source:** Finding 0010

**What happens**: The `find_links` operation searches the span-f (link enfilade) by I-address to discover which links are attached to content. This only works with permascroll I-addresses from the text subspace (`1.x`). Searching with link ISAs from `0.x` is meaningless — link orgls are not indexed by other link ISAs. The caller must know to use text I-addresses, not link reference I-addresses.

**Why it matters for spec**: The spec for `find_links` must state a precondition that the search I-addresses are permascroll addresses (from text subspace), not link orgl ISAs. This creates a dependency between the retrieval subsystem and the subspace convention — `find_links` implicitly requires the caller to understand the dual-enfilade structure.

**Code references**:
- span-f (link enfilade) indexes links by content I-address, not by link ISA

**Provenance**: Finding 0010
**Co-occurring entries:** [PRE-DELETE], [PRE-RETRIEVE-CONTENTS], [PRE-VCOPY], [INV-SUBSPACE-CONVENTION], [EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES]

---

### INT-SPORGL-LINK-INDEX

**Sources:** Findings 0013, 0035

#### Finding 0013

**What happens:** When a link is created, its endpoints (from, to, three) are converted to sporgls and indexed in the spanf enfilade. The function `insertendsetsinspanf()` receives sporglsets for each endpoint type and inserts them into the spanf index tagged with the link's ISA and endpoint type (`LINKFROMSPAN`, `LINKTOSPAN`). The spanf then maps: I-address → set of (link ISA, endpoint type) pairs. When retrieving links, the reverse path converts sporgls back to specsets via `linksporglset2specset()`.

**Why it matters for spec:** Sporgls are the data format at the interface between link creation and the spanf index. The spec for `insertendsetsinspanf` is: `spanf' = spanf ∪ { (sporgl.origin..sporgl.origin+sporgl.width) → (link_isa, endpoint_type) | sporgl ∈ endpoint_sporglset }`. The provenance field (`sporgladdress`) is stored in the index so that link retrieval can reconstruct which document each endpoint references. This means the spanf index stores document provenance, not just I-addresses.

**Code references:**
- `do2.c:116-128` — `insertendsetsinspanf()` inserts from/to/three sporglsets
- `sporgl.c:97+` — `linksporglset2specset()` for endpoint retrieval
- `spanf1.c` — spanf operations that consume sporglsets

**Provenance:** Finding 0013

#### Finding 0035

**What happens:** RETRIEVEENDSETS discovers links through the spanfilade by searching with ORGLRANGE dimension prefixes. The three link endset types are indexed as separate ORGLRANGE subspaces: LINKFROMSPAN=1, LINKTOSPAN=2, LINKTHREESPAN=3. The specset input is converted to I-addresses (sporglset) for the SPANRANGE restriction, then each endset type is searched independently by restricting the ORGLRANGE dimension. Results are converted back to V-addresses using the querying document's docid.

**Why it matters for spec:** This reveals how the spanfilade serves as a content-identity-based link index. The same spanfilade search mechanism that supports FINDLINKSFROMTOTHREE also supports RETRIEVEENDSETS, but with different input (V-spec region vs. from/to/three constraints) and different output (resolved endset specs vs. link ISAs). The use of the querying document's docid for V-address resolution means endsets are always expressed relative to the querying context, not the link's home.

**Code references:**
- ORGLRANGE subspace definitions: `backend/spanf1.c:190-235`
- `retrievesporglsetinrange()`: spanfilade search with dual range restriction
- `linksporglset2specset()`: I-to-V conversion using querying document's docid

**Provenance:** Finding 0035 (section 3)

**Co-occurring entries:** [SS-SPORGL], [SS-VSPAN-VS-VSPANSET], [ST-FIND-LINKS], [ST-PAGINATE-LINKS], [ST-RETRIEVE-ENDSETS], [ST-VSPAN-TO-SPORGL], [INT-SPORGL-TRANSCLUSION], [INT-SPORGL-VERSION-COMPARE], [EC-CURSOR-INVALIDATION], [EC-VSPAN-MISLEADING-SIZE]

---

### INT-SPORGL-TRANSCLUSION

**Source:** Finding 0013

**What happens:** During vcopy (transclusion), the data flow is: source V-spec → sporgls (via `vspanset2sporglset`) → `insertpm` into destination document. The sporgl carries the content's I-address identity through the copy operation. Because the sporgl preserves the original I-address (not a new one), the destination document ends up referencing the same content identities as the source. This is the mechanism by which transclusion preserves content identity — the sporgl is the carrier.

**Why it matters for spec:** The sporgl is the data structure that makes the ST-VCOPY postcondition (`references(target) = references(target_before) ∪ source_content_ids`) mechanically possible. Without the sporgl carrying provenance through the copy, the system would need another mechanism to ensure identity preservation. The spec for docopy should reference sporgls as the intermediate representation: `docopy(src, dst, vspec) = let sporgls = vspan_to_sporgl(src, vspec) in insert_by_iaddr(dst, sporgls)`.

**Code references:**
- `sporgl.c:35-65` — `vspanset2sporglset()` converts source content to sporgls
- The docopy flow: `VSpec → Sporgl → insertpm`

**Provenance:** Finding 0013
**Co-occurring entries:** [SS-SPORGL], [ST-VSPAN-TO-SPORGL], [INT-SPORGL-LINK-INDEX], [INT-SPORGL-VERSION-COMPARE]

---

### INT-SPORGL-VERSION-COMPARE

**Source:** Finding 0013

**What happens:** Version comparison (`compare_versions` / `correspond.c`) uses sporgls to find shared content between documents. Both documents' content is converted to sporgls, then intersection is computed by I-address (the `sporglorigin` field). Sporgls with the same I-address origin in both documents represent shared content — content that was transcluded or shares common ancestry. The sporgl's document provenance (`sporgladdress`) field distinguishes which document each span came from, enabling the comparison to report which content is shared and which is unique to each document.

**Why it matters for spec:** This is the mechanism underlying `compare_versions`: `shared(A, B) = { s ∈ sporgls(A) | ∃ t ∈ sporgls(B) :: s.origin ∩ t.origin ≠ ∅ }`. The I-address intersection is only meaningful for permascroll I-addresses (not link ISAs), connecting to the PRE-COMPARE-VERSIONS precondition from Finding 0009. The sporgl makes version comparison possible because it lifts document content from V-space (position-dependent) to I-space (identity-dependent) while retaining document provenance.

**Code references:**
- `correspond.c` — uses sporgls for version comparison
- `sporgl.c` — sporgl operations used by correspond

**Provenance:** Finding 0013
**Co-occurring entries:** [SS-SPORGL], [ST-VSPAN-TO-SPORGL], [INT-SPORGL-LINK-INDEX], [INT-SPORGL-TRANSCLUSION]

---

### INT-BERT-VERSION

**Source:** Finding 0014

**What happens:** When write access is denied (return -1), the protocol signals the client to create a new version of the document and open that version for writing instead. This connects BERT access control to the versioning system — access denial is not an error but a redirect into the version-branching workflow.

**Why it matters for spec:** The access control system and the versioning system interact: write contention triggers version creation rather than failure. This means the spec's version-creation operation has an implicit trigger from access denial, not just explicit user action. Formalizable as a protocol-level property: `denied_write(c, d) → should_create_version(c, d)`.

**Code references:** `bert.c:43-50` (return value -1 semantics), version creation logic in backend

**Provenance:** Finding 0014

## Omit

The following sections of Finding 0014 are omitted from analysis:

- **NOBERTREQUIRED bypass details:** The internal bypass mechanism (NOBERTREQUIRED=0) is an implementation optimization for avoiding redundant checks within already-protected contexts. It does not define new behavioral properties — it simply skips the access check. Not relevant to the formal specification of access semantics.
- **Test harness implications:** Single-connection test harness behavior is test infrastructure detail, not system semantics.
- **Connection tracking cleanup:** The cleanup-on-close behavior is operational lifecycle management, not a state property that needs formal verification.
**Co-occurring entries:** [SS-BERT], [PRE-OPEN-DOC], [INV-READ-SHARING], [INV-WRITE-EXCLUSIVITY]

---

### INT-CROSS-SESSION-TRANSCLUSION

**Source:** Finding 0022

**What happens:** Content identity (SPORGL/provenance tracking) is maintained globally. When session A transcludes content from session B's document via `vcopy`, content identity is preserved — `compare_versions` detects shared spans across session boundaries.

**Why it matters for spec:** The content identity system operates on global state. The invariant that transclusion preserves content identity holds regardless of which session performed the original insertion and which session performed the copy. This means the SPORGL system's tracking is not scoped to sessions.

**Concrete example:**
- Session B: `create_document(source)`, `insert("Shared content")`
- Session A: `create_document(dest)`, `vcopy(source → dest)`
- Any session: `compare_versions(dest, source)` → shared spans detected

**Provenance:** Finding 0022, section 4
**Co-occurring entries:** [SS-SESSION-STATE], [ST-CROSS-SESSION-VERSIONING], [ST-LINK-GLOBAL-VISIBILITY], [FC-SESSION-ACCOUNT-ISOLATION], [INV-GLOBAL-ADDRESS-UNIQUENESS], [EC-CONFLICT-COPY-NO-MERGE]

---

### INT-TRANSCLUSION-INSERT-ORDER

**Source:** Finding 0027

**What happens**: The LIFO insertion semantics apply equally to transclusion: when transcluding content to a position, the transcluded material appears before any existing content at that position. Sequential transclusions to the same position therefore appear in reverse chronological order in the resulting document.

**Why it matters for spec**: Transclusion and insert share the same position-insertion semantics. The spec for transclusion (copy) at a target position P must have the same shift postcondition as insert at position P. This means the ordering invariant for transclusion is: if `copy(src, target_pos=P)` is called twice, the second transclusion's content precedes the first's at P. Any formal model of document assembly via repeated transclusion must account for this reversal.

**Code references**: Implied by the shared insert-at-position mechanism; finding 0002 (transclusion content identity) confirms transclusion uses the same V-stream insertion path.

**Provenance**: Finding 0027a
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-DOCUMENT-LIFECYCLE], [PRE-RETRIEVE-CONTENTS], [ST-INSERT], [INT-LINK-FOLLOW-LIFECYCLE]

---

### INT-LINK-FOLLOW-LIFECYCLE

**Source:** Finding 0027

**What happens**: The link discovery and traversal pipeline has a lifecycle gap: `find_links` and `follow_link` can succeed and return references to documents that are not open, but the final step (`retrieve_contents` on the result) fails unless those documents are opened first. Specifically: (1) `find_links` searches the span-f index by I-address — no document handle needed; (2) `follow_link` reads link orgl endpoints and returns a SpecSet — no target document handle needed; (3) `retrieve_contents` resolves the SpecSet's V→I mappings within the target document — requires the target document to be open. This means a caller can discover and follow a link successfully, then fail to read the content it points to.

**Why it matters for spec**: The formal model of link traversal must specify that `follow_link` produces a deferred reference (SpecSet) whose resolution has a precondition. The spec should document the three-phase traversal pattern: discover (index-only) → follow (metadata-only) → resolve (content, requires open document). Any verification of link traversal completeness must include the open-document precondition on the resolve step. This is protocol-correct behavior — the FEBE protocol assumes the caller manages document lifecycle.

**Code references**:
- `find_links` — searches span-f by I-address, no `findorgl` call
- `follow_link` — reads link orgl endpoint spans, returns SpecSet
- `retrieve_contents` → `doretrievev` → `specset2ispanset` → `findorgl` — requires open document

**Concrete example**:
```
Setup:
  doc_A has text content and a link L
  doc_B transcludes content from doc_A
  doc_A is closed, doc_B is open

Step 1: find_links(doc_B, text_span) → finds link L (via I-address in span-f) ✓
Step 2: follow_link(L, LINK_SOURCE) → returns SpecSet S referencing doc_A ✓
Step 3: retrieve_contents(S) → FAILS (doc_A not open) ✗

Workaround:
  open_document(doc_A)
  retrieve_contents(S) → succeeds ✓
```

**Provenance**: Finding 0027b
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-DOCUMENT-LIFECYCLE], [PRE-RETRIEVE-CONTENTS], [ST-INSERT], [INT-TRANSCLUSION-INSERT-ORDER]

---

### INT-TRANSCLUSION-LINK-SEARCH

**Source:** Finding 0029

**What happens:** When content is transcluded (vcopy'd) to another document, the copy retains the original content identity (I-stream addresses). If the original content is deleted, links referencing that content become undiscoverable from the original document but remain discoverable from the copy, because the copy's V-stream still contains content at those I-stream addresses.

**Why it matters for spec:** Key interaction between transclusion and link search. Transclusion creates redundant discoverability paths — content identity is preserved across copies, so link search works from any document containing that content. Formalizable as: `vcopy(doc_a, span, doc_b) → (∀ link on span : find_links(doc_b, span) includes link)` and this survives `delete(doc_a, span)`.

**Code references:** Test `search_after_vcopy_source_deleted` in `febe/scenarios/links/search_endpoint_removal.py`.

**Concrete example:**
- Original document contains "linked", link created on it
- `vcopy("linked")` from Original to Copy
- Delete "linked" from Original
- `find_links(Original)` → `[]`
- `find_links(Copy)` → `[link_id]` (still found via the copy)

**Provenance:** Finding 0029, section 4
**Co-occurring entries:** [PRE-FIND-LINKS], [ST-FIND-LINKS], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE], [EC-SEARCH-SPEC-BEYOND-BOUNDS], [EC-TYPE-FILTER-NONFUNCTIONAL]

---

### INT-LINK-INSERT

**Sources:** Findings 0030, 0063

#### Finding 0030

**What happens**: Links attached to content via I-addresses survive insertion because I-addresses are immutable. A link targeting "CDE" (I-addresses I.3-I.5) remains valid after inserting "XY" at position 1.3. The link's I-address endpoints are unchanged. Link discovery via `find_links` still works. The V-address interpretation of the link shifts (the linked content now appears at 1.5-1.7 instead of 1.3-1.5), but the link itself references I-addresses and needs no update.

**Why it matters for spec**: Links are specified in I-space, not V-space. This means INSERT never invalidates any link. The formal property is: `forall link L :: INSERT does not modify L.from_iaddr or L.to_iaddr`. The V-space rendering of a link's endpoints changes (it must be recomputed from the current V-to-I mapping), but the link object is a frame-condition invariant of INSERT.

**Provenance**: Finding 0030

#### Finding 0063

**What happens:** CREATELINK breaks I-address contiguity for subsequent text INSERTs. After INSERT "ABC" (I-addresses 1.1–1.3) followed by CREATELINK, the next INSERT "DEF" receives I-addresses starting at 2 (not 1.4). This is because CREATELINK allocates an orgl in the granfilade via `createorglingranf`, which calls `findisatoinsertnonmolecule` to obtain an I-address. This allocation advances the granfilade's maximum I-address. When the next INSERT calls `findpreviousisagr` to determine the allocation point, it finds the link orgl's I-address as the highest and allocates above it — creating a gap in the text I-address sequence.

The gap is observable through `compare_versions`: a document with INSERT "ABC" + INSERT "DEF" (no link) yields 1 shared span pair, while INSERT "ABC" + CREATELINK + INSERT "DEF" yields 2 shared span pairs. The two text regions have non-contiguous I-address ranges because the link orgl's I-address sits between them.

**Why it matters for spec:** This is a cross-subsystem interaction: `create_link` modifies the I-address allocation sequence for subsequent `insert` operations, even though link orgls and text content occupy different V-space subspaces (2.x vs 1.x). The formal model must account for a shared I-address allocator across all granfilade entities. The allocation function is `next_iaddr(granf) = max_iaddr(granf) + 1` regardless of entity type — text characters and link orgls compete for the same monotonic sequence. The interaction predicate: `post(create_link) ⟹ next_text_iaddr > pre(create_link).next_text_iaddr + link_width`.

**Code references:**
- `do1.c:199-225` — `docreatelink` calls `createorglingranf`, which allocates an I-address for the link orgl
- `granf2.c:130-181` — `findisatoinsertgr` / `findisatoinsertmolecule` — shared allocation used by both text INSERT and link orgl creation
- `granf2.c:255-278` — `findpreviousisagr` — tree traversal returns the highest I-address regardless of entity type

**Concrete example:**
```
INSERT "ABC" → I-addresses 1.1, 1.2, 1.3 allocated in granfilade
CREATELINK   → link orgl gets I-address in higher range (consumes space up to ~2)
INSERT "DEF" → findpreviousisagr returns link orgl's I-address as max
               allocates at 2.1, 2.2, 2.3 (gap from text "ABC" at 1.1–1.3)

compare_versions reports 2 shared span pairs:
  span 1: source 1.1 width 0.3 (ABC)
  span 2: source 2   width 0.4 (DEF — note different I-address range)
```

**Provenance:** Finding 0063

**Co-occurring entries:** [ST-INSERT], [FC-GRANF-ON-DELETE], [FC-INSERT-IADDR], [INV-CRUM-BOUND], [INV-IADDR-IMMUTABILITY], [INV-MONOTONIC], [INT-TRANSCLUSION]

---

### INT-TRANSCLUSION

**Sources:** Findings 0030, 0034

#### Finding 0030

**What happens**: Transclusions (cross-document content sharing via `vcopy`) maintain identity across insertions because they reference I-addresses. If document B transcluded "CDE" from document A (sharing I-addresses I.3-I.5), and then text is inserted into document A shifting "CDE" from V-positions 1.3-1.5 to 1.5-1.7, the transclusion is unaffected. Document B still references I.3-I.5, and `compare_versions` between the documents still reveals shared identity.

**Why it matters for spec**: Transclusion is an I-space relationship, invariant under V-space mutations. The formal property: `forall doc A, doc B, iaddr set S :: if B.references(S) before INSERT into A, then B.references(S) after INSERT into A`. INSERT into one document has zero effect on other documents' I-address reference sets.

**Provenance**: Finding 0030

#### Finding 0034

**Detail level:** Useful

Transclusion (vcopy) preserves byte identity — the same bytes at the same I-addresses appear in multiple documents. Since content is encoding-opaque, transclusion inherits whatever encoding the original content had. Mixed encodings within a single document are possible if content is transcluded from sources using different encodings.

**Code references:**
- `context.c:308` — byte-level copy semantics

**Provenance:** Finding 0034

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [ST-INSERT], [FC-INSERT-IADDR], [INV-IADDR-IMMUTABILITY], [INV-SINGLE-CHAR-GRANULARITY], [INT-LINK-INSERT], [EC-ENCODING-BOUNDARY-SPLIT]

---

### INT-BERT-FEBE

**Source:** Finding 0050

**What happens:** The FEBE boundary is not a trust boundary — it is a coordination protocol. The back end trusts the front end to: (1) acquire BERT tokens before mutations, (2) respect write exclusivity, and (3) release tokens when done. The back end provides the BERT machinery for front ends to coordinate among themselves, but does not enforce compliance. A non-compliant front end can perform any mutation on any document.

This means the FEBE contract (front end obligations FE3: token acquisition) is a *cooperative protocol*, not an *enforced contract*. The back end's role is to maintain shared BERT state for coordination; the front end's role is to consult and obey it.

**Why it matters for spec:** The formal specification must explicitly model the trust assumption: all behavioral guarantees (write exclusivity, access control, concurrent safety) are conditional on front-end compliance with the BERT protocol. This is a system-level assumption, not a component-level invariant. Formalizable as: `system_correct ↔ (backend_correct ∧ all_frontends_compliant)`. Without this assumption, the only guarantee is that the BERT table itself is consistent.

**Code references:**
- `fns.c:84-98` — mutation handler trusts front end
- `granf1.c:17-41` — `findorgl` BERT check is internal only
- `bert.c:52-87` — BERT state is maintained but not used as a gate

**Provenance:** Finding 0050
**Co-occurring entries:** [SS-BERT], [PRE-INSERT], [INV-WRITE-EXCLUSIVITY], [EC-RESPONSE-BEFORE-CHECK]

---

### INT-DELETE-SUBSPACE-ASYMMETRY

**Source:** Finding 0055

**What happens:** INSERT and DELETE both preserve subspace isolation but through fundamentally different mechanisms. INSERT uses a deliberate structural guard: `findaddressofsecondcutforinsert()` computes a second knife blade at the next subspace boundary, causing `insertcutsectionnd` to classify cross-subspace entries as case 2 (no shift) before any arithmetic occurs. DELETE uses no such structural guard — its knife blades are `[origin, origin + width]` with no subspace boundary computation. Instead, DELETE relies on an incidental arithmetic property: `strongsub` returns the minuend unchanged when the subtrahend has a smaller exponent.

The asymmetry is a fragility risk. INSERT's protection is robust — it was designed intentionally (the source contains explanatory comments). DELETE's protection is accidental — there is no comment suggesting awareness of the exponent guard as a subspace protection mechanism. If `strongsub` were modified to handle cross-exponent subtraction correctly, DELETE would break subspace isolation while INSERT would remain safe.

**Why it matters for spec:** The formal spec should document this asymmetry. INSERT's frame condition is structurally guaranteed (by knife construction). DELETE's frame condition depends on an arithmetic invariant (`∀ width, entry : different_subspace(width, entry) ==> width.exp < entry.vpos.exp`). These are different proof obligations. INSERT's can be discharged by analyzing knife construction alone; DELETE's requires reasoning about tumbler exponent relationships across subspaces.

**Code references:**
- `insertnd.c:174-183` — `findaddressofsecondcutforinsert()` (INSERT's deliberate guard)
- `edit.c:40-43` — `deletend` knife construction (no equivalent guard)
- `tumble.c:534-547` — `strongsub` exponent check (DELETE's accidental guard)

**Provenance:** Finding 0055
**Co-occurring entries:** [SS-TUMBLER], [PRE-DELETE], [ST-DELETE], [FC-SUBSPACE], [EC-DEEPLY-ORPHANED-LINK]

---

### INT-DELETE-SPANF-DIVERGENCE

**Source:** Finding 0057

**What happens:** DELETE causes the POOM (granf) and spanfilade (spanf) to diverge. Before DELETE, both layers agree: the POOM says the document maps V-addresses to certain I-addresses, and the spanfilade says the document contains those I-addresses. After DELETE, the POOM no longer contains the mapping, but the spanfilade still claims the document contains those I-addresses. This divergence is permanent — no mechanism exists to reconcile the two layers.

**Why it matters for spec:** The formal model cannot treat spanf as derivable from POOM state. After any DELETE, the system may be in a state where `i ∈ spanf_index(D) ∧ ¬(∃ v : poom.D(v) = i)`. The invariant that holds is weaker than consistency: `∀ D, i : (∃ v : poom.D(v) = i) ⟹ i ∈ spanf_index(D)` (every live reference is indexed), but the converse is false (indexed does not imply live). This asymmetric invariant — spanf is a superset of current POOM associations — is the key structural property the spec must capture.

**Code references:**
- COPY path (both layers updated): `backend/do1.c:45-65` — `insertpm` (granf) + `insertspanf` (spanf)
- DELETE path (only granf updated): `backend/do1.c:162-171` — `deletevspanpm` (granf only)
- Same pattern for links: Creating a link calls `insertendsetsinspanf`; deleting does not clean up (Finding 0024)

**Provenance:** Finding 0057
**Co-occurring entries:** [ST-DELETE], [INV-SPANF-WRITE-ONLY], [EC-STALE-SPANF-REFERENCE]

---

## Edge Cases

> Boundary and unusual behavior

### EC-ORPHANED-LINK

**Sources:** Findings 0005, 0024

#### Finding 0005

**What happens:** When the entire content of a link's source span is deleted from all documents, the link enters an "orphaned" state: it exists in the link enfilade and can be traversed via `follow_link()` (returning empty content), but it cannot be discovered via `find_links()` because no document contains content identities matching its endpoints. The finding notes this as an open question — whether there should be a mechanism to find orphaned links.

**Why it matters for spec:** This is an edge case at the boundary of link persistence and link discoverability. The spec must distinguish between link existence (`link ∈ links(system)`, always true once created) and link discoverability (`∃ doc :: find_links(doc) returns link`, conditional on content reference survival). The predicate `orphaned(link) ≡ link ∈ links(system) ∧ ¬∃ doc :: discoverable(link, doc)` identifies links that exist but are unreachable via content search. Whether the system should provide an alternative discovery mechanism for orphaned links is a design question.

**Concrete example:**
- Link on "here" in document A
- Delete "here" from A (and no other document references those content identities)
- `follow_link(link)` → succeeds, returns empty span
- `find_links(A)` → does not return the link
- Link exists but is undiscoverable through normal content-based search

**Code references:** Test `link_when_source_span_deleted` (PASS)

**Provenance:** Finding 0005

#### Finding 0024

**What happens:** Finding 0024 provides a comprehensive behavior matrix for orphaned links across all deletion combinations. The key addition beyond Finding 0005 is the full matrix and the anomalous type-endset behavior:

| Deleted Content         | `find_links` | source | target | type   |
|------------------------|-------------|--------|--------|--------|
| Nothing                | Works       | Works  | Works  | Works  |
| Source text only        | Empty       | Empty  | Works  | Works  |
| Target text only        | Works       | Works  | Empty  | Works  |
| Both source & target    | Empty       | Empty  | Empty  | Empty* |
| Home doc text only      | Works       | Works  | Works  | Works  |

The critical asymmetry: `find_links(source_specs)` requires content at the source address to succeed, while `follow_link(link_id)` always works if you know the link ID. Link IDs function as permanent capability tokens — knowing one grants access to the link even when content-based discovery fails.

**Why it matters for spec:** Extends EC-ORPHANED-LINK from Finding 0005 with two new properties:

1. `find_links` discoverability depends on which endpoint is queried: deleting source makes source-based discovery fail but target-based still works, and vice versa. Formally: `source_deleted(link) ⟹ find_links(source_specs) ∌ link ∧ find_links(NOSPECS, target_specs) ∋ link` (when target content survives).

2. The type endset anomaly when both endpoints are deleted (marked * above) — `follow_link(link_id, LINK_TYPE)` returns empty even though the type references the bootstrap document, which was not deleted. This is either a bug or an undocumented dependency of type resolution on endpoint resolution.

**Concrete example:**
```
Link: source in doc_B ("source text"), target in doc_C ("target text"), type = QUOTE

After deleting source text from doc_B:
  find_links(doc_B content)    → [] (empty - source content gone)
  follow_link(link, SOURCE)    → [] (empty span)
  follow_link(link, TARGET)    → "target text" (works)
  follow_link(link, TYPE)      → QUOTE type (works)

After ALSO deleting target text from doc_C:
  follow_link(link, SOURCE)    → [] (empty)
  follow_link(link, TARGET)    → [] (empty)
  follow_link(link, TYPE)      → [] (empty — UNEXPECTED)
```

**Code references:** Tests `orphaned_link_source_all_deleted`, `orphaned_link_target_all_deleted`, `orphaned_link_both_endpoints_deleted`, `orphaned_link_discovery_by_link_id` (all PASS).

**Provenance:** Finding 0024, Orphaned Link Behavior Matrix and Semantic Insight 4.

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [ST-DELETE], [ST-REMOVE], [FC-LINK-PERSISTENCE], [INV-LINK-CONTENT-TRACKING], [INV-LINK-PERMANENCE], [INT-LINK-TRANSCLUSION]

---

### EC-COMPARE-VERSIONS-LINK-CRASH

**Sources:** Findings 0006, 0009, 0018

#### Finding 0006

**What happens:** The `compare_versions()` operation crashes the backend (abort) when comparing documents that contain links. This is a known bug — the comparison logic does not handle the link enfilade correctly, causing a fatal error rather than returning a result or a clean error.

**Why it matters for spec:** This is a known defect, not intended behavior, but it constrains what the spec can assume about compare_versions: the operation's domain currently excludes documents with links. A defensive precondition would be `pre_compare_versions(doc1, doc2) ≡ links(doc1) = ∅ ∧ links(doc2) = ∅`, though this is a bug to be fixed rather than a design constraint. The spec should note this as a known implementation limitation.

**Concrete example:**
- Document A contains text with a link attached
- `compare_versions(A, B)` → backend aborts (crash)

**Code references:** `compare_versions()` (backend)

**Provenance:** Finding 0006

## Omit

The following sections of Finding 0006 are omitted from analysis:

- **API Type Requirements (SpecSet vs VSpec):** Client-side type wrapper details for the FEBE protocol. The distinction between VSpec and SpecSet is a protocol serialization concern, not a semantic property of the data model.
- **Debug Output:** Backend stderr logging details (xgrabmorecore, levelpush, etc.) are implementation internals for debugging, not behavioral properties.
- **Testing Notes:** Test infrastructure details (how to run golden tests, debug scripts) are not spec-relevant.

#### Finding 0009

**What happens**: The `compare_versions` operation assumes a uniform content model: convert V-spans to I-spans for both documents, intersect I-spans to find shared content, map back to V-spans. When the document contains links, the `0.x` V-subspace produces link orgl ISAs as I-addresses. These are in a completely different address space from permascroll I-addresses and will never intersect with text I-addresses. The code paths in `correspond.c` do not handle the case where some V-spans produce no common I-spans, leading to crashes. The nested loop structure in `correspond.c` assumes each ispan matches at most one vspec, which the link subspace violates.

**Why it matters for spec**: This is a precondition violation — `compare_versions` requires that its input V-spans come only from the text subspace (`1.x`). Alternatively, the spec could require `compare_versions` to filter to text subspace before comparison. Either way, the formal spec must make explicit that I-span intersection is only meaningful within the same I-address type.

**Code references**:
- `correspond.c` — nested loop assumes 1:1 ispan-to-vspec correspondence
- `orglinks.c:404-422` — `permute()` performs type-agnostic conversion

**Concrete example**:
```
Document A vspanset after link: at 0 for 0.1, at 1 for 1
Document B vspanset (text only): at 1.1 for 0.16

compare_versions(A, B):
  A's 0.x → I-addresses are link ISAs (e.g., 1.1.0.1.0.2)
  B's 1.x → I-addresses are permascroll (e.g., 2.1.0.5.0.1)
  Intersection of link ISAs ∩ permascroll = empty
  → correspond.c loop encounters empty match → crash
```

**Provenance**: Finding 0009, Bug 0009

#### Finding 0018

**What happens:** Deep version chains (3+ versions with content added at each level) cause the backend to crash when `compare_versions` or `FINDDOCSCONTAINING` is called. This limits the testable depth of version-chain identity preservation.

**Why it matters for spec:** This is a known implementation limitation (Bug 0012). The spec should define the expected behavior for arbitrary version chain depths, even though the current implementation fails beyond depth 2.

**Code references:** Bug 0012.

**Provenance:** Finding 0018, Key Finding 5 note.

**Co-occurring entries:** [SS-CONTENT-IDENTITY], [SS-DUAL-ENFILADE], [PRE-COMPARE-VERSIONS], [PRE-OPEN-DOC], [PRE-REARRANGE], [ST-INSERT], [ST-REARRANGE], [ST-REMOVE], [ST-VCOPY], [ST-VERSION-CREATE], [FC-CONTENT-SPANF-ISOLATION], [FC-SUBSPACE], [INV-REARRANGE-IDENTITY], [INV-SUBSPACE-CONVENTION], [INV-TRANSITIVE-IDENTITY]

---

### EC-EMPTY-DOC

**Sources:** Findings 0007, 0058, 0066

#### Finding 0007

**What happens:** Empty documents can be versioned. The resulting version is also empty and can have content added independently. Adding content to the version does not affect the empty original. This is a boundary case confirming that version-create has no precondition on document size — the operation is valid even when the document's reference set is empty.

**Why it matters for spec:** The precondition for version-create is: `doc exists` (no minimum content requirement). The postcondition when the original is empty: `references(version) = ∅`. This edge case confirms that ST-VERSION-CREATE and FC-DOC-ISOLATION hold at the empty-set boundary.

**Concrete example:**
- Empty document: (no content, reference set = ∅)
- Version: (no content initially, reference set = ∅)
- After insert to version: Version has "Content in version only"
- Original: still empty

**Code references:** Test `version_of_empty_document`

**Provenance:** Finding 0007

#### Finding 0058

**What happens:** Two distinct "empty document" states exist that are structurally non-equivalent:

| State | Height | Fullcrum sons | Bottom nodes |
|-------|--------|---------------|--------------|
| Never-filled (`createenf`) | 1 | 1 (zero-width bottom) | 1 |
| After delete-everything | H (from prior growth) | 2+ (empty intermediates) | 0 |

A never-filled document has a minimal height-1 tree with one zero-width bottom node. A document where all content was deleted has a taller tree with empty intermediate nodes and no bottom nodes at all. Both return empty content on retrieve, but their internal structures differ.

This non-equivalence has concrete consequences: Finding 0064 confirms that the empty-after-delete state causes INSERT and VCOPY to crash (Bug 0019) because `firstinsertionnd()` assumes a bottom crum always exists. When `findleftson()` returns NULL (no bottom nodes), the code dereferences a null pointer.

**Why it matters for spec:** The formal model must distinguish these two empty states, or at minimum specify that delete-everything does NOT restore the initial state. The predicate `is_empty(doc) ≡ dom(poom(doc)) = ∅` is true for both states, but `is_initial(doc) ≡ is_empty(doc) ∧ enf.height(doc) = 1 ∧ has_bottom_node(doc)` is only true for never-filled documents. The crash on reinsertion into a deleted-everything document means the current implementation has a hidden precondition: `pre_insert(doc) ⟹ has_bottom_node(enf(doc))`, which never-filled documents satisfy but delete-everything documents violate.

**Code references:**
- `backend/credel.c:492-516` — `createenf`: produces height-1 with one bottom node
- `backend/edit.c:31-76` — `deletend`: removes all bottom nodes without creating replacements
- Finding 0064 / Bug 0019 — crash on INSERT after delete-everything (null bottom node)

**Provenance:** Finding 0058

#### Finding 0066

**What happens:** Empty 2D enfilades are detected by checking that BOTH `cdsp` and `cwid` are zero (`isemptyenfilade` at `genf.c:97-116`). This is necessary because a non-empty 2D enfilade typically has non-zero `cdsp` (the minimum address). In contrast, empty GRAN enfilades only check that `cwid` is zero, because GRAN root displacement is always zero.

When all children of a 2D enfilade are deleted, `setwispnd` clears both `cdsp` and `cwid` to zero (`wisp.c:187-189`), restoring the empty state.

**Why it matters for spec:** The emptiness predicate is type-dependent. For GRAN: `empty(e) iff e.cwid = 0`. For POOM/SPAN: `empty(e) iff e.cwid = 0 AND e.cdsp = 0`. This asymmetry must be captured in the formal model.

**Code references:**
- `backend/genf.c:97-116` — `isemptyenfilade`: type-dependent emptiness check
- `backend/wisp.c:187-189` — `setwispnd`: clears both fields when all children deleted

**Provenance:** Finding 0066

**Co-occurring entries:** [SS-ENFILADE-TREE], [SS-VERSION-ADDRESS], [ST-DELETE], [ST-INSERT], [ST-VERSION-CREATE], [FC-DOC-ISOLATION], [INV-ENFILADE-MINIMALITY], [INV-ENFILADE-RELATIVE-ADDRESSING], [INV-TRANSITIVE-IDENTITY], [INT-LINK-TRANSCLUSION], [INT-VERSION-TRANSCLUSION]

---

### EC-RETRIEVE-VSPANSET-BOTH-SUBSPACES

**Source:** Finding 0010

**What happens**: The `retrieve_vspanset` operation returns the full V-extent of a document, including both the link subspace (`0.x`) and text subspace (`1.x`). Any caller that uses "full document extent" as input to another operation (compare_versions, vcopy, retrieve_contents) inadvertently includes link references. This is the root cause of multiple abstraction leaks: the unified storage model provides no built-in way to request "text content only."

**Why it matters for spec**: The spec should either: (a) define `retrieve_vspanset` as returning all subspaces and require callers to filter, or (b) provide a variant that returns text-only spans. Either choice creates a formal obligation — if (a), every operation using vspanset results must state a subspace precondition; if (b), the variant's postcondition must guarantee `V >= 1.0` for all returned spans.

**Code references**:
- Debug output evidence: `<VSpec in 1.1.0.1.0.1, at 0 for 0.1, at 1 for 1>` (both subspaces)

**Concrete example**:
```
Document with text and one link:
  retrieve_vspanset → {V 0.1 for 0.1, V 1.1 for 0.16}

Caller uses full vspanset for compare_versions → crash (Bug 0009)
Caller uses full vspanset for vcopy → copies link ISAs as text
Caller uses full vspanset for retrieve_contents → garbage bytes for link entries
```

**Provenance**: Finding 0010
**Co-occurring entries:** [PRE-DELETE], [PRE-RETRIEVE-CONTENTS], [PRE-VCOPY], [INV-SUBSPACE-CONVENTION], [INT-LINK-RETRIEVAL]

---

### EC-ERROR-ABORT

**Source:** Finding 0011

**What happens:** When implicit contracts are violated, the system's error handling is to crash immediately via `qerror`/`abort` in `genf.c:546`. There is no recovery path, no error return, and no graceful degradation. Violations of conventions produce fatal aborts rather than error codes or exceptions.

**Why it matters for spec:** This establishes that the implementation treats precondition violations as undefined behavior terminated by abort. For specification purposes, this confirms that preconditions are hard requirements: violating them does not produce a defined error state, it produces program termination. The spec should model precondition violations as operations that are simply not defined, matching the implementation's "crash on invalid" behavior.

**Code references:**
- `backend/green/genf.c:546` — `qerror` calls `fprintf` then `abort()`

**Concrete example:**
- Before: Operation encounters an invalid internal state (null pointer, unexpected data type)
- After: Process terminates via `abort()` with a message to stderr. No state is returned. No partial result.

**Provenance:** Finding 0011
**Co-occurring entries:** [SS-DUAL-ENFILADE], [PRE-COMPARE-VERSIONS], [PRE-INSERT], [INV-SUBSPACE-CONVENTION]

---

### EC-VSPAN-MISLEADING-SIZE

**Sources:** Findings 0017, 0035

#### Finding 0017

**What happens**: For a document containing both text and links, `retrieve_vspan` returns a single span that bridges the link subspace (`0.x`) and text subspace (`1.x`). The example shows a span `1.1 for 1.2`, which implies continuous content from position `1.1` to position `2.3`. In reality, there is a gap — positions between `0.x` and `1.x` are in different subspaces and do not represent contiguous content. Using this span for size calculation or content iteration will yield incorrect results: the span's width overstates the actual content extent.

**Why it matters for spec**: The bounding span returned by `retrieve_vspan` does not satisfy a contiguity invariant — the V-addresses within the span are not necessarily occupied. The formal spec should distinguish between a *bounding span* (smallest span containing all content) and a *content span* (span where every V-position maps to an I-address). The `retrieve_vspan` result is the former, while individual spans in a `retrieve_vspanset` result are the latter.

**Code references**:
- Golden tests: `golden/documents/retrieve_vspan*.json`

**Concrete example**:
```
retrieve_vspan returns: 1.1 for 1.2
  Naive size interpretation: 1.2 units of content
  Actual content: 0.1 units in link subspace + ~1.0 units in text subspace
  Gap: V-positions between 0.x and 1.x are unoccupied
```

**Provenance**: Finding 0017

#### Finding 0035

**What happens:** RETRIEVEDOCVSPAN returns a raw bounding-box width for documents containing links. For a document with 10 chars of text and 1 link, it returns `1.1 for 1.2` — a width that spans both the link subspace (0.x) and text subspace (1.x). This value is neither the text extent nor the link extent; it is the root node's V-dimension width, an internal structural artifact.

**Why it matters for spec:** A precondition for any spec relying on document extent must specify which operation was used. RETRIEVEDOCVSPAN's output violates the subspace convention for mixed-content documents. The spec should mark this operation as producing a raw structural value, not a semantically meaningful V-span.

**Code references:**
- `retrievevspanpm()`: `backend/orglinks.c:165-172`
- `retrievedocumentpartofvspanpm()`: `backend/orglinks.c:155-162` — identical "kluge" twin

**Provenance:** Finding 0035 (section 1), Bug 0011

**Co-occurring entries:** [SS-VSPAN-VS-VSPANSET], [PRE-CONTENT-ITERATION], [ST-FIND-LINKS], [ST-PAGINATE-LINKS], [ST-RETRIEVE-ENDSETS], [INT-SPORGL-LINK-INDEX], [EC-CURSOR-INVALIDATION]

---

### EC-PIVOT-LINK-FRAGMENTATION

**Source:** Finding 0019

When linked content is rearranged via pivot, the link's endsets become fragmented into multiple spans, and the link itself may appear duplicated in `find_links` results.

Concrete example:
```
Before: "ABCDEFGH" — link on "CD" at V 1.3 width 0.2
Pivot:  swap BC and DE
After:  "ADEBCFGH" — endsets report FOUR spans:
        - 1.2 width 0.1 (twice)
        - 1.5 width 0.1 (twice)
find_links returns the same link TWICE
```

This suggests that rearrangement can cause internal fragmentation in the enfilade structure that is visible through the endset API. The duplication may be a bug or may reflect the internal representation of fragmented spans.

**Why it matters for spec**: The postcondition for pivot/rearrange must account for endset fragmentation. The spec may need to define whether duplicated spans in endset results are normalized or left as-is. This is an edge case that constrains how rearrangement interacts with the link subsystem.

**Code references**: Tested via `endsets/endsets_after_pivot` scenario.

**Provenance**: Finding 0019, section 3
**Co-occurring entries:** [SS-LINK-ENDPOINT], [INV-LINK-CONTENT-TRACKING], [INT-LINK-VERSION], [EC-MULTISPAN-LINK-DUPLICATION]

---

### EC-MULTISPAN-LINK-DUPLICATION

**Source:** Finding 0019

Creating a link with multiple source spans works, but `retrieve_endsets` may return duplicate spans:

```
Link source: ["First" at V 1.1, "second" at V 1.16]
Endsets return: 3 spans (1.16 appears twice)
```

This duplication in multi-span link endsets may be related to the same internal fragmentation mechanism observed with pivot (EC-PIVOT-LINK-FRAGMENTATION).

**Why it matters for spec**: Multi-span link creation postconditions must specify whether endset results are deduplicated. This observed duplication may indicate an implementation artifact rather than intended semantics.

**Code references**: Tested via `endsets/endsets_multispan_link` scenario.

**Provenance**: Finding 0019, section 7
**Co-occurring entries:** [SS-LINK-ENDPOINT], [INV-LINK-CONTENT-TRACKING], [INT-LINK-VERSION], [EC-PIVOT-LINK-FRAGMENTATION]

---

### EC-SELF-LINK

**Source:** Finding 0020

Internal links (source and target in the same document) are a valid edge case that the system handles without error. This contradicts an earlier assumption documented in `scenario_bidirectional_links` that internal links would be rejected. The system treats same-document links identically to cross-document links.

Related edge cases from other tests extend the link model further:
- Same span can have multiple links to different targets (`links/overlapping_links_different_targets`)
- Intermediate nodes can be both link sources and link targets (`links/link_chain`)

**Why it matters for spec:** Bounded checking should include same-document link scenarios. Any Alloy model of links should not constrain `source.doc != target.doc`.

**Code references:** Tests `links/self_referential_link`, `links/link_chain`, `links/overlapping_links_different_targets`

**Provenance:** Finding 0020
**Co-occurring entries:** [SS-LINK-ENDPOINT], [PRE-LINK-CREATE], [ST-LINK-CREATE]

---

### EC-CONFLICT-COPY-NO-MERGE

**Source:** Finding 0022

**What happens:** When multiple sessions open the same document with `CONFLICT_COPY`, each session gets an independent copy. Changes made in different sessions are NOT merged — the final state depends on which copy is accessed. This means true concurrent editing requires application-level merge logic.

**Why it matters for spec:** This is an important edge case for concurrent access semantics. `CONFLICT_COPY` does not provide automatic conflict resolution or merging. The system makes no guarantees about combining concurrent edits — only one session's changes survive in a given read. This is a deliberate design boundary, not a bug.

**Concrete example:**
- Document contains: `"AAAA____BBBB"`
- Session A: opens with CONFLICT_COPY, changes `AAAA` → `XXXX`
- Session B: opens with CONFLICT_COPY, changes `BBBB` → `YYYY`
- Final read: `"XXXX____BBBB"` (only A's changes visible)

**Provenance:** Finding 0022, section 5
**Co-occurring entries:** [SS-SESSION-STATE], [ST-CROSS-SESSION-VERSIONING], [ST-LINK-GLOBAL-VISIBILITY], [FC-SESSION-ACCOUNT-ISOLATION], [INV-GLOBAL-ADDRESS-UNIQUENESS], [INT-CROSS-SESSION-TRANSCLUSION]

---

### EC-HOMEDOCIDS-FILTER-BROKEN

**Source:** Finding 0025

**What happens**: The `homedocids` filter parameter in `find_links` has no observable effect. When filtering by a specific home document, all links are returned regardless of their home document, producing the same results as an unfiltered query. The filter is accepted without error but does not constrain the result set.

**Why it matters for spec**: This is a known deviation between intended and actual behavior (Bug 0015). The spec should define the intended semantics: `find_links(homedocids=H) = {link ∈ all_links | link.home ∈ H ∧ matches(link, other_filters)}`. The current implementation violates this — it returns all matching links regardless of home document. This distinction matters for verification: the spec captures intended behavior, and this bug is a known non-conformance.

**Code references**: Bug 0015; tests `links/find_links_filter_by_homedocid`, `links/find_links_homedocids_multiple`, `links/find_links_homedocids_no_match`.

**Provenance**: Finding 0025
**Co-occurring entries:** [SS-LINK-HOME-DOCUMENT], [PRE-FIND-LINKS], [ST-ADDRESS-ALLOC]

---

### EC-LINK-TOPOLOGY

**Source:** Finding 0026

**What happens:** Several complex link topology patterns were tested and all work correctly:

| Pattern | Setup | Result |
|---------|-------|--------|
| Circular | A → B → C → A (3 links) | All links discoverable |
| Diamond | A → B, A → C, B → D, C → D (4 links) | All links discoverable |
| Star incoming | P1 → Hub, P2 → Hub, P3 → Hub | All links discoverable |
| Star outgoing | Hub → P1, Hub → P2, Hub → P3 | All links discoverable |
| Bidirectional | A ⟷ B (2 links) | Both links discoverable |
| Reverse traversal | Find path D ← C ← B ← A (3 links) | Chain traversable |

None of these topologies cause failures, missing links, or duplicate artifacts. Circular references do not cause infinite loops or errors in `find_links`.

**Why it matters for spec:** Confirms that link discovery has no topology-dependent edge cases. The `find_links` operation is purely based on content-identity intersection and does not depend on link graph structure. The spec need not restrict link topologies — circular, diamond, star, and bidirectional patterns are all valid. Formally: there are no preconditions on link graph shape for `create_link` or `find_links`.

**Code references:** Test `links/link_to_transcluded_content` (additional patterns section)

**Provenance:** Finding 0026
**Co-occurring entries:** [INV-LINK-CONTENT-TRACKING], [INT-LINK-TRANSCLUSION]

---

### EC-SELF-TRANSCLUSION

**Sources:** Findings 0028, 0039

#### Finding 0028

**What happens**: A document can transclude content from itself. Given document containing "Original", vcopy of "Orig" (positions 1–4) to the end produces "OriginalOrig". The transcluded portion shares I-position identity with the original content within the same document.

**Why it matters for spec**: The precondition for vcopy must NOT include `source_doc != target_doc`. Self-transclusion is a valid operation. The postcondition must handle the case where source and destination V-ranges are in the same document: `vcopy(doc, src_span, doc, target_pos)` is valid and the resulting content at target_pos shares I-positions with content at src_span. This enables recursive document structures where the same content identity appears at multiple V-positions within one document.

**Code references**: Test `edgecases/self_transclusion`

**Concrete example**:
```
Pre-state:  doc V-stream = "Original" (positions 1.1..1.8)
Operation:  vcopy(doc, Span(1.1, 0.4), doc, end)  — copy "Orig" to end
Post-state: doc V-stream = "OriginalOrig" (positions 1.1..1.12)
  I-positions of "Orig" at 1.9..1.12 == I-positions of "Orig" at 1.1..1.4
```

**Provenance**: Finding 0028 §2

#### Finding 0039

**What happens:** Internal transclusion (copying content within the same document) is a valid operation that the system handles without special-casing. A document can reference the same I-address at N distinct V-positions (tested with N=2 and N=3). All N positions are recognized as sharing identity: `compare_versions` between any pair reports shared content. The N-to-1 relationship (N V-positions to 1 I-address) scales correctly — all pairwise comparisons among three positions sharing one I-address report shared content.

**Why it matters for spec:** Self-transclusion is an edge case that validates the generality of the POOM multimap model. The spec need not distinguish internal from external transclusion — both are instances of "add a V-position reference to an existing I-address." The only difference is that source and target are the same document. The N-ary case (3+ copies) confirms there is no implicit cardinality constraint on how many V-positions can reference one I-address.

**Concrete example:**
```
doc has character "B" at V-positions 1.2, 1.4, 1.5 — all referencing I-address i_B

Pairwise comparisons:
  compare(V 1.2, V 1.4) → shared (same I-address)
  compare(V 1.2, V 1.5) → shared (same I-address)
  compare(V 1.4, V 1.5) → shared (same I-address)

No limit observed on number of V-positions per I-address.
```

**Code references:** Test `internal/internal_transclusion_multiple_copies`

**Provenance:** Finding 0039

**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [SS-POOM-MULTIMAP], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [ST-VCOPY], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-LINK-IDENTITY-DISCOVERY], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-COMPARISON]

---

### EC-SELF-COMPARISON

**Source:** Finding 0028

**What happens**: Comparing a document with itself via `compare_versions` returns the entire document content as shared. The result is a pair of identical spans, each covering the full document.

**Why it matters for spec**: `compare_versions` is reflexive: `compare_versions(doc, doc) == [(full_span(doc), full_span(doc))]`. Every character's I-position is trivially shared with itself. This is a boundary condition that any formal model of `compare_versions` must satisfy — the identity comparison. It follows directly from the definition (shared content = content with matching I-positions) but serves as a useful sanity predicate: `forall doc :: compare_versions(doc, doc) != []` whenever `doc` is non-empty.

**Code references**: Test `edgecases/self_comparison`

**Concrete example**:
```
doc contains "Hello, World!!!" (17 chars)
compare_versions(doc, doc) → [(Span(1.1, 0.17), Span(1.1, 0.17))]
  Both spans are identical — every character shares identity with itself
```

**Provenance**: Finding 0028 §7
**Co-occurring entries:** [SS-ADDRESS-SPACE], [SS-LINK-ENDPOINT], [SS-LINK-SPACE], [PRE-LINK-CREATE], [PRE-ZERO-WIDTH], [ST-FIND-LINKS], [ST-FOLLOW-LINK], [FC-DOC-ISOLATION], [INV-IDENTITY-OVERLAP], [INV-SINGLE-CHAR-GRANULARITY], [INV-VSPAN-CONSOLIDATION], [INT-LINK-TRANSCLUSION], [EC-SELF-TRANSCLUSION]

---

### EC-SEARCH-SPEC-BEYOND-BOUNDS

**Source:** Finding 0029

**What happens:** When a search spec references positions that no longer exist in the V-stream (e.g., after deletion shrinks the document), `find_links()` does not error. It gracefully intersects with whatever content remains, still finding links on surviving content.

**Why it matters for spec:** Edge case for find_links — stale or oversized specs are tolerated. The backend clips the spec to the current V-stream extent rather than rejecting it. This means callers need not track document size changes before searching.

**Code references:** Test `search_spanning_deleted_boundary` in `febe/scenarios/links/search_endpoint_removal.py`.

**Concrete example:**
- Document: "Start MIDDLE End link text" (26 chars), link on "link"
- Search spec: positions 1–26
- Delete "MIDDLE " (7 chars) → document now 19 chars
- `find_links(original 1-26 spec)` → `[link_id]` (still works despite spec exceeding bounds)

**Provenance:** Finding 0029, section 8
**Co-occurring entries:** [PRE-FIND-LINKS], [ST-FIND-LINKS], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE], [INT-TRANSCLUSION-LINK-SEARCH], [EC-TYPE-FILTER-NONFUNCTIONAL]

---

### EC-TYPE-FILTER-NONFUNCTIONAL

**Source:** Finding 0029

**What happens:** Type filtering with `find_links(source, NOSPECS, type_spec)` returns empty results even when unfiltered search finds links of those types. This is a pre-existing issue, not specific to endpoint removal.

**Why it matters for spec:** Signals that type-based link search may require a different specset format, have undocumented semantics, or be a backend limitation. Any formal spec of find_links should note that the type parameter's behavior is unverified/possibly broken.

**Code references:** Test `search_type_filter_with_removed_endpoints` in `febe/scenarios/links/search_endpoint_removal.py`. See also `golden/links/find_links_by_type.json`.

**Concrete example:**
- `find_links(source)` → `[jump, quote, footnote]` (3 links found)
- `find_links(source, NOSPECS, JUMP_TYPE)` → `[]` (empty)
- `find_links(source, NOSPECS, QUOTE_TYPE)` → `[]` (empty)

**Provenance:** Finding 0029, section 9
**Co-occurring entries:** [PRE-FIND-LINKS], [ST-FIND-LINKS], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE], [INT-TRANSCLUSION-LINK-SEARCH], [EC-SEARCH-SPEC-BEYOND-BOUNDS]

---

### EC-ENCODING-BOUNDARY-SPLIT

**Source:** Finding 0034

**Detail level:** Essential

Partial retrieval and link endpoints can split multi-byte character encodings because all operations use byte addressing. The backend performs no character boundary validation on any operation. Retrieving a sub-range of a V-span that straddles a multi-byte character boundary returns byte sequences that are invalid in the original encoding.

**Why it matters for spec:** The formal model does not need to model encoding validity — but any frontend/application layer must. The spec should document that partial retrieval returns `seq<byte>` with no encoding guarantee. This is not a bug but a design property: the backend is encoding-agnostic by construction. Preconditions on retrieval do not include encoding boundary checks.

**Concrete example:**
```
Content: "caf\xc3\xa9" (5 bytes, UTF-8 for "cafe with e-acute")
V-space: 1.1 through 1.5

Retrieve V-span [1.1, 1.4]: Returns bytes "caf\xc3" — invalid UTF-8
  (the \xc3 is the first byte of a 2-byte sequence, missing its continuation \xa9)

Retrieve V-span [1.5, 1.5]: Returns byte "\xa9" — invalid UTF-8
  (a continuation byte without its leading byte)
```

**Code references:**
- `context.c:308` — `movmem()` copies arbitrary byte ranges with no boundary check

**Provenance:** Finding 0034
**Co-occurring entries:** [SS-CONTENT-IDENTITY], [INV-SINGLE-CHAR-GRANULARITY], [INT-TRANSCLUSION]

---

### EC-CURSOR-INVALIDATION

**Source:** Finding 0035

**What happens:** In FINDNEXTNLINKSFROMTOTHREE, if the cursor link ISA no longer appears in the search results (e.g., because the link was deleted between paginated calls), the cursor walk falls off the end of the list and returns an empty set with count=0. This is not an error condition — it returns TRUE with an empty result.

**Why it matters for spec:** The pagination mechanism has no stable cursor guarantee. Between calls, link creation or deletion can change the result set, causing: missed links, duplicate links, or cursor invalidation. The spec must model pagination as a snapshot-less stateless query — each call is independent with no consistency guarantees across calls.

**Code references:**
- Cursor walk: `backend/spanf1.c:130-136` — if `tumblereq` never matches, `linkset` becomes NULL
- Empty result path: `backend/spanf1.c:138-141` — sets `*nextlinksetptr = NULL`, `*nptr = 0`

**Provenance:** Finding 0035 (section 5)
**Co-occurring entries:** [SS-VSPAN-VS-VSPANSET], [ST-FIND-LINKS], [ST-PAGINATE-LINKS], [ST-RETRIEVE-ENDSETS], [INT-SPORGL-LINK-INDEX], [EC-VSPAN-MISLEADING-SIZE]

---

### EC-APPEND-NO-DOCISPAN

**Source:** Finding 0036

**What happens:** APPEND (`doappend`) does NOT create DOCISPAN entries. The source code shows `insertspanf(taskptr,spanf,docptr,textset,DOCISPAN)` is explicitly commented out in the APPEND implementation, with a note suggesting `appendpm` may include the spanf insertion internally (though the comment is ambiguous: `/*zzz dies this put in granf?*/`). This means content added via APPEND is not discoverable through `find_documents`.

**Why it matters for spec:** APPEND and INSERT have different postconditions regarding discoverability:
- INSERT: content discoverable (`DOCISPAN` entries created)
- APPEND: content NOT discoverable (`DOCISPAN` entries omitted)

The spec must distinguish these operations. APPEND postcondition should explicitly state: `spanf' = spanf` (no DOCISPAN change). This is a significant semantic distinction — APPEND creates content that exists in the granf but is invisible to reverse-index queries.

**Code references:**
- `do1.c:25-31` — `doappend()` with commented-out `insertspanf` call
- Comment: `/*zzz dies this put in granf?*/` — suggests uncertainty about whether `appendpm` handles DOCISPAN internally

**Concrete example:**
```
APPEND "Some text" to document D
  granf: D's orgl updated with new content
  spanf: unchanged — no DOCISPAN entries created
  find_documents("Some text") → []   # not discoverable
```

**Provenance:** Finding 0036.
**Co-occurring entries:** [SS-DOCISPAN], [PRE-INSERT], [ST-INSERT], [ST-INSERT-ACCUMULATE], [FC-CONTENT-SPANF-ISOLATION]

---

### EC-LINK-PARTIAL-SURVIVAL

**Source:** Finding 0037

**What happens:** Because each I-span in a link endset independently tracks its content, partial survival is possible. If document A (source of "AA") is deleted but document B (source of "BB") remains, the link endset retains the I-span for "BB" while the I-span for "AA" becomes unresolvable. The link survives partially — it still points to the "BB" content.

**Why it matters for spec:** The link validity predicate is per-I-span, not per-endset: `valid_endset(endset) = ∃ sporgl ∈ endset :: resolvable(sporgl)`. A link with a partially valid endset is still a valid link. This extends the ST-REMOVE postcondition (from finding 0004): content removal affects individual sporgls within an endset independently, never atomically invalidating the entire endset.

**Code references:**
- Implied by the per-sporgl structure in `sporgl.c:49-58`

**Provenance:** Finding 0037
**Co-occurring entries:** [SS-LINK-ENDPOINT], [ST-LINK-CREATE], [INT-LINK-TRANSCLUSION]

---

### EC-VSPAN-NORMALIZATION

**Source:** Finding 0038

**What happens**: `retrievedocvspanset` output representation depends on document content: when both text and links exist, links are reported with normalized start `"0"` and text with start `"1"`; when only links exist (no text), links are reported at their actual internal V-position `"2.1"`. This means the same link at internal V-position `2.1` appears as either `"0"` or `"2.1"` in query output depending on whether the document has text content. The normalization is performed by `retrievevspansetpm()` which zeroes mantissa[1] for the link span and uses `maxtextwid()` to compute the text span.

**Why it matters for spec**: Any spec of vspanset retrieval must model this context-dependent normalization as a distinct presentation function. Callers must handle both representations. This creates a potential source of confusion where `"0"` and `"2.1"` both refer to the link subspace — the spec should define a canonical form and document the normalization rule.

**Code references**:
- `orglinks.c:173-221` — `retrievevspansetpm()` normalization logic

**Concrete example**:
```
Document with text + 1 link:
  Output: [{"start": "0", "width": "0.1"}, {"start": "1", "width": "1"}]

Same document after deleting all text:
  Output: [{"start": "2.1", "width": "0.1"}]
```

**Provenance**: Finding 0038
**Co-occurring entries:** [SS-DUAL-ENFILADE], [FC-SUBSPACE], [INV-SUBSPACE-CONVENTION]

---

### EC-REVERSE-ORPHAN

**Source:** Finding 0040

**What happens:** Removing a link from POOM via DELETEVSPAN creates a state that is the mirror image of an orphaned link (Finding 0024). In a standard orphan, the link exists in the POOM but its endpoints resolve to empty content. In a "reverse orphan," the link does NOT exist in the POOM but is fully intact — link orgl exists, endsets resolve correctly, and discovery via `find_links` works.

| Scenario | POOM | Link orgl | Endpoints | Discovery |
|----------|------|-----------|-----------|-----------|
| Normal link | Present | Exists | Resolve | Works |
| Orphaned link (0024) | Present | Exists | Empty | Fails (content gone) |
| Reverse orphan (0040) | Absent | Exists | Resolve | Works (spanfilade intact) |

**Why it matters for spec:** The spec must account for this asymmetric state. A link can be discoverable without being "contained" in any document's POOM. The predicate `link_in_poom(link, doc)` is independent of `link_discoverable(link)` and `link_followable(link)`. This also means the set of links visible via `retrieve_vspanset(doc)` can be a strict subset of the set of links discoverable via `find_links(doc_content)`.

**Concrete example:**
```
Orphaned link (Finding 0024):
  retrieve_vspanset(doc) → shows link at 2.1
  follow_link(link_id, SOURCE) → empty
  find_links(source_specs) → []

Reverse orphan (Finding 0040):
  retrieve_vspanset(doc) → no link span
  follow_link(link_id, SOURCE) → works, returns content
  find_links(source_specs) → [link_id]
```

**Provenance:** Finding 0040, Discovery vs Direct Access Asymmetry and Comparison with Finding 0024.
**Co-occurring entries:** [SS-THREE-LAYER-MODEL], [PRE-DELETE], [ST-DELETE], [FC-LINK-DELETE-ISOLATION], [INV-LINK-PERMANENCE]

---

### EC-GHOST-LINK

**Source:** Finding 0048

**What happens:** When a link's endset contains I-addresses that are not in any document's POOM (unreferenced addresses per DEL5), FOLLOWLINK succeeds but returns empty or partial results. These are "ghost links" — the link structure is intact in the permanent layer, but its endpoints point to content with no current V-position. Three observable cases: (1) all endset I-addresses live → full result; (2) some unreferenced → partial result, only live addresses converted; (3) all unreferenced → empty result `[]`, operation still succeeds.

**Why it matters for spec:** Ghost links are not an error condition but a natural consequence of content deletion in a system with permanent I-addresses. The spec must distinguish three result states: operation failure (link doesn't exist), ghost link (link exists, result empty), and normal link (link exists, result non-empty). An empty successful result from FOLLOWLINK does NOT mean the endset is empty — it means the endset's I-addresses have no current V-position in the queried document. Reconstitution (DEL7) is always possible since I-addresses are permanent (P0).

**Code references:**
- Silent filtering: `backend/orglinks.c:446-448` — NULL context returns without adding V-spans
- Test evidence: `golden/links/orphaned_link_target_all_deleted.json` — returns `[]` with `works: true`
- DEL5 definition: unreferenced(a) ≡ a ∈ dom.ispace ∧ ¬(∃d, v : poom.d(v) = a)

**Concrete example:**
- Before: Link L has to-endset I-address `a`, document D has `poom.D(1.5) = a`
- Delete all content from D: `poom.D` no longer maps any v to `a`
- After: FOLLOWLINK(L, TO, D) → `[]`, works=true
- Reconstitution: COPY `a` into new document D2 → `poom.D2(1.1) = a` → FOLLOWLINK(L, TO, D2) → `[1.1]`

**Provenance:** Finding 0048
**Co-occurring entries:** [PRE-FOLLOWLINK], [ST-FOLLOWLINK], [INV-ITOV-FILTERING]

---

### EC-RESPONSE-BEFORE-CHECK

**Source:** Finding 0050

**What happens:** For state-modifying FEBE operations, the back end sends the success response (`putXXX`) before executing the operation (`doXXX`). When the operation fails internally (BERT check, or any other failure in the `doXXX` path), the back end prints an error to stderr and silently continues. The front end has no way to detect the failure — it has already received a matching success response code.

Contrast with `createlink()` in `fns.c:100-115`, which follows the correct pattern: `getcreatelink() && docreatelink()` are checked *before* `putcreatelink()` is called, and `putrequestfailed()` is sent on error.

Commented-out code in `fns.c` shows the correct pattern for `deletevspan()` as well, suggesting the implementers were aware of the issue.

**Why it matters for spec:** This is a protocol-level edge case with direct implications for the FEBE contract. The spec must document that for mutations, the response code does not confirm operation success — it only confirms request receipt. Any formal model of the FEBE protocol must treat mutation responses as acknowledgments, not confirmations. The `createlink` operation is an exception that does confirm success.

**Code references:**
- `fns.c:84-98` — `insert()`: response before operation
- `fns.c:333-347` — `deletevspan()`: response before operation
- `fns.c:100-115` — `createlink()`: correct pattern (response after operation)
- `fns.c` (commented-out code) — correct `deletevspan` pattern was present but disabled

**Concrete example:**
- INSERT: `putinsert(taskptr)` at step 2, `doinsert(taskptr, ...)` at step 3. If step 3 fails, front end already has success from step 2.
- CREATELINK: `docreatelink(...)` checked first, `putcreatelink(taskptr, &linkisa)` sent only on success, `putrequestfailed(taskptr)` sent on failure.

**Provenance:** Finding 0050
**Co-occurring entries:** [SS-BERT], [PRE-INSERT], [INV-WRITE-EXCLUSIVITY], [INT-BERT-FEBE]

---

### EC-CONCURRENT-LINK-CREATION

**Source:** Finding 0052

**What happens:** Because CREATELINK uses `insertpm` with full shifting semantics, concurrent link creation (two operations interleaving) could cause observable shifting. If operation A calls `findnextlinkvsa` to get position P, then operation B inserts a link before P, then A inserts at P — B's link would be shifted by A's insertion. The V-positions of link orgls are NOT stable under concurrent modification, even though they are stable under sequential modification.

**Why it matters for spec:** Link orgl V-positions in the POOM are not permanent identifiers. The spec should note that `link_vposition` is a mutable property subject to shifting by any `insertpm` call, not an invariant. For sequential single-user operation this is invisible (append-at-end), but any formal model of concurrent access must account for it. This is analogous to the concurrent insert concern in Finding 0041.

**Code references:**
- `backend/do2.c:151-167` — `findnextlinkvsa` reads current extent (not atomic with insertion)
- `backend/insertnd.c:162` — shifting applies to link orgl entries the same as text entries

**Provenance:** Finding 0052
**Co-occurring entries:** [SS-LINK-SUBSPACE], [ST-CREATE-LINK], [ST-INSERT]

---

### EC-DEEPLY-ORPHANED-LINK

**Sources:** Findings 0053, 0055

#### Finding 0053

**What happens:** When DELETE shifts a link's endset V-positions negative, the link enters a state distinct from a standard orphaned link (Finding 0024). In a standard orphan, the link's POOM entry exists at a valid V-position but the content it points to has been deleted. In a deeply orphaned link, the POOM entry itself has an invalid (negative) V-position — the entry exists in the tree but is unreachable by any query.

| Scenario | POOM V-pos | I-space | FOLLOWLINK | FINDLINKS |
|----------|-----------|---------|------------|-----------|
| Normal link | Valid positive | Exists | Returns endsets | Finds link |
| Orphaned (0024) | Valid positive | Exists | Empty (content gone) | Fails |
| Reverse orphan (0040) | Absent (deleted) | Exists | Works | Works |
| Deeply orphaned (0053) | Negative (invalid) | Exists | Empty endsets | Fails |

The deeply orphaned state differs from POOM deletion (Finding 0040) in that the POOM entry still physically exists but is invisible. It also cannot be targeted by a subsequent `DELETEVSPAN` because its V-position is negative and thus unreachable by a positive-valued V-span argument.

**Why it matters for spec:** This is a fourth link lifecycle state that the formal model must account for. The predicate `link_reachable(link, doc) ≡ link ∈ poom(doc) ∧ link.vpos ≥ 0` distinguishes reachable links from deeply orphaned ones. Unlike reverse orphans (where the POOM entry is cleanly removed), deeply orphaned entries are leaked state that cannot be reclaimed by normal operations.

**Code references:**
- `orglinks.c:446-448` — FOLLOWLINK fails to map negative V-positions to I-addresses
- Golden test `golden/links/delete_text_before_link.json` lines 118-122 — empty endsets after full deletion
- Golden test `golden/links/delete_partial_text_before_link.json` lines 118-126 — shift 1.5→1.2; line 160 — empty endsets after negative shift

**Provenance:** Finding 0053

#### Finding 0055

**What happens:** Finding 0053's "deeply orphaned link" state (link POOM entry at a negative V-position) does not occur via cross-subspace deletion. The mechanism proposed in Finding 0053 — DELETE shifting a link's V-position negative — is prevented by `strongsub`'s exponent guard. The empty endsets observed in golden tests after deletion have a different cause: the link's endset I-addresses are freed from the POOM (case 1 in `deletend`: `disown` + `subtreefree`), not the link's own V-position going negative.

When FOLLOWLINK returns empty spans after text deletion:
1. The link's POOM entry remains at V-position 2.1 (verified by `retrieve_contents` at 2.1)
2. The link's endset I-addresses are immutable (stored in I-space)
3. FOLLOWLINK resolves those I-addresses through the home document's current POOM
4. If the I-addresses were in the deletion range, they were freed from the POOM (case 1)
5. Resolution fails because the I-addresses no longer have V-position mappings
6. Result: empty endset spans — from I-address removal, not V-position corruption

**Why it matters for spec:** The "deeply orphaned" link lifecycle state from Finding 0053's analysis is retracted for cross-subspace deletion scenarios. Empty endsets after deletion are explained by I-address removal from the POOM, which is the standard orphaning mechanism (Finding 0024). The link lifecycle model does not need a fourth "deeply orphaned" state for this scenario. Whether same-exponent deletion could produce negative V-positions remains a separate question.

**Code references:**
- `edit.c:53-57` — Case 1 in `deletend`: `disown` + `subtreefree` removes I-addresses
- `golden/subspace/delete_text_does_not_shift_link_subspace.json` — link remains at 2.1 after all text deleted
- `golden/links/delete_text_before_link.json` — reinterpreted: empty endsets from I-address removal

**Provenance:** Finding 0055

**Co-occurring entries:** [SS-TUMBLER], [PRE-DELETE], [ST-DELETE], [FC-SUBSPACE], [INV-POOM-BIJECTIVITY], [INT-DELETE-SUBSPACE-ASYMMETRY]

---

### EC-REARRANGE-EMPTY-REGION

**Source:** Finding 0056

**What happens:** If a region `[cutN, cutN+1)` contains no content, it contributes to offset computation but doesn't move anything. The algorithm operates per-span, and empty regions simply have no spans to process. This is correct behavior — the offset arithmetic is unaffected.

**Why it matters for spec:** Edge case for the rearrange postcondition: when a region is empty, its size still contributes to the offset for other regions. For pivot with an empty region 1 (`cut0 = cut1`), `diff[1] = 0` and `diff[2] = 0`, making the operation a no-op. The spec should handle this: `cut0 = cut1 ⇒ rearrange(doc, [cut0, cut1, cut2]) = doc`.

**Code references:** `backend/edit.c:78-184` — per-span iteration with `rearrangecutsectionnd()`

**Provenance:** Finding 0056
**Co-occurring entries:** [PRE-REARRANGE], [ST-REARRANGE], [INV-REARRANGE-IDENTITY], [EC-REARRANGE-CROSS-SUBSPACE]

---

### EC-REARRANGE-CROSS-SUBSPACE

**Source:** Finding 0056

**What happens:** Rearrange can move content across subspace boundaries because offsets are computed purely from tumbler arithmetic with no digit-0 (subspace) validation. Content at V-address `1.x` can be moved to `2.x` if the cut geometry spans the boundary.

**Why it matters for spec:** This violates the content discipline (CD0) which requires content type to match subspace. The rearrange operation lacks a precondition check: there is no `pre_rearrange_subspace(doc, cuts) ≡ ∀ regions r1, r2: subspace(r1) = subspace(r2)` guard. The spec should note this as a missing validation — the implementation accepts inputs that produce semantically invalid states.

**Code references:** `backend/edit.c:78-184` — no subspace validation in `rearrangend()`

**Provenance:** Finding 0056 (see also Finding 0051)

## Omit

The following sections of Finding 0056 are omitted:

- **Comparison with Delete+Insert table:** The individual properties (identity preservation, link survival, transclusion maintenance) are already captured in INV-REARRANGE-IDENTITY and INV-REARRANGE-LINK-SURVIVAL from Finding 0016. The comparison is motivational, not a new behavioral property.
- **Key function list** (`makecutsnd`, `recombine`, etc.): Implementation helper descriptions without behavioral properties beyond what is captured in ST-REARRANGE.
**Co-occurring entries:** [PRE-REARRANGE], [ST-REARRANGE], [INV-REARRANGE-IDENTITY], [EC-REARRANGE-EMPTY-REGION]

---

### EC-STALE-SPANF-REFERENCE

**Source:** Finding 0057

**What happens:** After DELETE removes transcluded content, FIND_DOCUMENTS still returns the document as containing those I-addresses. The document appears in the result because the spanfilade entry persists, but attempting to convert the I-addresses to V-addresses in that document yields empty — the POOM has no mapping. This creates a "ghost reference" in the spanfilade: the index points to a document that no longer contains the content. The same behavior occurs for deleted links (Finding 0024) — the spanfilade retains references to deleted link endsets.

**Why it matters for spec:** FIND_DOCUMENTS returns a **superset** of documents currently containing the queried I-addresses. Formally: `actual_docs(i) ⊆ find_documents(i)` where `actual_docs(i) = {D | ∃ v : poom.D(v) = i}`. The reverse inclusion does NOT hold: `find_documents(i)` may include documents where `¬∃ v : poom.D(v) = i`. Consumers of FIND_DOCUMENTS must post-filter via I-to-V conversion (INV-ITOV-FILTERING from Finding 0048) to distinguish live from stale results.

**Concrete example:**
```
Setup:
  Source doc S has content at I-addresses α₁..α₅
  Target doc T COPYs that content → spanf registers T for α₁..α₅

After DELETE from T:
  FIND_DOCUMENTS(α₁..α₅) → {S, T}   (T is stale)
  I-to-V(α₁, T) → ∅                  (no V-position in T)
  I-to-V(α₁, S) → v₁                 (still live in S)

Multiple transclusions (A, B, C all COPY same content):
  DELETE from B only
  FIND_DOCUMENTS → {S, A, B, C}      (B is stale, no reference counting)
```

**Code references:**
- `backend/spanf1.c` — `finddocscontainingsp` queries spanf, returns stale entries
- `backend/orglinks.c:425-449` — `span2spanset` silently drops I-addresses with no POOM mapping (the post-filter)
- Test scenario: `delete_transcluded_content_spanfilade_cleanup` confirms stale result

**Provenance:** Finding 0057
**Co-occurring entries:** [ST-DELETE], [INV-SPANF-WRITE-ONLY], [INT-DELETE-SPANF-DIVERGENCE]

---

### EC-CRASH-MID-WRITE

**Source:** Finding 0059

**What happens:** The `subtreewriterecurs` function writes modified subtrees bottom-up: children first, then parent. If a crash occurs mid-write (e.g., after writing leaf and middle nodes but before updating the root), the on-disk enfilade enters an inconsistent state. The root pointer still references the old subtree, while newly written child nodes are orphaned — allocated on disk but unreachable from any root. The old tree may reference deallocated blocks that were reassigned to the new children.

Similarly, `writeenfilades()` writes granfilade root then spanfilade root sequentially. A crash between these two writes leaves the granfilade updated but the spanfilade stale — violating the cross-enfilade consistency invariant (every I-address in the granfilade should have a corresponding DOCISPAN in the spanfilade).

**Why it matters for spec:** This defines a corruption class that a specification must acknowledge: the system has no atomicity guarantee for disk writes spanning multiple blocks. The bottom-up write order is a partial mitigation (children exist before parent references them), but without an atomic commit mechanism, no write ordering prevents all corruption scenarios. A crash-safety specification would need: `atomic_write(subtree) → consistent_on_disk(subtree)`, which this system does not provide.

**Code references:**
- `backend/corediskout.c:426-494` — `subtreewriterecurs` bottom-up write with `modified = FALSE` after each child
- `backend/corediskout.c:68-88` — `writeenfilades` writes granf root then spanf root sequentially
- `backend/disk.c:300-338` — `actuallywriteloaf` per-block write with no fsync

**Concrete example:**
```
Modified granfilade subtree (3 levels):
  Root (modified=TRUE)
  ├── Middle (modified=TRUE)
  │   ├── Leaf-A (modified=TRUE)
  │   └── Leaf-B (modified=TRUE)

subtreewriterecurs writes bottom-up:
  Step 1: Write Leaf-A to disk block 47, clear modified  ✓
  Step 2: Write Leaf-B to disk block 48, clear modified  ✓
  Step 3: Write Middle to disk block 49 (refs blocks 47,48)  ✓
  Step 4: Write Root to disk block 12 (refs block 49)  ← CRASH

On restart:
  - Root on disk (block 12) still points to OLD middle (e.g., block 30)
  - Blocks 47, 48, 49 are allocated but unreachable (orphaned)
  - Block 30 may reference deallocated leaf blocks → corruption
```

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-CACHE-MECHANISM], [SS-UNIFIED-STORAGE], [ST-INSERT], [INV-DURABILITY-BOUNDARY], [EC-CROSS-ENFILADE-EVICTION], [EC-NO-STARTUP-VALIDATION]

---

### EC-NO-STARTUP-VALIDATION

**Source:** Finding 0059

**What happens:** On startup, `initenffile()` opens `enf.enf` and reads the block allocation table via `readallocinfo()`. There is no consistency check: no enfilade tree traversal, no checksum verification, no detection of partial writes or orphaned blocks. If the file contains corrupted data from a crash, the backend loads it as-is. Subsequent operations may then fail with `gerror()` (process abort) or silently return corrupt data depending on which blocks are affected.

**Why it matters for spec:** The system has no precondition check on startup that the persistent state is well-formed. A specification that models restart must note: `restart(disk_state) → loaded_state` assumes `well_formed(disk_state)`, but this assumption is not validated. This means post-crash behavior is undefined — the system does not distinguish between "clean prior shutdown" and "crash-corrupted state".

**Code references:**
- `backend/disk.c:340-383` — `initenffile` opens file, reads allocation info, no validation
- `backend/disk.c:364-382` — fallthrough: if file exists, assume it's valid

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-CACHE-MECHANISM], [SS-UNIFIED-STORAGE], [ST-INSERT], [INV-DURABILITY-BOUNDARY], [EC-CRASH-MID-WRITE], [EC-CROSS-ENFILADE-EVICTION]

---

### EC-CROSS-ENFILADE-EVICTION

**Source:** Finding 0059

**What happens:** Because all enfilades share a single cache (grim reaper list), memory pressure from operations on one enfilade can evict modified crums from another. For example, a large link search loading many spanfilade nodes could cause eviction of recently-inserted but not-yet-written granfilade text atoms. The grim reaper selects victims by age, not by enfilade type.

**Why it matters for spec:** This creates a subtle interaction between subsystems. The order in which crums are evicted (and thus written to disk) is determined by access patterns across all enfilades, not by any per-enfilade policy. In crash scenarios, this means durability of content depends on unrelated link operations — a cross-subsystem dependency that a specification should acknowledge.

**Code references:**
- `backend/credel.c:106-162` — grim reaper scans entire circular list regardless of `denftype`
- `backend/credel.c:147` — `isreapable` checks age/modified but not enfilade type

**Provenance:** Finding 0059
**Co-occurring entries:** [SS-CACHE-MECHANISM], [SS-UNIFIED-STORAGE], [ST-INSERT], [INV-DURABILITY-BOUNDARY], [EC-CRASH-MID-WRITE], [EC-NO-STARTUP-VALIDATION]

---

### EC-GRAN-MB-ONE

**Source:** Finding 0060

**What happens:** The granfilade's `MAXBCINLOAF = 1` creates a degenerate B-tree structure where every height-1 non-root node holds exactly one bottom crum. This means the height-1 layer adds no fan-out — it is effectively a pass-through that maps each height-2 child pointer to exactly one bottom crum. The tree is taller than necessary: a granfilade with N bottom crums needs height `⌈log₆(N)⌉ + 1` (the extra +1 for the pass-through height-1 layer) rather than the `⌈log₆(N)⌉` that a uniform M=6 tree would require.

The code comment `/* so text will fit *//* as you wish */` on the `MAXBCINLOAF` definition suggests this is a deliberate trade-off: bottom crums can hold up to `GRANTEXTLENGTH = 950` bytes of text, and limiting each height-1 node to one bottom crum simplifies loaf management at the cost of tree depth.

The POOM and SPAN enfilades avoid this degenerate case because `MAX2DBCINLOAF = 4` permits useful fan-out at height-1.

**Why it matters for spec:** Models should treat the height-1 layer of a GRAN enfilade as a trivial 1:1 mapping layer, not a branching layer. Complexity and lookup cost analysis must account for this extra level. The choice is architecturally significant: it means the granfilade is always at least 1 level taller than a comparable POOM for the same number of leaf entries.

**Code references:**
- `backend/enf.h:27` — `#define MAXBCINLOAF 1  /* so text will fit *//* as you wish */`
- `backend/enf.h:26` — `#define MAXUCINLOAF 6`
- `backend/enf.h:28` — `#define MAX2DBCINLOAF 4`

**Provenance:** Finding 0060
**Co-occurring entries:** [SS-ENFILADE-TREE], [ST-INSERT], [INV-ENFILADE-MINIMALITY]

---

### EC-BOUNDARY-INSERT-CLASSIFICATION

**Source:** Finding 0062

**What happens:** When content is inserted at the exact boundary between two existing crums (e.g., position 1.4 which is the right border of crum "AAA" covering [1.1, 1.4)), the insert is classified as a boundary case, not an interior split. Test 3 demonstrates this: inserting "X" at 1.4 — the boundary between "AAA" and "BBB" — results in "AAAXBBBCCC" with a single contiguous vspan. The "X" is placed between the two crums without fragmenting either one.

The classification depends on which crum `findsontoinsertundernd` selects as the insertion target. For a position at the right boundary of crum_left (ONMYRIGHTBORDER), the function evaluates whether the position falls within the range of the adjacent crum_right (ONMYLEFTBORDER). The result is that boundary insertions are handled by the neighboring crum rather than splitting the crum whose boundary they touch.

**Why it matters for spec:** Boundary insertions are an edge case where the five-way classification system prevents unnecessary splits. The spec should note that `INSERT(pos)` where `pos == crum.reach` for some crum is NOT equivalent to `INSERT(pos)` where `crum.grasp < pos < crum.reach`. The former triggers the ONMYRIGHTBORDER path (no split, possible extension); the latter triggers the THRUME path (split). This distinction is observable: the former produces fewer crums.

**Code references:**
- `insertnd.c:269-291` — `findsontoinsertundernd()` selects which crum handles the insert
- `retrie.c:345-372` — `whereoncrum()` classifies position relative to each candidate crum

**Concrete example:**
```
Before: "AAA" [1.1, 1.4) + "BBB" [1.4, 1.7) + "CCC" [1.7, 1.10)
INSERT "X" at 1.4:
  1.4 is ONMYRIGHTBORDER of "AAA" (reach = 1.4)
  1.4 is ONMYLEFTBORDER of "BBB" (grasp = 1.4)
  findsontoinsertundernd selects "BBB" as target
  Result: "AAAXBBBCCC" — single contiguous vspan, no fragmentation
```

**Provenance:** Finding 0062
**Co-occurring entries:** [SS-WHEREONCRUM], [PRE-INSERT], [ST-INSERT], [INV-CRUM-BOUND]

---

### EC-GHOST-LINK-ENDPOINT

**Source:** Finding 0067

**What happens:** When a document DELETEs content that serves as a link endpoint in another document, the link in the other document becomes a "ghost link." The other document's link POOM entry remains unchanged at its V-position (e.g., 2.x). The link's I-addresses are immutable. What changes is that the source document's POOM no longer maps those I-addresses to V-positions, so endpoint resolution fails — producing empty endset spans.

This is NOT a violation of F0: the other document's structure is unchanged, the target document's POOM is correctly updated (I-address mappings removed), and the link subspace in the other document is unaffected. The ghost link is a consequence of content identity semantics, not a side effect.

**Why it matters for spec:** Link endpoint validity is not guaranteed as a postcondition of DELETE on source content. The formal model should track that link endpoints reference I-addresses, and I-address resolvability depends on the POOM state of the home document. DELETE on document D can make I-addresses unresolvable in D, which affects links in other documents that reference those I-addresses — but this is an indirect semantic consequence, not a structural mutation of other documents.

**Code references:**
- `edit.c:53-57` — Case 1 in `deletend`: `disown` + `subtreefree` removes I-address mappings
- `do1.c:162-171` — `dodeletevspan` modifies only target document's orgl

**Concrete example:**
```
Pre-state:
  Doc A has content at I-addresses α₁..α₅
  Doc B has link with endset referencing α₁..α₃ in Doc A

Operation: DELETE α₁..α₃ content from Doc A

Post-state:
  Doc A: POOM no longer maps α₁..α₃ to V-positions
  Doc B: link POOM entry UNCHANGED at V-position 2.x
  Doc B: link I-addresses UNCHANGED (still reference α₁..α₃)
  FOLLOWLINK from Doc B: empty endset spans (α₁..α₃ unresolvable in Doc A)
  F0 NOT violated: Doc B's structure is identical before and after
```

**Provenance:** Finding 0067 (referencing Finding 0048)
**Co-occurring entries:** [FC-DOC-ISOLATION], [FC-SUBSPACE], [INV-SPANF-WRITE-ONLY]

---

### EC-FIND-LINKS-GLOBAL

**Source:** Finding 0069

**What happens:** Because the orgl range parameter is ignored, all `find_links` calls are effectively global across the entire orgl address space. A call intended to find links only within a specific document will also return links from every other document, as long as the span-dimension (I-address) match succeeds. This interacts with transclusion: since transcluded content shares I-addresses across documents, a `find_links` scoped to document A would return links from document B if they share content — and with the orgl filter disabled, this is the only possible behavior anyway.

**Why it matters for spec:** This edge case means that no `find_links` result set can be attributed to a single document by orgl scoping. All link discovery is purely content-identity-based. This simplifies the spec model (no need for per-document link queries), but it also means there is no way to ask "what links exist within this document only" — the system has no such capability. Bounded model checking (Alloy) should verify that `find_links` results are identical regardless of what orgl range is passed.

**Code references:**
- `sporgl.c:222-226` — the `TRUE||` guard that makes all searches global
- Related: Finding 0026 documents link discovery via content identity, which is the only filtering mechanism that actually functions

**Provenance:** Finding 0069
**Co-occurring entries:** [SS-SPANF-OPERATIONS], [PRE-FIND-LINKS]

---

### EC-GRAN-BOTTOM-SINGLETON

**Source:** Finding 0070

**What happens:** GRAN (1D) enfilades have `MAXBCINLOAF = 1`, meaning bottom crums hold exactly one entry. The comment in `enf.h` says "so text will fit." This makes the granfilade bottom level effectively a linked list: each bottom crum contains a single text entry, with B-tree fan-out only at upper levels (where `MAXUCINLOAF = 6` still applies).

This asymmetry means the threshold functions behave differently at the bottom of a GRAN enfilade:
- `toomanysons` triggers at > 1 (any bottom node with 2+ children must split)
- `roomformoresons` returns TRUE only when sons = 0 (empty)
- `toofewsons` returns TRUE when sons < 1 (i.e., the node is empty)

**Why it matters for spec:** The formal model must handle GRAN bottom crums as a degenerate case of the B-tree structure. The occupancy invariant at the bottom level of a GRAN is `sons = 1` (exactly one entry per bottom crum), which is much tighter than the upper-level bound. This also means GRAN bottom crums never undergo merge/steal operations in the usual sense — they're always at their only valid occupancy.

**Code references:**
- `backend/enf.h:28` — `MAXBCINLOAF` = 1, with comment "so text will fit"
- `backend/genf.c:239-261` — threshold functions selecting `MAXBCINLOAF` for GRAN bottom crums

**Provenance:** Finding 0070
**Co-occurring entries:** [SS-ENFILADE-BRANCHING], [PRE-SPLIT], [INV-ENFILADE-OCCUPANCY]

---

### EC-RECOMBINE-RECEIVER-SATURATION

**Source:** Finding 0073

**What happens:** A receiver stops absorbing donors when any of these conditions hold:
1. `ishouldbother(sons[i], sons[j])` returns FALSE because the combined son count exceeds the branching limit (`MAXUCINLOAF` for height > 1, `MAX2DBCINLOAF` for height == 1)
2. The receiver's `age == RESERVED` (checked by `ishouldbother`)
3. The donor is NULL (already depleted by a prior merge) or RESERVED
4. `roomformoresons(sons[i])` returns FALSE during partial absorption (nephew-stealing path)

Once saturated, the receiver skips all remaining donors for that outer loop iteration, but remains in the array for subsequent iterations where it might be a donor to a later receiver (at position `i' > i`).

**Why it matters for spec:** The saturation conditions define the termination guarantee for the inner loop: a receiver cannot grow unboundedly. Combined with the occupancy invariant (`sons <= max_children`), this ensures rebalancing never creates overful nodes. The formal precondition for a merge attempt is: `ishouldbother(r, d) ∧ r ≠ NULL ∧ d ≠ NULL`.

**Code references:**
- `backend/recombine.c:150-163` — `ishouldbother` capacity and reserved-crum guards
- `backend/recombine.c:120-128` — Loop guards checking `sons[i] && sons[j]`
- `backend/recombine.c:186` — `roomformoresons` check in partial absorption path

**Provenance:** Finding 0073
**Co-occurring entries:** [ST-REBALANCE-2D]

---

### EC-VWIDTH-ZERO-ADDRESS

**Source:** Finding 0076

**What happens:** The V-width exponent computation `shift = tumblerlength(vsaptr) - 1` has an edge case when `vsaptr` is the zero tumbler. If `tumblerlength(vsaptr) = 0`, then `shift = -1`, producing a V-width with `exp = 1`. This would create a tumbler in a different magnitude range than normal V-widths (which have negative exponents). The original developer noted suspicion about this shift computation in a 1985 comment: `/*I'm suspissious of this shift <reg> 3/1/85 zzzz*/`.

**Why it matters for spec:** The precondition for V-width encoding should specify that `vsaptr` is a non-zero tumbler with `tumblerlength(vsaptr) >= 1`. If the zero-address case can occur, the resulting V-width has qualitatively different structure (positive exponent vs negative). A formal spec should either prove this case cannot arise (V-addresses are always non-zero during INSERT) or define behavior for it.

**Code references:**
- `orglinks.c:107` — `shift = tumblerlength(vsaptr) - 1` with suspicious-shift comment at line 106

**Provenance:** Finding 0076
**Co-occurring entries:** [SS-POOM-BOTTOM-CRUM], [ST-INSERT-VWIDTH-ENCODING], [INV-WIDTH-VALUE-EQUIVALENCE]

---
