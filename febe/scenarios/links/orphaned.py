"""Orphaned link scenarios - link behavior when content is deleted."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list
from .common import contents_to_list


def scenario_link_permanence_no_delete_operation(session):
    """Demonstrate that links cannot be explicitly deleted (no delete_link operation exists).

    FEBE protocol has no DELETELINK operation. This is by design - Xanadu philosophy
    of permanent storage means links, once created, cannot be deleted.
    """
    # Create two documents and a link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source document content"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document content"])

    # Create a link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link exists and works
    source_result = session.follow_link(link_id, LINK_SOURCE)
    source_text = session.retrieve_contents(source_result)
    target_result = session.follow_link(link_id, LINK_TARGET)
    target_text = session.retrieve_contents(target_result)

    # Note: There is no delete_link() method in client.py because the FEBE protocol
    # has no DELETELINK operation. This is intentional - links are permanent.
    # The only way to "orphan" a link is to delete the content it references.

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_permanence_no_delete_operation",
        "description": "Links cannot be explicitly deleted - no DELETELINK operation exists in FEBE protocol",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source document content"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target document content"},
            {"op": "create_link",
             "source_text": "Source", "target_text": "Target",
             "result": str(link_id)},
            {"op": "follow_link", "link": str(link_id), "end": "source",
             "result": contents_to_list(source_text)},
            {"op": "follow_link", "link": str(link_id), "end": "target",
             "result": contents_to_list(target_text)},
            {"op": "note",
             "message": "No delete_link operation exists - links are permanent by design",
             "xanadu_principle": "permanent_storage"}
        ]
    }


def scenario_orphaned_link_source_all_deleted(session):
    """Test link behavior when ALL content is deleted from the source document.

    When the entire source document content is deleted, the link becomes "orphaned"
    from the source side - find_links won't find it, but follow_link should still work.
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Short"])  # 5 characters

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content here"])

    # Create a link on all of source content
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 5))]))  # "Short"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_source = session.follow_link(link_id, LINK_SOURCE)
    before_source_text = session.retrieve_contents(before_source)
    before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 10))])))

    # Delete ALL content from source document
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 5)))

    # Check document is now empty
    vspanset = session.retrieve_vspanset(source_opened)
    doc_contents = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans)))) if vspanset.spans else []

    # Try to find and follow the link after complete source deletion
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 10))])))

    # Key question: Can we still follow the link?
    try:
        after_source = session.follow_link(link_id, LINK_SOURCE)
        after_source_text = session.retrieve_contents(after_source)
        source_follow_works = True
    except Exception as e:
        after_source_text = [f"Error: {e}"]
        source_follow_works = False

    # Can we still follow to target?
    try:
        after_target = session.follow_link(link_id, LINK_TARGET)
        after_target_text = session.retrieve_contents(after_target)
        target_follow_works = True
    except Exception as e:
        after_target_text = [f"Error: {e}"]
        target_follow_works = False

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "orphaned_link_source_all_deleted",
        "description": "Test link behavior when ALL content is deleted from source document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Short"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content here"},
            {"op": "create_link", "source_text": "Short", "target_text": "Target",
             "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": contents_to_list(before_source_text)},
            {"op": "find_links", "label": "before_delete",
             "result": [str(l) for l in before_find]},
            {"op": "delete_all", "doc": "source",
             "comment": "Delete ALL content from source document"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": contents_to_list(doc_contents),
             "comment": "Source document should now be empty"},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in after_find],
             "comment": "find_links should NOT find the link (no content to match)"},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": contents_to_list(after_source_text),
             "works": source_follow_works,
             "comment": "follow_link should still work but return empty"},
            {"op": "follow_link", "label": "after_delete", "end": "target",
             "result": contents_to_list(after_target_text),
             "works": target_follow_works,
             "comment": "Target endpoint should be unaffected"}
        ]
    }


