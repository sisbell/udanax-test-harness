#!/usr/bin/env python3
"""Generate golden test cases from the Udanax Green backend.

Runs test scenarios against the backend in test mode (fresh state per scenario)
and outputs JSON test cases capturing the expected behavior.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY, ALWAYS_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE
)

# Default account address for test mode
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)


class BackendProcess:
    """Manages a backend subprocess in test mode."""

    def __init__(self, backend_path):
        self.backend_path = backend_path
        self.process = None
        self.session = None

    def start(self):
        """Start the backend and establish a session."""
        # Use PipeStream to communicate with backend
        stream = PipeStream(f"{self.backend_path} --test-mode")
        self.session = XuSession(XuConn(stream))
        # Set up default account for creating documents
        self.session.account(DEFAULT_ACCOUNT)
        return self.session

    def stop(self):
        """Stop the backend."""
        if self.session and self.session.open:
            try:
                self.session.quit()
            except:
                pass
        self.session = None


def addr_to_str(addr):
    """Convert an Address to its string representation."""
    return str(addr)


def offset_to_str(offset):
    """Convert an Offset to its string representation."""
    return str(offset)


def span_to_dict(span):
    """Convert a Span to a dictionary."""
    return {
        "start": str(span.start),
        "width": str(span.width)
    }


def vspec_to_dict(vspec):
    """Convert a VSpec to a dictionary."""
    return {
        "docid": str(vspec.docid),
        "spans": [span_to_dict(s) for s in vspec.spans]
    }


def specset_to_list(specset):
    """Convert a SpecSet to a list of dictionaries."""
    result = []
    for spec in specset.specs:
        if hasattr(spec, 'docid'):
            result.append(vspec_to_dict(spec))
        else:
            result.append({"span": span_to_dict(spec)})
    return result


# =============================================================================
# Test Scenarios
# =============================================================================

def scenario_create_document(session):
    """Create a document and verify its address."""
    docid = session.create_document()
    return {
        "name": "create_document",
        "description": "Create a new empty document",
        "operations": [
            {"op": "create_document", "result": str(docid)}
        ]
    }


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


def scenario_create_link(session):
    """Create two documents and link them."""
    # Create source document
    source_docid = session.create_document()
    source_opened = session.open_document(source_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source document with link text"])
    source_vspanset = session.retrieve_vspanset(source_opened)

    # Create target document
    target_docid = session.create_document()
    target_opened = session.open_document(target_docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document content"])
    target_vspanset = session.retrieve_vspanset(target_opened)

    # Create a link from "link text" (positions 22-30) to target document
    source_span = Span(Address(1, 22), Offset(0, 9))  # "link text"
    source_specs = SpecSet(VSpec(source_opened, [source_span]))

    target_span = Span(Address(1, 1), Offset(0, 23))  # "Target document content"
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    link_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "create_link",
        "description": "Create two documents and link them with a jump link",
        "operations": [
            {"op": "create_document", "result": str(source_docid)},
            {"op": "open_document", "doc": str(source_docid), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Source document with link text"},
            {"op": "create_document", "result": str(target_docid)},
            {"op": "open_document", "doc": str(target_docid), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target document content"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)}
        ]
    }


def scenario_find_links(session):
    """Create links and find them."""
    # Create documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document one content"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document two content"])

    # Create link
    source_span = Span(Address(1, 1), Offset(0, 8))  # "Document"
    source_specs = SpecSet(VSpec(opened1, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 8))  # "Document"
    target_specs = SpecSet(VSpec(opened2, [target_span]))

    link_id = session.create_link(opened1, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Find links from doc1
    search_span = Span(Address(1, 1), Offset(0, 20))
    search_specs = SpecSet(VSpec(opened1, [search_span]))
    found_links = session.find_links(search_specs)

    # Follow the link
    target_result = session.follow_link(found_links[0], LINK_TARGET)
    type_result = session.follow_link(found_links[0], LINK_TYPE)

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "find_links",
        "description": "Create links and find them by searching source spans",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document one content"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document two content"},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]},
            {"op": "follow_link",
             "link": str(found_links[0]),
             "end": "target",
             "result": specset_to_list(target_result)},
            {"op": "follow_link",
             "link": str(found_links[0]),
             "end": "type",
             "result": specset_to_list(type_result)}
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


def scenario_internal_state(session):
    """Demonstrate internal enfilade state capture after operations."""
    docid = session.create_document()
    opened_docid = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Capture initial state (empty document)
    initial_state = session.dump_state()

    # Insert text
    session.insert(opened_docid, Address(1, 1), ["Hello, World!"])

    # Capture state after insert
    after_insert_state = session.dump_state()

    # Get content
    vspanset = session.retrieve_vspanset(opened_docid)
    specset = SpecSet(VSpec(opened_docid, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)

    session.close_document(opened_docid)

    return {
        "name": "internal_state",
        "description": "Capture internal enfilade state after operations",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened_docid)},
            {"op": "dump_state", "state": initial_state},
            {"op": "insert", "doc": str(opened_docid), "address": "1.1", "text": "Hello, World!"},
            {"op": "dump_state", "state": after_insert_state},
            {"op": "retrieve_contents", "doc": str(opened_docid), "result": contents},
            {"op": "close_document", "doc": str(opened_docid)}
        ]
    }


def scenario_multiple_documents(session):
    """Create and populate multiple independent documents."""
    # Create and populate first document
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document One"])
    vspanset1 = session.retrieve_vspanset(opened1)
    specset1 = SpecSet(VSpec(opened1, list(vspanset1.spans)))
    contents1 = session.retrieve_contents(specset1)
    session.close_document(opened1)

    # Create and populate second document
    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document Two"])
    vspanset2 = session.retrieve_vspanset(opened2)
    specset2 = SpecSet(VSpec(opened2, list(vspanset2.spans)))
    contents2 = session.retrieve_contents(specset2)
    session.close_document(opened2)

    return {
        "name": "multiple_documents",
        "description": "Create and populate multiple independent documents",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document One"},
            {"op": "retrieve_contents", "doc": str(opened1), "result": contents1},
            {"op": "close_document", "doc": str(opened1)},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document Two"},
            {"op": "retrieve_contents", "doc": str(opened2), "result": contents2},
            {"op": "close_document", "doc": str(opened2)}
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
             "doc": str(target_opened),
             "address": str(target_vspanset.spans[0].end()),
             "source": specset_to_list(copy_specs)},
            {"op": "retrieve_vspanset", "doc": str(target_opened), "result": vspec_to_dict(final_vspanset)},
            {"op": "retrieve_contents", "doc": str(target_opened), "result": final_contents}
        ]
    }


# =============================================================================
# Main
# =============================================================================

# Working scenarios
WORKING_SCENARIOS = [
    ("documents", "create_document", scenario_create_document),
    ("content", "insert_text", scenario_insert_text),
    ("content", "multiple_inserts", scenario_multiple_inserts),
    ("content", "insert_middle", scenario_insert_middle),
    ("content", "delete_text", scenario_delete_text),
    ("content", "partial_retrieve", scenario_partial_retrieve),
    ("internal", "internal_state", scenario_internal_state),
]

# Scenarios that fail due to backend bugs (abort traps, error responses)
# These need C backend fixes before they can be used
FAILING_SCENARIOS = [
    ("documents", "multiple_documents", scenario_multiple_documents),  # error on second create
    ("content", "vcopy_transclusion", scenario_vcopy),        # error response
    ("versions", "create_version", scenario_create_version),  # abort trap
    ("versions", "compare_versions", scenario_compare_versions),  # abort trap
    ("links", "create_link", scenario_create_link),           # error response
    ("links", "find_links", scenario_find_links),             # error response
]

ALL_SCENARIOS = WORKING_SCENARIOS


def run_scenario(backend_path, category, name, scenario_func):
    """Run a single scenario with a fresh backend."""
    backend = BackendProcess(backend_path)
    try:
        session = backend.start()
        result = scenario_func(session)
        return result
    except Exception as e:
        return {
            "name": name,
            "error": str(e),
            "operations": []
        }
    finally:
        backend.stop()


def main():
    parser = argparse.ArgumentParser(description="Generate golden test cases")
    parser.add_argument("--backend", default="../backend/build/backend",
                        help="Path to backend executable")
    parser.add_argument("--output", default="../golden",
                        help="Output directory for test cases")
    parser.add_argument("--scenario", help="Run only this scenario")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--include-failing", action="store_true",
                        help="Also run scenarios known to fail (for debugging)")
    args = parser.parse_args()

    scenarios = ALL_SCENARIOS
    if args.include_failing:
        scenarios = WORKING_SCENARIOS + FAILING_SCENARIOS

    if args.list:
        print("Working scenarios:")
        for category, name, _ in WORKING_SCENARIOS:
            print(f"  {category}/{name}")
        print("\nFailing scenarios (need backend fixes):")
        for category, name, _ in FAILING_SCENARIOS:
            print(f"  {category}/{name}")
        return

    # Resolve paths
    script_dir = Path(__file__).parent
    backend_path = (script_dir / args.backend).resolve()
    output_dir = (script_dir / args.output).resolve()

    if not backend_path.exists():
        print(f"Error: Backend not found at {backend_path}")
        print("Run 'make' in the backend directory first.")
        sys.exit(1)

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run scenarios
    for category, name, scenario_func in scenarios:
        if args.scenario and args.scenario != name:
            continue

        print(f"Running {category}/{name}...", end=" ", flush=True)

        result = run_scenario(str(backend_path), category, name, scenario_func)

        if "error" in result:
            print(f"ERROR: {result['error']}")
        else:
            print("ok")

            # Write output
            category_dir = output_dir / category
            category_dir.mkdir(exist_ok=True)

            output_file = category_dir / f"{name}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

    print(f"\nTests written to {output_dir}")


if __name__ == "__main__":
    main()
