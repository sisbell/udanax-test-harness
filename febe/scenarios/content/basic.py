"""Basic content manipulation scenarios (insert, delete, retrieve, rearrange)."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from ..common import vspec_to_dict, span_to_dict


def scenario_insert_text(session):
    """Create document and insert text."""
    docid = session.create_document()

    # Open document for writing
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text at position 1.1
    session.insert(opened_docid, Address(1, 1), ["Hello, World!"])

    # Retrieve content
    vspanset = session.retrieve_vspanset(opened_docid)
    specset = SpecSet(VSpec(opened_docid, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    # Close document
    session.close_document(opened_docid)

    return {
        "name": "insert_text",
        "description": "Create document and insert text",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Hello, World!"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset)},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_multiple_inserts(session):
    """Insert text at multiple positions."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert first text
    session.insert(opened_docid, Address(1, 1), ["First "])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Insert second text (appending)
    session.insert(opened_docid, vspanset1.spans[0].end(), ["Second "])
    vspanset2 = session.retrieve_vspanset(opened_docid)

    # Insert third text
    session.insert(opened_docid, vspanset2.spans[0].end(), ["Third"])
    vspanset3 = session.retrieve_vspanset(opened_docid)

    # Retrieve all content
    specset = SpecSet(VSpec(opened_docid, list(vspanset3.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "multiple_inserts",
        "description": "Insert text at multiple positions sequentially",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "First "},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "insert", "doc": str(opened_docid), "address": str(vspanset1.spans[0].end()), "text": "Second "},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset2)},
            {"op": "insert", "doc": str(opened_docid), "address": str(vspanset2.spans[0].end()), "text": "Third"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset3)},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_insert_middle(session):
    """Insert text in the middle of existing content."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert initial text
    session.insert(opened_docid, Address(1, 1), ["HelloWorld"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Insert ", " in the middle (after "Hello")
    session.insert(opened_docid, Address(1, 6), [", "])
    vspanset2 = session.retrieve_vspanset(opened_docid)

    # Retrieve content
    specset = SpecSet(VSpec(opened_docid, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "insert_middle",
        "description": "Insert text in the middle of existing content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "HelloWorld"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.6", "text": ", "},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_insert_beginning(session):
    """Insert text at the beginning (prepend) of existing content."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert initial text
    session.insert(opened_docid, Address(1, 1), ["World!"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Prepend "Hello, " at the beginning
    session.insert(opened_docid, Address(1, 1), ["Hello, "])
    vspanset2 = session.retrieve_vspanset(opened_docid)

    # Retrieve full content
    specset = SpecSet(VSpec(opened_docid, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "insert_beginning",
        "description": "Insert text at the beginning (prepend) of existing content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "World!"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Hello, ",
             "comment": "Prepend at beginning"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_delete_text(session):
    """Insert text then delete a portion using remove (DELETEVSPAN)."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text
    session.insert(opened_docid, Address(1, 1), ["Hello, World!"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Delete ", World" using remove (DELETEVSPAN) - span from position 6, width 7
    delete_vspan = VSpan(opened_docid, Span(Address(1, 6), Offset(0, 7)))
    session.remove(opened_docid, delete_vspan.span)

    # Retrieve remaining content
    vspanset2 = session.retrieve_vspanset(opened_docid)
    specset = SpecSet(VSpec(opened_docid, list(vspanset2.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "delete_text",
        "description": "Insert text then delete a portion using remove",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Hello, World!"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "remove", "doc": str(opened_docid), "span": span_to_dict(delete_vspan.span)},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset2)},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_multiple_deletes(session):
    """Delete multiple non-contiguous regions from a document."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text: "The quick brown fox jumps"
    session.insert(opened_docid, Address(1, 1), ["The quick brown fox jumps"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Delete "quick " (positions 5-10)
    session.remove(opened_docid, Span(Address(1, 5), Offset(0, 6)))
    vspanset2 = session.retrieve_vspanset(opened_docid)
    specset2 = SpecSet(VSpec(opened_docid, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    # Delete "fox " (now at different position after first delete)
    # Original: "The brown fox jumps" -> delete "fox "
    session.remove(opened_docid, Span(Address(1, 11), Offset(0, 4)))
    vspanset3 = session.retrieve_vspanset(opened_docid)
    specset3 = SpecSet(VSpec(opened_docid, list(vspanset3.spans)))
    contents3 = session.retrieve_contents(specset3)

    session.close_document(opened_docid)

    return {
        "name": "multiple_deletes",
        "description": "Delete multiple non-contiguous regions from a document",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "The quick brown fox jumps"},
            {"op": "remove", "doc": str(opened_docid), "span": span_to_dict(Span(Address(1, 5), Offset(0, 6))),
             "comment": "Delete 'quick '"},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents2},
            {"op": "remove", "doc": str(opened_docid), "span": span_to_dict(Span(Address(1, 11), Offset(0, 4))),
             "comment": "Delete 'fox '"},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents3},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_delete_all(session):
    """Delete all content from a document."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text
    session.insert(opened_docid, Address(1, 1), ["Content to delete"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # Delete all content
    session.remove(opened_docid, Span(Address(1, 1), Offset(0, 17)))
    vspanset2 = session.retrieve_vspanset(opened_docid)

    session.close_document(opened_docid)

    return {
        "name": "delete_all",
        "description": "Delete all content from a document",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Content to delete"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset1)},
            {"op": "remove", "doc": str(opened_docid), "span": span_to_dict(Span(Address(1, 1), Offset(0, 17))),
             "comment": "Delete all content"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset2),
             "comment": "Should be empty"},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_partial_retrieve(session):
    """Retrieve only a portion of document content."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text
    session.insert(opened_docid, Address(1, 1), ["The quick brown fox jumps over the lazy dog"])
    vspanset = session.retrieve_vspanset(opened_docid)

    # Retrieve only "quick brown" (positions 5-16)
    partial_span = Span(Address(1, 5), Offset(0, 11))
    partial_specset = SpecSet(VSpec(opened_docid, [partial_span]))
    partial_contents = session.retrieve_contents(partial_specset)

    session.close_document(opened_docid)

    return {
        "name": "partial_retrieve",
        "description": "Retrieve only a portion of document content",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "The quick brown fox jumps over the lazy dog"},
            {"op": "retrieve_vspanset", "doc": str(opened_docid), "result": vspec_to_dict(vspanset)},
            {"op": "retrieve_contents",
             "doc": str(opened_docid),
             "span": span_to_dict(partial_span),
             "result": partial_contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_rearrange_content(session):
    """Rearrange content by copying and deleting (cut and paste)."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "World Hello"
    session.insert(opened_docid, Address(1, 1), ["World Hello"])
    vspanset1 = session.retrieve_vspanset(opened_docid)

    # We want to move "Hello" to the beginning
    # First, vcopy "Hello" (positions 7-11) to a temp location at end
    source_ro = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
    hello_span = Span(Address(1, 7), Offset(0, 5))
    copy_specs = SpecSet(VSpec(source_ro, [hello_span]))

    # Insert "Hello " at beginning using vcopy
    session.vcopy(opened_docid, Address(1, 1), copy_specs)
    session.insert(opened_docid, Address(1, 6), [" "])  # Add space after Hello

    vspanset2 = session.retrieve_vspanset(opened_docid)
    specset2 = SpecSet(VSpec(opened_docid, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)

    session.close_document(source_ro)
    session.close_document(opened_docid)

    return {
        "name": "rearrange_content",
        "description": "Rearrange content using vcopy (simulating cut and paste)",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "World Hello"},
            {"op": "vcopy", "doc": str(opened_docid), "address": "1.1",
             "source_span": span_to_dict(hello_span),
             "comment": "Copy 'Hello' to beginning"},
            {"op": "insert", "doc": str(opened_docid), "address": "1.6", "text": " ",
             "comment": "Add space after copied Hello"},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents2},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_retrieve_noncontiguous_spans(session):
    """Retrieve multiple non-contiguous spans from a single document in one call."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert text: "The quick brown fox jumps over the lazy dog"
    session.insert(opened, Address(1, 1), ["The quick brown fox jumps over the lazy dog"])
    vspanset = session.retrieve_vspanset(opened)

    # Retrieve non-contiguous spans: "quick" (5-9) and "lazy" (36-39)
    span1 = Span(Address(1, 5), Offset(0, 5))   # "quick"
    span2 = Span(Address(1, 36), Offset(0, 4))  # "lazy"
    multi_specset = SpecSet(VSpec(opened, [span1, span2]))
    multi_contents = session.retrieve_contents(multi_specset)

    # Also retrieve them separately for comparison
    single1 = SpecSet(VSpec(opened, [span1]))
    single2 = SpecSet(VSpec(opened, [span2]))
    contents1 = session.retrieve_contents(single1)
    contents2 = session.retrieve_contents(single2)

    session.close_document(opened)

    return {
        "name": "retrieve_noncontiguous_spans",
        "description": "Retrieve multiple non-contiguous spans from a document in one call",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1",
             "text": "The quick brown fox jumps over the lazy dog"},
            {"op": "retrieve_contents", "spans": ["quick (5-9)", "lazy (36-39)"],
             "combined": True, "result": multi_contents},
            {"op": "retrieve_contents", "span": "quick", "result": contents1},
            {"op": "retrieve_contents", "span": "lazy", "result": contents2},
            {"op": "close_document", "doc": str(opened)}
        ]
    }


def scenario_retrieve_multiple_documents(session):
    """Retrieve content from multiple documents in a single SpecSet."""
    # Create three documents with different content
    docs = []
    for i, text in enumerate(["Alpha content", "Beta content", "Gamma content"]):
        docid = session.create_document()
        opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [text])
        session.close_document(opened)
        docs.append(docid)

    # Open all for reading
    opened_docs = []
    for docid in docs:
        opened = session.open_document(docid, READ_ONLY, CONFLICT_COPY)
        opened_docs.append(opened)

    # Create a SpecSet with spans from all three documents
    # Get first word from each: "Alpha", "Beta", "Gamma"
    vspecs = []
    for opened in opened_docs:
        vs = session.retrieve_vspanset(opened)
        # First 5 characters of each
        span = Span(Address(1, 1), Offset(0, 5))
        vspecs.append(VSpec(opened, [span]))

    # Retrieve from multiple documents at once
    multi_doc_specset = SpecSet(*vspecs)
    multi_contents = session.retrieve_contents(multi_doc_specset)

    # Close all
    for opened in opened_docs:
        session.close_document(opened)

    return {
        "name": "retrieve_multiple_documents",
        "description": "Retrieve content from multiple documents in a single SpecSet",
        "operations": [
            {"op": "create_documents", "count": 3,
             "texts": ["Alpha content", "Beta content", "Gamma content"],
             "results": [str(d) for d in docs]},
            {"op": "retrieve_contents",
             "specset": "First 5 chars from each document",
             "result": multi_contents,
             "comment": "Should contain 'Alpha', 'Beta', 'Gamma'"}
        ]
    }


def scenario_compare_multispan_specsets(session):
    """Compare documents using SpecSets with multiple spans."""
    # Create two documents with overlapping content structure
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["AAA unique1 BBB shared CCC unique2 DDD"])
    session.close_document(opened1)

    # Create doc2 as version of doc1, then modify
    doc2 = session.create_version(doc1)
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    # Insert something at the beginning to shift things
    session.insert(opened2, Address(1, 1), ["PREFIX "])
    vs2 = session.retrieve_vspanset(opened2)
    session.close_document(opened2)

    # Get contents
    r1 = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    r2 = session.open_document(doc2, READ_ONLY, CONFLICT_COPY)
    vs1 = session.retrieve_vspanset(r1)
    vs2 = session.retrieve_vspanset(r2)

    ss1 = SpecSet(VSpec(r1, list(vs1.spans)))
    ss2 = SpecSet(VSpec(r2, list(vs2.spans)))
    contents1 = session.retrieve_contents(ss1)
    contents2 = session.retrieve_contents(ss2)

    # Compare full documents
    full_shared = session.compare_versions(ss1, ss2)
    full_shared_result = []
    for span_a, span_b in full_shared:
        full_shared_result.append({
            "doc1": span_to_dict(span_a.span),
            "doc2": span_to_dict(span_b.span)
        })

    # Now compare using specific spans - just the "shared" portion
    # In doc1: "shared" is around position 13-18
    span1_specific = Span(Address(1, 13), Offset(0, 6))
    ss1_specific = SpecSet(VSpec(r1, [span1_specific]))

    # Compare specific span with full doc2
    partial_shared = session.compare_versions(ss1_specific, ss2)
    partial_shared_result = []
    for span_a, span_b in partial_shared:
        partial_shared_result.append({
            "doc1_span": span_to_dict(span_a.span),
            "doc2": span_to_dict(span_b.span)
        })

    session.close_document(r1)
    session.close_document(r2)

    return {
        "name": "compare_multispan_specsets",
        "description": "Compare documents using SpecSets with specific spans",
        "operations": [
            {"op": "create_document", "doc": "doc1", "result": str(doc1)},
            {"op": "insert", "doc": "doc1", "text": "AAA unique1 BBB shared CCC unique2 DDD"},
            {"op": "create_version", "from": "doc1", "result": str(doc2)},
            {"op": "insert", "doc": "doc2", "address": "1.1", "text": "PREFIX "},
            {"op": "contents", "doc": "doc1", "result": contents1},
            {"op": "contents", "doc": "doc2", "result": contents2},
            {"op": "compare_full", "shared": full_shared_result,
             "comment": "Full document comparison"},
            {"op": "compare_partial",
             "doc1_span": "shared (13-18)",
             "shared": partial_shared_result,
             "comment": "Compare specific span from doc1 with full doc2"}
        ]
    }


SCENARIOS = [
    ("content", "insert_text", scenario_insert_text),
    ("content", "multiple_inserts", scenario_multiple_inserts),
    ("content", "insert_middle", scenario_insert_middle),
    ("content", "insert_beginning", scenario_insert_beginning),
    ("content", "delete_text", scenario_delete_text),
    ("content", "multiple_deletes", scenario_multiple_deletes),
    ("content", "delete_all", scenario_delete_all),
    ("content", "partial_retrieve", scenario_partial_retrieve),
    ("content", "rearrange_content", scenario_rearrange_content),
    ("content", "retrieve_noncontiguous_spans", scenario_retrieve_noncontiguous_spans),
    ("content", "retrieve_multiple_documents", scenario_retrieve_multiple_documents),
    ("content", "compare_multispan_specsets", scenario_compare_multispan_specsets),
]