def scenario_orphaned_link_target_all_deleted(session):
    """Test link behavior when ALL content is deleted from the target document.

    The link should still be findable from source, but following to target returns empty.
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with link text"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Short"])  # 5 characters - will be deleted

    # Create a link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 5))]))  # "Short"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_target = session.follow_link(link_id, LINK_TARGET)
    before_target_text = session.retrieve_contents(before_target)
    before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))])))

    # Delete ALL content from target document
    session.remove(target_opened, Span(Address(1, 1), Offset(0, 5)))

    # Check target is now empty
    vspanset = session.retrieve_vspanset(target_opened)
    target_contents = session.retrieve_contents(SpecSet(VSpec(target_opened, list(vspanset.spans)))) if vspanset.spans else []

    # Can we still find the link from source?
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))])))

    # Can we still follow the link?
    try:
        after_target = session.follow_link(link_id, LINK_TARGET)
        after_target_text = session.retrieve_contents(after_target)
        target_follow_works = True
    except Exception as e:
        after_target_text = [f"Error: {e}"]
        target_follow_works = False

    # Source endpoint should be unaffected
    after_source = session.follow_link(link_id, LINK_SOURCE)
    after_source_text = session.retrieve_contents(after_source)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "orphaned_link_target_all_deleted",
        "description": "Test link behavior when ALL content is deleted from target document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source with link text"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Short"},
            {"op": "create_link", "source_text": "Source", "target_text": "Short",
             "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "target",
             "result": contents_to_list(before_target_text)},
            {"op": "find_links", "label": "before_delete",
             "result": [str(l) for l in before_find]},
            {"op": "delete_all", "doc": "target",
             "comment": "Delete ALL content from target document"},
            {"op": "contents", "doc": "target", "label": "after_delete",
             "result": contents_to_list(target_contents),
             "comment": "Target document should now be empty"},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in after_find],
             "comment": "Link should still be findable from source"},
            {"op": "follow_link", "label": "after_delete", "end": "target",
             "result": contents_to_list(after_target_text),
             "works": target_follow_works,
             "comment": "follow_link to target should work but return empty"},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": contents_to_list(after_source_text),
             "comment": "Source endpoint should be unaffected"}
        ]
    }


def scenario_orphaned_link_both_endpoints_deleted(session):
    """Test link behavior when ALL content is deleted from BOTH source AND target.

    This creates a fully "orphaned" link - both endpoints point to empty content.
    The link still exists and can be followed, but returns empty for both ends.
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["SRC"])  # 3 characters

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["TGT"])  # 3 characters

    # Create a link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 3))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 3))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_source_text = session.retrieve_contents(session.follow_link(link_id, LINK_SOURCE))
    before_target_text = session.retrieve_contents(session.follow_link(link_id, LINK_TARGET))

    # Delete ALL content from both documents
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 3)))
    session.remove(target_opened, Span(Address(1, 1), Offset(0, 3)))

    # Verify both documents are empty
    source_vspanset = session.retrieve_vspanset(source_opened)
    target_vspanset = session.retrieve_vspanset(target_opened)

    # Try to find links - should fail (no content to match in either direction)
    find_from_source = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 10))])))
    find_from_target = session.find_links(NOSPECS, SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 10))])))

    # Try to follow the link
    try:
        after_source = session.follow_link(link_id, LINK_SOURCE)
        after_source_text = session.retrieve_contents(after_source)
        after_target = session.follow_link(link_id, LINK_TARGET)
        after_target_text = session.retrieve_contents(after_target)
        after_type = session.follow_link(link_id, LINK_TYPE)
        after_type_specs = specset_to_list(after_type)
        follow_works = True
    except Exception as e:
        after_source_text = [f"Error: {e}"]
        after_target_text = [f"Error: {e}"]
        after_type_specs = []
        follow_works = False

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "orphaned_link_both_endpoints_deleted",
        "description": "Test link behavior when ALL content is deleted from BOTH source AND target",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "SRC"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "TGT"},
            {"op": "create_link", "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": contents_to_list(before_source_text)},
            {"op": "follow_link", "label": "before_delete", "end": "target",
             "result": contents_to_list(before_target_text)},
            {"op": "delete_all", "doc": "source"},
            {"op": "delete_all", "doc": "target"},
            {"op": "vspanset", "doc": "source",
             "spans": [span_to_dict(s) for s in source_vspanset.spans]},
            {"op": "vspanset", "doc": "target",
             "spans": [span_to_dict(s) for s in target_vspanset.spans]},
            {"op": "find_links", "by": "source",
             "result": [str(l) for l in find_from_source],
             "comment": "Cannot find link - no source content to match"},
            {"op": "find_links", "by": "target",
             "result": [str(l) for l in find_from_target],
             "comment": "Cannot find link - no target content to match"},
            {"op": "follow_link", "end": "source",
             "result": contents_to_list(after_source_text),
             "works": follow_works,
             "comment": "Link still exists - source returns empty"},
            {"op": "follow_link", "end": "target",
             "result": contents_to_list(after_target_text),
             "comment": "Link still exists - target returns empty"},
            {"op": "follow_link", "end": "type",
             "result": after_type_specs,
             "comment": "Link type should still be accessible"}
        ]
    }


