"""Test I-address allocation behavior during interleaved editing sessions."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_interleaved_insert_delete(session):
    """Test I-address allocation across INSERT-DELETE-INSERT sequences.

    Question: When a user performs INSERT, DELETE, INSERT, DELETE, INSERT,
    does findisatoinsertgr always allocate I-addresses monotonically from
    the current maximum in the granfilade, regardless of DELETE operations?

    Expected: DELETE operations do not touch the granfilade. They only
    update the spanfilade (removing V-space mappings). The next INSERT
    should continue allocating I-addresses from where the previous INSERT
    left off, as findisatoinsertmolecule calls findpreviousisagr to find
    the highest existing I-address and increments from there.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT #1: "AAA" at position 1.1
    session.insert(opened, Address(1, 1), ["AAA"])
    vs1 = session.retrieve_vspanset(opened)
    spec1 = SpecSet(VSpec(opened, list(vs1.spans)))
    content1 = session.retrieve_contents(spec1)

    # DELETE: Remove position 1.2 (middle 'A')
    session.remove(opened, Span(Address(1, 2), Offset(0, 1)))
    vs2 = session.retrieve_vspanset(opened)
    spec2 = SpecSet(VSpec(opened, list(vs2.spans)))
    content2 = session.retrieve_contents(spec2)

    # INSERT #2: "BBB" at position 1.2 (middle of remaining content)
    session.insert(opened, Address(1, 2), ["BBB"])
    vs3 = session.retrieve_vspanset(opened)
    spec3 = SpecSet(VSpec(opened, list(vs3.spans)))
    content3 = session.retrieve_contents(spec3)

    # DELETE: Remove positions 1.3-1.4 (two characters)
    session.remove(opened, Span(Address(1, 3), Offset(0, 2)))
    vs4 = session.retrieve_vspanset(opened)
    spec4 = SpecSet(VSpec(opened, list(vs4.spans)))
    content4 = session.retrieve_contents(spec4)

    # INSERT #3: "CCC" at position 1.3
    session.insert(opened, Address(1, 3), ["CCC"])
    vs5 = session.retrieve_vspanset(opened)
    spec5 = SpecSet(VSpec(opened, list(vs5.spans)))
    content5 = session.retrieve_contents(spec5)

    session.close_document(opened)

    return {
        "name": "interleaved_insert_delete",
        "description": "Test I-address allocation behavior across interleaved INSERTs and DELETEs",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert_1", "text": "AAA", "result": {"content": content1, "vspans": vspec_to_dict(vs1)}},
            {"op": "delete_1", "removed": "1.2", "result": {"content": content2, "vspans": vspec_to_dict(vs2)}},
            {"op": "insert_2", "text": "BBB", "result": {"content": content3, "vspans": vspec_to_dict(vs3)}},
            {"op": "delete_2", "removed": "1.3-1.4", "result": {"content": content4, "vspans": vspec_to_dict(vs4)}},
            {"op": "insert_3", "text": "CCC", "result": {"content": content5, "vspans": vspec_to_dict(vs5)}},
        ]
    }


