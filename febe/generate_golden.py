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
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
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


def scenario_link_types(session):
    """Create links with different types (quote, footnote, margin)."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Document with multiple link types"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content for all links"])

    # Create different link types
    # Quote link on "Document" (1-8)
    quote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 8))]))
    quote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    quote_link = session.create_link(source_opened, quote_source, quote_target, SpecSet([QUOTE_TYPE]))

    # Footnote link on "multiple" (15-23)
    footnote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 15), Offset(0, 8))]))
    footnote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 8), Offset(0, 7))]))
    footnote_link = session.create_link(source_opened, footnote_source, footnote_target, SpecSet([FOOTNOTE_TYPE]))

    # Margin link on "types" (29-34)
    margin_source = SpecSet(VSpec(source_opened, [Span(Address(1, 29), Offset(0, 5))]))
    margin_target = SpecSet(VSpec(target_opened, [Span(Address(1, 16), Offset(0, 3))]))
    margin_link = session.create_link(source_opened, margin_source, margin_target, SpecSet([MARGIN_TYPE]))

    # Find all links from source
    search_span = Span(Address(1, 1), Offset(0, 40))
    search_specs = SpecSet(VSpec(source_opened, [search_span]))
    found_links = session.find_links(search_specs)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_types",
        "description": "Create links with different types (quote, footnote, margin)",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Document with multiple link types"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target content for all links"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(quote_source),
             "target": specset_to_list(quote_target),
             "type": "quote",
             "result": str(quote_link)},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(footnote_source),
             "target": specset_to_list(footnote_target),
             "type": "footnote",
             "result": str(footnote_link)},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(margin_source),
             "target": specset_to_list(margin_target),
             "type": "margin",
             "result": str(margin_link)},
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]}
        ]
    }


def scenario_multiple_links_same_doc(session):
    """Create multiple links from the same source document."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with links to multiple targets"])

    # Create three target documents
    targets = []
    for i in range(3):
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [f"Target document {i+1}"])
        targets.append((doc, opened))

    # Create links to each target
    links = []
    link_ops = []

    # Link "Source" to target 1
    s1 = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 6))]))
    t1 = SpecSet(VSpec(targets[0][1], [Span(Address(1, 1), Offset(0, 6))]))
    link1 = session.create_link(source_opened, s1, t1, SpecSet([JUMP_TYPE]))
    links.append(link1)
    link_ops.append({"op": "create_link", "source_text": "Source", "target_doc": 1, "result": str(link1)})

    # Link "links" to target 2
    s2 = SpecSet(VSpec(source_opened, [Span(Address(1, 13), Offset(0, 5))]))
    t2 = SpecSet(VSpec(targets[1][1], [Span(Address(1, 1), Offset(0, 6))]))
    link2 = session.create_link(source_opened, s2, t2, SpecSet([JUMP_TYPE]))
    links.append(link2)
    link_ops.append({"op": "create_link", "source_text": "links", "target_doc": 2, "result": str(link2)})

    # Link "targets" to target 3
    s3 = SpecSet(VSpec(source_opened, [Span(Address(1, 31), Offset(0, 7))]))
    t3 = SpecSet(VSpec(targets[2][1], [Span(Address(1, 1), Offset(0, 6))]))
    link3 = session.create_link(source_opened, s3, t3, SpecSet([JUMP_TYPE]))
    links.append(link3)
    link_ops.append({"op": "create_link", "source_text": "targets", "target_doc": 3, "result": str(link3)})

    # Find all links from source
    search_span = Span(Address(1, 1), Offset(0, 40))
    search_specs = SpecSet(VSpec(source_opened, [search_span]))
    found_links = session.find_links(search_specs)

    # Close all documents
    session.close_document(source_opened)
    for _, opened in targets:
        session.close_document(opened)

    return {
        "name": "multiple_links_same_doc",
        "description": "Create multiple links from the same source document to different targets",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Source with links to multiple targets"},
            {"op": "create_documents", "count": 3, "results": [str(t[0]) for t in targets]},
        ] + link_ops + [
            {"op": "find_links",
             "search": specset_to_list(search_specs),
             "result": [str(l) for l in found_links]}
        ]
    }


