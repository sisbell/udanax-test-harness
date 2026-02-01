"""Partial overlap scenarios - links and transclusion with partial content overlap."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE, NOSPECS
)
from .common import span_to_dict


def scenario_partial_vcopy_of_linked_span(session):
    """Transclude only part of a linked span - link should be discoverable from subset.

    If we vcopy only a subset of a linked span's content identity,
    the link should still be discoverable from the copy (via I-address overlap).
    """
    # Create source document with linked content
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["The important hyperlink text here"])
    # "hyperlink text" is at positions 15-28

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target content"])

    # Create link on "hyperlink text"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 15), Offset(0, 14))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(source_opened)

    # Create copy document and vcopy only "link" (subset of "hyperlink text")
    copy = session.create_document()
    copy_opened = session.open_document(copy, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy_opened, Address(1, 1), ["Partial copy: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    # vcopy "link" from "hyperlink" - positions 20-23 (subset of linked span)
    copy_span = Span(Address(1, 20), Offset(0, 4))  # "link"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    copy_vs = session.retrieve_vspanset(copy_opened)
    session.vcopy(copy_opened, copy_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)

    # Get copy contents
    copy_vs2 = session.retrieve_vspanset(copy_opened)
    copy_ss = SpecSet(VSpec(copy_opened, list(copy_vs2.spans)))
    copy_contents = session.retrieve_contents(copy_ss)
    copy_contents = [str(c) if hasattr(c, 'digits') else c for c in copy_contents]

    # Find links from the partial copy - should find link via I-address overlap
    copy_search = SpecSet(VSpec(copy_opened, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_copy = session.find_links(copy_search)

    # Follow link from copy to see what portion is visible
    # NOTE: retrieve_contents requires the source document to be open
    # We'll reopen it to get the actual text
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)

    link_source_from_copy = None
    if links_from_copy:
        try:
            link_source_specset = session.follow_link(links_from_copy[0], LINK_SOURCE)
            link_source_from_copy = session.retrieve_contents(link_source_specset)
            link_source_from_copy = [str(c) if hasattr(c, 'digits') else c for c in link_source_from_copy]
        except Exception as e:
            link_source_from_copy = [f"Error: {e}"]

    session.close_document(source_read2)

    # Also check original source still finds full link
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_search = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_source = session.find_links(source_search)

    source_link_text = None
    if links_from_source:
        try:
            source_link_specset = session.follow_link(links_from_source[0], LINK_SOURCE)
            source_link_text = session.retrieve_contents(source_link_specset)
            source_link_text = [str(c) if hasattr(c, 'digits') else c for c in source_link_text]
        except Exception as e:
            source_link_text = [f"Error: {e}"]

    session.close_document(source_read2)
    session.close_document(copy_opened)

    return {
        "name": "partial_vcopy_of_linked_span",
        "description": "Transclude subset of linked span - link discoverable from partial copy",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "The important hyperlink text here"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Link target content"},
            {"op": "create_link", "source_text": "hyperlink text", "result": str(link_id)},
            {"op": "create_document", "doc": "copy", "result": str(copy)},
            {"op": "vcopy", "from": "source", "to": "copy", "text": "link",
             "comment": "Transclude only 'link' which is PART of 'hyperlink text'"},
            {"op": "contents", "doc": "copy", "result": copy_contents},
            {"op": "find_links", "from": "copy",
             "result": [str(l) for l in links_from_copy],
             "comment": "Link discoverable from partial copy via I-address overlap"},
            {"op": "follow_link", "from": "copy",
             "result": link_source_from_copy,
             "comment": "follow_link returns full link source (link is immutable entity)"},
            {"op": "find_links", "from": "source",
             "result": [str(l) for l in links_from_source]},
            {"op": "follow_link", "from": "source",
             "result": source_link_text,
             "comment": "From source, full 'hyperlink text' visible"}
        ]
    }


def scenario_link_spanning_multiple_transclusions(session):
    """Create link where source spans content from multiple vcopy origins.

    Combined document has content transcluded from multiple sources.
    Link spans across this combined content. Link should be discoverable
    from each origin document.
    """
    # Create document A with content
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["First part content"])
    session.close_document(a_opened)

    # Create document B with content
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["Second part content"])
    session.close_document(b_opened)

    # Create combined document that transcludes from both
    combined = session.create_document()
    combined_opened = session.open_document(combined, READ_WRITE, CONFLICT_FAIL)

    # Transclude "First" from A
    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_specs = SpecSet(VSpec(a_read, [Span(Address(1, 1), Offset(0, 5))]))  # "First"
    session.vcopy(combined_opened, Address(1, 1), a_specs)
    session.close_document(a_read)

    # Add local separator
    combined_vs = session.retrieve_vspanset(combined_opened)
    session.insert(combined_opened, combined_vs.spans[0].end(), [" and "])

    # Transclude "Second" from B
    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_specs = SpecSet(VSpec(b_read, [Span(Address(1, 1), Offset(0, 6))]))  # "Second"
    combined_vs2 = session.retrieve_vspanset(combined_opened)
    session.vcopy(combined_opened, combined_vs2.spans[0].end(), b_specs)
    session.close_document(b_read)

    # Get combined contents
    combined_vs3 = session.retrieve_vspanset(combined_opened)
    combined_ss = SpecSet(VSpec(combined_opened, list(combined_vs3.spans)))
    combined_contents = session.retrieve_contents(combined_ss)
    combined_contents = [str(c) if hasattr(c, 'digits') else c for c in combined_contents]

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Link target"])

    # Create link spanning "First and Second" in combined
    # This spans: "First" (from A), " and " (local), "Second" (from B)
    link_source = SpecSet(VSpec(combined_opened, [Span(Address(1, 1), Offset(0, 16))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_id = session.create_link(combined_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(combined_opened)

    # Find links from combined
    combined_read = session.open_document(combined, READ_ONLY, CONFLICT_COPY)
    combined_search = SpecSet(VSpec(combined_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_combined = session.find_links(combined_search)
    session.close_document(combined_read)

    # Find links from A - should find link (A's content is part of link source)
    a_read2 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_search = SpecSet(VSpec(a_read2, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_a = session.find_links(a_search)
    session.close_document(a_read2)

    # Find links from B - should find link (B's content is part of link source)
    b_read2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_search = SpecSet(VSpec(b_read2, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_b = session.find_links(b_search)
    session.close_document(b_read2)

    return {
        "name": "link_spanning_multiple_transclusions",
        "description": "Link source spans content from multiple vcopy origins",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "First part content"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Second part content"},
            {"op": "create_document", "doc": "combined", "result": str(combined)},
            {"op": "vcopy", "from": "A", "to": "combined", "text": "First"},
            {"op": "insert", "doc": "combined", "text": " and "},
            {"op": "vcopy", "from": "B", "to": "combined", "text": "Second"},
            {"op": "contents", "doc": "combined", "result": combined_contents},
            {"op": "create_link", "source_text": "First and Second",
             "result": str(link_id),
             "comment": "Link source spans A's content, local text, and B's content"},
            {"op": "find_links", "from": "combined",
             "result": [str(l) for l in links_from_combined]},
            {"op": "find_links", "from": "A",
             "result": [str(l) for l in links_from_a],
             "comment": "Link discoverable from A (its content is part of link source)"},
            {"op": "find_links", "from": "B",
             "result": [str(l) for l in links_from_b],
             "comment": "Link discoverable from B (its content is part of link source)"}
        ]
    }


def scenario_partial_delete_overlaps_link_and_transclusion(session):
    """Delete span that partially overlaps both a link source and a transclusion.

    Source has content with link and transclusion to another doc.
    Delete overlaps the link source and transcluded content.
    Link should shrink, transclusion unaffected (immutable I-space).
    """
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["ABCDEFGHIJ"])
    session.close_document(source_opened)

    # Create copy document - transclude DEFGH
    copy = session.create_document()
    copy_opened = session.open_document(copy, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy_opened, Address(1, 1), ["Copy: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_specs = SpecSet(VSpec(source_read, [Span(Address(1, 4), Offset(0, 5))]))  # "DEFGH"
    copy_vs = session.retrieve_vspanset(copy_opened)
    session.vcopy(copy_opened, copy_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(copy_opened)

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create link on CDEFG in source (overlaps DEFG of transclusion)
    source_opened2 = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    link_source = SpecSet(VSpec(source_opened2, [Span(Address(1, 3), Offset(0, 5))]))  # "CDEFG"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened2, link_source, link_target, SpecSet([JUMP_TYPE]))
    session.close_document(target_opened)

    # Get state before delete
    source_link_before = session.follow_link(link_id, LINK_SOURCE)
    source_link_text_before = session.retrieve_contents(source_link_before)
    source_link_text_before = [str(c) if hasattr(c, 'digits') else c for c in source_link_text_before]

    copy_read = session.open_document(copy, READ_ONLY, CONFLICT_COPY)
    copy_search = SpecSet(VSpec(copy_read, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy_before = session.find_links(copy_search)

    copy_link_text_before = None
    if links_from_copy_before:
        try:
            copy_link_specset = session.follow_link(links_from_copy_before[0], LINK_SOURCE)
            copy_link_text_before = session.retrieve_contents(copy_link_specset)
            copy_link_text_before = [str(c) if hasattr(c, 'digits') else c for c in copy_link_text_before]
        except Exception as e:
            copy_link_text_before = [f"Error: {e}"]
    session.close_document(copy_read)

    # Delete DEF from source - overlaps link (CDEFG) and transclusion (DEFGH)
    session.remove(source_opened2, Span(Address(1, 4), Offset(0, 3)))  # Delete "DEF"

    # Get source contents after delete
    source_vs = session.retrieve_vspanset(source_opened2)
    source_ss = SpecSet(VSpec(source_opened2, list(source_vs.spans)))
    source_after = session.retrieve_contents(source_ss)
    source_after = [str(c) if hasattr(c, 'digits') else c for c in source_after]

    # Get link source from source after delete
    try:
        source_link_after = session.follow_link(link_id, LINK_SOURCE)
        source_link_text_after = session.retrieve_contents(source_link_after)
        source_link_text_after = [str(c) if hasattr(c, 'digits') else c for c in source_link_text_after]
    except Exception as e:
        source_link_text_after = [f"Error: {e}"]

    session.close_document(source_opened2)

    # Get copy contents after source delete - should be unchanged (immutable)
    copy_read2 = session.open_document(copy, READ_ONLY, CONFLICT_COPY)
    copy_vs = session.retrieve_vspanset(copy_read2)
    copy_ss = SpecSet(VSpec(copy_read2, list(copy_vs.spans)))
    copy_after = session.retrieve_contents(copy_ss)
    copy_after = [str(c) if hasattr(c, 'digits') else c for c in copy_after]

    # Get link source from copy after source delete
    # NOTE: Need to reopen source for retrieve_contents since link source is in source doc
    source_read3 = session.open_document(source, READ_ONLY, CONFLICT_COPY)

    copy_search2 = SpecSet(VSpec(copy_read2, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy_after = session.find_links(copy_search2)

    copy_link_text_after = None
    if links_from_copy_after:
        try:
            copy_link_specset = session.follow_link(links_from_copy_after[0], LINK_SOURCE)
            copy_link_text_after = session.retrieve_contents(copy_link_specset)
            copy_link_text_after = [str(c) if hasattr(c, 'digits') else c for c in copy_link_text_after]
        except Exception as e:
            copy_link_text_after = [f"Error: {e}"]

    session.close_document(source_read3)
    session.close_document(copy_read2)

    return {
        "name": "partial_delete_overlaps_link_and_transclusion",
        "description": "Delete overlaps link source and transcluded content",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "ABCDEFGHIJ"},
            {"op": "create_document", "doc": "copy", "result": str(copy)},
            {"op": "vcopy", "from": "source", "to": "copy", "text": "DEFGH"},
            {"op": "create_link", "source_text": "CDEFG", "result": str(link_id),
             "comment": "Link source CDEFG overlaps transclusion DEFGH on DEFG"},
            {"op": "follow_link", "label": "before_delete", "from": "source",
             "result": source_link_text_before},
            {"op": "follow_link", "label": "before_delete", "from": "copy",
             "result": copy_link_text_before,
             "comment": "From copy, see DEFG (overlap of DEFGH and CDEFG)"},
            {"op": "delete", "doc": "source", "text": "DEF",
             "comment": "Delete DEF - overlaps both link and transclusion"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": source_after},
            {"op": "contents", "doc": "copy", "label": "after_delete",
             "result": copy_after,
             "comment": "Copy unaffected - references immutable I-space"},
            {"op": "follow_link", "label": "after_delete", "from": "source",
             "result": source_link_text_after,
             "comment": "Link source shrinks to remaining visible content"},
            {"op": "follow_link", "label": "after_delete", "from": "copy",
             "result": copy_link_text_after,
             "comment": "From copy, still see DEFG (immutable)"}
        ]
    }


def scenario_compare_versions_partial_content_overlap(session):
    """Compare two documents that share some but not all content identity.

    One document transcludes a subset of another. Compare should find
    only the shared portion.
    """
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original text that will be partially shared"])
    session.close_document(orig_opened)

    # Create partial copy - new prefix, transcluded middle, new suffix
    partial = session.create_document()
    partial_opened = session.open_document(partial, READ_WRITE, CONFLICT_FAIL)
    session.insert(partial_opened, Address(1, 1), ["New prefix: "])

    # Transclude "text that will be" from original (positions 10-26)
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 10), Offset(0, 17))  # "text that will be"
    copy_specs = SpecSet(VSpec(orig_read, [copy_span]))
    partial_vs = session.retrieve_vspanset(partial_opened)
    session.vcopy(partial_opened, partial_vs.spans[0].end(), copy_specs)
    session.close_document(orig_read)

    # Add new suffix
    partial_vs2 = session.retrieve_vspanset(partial_opened)
    session.insert(partial_opened, partial_vs2.spans[0].end(), [" with new suffix"])
    session.close_document(partial_opened)

    # Get contents
    orig_read2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vs = session.retrieve_vspanset(orig_read2)
    orig_ss = SpecSet(VSpec(orig_read2, list(orig_vs.spans)))
    orig_contents = session.retrieve_contents(orig_ss)

    partial_read = session.open_document(partial, READ_ONLY, CONFLICT_COPY)
    partial_vs3 = session.retrieve_vspanset(partial_read)
    partial_ss = SpecSet(VSpec(partial_read, list(partial_vs3.spans)))
    partial_contents = session.retrieve_contents(partial_ss)

    # Compare versions
    shared = session.compare_versions(orig_ss, partial_ss)

    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "partial": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(orig_read2)
    session.close_document(partial_read)

    return {
        "name": "compare_versions_partial_content_overlap",
        "description": "Compare documents with partial content identity overlap",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original",
             "text": "Original text that will be partially shared"},
            {"op": "create_document", "doc": "partial", "result": str(partial)},
            {"op": "insert", "doc": "partial", "text": "New prefix: "},
            {"op": "vcopy", "from": "original", "to": "partial",
             "text": "text that will be",
             "comment": "Transclude only middle portion"},
            {"op": "insert", "doc": "partial", "text": " with new suffix"},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "partial", "result": partial_contents},
            {"op": "compare_versions", "result": shared_result,
             "comment": "Only 'text that will be' should have common identity"}
        ]
    }


def scenario_overlapping_transclusions_shared_link(session):
    """Two documents transclude overlapping portions of source - link visible from both.

    Source has linked content. Two copies transclude overlapping but different
    ranges. Link should be discoverable from both, but show different portions.
    """
    # Create origin with content
    origin = session.create_document()
    origin_opened = session.open_document(origin, READ_WRITE, CONFLICT_FAIL)
    session.insert(origin_opened, Address(1, 1), ["ABCDEFGHIJ"])

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create link on DEF in origin
    link_source = SpecSet(VSpec(origin_opened, [Span(Address(1, 4), Offset(0, 3))]))  # "DEF"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(origin_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(origin_opened)

    # Create copy1 - transclude BCDEFG (contains full DEF)
    copy1 = session.create_document()
    copy1_opened = session.open_document(copy1, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy1_opened, Address(1, 1), ["Copy1: "])

    origin_read = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    specs1 = SpecSet(VSpec(origin_read, [Span(Address(1, 2), Offset(0, 6))]))  # "BCDEFG"
    copy1_vs = session.retrieve_vspanset(copy1_opened)
    session.vcopy(copy1_opened, copy1_vs.spans[0].end(), specs1)
    session.close_document(origin_read)
    session.close_document(copy1_opened)

    # Create copy2 - transclude EFGHIJ (contains partial EF of DEF)
    copy2 = session.create_document()
    copy2_opened = session.open_document(copy2, READ_WRITE, CONFLICT_FAIL)
    session.insert(copy2_opened, Address(1, 1), ["Copy2: "])

    origin_read2 = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    specs2 = SpecSet(VSpec(origin_read2, [Span(Address(1, 5), Offset(0, 6))]))  # "EFGHIJ"
    copy2_vs = session.retrieve_vspanset(copy2_opened)
    session.vcopy(copy2_opened, copy2_vs.spans[0].end(), specs2)
    session.close_document(origin_read2)
    session.close_document(copy2_opened)

    # Get contents
    copy1_read = session.open_document(copy1, READ_ONLY, CONFLICT_COPY)
    c1_vs = session.retrieve_vspanset(copy1_read)
    c1_ss = SpecSet(VSpec(copy1_read, list(c1_vs.spans)))
    copy1_contents = session.retrieve_contents(c1_ss)
    copy1_contents = [str(c) if hasattr(c, 'digits') else c for c in copy1_contents]

    copy2_read = session.open_document(copy2, READ_ONLY, CONFLICT_COPY)
    c2_vs = session.retrieve_vspanset(copy2_read)
    c2_ss = SpecSet(VSpec(copy2_read, list(c2_vs.spans)))
    copy2_contents = session.retrieve_contents(c2_ss)
    copy2_contents = [str(c) if hasattr(c, 'digits') else c for c in copy2_contents]

    # Find links from each copy
    c1_search = SpecSet(VSpec(copy1_read, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy1 = session.find_links(c1_search)

    c2_search = SpecSet(VSpec(copy2_read, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy2 = session.find_links(c2_search)

    # Follow link from each copy to see what portion is visible
    # NOTE: retrieve_contents requires the origin document (where link source is) to be open
    origin_read3 = session.open_document(origin, READ_ONLY, CONFLICT_COPY)

    copy1_link_text = None
    if links_from_copy1:
        try:
            c1_link_specset = session.follow_link(links_from_copy1[0], LINK_SOURCE)
            copy1_link_text = session.retrieve_contents(c1_link_specset)
            copy1_link_text = [str(c) if hasattr(c, 'digits') else c for c in copy1_link_text]
        except Exception as e:
            copy1_link_text = [f"Error: {e}"]

    copy2_link_text = None
    if links_from_copy2:
        try:
            c2_link_specset = session.follow_link(links_from_copy2[0], LINK_SOURCE)
            copy2_link_text = session.retrieve_contents(c2_link_specset)
            copy2_link_text = [str(c) if hasattr(c, 'digits') else c for c in copy2_link_text]
        except Exception as e:
            copy2_link_text = [f"Error: {e}"]

    session.close_document(origin_read3)

    # Compare copy1 and copy2 - should share EFG
    shared = session.compare_versions(c1_ss, c2_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "copy1": span_to_dict(span_a.span),
            "copy2": span_to_dict(span_b.span)
        })

    session.close_document(copy1_read)
    session.close_document(copy2_read)

    return {
        "name": "overlapping_transclusions_shared_link",
        "description": "Two docs transclude overlapping portions - link visible from both",
        "operations": [
            {"op": "create_document", "doc": "origin", "result": str(origin)},
            {"op": "insert", "doc": "origin", "text": "ABCDEFGHIJ"},
            {"op": "create_link", "source_text": "DEF", "result": str(link_id)},
            {"op": "create_document", "doc": "copy1", "result": str(copy1)},
            {"op": "vcopy", "from": "origin", "to": "copy1", "text": "BCDEFG",
             "comment": "Copy1 has full DEF"},
            {"op": "create_document", "doc": "copy2", "result": str(copy2)},
            {"op": "vcopy", "from": "origin", "to": "copy2", "text": "EFGHIJ",
             "comment": "Copy2 has partial overlap (EF of DEF)"},
            {"op": "contents", "doc": "copy1", "result": copy1_contents},
            {"op": "contents", "doc": "copy2", "result": copy2_contents},
            {"op": "find_links", "from": "copy1",
             "result": [str(l) for l in links_from_copy1],
             "comment": "Copy1 finds link (has full DEF)"},
            {"op": "find_links", "from": "copy2",
             "result": [str(l) for l in links_from_copy2],
             "comment": "Copy2 finds link (has partial EF)"},
            {"op": "follow_link", "from": "copy1", "result": copy1_link_text,
             "comment": "From copy1, see DEF"},
            {"op": "follow_link", "from": "copy2", "result": copy2_link_text,
             "comment": "From copy2, see only EF (overlap)"},
            {"op": "compare_versions", "docs": ["copy1", "copy2"],
             "result": shared_result,
             "comment": "Copy1 and copy2 share EFG"}
        ]
    }


def scenario_nested_partial_transclusions(session):
    """Chain of transclusions with progressively smaller subsets.

    Origin -> Level1 (subset) -> Level2 (smaller subset)
    Link on origin should be discoverable through the chain with
    progressively smaller visible portions.
    """
    # Create origin
    origin = session.create_document()
    origin_opened = session.open_document(origin, READ_WRITE, CONFLICT_FAIL)
    session.insert(origin_opened, Address(1, 1), ["ABCDEFGHIJKLMNOP"])

    # Create link target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create link on FGHIJK in origin
    link_source = SpecSet(VSpec(origin_opened, [Span(Address(1, 6), Offset(0, 6))]))  # "FGHIJK"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(origin_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(origin_opened)

    # Create level1 - transclude DEFGHIJKLM (larger range containing link source)
    level1 = session.create_document()
    level1_opened = session.open_document(level1, READ_WRITE, CONFLICT_FAIL)

    origin_read = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    specs1 = SpecSet(VSpec(origin_read, [Span(Address(1, 4), Offset(0, 10))]))  # "DEFGHIJKLM"
    session.vcopy(level1_opened, Address(1, 1), specs1)
    session.close_document(origin_read)
    session.close_document(level1_opened)

    # Create level2 - transclude GHIJ from level1 (smaller subset)
    level2 = session.create_document()
    level2_opened = session.open_document(level2, READ_WRITE, CONFLICT_FAIL)

    level1_read = session.open_document(level1, READ_ONLY, CONFLICT_COPY)
    specs2 = SpecSet(VSpec(level1_read, [Span(Address(1, 4), Offset(0, 4))]))  # "GHIJ"
    session.vcopy(level2_opened, Address(1, 1), specs2)
    session.close_document(level1_read)
    session.close_document(level2_opened)

    # Get contents
    origin_read2 = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(origin_read2)
    o_ss = SpecSet(VSpec(origin_read2, list(o_vs.spans)))
    origin_contents = session.retrieve_contents(o_ss)

    level1_read2 = session.open_document(level1, READ_ONLY, CONFLICT_COPY)
    l1_vs = session.retrieve_vspanset(level1_read2)
    l1_ss = SpecSet(VSpec(level1_read2, list(l1_vs.spans)))
    level1_contents = session.retrieve_contents(l1_ss)

    level2_read = session.open_document(level2, READ_ONLY, CONFLICT_COPY)
    l2_vs = session.retrieve_vspanset(level2_read)
    l2_ss = SpecSet(VSpec(level2_read, list(l2_vs.spans)))
    level2_contents = session.retrieve_contents(l2_ss)

    # Find links from each level
    o_search = SpecSet(VSpec(origin_read2, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_origin = session.find_links(o_search)

    l1_search = SpecSet(VSpec(level1_read2, [Span(Address(1, 1), Offset(0, 12))]))
    links_from_level1 = session.find_links(l1_search)

    l2_search = SpecSet(VSpec(level2_read, [Span(Address(1, 1), Offset(0, 6))]))
    links_from_level2 = session.find_links(l2_search)

    # Follow link from each level
    origin_link_text = None
    if links_from_origin:
        try:
            specset = session.follow_link(links_from_origin[0], LINK_SOURCE)
            origin_link_text = session.retrieve_contents(specset)
            origin_link_text = [str(c) if hasattr(c, 'digits') else c for c in origin_link_text]
        except Exception as e:
            origin_link_text = [f"Error: {e}"]

    level1_link_text = None
    if links_from_level1:
        try:
            specset = session.follow_link(links_from_level1[0], LINK_SOURCE)
            level1_link_text = session.retrieve_contents(specset)
            level1_link_text = [str(c) if hasattr(c, 'digits') else c for c in level1_link_text]
        except Exception as e:
            level1_link_text = [f"Error: {e}"]

    level2_link_text = None
    if links_from_level2:
        try:
            specset = session.follow_link(links_from_level2[0], LINK_SOURCE)
            level2_link_text = session.retrieve_contents(specset)
            level2_link_text = [str(c) if hasattr(c, 'digits') else c for c in level2_link_text]
        except Exception as e:
            level2_link_text = [f"Error: {e}"]

    # Compare origin and level2 - should share GHIJ
    shared_o_l2 = session.compare_versions(o_ss, l2_ss)
    shared_result = []
    for span_a, span_b in shared_o_l2:
        shared_result.append({
            "origin": span_to_dict(span_a.span),
            "level2": span_to_dict(span_b.span)
        })

    session.close_document(origin_read2)
    session.close_document(level1_read2)
    session.close_document(level2_read)

    return {
        "name": "nested_partial_transclusions",
        "description": "Chain of transclusions with shrinking subsets",
        "operations": [
            {"op": "create_document", "doc": "origin", "result": str(origin)},
            {"op": "insert", "doc": "origin", "text": "ABCDEFGHIJKLMNOP"},
            {"op": "create_link", "source_text": "FGHIJK", "result": str(link_id)},
            {"op": "create_document", "doc": "level1", "result": str(level1)},
            {"op": "vcopy", "from": "origin", "to": "level1", "text": "DEFGHIJKLM"},
            {"op": "create_document", "doc": "level2", "result": str(level2)},
            {"op": "vcopy", "from": "level1", "to": "level2", "text": "GHIJ"},
            {"op": "contents", "doc": "origin", "result": origin_contents},
            {"op": "contents", "doc": "level1", "result": level1_contents},
            {"op": "contents", "doc": "level2", "result": level2_contents},
            {"op": "find_links", "from": "origin",
             "result": [str(l) for l in links_from_origin]},
            {"op": "find_links", "from": "level1",
             "result": [str(l) for l in links_from_level1],
             "comment": "Level1 has FGHIJK (full link source)"},
            {"op": "find_links", "from": "level2",
             "result": [str(l) for l in links_from_level2],
             "comment": "Level2 has GHIJ (partial overlap with FGHIJK)"},
            {"op": "follow_link", "from": "origin", "result": origin_link_text,
             "comment": "Full link source FGHIJK"},
            {"op": "follow_link", "from": "level1", "result": level1_link_text,
             "comment": "Full link source FGHIJK (contained in DEFGHIJKLM)"},
            {"op": "follow_link", "from": "level2", "result": level2_link_text,
             "comment": "Only GHIJ visible (overlap of GHIJ and FGHIJK)"},
            {"op": "compare_versions", "docs": ["origin", "level2"],
             "result": shared_result,
             "comment": "Only GHIJ shared between origin and level2"}
        ]
    }


def scenario_link_endpoints_shared_origin(session):
    """Link where source and target endpoints share content identity from common origin.

    Both endpoints are transcluded from the same origin document.
    They share overlapping content identity.
    """
    # Create origin with content
    origin = session.create_document()
    origin_opened = session.open_document(origin, READ_WRITE, CONFLICT_FAIL)
    session.insert(origin_opened, Address(1, 1), ["The shared content text here"])
    session.close_document(origin_opened)

    # Create source_doc - transclude "shared content" from origin
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source: "])

    origin_read = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    specs1 = SpecSet(VSpec(origin_read, [Span(Address(1, 5), Offset(0, 14))]))  # "shared content"
    source_vs = session.retrieve_vspanset(source_opened)
    session.vcopy(source_opened, source_vs.spans[0].end(), specs1)
    session.close_document(origin_read)
    session.close_document(source_opened)

    # Create target_doc - transclude "content text" from origin (overlaps on "content")
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target: "])

    origin_read2 = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    specs2 = SpecSet(VSpec(origin_read2, [Span(Address(1, 12), Offset(0, 12))]))  # "content text"
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), specs2)
    session.close_document(origin_read2)
    session.close_document(target_opened)

    # Get contents
    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    s_vs = session.retrieve_vspanset(source_read)
    s_ss = SpecSet(VSpec(source_read, list(s_vs.spans)))
    source_contents = session.retrieve_contents(s_ss)
    source_contents = [str(c) if hasattr(c, 'digits') else c for c in source_contents]

    target_read = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    t_vs = session.retrieve_vspanset(target_read)
    t_ss = SpecSet(VSpec(target_read, list(t_vs.spans)))
    target_contents = session.retrieve_contents(t_ss)
    target_contents = [str(c) if hasattr(c, 'digits') else c for c in target_contents]

    session.close_document(source_read)
    session.close_document(target_read)

    # Create link from source_doc to target_doc
    source_opened2 = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    target_opened2 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)

    # Link source: "shared content" (transcluded), target: "content text" (transcluded)
    link_source = SpecSet(VSpec(source_opened2, [Span(Address(1, 9), Offset(0, 14))]))
    link_target = SpecSet(VSpec(target_opened2, [Span(Address(1, 9), Offset(0, 12))]))
    link_id = session.create_link(source_opened2, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened2)
    session.close_document(source_opened2)

    # Find links from origin - should find the link (shares identity with both endpoints)
    origin_read3 = session.open_document(origin, READ_ONLY, CONFLICT_COPY)
    o_search = SpecSet(VSpec(origin_read3, [Span(Address(1, 1), Offset(0, 30))]))
    links_from_origin = session.find_links(o_search)
    session.close_document(origin_read3)

    # Find links from source_doc
    source_read2 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    s_search = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 25))]))
    links_from_source = session.find_links(s_search)
    session.close_document(source_read2)

    # Compare source and target - should share "content"
    source_read3 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    target_read2 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    s_vs2 = session.retrieve_vspanset(source_read3)
    t_vs2 = session.retrieve_vspanset(target_read2)
    s_ss2 = SpecSet(VSpec(source_read3, list(s_vs2.spans)))
    t_ss2 = SpecSet(VSpec(target_read2, list(t_vs2.spans)))

    shared = session.compare_versions(s_ss2, t_ss2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": span_to_dict(span_a.span),
            "target": span_to_dict(span_b.span)
        })

    session.close_document(source_read3)
    session.close_document(target_read2)

    return {
        "name": "link_endpoints_shared_origin",
        "description": "Link endpoints share content identity from common origin",
        "operations": [
            {"op": "create_document", "doc": "origin", "result": str(origin)},
            {"op": "insert", "doc": "origin", "text": "The shared content text here"},
            {"op": "create_document", "doc": "source_doc", "result": str(source_doc)},
            {"op": "vcopy", "from": "origin", "to": "source_doc", "text": "shared content"},
            {"op": "create_document", "doc": "target_doc", "result": str(target_doc)},
            {"op": "vcopy", "from": "origin", "to": "target_doc", "text": "content text",
             "comment": "Overlaps source on 'content'"},
            {"op": "contents", "doc": "source_doc", "result": source_contents},
            {"op": "contents", "doc": "target_doc", "result": target_contents},
            {"op": "create_link", "source": "shared content", "target": "content text",
             "result": str(link_id),
             "comment": "Both endpoints have 'content' from same origin"},
            {"op": "find_links", "from": "origin",
             "result": [str(l) for l in links_from_origin],
             "comment": "Link discoverable from origin (shares identity with both endpoints)"},
            {"op": "find_links", "from": "source_doc",
             "result": [str(l) for l in links_from_source]},
            {"op": "compare_versions", "docs": ["source_doc", "target_doc"],
             "result": shared_result,
             "comment": "Source and target share 'content' identity"}
        ]
    }


SCENARIOS = [
    ("partial-overlap", "partial_vcopy_of_linked_span", scenario_partial_vcopy_of_linked_span),
    ("partial-overlap", "link_spanning_multiple_transclusions", scenario_link_spanning_multiple_transclusions),
    ("partial-overlap", "partial_delete_overlaps_link_and_transclusion", scenario_partial_delete_overlaps_link_and_transclusion),
    ("partial-overlap", "compare_versions_partial_content_overlap", scenario_compare_versions_partial_content_overlap),
    ("partial-overlap", "overlapping_transclusions_shared_link", scenario_overlapping_transclusions_shared_link),
    ("partial-overlap", "nested_partial_transclusions", scenario_nested_partial_transclusions),
    ("partial-overlap", "link_endpoints_shared_origin", scenario_link_endpoints_shared_origin),
]
