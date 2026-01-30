#!/usr/bin/env python3
"""Minimal debug script to pinpoint Bug 009 crash location."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import (XuSession, XuConn, PipeStream, Address, Offset, Span,
                    JUMP_TYPE, NOSPECS, VSpec, SpecSet,
                    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY)

DEFAULT_ACCOUNT = Address(1, 1, 0, 1)
BACKEND_PATH = "../backend/build/backend"

def run_test():
    """Minimal test case."""

    stream = PipeStream(f"{BACKEND_PATH} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(DEFAULT_ACCOUNT)

    print("Creating document and link...")

    # Create original with content
    original = session.create_document()
    orig_handle = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    session.insert(orig_handle, Address(1, 1), ['Shared text'])
    session.close_document(orig_handle)

    # Create version (before adding link)
    version = session.create_version(original)

    # Add link to original
    target = session.create_document()
    tgt_handle = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
    session.insert(tgt_handle, Address(1, 1), ['Target'])
    session.close_document(tgt_handle)

    orig_handle2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
    tgt_handle2 = session.open_document(target, READ_ONLY, CONFLICT_COPY)

    link_source = SpecSet(VSpec(orig_handle2, [Span(Address(1, 1), Offset(0, 6))]))
    link_target = SpecSet(VSpec(tgt_handle2, [Span(Address(1, 1), Offset(0, 6))]))
    link_id = session.create_link(orig_handle2, link_source, link_target, SpecSet([JUMP_TYPE]))
    print(f"Created link: {link_id}")

    session.close_document(tgt_handle2)
    session.close_document(orig_handle2)

    # Now try compare_versions
    print("\nOpening documents for comparison...")
    orig_ro = session.open_document(original, READ_ONLY, CONFLICT_COPY)
    ver_ro = session.open_document(version, READ_ONLY, CONFLICT_COPY)

    print("Retrieving vspansets...")
    o_vs = session.retrieve_vspanset(orig_ro)
    v_vs = session.retrieve_vspanset(ver_ro)

    print(f"Original vspanset: {o_vs}")
    print(f"Version vspanset: {v_vs}")

    # Try with ONLY the text span (filter out link subspace)
    print("\n--- Test 1: Using only text spans ---")
    text_spans = [s for s in o_vs.spans if s.start.digits and s.start.digits[0] >= 1]
    print(f"Filtered text spans: {text_spans}")

    if text_spans:
        o_ss = SpecSet(VSpec(orig_ro, text_spans))
        v_ss = SpecSet(VSpec(ver_ro, list(v_vs.spans)))

        print("Calling compare_versions with filtered spans...")
        try:
            shared = session.compare_versions(o_ss, v_ss)
            print(f"Result: {shared}")
            print("SUCCESS with filtered spans!")
        except Exception as e:
            print(f"FAILED: {e}")

    # Now try with ALL spans including link subspace
    print("\n--- Test 2: Using ALL spans (including link subspace) ---")
    o_ss_all = SpecSet(VSpec(orig_ro, list(o_vs.spans)))
    v_ss = SpecSet(VSpec(ver_ro, list(v_vs.spans)))

    print(f"Original specset: {o_ss_all}")
    print(f"Version specset: {v_ss}")

    print("Calling compare_versions with all spans...")
    try:
        shared = session.compare_versions(o_ss_all, v_ss)
        print(f"Result: {shared}")
        print("SUCCESS with all spans!")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\nTest completed.")
    session.quit()

if __name__ == '__main__':
    run_test()
