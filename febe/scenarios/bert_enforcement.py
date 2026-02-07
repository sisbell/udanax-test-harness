"""BERT token enforcement scenarios."""

from client import (
    Address, Offset, Span, SpecSet, VSpec,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, specset_to_list


def scenario_insert_without_write_token(session):
    """Attempt to INSERT without acquiring a WRITE token first."""
    # Create a document
    docid = session.create_document()

    # Open for READ only
    opened_doc = session.open_document(docid, READ_ONLY, CONFLICT_FAIL)

    # Try to INSERT without WRITE token - should fail
    try:
        session.insert(opened_doc, Address(1, 1), ["Unauthorized insert"])
        result = "OPERATION_SUCCEEDED"  # Should not reach here
    except Exception as e:
        result = f"OPERATION_FAILED: {str(e)}"

    session.close_document(opened_doc)

    return {
        "name": "insert_without_write_token",
        "description": "Attempt INSERT with only READ token - back end should reject",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_only", "result": str(opened_doc)},
            {"op": "insert", "doc": str(opened_doc), "address": "1.1", "text": "Unauthorized insert", "result": result},
            {"op": "close_document", "doc": str(opened_doc)}
        ]
    }


def scenario_delete_without_write_token(session):
    """Attempt to DELETE without acquiring a WRITE token first."""
    # Create and populate a document
    docid = session.create_document()
    opened_for_write = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_for_write, Address(1, 1), ["Content to delete"])
    session.close_document(opened_for_write)

    # Re-open for READ only
    opened_for_read = session.open_document(docid, READ_ONLY, CONFLICT_FAIL)

    # Try to DELETE without WRITE token - should fail
    try:
        session.delete_vspan(opened_for_read, Span(Address(1, 1), Offset(1, 17)))
        result = "OPERATION_SUCCEEDED"  # Should not reach here
    except Exception as e:
        result = f"OPERATION_FAILED: {str(e)}"

    session.close_document(opened_for_read)

    return {
        "name": "delete_without_write_token",
        "description": "Attempt DELETEVSPAN with only READ token - back end should reject",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_for_write)},
            {"op": "insert", "doc": str(opened_for_write), "address": "1.1", "text": "Content to delete"},
            {"op": "close_document", "doc": str(opened_for_write)},
            {"op": "open_document", "doc": str(docid), "mode": "read_only", "result": str(opened_for_read)},
            {"op": "delete_vspan", "doc": str(opened_for_read), "span": "1.1+1.17", "result": result},
            {"op": "close_document", "doc": str(opened_for_read)}
        ]
    }


def scenario_rearrange_without_write_token(session):
    """Attempt to REARRANGE without acquiring a WRITE token first."""
    # Create and populate a document
    docid = session.create_document()
    opened_for_write = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_for_write, Address(1, 1), ["ABCDEF"])
    session.close_document(opened_for_write)

    # Re-open for READ only
    opened_for_read = session.open_document(docid, READ_ONLY, CONFLICT_FAIL)

    # Try to REARRANGE without WRITE token - should fail
    try:
        # Swap positions: DEF ABC
        session.rearrange(opened_for_read, [
            (Span(Address(1, 1), Offset(1, 3)), Address(1, 7)),  # ABC to position 1.7
            (Span(Address(1, 4), Offset(1, 3)), Address(1, 1))   # DEF to position 1.1
        ])
        result = "OPERATION_SUCCEEDED"  # Should not reach here
    except Exception as e:
        result = f"OPERATION_FAILED: {str(e)}"

    session.close_document(opened_for_read)

    return {
        "name": "rearrange_without_write_token",
        "description": "Attempt REARRANGE with only READ token - back end should reject",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_for_write)},
            {"op": "insert", "doc": str(opened_for_write), "address": "1.1", "text": "ABCDEF"},
            {"op": "close_document", "doc": str(opened_for_write)},
            {"op": "open_document", "doc": str(docid), "mode": "read_only", "result": str(opened_for_read)},
            {"op": "rearrange", "doc": str(opened_for_read), "result": result},
            {"op": "close_document", "doc": str(opened_for_read)}
        ]
    }


def scenario_copy_without_write_token_on_target(session):
    """Attempt to COPY into a document without WRITE token on the target."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source content"])
    source_vspanset = session.retrieve_vspanset(source_opened)
    source_specset = SpecSet(VSpec(source_opened, list(source_vspanset.spans)))

    # Create target document
    target_doc = session.create_document()
    target_opened_read = session.open_document(target_doc, READ_ONLY, CONFLICT_FAIL)

    # Try to COPY into target without WRITE token - should fail
    try:
        session.copy(target_opened_read, Address(1, 1), source_specset)
        result = "OPERATION_SUCCEEDED"  # Should not reach here
    except Exception as e:
        result = f"OPERATION_FAILED: {str(e)}"

    session.close_document(source_opened)
    session.close_document(target_opened_read)

    return {
        "name": "copy_without_write_token_on_target",
        "description": "Attempt COPY into target document with only READ token - back end should reject",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Source content"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_only", "result": str(target_opened_read)},
            {"op": "copy", "target_doc": str(target_opened_read), "address": "1.1", "result": result},
            {"op": "close_document", "doc": str(source_opened)},
            {"op": "close_document", "doc": str(target_opened_read)}
        ]
    }


SCENARIOS = [
    scenario_insert_without_write_token,
    scenario_delete_without_write_token,
    scenario_rearrange_without_write_token,
    scenario_copy_without_write_token_on_target,
]
