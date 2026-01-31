"""Complex link pattern scenarios - chains, self-referential, overlapping targets."""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_self_referential_link(session):
    """Test creating a link within the same document (self-referential).

    The backend reportedly does not support internal links where source and target
    are in the same document. This test documents the actual behavior.
    """
    # Create a single document
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["See the glossary section below. Glossary: terms defined here."])
    # "glossary" at 9-16, "Glossary" at 33-40

    # Try to create a link from "glossary" to "Glossary" within same document
    link_source = SpecSet(VSpec(opened, [Span(Address(1, 9), Offset(0, 8))]))  # "glossary"
    link_target = SpecSet(VSpec(opened, [Span(Address(1, 33), Offset(0, 8))]))  # "Glossary"

    try:
        link_id = session.create_link(opened, link_source, link_target, SpecSet([JUMP_TYPE]))
        link_created = True
        error_msg = None

        # If it worked, try to follow it
        target_result = session.follow_link(link_id, LINK_TARGET)
        target_text = session.retrieve_contents(target_result)

        source_result = session.follow_link(link_id, LINK_SOURCE)
        source_text = session.retrieve_contents(source_result)
    except Exception as e:
        link_created = False
        link_id = None
        error_msg = str(e)
        target_text = []
        source_text = []

    session.close_document(opened)

    return {
        "name": "self_referential_link",
        "description": "Test creating a link within the same document (self-referential)",
        "operations": [
            {"op": "create_document", "result": str(doc)},
            {"op": "open_document", "doc": str(doc), "mode": "read_write", "result": str(opened)},
            {"op": "insert", "doc": str(opened), "address": "1.1",
             "text": "See the glossary section below. Glossary: terms defined here."},
            {"op": "create_link",
             "home_doc": str(opened),
             "source_text": "glossary",
             "target_text": "Glossary",
             "same_document": True,
             "type": "jump",
             "result": str(link_id) if link_id else None,
             "success": link_created,
             "error": error_msg,
             "comment": "Internal link - source and target in same document"},
            {"op": "follow_link",
             "link": str(link_id) if link_id else "none",
             "end": "target",
             "result": target_text} if link_created else {"op": "skipped", "reason": "link creation failed"},
            {"op": "follow_link",
             "link": str(link_id) if link_id else "none",
             "end": "source",
             "result": source_text} if link_created else {"op": "skipped", "reason": "link creation failed"}
        ]
    }


def scenario_link_chain(session):
    """Test link chains where a target document is also a source for another link.

    Creates A -> B -> C chain and tests following the entire chain.
    """
    # Create document A (starting point)
    doc_a = session.create_document()
    opened_a = session.open_document(doc_a, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_a, Address(1, 1), ["Start here to follow the chain"])

    # Create document B (middle - both target and source)
    doc_b = session.create_document()
    opened_b = session.open_document(doc_b, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_b, Address(1, 1), ["Middle document with next link"])

    # Create document C (end of chain)
    doc_c = session.create_document()
    opened_c = session.open_document(doc_c, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened_c, Address(1, 1), ["Final destination reached"])

    # Link A -> B: "here" in A links to "Middle" in B
    link_ab_source = SpecSet(VSpec(opened_a, [Span(Address(1, 7), Offset(0, 4))]))  # "here"
    link_ab_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 6))]))  # "Middle"
    link_ab = session.create_link(opened_a, link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # Link B -> C: "next" in B links to "Final" in C
    link_bc_source = SpecSet(VSpec(opened_b, [Span(Address(1, 22), Offset(0, 4))]))  # "next"
    link_bc_target = SpecSet(VSpec(opened_c, [Span(Address(1, 1), Offset(0, 5))]))  # "Final"
    link_bc = session.create_link(opened_b, link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # Follow link A -> B
    target_b = session.follow_link(link_ab, LINK_TARGET)
    target_b_text = session.retrieve_contents(target_b)

    # Find links from document B (should find link B -> C)
    search_b = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 35))]))
    links_from_b = session.find_links(search_b)

    # Follow the chain: if we found links from B, follow them
    if links_from_b:
        target_c = session.follow_link(links_from_b[0], LINK_TARGET)
        target_c_text = session.retrieve_contents(target_c)
    else:
        target_c_text = ["No links found from B"]

    # Also verify B is target of link from A AND source of link to C
    # Find links where B is target (reverse lookup)
    search_b_as_target = SpecSet(VSpec(opened_b, [Span(Address(1, 1), Offset(0, 35))]))
    links_to_b = session.find_links(NOSPECS, search_b_as_target)

    session.close_document(opened_a)
    session.close_document(opened_b)
    session.close_document(opened_c)

    return {
        "name": "link_chain",
        "description": "Test link chains: A -> B -> C where B is both target and source",
        "operations": [
            {"op": "create_document", "doc": "A", "result": str(doc_a)},
            {"op": "insert", "doc": "A", "text": "Start here to follow the chain"},
            {"op": "create_document", "doc": "B", "result": str(doc_b)},
            {"op": "insert", "doc": "B", "text": "Middle document with next link"},
            {"op": "create_document", "doc": "C", "result": str(doc_c)},
            {"op": "insert", "doc": "C", "text": "Final destination reached"},
            {"op": "create_link",
             "from": "A", "to": "B",
             "source_text": "here", "target_text": "Middle",
             "result": str(link_ab)},
            {"op": "create_link",
             "from": "B", "to": "C",
             "source_text": "next", "target_text": "Final",
             "result": str(link_bc)},
            {"op": "follow_link",
             "link": str(link_ab),
             "end": "target",
             "result": target_b_text,
             "comment": "Following A->B should give 'Middle'"},
            {"op": "find_links",
             "search_doc": "B",
             "result": [str(l) for l in links_from_b],
             "comment": "Find links originating from B (should find B->C)"},
            {"op": "follow_link",
             "link": str(links_from_b[0]) if links_from_b else "none",
             "end": "target",
             "result": target_c_text,
             "comment": "Following B->C should give 'Final'"},
            {"op": "find_links",
             "by": "target",
             "search_doc": "B",
             "result": [str(l) for l in links_to_b],
             "comment": "Find links targeting B (should find A->B)"}
        ]
    }


