"""Link survival scenarios - how links behave when content changes."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_link_survives_source_insert(session):
    """Test that link survives when text is inserted before the linked span in source."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for more"])
    # "here" is at positions 7-10

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "here" (positions 7-10)
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before modification
    before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))
    before_source = session.follow_link(link_id, LINK_SOURCE)
    before_source_text = session.retrieve_contents(before_source)

    # Insert text BEFORE the linked span
    session.insert(source_opened, Address(1, 1), ["PREFIX: "])
    # Document now: "PREFIX: Click here for more"

    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    # Try to find links after modification
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 30))])))

    # Follow the link to get source endpoint
    after_source = session.follow_link(link_id, LINK_SOURCE)
    after_source_text = session.retrieve_contents(after_source)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_survives_source_insert",
        "description": "Test that link survives when text is inserted before the linked span in source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click here for more"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "find_links", "label": "before_insert",
             "result": [str(l) for l in before_find]},
            {"op": "follow_link", "label": "before_insert", "end": "source",
             "result": before_source_text},
            {"op": "insert", "doc": "source", "address": "1.1", "text": "PREFIX: ",
             "comment": "Insert before linked span"},
            {"op": "contents", "doc": "source", "label": "after_insert",
             "result": after_contents},
            {"op": "find_links", "label": "after_insert",
             "result": [str(l) for l in after_find],
             "comment": "Link should still be findable"},
            {"op": "follow_link", "label": "after_insert", "end": "source",
             "result": after_source_text,
             "comment": "Link source should still resolve to 'here'"}
        ]
    }


def scenario_link_survives_source_delete_adjacent(session):
    """Test that link survives when adjacent (non-linked) text is deleted from source."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["DELETE_ME Click here for more"])
    # "here" is at positions 17-20

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "here" (positions 17-20)
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 17), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_source = session.follow_link(link_id, LINK_SOURCE)
    before_source_text = session.retrieve_contents(before_source)

    # Delete "DELETE_ME " (positions 1-10) - adjacent to but not overlapping link
    session.remove(source_opened, Span(Address(1, 1), Offset(0, 10)))

    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    # Try to find and follow link after deletion
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 25))])))
    after_source = session.follow_link(link_id, LINK_SOURCE)
    after_source_text = session.retrieve_contents(after_source)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_survives_source_delete_adjacent",
        "description": "Test that link survives when adjacent (non-linked) text is deleted from source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "DELETE_ME Click here for more"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": before_source_text},
            {"op": "delete", "doc": "source", "text": "DELETE_ME ",
             "comment": "Delete text adjacent to (not overlapping) link"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": after_contents},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in after_find],
             "comment": "Link should still be findable"},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": after_source_text,
             "comment": "Link source should still resolve to 'here'"}
        ]
    }


def scenario_link_when_source_span_deleted(session):
    """Test link behavior when the linked source span is deleted from the document."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for more info"])
    # "here" is at positions 7-10

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "here"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_source = session.follow_link(link_id, LINK_SOURCE)
    before_source_text = session.retrieve_contents(before_source)

    # Delete "here " (the linked span plus space)
    session.remove(source_opened, Span(Address(1, 7), Offset(0, 5)))
    # Document now: "Click for more info"

    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    # Key question: Does the link still exist? Can we still follow it?
    try:
        after_source = session.follow_link(link_id, LINK_SOURCE)
        after_source_text = session.retrieve_contents(after_source)
        link_survived = True
    except Exception as e:
        after_source = None
        after_source_text = [f"Error: {e}"]
        link_survived = False

    # Can we find links from the modified document?
    after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_when_source_span_deleted",
        "description": "Test link behavior when the linked source span is deleted from the document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click here for more info"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": before_source_text},
            {"op": "delete", "doc": "source", "span": "here ",
             "comment": "Delete the linked span itself"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": after_contents},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": after_source_text,
             "link_survived": link_survived,
             "comment": "Does link still resolve after source span deleted?"},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in after_find],
             "comment": "Can we find the link from the modified document?"}
        ]
    }


def scenario_link_when_target_span_deleted(session):
    """Test link behavior when the linked target span is deleted from the document."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for more"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content here"])
    # "Target" is at positions 1-6

    # Create link from "here" to "Target"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify link works before deletion
    before_target = session.follow_link(link_id, LINK_TARGET)
    before_target_text = session.retrieve_contents(before_target)

    # Delete "Target " from target document
    session.remove(target_opened, Span(Address(1, 1), Offset(0, 7)))
    # Target document now: "content here"

    vspanset = session.retrieve_vspanset(target_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(target_opened, list(vspanset.spans))))

    # Key question: Does the link still resolve? What does it point to?
    try:
        after_target = session.follow_link(link_id, LINK_TARGET)
        after_target_text = session.retrieve_contents(after_target)
        link_survived = True
    except Exception as e:
        after_target = None
        after_target_text = [f"Error: {e}"]
        link_survived = False

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_when_target_span_deleted",
        "description": "Test link behavior when the linked target span is deleted from the document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click here for more"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content here"},
            {"op": "create_link", "source_text": "here", "target_text": "Target",
             "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "target",
             "result": before_target_text},
            {"op": "delete", "doc": "target", "span": "Target ",
             "comment": "Delete the linked target span"},
            {"op": "contents", "doc": "target", "label": "after_delete",
             "result": after_contents},
            {"op": "follow_link", "label": "after_delete", "end": "target",
             "result": after_target_text,
             "link_survived": link_survived,
             "comment": "Does link still resolve after target span deleted?"}
        ]
    }


def scenario_link_source_partial_delete(session):
    """Test link behavior when part of the linked source span is deleted."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click hyperlink for more"])
    # "hyperlink" is at positions 7-15

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link on "hyperlink"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 9))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify before
    before_source = session.follow_link(link_id, LINK_SOURCE)
    before_source_text = session.retrieve_contents(before_source)

    # Delete "hyper" from "hyperlink" (partial deletion of linked span)
    session.remove(source_opened, Span(Address(1, 7), Offset(0, 5)))
    # Document now: "Click link for more"

    vspanset = session.retrieve_vspanset(source_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    # What does the link source point to now?
    try:
        after_source = session.follow_link(link_id, LINK_SOURCE)
        after_source_text = session.retrieve_contents(after_source)
        link_survived = True
    except Exception as e:
        after_source = None
        after_source_text = [f"Error: {e}"]
        link_survived = False

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_source_partial_delete",
        "description": "Test link behavior when part of the linked source span is deleted",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click hyperlink for more"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target content"},
            {"op": "create_link", "source_text": "hyperlink", "result": str(link_id)},
            {"op": "follow_link", "label": "before_delete", "end": "source",
             "result": before_source_text},
            {"op": "delete", "doc": "source", "span": "hyper",
             "comment": "Delete part of linked span (hyper from hyperlink)"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": after_contents},
            {"op": "follow_link", "label": "after_delete", "end": "source",
             "result": after_source_text,
             "link_survived": link_survived,
             "comment": "Link source after partial deletion - still 'hyperlink' or truncated?"}
        ]
    }


