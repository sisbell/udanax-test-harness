"""Internal state inspection scenarios."""

from client import Address, Offset, Span, VSpec, SpecSet, READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
from .common import vspec_to_dict, span_to_dict


def scenario_internal_state(session):
    """Demonstrate internal enfilade state capture after operations."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Capture initial state (empty document)
    initial_state = session.dump_state()

    # Insert text
    session.insert(opened_docid, Address(1, 1), ["Hello, World!"])

    # Capture state after insert
    after_insert_state = session.dump_state()

    # Get content
    vspanset = session.retrieve_vspanset(opened_docid)
    specset = SpecSet(VSpec(opened_docid, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "internal_state",
        "description": "Capture internal enfilade state after operations",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "dump_state", "state": initial_state},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Hello, World!"},
            {"op": "dump_state", "state": after_insert_state},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_ispan_consolidation_fragmented(session):
    """Test: Do 10 separate inserts produce 1 or 10 I-spans?

    This test creates content with 10 separate single-char inserts, then
    vcopies to a new doc and compares. The number of shared span pairs
    in compare_versions reveals whether I-spans are consolidated.

    If I-space consolidates adjacent addresses: 1 span pair
    If I-space preserves insert boundaries: 10 span pairs
    """
    # Create source with fragmented inserts
    source = session.create_document()
    opened_source = session.open_document(source, READ_WRITE, CONFLICT_FAIL)

    # Do 10 single-character inserts (use 10 to keep output manageable)
    for i in range(10):
        vspanset = session.retrieve_vspanset(opened_source)
        if vspanset.spans:
            pos = vspanset.spans[0].end()
        else:
            pos = Address(1, 1)
        session.insert(opened_source, pos, [chr(65 + i)])  # A, B, C, ...

    source_vspanset = session.retrieve_vspanset(opened_source)
    session.close_document(opened_source)

    # Vcopy entire content to new document
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_specset = SpecSet(VSpec(source_ro, list(source_vspanset.spans)))

    session.vcopy(opened_dest, Address(1, 1), source_specset)

    dest_vspanset = session.retrieve_vspanset(opened_dest)
    dest_specset = SpecSet(VSpec(opened_dest, list(dest_vspanset.spans)))

    # Get contents to verify
    source_contents = session.retrieve_contents(source_specset)
    dest_contents = session.retrieve_contents(dest_specset)

    # Compare versions - this reveals I-span structure
    # Number of span pairs = number of I-spans
    shared = session.compare_versions(source_specset, dest_specset)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": span_to_dict(span_a.span),
            "dest": span_to_dict(span_b.span)
        })

    session.close_document(source_ro)
    session.close_document(opened_dest)

    return {
        "name": "ispan_consolidation_fragmented",
        "description": "10 separate inserts - does compare_versions return 1 or 10 span pairs?",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert_loop", "count": 10, "each": "single character"},
            {"op": "retrieve_vspanset", "source_vspan_count": len(source_vspanset.spans)},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "what": "all content"},
            {"op": "retrieve_vspanset", "dest_vspan_count": len(dest_vspanset.spans)},
            {"op": "retrieve_contents", "source": source_contents, "dest": dest_contents},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "interpretation": "1 pair = I-space consolidated, 10 pairs = I-space fragmented"}
        ]
    }


def scenario_ispan_consolidation_bulk(session):
    """Test: Does a single bulk insert produce 1 I-span?

    Control case: Insert all 10 characters at once.
    Should produce exactly 1 span pair in compare_versions.
    """
    # Create source with single bulk insert
    source = session.create_document()
    opened_source = session.open_document(source, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened_source, Address(1, 1), ["ABCDEFGHIJ"])  # 10 chars at once

    source_vspanset = session.retrieve_vspanset(opened_source)
    session.close_document(opened_source)

    # Vcopy entire content to new document
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_specset = SpecSet(VSpec(source_ro, list(source_vspanset.spans)))

    session.vcopy(opened_dest, Address(1, 1), source_specset)

    dest_vspanset = session.retrieve_vspanset(opened_dest)
    dest_specset = SpecSet(VSpec(opened_dest, list(dest_vspanset.spans)))

    # Compare versions
    shared = session.compare_versions(source_specset, dest_specset)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": span_to_dict(span_a.span),
            "dest": span_to_dict(span_b.span)
        })

    session.close_document(source_ro)
    session.close_document(opened_dest)

    return {
        "name": "ispan_consolidation_bulk",
        "description": "Single bulk insert - should produce exactly 1 span pair",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "text": "ABCDEFGHIJ", "count": 10},
            {"op": "retrieve_vspanset", "source_vspan_count": len(source_vspanset.spans)},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest"},
            {"op": "retrieve_vspanset", "dest_vspan_count": len(dest_vspanset.spans)},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "expected": "exactly 1 span pair (bulk insert = contiguous I-addresses)"}
        ]
    }


def scenario_ispan_partial_overlap(session):
    """Test: What happens with partial overlap of fragmented I-spans?

    Create ABCDEFGHIJ with separate inserts.
    Vcopy positions 3-7 (CDEFG) to new doc.
    Compare should reveal if C, D, E, F, G are 5 separate I-spans or 1.
    """
    # Create source with fragmented inserts
    source = session.create_document()
    opened_source = session.open_document(source, READ_WRITE, CONFLICT_FAIL)

    for i in range(10):
        vspanset = session.retrieve_vspanset(opened_source)
        if vspanset.spans:
            pos = vspanset.spans[0].end()
        else:
            pos = Address(1, 1)
        session.insert(opened_source, pos, [chr(65 + i)])

    session.close_document(opened_source)

    # Vcopy only positions 3-7 (CDEFG)
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    partial_span = Span(Address(1, 3), Offset(0, 5))  # 5 chars starting at position 3
    source_specset = SpecSet(VSpec(source_ro, [partial_span]))

    session.vcopy(opened_dest, Address(1, 1), source_specset)

    dest_vspanset = session.retrieve_vspanset(opened_dest)
    dest_specset = SpecSet(VSpec(opened_dest, list(dest_vspanset.spans)))

    source_contents = session.retrieve_contents(source_specset)
    dest_contents = session.retrieve_contents(dest_specset)

    # Compare versions
    shared = session.compare_versions(source_specset, dest_specset)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": span_to_dict(span_a.span),
            "dest": span_to_dict(span_b.span)
        })

    session.close_document(source_ro)
    session.close_document(opened_dest)

    return {
        "name": "ispan_partial_overlap",
        "description": "Vcopy subset of fragmented content - reveals I-span granularity",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert_loop", "count": 10, "each": "A-J"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "positions 3-7 (CDEFG)", "to": "dest"},
            {"op": "retrieve_contents", "source": source_contents, "dest": dest_contents,
             "expected": "CDEFG in both"},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "interpretation": "1 pair = consolidated, 5 pairs = per-insert granularity"}
        ]
    }


def scenario_internal_transclusion_identity(session):
    """Test that internal transclusion creates two V-positions for same I-address.

    When content is transcluded within the same document, the POOM should map
    the same I-address to two different V-positions. This tests whether the
    bidirectional index (I→V direction) correctly returns all V-positions.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert original content
    session.insert(opened, Address(1, 1), ["Original text here"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Transclude "text" from within the same document to the end
    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_span = Span(Address(1, 10), Offset(0, 4))  # "text"
    source_spec = SpecSet(VSpec(source_ro, [source_span]))

    end_pos = vspanset1.spans[0].end()
    session.vcopy(opened, end_pos, source_spec)

    vspanset2 = session.retrieve_vspanset(opened)
    specset = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    # Now compare the document with itself to see if both occurrences
    # of "text" are recognized as sharing content identity
    session.close_document(source_ro)
    session.close_document(opened)

    # Reopen for comparison
    ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    vs = session.retrieve_vspanset(ro)

    # Create specs for the two regions containing "text"
    # First occurrence: positions 10-13 (0-indexed: 9-12)
    # Second occurrence: should be at positions 19-22 (0-indexed: 18-21)
    first_text = Span(Address(1, 10), Offset(0, 4))
    second_text = Span(Address(1, 19), Offset(0, 4))

    spec1 = SpecSet(VSpec(ro, [first_text]))
    spec2 = SpecSet(VSpec(ro, [second_text]))

    # Compare these two regions - they should share content identity
    # because they both reference the same I-addresses
    shared = session.compare_versions(spec1, spec2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "first": span_to_dict(span_a.span),
            "second": span_to_dict(span_b.span)
        })

    session.close_document(ro)

    return {
        "name": "internal_transclusion_identity",
        "description": "Test I→V mapping with internal transclusion (two V-positions, same I-address)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "Original text here"},
            {"op": "vcopy", "from": "positions 10-13 (text)", "to": "end of doc",
             "comment": "Self-transclusion creates duplicate reference"},
            {"op": "retrieve_contents", "result": contents,
             "expected": "Original text heretext"},
            {"op": "compare_versions",
             "spec1": "first occurrence of 'text' (1.10-1.13)",
             "spec2": "second occurrence of 'text' (1.19-1.22)",
             "shared": shared_result,
             "comment": "Both should map to same I-addresses, thus share identity"}
        ]
    }