def scenario_bidirectional_links(session):
    """Create bidirectional links between two documents.

    Note: Internal links (source and target in same document) are NOT supported
    by the backend - it returns an error. Links must span different documents.
    This test verifies that links can go both directions between documents.
    """
    # Create two documents
    doc1 = session.create_document()
    opened1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened1, Address(1, 1), ["Document one with source text"])

    doc2 = session.create_document()
    opened2 = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened2, Address(1, 1), ["Document two with target text"])

    # Link from doc1 to doc2: "Document" -> "Document"
    s1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 8))]))
    t1 = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 8))]))
    link1 = session.create_link(opened1, s1, t1, SpecSet([JUMP_TYPE]))

    # Link from doc2 back to doc1: "target" -> "source"
    s2 = SpecSet(VSpec(opened2, [Span(Address(1, 14), Offset(0, 6))]))
    t2 = SpecSet(VSpec(opened1, [Span(Address(1, 14), Offset(0, 6))]))
    link2 = session.create_link(opened2, s2, t2, SpecSet([JUMP_TYPE]))

    # Find links from doc1
    search1 = SpecSet(VSpec(opened1, [Span(Address(1, 1), Offset(0, 30))]))
    found_from_doc1 = session.find_links(search1)

    # Find links from doc2
    search2 = SpecSet(VSpec(opened2, [Span(Address(1, 1), Offset(0, 30))]))
    found_from_doc2 = session.find_links(search2)

    # Follow link1 to target
    link1_target = session.follow_link(link1, LINK_TARGET)

    # Follow link2 to target (back to doc1)
    link2_target = session.follow_link(link2, LINK_TARGET)

    session.close_document(opened1)
    session.close_document(opened2)

    return {
        "name": "bidirectional_links",
        "description": "Create bidirectional links between two documents (doc1->doc2 and doc2->doc1)",
        "operations": [
            {"op": "create_document", "result": str(doc1)},
            {"op": "open_document", "doc": str(doc1), "mode": "read_write", "result": str(opened1)},
            {"op": "insert", "doc": str(opened1), "address": "1.1", "text": "Document one with source text"},
            {"op": "create_document", "result": str(doc2)},
            {"op": "open_document", "doc": str(doc2), "mode": "read_write", "result": str(opened2)},
            {"op": "insert", "doc": str(opened2), "address": "1.1", "text": "Document two with target text"},
            {"op": "create_link",
             "home_doc": str(opened1),
             "source": specset_to_list(s1),
             "target": specset_to_list(t1),
             "type": "jump",
             "result": str(link1),
             "comment": "Link from doc1 to doc2"},
            {"op": "create_link",
             "home_doc": str(opened2),
             "source": specset_to_list(s2),
             "target": specset_to_list(t2),
             "type": "jump",
             "result": str(link2),
             "comment": "Link from doc2 back to doc1"},
            {"op": "find_links",
             "search": specset_to_list(search1),
             "result": [str(l) for l in found_from_doc1],
             "comment": "Links originating from doc1"},
            {"op": "find_links",
             "search": specset_to_list(search2),
             "result": [str(l) for l in found_from_doc2],
             "comment": "Links originating from doc2"},
            {"op": "follow_link",
             "link": str(link1),
             "end": "target",
             "result": specset_to_list(link1_target)},
            {"op": "follow_link",
             "link": str(link2),
             "end": "target",
             "result": specset_to_list(link2_target)}
        ]
    }


