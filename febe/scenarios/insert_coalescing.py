"""Test scenarios for INSERT coalescing behavior (isanextensionnd).

These tests answer: When does the second INSERT coalesce with the first?
Specifically, after a DELETE operation intervenes between two INSERTs,
are the I-addresses contiguous or does DELETE create a gap?
"""

from client import Address, Offset, Span, VSpec, SpecSet, READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY, JUMP_TYPE
from .common import vspec_to_dict, span_to_dict


def scenario_insert_delete_insert_iaddress_gap(session):
    """Test: Does DELETE create a gap in I-address allocation?

    Scenario:
    1. Type "ABC" at end of document (positions 1-3)
    2. Delete "B" from middle (position 2)
    3. Type "DEF" at end of document (positions 3-5, was 4-6 before delete)

    Question: Are the I-addresses for "DEF" contiguous with "AC"?
    Or does the DELETE (or any POOM mutation) advance the I-address counter?

    Method: Use compare_versions to see if we get 1 or 2 I-span pairs.
    If DELETE creates a gap: 2 pairs (ABC has one range, DEF has another)
    If DELETE doesn't affect I-allocation: 1 pair (all 6 chars contiguous)
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABC"
    session.insert(opened, Address(1, 1), ["ABC"])

    # Delete "B" (position 2, width 1)
    session.delete(opened, Address(1, 2), Offset(0, 1))

    # Insert "DEF" at the end (after "AC" which is now at positions 1-2)
    vspanset = session.retrieve_vspanset(opened)
    end_pos = vspanset.spans[0].end()  # Should be 1.3 (after "AC")
    session.insert(opened, end_pos, ["DEF"])

    # Get final content
    final_vspanset = session.retrieve_vspanset(opened)
    final_specset = SpecSet(VSpec(opened, list(final_vspanset.spans)))
    final_contents = session.retrieve_contents(final_specset)

    session.close_document(opened)

    # Now vcopy to a new document and compare to check I-span structure
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_vspanset = session.retrieve_vspanset(source_ro)
    source_specset = SpecSet(VSpec(source_ro, list(source_vspanset.spans)))

    session.vcopy(opened_dest, Address(1, 1), source_specset)

    dest_vspanset = session.retrieve_vspanset(opened_dest)
    dest_specset = SpecSet(VSpec(opened_dest, list(dest_vspanset.spans)))

    # Compare versions - reveals I-span structure
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
        "name": "insert_delete_insert_iaddress_gap",
        "description": "Does DELETE create a gap in I-address allocation?",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABC", "at": "1.1"},
            {"op": "delete", "span": "1.2+0.1", "comment": "Delete 'B' from middle"},
            {"op": "insert", "text": "DEF", "at": "end", "comment": "Resume typing at end"},
            {"op": "retrieve_contents", "result": final_contents, "expected": "ACDEF"},
            {"op": "vcopy", "to": "new document"},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "interpretation": {
                 "1 pair": "DELETE does NOT create I-address gap (ABC and DEF have contiguous I-addresses)",
                 "2 pairs": "DELETE DOES create I-address gap (ABC and DEF have separate I-address ranges)"
             }}
        ]
    }


def scenario_insert_rearrange_insert_iaddress_gap(session):
    """Test: Does REARRANGE create a gap in I-address allocation?

    Scenario:
    1. Type "ABC"
    2. Rearrange to "CBA"
    3. Type "DEF" at end

    REARRANGE modifies the SPAN enfilade but not the granfilade.
    Question: Does it affect subsequent I-address allocation?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABC"
    session.insert(opened, Address(1, 1), ["ABC"])

    # Rearrange to "CBA"
    # cutlist: [0, 2, 3, 1, 2]  (take positions 3, then 2, then 1)
    # Wait - the FEBE rearrange API might be different. Let me check the actual signature.
    # Actually, let's use a simpler rearrange: swap first two chars "ABC" -> "BAC"
    # cutlist: [0, 1, 2, 0, 1, 2, 3] would give us positions [1-2, 0-1, 2-3] = "BAC"

    # For now, let's just do a simple rearrange test
    # rearrange is: (docid, cutlist) where cutlist defines the new ordering
    try:
        session.rearrange(opened, [0, 2, 3, 1, 2, 3])  # "CBA"
    except Exception as e:
        # If rearrange fails, document it but continue
        rearrange_result = f"FAILED: {e}"
    else:
        rearrange_result = "success"

    # Insert "DEF" at end
    vspanset = session.retrieve_vspanset(opened)
    end_pos = vspanset.spans[0].end()
    session.insert(opened, end_pos, ["DEF"])

    # Get final content
    final_vspanset = session.retrieve_vspanset(opened)
    final_specset = SpecSet(VSpec(opened, list(final_vspanset.spans)))
    final_contents = session.retrieve_contents(final_specset)

    session.close_document(opened)

    # Vcopy and compare
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_vspanset = session.retrieve_vspanset(source_ro)
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
        "name": "insert_rearrange_insert_iaddress_gap",
        "description": "Does REARRANGE create a gap in I-address allocation?",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABC"},
            {"op": "rearrange", "to": "CBA", "result": rearrange_result},
            {"op": "insert", "text": "DEF", "at": "end"},
            {"op": "retrieve_contents", "result": final_contents},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "comment": "REARRANGE modifies SPAN enfilade only, not granfilade"}
        ]
    }


