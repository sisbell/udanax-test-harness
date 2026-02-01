"""Test scenario to reveal how INSERT updates the V-space mapping."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_insert_vspace_mapping(session):
    """
    Reveal exactly how INSERT updates the V-to-I mapping.

    Key questions:
    1. How do V-addresses of content after the insertion point change?
    2. How is the new content's I-space address allocated?
    3. What happens to the V-to-I mapping?
    """
    # Create document and insert initial content
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABCDE" at position 1.1
    session.insert(opened, Address(1, 1), ["ABCDE"])
    vspanset_before = session.retrieve_vspanset(opened)

    # Get content at each V-position before insertion
    positions_before = {}
    for i in range(1, 6):  # positions 1-5
        span = Span(Address(1, i), Offset(0, 1))
        specset = SpecSet(VSpec(opened, [span]))
        content = session.retrieve_contents(specset)
        positions_before[f"1.{i}"] = content[0] if content else None

    # Create a version BEFORE we insert (to track I-space)
    session.close_document(opened)
    version_before = session.create_version(docid)

    # Reopen for modification
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # Now insert "XY" in the middle (at position 1.3, between B and C)
    session.insert(opened, Address(1, 3), ["XY"])

    vspanset_after = session.retrieve_vspanset(opened)

    # Get full content after
    full_specset = SpecSet(VSpec(opened, list(vspanset_after.spans)))
    full_content_after = session.retrieve_contents(full_specset)

    # Get content at each V-position after insertion
    positions_after = {}
    for i in range(1, 8):  # positions 1-7 (2 more chars)
        span = Span(Address(1, i), Offset(0, 1))
        specset = SpecSet(VSpec(opened, [span]))
        content = session.retrieve_contents(specset)
        positions_after[f"1.{i}"] = content[0] if content else None

    session.close_document(opened)

    # Now compare with version_before to see I-space identity
    # This reveals which content shares the same I-address
    r1 = session.open_document(version_before, READ_ONLY, CONFLICT_COPY)
    r2 = session.open_document(docid, READ_ONLY, CONFLICT_COPY)

    vs1 = session.retrieve_vspanset(r1)
    vs2 = session.retrieve_vspanset(r2)

    ss1 = SpecSet(VSpec(r1, list(vs1.spans)))
    ss2 = SpecSet(VSpec(r2, list(vs2.spans)))

    shared = session.compare_versions(ss1, ss2)
    shared_spans = []
    for span_a, span_b in shared:
        shared_spans.append({
            "version_before": span_to_dict(span_a.span),
            "after_insert": span_to_dict(span_b.span),
            "interpretation": f"Content at V-{span_a.span.start} in version shares I-address with content at V-{span_b.span.start} after insert"
        })

    session.close_document(r1)
    session.close_document(r2)

    return {
        "name": "insert_vspace_mapping",
        "description": "Reveal how INSERT updates the V-to-I mapping",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "address": "1.1", "text": "ABCDE"},
            {"op": "retrieve_vspanset", "label": "before_middle_insert",
             "result": vspec_to_dict(vspanset_before)},
            {"op": "content_at_positions", "label": "before_middle_insert",
             "positions": positions_before,
             "interpretation": "V-address 1.1=A, 1.2=B, 1.3=C, 1.4=D, 1.5=E"},

            {"op": "create_version", "label": "version_before",
             "result": str(version_before),
             "comment": "Snapshot I-space identity before modification"},

            {"op": "insert", "address": "1.3", "text": "XY",
             "comment": "Insert 'XY' BEFORE character at 1.3 (which is 'C')"},

            {"op": "retrieve_vspanset", "label": "after_middle_insert",
             "result": vspec_to_dict(vspanset_after)},
            {"op": "retrieve_contents", "label": "full_content_after",
             "result": full_content_after},
            {"op": "content_at_positions", "label": "after_middle_insert",
             "positions": positions_after,
             "interpretation": "Shows how V-addresses shifted"},

            {"op": "compare_versions",
             "comparing": "version_before vs current (after insert)",
             "shared_spans": shared_spans,
             "comment": "Reveals I-space identity preservation - which V-addresses map to same I-address"}
        ],
        "analysis": {
            "v_address_shift": "Content after insertion point has V-addresses shifted by length of inserted text",
            "i_space_allocation": "New content gets new I-addresses (allocated from bert)",
            "v_to_i_mapping": "Original content keeps same I-address but V-addresses change; compare_versions reveals this"
        }
    }


SCENARIOS = [
    ("content", "insert_vspace_mapping", scenario_insert_vspace_mapping),
]
