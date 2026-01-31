"""Document discovery scenarios using find_documents.

Tests for find_documents (FEBE opcode 22) which finds all documents
containing content matching a given specset. This enables content-based
document discovery through content identity.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_find_documents_basic(session):
    """Basic find_documents - find a document by its own content."""
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Hello World"])

    # Search for this document using its own content
    search_spec = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 11))]))
    found_docs = session.find_documents(search_spec)

    session.close_document(opened)

    return {
        "name": "find_documents_basic",
        "description": "Find a document by searching its own content",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "Hello World"},
            {"op": "find_documents",
             "search": specset_to_list(search_spec),
             "result": [str(d) for d in found_docs],
             "comment": "Should find the document itself"}
        ]
    }


def scenario_find_documents_transcluded(session):
    """Find documents by transcluded content identity.

    When content is transcluded (vcopy), both the source and destination
    share content identity. find_documents should find both.
    """
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared content here"])
    session.close_document(source_opened)

    # Create destination and transclude from source
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)
    session.insert(dest_opened, Address(1, 1), ["Prefix: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_span = Span(Address(1, 1), Offset(0, 14))  # "Shared content"
    copy_specs = SpecSet(VSpec(source_read, [copy_span]))
    dest_vs = session.retrieve_vspanset(dest_opened)
    session.vcopy(dest_opened, dest_vs.spans[0].end(), copy_specs)

    # Get dest contents
    dest_vs2 = session.retrieve_vspanset(dest_opened)
    dest_ss = SpecSet(VSpec(dest_opened, list(dest_vs2.spans)))
    dest_contents = session.retrieve_contents(dest_ss)

    # Search for documents containing the shared content
    # Use the source's content as the search key
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 6))]))  # "Shared"
    found_docs = session.find_documents(search_spec)

    session.close_document(source_read)
    session.close_document(dest_opened)

    return {
        "name": "find_documents_transcluded",
        "description": "Find documents by transcluded content identity",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Shared content here"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "text": "Shared content"},
            {"op": "contents", "doc": "dest", "result": dest_contents},
            {"op": "find_documents",
             "search_text": "Shared",
             "result": [str(d) for d in found_docs],
             "expected_count": 2,
             "comment": "Should find both source and dest (shared content identity)"}
        ]
    }


def scenario_find_documents_versions(session):
    """Find all versions of a document via shared content.

    Versions share content identity with their source. find_documents
    should discover all versions containing the shared content.
    """
    # Create original document
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original content"])
    session.close_document(orig_opened)

    # Create multiple versions
    version1 = session.create_version(original)
    version2 = session.create_version(original)
    version3 = session.create_version(original)

    # Modify version2 (but it still shares "Original" with others)
    v2_opened = session.open_document(version2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" plus v2 additions"])
    session.close_document(v2_opened)

    # Search for documents containing "Original"
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(orig_read, [Span(Address(1, 1), Offset(0, 8))]))  # "Original"
    found_docs = session.find_documents(search_spec)
    session.close_document(orig_read)

    return {
        "name": "find_documents_versions",
        "description": "Find all versions via shared content identity",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original content"},
            {"op": "create_version", "from": "original", "result": str(version1)},
            {"op": "create_version", "from": "original", "result": str(version2)},
            {"op": "create_version", "from": "original", "result": str(version3)},
            {"op": "insert", "doc": "version2", "text": " plus v2 additions"},
            {"op": "find_documents",
             "search_text": "Original",
             "result": [str(d) for d in found_docs],
             "expected_count": 4,
             "comment": "Should find original + all 3 versions"}
        ]
    }


def scenario_find_documents_no_match(session):
    """find_documents with content that exists nowhere else.

    When content is unique to one document and we search from another
    unrelated document, should find nothing.
    """
    # Create two unrelated documents
    doc1 = session.create_document()
    d1_opened = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
    session.insert(d1_opened, Address(1, 1), ["First document content"])
    session.close_document(d1_opened)

    doc2 = session.create_document()
    d2_opened = session.open_document(doc2, READ_WRITE, CONFLICT_FAIL)
    session.insert(d2_opened, Address(1, 1), ["Second document content"])
    session.close_document(d2_opened)

    # Search for doc1's content - should only find doc1
    d1_read = session.open_document(doc1, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(d1_read, [Span(Address(1, 1), Offset(0, 5))]))  # "First"
    found_docs = session.find_documents(search_spec)
    session.close_document(d1_read)

    return {
        "name": "find_documents_no_match",
        "description": "find_documents returns only documents with matching content",
        "operations": [
            {"op": "create_document", "doc": "doc1", "result": str(doc1)},
            {"op": "insert", "doc": "doc1", "text": "First document content"},
            {"op": "create_document", "doc": "doc2", "result": str(doc2)},
            {"op": "insert", "doc": "doc2", "text": "Second document content"},
            {"op": "find_documents",
             "search_from": "doc1",
             "search_text": "First",
             "result": [str(d) for d in found_docs],
             "expected_count": 1,
             "comment": "Should only find doc1, not doc2 (no shared content)"}
        ]
    }


def scenario_find_documents_empty_spec(session):
    """find_documents with empty specset.

    What happens when we search with NOSPECS?
    """
    # Create a document
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["Some content"])
    session.close_document(opened)

    # Search with empty specset
    try:
        found_docs = session.find_documents(NOSPECS)
        error = None
    except Exception as e:
        found_docs = []
        error = str(e)

    return {
        "name": "find_documents_empty_spec",
        "description": "find_documents behavior with empty specset",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "insert", "text": "Some content"},
            {"op": "find_documents",
             "search": "NOSPECS (empty)",
             "result": [str(d) for d in found_docs],
             "error": error,
             "comment": "Behavior with empty search spec"}
        ]
    }


def scenario_find_documents_version_chain(session):
    """Find documents across a version chain (v1 -> v2 -> v3).

    All versions in a chain should share content identity with v1.
    """
    # Create v1
    v1 = session.create_document()
    v1_opened = session.open_document(v1, READ_WRITE, CONFLICT_FAIL)
    session.insert(v1_opened, Address(1, 1), ["Base content"])
    session.close_document(v1_opened)

    # Create v2 from v1
    v2 = session.create_version(v1)
    v2_opened = session.open_document(v2, READ_WRITE, CONFLICT_FAIL)
    v2_vs = session.retrieve_vspanset(v2_opened)
    session.insert(v2_opened, v2_vs.spans[0].end(), [" plus v2"])
    session.close_document(v2_opened)

    # Create v3 from v2
    v3 = session.create_version(v2)
    v3_opened = session.open_document(v3, READ_WRITE, CONFLICT_FAIL)
    v3_vs = session.retrieve_vspanset(v3_opened)
    session.insert(v3_opened, v3_vs.spans[0].end(), [" plus v3"])
    session.close_document(v3_opened)

    # Search for "Base" - should find all three
    v1_read = session.open_document(v1, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(v1_read, [Span(Address(1, 1), Offset(0, 4))]))  # "Base"
    found_from_base = session.find_documents(search_spec)
    session.close_document(v1_read)

    # Search for "v2" - should only find v2 and v3 (v3 inherited from v2)
    v2_read = session.open_document(v2, READ_ONLY, CONFLICT_COPY)
    v2_vs2 = session.retrieve_vspanset(v2_read)
    # "plus v2" is at end of v2's content
    search_v2 = SpecSet(VSpec(v2_read, [Span(Address(1, 14), Offset(0, 7))]))  # "plus v2"
    found_from_v2 = session.find_documents(search_v2)
    session.close_document(v2_read)

    return {
        "name": "find_documents_version_chain",
        "description": "Find documents across version chain v1 -> v2 -> v3",
        "operations": [
            {"op": "create_document", "doc": "v1", "result": str(v1)},
            {"op": "insert", "doc": "v1", "text": "Base content"},
            {"op": "create_version", "from": "v1", "result": str(v2)},
            {"op": "insert", "doc": "v2", "text": " plus v2"},
            {"op": "create_version", "from": "v2", "result": str(v3)},
            {"op": "insert", "doc": "v3", "text": " plus v3"},
            {"op": "find_documents",
             "search_text": "Base",
             "result": [str(d) for d in found_from_base],
             "expected_count": 3,
             "comment": "All versions share 'Base' content"},
            {"op": "find_documents",
             "search_text": "plus v2",
             "result": [str(d) for d in found_from_v2],
             "expected_count": 2,
             "comment": "Only v2 and v3 have 'plus v2' content"}
        ]
    }


def scenario_find_documents_transitive_transclusion(session):
    """Find documents through transitive transclusion.

    A -> B -> C chain where A transcludes from B and B transcludes from C.
    Searching C's content should find all three.
    """
    # Create C (the source)
    doc_c = session.create_document()
    c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(c_opened, Address(1, 1), ["Original from C"])
    session.close_document(c_opened)

    # Create B and transclude from C
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["B prefix: "])

    c_read = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_copy = SpecSet(VSpec(c_read, [Span(Address(1, 1), Offset(0, 8))]))  # "Original"
    b_vs = session.retrieve_vspanset(b_opened)
    session.vcopy(b_opened, b_vs.spans[0].end(), c_copy)
    session.close_document(c_read)
    session.close_document(b_opened)

    # Create A and transclude from B
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["A prefix: "])

    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs2 = session.retrieve_vspanset(b_read)
    # B contains "B prefix: Original" - transclude "Original" portion
    b_copy = SpecSet(VSpec(b_read, [Span(Address(1, 11), Offset(0, 8))]))  # "Original" in B
    a_vs = session.retrieve_vspanset(a_opened)
    session.vcopy(a_opened, a_vs.spans[0].end(), b_copy)
    session.close_document(b_read)
    session.close_document(a_opened)

    # Search for "Original" from C's perspective
    c_read2 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(c_read2, [Span(Address(1, 1), Offset(0, 8))]))  # "Original"
    found_docs = session.find_documents(search_spec)
    session.close_document(c_read2)

    # Get all contents for verification
    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    a_vs2 = session.retrieve_vspanset(a_read)
    a_contents = session.retrieve_contents(SpecSet(VSpec(a_read, list(a_vs2.spans))))
    session.close_document(a_read)

    b_read2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    b_vs3 = session.retrieve_vspanset(b_read2)
    b_contents = session.retrieve_contents(SpecSet(VSpec(b_read2, list(b_vs3.spans))))
    session.close_document(b_read2)

    c_read3 = session.open_document(doc_c, READ_ONLY, CONFLICT_COPY)
    c_vs = session.retrieve_vspanset(c_read3)
    c_contents = session.retrieve_contents(SpecSet(VSpec(c_read3, list(c_vs.spans))))
    session.close_document(c_read3)

    return {
        "name": "find_documents_transitive_transclusion",
        "description": "Find documents through A -> B -> C transclusion chain",
        "operations": [
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Original from C"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "vcopy", "from": "C", "to": "B", "text": "Original"},
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "vcopy", "from": "B", "to": "A", "text": "Original"},
            {"op": "contents", "doc": "A", "result": a_contents},
            {"op": "contents", "doc": "B", "result": b_contents},
            {"op": "contents", "doc": "C", "result": c_contents},
            {"op": "find_documents",
             "search_from": "C",
             "search_text": "Original",
             "result": [str(d) for d in found_docs],
             "expected_count": 3,
             "comment": "A, B, and C all share 'Original' content identity"}
        ]
    }


def scenario_find_documents_after_delete(session):
    """Find documents after content is deleted.

    If content is deleted from a document, it should no longer appear
    in find_documents results (unless other documents still have it).
    """
    # Create source with content
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Findable content"])
    session.close_document(source_opened)

    # Create dest and transclude
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)
    session.insert(dest_opened, Address(1, 1), ["Prefix: "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 8))]))  # "Findable"
    dest_vs = session.retrieve_vspanset(dest_opened)
    session.vcopy(dest_opened, dest_vs.spans[0].end(), copy_spec)
    session.close_document(dest_opened)

    # Find documents before delete - should find both
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 8))]))
    found_before = session.find_documents(search_spec)
    session.close_document(source_read)

    # Delete "Findable" from dest
    dest_opened2 = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)
    session.remove(dest_opened2, Span(Address(1, 9), Offset(0, 8)))  # Remove "Findable"
    dest_vs2 = session.retrieve_vspanset(dest_opened2)
    dest_contents = session.retrieve_contents(SpecSet(VSpec(dest_opened2, list(dest_vs2.spans))))
    session.close_document(dest_opened2)

    # Find documents after delete
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    search_spec2 = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 8))]))
    found_after = session.find_documents(search_spec2)
    session.close_document(source_read2)

    return {
        "name": "find_documents_after_delete",
        "description": "find_documents behavior after content deletion",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Findable content"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "text": "Findable"},
            {"op": "find_documents",
             "label": "before_delete",
             "result": [str(d) for d in found_before],
             "expected_count": 2,
             "comment": "Both source and dest have 'Findable'"},
            {"op": "delete", "doc": "dest", "text": "Findable"},
            {"op": "contents", "doc": "dest", "result": dest_contents},
            {"op": "find_documents",
             "label": "after_delete",
             "result": [str(d) for d in found_after],
             "expected_count": 1,
             "comment": "Only source has 'Findable' now (if delete removes content identity)"}
        ]
    }


def scenario_find_documents_partial_content(session):
    """Find documents searching for partial content.

    If we search for a substring of transcluded content,
    does it still find all documents?
    """
    # Create source
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["ABCDEFGHIJ"])
    session.close_document(source_opened)

    # Create dest and transclude the whole thing
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 10))]))
    session.vcopy(dest_opened, Address(1, 1), copy_spec)
    session.close_document(dest_opened)

    # Search for just "DEF" (middle portion)
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 4), Offset(0, 3))]))  # "DEF"
    found_partial = session.find_documents(search_spec)

    # Search for "ABC" (beginning)
    search_start = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 3))]))  # "ABC"
    found_start = session.find_documents(search_start)

    # Search for "HIJ" (end)
    search_end = SpecSet(VSpec(source_read, [Span(Address(1, 8), Offset(0, 3))]))  # "HIJ"
    found_end = session.find_documents(search_end)

    session.close_document(source_read)

    return {
        "name": "find_documents_partial_content",
        "description": "Find documents by searching partial content",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "ABCDEFGHIJ"},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "text": "ABCDEFGHIJ"},
            {"op": "find_documents",
             "search_text": "DEF (middle)",
             "result": [str(d) for d in found_partial],
             "expected_count": 2},
            {"op": "find_documents",
             "search_text": "ABC (start)",
             "result": [str(d) for d in found_start],
             "expected_count": 2},
            {"op": "find_documents",
             "search_text": "HIJ (end)",
             "result": [str(d) for d in found_end],
             "expected_count": 2,
             "comment": "All partial searches should find both documents"}
        ]
    }


def scenario_find_documents_multiple_transclusions(session):
    """Find documents when content is transcluded to multiple destinations.

    One source, many destinations - all should be discoverable.
    """
    # Create source
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Shared across many"])
    session.close_document(source_opened)

    # Create 5 destination documents, each transcluding from source
    destinations = []
    for i in range(5):
        dest = session.create_document()
        dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)
        session.insert(dest_opened, Address(1, 1), [f"Doc {i}: "])

        source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
        copy_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 6))]))  # "Shared"
        dest_vs = session.retrieve_vspanset(dest_opened)
        session.vcopy(dest_opened, dest_vs.spans[0].end(), copy_spec)
        session.close_document(source_read)
        session.close_document(dest_opened)

        destinations.append(dest)

    # Find all documents with "Shared"
    source_read2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(source_read2, [Span(Address(1, 1), Offset(0, 6))]))
    found_docs = session.find_documents(search_spec)
    session.close_document(source_read2)

    return {
        "name": "find_documents_multiple_transclusions",
        "description": "Find documents when content is transcluded to many destinations",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Shared across many"},
            {"op": "create_documents",
             "count": 5,
             "results": [str(d) for d in destinations]},
            {"op": "vcopy_all", "from": "source", "to": "all destinations", "text": "Shared"},
            {"op": "find_documents",
             "search_text": "Shared",
             "result": [str(d) for d in found_docs],
             "expected_count": 6,
             "comment": "Source + 5 destinations = 6 documents"}
        ]
    }


def scenario_find_documents_with_link_content(session):
    """Find documents that contain linked content.

    When content has a link attached, does find_documents still work?
    """
    # Create source with link
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Click here for info"])

    # Create target
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Information"])

    # Create link on "here"
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 11))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)

    # Transclude "Click here" (including linked content) to another doc
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)

    copy_spec = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 10))]))  # "Click here"
    session.vcopy(dest_opened, Address(1, 1), copy_spec)
    session.close_document(dest_opened)
    session.close_document(source_opened)

    # Find documents with "Click here"
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 10))]))
    found_docs = session.find_documents(search_spec)
    session.close_document(source_read)

    return {
        "name": "find_documents_with_link_content",
        "description": "Find documents containing linked content",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "Click here for info"},
            {"op": "create_link", "source_text": "here", "result": str(link_id)},
            {"op": "create_document", "doc": "dest", "result": str(dest)},
            {"op": "vcopy", "from": "source", "to": "dest", "text": "Click here"},
            {"op": "find_documents",
             "search_text": "Click here",
             "result": [str(d) for d in found_docs],
             "expected_count": 2,
             "comment": "Should find source and dest even with link attached"}
        ]
    }


def scenario_find_documents_empty_document(session):
    """find_documents behavior with empty documents.

    What happens when searching in or for empty documents?
    """
    # Create empty document
    empty = session.create_document()

    # Create document with content
    full = session.create_document()
    full_opened = session.open_document(full, READ_WRITE, CONFLICT_FAIL)
    session.insert(full_opened, Address(1, 1), ["Has content"])

    # Try to search from empty document's perspective
    empty_opened = session.open_document(empty, READ_ONLY, CONFLICT_COPY)
    empty_vs = session.retrieve_vspanset(empty_opened)

    if empty_vs.spans:
        search_spec = SpecSet(VSpec(empty_opened, list(empty_vs.spans)))
        try:
            found_from_empty = session.find_documents(search_spec)
            error = None
        except Exception as e:
            found_from_empty = []
            error = str(e)
    else:
        found_from_empty = []
        error = "Empty document has no spans to search"

    session.close_document(empty_opened)
    session.close_document(full_opened)

    return {
        "name": "find_documents_empty_document",
        "description": "find_documents behavior with empty documents",
        "operations": [
            {"op": "create_document", "doc": "empty", "result": str(empty)},
            {"op": "create_document", "doc": "full", "result": str(full)},
            {"op": "insert", "doc": "full", "text": "Has content"},
            {"op": "find_documents",
             "search_from": "empty",
             "result": [str(d) for d in found_from_empty],
             "error": error,
             "comment": "Searching from empty document's content"}
        ]
    }


SCENARIOS = [
    ("discovery", "find_documents_basic", scenario_find_documents_basic),
    ("discovery", "find_documents_transcluded", scenario_find_documents_transcluded),
    ("discovery", "find_documents_versions", scenario_find_documents_versions),
    ("discovery", "find_documents_no_match", scenario_find_documents_no_match),
    ("discovery", "find_documents_empty_spec", scenario_find_documents_empty_spec),
    ("discovery", "find_documents_version_chain", scenario_find_documents_version_chain),
    ("discovery", "find_documents_transitive_transclusion", scenario_find_documents_transitive_transclusion),
    ("discovery", "find_documents_after_delete", scenario_find_documents_after_delete),
    ("discovery", "find_documents_partial_content", scenario_find_documents_partial_content),
    ("discovery", "find_documents_multiple_transclusions", scenario_find_documents_multiple_transclusions),
    ("discovery", "find_documents_with_link_content", scenario_find_documents_with_link_content),
    ("discovery", "find_documents_empty_document", scenario_find_documents_empty_document),
]
