"""Complex interaction scenarios combining links, versions, and transclusion."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_transclude_linked_content(session):
    """Transclude content that has a link attached, check if link is discoverable.

    If content has a link, and we vcopy it to another document, can the
    new document find the link? This tests whether links follow content
    through transclusion.
    """
    # Create source document with content
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for details"])

    # Create link target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Detail information"])

    # Create link on "here" in source
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(source_opened)

    # Create a third document and vcopy the linked content ("here") to it
    copy_doc = session.create_document()
    copy_opened = session.open_document(copy_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy_opened, Address(1, 1), ["Transcluded: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 7), Offset(0, 4))  # "here"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    copy_vs = session.retrieve_vspanset(copy_opened)
    session.vcopy(copy_opened, copy_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)

    # Get copy contents
    copy_vs2 = session.retrieve_vspanset(copy_opened)
    copy_ss = SpecSet(VSpec(copy_opened, list(copy_vs2.spans)))
    copy_contents = session.retrieve_contents(copy_ss)
    # Handle embedded link addresses in content
    copy_contents = [str(c) if hasattr(c, 'digits') else c for c in copy_contents]

    # Can we find the link from the transcluded content?
    copy_search = SpecSet(VSpec(copy_opened, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_copy = session.find_links(copy_search)

    # Also check original can still find it
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_search = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_source = session.find_links(source_search)
    session.close_document(source_read2)

    session.close_document(copy_opened)

    return {
        "name": "transclude_linked_content",
        "description": "Transclude content with a link, check if link is discoverable from copy",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Click here for details"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Detail information"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "create_document", "doc": "copy", "result": str(copy_doc)},
            {"op": "vcopy", "from": "source", "to": "copy", "text": "here",
             "comment": "Transclude the linked content"},
            {"op": "contents", "doc": "copy", "result": copy_contents},
            {"op": "find_links", "from": "source",
             "result": [str(l) for l in links_from_source],
             "comment": "Original should find the link"},
            {"op": "find_links", "from": "copy",
             "result": [str(l) for l in links_from_copy],
             "comment": "Can transcluded content find the link?"}
        ]
    }


def scenario_link_to_transcluded_then_version(session):
    """Create link to transcluded content, then version the document.

    Doc A transcludes from Doc B. Create a link on the transcluded content.
    Then version Doc A. Can the version find the link?
    """
    # Create source document (will be transcluded from)
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source content to transclude"])
    session.close_document(source_opened)

    # Create doc that transcludes from source
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Prefix: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 14))  # "Source content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    doc_vs = session.retrieve_vspanset(doc_opened)
    session.vcopy(doc_opened, doc_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)

    # Create target for link
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target"])

    # Create link on transcluded content "content" (position 16-22 in doc)
    link_source = SpecSet(VSpec(doc_opened, [Span(Address(1, 16), Offset(0, 7))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_id = session.create_link(doc_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(doc_opened)

    # Create version of doc
    version = session.create_version(doc)

    # Find links from original doc
    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    doc_search = SpecSet(VSpec(doc_read, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_doc = session.find_links(doc_search)

    # Get doc contents (with embedded link)
    doc_vs2 = session.retrieve_vspanset(doc_read)
    doc_ss = SpecSet(VSpec(doc_read, list(doc_vs2.spans)))
    doc_contents = session.retrieve_contents(doc_ss)
    doc_contents = [str(c) if hasattr(c, 'digits') else c for c in doc_contents]
    session.close_document(doc_read)

    # Find links from version
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_search = SpecSet(VSpec(ver_read, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_version = session.find_links(ver_search)

    # Get version contents
    ver_vs = session.retrieve_vspanset(ver_read)
    ver_ss = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    ver_contents = [str(c) if hasattr(c, 'digits') else c for c in ver_contents]
    session.close_document(ver_read)

    # Also check if source (original transcluded-from) can find the link
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_search = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 30))]))
    links_from_source = session.find_links(source_search)
    session.close_document(source_read2)

    return {
        "name": "link_to_transcluded_then_version",
        "description": "Link on transcluded content, then version - can version find link?",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Source content to transclude"},
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "vcopy", "from": "source", "to": "doc", "text": "Source content"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "create_link", "on": "transcluded content", "result": str(link_id)},
            {"op": "create_version", "from": "doc", "result": str(version)},
            {"op": "contents", "doc": "doc", "result": doc_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "find_links", "from": "doc",
             "result": [str(l) for l in links_from_doc],
             "comment": "Original doc should find link"},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_version],
             "comment": "Version should find link (content identity shared)"},
            {"op": "find_links", "from": "source",
             "result": [str(l) for l in links_from_source],
             "comment": "Can original source find link on its transcluded content?"}
        ]
    }


def scenario_version_add_link_check_original(session):
    """Create version, add link to version, check if original can find it.

    Since content identity is shared between original and version,
    if we add a link to content in the version, can the original
    discover that link?
    """
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Shared content here"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target"])

    # Add link to VERSION (not original) on "content" (position 8-14)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    link_source = SpecSet(VSpec(ver_opened, [Span(Address(1, 8), Offset(0, 7))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_id = session.create_link(ver_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
    session.close_document(ver_opened)
    session.close_document(target_opened)

    # Find links from version (should find it - that's where we created it)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_search = SpecSet(VSpec(ver_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_version = session.find_links(ver_search)
    session.close_document(ver_read)

    # Find links from ORIGINAL - can it discover the link added to version?
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_search = SpecSet(VSpec(orig_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_original = session.find_links(orig_search)
    session.close_document(orig_read)

    return {
        "name": "version_add_link_check_original",
        "description": "Add link to version, check if original can discover it",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Shared content here"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "create_link", "on": "version", "source_text": "content",
             "result": str(link_id)},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_version],
             "comment": "Version should find its own link"},
            {"op": "find_links", "from": "original",
             "result": [str(l) for l in links_from_original],
             "comment": "Can original find link added to version? (shared content identity)"}
        ]
    }


def scenario_transitive_link_discovery(session):
    """Test link discovery through transitive content sharing.

    Chain: A transcludes from B, B is version of C, link created on C.
    Can A discover the link?
    """
    # Create C (the root)
    doc_c = session.create_document()
    c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(c_opened, Address(1, 1), ["Original content in C"])
    session.close_document(c_opened)

    # Create B as version of C
    doc_b = session.create_version(doc_c)

    # Create A and transclude from B
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["A prefix: "])

    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs = session.retrieve_vspanset(b_read)
    b_specs = SpecSet(VSpec(b_read, list(b_vs.spans)))
    a_vs = session.retrieve_vspanset(a_opened)
    session.vcopy(a_opened, a_vs.spans[0].end(), b_specs)
    session.close_document(b_read)
    session.close_document(a_opened)

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target"])

    # Create link on C (the root) on "content" (position 10-16)
    c_opened2 = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    link_source = SpecSet(VSpec(c_opened2, [Span(Address(1, 10), Offset(0, 7))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_id = session.create_link(c_opened2, link_source, link_target, SpecSet([JUMP_TYPE]))
    session.close_document(c_opened2)
    session.close_document(target_opened)

    # Get contents of all three
    c_read = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_vs = session.retrieve_vspanset(c_read)
    c_ss = SpecSet(VSpec(c_read, list(c_vs.spans)))
    c_contents = session.retrieve_contents(c_ss)
    c_contents = [str(x) if hasattr(x, 'digits') else x for x in c_contents]

    b_read2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs2 = session.retrieve_vspanset(b_read2)
    b_ss = SpecSet(VSpec(b_read2, list(b_vs2.spans)))
    b_contents = session.retrieve_contents(b_ss)
    b_contents = [str(x) if hasattr(x, 'digits') else x for x in b_contents]

    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_vs2 = session.retrieve_vspanset(a_read)
    a_ss = SpecSet(VSpec(a_read, list(a_vs2.spans)))
    a_contents = session.retrieve_contents(a_ss)
    a_contents = [str(x) if hasattr(x, 'digits') else x for x in a_contents]

    # Find links from each document
    c_search = SpecSet(VSpec(c_read, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_c = session.find_links(c_search)

    b_search = SpecSet(VSpec(b_read2, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_b = session.find_links(b_search)

    a_search = SpecSet(VSpec(a_read, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_a = session.find_links(a_search)

    session.close_document(c_read)
    session.close_document(b_read2)
    session.close_document(a_read)

    return {
        "name": "transitive_link_discovery",
        "description": "A transcludes B, B is version of C, link on C - can A find link?",
        "operations": [
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Original content in C"},
            {"op": "create_version", "from": "C", "result": str(doc_b), "doc": "B"},
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "vcopy", "from": "B", "to": "A"},
            {"op": "create_link", "on": "C", "source_text": "content",
             "result": str(link_id)},
            {"op": "contents", "doc": "C", "result": c_contents},
            {"op": "contents", "doc": "B", "result": b_contents},
            {"op": "contents", "doc": "A", "result": a_contents},
            {"op": "find_links", "from": "C",
             "result": [str(l) for l in links_from_c],
             "comment": "C should find its link"},
            {"op": "find_links", "from": "B",
             "result": [str(l) for l in links_from_b],
             "comment": "B (version of C) should find link"},
            {"op": "find_links", "from": "A",
             "result": [str(l) for l in links_from_a],
             "comment": "A (transcludes from B) should find link transitively"}
        ]
    }


def scenario_link_both_endpoints_transcluded(session):
    """Create a link where both source and target are transcluded content.

    Both the link source and link target come from other documents via vcopy.
    """
    # Create original documents for source and target content
    source_origin = session.create_document()
    so_opened = session.open_document(source_origin, READ_WRITE, CONFLICT_FAIL)
    session.insert(so_opened, Address(1, 1), ["Clickable source text"])
    session.close_document(so_opened)

    target_origin = session.create_document()
    to_opened = session.open_document(target_origin, READ_WRITE, CONFLICT_FAIL)
    session.insert(to_opened, Address(1, 1), ["Target destination text"])
    session.close_document(to_opened)

    # Create link home document that transcludes from both
    link_doc = session.create_document()
    link_opened = session.open_document(link_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(link_opened, Address(1, 1), ["Link doc: "])

    # Transclude "Clickable" from source_origin
    so_read = session.open_document(source_origin, READ_ONLY, CONFLICT_COPY)
    source_copy = SpecSet(VSpec(so_read, [Span(Address(1, 1), Offset(0, 9))]))
    link_vs = session.retrieve_vspanset(link_opened)
    session.vcopy(link_opened, link_vs.spans[0].end(), source_copy)
    session.close_document(so_read)

    # Add separator
    link_vs2 = session.retrieve_vspanset(link_opened)
    session.insert(link_opened, link_vs2.spans[0].end(), [" -> "])

    # Transclude "Target" from target_origin
    to_read = session.open_document(target_origin, READ_ONLY, CONFLICT_COPY)
    target_copy = SpecSet(VSpec(to_read, [Span(Address(1, 1), Offset(0, 6))]))
    link_vs3 = session.retrieve_vspanset(link_opened)
    session.vcopy(link_opened, link_vs3.spans[0].end(), target_copy)
    session.close_document(to_read)

    # Get link_doc contents
    link_vs4 = session.retrieve_vspanset(link_opened)
    link_ss = SpecSet(VSpec(link_opened, list(link_vs4.spans)))
    link_contents = session.retrieve_contents(link_ss)
    link_contents = [str(x) if hasattr(x, 'digits') else x for x in link_contents]

    # Create link from transcluded "Clickable" to transcluded "Target"
    # "Clickable" is at position 11-19, "Target" is at position 24-29
    link_source = SpecSet(VSpec(link_opened, [Span(Address(1, 11), Offset(0, 9))]))
    link_target = SpecSet(VSpec(link_opened, [Span(Address(1, 24), Offset(0, 6))]))
    link_id = session.create_link(link_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
    session.close_document(link_opened)

    # Find links from link_doc
    link_read = session.open_document(link_doc, READ_ONLY, CONFLICT_COPY)
    link_search = SpecSet(VSpec(link_read, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_link_doc = session.find_links(link_search)
    session.close_document(link_read)

    # Can source_origin find the link (since "Clickable" is the source endpoint)?
    so_read2 = session.open_document(source_origin, READ_ONLY, CONFLICT_COPY)
    so_search = SpecSet(VSpec(so_read2, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_source_origin = session.find_links(so_search)
    session.close_document(so_read2)

    # Can target_origin find the link (since "Target" is the target endpoint)?
    to_read2 = session.open_document(target_origin, READ_ONLY, CONFLICT_COPY)
    to_search = SpecSet(VSpec(to_read2, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_target_origin = session.find_links(NOSPECS, to_search)  # search by target
    session.close_document(to_read2)

    return {
        "name": "link_both_endpoints_transcluded",
        "description": "Create link where both source and target are transcluded content",
        "operations": [
            {"op": "create_document", "doc": "source_origin", "result": str(source_origin)},
            {"op": "insert", "doc": "source_origin", "text": "Clickable source text"},
            {"op": "create_document", "doc": "target_origin", "result": str(target_origin)},
            {"op": "insert", "doc": "target_origin", "text": "Target destination text"},
            {"op": "create_document", "doc": "link_doc", "result": str(link_doc)},
            {"op": "vcopy", "from": "source_origin", "to": "link_doc", "text": "Clickable"},
            {"op": "vcopy", "from": "target_origin", "to": "link_doc", "text": "Target"},
            {"op": "contents", "doc": "link_doc", "result": link_contents},
            {"op": "create_link", "source": "Clickable (transcluded)", "target": "Target (transcluded)",
             "result": str(link_id)},
            {"op": "find_links", "from": "link_doc",
             "result": [str(l) for l in links_from_link_doc],
             "comment": "Link doc should find its link"},
            {"op": "find_links", "from": "source_origin",
             "result": [str(l) for l in links_from_source_origin],
             "comment": "Source origin should find link (its content is link source)"},
            {"op": "find_links", "from": "target_origin", "by": "target",
             "result": [str(l) for l in links_from_target_origin],
             "comment": "Target origin should find link by target search"}
        ]
    }


def scenario_version_transcluded_linked_content(session):
    """Complex chain: transclude linked content, then version, then modify.

    Source has linked content. Doc transcludes from source.
    Version doc. Modify version. Check link discovery at each level.
    """
    # Create source with linked content
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with linked text here"])

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target"])

    # Create link on "linked" (position 13-18) in source
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 13), Offset(0, 6))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
    session.close_document(target_opened)
    session.close_document(source_opened)

    # Create doc that transcludes "linked text" from source
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Doc prefix: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 13), Offset(0, 11))  # "linked text"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    doc_vs = session.retrieve_vspanset(doc_opened)
    session.vcopy(doc_opened, doc_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(doc_opened)

    # Create version of doc
    version = session.create_version(doc)

    # Modify version - add suffix
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    ver_vs = session.retrieve_vspanset(ver_opened)
    session.insert(ver_opened, ver_vs.spans[0].end(), [" (version suffix)"])
    session.close_document(ver_opened)

    # Get contents of all
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    s_vs = session.retrieve_vspanset(source_read2)
    s_ss = SpecSet(VSpec(source_read2, list(s_vs.spans)))
    source_contents = session.retrieve_contents(s_ss)
    source_contents = [str(x) if hasattr(x, 'digits') else x for x in source_contents]

    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    d_vs = session.retrieve_vspanset(doc_read)
    d_ss = SpecSet(VSpec(doc_read, list(d_vs.spans)))
    doc_contents = session.retrieve_contents(d_ss)
    doc_contents = [str(x) if hasattr(x, 'digits') else x for x in doc_contents]

    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    v_vs = session.retrieve_vspanset(ver_read)
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))
    ver_contents = session.retrieve_contents(v_ss)
    ver_contents = [str(x) if hasattr(x, 'digits') else x for x in ver_contents]

    # Find links from each level
    s_search = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 30))]))
    links_from_source = session.find_links(s_search)

    d_search = SpecSet(VSpec(doc_read, [Span(Address(1, 1), Offset(0, 30))]))
    links_from_doc = session.find_links(d_search)

    v_search = SpecSet(VSpec(ver_read, [Span(Address(1, 1), Offset(0, 45))]))
    links_from_version = session.find_links(v_search)

    session.close_document(source_read2)
    session.close_document(doc_read)
    session.close_document(ver_read)

    return {
        "name": "version_transcluded_linked_content",
        "description": "Source has link, doc transcludes it, version doc, modify version",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Source with linked text here"},
            {"op": "create_link", "on": "linked", "result": str(link_id)},
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "vcopy", "from": "source", "to": "doc", "text": "linked text"},
            {"op": "create_version", "from": "doc", "result": str(version)},
            {"op": "insert", "doc": "version", "text": " (version suffix)"},
            {"op": "contents", "doc": "source", "result": source_contents},
            {"op": "contents", "doc": "doc", "result": doc_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "find_links", "from": "source",
             "result": [str(l) for l in links_from_source],
             "comment": "Source should find its link"},
            {"op": "find_links", "from": "doc",
             "result": [str(l) for l in links_from_doc],
             "comment": "Doc should find link (transcluded linked content)"},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_version],
             "comment": "Version should find link (version of transcluded linked content)"}
        ]
    }


def scenario_compare_versions_with_different_links(session):
    """Create versions, add different links to each, compare content sharing.

    Original and version share content, but have different links.
    Test that compare_versions works correctly and links don't interfere.
    """
    # Create original
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Shared text with linkable words"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Create two different link targets
    target1 = session.create_document()
    t1_opened = session.open_document(target1, READ_WRITE, CONFLICT_FAIL)
    session.insert(t1_opened, Address(1, 1), ["Target for original"])

    target2 = session.create_document()
    t2_opened = session.open_document(target2, READ_WRITE, CONFLICT_FAIL)
    session.insert(t2_opened, Address(1, 1), ["Target for version"])

    # Add link to ORIGINAL on "Shared" (position 1-6)
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    link1_source = SpecSet(VSpec(orig_opened2, [Span(Address(1, 1), Offset(0, 6))]))
    link1_target = SpecSet(VSpec(t1_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link1 = session.create_link(orig_opened2, link1_source, link1_target, SpecSet([JUMP_TYPE]))
    session.close_document(orig_opened2)

    # Add link to VERSION on "words" (position 27-31)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    link2_source = SpecSet(VSpec(ver_opened, [Span(Address(1, 27), Offset(0, 5))]))
    link2_target = SpecSet(VSpec(t2_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link2 = session.create_link(ver_opened, link2_source, link2_target, SpecSet([JUMP_TYPE]))
    session.close_document(ver_opened)

    session.close_document(t1_opened)
    session.close_document(t2_opened)

    # Compare versions - should still find shared content
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    v_vs = session.retrieve_vspanset(ver_read)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    # Get contents
    orig_contents = session.retrieve_contents(o_ss)
    orig_contents = [str(x) if hasattr(x, 'digits') else x for x in orig_contents]
    ver_contents = session.retrieve_contents(v_ss)
    ver_contents = [str(x) if hasattr(x, 'digits') else x for x in ver_contents]

    # Find links from each
    o_search = SpecSet(VSpec(orig_read, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_orig = session.find_links(o_search)

    v_search = SpecSet(VSpec(ver_read, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_ver = session.find_links(v_search)

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "compare_versions_with_different_links",
        "description": "Original and version have different links, compare content sharing",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Shared text with linkable words"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "create_link", "on": "original", "source_text": "Shared",
             "result": str(link1)},
            {"op": "create_link", "on": "version", "source_text": "words",
             "result": str(link2)},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare", "shared": shared_result,
             "comment": "Should find shared content despite different links"},
            {"op": "find_links", "from": "original",
             "result": [str(l) for l in links_from_orig],
             "comment": "Original's links (may include version's due to shared content)"},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_ver],
             "comment": "Version's links (may include original's due to shared content)"}
        ]
    }


SCENARIOS = [
    ("interactions", "transclude_linked_content", scenario_transclude_linked_content),
    ("interactions", "link_to_transcluded_then_version", scenario_link_to_transcluded_then_version),
    ("interactions", "version_add_link_check_original", scenario_version_add_link_check_original),
    ("interactions", "transitive_link_discovery", scenario_transitive_link_discovery),
    ("interactions", "link_both_endpoints_transcluded", scenario_link_both_endpoints_transcluded),
    ("interactions", "version_transcluded_linked_content", scenario_version_transcluded_linked_content),
    ("interactions", "compare_versions_with_different_links", scenario_compare_versions_with_different_links),
]
