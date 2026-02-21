# Bug Tracking

Bugs discovered during golden test development.

## Index

| ID | Title | Status | Severity | Notes |
|----|-------|--------|----------|-------|
| [0001](0001-tumbleraccounteq-child-parent.md) | tumbleraccounteq fails for child/parent comparison | Fixed | High | |
| [0002](0002-bertmodeonly-openstate-zero.md) | BERTMODEONLY doesn't handle openState==0 | Fixed | Medium | |
| [0003](0003-docreatenewversion-doopen.md) | docreatenewversion internal doopen fails | Fixed | High | |
| [0004](0004-first-document-address.md) | First document gets account address instead of document address | Fixed | High | |
| [0005](0005-pyxi-link-type-addresses.md) | pyxi has malformed link type addresses | Fixed | High | Also fixed 0006 |
| [0006](0006-backend-crashes-on-6th-link.md) | Backend crashes when creating 6th link | Partial | High | See 0016 |
| [0007](0007-backend-crashes-on-delete-all.md) | Backend crashes when deleting all content | Fixed | High | |
| [0008](0008-backend-crashes-on-linked-document-edit.md) | Backend crashes when editing documents with links | Fixed | High | Client bug |
| [0009](0009-compare-versions-crashes-with-links.md) | compare_versions crashes with links | Fixed | High | Filter link subspace spans |
| [0010](0010-no-vposition-validation.md) | No V-Position validation (acceptablevsa always TRUE) | Open | Medium | |
| [0011](0011-retrieve-vspan-broken-with-links.md) | retrieve_vspan returns invalid span with links | Closed | Medium | Workaround: use retrieve_vspanset |
| [0012](0012-deep-version-chain-crash.md) | Backend crashes on deep version chains | Fixed | Medium | |
| [0013](0013-account-node-operations.md) | account() and create_node() not working | Fixed | Medium | |
| [0014](0014-empty-document-crash.md) | Backend crashes during empty document scenario | Open | High | |
| [0015](0015-homedocids-filter-ignored.md) | find_links homedocids filter has no effect | Open | Medium | Workaround: filter client-side |
| [0016](0016-link-count-limit-regression.md) | Link count limit causes crash | Open | High | Limit varies with doc count |
| [0017](0017-zero-width-link-endpoint-crash.md) | Zero-width link endpoint crash | Open | Medium | Workaround: use non-zero spans |
| [0018](0018-large-insert-crash.md) | Large insert crash | Open | High | Limit ~10KB per insert |
| [0019](0019-insert-after-delete-all-crash.md) | INSERT/VCOPY after delete-all crashes | Fixed | High | Sequel to 0007 |
| [0020](0020-recombine-stack-overflow.md) | recombine stack overflow | Open | High | |

## Summary

- **Fixed:** 12
- **Closed:** 1 (workaround in place)
- **Open:** 7

## Discovery Context

These bugs were discovered while developing golden tests for the Xanadu specification project. The tests exercise the FEBE protocol against the original 1999 C backend.
