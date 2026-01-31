"""Content identity tracking scenarios.

Tests for the sporgl/provenance system that tracks content identity across
documents, transclusions, and versions.

Key operations tested:
- find_documents (FINDDOCSCONTAINING) - Find all documents containing content
- compare_versions (SHOWRELATIONOF2VERSIONS) - Compare I-address overlap
- Identity preservation through rearrange (pivot/swap)
- Identity tracking through version chains
- Multi-document identity sharing
"""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_find_documents_basic(session):
    """Test FINDDOCSCONTAINING - find all documents containing specific content."""
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Unique content to track"])
    session.close_document(source_opened)

    # Create target that transcludes from source
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target prefix: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 14))  # "Unique content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(), copy_specs)
    session.close_document(source_read)
    session.close_document(target_opened)

    # Now find all documents containing "Unique content"
    # Query from source's vspan
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    query_vspec = VSpec(source_read2, [Span(Address(1, 1), Offset(0, 14))])
    query_specset = SpecSet(query_vspec)

    found_docs = session.find_documents(query_specset)
    session.close_document(source_read2)

    return {
        "name": "find_documents_basic",
        "description": "Find all documents containing specific content via FINDDOCSCONTAINING",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Unique content to track"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "from": "source", "to": "target", "text": "Unique content"},
            {"op": "find_documents",
             "query": "Unique content from source",
             "result": [str(d) for d in found_docs],
             "comment": "Should find both source and target documents"}
        ]
    }


def scenario_find_documents_transitive(session):
    """Test FINDDOCSCONTAINING through transitive transclusion (A→B→C)."""
    # Create chain: C is original, B transcludes from C, A transcludes from B
    doc_c = session.create_document()
    c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(c_opened, Address(1, 1), ["Original content from C"])
    session.close_document(c_opened)

    # B transcludes from C
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["B: "])

    c_read = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_span = Span(Address(1, 1), Offset(0, 16))  # "Original content"
    session.vcopy(b_opened, Address(1, 4), SpecSet(VSpec(c_read, [c_span])))
    session.close_document(c_read)
    session.close_document(b_opened)

    # A transcludes from B
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["A: "])

    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs = session.retrieve_vspanset(b_read)
    session.vcopy(a_opened, Address(1, 4), SpecSet(VSpec(b_read, list(b_vs.spans))))
    session.close_document(b_read)
    session.close_document(a_opened)

    # Find documents containing the original content from C
    c_read2 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    query_vspec = VSpec(c_read2, [Span(Address(1, 1), Offset(0, 8))])  # "Original"
    query_specset = SpecSet(query_vspec)

    found_docs = session.find_documents(query_specset)
    session.close_document(c_read2)

    # Get contents of all documents for verification
    contents = {}
    for doc, name in [(doc_a, "A"), (doc_b, "B"), (doc_c, "C")]:
        r = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
        vs = session.retrieve_vspanset(r)
        ss = SpecSet(VSpec(r, list(vs.spans)))
        contents[name] = session.retrieve_contents(ss)
        session.close_document(r)

    return {
        "name": "find_documents_transitive",
        "description": "Find documents through transitive transclusion chain A→B→C",
        "operations": [
            {"op": "create_chain", "chain": "C→B→A",
             "docs": {"A": str(doc_a), "B": str(doc_b), "C": str(doc_c)}},
            {"op": "contents", "docs": contents},
            {"op": "find_documents",
             "query": "Original (from C)",
             "result": [str(d) for d in found_docs],
             "comment": "Should find A, B, and C - content identity is transitive"}
        ]
    }


