"""Link search behavior when endpoints are removed from V-stream.

These scenarios test how find_links() behaves when the content that link
endpoints refer to is partially or completely removed from the document's
V-stream (visible view).

Key questions:
- Can find_links() discover links when source content is gone?
- Can find_links() discover links when target content is gone?
- How does partial removal affect search?
- What about search via multiple criteria (source AND target)?
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list
from .common import contents_to_list


def scenario_search_by_source_after_source_removed(session):
    """Test find_links() by source specset after source content is deleted.

    Creates a link, then deletes the source content. Tests whether
    find_links(source_specset) can still discover the link.
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for more info"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Detailed information"])

    # Create link on "here" (positions 7-10)
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 8))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Find links BEFORE deletion - search entire source document
    search_spec = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))]))
    before_find = session.find_links(search_spec)

    # Delete the source endpoint content ("here ")
    session.remove(source_opened, Span(Address(1, 7), Offset(0, 5)))

    # Get new document contents
    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(
        SpecSet(VSpec(source_opened, list(vspanset.spans)))
    ) if vspanset.spans else []

    # Try to find links AFTER deletion - same search area
    after_find = session.find_links(search_spec)

    # Also try searching the exact deleted region
    deleted_region_search = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    deleted_region_find = session.find_links(deleted_region_search)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_by_source_after_source_removed",
        "description": "Test find_links() by source specset after source content is deleted",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click here for more info"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Detailed information"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "find_links", "label": "before_delete", "by": "source",
             "result": [str(l) for l in before_find],
             "comment": "Link should be found via source search"},
            {"op": "delete", "doc": "source", "span": "here ",
             "comment": "Delete the source endpoint content"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": contents_to_list(after_contents)},
            {"op": "find_links", "label": "after_delete", "by": "source",
             "search": "entire document",
             "result": [str(l) for l in after_find],
             "comment": "Can link be found after source content deleted?"},
            {"op": "find_links", "label": "deleted_region", "by": "source",
             "search": "exact deleted region",
             "result": [str(l) for l in deleted_region_find],
             "comment": "Search within the now-empty region"}
        ]
    }


def scenario_search_by_target_after_source_removed(session):
    """Test find_links() by target specset after source content is deleted.

    Creates a link, deletes the source content, but searches by target.
    The target is intact, so can we find the link via target search?
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source text here"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content unchanged"])

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search by target BEFORE deletion
    target_search = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 25))]))
    before_find = session.find_links(NOSPECS, target_search)

    # Delete ALL source content
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 16)))

    # Search by target AFTER source deletion
    after_find = session.find_links(NOSPECS, target_search)

    # Verify target content is unchanged
    target_vspanset = session.retrieve_vspanset(target_opened)
    target_contents = session.retrieve_contents(
        SpecSet(VSpec(target_opened, list(target_vspanset.spans)))
    )

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_by_target_after_source_removed",
        "description": "Test find_links() by target specset after source content is deleted",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source text here"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content unchanged"},
            {"op": "create_link", "source_text": "Source", "target_text": "Target",
             "result": str(link_id)},
            {"op": "find_links", "label": "before_delete", "by": "target",
             "result": [str(l) for l in before_find]},
            {"op": "delete_all", "doc": "source",
             "comment": "Delete all source content - target is intact"},
            {"op": "find_links", "label": "after_delete", "by": "target",
             "result": [str(l) for l in after_find],
             "comment": "Can link be found via target when source is gone?"},
            {"op": "contents", "doc": "target",
             "result": contents_to_list(target_contents),
             "comment": "Target content unchanged"}
        ]
    }


def scenario_search_by_source_after_target_removed(session):
    """Test find_links() by source specset after target content is deleted.

    Creates a link, deletes the target content, but searches by source.
    The source is intact, so can we find the link via source search?
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source content unchanged"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target text here"])

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search by source BEFORE deletion
    source_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))]))
    before_find = session.find_links(source_search)

    # Delete ALL target content
    session.remove(target_opened, Span(Address(1, 1), Offset(0, 16)))

    # Search by source AFTER target deletion
    after_find = session.find_links(source_search)

    # Verify source content is unchanged
    source_vspanset = session.retrieve_vspanset(source_opened)
    source_contents = session.retrieve_contents(
        SpecSet(VSpec(source_opened, list(source_vspanset.spans)))
    )

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_by_source_after_target_removed",
        "description": "Test find_links() by source specset after target content is deleted",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source content unchanged"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target text here"},
            {"op": "create_link", "source_text": "Source", "target_text": "Target",
             "result": str(link_id)},
            {"op": "find_links", "label": "before_delete", "by": "source",
             "result": [str(l) for l in before_find]},
            {"op": "delete_all", "doc": "target",
             "comment": "Delete all target content - source is intact"},
            {"op": "find_links", "label": "after_delete", "by": "source",
             "result": [str(l) for l in after_find],
             "comment": "Can link be found via source when target is gone?"},
            {"op": "contents", "doc": "source",
             "result": contents_to_list(source_contents),
             "comment": "Source content unchanged"}
        ]
    }


