#!/usr/bin/env python3
"""
Test DELETE behavior when cut points align exactly with bottom crum boundaries.

This test verifies whether slicecbcpm is called even when the deletion boundaries
coincide exactly with existing crum boundaries, and whether it can produce
zero-width pieces.

Background:
- DELETE Phase 1 calls makecutsnd() which cuts bottom crums at boundaries
- At height 0 (bottom crums), makecutsbackuptohere() calls slicecbcpm if whereoncrum == THRUME
- whereoncrum returns THRUME if cut is strictly interior to crum
- whereoncrum returns ONMYLEFTBORDER if cut equals crum's grasp (left edge)
- whereoncrum returns ONMYRIGHTBORDER if cut equals crum's reach (right edge)

Questions:
1. If DELETE start == crum.grasp, is whereoncrum == THRUME? (No - it's ONMYLEFTBORDER)
2. If DELETE end == crum.reach, is whereoncrum == THRUME? (No - it's ONMYRIGHTBORDER)
3. Can slicecbcpm ever be called with a cut at the exact boundary?
4. Can localcut.mantissa[0] ever be 0 or equal to cwid.mantissa[0]?
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')


def test_delete_single_insert_exact_boundaries():
    """
    Delete a span that exactly matches a single INSERT allocation.

    Setup:
    - INSERT "ABC" at 1.1 (allocates one bottom crum)
    - DELETE from 1.1 to 1.4 (exact span)

    Expected:
    - whereoncrum(1.1) on the "ABC" crum returns ONMYLEFTBORDER (not THRUME)
    - whereoncrum(1.4) on the "ABC" crum returns ONMYRIGHTBORDER (not THRUME)
    - slicecbcpm is NOT called (no interior cut)
    - The entire crum is classified for deletion
    """
    print("\n=== Test: DELETE with exact single-crum boundaries ===")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Single insert
    session.insert(opened, Address(1, 1), ["ABC"])

    # Verify content before delete
    vs = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs.spans if s.start.digits[0] >= 1]
    print(f"Before delete: {text_spans[0].start} width {text_spans[0].width}")

    # Delete exact span
    session.delete(opened, Address(1, 1), Offset(0, 3))

    # Check result
    vs_after = session.retrieve_vspanset(opened)
    if vs_after is None or len([s for s in vs_after.spans if s.start.digits[0] >= 1]) == 0:
        print("✓ Document is empty - entire crum deleted without cutting")
    else:
        text_spans_after = [s for s in vs_after.spans if s.start.digits[0] >= 1]
        print(f"✗ Document not empty: {text_spans_after}")

    session.close_document(opened)
    session.quit()


def test_delete_start_boundary_aligned():
    """
    Delete with start boundary aligned to crum boundary, end interior.

    Setup:
    - INSERT "ABCDEF" at 1.1
    - DELETE from 1.1 to 1.4 (delete "ABC", keep "DEF")

    Expected:
    - Deletion start (1.1) aligns with crum grasp
    - Deletion end (1.4) is interior to crum
    - whereoncrum(1.1) returns ONMYLEFTBORDER
    - whereoncrum(1.4) returns THRUME
    - slicecbcpm IS called for the 1.4 cut
    - localcut would be (1.4 - grasp 1.1) = 0.3
    """
    print("\n=== Test: DELETE with start-aligned boundary ===")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEF"])

    vs_before = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs_before.spans if s.start.digits[0] >= 1]
    print(f"Before: {text_spans[0].start} width {text_spans[0].width}")

    # Delete first 3 characters
    session.delete(opened, Address(1, 1), Offset(0, 3))

    vs_after = session.retrieve_vspanset(opened)
    text_spans_after = [s for s in vs_after.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans_after))
    contents = session.retrieve_contents(specs)

    print(f"After: {contents}")
    print(f"V-span: {text_spans_after[0].start} width {text_spans_after[0].width}")

    if contents[0] == "DEF":
        print("✓ Deletion succeeded - start boundary handled correctly")
    else:
        print(f"✗ Expected 'DEF', got '{contents[0]}'")

    session.close_document(opened)
    session.quit()


def test_delete_end_boundary_aligned():
    """
    Delete with start interior, end boundary aligned to crum boundary.

    Setup:
    - INSERT "ABCDEF" at 1.1
    - DELETE from 1.4 to 1.7 (delete "DEF", keep "ABC")

    Expected:
    - Deletion start (1.4) is interior to crum
    - Deletion end (1.7) aligns with crum reach
    - whereoncrum(1.4) returns THRUME
    - whereoncrum(1.7) returns ONMYRIGHTBORDER
    - slicecbcpm IS called for the 1.4 cut
    - localcut would be (1.4 - grasp 1.1) = 0.3
    """
    print("\n=== Test: DELETE with end-aligned boundary ===")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEF"])

    vs_before = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs_before.spans if s.start.digits[0] >= 1]
    print(f"Before: {text_spans[0].start} width {text_spans[0].width}")

    # Delete last 3 characters
    session.delete(opened, Address(1, 4), Offset(0, 3))

    vs_after = session.retrieve_vspanset(opened)
    text_spans_after = [s for s in vs_after.spans if s.start.digits[0] >= 1]
    specs = SpecSet(VSpec(opened, text_spans_after))
    contents = session.retrieve_contents(specs)

    print(f"After: {contents}")
    print(f"V-span: {text_spans_after[0].start} width {text_spans_after[0].width}")

    if contents[0] == "ABC":
        print("✓ Deletion succeeded - end boundary handled correctly")
    else:
        print(f"✗ Expected 'ABC', got '{contents[0]}'")

    session.close_document(opened)
    session.quit()


def test_delete_spanning_two_crums():
    """
    Delete a span that crosses a crum boundary created by two separate INSERTs.

    Setup:
    - INSERT "ABC" at 1.1 (creates crum at I-addr X)
    - INSERT "DEF" at 1.4 (creates crum at I-addr Y, adjacent in V-space)
    - DELETE from 1.2 to 1.6 (delete "BC" from first crum, "DE" from second)

    Expected:
    - Two crums at bottom level
    - Deletion start (1.2) is interior to first crum → THRUME
    - Deletion end (1.6) is interior to second crum → THRUME
    - slicecbcpm called twice (once per crum)
    - Result: "A" + "F"
    """
    print("\n=== Test: DELETE spanning two separate crums ===")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Two separate inserts create two bottom crums
    session.insert(opened, Address(1, 1), ["ABC"])
    session.insert(opened, Address(1, 4), ["DEF"])

    vs_before = session.retrieve_vspanset(opened)
    text_spans = [s for s in vs_before.spans if s.start.digits[0] >= 1]
    specs_before = SpecSet(VSpec(opened, text_spans))
    contents_before = session.retrieve_contents(specs_before)
    print(f"Before: {contents_before}")

    # Delete across the boundary
    session.delete(opened, Address(1, 2), Offset(0, 4))

    vs_after = session.retrieve_vspanset(opened)
    text_spans_after = [s for s in vs_after.spans if s.start.digits[0] >= 1]
    specs_after = SpecSet(VSpec(opened, text_spans_after))
    contents_after = session.retrieve_contents(specs_after)

    print(f"After: {contents_after}")

    if contents_after == ["A", "F"]:
        print("✓ Cross-crum deletion succeeded - both crums cut")
    elif len(contents_after) == 1 and contents_after[0] == "AF":
        print("✓ Cross-crum deletion succeeded - crums merged")
    else:
        print(f"? Unexpected result: {contents_after}")

    session.close_document(opened)
    session.quit()


def test_delete_between_crums():
    """
    Delete in the gap between two non-adjacent crums.

    Setup:
    - INSERT "ABC" at 1.1
    - INSERT "XYZ" at 1.10
    - DELETE from 1.5 to 1.8 (in the gap)

    Expected:
    - No crums intersect the deletion range
    - No cuts made
    - Content unchanged
    """
    print("\n=== Test: DELETE in gap between crums ===")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABC"])
    session.insert(opened, Address(1, 10), ["XYZ"])

    vs_before = session.retrieve_vspanset(opened)
    text_spans_before = [s for s in vs_before.spans if s.start.digits[0] >= 1]
    specs_before = SpecSet(VSpec(opened, text_spans_before))
    contents_before = session.retrieve_contents(specs_before)
    print(f"Before: {contents_before}, spans: {len(text_spans_before)}")

    # Delete in the gap
    session.delete(opened, Address(1, 5), Offset(0, 3))

    vs_after = session.retrieve_vspanset(opened)
    text_spans_after = [s for s in vs_after.spans if s.start.digits[0] >= 1]
    specs_after = SpecSet(VSpec(opened, text_spans_after))
    contents_after = session.retrieve_contents(specs_after)

    print(f"After: {contents_after}, spans: {len(text_spans_after)}")

    if contents_after == contents_before:
        print("✓ Gap deletion has no effect on content (as expected)")
    else:
        print(f"? Content changed: {contents_before} → {contents_after}")

    # Check if V-positions shifted
    if len(text_spans_after) >= 2:
        if text_spans_after[1].start == Address(1, 7):
            print("✓ Second span shifted by -3 (gap collapsed)")
        elif text_spans_after[1].start == Address(1, 10):
            print("✗ Second span NOT shifted (gap remains)")

    session.close_document(opened)
    session.quit()


if __name__ == "__main__":
    test_delete_single_insert_exact_boundaries()
    test_delete_start_boundary_aligned()
    test_delete_end_boundary_aligned()
    test_delete_spanning_two_crums()
    test_delete_between_crums()

    print("\n" + "="*70)
    print("DELETE Boundary Alignment Tests Complete")
    print("="*70)
    print("\nCode Analysis Summary:")
    print("- whereoncrum() returns ONMYLEFTBORDER when cut == crum.grasp")
    print("- whereoncrum() returns ONMYRIGHTBORDER when cut == crum.reach")
    print("- whereoncrum() returns THRUME only for INTERIOR cuts")
    print("- slicecbcpm() is called ONLY when whereoncrum() == THRUME")
    print("- Therefore: boundary-aligned cuts do NOT trigger slicecbcpm")
    print("- localcut.mantissa[0] is always > 0 and < cwid.mantissa[0]")
    print("  (because slicecbcpm requires THRUME, which means interior)")
