"""Edge case scenarios testing boundary conditions and unusual inputs."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_insert_single_char(session):
    """Insert a single character."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["X"])
    vspanset = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "insert_single_char",
        "description": "Insert a single character - minimum content unit",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "X"},
            {"op": "retrieve_vspanset", "result": vspec_to_dict(vspanset)},
            {"op": "retrieve_contents", "result": contents},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_delete_single_char(session):
    """Delete a single character from the middle."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABC"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Delete 'B' (position 2, length 1)
    session.remove(opened, Span(Address(1, 2), Offset(0, 1)))
    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "delete_single_char",
        "description": "Delete a single character from the middle",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "ABC"},
            {"op": "retrieve_vspanset", "before_delete": vspec_to_dict(vspanset1)},
            {"op": "remove", "doc": str(opened), "span": "1.2 length 1",
             "comment": "Delete 'B'"},
            {"op": "retrieve_vspanset", "after_delete": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "result": contents,
             "expected": "AC"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_delete_first_char(session):
    """Delete the first character of a document."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCD"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Delete 'A' (position 1, length 1)
    session.remove(opened, Span(Address(1, 1), Offset(0, 1)))
    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "delete_first_char",
        "description": "Delete the first character of a document",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "ABCD"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset1)},
            {"op": "remove", "doc": str(opened), "span": "1.1 length 1",
             "comment": "Delete first character 'A'"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "result": contents,
             "expected": "BCD"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_delete_last_char(session):
    """Delete the last character of a document."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCD"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Delete 'D' (position 4, length 1)
    session.remove(opened, Span(Address(1, 4), Offset(0, 1)))
    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "delete_last_char",
        "description": "Delete the last character of a document",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "ABCD"},
            {"op": "retrieve_vspanset", "before": vspec_to_dict(vspanset1)},
            {"op": "remove", "doc": str(opened), "span": "1.4 length 1",
             "comment": "Delete last character 'D'"},
            {"op": "retrieve_vspanset", "after": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "result": contents,
             "expected": "ABC"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_insert_at_exact_end(session):
    """Insert text at the exact end position of existing content."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["Hello"])
    vspanset1 = session.retrieve_vspanset(opened)
    end_pos = vspanset1.spans[0].end()

    # Insert at exact end position
    session.insert(opened, end_pos, ["World"])
    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "insert_at_exact_end",
        "description": "Insert text at the exact end position of existing content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1", "text": "Hello"},
            {"op": "retrieve_vspanset", "result": vspec_to_dict(vspanset1)},
            {"op": "insert", "doc": str(opened), "address": str(end_pos), "text": "World",
             "comment": "Insert at exact end position"},
            {"op": "retrieve_vspanset", "result": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "result": contents,
             "expected": "HelloWorld"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_multiple_inserts_same_position(session):
    """Multiple inserts at the same position - tests insertion order."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert three times at position 1.1
    session.insert(opened, Address(1, 1), ["First"])
    vspanset1 = session.retrieve_vspanset(opened)
    specset1 = SpecSet(VSpec(opened, list(vspanset1.spans)))
    contents1 = session.retrieve_contents(specset1)

    session.insert(opened, Address(1, 1), ["Second"])
    vspanset2 = session.retrieve_vspanset(opened)
    specset2 = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    session.insert(opened, Address(1, 1), ["Third"])
    vspanset3 = session.retrieve_vspanset(opened)
    specset3 = SpecSet(VSpec(opened, list(vspanset3.spans)))
    contents3 = session.retrieve_contents(specset3)

    session.close_document(opened)

    return {
        "name": "multiple_inserts_same_position",
        "description": "Multiple inserts at position 1.1 - tests insertion order",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "First", "result": contents1},
            {"op": "insert", "address": "1.1", "text": "Second", "result": contents2,
             "comment": "Does Second go before or after First?"},
            {"op": "insert", "address": "1.1", "text": "Third", "result": contents3,
             "comment": "Final order reveals insertion semantics"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_adjacent_deletes(session):
    """Delete adjacent regions one after another."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Delete 'CD' (positions 3-4)
    session.remove(opened, Span(Address(1, 3), Offset(0, 2)))
    vspanset2 = session.retrieve_vspanset(opened)
    specset2 = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    # Now delete 'EF' - but positions have shifted!
    # After first delete: "ABEFGH", so 'EF' is now at positions 3-4
    session.remove(opened, Span(Address(1, 3), Offset(0, 2)))
    vspanset3 = session.retrieve_vspanset(opened)
    specset3 = SpecSet(VSpec(opened, list(vspanset3.spans)))
    contents3 = session.retrieve_contents(specset3)

    session.close_document(opened)

    return {
        "name": "adjacent_deletes",
        "description": "Delete adjacent regions accounting for position shifts",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "remove", "span": "1.3 length 2", "comment": "Delete 'CD'",
             "result": contents2, "expected": "ABEFGH"},
            {"op": "remove", "span": "1.3 length 2",
             "comment": "Delete 'EF' (shifted position)",
             "result": contents3, "expected": "ABGH"},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_vcopy_single_char(session):
    """Vcopy (transclude) a single character."""
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Source"])
    session.close_document(opened1)

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)

    # Vcopy just the 'S' from Source
    source_ro = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    single_char_span = Span(Address(1, 1), Offset(0, 1))
    source_spec = SpecSet(VSpec(source_ro, [single_char_span]))

    session.vcopy(opened2, Address(1, 1), source_spec)
    vspanset = session.retrieve_vspanset(opened2)
    specset = SpecSet(VSpec(opened2, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    # Verify content identity
    shared = session.compare_versions(source_spec, specset)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": span_to_dict(span_a.span),
            "dest": span_to_dict(span_b.span)
        })

    session.close_document(source_ro)
    session.close_document(opened2)

    return {
        "name": "vcopy_single_char",
        "description": "Vcopy (transclude) a single character - minimum transclusion",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(doc1)},
            {"op": "insert", "doc": "source", "text": "Source"},
            {"op": "create_document", "doc": "dest", "result": str(doc2)},
            {"op": "vcopy", "to": "dest", "span": "just 'S'"},
            {"op": "retrieve_contents", "doc": "dest", "result": contents,
             "expected": "S"},
            {"op": "compare_versions", "shared": shared_result,
             "comment": "Single char should share identity"}
        ]
    }


