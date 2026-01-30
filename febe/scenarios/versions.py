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


def scenario_version_chain(session):
    """Create a chain of versions (version of a version)."""
    # Create original document
    doc_v1 = session.create_document()
    opened_v1 = session.open_document(doc_v1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_v1, Address(1, 1), ["Version 1 content"])
    session.close_document(opened_v1)

    # Create version 2 from version 1
    doc_v2 = session.create_version(doc_v1)
    opened_v2 = session.open_document(doc_v2, READ_WRITE, CONFLICT_FAIL)
    v2_vspanset = session.retrieve_vspanset(opened_v2)
    session.insert(opened_v2, v2_vspanset.spans[0].end(), [" + v2 additions"])
    session.close_document(opened_v2)

    # Create version 3 from version 2
    doc_v3 = session.create_version(doc_v2)
    opened_v3 = session.open_document(doc_v3, READ_WRITE, CONFLICT_FAIL)
    v3_vspanset = session.retrieve_vspanset(opened_v3)
    session.insert(opened_v3, v3_vspanset.spans[0].end(), [" + v3 additions"])

    # Get all contents
    v1_opened = session.open_document(doc_v1, READ_ONLY, CONFLICT_COPY)
    v1_vspanset = session.retrieve_vspanset(v1_opened)
    v1_contents = session.retrieve_contents(SpecSet(VSpec(v1_opened, list(v1_vspanset.spans))))

    v2_opened = session.open_document(doc_v2, READ_ONLY, CONFLICT_COPY)
    v2_vspanset_final = session.retrieve_vspanset(v2_opened)
    v2_contents = session.retrieve_contents(SpecSet(VSpec(v2_opened, list(v2_vspanset_final.spans))))

    v3_vspanset_final = session.retrieve_vspanset(opened_v3)
    v3_contents = session.retrieve_contents(SpecSet(VSpec(opened_v3, list(v3_vspanset_final.spans))))

    session.close_document(v1_opened)
    session.close_document(v2_opened)
    session.close_document(opened_v3)

    return {
        "name": "version_chain",
        "description": "Create a chain of versions (v1 -> v2 -> v3)",
        "operations": [
            {"op": "create_document", "result": str(doc_v1)},
            {"op": "insert", "doc": str(doc_v1), "text": "Version 1 content"},
            {"op": "create_version", "from": str(doc_v1), "result": str(doc_v2)},
            {"op": "insert", "doc": str(doc_v2), "text": " + v2 additions"},
            {"op": "create_version", "from": str(doc_v2), "result": str(doc_v3)},
            {"op": "insert", "doc": str(doc_v3), "text": " + v3 additions"},
            {"op": "retrieve_contents", "doc": str(doc_v1), "result": v1_contents},
            {"op": "retrieve_contents", "doc": str(doc_v2), "result": v2_contents},
            {"op": "retrieve_contents", "doc": str(doc_v3), "result": v3_contents}
        ]
    }


def scenario_multiple_versions_same_source(session):
    """Create multiple independent versions from the same source."""
    # Create original document
    original = session.create_document()
    opened_orig = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_orig, Address(1, 1), ["Original shared content"])
    session.close_document(opened_orig)

    # Create three independent versions
    versions = []
    for i in range(3):
        version_doc = session.create_version(original)
        opened_ver = session.open_document(version_doc, READ_WRITE, CONFLICT_FAIL)
        ver_vspanset = session.retrieve_vspanset(opened_ver)
        session.insert(opened_ver, ver_vspanset.spans[0].end(), [f" - branch {i+1}"])

        final_vspanset = session.retrieve_vspanset(opened_ver)
        final_specset = SpecSet(VSpec(opened_ver, list(final_vspanset.spans)))
        contents = session.retrieve_contents(final_specset)
        session.close_document(opened_ver)

        versions.append({
            "docid": str(version_doc),
            "contents": contents
        })

    # Compare version 1 and version 2 - should share original content
    v1_opened = session.open_document(Address(versions[0]["docid"]), READ_ONLY, CONFLICT_COPY)
    v2_opened = session.open_document(Address(versions[1]["docid"]), READ_ONLY, CONFLICT_COPY)

    v1_vspanset = session.retrieve_vspanset(v1_opened)
    v2_vspanset = session.retrieve_vspanset(v2_opened)

    v1_specset = SpecSet(VSpec(v1_opened, list(v1_vspanset.spans)))
    v2_specset = SpecSet(VSpec(v2_opened, list(v2_vspanset.spans)))

    shared = session.compare_versions(v1_specset, v2_specset)

    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "b": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(v1_opened)
    session.close_document(v2_opened)

    return {
        "name": "multiple_versions_same_source",
        "description": "Create multiple independent versions from the same source (branching)",
        "operations": [
            {"op": "create_document", "result": str(original)},
            {"op": "insert", "text": "Original shared content"},
            {"op": "create_versions", "from": str(original), "count": 3,
             "results": versions},
            {"op": "compare_versions",
             "v1": versions[0]["docid"],
             "v2": versions[1]["docid"],
             "shared": shared_result,
             "comment": "Both versions share original content"}
        ]
    }


def scenario_compare_unrelated_documents(session):
    """Compare two unrelated documents (no shared content)."""
    # Create first document
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["First document unique content"])
    session.close_document(opened1)

    # Create second document (not a version, completely independent)
    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Second document different text"])
    session.close_document(opened2)

    # Compare - should find no shared content
    doc1_opened = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    doc2_opened = session.open_document(doc2, READ_ONLY, CONFLICT_COPY)

    doc1_vspanset = session.retrieve_vspanset(doc1_opened)
    doc2_vspanset = session.retrieve_vspanset(doc2_opened)

    doc1_specset = SpecSet(VSpec(doc1_opened, list(doc1_vspanset.spans)))
    doc2_specset = SpecSet(VSpec(doc2_opened, list(doc2_vspanset.spans)))

    shared = session.compare_versions(doc1_specset, doc2_specset)

    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "b": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(doc1_opened)
    session.close_document(doc2_opened)

    return {
        "name": "compare_unrelated_documents",
        "description": "Compare two unrelated documents (should find no shared content)",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "insert", "doc": str(doc1), "text": "First document unique content"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "insert", "doc": str(doc2), "text": "Second document different text"},
            {"op": "compare_versions",
             "doc_a": str(doc1),
             "doc_b": str(doc2),
             "result": shared_result,
             "comment": "Should be empty - no shared content"}
        ]
    }


SCENARIOS = [
    ("versions", "create_version", scenario_create_version),
    ("versions", "compare_versions", scenario_compare_versions),
    ("versions", "version_chain", scenario_version_chain),
    ("versions", "multiple_versions_same_source", scenario_multiple_versions_same_source),
    ("versions", "compare_unrelated_documents", scenario_compare_unrelated_documents),
]
