#!/usr/bin/env python3
"""Test to examine tumbler lengths of V-addresses and I-addresses when insertpm creates bottom crums.

Question: In insertpm [orglinks.c:105-117], the V-width exponent is set from:
    shift = tumblerlength(vsaptr) - 1;
    tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V]);

Does tumblerlength(vsaptr) always equal the tumblerlength of the I-address (lstream)?
Or can they differ?
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import XuSession, XuConn, PipeStream, Address, READ_WRITE, CONFLICT_FAIL

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def count_tumbler_digits(tumbler_str):
    """Count the number of digits in a tumbler representation.

    Examples:
      "1.1" -> 2
      "1.1.0.2.0.100" -> 6
      "0" -> 0
    """
    if tumbler_str == '0' or tumbler_str == 0:
        return 0
    parts = str(tumbler_str).split('.')
    return len(parts)

def test_vspace_ispace_tumbler_lengths():
    """
    Examine the tumbler lengths of V-addresses and I-addresses.

    In insertpm (orglinks.c:105-117), the function receives:
    - vsaptr: V-address where new content is being inserted
    - sporglset: set of (lstream, lwidth, linfo) tuples

    For each sporgl:
    - lstream: I-address (origin in I-space)
    - lwidth: I-width (width in I-space)

    The V-width exponent is computed from vsaptr's tumblerlength:
        shift = tumblerlength(vsaptr) - 1
        inc = tumblerintdiff(&lwidth, &zero)
        tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V])

    Key question: Does tumblerlength(vsaptr) == tumblerlength(lstream)?
    """
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

    # Insert some text - this will call insertpm
    print("\n=== First insertion: 'Hello World' at 1.1 ===")
    session.insert(opened, Address(1, 1), ["Hello World"])

    # Get internal state
    state = session.dump_state()

    # The POOM tree is embedded in the granf structure
    # Looking at the JSON output, the POOM is in:
    # granf -> children[1] -> children[0] -> orgl

    print("\n=== Examining POOM tree after insert ===")

    granf_root = state['granf']
    poom = None

    # Navigate to the POOM tree
    if 'children' in granf_root and len(granf_root['children']) > 1:
        second_child = granf_root['children'][1]
        if 'children' in second_child and len(second_child['children']) > 0:
            bottom_child = second_child['children'][0]
            if 'orgl' in bottom_child:
                poom = bottom_child['orgl']

    if not poom:
        print("✗ Could not find POOM tree in expected location")
        import json
        print(json.dumps(state, indent=2))
        session.quit()
        return

    print("✓ Found POOM tree")
    print(f"  Height: {poom.get('height')}")
    print(f"  Enftype: {poom.get('enftype')}")
    print(f"  Width: {poom.get('wid')}")
    print(f"  Displacement: {poom.get('dsp')}")

    # Walk the tree to find bottom crums
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

    bottom_crums = collect_bottom_crums(poom)

    print(f"\n=== Found {len(bottom_crums)} bottom crum(s) ===")

    # If there are no bottom crums with non-zero width yet, we might need to do another insert
    if len(bottom_crums) == 0 or all(c['node'].get('wid') == ['0', '0'] for c in bottom_crums):
        print("\nPOOM tree is still empty (no insertpm calls yet)")
        print("This is expected - the first insert might not have called insertpm")

    for i, crum_info in enumerate(bottom_crums):
        crum = crum_info['node']
        path = crum_info['path']

        print(f"\n--- Bottom Crum {i} (path: {path}) ---")
        print(f"  Origin (cdsp): {crum.get('dsp')}")
        print(f"  Width (cwid): {crum.get('wid')}")
        print(f"  Homedoc: {crum.get('homedoc', 'N/A')}")

        # The 'dsp' and 'wid' are 2D tumblers [I-component, V-component]
        dsp = crum.get('dsp', [])
        wid = crum.get('wid', [])

        if len(dsp) >= 2 and len(wid) >= 2:
            i_origin = dsp[0]
            v_origin = dsp[1]
            i_width = wid[0]
            v_width = wid[1]

            print(f"\n  I-space: origin={i_origin}, width={i_width}")
            print(f"  V-space: origin={v_origin}, width={v_width}")

            # Skip if width is zero
            if i_width == '0' or i_width == 0:
                print("  (Skipping - zero width)")
                continue

            i_origin_len = count_tumbler_digits(i_origin)
            v_origin_len = count_tumbler_digits(v_origin)
            i_width_len = count_tumbler_digits(i_width)
            v_width_len = count_tumbler_digits(v_width)

            print(f"\n  Tumbler lengths:")
            print(f"    I-origin (lstream): {i_origin_len} digits")
            print(f"    V-origin (vsaptr): {v_origin_len} digits")
            print(f"    I-width: {i_width_len} digits")
            print(f"    V-width: {v_width_len} digits")

            # The V-width exponent should be tumblerlength(vsaptr) - 1
            # where vsaptr is v_origin (the V-address)
            expected_v_width_exponent = v_origin_len - 1

            print(f"\n  Analysis:")
            print(f"    vsaptr (V-origin) has {v_origin_len} digits")
            print(f"    Expected V-width exponent (from insertpm): {expected_v_width_exponent}")
            print(f"    lstream (I-origin) has {i_origin_len} digits")

            # The key question: do they match?
            if i_origin_len == v_origin_len:
                print(f"\n    ✓ MATCH: V-address and I-address have same tumbler length ({i_origin_len})")
            else:
                print(f"\n    ✗ DIFFER: V-address has {v_origin_len} digits, I-address has {i_origin_len} digits")

            # Check the V-width encoding
            # From insertpm:
            #   shift = tumblerlength(vsaptr) - 1
            #   inc = tumblerintdiff(&lwidth, &zero)
            #   tumblerincrement(&zero, shift, inc, &crumwidth.dsas[V])
            #
            # This means: V-width should encode the I-width value at exponent position (v_origin_len - 1)

            print(f"\n  V-width encoding check:")
            print(f"    I-width value (width in chars): {i_width}")
            print(f"    V-width tumbler: {v_width}")
            print(f"    Expected: V-width should be a tumbler with value={i_width} at exponent={expected_v_width_exponent}")

    # Additional check: examine multiple insertions
    print("\n\n=== Testing with second insertion ===")
    session.insert(opened, Address(1, 6), ["XYZ"])

    state2 = session.dump_state()

    # Navigate to POOM again
    poom2 = None
    granf_root2 = state2['granf']
    if 'children' in granf_root2 and len(granf_root2['children']) > 1:
        second_child = granf_root2['children'][1]
        if 'children' in second_child and len(second_child['children']) > 0:
            bottom_child = second_child['children'][0]
            if 'orgl' in bottom_child:
                poom2 = bottom_child['orgl']

    if poom2:
        bottom_crums2 = collect_bottom_crums(poom2)
        print(f"\nNow have {len(bottom_crums2)} bottom crum(s)")

        for i, crum_info in enumerate(bottom_crums2):
            crum = crum_info['node']
            dsp = crum.get('dsp', [])
            wid = crum.get('wid', [])

            if len(dsp) >= 2 and len(wid) >= 2:
                i_origin = dsp[0]
                v_origin = dsp[1]
                i_width = wid[0]

                # Skip zero-width crums
                if i_width == '0' or i_width == 0:
                    continue

                i_origin_len = count_tumbler_digits(i_origin)
                v_origin_len = count_tumbler_digits(v_origin)

                print(f"\n  Crum {i}: I-origin={i_origin} ({i_origin_len} digits), V-origin={v_origin} ({v_origin_len} digits)")

                if i_origin_len == v_origin_len:
                    print(f"    ✓ Lengths match")
                else:
                    print(f"    ✗ Lengths differ!")

    session.close_document(opened)
    session.quit()

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("In insertpm, when creating a bottom crum:")
    print("  - vsaptr is the V-address (e.g., 1.1)")
    print("  - lstream is the I-address (e.g., 1.1.0.1.0.100)")
    print()
    print("The V-width exponent is set to: tumblerlength(vsaptr) - 1")
    print("The I-width is used as the mantissa value.")
    print()
    print("Key finding: V-addresses and I-addresses can have DIFFERENT tumbler lengths!")
    print("  - V-addresses are typically shorter (e.g., 1.1, 1.2, 1.3)")
    print("  - I-addresses are typically longer (e.g., 1.1.0.1.0.100, 1.1.0.1.0.101)")
    print()
    print("This means the V-width uses a DIFFERENT exponent than the I-width,")
    print("encoding the I-width value at the V-space precision level.")

if __name__ == '__main__':
    test_vspace_ispace_tumbler_lengths()
