#!/usr/bin/env python3
"""Test to check what the POOM root crum's cdsp contains after inserting content."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import XuSession, XuConn, PipeStream, Address, READ_WRITE, CONFLICT_FAIL

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def test_poom_root_cdsp_after_insert():
    """
    Test what the POOM root crum's cdsp.dsas[V] contains after inserting text.

    The question: Does cdsp contain:
    - A relative V-offset like "0.1" (element-field offset)?
    - An absolute document-prefixed address like "1.1.0.1.0.1.0.1"?

    Based on code analysis:
    - credel.c:580 - cdsp is cleared to zero on crum creation
    - retrie.c:336 - prologuend computes grasp = offset + cdsp
    - retrie.c:356 - whereoncrum computes left = offset + cdsp

    This suggests cdsp is a RELATIVE offset within the tree, not an absolute address.
    """
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))

    session.account(Address(1, 1, 0, 1))
    docid = session.create_document()
    print(f"Created document: {docid}")

    # Open document for writing
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    print(f"Opened document: {opened}")

    # Insert some text at V-position 1.1
    session.insert(opened, Address(1, 1), ["HelloWorld"])
    print("Inserted 'HelloWorld' at V-position 1.1")

    # Retrieve the V-span to confirm insertion
    vspan = session.retrieve_vspanset(opened)
    print(f"Document V-span: {vspan}")

    # Dump internal state to examine the POOM tree
    state = session.dump_state()

    print("\n=== Searching for POOM tree ===")

    def find_poom_in_granf(node, depth=0):
        """Recursively search granf tree for POOM enfilade."""
        if node.get('enftype') == 'POOM':
            return node

        children = node.get('children', [])
        for child in children:
            if 'orgl' in child:
                return child['orgl']
            result = find_poom_in_granf(child, depth + 1)
            if result:
                return result
        return None

    poom_tree = find_poom_in_granf(state['granf'])

    if poom_tree:
        print("✓ Found POOM tree!")

        print("\n=== POOM Tree Root (Fullcrum) ===")
        print(f"  height: {poom_tree.get('height')}")
        print(f"  enftype: {poom_tree.get('enftype')}")
        print(f"  cwid (width): {poom_tree.get('wid')}")
        print(f"  cdsp (displacement): {poom_tree.get('dsp')}")

        # The critical question: what is cdsp.dsas[V]?
        cdsp = poom_tree.get('dsp', ['0', '0'])
        cwid = poom_tree.get('wid', ['0', '0'])

        print(f"\n=== Analysis ===")
        print(f"Root crum cdsp (full 2D): {cdsp}")
        print(f"Root crum cdsp[I] (I-dimension): {cdsp[0]}")
        print(f"Root crum cdsp[V] (V-dimension): {cdsp[1]}")
        print(f"Root crum cwid[V] (V-width): {cwid[1]}")

        # Check if cdsp[V] is relative or absolute
        if cdsp[1] == '0' or cdsp[1] == 0:
            print("\n✓ cdsp[V] is ZERO (0)")
            print("This suggests the root crum's V-displacement is ZERO,")
            print("meaning it represents V-space starting from V-position 0.")
        elif '.' in str(cdsp[1]) and str(cdsp[1]).count('.') == 1:
            print(f"\n✓ cdsp[V] is a RELATIVE offset: {cdsp[1]}")
            print("This is a short tumbler like '0.1' or '1.1',")
            print("representing an offset within the POOM tree.")
        else:
            print(f"\n? cdsp[V] has unexpected format: {cdsp[1]}")

        # Check children structure
        children = poom_tree.get('children', [])
        print(f"\n=== Children ({len(children)} total) ===")
        for i, child in enumerate(children):
            print(f"\nChild {i}:")
            print(f"  height: {child.get('height')}")
            print(f"  cdsp: {child.get('dsp')}")
            print(f"  cwid: {child.get('wid')}")
            if child.get('height') == 0:
                print(f"  homedoc: {child.get('homedoc', 'N/A')}")

        print("\n" + "="*70)
        print("CONCLUSION:")
        print("="*70)

        # The answer based on the code:
        print("\nBased on retrie.c:336 (prologuend):")
        print("  grasp = offset + cdsp")
        print("\nAnd retrie.c:356 (whereoncrum):")
        print("  left = offset + cdsp")
        print("\nThis arithmetic shows cdsp is a RELATIVE displacement,")
        print("not an absolute document-prefixed address.")
        print("\nThe root crum typically has cdsp = [0, 0], meaning:")
        print("  - It starts at the origin of its coordinate space")
        print("  - Children have non-zero cdsp values relative to parent")
        print("  - Absolute positions are computed by walking the tree")
        print("    and accumulating offsets")

    else:
        print("\n✗ Could not find POOM tree!")
        import json
        print(json.dumps(state, indent=2))

    session.close_document(opened)
    session.quit()

if __name__ == '__main__':
    test_poom_root_cdsp_after_insert()
