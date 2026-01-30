#!/usr/bin/env python3
"""Test link + insert crash - exact replica of scenario."""

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

# === Exact scenario code ===
print("Creating source doc...")
source_doc = session.create_document()
source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(source_opened, Address(1, 1), ["Click here for more"])

print("Creating target doc...")
target_doc = session.create_document()
target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(target_opened, Address(1, 1), ["Target content"])

print("Creating link...")
link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
print(f"Link: {link_id}")

print("Finding links before insert...")
before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))
print(f"Found: {before_find}")

print("Following link to source...")
before_source = session.follow_link(link_id, LINK_SOURCE)
print(f"Source: {before_source}")

print("Retrieving source text...")
before_source_text = session.retrieve_contents(before_source)
print(f"Text: {before_source_text}")

print("\n=== INSERTING PREFIX ===")
session.insert(source_opened, Address(1, 1), ["PREFIX: "])
print("Insert done")

print("Getting vspanset...")
vspanset = session.retrieve_vspanset(source_opened)

print("Retrieving after contents... (this is what scenario does)")
# Scenario line 677: after_contents = session.retrieve_contents(session.retrieve_vspanset(source_opened))
# But VSpec from retrieve_vspanset needs to be wrapped
# Actually looking at scenario - it passes the VSpec directly... let me check

# Check if session.retrieve_contents handles VSpec directly
print(f"Vspanset type: {type(vspanset)}")
try:
    # Try both ways
    print("Method 1: SpecSet wrapped...")
    specset = SpecSet(VSpec(source_opened, list(vspanset.spans)))
    after_contents = session.retrieve_contents(specset)
    print(f"Contents: {after_contents}")
except Exception as e1:
    print(f"Method 1 failed: {e1}")

print("\nFinding links after insert...")
after_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 30))])))
print(f"Found: {after_find}")

print("Following link to source after insert...")
after_source = session.follow_link(link_id, LINK_SOURCE)
print(f"Source: {after_source}")

print("Retrieving source text after insert...")
after_source_text = session.retrieve_contents(after_source)
print(f"Text: {after_source_text}")

print("\n=== All done! ===")

try:
    session.close_document(source_opened)
    session.close_document(target_opened)
    session.quit()
except:
    pass

print("\n=== Backend error log ===")
with open('backenderror', 'r') as f:
    print(f.read())