def scenario_find_documents_after_source_deletion(session):
    """Test FINDDOCSCONTAINING after content is deleted from source.

    When content is transcluded then deleted from source, the content identity
    still exists (in the target). Can we find it?
    """
    # Create source
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Keep. Transclude this. End."])
    session.close_document(source_opened)

    # Create target with transclusion
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target has: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    # Transclude "Transclude this" (positions 7-21)
    copy_span = Span(Address(1, 7), Offset(0, 15))
    session.vcopy(target_opened, Address(1, 13), SpecSet(VSpec(source_read, [copy_span])))
    session.close_document(source_read)
    session.close_document(target_opened)

    # Find documents BEFORE deletion
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    query_vspec = VSpec(source_read2, [Span(Address(1, 7), Offset(0, 15))])
    found_before = session.find_documents(SpecSet(query_vspec))
    session.close_document(source_read2)

    # Delete the transcluded content from source
    source_opened2 = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.remove(source_opened2, Span(Address(1, 7), Offset(0, 16)))  # Include space
    source_vs_after = session.retrieve_vspanset(source_opened2)
    source_ss_after = SpecSet(VSpec(source_opened2, list(source_vs_after.spans)))
    source_after = session.retrieve_contents(source_ss_after)
    session.close_document(source_opened2)

    # Get target contents (should still have it)
    target_read = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    target_vs = session.retrieve_vspanset(target_read)
    target_ss = SpecSet(VSpec(target_read, list(target_vs.spans)))
    target_contents = session.retrieve_contents(target_ss)

    # Try to find documents containing the content NOW - query from target
    # since source no longer has it
    query_vspec2 = VSpec(target_read, [Span(Address(1, 13), Offset(0, 15))])
    found_after = session.find_documents(SpecSet(query_vspec2))
    session.close_document(target_read)

    return {
        "name": "find_documents_after_source_deletion",
        "description": "Find documents after content is deleted from source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Keep. Transclude this. End."},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "from": "source", "to": "target", "text": "Transclude this"},
            {"op": "find_documents", "label": "before_deletion",
             "result": [str(d) for d in found_before]},
            {"op": "remove", "doc": "source", "text": "Transclude this. "},
            {"op": "contents", "doc": "source", "result": source_after},
            {"op": "contents", "doc": "target", "result": target_contents},
            {"op": "find_documents", "label": "after_deletion",
             "query": "from target's copy",
             "result": [str(d) for d in found_after],
             "comment": "Content still exists in target"}
        ]
    }


def scenario_identity_through_rearrange_pivot(session):
    """Test that rearrange (pivot) preserves content identity."""
    # Create document with content
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["First Second"])
    session.close_document(opened)

    # Create a version BEFORE rearrange for comparison
    version_before = session.create_version(doc)

    # Now pivot "First " and "Second" in the original
    opened2 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    # Pivot at positions 1, 7, 13: swap "First " (1-6) and "Second" (7-12)
    session.pivot(opened2, Address(1, 1), Address(1, 7), Address(1, 13))
    vs_after = session.retrieve_vspanset(opened2)
    ss_after = SpecSet(VSpec(opened2, list(vs_after.spans)))
    contents_after = session.retrieve_contents(ss_after)
    session.close_document(opened2)

    # Compare rearranged document with the pre-rearrange version
    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version_before, READ_ONLY, CONFLICT_COPY)

    doc_vs = session.retrieve_vspanset(doc_read)
    ver_vs = session.retrieve_vspanset(ver_read)

    doc_ss = SpecSet(VSpec(doc_read, list(doc_vs.spans)))
    ver_ss = SpecSet(VSpec(ver_read, list(ver_vs.spans)))

    shared = session.compare_versions(doc_ss, ver_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "rearranged": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "original": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    # Also get version contents for comparison
    ver_ss_full = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss_full)

    session.close_document(doc_read)
    session.close_document(ver_read)

    return {
        "name": "identity_through_rearrange_pivot",
        "description": "Test that pivot operation preserves content identity",
        "operations": [
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "insert", "doc": "doc", "text": "First Second"},
            {"op": "create_version", "doc": "version_before", "result": str(version_before),
             "comment": "Snapshot before rearrange"},
            {"op": "pivot", "doc": "doc", "cuts": [1, 7, 13],
             "comment": "Swap 'First ' and 'Second'"},
            {"op": "contents", "doc": "doc", "label": "after_pivot",
             "result": contents_after},
            {"op": "contents", "doc": "version_before", "result": ver_contents},
            {"op": "compare_versions",
             "doc1": "rearranged",
             "doc2": "original_version",
             "shared": shared_result,
             "comment": "Content identity should be preserved - same I-addresses, different V-positions"}
        ]
    }


