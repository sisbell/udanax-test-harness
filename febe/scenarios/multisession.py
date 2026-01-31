"""Multi-session behavior scenarios.

Tests what happens when multiple FEBE sessions interact with shared state.
These scenarios require the backenddaemon (TCP mode) rather than backend (pipe mode).

Key questions:
- Can session B see documents created by session A?
- What happens when both sessions modify the same document?
- Does account switching in one session affect others?
- Can session B find links created by session A?
- How do concurrent versioning operations work?
"""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_cross_session_doc_visibility(sessions):
    """Session A creates a document, session B reads it.

    Tests basic cross-session document visibility.
    Session A creates and populates a document.
    Session B should be able to open and read it.
    """
    session_a, session_b = sessions

    # Session A: Create and populate a document
    session_a.account(Address(1, 1, 0, 1))
    doc = session_a.create_document()

    opened_a = session_a.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(opened_a, Address(1, 1), ["Hello from session A"])
    session_a.close_document(opened_a)

    # Session B: Try to read the document created by A
    session_b.account(Address(1, 1, 0, 2))  # Different account

    opened_b = session_b.open_document(doc, READ_ONLY, CONFLICT_COPY)
    vspanset = session_b.retrieve_vspanset(opened_b)
    specset = SpecSet(VSpec(opened_b, list(vspanset.spans)))
    contents = session_b.retrieve_contents(specset)
    contents = [str(c) if hasattr(c, 'digits') else c for c in contents]
    session_b.close_document(opened_b)

    return {
        "name": "cross_session_doc_visibility",
        "description": "Session A creates document, session B reads it",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "account", "account": "1.1.0.1"},
            {"session": "A", "op": "create_document", "result": str(doc)},
            {"session": "A", "op": "insert", "text": "Hello from session A"},
            {"session": "A", "op": "close_document"},
            {"session": "B", "op": "account", "account": "1.1.0.2"},
            {"session": "B", "op": "open_document", "doc": str(doc)},
            {"session": "B", "op": "retrieve_contents", "result": contents,
             "comment": "B should see A's content"}
        ]
    }


