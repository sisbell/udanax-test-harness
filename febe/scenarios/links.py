"""Link creation and query scenarios."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def contents_to_list(contents):
    """Convert retrieve_contents result to JSON-serializable list.

    retrieve_contents can return strings (text) or Address objects (link IDs),
    so we need to convert Address objects to strings.
    """
    result = []
    for item in contents:
        if isinstance(item, Address):
            result.append({"link_id": str(item)})
        else:
            result.append(item)
    return result


def scenario_create_link(session):
    """Create two documents and link them."""
    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source document with link text"])
    source_vspanset = session.retrieve_vspanset(source_opened)

    # Create target document
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document content"])
    target_vspanset = session.retrieve_vspanset(target_opened)

    # Create a link from "link text" (positions 22-30) to target document
    source_span = Span(Address(1, 22), Offset(0, 9))  # "link text"
    source_specs = SpecSet(VSpec(source_opened, [source_span]))

    target_span = Span(Address(1, 1), Offset(0, 23))  # "Target document content"
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    link_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "create_link",
        "description": "Create two documents and link them with a jump link",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "open_document", "doc": str(source_docid), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Source document with link text"},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "open_document", "doc": str(target_docid), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target document content"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)}
        ]
    }


def scenario_find_links(session):
    """Create links and find them."""
    # Create documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document one content"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document two content"])

    # Create link
    source_span = Span(Address(1, 1), Offset(0, 8))  # "Document"
    source_specs = SpecSet(VSpec(opened1, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 8))  # "Document"
    target_specs = SpecSet(VSpec(opened2, [target_span]))

    link_id = session.create_link(opened1, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Find links from doc1
    search_span = Span(Address(1, 1), Offset(0, 20))
    search_specs = SpecSet(VSpec(opened1, [search_span]))
    found_links = session.find_links(search_specs)

    # Follow the link
    target_result = session.follow_link(found_links[0], LINK_TARGET)
    type_result = session.follow_link(found_links[0], LINK_TYPE)

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "find_links",
        "description": "Create links and find them by searching source spans",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document one content"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document two content"},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]},
            {"op": "follow_link",
             "link": str(found_links[0]),
             "end": "target",
             "result": specset_to_list(target_result)},
            {"op": "follow_link",
             "link": str(found_links[0]),
             "end": "type",
             "result": specset_to_list(type_result)}
        ]
    }


def scenario_link_types(session):
    """Create links with different types (quote, footnote, margin)."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Document with multiple link types"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content for all links"])

    # Create different link types
    # Quote link on "Document" (1-8)
    quote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 8))]))
    quote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    quote_link = session.create_link(source_opened, quote_source, quote_target, SpecSet([QUOTE_TYPE]))

    # Footnote link on "multiple" (15-23)
    footnote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 15), Offset(0, 8))]))
    footnote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 8), Offset(0, 7))]))
    footnote_link = session.create_link(source_opened, footnote_source, footnote_target, SpecSet([FOOTNOTE_TYPE]))

    # Margin link on "types" (29-34)
    margin_source = SpecSet(VSpec(source_opened, [Span(Address(1, 29), Offset(0, 5))]))
    margin_target = SpecSet(VSpec(target_opened, [Span(Address(1, 16), Offset(0, 3))]))
    margin_link = session.create_link(source_opened, margin_source, margin_target, SpecSet([MARGIN_TYPE]))

    # Find all links from source
    search_span = Span(Address(1, 1), Offset(0, 40))
    search_specs = SpecSet(VSpec(source_opened, [search_span]))
    found_links = session.find_links(search_specs)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_types",
        "description": "Create links with different types (quote, footnote, margin)",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Document with multiple link types"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target content for all links"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(quote_source),
             "target": specset_to_list(quote_target),
             "type": "quote",
             "result": str(quote_link)},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(footnote_source),
             "target": specset_to_list(footnote_target),
             "type": "footnote",
             "result": str(footnote_link)},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(margin_source),
             "target": specset_to_list(margin_target),
             "type": "margin",
             "result": str(margin_link)},
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]}
        ]
    }