def scenario_find_links_by_target(session):
    """Find links by searching target spans instead of source."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Document referencing the glossary"])

    # Create target (glossary) document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Glossary: terms and definitions here"])

    # Create link from source to target
    source_span = Span(Address(1, 21), Offset(0, 8))  # "glossary"
    target_span = Span(Address(1, 1), Offset(0, 8))  # "Glossary"

    source_specs = SpecSet(VSpec(source_opened, [source_span]))
    target_specs = SpecSet(VSpec(target_opened, [target_span]))

    link_id = session.create_link(source_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Find links by searching the TARGET document (reverse lookup)
    target_search = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 36))]))
    # Use empty source specs, search by target
    from client import NOSPECS
    found_by_target = session.find_links(NOSPECS, target_search)

    # Follow found link to get source
    if found_by_target:
        source_result = session.follow_link(found_by_target[0], LINK_SOURCE)
        source_contents = session.retrieve_contents(source_result)
    else:
        source_result = NOSPECS
        source_contents = []

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "find_links_by_target",
        "description": "Find links by searching target spans (reverse lookup)",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Document referencing the glossary"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Glossary: terms and definitions here"},
            {"op": "create_link",
             "home_doc": str(source_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "find_links",
             "by": "target",
             "search": specset_to_list(target_search),
             "result": [str(l) for l in found_by_target]},
            {"op": "follow_link",
             "link": str(found_by_target[0]) if found_by_target else "none",
             "end": "source",
             "result": specset_to_list(source_result)},
            {"op": "retrieve_contents",
             "specs": specset_to_list(source_result),
             "result": source_contents}
        ]
    }


def scenario_overlapping_links(session):
    """Create multiple links with overlapping source spans."""
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["The hypertext pioneer Vannevar Bush described the memex."])

    # Create target document for definitions
    def_doc = session.create_document()
    def_opened = session.open_document(def_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(def_opened, Address(1, 1), ["hypertext: non-linear text. Bush: American engineer. memex: memory extender."])

    # Link "hypertext" to its definition
    link1_source = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 9))]))
    link1_target = SpecSet(VSpec(def_opened, [Span(Address(1, 1), Offset(0, 10))]))
    link1 = session.create_link(opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Link "hypertext pioneer" (overlapping with previous)
    link2_source = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 17))]))
    link2_target = SpecSet(VSpec(def_opened, [Span(Address(1, 1), Offset(0, 30))]))
    link2 = session.create_link(opened, link2_source, link2_target, SpecSet([QUOTE_TYPE]))

    # Link "Vannevar Bush"
    link3_source = SpecSet(VSpec(opened, [Span(Address(1, 23), Offset(0, 13))]))
    link3_target = SpecSet(VSpec(def_opened, [Span(Address(1, 23), Offset(0, 22))]))
    link3 = session.create_link(opened, link3_source, link3_target, SpecSet([JUMP_TYPE]))

    # Link "memex"
    link4_source = SpecSet(VSpec(opened, [Span(Address(1, 51), Offset(0, 5))]))
    link4_target = SpecSet(VSpec(def_opened, [Span(Address(1, 47), Offset(0, 22))]))
    link4 = session.create_link(opened, link4_source, link4_target, SpecSet([JUMP_TYPE]))

    # Find links from "hypertext" region - should get both overlapping links
    hypertext_search = SpecSet(VSpec(opened, [Span(Address(1, 5), Offset(0, 9))]))
    found_hypertext = session.find_links(hypertext_search)

    # Find all links from full document
    full_search = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 60))]))
    found_all = session.find_links(full_search)

    session.close_document(opened)
    session.close_document(def_opened)

    return {
        "name": "overlapping_links",
        "description": "Create multiple links with overlapping source spans",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "open_document", "doc": str(docid), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1",
             "text": "The hypertext pioneer Vannevar Bush described the memex."},
            {"op": "create_document", "result": str(def_doc)},
            {"op": "open_document", "doc": str(def_doc), "mode": "read_write", "result": str(def_opened)},
            {"op": "insert", "doc": str(def_opened), "address": "1.1",
             "text": "hypertext: non-linear text. Bush: American engineer. memex: memory extender."},
            {"op": "create_link", "source_text": "hypertext", "type": "jump", "result": str(link1)},
            {"op": "create_link", "source_text": "hypertext pioneer", "type": "quote", "result": str(link2)},
            {"op": "create_link", "source_text": "Vannevar Bush", "type": "jump", "result": str(link3)},
            {"op": "create_link", "source_text": "memex", "type": "jump", "result": str(link4)},
            {"op": "find_links",
             "search_text": "hypertext",
             "result": [str(l) for l in found_hypertext],
             "comment": "Should find both overlapping links"},
            {"op": "find_links",
             "search_text": "full document",
             "result": [str(l) for l in found_all],
             "comment": "Should find all 4 links"}
        ]
    }


def scenario_find_links_by_type(session):
    """Find links filtered by their type."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Source with jump quote and footnote links"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target document for links"])

    # Create links of different types
    # "jump" at position 13-16
    jump_source = SpecSet(VSpec(source_opened, [Span(Address(1, 13), Offset(0, 4))]))
    jump_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    jump_link = session.create_link(source_opened, jump_source, jump_target, SpecSet([JUMP_TYPE]))

    # "quote" at position 18-22
    quote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 18), Offset(0, 5))]))
    quote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 8), Offset(0, 8))]))
    quote_link = session.create_link(source_opened, quote_source, quote_target, SpecSet([QUOTE_TYPE]))

    # "footnote" at position 28-35
    footnote_source = SpecSet(VSpec(source_opened, [Span(Address(1, 28), Offset(0, 8))]))
    footnote_target = SpecSet(VSpec(target_opened, [Span(Address(1, 17), Offset(0, 8))]))
    footnote_link = session.create_link(source_opened, footnote_source, footnote_target, SpecSet([FOOTNOTE_TYPE]))

    # Search the whole document
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 50))]))

    # Find all links (no type filter)
    all_links = session.find_links(full_search)

    # Find only JUMP links
    jump_links = session.find_links(full_search, NOSPECS, SpecSet([JUMP_TYPE]))

    # Find only QUOTE links
    quote_links = session.find_links(full_search, NOSPECS, SpecSet([QUOTE_TYPE]))

    # Find only FOOTNOTE links
    footnote_links = session.find_links(full_search, NOSPECS, SpecSet([FOOTNOTE_TYPE]))

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "find_links_by_type",
        "description": "Find links filtered by their type",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1",
             "text": "Source with jump quote and footnote links"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1",
             "text": "Target document for links"},
            {"op": "create_link", "source_text": "jump", "type": "jump", "result": str(jump_link)},
            {"op": "create_link", "source_text": "quote", "type": "quote", "result": str(quote_link)},
            {"op": "create_link", "source_text": "footnote", "type": "footnote", "result": str(footnote_link)},
            {"op": "find_links", "filter": "none",
             "result": [str(l) for l in all_links],
             "comment": "All 3 links"},
            {"op": "find_links", "filter": "jump",
             "result": [str(l) for l in jump_links],
             "comment": "Only jump links"},
            {"op": "find_links", "filter": "quote",
             "result": [str(l) for l in quote_links],
             "comment": "Only quote links"},
            {"op": "find_links", "filter": "footnote",
             "result": [str(l) for l in footnote_links],
             "comment": "Only footnote links"}
        ]
    }


