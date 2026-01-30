#!/usr/bin/env python3
"""Basic test - just create doc, insert, retrieve."""

import sys
sys.path.insert(0, '/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/febe')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL
)

# Start backend
stream = PipeStream("../backend/build/backend --test-mode 2>backenderror")
session = XuSession(XuConn(stream))

# Set account
account = Address(1, 1, 0, 1)
session.account(account)

print("Creating doc...")
doc = session.create_document()
print(f"Doc: {doc}")

print("Opening doc...")
opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
print(f"Opened: {opened}")

print("Inserting text...")
session.insert(opened, Address(1, 1), ["Hello World"])
print("Inserted")

print("Getting vspanset...")
vspanset = session.retrieve_vspanset(opened)
print(f"Vspanset: {vspanset}")

print("Getting contents...")
# Must wrap VSpec in SpecSet for retrieve_contents
specset = SpecSet(VSpec(opened, list(vspanset.spans)))
contents = session.retrieve_contents(specset)
print(f"Contents: {contents}")

session.close_document(opened)
session.quit()
print("Done!")
