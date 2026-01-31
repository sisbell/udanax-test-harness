"""Endset retrieval test scenarios.

Tests for retrieve_endsets (FEBE opcode 28) which returns the
source, target, and type specsets of links.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_retrieve_endsets(session):
    """Retrieve the endpoint specsets of a link."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here to navigate"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Destination content"])

    # Create a link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))  # "here"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 11))]))  # "Destination"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve the endsets of the link - use whole doc span
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "retrieve_endsets",
        "description": "Retrieve the endpoint specsets of a link",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Click here to navigate"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Destination content"},
            {"op": "create_link", "source_text": "here", "type": "jump", "result": str(link_id)},
            {"op": "retrieve_endsets", "link": str(link_id),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": specset_to_list(type_specs)}
        ]
    }


def scenario_endsets_after_source_insert(session):
    """Retrieve endsets after inserting text into the source region.

    Tests whether link endsets are updated when the source content grows.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for info"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Link "here" (positions 7-10) to target
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 14))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get endsets before modification - use whole doc span
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    source_before, target_before, type_before = session.retrieve_endsets(doc_span)

    # Insert text INSIDE the source span ("here" -> "right here")
    session.insert(source_opened, Address(1, 7), ["right "])

    # Get endsets after modification
    source_after, target_after, type_after = session.retrieve_endsets(doc_span)

    # Get content to verify
    vspanset = session.retrieve_vspanset(source_opened)
    content = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "endsets_after_source_insert",
        "description": "Retrieve endsets after inserting text into linked source region",
        "operations": [
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "retrieve_endsets", "label": "before",
             "source": specset_to_list(source_before),
             "target": specset_to_list(target_before)},
            {"op": "insert", "doc": "source", "address": "1.7", "text": "right ",
             "comment": "Insert inside link source span"},
            {"op": "retrieve_endsets", "label": "after",
             "source": specset_to_list(source_after),
             "target": specset_to_list(target_after),
             "comment": "Has source span width changed?"},
            {"op": "content", "result": content}
        ]
    }


def scenario_endsets_after_source_delete(session):
    """Retrieve endsets after deleting part of the source region.

    Tests what happens to link endsets when source content shrinks.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click right here for info"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Link "right here" (positions 7-16) to target
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 10))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 14))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get endsets before modification - use whole doc span
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    source_before, target_before, type_before = session.retrieve_endsets(doc_span)

    # Delete "right " from source (positions 7-12)
    session.delete(source_opened, Address(1, 7), Offset(0, 6))

    # Get endsets after modification
    source_after, target_after, type_after = session.retrieve_endsets(doc_span)

    # Get content to verify
    vspanset = session.retrieve_vspanset(source_opened)
    content = session.retrieve_contents(SpecSet(VSpec(source_opened, list(vspanset.spans))))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "endsets_after_source_delete",
        "description": "Retrieve endsets after deleting part of linked source region",
        "operations": [
            {"op": "create_link", "source_text": "right here", "result": str(link_id)},
            {"op": "retrieve_endsets", "label": "before",
             "source": specset_to_list(source_before),
             "target": specset_to_list(target_before)},
            {"op": "delete", "doc": "source", "text": "right ",
             "comment": "Delete part of link source span"},
            {"op": "retrieve_endsets", "label": "after",
             "source": specset_to_list(source_after),
             "target": specset_to_list(target_after),
             "comment": "Has source span shrunk? Or is link broken?"},
            {"op": "content", "result": content}
        ]
    }


