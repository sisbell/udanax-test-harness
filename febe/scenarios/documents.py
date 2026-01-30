"""Document creation and management scenarios."""

from client import Address, SpecSet, VSpec, READ_WRITE, CONFLICT_FAIL
from .common import vspec_to_dict


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


SCENARIOS = [
    ("documents", "create_document", scenario_create_document),
    ("documents", "multiple_documents", scenario_multiple_documents),
]
