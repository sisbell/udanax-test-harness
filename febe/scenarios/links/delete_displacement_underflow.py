"""Test scenarios to reveal displacement underflow in DELETE case-2 shift.

The defect is in edit.c:63 where case-2 root children have the deletion
width subtracted from their V-displacement via tumblersub:

    case 2:
        tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);

This test explores when a child's displacement (dsp_V) can be less than
the deletion width (w), causing negative displacement.

Key insight from newfindintersectionnd (ndinters.c:38-42):
    *ptrptr = fullcrumptr;
    clear(offset, sizeof(*offset));

The "intersection node" is ALWAYS the root (fullcrum). The shift operates
on the root's children, not on some deeper intersection node.
"""

from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL,
    LINK_SOURCE, LINK_TARGET,
    JUMP_TYPE,
    NOSPECS
)
from ..common import vspec_to_dict, span_to_dict, specset_to_list


def scenario_delete_at_root_origin_height_1(session):
    """Height-1 tree: root child at displacement 1.1.

    Tree structure:
        root (height=1)
        └── child at dsp=1.1, wid=0.15

    DELETE 1.1 + 0.15 (entire content).

    For the child to be case-2 (after the deletion range), we need:
        grasp_V >= v + w
        where v = origin = 1.1
              w = width = 0.15
              grasp_V = child's absolute position = root_offset + child_dsp = 0 + 1.1 = 1.1

    So: 1.1 >= 1.1 + 0.15 ? NO.

    This child is NOT case-2; it's case-1 (inside deletion range).

    To get case-2 in height-1, we need content AFTER the deletion range.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert 15 bytes at 1.1
    session.insert(opened, Address(1, 1), ["123456789012345"])

    # Insert MORE content at 1.16 (after the first block)
    session.insert(opened, Address(1, 16), ["ABCDEFGHIJKLMNO"])

    # Create link from second block
    source_span = Span(Address(1, 16), Offset(0, 5))
    target_span = Span(Address(1, 20), Offset(0, 5))
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    vspan_before = session.retrieve_vspanset(opened)
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # DELETE first 15 bytes at 1.1 (width = 0.15)
    # The second block (starting at 1.16) should be case-2 (after deletion range)
    # Its displacement is 1.16, deletion width is 0.15
    # dsp_V (1.16) > w (0.15), so no underflow in height-1
    session.delete(opened, Address(1, 1), Offset(0, 15))

    vspan_after = session.retrieve_vspanset(opened)
    endsets_after = session.follow_link(link_id, LINK_SOURCE)

    session.close_document(opened)

    return {
        "name": "delete_at_root_origin_height_1",
        "description": "Height-1 tree: case-2 child displacement >= deletion width",
        "operations": [
            {"op": "insert", "at": "1.1", "text": "123456789012345", "note": "15 bytes"},
            {"op": "insert", "at": "1.16", "text": "ABCDEFGHIJKLMNO", "note": "15 more bytes"},
            {"op": "create_link", "source": "1.16-1.20", "target": "1.20-1.24", "result": str(link_id)},
            {"op": "vspan_before", "result": vspec_to_dict(vspan_before)},
            {"op": "endsets_before", "result": specset_to_list(endsets_before)},
            {"op": "delete", "start": "1.1", "width": "0.15", "note": "Delete first block"},
            {"op": "vspan_after", "result": vspec_to_dict(vspan_after), "note": "Second block should shift to 1.1"},
            {"op": "endsets_after", "result": specset_to_list(endsets_after), "note": "Link endsets should shift by -0.15"}
        ],
        "analysis": {
            "tree_height": 1,
            "case_2_child_dsp": "1.16",
            "deletion_width": "0.15",
            "underflow": "NO - dsp (1.16) > w (0.15)"
        }
    }


def scenario_delete_deeper_tree_child_at_zero(session):
    """Deeper tree (height > 1): root child at displacement 0.

    Tree structure (hypothetical after levelpush):
        root (height=2)
        ├── left_child at dsp=0, wid=0.15
        └── right_child at dsp=0.15, wid=0.15

    If we DELETE origin=0.10, width=0.20:
        - Deletion range: [0.10, 0.30]
        - left_child grasp: 0 + 0 = 0
        - right_child grasp: 0 + 0.15 = 0.15

    For right_child:
        whereoncrum(right_child, grasp=0.15, blade[1]=0.30) returns ONMYLEFTBORDER or TOMYLEFT
        → deletecutsectionnd classifies as case-2 (return 2)
        → tumblersub(dsp=0.15, width=0.20, result) → result = -0.5 (NEGATIVE!)

    For left_child:
        whereoncrum(left_child, grasp=0, blade[0]=0.10) returns ONMYLEFTBORDER or TOMYLEFT
        whereoncrum(left_child, grasp=0, blade[1]=0.30) returns ... ?
        If blade[1] is ONMYRIGHTBORDER or TOMYRIGHT, then case-1 (inside deletion).

    Problem: We can't easily force a height-2 tree through FEBE.
    The tree structure is determined by backend splitting logic.

    Instead, test a scenario where deletion width exceeds all content.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert small amount of content
    session.insert(opened, Address(1, 1), ["ABC"])  # 3 bytes at 1.1-1.3

    # Create link
    source_span = Span(Address(1, 1), Offset(0, 2))
    target_span = Span(Address(1, 2), Offset(0, 1))
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    vspan_before = session.retrieve_vspanset(opened)
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # DELETE with width LARGER than all content (width=0.100)
    # Content ends at 1.3, but we delete up to 1.101
    # Link is at 2.something (let's say 2.1)
    # If link's dsp_V is small (e.g., 2.1 - 1.1 = 1.0 in some coordinate system),
    # and deletion width is 0.100, then dsp < w → UNDERFLOW
    #
    # Wait, that's wrong. Link displacement is in its own subspace coordinate.
    # Let me reconsider...
    #
    # Actually, in the POOM tree, the link entry has:
    #   - V-dimension displacement: some value relative to root origin
    #   - Root origin is typically (0, 0) in multi-dimensional space
    #
    # The DELETE operation uses index (dimension) to specify which dimension to shift.
    # For text content (dimension 0), we shift dimension 0.
    # For links (dimension 1), they are in a separate dimension.
    #
    # Hmm, but Finding 053 shows that links DO shift when text is deleted.
    # That means the dimension indexing is MORE COMPLEX than I thought.
    #
    # Let me re-read edit.c:63:
    #     tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);
    #
    # So it's shifting cdsp.dsas[index], where index is the deletion dimension.
    # If index=0 (V-dimension), it shifts the V-component of the displacement.
    #
    # For a POOM entry representing a link:
    #   - The link's V-position is (2, position)
    #   - Its displacement dsas[0] is the FULL V-position, not just dimension-0
    #   - Wait, no. dsas is indexed by dimension for multi-dimensional tumblers.
    #
    # I need to understand the tumbler structure better.
    pass


