#!/usr/bin/env python3
"""Test link + delete crash - mimics link_survives_source_delete_adjacent scenario."""

import sys
sys.path.insert(0, '/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/febe')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_WRITE, CONFLICT_FAIL, JUMP_TYPE, LINK_SOURCE
)

# Start backend
stream = PipeStream("../backend/build/backend --test-mode 2>backenderror")
session = XuSession(XuConn(stream))

# Set account
account = Address(1, 1, 0, 1)
session.account(account)

print("Creating source doc...")
source_doc = session.create_document()
source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(source_opened, Address(1, 1), ["DELETE_ME Click here for more"])
# "here" is at positions 17-20

print("Creating target doc...")
target_doc = session.create_document()
target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(target_opened, Address(1, 1), ["Target content"])

print("Creating link on 'here' (positions 17-20)...")
link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 17), Offset(0, 4))]))
link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
print(f"Link created: {link_id}")

print("Verifying link before delete...")
before_source = session.follow_link(link_id, LINK_SOURCE)
before_source_text = session.retrieve_contents(before_source)
print(f"Link source text: {before_source_text}")

print("\n=== DELETING 'DELETE_ME ' (positions 1-10) ===")
print("Testing delete with fixed client (uses DELETEVSPAN instead of REARRANGE)...")
try:
    session.delete(source_opened, Address(1, 1), Offset(0, 10))
    print("Delete SUCCEEDED!")

    # Check new contents
    vspanset = session.retrieve_vspanset(source_opened)
    specset = SpecSet(VSpec(source_opened, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)
    print(f"New contents: {contents}")

    # Verify link still works
    after_source = session.follow_link(link_id, LINK_SOURCE)
    after_text = session.retrieve_contents(after_source)
    print(f"Link source after delete: {after_text}")
except Exception as e:
    print(f"Delete FAILED: {e}")

print("\n=== Backend error log ===")
try:
    with open('backenderror', 'r') as f:
        print(f.read())
except:
    pass

try:
    session.quit()
except:
    pass
