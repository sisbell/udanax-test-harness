"""Test VCOPY operation with overlapping source I-ranges to trace insertspanf behavior."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL
)

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def test_copy_overlapping_source_irange():
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    
    try:
        session.account(Address(1, 1, 0, 1))
        
        # Create source document with text
        d1 = session.create_document()
        d1_open = session.open_document(d1, READ_WRITE, CONFLICT_FAIL)
        session.insert(d1_open, Address(1, 1), ["ABCDEFGH"])
        
        # Verify insert worked
        vspanset_d1 = session.retrieve_vspanset(d1_open)
        print(f"D1 vspanset after insert: {vspanset_d1}")
        specset_d1 = SpecSet(VSpec(d1_open, list(vspanset_d1.spans)))
        contents_d1 = session.retrieve_contents(specset_d1)
        print(f"D1 contents: {contents_d1}")
        assert contents_d1 == ["ABCDEFGH"]
        
        # Create destination document
        d2 = session.create_document()
        d2_open = session.open_document(d2, READ_WRITE, CONFLICT_FAIL)
        
        # First VCOPY: copy "ABC" from d1[1.1:1.4] to d2[1.1]
        # Source is at I-space addresses from d1's insert
        src1 = SpecSet(VSpec(d1_open, [Span(Address(1, 1), Offset(0, 3))]))
        session.vcopy(d2_open, Address(1, 1), src1)
        
        # Verify first VCOPY worked
        vspanset_d2_1 = session.retrieve_vspanset(d2_open)
        print(f"D2 vspanset after first VCOPY: {vspanset_d2_1}")
        specset_d2_1 = SpecSet(VSpec(d2_open, list(vspanset_d2_1.spans)))
        contents_d2_1 = session.retrieve_contents(specset_d2_1)
        print(f"D2 contents after first VCOPY: {contents_d2_1}")
        
        # Second VCOPY: copy "BCD" from d1[1.2:1.5] to d2[2.1]  
        # This overlaps first copy's I-range in source ("BC" is shared in I-space)
        src2 = SpecSet(VSpec(d1_open, [Span(Address(1, 2), Offset(0, 3))]))
        session.vcopy(d2_open, Address(2, 1), src2)
        
        # Verify second VCOPY worked
        vspanset_d2_2 = session.retrieve_vspanset(d2_open)
        print(f"D2 vspanset after second VCOPY: {vspanset_d2_2}")
        specset_d2_2 = SpecSet(VSpec(d2_open, list(vspanset_d2_2.spans)))
        contents_d2_2 = session.retrieve_contents(specset_d2_2)
        print(f"D2 contents after second VCOPY: {contents_d2_2}")
        
        # Expected: two vspans, both content present
        print(f"\nActual vspans: {len(vspanset_d2_2.spans)}")
        for i, span in enumerate(vspanset_d2_2.spans):
            print(f"  Span {i}: {span}")
        
        session.close_document(d2_open)
        session.close_document(d1_open)
        
        print("\nAnalysis:")
        print("Call chain from VCOPY to insertspanf:")
        print("  1. docopy [do1.c:45-64]:")
        print("       insertpm(taskptr, docisaptr, docorgl, vsaptr, ispanset)  [line 60]")
        print("       insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN) [line 62]")
        print("  2. insertspanf [spanf1.c:15-54]:")
        print("       prefixtumbler(isaptr, spantype, &crumorigin.dsas[ORGLRANGE])  [line 22]")
        print("         → ORGLRANGE = 4.(d2_isa) for both VCOPYs")
        print("       insertnd(taskptr, spanfptr, &crumorigin, &crumwidth, &linfo, SPANRANGE) [line 51]")
        print("  3. Second VCOPY's insertnd should encounter first's leaf:")
        print("       whereoncrum(ptr, offset, &I2.start, SPANRANGE) → THRUME if I-ranges overlap")
        print("       → triggers slicecbcpm [ndcuts.c:83] to split the leaf")
        
    finally:
        session.quit()

if __name__ == "__main__":
    test_copy_overlapping_source_irange()