def scenario_multiple_links_same_doc(session):
    """Create multiple links from the same source document."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with links to multiple targets"])

    # Create three target documents
    targets = []
    for i in range(3):
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [f"Target document {i+1}"])
        targets.append((doc, opened))

    # Create links to each target
    links = []
    link_ops = []

    # Link "Source" to target 1
    s1 = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))
    t1 = SpecSet(VSpec(targets[0][1], [Span(Address(1, 1), Offset(0, 6))]))
    link1 = session.create_link(source_opened, s1, t1, SpecSet([JUMP_TYPE]))
    links.append(link1)
    link_ops.append({"op": "create_link", "source_text": "Source", "target_doc": 1, "result": str(link1)})

    # Link "links" to target 2
    s2 = SpecSet(VSpec(source_opened, [Span(Address(1, 13), Offset(0, 5))]))
    t2 = SpecSet(VSpec(targets[1][1], [Span(Address(1, 1), Offset(0, 6))]))
    link2 = session.create_link(source_opened, s2, t2, SpecSet([JUMP_TYPE]))
    links.append(link2)
    link_ops.append({"op": "create_link", "source_text": "links", "target_doc": 2, "result": str(link2)})

    # Link "targets" to target 3
    s3 = SpecSet(VSpec(source_opened, [Span(Address(1, 31), Offset(0, 7))]))
    t3 = SpecSet(VSpec(targets[2][1], [Span(Address(1, 1), Offset(0, 6))]))
    link3 = session.create_link(source_opened, s3, t3, SpecSet([JUMP_TYPE]))
    links.append(link3)
    link_ops.append({"op": "create_link", "source_text": "targets", "target_doc": 3, "result": str(link3)})

    # Find all links from source
    search_span = Span(Address(1, 1), Offset(0, 40))
    search_specs = SpecSet(VSpec(source_opened, [search_span]))
    found_links = session.find_links(search_specs)

    # Close all documents
    session.close_document(source_opened)
    for _, opened in targets:
        session.close_document(opened)

    return {
        "name": "multiple_links_same_doc",
        "description": "Create multiple links from the same source document to different targets",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Source with links to multiple targets"},
            {"op": "create_documents", "count": 3, "results": [str(t[0]) for t in targets]},
        ] + link_ops + [
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]}
        ]
    }


def scenario_bidirectional_links(session):
    """Create bidirectional links between two documents.

    Note: Internal links (source and target in same document) ARE supported
    by the backend - see scenario_self_referential_link. This test verifies
    that links can go both directions between documents.
    """
    # Create two documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document one with source text"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document two with target text"])

    # Link from doc1 to doc2: "Document" -> "Document"
    s1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 8))]))
    t1 = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 8))]))
    link1 = session.create_link(opened1, s1, t1, SpecSet([JUMP_TYPE]))

    # Link from doc2 back to doc1: "target" -> "source"
    s2 = SpecSet(VSpec(opened2, [Span(Address(1, 14), Offset(0, 6))]))
    t2 = SpecSet(VSpec(opened1, [Span(Address(1, 14), Offset(0, 6))]))
    link2 = session.create_link(opened2, s2, t2, SpecSet([JUMP_TYPE]))

    # Find links from doc1
    search1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 30))]))
    found_from_doc1 = session.find_links(search1)

    # Find links from doc2
    search2 = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 30))]))
    found_from_doc2 = session.find_links(search2)

    # Follow link1 to target
    link1_target = session.follow_link(link1, LINK_TARGET)

    # Follow link2 to target (back to doc1)
    link2_target = session.follow_link(link2, LINK_TARGET)

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "bidirectional_links",
        "description": "Create bidirectional links between two documents (doc1->doc2 and doc2->doc1)",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document one with source text"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document two with target text"},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(s1),
             "target": specset_to_list(t1),
             "type": "jump",
             "result": str(link1),
             "comment": "Link from doc1 to doc2"},
            {"op": "create_link",
             "home_doc": str(opened2),
             "source": specset_to_list(s2),
             "target": specset_to_list(t2),
             "type": "jump",
             "result": str(link2),
             "comment": "Link from doc2 back to doc1"},
            {"op": "find_links",
             "search": specset_to_list(search1),
             "result": [str(l) for l in found_from_doc1],
             "comment": "Links originating from doc1"},
            {"op": "find_links",
             "search": specset_to_list(search2),
             "result": [str(l) for l in found_from_doc2],
             "comment": "Links originating from doc2"},
            {"op": "follow_link",
             "link": str(link1),
             "end": "target",
             "result": specset_to_list(link1_target)},
            {"op": "follow_link",
             "link": str(link2),
             "end": "target",
             "result": specset_to_list(link2_target)}
        ]
    }


def scenario_find_links_by_target(session):
    """Find links by searching target spans instead of source."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Document referencing the glossary"])

    # Create target (glossary) document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Glossary: terms and definitions here"])

    # Create link from source to target
    source_span = Span(Address(1, 21), Offset(0, 8))  # "glossary"
    target_span = Span(Address(1, 1), Offset(0, 8))  # "Glossary"

    source_specs = SpecSet(VSpec(source_opened, [source_span]))
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    link_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Find links by searching the TARGET document (reverse lookup)
    target_search = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 36))]))
    # Use empty source specs, search by target
    found_by_target = session.find_links(NOSPECS, target_search)

    # Follow found link to get source
    if found_by_target:
        source_result = session.follow_link(found_by_target[0], LINK_SOURCE)
        source_contents = session.retrieve_contents(source_result)
    else:
        source_result = NOSPECS
        source_contents = []

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "find_links_by_target",
        "description": "Find links by searching target spans (reverse lookup)",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Document referencing the glossary"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Glossary: terms and definitions here"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "find_links",
             "by": "target",
             "search": specset_to_list(target_search),
             "result": [str(l) for l in found_by_target]},
            {"op": "follow_link",
             "link": str(found_by_target[0]) if found_by_target else "none",
             "end": "source",
             "result": specset_to_list(source_result)},
            {"op": "retrieve_contents",
             "specs": specset_to_list(source_result),
             "result": source_contents}
        ]
    }


