#!/usr/bin/env python3
"""Test to examine what's stored inside the link orgl itself.

This test attempts to open the link as if it were a document and examine
its internal structure to see where the endsets are actually stored.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    JUMP_TYPE
)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend/build/backend"))

def test_link_orgl_structure():
    """Create a link and try to examine its internal structure."""
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create home document
    home_doc = session.create_document()
    home_opened = session.open_document(home_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(home_opened, Address(1, 1), ["Source text here"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link with type endset
    link_source = SpecSet(VSpec(home_opened, [Span(Address(1, 1), Offset(0, 11))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_type = SpecSet([JUMP_TYPE])

    link_id = session.create_link(home_opened, link_source, link_target, link_type)
    print(f"Created link: {link_id}")
    print(f"Link home doc: {home_doc}")

    # Try to open the link as if it were a document
    print("\n=== ATTEMPTING TO OPEN LINK AS DOCUMENT ===")
    try:
        link_opened = session.open_document(link_id, READ_ONLY, CONFLICT_FAIL)
        print(f"Successfully opened link orgl!")

        # Try to get its vspanset
        link_vspanset = session.retrieve_vspanset(link_opened)
        print(f"Link orgl vspanset: {link_vspanset}")
        for vspec in ([link_vspanset] if hasattr(link_vspanset, 'docid') else link_vspanset):
            for span in vspec.spans:
                start_str = str(span.start)
                print(f"  Span: start={span.start}, width={span.width}")
                if start_str.startswith("1"):
                    print(f"    -> Subspace 1 (source endset in link orgl)")
                elif start_str.startswith("2"):
                    print(f"    -> Subspace 2 (target endset in link orgl)")
                elif start_str.startswith("3"):
                    print(f"    -> Subspace 3 (type endset in link orgl!)")

        # Try to retrieve contents from different subspaces
        print("\n=== PROBING LINK ORGL SUBSPACES ===")
        for subspace in [1, 2, 3]:
            try:
                probe = SpecSet(VSpec(link_opened, [Span(Address(subspace, 1), Offset(0, 20))]))
                content = session.retrieve_contents(probe)
                print(f"Subspace {subspace}: {len(content)} bytes")
                if content:
                    print(f"  Content (hex): {content[:20].hex() if len(content) > 0 else 'empty'}")
            except Exception as e:
                print(f"Subspace {subspace}: Error - {e}")

        session.close_document(link_opened)
    except Exception as e:
        print(f"Cannot open link as document: {e}")

    # For comparison, check home document structure
    print("\n=== HOME DOCUMENT STRUCTURE ===")
    home_vspanset = session.retrieve_vspanset(home_opened)
    print(f"Home doc vspanset: {home_vspanset}")
    for vspec in ([home_vspanset] if hasattr(home_vspanset, 'docid') else home_vspanset):
        for span in vspec.spans:
            start_str = str(span.start)
            print(f"  Span: start={span.start}, width={span.width}")
            if start_str.startswith("0") or start_str.startswith("2"):
                print(f"    -> Link subspace (contains reference to link orgl)")
            elif start_str.startswith("1"):
                print(f"    -> Text subspace")
            elif start_str.startswith("3"):
                print(f"    -> Type subspace (UNEXPECTED!)")

    session.close_document(home_opened)
    session.close_document(target_opened)
    session.quit()


if __name__ == "__main__":
    test_link_orgl_structure()
