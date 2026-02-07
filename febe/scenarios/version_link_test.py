"""Test what CREATENEWVERSION copies from parent with links."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_version_copies_what(session):
    """Test whether CREATENEWVERSION copies only text (1.x) or everything including links (2.x)."""

    # Create parent document with text
    parent = session.create_document()
    parent_opened = session.open_document(parent, READ_WRITE, CONFLICT_FAIL)
    session.insert(parent_opened, Address(1, 1), ["Parent text with link"])

    # Create target document for link
    target = session.create_document()
    target_opened = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create link in parent
    from_span = Span(Address(1, 18), Offset(0, 4))  # "link"
    from_specs = SpecSet(VSpec(parent_opened, [from_span]))
    to_span = Span(Address(1, 1), Offset(0, 6))  # "Target"
    to_specs = SpecSet(VSpec(target_opened, [to_span]))

    link_id = session.create_link(parent_opened, from_specs, to_specs, SpecSet([JUMP_TYPE]))

    # Get parent vspanset BEFORE creating version
    parent_vspanset = session.retrieve_vspanset(parent_opened)
    parent_spans_before = list(parent_vspanset.spans)

    # Find links in parent
    parent_links_before = session.find_links(
        SpecSet(VSpec(parent_opened, parent_spans_before)),
        NOSPECS,
        NOSPECS
    )

    session.close_document(parent_opened)
    session.close_document(target_opened)

    # Create version
    version = session.create_version(parent)
    version_opened = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    # Get version vspanset
    version_vspanset = session.retrieve_vspanset(version_opened)
    version_spans = list(version_vspanset.spans)

    # Retrieve version content
    version_specset = SpecSet(VSpec(version_opened, version_spans))
    version_contents = session.retrieve_contents(version_specset)

    # Find links in version
    version_links = session.find_links(
        SpecSet(VSpec(version_opened, version_spans)),
        NOSPECS,
        NOSPECS
    )

    session.close_document(version_opened)

    return {
        "name": "version_copies_what",
        "description": "Test whether CREATENEWVERSION copies only text (1.x) or includes links (2.x)",
        "parent_spans": [span_to_dict(s) for s in parent_spans_before],
        "parent_links": len(parent_links_before),
        "version_spans": [span_to_dict(s) for s in version_spans],
        "version_contents": [str(c) if not isinstance(c, str) else c for c in version_contents],
        "version_links": len(version_links),
        "operations": [
            {"op": "create_document", "role": "parent", "result": str(parent)},
            {"op": "insert", "doc": "parent", "text": "Parent text with link"},
            {"op": "create_document", "role": "target", "result": str(target)},
            {"op": "insert", "doc": "target", "text": "Target"},
            {"op": "create_link", "result": str(link_id)},
            {"op": "retrieve_vspanset", "doc": "parent", "spans": [span_to_dict(s) for s in parent_spans_before]},
            {"op": "find_links", "doc": "parent", "count": len(parent_links_before)},
            {"op": "create_version", "from": str(parent), "result": str(version)},
            {"op": "retrieve_vspanset", "doc": "version", "spans": [span_to_dict(s) for s in version_spans]},
            {"op": "retrieve_contents", "doc": "version", "result": [str(c) if not isinstance(c, str) else c for c in version_contents]},
            {"op": "find_links", "doc": "version", "count": len(version_links)}
        ]
    }


SCENARIOS = [
    ("versions", "version_copies_what", scenario_version_copies_what),
]