def scenario_retrieve_endsets(session):
    """Retrieve the endpoint specsets of a link."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here to navigate"])

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Destination content"])

    # Create a link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))  # "here"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 11))]))  # "Destination"
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Retrieve the endsets of the link
    link_specset = SpecSet(VSpec(source_opened, [Span(Address(1, 0, 2, 1), Offset(0, 1))]))
    source_specs, target_specs, type_specs = session.retrieve_endsets(link_specset)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "retrieve_endsets",
        "description": "Retrieve the endpoint specsets of a link",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "Click here to navigate"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Destination content"},
            {"op": "create_link", "source_text": "here", "type": "jump", "result": str(link_id)},
            {"op": "retrieve_endsets", "link": str(link_id),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": specset_to_list(type_specs)}
        ]
    }


def scenario_follow_link(session):
    """Follow a link to retrieve its destination content."""
    # Create source document
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["See the reference for more info"])

    # Create target document with detailed content
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Reference: This is the detailed explanation."])

    # Create a link from "reference" to the explanation
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 9), Offset(0, 9))]))  # "reference"
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 12), Offset(0, 32))]))  # explanation
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Follow the link to get the target
    target_content = session.follow_link(link_id, LINK_TARGET)

    # Retrieve the actual text at the target
    target_text = session.retrieve_contents(target_content)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "follow_link",
        "description": "Follow a link to retrieve its destination content",
        "operations": [
            {"op": "create_document", "result": str(source_doc)},
            {"op": "open_document", "doc": str(source_doc), "mode": "read_write", "result": str(source_opened)},
            {"op": "insert", "doc": str(source_opened), "address": "1.1", "text": "See the reference for more info"},
            {"op": "create_document", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1",
             "text": "Reference: This is the detailed explanation."},
            {"op": "create_link", "source_text": "reference", "type": "jump", "result": str(link_id)},
            {"op": "follow_link", "link": str(link_id), "end": "target",
             "result": specset_to_list(target_content)},
            {"op": "retrieve_contents", "result": target_text,
             "comment": "The actual text at the link destination"}
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

# All working scenarios
ALL_SCENARIOS = [
    # Documents
    ("documents", "create_document", scenario_create_document),
    ("documents", "multiple_documents", scenario_multiple_documents),
    # Content
    ("content", "insert_text", scenario_insert_text),
    ("content", "multiple_inserts", scenario_multiple_inserts),
    ("content", "insert_middle", scenario_insert_middle),
    ("content", "delete_text", scenario_delete_text),
    ("content", "partial_retrieve", scenario_partial_retrieve),
    ("content", "vcopy_transclusion", scenario_vcopy),
    # Versions
    ("versions", "create_version", scenario_create_version),
    ("versions", "compare_versions", scenario_compare_versions),
    # Links
    ("links", "create_link", scenario_create_link),
    ("links", "find_links", scenario_find_links),
    ("links", "link_types", scenario_link_types),
    ("links", "multiple_links_same_doc", scenario_multiple_links_same_doc),
    ("links", "bidirectional_links", scenario_bidirectional_links),
    ("links", "find_links_by_target", scenario_find_links_by_target),
    ("links", "overlapping_links", scenario_overlapping_links),
    ("links", "find_links_by_type", scenario_find_links_by_type),
    ("links", "retrieve_endsets", scenario_retrieve_endsets),
    ("links", "follow_link", scenario_follow_link),
    # Internal
    ("internal", "internal_state", scenario_internal_state),
]

# Legacy alias for backward compatibility
WORKING_SCENARIOS = ALL_SCENARIOS
FAILING_SCENARIOS = []


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