def scenario_delete_width_larger_than_content(session):
    """Test DELETE with width larger than all content.

    Setup:
        - Text at 1.1-1.5 (5 bytes)
        - Link at 2.1 (first link position)

    Action:
        - DELETE 1.1 + 0.100 (100 bytes, but only 5 exist)

    Question: Does the backend allow deleting more than exists?
    What happens to link positions?

    Prediction:
        - DELETE might fail or clip to actual content width
        - If it succeeds, link at 2.1 would shift by -0.100
        - Link's new position: 2.1 - 0.100 = 2.(-99) → NEGATIVE
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    session.insert(opened, Address(1, 1), ["ABCDE"])  # 5 bytes

    source_span = Span(Address(1, 1), Offset(0, 2))
    target_span = Span(Address(1, 3), Offset(0, 2))
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    vspan_before = session.retrieve_vspanset(opened)
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # Try to DELETE 100 bytes (way more than exists)
    delete_succeeded = True
    delete_error = None
    try:
        session.delete(opened, Address(1, 1), Offset(0, 100))
    except Exception as e:
        delete_succeeded = False
        delete_error = str(e)

    vspan_after = session.retrieve_vspanset(opened)

    endsets_after = None
    follow_succeeded = True
    follow_error = None
    try:
        endsets_after = session.follow_link(link_id, LINK_SOURCE)
    except Exception as e:
        follow_succeeded = False
        follow_error = str(e)

    session.close_document(opened)

    return {
        "name": "delete_width_larger_than_content",
        "description": "DELETE with width > all content to trigger underflow",
        "operations": [
            {"op": "insert", "at": "1.1", "text": "ABCDE", "note": "5 bytes"},
            {"op": "create_link", "source": "1.1-1.2", "target": "1.3-1.4", "result": str(link_id)},
            {"op": "vspan_before", "result": vspec_to_dict(vspan_before)},
            {"op": "endsets_before", "result": specset_to_list(endsets_before)},
            {"op": "delete",
             "start": "1.1",
             "width": "0.100",
             "succeeded": delete_succeeded,
             "error": delete_error,
             "note": "Try to delete 100 bytes (only 5 exist)"},
            {"op": "vspan_after", "result": vspec_to_dict(vspan_after)},
            {"op": "follow_link",
             "result": specset_to_list(endsets_after) if follow_succeeded else None,
             "succeeded": follow_succeeded,
             "error": follow_error,
             "note": "If link shifted by -0.100, position would be negative"}
        ],
        "analysis": {
            "hypothesis": "DELETE clips to actual content width, OR shifts by full requested width",
            "underflow_trigger": "If shift by -0.100, link at 2.1 → 2.(-99) negative"
        }
    }


def scenario_delete_from_middle_affects_later_links(session):
    """Test DELETE from middle of content with link positioned after.

    Setup:
        - Text "AAAAAAAAAA" at 1.1-1.10 (10 bytes)
        - Text "BBBBBBBBBB" at 1.11-1.20 (10 bytes)
        - Link from second block: 1.15-1.17 → (somewhere)

    Action:
        - DELETE 1.5 + 0.10 (delete 10 bytes in middle)

    Analysis:
        - Deletion range: [1.5, 1.15]
        - Link source starts at 1.15 (right at deletion end)
        - Is link case-1 (inside) or case-2 (after)?

        From deletecutsectionnd (edit.c:235-248):
            for (i = knives->nblades-1; i >= 0; --i) {
                cmp = whereoncrum(ptr, offset, &knives->blades[i], knives->dimension);
                if (cmp == THRUME) {
                    return (-1);  // Error: blade cuts through this crum
                } else if (cmp <= ONMYLEFTBORDER) {
                    return (i+1);
                }
            }
            return (0);

        Knives has 2 blades: [0]=1.5 (start), [1]=1.15 (end)
        Loop checks blade[1] first (i=1).

        For a crum at 1.15:
            whereoncrum(crum, offset, blade[1]=1.15, V)
            If crum starts exactly at 1.15: ONMYLEFTBORDER or TOMYLEFT?
            → Depends on whether "at" means THRUME or ONMYLEFTBORDER

        If ONMYLEFTBORDER: cmp <= ONMYLEFTBORDER → return (1+1) = 2 (case-2)
        If TOMYLEFT: cmp <= ONMYLEFTBORDER → return (1+1) = 2 (case-2)

        So the link IS case-2, and its displacement is shifted by -0.10.

        Question: What is the link's displacement in the tree?
        - If link is at V-position 2.1 (first link), its absolute V-address is 2.1
        - Root offset is 0
        - Link's displacement relative to root: 2.1 - 0 = 2.1

        Shift: 2.1 - 0.10 = 2.0 (NOT negative, still valid)

        To get negative, we need link displacement < deletion width.
        For that, we need a link very early in its subspace (like 2.1)
        AND a large deletion width (> 2.1 in tumbler arithmetic).

        But wait: deletion width is in dimension V (text dimension), not link dimension.
        Are they compared directly?

        Let me re-examine edit.c:63:
            tumblersub(&ptr->cdsp.dsas[index], width, &ptr->cdsp.dsas[index]);

        where index is the deletion dimension (for text DELETE, index=0 for V-dimension).

        So it subtracts width->dsas[0] from ptr->cdsp.dsas[0].

        For a POOM link entry:
            - ptr->cdsp is a multi-dimensional displacement
            - dsas[0] is the V-dimension component
            - For a link at V-position 2.1, dsas[0] might be 2.1

        And width for text deletion is (0, width_in_text_dimension).
        So width->dsas[0] is the text width (e.g., 0.10).

        Subtracting: 2.1 - 0.10 = 2.0 (still positive).

        To get negative: need link V-position < deletion width.
        Example: link at 2.1, delete width 0.15:
            2.1 - 0.15 = 1.95 (still positive)

        Wait, 2.1 in tumbler notation is (mantissa=[2,1], exp=0).
        And 0.15 is (mantissa=[1,5], exp=-1).

        Tumbler subtraction: 2.1 - 0.15 = ?
        Convert to same exponent:
            2.1 = 2.10 (exp=-1)
            0.15 = 0.15 (exp=-1)
            Result = 1.95 (exp=-1) = 1.95

        So yes, still positive.

        To get negative:
            Link at 2.1, delete width 3.0:
            2.1 - 3.0 = -0.9 (NEGATIVE!)

        But can we delete 3.0 (30 bytes) of text to trigger this?
        Yes, if we have enough content.
    """
    doc = session.create_document()
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)

    # Insert 30 bytes at 1.1-1.30
    session.insert(opened, Address(1, 1), ["A" * 30])

    # Create link (will be at 2.1)
    source_span = Span(Address(1, 10), Offset(0, 5))
    target_span = Span(Address(1, 20), Offset(0, 5))
    source_specs = SpecSet(VSpec(opened, [source_span]))
    target_specs = SpecSet(VSpec(opened, [target_span]))
    link_id = session.create_link(opened, source_specs, target_specs, SpecSet([JUMP_TYPE]))

    vspan_before = session.retrieve_vspanset(opened)
    endsets_before = session.follow_link(link_id, LINK_SOURCE)

    # DELETE 30 bytes at 1.1 (all text)
    # Link at 2.1 should shift by -0.30
    # Result: 2.1 - 0.30 = 1.80 (still positive)
    #
    # Hmm, need larger deletion width relative to link position.
    # Can't get negative unless link position digit < deletion width digit.
    #
    # Example: link at 2.1, delete width 5.0:
    # 2.1 - 5.0 = -2.9 (NEGATIVE!)
    #
    # But can we delete 5.0 (50 bytes)?
    # Let's try deleting 25 bytes (width 0.25):
    # 2.1 - 0.25 = 1.85 (positive)
    #
    # Need link at smaller position OR larger deletion.
    # What if link is at 2.01 (second link, assuming links take 0.01 width)?
    # Then 2.01 - 0.25 = 1.76 (still positive)
    #
    # Conclusion: To trigger negative, need:
    #     link_position_digit < deletion_width_digit
    # Example: link at 2.1, delete width 3.0 or more
    #     2.1 - 3.0 = -0.9 (NEGATIVE)

    # Let's delete 25 bytes and check:
    session.delete(opened, Address(1, 1), Offset(0, 25))

    vspan_after = session.retrieve_vspanset(opened)
    endsets_after = session.follow_link(link_id, LINK_SOURCE)

    session.close_document(opened)

    return {
        "name": "delete_from_middle_affects_later_links",
        "description": "DELETE 25 bytes, link at 2.1 shifts to 1.85 (still positive)",
        "operations": [
            {"op": "insert", "at": "1.1", "text": "A" * 30, "note": "30 bytes"},
            {"op": "create_link", "source": "1.10-1.14", "target": "1.20-1.24", "result": str(link_id)},
            {"op": "vspan_before", "result": vspec_to_dict(vspan_before)},
            {"op": "endsets_before", "result": specset_to_list(endsets_before)},
            {"op": "delete", "start": "1.1", "width": "0.25", "note": "Delete 25 bytes"},
            {"op": "vspan_after", "result": vspec_to_dict(vspan_after), "note": "Link should shift from 2.1 to 1.85"},
            {"op": "endsets_after", "result": specset_to_list(endsets_after)}
        ],
        "analysis": {
            "link_position": "2.1",
            "deletion_width": "0.25",
            "expected_shift": "2.1 - 0.25 = 1.85",
            "underflow": "NO"
        }
    }


SCENARIOS = [
    ("links", "delete_at_root_origin_height_1", scenario_delete_at_root_origin_height_1),
    ("links", "delete_width_larger_than_content", scenario_delete_width_larger_than_content),
    ("links", "delete_from_middle_affects_later_links", scenario_delete_from_middle_affects_later_links),
]
