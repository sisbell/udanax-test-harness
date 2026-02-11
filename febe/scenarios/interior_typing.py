"""Test scenarios for interior typing and the ONMYRIGHTBORDER case.

These tests verify the claims in EWD-022 about interior typing:
- After INSERT at position v creates new_crum covering [v, v+1)
- The next INSERT at v+1 should hit ONMYRIGHTBORDER (no split)
- The new content should coalesce with new_crum (isanextensionnd succeeds)
"""

from client import Address, Offset, Span, VSpec, SpecSet, READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
from .common import vspec_to_dict, span_to_dict


def scenario_interior_typing_two_characters(session):
    """Test: Interior typing of two characters at the same advancing cursor position.

    EWD-022 claims:
    1. First INSERT at v=1.5 splits an existing crum, creates new_crum covering [1.5, 1.6)
    2. Second INSERT at v=1.6 (the next position):
       - Knife cut at v=1.6 hits ONMYRIGHTBORDER of new_crum
       - No split occurs (whereoncrum returns ONMYRIGHTBORDER = 1)
       - New content extends new_crum (isanextensionnd succeeds)
       - Result: Δc = 0 (no new crums created)

    We verify this by checking the final structure.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Create initial content "ABCDE"
    session.insert(opened, Address(1, 1), ["ABCDE"])

    # Get the vspanset to confirm initial state
    initial_vspanset = session.retrieve_vspanset(opened)
    initial_contents = session.retrieve_contents(SpecSet(VSpec(opened, list(initial_vspanset.spans))))

    # Insert "X" at position 1.3 (between "B" and "C")
    # This splits the crum "ABCDE" into ["AB", "X", "CDE"]
    session.insert(opened, Address(1, 3), ["X"])

    after_first_insert_vspanset = session.retrieve_vspanset(opened)
    after_first_insert_contents = session.retrieve_contents(SpecSet(VSpec(opened, list(after_first_insert_vspanset.spans))))

    # Insert "Y" at position 1.4 (immediately after "X")
    # According to EWD-022:
    # - The knife cut at 1.4 should be ONMYRIGHTBORDER of the "X" crum
    # - No split should occur
    # - "Y" should coalesce with "X" to form "XY"
    session.insert(opened, Address(1, 4), ["Y"])

    after_second_insert_vspanset = session.retrieve_vspanset(opened)
    after_second_insert_contents = session.retrieve_contents(SpecSet(VSpec(opened, list(after_second_insert_vspanset.spans))))

    session.close_document(opened)

    return {
        "name": "interior_typing_two_characters",
        "description": "Verify ONMYRIGHTBORDER case for interior typing",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABCDE", "at": "1.1"},
            {"op": "initial_state",
             "vspanset": [span_to_dict(s) for s in initial_vspanset.spans],
             "contents": initial_contents},
            {"op": "insert", "text": "X", "at": "1.3", "comment": "First interior insert splits existing crum"},
            {"op": "after_first_insert",
             "vspanset": [span_to_dict(s) for s in after_first_insert_vspanset.spans],
             "contents": after_first_insert_contents,
             "expected_contents": "ABXCDE"},
            {"op": "insert", "text": "Y", "at": "1.4", "comment": "Second insert at advancing cursor (v+1)"},
            {"op": "after_second_insert",
             "vspanset": [span_to_dict(s) for s in after_second_insert_vspanset.spans],
             "contents": after_second_insert_contents,
             "expected_contents": "ABXYCDE",
             "claim": "If ONMYRIGHTBORDER works as claimed, Y should coalesce with X"}
        ]
    }


def scenario_interior_typing_five_characters(session):
    """Test: Interior typing of five characters at advancing cursor position.

    This extends the two-character test to verify continuous typing.
    According to EWD-022, only the first character costs +2 crums (split + new).
    Every subsequent character at the advancing cursor costs +0 (ONMYRIGHTBORDER + coalesce).
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Create initial content "ABCDEFGH"
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    # Insert five characters "12345" starting at position 1.5 (between "D" and "E")
    # According to EWD-022:
    # - First insert "1" at 1.5: costs +2 (split "ABCDEFGH" into "ABCD" + "1" + "EFGH")
    # - Insert "2" at 1.6: costs +0 (ONMYRIGHTBORDER of "1", coalesces to "12")
    # - Insert "3" at 1.7: costs +0 (ONMYRIGHTBORDER of "12", coalesces to "123")
    # - Insert "4" at 1.8: costs +0 (ONMYRIGHTBORDER of "123", coalesces to "1234")
    # - Insert "5" at 1.9: costs +0 (ONMYRIGHTBORDER of "1234", coalesces to "12345")

    results = []
    for i, char in enumerate("12345"):
        position = Address(1, 5 + i)
        session.insert(opened, position, [char])

        vspanset = session.retrieve_vspanset(opened)
        contents = session.retrieve_contents(SpecSet(VSpec(opened, list(vspanset.spans))))

        results.append({
            "char": char,
            "position": str(position),
            "vspanset": [span_to_dict(s) for s in vspanset.spans],
            "contents": contents
        })

    final_contents = results[-1]["contents"]
    session.close_document(opened)

    return {
        "name": "interior_typing_five_characters",
        "description": "Verify continuous interior typing coalesces (Δc = 0 after first char)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABCDEFGH", "at": "1.1"},
            {"op": "interior_typing", "chars": "12345", "starting_at": "1.5", "results": results},
            {"op": "final_state",
             "contents": final_contents,
             "expected_contents": "ABCD12345EFGH",
             "claim": "All five characters should form one contiguous insertion"}
        ]
    }


