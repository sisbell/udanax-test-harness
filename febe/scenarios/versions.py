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


def scenario_version_delete_preserves_original(session):
    """Delete content from version, verify original is unchanged."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Content that will be deleted in version"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)

    # Delete "will be deleted " from version (positions 14-29)
    session.remove(ver_opened, Span(Address(1, 14), Offset(0, 16)))

    # Get version content after delete
    ver_vspanset = session.retrieve_vspanset(ver_opened)
    ver_specset = SpecSet(VSpec(ver_opened, list(ver_vspanset.spans)))
    ver_contents = session.retrieve_contents(ver_specset)
    session.close_document(ver_opened)

    # Get original content - should be unchanged
    orig_opened2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vspanset = session.retrieve_vspanset(orig_opened2)
    orig_specset = SpecSet(VSpec(orig_opened2, list(orig_vspanset.spans)))
    orig_contents = session.retrieve_contents(orig_specset)
    session.close_document(orig_opened2)

    # Compare - should find shared content (the parts not deleted)
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    v_vs = session.retrieve_vspanset(ver_read)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "version": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "version_delete_preserves_original",
        "description": "Delete content from version, verify original is unchanged",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Content that will be deleted in version"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "remove", "doc": "version", "text": "will be deleted ",
             "comment": "Delete from version only"},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Version should have 'Content that in version'"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Original should still have full text"},
            {"op": "compare", "shared": shared_result,
             "comment": "Should share 'Content that ' and 'in version'"}
        ]
    }


def scenario_modify_original_after_version(session):
    """Modify original document after creating version, verify both states."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original content here"])
    session.close_document(orig_opened)

    # Create version (snapshot of original)
    version = session.create_version(original)

    # Now modify the ORIGINAL
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    orig_vs = session.retrieve_vspanset(orig_opened2)
    session.insert(orig_opened2, orig_vs.spans[0].end(), [" plus modifications"])
    orig_vs2 = session.retrieve_vspanset(orig_opened2)
    orig_ss = SpecSet(VSpec(orig_opened2, list(orig_vs2.spans)))
    orig_after = session.retrieve_contents(orig_ss)
    session.close_document(orig_opened2)

    # Version should still have original content
    ver_opened = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs = session.retrieve_vspanset(ver_opened)
    ver_ss = SpecSet(VSpec(ver_opened, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    session.close_document(ver_opened)

    # Compare
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    v_vs = session.retrieve_vspanset(ver_read)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read)
    session.close_document(ver_read)

    return {
        "name": "modify_original_after_version",
        "description": "Modify original document after creating version",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original content here"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "original", "text": " plus modifications",
             "comment": "Modify original after versioning"},
            {"op": "contents", "doc": "original", "result": orig_after},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Version should have pre-modification content"},
            {"op": "compare", "shared": shared_result,
             "comment": "Should share 'Original content here'"}
        ]
    }


