"""Test scenarios to reveal subspace shift isolation."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict


def scenario_insert_text_check_link_positions(session):
    """
    Test whether inserting text in subspace 1.x shifts link positions in subspace 2.x.

    Expected behavior based on EWD-035 (CD0):
    - Subspaces are independent
    - INSERT at 1.3 should only shift content within subspace 1.x
    - Link positions in 2.x should remain unchanged
    """
    # Create two documents: one for content, one for linking
    doc1 = session.create_document()
    doc2 = session.create_document()

    # Open doc1 for modification
    opened_doc1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_doc1, Address(1, 1), ["ABCDE"])

    # Open doc2 for modification
    opened_doc2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_doc2, Address(1, 1), ["12345"])

    # Create a link in doc1 from text to doc2 text
    # This should place the link at position 2.1 (first position in link subspace)
    from_spec = SpecSet(VSpec(opened_doc1, [Span(Address(1, 2), Offset(0, 2))]))  # "BC"
    to_spec = SpecSet(VSpec(opened_doc2, [Span(Address(1, 2), Offset(0, 2))]))    # "23"
    session.create_link(opened_doc1, from_spec, to_spec, SpecSet([JUMP_TYPE]))

    # Get vspanset to see both text (1.x) and link (2.x) positions
    vspanset_before = session.retrieve_vspanset(opened_doc1)

    # Record content at specific positions before insert
    text_at_1_3_before = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(1, 3), Offset(0, 1))]))
    )

    # Try to retrieve link at 2.1 (this might not work directly, but we try)
    link_vspec_before = SpecSet(VSpec(opened_doc1, [Span(Address(2, 1), Offset(0, 1))]))

    # Now INSERT text at position 1.3 (in the middle of "ABCDE")
    session.insert(opened_doc1, Address(1, 3), ["XY"])

    # Get vspanset after insert
    vspanset_after = session.retrieve_vspanset(opened_doc1)

    # Check text positions - content should have shifted
    text_at_1_3_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(1, 3), Offset(0, 1))]))
    )
    text_at_1_5_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(1, 5), Offset(0, 1))]))
    )

    # Check link position - should this have shifted?
    # If subspaces are independent, link should still be at 2.1
    # If they're not, link might be at 2.3 now (shifted by 2 positions)
    link_at_2_1_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(2, 1), Offset(0, 1))]))
    )

    # Get full content to see everything
    full_content_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, list(vspanset_after.spans)))
    )

    # Follow the link to verify it's still intact
    full_search = SpecSet(VSpec(opened_doc1, list(vspanset_after.spans)))
    links_from_doc1 = session.find_links(full_search)

    session.close_document(opened_doc1)
    session.close_document(opened_doc2)

    return {
        "name": "insert_text_check_link_positions",
        "description": "Test whether INSERT in subspace 1.x shifts positions in subspace 2.x",
        "operations": [
            {"op": "create_documents", "doc1": str(doc1), "doc2": str(doc2)},
            {"op": "insert_text_doc1", "text": "ABCDE", "at": "1.1"},
            {"op": "insert_text_doc2", "text": "12345", "at": "1.1"},
            {"op": "create_link", "from": "doc1[1.2-1.4]", "to": "doc2[1.2-1.4]",
             "comment": "Link should be at position 2.1 in doc1"},
            {"op": "vspanset_before_insert", "result": vspec_to_dict(vspanset_before),
             "comment": "Should show both 1.x (text) and 2.x (link) ranges"},
            {"op": "text_at_1_3_before", "result": text_at_1_3_before,
             "interpretation": "Should be 'C' (third character)"},

            {"op": "INSERT", "at": "1.3", "text": "XY",
             "comment": "Insert in middle of text subspace"},

            {"op": "vspanset_after_insert", "result": vspec_to_dict(vspanset_after),
             "comment": "Key question: Did the 2.x range shift?"},
            {"op": "text_at_1_3_after", "result": text_at_1_3_after,
             "interpretation": "Should be 'X' (first inserted character)"},
            {"op": "text_at_1_5_after", "result": text_at_1_5_after,
             "interpretation": "Should be 'C' (shifted from 1.3 to 1.5)"},
            {"op": "link_at_2_1_after",
             "result": [str(x) for x in link_at_2_1_after] if isinstance(link_at_2_1_after, list) else str(link_at_2_1_after),
             "interpretation": "Critical test: Is link still at 2.1 or did it shift?"},
            {"op": "full_content_after",
             "result": [str(x) for x in full_content_after] if isinstance(full_content_after, list) else str(full_content_after)},
            {"op": "links_after_insert", "result": [str(link) for link in links_from_doc1],
             "comment": "Verify link still exists and is discoverable"}
        ],
        "analysis": {
            "question": "Are subspaces independent for shift operations?",
            "hypothesis_independent": "If independent, link remains at 2.1 after INSERT at 1.3",
            "hypothesis_shared": "If shared, link shifts to 2.3 (same displacement as text)",
            "displacement_value": "What tumbler value is passed to tumbleradd for shifts?"
        }
    }


def scenario_createlink_check_text_positions(session):
    """
    Test whether CREATELINK in subspace 2.x shifts text positions in subspace 1.x.

    This is the reverse test: does creating a link shift text?
    """
    # Create documents
    doc1 = session.create_document()
    doc2 = session.create_document()

    opened_doc1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    opened_doc2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)

    # Insert text in both documents
    session.insert(opened_doc1, Address(1, 1), ["ABCDE"])
    session.insert(opened_doc2, Address(1, 1), ["12345"])

    # Record text positions before link creation
    text_at_1_3_before = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(1, 3), Offset(0, 1))]))
    )
    vspanset_before = session.retrieve_vspanset(opened_doc1)

    # Create first link
    from_spec1 = SpecSet(VSpec(opened_doc1, [Span(Address(1, 2), Offset(0, 1))]))
    to_spec1 = SpecSet(VSpec(opened_doc2, [Span(Address(1, 2), Offset(0, 1))]))
    session.create_link(opened_doc1, from_spec1, to_spec1, SpecSet([JUMP_TYPE]))

    vspanset_after_first_link = session.retrieve_vspanset(opened_doc1)

    # Create second link
    from_spec2 = SpecSet(VSpec(opened_doc1, [Span(Address(1, 4), Offset(0, 1))]))
    to_spec2 = SpecSet(VSpec(opened_doc2, [Span(Address(1, 4), Offset(0, 1))]))
    session.create_link(opened_doc1, from_spec2, to_spec2, SpecSet([JUMP_TYPE]))

    vspanset_after_second_link = session.retrieve_vspanset(opened_doc1)

    # Check if text position 1.3 still contains 'C'
    text_at_1_3_after = session.retrieve_contents(
        SpecSet(VSpec(opened_doc1, [Span(Address(1, 3), Offset(0, 1))]))
    )

    session.close_document(opened_doc1)
    session.close_document(opened_doc2)

    return {
        "name": "createlink_check_text_positions",
        "description": "Test whether CREATELINK in subspace 2.x shifts positions in subspace 1.x",
        "operations": [
            {"op": "setup", "text_doc1": "ABCDE", "text_doc2": "12345"},
            {"op": "vspanset_before_links", "result": vspec_to_dict(vspanset_before),
             "comment": "Should show only 1.x range (text only)"},
            {"op": "text_at_1_3_before", "result": text_at_1_3_before,
             "interpretation": "Should be 'C'"},

            {"op": "create_link_1", "from": "doc1[1.2]", "to": "doc2[1.2]",
             "comment": "First link should go to 2.1"},
            {"op": "vspanset_after_first_link",
             "result": vspec_to_dict(vspanset_after_first_link),
             "comment": "Should now show both 1.x and 2.x"},

            {"op": "create_link_2", "from": "doc1[1.4]", "to": "doc2[1.4]",
             "comment": "Second link should go to 2.2"},
            {"op": "vspanset_after_second_link",
             "result": vspec_to_dict(vspanset_after_second_link),
             "comment": "2.x range should expand"},

            {"op": "text_at_1_3_after", "result": text_at_1_3_after,
             "interpretation": "Should still be 'C' if subspaces independent"}
        ],
        "analysis": {
            "question": "Does CREATELINK shift text positions?",
            "expected": "Text positions unchanged; links accumulate in 2.x subspace"
        }
    }


def scenario_displacement_tumbler_value(session):
    """
    Examine what displacement tumbler value is actually used in shifts.

    When inserting 5 bytes at position 1.3, what is the displacement value?
    - Option A: (0, 5) - subspace digit 0, position 5
    - Option B: (1, 5) - subspace digit 1, position 5
    - Option C: Something else
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert initial content
    session.insert(opened, Address(1, 1), ["ABCDE"])

    # Get positions before
    pos_1_4_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 4), Offset(0, 1))]))
    )

    # Insert 3 bytes at 1.3
    session.insert(opened, Address(1, 3), ["XYZ"])

    # Get positions after
    pos_1_4_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 4), Offset(0, 1))]))
    )
    pos_1_6_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 6), Offset(0, 1))]))
    )
    pos_1_7_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 7), Offset(0, 1))]))
    )

    session.close_document(opened)

    return {
        "name": "displacement_tumbler_value",
        "description": "Determine concrete displacement tumbler for shifts",
        "operations": [
            {"op": "insert", "at": "1.1", "text": "ABCDE"},
            {"op": "pos_1_4_before", "result": pos_1_4_before,
             "interpretation": "Should be 'D'"},

            {"op": "insert", "at": "1.3", "text": "XYZ"},

            {"op": "pos_1_4_after", "result": pos_1_4_after,
             "interpretation": "If shift by (0,3): still 'D'. If shift by (1,3): would be 'X'"},
            {"op": "pos_1_6_after", "result": pos_1_6_after,
             "interpretation": "Should be 'C' if content shifted by exactly 3 positions"},
            {"op": "pos_1_7_after", "result": pos_1_7_after,
             "interpretation": "Should be 'D'"}
        ],
        "analysis": {
            "question": "What displacement value is passed to tumbleradd?",
            "code_reference": "insertnd.c:162 - tumbleradd(&ptr->cdsp.dsas[V], &width->dsas[V], ...)",
            "width_dsas_V": "width->dsas[V] is the V-dimension component of the width tumbler"
        }
    }


SCENARIOS = [
    ("subspace", "insert_text_check_link_positions", scenario_insert_text_check_link_positions),
    ("subspace", "createlink_check_text_positions", scenario_createlink_check_text_positions),
    ("subspace", "displacement_tumbler_value", scenario_displacement_tumbler_value),
]
