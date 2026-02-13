#!/usr/bin/env python3
"""Test that two links with identical endsets can be distinguished by their I-addresses."""

import sys
import os

# Get absolute path to backend
script_dir = os.path.dirname(os.path.abspath(__file__))
test_harness_dir = os.path.join(script_dir, '..', '..', '..')
sys.path.insert(0, os.path.join(test_harness_dir, 'febe'))

from client import (
    XuSession, XuConn, PipeStream,
    Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE
)

BACKEND = os.path.join(test_harness_dir, "backend/build/backend")

def test_identical_endsets():
    """Create two links with identical endsets and verify they have different I-addresses."""
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source text here"])

    # Create target document
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target text here"])

    # Create link specifications
    source_span = Span(Address(1, 1), Offset(0, 6))  # "Source"
    source_specs = SpecSet(VSpec(source_opened, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 6))  # "Target"
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    # Create first link
    link1_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))
    print(f"Link 1 I-address: {link1_id}")

    # Create second link with IDENTICAL endsets
    link2_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))
    print(f"Link 2 I-address: {link2_id}")

    # Find both links
    search_specs = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))]))
    found_links = session.find_links(search_specs)
    print(f"\nFound {len(found_links)} links:")
    for link in found_links:
        print(f"  - {link}")

    # Verify they have different I-addresses
    assert str(link1_id) != str(link2_id), "Links should have different I-addresses"
    assert len(found_links) == 2, f"Expected 2 links, found {len(found_links)}"

    # Verify find_links returns both I-addresses
    found_addresses = set(str(link) for link in found_links)
    expected_addresses = {str(link1_id), str(link2_id)}
    assert found_addresses == expected_addresses, \
        f"Found links {found_addresses} don't match expected {expected_addresses}"

    # Verify we can follow each link individually to get the same endsets
    for i, link_id in enumerate([link1_id, link2_id], 1):
        source_endset = session.follow_link(link_id, LINK_SOURCE)
        target_endset = session.follow_link(link_id, LINK_TARGET)
        print(f"\nLink {i} ({link_id}):")
        print(f"  Source endset: {source_endset}")
        print(f"  Target endset: {target_endset}")

        # Verify endsets match expectations
        assert len(source_endset.specs) == 1
        assert len(target_endset.specs) == 1
        assert len(source_endset.specs[0].spans) == 1
        assert len(target_endset.specs[0].spans) == 1

    session.close_document(source_opened)
    session.close_document(target_opened)
    session.quit()

    print("\nSUCCESS: Two links with identical endsets have different I-addresses")
    print("and find_links returns both I-addresses.")

if __name__ == "__main__":
    test_identical_endsets()
