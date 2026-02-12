"""
Granfilade Split Test Scenarios

Tests to understand how splitting works in the granfilade (1D enfilade with M_b = 1).

The granfilade has MAXBCINLOAF = 1, meaning a height-1 internal node can hold
at most 1 bottom crum. This test explores what happens during splits when
a height-1 node would need to hold 2 children.

Key question: Does the split/rebalance algorithm ever create height-1 non-root
internal nodes in the granfilade? If so, how is the EN-4 constraint (2 ≤ #children ≤ M_b=1)
satisfied?
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)
from .common import vspec_to_dict, span_to_dict


def scenario_granfilade_single_text_atom(session):
    """
    Baseline: insert a single text atom and verify basic behavior.
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["HELLO"])

    vs = session.retrieve_vspanset(opened)
    specs = SpecSet(VSpec(opened, list(vs.spans)))
    contents = session.retrieve_contents(specs)

    session.close_document(opened)

    return {
        "name": "granfilade_single_text_atom",
        "description": "Baseline: single text atom in granfilade",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "HELLO", "address": "1.1"},
            {"op": "retrieve_contents", "result": contents,
             "vspans": vspec_to_dict(vs)},
        ],
        "expected": "Text stored and retrieved successfully"
    }


def scenario_granfilade_two_inserts(session):
    """
    Insert two separate text atoms to force the granfilade to have
    2 bottom crums. Observe the tree structure.

    Expected: Since MAXBCINLOAF = 1, a height-1 node can only hold 1 bottom crum.
    When a second insert creates a second bottom crum, one of:
    1. The fullcrum does a levelpush (increases height to 2)
    2. The second crum becomes a sibling at height-0 under the same height-1 parent
    3. Something else?
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    # First insert at position 1.1
    session.insert(opened, Address(1, 1), ["AAAAA"])
    vs1 = session.retrieve_vspanset(opened)
    specs1 = SpecSet(VSpec(opened, list(vs1.spans)))
    contents1 = session.retrieve_contents(specs1)

    # Second insert at end
    session.insert(opened, vs1.spans[0].end(), ["BBBBB"])
    vs2 = session.retrieve_vspanset(opened)
    specs2 = SpecSet(VSpec(opened, list(vs2.spans)))
    contents2 = session.retrieve_contents(specs2)

    session.close_document(opened)

    return {
        "name": "granfilade_two_inserts",
        "description": "Insert two text atoms to observe granfilade structure with 2 bottom crums",
        "operations": [
            {"op": "create_document", "result": str(docid)},
            {"op": "insert", "text": "AAAAA", "address": "1.1"},
            {"op": "retrieve_contents", "label": "after_first",
             "result": contents1, "vspans": vspec_to_dict(vs1)},
            {"op": "insert", "text": "BBBBB", "address": "after first"},
            {"op": "retrieve_contents", "label": "after_second",
             "result": contents2, "vspans": vspec_to_dict(vs2)},
        ],
        "expected": "Both inserts succeed; tree structure adapts to M_b=1 constraint"
    }


def scenario_granfilade_force_split(session):
    """
    Insert multiple text atoms in sequence to force the granfilade
    to split a height-1 node.

    With MAXBCINLOAF = 1, even inserting adjacent text should only
    create one bottom crum per atom (since fillupcbcseq has limits).
    """
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

    insert_results = []
    for i in range(5):
        vs = session.retrieve_vspanset(opened)
        if vs.spans:
            pos = vs.spans[-1].end()
        else:
            pos = Address(1, 1)
        text = f"TEXT{i}"
        session.insert(opened, pos, [text])
        vs_after = session.retrieve_vspanset(opened)
        insert_results.append({
            "text": text,
            "vspans_after": vspec_to_dict(vs_after)
        })

    # Retrieve all content
    final_vs = session.retrieve_vspanset(opened)
    final_specs = SpecSet(VSpec(opened, list(final_vs.spans)))
    final_contents = session.retrieve_contents(final_specs)

    session.close_document(opened)

    return {
        "name": "granfilade_force_split",
        "description": "Insert 5 text atoms to force granfilade to handle multiple bottom crums",
        "operations": [
            {"op": "create_document", "result": str(docid)},
        ] + [
            {"op": f"insert_{i}", "text": r["text"], "vspans": r["vspans_after"]}
            for i, r in enumerate(insert_results)
        ] + [
            {"op": "retrieve_contents", "result": final_contents,
             "vspans": vspec_to_dict(final_vs)},
        ],
        "expected": "All inserts succeed; granfilade handles M_b=1 via levelpush"
    }


SCENARIOS = [
    ("granfilade_split", "granfilade_single_text_atom", scenario_granfilade_single_text_atom),
    ("granfilade_split", "granfilade_two_inserts", scenario_granfilade_two_inserts),
    ("granfilade_split", "granfilade_force_split", scenario_granfilade_force_split),
]
