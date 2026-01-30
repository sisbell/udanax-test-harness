"""Content manipulation scenarios (insert, delete, retrieve, vcopy)."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


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
    ("content", "vcopy_transclusion", scenario_vcopy),
    ("content", "vcopy_preserves_identity", scenario_vcopy_preserves_identity),
    ("content", "multiple_vcopy_same_source", scenario_multiple_vcopy_same_source),
]
