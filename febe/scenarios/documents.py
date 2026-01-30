"""Document creation and management scenarios."""

from client import (
    Address, Offset, Span, SpecSet, VSpec,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, specset_to_list


def scenario_create_document(session):
    """Create a document and verify its address."""
    docid = session.create_document()
    return {
        "name": "create_document",
        "description": "Create a new empty document",
        "operations": [
            {"op": "create_document", "result": str(docid)}
        ]
    }


def scenario_multiple_documents(session):
    """Create and populate multiple independent documents."""
    # Create and populate first document
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document One"])
    vspanset1 = session.retrieve_vspanset(opened1)
    specset1 = SpecSet(VSpec(opened1, list(vspanset1.spans)))
    contents1 = session.retrieve_contents(specset1)
    session.close_document(opened1)

    # Create and populate second document
    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document Two"])
    vspanset2 = session.retrieve_vspanset(opened2)
    specset2 = SpecSet(VSpec(opened2, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)
    session.close_document(opened2)

    return {
        "name": "multiple_documents",
        "description": "Create and populate multiple independent documents",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document One"},
            {"op": "retrieve_contents", "doc": str(opened1), "result": contents1},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document Two"},
            {"op": "retrieve_contents", "doc": str(opened2), "result": contents2},
            {"op": "close_document", "doc": str(opened2)}
        ]
    }


def scenario_read_only_access(session):
    """Open document read-only and verify content retrieval works."""
    # Create and populate document
    docid = session.create_document()
    opened_rw = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_rw, Address(1, 1), ["Content for read-only test"])
    session.close_document(opened_rw)

    # Reopen read-only
    opened_ro = session.open_document(docid, READ_ONLY, CONFLICT_FAIL)
    vspanset = session.retrieve_vspanset(opened_ro)
    specset = SpecSet(VSpec(opened_ro, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)
    session.close_document(opened_ro)

    return {
        "name": "read_only_access",
        "description": "Open document read-only and retrieve content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_rw)},
            {"op": "insert", "doc": str(opened_rw), "address": "1.1", "text": "Content for read-only test"},
            {"op": "close_document", "doc": str(opened_rw)},
            {"op": "open_document", "doc": str(docid), "mode": "read_only", "result": str(opened_ro)},
            {"op": "retrieve_vspanset", "doc": str(opened_ro), "result": vspec_to_dict(vspanset)},
            {"op": "retrieve_contents", "doc": str(opened_ro), "result": contents},
            {"op": "close_document", "doc": str(opened_ro)}
        ]
    }


def scenario_reopen_document(session):
    """Close and reopen a document, verifying content persists."""
    docid = session.create_document()

    # First open: insert content
    opened1 = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Persistent content"])
    vspanset1 = session.retrieve_vspanset(opened1)
    session.close_document(opened1)

    # Second open: verify content still there
    opened2 = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    vspanset2 = session.retrieve_vspanset(opened2)
    specset = SpecSet(VSpec(opened2, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    # Append more content
    session.insert(opened2, vspanset2.spans[0].end(), [" with additions"])
    vspanset3 = session.retrieve_vspanset(opened2)
    specset3 = SpecSet(VSpec(opened2, list(vspanset3.spans)))
    contents3 = session.retrieve_contents(specset3)
    session.close_document(opened2)

    return {
        "name": "reopen_document",
        "description": "Close and reopen a document, verifying content persists",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Persistent content"},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened2),
             "comment": "Reopen same document"},
            {"op": "retrieve_contents", "doc": str(opened2), "result": contents,
             "comment": "Content persisted across close/open"},
            {"op": "insert", "doc": str(opened2), "address": str(vspanset2.spans[0].end()),
             "text": " with additions"},
            {"op": "retrieve_contents", "doc": str(opened2), "result": contents3},
            {"op": "close_document", "doc": str(opened2)}
        ]
    }


def scenario_conflict_copy(session):
    """Open a document while already open using CONFLICT_COPY mode."""
    docid = session.create_document()

    # First open for writing
    opened1 = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Shared document content"])
    vspanset1 = session.retrieve_vspanset(opened1)

    # Second open with CONFLICT_COPY (creates a copy)
    opened2 = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    vspanset2 = session.retrieve_vspanset(opened2)
    specset2 = SpecSet(VSpec(opened2, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "conflict_copy",
        "description": "Open a document while already open using CONFLICT_COPY",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Shared document content"},
            {"op": "open_document", "doc": str(docid), "mode": "read_only", "conflict": "copy",
             "result": str(opened2), "comment": "Second open while first still open"},
            {"op": "retrieve_contents", "doc": str(opened2), "result": contents2},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "close_document", "doc": str(opened2)}
        ]
    }


def scenario_find_documents(session):
    """Find documents that contain specific content."""
    # Create multiple documents with some shared content (via vcopy)
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document with unique content"])
    vspanset1 = session.retrieve_vspanset(opened1)
    session.close_document(opened1)

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Another document here"])
    session.close_document(opened2)

    # Search for documents containing content from doc1
    opened1_ro = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    search_specs = SpecSet(VSpec(opened1_ro, [Span(Address(1, 1), Offset(0, 8))]))  # "Document"
    found_docs = session.find_documents(search_specs)
    session.close_document(opened1_ro)

    return {
        "name": "find_documents",
        "description": "Find documents containing specific content",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document with unique content"},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Another document here"},
            {"op": "close_document", "doc": str(opened2)},
            {"op": "find_documents",
             "search": specset_to_list(search_specs),
             "result": [str(d) for d in found_docs]}
        ]
    }


SCENARIOS = [
    ("documents", "create_document", scenario_create_document),
    ("documents", "multiple_documents", scenario_multiple_documents),
    ("documents", "read_only_access", scenario_read_only_access),
    ("documents", "reopen_document", scenario_reopen_document),
    ("documents", "conflict_copy", scenario_conflict_copy),
    ("documents", "find_documents", scenario_find_documents),
]
