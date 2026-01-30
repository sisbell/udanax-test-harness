# Tumbler Technical Reference

Technical explanation of tumblers for agents working with Xanadu specifications.

---

## What Tumblers Are

Tumblers are **permanent addresses** in the Xanadu docuverse. They're a custom number system invented by Mark Miller to solve a specific problem: how to address items in an ever-growing, decentralized network where new items can be inserted between existing items without invalidating existing addresses.

### The Core Insight

Think of the Dewey Decimal System: `621.3` and `621.4` can have `621.35` inserted between them indefinitely. Tumblers extend this with:
- **Forking:** Any digit can spawn sub-digits (1.2 can become 1.2.1, 1.2.2, etc.)
- **Fields:** Major divisions separated by `.0.` for different entity types
- **Infinite precision:** Digits can be arbitrarily large (humbers)

---

## Tumbler Structure

A tumbler is a sequence of non-negative integers separated by periods:

```
1.2368.792.6.0.6974.383.1988.352.0.75.2.0.1.9287
│─────────────│────────────────────│─────│─────────│
   Node Field      User Field        Doc    Element
```

### The Four Fields

Separated by the major divider `.0.`:

| Field | Purpose | Example |
|-------|---------|---------|
| **Node** | Server/storage location | `1.2368.792.6` |
| **User** | Account/owner | `6974.383.1988.352` |
| **Document** | Document and version | `75.2` |
| **Element** | Content within document | V-space address |

An address tumbler has **at most three zeroes** (the field separators).

### Element Field (V-Space Addresses)

The element field addresses content within a document's virtual stream (V-space).

From the C code, the V-space is divided:
- Text (bytes) occupy lower addresses
- Links occupy addresses >= `linkspacevstart` (which is 2)

**Note:** The exact structure of V-space addresses and how links are addressed needs further verification against the backend. The pyxi client's handling of link addresses appears to be incorrect.

### Forking (Subdivision)

Any digit can "fork" into sub-digits:
```
2         → parent
2.1       → first child under 2
2.1.3     → third grandchild
2.4.6.312 → 312th item under 6th under 4th under 2
```

This enables:
- Nodes spawning child nodes
- Accounts spawning sub-accounts
- Documents spawning versions
- Versions spawning sub-versions

---

## The Tumbler Line

All tumblers form a **linear sequence** when sorted in ascending order:

```
1
1.1
1.1.2
1.1.2.1
1.1.2.2
1.1.3
1.2
1.2.1
1.2.1.9
1.2.2
1.2.65
1.2.65.831
1.3
...
```

This is a "depth-first" ordering of the tree structure. Every subtree maps to a contiguous range on the tumbler line.

### Why This Matters

A **span** (range on the tumbler line) corresponds to a **subtree** of the docuverse:
- Span `1.2` to `1.3` includes all of `1.2.*`
- You can reference "all versions of document 75" with a single span
- Links can point to spans, not just individual addresses

---

## Two Types of Tumblers

### 1. Address Tumblers

Represent specific locations. Properties:
- At most 3 zeros (field separators)
- Permanent - never change meaning
- Self-describing structure

Example: `1.2368.792.6.0.6974.383.0.75.2.0.1.9287`

### 2. Difference Tumblers

Represent spans (ranges). Properties:
- May have many zeros
- Always paired with an address tumbler
- Non-unique: same diff can mean different spans at different starting points
- Start with leading zeros (except for whole-docuverse span which is just `1`)

Example: `0.0.0.0.0.0.0.5.0.0.300` = "5 more documents, then 300 more bytes"

---

## Tumbler Arithmetic

### Addition: START + DIF = AFTER

Given a start address and difference, find where the span ends.

**Mechanics:** Align left-to-right (not right-to-left like normal arithmetic):
1. For every leading zero in DIF, copy corresponding digit from START
2. At first non-zero DIF digit, add the two digits
3. Copy remaining digits from DIF

```
START:  1.1.0.2.0.2.0.1.777
  DIF:  0.0.0.0.0.0.0.0.300
        ─────────────────────
AFTER:  1.1.0.2.0.2.0.1.1077
```

**Interpretation:** "Step forward 300 bytes within the same document."

