"""Test scenarios for element type enforcement in V-subspaces.

This tests whether the system enforces type restrictions - specifically,
can link orgls (element type 2) appear in the text subspace (1.x)?
Can text bytes appear in the link subspace (2.x)?
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_copy_link_to_text_subspace(session):
    """Test whether copying from link subspace (0.x) to text subspace (1.x) is allowed.

    This scenario attempts to:
    1. Create document A with text
    2. Create document B with text
    3. Create a link in A (stored at V-position 0.x)
    4. Attempt to vcopy from A's link subspace (0.x) to A's text subspace (1.x)
    5. Check what happens - does it:
       a) Succeed and store orgl reference as "text"?
       b) Fail with error?
       c) Succeed but retrieve_contents returns gibberish?

    Expected behavior: The system has NO type enforcement - vcopy will succeed
    and the link ISA will appear in the text subspace.
    """
    # Create document A with initial text
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["TextInA"])

    # Create document B for link target
    doc_b = session.create_document()
    b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(b_opened, Address(1, 1), ["TextInB"])

    # Create a link in A (will be at 0.x)
    source_span = Span(Address(1, 1), Offset(0, 4))  # "Text"
    source_specs = SpecSet(VSpec(a_opened, [source_span]))
    target_span = Span(Address(1, 1), Offset(0, 4))
    target_specs = SpecSet(VSpec(b_opened, [target_span]))
    link_id = session.create_link(a_opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    # Check vspanset - should show 0.x (link) and 1.x (text)
    vspan_before = session.retrieve_vspanset(a_opened)

    # Attempt to vcopy from link subspace (0.x) to text subspace (1.x)
    # This creates a SpecSet that references the link subspace
    link_span = Span(Address(0, 1), Offset(0, 1))  # Link at 0.1
    link_specs = SpecSet(VSpec(a_opened, [link_span]))

    try:
        # Try to copy the link reference to position 1.20 (text subspace)
        session.vcopy(a_opened, Address(1, 20), link_specs)
        copy_succeeded = True
        copy_error = None
    except Exception as e:
        copy_succeeded = False
        copy_error = str(e)

    # Check vspanset after copy attempt
    vspan_after = session.retrieve_vspanset(a_opened)

    # Try to retrieve contents from position 1.20
    try:
        retrieve_span = Span(Address(1, 20), Offset(0, 1))
        retrieve_specs = SpecSet(VSpec(a_opened, [retrieve_span]))
        retrieved = session.retrieve_contents(retrieve_specs)
        retrieve_succeeded = True
        retrieve_error = None
    except Exception as e:
        retrieved = None
        retrieve_succeeded = False
        retrieve_error = str(e)

    session.close_document(a_opened)
    session.close_document(b_opened)

    return {
        "name": "copy_link_to_text_subspace",
        "description": "Test whether link orgl references can be copied to text subspace (1.x)",
        "operations": [
            {"op": "create_document", "result": str(doc_a)},
            {"op": "open_document", "doc": str(doc_a), "mode": "read_write", "result": str(a_opened)},
            {"op": "insert", "doc": str(a_opened), "address": "1.1", "text": "TextInA"},
            {"op": "create_document", "result": str(doc_b)},
            {"op": "open_document", "doc": str(doc_b), "mode": "read_write", "result": str(b_opened)},
            {"op": "insert", "doc": str(b_opened), "address": "1.1", "text": "TextInB"},
            {"op": "create_link",
             "home_doc": str(a_opened),
             "source": specset_to_list(source_specs),
             "target": specset_to_list(target_specs),
             "type": "jump",
             "result": str(link_id)},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_before), "note": "Before copy: 0.x link, 1.x text"},
            {"op": "vcopy",
             "doc": str(a_opened),
             "address": "1.20",
             "source": specset_to_list(link_specs),
             "succeeded": copy_succeeded,
             "error": copy_error,
             "note": "Attempt to copy link ISA (0.1) to text position (1.20)"},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_after), "note": "After copy attempt"},
            {"op": "retrieve_contents",
             "from": "1.20",
             "width": "0.1",
             "result": retrieved,
             "succeeded": retrieve_succeeded,
             "error": retrieve_error,
             "note": "What does position 1.20 contain?"}
        ]
    }


def scenario_insert_text_at_link_subspace(session):
    """Test whether INSERT can place text bytes at a 2.x V-position (link subspace).

    Question: Does the back end enforce subspace partition at INSERT level?
    - Expected (if enforced): INSERT at 2.x should fail
    - Actual (if not enforced): INSERT at 2.x succeeds, text bytes at link position

    Test strategy:
    1. Create document A with normal text at 1.1
    2. Attempt to INSERT text at 2.1 (link subspace)
    3. Check vspanset - does 2.x position appear?
    4. Attempt to retrieve contents from 2.1
    5. Check if FINDDOCSCONTAINING can find the document via 2.x content

    This tests whether insertpm (orglinks.c:75-134) validates V-position subspace.
    Code inspection shows acceptablevsa (do2.c:110) just returns TRUE - no validation.
    """
    # Create document with normal text
    doc_a = session.create_document()
    a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(a_opened, Address(1, 1), ["NormalText"])

    # Check initial vspanset - should be 1.x only
    vspan_before = session.retrieve_vspanset(a_opened)

    # Attempt to INSERT text at 2.1 (link subspace)
    try:
        session.insert(a_opened, Address(2, 1), ["TextAtLinkPosition"])
        insert_succeeded = True
        insert_error = None
    except Exception as e:
        insert_succeeded = False
        insert_error = str(e)

    # Check vspanset after insert attempt
    vspan_after = session.retrieve_vspanset(a_opened)

    # Try to retrieve contents from 2.1
    try:
        retrieve_span = Span(Address(2, 1), Offset(0, 19))
        retrieve_specs = SpecSet(VSpec(a_opened, [retrieve_span]))
        retrieved = session.retrieve_contents(retrieve_specs)
        retrieve_succeeded = True
        retrieve_error = None
    except Exception as e:
        retrieved = None
        retrieve_succeeded = False
        retrieve_error = str(e)

    # Check FINDDOCSCONTAINING - can it find via 2.x content?
    try:
        find_specs = SpecSet(VSpec(a_opened, [Span(Address(2, 1), Offset(0, 4))]))  # "Text"
        found_docs = session.find_documents_containing(find_specs)
        find_succeeded = True
        find_error = None
    except Exception as e:
        found_docs = []
        find_succeeded = False
        find_error = str(e)

    session.close_document(a_opened)

    return {
        "name": "insert_text_at_link_subspace",
        "description": "Test whether INSERT allows text bytes at 2.x V-position (link subspace)",
        "operations": [
            {"op": "create_document", "result": str(doc_a)},
            {"op": "open_document", "doc": str(doc_a), "mode": "read_write", "result": str(a_opened)},
            {"op": "insert", "doc": str(a_opened), "address": "1.1", "text": "NormalText"},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_before), "note": "Before 2.x insert: should be 1.x only"},
            {"op": "insert",
             "doc": str(a_opened),
             "address": "2.1",
             "text": "TextAtLinkPosition",
             "succeeded": insert_succeeded,
             "error": insert_error,
             "note": "CRITICAL: Can INSERT place text at 2.x (link subspace)?"},
            {"op": "retrieve_vspanset", "doc": str(a_opened), "result": vspec_to_dict(vspan_after), "note": "After 2.x insert: does 2.x appear?"},
            {"op": "retrieve_contents",
             "from": "2.1",
             "width": "0.19",
             "result": retrieved,
             "succeeded": retrieve_succeeded,
             "error": retrieve_error,
             "note": "Can we retrieve text from 2.x?"},
            {"op": "find_documents_containing",
             "specset": specset_to_list(SpecSet(VSpec(a_opened, [Span(Address(2, 1), Offset(0, 4))]))),
             "result": [str(d) for d in found_docs] if found_docs else [],
             "succeeded": find_succeeded,
             "error": find_error,
             "note": "Can FINDDOCSCONTAINING find doc via 2.x content?"}
        ]
    }


SCENARIOS = [
    ("links", "copy_link_to_text_subspace", scenario_copy_link_to_text_subspace),
    ("links", "insert_text_at_link_subspace", scenario_insert_text_at_link_subspace),
]
