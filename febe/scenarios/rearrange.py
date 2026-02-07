"""Rearrange operation test scenarios (pivot and swap)."""

from client import Address, Offset, Span, VSpec, SpecSet
from scenarios.common import READ_WRITE, CONFLICT_FAIL


def scenario_pivot_adjacent_regions(session):
    """Pivot swaps two adjacent regions around a pivot point.

    Given text "ABCDE" with cuts at positions marking:
    - Region 1: "BC" (positions 2-3)
    - Region 2: "DE" (positions 4-5)

    After pivot: "ADEBC" - the two regions swap positions.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABCDE" (positions 1.1 through 1.5)
    session.insert(opened, Address(1, 1), ["ABCDE"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    # Pivot: swap regions [1.2, 1.4) and [1.4, 1.6)
    # Cut points: 1.2 (after A), 1.4 (after C), 1.6 (after E)
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    session.close_document(opened)

    return {
        "name": "pivot_adjacent_regions",
        "description": "Pivot swaps two adjacent regions",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDE"},
            {"op": "retrieve", "before": content_before},
            {"op": "pivot", "cut1": "1.2", "cut2": "1.4", "cut3": "1.6",
             "description": "Swap regions BC and DE"},
            {"op": "retrieve", "after": content_after,
             "expected": "ADEBC (regions swapped)"}
        ]
    }


def scenario_pivot_word_swap(session):
    """Pivot to swap two words.

    "Hello World" -> "World Hello" by pivoting around the space.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["Hello World"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 11))]))
    )

    # Pivot: swap "Hello " and "World"
    # Cut points: 1.1 (start), 1.7 (after "Hello "), 1.12 (end)
    session.pivot(opened, Address(1, 1), Address(1, 7), Address(1, 12))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 11))]))
    )

    session.close_document(opened)

    return {
        "name": "pivot_word_swap",
        "description": "Pivot to swap two words",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "Hello World"},
            {"op": "retrieve", "before": content_before},
            {"op": "pivot", "cut1": "1.1", "cut2": "1.7", "cut3": "1.12",
             "description": "Swap 'Hello ' and 'World'"},
            {"op": "retrieve", "after": content_after,
             "expected": "WorldHello  (note space position)"}
        ]
    }


def scenario_pivot_single_char(session):
    """Pivot a single character to a different position.

    "ABC" -> "BAC" by moving B before A.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABC"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 3))]))
    )

    # Pivot: swap "A" and "B"
    # Cut points: 1.1 (start), 1.2 (after A), 1.3 (after B)
    session.pivot(opened, Address(1, 1), Address(1, 2), Address(1, 3))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 3))]))
    )

    session.close_document(opened)

    return {
        "name": "pivot_single_char",
        "description": "Pivot single characters",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABC"},
            {"op": "retrieve", "before": content_before},
            {"op": "pivot", "cut1": "1.1", "cut2": "1.2", "cut3": "1.3",
             "description": "Swap A and B"},
            {"op": "retrieve", "after": content_after,
             "expected": "BAC"}
        ]
    }


def scenario_swap_non_adjacent(session):
    """Swap two non-adjacent regions.

    "ABCDEFGH" -> swap "BC" and "FG" -> "AFGDEBCH"
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Swap: regions [1.2, 1.4) = "BC" and [1.6, 1.8) = "FG"
    # Cut points: 1.2 (after A), 1.4 (after C), 1.6 (after E), 1.8 (after G)
    session.swap(opened, Address(1, 2), Address(1, 4), Address(1, 6), Address(1, 8))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    session.close_document(opened)

    return {
        "name": "swap_non_adjacent",
        "description": "Swap two non-adjacent regions",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "retrieve", "before": content_before},
            {"op": "swap", "cut1": "1.2", "cut2": "1.4", "cut3": "1.6", "cut4": "1.8",
             "description": "Swap BC and FG"},
            {"op": "retrieve", "after": content_after,
             "expected": "AFGDEBCH (BC and FG swapped)"}
        ]
    }


