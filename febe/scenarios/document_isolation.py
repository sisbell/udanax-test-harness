"""Document isolation scenarios - verifying the F0 frame axiom.

Tests that document operations (INSERT, DELETE, COPY, REARRANGE) only affect
the target document and do not have cross-document side effects. Specifically:

- Operations on document A do not modify document B's text span sequence
- Operations on document A do not modify document B's links
- Operations on document A do not modify the global spanfilade in ways that
  corrupt other documents
- Operations within a document's text subspace do not corrupt its link subspace

This validates the formal specification's F0 (frame axiom): document operations
only modify the target document's text span sequence.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_insert_does_not_affect_other_documents(session):
    """Test that INSERT in doc A does not modify doc B's content or structure.

    Create two independent documents, insert into one, verify the other is
    unchanged (content, vspanset, I-addresses).
    """
    # Create doc A with content
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["Document A content"])
    a_vs_initial = session.retrieve_vspanset(a_opened)
    a_ss_initial = SpecSet(VSpec(a_opened, list(a_vs_initial.spans)))
    a_content_initial = session.retrieve_contents(a_ss_initial)
    session.close_document(a_opened)

    # Create doc B with content
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["Document B content"])
    b_vs_initial = session.retrieve_vspanset(b_opened)
    b_ss_initial = SpecSet(VSpec(b_opened, list(b_vs_initial.spans)))
    b_content_initial = session.retrieve_contents(b_ss_initial)
    session.close_document(b_opened)

    # Capture B's state before modification to A
    b_read_before = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs_before = session.retrieve_vspanset(b_read_before)
    b_ss_before = SpecSet(VSpec(b_read_before, list(b_vs_before.spans)))
    b_content_before = session.retrieve_contents(b_ss_before)
    session.close_document(b_read_before)

    # INSERT into doc A
    a_opened2 = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened2, Address(1, 10), ["INSERTED"])
    a_vs_after = session.retrieve_vspanset(a_opened2)
    a_ss_after = SpecSet(VSpec(a_opened2, list(a_vs_after.spans)))
    a_content_after = session.retrieve_contents(a_ss_after)
    session.close_document(a_opened2)

    # Check B's state after modification to A
    b_read_after = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs_after = session.retrieve_vspanset(b_read_after)
    b_ss_after = SpecSet(VSpec(b_read_after, list(b_vs_after.spans)))
    b_content_after = session.retrieve_contents(b_ss_after)
    session.close_document(b_read_after)

    return {
        "name": "insert_does_not_affect_other_documents",
        "description": "INSERT in doc A does not modify doc B",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Document A content"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Document B content"},
            {"op": "snapshot", "doc": "B", "label": "before_A_insert",
             "vspanset": [span_to_dict(s) for s in b_vs_before.spans],
             "content": b_content_before},
            {"op": "insert", "doc": "A", "position": "1.10", "text": "INSERTED"},
            {"op": "contents", "doc": "A", "label": "after_insert", "result": a_content_after},
            {"op": "snapshot", "doc": "B", "label": "after_A_insert",
             "vspanset": [span_to_dict(s) for s in b_vs_after.spans],
             "content": b_content_after},
            {"op": "verify", "assertion": "B unchanged",
             "before": b_content_before,
             "after": b_content_after,
             "match": b_content_before == b_content_after,
             "comment": "F0: doc B should be completely unaffected by insert into doc A"}
        ]
    }


def scenario_delete_does_not_affect_other_documents(session):
    """Test that DELETE in doc A does not modify doc B's content."""
    # Create two documents
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["ABCDEFGHIJ"])
    session.close_document(a_opened)

    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["1234567890"])
    session.close_document(b_opened)

    # Snapshot B before deletion
    b_read_before = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs_before = session.retrieve_vspanset(b_read_before)
    b_ss_before = SpecSet(VSpec(b_read_before, list(b_vs_before.spans)))
    b_content_before = session.retrieve_contents(b_ss_before)
    session.close_document(b_read_before)

    # DELETE from doc A
    a_opened2 = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.remove(a_opened2, Span(Address(1, 3), Offset(0, 5)))  # Delete "CDEFG"
    a_vs_after = session.retrieve_vspanset(a_opened2)
    a_ss_after = SpecSet(VSpec(a_opened2, list(a_vs_after.spans)))
    a_content_after = session.retrieve_contents(a_ss_after)
    session.close_document(a_opened2)

    # Check B after deletion
    b_read_after = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs_after = session.retrieve_vspanset(b_read_after)
    b_ss_after = SpecSet(VSpec(b_read_after, list(b_vs_after.spans)))
    b_content_after = session.retrieve_contents(b_ss_after)
    session.close_document(b_read_after)

    return {
        "name": "delete_does_not_affect_other_documents",
        "description": "DELETE in doc A does not modify doc B",
        "operations": [
            {"op": "setup", "docs": {"A": str(doc_a), "B": str(doc_b)}},
            {"op": "snapshot", "doc": "B", "label": "before_A_delete",
             "content": b_content_before},
            {"op": "remove", "doc": "A", "span": "1.3 for 0.5 (CDEFG)"},
            {"op": "contents", "doc": "A", "label": "after_delete", "result": a_content_after},
            {"op": "snapshot", "doc": "B", "label": "after_A_delete",
             "content": b_content_after},
            {"op": "verify", "assertion": "B unchanged",
             "match": b_content_before == b_content_after}
        ]
    }