def scenario_endsets_multispan_link(session):
    """Create a link with multiple source spans and retrieve endsets.

    Xanadu links can connect multiple non-contiguous spans.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["First word and second word here"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Definition of terms"])

    # Link multiple spans: "First" and "second" both link to target
    span1 = Span(Address(1, 1), Offset(0, 5))   # "First"
    span2 = Span(Address(1, 16), Offset(0, 6))  # "second"
    link_source = SpecSet(VSpec(source_opened, [span1, span2]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 19))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve endsets - use whole doc span
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "endsets_multispan_link",
        "description": "Retrieve endsets of a link with multiple source spans",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "insert", "text": "First word and second word here"},
            {"op": "create_link",
             "source_spans": ["First", "second"],
             "target": "Definition of terms",
             "result": str(link_id)},
            {"op": "retrieve_endsets",
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": specset_to_list(type_specs),
             "comment": "Source should have two spans"}
        ]
    }


def scenario_endsets_after_pivot(session):
    """Retrieve endsets after rearranging content with pivot.

    Tests whether link endsets track content identity through rearrangement.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Link "CD" (positions 3-4) to target
    link_source = SpecSet(VSpec(opened, [Span(Address(1, 3), Offset(0, 2))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get endsets before pivot - use whole doc span
    doc_span = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(1))]))
    source_before, target_before, type_before = session.retrieve_endsets(doc_span)

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Pivot: swap BC and DE -> ADEBC FGH
    # This moves "CD" to a different position
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Get endsets after pivot
    source_after, target_after, type_after = session.retrieve_endsets(doc_span)

    # Try to find the link by searching all content
    all_links = session.find_links(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    session.close_document(opened)
    session.close_document(target_opened)

    return {
        "name": "endsets_after_pivot",
        "description": "Retrieve endsets after rearranging content with pivot",
        "operations": [
            {"op": "insert", "text": "ABCDEFGH"},
            {"op": "create_link", "source_text": "CD", "result": str(link_id)},
            {"op": "retrieve_endsets", "label": "before",
             "source": specset_to_list(source_before)},
            {"op": "content", "before": content_before},
            {"op": "pivot", "description": "Swap regions, moving CD"},
            {"op": "content", "after": content_after},
            {"op": "retrieve_endsets", "label": "after",
             "source": specset_to_list(source_after),
             "comment": "Do endsets track the rearranged content?"},
            {"op": "find_links", "result": [str(l) for l in all_links],
             "comment": "Is the link still discoverable?"}
        ]
    }


def scenario_endsets_transcluded_source(session):
    """Link from transcluded content and retrieve endsets.

    Tests how endsets work when the link source is transcluded content.
    """
    # Create original document with content
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original shared text"])
    session.close_document(orig_opened)

    # Create document that transcludes from original
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Prefix: "])

    # vcopy "shared" from original
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 10), Offset(0, 6))  # "shared"
    copy_specs = SpecSet(VSpec(orig_read, [copy_span]))
    doc_vs = session.retrieve_vspanset(doc_opened)
    session.vcopy(doc_opened, doc_vs.spans[0].end(), copy_specs)
    session.close_document(orig_read)

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Definition of shared"])

    # Create link from the transcluded "shared" to target
    # The transcluded content is at position 9-14 in doc
    link_source = SpecSet(VSpec(doc_opened, [Span(Address(1, 9), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 20))]))
    link_id = session.create_link(doc_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve endsets - use whole doc span
    doc_span = SpecSet(VSpec(doc_opened, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)

    # Also check if link can be found from original document
    orig_read2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    links_from_original = session.find_links(
        SpecSet(VSpec(orig_read2, [Span(Address(1, 10), Offset(0, 6))]))
    )
    session.close_document(orig_read2)

    # Get content to verify
    doc_vs2 = session.retrieve_vspanset(doc_opened)
    doc_content = session.retrieve_contents(SpecSet(VSpec(doc_opened, list(doc_vs2.spans))))

    session.close_document(doc_opened)
    session.close_document(target_opened)

    return {
        "name": "endsets_transcluded_source",
        "description": "Link from transcluded content and retrieve endsets",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "text": "Original shared text"},
            {"op": "vcopy", "from": "original", "text": "shared"},
            {"op": "create_link", "source_text": "shared (transcluded)",
             "result": str(link_id)},
            {"op": "retrieve_endsets",
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "comment": "Endsets of link from transcluded content"},
            {"op": "find_links", "from": "original",
             "result": [str(l) for l in links_from_original],
             "comment": "Can we find link via original document's content identity?"},
            {"op": "content", "doc": str(doc), "result": doc_content}
        ]
    }