def scenario_swap_first_and_last(session):
    """Swap first and last characters.

    "HELLO" -> "OELLH"
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["HELLO"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    # Swap: regions [1.1, 1.2) = "H" and [1.5, 1.6) = "O"
    session.swap(opened, Address(1, 1), Address(1, 2), Address(1, 5), Address(1, 6))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    session.close_document(opened)

    return {
        "name": "swap_first_and_last",
        "description": "Swap first and last characters",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "HELLO"},
            {"op": "retrieve", "before": content_before},
            {"op": "swap", "cut1": "1.1", "cut2": "1.2", "cut3": "1.5", "cut4": "1.6",
             "description": "Swap H and O"},
            {"op": "retrieve", "after": content_after,
             "expected": "OELLH"}
        ]
    }


def scenario_swap_words_in_sentence(session):
    """Swap two words in a longer sentence.

    "The quick brown fox" -> "The brown quick fox"
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["The quick brown fox"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 19))]))
    )

    # "The quick brown fox"
    #  123456789...
    # "quick" = positions 5-9 (indices 5-10, not including space)
    # "brown" = positions 11-15
    # Swap: [1.5, 1.10) = "quick" and [1.11, 1.16) = "brown"
    session.swap(opened, Address(1, 5), Address(1, 10), Address(1, 11), Address(1, 16))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 19))]))
    )

    session.close_document(opened)

    return {
        "name": "swap_words_in_sentence",
        "description": "Swap two words in a sentence",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "The quick brown fox"},
            {"op": "retrieve", "before": content_before},
            {"op": "swap", "cut1": "1.5", "cut2": "1.10", "cut3": "1.11", "cut4": "1.16",
             "description": "Swap 'quick' and 'brown'"},
            {"op": "retrieve", "after": content_after,
             "expected": "The brown quick fox"}
        ]
    }


def scenario_pivot_preserves_identity(session):
    """Verify that pivot preserves content identity (I-addresses).

    After pivoting, the content should still have the same identity,
    just at different V-addresses.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDE"])

    # Get vspanset before pivot to see I-addresses
    vspanset_before = session.retrieve_vspanset(opened)

    # Pivot to swap BC and DE
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    # Get vspanset after pivot
    vspanset_after = session.retrieve_vspanset(opened)

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    session.close_document(opened)

    return {
        "name": "pivot_preserves_identity",
        "description": "Pivot preserves content identity (I-addresses)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDE"},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot", "description": "Swap BC and DE"},
            {"op": "vspanset_after", "result": str(vspanset_after),
             "comment": "I-addresses should be same, V-addresses changed"},
            {"op": "retrieve", "result": content_after}
        ]
    }


def scenario_swap_with_links(session):
    """Verify link behavior when swapping linked content.

    If a link points to a region that gets swapped, the link should
    follow the content to its new position (content identity preservation).
    """
    from scenarios.common import JUMP_TYPE

    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # "ABCDEFGH" - we'll link to "BC" then swap it with "FG"
    session.insert(opened, Address(1, 1), ["ABCDEFGH"])

    # Create a link to "BC" (positions 1.2 to 1.4)
    link_source = SpecSet(VSpec(opened, [Span(Address(1, 2), Offset(0, 2))]))
    link_target = SpecSet(VSpec(opened, [Span(Address(1, 6), Offset(0, 2))]))  # FG
    link_id = session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Find links before swap
    links_before = session.find_links(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Swap BC and FG
    session.swap(opened, Address(1, 2), Address(1, 4), Address(1, 6), Address(1, 8))

    content_after = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    # Find links after swap - should still find the link
    links_after = session.find_links(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 8))]))
    )

    session.close_document(opened)

    return {
        "name": "swap_with_links",
        "description": "Links follow content through swap operations",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDEFGH"},
            {"op": "create_link", "source": "BC", "target": "FG", "result": str(link_id)},
            {"op": "find_links", "before_swap": [str(l) for l in links_before]},
            {"op": "swap", "description": "Swap BC and FG"},
            {"op": "retrieve", "after": content_after},
            {"op": "find_links", "after_swap": [str(l) for l in links_after],
             "comment": "Link should still be discoverable at new positions"}
        ]
    }


def scenario_double_pivot(session):
    """Two pivots should return content to original order.

    ABCDE -> pivot BC/DE -> ADEBC -> pivot DE/BC -> ABCDE
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDE"])

    content_original = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    # First pivot: swap BC and DE -> ADEBC
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    content_after_first = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    # Second pivot: swap the now-rearranged content back
    # After first pivot: A DE BC (positions: A=1, D=2, E=3, B=4, C=5)
    # Swap DE (1.2-1.4) and BC (1.4-1.6)
    session.pivot(opened, Address(1, 2), Address(1, 4), Address(1, 6))

    content_after_second = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
    )

    session.close_document(opened)

    return {
        "name": "double_pivot",
        "description": "Two pivots return content to original order",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABCDE"},
            {"op": "retrieve", "original": content_original},
            {"op": "pivot", "first": "swap BC and DE"},
            {"op": "retrieve", "after_first": content_after_first},
            {"op": "pivot", "second": "swap back"},
            {"op": "retrieve", "after_second": content_after_second,
             "expected": "Should match original (ABCDE)"}
        ]
    }


