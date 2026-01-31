"""VCopy (transclusion) scenarios."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from ..common import vspec_to_dict, span_to_dict


def scenario_vcopy(session):
    """Copy content from one document to another (transclusion)."""
    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Original content to copy"])
    source_vspanset = session.retrieve_vspanset(source_opened)
    session.close_document(source_opened)

    # Create target document
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Prefix: "])
    target_vspanset = session.retrieve_vspanset(target_opened)

    # Copy from source to target (vcopy = virtual copy, maintains link)
    # Need to re-open source for reading
    source_read = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 16))  # "Original content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    session.vcopy(target_opened, target_vspanset.spans[0].end(), copy_specs)

    # Retrieve target content
    final_vspanset = session.retrieve_vspanset(target_opened)
    final_specset = SpecSet(VSpec(target_opened, list(final_vspanset.spans)))
    final_contents = session.retrieve_contents(final_specset)

    session.close_document(source_read)
    session.close_document(target_opened)

    return {
        "name": "vcopy_transclusion",
        "description": "Copy content from one document to another (virtual copy)",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "open_document", "doc": str(source_docid), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Original content to copy"},
            {"op": "close_document", "doc": str(source_opened)},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "open_document", "doc": str(target_docid), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Prefix: "},
            {"op": "vcopy",
             "source_doc": str(source_docid),
             "source_span": span_to_dict(copy_span),
             "target_doc": str(target_opened)},
            {"op": "retrieve_contents", "doc": str(target_opened), "result": final_contents},
            {"op": "close_document", "doc": str(target_opened)}
        ]
    }


def scenario_vcopy_preserves_identity(session):
    """Verify that vcopy preserves content identity (compare_versions shows shared)."""
    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared content that will be transcluded"])
    source_vspanset = session.retrieve_vspanset(source_opened)
    session.close_document(source_opened)

    # Create target document with vcopy
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Prefix: "])

    # vcopy content from source
    source_read = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 14))  # "Shared content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    target_vspanset1 = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vspanset1.spans[0].end(), copy_specs)

    target_vspanset2 = session.retrieve_vspanset(target_opened)
    session.close_document(target_opened)

    # Compare source and target - should find shared content
    source_opened2 = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
    target_opened2 = session.open_document(target_docid, READ_ONLY, CONFLICT_COPY)

    source_vspanset2 = session.retrieve_vspanset(source_opened2)
    target_vspanset3 = session.retrieve_vspanset(target_opened2)

    source_specset = SpecSet(VSpec(source_opened2, list(source_vspanset2.spans)))
    target_specset = SpecSet(VSpec(target_opened2, list(target_vspanset3.spans)))

    shared = session.compare_versions(source_specset, target_specset)

    # Convert to serializable format
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "a": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "b": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(source_read)
    session.close_document(source_opened2)
    session.close_document(target_opened2)

    return {
        "name": "vcopy_preserves_identity",
        "description": "Verify vcopy preserves content identity (compare_versions shows shared)",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "open_document", "doc": str(source_docid), "mode": "read_write"},
            {"op": "insert", "doc": str(source_docid), "address": "1.1",
             "text": "Shared content that will be transcluded"},
            {"op": "close_document", "doc": str(source_docid)},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "vcopy", "target_doc": str(target_docid),
             "source_span": span_to_dict(copy_span),
             "comment": "Transclude 'Shared content' from source"},
            {"op": "compare_versions",
             "doc_a": str(source_docid),
             "doc_b": str(target_docid),
             "result": shared_result,
             "comment": "Should find shared content from vcopy"}
        ]
    }


def scenario_multiple_vcopy_same_source(session):
    """Copy the same source content to multiple target documents."""
    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Reusable content block"])
    session.close_document(source_opened)

    # Create multiple target documents, each with vcopy from source
    targets = []
    for i in range(3):
        target_docid = session.create_document()
        target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
        session.insert(target_opened, Address(1, 1), [f"Target {i+1}: "])

        # vcopy from source
        source_read = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
        copy_span = Span(Address(1, 1), Offset(0, 8))  # "Reusable"
        copy_specs = SpecSet(VSpec(source_read, [copy_span]))
        target_vspanset = session.retrieve_vspanset(target_opened)
        session.vcopy(target_opened, target_vspanset.spans[0].end(), copy_specs)

        # Get final content
        final_vspanset = session.retrieve_vspanset(target_opened)
        final_specset = SpecSet(VSpec(target_opened, list(final_vspanset.spans)))
        contents = session.retrieve_contents(final_specset)

        targets.append({
            "docid": str(target_docid),
            "contents": contents
        })

        session.close_document(source_read)
        session.close_document(target_opened)

    return {
        "name": "multiple_vcopy_same_source",
        "description": "Copy the same source content to multiple target documents",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "insert", "text": "Reusable content block"},
            {"op": "vcopy_to_multiple",
             "source_span": span_to_dict(Span(Address(1, 1), Offset(0, 8))),
             "targets": targets,
             "comment": "Each target has transcluded copy of 'Reusable'"}
        ]
    }


def scenario_nested_vcopy(session):
    """Test nested transclusion: A includes content from B, B includes content from C."""
    # Create document C (the original source)
    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Original from C"])
    session.close_document(opened_c)

    # Create document B, which transcludes from C
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["B prefix: "])

    # vcopy "Original" from C into B
    c_read = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_span = Span(Address(1, 1), Offset(0, 8))  # "Original"
    c_specs = SpecSet(VSpec(c_read, [c_span]))
    b_vspanset = session.retrieve_vspanset(opened_b)
    session.vcopy(opened_b, b_vspanset.spans[0].end(), c_specs)
    session.close_document(c_read)
    session.close_document(opened_b)

    # Create document A, which transcludes from B
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["A prefix: "])

    # vcopy content from B (which includes transcluded content from C)
    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vspanset = session.retrieve_vspanset(b_read)
    b_specs = SpecSet(VSpec(b_read, list(b_vspanset.spans)))
    a_vspanset = session.retrieve_vspanset(opened_a)
    session.vcopy(opened_a, a_vspanset.spans[0].end(), b_specs)
    session.close_document(b_read)

    # Get final contents of all three
    a_final = session.retrieve_vspanset(opened_a)
    a_specset = SpecSet(VSpec(opened_a, list(a_final.spans)))
    a_contents = session.retrieve_contents(a_specset)
    session.close_document(opened_a)

    b_read2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_final = session.retrieve_vspanset(b_read2)
    b_specset = SpecSet(VSpec(b_read2, list(b_final.spans)))
    b_contents = session.retrieve_contents(b_specset)
    session.close_document(b_read2)

    c_read2 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_final = session.retrieve_vspanset(c_read2)
    c_specset = SpecSet(VSpec(c_read2, list(c_final.spans)))
    c_contents = session.retrieve_contents(c_specset)
    session.close_document(c_read2)

    # Compare A and C - should find shared content (the "Original" from C)
    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    c_read3 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    a_vs = session.retrieve_vspanset(a_read)
    c_vs = session.retrieve_vspanset(c_read3)
    a_ss = SpecSet(VSpec(a_read, list(a_vs.spans)))
    c_ss = SpecSet(VSpec(c_read3, list(c_vs.spans)))
    shared_a_c = session.compare_versions(a_ss, c_ss)

    shared_result = []
    for span_a, span_b in shared_a_c:
        shared_result.append({
            "a": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "c": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(a_read)
    session.close_document(c_read3)

    return {
        "name": "nested_vcopy",
        "description": "Test nested transclusion: A includes B, B includes C",
        "operations": [
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Original from C"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "vcopy", "from": "C", "to": "B", "text": "Original"},
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "vcopy", "from": "B", "to": "A", "text": "all of B"},
            {"op": "contents", "doc": "C", "result": c_contents},
            {"op": "contents", "doc": "B", "result": b_contents},
            {"op": "contents", "doc": "A", "result": a_contents},
            {"op": "compare", "docs": ["A", "C"], "shared": shared_result,
             "comment": "A and C should share 'Original' through transitive transclusion"}
        ]
    }


def scenario_vcopy_source_modified(session):
    """Test what happens when source document is modified after vcopy.

    In Xanadu, vcopy creates a reference to the original content's identity.
    When source is modified (text inserted/deleted), it creates NEW content -
    the original content identity is preserved. So the target should still
    reference the original content.
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Original content here"])
    session.close_document(source_opened)

    # Create target document with vcopy
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target: "])

    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 16))  # "Original content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(target_opened)

    # Get target contents BEFORE source modification
    target_read1 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    target_vs1 = session.retrieve_vspanset(target_read1)
    target_ss1 = SpecSet(VSpec(target_read1, list(target_vs1.spans)))
    target_before = session.retrieve_contents(target_ss1)
    session.close_document(target_read1)

    # NOW modify the source document - insert text at the beginning
    source_opened2 = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened2, Address(1, 1), ["NEW: "])
    source_vs2 = session.retrieve_vspanset(source_opened2)
    source_ss2 = SpecSet(VSpec(source_opened2, list(source_vs2.spans)))
    source_after = session.retrieve_contents(source_ss2)
    session.close_document(source_opened2)

    # Get target contents AFTER source modification
    target_read2 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    target_vs2 = session.retrieve_vspanset(target_read2)
    target_ss2 = SpecSet(VSpec(target_read2, list(target_vs2.spans)))
    target_after = session.retrieve_contents(target_ss2)
    session.close_document(target_read2)

    return {
        "name": "vcopy_source_modified",
        "description": "Test vcopy behavior when source is modified after transclusion",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Original content here"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "vcopy", "from": "source", "to": "target", "span": "Original content"},
            {"op": "contents", "doc": "target", "label": "before_modification",
             "result": target_before},
            {"op": "insert", "doc": "source", "address": "1.1", "text": "NEW: ",
             "comment": "Modify source by prepending"},
            {"op": "contents", "doc": "source", "label": "after_modification",
             "result": source_after},
            {"op": "contents", "doc": "target", "label": "after_source_modification",
             "result": target_after,
             "comment": "Target should still have original content (not affected by source edit)"}
        ]
    }


