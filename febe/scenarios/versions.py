"""Version creation and comparison scenarios."""

from client import (
    Address, Offset, Span, SpecSet, VSpec, VSpan,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


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
            {"op": "create_version", "from": str(docid), "result": str(version_docid)},
            {"op": "open_document", "doc": str(version_docid), "mode": "read_write", "result": str(opened_version)},
            {"op": "retrieve_vspanset", "doc": str(opened_version), "result": vspec_to_dict(version_vspanset)},
            {"op": "insert", "doc": str(opened_version), "text": " with additions"},
            {"op": "retrieve_contents", "doc": "original", "result": orig_contents},
            {"op": "retrieve_contents", "doc": "version", "result": new_contents}
        ]
    }


def scenario_compare_versions(session):
    """Create document, create version, compare content."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Shared content"])
    session.close_document(orig_opened)

    # Create version and add unique text
    version = session.create_version(original)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    ver_vs = session.retrieve_vspanset(ver_opened)
    session.insert(ver_opened, ver_vs.spans[0].end(), [" plus new text"])
    session.close_document(ver_opened)

    # Compare the two versions
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    orig_vs = session.retrieve_vspanset(orig_read)
    ver_vs = session.retrieve_vspanset(ver_read)

    orig_specs = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs.spans)))

    shared = session.compare_versions(orig_specs, ver_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "compare_versions",
        "description": "Create document, create version, add text to version, compare",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Shared content"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "version", "text": " plus new text"},
            {"op": "compare_versions", "shared": shared_result}
        ]
    }


def scenario_version_chain(session):
    """Create a chain of versions: v1 -> v2 -> v3."""
    v1 = session.create_document()
    v1_opened = session.open_document(v1, READ_WRITE, CONFLICT_FAIL)
    session.insert(v1_opened, Address(1, 1), ["v1 content"])
    session.close_document(v1_opened)

    v2 = session.create_version(v1)
    v2_opened = session.open_document(v2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" plus v2"])
    session.close_document(v2_opened)

    v3 = session.create_version(v2)
    v3_opened = session.open_document(v3, READ_WRITE, CONFLICT_FAIL)
    v3_vs = session.retrieve_vspanset(v3_opened)
    session.insert(v3_opened, v3_vs.spans[0].end(), [" plus v3"])
    session.close_document(v3_opened)

    # Retrieve all three
    v1_read = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    v1_vs = session.retrieve_vspanset(v1_read)
    v1_specs = SpecSet(VSpec(v1_read, list(v1_vs.spans)))
    v1_contents = session.retrieve_contents(v1_specs)

    v2_read = session.open_document(v2, READ_ONLY, CONFLICT_COPY)
    v2_vs = session.retrieve_vspanset(v2_read)
    v2_specs = SpecSet(VSpec(v2_read, list(v2_vs.spans)))
    v2_contents = session.retrieve_contents(v2_specs)

    v3_read = session.open_document(v3, READ_ONLY, CONFLICT_COPY)
    v3_vs = session.retrieve_vspanset(v3_read)
    v3_specs = SpecSet(VSpec(v3_read, list(v3_vs.spans)))
    v3_contents = session.retrieve_contents(v3_specs)

    session.close_document(v1_read)
    session.close_document(v2_read)
    session.close_document(v3_read)

    return {
        "name": "version_chain",
        "description": "Create chain v1 -> v2 -> v3, each adding unique content",
        "operations": [
            {"op": "create_document", "doc": "v1", "result": str(v1)},
            {"op": "insert", "doc": "v1", "text": "v1 content"},
            {"op": "create_version", "from": "v1", "result": str(v2)},
            {"op": "insert", "doc": "v2", "text": " plus v2"},
            {"op": "create_version", "from": "v2", "result": str(v3)},
            {"op": "insert", "doc": "v3", "text": " plus v3"},
            {"op": "contents", "doc": "v1", "result": v1_contents},
            {"op": "contents", "doc": "v2", "result": v2_contents},
            {"op": "contents", "doc": "v3", "result": v3_contents}
        ]
    }


def scenario_multiple_versions_same_source(session):
    """Create multiple independent versions from the same source."""
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Base content"])
    session.close_document(source_opened)

    # Create two versions
    v1 = session.create_version(source)
    v2 = session.create_version(source)

    # Modify each independently
    v1_opened = session.open_document(v1, READ_WRITE, CONFLICT_FAIL)
    v1_vs = session.retrieve_vspanset(v1_opened)
    session.insert(v1_opened, v1_vs.spans[0].end(), [" v1"])
    session.close_document(v1_opened)

    v2_opened = session.open_document(v2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" v2"])
    session.close_document(v2_opened)

    # Retrieve all three
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_vs = session.retrieve_vspanset(source_read)
    source_specs = SpecSet(VSpec(source_read, list(source_vs.spans)))
    source_contents = session.retrieve_contents(source_specs)
    session.close_document(source_read)

    v1_read = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    v1_vs = session.retrieve_vspanset(v1_read)
    v1_specs = SpecSet(VSpec(v1_read, list(v1_vs.spans)))
    v1_contents = session.retrieve_contents(v1_specs)
    session.close_document(v1_read)

    v2_read = session.open_document(v2, READ_ONLY, CONFLICT_COPY)
    v2_vs = session.retrieve_vspanset(v2_read)
    v2_specs = SpecSet(VSpec(v2_read, list(v2_vs.spans)))
    v2_contents = session.retrieve_contents(v2_specs)
    session.close_document(v2_read)

    return {
        "name": "multiple_versions_same_source",
        "description": "Create two independent versions from same source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Base content"},
            {"op": "create_version", "from": "source", "result": str(v1)},
            {"op": "create_version", "from": "source", "result": str(v2)},
            {"op": "insert", "doc": "v1", "text": " v1"},
            {"op": "insert", "doc": "v2", "text": " v2"},
            {"op": "contents", "doc": "source", "result": source_contents},
            {"op": "contents", "doc": "v1", "result": v1_contents},
            {"op": "contents", "doc": "v2", "result": v2_contents}
        ]
    }


def scenario_compare_unrelated_documents(session):
    """Compare two documents that have no shared content."""
    doc1 = session.create_document()
    doc1_opened = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc1_opened, Address(1, 1), ["Content A"])
    session.close_document(doc1_opened)

    doc2 = session.create_document()
    doc2_opened = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc2_opened, Address(1, 1), ["Content B"])
    session.close_document(doc2_opened)

    # Compare
    doc1_read = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    doc2_read = session.open_document(doc2, READ_ONLY, CONFLICT_COPY)

    doc1_vs = session.retrieve_vspanset(doc1_read)
    doc2_vs = session.retrieve_vspanset(doc2_read)

    doc1_specs = SpecSet(VSpec(doc1_read, list(doc1_vs.spans)))
    doc2_specs = SpecSet(VSpec(doc2_read, list(doc2_vs.spans)))

    shared = session.compare_versions(doc1_specs, doc2_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "doc1": span_to_dict(span_a.span),
            "doc2": span_to_dict(span_b.span)
        })

    session.close_document(doc1_read)
    session.close_document(doc2_read)

    return {
        "name": "compare_unrelated_documents",
        "description": "Compare two documents with no shared content (should be empty)",
        "operations": [
            {"op": "create_document", "doc": "doc1", "result": str(doc1)},
            {"op": "insert", "doc": "doc1", "text": "Content A"},
            {"op": "create_document", "doc": "doc2", "result": str(doc2)},
            {"op": "insert", "doc": "doc2", "text": "Content B"},
            {"op": "compare_versions", "shared": shared_result,
             "comment": "Should be empty - no shared content identity"}
        ]
    }


def scenario_version_delete_preserves_original(session):
    """Create version, delete from version, ensure original unchanged."""
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original content that will be partially deleted"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Delete from version
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    delete_span = Span(Address(1, 10), Offset(0, 17))  # "content that will"
    session.delete(ver_opened, SpecSet(VSpec(ver_opened, [delete_span])))

    ver_vs = session.retrieve_vspanset(ver_opened)
    ver_specs = SpecSet(VSpec(ver_opened, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_specs)
    session.close_document(ver_opened)

    # Check original is unchanged
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vs = session.retrieve_vspanset(orig_read)
    orig_specs = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    orig_contents = session.retrieve_contents(orig_specs)
    session.close_document(orig_read)

    # Compare to see what's still shared
    orig_read2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    orig_vs2 = session.retrieve_vspanset(orig_read2)
    ver_vs2 = session.retrieve_vspanset(ver_read)
    orig_specs2 = SpecSet(VSpec(orig_read2, list(orig_vs2.spans)))
    ver_specs2 = SpecSet(VSpec(ver_read, list(ver_vs2.spans)))
    shared = session.compare_versions(orig_specs2, ver_specs2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })
    session.close_document(orig_read2)
    session.close_document(ver_read)

    return {
        "name": "version_delete_preserves_original",
        "description": "Delete from version, verify original unchanged",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original content that will be partially deleted"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "delete", "doc": "version", "text": "content that will",
             "comment": "Delete middle portion from version"},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Should be 'Original  be partially deleted'"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Should be unchanged"},
            {"op": "compare_versions", "shared": shared_result,
             "comment": "Should share the non-deleted parts"}
        ]
    }


def scenario_modify_original_after_version(session):
    """Create version, then modify original, ensure version unchanged."""
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original content"])
    session.close_document(orig_opened)

    # Create version (snapshot of current state)
    version = session.create_version(original)

    # Now modify original
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    orig_vs = session.retrieve_vspanset(orig_opened2)
    session.insert(orig_opened2, orig_vs.spans[0].end(), [" with additions"])
    orig_vs2 = session.retrieve_vspanset(orig_opened2)
    orig_specs = SpecSet(VSpec(orig_opened2, list(orig_vs2.spans)))
    orig_contents = session.retrieve_contents(orig_specs)
    session.close_document(orig_opened2)

    # Check version is unchanged
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_read)
    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_specs)
    session.close_document(ver_read)

    return {
        "name": "modify_original_after_version",
        "description": "Create version, modify original, verify version unchanged",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original content"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "original", "text": " with additions",
             "comment": "Modify original after version created"},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Should be 'Original content' (unchanged)"}
        ]
    }


def scenario_version_preserves_transclusion(session):
    """Version a document that contains transclusion, verify identity preserved."""
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared transcluded content"])
    session.close_document(source_opened)

    # Create document that transcludes from source
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Prefix: "])

    # Transclude "Shared" from source
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 6))  # "Shared"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    doc_vs = session.retrieve_vspanset(doc_opened)
    session.vcopy(doc_opened, doc_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(doc_opened)

    # Create version of doc
    version = session.create_version(doc)

    # Compare version with source - should find "Shared" as shared content
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)

    ver_vs = session.retrieve_vspanset(ver_read)
    source_vs = session.retrieve_vspanset(source_read2)

    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    source_specs = SpecSet(VSpec(source_read2, list(source_vs.spans)))

    shared = session.compare_versions(ver_specs, source_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "version": span_to_dict(span_a.span),
            "source": span_to_dict(span_b.span)
        })

    # Get version contents
    ver_contents = session.retrieve_contents(ver_specs)

    session.close_document(ver_read)
    session.close_document(source_read2)

    return {
        "name": "version_preserves_transclusion",
        "description": "Version document with transclusion, verify content identity preserved",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Shared transcluded content"},
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "insert", "doc": "doc", "text": "Prefix: "},
            {"op": "vcopy", "from": "source", "text": "Shared", "to": "doc"},
            {"op": "create_version", "from": "doc", "result": str(version)},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare_versions", "docs": ["version", "source"], "shared": shared_result,
             "comment": "Version should share 'Shared' with source through transclusion"}
        ]
    }


def scenario_delete_from_original_check_version(session):
    """Delete from original after versioning, verify version unchanged."""
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Content to be deleted later"])
    session.close_document(orig_opened)

    # Create version (snapshot)
    version = session.create_version(original)

    # Delete from original
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    delete_span = Span(Address(1, 9), Offset(0, 18))  # "to be deleted later"
    session.delete(orig_opened2, SpecSet(VSpec(orig_opened2, [delete_span])))

    orig_vs = session.retrieve_vspanset(orig_opened2)
    orig_specs = SpecSet(VSpec(orig_opened2, list(orig_vs.spans)))
    orig_contents = session.retrieve_contents(orig_specs)
    session.close_document(orig_opened2)

    # Check version is unchanged
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_read)
    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_specs)
    session.close_document(ver_read)

    return {
        "name": "delete_from_original_check_version",
        "description": "Delete from original, verify version still has deleted content",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Content to be deleted later"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "delete", "doc": "original", "text": "to be deleted later"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Should be 'Content '"},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Should be unchanged: 'Content to be deleted later'"}
        ]
    }


def scenario_compare_across_version_chain(session):
    """Compare v1 with v3 in chain v1->v2->v3, verify transitive content sharing."""
    v1 = session.create_document()
    v1_opened = session.open_document(v1, READ_WRITE, CONFLICT_FAIL)
    session.insert(v1_opened, Address(1, 1), ["Original from v1"])
    session.close_document(v1_opened)

    v2 = session.create_version(v1)
    v2_opened = session.open_document(v2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" plus v2"])
    session.close_document(v2_opened)

    v3 = session.create_version(v2)
    v3_opened = session.open_document(v3, READ_WRITE, CONFLICT_FAIL)
    v3_vs = session.retrieve_vspanset(v3_opened)
    session.insert(v3_opened, v3_vs.spans[0].end(), [" plus v3"])
    session.close_document(v3_opened)

    # Compare v1 with v3 (skipping v2)
    v1_read = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    v3_read = session.open_document(v3, READ_ONLY, CONFLICT_COPY)

    v1_vs = session.retrieve_vspanset(v1_read)
    v3_vs = session.retrieve_vspanset(v3_read)

    v1_specs = SpecSet(VSpec(v1_read, list(v1_vs.spans)))
    v3_specs = SpecSet(VSpec(v3_read, list(v3_vs.spans)))

    shared = session.compare_versions(v1_specs, v3_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "v1": span_to_dict(span_a.span),
            "v3": span_to_dict(span_b.span)
        })

    session.close_document(v1_read)
    session.close_document(v3_read)

    return {
        "name": "compare_across_version_chain",
        "description": "Compare v1 with v3 in chain v1->v2->v3",
        "operations": [
            {"op": "create_document", "doc": "v1", "result": str(v1)},
            {"op": "insert", "doc": "v1", "text": "Original from v1"},
            {"op": "create_version", "from": "v1", "result": str(v2)},
            {"op": "insert", "doc": "v2", "text": " plus v2"},
            {"op": "create_version", "from": "v2", "result": str(v3)},
            {"op": "insert", "doc": "v3", "text": " plus v3"},
            {"op": "compare_versions", "docs": ["v1", "v3"], "shared": shared_result,
             "comment": "Should share 'Original from v1' transitively"}
        ]
    }


def scenario_version_with_links(session):
    """Create document with links, then version it, verify link behavior."""
    # Create source document (will have link from it)
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for info"])

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Information content"])

    # Create link from "here" to target
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 11))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)
    session.close_document(source_opened)

    # Create version of source document (which has the link)
    version = session.create_version(source)

    # Find links from original source
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_search = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_source = session.find_links(source_search)
    session.close_document(source_read)

    # Find links from version - do links transfer to versions?
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_search = SpecSet(VSpec(ver_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_version = session.find_links(ver_search)

    # Get version contents
    ver_vs = session.retrieve_vspanset(ver_read)
    ver_ss = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents_raw = session.retrieve_contents(ver_ss)
    # Convert any Address objects (embedded links) to strings
    ver_contents = [str(c) if hasattr(c, 'digits') else c for c in ver_contents_raw]
    session.close_document(ver_read)

    return {
        "name": "version_with_links",
        "description": "Create document with links, then version it",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Click here for info"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Information content"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "create_version", "from": "source", "result": str(version)},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Text plus embedded link address"},
            {"op": "find_links", "from": "source",
             "result": [str(l) for l in links_from_source],
             "comment": "Links from original source"},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_version],
             "comment": "Do links transfer to version? (tests link-to-content binding)"}
        ]
    }


def scenario_version_of_empty_document(session):
    """Create version of an empty document."""
    # Create empty document
    empty = session.create_document()

    # Create version of empty document
    version = session.create_version(empty)

    # Check both are empty initially
    empty_read1 = session.open_document(empty, READ_ONLY, CONFLICT_COPY)
    empty_vs = session.retrieve_vspanset(empty_read1)
    session.close_document(empty_read1)

    ver_read1 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_read1)
    session.close_document(ver_read1)

    # Now add content to version
    ver_write = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    session.insert(ver_write, Address(1, 1), ["Content in version only"])
    ver_vs2 = session.retrieve_vspanset(ver_write)
    ver_ss = SpecSet(VSpec(ver_write, list(ver_vs2.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    session.close_document(ver_write)

    # Empty should still be empty
    empty_read2 = session.open_document(empty, READ_ONLY, CONFLICT_COPY)
    empty_vs2 = session.retrieve_vspanset(empty_read2)
    session.close_document(empty_read2)

    return {
        "name": "version_of_empty_document",
        "description": "Create version of an empty document",
        "operations": [
            {"op": "create_document", "doc": "empty", "result": str(empty)},
            {"op": "create_version", "from": "empty", "result": str(version)},
            {"op": "retrieve_vspanset", "doc": "empty", "label": "initial",
             "result": vspec_to_dict(empty_vs),
             "comment": "Empty document should have no spans"},
            {"op": "retrieve_vspanset", "doc": "version", "label": "initial",
             "result": vspec_to_dict(ver_vs),
             "comment": "Version of empty should also have no spans"},
            {"op": "insert", "doc": "version", "text": "Content in version only"},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "retrieve_vspanset", "doc": "empty", "label": "after",
             "result": vspec_to_dict(empty_vs2),
             "comment": "Empty document should still be empty"}
        ]
    }


def scenario_cross_version_vcopy(session):
    """Copy content from version back to original (or between versions)."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original text"])
    session.close_document(orig_opened)

    # Create version and add unique content
    version = session.create_version(original)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    ver_vs = session.retrieve_vspanset(ver_opened)
    session.insert(ver_opened, ver_vs.spans[0].end(), [" with version-only addition"])
    session.close_document(ver_opened)

    # Now vcopy "version-only" from version back to original
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    # "version-only" is at position 20-32 in version
    copy_span = Span(Address(1, 20), Offset(0, 12))
    copy_specs = SpecSet(VSpec(ver_read, [copy_span]))

    orig_vs = session.retrieve_vspanset(orig_opened2)
    session.vcopy(orig_opened2, orig_vs.spans[0].end(), copy_specs)

    # Get final contents
    orig_vs2 = session.retrieve_vspanset(orig_opened2)
    orig_ss = SpecSet(VSpec(orig_opened2, list(orig_vs2.spans)))
    orig_contents = session.retrieve_contents(orig_ss)

    session.close_document(ver_read)
    session.close_document(orig_opened2)

    # Get version contents
    ver_read2 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs2 = session.retrieve_vspanset(ver_read2)
    ver_ss = SpecSet(VSpec(ver_read2, list(ver_vs2.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    session.close_document(ver_read2)

    # Compare - should now have two shared regions
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read3 = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    orig_vs3 = session.retrieve_vspanset(orig_read)
    ver_vs3 = session.retrieve_vspanset(ver_read3)

    orig_specs = SpecSet(VSpec(orig_read, list(orig_vs3.spans)))
    ver_specs = SpecSet(VSpec(ver_read3, list(ver_vs3.spans)))

    shared = session.compare_versions(orig_specs, ver_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read)
    session.close_document(ver_read3)

    return {
        "name": "cross_version_vcopy",
        "description": "Copy content from version back to original",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original text"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "version", "text": " with version-only addition"},
            {"op": "vcopy", "from": "version", "text": "version-only", "to": "original"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Should be 'Original textversion-only'"},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare_versions", "shared": shared_result,
             "comment": "Should share both 'Original text' and 'version-only'"}
        ]
    }


def scenario_version_insert_in_middle(session):
    """Insert text in middle of versioned content, verify content identity splits."""
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["FirstSecond"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Insert in middle of version
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    session.insert(ver_opened, Address(1, 6), [" MIDDLE "])

    ver_vs = session.retrieve_vspanset(ver_opened)
    ver_specs = SpecSet(VSpec(ver_opened, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_specs)
    session.close_document(ver_opened)

    # Compare - should find two shared regions
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    orig_vs = session.retrieve_vspanset(orig_read)
    ver_vs2 = session.retrieve_vspanset(ver_read)

    orig_specs = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    ver_specs2 = SpecSet(VSpec(ver_read, list(ver_vs2.spans)))

    shared = session.compare_versions(orig_specs, ver_specs2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "version_insert_in_middle",
        "description": "Insert in middle of versioned content, splits content identity",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "FirstSecond"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "version", "address": "1.6", "text": " MIDDLE "},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Should be 'First MIDDLE Second'"},
            {"op": "compare_versions", "shared": shared_result,
             "comment": "Should find two regions: 'First' and 'Second' at different positions"}
        ]
    }


def scenario_both_versions_modified(session):
    """Modify both original and version independently, then compare."""
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Shared base content"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Modify original
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    orig_vs = session.retrieve_vspanset(orig_opened2)
    session.insert(orig_opened2, orig_vs.spans[0].end(), [" original-only"])
    session.close_document(orig_opened2)

    # Modify version
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    session.insert(ver_opened, Address(1, 1), ["version-only "])
    session.close_document(ver_opened)

    # Get contents of both
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vs2 = session.retrieve_vspanset(orig_read)
    orig_specs = SpecSet(VSpec(orig_read, list(orig_vs2.spans)))
    orig_contents = session.retrieve_contents(orig_specs)

    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_read)
    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_specs)

    # Compare
    shared = session.compare_versions(orig_specs, ver_specs)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "both_versions_modified",
        "description": "Modify both original and version independently, then compare",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Shared base content"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "original", "text": " original-only",
             "comment": "Append to original"},
            {"op": "insert", "doc": "version", "address": "1.1", "text": "version-only ",
             "comment": "Prepend to version"},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare", "shared": shared_result,
             "comment": "Should share 'Shared base content' despite both being modified"}
        ]
    }


