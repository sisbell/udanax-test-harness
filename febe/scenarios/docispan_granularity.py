"""Test scenario to determine DOCISPAN entry granularity.

This test determines whether DOCISPAN entries are created per-span or per-byte:
- INSERT k contiguous bytes: 1 DOCISPAN entry for the span, or k entries?
- COPY k contiguous bytes: 1 DOCISPAN entry for the span, or k entries?
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_docispan_granularity_insert_contiguous(session):
    """Test DOCISPAN granularity for a single INSERT of contiguous bytes.

    We insert 10 contiguous bytes "ABCDEFGHIJ" via a single INSERT.
    According to Finding 033, this creates contiguous I-addresses that
    consolidate into a single I-span.

    Question: Does insertspanf create ONE DOCISPAN entry for the entire
    I-span, or does it create 10 separate DOCISPAN entries (one per byte)?

    We can infer this by examining how the spanfilade is used during queries.
    """
    # Create document and insert 10 contiguous bytes
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["ABCDEFGHIJ"])

    # Try searching for single byte vs. multi-byte spans
    # If DOCISPAN is per-byte, both should work equally
    # If DOCISPAN is per-span, both should still work (enfilade queries are range-based)

    # Search for single byte 'A'
    search_a = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 1))]))
    found_a = session.find_documents(search_a)

    # Search for 3 bytes 'ABC'
    search_abc = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 3))]))
    found_abc = session.find_documents(search_abc)

    # Search for middle byte 'F'
    search_f = SpecSet(VSpec(opened, [Span(Address(1, 6), Offset(0, 1))]))
    found_f = session.find_documents(search_f)

    # Search for all 10 bytes
    search_all = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
    found_all = session.find_documents(search_all)

    session.close_document(opened)

    return {
        "name": "docispan_granularity_insert_contiguous",
        "description": "Test DOCISPAN granularity for contiguous INSERT",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "ABCDEFGHIJ (10 bytes)", "position": "1.1"},
            {"op": "find_documents", "search": "A (1 byte)",
             "result": [str(d) for d in found_a]},
            {"op": "find_documents", "search": "ABC (3 bytes)",
             "result": [str(d) for d in found_abc]},
            {"op": "find_documents", "search": "F (middle byte)",
             "result": [str(d) for d in found_f]},
            {"op": "find_documents", "search": "ABCDEFGHIJ (all 10 bytes)",
             "result": [str(d) for d in found_all]},
        ],
        "analysis": {
            "comment": "All searches should find the document regardless of DOCISPAN granularity, "
                      "because enfilade queries are range-based. The granularity affects storage "
                      "efficiency, not query results."
        }
    }


def scenario_docispan_granularity_multiple_inserts(session):
    """Test DOCISPAN granularity for multiple separate INSERTs.

    Insert 10 bytes via 10 separate single-byte INSERTs.
    According to Finding 033, these create contiguous I-addresses that
    consolidate into a single I-span when queried.

    Question: Does each INSERT create a separate DOCISPAN entry,
    or do they consolidate into one entry?
    """
    # Create document
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert 10 single bytes separately
    chars = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i, char in enumerate(chars):
        session.insert(opened, Address(1, 1 + i), [char])

    # Search for single byte 'A'
    search_a = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 1))]))
    found_a = session.find_documents(search_a)

    # Search for 3 bytes 'ABC'
    search_abc = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 3))]))
    found_abc = session.find_documents(search_abc)

    # Search for all 10 bytes
    search_all = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
    found_all = session.find_documents(search_all)

    session.close_document(opened)

    return {
        "name": "docispan_granularity_multiple_inserts",
        "description": "Test DOCISPAN granularity for multiple separate INSERTs",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "count": 10, "description": "10 separate single-byte INSERTs"},
            {"op": "find_documents", "search": "A (1 byte)",
             "result": [str(d) for d in found_a]},
            {"op": "find_documents", "search": "ABC (3 bytes)",
             "result": [str(d) for d in found_abc]},
            {"op": "find_documents", "search": "ABCDEFGHIJ (all 10 bytes)",
             "result": [str(d) for d in found_all]},
        ],
        "analysis": {
            "comment": "Compare with single INSERT test. If results identical, DOCISPAN entries "
                      "may be consolidating. If different... that would be surprising given "
                      "Finding 033's I-span consolidation."
        }
    }


def scenario_docispan_granularity_copy_contiguous(session):
    """Test DOCISPAN granularity for COPY of contiguous bytes.

    Copy 10 contiguous bytes from one document to another.
    Does docopy create ONE DOCISPAN entry for the entire span,
    or 10 separate entries?
    """
    # Create source document with content
    source = session.create_document()
    s_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(s_opened, Address(1, 1), ["ABCDEFGHIJ"])
    session.close_document(s_opened)

    # Create dest document and copy all 10 bytes
    dest = session.create_document()
    d_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    s_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(s_read, [Span(Address(1, 1), Offset(0, 10))]))
    session.vcopy(d_opened, Address(1, 1), copy_spec)
    session.close_document(s_read)

    # Search for content in dest document
    search_a = SpecSet(VSpec(d_opened, [Span(Address(1, 1), Offset(0, 1))]))
    found_a = session.find_documents(search_a)

    search_all = SpecSet(VSpec(d_opened, [Span(Address(1, 1), Offset(0, 10))]))
    found_all = session.find_documents(search_all)

    session.close_document(d_opened)

    return {
        "name": "docispan_granularity_copy_contiguous",
        "description": "Test DOCISPAN granularity for COPY of contiguous span",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "ABCDEFGHIJ"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "bytes": 10},
            {"op": "find_documents", "search": "A (1 byte) in dest",
             "result": [str(d) for d in found_a]},
            {"op": "find_documents", "search": "ABCDEFGHIJ (all 10 bytes) in dest",
             "result": [str(d) for d in found_all]},
        ],
        "analysis": {
            "comment": "COPY calls insertspanf with ispanset. The ispanset contains I-spans, "
                      "not individual bytes. So COPY should create one DOCISPAN entry per I-span."
        }
    }


SCENARIOS = [
    ("internal", "docispan_granularity_insert_contiguous", scenario_docispan_granularity_insert_contiguous),
    ("internal", "docispan_granularity_multiple_inserts", scenario_docispan_granularity_multiple_inserts),
    ("internal", "docispan_granularity_copy_contiguous", scenario_docispan_granularity_copy_contiguous),
]