def scenario_pivot_cross_subspace_boundary(session):
    """Test whether REARRANGE can move content across subspace boundaries.

    This test attempts to pivot content from 1.x (text subspace) such that
    it would end up in 2.x (link subspace) positions. This tests the
    fundamental constraint: does REARRANGE operate within a single subspace,
    or can it cross boundaries?

    Insert text at 1.1-1.3 and 1.5-1.7, then pivot with cuts at 1.1, 1.4, 2.1
    to attempt moving content from 1.x to 2.x.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert "ABC" at 1.1 (fills 1.1, 1.2, 1.3)
    session.insert(opened, Address(1, 1), ["ABC"])

    # Insert "DEF" at 1.5 (fills 1.5, 1.6, 1.7)
    session.insert(opened, Address(1, 5), ["DEF"])

    content_before = session.retrieve_contents(
        SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
    )

    vspanset_before = session.retrieve_vspanset(opened)

    # Attempt pivot with cuts at: 1.1, 1.4, 2.1
    # This would try to move content at [1.1, 1.4) forward by (2.1 - 1.4) = 0.7
    # Result: 1.1 + 0.7 = 1.8 (still in 1.x subspace)
    #
    # To actually cross into 2.x, content would need to move from below 2.0 to at or above 2.0
    # Let's try: cuts at 1.1, 1.4, 2.5
    # Offset would be 2.5 - 1.4 = 1.1
    # Content at 1.1-1.4 would move to 2.2-2.5 (crossing boundary!)
    try:
        session.pivot(opened, Address(1, 1), Address(1, 4), Address(2, 5))

        content_after = session.retrieve_contents(
            SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
        )

        # Also try retrieving from 2.x subspace explicitly
        content_2x = session.retrieve_contents(
            SpecSet(VSpec(opened, [Span(Address(2, 1), Offset(0, 10))]))
        )

        vspanset_after = session.retrieve_vspanset(opened)

        result_status = "succeeded"
    except Exception as e:
        result_status = f"failed: {e}"
        content_after = None
        content_2x = None
        vspanset_after = None

    session.close_document(opened)

    return {
        "name": "pivot_cross_subspace_boundary",
        "description": "Test whether REARRANGE can cross subspace boundaries (1.x to 2.x)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "ABC"},
            {"op": "insert", "address": "1.5", "text": "DEF"},
            {"op": "retrieve", "before": content_before},
            {"op": "vspanset_before", "result": str(vspanset_before)},
            {"op": "pivot_attempt",
             "cut1": "1.1",
             "cut2": "1.4",
             "cut3": "2.5",
             "status": result_status,
             "description": "Attempt to pivot ABC from 1.1-1.4 to 2.2-2.5 (crossing boundary)"},
            {"op": "retrieve_after_1x", "result": str(content_after) if content_after else "N/A"},
            {"op": "retrieve_after_2x", "result": str(content_2x) if content_2x else "N/A"},
            {"op": "vspanset_after", "result": str(vspanset_after) if vspanset_after else "N/A"}
        ]
    }


SCENARIOS = [
    ("rearrange", "pivot_adjacent_regions", scenario_pivot_adjacent_regions),
    ("rearrange", "pivot_word_swap", scenario_pivot_word_swap),
    ("rearrange", "pivot_single_char", scenario_pivot_single_char),
    ("rearrange", "swap_non_adjacent", scenario_swap_non_adjacent),
    ("rearrange", "swap_first_and_last", scenario_swap_first_and_last),
    ("rearrange", "swap_words_in_sentence", scenario_swap_words_in_sentence),
    ("rearrange", "pivot_preserves_identity", scenario_pivot_preserves_identity),
    ("rearrange", "swap_with_links", scenario_swap_with_links),
    ("rearrange", "double_pivot", scenario_double_pivot),
    ("rearrange", "pivot_cross_subspace_boundary", scenario_pivot_cross_subspace_boundary),
]
