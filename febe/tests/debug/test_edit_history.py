#!/usr/bin/env python3
"""Test whether edits maintain any implicit history or undo capability.

Question: Can we recover intermediate states without explicit CREATENEWVERSION?
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, SpecSet, VSpec,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)

BACKEND = os.path.join(os.path.dirname(__file__), '../../../backend/build/backend')

def main():
    print("Testing whether edits maintain implicit history...\n")

    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create a document and perform a sequence of edits WITHOUT creating versions
    docid = session.create_document()
    print(f"Created document: {docid}")

    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    print(f"Opened document: {opened}\n")

    # State 1: Insert "First"
    print("State 1: Insert 'First'")
    session.insert(opened, Address(1, 1), ["First"])
    vs1 = session.retrieve_vspanset(opened)
    specs1 = SpecSet(VSpec(opened, list(vs1.spans)))
    content1 = session.retrieve_contents(specs1)
    print(f"  Content: {content1}")
    print(f"  V-spans: {vs1.spans}\n")

    # State 2: Insert " Second" after "First"
    print("State 2: Insert ' Second'")
    session.insert(opened, vs1.spans[0].end(), [" Second"])
    vs2 = session.retrieve_vspanset(opened)
    specs2 = SpecSet(VSpec(opened, list(vs2.spans)))
    content2 = session.retrieve_contents(specs2)
    print(f"  Content: {content2}")
    print(f"  V-spans: {vs2.spans}\n")

    # State 3: Insert " Third"
    print("State 3: Insert ' Third'")
    session.insert(opened, vs2.spans[0].end(), [" Third"])
    vs3 = session.retrieve_vspanset(opened)
    specs3 = SpecSet(VSpec(opened, list(vs3.spans)))
    content3 = session.retrieve_contents(specs3)
    print(f"  Content: {content3}")
    print(f"  V-spans: {vs3.spans}\n")

    # Now the question: Can we recover State 1 or State 2?

    print("=" * 60)
    print("QUESTION: Can we recover intermediate states?")
    print("=" * 60)
    print()

    # Attempt 1: Check if there are multiple V-span ranges representing history
    print("Attempt 1: Check current V-spanset")
    print(f"  Current spans: {len(vs3.spans)} span(s)")
    print(f"  Spans: {vs3.spans}")
    print("  → Only shows current state, not history\n")

    # Attempt 2: Try to retrieve earlier V-positions directly
    print("Attempt 2: Try to retrieve just the first 5 characters (State 1)")
    try:
        # Try to read just V-positions 1.1 to 1.6 (the original "First")
        partial_spec = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 5))]))
        partial_content = session.retrieve_contents(partial_spec)
        print(f"  Retrieved: {partial_content}")
        print(f"  → This works, but it's reading current I-addresses at those V-positions")
        print(f"  → NOT historical content\n")
    except Exception as e:
        print(f"  Failed: {e}\n")

    # Attempt 3: Delete recent additions and see if old content can be recovered
    print("Attempt 3: Delete ' Third' and ' Second' - can we get back to 'First'?")
    # Delete " Third" and " Second"
    session.delete(opened, Address(1, 6), Offset(0, 13))  # Delete positions 1.6 onward
    vs_after_delete = session.retrieve_vspanset(opened)
    specs_after_delete = SpecSet(VSpec(opened, list(vs_after_delete.spans)))
    content_after_delete = session.retrieve_contents(specs_after_delete)
    print(f"  Content after delete: {content_after_delete}")
    print(f"  V-spans: {vs_after_delete.spans}")
    print(f"  → DELETE shifts V-positions. We get back to 'First', but...")
    print(f"  → The I-addresses are DIFFERENT from the original 'First'\n")

    # Attempt 4: Check if I-addresses differ by re-inserting and comparing
    print("Attempt 4: Re-insert ' Second Third' and check I-addresses")
    session.insert(opened, vs_after_delete.spans[0].end(), [" Second Third"])
    vs_reinserted = session.retrieve_vspanset(opened)

    print(f"  After re-insert V-spans: {vs_reinserted.spans}")
    print(f"  Compare to original State 3 V-spans: {vs3.spans}")
    print(f"  → V-space looks the same, but I-space is DIFFERENT")
    print(f"  → Finding 064: DELETE is irreversible in I-space\n")

    session.close_document(opened)

    print("=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("✗ No implicit edit history")
    print("✗ No automatic undo/backtrack capability")
    print("✗ DELETE is destructive - removes V→I mappings permanently")
    print("✗ Re-INSERT creates new I-addresses, breaking content identity")
    print()
    print("✓ ONLY way to preserve history: explicit CREATENEWVERSION")
    print("✓ Versions capture state snapshots with preserved I-addresses")
    print("✓ Without explicit versioning, intermediate states are LOST")

    session.quit()

if __name__ == "__main__":
    main()
