# Bug 016: Link Count Limit - Regression/Not Fully Fixed

**Date discovered:** 2026-01-31
**Status:** Open
**Severity:** High - backend crash (abort trap)
**Related:** Bug 006 (previously marked as fixed)

## Summary

The backend crashes when creating too many links in a session. The exact limit varies based on the total number of documents and other factors, but is generally around 5-6 links total.

## Reproduction

```python
# With 2 documents: crash on 6th link
doc1, doc2 = create_two_docs()
for i in range(6):  # Link 6 crashes
    create_link(doc1, doc2)

# With 7 documents: crash on 4th link
docs = create_seven_docs()
for i in range(4):  # Link 4 crashes
    create_link(docs[i], docs[i+1])
```

## Observations

| Scenario | Documents | Links before crash |
|----------|-----------|-------------------|
| Simple 2-doc | 2 | 5 (crash on 6th) |
| Hub pattern | 6 | 3 (crash on 4th) |
| Chain pattern | 7 | 3 (crash on 4th) |

The crash threshold decreases as the number of documents increases.

## Analysis

This appears to be a memory/space allocation issue in the link subspace management. Possible causes:

1. **Link subspace size limit** - The 0.x subspace for links may have a small fixed allocation
2. **Enfilade rebalancing** - Creating many links may trigger a rebalance that crashes
3. **POOM tree overflow** - The link tracking tree may overflow its bounds
4. **Global link registry** - Some global structure tracking all links may overflow

## Why Bug 006 Was Marked Fixed

Bug 006 focused on malformed link type addresses (Bug 005). After fixing the type address format, some scenarios that previously crashed started working. However, the underlying link count limit issue was not resolved - it was masked by the address fix changing the crash threshold.

## Impact

- Cannot create more than 3-5 links in complex test scenarios
- Star/hub link patterns crash the backend
- Limits testing of complex link topologies

## Workaround

Keep link count per scenario below 4-5 links, especially when many documents are involved.

## Files Affected

- Backend link creation code (unknown specific location)
- Link subspace management
- POOM tree operations

## Test Cases

- `febe/scenarios/links/chains.py::scenario_star_hub_incoming` (CRASHES)
- `febe/scenarios/links/chains.py::scenario_star_hub_outgoing` (CRASHES)
