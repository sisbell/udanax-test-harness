"""Test what happens to link V-positions when text before them is deleted.

This scenario tests whether DELETE causes V-position shifts and whether
position digits can go negative or below 1.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_delete_text_before_link(session):
    """Test whether deleting text causes link V-positions to shift.

    Setup:
    - Create document with text at 1.1-1.15 (15 bytes)
    - Create link at some V-position in 2.x subspace
    - Delete all text (DELETE at 1.1, width=0.15)

    Question: What happens to the link's V-position?
    - Does it shift left by 0.15?
    - Can the position digit go below 1?
    - Does tumblersub handle negative results?
    """
    # Create document
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert text at 1.1-1.15 (15 bytes: "123456789012345")
    session.insert(opened, Address(1, 1), ["123456789012345"])

    # Create a self-link at the beginning of the text
    source_span = Span(Address(1, 1), Offset(0, 5))  # "12345"
    target_span = Span(Address(1, 10), Offset(0, 5))  # "01234"
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Get vspanset before deletion - should show link at some 2.x position
    vspan_before = session.retrieve_vspanset(opened)

    # Follow link to see the exact endset addresses before deletion
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # Delete all text: start at 1.1, delete 15 bytes (width 0.15)
    try:
        session.delete(opened, Address(1, 1), Offset(0, 15))
        delete_succeeded = True
        delete_error = None
    except Exception as e:
        delete_succeeded = False
        delete_error = str(e)

    # Get vspanset after deletion
    vspan_after = session.retrieve_vspanset(opened)

    # Try to follow the link again to see if endsets changed
    try:
        endsets_after = session.follow_link(link_id, LINK_SOURCE)
        follow_succeeded = True
        follow_error = None
    except Exception as e:
        endsets_after = None
        follow_succeeded = False
        follow_error = str(e)

    # Try to find the link from source position (which no longer has text)
    try:
        links_found = session.find_links(source_specs)
        find_succeeded = True
        find_error = None
    except Exception as e:
        links_found = []
        find_succeeded = False
        find_error = str(e)

    session.close_document(opened)

    return {
        "name": "delete_text_before_link",
        "description": "Test whether DELETE causes link V-positions to shift left",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "123456789012345", "note": "15 bytes at 1.1-1.15"},
            {"op": "create_link",
             "home_doc": str(opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id),
             "note": "Link from 1.1-1.5 to 1.10-1.14"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan_before), "note": "Before deletion: text at 1.x, link at 2.x"},
            {"op": "follow_link", "link": str(link_id), "end": "source", "result": specset_to_list(endsets_before), "note": "Link endsets before deletion"},
            {"op": "delete",
             "doc": str(opened),
             "start": "1.1",
             "width": "0.15",
             "succeeded": delete_succeeded,
             "error": delete_error,
             "note": "Delete all 15 bytes of text"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan_after), "note": "After deletion: does link position shift?"},
            {"op": "follow_link",
             "link": str(link_id),
             "end": "source",
             "result": specset_to_list(endsets_after) if follow_succeeded else None,
             "succeeded": follow_succeeded,
             "error": follow_error,
             "note": "Can we still follow the link? Do endsets change?"},
            {"op": "find_links",
             "specs": specset_to_list(source_specs),
             "result": [str(lid) for lid in links_found],
             "succeeded": find_succeeded,
             "error": find_error,
             "note": "Can we find link from original source span (now deleted)?"}
        ]
    }


def scenario_delete_partial_text_before_link(session):
    """Test partial deletion to observe incremental V-position shifting.

    Setup:
    - Text at 1.1-1.20
    - Link from 1.5-1.10 to 1.15-1.20
    - Delete first 3 bytes (1.1-1.3)

    Expected: Link V-positions should shift left by 0.3
    Critical question: What if we delete enough to make position < 1?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert 20 bytes
    session.insert(opened, Address(1, 1), ["12345678901234567890"])

    # Link from middle to end
    source_span = Span(Address(1, 5), Offset(0, 5))
    target_span = Span(Address(1, 15), Offset(0, 5))
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    vspan_before = session.retrieve_vspanset(opened)
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # Delete first 3 bytes
    session.delete(opened, Address(1, 1), Offset(0, 3))

    vspan_after_small = session.retrieve_vspanset(opened)
    endsets_after_small = session.follow_link(link_id, LINK_SOURCE)

    # Delete another 10 bytes (total 13 deleted, link source was at 1.5)
    # This should shift link source from 1.5 to below 1.1
    session.delete(opened, Address(1, 1), Offset(0, 10))

    vspan_after_large = session.retrieve_vspanset(opened)
    endsets_after_large = session.follow_link(link_id, LINK_SOURCE)

    session.close_document(opened)

    return {
        "name": "delete_partial_text_before_link",
        "description": "Test incremental V-position shifting and behavior when shift would go below 1.1",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "12345678901234567890", "note": "20 bytes"},
            {"op": "create_link",
             "home_doc": str(opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id),
             "note": "Link from 1.5-1.9 to 1.15-1.19"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan_before), "note": "Initial state"},
            {"op": "follow_link", "link": str(link_id), "end": "source", "result": specset_to_list(endsets_before), "note": "Initial endsets"},
            {"op": "delete", "doc": str(opened), "start": "1.1", "width": "0.3", "note": "Delete 3 bytes, link should shift from 1.5 to 1.2"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan_after_small), "note": "After small deletion"},
            {"op": "follow_link", "link": str(link_id), "end": "source", "result": specset_to_list(endsets_after_small), "note": "Endsets after small deletion"},
            {"op": "delete", "doc": str(opened), "start": "1.1", "width": "0.10", "note": "Delete 10 more bytes (13 total), link source would shift below 1.1"},
            {"op": "retrieve_vspanset", "doc": str(opened), "result": vspec_to_dict(vspan_after_large), "note": "After large deletion - what happens to link V-positions?"},
            {"op": "follow_link", "link": str(link_id), "end": "source", "result": specset_to_list(endsets_after_large), "note": "Final endsets - can position digit go below 1?"}
        ]
    }


SCENARIOS = [
    ("links", "delete_text_before_link", scenario_delete_text_before_link),
    ("links", "delete_partial_text_before_link", scenario_delete_partial_text_before_link),
]
