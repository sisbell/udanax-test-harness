#!/usr/bin/env python3
"""
Test whether COPY (vcopy) can copy content from dom₂ (link subspace).

Question: Does docopy filter by V-address first component, or does it
copy any V-span specified (including those in link subspace at 0.x or 2.x)?
"""

import sys
sys.path.insert(0, 'febe')

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY, JUMP_TYPE
)

BACKEND = "backend/build/backend"

def main():
    stream = PipeStream(f"{BACKEND} --test-mode")
    session = XuSession(XuConn(stream))
    session.account(Address(1, 1, 0, 1))
    
    print("\n=== Test: COPY from dom₂ (link subspace) ===\n")
    
    # Create source document with a link
    source = session.create_document()
    source_opened = session.open_document(source, READ_WRITE, CONFLICT_FAIL)
    
    # Insert text first
    session.insert(source_opened, Address(1, 1), ["ABC"])
    print(f"Source after text insert:")
    vs = session.retrieve_vspanset(source_opened)
    for span in vs.spans:
        print(f"  V-span: {span.start} for {span.width}")
    
    # Create a link (will appear at 2.1 or 0.x in vspanset)
    link = session.create_link(
        source_opened,
        SpecSet(VSpec(source_opened, [Span(Address(1, 1), Offset(0, 1))])),  # from: A
        SpecSet(VSpec(source_opened, [Span(Address(1, 2), Offset(0, 1))])),  # to: B
        SpecSet([JUMP_TYPE])
    )
    print(f"\nLink created: {link}")
    
    vs = session.retrieve_vspanset(source_opened)
    print(f"\nSource vspanset after link creation:")
    link_span = None
    text_span = None
    for span in vs.spans:
        print(f"  V-span: {span.start} for {span.width}")
        # Link subspace is at 0.x or 2.x - check string representation
        start_str = str(span.start)
        if start_str.startswith("0") or start_str.startswith("2"):
            link_span = span
            print(f"    ^ This is the link subspace (dom₂)")
        elif start_str.startswith("1"):
            text_span = span
            print(f"    ^ This is the text subspace (dom₁)")
    
    session.close_document(source_opened)
    
    # Now try to COPY the link subspace to a new document
    print("\n--- Attempting to COPY link subspace span to destination ---\n")
    
    dest = session.create_document()
    dest_opened = session.open_document(dest, READ_WRITE, CONFLICT_FAIL)
    
    # Try to copy ONLY the link span
    source_ro = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    
    if link_span is None:
        print("ERROR: No link span found in source!")
        session.quit()
        return
    
    print(f"Attempting vcopy of link span: {link_span.start} for {link_span.width}")
    
    try:
        # Build specset containing ONLY the link subspace span
        link_specset = SpecSet(VSpec(source_ro, [link_span]))
        
        # Try to copy to destination at V-address 1.1 (text subspace destination)
        session.vcopy(dest_opened, Address(1, 1), link_specset)
        print("SUCCESS: vcopy completed without error")
        
        # Check what ended up in destination
        vs = session.retrieve_vspanset(dest_opened)
        print(f"\nDestination vspanset after copy:")
        for span in vs.spans:
            print(f"  V-span: {span.start} for {span.width}")
        
        # Try to retrieve content from destination
        if len(vs.spans) > 0:
            first_span = vs.spans[0]
            print(f"\nAttempting retrieve_contents from {first_span.start} for {first_span.width}:")
            try:
                contents = session.retrieve_contents(SpecSet(VSpec(dest_opened, [first_span])))
                print(f"  Contents: {contents}")
            except Exception as e:
                print(f"  ERROR retrieving: {e}")
        
    except Exception as e:
        print(f"FAILED: vcopy raised exception: {e}")
    
    session.close_document(source_ro)
    session.close_document(dest_opened)
    
    # Also test: can we copy to a link subspace destination (2.1)?
    print("\n--- Attempting to COPY link subspace to link subspace destination ---\n")
    
    dest2 = session.create_document()
    dest2_opened = session.open_document(dest2, READ_WRITE, CONFLICT_FAIL)
    source_ro2 = session.open_document(source, READ_ONLY, CONFLICT_COPY)
    
    print(f"Attempting vcopy of link span to V-address 2.1 (link subspace destination)")
    
    try:
        link_specset2 = SpecSet(VSpec(source_ro2, [link_span]))
        session.vcopy(dest2_opened, Address(2, 1), link_specset2)
        print("SUCCESS: vcopy to 2.1 completed without error")
        
        vs = session.retrieve_vspanset(dest2_opened)
        print(f"\nDestination vspanset after copy to 2.1:")
        for span in vs.spans:
            print(f"  V-span: {span.start} for {span.width}")
        
    except Exception as e:
        print(f"FAILED: vcopy to 2.1 raised exception: {e}")
    
    session.close_document(source_ro2)
    session.close_document(dest2_opened)
    
    session.quit()
    print("\n=== Test complete ===\n")

if __name__ == '__main__':
    main()