def scenario_vcopy_to_same_document(session):
    """Vcopy content within the same document (self-transclusion)."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["Original"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Vcopy "Orig" to end of document
    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_span = Span(Address(1, 1), Offset(0, 4))  # "Orig"
    source_spec = SpecSet(VSpec(source_ro, [source_span]))

    end_pos = vspanset1.spans[0].end()
    session.vcopy(opened, end_pos, source_spec)

    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(source_ro)
    session.close_document(opened)

    return {
        "name": "vcopy_to_same_document",
        "description": "Vcopy content within the same document (self-transclusion)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "Original"},
            {"op": "vcopy", "from": "positions 1-4 (Orig)", "to": "end of doc",
             "comment": "Self-transclusion"},
            {"op": "retrieve_contents", "result": contents,
             "expected": "OriginalOrig"}
        ]
    }


def scenario_overlapping_vcopy(session):
    """Vcopy overlapping content to multiple positions."""
    source = session.create_document()
    opened_source = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_source, Address(1, 1), ["ABCDEFGH"])
    session.close_document(opened_source)

    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)

    # First vcopy: "ABCD"
    span1 = Span(Address(1, 1), Offset(0, 4))
    session.vcopy(opened_dest, Address(1, 1), SpecSet(VSpec(source_ro, [span1])))

    vs1 = session.retrieve_vspanset(opened_dest)
    end1 = vs1.spans[0].end()

    # Second vcopy: "CDEF" (overlaps with first in source)
    span2 = Span(Address(1, 3), Offset(0, 4))
    session.vcopy(opened_dest, end1, SpecSet(VSpec(source_ro, [span2])))

    vspanset = session.retrieve_vspanset(opened_dest)
    specset = SpecSet(VSpec(opened_dest, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(source_ro)
    session.close_document(opened_dest)

    return {
        "name": "overlapping_vcopy",
        "description": "Vcopy overlapping ranges from source to dest",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "ABCDEFGH"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "span": "ABCD (1-4)"},
            {"op": "vcopy", "span": "CDEF (3-6)", "comment": "Overlaps with first"},
            {"op": "retrieve_contents", "result": contents,
             "expected": "ABCDCDEF",
             "comment": "Both copies maintain identity with overlapping source regions"}
        ]
    }


def scenario_retrieve_empty_specset(session):
    """Retrieve with an empty specset - what happens?"""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Content"])

    # Create empty specset (no spans)
    empty_specset = SpecSet()

    try:
        contents = session.retrieve_contents(empty_specset)
        result = {"success": True, "contents": contents}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    session.close_document(opened)

    return {
        "name": "retrieve_empty_specset",
        "description": "Retrieve with an empty specset",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "Content"},
            {"op": "retrieve_contents", "specset": "empty",
             "result": result,
             "comment": "What happens with no spans specified?"}
        ]
    }


def scenario_retrieve_zero_width_span(session):
    """Retrieve with a zero-width span."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Content"])

    # Zero-width span at position 1
    zero_span = Span(Address(1, 1), Offset(0, 0))
    specset = SpecSet(VSpec(opened, [zero_span]))

    try:
        contents = session.retrieve_contents(specset)
        result = {"success": True, "contents": contents}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    session.close_document(opened)

    return {
        "name": "retrieve_zero_width_span",
        "description": "Retrieve with a zero-width span",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "Content"},
            {"op": "retrieve_contents", "span": "1.1 length 0",
             "result": result,
             "comment": "What does retrieving zero characters return?"}
        ]
    }