def scenario_whereoncrum_boundary_classification(session):
    """Test: Verify whereoncrum classification at crum boundaries.

    This test explicitly checks what happens when a knife cut falls exactly
    on the right boundary of a crum (the reach).

    According to retrie.c:343:
    - if address == right: return ONMYRIGHTBORDER (value 1)

    According to insertnd.c:286-287:
    - findsontoinsertundernd looks for a son where:
      whereoncrum(ptr, grasp, &origin, index) >= ONMYLEFTBORDER
      && whereoncrum(ptr, grasp, &spanend, index) <= ONMYRIGHTBORDER

    So ONMYRIGHTBORDER (1) satisfies the condition (<= 1), meaning the knife
    cut is classified as "on my boundary" not "to my right".
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Create a document with three segments to establish boundaries
    session.insert(opened, Address(1, 1), ["AAA"])
    session.insert(opened, Address(1, 4), ["BBB"])
    session.insert(opened, Address(1, 7), ["CCC"])

    initial_vspanset = session.retrieve_vspanset(opened)
    initial_contents = session.retrieve_contents(SpecSet(VSpec(opened, list(initial_vspanset.spans))))

    # Now insert exactly at the boundary positions
    # If "AAA" occupies [1.1, 1.4), then 1.4 is ONMYRIGHTBORDER of "AAA"
    # The insert at 1.4 should NOT split "AAA" (it's at the boundary)
    session.insert(opened, Address(1, 4), ["X"])

    after_boundary_insert = session.retrieve_vspanset(opened)
    contents_after = session.retrieve_contents(SpecSet(VSpec(opened, list(after_boundary_insert.spans))))

    session.close_document(opened)

    return {
        "name": "whereoncrum_boundary_classification",
        "description": "Verify whereoncrum returns ONMYRIGHTBORDER when cut == reach",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "AAA", "at": "1.1"},
            {"op": "insert", "text": "BBB", "at": "1.4"},
            {"op": "insert", "text": "CCC", "at": "1.7"},
            {"op": "initial_state",
             "vspanset": [span_to_dict(s) for s in initial_vspanset.spans],
             "contents": initial_contents,
             "expected": "AAABBBCCC"},
            {"op": "insert", "text": "X", "at": "1.4", "comment": "Insert at boundary (reach of AAA)"},
            {"op": "after_boundary_insert",
             "vspanset": [span_to_dict(s) for s in after_boundary_insert.spans],
             "contents": contents_after,
             "note": "Position 1.4 is ONMYRIGHTBORDER of AAA, should not split it"}
        ]
    }


def scenario_isanextensionnd_checks_left_or_right(session):
    """Test: Does isanextensionnd check the left neighbor or right neighbor?

    EWD-022 line 53 says: "isanextensionnd checks whether the new content extends
    new_crum: V-contiguity (reach_V = v+1 = origin of new), I-contiguity (...),
    homedoc match."

    This implies it checks if the NEW insertion extends an EXISTING crum by comparing
    the existing crum's REACH with the new insertion's ORIGIN.

    In insertcbcnd (insertnd.c:234-267), the loop iterates through all sons and
    calls isanextensionnd on each. The function checks if new content at 'origin'
    extends the crum at 'ptr' by checking if ptr's reach == origin.

    So isanextensionnd checks if the NEW content is contiguous with the END (reach)
    of an EXISTING crum. This is "extending to the right" from the existing crum's
    perspective.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Scenario: Create gaps and see which gaps get filled by extension

    # Insert "AAA" at 1.1 (covers [1.1, 1.4))
    session.insert(opened, Address(1, 1), ["AAA"])
    state1 = session.retrieve_vspanset(opened)

    # Insert "CCC" at 1.7 (covers [1.7, 1.10))
    # This creates a gap [1.4, 1.7)
    session.insert(opened, Address(1, 7), ["CCC"])
    state2 = session.retrieve_vspanset(opened)

    # Insert "BBB" at 1.4 (covers [1.4, 1.7))
    # This should fill the gap
    # Question: Does it extend "AAA" (checking AAA's right neighbor)?
    # Or does it extend "CCC" (checking CCC's left neighbor)?
    # According to insertnd.c:242, isanextensionnd checks if new origin == existing reach
    # "AAA" has reach 1.4, new origin is 1.4, so it extends "AAA" to the right
    session.insert(opened, Address(1, 4), ["BBB"])
    state3 = session.retrieve_vspanset(opened)
    contents = session.retrieve_contents(SpecSet(VSpec(opened, list(state3.spans))))

    session.close_document(opened)

    return {
        "name": "isanextensionnd_checks_left_or_right",
        "description": "Verify isanextensionnd extends existing crum to the right (checks reach)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "AAA", "at": "1.1", "vspanset": [span_to_dict(s) for s in state1.spans]},
            {"op": "insert", "text": "CCC", "at": "1.7", "vspanset": [span_to_dict(s) for s in state2.spans], "comment": "Creates gap [1.4, 1.7)"},
            {"op": "insert", "text": "BBB", "at": "1.4",
             "vspanset": [span_to_dict(s) for s in state3.spans],
             "contents": contents,
             "expected": "AAABBBCCC",
             "claim": "BBB at 1.4 should extend AAA (reach of AAA = 1.4 = origin of BBB)"}
        ]
    }


SCENARIOS = [
    ("internal", "interior_typing_two_characters", scenario_interior_typing_two_characters),
    ("internal", "interior_typing_five_characters", scenario_interior_typing_five_characters),
    ("internal", "whereoncrum_boundary_classification", scenario_whereoncrum_boundary_classification),
    ("internal", "isanextensionnd_checks_left_or_right", scenario_isanextensionnd_checks_left_or_right),
]
