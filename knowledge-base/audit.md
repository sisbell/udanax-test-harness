# KB Audit — 2026-02-21

KB: 189 entries, 79 findings referenced

## Miscategorized Entries

# Miscategorized Entries

26 entries flagged out of 189 reviewed.

---

## SS-* (State Structure)

### SS-BERT (Finding 0050 sub-entry)
**Current category:** SS
**Suggested category:** EC
**Reason:** Finding 0014 within SS-BERT correctly describes the BERT hash table structure. But Finding 0050's primary content is the response-before-check behavioral anomaly — `putXXX()` sends success before `doXXX()` verifies BERT. This describes what the BERT mechanism *fails to enforce* at runtime, not what the state IS. The anomaly is already captured by EC-RESPONSE-BEFORE-CHECK.
**Finding(s):** Finding 0050

### SS-SPANF-OPERATIONS (Finding 0069 sub-entry)
**Current category:** SS
**Suggested category:** EC
**Reason:** Finding 0012 correctly describes the spanf operations as an abstract data type interface. But Finding 0069's primary content is a code bug: the `TRUE||!homeset` expression that disables the orgl-dimension filter, reducing a 2D query to 1D. This is an implementation defect, not a structural description. Already captured by EC-FIND-LINKS-GLOBAL.
**Finding(s):** Finding 0069

### SS-POOM-MUTABILITY
**Current category:** SS
**Suggested category:** FC / INV
**Reason:** Primary content is not "what the POOM is" (covered by SS-DUAL-ENFILADE, SS-POOM-MULTIMAP, SS-POOM-BOTTOM-CRUM). It instead declares which layers are mutable vs. immutable: granfilade is append-only, spanfilade is write-only, POOM is the "sole locus of destructive mutation." The mutability table (`granfilade: immutable, spanfilade: immutable, pooms: MUTABLE`) is a frame condition / invariant declaration about what operations can and cannot change.
**Finding(s):** Finding 0072

---

## PRE-* (Preconditions)

### PRE-FIND-LINKS (Finding 0069 sub-entry)
**Current category:** PRE
**Suggested category:** EC
**Reason:** Finding 0069 describes a dead-code bug (`TRUE||!homeset`) that causes the orgl range parameter to be permanently ignored. The operation accepts any input and always succeeds — there is no validity check to describe. This is an edge case / defect, not a precondition.
**Finding(s):** Finding 0069

### PRE-VERSION-OWNERSHIP
**Current category:** PRE
**Suggested category:** ST
**Reason:** The entry explicitly states "This is not a precondition that rejects the operation — both paths succeed." The ownership check determines WHERE the new version address lands (under document vs. under user account), not WHETHER the operation is valid. This is a branching postcondition, not a precondition.
**Finding(s):** Finding 0068

### PRE-SPLIT
**Current category:** PRE
**Suggested category:** SS
**Reason:** Primary content describes the internal structure and branching logic of the `splitcrumupwards` algorithm: how it distinguishes root nodes from internal nodes via `isfullcrum`, and what structural changes each branch produces (height change vs. width change). The "precondition" framing is superficial — the entry defines the split algorithm's two structural cases and their effects on the tree, which is State Structure.
**Finding(s):** Finding 0070

---

## ST-* (State Transitions)

### ST-COMPARE-VERSIONS
**Current category:** ST
**Suggested category:** SS
**Reason:** `compare_versions` is a read-only query that produces a list of shared span pairs. It modifies no state. The "postcondition" describes what it *returns*, not what it *changes*. This is a structural definition of a query operation's output specification.
**Finding(s):** Finding 0015

### ST-VSPAN-TO-SPORGL
**Current category:** ST
**Suggested category:** SS
**Reason:** `vspanset2sporglset` is a pure read-only conversion function. The entry itself states "it reads the enfilade but does not modify it." A pure derivation is not a state transition.
**Finding(s):** Finding 0013

### ST-FIND-LINKS
**Current category:** ST
**Suggested category:** SS
**Reason:** `find_links` is a read-only query (I-address set intersection over the spanfilade). All three findings describe query semantics — how results are computed — not state changes. Finding 0035 explicitly says "no additional state transitions or side effects."
**Finding(s):** Findings 0028, 0029, 0035

