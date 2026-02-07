"""Provenance and POOM behavior scenarios for EWD-029 verification."""

from client import (
    Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_copy_duplicate_iaddresses(session):
    """What happens when you COPY I-addresses that already exist in the target POOM?

    Question 1: Does the implementation check for duplicates? What happens if you
    COPY an I-address that already appears in the target document?

    Test: Create document with text, COPY same content twice to same V-position range.
    """
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["ABCDE"])
    session.close_document(source_opened)

    # Create target document and COPY source content
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_specs = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 5))]))

    # First COPY - should work normally
    session.vcopy(target_opened, Address(1, 1), copy_specs)

    # Get vspanset and contents after first copy
    vs1 = session.retrieve_vspanset(target_opened)
    ss1 = SpecSet(VSpec(target_opened, list(vs1.spans)))
    contents1 = session.retrieve_contents(ss1)
    contents1 = [str(c) if hasattr(c, 'digits') else c for c in contents1]

    # Second COPY - same I-addresses to DIFFERENT V-position
    session.vcopy(target_opened, Address(1, 10), copy_specs)

    vs2 = session.retrieve_vspanset(target_opened)
    ss2 = SpecSet(VSpec(target_opened, list(vs2.spans)))
    contents2 = session.retrieve_contents(ss2)
    contents2 = [str(c) if hasattr(c, 'digits') else c for c in contents2]

    # Third COPY - same I-addresses to OVERLAPPING V-position
    # This tests if COPY extends existing mappings or creates duplicates
    session.vcopy(target_opened, Address(1, 8), copy_specs)

    vs3 = session.retrieve_vspanset(target_opened)
    ss3 = SpecSet(VSpec(target_opened, list(vs3.spans)))
    contents3 = session.retrieve_contents(ss3)
    contents3 = [str(c) if hasattr(c, 'digits') else c for c in contents3]

    session.close_document(source_read)
    session.close_document(target_opened)

    return {
        "name": "copy_duplicate_iaddresses",
        "description": "Test what happens when COPYing I-addresses that already exist in target POOM",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "ABCDE"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "vcopy", "from": "source", "to": "target", "at": "1.1",
             "comment": "First COPY - should work"},
            {"op": "contents", "doc": "target", "result": contents1},
            {"op": "vspanset", "doc": "target", "result": [span_to_dict(s) for s in vs1.spans]},
            {"op": "vcopy", "from": "source", "to": "target", "at": "1.10",
             "comment": "Second COPY - same I-addresses, different V-position"},
            {"op": "contents", "doc": "target", "result": contents2,
             "comment": "Should have ABCDE twice?"},
            {"op": "vspanset", "doc": "target", "result": [span_to_dict(s) for s in vs2.spans]},
            {"op": "vcopy", "from": "source", "to": "target", "at": "1.8",
             "comment": "Third COPY - overlapping V-position"},
            {"op": "contents", "doc": "target", "result": contents3,
             "comment": "What happens with overlapping COPY?"},
            {"op": "vspanset", "doc": "target", "result": [span_to_dict(s) for s in vs3.spans]}
        ]
    }