def scenario_version_copies_link_subspace(session):
    """Test whether CREATENEWVERSION copies link subspace (2.x) or only text (1.x)."""
    # Create source document with text
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Text with link"])

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])
    session.close_document(target_opened)

    # Create link from "link" to target
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 11), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get source vspanset BEFORE creating version
    source_vs_before = session.retrieve_vspanset(source_opened)
    session.close_document(source_opened)

    # Create version of source (which has both text and link)
    version = session.create_version(source)

    # Get version vspanset - does it have link subspace (0.x or 2.x)?
    ver_opened = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_opened)
    session.close_document(ver_opened)

    # Get source vspanset AFTER version creation
    source_opened2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    source_vs_after = session.retrieve_vspanset(source_opened2)
    session.close_document(source_opened2)

    return {
        "name": "version_copies_link_subspace",
        "description": "Test whether CREATENEWVERSION copies link subspace (2.x) or only text (1.x)",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Text with link"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Target"},
            {"op": "create_link", "source_text": "link", "result": str(link_id)},
            {"op": "retrieve_vspanset", "doc": "source", "label": "before_version",
             "result": vspec_to_dict(source_vs_before),
             "comment": "Source vspanset should include both text (1.x) and link (0.x or 2.x) subspaces"},
            {"op": "create_version", "from": "source", "result": str(version)},
            {"op": "retrieve_vspanset", "doc": "version", "label": "after_version",
             "result": vspec_to_dict(ver_vs),
             "comment": "CRITICAL: Does version have link subspace? If yes, CREATENEWVERSION copies links. If no, it copies only text."},
            {"op": "retrieve_vspanset", "doc": "source", "label": "after_version",
             "result": vspec_to_dict(source_vs_after),
             "comment": "Source vspanset unchanged"}
        ]
    }


SCENARIOS = [
    ("versions", "create_version", scenario_create_version),
    ("versions", "compare_versions", scenario_compare_versions),
    ("versions", "version_chain", scenario_version_chain),
    ("versions", "multiple_versions_same_source", scenario_multiple_versions_same_source),
    ("versions", "compare_unrelated_documents", scenario_compare_unrelated_documents),
    ("versions", "version_delete_preserves_original", scenario_version_delete_preserves_original),
    ("versions", "modify_original_after_version", scenario_modify_original_after_version),
    ("versions", "version_preserves_transclusion", scenario_version_preserves_transclusion),
    ("versions", "delete_from_original_check_version", scenario_delete_from_original_check_version),
    ("versions", "compare_across_version_chain", scenario_compare_across_version_chain),
    ("versions", "version_with_links", scenario_version_with_links),
    ("versions", "version_of_empty_document", scenario_version_of_empty_document),
    ("versions", "cross_version_vcopy", scenario_cross_version_vcopy),
    ("versions", "version_insert_in_middle", scenario_version_insert_in_middle),
    ("versions", "both_versions_modified", scenario_both_versions_modified),
    ("versions", "version_copies_link_subspace", scenario_version_copies_link_subspace),
]
