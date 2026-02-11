"""Rearrange operation semantic tests - exploring edge cases and specifications.

This module tests specific semantic questions about the rearrange operation:
1. Is v₃ in pre-move or post-move address space?
2. What happens when v₃ falls inside the source span?
3. What are the precise results for each case?
4. Does rearrange preserve I-addresses exactly?
"""

from client import Address, Offset, Span, VSpec, SpecSet
from scenarios.common import READ_WRITE, CONFLICT_FAIL


def scenario_pivot_v3_before_v1(session):
    """Test pivot where destination v₃ < source v₁.

    Text: "ABCDEFGH" at positions 1.1-1.8
    Move span [1.4, 1.6) = "DE" to position v₃ = 1.2

    Expected result: "ADEDEFGH" or "ADEFBCGH" depending on semantics.

    This tests: When v₃ < v₁, does content move to v₃ position in pre-move
    or post-move address space?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    # Pivot with cuts at: v₁=1.4, v₂=1.6, v₃=1.2
    # This should move "DE" (at 1.4-1.6) to position 1.2
    session.pivot(opened, Address(1, 4), Address(1, 6), Address(1, 2))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_after = session.retrieve_vspanset(opened)

    session.close_document(opened)

    return {
        "name": "pivot_v3_before_v1",
        "description": "Pivot where v₃ < v₁ (move content earlier)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot", "v1": "1.4", "v2": "1.6", "v3": "1.2",
             "description": "Move DE from [1.4,1.6) to 1.2"},
            {"op": "retrieve", "after": content_after},
            {"op": "vspanset_after", "result": str(vspanset_after),
             "comment": "Check if I-addresses preserved and V-addresses changed"}
        ]
    }


def scenario_pivot_v3_after_v2(session):
    """Test pivot where destination v₃ > source v₂.

    Text: "ABCDEFGH" at positions 1.1-1.8
    Move span [1.2, 1.4) = "BC" to position v₃ = 1.7

    This tests: When v₃ > v₂, how does content rearrange?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    # Pivot with cuts at: v₁=1.2, v₂=1.4, v₃=1.7
    # This should move "BC" (at 1.2-1.4) toward position 1.7
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 7))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_after = session.retrieve_vspanset(opened)

    session.close_document(opened)

    return {
        "name": "pivot_v3_after_v2",
        "description": "Pivot where v₃ > v₂ (move content later)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot", "v1": "1.2", "v2": "1.4", "v3": "1.7",
             "description": "Move BC from [1.2,1.4) toward 1.7"},
            {"op": "retrieve", "after": content_after},
            {"op": "vspanset_after", "result": str(vspanset_after)}
        ]
    }


def scenario_pivot_v3_inside_source(session):
    """Test pivot where v₃ falls inside the source span [v₁, v₂).

    Text: "ABCDEFGH" at positions 1.1-1.8
    Attempt: Move span [1.2, 1.6) = "BCDE" with v₃ = 1.4 (inside source!)

    This tests: What happens when v₃ is inside [v₁, v₂]?
    - No-op (do nothing)?
    - Error (reject the operation)?
    - Defined behavior (some specific result)?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    try:
        # Pivot with cuts at: v₁=1.2, v₂=1.4, v₃=1.3 (v₃ is inside [v₁, v₂))
        # What should happen here?
        session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 3))

        content_after = session.retrieve_contents(
            SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
        )

        vspanset_after = session.retrieve_vspanset(opened)
        status = "succeeded"
        error = None
    except Exception as e:
        content_after = None
        vspanset_after = None
        status = "failed"
        error = str(e)

    session.close_document(opened)

    return {
        "name": "pivot_v3_inside_source",
        "description": "Pivot where v₃ falls inside source span [v₁, v₂)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot_attempt", "v1": "1.2", "v2": "1.4", "v3": "1.3",
             "description": "Attempt pivot with v₃ inside source span",
             "status": status,
             "error": error if error else "N/A"},
            {"op": "retrieve", "after": str(content_after) if content_after else "N/A"},
            {"op": "vspanset_after", "result": str(vspanset_after) if vspanset_after else "N/A"}
        ]
    }


def scenario_pivot_v3_equals_v1(session):
    """Test pivot where v₃ = v₁ (move to same position).

    Text: "ABCDEFGH" at positions 1.1-1.8
    Move span [1.3, 1.5) = "CD" to position v₃ = 1.3

    This tests: Is this a no-op? Or does it have defined behavior?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    try:
        # Pivot with cuts at: v₁=1.3, v₂=1.5, v₃=1.3 (v₃ = v₁)
        session.pivot(opened, Address(1, 3), Address(1, 5), Address(1, 3))

        content_after = session.retrieve_contents(
            SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
        )

        vspanset_after = session.retrieve_vspanset(opened)
        status = "succeeded"
        error = None
    except Exception as e:
        content_after = None
        vspanset_after = None
        status = "failed"
        error = str(e)

    session.close_document(opened)

    return {
        "name": "pivot_v3_equals_v1",
        "description": "Pivot where v₃ = v₁ (destination = source start)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot_attempt", "v1": "1.3", "v2": "1.5", "v3": "1.3",
             "description": "Pivot with v₃ = v₁",
             "status": status,
             "error": error if error else "N/A"},
            {"op": "retrieve", "after": str(content_after) if content_after else "N/A"},
            {"op": "vspanset_after", "result": str(vspanset_after) if vspanset_after else "N/A"}
        ]
    }


