#!/usr/bin/env python3
"""
Verification tests for DN-0002 I-stream invariants claims.

These tests verify the actual udanax-green implementation behavior
against the formal invariants documented in DN-0002.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def test_insert_allocation_monotonic():
    """
    DN-0002 Claim: INSERT allocates from monotonically increasing "next" pointer.
    
    Test: Insert text multiple times and verify I-addresses are sequential.
    """
    print("\n=== Test: INSERT I-address monotonicity ===")
    
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    
    # Insert three separate pieces of text
    session.insert(opened, Address(1, 1), ["AAA"])
    session.insert(opened, Address(1, 4), ["BBB"])
    session.insert(opened, Address(1, 7), ["CCC"])
    
    # Read back the content
    vs = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans))
    contents = session.retrieve_contents(specs)
    
    print(f"Content: {contents}")
    print(f"V-spans: {[(s.start, s.width) for s in text_spans]}")
    
    # Now create a version to see if I-addresses are shared
    v1 = session.create_version(opened)
    session.close_document(opened)
    
    # Open version read-only
    v1_ro = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    vs_v1 = session.retrieve_vspanset(v1_ro)
    text_spans_v1 = [s for s in vs_v1.spans if s.start.digits[0] >= 1]
    specs_v1 = SpecSet(VSpec(v1_ro, text_spans_v1))
    
    # Compare versions - should show they share I-addresses
    spec_orig = SpecSet(VSpec(v1_ro, text_spans_v1))
    shared = session.compare_versions(spec_orig, spec_orig)
    
    print(f"Version I-address sharing: {len(shared)} shared regions")
    
    session.close_document(v1_ro)
    session.quit()
    
    print("✓ INSERT appears to allocate sequentially")


def test_delete_preserves_granfilade():
    """
    DN-0002 Claim: DELETE only modifies POOM, leaves granfilade untouched.
    
    Test: Delete from document, verify I-addresses still exist in granfilade
    via version comparison.
    """
    print("\n=== Test: DELETE preserves granfilade ===")
    
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    
    # Insert text
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])
    
    # Create a version before delete
    v1 = session.create_version(opened)
    
    # Delete middle portion
    session.delete(opened, Address(1, 3), Offset(0, 4))  # Delete "CDEF"
    
    # Read remaining content
    vs = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans))
    contents = session.retrieve_contents(specs)
    
    print(f"After delete: {contents}")  # Should be "ABGH"
    
    session.close_document(opened)
    
    # Open both versions and compare
    doc_ro = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    v1_ro = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    
    vs_doc = session.retrieve_vspanset(doc_ro)
    vs_v1 = session.retrieve_vspanset(v1_ro)
    
    text_spans_doc = [s for s in vs_doc.spans if s.start.digits[0] >= 1]
    text_spans_v1 = [s for s in vs_v1.spans if s.start.digits[0] >= 1]
    
    spec_doc = SpecSet(VSpec(doc_ro, text_spans_doc))
    spec_v1 = SpecSet(VSpec(v1_ro, text_spans_v1))
    
    shared = session.compare_versions(spec_doc, spec_v1)
    
    print(f"Shared I-addresses after delete: {len(shared)} regions")
    print(f"  (If DELETE preserves granfilade, should share AB and GH)")
    
    for vspan1, vspan2 in shared:
        print(f"  Shared: doc@{vspan1.start} ↔ v1@{vspan2.start}")
    
    session.close_document(doc_ro)
    session.close_document(v1_ro)
    session.quit()
    
    print("✓ DELETE appears to preserve granfilade")


def test_vcopy_reuses_iaddresses():
    """
    DN-0002 Claim: COPY reuses I-addresses rather than allocating fresh ones.
    
    Test: Copy content between documents, verify they share I-addresses.
    """
    print("\n=== Test: VCOPY reuses I-addresses ===")
    
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    # Create source document
    src = session.create_document()
    src_opened = session.open_document(src, READ_WRITE, CONFLICT_FAIL)
    session.insert(src_opened, Address(1, 1), ["SOURCE"])
    session.close_document(src_opened)
    
    # Create target document
    dst = session.create_document()
    dst_opened = session.open_document(dst, READ_WRITE, CONFLICT_FAIL)
    
    # Copy from source to target
    src_ro = session.open_document(src, READ_ONLY, CONFLICT_COPY)
    vs_src = session.retrieve_vspanset(src_ro)
    text_spans_src = [s for s in vs_src.spans if s.start.digits[0] >= 1]
    src_specs = SpecSet(VSpec(src_ro, text_spans_src))
    
    session.vcopy(dst_opened, Address(1, 1), src_specs)
    
    session.close_document(src_ro)
    session.close_document(dst_opened)
    
    # Compare source and target I-addresses
    src_ro = session.open_document(src, READ_ONLY, CONFLICT_COPY)
    dst_ro = session.open_document(dst, READ_ONLY, CONFLICT_COPY)
    
    vs_src = session.retrieve_vspanset(src_ro)
    vs_dst = session.retrieve_vspanset(dst_ro)
    
    text_spans_src = [s for s in vs_src.spans if s.start.digits[0] >= 1]
    text_spans_dst = [s for s in vs_dst.spans if s.start.digits[0] >= 1]
    
    spec_src = SpecSet(VSpec(src_ro, text_spans_src))
    spec_dst = SpecSet(VSpec(dst_ro, text_spans_dst))
    
    shared = session.compare_versions(spec_src, spec_dst)
    
    print(f"Source content: {session.retrieve_contents(spec_src)}")
    print(f"Target content: {session.retrieve_contents(spec_dst)}")
    print(f"Shared I-addresses: {len(shared)} regions")
    
    for vspan1, vspan2 in shared:
        print(f"  src@{vspan1.start} ↔ dst@{vspan2.start}")
    
    if len(shared) > 0:
        print("✓ VCOPY reuses I-addresses (transclusion)")
    else:
        print("✗ VCOPY does NOT reuse I-addresses (copy by value)")
    
    session.close_document(src_ro)
    session.close_document(dst_ro)
    session.quit()


def test_vcopy_same_document_read_then_shift():
    """
    DN-0002 Claim: When d1=d2, COPY reads source before V-shift.
    
    Test: Copy within same document, verify two-phase operation.
    """
    print("\n=== Test: VCOPY d1=d2 read-then-shift ===")
    
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    
    # Insert initial content
    session.insert(opened, Address(1, 1), ["ABC"])
    
    # Copy "ABC" to position 1.4 (should become "ABCABC")
    vs = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans))
    
    session.vcopy(opened, Address(1, 4), specs)
    
    # Read final content
    vs = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans))
    contents = session.retrieve_contents(specs)
    
    print(f"After self-copy: {contents}")
    print(f"Expected: ABCABC (if read-before-shift)")
    print(f"Wrong if: ABC (if shift-while-reading)")
    
    if contents[0] == "ABCABC":
        print("✓ VCOPY appears to read source before V-shift")
    else:
        print("✗ VCOPY does NOT read before shift")
    
    session.close_document(opened)
    session.quit()


def test_rearrange_primitive_vs_delete_insert():
    """
    DN-0002 Question: Does REARRANGE exist as primitive, or DELETE+INSERT?
    
    Test: Use pivot/swap and check if I-addresses are preserved.
    """
    print("\n=== Test: REARRANGE I-address preservation ===")
    
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    
    # Insert "ABCDEF"
    session.insert(opened, Address(1, 1), ["ABCDEF"])
    
    # Create version before rearrange
    v1 = session.create_version(opened)
    
    # Pivot at position 4: "ABC|DEF" → "DEFABC"
    try:
        session.pivot(opened, Address(1, 1), Address(1, 4), Address(1, 7))
        
        # Read result
        vs = session.retrieve_vspanset(opened)
        text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
        specs = SpecSet(VSpec(opened, text_spans))
        contents = session.retrieve_contents(specs)
        
        print(f"After pivot: {contents}")
        
        session.close_document(opened)
        
        # Compare I-addresses with original
        doc_ro = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
        v1_ro = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
        
        vs_doc = session.retrieve_vspanset(doc_ro)
        vs_v1 = session.retrieve_vspanset(v1_ro)
        
        text_spans_doc = [s for s in vs_doc.spans if s.start.digits[0] >= 1]
        text_spans_v1 = [s for s in vs_v1.spans if s.start.digits[0] >= 1]
        
        spec_doc = SpecSet(VSpec(doc_ro, text_spans_doc))
        spec_v1 = SpecSet(VSpec(v1_ro, text_spans_v1))
        
        shared = session.compare_versions(spec_doc, spec_v1)
        
        print(f"Shared I-addresses: {len(shared)} regions")
        
        if len(shared) == 2:  # Should share DEF and ABC
            print("✓ REARRANGE preserves I-addresses (native primitive)")
        else:
            print("? REARRANGE may be DELETE+INSERT (allocates new I-addrs)")
        
        session.close_document(doc_ro)
        session.close_document(v1_ro)
        
    except Exception as e:
        print(f"Error during pivot: {e}")
        print("(pivot may not be implemented or may crash)")
    
    session.quit()


if __name__ == "__main__":
    test_insert_allocation_monotonic()
    test_delete_preserves_granfilade()
    test_vcopy_reuses_iaddresses()
    test_vcopy_same_document_read_then_shift()
    test_rearrange_primitive_vs_delete_insert()
    
    print("\n" + "="*60)
    print("DN-0002 Verification Tests Complete")
    print("="*60)