def scenario_createnewversion_text_vs_links(session):
    """Does CREATENEWVERSION copy text only (1.x) or also links (2.x)?

    Question 2: When CREATENEWVERSION runs, what subspaces get copied?

    Test: Create document with both text and links, create version, check what appears.
    """
    # Create original document with text
    original = session.create_document()
    orig_opened = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_opened, Address(1, 1), ["Original text with linkable words"])

    # Create target for link
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create link on "linkable" in original
    link_source = SpecSet(VSpec(orig_opened, [Span(Address(1, 19), Offset(0, 8))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(orig_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    session.close_document(target_opened)

    # Get original vspanset before versioning
    vs_before = session.retrieve_vspanset(orig_opened)
    session.close_document(orig_opened)

    # Create version (takes only one argument: the document to version)
    version = session.create_version(original)

    # Check version contents and vspanset
    ver_opened = session.open_document(version, READ_ONLY, CONFLICT_COPY)
    vs_version = session.retrieve_vspanset(ver_opened)
    ss_version = SpecSet(VSpec(ver_opened, list(vs_version.spans)))
    contents_version = session.retrieve_contents(ss_version)
    contents_version = [str(c) if hasattr(c, 'digits') else c for c in contents_version]

    # Can version find the link?
    ver_search = SpecSet(VSpec(ver_opened, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_version = session.find_links(ver_search)

    session.close_document(ver_opened)

    # Check original still has link
    orig_read = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    orig_search = SpecSet(VSpec(orig_read, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_original = session.find_links(orig_search)
    session.close_document(orig_read)

    return {
        "name": "createnewversion_text_vs_links",
        "description": "Test whether CREATENEWVERSION copies text subspace only or also link subspace",
        "operations": [
            {"op": "create_document", "doc": "original", "result": str(original)},
            {"op": "insert", "doc": "original", "text": "Original text with linkable words"},
            {"op": "create_link", "source_text": "linkable", "result": str(link_id)},
            {"op": "vspanset", "doc": "original", "result": [span_to_dict(s) for s in vs_before.spans],
             "comment": "Original should have text (1.x) and links (0.x or 2.x)"},
            {"op": "create_version", "from": "original", "result": str(version)},
            {"op": "vspanset", "doc": "version", "result": [span_to_dict(s) for s in vs_version.spans],
             "comment": "Does version have links subspace?"},
            {"op": "contents", "doc": "version", "result": contents_version,
             "comment": "Version text should match original"},
            {"op": "find_links", "from": "version",
             "result": [str(l) for l in links_from_version],
             "comment": "Can version find the link? (tests if links inherited)"},
            {"op": "find_links", "from": "original",
             "result": [str(l) for l in links_from_original],
             "comment": "Original should still have link"}
        ]
    }


def scenario_same_iaddress_multiple_vpositions(session):
    """Can the same I-address appear at multiple V-positions in one POOM?

    Question 3: If you COPY the same source span into a document twice,
    does the POOM contain duplicate I→V mappings?

    Test: Create source, COPY to target twice at different V-positions, check structure.
    """
    # Create source document
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["XYZ"])
    session.close_document(source_opened)

    # Create target and COPY twice
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["START "])

    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_specs = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 3))]))

    # First occurrence of XYZ at 1.7
    session.vcopy(target_opened, Address(1, 7), copy_specs)

    # Add separator
    vs1 = session.retrieve_vspanset(target_opened)
    session.insert(target_opened, vs1.spans[0].end(), [" MIDDLE "])

    # Second occurrence of XYZ
    vs2 = session.retrieve_vspanset(target_opened)
    session.vcopy(target_opened, vs2.spans[0].end(), copy_specs)

    # Add end marker
    vs3 = session.retrieve_vspanset(target_opened)
    session.insert(target_opened, vs3.spans[0].end(), [" END"])

    session.close_document(source_read)

    # Get final state
    vs_final = session.retrieve_vspanset(target_opened)
    ss_final = SpecSet(VSpec(target_opened, list(vs_final.spans)))
    contents_final = session.retrieve_contents(ss_final)
    contents_final = [str(c) if hasattr(c, 'digits') else c for c in contents_final]

    session.close_document(target_opened)

    return {
        "name": "same_iaddress_multiple_vpositions",
        "description": "Test if same I-address can appear at multiple V-positions in one POOM",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "XYZ"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "START "},
            {"op": "vcopy", "from": "source", "to": "target", "at": "1.7",
             "comment": "First occurrence of XYZ"},
            {"op": "insert", "doc": "target", "text": " MIDDLE "},
            {"op": "vcopy", "from": "source", "to": "target",
             "comment": "Second occurrence of XYZ"},
            {"op": "insert", "doc": "target", "text": " END"},
            {"op": "contents", "doc": "target", "result": contents_final,
             "comment": "Should be: START XYZ MIDDLE XYZ END"},
            {"op": "vspanset", "doc": "target", "result": [span_to_dict(s) for s in vs_final.spans],
             "comment": "How does POOM represent two occurrences of same I-addresses?"}
        ]
    }


