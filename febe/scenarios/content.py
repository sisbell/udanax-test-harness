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


SCENARIOS = [
    ("content", "insert_text", scenario_insert_text),
    ("content", "multiple_inserts", scenario_multiple_inserts),
    ("content", "insert_middle", scenario_insert_middle),
    ("content", "delete_text", scenario_delete_text),
    ("content", "partial_retrieve", scenario_partial_retrieve),
    ("content", "vcopy_transclusion", scenario_vcopy),
]