def scenario_identity_through_rearrange_swap(session):
    """Test that rearrange (swap) preserves content identity."""
    # Create document with content
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["AAA middle BBB"])
    session.close_document(opened)

    # Create a version BEFORE rearrange
    version_before = session.create_version(doc)

    # Swap "AAA" (1-3) with "BBB" (12-14)
    opened2 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.swap(opened2, Address(1, 1), Address(1, 4), Address(1, 12), Address(1, 15))
    vs_after = session.retrieve_vspanset(opened2)
    ss_after = SpecSet(VSpec(opened2, list(vs_after.spans)))
    contents_after = session.retrieve_contents(ss_after)
    session.close_document(opened2)

    # Compare with pre-swap version
    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    ver_read = session.open_document(version_before, READ_ONLY, CONFLICT_COPY)

    doc_vs = session.retrieve_vspanset(doc_read)
    ver_vs = session.retrieve_vspanset(ver_read)

    doc_ss = SpecSet(VSpec(doc_read, list(doc_vs.spans)))
    ver_ss = SpecSet(VSpec(ver_read, list(ver_vs.spans)))

    shared = session.compare_versions(doc_ss, ver_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "swapped": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "original": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    ver_ss_full = SpecSet(VSpec(ver_read, list(ver_vs.spans)))
    ver_contents = session.retrieve_contents(ver_ss_full)

    session.close_document(doc_read)
    session.close_document(ver_read)

    return {
        "name": "identity_through_rearrange_swap",
        "description": "Test that swap operation preserves content identity",
        "operations": [
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "insert", "doc": "doc", "text": "AAA middle BBB"},
            {"op": "create_version", "doc": "version_before", "result": str(version_before)},
            {"op": "swap", "doc": "doc", "regions": ["AAA", "BBB"]},
            {"op": "contents", "doc": "doc", "label": "after_swap", "result": contents_after},
            {"op": "contents", "doc": "version_before", "result": ver_contents},
            {"op": "compare_versions",
             "shared": shared_result,
             "comment": "All content should share identity - rearrange doesn't create new content"}
        ]
    }


def scenario_identity_multi_document_sharing(session):
    """Multiple documents share content from same source - all should be discoverable."""
    # Create source
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared content for all"])
    session.close_document(source_opened)

    # Create multiple targets that all transclude from source
    targets = []
    for i in range(4):
        target = session.create_document()
        target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
        session.insert(target_opened, Address(1, 1), [f"Doc {i}: "])

        source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
        copy_span = Span(Address(1, 1), Offset(0, 14))  # "Shared content"
        target_vs = session.retrieve_vspanset(target_opened)
        session.vcopy(target_opened, target_vs.spans[0].end(),
                     SpecSet(VSpec(source_read, [copy_span])))
        session.close_document(source_read)
        session.close_document(target_opened)
        targets.append(target)

    # Find all documents containing "Shared content"
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    query_vspec = VSpec(source_read2, [Span(Address(1, 1), Offset(0, 14))])
    found_docs = session.find_documents(SpecSet(query_vspec))
    session.close_document(source_read2)

    # Get contents of all documents
    all_contents = []
    for i, target in enumerate(targets):
        r = session.open_document(target, READ_ONLY, CONFLICT_COPY)
        vs = session.retrieve_vspanset(r)
        ss = SpecSet(VSpec(r, list(vs.spans)))
        contents = session.retrieve_contents(ss)
        all_contents.append({"doc": f"target_{i}", "docid": str(target), "contents": contents})
        session.close_document(r)

    return {
        "name": "identity_multi_document_sharing",
        "description": "Multiple documents share content from same source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Shared content for all"},
            {"op": "create_multiple_targets", "count": 4,
             "results": [str(t) for t in targets]},
            {"op": "contents", "targets": all_contents},
            {"op": "find_documents",
             "query": "Shared content",
             "result": [str(d) for d in found_docs],
             "expected_count": 5,
             "comment": "Should find source + all 4 targets = 5 documents"}
        ]
    }