def scenario_concurrent_document_creation(sessions):
    """Both sessions create documents under different accounts.

    Tests that document creation from different sessions
    doesn't interfere with each other.
    """
    session_a, session_b = sessions

    # Both sessions set their accounts
    session_a.account(Address(1, 1, 0, 1))
    session_b.account(Address(1, 1, 0, 2))

    # Interleaved document creation
    doc_a1 = session_a.create_document()
    doc_b1 = session_b.create_document()
    doc_a2 = session_a.create_document()
    doc_b2 = session_b.create_document()

    # Populate all documents
    opened_a1 = session_a.open_document(doc_a1, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(opened_a1, Address(1, 1), ["A doc 1"])
    session_a.close_document(opened_a1)

    opened_b1 = session_b.open_document(doc_b1, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(opened_b1, Address(1, 1), ["B doc 1"])
    session_b.close_document(opened_b1)

    opened_a2 = session_a.open_document(doc_a2, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(opened_a2, Address(1, 1), ["A doc 2"])
    session_a.close_document(opened_a2)

    opened_b2 = session_b.open_document(doc_b2, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(opened_b2, Address(1, 1), ["B doc 2"])
    session_b.close_document(opened_b2)

    # Verify each can read the other's documents
    read_a1 = session_b.open_document(doc_a1, READ_ONLY, CONFLICT_COPY)
    vs_a1 = session_b.retrieve_vspanset(read_a1)
    ss_a1 = SpecSet(VSpec(read_a1, list(vs_a1.spans)))
    contents_a1 = session_b.retrieve_contents(ss_a1)
    contents_a1 = [str(c) if hasattr(c, 'digits') else c for c in contents_a1]
    session_b.close_document(read_a1)

    read_b1 = session_a.open_document(doc_b1, READ_ONLY, CONFLICT_COPY)
    vs_b1 = session_a.retrieve_vspanset(read_b1)
    ss_b1 = SpecSet(VSpec(read_b1, list(vs_b1.spans)))
    contents_b1 = session_a.retrieve_contents(ss_b1)
    contents_b1 = [str(c) if hasattr(c, 'digits') else c for c in contents_b1]
    session_a.close_document(read_b1)

    return {
        "name": "concurrent_document_creation",
        "description": "Both sessions create documents with interleaved operations",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "account", "account": "1.1.0.1"},
            {"session": "B", "op": "account", "account": "1.1.0.2"},
            {"session": "A", "op": "create_document", "doc": "a1", "result": str(doc_a1)},
            {"session": "B", "op": "create_document", "doc": "b1", "result": str(doc_b1)},
            {"session": "A", "op": "create_document", "doc": "a2", "result": str(doc_a2)},
            {"session": "B", "op": "create_document", "doc": "b2", "result": str(doc_b2)},
            {"session": "A", "op": "insert", "doc": "a1", "text": "A doc 1"},
            {"session": "B", "op": "insert", "doc": "b1", "text": "B doc 1"},
            {"session": "A", "op": "insert", "doc": "a2", "text": "A doc 2"},
            {"session": "B", "op": "insert", "doc": "b2", "text": "B doc 2"},
            {"session": "B", "op": "read", "doc": str(doc_a1), "result": contents_a1,
             "comment": "B reads A's first doc"},
            {"session": "A", "op": "read", "doc": str(doc_b1), "result": contents_b1,
             "comment": "A reads B's first doc"}
        ]
    }


def scenario_concurrent_write_same_account(sessions):
    """Both sessions write using the same account.

    What happens when both sessions claim to be the same account
    and create documents? Are document addresses unique?
    """
    session_a, session_b = sessions

    same_account = Address(1, 1, 0, 1)
    session_a.account(same_account)
    session_b.account(same_account)

    # Both create documents under the same account
    doc_a = session_a.create_document()
    doc_b = session_b.create_document()

    # Populate them
    opened_a = session_a.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(opened_a, Address(1, 1), ["From A"])
    session_a.close_document(opened_a)

    opened_b = session_b.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(opened_b, Address(1, 1), ["From B"])
    session_b.close_document(opened_b)

    # Both read both documents
    read_a = session_a.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    vs_a = session_a.retrieve_vspanset(read_a)
    ss_a = SpecSet(VSpec(read_a, list(vs_a.spans)))
    contents_a = session_a.retrieve_contents(ss_a)
    contents_a = [str(c) if hasattr(c, 'digits') else c for c in contents_a]
    session_a.close_document(read_a)

    read_b = session_b.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    vs_b = session_b.retrieve_vspanset(read_b)
    ss_b = SpecSet(VSpec(read_b, list(vs_b.spans)))
    contents_b = session_b.retrieve_contents(ss_b)
    contents_b = [str(c) if hasattr(c, 'digits') else c for c in contents_b]
    session_b.close_document(read_b)

    docs_same = (doc_a == doc_b)

    return {
        "name": "concurrent_write_same_account",
        "description": "Both sessions use same account - are doc addresses unique?",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "account", "account": str(same_account)},
            {"session": "B", "op": "account", "account": str(same_account)},
            {"session": "A", "op": "create_document", "result": str(doc_a)},
            {"session": "B", "op": "create_document", "result": str(doc_b)},
            {"op": "verify", "docs_are_same": docs_same,
             "comment": "Documents should have unique addresses"},
            {"session": "A", "op": "insert", "doc": str(doc_a), "text": "From A"},
            {"session": "B", "op": "insert", "doc": str(doc_b), "text": "From B"},
            {"session": "A", "op": "read", "doc": str(doc_a), "result": contents_a},
            {"session": "B", "op": "read", "doc": str(doc_b), "result": contents_b}
        ]
    }


def scenario_cross_session_link_visibility(sessions):
    """Session A creates a link, session B finds it.

    Tests that links are visible across sessions.
    """
    session_a, session_b = sessions

    # Session A: Create source and target documents
    session_a.account(Address(1, 1, 0, 1))
    source = session_a.create_document()
    target = session_a.create_document()

    source_opened = session_a.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(source_opened, Address(1, 1), ["Click here"])

    target_opened = session_a.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(target_opened, Address(1, 1), ["Destination"])

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 5))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 5))]))
    link_id = session_a.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session_a.close_document(target_opened)
    session_a.close_document(source_opened)

    # Session B: Find the link
    session_b.account(Address(1, 1, 0, 2))

    source_read = session_b.open_document(source, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 10))]))
    links_found = session_b.find_links(search_spec)
    session_b.close_document(source_read)

    return {
        "name": "cross_session_link_visibility",
        "description": "Session A creates link, session B finds it",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "create_document", "doc": "source", "result": str(source)},
            {"session": "A", "op": "create_document", "doc": "target", "result": str(target)},
            {"session": "A", "op": "insert", "doc": "source", "text": "Click here"},
            {"session": "A", "op": "insert", "doc": "target", "text": "Destination"},
            {"session": "A", "op": "create_link", "result": str(link_id)},
            {"session": "B", "op": "find_links", "in": str(source),
             "result": [str(l) for l in links_found],
             "comment": "B should find A's link"}
        ]
    }


