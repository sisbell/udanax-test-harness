"""Test spanfilade cleanup behavior for deleted transcluded content.

This scenario tests whether DELETE operations clean up spanfilade entries
that were created by previous COPY operations. The question:

When a document DELETEs content that was previously COPYed (transcluded)
into it, does the DELETE operation clean up the spanfilade entries?

COPY calls insertspanf to register the destination document's reference
to the transcluded I-addresses. When that content is later deleted from
the destination via deletevspanpm, is there a corresponding call to
remove the spanfilade entries?

Expected behavior (if cleanup happens):
- After DELETE, FIND_DOCUMENTS should not return the destination document

Actual behavior (if no cleanup):
- The spanfilade retains stale references to documents that no longer
  contain those I-addresses
"""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_delete_transcluded_content_spanfilade_cleanup(session):
    """Test whether DELETE cleans up spanfilade entries for transcluded content.

    Steps:
    1. Create source document with content
    2. Create target document
    3. COPY (transclude) source content into target
       - This calls insertspanf to register target's reference to the I-addresses
    4. Verify target appears in FIND_DOCUMENTS for the content
    5. DELETE the transcluded content from target
       - Should this call a deletespanf-like operation?
    6. Check if target still appears in FIND_DOCUMENTS
       - If yes: spanfilade has stale references (no cleanup)
       - If no: spanfilade was properly cleaned up
    """
    # Step 1: Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source content to transclude"])
    source_vspanset = session.retrieve_vspanset(source_opened)
    session.close_document(source_opened)

    # Step 2: Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Prefix: "])
    target_vspanset1 = session.retrieve_vspanset(target_opened)

    # Step 3: COPY source content into target (this calls insertspanf)
    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    # Copy "Source content" (first 14 characters)
    copy_span = Span(Address(1, 1), Offset(0, 14))
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    session.vcopy(target_opened, target_vspanset1.spans[0].end(), copy_specs)
    session.close_document(source_read)

    # Get target content after copy
    target_vspanset2 = session.retrieve_vspanset(target_opened)
    target_specset_after_copy = SpecSet(VSpec(target_opened, list(target_vspanset2.spans)))
    target_contents_after_copy = session.retrieve_contents(target_specset_after_copy)
    session.close_document(target_opened)

    # Step 4: Find which documents contain the transcluded content
    # Search for the I-addresses that were copied
    source_read2 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_span = Span(Address(1, 1), Offset(0, 14))
    search_specs = SpecSet(VSpec(source_read2, [search_span]))

    docs_before_delete = session.find_documents(search_specs)
    session.close_document(source_read2)

    # Convert to serializable format
    docs_before_list = [str(docid) for docid in docs_before_delete]

    # Step 5: DELETE the transcluded content from target
    # This calls deletevspanpm, but does it clean up spanfilade?
    target_opened2 = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    target_vspanset3 = session.retrieve_vspanset(target_opened2)

    # Find the transcluded span in target (should be the second span after "Prefix: ")
    # Delete it
    delete_span = Span(Address(1, 9), Offset(0, 14))  # "Source content"
    session.remove(target_opened2, delete_span)

    # Get target content after deletion
    target_vspanset4 = session.retrieve_vspanset(target_opened2)
    target_specset_after_delete = SpecSet(VSpec(target_opened2, list(target_vspanset4.spans)))
    target_contents_after_delete = session.retrieve_contents(target_specset_after_delete)
    session.close_document(target_opened2)

    # Step 6: Find which documents contain the content NOW
    # If spanfilade was cleaned up, target should NOT appear
    # If spanfilade has stale references, target WILL appear
    source_read3 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_span2 = Span(Address(1, 1), Offset(0, 14))
    search_specs2 = SpecSet(VSpec(source_read3, [search_span2]))

    docs_after_delete = session.find_documents(search_specs2)
    session.close_document(source_read3)

    docs_after_list = [str(docid) for docid in docs_after_delete]

    # Analysis
    target_in_results_before = str(target_doc) in docs_before_list
    target_in_results_after = str(target_doc) in docs_after_list

    spanfilade_cleaned_up = target_in_results_before and not target_in_results_after
    spanfilade_has_stale_refs = target_in_results_before and target_in_results_after

    return {
        "name": "delete_transcluded_content_spanfilade_cleanup",
        "description": "Test whether DELETE cleans up spanfilade entries for transcluded content",
        "operations": [
            {"op": "create_document", "label": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source content to transclude"},
            {"op": "create_document", "label": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Prefix: "},
            {"op": "vcopy", "from": "source", "to": "target", "text": "Source content",
             "comment": "This calls insertspanf to register target's reference"},
            {"op": "retrieve_contents", "doc": "target", "label": "after_copy",
             "result": target_contents_after_copy},
            {"op": "find_documents", "search": "Source content", "label": "before_delete",
             "result": docs_before_list,
             "comment": "Should include both source and target"},
            {"op": "remove", "doc": "target", "span": "Source content",
             "comment": "Delete transcluded content from target"},
            {"op": "retrieve_contents", "doc": "target", "label": "after_delete",
             "result": target_contents_after_delete,
             "comment": "Should only have 'Prefix: '"},
            {"op": "find_documents", "search": "Source content", "label": "after_delete",
             "result": docs_after_list,
             "comment": "If spanfilade cleaned up: only source. If stale refs: source AND target"},
            {"op": "analysis", "results": {
                "target_found_before_delete": target_in_results_before,
                "target_found_after_delete": target_in_results_after,
                "spanfilade_cleaned_up": spanfilade_cleaned_up,
                "spanfilade_has_stale_refs": spanfilade_has_stale_refs
            }}
        ]
    }


def scenario_delete_destination_multiple_transclusions(session):
    """Test spanfilade cleanup when same content is transcluded into multiple documents.

    This tests whether DELETE properly handles reference counting:
    - If content is transcluded into docs A, B, and C
    - And we DELETE from doc B
    - Should B be removed from spanfilade but A and C remain?
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared transcluded content"])
    session.close_document(source_opened)

    # Create three target documents that all transclude the same content
    targets = []
    for i in range(3):
        target_doc = session.create_document()
        target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(target_opened, Address(1, 1), [f"Target {i}: "])

        source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
        copy_span = Span(Address(1, 1), Offset(0, 24))  # All of it
        copy_specs = SpecSet(VSpec(source_read, [copy_span]))
        target_vs = session.retrieve_vspanset(target_opened)
        session.vcopy(target_opened, target_vs.spans[0].end(), copy_specs)
        session.close_document(source_read)
        session.close_document(target_opened)

        targets.append(target_doc)

    # Find documents before any deletion
    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_span = Span(Address(1, 1), Offset(0, 24))
    search_specs = SpecSet(VSpec(source_read, [search_span]))
    docs_before = session.find_documents(search_specs)
    session.close_document(source_read)

    docs_before_list = sorted([str(d) for d in docs_before])

    # Delete from target[1] (the middle one)
    target_opened = session.open_document(targets[1], READ_WRITE, CONFLICT_FAIL)
    delete_span = Span(Address(1, 11), Offset(0, 24))  # After "Target 1: "
    session.remove(target_opened, delete_span)
    session.close_document(target_opened)

    # Find documents after deletion
    source_read2 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_specs2 = SpecSet(VSpec(source_read2, [search_span]))
    docs_after = session.find_documents(search_specs2)
    session.close_document(source_read2)

    docs_after_list = sorted([str(d) for d in docs_after])

    # Analysis
    target1_str = str(targets[1])
    target1_in_before = target1_str in docs_before_list
    target1_in_after = target1_str in docs_after_list

    other_targets_still_present = (
        str(targets[0]) in docs_after_list and
        str(targets[2]) in docs_after_list
    )

    return {
        "name": "delete_destination_multiple_transclusions",
        "description": "Test spanfilade cleanup with multiple documents transcluding same content",
        "operations": [
            {"op": "create_document", "label": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Shared transcluded content"},
            {"op": "create_and_transclude", "count": 3,
             "targets": [str(t) for t in targets],
             "comment": "Three documents all transclude the same source content"},
            {"op": "find_documents", "label": "before_delete",
             "result": docs_before_list,
             "comment": "Should find source + 3 targets = 4 documents"},
            {"op": "remove", "doc": str(targets[1]), "text": "transcluded content",
             "comment": "Delete from target[1] only"},
            {"op": "find_documents", "label": "after_delete",
             "result": docs_after_list,
             "comment": "If cleanup works: source + targets[0,2]. If stale: all 4"},
            {"op": "analysis", "results": {
                "target1_in_before": target1_in_before,
                "target1_in_after": target1_in_after,
                "other_targets_still_present": other_targets_still_present,
                "expected_behavior": "target1 removed from results, others remain"
            }}
        ]
    }


def scenario_delete_all_transcluded_content(session):
    """Test cleanup when ALL content in a document is transcluded and then deleted.

    This is an edge case: if a document contains ONLY transcluded content
    and we delete all of it, the document's POOM becomes empty but the
    spanfilade may still have entries.
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["All transcluded"])
    session.close_document(source_opened)

    # Create target document with ONLY transcluded content (no native content)
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)

    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 15))
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    session.vcopy(target_opened, Address(1, 1), copy_specs)
    session.close_document(source_read)

    # Verify target has content
    target_vs1 = session.retrieve_vspanset(target_opened)
    target_ss1 = SpecSet(VSpec(target_opened, list(target_vs1.spans)))
    target_before = session.retrieve_contents(target_ss1)
    session.close_document(target_opened)

    # Find documents before deletion
    source_read2 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_specs = SpecSet(VSpec(source_read2, [copy_span]))
    docs_before = session.find_documents(search_specs)
    session.close_document(source_read2)

    # Delete ALL content from target
    target_opened2 = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    target_vs2 = session.retrieve_vspanset(target_opened2)
    # Delete the entire document content
    for span in target_vs2.spans:
        session.remove(target_opened2, span)

    # Verify target is empty
    target_vs3 = session.retrieve_vspanset(target_opened2)
    target_empty = len(list(target_vs3.spans)) == 0
    session.close_document(target_opened2)

    # Find documents after deletion
    source_read3 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    search_specs2 = SpecSet(VSpec(source_read3, [copy_span]))
    docs_after = session.find_documents(search_specs2)
    session.close_document(source_read3)

    docs_before_list = sorted([str(d) for d in docs_before])
    docs_after_list = sorted([str(d) for d in docs_after])

    target_in_before = str(target_doc) in docs_before_list
    target_in_after = str(target_doc) in docs_after_list

    return {
        "name": "delete_all_transcluded_content",
        "description": "Test cleanup when deleting ALL content from a document (which is all transcluded)",
        "operations": [
            {"op": "create_document", "label": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "All transcluded"},
            {"op": "create_document", "label": "target", "result": str(target_doc)},
            {"op": "vcopy", "from": "source", "to": "target", "text": "all",
             "comment": "Target has ONLY transcluded content, no native content"},
            {"op": "retrieve_contents", "doc": "target", "result": target_before},
            {"op": "find_documents", "label": "before_delete",
             "result": docs_before_list},
            {"op": "remove_all", "doc": "target",
             "comment": "Delete ALL content from target"},
            {"op": "verify_empty", "doc": "target", "is_empty": target_empty},
            {"op": "find_documents", "label": "after_delete",
             "result": docs_after_list,
             "comment": "Should only find source, not empty target"},
            {"op": "analysis", "results": {
                "target_in_before": target_in_before,
                "target_in_after": target_in_after,
                "target_is_empty": target_empty,
                "expected": "target not in results after deletion"
            }}
        ]
    }


SCENARIOS = [
    ("spanfilade", "delete_transcluded_content_spanfilade_cleanup",
     scenario_delete_transcluded_content_spanfilade_cleanup),
    ("spanfilade", "delete_destination_multiple_transclusions",
     scenario_delete_destination_multiple_transclusions),
    ("spanfilade", "delete_all_transcluded_content",
     scenario_delete_all_transcluded_content),
]
