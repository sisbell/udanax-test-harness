"""Test allocation independence between different operation types.

This test validates EWD-013's claims about independent allocation counters:
1. INSERT allocates under addr(d).0.3 (element subspace 3)
2. MAKELINK allocates under addr(d).0.2 (element subspace 2)
3. VERSION allocates at document level, under addr(d)
4. These allocations use independent counters

The test interleaves these operations to check if allocation from one
operation affects the addresses allocated by another.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_insert_link_allocation_independence(session):
    """Test that INSERT and MAKELINK use independent allocation counters.

    EWD-013 claims:
    - INSERT allocates under addr(d).0.3 using counter A(addr(d), 3)
    - MAKELINK allocates under addr(d).0.2 using counter A(addr(d), 2)
    - These are independent by A1'

    Test pattern:
    1. INSERT text → allocates under .0.3.1
    2. MAKELINK → allocates under .0.2.1
    3. INSERT more text → should allocate under .0.3.2 (not .0.3.3)
    4. MAKELINK again → should allocate under .0.2.2 (not .0.2.3)

    This tests if the counters are truly independent.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT #1: "AAA" → should get .0.3.1, .0.3.2, .0.3.3
    session.insert(opened, Address(1, 1), ["AAA"])
    vs1 = session.retrieve_vspanset(opened)

    # MAKELINK #1: link from doc → should get .0.2.1 (independent of text)
    link_from = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 1))]))
    link_to = SpecSet(VSpec(opened, [Span(Address(1, 2), Offset(0, 1))]))
    link_type = SpecSet()  # empty type set
    link1_result = session.create_link(opened, link_from, link_to, link_type)
    links1 = session.find_links(link_from)

    # INSERT #2: "BBB" → should get .0.3.4, .0.3.5, .0.3.6 (continuing from text counter)
    session.insert(opened, Address(1, 4), ["BBB"])
    vs2 = session.retrieve_vspanset(opened)

    # MAKELINK #2: another link → should get .0.2.2 (continuing from link counter)
    link2_from = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 2))]))
    link2_to = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 1))]))
    link2_result = session.create_link(opened, link2_from, link2_to, link_type)
    links2 = session.find_links(link2_from)

    # INSERT #3: "CCC" → should get .0.3.7, .0.3.8, .0.3.9 (text counter unaffected by links)
    session.insert(opened, Address(1, 7), ["CCC"])
    vs3 = session.retrieve_vspanset(opened)

    # Get final content
    spec_final = SpecSet(VSpec(opened, list(vs3.spans)))
    content_final = session.retrieve_contents(spec_final)

    session.close_document(opened)

    # Extract I-addresses from vspans to analyze allocation
    def extract_spans(vspanset):
        """Extract span information from vspanset."""
        return [span_to_dict(span) for span in vspanset.spans]

    return {
        "name": "insert_link_allocation_independence",
        "description": "Verify INSERT and MAKELINK use independent allocation counters",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert_1_AAA", "result": {
                "vspans": extract_spans(vs1),
                "expected": "I-addresses under .0.3.1, .0.3.2, .0.3.3"
            }},
            {"op": "makelink_1", "result": {
                "link": str(link1_result),
                "links_found": len(links1),
                "expected": "Link I-address under .0.2.1"
            }},
            {"op": "insert_2_BBB", "result": {
                "vspans": extract_spans(vs2),
                "expected": "I-addresses continue at .0.3.4 (link did not affect text counter)"
            }},
            {"op": "makelink_2", "result": {
                "link": str(link2_result),
                "links_found": len(links2),
                "expected": "Link I-address continues at .0.2.2 (text did not affect link counter)"
            }},
            {"op": "insert_3_CCC", "result": {
                "vspans": extract_spans(vs3),
                "content": content_final,
                "expected": "I-addresses continue at .0.3.7 (links did not affect text counter)"
            }},
        ]
    }