def scenario_concurrent_versioning(sessions):
    """Both sessions version the same document.

    Tests what happens when two sessions both try to
    create versions of the same document.

    Note: Versions are created under the creator's account, so each session
    needs to use the same account to modify their version, or use CONFLICT_COPY.
    """
    session_a, session_b = sessions

    # Both sessions use the same account for this test
    # (versions belong to the creator's account)
    session_a.account(Address(1, 1, 0, 1))
    session_b.account(Address(1, 1, 0, 1))

    # Session A creates the original document
    original = session_a.create_document()

    orig_opened = session_a.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(orig_opened, Address(1, 1), ["Original content"])
    session_a.close_document(orig_opened)

    # Both sessions create versions
    version_a = session_a.create_version(original)
    version_b = session_b.create_version(original)

    # Modify each version (using CONFLICT_COPY since other session might have it open)
    va_opened = session_a.open_document(version_a, READ_WRITE, CONFLICT_COPY)
    va_vs = session_a.retrieve_vspanset(va_opened)
    session_a.insert(va_opened, va_vs.spans[0].end(), [" (A's changes)"])
    session_a.close_document(va_opened)

    vb_opened = session_b.open_document(version_b, READ_WRITE, CONFLICT_COPY)
    vb_vs = session_b.retrieve_vspanset(vb_opened)
    session_b.insert(vb_opened, vb_vs.spans[0].end(), [" (B's changes)"])
    session_b.close_document(vb_opened)

    # Read all versions
    orig_read = session_a.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_vs = session_a.retrieve_vspanset(orig_read)
    orig_ss = SpecSet(VSpec(orig_read, list(orig_vs.spans)))
    orig_contents = session_a.retrieve_contents(orig_ss)
    orig_contents = [str(c) if hasattr(c, 'digits') else c for c in orig_contents]
    session_a.close_document(orig_read)

    va_read = session_b.open_document(version_a, READ_ONLY, CONFLICT_COPY)
    va_vs2 = session_b.retrieve_vspanset(va_read)
    va_ss = SpecSet(VSpec(va_read, list(va_vs2.spans)))
    va_contents = session_b.retrieve_contents(va_ss)
    va_contents = [str(c) if hasattr(c, 'digits') else c for c in va_contents]
    session_b.close_document(va_read)

    vb_read = session_a.open_document(version_b, READ_ONLY, CONFLICT_COPY)
    vb_vs2 = session_a.retrieve_vspanset(vb_read)
    vb_ss = SpecSet(VSpec(vb_read, list(vb_vs2.spans)))
    vb_contents = session_a.retrieve_contents(vb_ss)
    vb_contents = [str(c) if hasattr(c, 'digits') else c for c in vb_contents]
    session_a.close_document(vb_read)

    versions_same = (version_a == version_b)

    return {
        "name": "concurrent_versioning",
        "description": "Both sessions create versions of the same document",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "account", "account": "1.1.0.1"},
            {"session": "B", "op": "account", "account": "1.1.0.1",
             "comment": "Both use same account (versions belong to creator)"},
            {"session": "A", "op": "create_document", "result": str(original)},
            {"session": "A", "op": "insert", "text": "Original content"},
            {"session": "A", "op": "create_version", "result": str(version_a)},
            {"session": "B", "op": "create_version", "of": str(original), "result": str(version_b)},
            {"op": "verify", "versions_are_same": versions_same,
             "comment": "Each session should get unique version addresses"},
            {"session": "A", "op": "insert", "doc": str(version_a), "text": " (A's changes)"},
            {"session": "B", "op": "insert", "doc": str(version_b), "text": " (B's changes)"},
            {"op": "contents", "doc": "original", "result": orig_contents,
             "comment": "Original unchanged"},
            {"op": "contents", "doc": "version_a", "result": va_contents,
             "comment": "A's version has A's changes"},
            {"op": "contents", "doc": "version_b", "result": vb_contents,
             "comment": "B's version has B's changes"}
        ]
    }