def scenario_search_by_both_endpoints_one_removed(session):
    """Test find_links() with both source AND target specs when one endpoint is removed.

    find_links(source, target) returns links matching BOTH criteria.
    What happens when one side is deleted?
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source endpoint text"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target endpoint text"])

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search with BOTH source and target specs BEFORE deletion
    source_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))]))
    target_search = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 20))]))
    before_find_both = session.find_links(source_search, target_search)

    # Delete source content
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 20)))

    # Search with BOTH specs AFTER source deletion
    # Source is empty, target is intact
    after_find_both = session.find_links(source_search, target_search)

    # Also test just target search (should still work)
    after_find_target_only = session.find_links(NOSPECS, target_search)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_by_both_endpoints_one_removed",
        "description": "Test find_links(source, target) when source endpoint is deleted",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source endpoint text"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target endpoint text"},
            {"op": "create_link", "result": str(link_id)},
            {"op": "find_links", "label": "before_delete", "by": "source AND target",
             "result": [str(l) for l in before_find_both],
             "comment": "Search with both endpoint criteria"},
            {"op": "delete_all", "doc": "source"},
            {"op": "find_links", "label": "after_delete", "by": "source AND target",
             "result": [str(l) for l in after_find_both],
             "comment": "Both-endpoint search when source is empty"},
            {"op": "find_links", "label": "after_delete", "by": "target only",
             "result": [str(l) for l in after_find_target_only],
             "comment": "Target-only search for comparison"}
        ]
    }


def scenario_search_partial_source_removal(session):
    """Test find_links() when only PART of the source endpoint is removed.

    Link is on "hyperlink", we delete "hyper", leaving "link".
    Does find_links() still find it when searching the document?
    """
    # Create documents
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click hyperlink here"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "hyperlink" (positions 7-15)
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 9))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search entire document BEFORE partial deletion
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))]))
    before_find = session.find_links(full_search)

    # Also search just the linked region
    linked_region_search = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 9))]))
    before_find_region = session.find_links(linked_region_search)

    # Delete "hyper" (positions 7-11), leaving "link" (now at positions 7-10)
    session.remove(source_opened, Span(Address(1, 7), Offset(0, 5)))

    # Get new contents
    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(
        SpecSet(VSpec(source_opened, list(vspanset.spans)))
    )

    # Search entire document AFTER partial deletion
    after_find_full = session.find_links(full_search)

    # Search the region that still contains "link"
    remaining_region_search = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    after_find_remaining = session.find_links(remaining_region_search)

    # Search the now-empty region (where "hyper" was)
    # Note: The deleted region doesn't exist in V-stream anymore

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_partial_source_removal",
        "description": "Test find_links() when only PART of the source endpoint is removed",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click hyperlink here"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "hyperlink", "result": str(link_id)},
            {"op": "find_links", "label": "before_delete", "by": "full document",
             "result": [str(l) for l in before_find]},
            {"op": "find_links", "label": "before_delete", "by": "linked region",
             "result": [str(l) for l in before_find_region]},
            {"op": "delete", "doc": "source", "span": "hyper",
             "comment": "Delete 'hyper' from 'hyperlink', leaving 'link'"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": contents_to_list(after_contents)},
            {"op": "find_links", "label": "after_delete", "by": "full document",
             "result": [str(l) for l in after_find_full],
             "comment": "Full doc search after partial deletion"},
            {"op": "find_links", "label": "after_delete", "by": "remaining region",
             "result": [str(l) for l in after_find_remaining],
             "comment": "Search region still containing 'link'"}
        ]
    }


def scenario_search_multiple_links_selective_removal(session):
    """Test find_links() with multiple links when only some endpoints are removed.

    Creates 3 links to same target. Deletes source content for link2 only.
    find_links should still find link1 and link3.
    """
    # Create three source documents
    source1_doc = session.create_document()
    source1 = session.open_document(source1_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source1, Address(1, 1), ["First source text"])

    source2_doc = session.create_document()
    source2 = session.open_document(source2_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source2, Address(1, 1), ["Second source text"])

    source3_doc = session.create_document()
    source3 = session.open_document(source3_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source3, Address(1, 1), ["Third source text"])

    # Create shared target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Shared target content"])

    # Create three links, all pointing to same target
    link1_source = SpecSet(VSpec(source1, [Span(Address(1, 1), Offset(0, 5))]))
    link2_source = SpecSet(VSpec(source2, [Span(Address(1, 1), Offset(0, 6))]))
    link3_source = SpecSet(VSpec(source3, [Span(Address(1, 1), Offset(0, 5))]))
    common_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))

    link1_id = session.create_link(source1, link1_source, common_target, SpecSet([JUMP_TYPE]))
    link2_id = session.create_link(source2, link2_source, common_target, SpecSet([JUMP_TYPE]))
    link3_id = session.create_link(source3, link3_source, common_target, SpecSet([JUMP_TYPE]))

    # Find all links via target BEFORE any deletion
    target_search = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 25))]))
    before_find = session.find_links(NOSPECS, target_search)

    # Delete ALL content from source2 (middle link)
    session.remove(source2, Span(Address(1, 1), Offset(0, 18)))

    # Find links via target AFTER deletion
    after_find = session.find_links(NOSPECS, target_search)

    # Find links from each source individually
    search1 = SpecSet(VSpec(source1, [Span(Address(1, 1), Offset(0, 20))]))
    search2 = SpecSet(VSpec(source2, [Span(Address(1, 1), Offset(0, 20))]))  # empty now
    search3 = SpecSet(VSpec(source3, [Span(Address(1, 1), Offset(0, 20))]))

    find_from_s1 = session.find_links(search1)
    find_from_s2 = session.find_links(search2)
    find_from_s3 = session.find_links(search3)

    session.close_document(source1)
    session.close_document(source2)
    session.close_document(source3)
    session.close_document(target_opened)

    return {
        "name": "search_multiple_links_selective_removal",
        "description": "Test find_links() with multiple links when only some endpoints are removed",
        "operations": [
            {"op": "create_documents", "count": 3, "type": "source"},
            {"op": "create_document", "doc": "shared_target", "result": str(target_doc)},
            {"op": "create_links", "count": 3,
             "results": [str(link1_id), str(link2_id), str(link3_id)]},
            {"op": "find_links", "label": "before_delete", "by": "target",
             "result": [str(l) for l in before_find],
             "comment": "Should find all 3 links"},
            {"op": "delete_all", "doc": "source2",
             "comment": "Delete content from second source only"},
            {"op": "find_links", "label": "after_delete", "by": "target",
             "result": [str(l) for l in after_find],
             "comment": "Should find all 3 (target intact) or just 2?"},
            {"op": "find_links", "by": "source1",
             "result": [str(l) for l in find_from_s1]},
            {"op": "find_links", "by": "source2 (empty)",
             "result": [str(l) for l in find_from_s2],
             "comment": "Source2 is empty - can we find its link?"},
            {"op": "find_links", "by": "source3",
             "result": [str(l) for l in find_from_s3]}
        ]
    }


def scenario_search_spanning_deleted_boundary(session):
    """Test find_links() with search spec that spans across a deletion point.

    Creates a link, deletes content in the middle of the document,
    then searches with a spec that would have covered the deleted region.
    """
    # Create documents
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Start MIDDLE End link text"])
    # Positions: Start=1-5, MIDDLE=7-12, End=14-16, link=18-21, text=23-26

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "link" (positions 18-21)
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 18), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search full document BEFORE deletion
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 26))]))
    before_find = session.find_links(full_search)
    before_contents = session.retrieve_contents(full_search)

    # Delete "MIDDLE " (positions 7-13)
    session.remove(source_opened, Span(Address(1, 7), Offset(0, 7)))
    # Result: "Start End link text"

    # Get new vspanset to understand new layout
    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(
        SpecSet(VSpec(source_opened, list(vspanset.spans)))
    ) if vspanset.spans else []

    # Search with the ORIGINAL spec (positions 1-26)
    # Some of these positions no longer exist in V-stream
    after_find_original = session.find_links(full_search)

    # Search with a NEW spec covering actual remaining content
    # Document is now shorter, but link should still be there
    new_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))]))
    after_find_adjusted = session.find_links(new_search)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_spanning_deleted_boundary",
        "description": "Test find_links() with search spec spanning a deletion point",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Start MIDDLE End link text"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "link", "result": str(link_id)},
            {"op": "find_links", "label": "before_delete",
             "result": [str(l) for l in before_find]},
            {"op": "contents", "label": "before_delete",
             "result": contents_to_list(before_contents)},
            {"op": "delete", "doc": "source", "span": "MIDDLE ",
             "comment": "Delete middle section of document"},
            {"op": "contents", "label": "after_delete",
             "result": contents_to_list(after_contents)},
            {"op": "find_links", "label": "after_delete", "search": "original spec",
             "result": [str(l) for l in after_find_original],
             "comment": "Original search spec (may reference non-existent positions)"},
            {"op": "find_links", "label": "after_delete", "search": "adjusted spec",
             "result": [str(l) for l in after_find_adjusted],
             "comment": "Search spec adjusted to new document size"}
        ]
    }


def scenario_search_after_vcopy_source_deleted(session):
    """Test find_links() after transcluded (vcopy'd) content is deleted.

    Creates a link on content in doc A. Vcopies that content to doc B.
    Then deletes original content from doc A. Can we find the link from doc B?
    """
    # Create original document
    orig_doc = session.create_document()
    orig_opened = session.open_document(orig_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original linked content here"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "linked" (positions 10-15)
    link_source = SpecSet(VSpec(orig_opened, [Span(Address(1, 10), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(orig_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Create copy document and vcopy the linked content
    copy_doc = session.create_document()
    copy_opened = session.open_document(copy_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy_opened, Address(1, 1), ["Prefix: "])

    # vcopy "linked" from original to copy
    copy_specs = SpecSet(VSpec(orig_opened, [Span(Address(1, 10), Offset(0, 6))]))
    session.vcopy(copy_opened, Address(1, 9), copy_specs)

    # Verify link can be found from both original and copy BEFORE deletion
    orig_search = SpecSet(VSpec(orig_opened, [Span(Address(1, 1), Offset(0, 30))]))
    copy_search = SpecSet(VSpec(copy_opened, [Span(Address(1, 1), Offset(0, 20))]))

    before_find_orig = session.find_links(orig_search)
    before_find_copy = session.find_links(copy_search)

    # Delete the linked content from ORIGINAL document
    session.remove(orig_opened, Span(Address(1, 10), Offset(0, 7)))  # "linked "

    # Get contents of both documents after deletion
    orig_vspanset = session.retrieve_vspanset(orig_opened)
    orig_contents = session.retrieve_contents(
        SpecSet(VSpec(orig_opened, list(orig_vspanset.spans)))
    ) if orig_vspanset.spans else []

    copy_vspanset = session.retrieve_vspanset(copy_opened)
    copy_contents = session.retrieve_contents(
        SpecSet(VSpec(copy_opened, list(copy_vspanset.spans)))
    )

    # Try to find link from both documents AFTER deletion
    after_find_orig = session.find_links(orig_search)
    after_find_copy = session.find_links(copy_search)

    session.close_document(orig_opened)
    session.close_document(copy_opened)
    session.close_document(target_opened)

    return {
        "name": "search_after_vcopy_source_deleted",
        "description": "Test find_links() after transcluded content deleted from original",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(orig_doc)},
            {"op": "insert", "doc": "original", "text": "Original linked content here"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "linked", "result": str(link_id)},
            {"op": "create_document", "doc": "copy", "result": str(copy_doc)},
            {"op": "vcopy", "from": "original", "to": "copy", "text": "linked"},
            {"op": "find_links", "label": "before_delete", "by": "original",
             "result": [str(l) for l in before_find_orig]},
            {"op": "find_links", "label": "before_delete", "by": "copy",
             "result": [str(l) for l in before_find_copy],
             "comment": "Link findable from transcluded copy?"},
            {"op": "delete", "doc": "original", "span": "linked ",
             "comment": "Delete linked content from ORIGINAL only"},
            {"op": "contents", "doc": "original", "label": "after_delete",
             "result": contents_to_list(orig_contents)},
            {"op": "contents", "doc": "copy", "label": "after_delete",
             "result": contents_to_list(copy_contents),
             "comment": "Copy may still have content via transclusion"},
            {"op": "find_links", "label": "after_delete", "by": "original",
             "result": [str(l) for l in after_find_orig],
             "comment": "Link from original after deletion"},
            {"op": "find_links", "label": "after_delete", "by": "copy",
             "result": [str(l) for l in after_find_copy],
             "comment": "Link from copy - does transclusion preserve findability?"}
        ]
    }


def scenario_search_type_filter_with_removed_endpoints(session):
    """Test find_links() with type filter when endpoints are removed.

    Creates links of different types, removes endpoints, tests if
    type filtering still works correctly.
    """
    # Create documents
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Jump Quote Footnote text"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content here"])

    # Create links of different types
    jump_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 4))]))  # "Jump"
    quote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 6), Offset(0, 5))]))  # "Quote"
    footnote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 12), Offset(0, 8))]))  # "Footnote"
    common_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))

    jump_link = session.create_link(source_opened, jump_source, common_target, SpecSet([JUMP_TYPE]))
    quote_link = session.create_link(source_opened, quote_source, common_target, SpecSet([QUOTE_TYPE]))
    footnote_link = session.create_link(source_opened, footnote_source, common_target, SpecSet([FOOTNOTE_TYPE]))

    # Search with type filters BEFORE deletion
    source_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))]))

    before_all = session.find_links(source_search)
    before_jump = session.find_links(source_search, NOSPECS, SpecSet([JUMP_TYPE]))
    before_quote = session.find_links(source_search, NOSPECS, SpecSet([QUOTE_TYPE]))
    before_footnote = session.find_links(source_search, NOSPECS, SpecSet([FOOTNOTE_TYPE]))

    # Delete "Quote " (the quote link source)
    session.remove(source_opened, Span(Address(1, 6), Offset(0, 6)))

    # Get updated contents
    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(
        SpecSet(VSpec(source_opened, list(vspanset.spans)))
    )

    # Search with type filters AFTER deletion
    after_all = session.find_links(source_search)
    after_jump = session.find_links(source_search, NOSPECS, SpecSet([JUMP_TYPE]))
    after_quote = session.find_links(source_search, NOSPECS, SpecSet([QUOTE_TYPE]))
    after_footnote = session.find_links(source_search, NOSPECS, SpecSet([FOOTNOTE_TYPE]))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "search_type_filter_with_removed_endpoints",
        "description": "Test find_links() with type filter when some endpoints are removed",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Jump Quote Footnote text"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content here"},
            {"op": "create_link", "type": "JUMP", "source": "Jump",
             "result": str(jump_link)},
            {"op": "create_link", "type": "QUOTE", "source": "Quote",
             "result": str(quote_link)},
            {"op": "create_link", "type": "FOOTNOTE", "source": "Footnote",
             "result": str(footnote_link)},
            {"op": "find_links", "label": "before_delete", "filter": "all",
             "result": [str(l) for l in before_all]},
            {"op": "find_links", "label": "before_delete", "filter": "JUMP",
             "result": [str(l) for l in before_jump]},
            {"op": "find_links", "label": "before_delete", "filter": "QUOTE",
             "result": [str(l) for l in before_quote]},
            {"op": "find_links", "label": "before_delete", "filter": "FOOTNOTE",
             "result": [str(l) for l in before_footnote]},
            {"op": "delete", "doc": "source", "span": "Quote ",
             "comment": "Delete quote link source only"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": contents_to_list(after_contents)},
            {"op": "find_links", "label": "after_delete", "filter": "all",
             "result": [str(l) for l in after_all],
             "comment": "Should find 2 or 3 links?"},
            {"op": "find_links", "label": "after_delete", "filter": "JUMP",
             "result": [str(l) for l in after_jump]},
            {"op": "find_links", "label": "after_delete", "filter": "QUOTE",
             "result": [str(l) for l in after_quote],
             "comment": "Quote source deleted - findable?"},
            {"op": "find_links", "label": "after_delete", "filter": "FOOTNOTE",
             "result": [str(l) for l in after_footnote]}
        ]
    }


SCENARIOS = [
    # Link search after endpoint removal
    ("links", "search_by_source_after_source_removed", scenario_search_by_source_after_source_removed),
    ("links", "search_by_target_after_source_removed", scenario_search_by_target_after_source_removed),
    ("links", "search_by_source_after_target_removed", scenario_search_by_source_after_target_removed),
    ("links", "search_by_both_endpoints_one_removed", scenario_search_by_both_endpoints_one_removed),
    ("links", "search_partial_source_removal", scenario_search_partial_source_removal),
    ("links", "search_multiple_links_selective_removal", scenario_search_multiple_links_selective_removal),
    ("links", "search_spanning_deleted_boundary", scenario_search_spanning_deleted_boundary),
    ("links", "search_after_vcopy_source_deleted", scenario_search_after_vcopy_source_deleted),
    ("links", "search_type_filter_with_removed_endpoints", scenario_search_type_filter_with_removed_endpoints),
]
