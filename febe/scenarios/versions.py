"""Version creation and comparison scenarios."""

from client import Address, SpecSet, VSpec, READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
from .common import vspec_to_dict, span_to_dict


def scenario_create_version(session):
    """Create document, insert text, create version, modify version."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text in original
    session.insert(opened_docid, Address(1, 1), ["Original text"])
    vspanset1 = session.retrieve_vspanset(opened_docid)
    session.close_document(opened_docid)

    # Create version
    version_docid = session.create_version(docid)
    opened_version = session.open_document(version_docid, READ_WRITE, CONFLICT_FAIL)

    # Insert more text in version
    version_vspanset = session.retrieve_vspanset(opened_version)
    session.insert(opened_version, version_vspanset.spans[0].end(), [" with additions"])

    # Retrieve both versions
    orig_opened = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    orig_vspanset = session.retrieve_vspanset(orig_opened)
    orig_specset = SpecSet(VSpec(orig_opened, list(orig_vspanset.spans)))
    orig_contents = session.retrieve_contents(orig_specset)

    new_vspanset = session.retrieve_vspanset(opened_version)
    new_specset = SpecSet(VSpec(opened_version, list(new_vspanset.spans)))
    new_contents = session.retrieve_contents(new_specset)

    session.close_document(orig_opened)
    session.close_document(opened_version)

    return {
        "name": "create_version",
        "description": "Create document, insert text, create version, modify version",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Original text"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "close_document", "doc": str(opened_docid)},
            {"op": "create_version", "doc": str(docid), "result": str(version_docid)},
            {"op": "open_document", "doc": str(version_docid), "mode": "read_write", "result": str(opened_version)},
            {"op": "insert", "doc": str(opened_version), "address": str(version_vspanset.spans[0].end()), "text": " with additions"},
            {"op": "retrieve_contents", "doc": str(orig_opened), "result": orig_contents},
            {"op": "retrieve_contents", "doc": str(opened_version), "result": new_contents}
        ]
    }


def scenario_compare_versions(session):
    """Create two versions and compare them."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text in original
    session.insert(opened_docid, Address(1, 1), ["Shared text that stays the same"])
    session.close_document(opened_docid)

    # Create version
    version_docid = session.create_version(docid)
    opened_version = session.open_document(version_docid, READ_WRITE, CONFLICT_FAIL)

    # Modify version
    version_vspanset = session.retrieve_vspanset(opened_version)
    session.insert(opened_version, version_vspanset.spans[0].end(), [" plus new"])
    session.close_document(opened_version)

    # Compare versions (open both for reading)
    orig_opened = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    version_opened = session.open_document(version_docid, READ_ONLY, CONFLICT_COPY)

    orig_vspanset = session.retrieve_vspanset(orig_opened)
    new_vspanset = session.retrieve_vspanset(version_opened)

    orig_specset = SpecSet(VSpec(orig_opened, list(orig_vspanset.spans)))
    new_specset = SpecSet(VSpec(version_opened, list(new_vspanset.spans)))

    shared = session.compare_versions(orig_specset, new_specset)

    # Convert shared spans to serializable format
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "b": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(orig_opened)
    session.close_document(version_opened)

    return {
        "name": "compare_versions",
        "description": "Create two versions and compare them to find shared content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Shared text that stays the same"},
            {"op": "close_document", "doc": str(opened_docid)},
            {"op": "create_version", "doc": str(docid), "result": str(version_docid)},
            {"op": "open_document", "doc": str(version_docid), "mode": "read_write", "result": str(opened_version)},
            {"op": "insert", "doc": str(opened_version), "address": str(version_vspanset.spans[0].end()), "text": " plus new"},
            {"op": "close_document", "doc": str(opened_version)},
            {"op": "compare_versions", "doc_a": str(orig_opened), "doc_b": str(version_opened), "result": shared_result}
        ]
    }


SCENARIOS = [
    ("versions", "create_version", scenario_create_version),
    ("versions", "compare_versions", scenario_compare_versions),
]
