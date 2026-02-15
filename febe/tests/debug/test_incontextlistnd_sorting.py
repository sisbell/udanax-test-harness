"""
Test whether incontextlistnd performs insertion-sort by V-address.

The question: When retrieverestricted → findcbcinarea2d discovers contexts during
tree traversal, does incontextlistnd maintain V-sorted order explicitly, or does
V-ordering arise from tree traversal order alone?

Strategy:
1. Create content at V-position 1.1
2. Transclude it to positions 1.30, 1.20, 1.40 (out of V-order)
3. Use compare_versions which internally calls ispan2vspanset
4. Check if the shared spans are returned in V-sorted order

If results are V-sorted, then incontextlistnd performs insertion-sort.
If results match insertion order, then tree traversal order determines result order.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, READ_ONLY, CONFLICT_FAIL, CONFLICT_COPY, NOSPECS
)

BACKEND = os.path.join(os.path.dirname(__file__), '../../backend/build/backend')

def test_incontextlistnd_sorting():
    """Test whether incontextlistnd maintains V-sorted order."""

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    try:
        # Create document
        docid = session.create_document()
        print(f"Created document: {docid}")

        # Open for editing
        opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)

        # Insert original content at 1.1
        session.insert(opened, Address(1, 1), ["test"])
        print(f"Inserted 'test' at 1.1")

        # Get the vspanset to see what we created
        vspanset = session.retrieve_vspanset(opened)
        print(f"After insert, vspanset: {vspanset}")

        # Now transclude to OUT-OF-ORDER positions: 1.30, 1.20, 1.40
        # This forces the POOM to be built in non-V-sorted order

        # First transclude to 1.30
        source_spec = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 4))]))
        session.vcopy(opened, Address(1, 30), source_spec)
        print(f"Transcluded to 1.30 (inserted 1st, but 2nd in V-order)")

        # Then transclude to 1.20
        session.vcopy(opened, Address(1, 20), source_spec)
        print(f"Transcluded to 1.20 (inserted 2nd, but 1st in V-order)")

        # Then transclude to 1.40
        session.vcopy(opened, Address(1, 40), source_spec)
        print(f"Transcluded to 1.40 (inserted 3rd, and 3rd in V-order)")

        # Check final state
        final_vspanset = session.retrieve_vspanset(opened)
        print(f"\nFinal vspanset: {final_vspanset}")

        # Now use compare_versions to trigger I→V mapping
        # Compare original (1.1) with itself - this should show ALL V-positions
        # that share the same I-addresses

        print(f"\n=== Testing compare_versions (triggers ispan2vspanset) ===")

        # Compare each position pairwise to see if they share identity
        positions = [
            ("1.1 (original)", Span(Address(1, 1), Offset(0, 4))),
            ("1.20 (ins 2nd)", Span(Address(1, 20), Offset(0, 4))),
            ("1.30 (ins 1st)", Span(Address(1, 30), Offset(0, 4))),
            ("1.40 (ins 3rd)", Span(Address(1, 40), Offset(0, 4))),
        ]

        for name, pos in positions:
            result = session.compare_versions(
                docid, Span(Address(1, 1), Offset(0, 4)),
                docid, pos
            )
            shared = result.get('shared', [])
            if shared:
                print(f"{name}: SHARED")
                # Print the V-addresses in the shared result
                for pair in shared:
                    first_start = pair['first']['start']
                    second_start = pair['second']['start']
                    print(f"  First: {first_start}, Second: {second_start}")
            else:
                print(f"{name}: NOT SHARED")

        # Most direct test: create a link, then find it from each position
        print(f"\n=== Testing link discovery (also uses ispan2vspanset) ===")

        link_addr = session.create_link(
            opened,
            Span(Address(1, 1), Offset(0, 4)),  # from
            Span(Address(1, 1), Offset(0, 4)),  # to (self-link)
            1  # link type
        )
        print(f"Created link at 1.1: {link_addr}")

        # Try finding from each transcluded position
        for name, pos in positions[1:]:  # Skip original, test the copies
            links = session.find_links(
                opened,
                source_span=pos
            )
            if links:
                print(f"{name}: FOUND {len(links)} link(s)")
            else:
                print(f"{name}: NO LINKS FOUND")

        session.close_document(opened)
        session.quit()

        print("\n=== Analysis ===")
        print("If all transcluded positions found the link, then I→V mapping is correct.")
        print("The ordering of results in compare_versions would show whether incontextlistnd")
        print("maintains sorted order or just uses tree traversal order.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        session.quit()
        raise

if __name__ == "__main__":
    test_incontextlistnd_sorting()
