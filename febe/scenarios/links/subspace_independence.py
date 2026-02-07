"""Test scenarios for verifying V-position subspace independence."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_text_insert_preserves_link_vpositions(session):
    """Test whether inserting text in 1.x subspace affects link positions in 2.x subspace.

    This scenario:
    1. Creates a document with text at V-positions 1.1-1.10 (10 characters)
    2. Creates a link, which should be at V-position 2.1
    3. Inserts 5 more characters at position 1.5 (middle of text)
    4. Retrieves vspanset to check if link is still at 2.1 or shifted

    Expected behavior (if subspaces are independent):
    - Text should now span 1.1-1.15
    - Link should remain at 2.1 (unchanged)

    Alternative behavior (if subspaces are unified):
    - Link position might shift to account for inserted text
    """
    # Create source document with initial text
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["HelloWorld"])  # 10 chars

    # Check initial vspanset (should show text at 1.x only)
    vspanset_before_link = session.retrieve_vspanset(source_opened)

    # Create target document
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create a link from positions 1.1-1.5 to target
    source_span = Span(Address(1, 1), Offset(0, 5))  # "Hello"
    source_specs = SpecSet(VSpec(source_opened, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 6))
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    link_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Check vspanset after link creation (should show both 1.x text and 2.x link)
    vspanset_after_link = session.retrieve_vspanset(source_opened)

    # Insert 5 characters in the MIDDLE of the text (at position 1.5)
    session.insert(source_opened, Address(1, 5), ["XXXXX"])

    # Check final vspanset
    vspanset_after_insert = session.retrieve_vspanset(source_opened)

    # Get final contents of text subspace (1.x)
    text_span = Span(Address(1, 1), Offset(0, 20))  # Enough to cover all text
    text_specs = SpecSet(VSpec(source_opened, [text_span]))
    final_text = session.retrieve_contents(text_specs)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "text_insert_preserves_link_vpositions",
        "description": "Test whether text insertion in 1.x affects link positions in 2.x",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "open_document", "doc": str(source_docid), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "HelloWorld", "note": "Initial 10 chars"},
            {"op": "retrieve_vspanset", "doc": str(source_opened), "result": vspec_to_dict(vspanset_before_link), "note": "Before link: should show 1.x only"},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "open_document", "doc": str(target_docid), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id),
             "note": "Link should be at 2.1"},
            {"op": "retrieve_vspanset", "doc": str(source_opened), "result": vspec_to_dict(vspanset_after_link), "note": "After link: should show 1.x and 2.x"},
            {"op": "insert", "doc": str(source_opened), "address": "1.5", "text": "XXXXX", "note": "Insert 5 chars at middle of text"},
            {"op": "retrieve_vspanset", "doc": str(source_opened), "result": vspec_to_dict(vspanset_after_insert), "note": "After insert: text should be 1.15, link position?"},
            {"op": "retrieve_contents", "doc": str(source_opened), "result": final_text, "note": "Final text should be 'HelloXXXXXWorld'"}
        ]
    }


def scenario_multiple_text_insertions_with_links(session):
    """Test multiple insertions at different positions with links present.

    This scenario creates a more complex pattern:
    1. Insert text "ABC" at 1.1 (text now 1.1-1.3)
    2. Create link (should be at 2.1)
    3. Insert "XX" at 1.2 (text becomes 1.1-1.5, "AXXBC")
    4. Create second link (should be at 2.2)
    5. Insert "YY" at 1.1 (text becomes 1.1-1.7, "YYAXXBC")
    6. Check all V-positions
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Step 1: Initial text
    session.insert(opened, Address(1, 1), ["ABC"])
    vspan1 = session.retrieve_vspanset(opened)

    # Step 2: First link
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["T1"])

    source_span1 = Span(Address(1, 1), Offset(0, 1))  # "A"
    source_specs1 = SpecSet(VSpec(opened, [source_span1]))
    target_span1 = Span(Address(1, 1), Offset(0, 2))
    target_specs1 = SpecSet(VSpec(target_opened, [target_span1]))
    link1 = session.create_link(opened, source_specs1, target_specs1, SpecSet([JUMP_TYPE]))

    vspan2 = session.retrieve_vspanset(opened)

    # Step 3: Insert in middle
    session.insert(opened, Address(1, 2), ["XX"])
    vspan3 = session.retrieve_vspanset(opened)

    # Step 4: Second link
    session.insert(target_opened, Address(1, 3), ["T2"])
    source_span2 = Span(Address(1, 3), Offset(0, 1))  # "X" (first X)
    source_specs2 = SpecSet(VSpec(opened, [source_span2]))
    target_span2 = Span(Address(1, 3), Offset(0, 2))
    target_specs2 = SpecSet(VSpec(target_opened, [target_span2]))
    link2 = session.create_link(opened, source_specs2, target_specs2, SpecSet([JUMP_TYPE]))

    vspan4 = session.retrieve_vspanset(opened)

    # Step 5: Insert at beginning
    session.insert(opened, Address(1, 1), ["YY"])
    vspan5 = session.retrieve_vspanset(opened)

    # Get final text
    text_span = Span(Address(1, 1), Offset(0, 10))
    text_specs = SpecSet(VSpec(opened, [text_span]))
    final_text = session.retrieve_contents(text_specs)

    session.close_document(opened)
    session.close_document(target_opened)

    return {
        "name": "multiple_text_insertions_with_links",
        "description": "Multiple insertions at different positions with links to verify subspace independence",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "ABC"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan1), "note": "Step 1: text 1.1-1.3"},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "open_document", "doc": str(target_docid), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "T1"},
            {"op": "create_link", "home_doc": str(opened), "source": specset_to_list(source_specs1), "target": specset_to_list(target_specs1), "type": "jump", "result": str(link1), "note": "Link1 at 2.1"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan2), "note": "Step 2: text 1.x + link 2.1"},
            {"op": "insert", "doc": str(opened), "address": "1.2", "text": "XX"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan3), "note": "Step 3: text 1.1-1.5, link?"},
            {"op": "insert", "doc": str(target_opened), "address": "1.3", "text": "T2"},
            {"op": "create_link", "home_doc": str(opened), "source": specset_to_list(source_specs2), "target": specset_to_list(target_specs2), "type": "jump", "result": str(link2), "note": "Link2 at 2.2"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan4), "note": "Step 4: links at 2.1 and 2.2"},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "YY"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan5), "note": "Step 5: final state"},
            {"op": "retrieve_contents", "doc": str(opened), "result": final_text, "note": "Should be 'YYAXXBC'"}
        ]
    }


SCENARIOS = [
    ("links", "text_insert_preserves_link_vpositions", scenario_text_insert_preserves_link_vpositions),
    ("links", "multiple_text_insertions_with_links", scenario_multiple_text_insertions_with_links),
]
