"""Internal state inspection scenarios."""

from client import Address, VSpec, SpecSet, READ_WRITE, CONFLICT_FAIL
from .common import vspec_to_dict


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


SCENARIOS = [
    ("internal", "internal_state", scenario_internal_state),
]