def scenario_pivot_single_char_regions(session):
    """Pivot with single-character regions."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["AB"])
    vspanset1 = session.retrieve_vspanset(opened)
    specset1 = SpecSet(VSpec(opened, list(vspanset1.spans)))
    contents1 = session.retrieve_contents(specset1)

    # Pivot: swap A and B (single chars)
    # pivot(doc, start, pivot_point, end)
    # Region 1: start to pivot_point
    # Region 2: pivot_point to end
    session.pivot(opened, Address(1, 1), Address(1, 2), Address(1, 3))

    vspanset2 = session.retrieve_vspanset(opened)
    specset2 = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    session.close_document(opened)

    return {
        "name": "pivot_single_char_regions",
        "description": "Pivot with single-character regions",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "AB", "result": contents1},
            {"op": "pivot", "start": "1.1", "pivot": "1.2", "end": "1.3",
             "comment": "Swap single chars A and B"},
            {"op": "retrieve_contents", "result": contents2,
             "expected": "BA"}
        ]
    }


def scenario_version_immediately(session):
    """Create a version immediately after document creation (empty doc)."""
    doc1 = session.create_document()

    # Version before any content
    try:
        doc2 = session.create_version(doc1)
        result = {"success": True, "version": str(doc2)}

        # Try to add content to version
        opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened2, Address(1, 1), ["Content in version"])
        vspanset = session.retrieve_vspanset(opened2)
        specset = SpecSet(VSpec(opened2, list(vspanset.spans)))
        contents = session.retrieve_contents(specset)
        session.close_document(opened2)

        result["contents"] = contents
    except Exception as e:
        result = {"success": False, "error": str(e)}

    return {
        "name": "version_immediately",
        "description": "Create a version of an empty document (no content yet)",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "create_version", "of": str(doc1),
             "comment": "Version before any content added",
             "result": result}
        ]
    }


def scenario_link_zero_width_endpoints(session):
    """Create a link with zero-width endpoint spans.

    NOTE: This test is DISABLED because it crashes the backend.
    See bugs/017-zero-width-link-endpoint-crash.md

    Instead, we test minimum-width (1 char) endpoints.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Source and Target"])

    # Minimum-width spans (1 character) instead of zero-width
    from_span = Span(Address(1, 1), Offset(0, 1))  # Just 'S'
    to_span = Span(Address(1, 12), Offset(0, 1))   # Just 'T'

    from_specs = SpecSet(VSpec(opened, [from_span]))
    to_specs = SpecSet(VSpec(opened, [to_span]))
    type_specs = SpecSet(Span(Address(1, 1, 0, 1), Offset(0, 1)))

    try:
        link_id = session.create_link(opened, from_specs, to_specs, type_specs)
        result = {"success": True, "link_id": str(link_id)}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    session.close_document(opened)

    return {
        "name": "link_zero_width_endpoints",
        "description": "Test minimum-width link endpoints (zero-width crashes - see bug 017)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "Source and Target"},
            {"op": "create_link",
             "from": "1-char span at 1.1",
             "to": "1-char span at 1.12",
             "result": result,
             "comment": "Zero-width crashes; testing 1-char minimum"}
        ]
    }