def scenario_delete_then_recopy(session):
    """If you DELETE and then COPY back, is the POOM distinguishable?

    Question 4: After DELETE + COPY of same I-addresses, can you tell the
    difference from the original state?

    Test: Create doc, INSERT text, record state, DELETE, COPY back, compare.
    """
    # Create source (will copy from here)
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["SAMPLE"])
    session.close_document(source_opened)

    # Create target and INSERT same text directly
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["SAMPLE"])

    # Record initial state (from INSERT)
    vs_insert = session.retrieve_vspanset(target_opened)
    ss_insert = SpecSet(VSpec(target_opened, list(vs_insert.spans)))
    contents_insert = session.retrieve_contents(ss_insert)
    contents_insert = [str(c) if hasattr(c, 'digits') else c for c in contents_insert]

    # DELETE everything - delete(docid, start, end) where end is exclusive
    session.delete(target_opened, Address(1, 1), Address(1, 7))

    vs_deleted = session.retrieve_vspanset(target_opened)

    # COPY back the same I-addresses from source
    source_read = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    copy_specs = SpecSet(VSpec(source_read, [Span(Address(1, 1), Offset(0, 6))]))
    session.vcopy(target_opened, Address(1, 1), copy_specs)
    session.close_document(source_read)

    # Record final state (after DELETE + COPY)
    vs_recopied = session.retrieve_vspanset(target_opened)
    ss_recopied = SpecSet(VSpec(target_opened, list(vs_recopied.spans)))
    contents_recopied = session.retrieve_contents(ss_recopied)
    contents_recopied = [str(c) if hasattr(c, 'digits') else c for c in contents_recopied]

    session.close_document(target_opened)

    # Compare states
    insert_vspans = [span_to_dict(s) for s in vs_insert.spans]
    recopied_vspans = [span_to_dict(s) for s in vs_recopied.spans]

    return {
        "name": "delete_then_recopy",
        "description": "Test if DELETE + COPY produces same POOM as original INSERT",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source)},
            {"op": "insert", "doc": "source", "text": "SAMPLE"},
            {"op": "create_document", "doc": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "SAMPLE",
             "comment": "Direct INSERT - creates new I-addresses"},
            {"op": "vspanset", "doc": "target", "result": insert_vspans,
             "comment": "State after INSERT"},
            {"op": "contents", "doc": "target", "result": contents_insert},
            {"op": "delete", "doc": "target", "vspan": "1.1 to 1.7"},
            {"op": "vspanset", "doc": "target",
             "result": [span_to_dict(s) for s in vs_deleted.spans] if vs_deleted.spans else [],
             "comment": "State after DELETE (should be empty)"},
            {"op": "vcopy", "from": "source", "to": "target", "at": "1.1",
             "comment": "COPY back - shares I-addresses with source"},
            {"op": "vspanset", "doc": "target", "result": recopied_vspans,
             "comment": "State after DELETE + COPY"},
            {"op": "contents", "doc": "target", "result": contents_recopied,
             "comment": "Same text as before?"},
            {"op": "compare", "insert_vs_recopy": {
                "insert_vspans": insert_vspans,
                "recopied_vspans": recopied_vspans,
                "same": insert_vspans == recopied_vspans
            }, "comment": "Are vspansets identical? (probably NOT, different I-addresses)"}
        ]
    }


SCENARIOS = [
    ("provenance", "copy_duplicate_iaddresses", scenario_copy_duplicate_iaddresses),
    ("provenance", "createnewversion_text_vs_links", scenario_createnewversion_text_vs_links),
    ("provenance", "same_iaddress_multiple_vpositions", scenario_same_iaddress_multiple_vpositions),
    ("provenance", "delete_then_recopy", scenario_delete_then_recopy),
]