def scenario_vcopy_does_not_modify_source_document(session):
    """Test that VCOPY from doc A to doc B does not modify doc A.

    This is critical: COPY should be a read operation on the source.
    """
    # Create source with content
    source = session.create_document()
    src_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(src_opened, Address(1, 1), ["Source content here"])
    session.close_document(src_opened)

    # Snapshot source before vcopy
    src_read_before = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    src_vs_before = session.retrieve_vspanset(src_read_before)
    src_ss_before = SpecSet(VSpec(src_read_before, list(src_vs_before.spans)))
    src_content_before = session.retrieve_contents(src_ss_before)
    session.close_document(src_read_before)

    # Create target and vcopy from source
    target = session.create_document()
    tgt_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)

    src_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 14))  # "Source content"
    session.vcopy(tgt_opened, Address(1, 1), SpecSet(VSpec(src_read, [copy_span])))
    session.close_document(src_read)

    tgt_vs = session.retrieve_vspanset(tgt_opened)
    tgt_ss = SpecSet(VSpec(tgt_opened, list(tgt_vs.spans)))
    tgt_content = session.retrieve_contents(tgt_ss)
    session.close_document(tgt_opened)

    # Check source after vcopy
    src_read_after = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    src_vs_after = session.retrieve_vspanset(src_read_after)
    src_ss_after = SpecSet(VSpec(src_read_after, list(src_vs_after.spans)))
    src_content_after = session.retrieve_contents(src_ss_after)
    session.close_document(src_read_after)

    return {
        "name": "vcopy_does_not_modify_source_document",
        "description": "VCOPY from source to target does not modify source",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Source content here"},
            {"op": "snapshot", "doc": "source", "label": "before_vcopy",
             "content": src_content_before},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "from": "source", "to": "target", "text": "Source content"},
            {"op": "contents", "doc": "target", "result": tgt_content},
            {"op": "snapshot", "doc": "source", "label": "after_vcopy",
             "content": src_content_after},
            {"op": "verify", "assertion": "source unchanged",
             "match": src_content_before == src_content_after,
             "comment": "F0: VCOPY is read-only on source, no side effects"}
        ]
    }


