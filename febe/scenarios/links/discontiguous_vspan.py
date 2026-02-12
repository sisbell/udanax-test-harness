"""Link creation on discontiguous I-addresses - does a V-span that maps to
non-contiguous I-addresses create multiple I-spans in the link endset?"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE,
)
from ..common import vspec_to_dict


def scenario_link_on_discontiguous_transcluded_content(session):
    """Test creating a link on a V-span that maps to non-contiguous I-addresses.

    This tests whether the backend creates multiple I-spans when a single V-span
    maps to non-contiguous I-addresses due to transclusion from different sources.
    """
    # Create source document A with "AAA"
    doc_a = session.create_document()
    doc_a_opened = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_a_opened, Address(1, 1), ["AAA"])
    session.close_document(doc_a_opened)

    # Create source document B with "BBB"
    doc_b = session.create_document()
    doc_b_opened = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(doc_b_opened, Address(1, 1), ["BBB"])
    session.close_document(doc_b_opened)

    # Create composite document C
    doc_c = session.create_document()
    doc_c_opened = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)

    # Need to re-open A and B to vcopy from them
    doc_a_opened2 = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    doc_b_opened2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)

    # Transclude "AA" from doc A
    session.vcopy(doc_c_opened, Address(1, 1),
                  SpecSet(VSpec(doc_a_opened2, [Span(Address(1, 1), Offset(0, 2))])))

    # Transclude "BB" from doc B
    session.vcopy(doc_c_opened, Address(1, 3),
                  SpecSet(VSpec(doc_b_opened2, [Span(Address(1, 1), Offset(0, 2))])))

    session.close_document(doc_a_opened2)
    session.close_document(doc_b_opened2)

    # Now doc C has "AABB" in V-space but maps to non-contiguous I-addresses:
    # V-positions 1.1-1.2 -> I-addresses from doc A
    # V-positions 1.3-1.4 -> I-addresses from doc B

    doc_c_contents = session.retrieve_contents(
        SpecSet(VSpec(doc_c_opened, [Span(Address(1, 1), Offset(0, 4))])))

    # Create target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Now create a link with the entire "AABB" span as the source
    # This is a CONTIGUOUS V-span (1.1 width 0.4) but maps to
    # NON-CONTIGUOUS I-addresses (some from doc A, some from doc B)
    link_source = SpecSet(VSpec(doc_c_opened, [Span(Address(1, 1), Offset(0, 4))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))

    try:
        link_id = session.create_link(doc_c_opened, link_source, link_target,
                                       SpecSet([JUMP_TYPE]))
        create_link_error = None
    except Exception as e:
        link_id = None
        create_link_error = str(e)

    followed_text = None
    follow_error = None
    endset_result = None
    endset_error = None

    if link_id is not None:
        # Follow the link back to see what we get
        try:
            followed_source = session.follow_link(link_id, LINK_SOURCE)
            followed_text = session.retrieve_contents(followed_source)
        except Exception as e:
            follow_error = str(e)

        # Retrieve the endsets — needs a SpecSet containing the link's span
        try:
            link_search = SpecSet(VSpec(doc_c_opened, [Span(Address(1, 1), Offset(0, 4))]))
            source_endset, target_endset, type_endset = session.retrieve_endsets(link_search)
            endset_result = {
                "source": str(source_endset),
                "target": str(target_endset),
                "type": str(type_endset)
            }
        except Exception as e:
            endset_error = str(e)

    try:
        session.close_document(doc_c_opened)
        session.close_document(target_opened)
    except Exception:
        pass

    return {
        "name": "link_on_discontiguous_transcluded_content",
        "description": "Test creating a link on a V-span that maps to non-contiguous I-addresses",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "AAA"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "BBB"},
            {"op": "create_document", "doc": "C (composite)", "result": str(doc_c)},
            {"op": "vcopy", "from": "A", "to": "C", "text": "AA"},
            {"op": "vcopy", "from": "B", "to": "C", "text": "BB"},
            {"op": "contents", "doc": "C", "result": doc_c_contents,
             "comment": "C has AABB from two different I-address sources"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "insert", "doc": "target", "text": "Target"},
            {"op": "create_link",
             "comment": "Link source is contiguous V-span 1.1 width 0.4 mapping to non-contiguous I-addresses",
             "result": str(link_id) if link_id else None,
             "error": create_link_error},
            {"op": "follow_link", "end": "source", "result": followed_text,
             "error": follow_error,
             "comment": "Should return full 'AABB' text"},
            {"op": "retrieve_endsets", "result": endset_result,
             "error": endset_error,
             "comment": "KEY: If source has 2+ spans, backend split discontiguous I-addresses"}
        ]
    }


SCENARIOS = [
    ("links", "link_on_discontiguous_transcluded_content",
     scenario_link_on_discontiguous_transcluded_content),
]
