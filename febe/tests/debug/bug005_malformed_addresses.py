#!/usr/bin/env python3
"""
Test for Bug 005: pyxi link type addresses - FIXED.

This test documents what pyxi used to use vs the correct addresses.

OLD (wrong):
  LINK_DOCID = Address(1, 1, 0, 1, 0, 2)
  This was: Node.0.User.0.Doc = "document 2" (no element field)

NEW (correct):
  LINK_TYPES_DOC = Address(1, 1, 0, 1, 0, 1)  # Document 1
  Types reference link subspace: Address(1, 0, 2, X) for type X

See bugs/005-pyxi-link-type-addresses.md for details.
See resources/link-registry/link-types.md for the type registry.
"""

import sys
sys.path.insert(0, '.')

from client import (
    Address, LINK_TYPES_DOC, JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE
)


def test_fixed_addresses():
    """Verify the corrected link type addresses."""

    print("=== Bug 005: Link Type Addresses - FIXED ===\n")

    print(f"LINK_TYPES_DOC = {LINK_TYPES_DOC}")
    print(f"  Digits: {LINK_TYPES_DOC.digits}")
    print()

    print("Correct structure:")
    print("  1.1.0.1.0.1")
    print("  ├─ 1.1    = Node 1, dimension 1")
    print("  ├─ 0.1    = User 1")
    print("  └─ 0.1    = Document 1 (bootstrap doc with type definitions)")
    print()

    print("Type VSpecs (corrected):")
    for name, vspec in [("JUMP_TYPE", JUMP_TYPE), ("QUOTE_TYPE", QUOTE_TYPE),
                        ("FOOTNOTE_TYPE", FOOTNOTE_TYPE), ("MARGIN_TYPE", MARGIN_TYPE)]:
        print(f"  {name} = {vspec}")
        span = vspec.spans[0]
        print(f"    docid: {vspec.docid}")
        print(f"    local addr: {span.start} (version.0.link_subspace.type)")
        print()

    print("Type numbers from registry (resources/link-registry/link-types-relationship.md):")
    print("  2.2 = jump")
    print("  2.3 = quote")
    print("  2.6 = footnote")
    print("  2.6.2 = footnote.margin")
    print()

    # Verify correct structure
    expected_doc = Address(1, 1, 0, 1, 0, 1)
    assert LINK_TYPES_DOC == expected_doc, f"LINK_TYPES_DOC wrong: {LINK_TYPES_DOC}"

    print("Bug 005 FIXED: Link types now use proper element addresses in doc 1's link subspace")
    return True


if __name__ == "__main__":
    test_fixed_addresses()