def scenario_internal_transclusion_with_link(session):
    """Test link discovery through internal transclusion.

    If we create a link on the first occurrence of transcluded content,
    can we discover that link by searching from the second occurrence?
    This tests whether ispan2vspanset returns both V-positions.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert original content
    session.insert(opened, Address(1, 1), ["Original text here"])
    vspanset1 = session.retrieve_vspanset(opened)

    # Transclude "text" to end
    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_span = Span(Address(1, 10), Offset(0, 4))  # "text"
    source_spec = SpecSet(VSpec(source_ro, [source_span]))

    end_pos = vspanset1.spans[0].end()
    session.vcopy(opened, end_pos, source_spec)
    session.close_document(source_ro)

    # Get updated content
    vspanset2 = session.retrieve_vspanset(opened)
    specset2 = SpecSet(VSpec(opened, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset2)

    # Create a link on the FIRST occurrence of "text" (positions 10-13)
    from_span = Span(Address(1, 10), Offset(0, 4))
    to_span = Span(Address(1, 1), Offset(0, 8))  # link to "Original"
    type_span = Span(Address(1, 1, 0, 1), Offset(0, 1))

    from_specs = SpecSet(VSpec(opened, [from_span]))
    to_specs = SpecSet(VSpec(opened, [to_span]))
    type_specs = SpecSet(type_span)

    link_id = session.create_link(opened, from_specs, to_specs, type_specs)

    # Now search for links from the SECOND occurrence of "text" (positions 19-22)
    # If ispan2vspanset correctly returns both V-positions for the shared I-address,
    # the link should be discoverable from the second occurrence too
    second_text_span = Span(Address(1, 19), Offset(0, 4))
    second_text_specs = SpecSet(VSpec(opened, [second_text_span]))

    links_from_second = session.find_links(second_text_specs)

    session.close_document(opened)

    return {
        "name": "internal_transclusion_with_link",
        "description": "Test link discovery through internal transclusion (I→V mapping)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "Original text here"},
            {"op": "vcopy", "span": "text", "to": "end",
             "comment": "Creates duplicate reference to same I-addresses"},
            {"op": "retrieve_contents", "result": contents},
            {"op": "create_link",
             "from": "first occurrence of 'text' (1.10-1.13)",
             "to": "Original",
             "result": str(link_id)},
            {"op": "find_links",
             "from": "second occurrence of 'text' (1.19-1.22)",
             "result": [str(l) for l in links_from_second],
             "expected": "Should find the link (same I-address as first occurrence)",
             "comment": "Tests if I→V mapping returns both V-positions"}
        ]
    }


def scenario_internal_transclusion_multiple_copies(session):
    """Test with multiple internal transclusions of the same content.

    Create three copies of the same content within one document,
    then verify all three are recognized as sharing identity.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert original
    session.insert(opened, Address(1, 1), ["ABC"])

    # Make two more copies of "B"
    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    b_span = Span(Address(1, 2), Offset(0, 1))  # "B"
    b_spec = SpecSet(VSpec(source_ro, [b_span]))

    vspanset1 = session.retrieve_vspanset(opened)
    end1 = vspanset1.spans[0].end()
    session.vcopy(opened, end1, b_spec)

    vspanset2 = session.retrieve_vspanset(opened)
    end2 = vspanset2.spans[0].end()
    session.vcopy(opened, end2, b_spec)

    session.close_document(source_ro)

    vspanset3 = session.retrieve_vspanset(opened)
    specset3 = SpecSet(VSpec(opened, list(vspanset3.spans)))
    contents = session.retrieve_contents(specset3)

    # Now verify all three "B"s share identity
    # Positions: 1.2 (original), 1.4 (first copy), 1.5 (second copy)
    session.close_document(opened)

    ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)

    pos1 = Span(Address(1, 2), Offset(0, 1))
    pos2 = Span(Address(1, 4), Offset(0, 1))
    pos3 = Span(Address(1, 5), Offset(0, 1))

    spec_pos1 = SpecSet(VSpec(ro, [pos1]))
    spec_pos2 = SpecSet(VSpec(ro, [pos2]))
    spec_pos3 = SpecSet(VSpec(ro, [pos3]))

    # Compare all pairs
    shared_1_2 = session.compare_versions(spec_pos1, spec_pos2)
    shared_1_3 = session.compare_versions(spec_pos1, spec_pos3)
    shared_2_3 = session.compare_versions(spec_pos2, spec_pos3)

    results = {
        "1_2": len(list(shared_1_2)) > 0,
        "1_3": len(list(shared_1_3)) > 0,
        "2_3": len(list(shared_2_3)) > 0
    }

    session.close_document(ro)

    return {
        "name": "internal_transclusion_multiple_copies",
        "description": "Three copies of same content in one document - all share identity",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABC"},
            {"op": "vcopy", "span": "B", "to": "end", "comment": "First copy"},
            {"op": "vcopy", "span": "B", "to": "end", "comment": "Second copy"},
            {"op": "retrieve_contents", "result": contents,
             "expected": "ABCBB"},
            {"op": "compare_all_pairs",
             "positions": ["1.2", "1.4", "1.5"],
             "results": results,
             "expected": "All three should share identity (all true)",
             "comment": "Tests I→V mapping with three V-positions for one I-address"}
        ]
    }


SCENARIOS = [
    ("internal", "internal_state", scenario_internal_state),
    ("internal", "ispan_consolidation_fragmented", scenario_ispan_consolidation_fragmented),
    ("internal", "ispan_consolidation_bulk", scenario_ispan_consolidation_bulk),
    ("internal", "ispan_partial_overlap", scenario_ispan_partial_overlap),
    ("internal", "internal_transclusion_identity", scenario_internal_transclusion_identity),
    ("internal", "internal_transclusion_with_link", scenario_internal_transclusion_with_link),
    ("internal", "internal_transclusion_multiple_copies", scenario_internal_transclusion_multiple_copies),
]
