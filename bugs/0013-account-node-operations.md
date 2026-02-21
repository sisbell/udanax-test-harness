# Bug 0013: Account and Node Operations Not Working

**Status: FIXED**

## Summary

The `account()` (opcode 34) and `create_node()` (opcode 38) FEBE operations did not work as expected. Account switching didn't affect document creation location, and create_node always returned the same address.

## Severity

Medium - affects multi-user/multi-node scenarios

## Fix

Two bugs were fixed:

1. **granf2.c:findisatoinsertnonmolecule** - When searching for existing items to find the next address, the function didn't check if found items were actually under the target account. Documents from other accounts (e.g., 1.1.0.1.0.1 when creating under 1.1.0.2) would be found and incremented from. Fix: Added check to verify lowerbound is under hintisa before using it.

2. **do1.c:docreatenode_or_account** - The newly allocated address was written to a local variable instead of the output parameter. Fix: Copy the result back to isaptr before returning.

## Symptoms

### 1. account() switch is ineffective

After calling `account()` with a new address, documents are still created under the original account:

```python
account1 = Address(1, 1, 0, 1)
session.account(account1)
doc1 = session.create_document()  # Returns 1.1.0.1.0.1 ✓

account2 = Address(1, 1, 0, 2)
session.account(account2)
doc2 = session.create_document()  # Returns 1.1.0.1.0.2 ✗ (should be 1.1.0.2.0.1)
```

### 2. create_node() always returns same address

Multiple calls to `create_node()` return identical addresses:

```python
session.account(Address(1, 1, 0, 1))
node1 = session.create_node(Address(1, 1, 0, 1))  # Returns 1.1.0.1
node2 = session.create_node(Address(1, 1, 0, 1))  # Returns 1.1.0.1 (same!)
node3 = session.create_node(Address(1, 1, 0, 1))  # Returns 1.1.0.1 (same!)
```

### 3. Cross-account document access causes crash

Opening a document while the current account doesn't match the document's account causes a backend abort:

```python
account1 = Address(1, 1, 0, 1)
session.account(account1)
doc1 = session.create_document()
session.close_document(session.open_document(doc1, ...))

account2 = Address(1, 1, 0, 2)
session.account(account2)
doc2 = session.create_document()  # Created as 1.1.0.1.0.2
session.open_document(doc2, ...)  # CRASH - doc belongs to account1 but current is account2
```

## Root Cause Analysis

### account() issue

In `backend/get1fe.c:213`:
```c
bool getxaccount(typetask *taskptr, typeisa *accountptr)
{
  ...
  player[user].account = *accountptr;
  taskptr->account = *accountptr;
  ...
}
```

The account is updated in both `player[user].account` and `taskptr->account`, but document creation in `do1.c:243` uses `&taskptr->account` which may be getting reset between operations.

### create_node() issue

In `backend/do1.c:247`:
```c
bool docreatenode_or_account(typetask *taskptr, typeisa *isaptr)
{
    ...
    makehint (NODE, NODE, 0, &isa, &hint);
    ...
}
```

The function appears to return the input address rather than allocating a new one.

## Affected Operations

- XACCOUNT (opcode 34)
- CREATENODE_OR_ACCOUNT (opcode 38)

## Workaround

Stay with a single account per session. Multiple accounts require separate sessions or backend instances.

## Test Coverage

See `febe/scenarios/accounts.py` for test scenarios that document the actual behavior.

## Related Bugs

- Bug 0001: tumbleraccounteq child/parent comparison
- Bug 0002: BERTMODEONLY openstate handling