def scenario_overlapping_links_different_targets(session):
    """Test overlapping links on same content pointing to different targets.

    Multiple links with overlapping source spans but different target documents.
    """
    # Create source document with a term that has multiple meanings
    source_doc = session.create_document()
    source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(source_opened, Address(1, 1), ["The bank can refer to a financial institution or a river bank."])
    # First "bank" at 5-8, second "bank" at 55-58

    # Create target documents for different meanings
    finance_doc = session.create_document()
    finance_opened = session.open_document(finance_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(finance_opened, Address(1, 1), ["Financial institution: accepts deposits, makes loans."])

    geography_doc = session.create_document()
    geography_opened = session.open_document(geography_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(geography_opened, Address(1, 1), ["River bank: the land alongside a river."])

    # Create link from first "bank" to financial definition
    link1_source = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))  # first "bank"
    link1_target = SpecSet(VSpec(finance_opened, [Span(Address(1, 1), Offset(0, 21))]))  # "Financial institution"
    link1 = session.create_link(source_opened, link1_source, link1_target, SpecSet([JUMP_TYPE]))

    # Create link from SAME first "bank" to geography definition (overlapping!)
    link2_source = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))  # same "bank"
    link2_target = SpecSet(VSpec(geography_opened, [Span(Address(1, 1), Offset(0, 10))]))  # "River bank"
    link2 = session.create_link(source_opened, link2_source, link2_target, SpecSet([QUOTE_TYPE]))

    # Create link from second "bank" (river bank context) to geography
    link3_source = SpecSet(VSpec(source_opened, [Span(Address(1, 55), Offset(0, 4))]))  # second "bank"
    link3_target = SpecSet(VSpec(geography_opened, [Span(Address(1, 1), Offset(0, 10))]))  # "River bank"
    link3 = session.create_link(source_opened, link3_source, link3_target, SpecSet([JUMP_TYPE]))

    # Find links from the first "bank" - should find BOTH link1 and link2
    first_bank_search = SpecSet(VSpec(source_opened, [Span(Address(1, 5), Offset(0, 4))]))
    links_from_first_bank = session.find_links(first_bank_search)

    # Follow each link and compare
    link1_dest = session.follow_link(link1, LINK_TARGET)
    link1_text = session.retrieve_contents(link1_dest)

    link2_dest = session.follow_link(link2, LINK_TARGET)
    link2_text = session.retrieve_contents(link2_dest)

    # Find all links from document
    full_search = SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 65))]))
    all_links = session.find_links(full_search)

    session.close_document(source_opened)
    session.close_document(finance_opened)
    session.close_document(geography_opened)

    return {
        "name": "overlapping_links_different_targets",
        "description": "Test overlapping links on same content pointing to different targets",
        "operations": [
            {"op": "create_document", "doc": "source", "result": str(source_doc)},
            {"op": "insert", "doc": "source",
             "text": "The bank can refer to a financial institution or a river bank."},
            {"op": "create_document", "doc": "finance", "result": str(finance_doc)},
            {"op": "insert", "doc": "finance",
             "text": "Financial institution: accepts deposits, makes loans."},
            {"op": "create_document", "doc": "geography", "result": str(geography_doc)},
            {"op": "insert", "doc": "geography",
             "text": "River bank: the land alongside a river."},
            {"op": "create_link",
             "source_text": "bank (first)",
             "target_text": "Financial institution",
             "type": "jump",
             "result": str(link1)},
            {"op": "create_link",
             "source_text": "bank (first, same span)",
             "target_text": "River bank",
             "type": "quote",
             "result": str(link2),
             "comment": "Same source span as link1, different target and type"},
            {"op": "create_link",
             "source_text": "bank (second)",
             "target_text": "River bank",
             "type": "jump",
             "result": str(link3)},
            {"op": "find_links",
             "search_text": "first 'bank'",
             "result": [str(l) for l in links_from_first_bank],
             "comment": "Should find both link1 and link2 (overlapping sources)"},
            {"op": "follow_link",
             "link": str(link1),
             "end": "target",
             "result": link1_text,
             "comment": "Link1 should lead to finance definition"},
            {"op": "follow_link",
             "link": str(link2),
             "end": "target",
             "result": link2_text,
             "comment": "Link2 should lead to geography definition"},
            {"op": "find_links",
             "search_text": "full document",
             "result": [str(l) for l in all_links],
             "comment": "Should find all 3 links"}
        ]
    }


