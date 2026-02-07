"""Link POOM shifting test scenarios.

Tests to determine whether CREATELINK shifts existing POOM entries or
places at next available position without disturbing existing entries.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    JUMP_TYPE
)
from ..common import specset_to_list


def scenario_link_poom_no_shift(session):
    """Create two links and verify they don't shift each other's positions.

    If CREATELINK shifts existing entries (like INSERT), the second link
    would push the first link's orgl reference to a new V-position.

    If CREATELINK places at next available position without shifting,
    the first link's orgl reference stays at its original V-position.
    """
    # Create source and target documents
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["First link and second link"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Create first link from "First" to target
    link1_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 5))]))
    link1_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link1_id = session.create_link(source_opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Retrieve the full vspanset after first link - should include link orgl reference
    vspan1 = session.retrieve_vspanset(source_opened)

    # Create second link from "second" to target
    link2_source = SpecSet(VSpec(source_opened, [Span(Address(1, 16), Offset(0, 6))]))
    link2_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link2_id = session.create_link(source_opened, link2_source, link2_target, SpecSet([JUMP_TYPE]))

    # Retrieve the full vspanset after second link
    vspan2 = session.retrieve_vspanset(source_opened)

    # Retrieve endsets to see if positions changed
    doc_span = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(1))]))
    final_source, final_target, final_type = session.retrieve_endsets(doc_span)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_poom_no_shift",
        "description": "Verify CREATELINK doesn't shift existing link POOM entries",
        "operations": [
            {"op": "create_link", "num": 1, "source_text": "First", "result": str(link1_id)},
            {"op": "retrieve_vspanset", "after": "link1",
             "spans": [f"{s.start}-{s.width}" for s in vspan1.spans],
             "comment": "Document extent after first link"},
            {"op": "create_link", "num": 2, "source_text": "second", "result": str(link2_id)},
            {"op": "retrieve_vspanset", "after": "link2",
             "spans": [f"{s.start}-{s.width}" for s in vspan2.spans],
             "comment": "Document extent after second link - did vspan change?"},
            {"op": "retrieve_endsets", "final_state": True,
             "source": specset_to_list(final_source),
             "comment": "Final endset positions - do they match vspanset growth?"}
        ]
    }


def scenario_link_orgl_vposition_observation(session):
    """Observe the V-position where link orgl references are placed.

    This test creates a link and examines the full document vspan to see
    where the link orgl reference appears in the 2.x subspace.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["Content for linking"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    # Get vspan before link creation
    vspan_before = session.retrieve_vspanset(source_opened)

    # Create link
    link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 7))]))
    link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Get vspan after link creation
    vspan_after = session.retrieve_vspanset(source_opened)

    # Find the new span (should be in 2.x subspace)
    new_spans = [s for s in vspan_after.spans if s not in vspan_before.spans]

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "link_orgl_vposition_observation",
        "description": "Observe V-position of link orgl reference in POOM",
        "operations": [
            {"op": "insert", "text": "Content for linking"},
            {"op": "retrieve_vspanset", "label": "before_link",
             "spans": [f"{s.start}-{s.width}" for s in vspan_before.spans],
             "comment": "Only text (1.x subspace)"},
            {"op": "create_link", "result": str(link_id)},
            {"op": "retrieve_vspanset", "label": "after_link",
             "spans": [f"{s.start}-{s.width}" for s in vspan_after.spans],
             "new_spans": [f"{s.start}-{s.width}" for s in new_spans],
             "comment": "Should show link orgl in 2.x subspace"}
        ]
    }


def scenario_three_links_vspan_growth(session):
    """Create three links and track vspan growth pattern.

    This reveals whether links are placed sequentially at 2.(k+1)
    without shifting, or if each new link shifts previous entries.
    """
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["First, second, and third"])

    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target"])

    vspan_initial = session.retrieve_vspanset(source_opened)

    # Create first link
    link1_source = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 5))]))
    link1_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link1_id = session.create_link(source_opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))
    vspan_1 = session.retrieve_vspanset(source_opened)

    # Create second link
    link2_source = SpecSet(VSpec(source_opened, [Span(Address(1, 8), Offset(0, 6))]))
    link2_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link2_id = session.create_link(source_opened, link2_source, link2_target, SpecSet([JUMP_TYPE]))
    vspan_2 = session.retrieve_vspanset(source_opened)

    # Create third link
    link3_source = SpecSet(VSpec(source_opened, [Span(Address(1, 20), Offset(0, 5))]))
    link3_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
    link3_id = session.create_link(source_opened, link3_source, link3_target, SpecSet([JUMP_TYPE]))
    vspan_3 = session.retrieve_vspanset(source_opened)

    session.close_document(source_opened)
    session.close_document(target_opened)

    return {
        "name": "three_links_vspan_growth",
        "description": "Track vspan growth pattern for three successive links",
        "operations": [
            {"op": "insert", "text": "First, second, and third"},
            {"op": "retrieve_vspanset", "label": "initial",
             "spans": [f"{s.start}-{s.width}" for s in vspan_initial.spans]},
            {"op": "create_link", "num": 1, "result": str(link1_id)},
            {"op": "retrieve_vspanset", "label": "after_link1",
             "spans": [f"{s.start}-{s.width}" for s in vspan_1.spans]},
            {"op": "create_link", "num": 2, "result": str(link2_id)},
            {"op": "retrieve_vspanset", "label": "after_link2",
             "spans": [f"{s.start}-{s.width}" for s in vspan_2.spans],
             "comment": "If link1's span changed, CREATELINK shifts; if not, it appends"},
            {"op": "create_link", "num": 3, "result": str(link3_id)},
            {"op": "retrieve_vspanset", "label": "after_link3",
             "spans": [f"{s.start}-{s.width}" for s in vspan_3.spans],
             "comment": "Pattern should be clear by now"}
        ]
    }


SCENARIOS = [
    ("link_poom", "link_poom_no_shift", scenario_link_poom_no_shift),
    ("link_poom", "link_orgl_vposition_observation", scenario_link_orgl_vposition_observation),
    ("link_poom", "three_links_vspan_growth", scenario_three_links_vspan_growth),
]
