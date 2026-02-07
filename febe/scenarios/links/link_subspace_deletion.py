"""Test DELETEVSPAN on link subspace (2.x) to understand link management."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_delete_link_subspace(session):
    """Test whether DELETEVSPAN on link subspace (2.x) removes links.

    This tests what happens when you delete the V-range where link
    references are stored. Does it:
    a) Remove the link from the document's POOM?
    b) Orphan the link orgl but leave it in spanf?
    c) Fail with an error?
    """
    # Create documents
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["Source text"])

    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["Target text"])

    # Create a link
    source_span = Span(Address(1, 1), Offset(0, 6))  # "Source"
    source_specs = SpecSet(VSpec(a_opened, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 6))
    target_specs = SpecSet(VSpec(b_opened, [target_span]))
    link_id = session.create_link(a_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Check vspanset - should show 0.x/2.x (link) and 1.x (text)
    vspan_before = session.retrieve_vspanset(a_opened)

    # Find the link to confirm it exists
    find_specs = SpecSet(VSpec(a_opened, [source_span]))
    links_before = session.find_links(find_specs)

    # Delete the link subspace (2.x range based on Finding 038)
    try:
        session.delete(a_opened, Address(2, 1), Offset(0, 1))
        delete_succeeded = True
        delete_error = None
    except Exception as e:
        delete_succeeded = False
        delete_error = str(e)

    # Check vspanset after deletion
    vspan_after = session.retrieve_vspanset(a_opened)

    # Try to find the link again
    links_after = session.find_links(find_specs)

    # Try to follow the link (should work if link orgl persists in I-space)
    try:
        followed = session.follow_link(link_id, LINK_SOURCE)
        follow_succeeded = True
        follow_error = None
    except Exception as e:
        followed = None
        follow_succeeded = False
        follow_error = str(e)

    session.close_document(a_opened)
    session.close_document(b_opened)

    return {
        "name": "delete_link_subspace",
        "description": "Test DELETEVSPAN on link subspace (2.x) to see if it removes link references",
        "operations": [
            {"op": "create_document", "result": str(doc_a)},
            {"op": "open_document", "doc": str(doc_a), "mode": "read_write", "result": str(a_opened)},
            {"op": "insert", "doc": str(a_opened), "address": "1.1", "text": "Source text"},
            {"op": "create_document", "result": str(doc_b)},
            {"op": "open_document", "doc": str(doc_b), "mode": "read_write", "result": str(b_opened)},
            {"op": "insert", "doc": str(b_opened), "address": "1.1", "text": "Target text"},
            {"op": "create_link",
             "home_doc": str(a_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_before), "note": "Before deletion: 0.x/2.x link, 1.x text"},
            {"op": "find_links", "specs": specset_to_list(find_specs), "result": [str(lid) for lid in links_before], "note": "Link should be found"},
            {"op": "delete",
             "doc": str(a_opened),
             "start": "2.1",
             "width": "0.1",
             "succeeded": delete_succeeded,
             "error": delete_error,
             "note": "Delete link subspace V-range 2.1"},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_after), "note": "After deletion: is 2.x gone?"},
            {"op": "find_links", "specs": specset_to_list(find_specs), "result": [str(lid) for lid in links_after], "note": "Can we still find the link?"},
            {"op": "follow_link",
             "link": str(link_id),
             "end": "source",
             "result": specset_to_list(followed) if follow_succeeded else None,
             "succeeded": follow_succeeded,
             "error": follow_error,
             "note": "Can we still follow the link?"}
        ]
    }


SCENARIOS = [
    ("links", "delete_link_subspace", scenario_delete_link_subspace),
]