def scenario_version_insert_allocation_independence(session):
    """Test that VERSION and INSERT use independent allocation counters.

    EWD-013 claims:
    - INSERT allocates at element level under addr(d).0.3
    - VERSION allocates at document level under addr(d)
    - These use different counters: A(addr(d), 3) vs A_doc(addr(d))

    Test pattern:
    1. Create document d → gets address 1.1.0.1.0.1
    2. INSERT text into d → allocates under 1.1.0.1.0.1.0.3.x
    3. VERSION d → should allocate child document at 1.1.0.1.0.1.1 (doc-level counter)
    4. INSERT more text into d → should continue from element-level counter
    5. VERSION d again → should allocate at 1.1.0.1.0.1.2 (doc-level counter)

    This tests if document-level and element-level counters are independent.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT #1: Add some text
    session.insert(opened, Address(1, 1), ["AAA"])
    vs1 = session.retrieve_vspanset(opened)

    # VERSION #1: Create first version (should be docid.1)
    session.close_document(opened)
    ver1 = session.create_version(docid)

    # Re-open original document
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT #2: Add more text (element counter should be unaffected by VERSION)
    session.insert(opened, Address(1, 4), ["BBB"])
    vs2 = session.retrieve_vspanset(opened)

    # VERSION #2: Create second version (should be docid.2)
    session.close_document(opened)
    ver2 = session.create_version(docid)

    # Re-open original document
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT #3: Add more text
    session.insert(opened, Address(1, 7), ["CCC"])
    vs3 = session.retrieve_vspanset(opened)

    # Get final content
    spec_final = SpecSet(VSpec(opened, list(vs3.spans)))
    content_final = session.retrieve_contents(spec_final)

    session.close_document(opened)

    # Extract span information from vspans
    def extract_spans(vspanset):
        return [span_to_dict(span) for span in vspanset.spans]

    return {
        "name": "version_insert_allocation_independence",
        "description": "Verify VERSION and INSERT use independent allocation counters",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "result": str(opened)},
            {"op": "insert_1_AAA", "result": {
                "vspans": extract_spans(vs1),
                "expected": "Element-level: .0.3.1, .0.3.2, .0.3.3"
            }},
            {"op": "version_1", "result": {
                "version": str(ver1),
                "expected": f"Document-level child: {docid}.1"
            }},
            {"op": "insert_2_BBB", "result": {
                "vspans": extract_spans(vs2),
                "expected": "Element-level continues: .0.3.4 (VERSION did not affect element counter)"
            }},
            {"op": "version_2", "result": {
                "version": str(ver2),
                "expected": f"Document-level continues: {docid}.2 (INSERT did not affect doc counter)"
            }},
            {"op": "insert_3_CCC", "result": {
                "vspans": extract_spans(vs3),
                "content": content_final,
                "expected": "Element-level continues: .0.3.7"
            }},
        ]
    }


def scenario_version_link_allocation_independence(session):
    """Test that VERSION and MAKELINK use independent allocation counters.

    EWD-013 Case 2 (VERSION-MAKELINK) claims these operations allocate
    under independent counters:
    - VERSION: document-level A_doc(addr(d))
    - MAKELINK: element-level A(addr(d), 2)

    Test pattern:
    1. Create doc, insert text
    2. MAKELINK → allocates at .0.2.1
    3. VERSION → allocates at doc.1
    4. MAKELINK → should allocate at .0.2.2 (unaffected by VERSION)
    5. VERSION → should allocate at doc.2 (unaffected by MAKELINK)
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # INSERT: Need some content to create links
    session.insert(opened, Address(1, 1), ["ABCDEF"])

    # MAKELINK #1
    link_from = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 1))]))
    link_to = SpecSet(VSpec(opened, [Span(Address(1, 2), Offset(0, 1))]))
    link_type = SpecSet()
    link1 = session.create_link(opened, link_from, link_to, link_type)

    # VERSION #1
    session.close_document(opened)
    ver1 = session.create_version(docid)

    # MAKELINK #2 (in original doc)
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    link2_from = SpecSet(VSpec(opened, [Span(Address(1, 3), Offset(0, 1))]))
    link2_to = SpecSet(VSpec(opened, [Span(Address(1, 4), Offset(0, 1))]))
    link2 = session.create_link(opened, link2_from, link2_to, link_type)

    # VERSION #2
    session.close_document(opened)
    ver2 = session.create_version(docid)

    # MAKELINK #3 (in original doc)
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    link3_from = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 1))]))
    link3_to = SpecSet(VSpec(opened, [Span(Address(1, 6), Offset(0, 1))]))
    link3 = session.create_link(opened, link3_from, link3_to, link_type)

    session.close_document(opened)

    return {
        "name": "version_link_allocation_independence",
        "description": "Verify VERSION and MAKELINK use independent allocation counters",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert_text", "text": "ABCDEF"},
            {"op": "makelink_1", "result": {
                "link": str(link1),
                "expected": "Link at .0.2.1"
            }},
            {"op": "version_1", "result": {
                "version": str(ver1),
                "expected": f"{docid}.1"
            }},
            {"op": "makelink_2", "result": {
                "link": str(link2),
                "expected": "Link at .0.2.2 (VERSION did not affect link counter)"
            }},
            {"op": "version_2", "result": {
                "version": str(ver2),
                "expected": f"{docid}.2 (MAKELINK did not affect doc counter)"
            }},
            {"op": "makelink_3", "result": {
                "link": str(link3),
                "expected": "Link at .0.2.3"
            }},
        ]
    }


