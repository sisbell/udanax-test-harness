"""Link discovery scenarios - find_links with homedocids filtering."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_find_links_filter_by_homedocid(session):
    """Test find_links filtering by home document ID.

    Links are 'homed' in the document specified as the first argument to create_link.
    The homedocids parameter (4th parameter to find_links) should filter to links
    homed in specific documents.

    NOTE: homedocids must be passed as spans (I-spans), not just addresses.
    Each span covers a range of document IDs in the identity space.

    FINDING: The homedocids filter appears to be ignored by the backend.
    See bugs/015-homedocids-filter-ignored.md
    """
    # Create three documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document one content here"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document two content here"])

    doc3 = session.create_document()
    opened3 = session.open_document(doc3, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened3, Address(1, 1), ["Document three content"])

    # Create link homed in doc1 (doc1 -> doc2)
    link1_source = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 8))]))
    link1_target = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 8))]))
    link1 = session.create_link(opened1, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Create link homed in doc2 (doc2 -> doc3)
    link2_source = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 8))]))
    link2_target = SpecSet(VSpec(opened3, [Span(Address(1, 1), Offset(0, 8))]))
    link2 = session.create_link(opened2, link2_source, link2_target, SpecSet([JUMP_TYPE]))

    # Create another link homed in doc1 (doc1 -> doc3)
    link3_source = SpecSet(VSpec(opened1, [Span(Address(1, 10), Offset(0, 7))]))
    link3_target = SpecSet(VSpec(opened3, [Span(Address(1, 10), Offset(0, 7))]))
    link3 = session.create_link(opened1, link3_source, link3_target, SpecSet([QUOTE_TYPE]))

    # Find all links from doc1 (no homedocids filter)
    search_doc1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 30))]))
    all_from_doc1 = session.find_links(search_doc1)

    # Find links from doc1, but only those homed in doc1
    # homedocids uses spans in the identity space - Span(docid, Offset(0, 1)) covers one doc
    home_span1 = Span(opened1, Offset(0, 1))
    homed_in_doc1 = session.find_links(search_doc1, NOSPECS, NOSPECS, [home_span1])

    # Find links from doc2 (no filter)
    search_doc2 = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 30))]))
    all_from_doc2 = session.find_links(search_doc2)

    # Find links from doc2, but only those homed in doc2
    home_span2 = Span(opened2, Offset(0, 1))
    homed_in_doc2 = session.find_links(search_doc2, NOSPECS, NOSPECS, [home_span2])

    session.close_document(opened1)
    session.close_document(opened2)
    session.close_document(opened3)

    return {
        "name": "find_links_filter_by_homedocid",
        "description": "Test find_links filtering by home document ID",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "text": "Document one content here"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "text": "Document two content here"},
            {"op": "create_document", "result": str(doc3)},
            {"op": "open_document", "doc": str(doc3), "mode": "read_write", "result": str(opened3)},
            {"op": "insert", "doc": str(opened3), "text": "Document three content"},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(link1_source),
             "target": specset_to_list(link1_target),
             "type": "jump",
             "result": str(link1)},
            {"op": "create_link",
             "home_doc": str(opened2),
             "source": specset_to_list(link2_source),
             "target": specset_to_list(link2_target),
             "type": "jump",
             "result": str(link2)},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(link3_source),
             "target": specset_to_list(link3_target),
             "type": "quote",
             "result": str(link3)},
            {"op": "find_links",
             "search": specset_to_list(search_doc1),
             "homedocids": None,
             "result": [str(l) for l in all_from_doc1],
             "note": "All links with source in doc1 (expected: link1, link3)"},
            {"op": "find_links",
             "search": specset_to_list(search_doc1),
             "homedocids": [span_to_dict(home_span1)],
             "result": [str(l) for l in homed_in_doc1],
             "note": "Links with source in doc1 AND homed in doc1 (expected: link1, link3)"},
            {"op": "find_links",
             "search": specset_to_list(search_doc2),
             "homedocids": None,
             "result": [str(l) for l in all_from_doc2],
             "note": "All links with source in doc2 (expected: link1 target, link2 source)"},
            {"op": "find_links",
             "search": specset_to_list(search_doc2),
             "homedocids": [span_to_dict(home_span2)],
             "result": [str(l) for l in homed_in_doc2],
             "note": "Links with source in doc2 AND homed in doc2 (expected: link2 only)"}
        ]
    }


def scenario_find_links_homedocids_multiple(session):
    """Test find_links with multiple home document IDs in the filter.

    When multiple homedocids are specified, links homed in ANY of them should match.

    FINDING: The homedocids filter appears to be ignored by the backend.
    All links are returned regardless of the filter.
    See bugs/015-homedocids-filter-ignored.md
    """
    # Create four documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["First document text"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Second document text"])

    doc3 = session.create_document()
    opened3 = session.open_document(doc3, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened3, Address(1, 1), ["Third document text"])

    doc4 = session.create_document()
    opened4 = session.open_document(doc4, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened4, Address(1, 1), ["Fourth document text"])

    # Create links in different home documents, all pointing to doc4
    # Link homed in doc1
    link1_source = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 5))]))
    link1_target = SpecSet(VSpec(opened4, [Span(Address(1, 1), Offset(0, 6))]))
    link1 = session.create_link(opened1, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Link homed in doc2
    link2_source = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 6))]))
    link2_target = SpecSet(VSpec(opened4, [Span(Address(1, 1), Offset(0, 6))]))
    link2 = session.create_link(opened2, link2_source, link2_target, SpecSet([JUMP_TYPE]))

    # Link homed in doc3
    link3_source = SpecSet(VSpec(opened3, [Span(Address(1, 1), Offset(0, 5))]))
    link3_target = SpecSet(VSpec(opened4, [Span(Address(1, 1), Offset(0, 6))]))
    link3 = session.create_link(opened3, link3_source, link3_target, SpecSet([JUMP_TYPE]))

    # Search doc4's targets to find links pointing to it
    search_target = SpecSet(VSpec(opened4, [Span(Address(1, 1), Offset(0, 25))]))

    # Find all links targeting doc4 (no filter)
    all_links = session.find_links(NOSPECS, search_target)

    # Create home doc spans for filtering (spans in identity space)
    home_span1 = Span(opened1, Offset(0, 1))
    home_span2 = Span(opened2, Offset(0, 1))
    home_span3 = Span(opened3, Offset(0, 1))

    # Find links targeting doc4, homed in doc1 only
    homed_doc1 = session.find_links(NOSPECS, search_target, NOSPECS, [home_span1])

    # Find links targeting doc4, homed in doc1 OR doc2
    homed_doc1_or_doc2 = session.find_links(NOSPECS, search_target, NOSPECS, [home_span1, home_span2])

    # Find links targeting doc4, homed in doc1 OR doc2 OR doc3 (all)
    homed_all_three = session.find_links(NOSPECS, search_target, NOSPECS, [home_span1, home_span2, home_span3])

    session.close_document(opened1)
    session.close_document(opened2)
    session.close_document(opened3)
    session.close_document(opened4)

    return {
        "name": "find_links_homedocids_multiple",
        "description": "Test find_links with multiple home document IDs in filter",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "insert", "doc": str(doc1), "text": "First document text"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "insert", "doc": str(doc2), "text": "Second document text"},
            {"op": "create_document", "result": str(doc3)},
            {"op": "insert", "doc": str(doc3), "text": "Third document text"},
            {"op": "create_document", "result": str(doc4)},
            {"op": "insert", "doc": str(doc4), "text": "Fourth document text"},
            {"op": "create_link",
             "home_doc": str(doc1),
             "note": "doc1 -> doc4",
             "result": str(link1)},
            {"op": "create_link",
             "home_doc": str(doc2),
             "note": "doc2 -> doc4",
             "result": str(link2)},
            {"op": "create_link",
             "home_doc": str(doc3),
             "note": "doc3 -> doc4",
             "result": str(link3)},
            {"op": "find_links",
             "target": specset_to_list(search_target),
             "homedocids": None,
             "result": [str(l) for l in all_links],
             "note": "All links targeting doc4 (expected: 3)"},
            {"op": "find_links",
             "target": specset_to_list(search_target),
             "homedocids": [span_to_dict(home_span1)],
             "result": [str(l) for l in homed_doc1],
             "note": "Links targeting doc4 homed in doc1 only (expected: 1)"},
            {"op": "find_links",
             "target": specset_to_list(search_target),
             "homedocids": [span_to_dict(home_span1), span_to_dict(home_span2)],
             "result": [str(l) for l in homed_doc1_or_doc2],
             "note": "Links targeting doc4 homed in doc1 or doc2 (expected: 2)"},
            {"op": "find_links",
             "target": specset_to_list(search_target),
             "homedocids": [span_to_dict(home_span1), span_to_dict(home_span2), span_to_dict(home_span3)],
             "result": [str(l) for l in homed_all_three],
             "note": "Links targeting doc4 homed in doc1/doc2/doc3 (expected: 3)"}
        ]
    }


def scenario_find_links_homedocids_no_match(session):
    """Test find_links with homedocids that match no links.

    When filtering by a homedocid that has no links homed in it,
    the result should be empty.

    FINDING: The homedocids filter appears to be ignored by the backend.
    Links are found even when the filter specifies documents with no links.
    See bugs/015-homedocids-filter-ignored.md
    """
    # Create three documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Source document content"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Target document content"])

    doc3 = session.create_document()
    opened3 = session.open_document(doc3, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened3, Address(1, 1), ["Uninvolved document"])

    # Create link homed in doc1 (doc1 -> doc2)
    link_source = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 6))]))
    link_target = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 6))]))
    link1 = session.create_link(opened1, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Search from doc1
    search_doc1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 30))]))

    # Find all links (no filter) - should find the link
    all_links = session.find_links(search_doc1)

    # Create home doc spans for filtering (spans in identity space)
    home_span2 = Span(opened2, Offset(0, 1))
    home_span3 = Span(opened3, Offset(0, 1))

    # Filter by doc3 which has no links homed in it
    no_match = session.find_links(search_doc1, NOSPECS, NOSPECS, [home_span3])

    # Filter by doc2 - link targets doc2 but is not homed there
    target_not_home = session.find_links(search_doc1, NOSPECS, NOSPECS, [home_span2])

    session.close_document(opened1)
    session.close_document(opened2)
    session.close_document(opened3)

    return {
        "name": "find_links_homedocids_no_match",
        "description": "Test find_links with homedocids that match no links",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "insert", "doc": str(doc1), "text": "Source document content"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "insert", "doc": str(doc2), "text": "Target document content"},
            {"op": "create_document", "result": str(doc3)},
            {"op": "insert", "doc": str(doc3), "text": "Uninvolved document"},
            {"op": "create_link",
             "home_doc": str(doc1),
             "note": "Link homed in doc1, points to doc2",
             "result": str(link1)},
            {"op": "find_links",
             "search": specset_to_list(search_doc1),
             "homedocids": None,
             "result": [str(l) for l in all_links],
             "note": "All links from doc1 (expected: 1)"},
            {"op": "find_links",
             "search": specset_to_list(search_doc1),
             "homedocids": [span_to_dict(home_span3)],
             "result": [str(l) for l in no_match],
             "note": "Links from doc1 homed in doc3 (expected: 0 - doc3 has no links)"},
            {"op": "find_links",
             "search": specset_to_list(search_doc1),
             "homedocids": [span_to_dict(home_span2)],
             "result": [str(l) for l in target_not_home],
             "note": "Links from doc1 homed in doc2 (expected: 0 - link targets doc2 but homed in doc1)"}
        ]
    }


SCENARIOS = [
    # find_links with homedocids filtering
    ("links", "find_links_filter_by_homedocid", scenario_find_links_filter_by_homedocid),
    ("links", "find_links_homedocids_multiple", scenario_find_links_homedocids_multiple),
    ("links", "find_links_homedocids_no_match", scenario_find_links_homedocids_no_match),
]
