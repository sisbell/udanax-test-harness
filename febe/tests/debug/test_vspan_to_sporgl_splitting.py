"""
Test whether a single V-span that maps to discontiguous I-addresses
produces multiple sporgl entries in the COPY path.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, READ_ONLY, CONFLICT_FAIL, CONFLICT_COPY
)

def test_single_vspan_discontiguous_iaddresses():
    BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    # Create documents
    doc_a = session.create_document()
    doc_b = session.create_document()
    doc_c = session.create_document()
    doc_d = session.create_document()
    
    # Open documents
    handle_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    handle_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    handle_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    handle_d = session.open_document(doc_d, READ_WRITE, CONFLICT_FAIL)
    
    # Insert content into A and B
    session.insert(handle_a, Address(1, 1), ["XX"])
    session.insert(handle_b, Address(1, 1), ["YY"])
    
    # Build C with interleaved content from A and B: "XYX"
    session.vcopy(handle_c, Address(1, 1), SpecSet(VSpec(handle_a, [Span(Address(1, 1), Offset(0, 1))])))
    session.vcopy(handle_c, Address(1, 2), SpecSet(VSpec(handle_b, [Span(Address(1, 1), Offset(0, 1))])))
    session.vcopy(handle_c, Address(1, 3), SpecSet(VSpec(handle_a, [Span(Address(1, 1), Offset(0, 1))])))
    
    # Verify C has "XYX"
    content_c = "".join(session.retrieve_contents(SpecSet(VSpec(handle_c, [Span(Address(1, 1), Offset(0, 3))]))))
    assert content_c == "XYX", f"Expected 'XYX', got {content_c}"
    
    # Now COPY the entire V-span [1.1, width 0.3] from C to D
    session.vcopy(handle_d, Address(1, 1), SpecSet(VSpec(handle_c, [Span(Address(1, 1), Offset(0, 3))])))
    
    # Verify D has "XYX"
    content_d = "".join(session.retrieve_contents(SpecSet(VSpec(handle_d, [Span(Address(1, 1), Offset(0, 3))]))))
    assert content_d == "XYX", f"Expected 'XYX', got {content_d}"
    
    # Compare D with C
    comparison = session.compare_versions(
        SpecSet(VSpec(handle_d, [Span(Address(1, 1), Offset(0, 3))])),
        SpecSet(VSpec(handle_c, [Span(Address(1, 1), Offset(0, 3))]))
    )
    
    print("\nComparison results (D vs C):")
    print(f"Number of shared regions: {len(comparison)}")
    for idx, (d_vspan, c_vspan) in enumerate(comparison):
        print(f"  Region {idx+1}: D:{d_vspan.span} <-> C:{c_vspan.span}")
    
    # Compare D with originals
    comp_d_a = session.compare_versions(
        SpecSet(VSpec(handle_d, [Span(Address(1, 1), Offset(0, 3))])),
        SpecSet(VSpec(handle_a, [Span(Address(1, 1), Offset(0, 2))]))
    )
    
    comp_d_b = session.compare_versions(
        SpecSet(VSpec(handle_d, [Span(Address(1, 1), Offset(0, 3))])),
        SpecSet(VSpec(handle_b, [Span(Address(1, 1), Offset(0, 2))]))
    )
    
    print("\nComparison with original A:")
    for idx, (d_vspan, a_vspan) in enumerate(comp_d_a):
        print(f"  D:{d_vspan.span} <-> A:{a_vspan.span}")
    
    print("\nComparison with original B:")
    for idx, (d_vspan, b_vspan) in enumerate(comp_d_b):
        print(f"  D:{d_vspan.span} <-> B:{b_vspan.span}")
    
    session.quit()
    
    return {
        "test": "single_vspan_discontiguous_iaddresses",
        "source_c_content": "XYX",
        "source_c_structure": ["X from A", "Y from B", "X from A"],
        "dest_d_content": content_d,
        "num_shared_regions_with_C": len(comparison),
        "num_shared_regions_with_A": len(comp_d_a),
        "num_shared_regions_with_B": len(comp_d_b),
        "shared_regions_with_C": [
            {"d": str(d.span), "c": str(c.span)} for d, c in comparison
        ]
    }

if __name__ == "__main__":
    result = test_single_vspan_discontiguous_iaddresses()
    import json
    print(json.dumps(result, indent=2))
