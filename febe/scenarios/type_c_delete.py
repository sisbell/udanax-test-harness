"""Test scenarios to verify EWD-022 Type C claims about single-character DELETE.

EWD-022 claims:
"DELETE of [v, v+1) in the interior of a crum. Two knife cuts split the crum
into three pieces; the middle piece (width 1) is removed: Δc(Type C) = +1
(2 splits - 1 removal)"

This test verifies:
1. Does DELETE make two knife cuts at v and v+1?
2. After two cuts in the interior of a single crum, do we get exactly 3 pieces?
3. Is the middle piece removed, leaving 2 pieces (net Δc = +1)?
4. What happens at crum boundaries (v at left edge, v+1 at right edge)?
"""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_type_c_interior_delete(session):
    """Delete a single character in the interior of a crum.

    Setup: Insert "ABCDEFGH" at 1.1 - this creates one crum [1.1, 1.9)
    Delete: Remove character at position 1.4 (the 'D')

    Expected (per EWD-022):
    - Two knife cuts at 1.4 and 1.5 split the crum into 3 pieces
    - Left piece: [1.1, 1.4) = "ABC"
    - Middle piece: [1.4, 1.5) = "D" - REMOVED
    - Right piece: [1.5, 1.9) = "EFGH" - but after shift becomes [1.4, 1.8)
    - Net result: 2 crums, Δc = +1
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert a contiguous string - should create one crum
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    vspanset_before = session.retrieve_vspanset(opened)
    specset_before = SpecSet(VSpec(opened, list(vspanset_before.spans)))
    contents_before = session.retrieve_contents(specset_before)

    # Delete single character at position 1.4 (the 'D')
    delete_span = Span(Address(1, 4), Offset(0, 1))
    session.remove(opened, delete_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    # The V-span should now show two pieces (after shift):
    # [1.1, 1.4) and [1.4, 1.8) - with total content "ABCEFGH"

    session.close_document(opened)

    return {
        "name": "type_c_interior_delete",
        "description": "Verify EWD-022 Type C: single-character DELETE in crum interior",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH",
             "comment": "Creates one crum [1.1, 1.9)"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset_before),
             "comment": "Should be single span: 1.1 width 0.8"},
            {"op": "retrieve_contents", "before": contents_before,
             "expected": "ABCDEFGH"},
            {"op": "remove", "span": span_to_dict(delete_span),
             "comment": "DELETE [1.4, 1.5) - the 'D'. Two cuts at 1.4 and 1.5 split into 3 pieces"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset_after),
             "comment": "Expected: Two spans after shift [1.1, 1.4) and [1.4, 1.8). Δc = +1"},
            {"op": "retrieve_contents", "after": contents_after,
             "expected": "ABCEFGH"},
            {"op": "close_document"}
        ]
    }


def scenario_type_c_boundary_left(session):
    """Delete at the LEFT boundary of a crum.

    Setup: Insert "ABCDEFGH" at 1.1
    Delete: Remove character at position 1.1 (the 'A')

    Question: When v is at the start of a crum:
    - Cut at v (1.1) falls on ONMYLEFTBORDER - no split
    - Cut at v+1 (1.2) is THRUME - splits the crum
    - Result: 2 pieces (left piece has width 1, removed; right piece remains)
    - Net: started with 1 crum, removed 1 crum, have 1 crum. Δc = 0

    But EWD-022 says "in the interior of a crum" - does this case differ?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    vspanset_before = session.retrieve_vspanset(opened)
    specset_before = SpecSet(VSpec(opened, list(vspanset_before.spans)))
    contents_before = session.retrieve_contents(specset_before)

    # Delete at LEFT boundary: position 1.1 (the 'A')
    delete_span = Span(Address(1, 1), Offset(0, 1))
    session.remove(opened, delete_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    session.close_document(opened)

    return {
        "name": "type_c_boundary_left",
        "description": "Single-character DELETE at LEFT crum boundary",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset_before)},
            {"op": "retrieve_contents", "before": contents_before},
            {"op": "remove", "span": span_to_dict(delete_span),
             "comment": "DELETE [1.1, 1.2) - at left boundary. Cut at 1.1 = ONMYLEFTBORDER (no split), cut at 1.2 = THRUME (split)"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset_after),
             "comment": "Expected: One span after shift [1.1, 1.8). Δc = 0?"},
            {"op": "retrieve_contents", "after": contents_after,
             "expected": "BCDEFGH"},
            {"op": "close_document"}
        ]
    }


