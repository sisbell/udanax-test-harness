#!/usr/bin/env python3
"""
Test for Bug 006: Backend crashes when creating 6th link in a document.

This is a backend bug - it crashes regardless of link type address format.

Expected behavior: Should be able to create unlimited links
Actual behavior: Crashes on 6th link

See bugs/006-backend-crashes-on-6th-link.md for details.
"""

import sys
sys.path.insert(0, '.')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL, JUMP_TYPE
)

BACKEND = "../backend/build/backend"


def test_link_crash():
    """Attempt to create 10 links - demonstrates crash on 6th."""
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))

    # Create link home document
    docid = session.create_document()
    opened = session.open_document(docid, READ_WRITE, CONFLICT_FAIL)
    session.insert(opened, Address(1, 1), ["ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

    # Create link target document
    target_doc = session.create_document()
    target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
    session.insert(target_opened, Address(1, 1), ["Target text here"])

    links_created = 0
    try:
        for i in range(1, 11):
            print(f"Creating link {i}...")
            source = SpecSet(VSpec(opened, [Span(Address(1, i), Offset(0, 1))]))
            target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 1))]))
            link = session.create_link(opened, source, target, SpecSet([JUMP_TYPE]))
            print(f"  link{i} = {link}")
            links_created = i
    except Exception as e:
        print(f"\nCRASH after {links_created} links: {e}")
        print("\nBug 006 confirmed: Backend crashes on 6th link")
        return links_created

    print(f"\nSUCCESS: Created {links_created} links (bug may be fixed)")
    session.quit()
    return links_created


if __name__ == "__main__":
    count = test_link_crash()
    if count < 10:
        print(f"\nResult: Bug 006 reproduced - only {count} links before crash")
        sys.exit(1)
    else:
        print(f"\nResult: Bug 006 NOT reproduced - all 10 links created")
        sys.exit(0)