### ST-FOLLOW-LINK
**Current category:** ST
**Suggested category:** SS
**Reason:** `follow_link` is a read-only query returning the link's original specset. It modifies no state. The entry describes what the operation returns, not what it changes.
**Finding(s):** Finding 0028

### ST-RETRIEVE-ENDSETS
**Current category:** ST
**Suggested category:** SS
**Reason:** `RETRIEVEENDSETS` is a read-only query through the spanfilade. It returns three specsets but modifies no persistent state.
**Finding(s):** Finding 0035

### ST-PAGINATE-LINKS
**Current category:** ST
**Suggested category:** SS
**Reason:** `FINDNEXTNLINKSFROMTOTHREE` is a stateless read-only query with cursor-based pagination. "Destructive truncation" is on a transient in-memory list, not persistent state. No system state is modified.
**Finding(s):** Finding 0035

### ST-FOLLOWLINK
**Current category:** ST
**Suggested category:** SS
**Reason:** Duplicate topic with ST-FOLLOW-LINK. `FOLLOWLINK` is a read-only two-phase query (I-address extraction then V-address resolution). It modifies no state.
**Finding(s):** Finding 0048

### ST-INSERT-ACCUMULATE
**Current category:** ST
**Suggested category:** INV
**Reason:** Primary content describes a monotonic growth property of DOCISPAN across multiple INSERT operations ("DOCISPAN creation is additive," "only grows"). This is an invariant about how the DOCISPAN index behaves, not a distinct state transition.
**Finding(s):** Finding 0036

### ST-INSERT-VWIDTH-ENCODING
**Current category:** ST
**Suggested category:** SS
**Reason:** Primary content describes how V-width is structurally encoded in POOM bottom crums — how tumbler representation differs between V-space and I-space for the same numeric width. This is a structural definition of internal data representation, not a description of what INSERT changes.
**Finding(s):** Finding 0076

### ST-ADDRESS-ALLOC
**Current category:** ST
**Suggested category:** SS
**Reason:** Findings primarily define the structural rules of the address space hierarchy: first-child convention (`.0.1`), upper-bound computation from parent, query-and-increment mechanism, containment checks. While allocation IS a transition, the bulk of the content describes address space layout rules, not the mutation itself.
**Finding(s):** Findings 0021, 0025, 0065, 0068

---

## FC-* (Frame Conditions)

### FC-DOC-ISOLATION (Finding 0028 sub-entry)
**Current category:** FC
**Suggested category:** INV
**Reason:** Primary content is that independently created documents always have disjoint I-positions — the identity-by-origin property. This holds universally as a property of the identity model, not as a frame condition on a specific operation.
**Finding(s):** Finding 0028

### FC-DOC-ISOLATION (Finding 0033 sub-entry)
**Current category:** FC
**Suggested category:** ST
**Reason:** Primary content describes a postcondition of vcopy — that copying a contiguous V-span produces a contiguous I-span in the target. This is what vcopy *produces*, not what it leaves unchanged.
**Finding(s):** Finding 0033

### FC-SPECSET-COMPARE
**Current category:** FC
**Suggested category:** ST
**Reason:** Primary content describes the operational semantics of compare — it filters by SpecSet boundaries and reports only identity overlaps within those boundaries. This defines what compare *does*, not what it leaves unchanged.
**Finding(s):** Finding 0003

### FC-ENFILADE-QUERY-INDEPENDENCE
**Current category:** FC
**Suggested category:** INV
**Reason:** Primary content is a representation independence invariant — all valid tree shapes encoding the same logical set produce identical query results. This holds universally across all operations and tree configurations, not as a frame condition on a specific operation.
**Finding(s):** Finding 0041

### FC-RETRIEVAL-TREE-INDEPENDENCE
**Current category:** FC
**Suggested category:** INV
**Reason:** Primary content is that V-ordering of retrieval results is invariant under tree reorganization (splits, rebalances, rotations). This is a universally-holding abstraction invariant, not a per-operation frame condition.
**Finding(s):** Finding 0078

---

## INV-* (Invariants)

