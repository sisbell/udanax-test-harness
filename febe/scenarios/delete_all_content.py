"""Test scenarios for deleting ALL content from a document.

This explores the tree state when DELETE removes the entire V-span,
comparing it to the initial empty enfilade state created by createenf(POOM).
"""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_delete_all_content_simple(session):
    """Delete all content from a document in one operation.

    Questions:
    - Does the tree return to the initial empty enfilade form (height-1, one zero-width node)?
    - Or does disown + recombine produce a different structure?
    - What is the resulting tree height?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert some content
    session.insert(opened, Address(1, 1), ["Test content"])
    vspanset_before = session.retrieve_vspanset(opened)
    specset_before = SpecSet(VSpec(opened, list(vspanset_before.spans)))
    contents_before = session.retrieve_contents(specset_before)

    # Delete ALL content - the entire V-span
    full_span = vspanset_before.spans[0]
    session.remove(opened, full_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    # Insert again at 1.1 after delete-all
    session.insert(opened, Address(1, 1), ["After delete"])
    vspanset_reinsert = session.retrieve_vspanset(opened)
    specset_reinsert = SpecSet(VSpec(opened, list(vspanset_reinsert.spans)))
    contents_reinsert = session.retrieve_contents(specset_reinsert)

    session.close_document(opened)

    return {
        "name": "delete_all_content_simple",
        "description": "Delete entire V-span in one operation, observe tree state",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "Test content"},
            {"op": "retrieve_vspanset", "before_delete": vspec_to_dict(vspanset_before)},
            {"op": "retrieve_contents", "before": contents_before},
            {"op": "remove", "span": span_to_dict(full_span),
             "comment": "DELETE entire V-span - all content"},
            {"op": "retrieve_vspanset", "after_delete": vspec_to_dict(vspanset_after),
             "comment": "Is this empty like createenf(POOM)?"},
            {"op": "retrieve_contents", "after": contents_after,
             "expected": "empty"},
            {"op": "insert_after_delete", "address": "1.1", "text": "After delete",
             "result": contents_reinsert,
             "reinsert_vspans": vspec_to_dict(vspanset_reinsert),
             "comment": "INSERT into fully-deleted document — tests if empty-after-edit state supports re-insertion"}
        ]
    }


def scenario_delete_all_incrementally(session):
    """Delete all content incrementally (multiple DELETE operations).

    Does incremental deletion produce the same final state as deleting everything at once?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert content
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])
    vspanset_initial = session.retrieve_vspanset(opened)
    specset_initial = SpecSet(VSpec(opened, list(vspanset_initial.spans)))
    contents_initial = session.retrieve_contents(specset_initial)

    # Delete in chunks: 3, 3, 2 characters
    session.remove(opened, Span(Address(1, 1), Offset(0, 3)))  # Delete "ABC"
    vspanset_1 = session.retrieve_vspanset(opened)
    specset_1 = SpecSet(VSpec(opened, list(vspanset_1.spans)))
    contents_1 = session.retrieve_contents(specset_1)

    session.remove(opened, Span(Address(1, 1), Offset(0, 3)))  # Delete "DEF"
    vspanset_2 = session.retrieve_vspanset(opened)
    specset_2 = SpecSet(VSpec(opened, list(vspanset_2.spans)))
    contents_2 = session.retrieve_contents(specset_2)

    session.remove(opened, Span(Address(1, 1), Offset(0, 2)))  # Delete "GH" - last content
    vspanset_final = session.retrieve_vspanset(opened)
    specset_final = SpecSet(VSpec(opened, list(vspanset_final.spans)))
    contents_final = session.retrieve_contents(specset_final)

    # Reinsert after all content deleted
    session.insert(opened, Address(1, 1), ["Rebuilt"])
    vspanset_rebuilt = session.retrieve_vspanset(opened)
    specset_rebuilt = SpecSet(VSpec(opened, list(vspanset_rebuilt.spans)))
    contents_rebuilt = session.retrieve_contents(specset_rebuilt)

    session.close_document(opened)

    return {
        "name": "delete_all_incrementally",
        "description": "Delete all content in multiple operations",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABCDEFGH", "result": contents_initial},
            {"op": "remove", "span": "1.1 length 3", "comment": "Delete ABC",
             "remaining": contents_1},
            {"op": "remove", "span": "1.1 length 3", "comment": "Delete DEF (shifted)",
             "remaining": contents_2},
            {"op": "remove", "span": "1.1 length 2", "comment": "Delete GH - last content",
             "remaining": contents_final, "expected": "empty"},
            {"op": "retrieve_vspanset", "after_all_deletes": vspec_to_dict(vspanset_final),
             "comment": "Final tree state after incremental deletion"},
            {"op": "insert_after_delete", "text": "Rebuilt", "result": contents_rebuilt,
             "comment": "INSERT into fully-deleted document — tests empty-after-edit state"}
        ]
    }