def scenario_pivot_v3_equals_v2(session):
    """Test pivot where v₃ = v₂ (move to position right after source).

    Text: "ABCDEFGH" at positions 1.1-1.8
    Move span [1.2, 1.4) = "BC" to position v₃ = 1.4

    This tests: What happens when destination is immediately after source?
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    try:
        # Pivot with cuts at: v₁=1.2, v₂=1.4, v₃=1.4 (v₃ = v₂)
        session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 4))

        content_after = session.retrieve_contents(
            SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
        )

        vspanset_after = session.retrieve_vspanset(opened)
        status = "succeeded"
        error = None
    except Exception as e:
        content_after = None
        vspanset_after = None
        status = "failed"
        error = str(e)

    session.close_document(opened)

    return {
        "name": "pivot_v3_equals_v2",
        "description": "Pivot where v₃ = v₂ (destination = source end)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot_attempt", "v1": "1.2", "v2": "1.4", "v3": "1.4",
             "description": "Pivot with v₃ = v₂",
             "status": status,
             "error": error if error else "N/A"},
            {"op": "retrieve", "after": str(content_after) if content_after else "N/A"},
            {"op": "vspanset_after", "result": str(vspanset_after) if vspanset_after else "N/A"}
        ]
    }


def scenario_pivot_iaddress_preservation_detailed(session):
    """Detailed test of I-address preservation during pivot.

    Insert text, record exact I-addresses, pivot, verify I-addresses unchanged.
    This verifies that rearrange is truly moving the same content to new
    V-positions, not copying.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    # Get detailed vspanset before - this shows V→I mapping
    vspanset_before = session.retrieve_vspanset(opened)

    # Also get content to see what's there
    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Pivot: swap BC and DE
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    # Get vspanset after pivot
    vspanset_after = session.retrieve_vspanset(opened)

    # Get content after
    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    session.close_document(opened)

    return {
        "name": "pivot_iaddress_preservation_detailed",
        "description": "Detailed verification that pivot preserves I-addresses",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "vspanset_before", "result": str(vspanset_before),
             "comment": "Record exact V→I mapping before pivot"},
            {"op": "content_before", "result": content_before},
            {"op": "pivot", "v1": "1.2", "v2": "1.4", "v3": "1.6",
             "description": "Swap BC and DE"},
            {"op": "vspanset_after", "result": str(vspanset_after),
             "comment": "V-positions should change, I-addresses should be same"},
            {"op": "content_after", "result": content_after,
             "expected": "ADEBC (+ unchanged FGH)"}
        ]
    }


SCENARIOS = [
    ("rearrange_semantics", "pivot_v3_before_v1", scenario_pivot_v3_before_v1),
    ("rearrange_semantics", "pivot_v3_after_v2", scenario_pivot_v3_after_v2),
    ("rearrange_semantics", "pivot_v3_inside_source", scenario_pivot_v3_inside_source),
    ("rearrange_semantics", "pivot_v3_equals_v1", scenario_pivot_v3_equals_v1),
    ("rearrange_semantics", "pivot_v3_equals_v2", scenario_pivot_v3_equals_v2),
    ("rearrange_semantics", "pivot_iaddress_preservation_detailed", scenario_pivot_iaddress_preservation_detailed),
]
