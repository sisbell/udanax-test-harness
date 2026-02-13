#!/usr/bin/env python3
"""Test to investigate type subspace (3.x) behavior during link creation.

This test examines what happens to the home document's type subspace when
MAKELINK creates a link with a type endset. Specifically:

1. Does the home document get a span in its type subspace (3.x)?
2. What I-address is stored there - the link ISA or something from the type endset?
3. Does this only happen when the type endset is non-empty?
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE
)

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend/build/backend"))

def test_type_subspace_with_non_empty_type():
    """Create link with non-empty type endset and examine type subspace."""
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create home document
    home_doc = session.create_document()
    home_opened = session.open_document(home_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(home_opened, Address(1, 1), ["Source text"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Check vspanset before link creation
    vspan_before = session.retrieve_vspanset(home_opened)
    print("\n=== BEFORE LINK CREATION ===")
    print(f"Home document vspanset: {vspan_before}")
    for vspec in ([vspan_before] if hasattr(vspan_before, 'docid') else vspan_before):
        for span in vspec.spans:
            print(f"  Span: start={span.start}, width={span.width}")

    # Create link with type endset
    link_source = SpecSet(VSpec(home_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_type = SpecSet([JUMP_TYPE])  # Non-empty type endset

    print(f"\n=== CREATING LINK ===")
    print(f"Type endset: {link_type}")
    link_id = session.create_link(home_opened, link_source, link_target, link_type)
    print(f"Link created: {link_id}")

    # Check vspanset after link creation
    vspan_after = session.retrieve_vspanset(home_opened)
    print("\n=== AFTER LINK CREATION ===")
    print(f"Home document vspanset: {vspan_after}")
    for vspec in ([vspan_after] if hasattr(vspan_after, 'docid') else vspan_after):
        for span in vspec.spans:
            print(f"  Span: start={span.start}, width={span.width}")
            # Try to identify which subspace this is
            start_str = str(span.start)
            if start_str.startswith("0"):
                print(f"    -> Link subspace (normalized)")
            elif start_str.startswith("1"):
                print(f"    -> Text subspace")
            elif start_str.startswith("2"):
                print(f"    -> Link subspace (actual)")
            elif start_str.startswith("3"):
                print(f"    -> TYPE SUBSPACE!")

    # Try to retrieve content from type subspace (3.x)
    print("\n=== PROBING TYPE SUBSPACE (3.x) ===")
    try:
        # Try to retrieve from position 3.1
        type_span = SpecSet(VSpec(home_opened, [Span(Address(3, 1), Offset(0, 10))]))
        type_content = session.retrieve_contents(type_span)
        print(f"Content at 3.1-3.11: {type_content}")
    except Exception as e:
        print(f"Error retrieving from 3.x: {e}")

    # Try broader range
    try:
        type_span_broad = SpecSet(VSpec(home_opened, [Span(Address(3), Offset(1))]))
        type_content_broad = session.retrieve_contents(type_span_broad)
        print(f"Content at 3.0+: {type_content_broad}")
    except Exception as e:
        print(f"Error retrieving from 3+: {e}")

    # Check endsets
    print("\n=== LINK ENDSETS ===")
    doc_span = SpecSet(VSpec(home_opened, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)
    print(f"Source endsets: {source_specs}")
    print(f"Target endsets: {target_specs}")
    print(f"Type endsets: {type_specs}")

    session.close_document(home_opened)
    session.close_document(target_opened)
    session.quit()


def test_type_subspace_with_empty_type():
    """Create link with empty type endset and examine type subspace."""
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create home document
    home_doc = session.create_document()
    home_opened = session.open_document(home_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(home_opened, Address(1, 1), ["Source text"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Check vspanset before link creation
    vspan_before = session.retrieve_vspanset(home_opened)
    print("\n=== BEFORE LINK CREATION (EMPTY TYPE) ===")
    print(f"Home document vspanset: {vspan_before}")

    # Create link with EMPTY type endset
    link_source = SpecSet(VSpec(home_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_type = SpecSet([])  # EMPTY type endset

    print(f"\n=== CREATING LINK WITH EMPTY TYPE ===")
    print(f"Type endset: {link_type}")
    link_id = session.create_link(home_opened, link_source, link_target, link_type)
    print(f"Link created: {link_id}")

    # Check vspanset after link creation
    vspan_after = session.retrieve_vspanset(home_opened)
    print("\n=== AFTER LINK CREATION (EMPTY TYPE) ===")
    print(f"Home document vspanset: {vspan_after}")
    for vspec in ([vspan_after] if hasattr(vspan_after, 'docid') else vspan_after):
        for span in vspec.spans:
            print(f"  Span: start={span.start}, width={span.width}")

    # Check endsets
    print("\n=== LINK ENDSETS (EMPTY TYPE CASE) ===")
    doc_span = SpecSet(VSpec(home_opened, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)
    print(f"Type endsets: {type_specs}")

    session.close_document(home_opened)
    session.close_document(target_opened)
    session.quit()


if __name__ == "__main__":
    print("=" * 70)
    print("TEST 1: Link with non-empty type endset")
    print("=" * 70)
    test_type_subspace_with_non_empty_type()

    print("\n\n")
    print("=" * 70)
    print("TEST 2: Link with empty type endset")
    print("=" * 70)
    test_type_subspace_with_empty_type()