def scenario_identity_through_version_chain(session):
    """Test content identity through a deep version chain (4 versions)."""
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original text"])
    session.close_document(orig_opened)

    # Create a chain of 3 more versions, each adding content
    versions = [original]
    for i in range(3):
        new_ver = session.create_version(versions[-1])
        ver_opened = session.open_document(new_ver, READ_WRITE, CONFLICT_FAIL)
        vs = session.retrieve_vspanset(ver_opened)
        session.insert(ver_opened, vs.spans[0].end(), [f" v{i+2}"])
        session.close_document(ver_opened)
        versions.append(new_ver)

    # Compare original (v1) and final version (v4) - should share "Original text"
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    final_read = session.open_document(versions[-1], READ_ONLY, CONFLICT_COPY)

    orig_vs = session.retrieve_vspanset(orig_read)
    final_vs = session.retrieve_vspanset(final_read)

    orig_ss = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    final_ss = SpecSet(VSpec(final_read, list(final_vs.spans)))

    orig_contents = session.retrieve_contents(orig_ss)
    final_contents = session.retrieve_contents(final_ss)

    shared = session.compare_versions(orig_ss, final_ss)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "original": {"docid": str(span_a.docid), "span": span_to_dict(span_a.span)},
            "version": {"docid": str(span_b.docid), "span": span_to_dict(span_b.span)}
        })

    # Find all documents containing "Original"
    query_vspec = VSpec(orig_read, [Span(Address(1, 1), Offset(0, 8))])  # "Original"
    found_docs = session.find_documents(SpecSet(query_vspec))

    session.close_document(orig_read)
    session.close_document(final_read)

    return {
        "name": "identity_through_version_chain",
        "description": "Content identity through a deep version chain (4 versions)",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original text"},
            {"op": "create_version_chain", "count": 3,
             "versions": [str(v) for v in versions],
             "additions": [" v2", " v3", " v4"]},
            {"op": "contents", "doc": "original (v1)", "result": orig_contents},
            {"op": "contents", "doc": "final (v4)", "result": final_contents},
            {"op": "compare_versions",
             "doc1": "original (v1)",
             "doc2": "final (v4)",
             "shared": shared_result,
             "comment": "Original text should be shared across entire version chain"},
            {"op": "find_documents",
             "query": "Original",
             "result": [str(d) for d in found_docs],
             "expected_count": 2,
             "comment": "Should find both original and version"}
        ]
    }


