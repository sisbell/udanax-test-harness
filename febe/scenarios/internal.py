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


SCENARIOS = [
    ("internal", "internal_state", scenario_internal_state),
    ("internal", "ispan_consolidation_fragmented", scenario_ispan_consolidation_fragmented),
    ("internal", "ispan_consolidation_bulk", scenario_ispan_consolidation_bulk),
    ("internal", "ispan_partial_overlap", scenario_ispan_partial_overlap),
]
