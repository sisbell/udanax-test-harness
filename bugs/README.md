# Bug Tracking

Bugs discovered during golden test development.

## Index

| ID | Title | Status | Severity |
|----|-------|--------|----------|
| [001](001-tumbleraccounteq-child-parent.md) | tumbleraccounteq fails for child/parent comparison | Fixed | High |
| [002](002-bertmodeonly-openstate-zero.md) | BERTMODEONLY doesn't handle openState==0 | Fixed | Medium |
| [003](003-docreatenewversion-doopen.md) | docreatenewversion internal doopen fails | Fixed | High |
| [013](013-account-node-operations.md) | account() and create_node() not working | Fixed | Medium |

## Bug Relationships

```
Bug 001 (tumbleraccounteq)
    ↓ exposes
Bug 002 (BERTMODEONLY)

Bug 003 (docreatenewversion)
    ↓ caused by
Bug 001 + original BERTMODEONLY logic
```

## Discovery Context

These bugs were discovered while developing golden tests for the Xanadu specification project. The `create_version` test scenario triggered an abort trap, leading to investigation of the bert (document open tracking) and tumbler comparison code.

## Test Coverage

All bugs are covered by the `create_version` and `compare_versions` scenarios in `febe/generate_golden.py`.
