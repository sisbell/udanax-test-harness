"""Link I-address allocation test scenarios."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_link_allocation_per_document(session):
    """Test whether link I-address allocation is per-document or global.

    Creates two documents A and B, and performs:
    1. MAKELINK on document A (creates link L1)
    2. MAKELINK on document B (creates link L2)
    3. MAKELINK on document A again (creates link L3)

    The link IDs returned by create_link are I-addresses of the link orgls.
    Per EWD-006, these should be in element subspace 2 (for links).

    If allocation is per-document:
      - L1 address: docA.2.1 (or similar)
      - L3 address: docA.2.2 (consecutive element number)
      - L2's allocation in document B should not affect document A's counter

    If allocation is global:
      - L1 address: docA.2.1
      - L2 address: docB.2.2
      - L3 address: docA.2.3 (non-consecutive because B's link advanced a global counter)
    """
    # Create document A
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Document A with text for links"])

    # Create document B
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Document B with text for links"])

    # Create target document (shared by all links)
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target content"])

    # Step 1: Create link L1 in document A
    source_a1 = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 8))]))  # "Document"
    target_specs = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))  # "Target"
    link_a1 = session.create_link(opened_a, source_a1, target_specs, SpecSet([JUMP_TYPE]))

    # Step 2: Create link L2 in document B
    source_b1 = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 8))]))  # "Document"
    link_b1 = session.create_link(opened_b, source_b1, target_specs, SpecSet([JUMP_TYPE]))

    # Step 3: Create link L3 in document A again
    source_a2 = SpecSet(VSpec(opened_a, [Span(Address(1, 15), Offset(0, 4))]))  # "text"
    link_a2 = session.create_link(opened_a, source_a2, target_specs, SpecSet([JUMP_TYPE]))

    session.close_document(opened_a)
    session.close_document(opened_b)
    session.close_document(target_opened)

    return {
        "name": "link_allocation_per_document",
        "description": "Test whether link I-address allocation is per-document (consecutive within doc) or global (interleaved)",
        "question": "If MAKELINK on doc A, then doc B, then doc A again — does doc A's second link get consecutive element number?",
        "link_a1_address": str(link_a1),
        "link_b1_address": str(link_b1),
        "link_a2_address": str(link_a2),
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "open_document", "doc": str(doc_a), "mode": "read_write", "result": str(opened_a)},
            {"op": "insert", "doc": str(opened_a), "address": "1.1", "text": "Document A with text for links"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "open_document", "doc": str(doc_b), "mode": "read_write", "result": str(opened_b)},
            {"op": "insert", "doc": str(opened_b), "address": "1.1", "text": "Document B with text for links"},
            {"op": "create_document", "doc": "target", "result": str(target_doc)},
            {"op": "open_document", "doc": str(target_doc), "mode": "read_write", "result": str(target_opened)},
            {"op": "insert", "doc": str(target_opened), "address": "1.1", "text": "Target content"},
            {"op": "create_link", "doc": "A", "link": "L1",
             "source": specset_to_list(source_a1),
             "target": specset_to_list(target_specs),
             "result": str(link_a1)},
            {"op": "create_link", "doc": "B", "link": "L2",
             "source": specset_to_list(source_b1),
             "target": specset_to_list(target_specs),
             "result": str(link_b1)},
            {"op": "create_link", "doc": "A", "link": "L3",
             "source": specset_to_list(source_a2),
             "target": specset_to_list(target_specs),
             "result": str(link_a2)},
            {"op": "analysis",
             "link_a1_id": str(link_a1),
             "link_b1_id": str(link_b1),
             "link_a2_id": str(link_a2),
             "interpretation": {
                 "per_document": "If L1 and L3 have consecutive element numbers (e.g., docA.2.1 and docA.2.2), allocation is per-document",
                 "global": "If L3 has non-consecutive element (e.g., docA.2.3 after docB.2.2), allocation is global"
             }}
        ]
    }


SCENARIOS = [
    ("links", "link_allocation_per_document", scenario_link_allocation_per_document),
]
