"""Test scenarios for INSERT operation's DOCISPAN creation.

These tests verify whether INSERT creates DOCISPAN entries (type 4)
in the spanfilade, which enables content discovery via find_documents.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_insert_creates_docispan(session):
    """Test if INSERT creates DOCISPAN entries for newly inserted content.

    We know:
    - COPY creates DOCISPAN entries (do1.c:62)
    - APPEND has DOCISPAN insertion commented out (do1.c:30)

    This test checks whether INSERT (via inserttextingranf + docopy)
    creates DOCISPAN entries that make the new content discoverable.
    """
    # Create document and INSERT new content
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Inserted text"])

    # Try to find documents containing the inserted content
    # If INSERT creates DOCISPAN, we should find this document
    search_spec = SpecSet(VSpec(doc_opened, [Span(Address(1, 1), Offset(0, 8))]))  # "Inserted"
    found_docs = session.find_documents(search_spec)

    session.close_document(doc_opened)

    return {
        "name": "insert_creates_docispan",
        "description": "Test if INSERT creates DOCISPAN entries for content discovery",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "Inserted text"},
            {"op": "find_documents",
             "search_text": "Inserted",
             "result": [str(d) for d in found_docs],
             "expected_if_docispan": [str(doc)],
             "comment": "If INSERT creates DOCISPAN, should find this document"}
        ]
    }


def scenario_insert_vs_append_docispan(session):
    """Compare INSERT and APPEND behavior for DOCISPAN creation.

    APPEND has insertspanf(DOCISPAN) commented out in do1.c:30.
    INSERT calls docopy which calls insertspanf(DOCISPAN) at do1.c:62.

    This test checks if they differ in content discoverability.
    """
    # Create document with INSERT
    doc_insert = session.create_document()
    di_opened = session.open_document(doc_insert, READ_WRITE, CONFLICT_FAIL)
    session.insert(di_opened, Address(1, 1), ["Via insert"])
    session.close_document(di_opened)

    # Create document with APPEND
    doc_append = session.create_document()
    da_opened = session.open_document(doc_append, READ_WRITE, CONFLICT_FAIL)
    session.append(da_opened, ["Via append"])
    session.close_document(da_opened)

    # Search for INSERT content
    di_read = session.open_document(doc_insert, READ_ONLY, CONFLICT_COPY)
    search_insert = SpecSet(VSpec(di_read, [Span(Address(1, 1), Offset(0, 10))]))  # "Via insert"
    found_insert = session.find_documents(search_insert)
    session.close_document(di_read)

    # Search for APPEND content
    da_read = session.open_document(doc_append, READ_ONLY, CONFLICT_COPY)
    search_append = SpecSet(VSpec(da_read, [Span(Address(1, 1), Offset(0, 10))]))  # "Via append"
    found_append = session.find_documents(search_append)
    session.close_document(da_read)

    return {
        "name": "insert_vs_append_docispan",
        "description": "Compare INSERT vs APPEND for DOCISPAN creation",
        "operations": [
            {"op": "create_document", "doc": "insert", "result": str(doc_insert)},
            {"op": "insert", "doc": "insert", "text": "Via insert"},
            {"op": "create_document", "doc": "append", "result": str(doc_append)},
            {"op": "append", "doc": "append", "text": "Via append"},
            {"op": "find_documents",
             "search_from": "insert",
             "result": [str(d) for d in found_insert],
             "comment": "INSERT content discoverability"},
            {"op": "find_documents",
             "search_from": "append",
             "result": [str(d) for d in found_append],
             "comment": "APPEND content discoverability (DOCISPAN commented out)"}
        ]
    }


def scenario_insert_content_discoverable_elsewhere(session):
    """Test if INSERT-created content is discoverable from other documents.

    If INSERT creates DOCISPAN entries, then another document that
    transcludes the inserted content should be able to discover it.
    """
    # Create source with INSERT
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Discover this"])
    session.close_document(source_opened)

    # Create dest and transclude from source
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 8))]))  # "Discover"
    session.vcopy(dest_opened, Address(1, 1), copy_spec)
    session.close_document(dest_opened)

    # Find documents containing "Discover"
    # If INSERT created DOCISPAN, we should find both source and dest
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 8))]))
    found_docs = session.find_documents(search_spec)
    session.close_document(source_read)

    return {
        "name": "insert_content_discoverable_elsewhere",
        "description": "Test if INSERT-created content is discoverable via transclusion",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Discover this"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "text": "Discover"},
            {"op": "find_documents",
             "search_text": "Discover",
             "result": [str(d) for d in found_docs],
             "expected_if_docispan": 2,
             "comment": "Should find both source and dest if INSERT creates DOCISPAN"}
        ]
    }


def scenario_insert_multiple_times_accumulates_docispan(session):
    """Test if multiple INSERTs accumulate DOCISPAN entries.

    Each INSERT should create new DOCISPAN entries for the new content.
    """
    # Create document and INSERT multiple times
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(doc_opened, Address(1, 1), ["First "])
    doc_vs1 = session.retrieve_vspanset(doc_opened)
    session.insert(doc_opened, doc_vs1.spans[0].end(), ["Second "])
    doc_vs2 = session.retrieve_vspanset(doc_opened)
    session.insert(doc_opened, doc_vs2.spans[0].end(), ["Third"])

    # Search for "First"
    search_first = SpecSet(VSpec(doc_opened, [Span(Address(1, 1), Offset(0, 5))]))
    found_first = session.find_documents(search_first)

    # Search for "Second"
    search_second = SpecSet(VSpec(doc_opened, [Span(Address(1, 7), Offset(0, 6))]))
    found_second = session.find_documents(search_second)

    # Search for "Third"
    search_third = SpecSet(VSpec(doc_opened, [Span(Address(1, 14), Offset(0, 5))]))
    found_third = session.find_documents(search_third)

    session.close_document(doc_opened)

    return {
        "name": "insert_multiple_times_accumulates_docispan",
        "description": "Test if multiple INSERTs create multiple DOCISPAN entries",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "First ", "position": "1.1"},
            {"op": "insert", "text": "Second ", "position": "after First"},
            {"op": "insert", "text": "Third", "position": "after Second"},
            {"op": "find_documents",
             "search_text": "First",
             "result": [str(d) for d in found_first],
             "comment": "Search for first insertion"},
            {"op": "find_documents",
             "search_text": "Second",
             "result": [str(d) for d in found_second],
             "comment": "Search for second insertion"},
            {"op": "find_documents",
             "search_text": "Third",
             "result": [str(d) for d in found_third],
             "comment": "Search for third insertion"}
        ]
    }


SCENARIOS = [
    ("discovery", "insert_creates_docispan", scenario_insert_creates_docispan),
    ("discovery", "insert_vs_append_docispan", scenario_insert_vs_append_docispan),
    ("discovery", "insert_content_discoverable_elsewhere", scenario_insert_content_discoverable_elsewhere),
    ("discovery", "insert_multiple_times_accumulates_docispan", scenario_insert_multiple_times_accumulates_docispan),
]
