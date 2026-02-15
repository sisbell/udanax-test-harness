#!/usr/bin/env python3
"""Test: I-width arriving at insertpm is guaranteed to be 1-story.

This test verifies that when insertpm receives lwidth (the I-space width)
from a sporgl set, it is guaranteed to be a 1-story tumbler, i.e.,
mantissa[i] = 0 for all i > 0.

The construction chain is:
1. inserttextgr allocates I-addresses and computes width via tumblersub
2. The ispan width is copied directly to sporgl width
3. insertpm unpacks the sporgl to get lwidth

Since tumblersub is followed by tumblerjustify, and the width represents
a simple character count, the result should always be 1-story.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import XuSession, XuConn, PipeStream, Address, READ_WRITE, CONFLICT_FAIL

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def is_onestory_tumbler(tumbler_str):
    """Check if a tumbler is 1-story (only one non-zero digit).

    Examples of 1-story tumblers:
      "5" -> True (mantissa[0] = 5, rest are 0)
      "0.11" -> True (mantissa[0] = 11, rest are 0)
      "100" -> True (mantissa[0] = 100, rest are 0)

    Examples of multi-story tumblers:
      "1.1" -> False (mantissa[0] = 1, mantissa[1] = 1)
      "1.0.2" -> False (mantissa[0] = 1, mantissa[2] = 2)
    """
    if tumbler_str == '0' or tumbler_str == 0:
        return True  # Zero is trivially 1-story

    parts = str(tumbler_str).split('.')
    non_zero_parts = [p for p in parts if int(p) != 0]

    return len(non_zero_parts) <= 1

def collect_bottom_crums(node, path="root"):
    """Recursively collect all bottom crums (height=0)."""
    crums = []

    height = node.get('height', -1)
    if height == 0:
        crums.append({
            'path': path,
            'node': node
        })

    # Recurse to children
    for i, child in enumerate(node.get('children', [])):
        crums.extend(collect_bottom_crums(child, f"{path}/child[{i}]"))

    return crums

def test_iwidth_is_onestory():
    """Verify I-width is 1-story when it arrives at insertpm."""

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))

    # Account is required
    session.account(Address(1, 1, 0, 1))

    # Create a document
    docid = session.create_document()
    print(f"Created document: {docid}")

    # MUST open document before inserting
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    print(f"Opened document: {opened}")

    # Insert texts of different lengths to check I-width structure
    test_cases = [
        (["a"], "1 character"),
        (["Hello"], "5 characters"),
        (["x" * 50], "50 characters"),
        (["y" * 100], "100 characters"),
    ]

    all_onestory = True

    for text_list, description in test_cases:
        print(f"\n=== Inserting {description} ===")

        # Insert the text
        session.insert(opened, Address("1.1"), text_list)

        # Get internal state to examine POOM
        state = session.dump_state()

        # Navigate to the POOM tree
        granf_root = state.get('granf', {})
        poom = None

        if 'children' in granf_root and len(granf_root['children']) > 1:
            second_child = granf_root['children'][1]
            if 'children' in second_child and len(second_child['children']) > 0:
                bottom_child = second_child['children'][0]
                if 'orgl' in bottom_child:
                    poom = bottom_child['orgl']

        if not poom:
            print("✗ Could not find POOM tree")
            continue

        # Walk the POOM and collect bottom crums
        bottom_crums = collect_bottom_crums(poom)

        print(f"  Found {len(bottom_crums)} bottom crum(s)")

        for crum_info in bottom_crums:
            crum = crum_info['node']
            path = crum_info['path']

            # Extract I-width from the 2D tumbler
            wid = crum.get('wid', [])
            if len(wid) < 1:
                continue

            i_width = str(wid[0])

            # Skip zero-width crums
            if i_width == '0' or i_width == 0:
                continue

            if not is_onestory_tumbler(i_width):
                print(f"  ✗ FAIL: I-width is multi-story!")
                print(f"     Path: {path}")
                dsp = crum.get('dsp', [])
                if len(dsp) >= 1:
                    print(f"     I-origin: {dsp[0]}")
                print(f"     I-width: {i_width} <- NOT 1-story")
                all_onestory = False
            else:
                print(f"  ✓ I-width = {i_width} (1-story)")

    session.quit()

    if all_onestory:
        print("\n✓ SUCCESS: All I-widths are 1-story")
    else:
        print("\n✗ FAILURE: Some I-widths are multi-story")
        assert False, "I-width is not always 1-story"

if __name__ == '__main__':
    test_iwidth_is_onestory()