def scenario_cross_session_transclusion(sessions):
    """Session A transcludes from a document created by session B.

    Tests content identity preservation across sessions.
    """
    session_a, session_b = sessions

    # Session B creates source document
    session_b.account(Address(1, 1, 0, 2))
    source = session_b.create_document()

    source_opened = session_b.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(source_opened, Address(1, 1), ["Shared content from B"])
    session_b.close_document(source_opened)

    # Session A creates document and transcludes from B's document
    session_a.account(Address(1, 1, 0, 1))
    dest = session_a.create_document()

    dest_opened = session_a.open_document(dest, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(dest_opened, Address(1, 1), ["A's prefix: "])

    source_read = session_a.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_specs = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 14))]))  # "Shared content"
    dest_vs = session_a.retrieve_vspanset(dest_opened)
    session_a.vcopy(dest_opened, dest_vs.spans[0].end(), copy_specs)
    session_a.close_document(source_read)
    session_a.close_document(dest_opened)

    # Read both documents
    source_read2 = session_a.open_document(source, READ_ONLY, CONFLICT_COPY)
    s_vs = session_a.retrieve_vspanset(source_read2)
    s_ss = SpecSet(VSpec(source_read2, list(s_vs.spans)))
    source_contents = session_a.retrieve_contents(s_ss)
    source_contents = [str(c) if hasattr(c, 'digits') else c for c in source_contents]
    session_a.close_document(source_read2)

    dest_read = session_b.open_document(dest, READ_ONLY, CONFLICT_COPY)
    d_vs = session_b.retrieve_vspanset(dest_read)
    d_ss = SpecSet(VSpec(dest_read, list(d_vs.spans)))
    dest_contents = session_b.retrieve_contents(d_ss)
    dest_contents = [str(c) if hasattr(c, 'digits') else c for c in dest_contents]
    session_b.close_document(dest_read)

    # Compare versions to verify content sharing
    dest_read2 = session_a.open_document(dest, READ_ONLY, CONFLICT_COPY)
    source_read3 = session_a.open_document(source, READ_ONLY, CONFLICT_COPY)

    d_vs2 = session_a.retrieve_vspanset(dest_read2)
    s_vs2 = session_a.retrieve_vspanset(source_read3)

    d_ss2 = SpecSet(VSpec(dest_read2, list(d_vs2.spans)))
    s_ss2 = SpecSet(VSpec(source_read3, list(s_vs2.spans)))

    shared = session_a.compare_versions(d_ss2, s_ss2)
    shared_result = []
    for span_a, span_b in shared:
        shared_result.append({
            "dest": span_to_dict(span_a.span),
            "source": span_to_dict(span_b.span)
        })

    session_a.close_document(dest_read2)
    session_a.close_document(source_read3)

    return {
        "name": "cross_session_transclusion",
        "description": "Session A transcludes from document created by session B",
        "multisession": True,
        "operations": [
            {"session": "B", "op": "create_document", "doc": "source", "result": str(source)},
            {"session": "B", "op": "insert", "text": "Shared content from B"},
            {"session": "A", "op": "create_document", "doc": "dest", "result": str(dest)},
            {"session": "A", "op": "vcopy", "from": str(source), "to": str(dest)},
            {"op": "contents", "doc": "source", "result": source_contents},
            {"op": "contents", "doc": "dest", "result": dest_contents},
            {"op": "compare", "shared": shared_result,
             "comment": "Transcluded content should be shared"}
        ]
    }


def scenario_session_isolation(sessions):
    """Test that session state (account) is properly isolated.

    Changing account in session A should not affect session B.
    """
    session_a, session_b = sessions

    # Both start with same account
    account1 = Address(1, 1, 0, 1)
    account2 = Address(1, 1, 0, 2)

    session_a.account(account1)
    session_b.account(account1)

    # A creates a doc
    doc_a1 = session_a.create_document()

    # A switches account
    session_a.account(account2)

    # B creates a doc - should still be under account1
    doc_b1 = session_b.create_document()

    # A creates another doc - should be under account2
    doc_a2 = session_a.create_document()

    return {
        "name": "session_isolation",
        "description": "Account changes in one session don't affect another",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "account", "account": str(account1)},
            {"session": "B", "op": "account", "account": str(account1)},
            {"session": "A", "op": "create_document", "result": str(doc_a1),
             "comment": "Under account 1.1.0.1"},
            {"session": "A", "op": "account", "account": str(account2),
             "comment": "A switches to account 1.1.0.2"},
            {"session": "B", "op": "create_document", "result": str(doc_b1),
             "comment": "B should still be under 1.1.0.1"},
            {"session": "A", "op": "create_document", "result": str(doc_a2),
             "comment": "A creates under 1.1.0.2"}
        ]
    }