def scenario_link_chain_three_hops(session):
    """Test a longer link chain with 3 hops: A -> B -> C -> D.

    This tests programmatic link traversal and chain discovery.
    """
    # Create four documents
    docs = []
    handles = []
    texts = [
        "Document A: start your journey here",
        "Document B: continue to the next stop",
        "Document C: almost at the destination",
        "Document D: you have reached the end"
    ]

    for i, text in enumerate(texts):
        doc = session.create_document()
        opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
        session.insert(opened, Address(1, 1), [text])
        docs.append(doc)
        handles.append(opened)

    # Create link chain: A->B, B->C, C->D
    # A: "journey" (25-32) -> B: "Document" (1-8)
    link_ab_source = SpecSet(VSpec(handles[0], [Span(Address(1, 25), Offset(0, 7))]))
    link_ab_target = SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 8))]))
    link_ab = session.create_link(handles[0], link_ab_source, link_ab_target, SpecSet([JUMP_TYPE]))

    # B: "next" (25-28) -> C: "Document" (1-8)
    link_bc_source = SpecSet(VSpec(handles[1], [Span(Address(1, 25), Offset(0, 4))]))
    link_bc_target = SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 8))]))
    link_bc = session.create_link(handles[1], link_bc_source, link_bc_target, SpecSet([JUMP_TYPE]))

    # C: "destination" (22-32) -> D: "Document" (1-8)
    link_cd_source = SpecSet(VSpec(handles[2], [Span(Address(1, 22), Offset(0, 11))]))
    link_cd_target = SpecSet(VSpec(handles[3], [Span(Address(1, 1), Offset(0, 8))]))
    link_cd = session.create_link(handles[2], link_cd_source, link_cd_target, SpecSet([JUMP_TYPE]))

    # Follow the entire chain
    chain_results = []

    # Start at A, find link to B
    search_a = SpecSet(VSpec(handles[0], [Span(Address(1, 1), Offset(0, 40))]))
    links_from_a = session.find_links(search_a)
    chain_results.append({
        "step": "A",
        "links_found": [str(l) for l in links_from_a]
    })

    # Follow to B, find link to C
    if links_from_a:
        target_b = session.follow_link(links_from_a[0], LINK_TARGET)
        # Get the document from target_b specset to search for next link
        search_b = SpecSet(VSpec(handles[1], [Span(Address(1, 1), Offset(0, 40))]))
        links_from_b = session.find_links(search_b)
        chain_results.append({
            "step": "B",
            "links_found": [str(l) for l in links_from_b]
        })

        # Follow to C, find link to D
        if links_from_b:
            search_c = SpecSet(VSpec(handles[2], [Span(Address(1, 1), Offset(0, 40))]))
            links_from_c = session.find_links(search_c)
            chain_results.append({
                "step": "C",
                "links_found": [str(l) for l in links_from_c]
            })

            # Follow to D (end of chain)
            if links_from_c:
                target_d = session.follow_link(links_from_c[0], LINK_TARGET)
                target_d_text = session.retrieve_contents(target_d)
                chain_results.append({
                    "step": "D (end)",
                    "content": target_d_text
                })

    # Close all
    for h in handles:
        session.close_document(h)

    return {
        "name": "link_chain_three_hops",
        "description": "Test a longer link chain with 3 hops: A -> B -> C -> D",
        "operations": [
            {"op": "create_documents", "count": 4,
             "results": [str(d) for d in docs]},
            {"op": "insert_all", "texts": texts},
            {"op": "create_link", "from": "A", "to": "B",
             "source_text": "journey", "result": str(link_ab)},
            {"op": "create_link", "from": "B", "to": "C",
             "source_text": "next", "result": str(link_bc)},
            {"op": "create_link", "from": "C", "to": "D",
             "source_text": "destination", "result": str(link_cd)},
            {"op": "traverse_chain",
             "results": chain_results,
             "comment": "Following links A->B->C->D"}
        ]
    }


SCENARIOS = [
    # Link edge cases
    ("links", "self_referential_link", scenario_self_referential_link),
    ("links", "link_chain", scenario_link_chain),
    ("links", "overlapping_links_different_targets", scenario_overlapping_links_different_targets),
    ("links", "link_chain_three_hops", scenario_link_chain_three_hops),
]