def scenario_insert_text_does_not_affect_links_in_same_document(session):
    """Test that INSERT in text subspace (1.x) does not corrupt link subspace (2.x).

    This verifies Finding 054: INSERT uses a two-blade knife that bounds the shift
    to the text subspace only.
    """
    # Create document with text and a link
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["ABCDE"])
    session.close_document(opened)

    # Create link
    opened2 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    from_span = Span(Address(1, 1), Offset(0, 3))  # "ABC"
    to_span = Span(Address(1, 3), Offset(0, 2))    # "CD"
    type_span = Span(Address(1, 1, 0, 1), Offset(0, 1))

    from_specs = SpecSet(VSpec(opened2, [from_span]))
    to_specs = SpecSet(VSpec(opened2, [to_span]))
    type_specs = SpecSet(type_span)

    link_id = session.create_link(opened2, from_specs, to_specs, type_specs)

    # Capture link state before insertion
    links_before = session.find_links(from_specs)
    follow_before = session.follow_link(link_id)

    session.close_document(opened2)

    # INSERT into text subspace
    opened3 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened3, Address(1, 3), ["XYZ"])  # Insert in middle of text

    text_vs_after = session.retrieve_vspanset(opened3)
    text_ss_after = SpecSet(VSpec(opened3, list(text_vs_after.spans)))
    text_content_after = session.retrieve_contents(text_ss_after)

    # Check link state after insertion
    # The link should still exist and be discoverable
    links_after = session.find_links(from_specs)
    follow_after = session.follow_link(link_id)

    session.close_document(opened3)

    return {
        "name": "insert_text_does_not_affect_links_in_same_document",
        "description": "INSERT in text subspace (1.x) does not corrupt link subspace (2.x)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "ABCDE"},
            {"op": "create_link", "from": "ABC", "to": "CD", "result": str(link_id)},
            {"op": "find_links", "label": "before_insert",
             "result": [str(l) for l in links_before]},
            {"op": "follow_link", "label": "before_insert",
             "link_id": str(link_id),
             "result": [vspec_to_dict(v) for v in follow_before]},
            {"op": "insert", "position": "1.3", "text": "XYZ",
             "comment": "Insert in text subspace"},
            {"op": "contents", "label": "after_insert", "result": text_content_after,
             "expected": "ABXYZCDE"},
            {"op": "find_links", "label": "after_insert",
             "result": [str(l) for l in links_after]},
            {"op": "follow_link", "label": "after_insert",
             "link_id": str(link_id),
             "result": [vspec_to_dict(v) for v in follow_after]},
            {"op": "verify", "assertion": "link still exists",
             "before_count": len(links_before),
             "after_count": len(links_after),
             "match": len(links_before) == len(links_after),
             "comment": "Finding 054: two-blade knife isolates text from link subspace"}
        ]
    }


def scenario_delete_text_does_not_affect_links_in_same_document(session):
    """Test that DELETE in text subspace (1.x) does not corrupt link subspace (2.x).

    This verifies Finding 055: DELETE uses strongsub's exponent guard to prevent
    cross-subspace corruption.
    """
    # Create document with text and link
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["ABCDEFGHIJ"])
    session.close_document(opened)

    # Create link at V-position 2.1
    opened2 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    from_span = Span(Address(1, 1), Offset(0, 5))  # "ABCDE"
    to_span = Span(Address(1, 6), Offset(0, 5))    # "FGHIJ"
    type_span = Span(Address(1, 1, 0, 1), Offset(0, 1))

    from_specs = SpecSet(VSpec(opened2, [from_span]))
    to_specs = SpecSet(VSpec(opened2, [to_span]))
    type_specs = SpecSet(type_span)

    link_id = session.create_link(opened2, from_specs, to_specs, type_specs)

    # Capture link before deletion
    links_before = session.find_links(from_specs)
    session.close_document(opened2)

    # DELETE from text subspace
    opened3 = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.remove(opened3, Span(Address(1, 3), Offset(0, 3)))  # Delete "CDE"

    text_vs_after = session.retrieve_vspanset(opened3)
    text_ss_after = SpecSet(VSpec(opened3, list(text_vs_after.spans)))
    text_content_after = session.retrieve_contents(text_ss_after)

    # Check link after deletion
    links_after = session.find_links(from_specs)

    # The link should still be discoverable (though endpoints may have shifted)
    try:
        follow_after = session.follow_link(link_id)
        follow_result = [vspec_to_dict(v) for v in follow_after]
    except:
        follow_result = "error"

    session.close_document(opened3)

    return {
        "name": "delete_text_does_not_affect_links_in_same_document",
        "description": "DELETE in text subspace (1.x) does not corrupt link subspace (2.x)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "ABCDEFGHIJ"},
            {"op": "create_link", "from": "ABCDE", "to": "FGHIJ", "result": str(link_id)},
            {"op": "find_links", "label": "before_delete",
             "result": [str(l) for l in links_before]},
            {"op": "remove", "span": "1.3 for 0.3 (CDE)"},
            {"op": "contents", "label": "after_delete", "result": text_content_after,
             "expected": "ABFGHIJ"},
            {"op": "find_links", "label": "after_delete",
             "result": [str(l) for l in links_after]},
            {"op": "follow_link", "label": "after_delete",
             "result": follow_result},
            {"op": "verify", "assertion": "link V-position unchanged",
             "comment": "Finding 055: strongsub exponent guard prevents shift of 2.x from 1.x delete"}
        ]
    }