def scenario_identity_partial_transclusion(session):
    """Test identity when transcluding part of already-transcluded content."""
    # C has original content
    doc_c = session.create_document()
    c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(c_opened, Address(1, 1), ["ABCDEFGHIJ"])  # 10 chars
    session.close_document(c_opened)

    # B transcludes all from C
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)

    c_read = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_span = Span(Address(1, 1), Offset(0, 10))
    session.vcopy(b_opened, Address(1, 1), SpecSet(VSpec(c_read, [c_span])))
    session.close_document(c_read)
    session.close_document(b_opened)

    # A transcludes only part from B: "DEFGH" (positions 4-8)
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)

    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    partial_span = Span(Address(1, 4), Offset(0, 5))  # "DEFGH"
    session.vcopy(a_opened, Address(1, 1), SpecSet(VSpec(b_read, [partial_span])))
    session.close_document(b_read)
    session.close_document(a_opened)

    # Get all contents
    contents = {}
    for doc, name in [(doc_a, "A"), (doc_b, "B"), (doc_c, "C")]:
        r = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
        vs = session.retrieve_vspanset(r)
        ss = SpecSet(VSpec(r, list(vs.spans)))
        contents[name] = session.retrieve_contents(ss)
        session.close_document(r)

    # Compare A with C directly - should find shared "DEFGH"
    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    c_read2 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)

    a_vs = session.retrieve_vspanset(a_read)
    c_vs = session.retrieve_vspanset(c_read2)

    a_ss = SpecSet(VSpec(a_read, list(a_vs.spans)))
    c_ss = SpecSet(VSpec(c_read2, list(c_vs.spans)))

    shared_a_c = session.compare_versions(a_ss, c_ss)
    shared_result = []
    for span_a, span_b in shared_a_c:
        shared_result.append({
            "A": {"span": span_to_dict(span_a.span)},
            "C": {"span": span_to_dict(span_b.span)}
        })

    # Find docs containing "DEF" from C
    query_vspec = VSpec(c_read2, [Span(Address(1, 4), Offset(0, 3))])  # "DEF"
    found_docs = session.find_documents(SpecSet(query_vspec))

    session.close_document(a_read)
    session.close_document(c_read2)

    return {
        "name": "identity_partial_transclusion",
        "description": "Identity when transcluding part of already-transcluded content",
        "operations": [
            {"op": "create_documents",
             "docs": {"A": str(doc_a), "B": str(doc_b), "C": str(doc_c)}},
            {"op": "setup",
             "description": "C='ABCDEFGHIJ', B=vcopy(C), A=vcopy('DEFGH' from B)"},
            {"op": "contents", "docs": contents},
            {"op": "compare_versions",
             "doc1": "A",
             "doc2": "C",
             "shared": shared_result,
             "comment": "A and C should share 'DEFGH' even though A transcluded from B"},
            {"op": "find_documents",
             "query": "DEF (from C)",
             "result": [str(d) for d in found_docs],
             "expected_count": 3,
             "comment": "Should find A, B, and C - all have 'DEF'"}
        ]
    }


def scenario_identity_mixed_sources(session):
    """Test document with content from multiple sources maintains separate identities."""
    # Create two independent sources
    source1 = session.create_document()
    s1_opened = session.open_document(source1, READ_WRITE, CONFLICT_FAIL)
    session.insert(s1_opened, Address(1, 1), ["From source one"])
    session.close_document(s1_opened)

    source2 = session.create_document()
    s2_opened = session.open_document(source2, READ_WRITE, CONFLICT_FAIL)
    session.insert(s2_opened, Address(1, 1), ["From source two"])
    session.close_document(s2_opened)

    # Create target with content from both sources
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Mixed: "])

    # vcopy from source1
    s1_read = session.open_document(source1, READ_ONLY, CONFLICT_COPY)
    span1 = Span(Address(1, 1), Offset(0, 11))  # "From source"
    target_vs = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs.spans[0].end(),
                 SpecSet(VSpec(s1_read, [span1])))
    session.close_document(s1_read)

    # Add separator
    target_vs2 = session.retrieve_vspanset(target_opened)
    session.insert(target_opened, target_vs2.spans[0].end(), [" | "])

    # vcopy from source2
    s2_read = session.open_document(source2, READ_ONLY, CONFLICT_COPY)
    span2 = Span(Address(1, 1), Offset(0, 11))  # "From source"
    target_vs3 = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, target_vs3.spans[0].end(),
                 SpecSet(VSpec(s2_read, [span2])))
    session.close_document(s2_read)
    session.close_document(target_opened)

    # Get target contents
    target_read = session.open_document(target, READ_ONLY, CONFLICT_COPY)
    target_vs = session.retrieve_vspanset(target_read)
    target_ss = SpecSet(VSpec(target_read, list(target_vs.spans)))
    target_contents = session.retrieve_contents(target_ss)

    # Compare target with source1 and source2
    s1_read2 = session.open_document(source1, READ_ONLY, CONFLICT_COPY)
    s2_read2 = session.open_document(source2, READ_ONLY, CONFLICT_COPY)

    s1_vs = session.retrieve_vspanset(s1_read2)
    s2_vs = session.retrieve_vspanset(s2_read2)

    s1_ss = SpecSet(VSpec(s1_read2, list(s1_vs.spans)))
    s2_ss = SpecSet(VSpec(s2_read2, list(s2_vs.spans)))
    target_ss2 = SpecSet(VSpec(target_read, list(target_vs.spans)))

    shared_with_s1 = session.compare_versions(target_ss2, s1_ss)
    shared_with_s2 = session.compare_versions(target_ss2, s2_ss)

    # Compare source1 with source2 - should have NO shared content
    shared_s1_s2 = session.compare_versions(s1_ss, s2_ss)

    session.close_document(target_read)
    session.close_document(s1_read2)
    session.close_document(s2_read2)

    def format_shared(shared):
        return [{"a": span_to_dict(a.span), "b": span_to_dict(b.span)} for a, b in shared]

    return {
        "name": "identity_mixed_sources",
        "description": "Document with content from multiple sources maintains separate identities",
        "operations": [
            {"op": "create_sources",
             "source1": str(source1), "source2": str(source2)},
            {"op": "create_target", "result": str(target)},
            {"op": "vcopy_from_both", "order": ["source1", "source2"]},
            {"op": "contents", "doc": "target", "result": target_contents},
            {"op": "compare", "label": "target_vs_source1",
             "shared": format_shared(shared_with_s1),
             "comment": "Target shares 'From source' with source1"},
            {"op": "compare", "label": "target_vs_source2",
             "shared": format_shared(shared_with_s2),
             "comment": "Target shares 'From source' with source2"},
            {"op": "compare", "label": "source1_vs_source2",
             "shared": format_shared(shared_s1_s2),
             "comment": "Sources should NOT share content - independent identities"}
        ]
    }