def scenario_consecutive_inserts_monotonic(session):
    """Verify that consecutive inserts without intervening operations allocate monotonically.

    This is a control test: without any DELETE operations, we expect I-addresses
    to increment strictly monotonically.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Three consecutive inserts
    session.insert(opened, Address(1, 1), ["A"])
    vs1 = session.retrieve_vspanset(opened)

    session.insert(opened, Address(1, 2), ["B"])
    vs2 = session.retrieve_vspanset(opened)

    session.insert(opened, Address(1, 3), ["C"])
    vs3 = session.retrieve_vspanset(opened)

    # Get final content
    spec3 = SpecSet(VSpec(opened, list(vs3.spans)))
    content = session.retrieve_contents(spec3)

    session.close_document(opened)

    return {
        "name": "consecutive_inserts_monotonic",
        "description": "Control: consecutive inserts allocate monotonically increasing I-addresses",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert_A", "result": {"vspans": vspec_to_dict(vs1)}},
            {"op": "insert_B", "result": {"vspans": vspec_to_dict(vs2)}},
            {"op": "insert_C", "result": {"vspans": vspec_to_dict(vs3), "content": content}},
        ]
    }


def scenario_delete_does_not_affect_next_insert(session):
    """Test that DELETE operations do not change the next I-address allocation.

    Specifically: Insert "A", note the I-address. Insert "B", note the I-address.
    Delete "A". Insert "C", check if C's I-address follows B's, not A's.

    We'll use COMPARE_VERSIONS to examine the I-space structure. If DELETE
    affects allocation, C might reuse A's I-address. If allocation is monotonic,
    C gets a fresh I-address after B.
    """
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)

    # Insert A
    session.insert(opened1, Address(1, 1), ["A"])
    vs1 = session.retrieve_vspanset(opened1)
    content1 = session.retrieve_contents(SpecSet(VSpec(opened1, list(vs1.spans))))

    # Insert B (at end)
    session.insert(opened1, Address(1, 2), ["B"])
    vs2 = session.retrieve_vspanset(opened1)
    content2 = session.retrieve_contents(SpecSet(VSpec(opened1, list(vs2.spans))))

    # Delete A (position 1.1)
    session.remove(opened1, Span(Address(1, 1), Offset(0, 1)))
    vs3 = session.retrieve_vspanset(opened1)
    content3 = session.retrieve_contents(SpecSet(VSpec(opened1, list(vs3.spans))))

    # Insert C (at new position 1.2, which is after B)
    session.insert(opened1, Address(1, 2), ["C"])
    vs4 = session.retrieve_vspanset(opened1)
    content4 = session.retrieve_contents(SpecSet(VSpec(opened1, list(vs4.spans))))

    # Close doc1 write handle before re-opening as read-only
    session.close_document(opened1)

    # Now create a second document and transclude content from doc1
    # to examine I-address structure via compare_versions
    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)

    # Copy B and C to doc2
    read1 = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    vs_read = session.retrieve_vspanset(read1)
    source_specs = SpecSet(VSpec(read1, list(vs_read.spans)))
    session.vcopy(opened2, Address(1, 1), source_specs)

    # Compare the two documents - they should share I-addresses for B and C
    session.close_document(opened2)
    read2 = session.open_document(doc2, READ_ONLY, CONFLICT_COPY)
    vs_doc1 = session.retrieve_vspanset(read1)
    vs_doc2 = session.retrieve_vspanset(read2)
    spec_doc1 = SpecSet(VSpec(read1, list(vs_doc1.spans)))
    spec_doc2 = SpecSet(VSpec(read2, list(vs_doc2.spans)))

    comparison = session.compare_versions(spec_doc1, spec_doc2)
    comparison_result = [
        {"doc1": span_to_dict(s1.span), "doc2": span_to_dict(s2.span)}
        for s1, s2 in comparison
    ]

    session.close_document(read1)
    session.close_document(read2)

    return {
        "name": "delete_does_not_affect_next_insert",
        "description": "DELETE should not change I-address allocation for subsequent INSERTs",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "result": str(opened1)},
            {"op": "insert_A", "result": {"content": content1, "vspans": vspec_to_dict(vs1)}},
            {"op": "insert_B", "result": {"content": content2, "vspans": vspec_to_dict(vs2)}},
            {"op": "delete_A", "result": {"content": content3, "vspans": vspec_to_dict(vs3)}},
            {"op": "insert_C", "result": {"content": content4, "vspans": vspec_to_dict(vs4)}},
            {"op": "compare_via_transclusion", "result": {
                "shared_span_pairs": len(comparison),
                "shared": comparison_result
            }},
            {"op": "note", "text": "If monotonic, C's I-address should follow B's, not reuse A's"}
        ]
    }


SCENARIOS = [
    ("iaddress_allocation", "interleaved_insert_delete", scenario_interleaved_insert_delete),
    ("iaddress_allocation", "consecutive_inserts_monotonic", scenario_consecutive_inserts_monotonic),
    ("iaddress_allocation", "delete_does_not_affect_next_insert", scenario_delete_does_not_affect_next_insert),
]