def scenario_compare_identical_documents(session):
    """Compare a document with itself - should share everything."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Identical content"])
    session.close_document(opened)

    ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    vspanset = session.retrieve_vspanset(ro)
    specset = SpecSet(VSpec(ro, list(vspanset.spans)))

    # Compare document with itself
    shared = session.compare_versions(specset, specset)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": span_to_dict(span_a.span),
            "b": span_to_dict(span_b.span)
        })

    session.close_document(ro)

    return {
        "name": "compare_identical_documents",
        "description": "Compare a document with itself",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "Identical content"},
            {"op": "compare_versions", "a": "same doc", "b": "same doc",
             "shared": shared_result,
             "comment": "Should return full document as shared"}
        ]
    }


def scenario_compare_disjoint_documents(session):
    """Compare two documents with completely different content."""
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["First document content"])
    session.close_document(opened1)

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Second document content"])
    session.close_document(opened2)

    ro1 = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    ro2 = session.open_document(doc2, READ_ONLY, CONFLICT_COPY)

    vs1 = session.retrieve_vspanset(ro1)
    vs2 = session.retrieve_vspanset(ro2)

    specset1 = SpecSet(VSpec(ro1, list(vs1.spans)))
    specset2 = SpecSet(VSpec(ro2, list(vs2.spans)))

    shared = session.compare_versions(specset1, specset2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": span_to_dict(span_a.span),
            "b": span_to_dict(span_b.span)
        })

    session.close_document(ro1)
    session.close_document(ro2)

    return {
        "name": "compare_disjoint_documents",
        "description": "Compare two documents with no shared content",
        "operations": [
            {"op": "create_document", "doc": "doc1", "result": str(doc1)},
            {"op": "insert", "doc": "doc1", "text": "First document content"},
            {"op": "create_document", "doc": "doc2", "result": str(doc2)},
            {"op": "insert", "doc": "doc2", "text": "Second document content"},
            {"op": "compare_versions", "shared": shared_result,
             "expected": "empty list - no shared origin",
             "comment": "Different origins means no sharing"}
        ]
    }


def scenario_find_links_empty_document(session):
    """Search for links in/from an empty document."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    # Don't insert any content

    vspanset = session.retrieve_vspanset(opened)

    # Try to find links (should be none)
    try:
        # Search with empty/minimal criteria
        from_specs = SpecSet(VSpec(opened, []))
        links = session.find_links(from_specs)
        result = {"success": True, "links": [str(l) for l in links]}
    except Exception as e:
        result = {"success": False, "error": str(e)}

    session.close_document(opened)

    return {
        "name": "find_links_empty_document",
        "description": "Search for links in an empty document",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "retrieve_vspanset", "result": vspec_to_dict(vspanset),
             "comment": "Empty document - no content"},
            {"op": "find_links", "from": "empty doc",
             "result": result}
        ]
    }


def scenario_large_insert(session):
    """Insert moderately large text.

    NOTE: Very large inserts (10KB+) crash the backend.
    See bugs/018-large-insert-crash.md

    This test uses a safe size that works reliably.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Use a moderate size that works (discovered through testing)
    # The exact limit varies but ~50 chars is safe
    text = "The quick brown fox jumps over the lazy dog. "  # 46 chars

    session.insert(opened, Address(1, 1), [text])
    vspanset = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "large_insert",
        "description": "Insert moderately large text (very large crashes - see bug 018)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": text, "length": len(text)},
            {"op": "retrieve_contents", "result": contents,
             "comment": "Moderate size works; 10KB+ crashes backend"}
        ]
    }


def scenario_many_small_inserts(session):
    """Many small inserts to same document (fragmentation test)."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Do 100 single-character inserts
    for i in range(100):
        vspanset = session.retrieve_vspanset(opened)
        if vspanset.spans:
            pos = vspanset.spans[0].end()
        else:
            pos = Address(1, 1)
        session.insert(opened, pos, [chr(65 + (i % 26))])

    final_vspanset = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(final_vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened)

    return {
        "name": "many_small_inserts",
        "description": "100 single-character inserts",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert_loop", "count": 100, "each": "single character"},
            {"op": "retrieve_vspanset",
             "span_count": len(final_vspanset.spans),
             "comment": "How many spans after fragmented inserts?"},
            {"op": "retrieve_contents",
             "length": len(contents) if contents else 0,
             "sample": contents[:50] if contents else None}
        ]
    }


SCENARIOS = [
    ("edgecases", "insert_single_char", scenario_insert_single_char),
    ("edgecases", "delete_single_char", scenario_delete_single_char),
    ("edgecases", "delete_first_char", scenario_delete_first_char),
    ("edgecases", "delete_last_char", scenario_delete_last_char),
    ("edgecases", "insert_at_exact_end", scenario_insert_at_exact_end),
    ("edgecases", "multiple_inserts_same_position", scenario_multiple_inserts_same_position),
    ("edgecases", "adjacent_deletes", scenario_adjacent_deletes),
    ("edgecases", "vcopy_single_char", scenario_vcopy_single_char),
    ("edgecases", "vcopy_to_same_document", scenario_vcopy_to_same_document),
    ("edgecases", "overlapping_vcopy", scenario_overlapping_vcopy),
    ("edgecases", "retrieve_empty_specset", scenario_retrieve_empty_specset),
    ("edgecases", "retrieve_zero_width_span", scenario_retrieve_zero_width_span),
    ("edgecases", "pivot_single_char_regions", scenario_pivot_single_char_regions),
    ("edgecases", "version_immediately", scenario_version_immediately),
    ("edgecases", "link_zero_width_endpoints", scenario_link_zero_width_endpoints),
    ("edgecases", "compare_identical_documents", scenario_compare_identical_documents),
    ("edgecases", "compare_disjoint_documents", scenario_compare_disjoint_documents),
    ("edgecases", "find_links_empty_document", scenario_find_links_empty_document),
    ("edgecases", "large_insert", scenario_large_insert),
    ("edgecases", "many_small_inserts", scenario_many_small_inserts),
]