def scenario_concurrent_edit_different_regions(sessions):
    """Both sessions edit different parts of the same document.

    Tests concurrent editing when operations don't overlap.
    """
    session_a, session_b = sessions

    # A creates the document
    session_a.account(Address(1, 1, 0, 1))
    doc = session_a.create_document()

    doc_opened = session_a.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(doc_opened, Address(1, 1), ["AAAA____BBBB"])
    session_a.close_document(doc_opened)

    # Both open for editing
    edit_a = session_a.open_document(doc, READ_WRITE, CONFLICT_COPY)

    session_b.account(Address(1, 1, 0, 2))
    edit_b = session_b.open_document(doc, READ_WRITE, CONFLICT_COPY)

    # A edits the beginning (replace AAAA with XXXX)
    session_a.delete(edit_a, Address(1, 1), Offset(0, 4))
    session_a.insert(edit_a, Address(1, 1), ["XXXX"])

    # B edits the end (replace BBBB with YYYY)
    session_b.delete(edit_b, Address(1, 9), Offset(0, 4))
    session_b.insert(edit_b, Address(1, 9), ["YYYY"])

    session_a.close_document(edit_a)
    session_b.close_document(edit_b)

    # Read final state
    doc_read = session_a.open_document(doc, READ_ONLY, CONFLICT_COPY)
    vs = session_a.retrieve_vspanset(doc_read)
    ss = SpecSet(VSpec(doc_read, list(vs.spans)))
    contents = session_a.retrieve_contents(ss)
    contents = [str(c) if hasattr(c, 'digits') else c for c in contents]
    session_a.close_document(doc_read)

    return {
        "name": "concurrent_edit_different_regions",
        "description": "Both sessions edit non-overlapping regions of same document",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "create_document", "result": str(doc)},
            {"session": "A", "op": "insert", "text": "AAAA____BBBB"},
            {"session": "A", "op": "open_document", "mode": "READ_WRITE"},
            {"session": "B", "op": "open_document", "mode": "READ_WRITE"},
            {"session": "A", "op": "delete", "range": "1-4", "comment": "Delete AAAA"},
            {"session": "A", "op": "insert", "text": "XXXX"},
            {"session": "B", "op": "delete", "range": "9-12", "comment": "Delete BBBB"},
            {"session": "B", "op": "insert", "text": "YYYY"},
            {"op": "final_contents", "result": contents,
             "comment": "Both changes should be reflected (order may vary)"}
        ]
    }


def scenario_link_from_session_a_to_session_b_doc(sessions):
    """Session A creates a link pointing to a document owned by session B.

    Tests cross-session link creation and discovery.
    """
    session_a, session_b = sessions

    # B creates target document
    session_b.account(Address(1, 1, 0, 2))
    target = session_b.create_document()

    target_opened = session_b.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(target_opened, Address(1, 1), ["B's target content"])
    session_b.close_document(target_opened)

    # A creates source document and link to B's document
    session_a.account(Address(1, 1, 0, 1))
    source = session_a.create_document()

    source_opened = session_a.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(source_opened, Address(1, 1), ["Link to B's doc"])

    target_read = session_a.open_document(target, READ_ONLY, CONFLICT_COPY)

    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 4))]))  # "Link"
    link_target = SpecSet(VSpec(target_read, [Span(Address(1, 1), Offset(0, 8))]))  # "B's targ"
    link_id = session_a.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session_a.close_document(target_read)
    session_a.close_document(source_opened)

    # B finds links pointing to their document
    target_read2 = session_b.open_document(target, READ_ONLY, CONFLICT_COPY)
    search_spec = SpecSet(VSpec(target_read2, [Span(Address(1, 1), Offset(0, 20))]))
    links_by_target = session_b.find_links(NOSPECS, search_spec)  # Search by target
    session_b.close_document(target_read2)

    # A finds links from source
    source_read = session_a.open_document(source, READ_ONLY, CONFLICT_COPY)
    search_source = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 20))]))
    links_by_source = session_a.find_links(search_source)
    session_a.close_document(source_read)

    return {
        "name": "link_from_session_a_to_session_b_doc",
        "description": "A creates link pointing to B's document",
        "multisession": True,
        "operations": [
            {"session": "B", "op": "create_document", "doc": "target", "result": str(target)},
            {"session": "B", "op": "insert", "text": "B's target content"},
            {"session": "A", "op": "create_document", "doc": "source", "result": str(source)},
            {"session": "A", "op": "insert", "text": "Link to B's doc"},
            {"session": "A", "op": "create_link",
             "source_text": "Link", "target_doc": str(target),
             "result": str(link_id)},
            {"session": "B", "op": "find_links", "by": "target",
             "result": [str(l) for l in links_by_target],
             "comment": "B finds links targeting their document"},
            {"session": "A", "op": "find_links", "by": "source",
             "result": [str(l) for l in links_by_source],
             "comment": "A finds links from their source"}
        ]
    }


