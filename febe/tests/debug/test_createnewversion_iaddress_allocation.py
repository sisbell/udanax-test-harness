"""
Test: Does CREATENEWVERSION advance Σ.next (the content allocation counter)?

Strategy:
1. Create doc1, INSERT "ABC" → observe I-addresses
2. CREATENEWVERSION → doc2
3. INSERT "XYZ" into doc1 → observe I-addresses
4. Compare I-addresses to see if CREATENEWVERSION consumed any

Expected behavior (hypothesis):
- CREATENEWVERSION allocates a document address via findisatoinsertnonmolecule
- It does NOT allocate content I-addresses (it copies SPAN entries, doesn't call findisatoinsertgr)
- Therefore Σ.next should be unchanged after CREATENEWVERSION
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY, NOSPECS
)

def test_createnewversion_does_not_advance_content_allocation():
    """Test that CREATENEWVERSION does not consume content I-addresses."""
    backend_path = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')
    stream = PipeStream(f"{backend_path} --test-mode")
    session = XuSession(XuConn(stream))
    
    try:
        # Setup
        session.account(Address(1, 1, 0, 1))
        
        # 1. Create doc1 and insert "ABC"
        doc1 = session.create_document()
        doc1_opened = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
        session.insert(doc1_opened, Address(1, 1), ["ABC"])
        
        # Retrieve I-addresses of ABC
        vspec = session.retrieve_vspanset(doc1_opened)
        print(f"After INSERT ABC: vspec = {vspec}")
        
        # Get compare_versions to see I-addresses
        doc1_ro = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
        doc1_vs = session.retrieve_vspanset(doc1_ro)
        doc1_specs = SpecSet(VSpec(doc1_ro, list(doc1_vs.spans)))
        
        # Compare doc1 with itself to see I-addresses (should be identity mapping)
        comparison1 = session.compare_versions(doc1_specs, doc1_specs)
        print(f"ABC I-addresses (num pairs): {len(comparison1)}")
        print(f"ABC I-addresses (pairs): {comparison1}")
        
        if len(comparison1) > 0:
            abc_ispan = comparison1[0][0]  # First pair, source side
            print(f"ABC I-span starts at: {abc_ispan.start()}")
        
        session.close_document(doc1_ro)
        
        # 2. CREATENEWVERSION
        doc2 = session.create_version(doc1_opened)
        print(f"\nCreated version: {doc2}")
        
        # 3. INSERT "XYZ" into doc1
        session.insert(doc1_opened, Address(1, 4), ["XYZ"])  # Insert after "ABC"
        
        # Retrieve the updated V-span
        vspec2 = session.retrieve_vspanset(doc1_opened)
        print(f"\nAfter INSERT XYZ: vspec = {vspec2}")
        
        # Get I-addresses of the full document
        doc1_ro2 = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
        doc1_vs2 = session.retrieve_vspanset(doc1_ro2)
        doc1_specs2 = SpecSet(VSpec(doc1_ro2, list(doc1_vs2.spans)))
        comparison2 = session.compare_versions(doc1_specs2, doc1_specs2)
        print(f"ABCXYZ I-addresses (num pairs): {len(comparison2)}")
        print(f"ABCXYZ I-addresses (pairs): {comparison2}")
        
        # Analysis: Are there 1 or 2 shared span pairs?
        # - 1 span pair → XYZ I-addresses are contiguous with ABC (CREATENEWVERSION didn't consume)
        # - 2 span pairs → XYZ I-addresses have a gap from ABC (CREATENEWVERSION consumed)
        
        num_shared_pairs = len(comparison2)
        print(f"\nNumber of shared I-span pairs: {num_shared_pairs}")
        
        if num_shared_pairs == 1:
            print("✓ CREATENEWVERSION did NOT advance Σ.next (content allocation counter)")
            print("  XYZ I-addresses are contiguous with ABC")
            single_span = comparison2[0][0]
            print(f"  Combined I-span: {single_span.start()} + {single_span.span.width}")
        elif num_shared_pairs == 2:
            print("✗ CREATENEWVERSION DID advance Σ.next")
            print("  XYZ I-addresses have a gap from ABC")
            abc_span = comparison2[0][0]
            xyz_span = comparison2[1][0]
            print(f"  ABC I-span: {abc_span.start()} + {abc_span.span.width}")
            print(f"  XYZ I-span: {xyz_span.start()} + {xyz_span.span.width}")
        else:
            print(f"? Unexpected result: {num_shared_pairs} shared pairs")
        
        # Also check: did doc2 get allocated a document address?
        print(f"\nDocument addresses:")
        print(f"  doc1: {doc1}")
        print(f"  doc2: {doc2}")
        
        # doc2 should be a child of doc1 (e.g., 1.1.0.1.0.1 → 1.1.0.1.0.1.1)
        # This confirms that findisatoinsertnonmolecule WAS called for the document
        
        session.close_document(doc1_ro2)
        session.close_document(doc1_opened)
        session.quit()
        
        # Assertion for test framework
        assert num_shared_pairs == 1, f"Expected 1 shared span pair (contiguous I-addresses), got {num_shared_pairs}"
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        session.quit()
        raise

if __name__ == "__main__":
    test_createnewversion_does_not_advance_content_allocation()