### Subtraction: AFTER - START = DIF

Given two addresses, find the span between them.

**Mechanics:**
1. For matching digits, write zero
2. At first difference, subtract
3. Copy remaining digits from AFTER

```
AFTER:  1.17401.0.7.3.0.5.635.0.1.7922
START:  1.17392.0.7.0.0.0.0.0.0.0
        ─────────────────────────────────
  DIF:  0.9.0.0.3.0.5.635.0.1.7922
```

### Paradoxes of Tumbler Arithmetic

**Addition paradox:** A range of addends gives the same answer
- Adding anything in the span 1.2.* to 1.1 gives 1.3
- "Go to beginning of next chapter" regardless of where you add from

**Subtraction paradox:** A range of minuends gives the same answer
- Subtracting from anywhere in 1.3.* starting at 1.2 gives the same DIF
- The span captures "everything under 1.2"

---

## Implementation Notes

### Humbers (Humungous Numbers)

The individual digits of a tumbler are encoded as **humbers** - variable-length integers:
- If high bit is 0: remaining 7 bits ARE the number (0-127)
- If high bit is 1: remaining 7 bits specify LENGTH of number in bytes

This allows small numbers (most common) to be 1 byte, while supporting arbitrarily large numbers.

### In the C Implementation (udanax-green)

```c
struct structtumbler {
    char sign;           // 0 = non-negative, 1 = negative
    short exp;           // exponent, always <= 0
    tdigit mantissa[NPLACES];  // NPLACES = 11 digits
}
```

The C implementation uses a fixed-size mantissa with an exponent to represent the variable-depth tree structure. The exponent indicates where the "decimal point" falls.

### Key Operations (tumble.c)

| Function | Purpose |
|----------|---------|
| `tumblercmp` | Compare two tumblers |
| `tumbleradd` | Add tumblers (START + DIF = AFTER) |
| `tumblersub` | Subtract tumblers (AFTER - START = DIF) |
| `nstories` | Count significant digits |
| `intervalcmp` | Check if address is within span |
| `prefixtumbler` | Prepend a digit (move down tree) |
| `beheadtumbler` | Remove first digit (move up tree) |

---

## Semantic Guarantees

### All Addresses Remain Valid

> "New items may be continually inserted in tumbler-space while the other addresses remain valid."

This is THE fundamental guarantee. An address you save today works forever because:
1. Forking creates new addresses UNDER existing ones (not between)
2. The tree structure never rebalances at the tumbler level
3. Addresses are permanent by design, not by policy

### Ghost Elements

Servers, accounts, and documents are "virtually present" in tumbler-space even if nothing is stored for them. You can link to account `1.2.0.999` even if that account has no documents yet.

### Independence Properties

Tumblers are independent of:
- **Content structure:** Tree addresses don't impose structure on what's stored
- **Subject/category:** Not a semantic classification system
- **Mechanism:** Pure addressing, doesn't dictate storage implementation
- **Time:** Time is tracked separately

---

## Common Patterns

### Addressing a Document
```
1.2.0.50.0.100      Node 1.2, User 50, Document 100
```

### Addressing a Version
```
1.2.0.50.0.100.3    Node 1.2, User 50, Document 100, Version 3
```

### Addressing Content in a Document
```
1.2.0.50.0.100.0.N    Node 1.2, User 50, Document 100, V-space address N
```

### Addressing All Versions of a Document (Span)
```
START: 1.2.0.50.0.100
AFTER: 1.2.0.50.0.101
```
This span covers all of document 100 including all versions.

---

## Known Issues

**pyxi client:** The Python client included in udanax-green has incorrect link address handling. Link type addresses are malformed (missing element field separator). Do not rely on pyxi for link operations without verification.

**V-space structure:** The exact interpretation of V-space addresses for text vs links needs verification against the C backend. Literary Machines 4/30 describes element types, but the implementation details require further investigation.

---

## References

- Literary Machines, pages 4/13-4/40 (Tumblers, Tumbler Arithmetic)
- `udanax-green/green/be_source/tumble.c` - C implementation
- `udanax-green/green/be_source/orglinks.c` - Link space handling
- `spec/abstract/tumbler-salvage.dfy` - Dafny specification
