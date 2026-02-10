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
    doc_spec = session.send("CREATE_DOCUMENT", {})
    doc_id = doc_spec["document_id"]
    session.send("OPEN_DOCUMENT", {"document_id": doc_id})

    # First insert at position 1.1
    session.send("INSERT", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "0.5"},
        "text": "AAAAA"
    })

    # Retrieve to confirm
    result1 = session.send("RETRIEVE_CONTENTS", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "0.5"}
    })

    # Second insert at position 2.1 (non-adjacent)
    session.send("INSERT", {
        "document_id": doc_id,
        "vspan": {"start": "2.1", "width": "0.5"},
        "text": "BBBBB"
    })

    # Retrieve both
    result2 = session.send("RETRIEVE_CONTENTS", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "1.5"}
    })

    session.send("CLOSE_DOCUMENT", {"document_id": doc_id})

    return {
        "name": "granfilade_two_inserts",
        "description": "Insert two text atoms to observe granfilade structure with 2 bottom crums",
        "operations": [
            "CREATE_DOCUMENT", "OPEN_DOCUMENT",
            "INSERT at 1.1", "RETRIEVE at 1.1",
            "INSERT at 2.1", "RETRIEVE 1.1-2.6",
            "CLOSE_DOCUMENT"
        ],
        "expected": "Both inserts succeed; tree structure adapts to M_b=1 constraint",
        "actual": {
            "first_insert": result1,
            "second_insert": result2
        }
    }


def scenario_granfilade_force_split(session):
    """
    Insert multiple text atoms in sequence to force the granfilade
    to split a height-1 node.

    With MAXBCINLOAF = 1, even inserting adjacent text should only
    create one bottom crum per atom (since fillupcbcseq has limits).
    """
    doc_spec = session.send("CREATE_DOCUMENT", {})
    doc_id = doc_spec["document_id"]
    session.send("OPEN_DOCUMENT", {"document_id": doc_id})

    inserts = []
    for i in range(5):
        vpos = f"{i+1}.1"
        session.send("INSERT", {
            "document_id": doc_id,
            "vspan": {"start": vpos, "width": "0.8"},
            "text": f"TEXT{i}"
        })
        inserts.append(vpos)

    # Retrieve all
    result = session.send("RETRIEVE_CONTENTS", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "4.8"}
    })

    session.send("CLOSE_DOCUMENT", {"document_id": doc_id})

    return {
        "name": "granfilade_force_split",
        "description": "Insert 5 text atoms to force granfilade to handle multiple bottom crums",
        "operations": [f"INSERT at {pos}" for pos in inserts] + ["RETRIEVE_CONTENTS"],
        "expected": "All inserts succeed; granfilade handles M_b=1 via levelpush",
        "actual": result
    }


def scenario_granfilade_single_text_atom(session):
    """
    Baseline: insert a single text atom and verify basic behavior.
    """
    doc_spec = session.send("CREATE_DOCUMENT", {})
    doc_id = doc_spec["document_id"]
    session.send("OPEN_DOCUMENT", {"document_id": doc_id})

    session.send("INSERT", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "0.5"},
        "text": "HELLO"
    })

    result = session.send("RETRIEVE_CONTENTS", {
        "document_id": doc_id,
        "vspan": {"start": "1.1", "width": "0.5"}
    })

    session.send("CLOSE_DOCUMENT", {"document_id": doc_id})

    return {
        "name": "granfilade_single_text_atom",
        "description": "Baseline: single text atom in granfilade",
        "operations": ["CREATE", "OPEN", "INSERT", "RETRIEVE", "CLOSE"],
        "expected": "Text stored and retrieved successfully",
        "actual": result
    }


SCENARIOS = [
    ("granfilade_split", "granfilade_single_text_atom", scenario_granfilade_single_text_atom),
    ("granfilade_split", "granfilade_two_inserts", scenario_granfilade_two_inserts),
    ("granfilade_split", "granfilade_force_split", scenario_granfilade_force_split),
]
