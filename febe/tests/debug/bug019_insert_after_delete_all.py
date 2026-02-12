#!/usr/bin/env python3
"""
Bug 019: Backend crashes on INSERT/VCOPY after deleting all content.

After DELETE-all empties the POOM enfilade, firstinsertionnd() finds no
bottom crum (findleftson returns NULL). The fix creates a fresh bottom crum.

Status: FIXED in backend/insertnd.c (firstinsertionnd)

Run from the udanax-test-harness directory:
  PYTHONPATH=febe python3 febe/tests/debug/bug019_insert_after_delete_all.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY
)

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', '..', '..', 'backend', 'build', 'backend')
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)

stream = PipeStream(f"{BACKEND} --test-mode")
session = XuSession(XuConn(stream))
session.account(DEFAULT_ACCOUNT)

# --- Test 1: INSERT after delete-all ---
print("Test 1: INSERT after delete-all...", end=" ")
doc1 = session.create_document()
d1 = session.open_document(doc1, READ_WRITE, CONFLICT_FAIL)
session.insert(d1, Address(1, 1), ["Hello"])
vs = session.retrieve_vspanset(d1)
session.remove(d1, vs.spans[0])
session.insert(d1, Address(1, 1), ["After delete"])
vs2 = session.retrieve_vspanset(d1)
ss = SpecSet(VSpec(d1, list(vs2.spans)))
contents = session.retrieve_contents(ss)
session.close_document(d1)
print(f"PASS (got: {contents})")

# --- Test 2: VCOPY after delete-all ---
print("Test 2: VCOPY after delete-all...", end=" ")
src = session.create_document()
src_w = session.open_document(src, READ_WRITE, CONFLICT_FAIL)
session.insert(src_w, Address(1, 1), ["Source text"])
session.close_document(src_w)

tgt = session.create_document()
tgt_w = session.open_document(tgt, READ_WRITE, CONFLICT_FAIL)
session.insert(tgt_w, Address(1, 1), ["Temporary"])
vs = session.retrieve_vspanset(tgt_w)
session.remove(tgt_w, vs.spans[0])

src_ro = session.open_document(src, READ_ONLY, CONFLICT_COPY)
src_vs = session.retrieve_vspanset(src_ro)
src_specs = SpecSet(VSpec(src_ro, list(src_vs.spans)))
session.vcopy(tgt_w, Address(1, 1), src_specs)
tgt_vs = session.retrieve_vspanset(tgt_w)
ss = SpecSet(VSpec(tgt_w, list(tgt_vs.spans)))
contents = session.retrieve_contents(ss)
session.close_document(src_ro)
session.close_document(tgt_w)
print(f"PASS (got: {contents})")

# --- Test 3: Incremental delete then INSERT ---
print("Test 3: Incremental delete then INSERT...", end=" ")
doc3 = session.create_document()
d3 = session.open_document(doc3, READ_WRITE, CONFLICT_FAIL)
session.insert(d3, Address(1, 1), ["ABCDEF"])
session.remove(d3, Span(Address(1, 1), Offset(0, 3)))  # ABC
session.remove(d3, Span(Address(1, 1), Offset(0, 3)))  # DEF
session.insert(d3, Address(1, 1), ["Rebuilt"])
vs = session.retrieve_vspanset(d3)
ss = SpecSet(VSpec(d3, list(vs.spans)))
contents = session.retrieve_contents(ss)
session.close_document(d3)
print(f"PASS (got: {contents})")

print("\nAll Bug 019 tests passed.")
