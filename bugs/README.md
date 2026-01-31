# Bug Tracking

Bugs discovered during golden test development.

## Index

| ID | Title | Status | Severity | Notes |
|----|-------|--------|----------|-------|
| [001](001-tumbleraccounteq-child-parent.md) | tumbleraccounteq fails for child/parent comparison | Fixed | High | |
| [002](002-bertmodeonly-openstate-zero.md) | BERTMODEONLY doesn't handle openState==0 | Fixed | Medium | |
| [003](003-docreatenewversion-doopen.md) | docreatenewversion internal doopen fails | Fixed | High | |
| [004](004-first-document-address.md) | First document gets account address instead of document address | Fixed | High | |
| [005](005-pyxi-link-type-addresses.md) | pyxi has malformed link type addresses | Fixed | High | Also fixed 006 |
| [006](006-backend-crashes-on-6th-link.md) | Backend crashes when creating 6th link | Fixed | High | Fixed by 005 |
| [007](007-backend-crashes-on-delete-all.md) | Backend crashes when deleting all content | Fixed | High | |
| [008](008-backend-crashes-on-linked-document-edit.md) | Backend crashes when editing documents with links | Fixed | High | Client bug |
| [009](009-compare-versions-crashes-with-links.md) | compare_versions crashes with links | Fixed | High | Filter link subspace spans |
| [010](010-no-vposition-validation.md) | No V-Position validation (acceptablevsa always TRUE) | Open | Medium | |
| [011](011-retrieve-vspan-broken-with-links.md) | retrieve_vspan returns invalid span with links | Closed | Medium | Workaround: use retrieve_vspanset |
| [012](012-deep-version-chain-crash.md) | Backend crashes on deep version chains | Fixed | Medium | |
| [013](013-account-node-operations.md) | account() and create_node() not working | Fixed | Medium | |
| [014](014-empty-document-crash.md) | Backend crashes during empty document scenario | Open | High | |
| [015](015-homedocids-filter-ignored.md) | find_links homedocids filter has no effect | Open | Medium | Workaround: filter client-side |

## Summary

- **Fixed:** 11
- **Closed:** 1 (workaround in place)
- **Open:** 3

## Discovery Context

These bugs were discovered while developing golden tests for the Xanadu specification project. The tests exercise the FEBE protocol against the original 1999 C backend.
