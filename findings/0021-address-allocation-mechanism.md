# Finding 0021: Address Allocation and Account Boundaries

## Summary

Bug 0013 investigation revealed how the backend allocates tumbler addresses and the semantic importance of account boundaries.

## Address Allocation Algorithm

New addresses (for documents, nodes, accounts) are allocated by `findisatoinsertnonmolecule` in `granf2.c`:

1. **Compute search bounds** from the hint (parent address):
   - `upperbound = tumblerincrement(hintisa, depth-1, 1)` - next sibling of parent
   - Example: For hintisa=1.1.0.2 (account), upperbound=1.1.0.2.1

2. **Find highest existing item** below upperbound via `findpreviousisagr`

3. **Increment from found item** or create first child if nothing found:
   - First child: `hintisa.0.1` (e.g., 1.1.0.2.0.1)
   - Subsequent: truncate + increment

## Key Insight: Account Boundaries

The original bug: `findpreviousisagr` searches the *entire* address space up to upperbound, crossing account boundaries.

Example:
- Account 1.1.0.1 has document 1.1.0.1.0.1
- Creating under account 1.1.0.2:
  - upperbound = 1.1.0.2.1
  - findpreviousisagr finds 1.1.0.1.0.1 (it's less than 1.1.0.2.1)
  - **BUG**: Increments from 1.1.0.1.0.1 → 1.1.0.1.0.2 (wrong account!)

The fix verifies the found item is actually under the target account by prefix matching.

## Tumbler Containment Check

To check if address A is "under" address B:
```c
tumblertruncate(&A, tumblerlength(&B), &truncated);
tumblereq(&truncated, &B);  // TRUE if A is under B
```

Example:
- Is 1.1.0.1.0.1 under 1.1.0.2?
- Truncate to length 4: 1.1.0.1
- Compare: 1.1.0.1 ≠ 1.1.0.2 → NO

## Hierarchy Levels

The `makehint` function encodes the hierarchy:

| supertype | subtype | depth | Example |
|-----------|---------|-------|---------|
| NODE | NODE | 1 | Creating node under node |
| ACCOUNT | DOCUMENT | 2 | Creating document under account |
| DOCUMENT | DOCUMENT | 1 | Creating version under document |
| DOCUMENT | ATOM | - | Creating text/link in document |

`depth = (supertype == subtype) ? 1 : 2`

This determines how many `.0.` boundaries to cross when allocating.

## Semantic Implications

1. **Accounts are namespaces**: Documents under different accounts have independent address allocation. The first document under any account is always `account.0.1`.

2. **Flat storage, hierarchical addressing**: The granf (global address enfilade) stores everything in one tree, but the allocation logic must enforce hierarchical boundaries.

3. **Node allocation**: Nodes are allocated at a higher level (1.1.0.1.1, 1.1.0.1.2) without the `.0.` boundary that documents have.

## Test Coverage

See `febe/scenarios/accounts.py`:
- `account_switch` - Verifies documents go under correct account
- `create_multiple_nodes` - Verifies sequential node allocation