def scenario_node_creation_cross_session(sessions):
    """One session creates a node, another creates documents in it.

    Tests node/account visibility across sessions.
    """
    session_a, session_b = sessions

    # A creates a new node
    base_account = Address(1, 1, 0, 1)
    session_a.account(base_account)
    new_node = session_a.create_node(base_account)

    # A creates a document in the new node
    session_a.account(new_node)
    doc_a = session_a.create_document()

    opened_a = session_a.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session_a.insert(opened_a, Address(1, 1), ["A's doc in new node"])
    session_a.close_document(opened_a)

    # B switches to the new node and creates a document
    session_b.account(new_node)
    doc_b = session_b.create_document()

    opened_b = session_b.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session_b.insert(opened_b, Address(1, 1), ["B's doc in same node"])
    session_b.close_document(opened_b)

    # Both read each other's documents
    read_a = session_b.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    vs_a = session_b.retrieve_vspanset(read_a)
    ss_a = SpecSet(VSpec(read_a, list(vs_a.spans)))
    contents_a = session_b.retrieve_contents(ss_a)
    contents_a = [str(c) if hasattr(c, 'digits') else c for c in contents_a]
    session_b.close_document(read_a)

    read_b = session_a.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    vs_b = session_a.retrieve_vspanset(read_b)
    ss_b = SpecSet(VSpec(read_b, list(vs_b.spans)))
    contents_b = session_a.retrieve_contents(ss_b)
    contents_b = [str(c) if hasattr(c, 'digits') else c for c in contents_b]
    session_a.close_document(read_b)

    return {
        "name": "node_creation_cross_session",
        "description": "A creates node, both sessions create docs in it",
        "multisession": True,
        "operations": [
            {"session": "A", "op": "create_node", "result": str(new_node)},
            {"session": "A", "op": "account", "account": str(new_node)},
            {"session": "A", "op": "create_document", "result": str(doc_a)},
            {"session": "A", "op": "insert", "text": "A's doc in new node"},
            {"session": "B", "op": "account", "account": str(new_node)},
            {"session": "B", "op": "create_document", "result": str(doc_b)},
            {"session": "B", "op": "insert", "text": "B's doc in same node"},
            {"session": "B", "op": "read", "doc": str(doc_a), "result": contents_a,
             "comment": "B reads A's doc"},
            {"session": "A", "op": "read", "doc": str(doc_b), "result": contents_b,
             "comment": "A reads B's doc"}
        ]
    }


# Multi-session scenarios are run differently - they need the daemon
MULTISESSION_SCENARIOS = [
    ("multisession", "cross_session_doc_visibility", scenario_cross_session_doc_visibility),
    ("multisession", "concurrent_document_creation", scenario_concurrent_document_creation),
    ("multisession", "concurrent_write_same_account", scenario_concurrent_write_same_account),
    ("multisession", "cross_session_link_visibility", scenario_cross_session_link_visibility),
    ("multisession", "concurrent_versioning", scenario_concurrent_versioning),
    ("multisession", "cross_session_transclusion", scenario_cross_session_transclusion),
    ("multisession", "session_isolation", scenario_session_isolation),
    ("multisession", "concurrent_edit_different_regions", scenario_concurrent_edit_different_regions),
    ("multisession", "link_from_session_a_to_session_b_doc", scenario_link_from_session_a_to_session_b_doc),
    ("multisession", "node_creation_cross_session", scenario_node_creation_cross_session),
]

# Empty SCENARIOS list - these aren't run by the normal runner
SCENARIOS = []
