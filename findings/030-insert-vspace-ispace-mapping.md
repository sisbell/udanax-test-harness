# Finding 030: INSERT Updates V-Space While Preserving I-Space Identity

**Date:** 2026-02-01
**Related:** Finding 027, Finding 028

## Summary

INSERT operations shift V-addresses for content after the insertion point while preserving I-address identity for existing content. New inserted content receives fresh I-addresses. The `compare_versions` operation reveals this by showing which V-addresses across versions map to the same I-addresses.

## Key Semantic Properties

### 1. V-Addresses Shift, I-Addresses Don't

When inserting content, existing content after the insertion point gets new V-addresses but retains its original I-addresses:

```
Before INSERT at 1.3:
  V-address: 1.1  1.2  1.3  1.4  1.5
  Content:    A    B    C    D    E
  I-address: I.1  I.2  I.3  I.4  I.5

After INSERT "XY" at 1.3:
  V-address: 1.1  1.2  1.3  1.4  1.5  1.6  1.7
  Content:    A    B    X    Y    C    D    E
  I-address: I.1  I.2  I.6  I.7  I.3  I.4  I.5
                        ↑    ↑
                    New I-addresses
```

### 2. Content Before Insertion Point Unchanged

Content before the insertion point retains both its V-address and I-address:
- "A" remains at V-address 1.1, I-address I.1
- "B" remains at V-address 1.2, I-address I.2

### 3. Content After Insertion Point Shifts

Content after the insertion point:
- V-addresses shift by the length of inserted text (+2 in this case)
- I-addresses remain unchanged (identity preserved)

```
"C": V-address 1.3 → 1.5, I-address I.3 (unchanged)
"D": V-address 1.4 → 1.6, I-address I.4 (unchanged)
"E": V-address 1.5 → 1.7, I-address I.5 (unchanged)
```

### 4. New Content Gets Fresh I-Addresses

Inserted content receives new I-addresses allocated from the bert:
- "X" gets new I-address I.6
- "Y" gets new I-address I.7

These have no shared identity with any existing content.

## Revealing I-Space Identity with compare_versions

The `compare_versions` operation reveals I-address preservation by showing which spans across different document versions share identity:

```
compare_versions(version_before, current_document) returns:
  [
    { version: 1.1-1.2, current: 1.1-1.2 }   // "AB" - same position
    { version: 1.3-1.5, current: 1.5-1.7 }   // "CDE" - shifted +2
  ]
```

Note: No entry for positions 1.3-1.4 in current (the inserted "XY") because this content has no shared I-addresses with the version_before.

## Semantic Model

```
         VERSION BEFORE                      CURRENT (AFTER INSERT)
         ─────────────────                   ─────────────────────────
V-addr:  1.1  1.2  1.3  1.4  1.5            1.1  1.2  1.3  1.4  1.5  1.6  1.7
Content:  A    B    C    D    E              A    B    X    Y    C    D    E
I-addr:  I.1  I.2  I.3  I.4  I.5            I.1  I.2  I.6  I.7  I.3  I.4  I.5
          │    │    │    │    │              │    │              │    │    │
          └────┼────┼────┼────┼──────────────┘    │              │    │    │
               └────┼────┼────┼───────────────────┘              │    │    │
                    └────┼────┼──────────────────────────────────┘    │    │
                         └────┼───────────────────────────────────────┘    │
                              └────────────────────────────────────────────┘
                                     (I-address identity links)
```

## Implications

### 1. Links Survive Insertion

A link attached to "CDE" (I-addresses I.3-I.5) remains valid after insertion:
- The link's I-address endpoints are unchanged
- Discovery via find_links still works
- The V-address interpretation shifts (now 1.5-1.7 instead of 1.3-1.5)

### 2. Transclusions Maintain Identity

If another document transcluded "CDE" before the insertion:
- The transcluded content still shares I-addresses I.3-I.5
- compare_versions between documents still shows shared identity
- The relationship "same content" is preserved despite V-address changes

### 3. Version Tracking is I-Address Based

Comparing versions works because I-addresses are permanent:
- V-addresses are document-local and mutable
- I-addresses are global and immutable
- Version comparison reveals what content survived, even if rearranged

## Test Evidence

From `insert_vspace_mapping.py`:

```python
# Before: "ABCDE" at positions 1.1-1.5
positions_before = {"1.1": "A", "1.2": "B", "1.3": "C", "1.4": "D", "1.5": "E"}

# After INSERT "XY" at 1.3: "ABXYCDE" at positions 1.1-1.7
positions_after = {"1.1": "A", "1.2": "B", "1.3": "X", "1.4": "Y",
                   "1.5": "C", "1.6": "D", "1.7": "E"}

# compare_versions reveals I-space identity preservation:
shared_spans = [
    {"version_before": "1.1 for 0.2", "after_insert": "1.1 for 0.2"},  # AB
    {"version_before": "1.3 for 0.3", "after_insert": "1.5 for 0.3"}   # CDE shifted
]
```

## Related

- **Finding 027b**: retrieve_contents requires source document open
- **Finding 028b**: Link discovery via content identity
- **Literary Machines**: "The address of a byte never changes"