def scenario_overlapping_links(session):
    """Create multiple links with overlapping source spans."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["The hypertext pioneer Vannevar Bush described the memex."])

    # Create target document for definitions
    def_doc = session.create_document()
    def_opened = session.open_document(def_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(def_opened, Address(1, 1), ["hypertext: non-linear text. Bush: American engineer. memex: memory extender."])

    # Link "hypertext" to its definition
    link1_source = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 9))]))
    link1_target = SpecSet(VSpec(def_opened, [Span(Address(1, 1), Offset(0, 10))]))
    link1 = session.create_link(opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Link "hypertext pioneer" (overlapping with previous)
    link2_source = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 17))]))
    link2_target = SpecSet(VSpec(def_opened, [Span(Address(1, 1), Offset(0, 30))]))
    link2 = session.create_link(opened, link2_source, link2_target, SpecSet([QUOTE_TYPE]))

    # Link "Vannevar Bush"
    link3_source = SpecSet(VSpec(opened, [Span(Address(1, 23), Offset(0, 13))]))
    link3_target = SpecSet(VSpec(def_opened, [Span(Address(1, 23), Offset(0, 22))]))
    link3 = session.create_link(opened, link3_source, link3_target, SpecSet([JUMP_TYPE]))

    # Link "memex"
    link4_source = SpecSet(VSpec(opened, [Span(Address(1, 51), Offset(0, 5))]))
    link4_target = SpecSet(VSpec(def_opened, [Span(Address(1, 47), Offset(0, 22))]))
    link4 = session.create_link(opened, link4_source, link4_target, SpecSet([JUMP_TYPE]))

    # Find links from "hypertext" region - should get both overlapping links
    hypertext_search = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 9))]))
    found_hypertext = session.find_links(hypertext_search)

    # Find all links from full document
    full_search = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 60))]))
    found_all = session.find_links(full_search)

    session.close_document(opened)
    session.close_document(def_opened)

    return {
        "name": "overlapping_links",
        "description": "Create multiple links with overlapping source spans",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1",
             "text": "The hypertext pioneer Vannevar Bush described the memex."},
            {"op": "create_document", "result": str(def_doc)},
            {"op": "open_document", "doc": str(def_doc), "mode": "read_write", "result": str(def_opened)},
            {"op": "insert", "doc": str(def_opened), "address": "1.1",
             "text": "hypertext: non-linear text. Bush: American engineer. memex: memory extender."},
            {"op": "create_link", "source_text": "hypertext", "type": "jump", "result": str(link1)},
            {"op": "create_link", "source_text": "hypertext pioneer", "type": "quote", "result": str(link2)},
            {"op": "create_link", "source_text": "Vannevar Bush", "type": "jump", "result": str(link3)},
            {"op": "create_link", "source_text": "memex", "type": "jump", "result": str(link4)},
            {"op": "find_links",
             "search_text": "hypertext",
             "result": [str(l) for l in found_hypertext],
             "comment": "Should find both overlapping links"},
            {"op": "find_links",
             "search_text": "full document",
             "result": [str(l) for l in found_all],
             "comment": "Should find all 4 links"}
        ]
    }


def scenario_find_links_by_type(session):
    """Find links filtered by their type."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with jump quote and footnote links"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document for links"])

    # Create links of different types
    # "jump" at position 13-16
    jump_source = SpecSet(VSpec(source_opened, [Span(Address(1, 13), Offset(0, 4))]))
    jump_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    jump_link = session.create_link(source_opened, jump_source, jump_target, SpecSet([JUMP_TYPE]))

    # "quote" at position 18-22
    quote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 18), Offset(0, 5))]))
    quote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 8), Offset(0, 8))]))
    quote_link = session.create_link(source_opened, quote_source, quote_target, SpecSet([QUOTE_TYPE]))

    # "footnote" at position 28-35
    footnote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 28), Offset(0, 8))]))
    footnote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 17), Offset(0, 8))]))
    footnote_link = session.create_link(source_opened, footnote_source, footnote_target, SpecSet([FOOTNOTE_TYPE]))

    # Search the whole document
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 50))]))

    # Find all links (no type filter)
    all_links = session.find_links(full_search)

    # Find only JUMP links
    jump_links = session.find_links(full_search, NOSPECS, SpecSet([JUMP_TYPE]))

    # Find only QUOTE links
    quote_links = session.find_links(full_search, NOSPECS, SpecSet([QUOTE_TYPE]))

    # Find only FOOTNOTE links
    footnote_links = session.find_links(full_search, NOSPECS, SpecSet([FOOTNOTE_TYPE]))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "find_links_by_type",
        "description": "Find links filtered by their type",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1",
             "text": "Source with jump quote and footnote links"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1",
             "text": "Target document for links"},
            {"op": "create_link", "source_text": "jump", "type": "jump", "result": str(jump_link)},
            {"op": "create_link", "source_text": "quote", "type": "quote", "result": str(quote_link)},
            {"op": "create_link", "source_text": "footnote", "type": "footnote", "result": str(footnote_link)},
            {"op": "find_links", "filter": "none",
             "result": [str(l) for l in all_links],
             "comment": "All 3 links"},
            {"op": "find_links", "filter": "jump",
             "result": [str(l) for l in jump_links],
             "comment": "Only jump links"},
            {"op": "find_links", "filter": "quote",
             "result": [str(l) for l in quote_links],
             "comment": "Only quote links"},
            {"op": "find_links", "filter": "footnote",
             "result": [str(l) for l in footnote_links],
             "comment": "Only footnote links"}
        ]
    }


