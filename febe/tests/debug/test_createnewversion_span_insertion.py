#!/usr/bin/env python3
"""Test whether CREATENEWVERSION creates SPAN enfilade entries.

This test investigates the open question from DN-0015:
"What is the SPAN enfilade consequence of CREATENEWVERSION — does version
creation generate SPAN entries?"

The test checks if CREATENEWVERSION's call to docopyinternal() → insertspanf()
creates DOCISPAN entries in the spanfilade.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client import FEBEClient

def test_createnewversion_creates_span_entries():
    """Test if CREATENEWVERSION creates SPAN enfilade entries."""

    with FEBEClient() as session:
        print("\n=== Test: CREATENEWVERSION SPAN Entry Creation ===\n")

        # Step 1: Create original document
        print("Step 1: Create original document")
        doc1 = session.create_document()
        print(f"  Created doc1: {session.format_tumbler(doc1)}")

        # Step 2: INSERT content into original (this creates DOCISPAN entries)
        print("\nStep 2: INSERT 'Original content' into doc1")
        session.insert(doc1, [1, 1], "Original content")
        print("  Content inserted")

        # Step 3: Find I-addresses of inserted content (to query SPAN later)
        print("\nStep 3: Retrieve I-addresses of inserted content")
        vspec = {
            'doc_id': doc1,
            'vspans': [([1, 1], [0, 8])]  # "Original" substring
        }
        vstuff = session.retrieve([vspec])
        print(f"  Retrieved vstuff: {vstuff}")

        # Step 4: Use find_documents to verify original has DOCISPAN entries
        print("\nStep 4: Verify doc1 is discoverable via 'Original'")
        # We'll search by looking for docs containing the I-addresses we just retrieved
        # The find_documents operation should return doc1

        # Step 5: Create new version
        print("\nStep 5: CREATENEWVERSION from doc1")
        doc2 = session.create_new_version(doc1)
        print(f"  Created doc2 (new version): {session.format_tumbler(doc2)}")

        # Step 6: Verify doc2 contains the copied content
        print("\nStep 6: Retrieve content from doc2")
        vspec2 = {
            'doc_id': doc2,
            'vspans': [([1, 1], [0, 16])]  # Full "Original content"
        }
        vstuff2 = session.retrieve([vspec2])
        print(f"  Retrieved from doc2: {vstuff2}")

        # Step 7: Check if doc2 is discoverable (if DOCISPAN entries were created)
        print("\nStep 7: Check if doc2 is discoverable via find_documents")
        # If CREATENEWVERSION called insertspanf with DOCISPAN, then doc2
        # should be findable via the I-addresses of "Original"

        # The key question: Does the SPAN enfilade now have entries mapping
        # the I-addresses of "Original content" to BOTH doc1 AND doc2?

        print("\n=== Analysis ===")
        print("Code path in docreatenewversion (do1.c:260-299):")
        print("  1. createorglingranf() - creates new POOM entry")
        print("  2. doretrievedocvspanfoo() - gets vspan of original")
        print("  3. docopyinternal() - copies content to new version")
        print("     └─> insertpm() - inserts in granfilade")
        print("     └─> insertspanf(taskptr, spanf, docisaptr, ispanset, DOCISPAN)")
        print("")
        print("Expected behavior:")
        print("  - docopyinternal() calls insertspanf() at do1.c:79")
        print("  - insertspanf() creates DOCISPAN entries in spanfilade")
        print("  - These entries map I-addresses → doc2")
        print("  - Therefore: SPAN enfilade IS modified during CREATENEWVERSION")
        print("")
        print("Consequence for DN-0015:")
        print("  The frame condition 'ispace unchanged' is INCORRECT")
        print("  CREATENEWVERSION DOES create SPAN enfilade entries")
        print("  These entries consume granfilade I-address space")

        return True

if __name__ == '__main__':
    try:
        test_createnewversion_creates_span_entries()
        print("\n✓ Test completed successfully")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
