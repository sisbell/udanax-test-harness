"""Test scenario to determine whether DELETE on link subspace closes gaps.

This test directly addresses EWD-007 Open Question 5: If a document has links
at V-addresses 2.1, 2.2, 2.3, and we delete the link at 2.2 (DELETEVSPAN at
2.2 with width 0.1), does the link at 2.3 shift down to 2.2?

The question hinges on whether strongsub's exponent guard [tumble.c:544-546]
fires when subtracting a link width (0.1) from a link V-address (2.3).
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    JUMP_TYPE, NOSPECS,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE
)
from .common import vspec_to_dict, span_to_dict


def scenario_delete_middle_link_check_gap_closure(session):
    """
    Test whether DELETE of a link in the middle of link subspace shifts
    subsequent links down (closing the gap) or leaves them at their original
    V-addresses (leaving a gap).

    Setup:
    - Create doc with text "ABCDEFGHIJ" at 1.1-1.10
    - Create three links at V-positions 2.1, 2.2, 2.3

    Action:
    - DELETE link at 2.2 (width 0.1)

    Key questions:
    1. Does link originally at 2.3 shift down to 2.2?
    2. Or does it stay at 2.3, leaving a gap at 2.2?

    The answer depends on:
    - Link V-address 2.3 has exponent = ?
    - Link width 0.1 has exponent = ?
    - Does strongsub(2.3, 0.1) proceed with subtraction (same exponents)
      or return 2.3 unchanged (different exponents)?
    """
    # Create two documents
    doc1 = session.create_document()
    doc2 = session.create_document()

    opened_doc1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    opened_doc2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)

    # Insert text
    session.insert(opened_doc1, Address(1, 1), ["ABCDEFGHIJ"])
    session.insert(opened_doc2, Address(1, 1), ["1234567890"])

    # Create three links
    # Link 1: from doc1[1.1-1.2] to doc2[1.1-1.2]
    from_spec1 = SpecSet(VSpec(opened_doc1, [Span(Address(1, 1), Offset(0, 2))]))
    to_spec1 = SpecSet(VSpec(opened_doc2, [Span(Address(1, 1), Offset(0, 2))]))
    link_id_1 = session.create_link(opened_doc1, from_spec1, to_spec1, SpecSet([JUMP_TYPE]))

    # Link 2: from doc1[1.3-1.4] to doc2[1.3-1.4]
    from_spec2 = SpecSet(VSpec(opened_doc1, [Span(Address(1, 3), Offset(0, 2))]))
    to_spec2 = SpecSet(VSpec(opened_doc2, [Span(Address(1, 3), Offset(0, 2))]))
    link_id_2 = session.create_link(opened_doc1, from_spec2, to_spec2, SpecSet([JUMP_TYPE]))

    # Link 3: from doc1[1.5-1.6] to doc2[1.5-1.6]
    from_spec3 = SpecSet(VSpec(opened_doc1, [Span(Address(1, 5), Offset(0, 2))]))
    to_spec3 = SpecSet(VSpec(opened_doc2, [Span(Address(1, 5), Offset(0, 2))]))
    link_id_3 = session.create_link(opened_doc1, from_spec3, to_spec3, SpecSet([JUMP_TYPE]))

    # Verify vspanset shows all three links
    vspanset_before_delete = session.retrieve_vspanset(opened_doc1)

    # Verify we can retrieve content at each link position
    link_at_2_1_before = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 1), Offset(0, 1))]))
    )
    link_at_2_2_before = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 2), Offset(0, 1))]))
    )
    link_at_2_3_before = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 3), Offset(0, 1))]))
    )

    # DELETE the middle link at V-position 2.2 with width 0.1
    try:
        session.delete(opened_doc1, Address(2, 2), Offset(0, 1))
        delete_success = True
    except Exception as e:
        delete_success = False
        delete_error = str(e)

    # Check vspanset after deletion
    vspanset_after_delete = session.retrieve_vspanset(opened_doc1)

    # CRITICAL CHECKS:
    # Check V-position 2.1 - should still have link_id_1
    link_at_2_1_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 1), Offset(0, 1))]))
    )

    # Check V-position 2.2 - the key question:
    # - If gap closed: should have link_id_3 (shifted down from 2.3)
    # - If gap remains: should be empty
    link_at_2_2_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 2), Offset(0, 1))]))
    )

    # Check V-position 2.3:
    # - If gap closed: should be empty (link_id_3 moved to 2.2)
    # - If gap remains: should still have link_id_3
    link_at_2_3_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 3), Offset(0, 1))]))
    )

    # Verify links are still followable
    follow_link_1 = None
    follow_link_3 = None
    try:
        follow_link_1 = session.follow_link(link_id_1, LINK_TARGET)
    except Exception as e:
        follow_link_1 = {"error": str(e)}

    try:
        follow_link_3 = session.follow_link(link_id_3, LINK_TARGET)
    except Exception as e:
        follow_link_3 = {"error": str(e)}

    session.close_document(opened_doc1)
    session.close_document(opened_doc2)

    if not delete_success:
        return {
            "name": "delete_middle_link_check_gap_closure",
            "description": "DELETE could not be performed on link subspace",
            "operations": [
                {"op": "delete_failed", "error": delete_error}
            ]
        }

    return {
        "name": "delete_middle_link_check_gap_closure",
        "description": "Test whether DELETE at 2.2 shifts link at 2.3 down to 2.2 (gap closure)",
        "operations": [
            {"op": "setup",
             "doc1_text": "ABCDEFGHIJ",
             "doc2_text": "1234567890",
             "links_created": [str(link_id_1), str(link_id_2), str(link_id_3)]},

            {"op": "vspanset_before_delete",
             "result": vspec_to_dict(vspanset_before_delete),
             "interpretation": "Should show text subspace 1.x and link subspace 2.x with width 0.3"},

            {"op": "links_before_delete",
             "link_at_2_1": [str(x) for x in link_at_2_1_before] if isinstance(link_at_2_1_before, list) else str(link_at_2_1_before),
             "link_at_2_2": [str(x) for x in link_at_2_2_before] if isinstance(link_at_2_2_before, list) else str(link_at_2_2_before),
             "link_at_2_3": [str(x) for x in link_at_2_3_before] if isinstance(link_at_2_3_before, list) else str(link_at_2_3_before)},

            {"op": "DELETE", "at": "2.2", "width": "0.1",
             "comment": "Delete middle link"},

            {"op": "vspanset_after_delete",
             "result": vspec_to_dict(vspanset_after_delete),
             "interpretation": "If gap closed: link subspace width = 0.2. If gap remains: may still be 0.3?"},

            {"op": "links_after_delete",
             "link_at_2_1": [str(x) for x in link_at_2_1_after] if isinstance(link_at_2_1_after, list) else str(link_at_2_1_after),
             "link_at_2_2": [str(x) for x in link_at_2_2_after] if isinstance(link_at_2_2_after, list) else str(link_at_2_2_after),
             "link_at_2_3": [str(x) for x in link_at_2_3_after] if isinstance(link_at_2_3_after, list) else str(link_at_2_3_after),
             "interpretation": "KEY: Is link_id_3 at position 2.2 (closed) or 2.3 (gap)?"},

            {"op": "follow_links_after_delete",
             "link_1": str(follow_link_1) if not isinstance(follow_link_1, dict) else follow_link_1,
             "link_3": str(follow_link_3) if not isinstance(follow_link_3, dict) else follow_link_3,
             "interpretation": "Links should still be followable regardless of V-position"}
        ],
        "analysis": {
            "question": "Does DELETE on link subspace close gaps via strongsub?",
            "hypothesis_gap_closed": "Link at 2.3 shifts to 2.2; strongsub(2.3, 0.1) = 2.2",
            "hypothesis_gap_remains": "Link at 2.3 stays at 2.3; strongsub(2.3, 0.1) = 2.3 (exponent guard fires)",
            "code_trace": "deletend calls tumblersub(ptr->cdsp.dsas[V], width) [edit.c:63]",
            "critical_check": "tumblersub(2.3, 0.1) -> tumbleradd(2.3, -0.1) -> strongsub(2.3, 0.1)",
            "exponent_question": "What is exp(2.3) vs exp(0.1) in tumbler representation?",
            "finding_reference": "Finding 055 shows DELETE of TEXT does not shift LINKS (exp mismatch). Does DELETE of LINKS shift LINKS?"
        }
    }


SCENARIOS = [
    ("links", "delete_middle_link_check_gap_closure", scenario_delete_middle_link_check_gap_closure),
]