def scenario_version_preserves_transclusion(session):
    """Verify that version preserves vcopy/transclusion identity."""
    # Create source document with content to transclude
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared transcluded content"])
    session.close_document(source_opened)

    # Create document that transcludes from source
    doc = session.create_document()
    doc_opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_opened, Address(1, 1), ["Prefix: "])

    # vcopy "Shared" from source
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 6))  # "Shared"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    doc_vs = session.retrieve_vspanset(doc_opened)
    session.vcopy(doc_opened, doc_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(doc_opened)

    # Create version of doc (which contains transcluded content)
    version = session.create_version(doc)

    # Compare version with SOURCE - should find shared transcluded content
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    s_vs = session.retrieve_vspanset(source_read2)
    v_vs = session.retrieve_vspanset(ver_read)
    s_ss = SpecSet(VSpec(source_read2, list(s_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared_with_source = session.compare_versions(v_ss, s_ss)
    shared_source_result = []
    for span_a, span_b in shared_with_source:
        shared_source_result.append({
            "version": span_to_dict(span_a.span),
            "source": span_to_dict(span_b.span)
        })

    # Also compare version with original doc
    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    d_vs = session.retrieve_vspanset(doc_read)
    d_ss = SpecSet(VSpec(doc_read, list(d_vs.spans)))

    shared_with_doc = session.compare_versions(v_ss, d_ss)
    shared_doc_result = []
    for span_a, span_b in shared_with_doc:
        shared_doc_result.append({
            "version": span_to_dict(span_a.span),
            "doc": span_to_dict(span_b.span)
        })

    # Get contents
    ver_contents = session.retrieve_contents(v_ss)

    session.close_document(source_read2)
    session.close_document(ver_read)
    session.close_document(doc_read)

    return {
        "name": "version_preserves_transclusion",
        "description": "Verify that version preserves vcopy/transclusion identity",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Shared transcluded content"},
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "vcopy", "from": "source", "to": "doc", "text": "Shared"},
            {"op": "create_version", "from": "doc", "result": str(version)},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare", "docs": ["version", "source"], "shared": shared_source_result,
             "comment": "Version should share 'Shared' with source (transclusion preserved)"},
            {"op": "compare", "docs": ["version", "doc"], "shared": shared_doc_result,
             "comment": "Version should share all content with original doc"}
        ]
    }


def scenario_delete_from_original_check_version(session):
    """Delete from original after versioning, verify version unchanged."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Delete this. Keep this."])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Get version content before original is modified
    ver_read1 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs1 = session.retrieve_vspanset(ver_read1)
    ver_ss1 = SpecSet(VSpec(ver_read1, list(ver_vs1.spans)))
    ver_before = session.retrieve_contents(ver_ss1)
    session.close_document(ver_read1)

    # Delete "Delete this. " from original
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.remove(orig_opened2, Span(Address(1, 1), Offset(0, 13)))
    orig_vs = session.retrieve_vspanset(orig_opened2)
    orig_ss = SpecSet(VSpec(orig_opened2, list(orig_vs.spans)))
    orig_after = session.retrieve_contents(orig_ss)
    session.close_document(orig_opened2)

    # Get version content after original is modified
    ver_read2 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs2 = session.retrieve_vspanset(ver_read2)
    ver_ss2 = SpecSet(VSpec(ver_read2, list(ver_vs2.spans)))
    ver_after = session.retrieve_contents(ver_ss2)
    session.close_document(ver_read2)

    return {
        "name": "delete_from_original_check_version",
        "description": "Delete from original after versioning, verify version unchanged",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Delete this. Keep this."},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "contents", "doc": "version", "label": "before", "result": ver_before},
            {"op": "remove", "doc": "original", "text": "Delete this. "},
            {"op": "contents", "doc": "original", "label": "after", "result": orig_after,
             "comment": "Original should have 'Keep this.'"},
            {"op": "contents", "doc": "version", "label": "after", "result": ver_after,
             "comment": "Version should still have full original content"}
        ]
    }


def scenario_compare_across_version_chain(session):
    """Compare v1 with v3 directly (skipping v2) to see transitive sharing."""
    # Create v1
    v1 = session.create_document()
    v1_opened = session.open_document(v1, READ_WRITE, CONFLICT_FAIL)
    session.insert(v1_opened, Address(1, 1), ["Original from v1"])
    session.close_document(v1_opened)

    # Create v2 from v1, modify it
    v2 = session.create_version(v1)
    v2_opened = session.open_document(v2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" plus v2"])
    session.close_document(v2_opened)

    # Create v3 from v2, modify it
    v3 = session.create_version(v2)
    v3_opened = session.open_document(v3, READ_WRITE, CONFLICT_FAIL)
    v3_vs = session.retrieve_vspanset(v3_opened)
    session.insert(v3_opened, v3_vs.spans[0].end(), [" plus v3"])
    session.close_document(v3_opened)

    # Get all contents
    v1_read = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    v2_read = session.open_document(v2, READ_ONLY, CONFLICT_COPY)
    v3_read = session.open_document(v3, READ_ONLY, CONFLICT_COPY)

    v1_vs = session.retrieve_vspanset(v1_read)
    v2_vs = session.retrieve_vspanset(v2_read)
    v3_vs = session.retrieve_vspanset(v3_read)

    v1_ss = SpecSet(VSpec(v1_read, list(v1_vs.spans)))
    v2_ss = SpecSet(VSpec(v2_read, list(v2_vs.spans)))
    v3_ss = SpecSet(VSpec(v3_read, list(v3_vs.spans)))

    v1_contents = session.retrieve_contents(v1_ss)
    v2_contents = session.retrieve_contents(v2_ss)
    v3_contents = session.retrieve_contents(v3_ss)

    # Compare v1 directly with v3 (skipping v2)
    shared_v1_v3 = session.compare_versions(v1_ss, v3_ss)
    shared_result = []
    for span_a, span_b in shared_v1_v3:
        shared_result.append({
            "v1": span_to_dict(span_a.span),
            "v3": span_to_dict(span_b.span)
        })

    session.close_document(v1_read)
    session.close_document(v2_read)
    session.close_document(v3_read)

    return {
        "name": "compare_across_version_chain",
        "description": "Compare v1 with v3 directly to see transitive content sharing",
        "operations": [
            {"op": "create_document", "doc": "v1", "result": str(v1)},
            {"op": "insert", "doc": "v1", "text": "Original from v1"},
            {"op": "create_version", "from": "v1", "result": str(v2)},
            {"op": "insert", "doc": "v2", "text": " plus v2"},
            {"op": "create_version", "from": "v2", "result": str(v3)},
            {"op": "insert", "doc": "v3", "text": " plus v3"},
            {"op": "contents", "doc": "v1", "result": v1_contents},
            {"op": "contents", "doc": "v2", "result": v2_contents},
            {"op": "contents", "doc": "v3", "result": v3_contents},
            {"op": "compare", "docs": ["v1", "v3"], "shared": shared_result,
             "comment": "v1 and v3 should share 'Original from v1' transitively"}
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

    # Compare - original should now share "version-only" with version
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read3 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    v_vs = session.retrieve_vspanset(ver_read3)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read3, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
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
            {"op": "vcopy", "from": "version", "to": "original", "text": "version-only",
             "comment": "Copy version-specific content back to original"},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "compare", "shared": shared_result,
             "comment": "Both should share 'Original text' and 'version-only'"}
        ]
    }


def scenario_version_insert_in_middle(session):
    """Insert content in the middle of versioned content, see how spans behave."""
    # Create original
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["FirstSecond"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Insert " MIDDLE " in the middle of version (between First and Second)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    session.insert(ver_opened, Address(1, 6), [" MIDDLE "])

    # Get version vspanset - how many spans?
    ver_vs = session.retrieve_vspanset(ver_opened)
    ver_ss = SpecSet(VSpec(ver_opened, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    session.close_document(ver_opened)

    # Get original (unchanged)
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vs = session.retrieve_vspanset(orig_read)
    orig_ss = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    orig_contents = session.retrieve_contents(orig_ss)
    session.close_document(orig_read)

    # Compare
    orig_read2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read2)
    v_vs = session.retrieve_vspanset(ver_read)
    o_ss = SpecSet(VSpec(orig_read2, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": span_to_dict(span_a.span),
            "version": span_to_dict(span_b.span)
        })

    session.close_document(orig_read2)
    session.close_document(ver_read)

    return {
        "name": "version_insert_in_middle",
        "description": "Insert in middle of versioned content, observe span structure",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "FirstSecond"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "version", "address": "1.6", "text": " MIDDLE ",
             "comment": "Insert between First and Second"},
            {"op": "retrieve_vspanset", "doc": "version",
             "result": vspec_to_dict(ver_vs),
             "comment": "How many spans? Content may be split."},
            {"op": "contents", "doc": "version", "result": ver_contents,
             "comment": "Should be 'First MIDDLE Second'"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Should still be 'FirstSecond'"},
            {"op": "compare", "shared": shared_result,
             "comment": "Should share 'First' and 'Second' as separate regions"}
        ]
    }


def scenario_both_versions_modified(session):
    """Modify both original and version, then compare."""
    # Create original
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Shared base content"])
    session.close_document(orig_opened)

    # Create version
    version = session.create_version(original)

    # Modify original - append
    orig_opened2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    orig_vs = session.retrieve_vspanset(orig_opened2)
    session.insert(orig_opened2, orig_vs.spans[0].end(), [" original-only"])
    orig_vs2 = session.retrieve_vspanset(orig_opened2)
    orig_ss = SpecSet(VSpec(orig_opened2, list(orig_vs2.spans)))
    orig_contents = session.retrieve_contents(orig_ss)
    session.close_document(orig_opened2)

    # Modify version - prepend
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    session.insert(ver_opened, Address(1, 1), ["version-only "])
    ver_vs = session.retrieve_vspanset(ver_opened)
    ver_ss = SpecSet(VSpec(ver_opened, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss)
    session.close_document(ver_opened)

    # Compare - should share "Shared base content"
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    v_vs = session.retrieve_vspanset(ver_read)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_read, list(v_vs.spans)))

    shared = session.compare_versions(o_ss, v_ss)
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
]