def scenario_link_with_vcopy_source(session):
    """Test link behavior when source span is also transcluded to another document."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for details"])

    # Create target document for link
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Detail information"])

    # Create link on "here"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Create a third document and vcopy "here" to it
    copy_doc = session.create_document()
    copy_opened = session.open_document(copy_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy_opened, Address(1, 1), ["Copied: "])

    # vcopy "here" from source to copy_doc
    # Use the existing source_opened handle - can't open same doc twice
    copy_span = Span(Address(1, 7), Offset(0, 4))  # "here"
    copy_specs = SpecSet(VSpec(source_opened, [copy_span]))
    session.vcopy(copy_opened, Address(1, 9), copy_specs)

    copy_vspanset = session.retrieve_vspanset(copy_opened)
    copy_contents = session.retrieve_contents(SpecSet(VSpec(copy_opened, list(copy_vspanset.spans))))

    # Key question: Can we find the link from the transcluded copy?
    # The "here" in copy_doc shares content identity with source
    copy_search = SpecSet(VSpec(copy_opened, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy = session.find_links(copy_search)

    # Note: compare_versions crashes backend when comparing documents with links
    # (separate bug) - the key test is that links can be found from transcluded content

    session.close_document(source_opened)
    session.close_document(target_opened)
    session.close_document(copy_opened)

    return {
        "name": "link_with_vcopy_source",
        "description": "Test link behavior when source span is also transcluded to another document",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Click here for details"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Detail information"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "create_document", "doc": "copy", "result": str(copy_doc)},
            {"op": "insert", "doc": "copy", "text": "Copied: "},
            {"op": "vcopy", "text": "here", "from": "source", "to": "copy"},
            {"op": "contents", "doc": "copy", "result": copy_contents},
            {"op": "find_links", "search_doc": "copy",
             "result": [str(l) for l in links_from_copy],
             "comment": "Can we find links from the transcluded content?"}
        ]
    }


def scenario_link_survives_target_modify(session):
    """Test that link survives when target document is modified (non-linked region)."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Reference this glossary term"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Glossary: Term definition here"])
    # "Glossary" is at positions 1-8

    # Create link from "glossary" to "Glossary"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 16), Offset(0, 8))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 8))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Verify before
    before_target = session.follow_link(link_id, LINK_TARGET)
    before_target_text = session.retrieve_contents(before_target)

    # Modify target document in a NON-linked region
    session.insert(target_opened, Address(1, 11), ["INSERTED "])
    # Target now: "Glossary: INSERTED Term definition here"

    target_vspanset = session.retrieve_vspanset(target_opened)
    after_contents = session.retrieve_contents(SpecSet(VSpec(target_opened, list(target_vspanset.spans))))

    # Link should still work - linked region wasn't touched
    after_target = session.follow_link(link_id, LINK_TARGET)
    after_target_text = session.retrieve_contents(after_target)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_survives_target_modify",
        "description": "Test that link survives when target document is modified (non-linked region)",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Reference this glossary term"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Glossary: Term definition here"},
            {"op": "create_link", "source_text": "glossary", "target_text": "Glossary",
             "result": str(link_id)},
            {"op": "follow_link", "label": "before_modify", "end": "target",
             "result": before_target_text},
            {"op": "insert", "doc": "target", "address": "1.11", "text": "INSERTED ",
             "comment": "Insert in non-linked region"},
            {"op": "contents", "doc": "target", "label": "after_modify",
             "result": after_contents},
            {"op": "follow_link", "label": "after_modify", "end": "target",
             "result": after_target_text,
             "comment": "Link target should still resolve to 'Glossary'"}
        ]
    }


SCENARIOS = [
    # Link survivability tests (Bug 008 - all crash/error currently)
    ("links", "link_survives_source_insert", scenario_link_survives_source_insert),
    ("links", "link_survives_source_delete_adjacent", scenario_link_survives_source_delete_adjacent),
    ("links", "link_when_source_span_deleted", scenario_link_when_source_span_deleted),
    ("links", "link_when_target_span_deleted", scenario_link_when_target_span_deleted),
    ("links", "link_source_partial_delete", scenario_link_source_partial_delete),
    ("links", "link_with_vcopy_source", scenario_link_with_vcopy_source),
    ("links", "link_survives_target_modify", scenario_link_survives_target_modify),
]