### INV-SUBSPACE-CONVENTION
**Current category:** INV
**Suggested category:** SS + PRE
**Reason:** The bulk of the content describes what the three-subspace partition IS (structural definition: text at `1.x`, links at `2.x`, metadata at `3.x`) and that it is not enforced at runtime ("convention-over-enforcement," "must be modeled as a precondition"). The actual subspace isolation invariant for operations is already captured by FC-SUBSPACE.
**Finding(s):** Findings 0009, 0010, 0011, 0015, 0038, 0049, 0051, 0054

### INV-ENFILADE-MINIMALITY
**Current category:** INV
**Suggested category:** EC
**Reason:** Primary content documents that tree minimality and EN-4 occupancy invariants are **violated** by the implementation. Finding 0058 says "`levelpull` is disabled" and "the formal spec should NOT assert tree minimality as an invariant." This describes where the expected invariant does not hold — a deviation/edge case.
**Finding(s):** Findings 0058, 0060

### INV-DURABILITY-BOUNDARY
**Current category:** INV
**Suggested category:** SS
**Reason:** Primary content describes the structure of the persistence model — session-level vs. operation-level durability, absence of fsync, absence of a transaction log, the grim reaper cache eviction mechanism. This is what the storage architecture IS, not a property that holds across all operations.
**Finding(s):** Finding 0059

### INV-CRUM-BOUND
**Current category:** INV
**Suggested category:** ST
**Reason:** Primary content describes how crum count changes as a consequence of INSERT and CREATELINK operations, providing a per-operation growth formula (`c <= 1 + 2C + 2L + 3R + 3P`). This is fundamentally about what operations change — a state-transition complexity bound.
**Finding(s):** Findings 0062, 0063

### INV-POOM-BIJECTIVITY
**Current category:** INV
**Suggested category:** EC
**Reason:** Primary content documents that the classical POOM bijectivity invariant (EWD-018 I1) **can be violated** by DELETE creating negative V-positions. The entry says the invariant "does not hold after certain DELETE sequences." The discovery that the nominal invariant is broken is an edge case, not a statement of what always holds.
**Finding(s):** Finding 0053

---

## EC-* (Edge Cases)

### EC-APPEND-NO-DOCISPAN
**Current category:** EC
**Suggested category:** ST or FC
**Reason:** Primary content defines a postcondition difference between APPEND and INSERT: APPEND does not create DOCISPAN entries (`spanf' = spanf`). This is a state-transition property (what APPEND changes/preserves), not boundary behavior.
**Finding(s):** Finding 0036

### EC-CROSS-ENFILADE-EVICTION
**Current category:** EC
**Suggested category:** INT
**Reason:** Primary content describes a cross-subsystem interaction: operations on one enfilade (e.g., link search loading spanfilade nodes) cause cache eviction affecting another enfilade (e.g., granfilade text atoms). This is how subsystems affect each other through a shared resource, which is an Interaction.
**Finding(s):** Finding 0059

### EC-GRAN-MB-ONE
**Current category:** EC
**Suggested category:** SS
**Reason:** Primary content describes what the granfilade structure IS — `MAXBCINLOAF=1` creates a degenerate B-tree where the height-1 layer is a 1:1 pass-through. This is a data model / structural property, not boundary behavior.
**Finding(s):** Finding 0060

### EC-FIND-LINKS-GLOBAL
**Current category:** EC
**Suggested category:** ST
**Reason:** Primary content defines the actual operational semantics of `find_links`: it always searches globally because the orgl range parameter is ignored. This describes what the operation *does* (positive semantics), going beyond just documenting a broken filter.
**Finding(s):** Finding 0069

### EC-GRAN-BOTTOM-SINGLETON
**Current category:** EC
**Suggested category:** SS or INV
**Reason:** Primary content describes structural invariants of GRAN bottom crums: occupancy is always exactly 1, threshold functions have specific fixed behaviors. The `sons=1` property is an invariant, and the threshold function behaviors are structural properties — not boundary/unusual behavior.
**Finding(s):** Finding 0070


## Invented Categories

None — all entries use standard categories.

## Category Imbalance

| Category | Count |
|----------|-------|
| SS | 32 |
| PRE | 19 |
| ST | 24 |
| FC | 16 |
| INV | 41 |
| INT | 18 |
| EC | 39 |

No imbalance flags.

## Cross-Reference Integrity

All references valid.
