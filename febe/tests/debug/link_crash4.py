#!/usr/bin/env python3
"""Test without stderr redirect - like generate_golden.py"""

import sys
sys.path.insert(0, '/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/febe')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL, JUMP_TYPE, LINK_SOURCE
)

# Start backend WITHOUT stderr redirect (like generate_golden.py)
stream = PipeStream("../backend/build/backend --test-mode")
session = XuSession(XuConn(stream))

# Set account
account = Address(1, 1, 0, 1)
session.account(account)

# === Exact scenario code ===
source_doc = session.create_document()
source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(source_opened, Address(1, 1), ["Click here for more"])

target_doc = session.create_document()
target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(target_opened, Address(1, 1), ["Target content"])

link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))

before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))
before_source = session.follow_link(link_id, LINK_SOURCE)
before_source_text = session.retrieve_contents(before_source)

print("Before insert:")
print(f"  Found links: {before_find}")
print(f"  Link source: {before_source_text}")

print("\nInserting PREFIX...")
session.insert(source_opened, Address(1, 1), ["PREFIX: "])
print("Insert done!")

# This is what seems to crash the scenario
print("\nRetrieving vspanset...")
vspanset = session.retrieve_vspanset(source_opened)

# Scenario does: session.retrieve_contents(session.retrieve_vspanset(source_opened))
# Which passes VSpec directly - but that seems wrong based on earlier tests
# Let me try it the scenario way:
print("Retrieving contents (scenario way - passing VSpec)...")
try:
    after_contents = session.retrieve_contents(vspanset)
    print(f"Contents: {after_contents}")
except Exception as e:
    print(f"Failed: {e}")
    # Try the correct way
    specset = SpecSet(VSpec(source_opened, list(vspanset.spans)))
    after_contents = session.retrieve_contents(specset)
    print(f"Contents (correct way): {after_contents}")

print("\nAll done!")
session.quit()