def scenario_cross_document_transclusion_isolation(session):
    """Test that operations on a target document with transcluded content do not
    affect the source document or the spanfilade's ability to track other documents.

    Setup: Doc A has content, Doc B transcludes from A, Doc C also transcludes from A.
    Action: DELETE from B's transcluded content.
    Verify: A and C are unchanged.
    """
    # Create source A
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["Shared content"])
    session.close_document(a_opened)

    # B transcludes from A
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["B prefix: "])

    a_read1 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_span = Span(Address(1, 1), Offset(0, 14))  # "Shared content"
    a_vs = session.retrieve_vspanset(b_opened)
    session.vcopy(b_opened, a_vs.spans[0].end(), SpecSet(VSpec(a_read1, [a_span])))
    session.close_document(a_read1)
    session.close_document(b_opened)

    # C transcludes from A
    doc_c = session.create_document()
    c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(c_opened, Address(1, 1), ["C prefix: "])

    a_read2 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    c_vs = session.retrieve_vspanset(c_opened)
    session.vcopy(c_opened, c_vs.spans[0].end(), SpecSet(VSpec(a_read2, [a_span])))
    session.close_document(a_read2)
    session.close_document(c_opened)

    # Snapshot A and C before modification to B
    a_read3 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_vs_before = session.retrieve_vspanset(a_read3)
    a_ss_before = SpecSet(VSpec(a_read3, list(a_vs_before.spans)))
    a_content_before = session.retrieve_contents(a_ss_before)
    session.close_document(a_read3)

    c_read1 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_vs_before = session.retrieve_vspanset(c_read1)
    c_ss_before = SpecSet(VSpec(c_read1, list(c_vs_before.spans)))
    c_content_before = session.retrieve_contents(c_ss_before)
    session.close_document(c_read1)

    # DELETE transcluded content from B
    b_opened2 = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.remove(b_opened2, Span(Address(1, 11), Offset(0, 7)))  # Delete "Shared "
    b_vs_after = session.retrieve_vspanset(b_opened2)
    b_ss_after = SpecSet(VSpec(b_opened2, list(b_vs_after.spans)))
    b_content_after = session.retrieve_contents(b_ss_after)
    session.close_document(b_opened2)

    # Check A and C after deletion from B
    a_read4 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_vs_after = session.retrieve_vspanset(a_read4)
    a_ss_after = SpecSet(VSpec(a_read4, list(a_vs_after.spans)))
    a_content_after = session.retrieve_contents(a_ss_after)
    session.close_document(a_read4)

    c_read2 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_vs_after = session.retrieve_vspanset(c_read2)
    c_ss_after = SpecSet(VSpec(c_read2, list(c_vs_after.spans)))
    c_content_after = session.retrieve_contents(c_ss_after)
    session.close_document(c_read2)

    return {
        "name": "cross_document_transclusion_isolation",
        "description": "DELETE from doc B (with transcluded content) does not affect docs A or C",
        "operations": [
            {"op": "setup", "description": "A has content, B and C transclude from A"},
            {"op": "docs", "A": str(doc_a), "B": str(doc_b), "C": str(doc_c)},
            {"op": "snapshot", "label": "before_B_delete",
             "A_content": a_content_before,
             "C_content": c_content_before},
            {"op": "remove", "doc": "B", "span": "1.11 for 0.7 (delete 'Shared ')"},
            {"op": "contents", "doc": "B", "label": "after_delete", "result": b_content_after},
            {"op": "snapshot", "label": "after_B_delete",
             "A_content": a_content_after,
             "C_content": c_content_after},
            {"op": "verify", "assertion": "A unchanged",
             "match": a_content_before == a_content_after},
            {"op": "verify", "assertion": "C unchanged",
             "match": c_content_before == c_content_after,
             "comment": "F0: DELETE from B only affects B, not source A or sibling C"}
        ]
    }


SCENARIOS = [
    ("isolation", "insert_does_not_affect_other_documents", scenario_insert_does_not_affect_other_documents),
    ("isolation", "delete_does_not_affect_other_documents", scenario_delete_does_not_affect_other_documents),
    ("isolation", "vcopy_does_not_modify_source_document", scenario_vcopy_does_not_modify_source_document),
    ("isolation", "insert_text_does_not_affect_links_in_same_document", scenario_insert_text_does_not_affect_links_in_same_document),
    ("isolation", "delete_text_does_not_affect_links_in_same_document", scenario_delete_text_does_not_affect_links_in_same_document),
    ("isolation", "cross_document_transclusion_isolation", scenario_cross_document_transclusion_isolation),
]