def scenario_find_documents_empty_result(session):
    """Test FINDDOCSCONTAINING with content that exists in only one document."""
    # Create a document with unique content
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Completely unique content"])
    session.close_document(opened)

    # Create another document with different content (no transclusion)
    other = session.create_document()
    other_opened = session.open_document(other, READ_WRITE, CONFLICT_FAIL)
    session.insert(other_opened, Address(1, 1), ["Different content"])
    session.close_document(other_opened)

    # Find documents containing unique content
    doc_read = session.open_document(doc, READ_ONLY, CONFLICT_COPY)
    query_vspec = VSpec(doc_read, [Span(Address(1, 1), Offset(0, 10))])  # "Completely"
    found_docs = session.find_documents(SpecSet(query_vspec))
    session.close_document(doc_read)

    return {
        "name": "find_documents_empty_result",
        "description": "FINDDOCSCONTAINING with content in only one document",
        "operations": [
            {"op": "create_document", "doc": "doc", "result": str(doc)},
            {"op": "insert", "doc": "doc", "text": "Completely unique content"},
            {"op": "create_document", "doc": "other", "result": str(other)},
            {"op": "insert", "doc": "other", "text": "Different content"},
            {"op": "find_documents",
             "query": "Completely",
             "result": [str(d) for d in found_docs],
             "expected_count": 1,
             "comment": "Should find only the original document"}
        ]
    }


SCENARIOS = [
    ("identity", "find_documents_basic", scenario_find_documents_basic),
    ("identity", "find_documents_transitive", scenario_find_documents_transitive),
    ("identity", "find_documents_after_source_deletion", scenario_find_documents_after_source_deletion),
    ("identity", "identity_through_rearrange_pivot", scenario_identity_through_rearrange_pivot),
    ("identity", "identity_through_rearrange_swap", scenario_identity_through_rearrange_swap),
    ("identity", "identity_multi_document_sharing", scenario_identity_multi_document_sharing),
    ("identity", "identity_through_version_chain", scenario_identity_through_version_chain),
    ("identity", "identity_partial_transclusion", scenario_identity_partial_transclusion),
    ("identity", "identity_mixed_sources", scenario_identity_mixed_sources),
    ("identity", "find_documents_empty_result", scenario_find_documents_empty_result),
]
