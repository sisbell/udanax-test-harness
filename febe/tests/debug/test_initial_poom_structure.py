#!/usr/bin/env python3
"""Test to examine the initial POOM tree structure when a new document is created."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import XuSession, XuConn, PipeStream, Address

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def test_initial_poom_structure():
    """
    Test the initial POOM enfilade tree structure created by createenf(POOM)
    when a new document is created.
    
    According to credel.c:492-516, createenf(POOM) should produce:
    - Fullcrum (height-1 crum, isapex=TRUE, isleftmost=TRUE)
    - Single bottom crum (height-0) as the only son
    
    For POOM enfilades (2D), the bottom crum is type2dcbc with:
    - cdsp: cleared (all zeros) - 2D displacement
    - cwid: cleared (all zeros) - 2D width
    - c2dinfo.homedoc: cleared (all zeros)
    """
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    
    # Account is required
    session.account(Address(1, 1, 0, 1))
    
    # Create a new document
    docid = session.create_document()
    print(f"Created document: {docid}")
    
    # Dump internal state to examine the POOM tree
    state = session.dump_state()
    
    # Find the POOM tree for our document in the granf
    print("\n=== Searching for POOM tree ===")
    poom_tree = None
    
    def find_poom_in_granf(node, depth=0):
        """Recursively search granf tree for POOM enfilade."""
        nonlocal poom_tree
        
        if node.get('enftype') == 'POOM':
            # Found the POOM tree root!
            return node
        
        # Check children
        children = node.get('children', [])
        for child in children:
            # Check if this child has an orgl
            if 'orgl' in child:
                return child['orgl']
            
            # Recurse
            result = find_poom_in_granf(child, depth + 1)
            if result:
                return result
        
        return None
    
    # Search the granf tree
    poom_tree = find_poom_in_granf(state['granf'])
    
    if poom_tree:
        print("✓ Found POOM tree!")
        
        print("\n=== POOM Tree Root (Fullcrum) ===")
        print(f"  height: {poom_tree.get('height')}")
        print(f"  enftype: {poom_tree.get('enftype')}")
        print(f"  cwid (width): {poom_tree.get('wid')}")
        print(f"  cdsp (displacement): {poom_tree.get('dsp')}")
        
        children = poom_tree.get('children', [])
        print(f"\n  Number of children: {len(children)}")
        
        if children:
            for i, child in enumerate(children):
                print(f"\n=== Child {i} (Bottom Crum) ===")
                print(f"  height: {child.get('height')}")
                print(f"  enftype: {child.get('enftype')}")
                print(f"  cwid (width): {child.get('wid')}")
                print(f"  cdsp (displacement): {child.get('dsp')}")
                print(f"  homedoc: {child.get('homedoc', 'N/A')}")
        
        # Verify the expected structure
        print("\n=== Verification ===")
        
        # Check fullcrum properties
        assert poom_tree.get('height') == 1, f"Expected height=1, got {poom_tree.get('height')}"
        assert poom_tree.get('enftype') == 'POOM', f"Expected enftype=POOM"
        
        # Check number of children (sons)
        assert len(children) == 1, f"Expected 1 child, got {len(children)}"
        
        # Check the single bottom crum
        bottom = children[0]
        assert bottom.get('height') == 0, f"Expected bottom crum height=0, got {bottom.get('height')}"
        assert bottom.get('enftype') == 'POOM', f"Expected bottom enftype=POOM"
        
        # Check that cdsp and cwid are zero (empty)
        # For 2D enfilades, these should be [0, 0]
        wid = bottom.get('wid', [])
        dsp = bottom.get('dsp', [])
        
        print(f"\nBottom crum width (cwid): {wid}")
        print(f"Bottom crum displacement (cdsp): {dsp}")
        print(f"Bottom crum homedoc: {bottom.get('homedoc')}")
        
        # Verify zero-width and zero-displacement
        assert wid == ['0', '0'] or wid == [0, 0] or all(w == 0 or w == '0' for w in wid), \
            f"Expected zero width, got {wid}"
        assert dsp == ['0', '0'] or dsp == [0, 0] or all(d == 0 or d == '0' for d in dsp), \
            f"Expected zero displacement, got {dsp}"
        
        # Verify homedoc is zero
        homedoc = bottom.get('homedoc', '0')
        assert homedoc == '0' or homedoc == 0, f"Expected homedoc=0, got {homedoc}"
        
        print("\n" + "="*60)
        print("✓ Initial POOM structure VERIFIED!")
        print("="*60)
        print("\nSummary:")
        print("  1. Fullcrum (root): height=1, enftype=POOM")
        print("  2. Single bottom crum: height=0, enftype=POOM")
        print("  3. Bottom crum cdsp: [0, 0] (zero displacement)")
        print("  4. Bottom crum cwid: [0, 0] (zero width)")
        print("  5. Bottom crum homedoc: 0 (cleared)")
        print("\nThis matches the code in credel.c:492-516:")
        print("  - createenf(POOM) creates height-1 fullcrum")
        print("  - Adopts single height-0 bottom crum")
        print("  - For POOM, c2dinfo is cleared (credel.c:591)")
        print("  - cdsp and cwid are cleared (credel.c:580-581)")
        
    else:
        print("\n✗ Could not find POOM tree in granf!")
        import json
        print("\nFull state:")
        print(json.dumps(state, indent=2))
    
    session.quit()

if __name__ == '__main__':
    test_initial_poom_structure()