def scenario_vcopy_source_deleted(session):
    """Test what happens when transcluded content is deleted from source.

    The target's vcopy references the original content identity.
    Deleting from source removes it from source's view but the content
    still exists (referenced by target).
    """
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Keep this. Delete this. Keep end."])
    source_vs1 = session.retrieve_vspanset(source_opened)
    session.close_document(source_opened)

    # Create target document and vcopy the middle section
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Transcluded: "])

    source_read = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    # vcopy "Delete this" (positions 12-22)
    copy_span = Span(Address(1, 12), Offset(0, 12))
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(target_opened)

    # Get contents before deletion
    target_read1 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    t_vs1 = session.retrieve_vspanset(target_read1)
    t_ss1 = SpecSet(VSpec(target_read1, list(t_vs1.spans)))
    target_before = session.retrieve_contents(t_ss1)
    session.close_document(target_read1)

    source_read2 = session.open_document(source_doc, READ_ONLY, CONFLICT_COPY)
    s_vs1 = session.retrieve_vspanset(source_read2)
    s_ss1 = SpecSet(VSpec(source_read2, list(s_vs1.spans)))
    source_before = session.retrieve_contents(s_ss1)
    session.close_document(source_read2)

    # Delete "Delete this. " from source (positions 12-24)
    source_opened2 = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.remove(source_opened2, Span(Address(1, 12), Offset(0, 13)))
    s_vs2 = session.retrieve_vspanset(source_opened2)
    s_ss2 = SpecSet(VSpec(source_opened2, list(s_vs2.spans)))
    source_after = session.retrieve_contents(s_ss2)
    session.close_document(source_opened2)

    # Get target contents after source deletion
    target_read2 = session.open_document(target_doc, READ_ONLY, CONFLICT_COPY)
    t_vs2 = session.retrieve_vspanset(target_read2)
    t_ss2 = SpecSet(VSpec(target_read2, list(t_vs2.spans)))
    target_after = session.retrieve_contents(t_ss2)
    session.close_document(target_read2)

    return {
        "name": "vcopy_source_deleted",
        "description": "Test vcopy behavior when transcluded content is deleted from source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source", "text": "Keep this. Delete this. Keep end."},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "vcopy", "from": "source", "to": "target", "text": "Delete this."},
            {"op": "contents", "doc": "source", "label": "before_delete",
             "result": source_before},
            {"op": "contents", "doc": "target", "label": "before_delete",
             "result": target_before},
            {"op": "remove", "doc": "source", "text": "Delete this. ",
             "comment": "Delete the transcluded section from source"},
            {"op": "contents", "doc": "source", "label": "after_delete",
             "result": source_after},
            {"op": "contents", "doc": "target", "label": "after_delete",
             "result": target_after,
             "comment": "Target should still have the content (it references the identity)"}
        ]
    }