def scenario_follow_link(session):
    """Follow a link to retrieve its destination content."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["See the reference for more info"])

    # Create target document with detailed content
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Reference: This is the detailed explanation."])

    # Create a link from "reference" to the explanation
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 9), Offset(0, 9))]))  # "reference"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 12), Offset(0, 32))]))  # explanation
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Follow the link to get the target
    target_content = session.follow_link(link_id, LINK_TARGET)

    # Retrieve the actual text at the target
    target_text = session.retrieve_contents(target_content)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "follow_link",
        "description": "Follow a link to retrieve its destination content",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "See the reference for more info"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1",
             "text": "Reference: This is the detailed explanation."},
            {"op": "create_link", "source_text": "reference", "type": "jump", "result": str(link_id)},
            {"op": "follow_link", "link": str(link_id), "end": "target",
             "result": specset_to_list(target_content)},
            {"op": "retrieve_contents", "result": target_text,
             "comment": "The actual text at the link destination"}
        ]
    }


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


def scenario_self_referential_link(session):
    """Test creating a link within the same document (self-referential).

    The backend reportedly does not support internal links where source and target
    are in the same document. This test documents the actual behavior.
    """
    # Create a single document
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["See the glossary section below. Glossary: terms defined here."])
    # "glossary" at 9-16, "Glossary" at 33-40

    # Try to create a link from "glossary" to "Glossary" within same document
    link_source = SpecSet(VSpec(opened, [Span(Address(1, 9), Offset(0, 8))]))  # "glossary"
    link_target = SpecSet(VSpec(opened, [Span(Address(1, 33), Offset(0, 8))]))  # "Glossary"

    try:
        link_id = session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))
        link_created = True
        error_msg = None

        # If it worked, try to follow it
        target_result = session.follow_link(link_id, LINK_TARGET)
        target_text = session.retrieve_contents(target_result)

        source_result = session.follow_link(link_id, LINK_SOURCE)
        source_text = session.retrieve_contents(source_result)
    except Exception as e:
        link_created = False
        link_id = None
        error_msg = str(e)
        target_text = []
        source_text = []

    session.close_document(opened)

    return {
        "name": "self_referential_link",
        "description": "Test creating a link within the same document (self-referential)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1",
             "text": "See the glossary section below. Glossary: terms defined here."},
            {"op": "create_link",
             "home_doc": str(opened),
             "source_text": "glossary",
             "target_text": "Glossary",
             "same_document": True,
             "type": "jump",
             "result": str(link_id) if link_id else None,
             "success": link_created,
             "error": error_msg,
             "comment": "Internal link - source and target in same document"},
            {"op": "follow_link",
             "link": str(link_id) if link_id else "none",
             "end": "target",
             "result": target_text} if link_created else {"op": "skipped", "reason": "link creation failed"},
            {"op": "follow_link",
             "link": str(link_id) if link_id else "none",
             "end": "source",
             "result": source_text} if link_created else {"op": "skipped", "reason": "link creation failed"}
        ]
    }


def scenario_link_chain(session):
    """Test link chains where a target document is also a source for another link.

    Creates A -> B -> C chain and tests following the entire chain.
    """
    # Create document A (starting point)
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Start here to follow the chain"])

    # Create document B (middle - both target and source)
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Middle document with next link"])

    # Create document C (end of chain)
    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Final destination reached"])

    # Link A -> B: "here" in A links to "Middle" in B
    link_ab_source = SpecSet(VSpec(opened_a, [Span(Address(1, 7), Offset(0, 4))]))  # "here"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 6))]))  # "Middle"
    link_ab = session.create_link(opened_a, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # Link B -> C: "next" in B links to "Final" in C
    link_bc_source = SpecSet(VSpec(opened_b, [Span(Address(1, 22), Offset(0, 4))]))  # "next"
    link_bc_target = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 5))]))  # "Final"
    link_bc = session.create_link(opened_b, link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # Follow link A -> B
    target_b = session.follow_link(link_ab, LINK_TARGET)
    target_b_text = session.retrieve_contents(target_b)

    # Find links from document B (should find link B -> C)
    search_b = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_b = session.find_links(search_b)

    # Follow the chain: if we found links from B, follow them
    if links_from_b:
        target_c = session.follow_link(links_from_b[0], LINK_TARGET)
        target_c_text = session.retrieve_contents(target_c)
    else:
        target_c_text = ["No links found from B"]

    # Also verify B is target of link from A AND source of link to C
    # Find links where B is target (reverse lookup)
    search_b_as_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 35))]))
    links_to_b = session.find_links(NOSPECS, search_b_as_target)

    session.close_document(opened_a)
    session.close_document(opened_b)
    session.close_document(opened_c)

    return {
        "name": "link_chain",
        "description": "Test link chains: A -> B -> C where B is both target and source",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Start here to follow the chain"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Middle document with next link"},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Final destination reached"},
            {"op": "create_link",
             "from": "A", "to": "B",
             "source_text": "here", "target_text": "Middle",
             "result": str(link_ab)},
            {"op": "create_link",
             "from": "B", "to": "C",
             "source_text": "next", "target_text": "Final",
             "result": str(link_bc)},
            {"op": "follow_link",
             "link": str(link_ab),
             "end": "target",
             "result": target_b_text,
             "comment": "Following A->B should give 'Middle'"},
            {"op": "find_links",
             "search_doc": "B",
             "result": [str(l) for l in links_from_b],
             "comment": "Find links originating from B (should find B->C)"},
            {"op": "follow_link",
             "link": str(links_from_b[0]) if links_from_b else "none",
             "end": "target",
             "result": target_c_text,
             "comment": "Following B->C should give 'Final'"},
            {"op": "find_links",
             "by": "target",
             "search_doc": "B",
             "result": [str(l) for l in links_to_b],
             "comment": "Find links targeting B (should find A->B)"}
        ]
    }


def scenario_overlapping_links_different_targets(session):
    """Test overlapping links on same content pointing to different targets.

    Multiple links with overlapping source spans but different target documents.
    """
    # Create source document with a term that has multiple meanings
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["The bank can refer to a financial institution or a river bank."])
    # First "bank" at 5-8, second "bank" at 55-58

    # Create target documents for different meanings
    finance_doc = session.create_document()
    finance_opened = session.open_document(finance_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(finance_opened, Address(1, 1), ["Financial institution: accepts deposits, makes loans."])

    geography_doc = session.create_document()
    geography_opened = session.open_document(geography_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(geography_opened, Address(1, 1), ["River bank: the land alongside a river."])

    # Create link from first "bank" to financial definition
    link1_source = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))  # first "bank"
    link1_target = SpecSet(VSpec(finance_opened, [Span(Address(1, 1), Offset(0, 21))]))  # "Financial institution"
    link1 = session.create_link(source_opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Create link from SAME first "bank" to geography definition (overlapping!)
    link2_source = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))  # same "bank"
    link2_target = SpecSet(VSpec(geography_opened, [Span(Address(1, 1), Offset(0, 10))]))  # "River bank"
    link2 = session.create_link(source_opened, link2_source, link2_target, SpecSet([QUOTE_TYPE]))

    # Create link from second "bank" (river bank context) to geography
    link3_source = SpecSet(VSpec(source_opened, [Span(Address(1, 55), Offset(0, 4))]))  # second "bank"
    link3_target = SpecSet(VSpec(geography_opened, [Span(Address(1, 1), Offset(0, 10))]))  # "River bank"
    link3 = session.create_link(source_opened, link3_source, link3_target, SpecSet([JUMP_TYPE]))

    # Find links from the first "bank" - should find BOTH link1 and link2
    first_bank_search = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))
    links_from_first_bank = session.find_links(first_bank_search)

    # Follow each link and compare
    link1_dest = session.follow_link(link1, LINK_TARGET)
    link1_text = session.retrieve_contents(link1_dest)

    link2_dest = session.follow_link(link2, LINK_TARGET)
    link2_text = session.retrieve_contents(link2_dest)

    # Find all links from document
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 65))]))
    all_links = session.find_links(full_search)

    session.close_document(source_opened)
    session.close_document(finance_opened)
    session.close_document(geography_opened)

    return {
        "name": "overlapping_links_different_targets",
        "description": "Test overlapping links on same content pointing to different targets",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source",
             "text": "The bank can refer to a financial institution or a river bank."},
            {"op": "create_document", "doc": "finance", "result": str(finance_doc)},
            {"op": "insert", "doc": "finance",
             "text": "Financial institution: accepts deposits, makes loans."},
            {"op": "create_document", "doc": "geography", "result": str(geography_doc)},
            {"op": "insert", "doc": "geography",
             "text": "River bank: the land alongside a river."},
            {"op": "create_link",
             "source_text": "bank (first)",
             "target_text": "Financial institution",
             "type": "jump",
             "result": str(link1)},
            {"op": "create_link",
             "source_text": "bank (first, same span)",
             "target_text": "River bank",
             "type": "quote",
             "result": str(link2),
             "comment": "Same source span as link1, different target and type"},
            {"op": "create_link",
             "source_text": "bank (second)",
             "target_text": "River bank",
             "type": "jump",
             "result": str(link3)},
            {"op": "find_links",
             "search_text": "first 'bank'",
             "result": [str(l) for l in links_from_first_bank],
             "comment": "Should find both link1 and link2 (overlapping sources)"},
            {"op": "follow_link",
             "link": str(link1),
             "end": "target",
             "result": link1_text,
             "comment": "Link1 should lead to finance definition"},
            {"op": "follow_link",
             "link": str(link2),
             "end": "target",
             "result": link2_text,
             "comment": "Link2 should lead to geography definition"},
            {"op": "find_links",
             "search_text": "full document",
             "result": [str(l) for l in all_links],
             "comment": "Should find all 3 links"}
        ]
    }


def scenario_link_chain_three_hops(session):
    """Test a longer link chain with 3 hops: A -> B -> C -> D.

    This tests programmatic link traversal and chain discovery.
    """
    # Create four documents
    docs = []
    handles = []
    texts = [
        "Document A: start your journey here",
        "Document B: continue to the next stop",
        "Document C: almost at the destination",
        "Document D: you have reached the end"
    ]

    for i, text in enumerate(texts):
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [text])
        docs.append(doc)
        handles.append(opened)

    # Create link chain: A->B, B->C, C->D
    # A: "journey" (25-32) -> B: "Document" (1-8)
    link_ab_source = SpecSet(VSpec(handles[0], [Span(Address(1, 25), Offset(0, 7))]))
    link_ab_target = SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 8))]))
    link_ab = session.create_link(handles[0], link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # B: "next" (25-28) -> C: "Document" (1-8)
    link_bc_source = SpecSet(VSpec(handles[1], [Span(Address(1, 25), Offset(0, 4))]))
    link_bc_target = SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 8))]))
    link_bc = session.create_link(handles[1], link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # C: "destination" (22-32) -> D: "Document" (1-8)
    link_cd_source = SpecSet(VSpec(handles[2], [Span(Address(1, 22), Offset(0, 11))]))
    link_cd_target = SpecSet(VSpec(handles[3], [Span(Address(1, 1), Offset(0, 8))]))
    link_cd = session.create_link(handles[2], link_cd_source, link_cd_target, SpecSet([JUMP_TYPE]))

    # Follow the entire chain
    chain_results = []

    # Start at A, find link to B
    search_a = SpecSet(VSpec(handles[0], [Span(Address(1, 1), Offset(0, 40))]))
    links_from_a = session.find_links(search_a)
    chain_results.append({
        "step": "A",
        "links_found": [str(l) for l in links_from_a]
    })

    # Follow to B, find link to C
    if links_from_a:
        target_b = session.follow_link(links_from_a[0], LINK_TARGET)
        # Get the document from target_b specset to search for next link
        search_b = SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 40))]))
        links_from_b = session.find_links(search_b)
        chain_results.append({
            "step": "B",
            "links_found": [str(l) for l in links_from_b]
        })

        # Follow to C, find link to D
        if links_from_b:
            search_c = SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 40))]))
            links_from_c = session.find_links(search_c)
            chain_results.append({
                "step": "C",
                "links_found": [str(l) for l in links_from_c]
            })

            # Follow to D (end of chain)
            if links_from_c:
                target_d = session.follow_link(links_from_c[0], LINK_TARGET)
                target_d_text = session.retrieve_contents(target_d)
                chain_results.append({
                    "step": "D (end)",
                    "content": target_d_text
                })

    # Close all
    for h in handles:
        session.close_document(h)

    return {
        "name": "link_chain_three_hops",
        "description": "Test a longer link chain with 3 hops: A -> B -> C -> D",
        "operations": [
            {"op": "create_documents", "count": 4,
             "results": [str(d) for d in docs]},
            {"op": "insert_all", "texts": texts},
            {"op": "create_link", "from": "A", "to": "B",
             "source_text": "journey", "result": str(link_ab)},
            {"op": "create_link", "from": "B", "to": "C",
             "source_text": "next", "result": str(link_bc)},
            {"op": "create_link", "from": "C", "to": "D",
             "source_text": "destination", "result": str(link_cd)},
            {"op": "traverse_chain",
             "results": chain_results,
             "comment": "Following links A->B->C->D"}
        ]
    }


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
    ("links", "create_link", scenario_create_link),
    ("links", "find_links", scenario_find_links),
    ("links", "link_types", scenario_link_types),
    ("links", "multiple_links_same_doc", scenario_multiple_links_same_doc),
    ("links", "bidirectional_links", scenario_bidirectional_links),
    ("links", "find_links_by_target", scenario_find_links_by_target),
    ("links", "overlapping_links", scenario_overlapping_links),
    ("links", "find_links_by_type", scenario_find_links_by_type),
    ("links", "follow_link", scenario_follow_link),
    # Link survivability tests (Bug 008 - all crash/error currently)
    ("links", "link_survives_source_insert", scenario_link_survives_source_insert),
    ("links", "link_survives_source_delete_adjacent", scenario_link_survives_source_delete_adjacent),
    ("links", "link_when_source_span_deleted", scenario_link_when_source_span_deleted),
    ("links", "link_when_target_span_deleted", scenario_link_when_target_span_deleted),
    ("links", "link_source_partial_delete", scenario_link_source_partial_delete),
    ("links", "link_with_vcopy_source", scenario_link_with_vcopy_source),
    ("links", "link_survives_target_modify", scenario_link_survives_target_modify),
    # Link edge cases
    ("links", "self_referential_link", scenario_self_referential_link),
    ("links", "link_chain", scenario_link_chain),
    ("links", "overlapping_links_different_targets", scenario_overlapping_links_different_targets),
    ("links", "link_chain_three_hops", scenario_link_chain_three_hops),
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
