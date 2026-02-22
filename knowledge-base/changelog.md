# KB Recategorization Changelog — 2026-02-22

Based on review of `audit.md` (26 entries flagged, 31 individual items including sub-entries).

## Decision Table

| # | Entry | From | To | Notes |
|---|-------|------|----|-------|
| 1 | SS-BERT (F0050 sub-entry) | SS | EC | Move to EC-RESPONSE-BEFORE-CHECK |
| 2 | SS-SPANF-OPERATIONS (F0069 sub-entry) | SS | EC | Move to EC-FIND-LINKS-GLOBAL |
| 3 | SS-POOM-MUTABILITY (F0072) | SS | FC + INV | Duplicate into both |
| 4 | PRE-FIND-LINKS (F0069 sub-entry) | PRE | EC | Move to EC-FIND-LINKS-GLOBAL |
| 5 | PRE-VERSION-OWNERSHIP (F0068) | PRE | ST | Branching postcondition, not a gate |
| 6 | PRE-SPLIT (F0070) | PRE | SS | Tree algorithm structure |
| 7 | ST-COMPARE-VERSIONS (F0015) | ST | SS | Read-only query |
| 8 | ST-VSPAN-TO-SPORGL (F0013) | ST | SS | Read-only conversion |
| 9 | ST-FIND-LINKS (F0028, F0029, F0035) | ST | SS | Read-only query |
| 10 | ST-FOLLOW-LINK (F0028) | ST | SS | Read-only query |
| 11 | ST-RETRIEVE-ENDSETS (F0035) | ST | SS | Read-only query |
| 12 | ST-PAGINATE-LINKS (F0035) | ST | SS | Read-only query |
| 13 | ST-FOLLOWLINK (F0048) | ST | SS | Read-only query, keep separate from ST-FOLLOW-LINK |
| 14 | ST-INSERT-ACCUMULATE (F0036) | ST | INV | Monotonic growth property |
| 15 | ST-INSERT-VWIDTH-ENCODING (F0076) | ST | SS | Data representation definition |
| 16 | ST-ADDRESS-ALLOC (F0021, F0025, F0065, F0068) | ST | SS + ST | Duplicate into both |
| 17 | FC-DOC-ISOLATION (F0028 sub-entry) | FC | INV | Universal identity property |
| 18 | FC-DOC-ISOLATION (F0033 sub-entry) | FC | ST | vcopy postcondition |
| 19 | FC-SPECSET-COMPARE (F0003) | FC | ST | Operational semantics |
| 20 | FC-ENFILADE-QUERY-INDEPENDENCE (F0041) | FC | INV | Representation independence invariant |
| 21 | FC-RETRIEVAL-TREE-INDEPENDENCE (F0078) | FC | INV | Representation independence invariant |
| 22 | INV-SUBSPACE-CONVENTION (F0009–F0054) | INV | SS + PRE | Structure + caller-enforced precondition |
| 23 | INV-ENFILADE-MINIMALITY (F0058, F0060) | INV | **Leave** | — |
| 24 | INV-DURABILITY-BOUNDARY (F0059) | INV | SS | Storage architecture description |
| 25 | INV-CRUM-BOUND (F0062, F0063) | INV | ST | Per-operation complexity bound |
| 26 | INV-POOM-BIJECTIVITY (F0053) | INV | **Leave** | — |
| 27 | EC-APPEND-NO-DOCISPAN (F0036) | EC | ST + FC | Postcondition + frame condition |
| 28 | EC-CROSS-ENFILADE-EVICTION (F0059) | EC | INT | Cross-subsystem interaction |
| 29 | EC-GRAN-MB-ONE (F0060) | EC | SS | Structural property |
| 30 | EC-FIND-LINKS-GLOBAL (F0069) | EC | **Leave** | — |
| 31 | EC-GRAN-BOTTOM-SINGLETON (F0070) | EC | SS + INV | Structure + always-holds property |

## Summary

- **Moved:** 28 items
- **Left in place:** 3 items (#23, #26, #30)
- **Duplicated into 2 categories:** 6 items (#3, #16, #22, #27, #31)
- **Sub-entries moved out of parent:** 5 items (#1, #2, #4, #17, #18)