def scenario_delete_all_with_links(session):
    """Delete all content from a document that has links.

    When all content is deleted:
    - Do links survive in the tree?
    - What happens to link endsets with no V-mapping?
    - Does recombine clean up orphaned link entries?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert content and create a link
    session.insert(opened, Address(1, 1), ["Source and Target"])
    from_span = Span(Address(1, 1), Offset(0, 6))  # "Source"
    to_span = Span(Address(1, 12), Offset(0, 6))    # "Target"
    from_specs = SpecSet(VSpec(opened, [from_span]))
    to_specs = SpecSet(VSpec(opened, [to_span]))
    type_specs = SpecSet(Span(Address(1, 1, 0, 1), Offset(0, 1)))

    link_id = session.create_link(opened, from_specs, to_specs, type_specs)

    # Verify link exists
    links_before = session.find_links(from_specs)

    vspanset_before = session.retrieve_vspanset(opened)
    full_span = vspanset_before.spans[0]

    # Delete ALL content
    session.remove(opened, full_span)

    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    # Try to find links after deletion
    try:
        links_after = session.find_links(SpecSet(VSpec(opened, [])))
        links_result = {"success": True, "count": len(links_after)}
    except Exception as e:
        links_result = {"success": False, "error": str(e)}

    session.close_document(opened)

    return {
        "name": "delete_all_with_links",
        "description": "Delete all content including link endpoints",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "Source and Target"},
            {"op": "create_link", "from": "Source", "to": "Target",
             "link_id": str(link_id)},
            {"op": "find_links", "before_delete": [str(l) for l in links_before]},
            {"op": "remove", "span": "entire document",
             "comment": "Delete all content including link endpoints"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset_after)},
            {"op": "retrieve_contents", "after": contents_after},
            {"op": "find_links", "after_delete": links_result,
             "comment": "Do links survive when all content is deleted?"}
        ]
    }


def scenario_empty_document_never_filled(session):
    """Create a document but never insert content - pure empty state.

    This establishes the baseline: what does createenf(POOM) produce?
    Compare with delete_all_content to see if they produce identical structures.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Retrieve vspanset of empty document
    vspanset_empty = session.retrieve_vspanset(opened)
    specset_empty = SpecSet(VSpec(opened, list(vspanset_empty.spans)))
    contents_empty = session.retrieve_contents(specset_empty)

    # Try to insert at 1.1 (should work)
    session.insert(opened, Address(1, 1), ["First content"])
    vspanset_after = session.retrieve_vspanset(opened)
    specset_after = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    session.close_document(opened)

    return {
        "name": "empty_document_never_filled",
        "description": "Baseline: document created but never filled with content",
        "operations": [
            {"op": "create_document", "result": str(docid),
             "comment": "createenf(POOM) creates initial empty enfilade"},
            {"op": "open_document", "result": str(opened)},
            {"op": "retrieve_vspanset", "empty_state": vspec_to_dict(vspanset_empty),
             "comment": "What does the initial empty enfilade look like?"},
            {"op": "retrieve_contents", "empty": contents_empty,
             "expected": "empty"},
            {"op": "insert", "address": "1.1", "text": "First content"},
            {"op": "retrieve_vspanset", "after_insert": vspec_to_dict(vspanset_after)},
            {"op": "retrieve_contents", "after": contents_after}
        ]
    }


def scenario_delete_all_then_transclude(session):
    """Delete all content, then transclude into the empty document.

    Does VCOPY work into a fully-deleted document?
    Does it behave the same as VCOPY into a never-filled document?
    """
    # Create source document
    source = session.create_document()
    opened_source = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_source, Address(1, 1), ["Source material"])
    session.close_document(opened_source)

    # Create target, add content, then delete all
    target = session.create_document()
    opened_target = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_target, Address(1, 1), ["Temporary"])
    vspanset_temp = session.retrieve_vspanset(opened_target)
    session.remove(opened_target, vspanset_temp.spans[0])  # Delete all

    vspanset_empty = session.retrieve_vspanset(opened_target)

    # Now transclude into the empty document
    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_vspanset = session.retrieve_vspanset(source_ro)
    source_specs = SpecSet(VSpec(source_ro, list(source_vspanset.spans)))

    session.vcopy(opened_target, Address(1, 1), source_specs)
    vspanset_after = session.retrieve_vspanset(opened_target)
    specset_after = SpecSet(VSpec(opened_target, list(vspanset_after.spans)))
    contents_after = session.retrieve_contents(specset_after)

    session.close_document(source_ro)
    session.close_document(opened_target)

    return {
        "name": "delete_all_then_transclude",
        "description": "Delete all content, then VCOPY into empty document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Source material"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Temporary"},
            {"op": "remove", "doc": "target", "comment": "Delete all content"},
            {"op": "retrieve_vspanset", "empty_state": vspec_to_dict(vspanset_empty)},
            {"op": "vcopy_after_delete", "from": "source", "to": "target at 1.1",
             "result": contents_after,
             "after_vspans": vspec_to_dict(vspanset_after),
             "comment": "VCOPY into fully-deleted document — tests empty-after-edit state"}
        ]
    }


SCENARIOS = [
    ("delete_all", "delete_all_content_simple", scenario_delete_all_content_simple),
    ("delete_all", "delete_all_incrementally", scenario_delete_all_incrementally),
    ("delete_all", "delete_all_with_links", scenario_delete_all_with_links),
    ("delete_all", "empty_document_never_filled", scenario_empty_document_never_filled),
    ("delete_all", "delete_all_then_transclude", scenario_delete_all_then_transclude),
]