def scenario_all_operations_interleaved(session):
    """Comprehensive test: interleave INSERT, MAKELINK, VERSION, DELETE, COPY.

    EWD-013 claims:
    - INSERT allocates under .0.3 using A(addr(d), 3)
    - MAKELINK allocates under .0.2 using A(addr(d), 2)
    - VERSION allocates at doc level using A_doc(addr(d))
    - DELETE performs no allocation
    - COPY performs no allocation (reuses I-addresses)

    This test interleaves all operations to verify allocation independence.
    """
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)

    # INSERT #1: "AAA" → .0.3.1, .0.3.2, .0.3.3
    session.insert(opened1, Address(1, 1), ["AAA"])
    vs1 = session.retrieve_vspanset(opened1)

    # MAKELINK #1 → .0.2.1
    link_from = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 1))]))
    link_to = SpecSet(VSpec(opened1, [Span(Address(1, 2), Offset(0, 1))]))
    link_type = SpecSet()
    link1 = session.create_link(opened1, link_from, link_to, link_type)

    # VERSION #1 → doc1.1
    session.close_document(opened1)
    ver1 = session.create_version(doc1)

    # DELETE (should not affect allocation)
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.remove(opened1, Span(Address(1, 2), Offset(0, 1)))
    vs_after_delete = session.retrieve_vspanset(opened1)

    # INSERT #2: "BBB" → should continue at .0.3.4
    session.insert(opened1, Address(1, 3), ["BBB"])
    vs2 = session.retrieve_vspanset(opened1)

    # Create second document for COPY
    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)

    # COPY from doc1 to doc2 (should not allocate new I-addresses)
    read1 = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    vs_read = session.retrieve_vspanset(read1)
    copy_spec = SpecSet(VSpec(read1, list(vs_read.spans)))
    session.vcopy(opened2, Address(1, 1), copy_spec)
    vs_doc2 = session.retrieve_vspanset(opened2)
    session.close_document(read1)

    # MAKELINK #2 in doc1 → should continue at .0.2.2
    link2_from = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 2))]))
    link2_to = SpecSet(VSpec(opened1, [Span(Address(1, 4), Offset(0, 1))]))
    link2 = session.create_link(opened1, link2_from, link2_to, link_type)

    # VERSION #2 → doc1.2
    session.close_document(opened1)
    ver2 = session.create_version(doc1)

    # INSERT #3 in doc1 → should continue at .0.3.7
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 6), ["CCC"])
    vs3 = session.retrieve_vspanset(opened1)

    spec_final = SpecSet(VSpec(opened1, list(vs3.spans)))
    content_final = session.retrieve_contents(spec_final)

    session.close_document(opened1)
    session.close_document(opened2)

    def extract_spans(vspanset):
        return [span_to_dict(span) for span in vspanset.spans]

    return {
        "name": "all_operations_interleaved",
        "description": "Comprehensive test of allocation independence across all operations",
        "operations": [
            {"op": "create_doc1", "result": str(doc1)},
            {"op": "insert_1_AAA", "result": extract_spans(vs1)},
            {"op": "makelink_1", "result": str(link1)},
            {"op": "version_1", "result": str(ver1)},
            {"op": "delete", "result": extract_spans(vs_after_delete)},
            {"op": "insert_2_BBB", "result": extract_spans(vs2)},
            {"op": "create_doc2_and_copy", "result": {
                "doc2": str(doc2),
                "vspans_doc2": extract_spans(vs_doc2),
                "note": "COPY should reuse I-addresses, not allocate new ones"
            }},
            {"op": "makelink_2", "result": str(link2)},
            {"op": "version_2", "result": str(ver2)},
            {"op": "insert_3_CCC", "result": {
                "vspans": extract_spans(vs3),
                "content": content_final
            }},
            {"op": "summary", "expected_allocation": {
                "text_counter": "A(doc1, 3): 1,2,3 → 4,5,6 → 7,8,9",
                "link_counter": "A(doc1, 2): 1 → 2",
                "doc_counter": "A_doc(doc1): 1 → 2",
                "delete_effect": "none (DELETE does not allocate)",
                "copy_effect": "none (COPY reuses I-addresses)"
            }}
        ]
    }


SCENARIOS = [
    ("allocation_independence", "insert_link_allocation_independence", scenario_insert_link_allocation_independence),
    ("allocation_independence", "version_insert_allocation_independence", scenario_version_insert_allocation_independence),
    ("allocation_independence", "version_link_allocation_independence", scenario_version_link_allocation_independence),
    ("allocation_independence", "all_operations_interleaved", scenario_all_operations_interleaved),
]