def scenario_endsets_after_version(session):
    """Retrieve endsets of link after creating a version.

    Tests whether link endsets are preserved across versioning.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Document with a link here"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Create link from "link" to target
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 17), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 14))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get endsets before versioning - use whole doc span
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    source_before, target_before, type_before = session.retrieve_endsets(doc_span)

    session.close_document(source_opened)
    session.close_document(target_opened)

    # Create version of source document
    version_doc = session.create_version(source_doc)

    # Find links in version
    version_opened = session.open_document(version_doc, READ_ONLY, CONFLICT_COPY)
    version_links = session.find_links(
        SpecSet(VSpec(version_opened, [Span(Address(1, 1), Offset(0, 25))]))
    )

    # Get endsets from version - use whole doc span
    version_doc_span = SpecSet(VSpec(version_opened, [Span(Address(1, 1), Offset(1))]))
    v_source, v_target, v_type = session.retrieve_endsets(version_doc_span)
    version_endsets = {
        "source": specset_to_list(v_source),
        "target": specset_to_list(v_target),
        "type": specset_to_list(v_type)
    }

    session.close_document(version_opened)

    return {
        "name": "endsets_after_version",
        "description": "Retrieve endsets of link after creating a version",
        "operations": [
            {"op": "create_link", "source_text": "link", "result": str(link_id)},
            {"op": "retrieve_endsets", "label": "original",
             "source": specset_to_list(source_before),
             "target": specset_to_list(target_before)},
            {"op": "create_version", "from": str(source_doc), "result": str(version_doc)},
            {"op": "find_links", "in": "version",
             "result": [str(l) for l in version_links],
             "comment": "Are links inherited by versions?"},
            {"op": "retrieve_endsets", "label": "version",
             "result": version_endsets,
             "comment": "Endsets in version (if links exist)"}
        ]
    }


def scenario_endsets_compare_link_ends(session):
    """Compare the source and target endsets to understand their structure.

    Explores the relationship between link endpoints and content identity.
    """
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Source text"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Target text"])

    # Create link
    link_source = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 6))]))  # "Source"
    link_target = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_id = session.create_link(opened1, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve endsets - use whole doc span
    doc_span = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(doc_span)

    # Follow link in both directions
    source_end = session.follow_link(link_id, LINK_SOURCE)
    target_end = session.follow_link(link_id, LINK_TARGET)

    # Retrieve content at each end
    source_content = session.retrieve_contents(source_end) if source_end else None
    target_content = session.retrieve_contents(target_end) if target_end else None

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "endsets_compare_link_ends",
        "description": "Compare source and target endsets structure",
        "operations": [
            {"op": "create_link", "source": "Source", "target": "Target",
             "result": str(link_id)},
            {"op": "retrieve_endsets",
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": specset_to_list(type_specs)},
            {"op": "follow_link", "direction": "source",
             "content": source_content},
            {"op": "follow_link", "direction": "target",
             "content": target_content},
        ]
    }


SCENARIOS = [
    ("endsets", "retrieve_endsets", scenario_retrieve_endsets),
    ("endsets", "endsets_after_source_insert", scenario_endsets_after_source_insert),
    ("endsets", "endsets_after_source_delete", scenario_endsets_after_source_delete),
    ("endsets", "endsets_multispan_link", scenario_endsets_multispan_link),
    ("endsets", "endsets_after_pivot", scenario_endsets_after_pivot),
    ("endsets", "endsets_transcluded_source", scenario_endsets_transcluded_source),
    ("endsets", "endsets_after_version", scenario_endsets_after_version),
    ("endsets", "endsets_compare_link_ends", scenario_endsets_compare_link_ends),
]