def scenario_type_c_boundary_right(session):
    """Delete at the RIGHT boundary of a crum.

    Setup: Insert "ABCDEFGH" at 1.1 (creates crum [1.1, 1.9))
    Delete: Remove character at position 1.8 (the 'H', last character)

    Question: When v+1 is at the end of a crum:
    - Cut at v (1.8) is THRUME - splits the crum
    - Cut at v+1 (1.9) falls on ONMYRIGHTBORDER - no split
    - Result: 2 pieces (left piece remains; right piece has width 1, removed)
    - Net: started with 1 crum, removed 1 crum, have 1 crum. Δc = 0
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    vspanset_before = session.retrieve_vspanset(opened)
    specset_before = SpecSet(VSpec(opened, list(vspanset_before.spans)))
    contents_before = session.retrieve_contents(specset_before)

    # Delete at RIGHT boundary: position 1.8 (the 'H')
    delete_span = Span(Address(1, 8), Offset(0, 1))
    session.remove(opened, delete_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    session.close_document(opened)

    return {
        "name": "type_c_boundary_right",
        "description": "Single-character DELETE at RIGHT crum boundary",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset_before)},
            {"op": "retrieve_contents", "before": contents_before},
            {"op": "remove", "span": span_to_dict(delete_span),
             "comment": "DELETE [1.8, 1.9) - at right boundary. Cut at 1.8 = THRUME (split), cut at 1.9 = ONMYRIGHTBORDER (no split)"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset_after),
             "comment": "Expected: One span [1.1, 1.8). Δc = 0?"},
            {"op": "retrieve_contents", "after": contents_after,
             "expected": "ABCDEFG"},
            {"op": "close_document"}
        ]
    }


def scenario_type_c_multiple_crums(session):
    """Delete in the interior of a crum when multiple crums exist.

    Setup:
    - Insert "ABC" at 1.1 (crum 1)
    - Insert "DEF" at 1.7 (crum 2, after repositioning cursor)
    - This creates 2 crums with a gap

    Delete: Remove 'B' at position 1.2

    This verifies Type C behavior when there are other crums in the tree.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert first burst
    session.insert(opened, Address(1, 1), ["ABC"])
    vspanset_1 = session.retrieve_vspanset(opened)
    specset_1 = SpecSet(VSpec(opened, list(vspanset_1.spans)))
    contents_1 = session.retrieve_contents(specset_1)

    # Insert second burst at a different position (creates separate crum)
    session.insert(opened, Address(1, 7), ["DEF"])
    vspanset_2 = session.retrieve_vspanset(opened)
    specset_2 = SpecSet(VSpec(opened, list(vspanset_2.spans)))
    contents_2 = session.retrieve_contents(specset_2)

    # Delete 'B' at position 1.2 (interior of first crum)
    delete_span = Span(Address(1, 2), Offset(0, 1))
    session.remove(opened, delete_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    session.close_document(opened)

    return {
        "name": "type_c_multiple_crums",
        "description": "Type C delete when document has multiple crums",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "ABC",
             "comment": "Creates crum 1"},
            {"op": "retrieve_contents", "after_insert_1": contents_1},
            {"op": "insert", "address": "1.7", "text": "DEF",
             "comment": "Creates crum 2 (separate I-address range)"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset_2),
             "comment": "Should show 2 spans with gap"},
            {"op": "retrieve_contents", "before": contents_2},
            {"op": "remove", "span": span_to_dict(delete_span),
             "comment": "DELETE [1.2, 1.3) - 'B' in interior of crum 1. Δc = +1 for crum 1"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset_after),
             "comment": "Expected: 3 spans after split and shift"},
            {"op": "retrieve_contents", "after": contents_after,
             "expected": "ACDEF (with B removed)"},
            {"op": "close_document"}
        ]
    }


def scenario_type_c_sequence(session):
    """Delete multiple single characters sequentially.

    Setup: Insert "ABCDEFGH" at 1.1
    Delete: Remove 'D' (1.4), then 'F' (now at 1.5), then 'B' (1.2)

    This tests whether Type C fragmentation accumulates.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    vspanset_initial = session.retrieve_vspanset(opened)
    specset_initial = SpecSet(VSpec(opened, list(vspanset_initial.spans)))
    contents_initial = session.retrieve_contents(specset_initial)

    # First delete: 'D' at 1.4
    session.remove(opened, Span(Address(1, 4), Offset(0, 1)))
    vspanset_1 = session.retrieve_vspanset(opened)
    specset_1 = SpecSet(VSpec(opened, list(vspanset_1.spans)))
    contents_1 = session.retrieve_contents(specset_1)

    # Second delete: 'F' now at 1.5 (was 1.6 before first delete)
    session.remove(opened, Span(Address(1, 5), Offset(0, 1)))
    vspanset_2 = session.retrieve_vspanset(opened)
    specset_2 = SpecSet(VSpec(opened, list(vspanset_2.spans)))
    contents_2 = session.retrieve_contents(specset_2)

    # Third delete: 'B' at 1.2
    session.remove(opened, Span(Address(1, 2), Offset(0, 1)))
    vspanset_3 = session.retrieve_vspanset(opened)
    specset_3 = SpecSet(VSpec(opened, list(vspanset_3.spans)))
    contents_3 = session.retrieve_contents(specset_3)

    session.close_document(opened)

    return {
        "name": "type_c_sequence",
        "description": "Sequential Type C deletes - observe cumulative fragmentation",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABCDEFGH", "result": contents_initial},
            {"op": "retrieve_vspanset", "initial": vspec_to_dict(vspanset_initial),
             "comment": "1 crum initially"},
            {"op": "remove", "span": "1.4 length 1", "comment": "Delete D. Δc = +1",
             "result": contents_1},
            {"op": "retrieve_vspanset", "after_delete_1": vspec_to_dict(vspanset_1),
             "comment": "Expected: 2 crums"},
            {"op": "remove", "span": "1.5 length 1", "comment": "Delete F (shifted position). Splits right crum, Δc = +1",
             "result": contents_2},
            {"op": "retrieve_vspanset", "after_delete_2": vspec_to_dict(vspanset_2),
             "comment": "Expected: 3 crums"},
            {"op": "remove", "span": "1.2 length 1", "comment": "Delete B. Splits left crum, Δc = +1",
             "result": contents_3},
            {"op": "retrieve_vspanset", "after_delete_3": vspec_to_dict(vspanset_3),
             "comment": "Expected: 4 crums. Total fragmentation from 3 Type C deletes."},
        ]
    }


SCENARIOS = [
    ("type_c_delete", "type_c_interior_delete", scenario_type_c_interior_delete),
    ("type_c_delete", "type_c_boundary_left", scenario_type_c_boundary_left),
    ("type_c_delete", "type_c_boundary_right", scenario_type_c_boundary_right),
    ("type_c_delete", "type_c_multiple_crums", scenario_type_c_multiple_crums),
    ("type_c_delete", "type_c_sequence", scenario_type_c_sequence),
]
