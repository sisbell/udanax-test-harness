"""Cross-document link chain scenarios - complex multi-hop link graphs.

Tests for:
- Circular link references (cycles)
- Diamond patterns (multiple paths to same destination)
- Star/hub patterns (many-to-one and one-to-many)
- Bidirectional explicit links
- Link chains combined with transclusion
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_circular_link_chain(session):
    """Test circular link references: A -> B -> C -> A.

    What happens when following links leads back to the starting point?
    Does the system detect cycles? Can we traverse indefinitely?
    """
    # Create three documents
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Document A: go to B"])

    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Document B: go to C"])

    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Document C: go to A"])

    # Create circular chain: A -> B -> C -> A
    # A: "go to B" links to B
    link_ab_source = SpecSet(VSpec(opened_a, [Span(Address(1, 14), Offset(0, 6))]))  # "go to B"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 10))]))  # "Document B"
    link_ab = session.create_link(opened_a, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # B: "go to C" links to C
    link_bc_source = SpecSet(VSpec(opened_b, [Span(Address(1, 14), Offset(0, 6))]))  # "go to C"
    link_bc_target = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 10))]))  # "Document C"
    link_bc = session.create_link(opened_b, link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # C: "go to A" links back to A (completing the cycle)
    link_ca_source = SpecSet(VSpec(opened_c, [Span(Address(1, 14), Offset(0, 6))]))  # "go to A"
    link_ca_target = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 10))]))  # "Document A"
    link_ca = session.create_link(opened_c, link_ca_source, link_ca_target, SpecSet([JUMP_TYPE]))

    # Traverse the cycle: start at A, follow links
    traversal = []

    # From A, find and follow link to B
    search_a = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_a = session.find_links(search_a)
    if links_from_a:
        target_b = session.follow_link(links_from_a[0], LINK_TARGET)
        target_b_text = session.retrieve_contents(target_b)
        traversal.append({"from": "A", "to": "B", "text": target_b_text})

    # From B, find and follow link to C
    search_b = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_b = session.find_links(search_b)
    if links_from_b:
        target_c = session.follow_link(links_from_b[0], LINK_TARGET)
        target_c_text = session.retrieve_contents(target_c)
        traversal.append({"from": "B", "to": "C", "text": target_c_text})

    # From C, find and follow link back to A
    search_c = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 20))]))
    links_from_c = session.find_links(search_c)
    if links_from_c:
        target_a = session.follow_link(links_from_c[0], LINK_TARGET)
        target_a_text = session.retrieve_contents(target_a)
        traversal.append({"from": "C", "to": "A (cycle complete)", "text": target_a_text})

    session.close_document(opened_a)
    session.close_document(opened_b)
    session.close_document(opened_c)

    return {
        "name": "circular_link_chain",
        "description": "Test circular link references: A -> B -> C -> A",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Document A: go to B"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Document B: go to C"},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Document C: go to A"},
            {"op": "create_link", "from": "A", "to": "B", "result": str(link_ab)},
            {"op": "create_link", "from": "B", "to": "C", "result": str(link_bc)},
            {"op": "create_link", "from": "C", "to": "A", "result": str(link_ca),
             "comment": "Completes the cycle"},
            {"op": "traverse_cycle",
             "traversal": traversal,
             "comment": "Following A->B->C->A should return to starting point"}
        ]
    }


def scenario_diamond_link_pattern(session):
    """Test diamond pattern: A -> B, A -> C, B -> D, C -> D.

    Multiple paths from A to D. Tests that both paths can be discovered
    and that D can be reached via either B or C.
    """
    # Create four documents in diamond shape
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Start: choose path B or path C"])

    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Path B: continue to destination"])

    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Path C: continue to destination"])

    doc_d = session.create_document()
    opened_d = session.open_document(doc_d, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_d, Address(1, 1), ["Destination: both paths lead here"])

    # A -> B: "path B" links to doc B
    link_ab_source = SpecSet(VSpec(opened_a, [Span(Address(1, 15), Offset(0, 6))]))  # "path B"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 6))]))   # "Path B"
    link_ab = session.create_link(opened_a, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # A -> C: "path C" links to doc C
    link_ac_source = SpecSet(VSpec(opened_a, [Span(Address(1, 25), Offset(0, 6))]))  # "path C"
    link_ac_target = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 6))]))   # "Path C"
    link_ac = session.create_link(opened_a, link_ac_source, link_ac_target, SpecSet([JUMP_TYPE]))

    # B -> D: "destination" links to doc D
    link_bd_source = SpecSet(VSpec(opened_b, [Span(Address(1, 22), Offset(0, 11))]))  # "destination"
    link_bd_target = SpecSet(VSpec(opened_d, [Span(Address(1, 1), Offset(0, 11))]))   # "Destination"
    link_bd = session.create_link(opened_b, link_bd_source, link_bd_target, SpecSet([JUMP_TYPE]))

    # C -> D: "destination" links to doc D
    link_cd_source = SpecSet(VSpec(opened_c, [Span(Address(1, 22), Offset(0, 11))]))  # "destination"
    link_cd_target = SpecSet(VSpec(opened_d, [Span(Address(1, 1), Offset(0, 11))]))   # "Destination"
    link_cd = session.create_link(opened_c, link_cd_source, link_cd_target, SpecSet([JUMP_TYPE]))

    # Find all links from A (should find 2: A->B and A->C)
    search_a = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_a = session.find_links(search_a)

    # Find all links targeting D (should find 2: B->D and C->D)
    search_d = SpecSet(VSpec(opened_d, [Span(Address(1, 1), Offset(0, 35))]))
    links_to_d = session.find_links(NOSPECS, search_d)

    # Traverse path A -> B -> D
    path_b_result = []
    if links_from_a:
        # Follow first link from A (to B)
        target_b = session.follow_link(link_ab, LINK_TARGET)
        target_b_text = session.retrieve_contents(target_b)
        path_b_result.append({"step": "A->B", "text": target_b_text})

        # Follow link from B to D
        target_d_via_b = session.follow_link(link_bd, LINK_TARGET)
        target_d_via_b_text = session.retrieve_contents(target_d_via_b)
        path_b_result.append({"step": "B->D", "text": target_d_via_b_text})

    # Traverse path A -> C -> D
    path_c_result = []
    target_c = session.follow_link(link_ac, LINK_TARGET)
    target_c_text = session.retrieve_contents(target_c)
    path_c_result.append({"step": "A->C", "text": target_c_text})

    target_d_via_c = session.follow_link(link_cd, LINK_TARGET)
    target_d_via_c_text = session.retrieve_contents(target_d_via_c)
    path_c_result.append({"step": "C->D", "text": target_d_via_c_text})

    session.close_document(opened_a)
    session.close_document(opened_b)
    session.close_document(opened_c)
    session.close_document(opened_d)

    return {
        "name": "diamond_link_pattern",
        "description": "Test diamond pattern: A -> B, A -> C, B -> D, C -> D",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "create_document", "doc": "D", "result": str(doc_d)},
            {"op": "create_link", "from": "A", "to": "B", "result": str(link_ab)},
            {"op": "create_link", "from": "A", "to": "C", "result": str(link_ac)},
            {"op": "create_link", "from": "B", "to": "D", "result": str(link_bd)},
            {"op": "create_link", "from": "C", "to": "D", "result": str(link_cd)},
            {"op": "find_links",
             "from": "A",
             "result": [str(l) for l in links_from_a],
             "expected_count": 2,
             "comment": "Should find links to both B and C"},
            {"op": "find_links",
             "to": "D",
             "result": [str(l) for l in links_to_d],
             "expected_count": 2,
             "comment": "Should find links from both B and C"},
            {"op": "traverse_path",
             "path": "A->B->D",
             "result": path_b_result},
            {"op": "traverse_path",
             "path": "A->C->D",
             "result": path_c_result,
             "comment": "Both paths should reach the same destination D"}
        ]
    }


def scenario_star_hub_incoming(session):
    """Test star/hub pattern with many documents linking TO one central hub.

    3 peripheral documents all link to 1 central document.
    Tests discovery of all incoming links to a hub.

    Note: Limited to 3 peripherals due to Bug 016 (link count limit).
    """
    # Create central hub document
    hub = session.create_document()
    hub_opened = session.open_document(hub, READ_WRITE, CONFLICT_FAIL)
    session.insert(hub_opened, Address(1, 1), ["Central Hub: all roads lead here"])

    # Create peripheral documents and links to hub
    peripherals = []
    peripheral_handles = []
    links_to_hub = []

    for i in range(3):  # Limited to 3 due to Bug 016
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [f"Peripheral {i}: link to hub"])
        peripherals.append(doc)
        peripheral_handles.append(opened)

        # Create link from this peripheral to hub
        # "link to hub" at position 15
        link_source = SpecSet(VSpec(opened, [Span(Address(1, 15), Offset(0, 11))]))  # "link to hub"
        link_target = SpecSet(VSpec(hub_opened, [Span(Address(1, 1), Offset(0, 11))]))  # "Central Hub"
        link_id = session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))
        links_to_hub.append(link_id)

    # Find all links targeting the hub
    hub_search = SpecSet(VSpec(hub_opened, [Span(Address(1, 1), Offset(0, 35))]))
    found_links_to_hub = session.find_links(NOSPECS, hub_search)

    # Follow each link backwards to find its source
    sources_found = []
    for link_id in found_links_to_hub:
        source_specs = session.follow_link(link_id, LINK_SOURCE)
        source_text = session.retrieve_contents(source_specs)
        sources_found.append({"link": str(link_id), "source_text": source_text})

    # Close all
    session.close_document(hub_opened)
    for h in peripheral_handles:
        session.close_document(h)

    return {
        "name": "star_hub_incoming",
        "description": "Test star/hub pattern: 3 peripherals all link TO central hub",
        "operations": [
            {"op": "create_document", "doc": "hub", "result": str(hub)},
            {"op": "insert", "doc": "hub", "text": "Central Hub: all roads lead here"},
            {"op": "create_documents", "doc": "peripherals", "count": 3,
             "results": [str(d) for d in peripherals]},
            {"op": "create_links", "from": "peripherals", "to": "hub",
             "results": [str(l) for l in links_to_hub]},
            {"op": "find_links",
             "to": "hub",
             "result": [str(l) for l in found_links_to_hub],
             "expected_count": 3,
             "comment": "Should find all 3 links pointing to hub"},
            {"op": "follow_links_to_sources",
             "results": sources_found,
             "comment": "Each link source should be a different peripheral"}
        ]
    }


def scenario_star_hub_outgoing(session):
    """Test star/hub pattern with one central document linking TO many others.

    1 central document links out to 3 peripheral documents.
    Tests discovery of all outgoing links from a hub.

    Note: Limited to 3 peripherals due to Bug 016 (link count limit).
    """
    # Create central hub document with multiple link anchors
    hub = session.create_document()
    hub_opened = session.open_document(hub, READ_WRITE, CONFLICT_FAIL)
    session.insert(hub_opened, Address(1, 1), ["Hub with links: ref1 ref2 ref3"])
    # ref1 at 18, ref2 at 23, ref3 at 28

    # Create peripheral documents
    peripherals = []
    peripheral_handles = []
    links_from_hub = []

    for i in range(3):  # Limited to 3 due to Bug 016
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [f"Target document number {i}"])
        peripherals.append(doc)
        peripheral_handles.append(opened)

        # Create link from hub to this peripheral
        # refN at position 18 + (i * 5)
        ref_pos = 18 + (i * 5)
        link_source = SpecSet(VSpec(hub_opened, [Span(Address(1, ref_pos), Offset(0, 4))]))
        link_target = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 15))]))  # "Target document"
        link_id = session.create_link(hub_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
        links_from_hub.append(link_id)

    # Find all links originating from hub
    hub_search = SpecSet(VSpec(hub_opened, [Span(Address(1, 1), Offset(0, 35))]))
    found_links_from_hub = session.find_links(hub_search)

    # Follow each link to find its target
    targets_found = []
    for link_id in found_links_from_hub:
        target_specs = session.follow_link(link_id, LINK_TARGET)
        target_text = session.retrieve_contents(target_specs)
        targets_found.append({"link": str(link_id), "target_text": target_text})

    # Close all
    session.close_document(hub_opened)
    for h in peripheral_handles:
        session.close_document(h)

    return {
        "name": "star_hub_outgoing",
        "description": "Test star/hub pattern: central hub links TO 3 peripherals",
        "operations": [
            {"op": "create_document", "doc": "hub", "result": str(hub)},
            {"op": "insert", "doc": "hub", "text": "Hub with links: ref1 ref2 ref3"},
            {"op": "create_documents", "doc": "peripherals", "count": 3,
             "results": [str(d) for d in peripherals]},
            {"op": "create_links", "from": "hub", "to": "peripherals",
             "results": [str(l) for l in links_from_hub]},
            {"op": "find_links",
             "from": "hub",
             "result": [str(l) for l in found_links_from_hub],
             "expected_count": 3,
             "comment": "Should find all 3 links from hub"},
            {"op": "follow_links_to_targets",
             "results": targets_found,
             "comment": "Each link target should be a different peripheral"}
        ]
    }


def scenario_bidirectional_explicit_links(session):
    """Test explicit bidirectional links: A <-> B.

    Create two documents with links in both directions.
    Unlike implicit backlinking, these are separate link objects.
    """
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Document A: see also Document B"])

    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Document B: see also Document A"])

    # Link A -> B: "Document B" in A links to B
    link_ab_source = SpecSet(VSpec(opened_a, [Span(Address(1, 22), Offset(0, 10))]))  # "Document B"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 10))]))   # "Document B"
    link_ab = session.create_link(opened_a, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # Link B -> A: "Document A" in B links to A
    link_ba_source = SpecSet(VSpec(opened_b, [Span(Address(1, 22), Offset(0, 10))]))  # "Document A"
    link_ba_target = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 10))]))   # "Document A"
    link_ba = session.create_link(opened_b, link_ba_source, link_ba_target, SpecSet([JUMP_TYPE]))

    # From A, find outgoing links (should find A->B)
    search_a = SpecSet(VSpec(opened_a, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_a = session.find_links(search_a)

    # From A, find incoming links (should find B->A)
    links_to_a = session.find_links(NOSPECS, search_a)

    # From B, find outgoing links (should find B->A)
    search_b = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_b = session.find_links(search_b)

    # From B, find incoming links (should find A->B)
    links_to_b = session.find_links(NOSPECS, search_b)

    # Verify we can navigate in both directions
    # A -> B
    target_b = session.follow_link(link_ab, LINK_TARGET)
    target_b_text = session.retrieve_contents(target_b)

    # B -> A
    target_a = session.follow_link(link_ba, LINK_TARGET)
    target_a_text = session.retrieve_contents(target_a)

    session.close_document(opened_a)
    session.close_document(opened_b)

    return {
        "name": "bidirectional_explicit_links",
        "description": "Test explicit bidirectional links: A <-> B (two separate links)",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Document A: see also Document B"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Document B: see also Document A"},
            {"op": "create_link", "from": "A", "to": "B", "result": str(link_ab)},
            {"op": "create_link", "from": "B", "to": "A", "result": str(link_ba)},
            {"op": "find_links",
             "from": "A", "direction": "outgoing",
             "result": [str(l) for l in links_from_a],
             "expected": [str(link_ab)]},
            {"op": "find_links",
             "to": "A", "direction": "incoming",
             "result": [str(l) for l in links_to_a],
             "expected": [str(link_ba)]},
            {"op": "find_links",
             "from": "B", "direction": "outgoing",
             "result": [str(l) for l in links_from_b],
             "expected": [str(link_ba)]},
            {"op": "find_links",
             "to": "B", "direction": "incoming",
             "result": [str(l) for l in links_to_b],
             "expected": [str(link_ab)]},
            {"op": "follow_link",
             "link": str(link_ab), "direction": "A->B",
             "result": target_b_text},
            {"op": "follow_link",
             "link": str(link_ba), "direction": "B->A",
             "result": target_a_text,
             "comment": "Both directions should work independently"}
        ]
    }


def scenario_link_chain_with_transclusion(session):
    """Test link chain where documents share content via transclusion.

    A -> B -> C, but B transcludes content from A.
    Does the link from B still work when B's content is transcluded?
    """
    # Create A with content
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Original content from A with link anchor"])
    session.close_document(opened_a)

    # Create B and transclude from A
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["B prefix: "])

    # Transclude "Original content from A" from doc A
    a_read = session.open_document(doc_a, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(a_read, [Span(Address(1, 1), Offset(0, 24))]))  # "Original content from A"
    b_vs = session.retrieve_vspanset(opened_b)
    session.vcopy(opened_b, b_vs.spans[0].end(), copy_spec)
    session.close_document(a_read)

    # Add more content to B after transcluded part
    b_vs2 = session.retrieve_vspanset(opened_b)
    session.insert(opened_b, b_vs2.spans[0].end(), [" and B's own link anchor"])

    # Get B's content to verify
    b_vs3 = session.retrieve_vspanset(opened_b)
    b_content = session.retrieve_contents(SpecSet(VSpec(opened_b, list(b_vs3.spans))))

    # Create C
    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Destination document C"])

    # Create link A -> B (using A's original content as source)
    # Need read-write handle for creating links
    a_write = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    link_ab_source = SpecSet(VSpec(a_write, [Span(Address(1, 30), Offset(0, 11))]))  # "link anchor"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 8))]))   # "B prefix"
    link_ab = session.create_link(a_write, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))
    session.close_document(a_write)

    # Create link B -> C (using B's own content, not transcluded part)
    # B's content is "B prefix: Original content from A and B's own link anchor"
    # "link anchor" is at the end
    b_vs4 = session.retrieve_vspanset(opened_b)
    b_end = b_vs4.spans[0].end()
    # Calculate position of "link anchor" in B - it's the last 11 chars
    link_bc_source = SpecSet(VSpec(opened_b, [Span(Address(1, 46), Offset(0, 11))]))  # "link anchor" in B
    link_bc_target = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 11))]))   # "Destination"
    link_bc = session.create_link(opened_b, link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # Traverse chain: A -> B -> C
    traversal = []

    # Follow A -> B
    target_b = session.follow_link(link_ab, LINK_TARGET)
    target_b_text = session.retrieve_contents(target_b)
    traversal.append({"step": "A->B", "text": target_b_text})

    # Find links from B
    search_b = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 60))]))
    links_from_b = session.find_links(search_b)

    # Follow B -> C
    target_c = session.follow_link(link_bc, LINK_TARGET)
    target_c_text = session.retrieve_contents(target_c)
    traversal.append({"step": "B->C", "text": target_c_text})

    # Also test: can we find links via the transcluded content in B?
    # Search for links where source is the transcluded "Original" text
    transcluded_search = SpecSet(VSpec(opened_b, [Span(Address(1, 11), Offset(0, 8))]))  # "Original" in B
    links_via_transcluded = session.find_links(transcluded_search)

    session.close_document(opened_b)
    session.close_document(opened_c)

    return {
        "name": "link_chain_with_transclusion",
        "description": "Test link chain where B transcludes content from A",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Original content from A with link anchor"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "vcopy", "from": "A", "to": "B", "text": "Original content from A"},
            {"op": "insert", "doc": "B", "text": " and B's own link anchor"},
            {"op": "contents", "doc": "B", "result": b_content},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "create_link", "from": "A", "to": "B",
             "source_text": "link anchor (in A)",
             "result": str(link_ab)},
            {"op": "create_link", "from": "B", "to": "C",
             "source_text": "link anchor (in B's own content)",
             "result": str(link_bc)},
            {"op": "traverse_chain",
             "traversal": traversal},
            {"op": "find_links",
             "via_transcluded_content": True,
             "result": [str(l) for l in links_via_transcluded],
             "comment": "Links found when searching via transcluded content in B"}
        ]
    }


def scenario_link_to_transcluded_content(session):
    """Test creating a link where the target is transcluded content.

    A transcludes from B. C links to the transcluded content in A.
    Does the link follow the content identity back to B?
    """
    # Create B (source of transcluded content)
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Source content in B: important text here"])
    session.close_document(opened_b)

    # Create A and transclude from B
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["A contains: "])

    b_read = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    copy_spec = SpecSet(VSpec(b_read, [Span(Address(1, 22), Offset(0, 14))]))  # "important text"
    a_vs = session.retrieve_vspanset(opened_a)
    session.vcopy(opened_a, a_vs.spans[0].end(), copy_spec)
    session.close_document(b_read)

    # Get A's content
    a_vs2 = session.retrieve_vspanset(opened_a)
    a_content = session.retrieve_contents(SpecSet(VSpec(opened_a, list(a_vs2.spans))))

    # Create C with a link to the transcluded content in A
    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["C references: see the important text"])

    # Link from C to transcluded "important text" in A
    link_source = SpecSet(VSpec(opened_c, [Span(Address(1, 19), Offset(0, 14))]))  # "important text" in C
    link_target = SpecSet(VSpec(opened_a, [Span(Address(1, 13), Offset(0, 14))]))  # transcluded in A
    link_ca = session.create_link(opened_c, link_source, link_target, SpecSet([JUMP_TYPE]))

    # Follow the link
    target_in_a = session.follow_link(link_ca, LINK_TARGET)
    target_in_a_text = session.retrieve_contents(target_in_a)

    # Key question: If we search for links targeting B's original content,
    # do we find this link? (Since A's content shares identity with B)
    b_read2 = session.open_document(doc_b, READ_ONLY, CONFLICT_COPY)
    search_b_content = SpecSet(VSpec(b_read2, [Span(Address(1, 22), Offset(0, 14))]))  # "important text" in B
    links_to_b_content = session.find_links(NOSPECS, search_b_content)
    session.close_document(b_read2)

    # And vice versa: links targeting A's transcluded content
    search_a_content = SpecSet(VSpec(opened_a, [Span(Address(1, 13), Offset(0, 14))]))
    links_to_a_content = session.find_links(NOSPECS, search_a_content)

    session.close_document(opened_a)
    session.close_document(opened_c)

    return {
        "name": "link_to_transcluded_content",
        "description": "Test link where target is transcluded content (shared identity)",
        "operations": [
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Source content in B: important text here"},
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "vcopy", "from": "B", "to": "A", "text": "important text"},
            {"op": "contents", "doc": "A", "result": a_content},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "C references: see the important text"},
            {"op": "create_link",
             "from": "C", "to": "A (transcluded content)",
             "source_text": "important text",
             "target_text": "important text (transcluded from B)",
             "result": str(link_ca)},
            {"op": "follow_link",
             "link": str(link_ca),
             "result": target_in_a_text},
            {"op": "find_links",
             "to": "B's original content",
             "result": [str(l) for l in links_to_b_content],
             "comment": "Does link to A's transcluded content appear when searching B?"},
            {"op": "find_links",
             "to": "A's transcluded content",
             "result": [str(l) for l in links_to_a_content],
             "comment": "Links targeting A's transcluded content"}
        ]
    }


def scenario_multi_hop_reverse_traversal(session):
    """Test reverse traversal of a link chain.

    Given A -> B -> C -> D, start at D and find path back to A
    using target-based link search.
    """
    # Create chain of 4 documents
    docs = []
    handles = []
    texts = [
        "Doc A: starting point",
        "Doc B: first hop",
        "Doc C: second hop",
        "Doc D: final destination"
    ]

    for text in texts:
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [text])
        docs.append(doc)
        handles.append(opened)

    # Create forward chain: A->B, B->C, C->D
    # A: "point" -> B: "Doc B"
    link_ab = session.create_link(
        handles[0],
        SpecSet(VSpec(handles[0], [Span(Address(1, 16), Offset(0, 5))])),  # "point"
        SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 5))])),   # "Doc B"
        SpecSet([JUMP_TYPE])
    )

    # B: "hop" -> C: "Doc C"
    link_bc = session.create_link(
        handles[1],
        SpecSet(VSpec(handles[1], [Span(Address(1, 14), Offset(0, 3))])),  # "hop"
        SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 5))])),   # "Doc C"
        SpecSet([JUMP_TYPE])
    )

    # C: "hop" -> D: "Doc D"
    link_cd = session.create_link(
        handles[2],
        SpecSet(VSpec(handles[2], [Span(Address(1, 15), Offset(0, 3))])),  # "hop"
        SpecSet(VSpec(handles[3], [Span(Address(1, 1), Offset(0, 5))])),   # "Doc D"
        SpecSet([JUMP_TYPE])
    )

    # Now traverse BACKWARDS from D to A
    reverse_path = []

    # Start at D, find links targeting D
    search_d = SpecSet(VSpec(handles[3], [Span(Address(1, 1), Offset(0, 25))]))
    links_to_d = session.find_links(NOSPECS, search_d)
    if links_to_d:
        source_c = session.follow_link(links_to_d[0], LINK_SOURCE)
        source_c_text = session.retrieve_contents(source_c)
        reverse_path.append({"at": "D", "found_link_from": "C", "text": source_c_text})

    # At C, find links targeting C
    search_c = SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 20))]))
    links_to_c = session.find_links(NOSPECS, search_c)
    if links_to_c:
        source_b = session.follow_link(links_to_c[0], LINK_SOURCE)
        source_b_text = session.retrieve_contents(source_b)
        reverse_path.append({"at": "C", "found_link_from": "B", "text": source_b_text})

    # At B, find links targeting B
    search_b = SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 20))]))
    links_to_b = session.find_links(NOSPECS, search_b)
    if links_to_b:
        source_a = session.follow_link(links_to_b[0], LINK_SOURCE)
        source_a_text = session.retrieve_contents(source_a)
        reverse_path.append({"at": "B", "found_link_from": "A", "text": source_a_text})

    # At A, find links targeting A (should be none - it's the start)
    search_a = SpecSet(VSpec(handles[0], [Span(Address(1, 1), Offset(0, 25))]))
    links_to_a = session.find_links(NOSPECS, search_a)
    reverse_path.append({"at": "A", "links_found": len(links_to_a), "comment": "Start of chain"})

    for h in handles:
        session.close_document(h)

    return {
        "name": "multi_hop_reverse_traversal",
        "description": "Test reverse traversal: starting at D, find path back to A",
        "operations": [
            {"op": "create_documents", "count": 4, "results": [str(d) for d in docs]},
            {"op": "create_link", "A->B": str(link_ab)},
            {"op": "create_link", "B->C": str(link_bc)},
            {"op": "create_link", "C->D": str(link_cd)},
            {"op": "reverse_traversal",
             "start": "D",
             "end": "A",
             "path": reverse_path,
             "comment": "Should find D<-C<-B<-A by following link sources"}
        ]
    }


SCENARIOS = [
    ("links", "circular_link_chain", scenario_circular_link_chain),
    ("links", "diamond_link_pattern", scenario_diamond_link_pattern),
    ("links", "star_hub_incoming", scenario_star_hub_incoming),
    ("links", "star_hub_outgoing", scenario_star_hub_outgoing),
    ("links", "bidirectional_explicit_links", scenario_bidirectional_explicit_links),
    ("links", "link_chain_with_transclusion", scenario_link_chain_with_transclusion),
    ("links", "link_to_transcluded_content", scenario_link_to_transcluded_content),
    ("links", "multi_hop_reverse_traversal", scenario_multi_hop_reverse_traversal),
]