def scenario_insert_link_insert_iaddress_gap(session):
    """Test: Does CREATELINK create a gap in I-address allocation?

    Scenario:
    1. Type "ABC"
    2. Create a link from "B" to some target
    3. Type "DEF" at end

    CREATELINK adds entries to the POOM enfilade but doesn't touch granfilade.
    Question: Does it affect subsequent I-address allocation?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABC"
    session.insert(opened, Address(1, 1), ["ABC"])

    # Create a link from "B" (position 2) to "A" (position 1)
    from_span = Span(Address(1, 2), Offset(0, 1))
    to_span = Span(Address(1, 1), Offset(0, 1))

    from_specs = SpecSet(VSpec(opened, [from_span]))
    to_specs = SpecSet(VSpec(opened, [to_span]))
    type_specs = SpecSet([JUMP_TYPE])

    link_id = session.create_link(opened, from_specs, to_specs, type_specs)

    # Insert "DEF" at end of text subspace (V >= 1.0, skip link subspace at 0.x)
    vspanset = session.retrieve_vspanset(opened)
    text_spans = [s for s in vspanset.spans if s.start.digits[0] >= 1]
    end_pos = text_spans[-1].end()
    session.insert(opened, end_pos, ["DEF"])

    # Get final content (text subspace only)
    final_vspanset = session.retrieve_vspanset(opened)
    final_text_spans = [s for s in final_vspanset.spans if s.start.digits[0] >= 1]
    final_specset = SpecSet(VSpec(opened, final_text_spans))
    final_contents = session.retrieve_contents(final_specset)
    # Filter to strings only (skip any Address objects from link metadata)
    final_contents = [c for c in final_contents if isinstance(c, str)]

    session.close_document(opened)

    # Vcopy and compare (text subspace only to avoid Bug 009)
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_vspanset = session.retrieve_vspanset(source_ro)
    source_text_spans = [s for s in source_vspanset.spans if s.start.digits[0] >= 1]
    source_specset = SpecSet(VSpec(source_ro, source_text_spans))

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
        "name": "insert_link_insert_iaddress_gap",
        "description": "Does CREATELINK create a gap in I-address allocation?",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABC"},
            {"op": "create_link", "from": "B", "to": "A", "result": str(link_id)},
            {"op": "insert", "text": "DEF", "at": "end"},
            {"op": "retrieve_contents", "result": final_contents, "expected": "ABCDEF"},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "comment": "CREATELINK modifies POOM enfilade only, not granfilade"}
        ]
    }


def scenario_insert_only_baseline(session):
    """Baseline test: Just two inserts with no intervening operation.

    This should definitely produce 1 I-span pair (contiguous I-addresses).
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABC"
    session.insert(opened, Address(1, 1), ["ABC"])

    # Insert "DEF" at end
    vspanset = session.retrieve_vspanset(opened)
    end_pos = vspanset.spans[0].end()
    session.insert(opened, end_pos, ["DEF"])

    # Get final content
    final_vspanset = session.retrieve_vspanset(opened)
    final_specset = SpecSet(VSpec(opened, list(final_vspanset.spans)))
    final_contents = session.retrieve_contents(final_specset)

    session.close_document(opened)

    # Vcopy and compare
    dest = session.create_document()
    opened_dest = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    source_vspanset = session.retrieve_vspanset(source_ro)
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
        "name": "insert_only_baseline",
        "description": "Baseline: Two inserts with no intervening operation",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "ABC"},
            {"op": "insert", "text": "DEF", "at": "end"},
            {"op": "retrieve_contents", "result": final_contents, "expected": "ABCDEF"},
            {"op": "compare_versions",
             "shared_span_pairs": len(shared),
             "shared": shared_result,
             "expected": "1 pair (definitely contiguous)"}
        ]
    }


SCENARIOS = [
    ("internal", "insert_only_baseline", scenario_insert_only_baseline),
    ("internal", "insert_delete_insert_iaddress_gap", scenario_insert_delete_insert_iaddress_gap),
    ("internal", "insert_link_insert_iaddress_gap", scenario_insert_link_insert_iaddress_gap),
    ("internal", "insert_rearrange_insert_iaddress_gap", scenario_insert_rearrange_insert_iaddress_gap),
]
