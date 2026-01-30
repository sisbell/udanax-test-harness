#!/usr/bin/env python3
"""Test link + insert crash (Bug 008) - following scenario more closely."""

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

# === Create source document ===
print("Creating source doc...")
source_doc = session.create_document()
source_opened = session.open_document(source_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(source_opened, Address(1, 1), ["Click here for more"])
print(f"Source doc: {source_opened}")

# === Create target document ===
print("Creating target doc...")
target_doc = session.create_document()
target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(target_opened, Address(1, 1), ["Target content"])
print(f"Target doc: {target_opened}")

# === Create link from "here" to "Target" ===
print("\nCreating link on 'here' (positions 7-10)...")
link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
print(f"Link created: {link_id}")

# === Verify link works BEFORE insert (like the scenario does) ===
print("\n=== Verifying link before insert ===")
before_find = session.find_links(SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 20))])))
print(f"Found links: {before_find}")

print("Following link to get source...")
before_source = session.follow_link(link_id, LINK_SOURCE)
print(f"Link source specset: {before_source}")

print("Getting source text...")
before_source_text = session.retrieve_contents(before_source)
print(f"Link source text: {before_source_text}")

# === THE CRASH: Insert before the link ===
print("\n=== INSERTING PREFIX AT 1.1 (before link) ===")
print("This should crash the backend with Bug 008...")
try:
    session.insert(source_opened, Address(1, 1), ["PREFIX: "])
    print("Insert SUCCEEDED!")

    # Check new contents
    vspanset = session.retrieve_vspanset(source_opened)
    specset = SpecSet(VSpec(source_opened, list(vspanset.spans)))
    contents = session.retrieve_contents(specset)
    print(f"New contents: {contents}")
except Exception as e:
    print(f"Insert FAILED: {e}")
    print("\nThis is Bug 008 - backend crashes when editing documents with links")

# Check backend error log
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