def scenario_vcopy_from_version(session):
    """Transclude content from a specific version of a document."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Version 1 content"])
    session.close_document(orig_opened)

    # Create version and modify it
    version = session.create_version(original)
    ver_opened = session.open_document(version, READ_WRITE, CONFLICT_FAIL)
    ver_vs = session.retrieve_vspanset(ver_opened)
    session.insert(ver_opened, ver_vs.spans[0].end(), [" plus version 2 additions"])
    session.close_document(ver_opened)

    # Create target document and vcopy from the VERSION (not original)
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["From version: "])

    ver_read = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    ver_vs2 = session.retrieve_vspanset(ver_read)
    # Copy all content from version
    ver_specs = SpecSet(VSpec(ver_read, list(ver_vs2.spans)))
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), ver_specs)
    session.close_document(ver_read)
    session.close_document(target_opened)

    # Get all contents
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    o_vs = session.retrieve_vspanset(orig_read)
    o_ss = SpecSet(VSpec(orig_read, list(o_vs.spans)))
    orig_contents = session.retrieve_contents(o_ss)
    session.close_document(orig_read)

    ver_read2 = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    v_vs = session.retrieve_vspanset(ver_read2)
    v_ss = SpecSet(VSpec(ver_read2, list(v_vs.spans)))
    ver_contents = session.retrieve_contents(v_ss)
    session.close_document(ver_read2)

    target_read = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    t_vs = session.retrieve_vspanset(target_read)
    t_ss = SpecSet(VSpec(target_read, list(t_vs.spans)))
    target_contents = session.retrieve_contents(t_ss)
    session.close_document(target_read)

    # Compare target with original and version
    target_read2 = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    orig_read2 = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_read3 = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    t_vs2 = session.retrieve_vspanset(target_read2)
    o_vs2 = session.retrieve_vspanset(orig_read2)
    v_vs2 = session.retrieve_vspanset(ver_read3)

    t_ss2 = SpecSet(VSpec(target_read2, list(t_vs2.spans)))
    o_ss2 = SpecSet(VSpec(orig_read2, list(o_vs2.spans)))
    v_ss2 = SpecSet(VSpec(ver_read3, list(v_vs2.spans)))

    shared_with_orig = session.compare_versions(t_ss2, o_ss2)
    shared_with_ver = session.compare_versions(t_ss2, v_ss2)

    shared_orig_result = []
    for span_a, span_b in shared_with_orig:
        shared_orig_result.append({
            "target": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "original": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    shared_ver_result = []
    for span_a, span_b in shared_with_ver:
        shared_ver_result.append({
            "target": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "version": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(target_read2)
    session.close_document(orig_read2)
    session.close_document(ver_read3)

    return {
        "name": "vcopy_from_version",
        "description": "Transclude content from a specific version of a document",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Version 1 content"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "insert", "doc": "version", "text": " plus version 2 additions"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "from": "version", "to": "target"},
            {"op": "contents", "doc": "original", "result": orig_contents},
            {"op": "contents", "doc": "version", "result": ver_contents},
            {"op": "contents", "doc": "target", "result": target_contents},
            {"op": "compare", "docs": ["target", "original"],
             "shared": shared_orig_result,
             "comment": "Should share 'Version 1 content' with original"},
            {"op": "compare", "docs": ["target", "version"],
             "shared": shared_ver_result,
             "comment": "Should share all content with version"}
        ]
    }


def scenario_vcopy_multiple_spans(session):
    """Copy multiple non-contiguous spans in a single vcopy operation."""
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["First part. Middle part. Last part."])
    session.close_document(source_opened)

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Copied: "])

    # vcopy "First part" and "Last part" (skipping middle)
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    span1 = Span(Address(1, 1), Offset(0, 10))   # "First part"
    span2 = Span(Address(1, 26), Offset(0, 10))  # "Last part."
    multi_span_specs = SpecSet(VSpec(source_read, [span1, span2]))

    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), multi_span_specs)
    session.close_document(source_read)

    # Get final target content
    target_final_vs = session.retrieve_vspanset(target_opened)
    target_final_ss = SpecSet(VSpec(target_opened, list(target_final_vs.spans)))
    target_contents = session.retrieve_contents(target_final_ss)
    session.close_document(target_opened)

    # Compare with source - should share "First part" and "Last part"
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    target_read = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    s_vs = session.retrieve_vspanset(source_read2)
    t_vs = session.retrieve_vspanset(target_read)
    s_ss = SpecSet(VSpec(source_read2, list(s_vs.spans)))
    t_ss = SpecSet(VSpec(target_read, list(t_vs.spans)))

    shared = session.compare_versions(s_ss, t_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "source": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "target": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    session.close_document(source_read2)
    session.close_document(target_read)

    return {
        "name": "vcopy_multiple_spans",
        "description": "Copy multiple non-contiguous spans in a single vcopy",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "First part. Middle part. Last part."},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "spans": ["First part", "Last part"],
             "comment": "Skip middle, copy first and last"},
            {"op": "contents", "doc": "target", "result": target_contents},
            {"op": "compare", "shared": shared_result,
             "comment": "Should share 'First part' and 'Last part' but not 'Middle part'"}
        ]
    }


def scenario_vcopy_from_multiple_documents(session):
    """Transclude content from multiple source documents into one target."""
    # Create three source documents
    sources = []
    source_texts = ["Source A text", "Source B text", "Source C text"]
    for text in source_texts:
        docid = session.create_document()
        opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [text])
        session.close_document(opened)
        sources.append(docid)

    # Create target document
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Combined: "])

    # vcopy from each source (first 8 chars: "Source X")
    for source_docid in sources:
        source_read = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
        span = Span(Address(1, 1), Offset(0, 8))  # "Source X"
        specs = SpecSet(VSpec(source_read, [span]))
        target_vs = session.retrieve_vspanset(target_opened)
        session.vcopy(target_opened, target_vs.spans[0].end(), specs)
        # Add separator
        target_vs2 = session.retrieve_vspanset(target_opened)
        session.insert(target_opened, target_vs2.spans[0].end(), [" | "])
        session.close_document(source_read)

    # Get final target content
    target_final_vs = session.retrieve_vspanset(target_opened)
    target_final_ss = SpecSet(VSpec(target_opened, list(target_final_vs.spans)))
    target_contents = session.retrieve_contents(target_final_ss)
    session.close_document(target_opened)

    # Compare target with each source
    comparisons = []
    target_read = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    t_vs = session.retrieve_vspanset(target_read)
    t_ss = SpecSet(VSpec(target_read, list(t_vs.spans)))

    for i, source_docid in enumerate(sources):
        source_read = session.open_document(source_docid, READ_ONLY, CONFLICT_COPY)
        s_vs = session.retrieve_vspanset(source_read)
        s_ss = SpecSet(VSpec(source_read, list(s_vs.spans)))
        shared = session.compare_versions(t_ss, s_ss)

        shared_list = []
        for span_a, span_b in shared:
            shared_list.append({
                "target": span_to_dict(span_a.span),
                "source": span_to_dict(span_b.span)
            })
        comparisons.append({
            "source": chr(65 + i),  # A, B, C
            "shared": shared_list
        })
        session.close_document(source_read)

    session.close_document(target_read)

    return {
        "name": "vcopy_from_multiple_documents",
        "description": "Transclude content from multiple source documents into one target",
        "operations": [
            {"op": "create_documents", "docs": ["A", "B", "C"],
             "texts": source_texts,
             "results": [str(d) for d in sources]},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy_multiple", "from": ["A", "B", "C"], "to": "target"},
            {"op": "contents", "doc": "target", "result": target_contents},
            {"op": "comparisons", "results": comparisons,
             "comment": "Target shares content with each source independently"}
        ]
    }


SCENARIOS = [
    ("content", "vcopy_transclusion", scenario_vcopy),
    ("content", "vcopy_preserves_identity", scenario_vcopy_preserves_identity),
    ("content", "multiple_vcopy_same_source", scenario_multiple_vcopy_same_source),
    ("content", "nested_vcopy", scenario_nested_vcopy),
    ("content", "vcopy_source_modified", scenario_vcopy_source_modified),
    ("content", "vcopy_source_deleted", scenario_vcopy_source_deleted),
    ("content", "vcopy_from_version", scenario_vcopy_from_version),
    ("content", "vcopy_multiple_spans", scenario_vcopy_multiple_spans),
    ("content", "vcopy_from_multiple_documents", scenario_vcopy_from_multiple_documents),
]
