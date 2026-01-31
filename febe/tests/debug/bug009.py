#!/usr/bin/env python3
"""Debug script to investigate Bug 009: compare_versions crash with links."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import (XuSession, XuConn, PipeStream, Address, Offset, Span,
                    JUMP_TYPE, NOSPECS, VSpec, SpecSet,
                    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY)

# Default account address for test mode
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)
BACKEND_PATH = "../backend/build/backend"


class BackendProcess:
    """Manages a backend subprocess in test mode."""

    def __init__(self, backend_path=BACKEND_PATH):
        self.backend_path = backend_path
        self.process = None
        self.session = None

    def start(self):
        """Start the backend and establish a session."""
        stream = PipeStream(f"{self.backend_path} --test-mode")
        self.session = XuSession(XuConn(stream))
        self.session.account(DEFAULT_ACCOUNT)
        return self.session

    def stop(self):
        """Stop the backend."""
        if self.session and self.session.open:
            try:
                self.session.quit()
            except:
                pass
        self.session = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def debug_compare_versions():
    """Reproduce and debug the compare_versions crash."""

    with BackendProcess() as session:
        print("=== Creating documents ===")

        # Create original document
        original = session.create_document()
        print(f"Original document: {original}")

        # Open and add content
        orig_handle = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
        session.insert(orig_handle, Address(1, 1), ['Shared text here'])
        print(f"Inserted text into original")

        # Get vspanset BEFORE adding link
        orig_vspanset_before = session.retrieve_vspanset(orig_handle)
        print(f"\nOriginal vspanset BEFORE link: {orig_vspanset_before}")

        session.close_document(orig_handle)

        # Create version
        version = session.create_version(original)
        print(f"\nVersion document: {version}")

        # Check version vspanset
        ver_handle = session.open_document(version, READ_ONLY, CONFLICT_COPY)
        ver_vspanset = session.retrieve_vspanset(ver_handle)
        print(f"Version vspanset: {ver_vspanset}")
        session.close_document(ver_handle)

        # Create target document for link
        target = session.create_document()
        tgt_handle = session.open_document(target, READ_WRITE, CONFLICT_FAIL)
        session.insert(tgt_handle, Address(1, 1), ['Target'])
        session.close_document(tgt_handle)
        print(f"\nTarget document: {target}")

        # Add link to ORIGINAL document
        orig_handle2 = session.open_document(original, READ_WRITE, CONFLICT_FAIL)

        # Link source: "Shared" (chars 1-6)
        link_source = SpecSet(VSpec(orig_handle2, [Span(Address(1, 1), Offset(0, 6))]))

        # Link target: "Target" (chars 1-6)
        tgt_handle2 = session.open_document(target, READ_ONLY, CONFLICT_COPY)
        link_target = SpecSet(VSpec(tgt_handle2, [Span(Address(1, 1), Offset(0, 6))]))

        # Create link
        link_id = session.create_link(orig_handle2, link_source, link_target, SpecSet([JUMP_TYPE]))
        print(f"\nCreated link: {link_id}")

        session.close_document(tgt_handle2)

        # Get vspanset AFTER adding link
        orig_vspanset_after = session.retrieve_vspanset(orig_handle2)
        print(f"\nOriginal vspanset AFTER link: {orig_vspanset_after}")

        # Notice the difference!
        print("\n=== KEY OBSERVATION ===")
        print(f"Before link: {orig_vspanset_before}")
        print(f"After link:  {orig_vspanset_after}")

        session.close_document(orig_handle2)

        # Now try compare_versions
        print("\n=== Attempting compare_versions ===")

        # Re-open documents for comparison
        orig_ro = session.open_document(original, READ_ONLY, CONFLICT_COPY)
        ver_ro = session.open_document(version, READ_ONLY, CONFLICT_COPY)

        # Get vspansets again
        o_vs = session.retrieve_vspanset(orig_ro)
        v_vs = session.retrieve_vspanset(ver_ro)

        print(f"Original vspanset for compare: {o_vs}")
        print(f"Version vspanset for compare: {v_vs}")

        # Build specsets
        o_ss = SpecSet(VSpec(orig_ro, list(o_vs.spans)))
        v_ss = SpecSet(VSpec(ver_ro, list(v_vs.spans)))

        print(f"\nCalling compare_versions...")
        print(f"  Specset 1: {o_ss}")
        print(f"  Specset 2: {v_ss}")

        # This is where the crash happens!
        try:
            shared = session.compare_versions(o_ss, v_ss)
            print(f"Result: {shared}")
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")

        session.close_document(orig_ro)
        session.close_document(ver_ro)


def debug_compare_without_links():
    """Test compare_versions WITHOUT links - should work."""

    print("\n\n=== TEST WITHOUT LINKS (control) ===")

    with BackendProcess() as session:
        # Create original document
        original = session.create_document()
        orig_handle = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
        session.insert(orig_handle, Address(1, 1), ['Shared text here'])
        session.close_document(orig_handle)

        # Create version
        version = session.create_version(original)

        # Compare WITHOUT adding any links
        orig_ro = session.open_document(original, READ_ONLY, CONFLICT_COPY)
        ver_ro = session.open_document(version, READ_ONLY, CONFLICT_COPY)

        o_vs = session.retrieve_vspanset(orig_ro)
        v_vs = session.retrieve_vspanset(ver_ro)

        print(f"Original vspanset: {o_vs}")
        print(f"Version vspanset: {v_vs}")

        o_ss = SpecSet(VSpec(orig_ro, list(o_vs.spans)))
        v_ss = SpecSet(VSpec(ver_ro, list(v_vs.spans)))

        print(f"\nCalling compare_versions (no links)...")
        try:
            shared = session.compare_versions(o_ss, v_ss)
            print(f"Result: {shared}")
            print("SUCCESS - compare_versions works without links")
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")

        session.close_document(orig_ro)
        session.close_document(ver_ro)


def debug_compare_with_filtered_spans():
    """Try compare_versions with links, but filter out span at position 0."""

    print("\n\n=== TEST WITH FILTERED SPANS ===")

    with BackendProcess() as session:
        # Create original document
        original = session.create_document()
        orig_handle = session.open_document(original, READ_WRITE, CONFLICT_FAIL)
        session.insert(orig_handle, Address(1, 1), ['Shared text here'])
        session.close_document(orig_handle)

        # Create version
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

        # Compare with FILTERED spans
        orig_ro = session.open_document(original, READ_ONLY, CONFLICT_COPY)
        ver_ro = session.open_document(version, READ_ONLY, CONFLICT_COPY)

        o_vs = session.retrieve_vspanset(orig_ro)
        v_vs = session.retrieve_vspanset(ver_ro)

        print(f"\nOriginal vspanset (unfiltered): {o_vs}")
        print(f"Version vspanset: {v_vs}")

        # Filter: only keep spans that start at position 1.x (not 0.x)
        def is_text_span(span):
            """Check if span is in text subspace (position >= 1), not link subspace (position 0)."""
            return span.start.digits[0] >= 1 if span.start.digits else False

        o_text_spans = [s for s in o_vs.spans if is_text_span(s)]
        v_text_spans = [s for s in v_vs.spans if is_text_span(s)]

        print(f"\nFiltered original spans: {o_text_spans}")
        print(f"Filtered version spans: {v_text_spans}")

        if o_text_spans and v_text_spans:
            o_ss = SpecSet(VSpec(orig_ro, o_text_spans))
            v_ss = SpecSet(VSpec(ver_ro, v_text_spans))

            print(f"\nCalling compare_versions with filtered spans...")
            try:
                shared = session.compare_versions(o_ss, v_ss)
                print(f"Result: {shared}")
                print("SUCCESS - compare_versions works with filtered spans")
            except Exception as e:
                print(f"EXCEPTION: {type(e).__name__}: {e}")
        else:
            print("No text spans found!")

        session.close_document(orig_ro)
        session.close_document(ver_ro)


if __name__ == '__main__':
    debug_compare_without_links()  # Control test - should work
    debug_compare_with_filtered_spans()  # Test workaround - might work
    debug_compare_versions()  # The crash case - will crash
