#!/usr/bin/env python3
"""Test link + vcopy scenario."""

import sys
sys.path.insert(0, '/Users/shane/Documents/github/claude/xanadu-spec/udanax-test-harness/febe')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, JUMP_TYPE, LINK_SOURCE
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
session.insert(source_opened, Address(1, 1), ["Click here for details"])

print("Creating target doc...")
target_doc = session.create_document()
target_opened = session.open_document(target_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(target_opened, Address(1, 1), ["Detail information"])

print("Creating link on 'here' (positions 7-10)...")
link_source = SpecSet(VSpec(source_opened, [Span(Address(1, 7), Offset(0, 4))]))
link_target = SpecSet(VSpec(target_opened, [Span(Address(1, 1), Offset(0, 6))]))
link_id = session.create_link(source_opened, link_source, link_target, SpecSet([JUMP_TYPE]))
print(f"Link created: {link_id}")

# Create a third document to vcopy to
print("\nCreating copy doc...")
copy_doc = session.create_document()
copy_opened = session.open_document(copy_doc, READ_WRITE, CONFLICT_FAIL)
session.insert(copy_opened, Address(1, 1), ["Copied: "])

# vcopy "here" from source to copy_doc
# Use the existing source_opened handle - can't open same doc twice
print("Creating vcopy specset (using existing handle - can't open same doc twice)...")
copy_span = Span(Address(1, 7), Offset(0, 4))  # "here"
copy_specs = SpecSet(VSpec(source_opened, [copy_span]))

print(f"Vcopy specs: {copy_specs}")
print("Executing vcopy...")
try:
    session.vcopy(copy_opened, Address(1, 9), copy_specs)
    print("Vcopy SUCCEEDED!")

    copy_vspanset = session.retrieve_vspanset(copy_opened)
    copy_contents = session.retrieve_contents(SpecSet(VSpec(copy_opened, list(copy_vspanset.spans))))
    print(f"Copy contents: {copy_contents}")

    # Test if we can find links from the transcluded copy
    copy_search = SpecSet(VSpec(copy_opened, [Span(Address(1, 1), Offset(0, 15))]))
    links_from_copy = session.find_links(copy_search)
    print(f"Links found from copy: {links_from_copy}")
except Exception as e:
    print(f"Vcopy FAILED: {e}")

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