def scenario_orphaned_link_discovery_by_link_id(session):
    """Test that orphaned links can still be accessed if you have their link ID.

    Even when find_links() can't discover a link (because the content is deleted),
    the link still exists and can be accessed directly by ID via follow_link().
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Linkable text"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 8))]))  # "Linkable"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Record the link ID - this is our "bookmark" to the link
    saved_link_id = str(link_id)

    # Delete source content to orphan the link
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 13)))

    # Verify link is not findable via find_links
    search_result = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))

    # But we can still access it directly via the link ID
    # (Simulating: user stored link_id in a bookmark, external database, etc.)
    direct_source = session.follow_link(link_id, LINK_SOURCE)
    direct_target = session.follow_link(link_id, LINK_TARGET)
    direct_type = session.follow_link(link_id, LINK_TYPE)

    source_text = session.retrieve_contents(direct_source)
    target_text = session.retrieve_contents(direct_target)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "orphaned_link_discovery_by_link_id",
        "description": "Orphaned links can still be accessed directly by link ID",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Linkable text"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target"},
            {"op": "create_link", "result": saved_link_id,
             "comment": "Save this link ID - it's the only way to access orphaned link later"},
            {"op": "delete_all", "doc": "source",
             "comment": "Delete source content - link becomes orphaned"},
            {"op": "find_links",
             "result": [str(l) for l in search_result],
             "comment": "find_links returns empty - link is not discoverable"},
            {"op": "follow_link_by_id",
             "link_id": saved_link_id,
             "end": "source",
             "result": contents_to_list(source_text),
             "comment": "Direct access via saved link ID still works"},
            {"op": "follow_link_by_id",
             "link_id": saved_link_id,
             "end": "target",
             "result": contents_to_list(target_text),
             "comment": "Target is still accessible"},
            {"op": "follow_link_by_id",
             "link_id": saved_link_id,
             "end": "type",
             "result": specset_to_list(direct_type),
             "comment": "Type is still accessible"}
        ]
    }


def scenario_link_home_document_content_deleted(session):
    """Test what happens when the HOME document's content is deleted.

    Links are stored in their "home document" (the first argument to create_link).
    What happens if all content is deleted from the home document but not the
    source/target documents?
    """
    # Create three documents: home (where link lives), source, target
    home_doc = session.create_document()
    home_opened = session.open_document(home_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(home_opened, Address(1, 1), ["Home document stores the link"])

    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source document content"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document content"])

    # Create a link from source to target, stored in home document
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(home_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works
    before_source_text = contents_to_list(session.retrieve_contents(session.follow_link(link_id, LINK_SOURCE)))
    before_target_text = contents_to_list(session.retrieve_contents(session.follow_link(link_id, LINK_TARGET)))
    before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))])))

    # Delete ALL content from home document (where the link is stored)
    session.remove(home_opened, Span(Address(1, 1), Offset(0, 29)))

    # Verify home is empty
    home_vspanset = session.retrieve_vspanset(home_opened)

    # Key questions:
    # 1. Can we still find the link from source?
    # 2. Can we still follow the link?
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))])))

    try:
        after_source = session.follow_link(link_id, LINK_SOURCE)
        after_source_text = contents_to_list(session.retrieve_contents(after_source))
        after_target = session.follow_link(link_id, LINK_TARGET)
        after_target_text = contents_to_list(session.retrieve_contents(after_target))
        follow_works = True
    except Exception as e:
        after_source_text = [f"Error: {e}"]
        after_target_text = [f"Error: {e}"]
        follow_works = False

    session.close_document(home_opened)
    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_home_document_content_deleted",
        "description": "Test what happens when the link's HOME document content is deleted",
        "operations": [
            {"op": "create_document", "doc": "home", "result": str(home_doc)},
            {"op": "insert", "doc": "home", "text": "Home document stores the link"},
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source document content"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target document content"},
            {"op": "create_link",
             "home_doc": str(home_opened),
             "source_text": "Source", "target_text": "Target",
             "result": str(link_id),
             "comment": "Link stored in home document, spans source and target"},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": before_source_text},
            {"op": "follow_link", "label": "before_delete", "end": "target",
             "result": before_target_text},
            {"op": "find_links", "label": "before_delete",
             "result": [str(l) for l in before_find]},
            {"op": "delete_all", "doc": "home",
             "comment": "Delete ALL content from home document where link is stored"},
            {"op": "vspanset", "doc": "home",
             "spans": [span_to_dict(s) for s in home_vspanset.spans]},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in after_find],
             "comment": "Can link still be found from source?"},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": after_source_text,
             "works": follow_works,
             "comment": "Can link still be followed?"},
            {"op": "follow_link", "label": "after_delete", "end": "target",
             "result": after_target_text,
             "comment": "Does target still work?"}
        ]
    }


def scenario_multiple_orphaned_links_same_content(session):
    """Test multiple links to same content - what happens when that content is deleted.

    Creates several links pointing to the same target, then deletes the target.
    All links become partially orphaned simultaneously.
    """
    # Create source documents (each with its own link to shared target)
    sources = []
    source_handles = []
    for i in range(3):
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [f"Source {i+1} links here"])
        sources.append(doc)
        source_handles.append(opened)

    # Create shared target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Shared target content"])

    # Create links from each source to the shared target
    links = []
    for i, handle in enumerate(source_handles):
        link_source = SpecSet(VSpec(handle, [Span(Address(1, 8 + i), Offset(0, 1))]))  # single char varies
        link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Shared"
        link_id = session.create_link(handle, link_source, link_target, SpecSet([JUMP_TYPE]))
        links.append(link_id)

    # Verify all links work before deletion
    before_targets = []
    for link_id in links:
        target = session.follow_link(link_id, LINK_TARGET)
        text = contents_to_list(session.retrieve_contents(target))
        before_targets.append(text)

    # Delete the shared target content
    session.remove(target_opened, Span(Address(1, 1), Offset(0, 21)))

    # Check all links now point to empty target
    after_targets = []
    for link_id in links:
        target = session.follow_link(link_id, LINK_TARGET)
        text = contents_to_list(session.retrieve_contents(target))
        after_targets.append(text)

    # Source endpoints should still work
    after_sources = []
    for link_id in links:
        source = session.follow_link(link_id, LINK_SOURCE)
        text = contents_to_list(session.retrieve_contents(source))
        after_sources.append(text)

    # Close all
    for handle in source_handles:
        session.close_document(handle)
    session.close_document(target_opened)

    return {
        "name": "multiple_orphaned_links_same_content",
        "description": "Test multiple links to same content - all become orphaned when target deleted",
        "operations": [
            {"op": "create_documents", "count": 3,
             "results": [str(d) for d in sources]},
            {"op": "create_document", "doc": "shared_target", "result": str(target_doc)},
            {"op": "insert", "doc": "shared_target", "text": "Shared target content"},
            {"op": "create_links", "count": 3,
             "results": [str(l) for l in links],
             "comment": "Three links all pointing to same target"},
            {"op": "follow_links_target", "label": "before_delete",
             "results": before_targets,
             "comment": "All links resolve to 'Shared'"},
            {"op": "delete_all", "doc": "shared_target",
             "comment": "Delete shared target - orphans all links at once"},
            {"op": "follow_links_target", "label": "after_delete",
             "results": after_targets,
             "comment": "All links now resolve to empty"},
            {"op": "follow_links_source", "label": "after_delete",
             "results": after_sources,
             "comment": "Source endpoints still work"}
        ]
    }


def scenario_link_retrieval_via_endsets(session):
    """Test using retrieve_endsets to examine orphaned links.

    retrieve_endsets takes a specset and returns the from/to/type sets of any
    links whose endpoints fall within that specset. Can this find orphaned links?
    """
    # Create documents and link
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source text for endset test"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target text"])

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve endsets before deletion
    before_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 30))]))
    before_from, before_to, before_type = session.retrieve_endsets(before_search)

    # Delete source content
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 27)))

    # Try retrieve_endsets on the now-empty document
    after_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 30))]))
    after_from, after_to, after_type = session.retrieve_endsets(after_search)

    # The link still exists - can we get its endsets via the link ID directly?
    link_search = SpecSet(VSpec(link_id, [Span(Address(1, 1), Offset(0, 100))]))
    try:
        link_from, link_to, link_type = session.retrieve_endsets(link_search)
        direct_endsets_work = True
    except Exception as e:
        link_from = link_to = link_type = NOSPECS
        direct_endsets_work = False

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_retrieval_via_endsets",
        "description": "Test using retrieve_endsets to examine orphaned links",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Source text for endset test"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target text"},
            {"op": "create_link", "result": str(link_id)},
            {"op": "retrieve_endsets", "label": "before_delete",
             "search": specset_to_list(before_search),
             "from": specset_to_list(before_from),
             "to": specset_to_list(before_to),
             "type": specset_to_list(before_type)},
            {"op": "delete_all", "doc": "source"},
            {"op": "retrieve_endsets", "label": "after_delete",
             "search": specset_to_list(after_search),
             "from": specset_to_list(after_from),
             "to": specset_to_list(after_to),
             "type": specset_to_list(after_type),
             "comment": "Can retrieve_endsets find orphaned link info?"},
            {"op": "retrieve_endsets", "label": "via_link_id",
             "search": "link address space",
             "from": specset_to_list(link_from),
             "to": specset_to_list(link_to),
             "type": specset_to_list(link_type),
             "works": direct_endsets_work,
             "comment": "Direct query of link address space"}
        ]
    }


SCENARIOS = [
    # Link deletion and orphaned links
    ("links", "link_permanence_no_delete_operation", scenario_link_permanence_no_delete_operation),
    ("links", "orphaned_link_source_all_deleted", scenario_orphaned_link_source_all_deleted),
    ("links", "orphaned_link_target_all_deleted", scenario_orphaned_link_target_all_deleted),
    ("links", "orphaned_link_both_endpoints_deleted", scenario_orphaned_link_both_endpoints_deleted),
    ("links", "orphaned_link_discovery_by_link_id", scenario_orphaned_link_discovery_by_link_id),
    ("links", "link_home_document_content_deleted", scenario_link_home_document_content_deleted),
    ("links", "multiple_orphaned_links_same_content", scenario_multiple_orphaned_links_same_content),
    ("links", "link_retrieval_via_endsets", scenario_link_retrieval_via_endsets),
]
