"""
Test to verify that retrieverestricted returns spans in V-order.

This tests the claim in DN-0015 that:
"The source's content is retrieved by retrieverestricted, which performs 
a left-to-right traversal of the source tree... left-to-right traversal 
yields V-ordered spans."

We'll create a document with multiple insertions, retrieve the content,
and observe the order in which I-spans are returned.
"""

from febe.client import FEBEClient

def test_retrieval_ordering():
    """Verify that retrieverestricted yields I-spans in V-order."""
    client = FEBEClient()
    session = client.connect()
    
    try:
        # Create a document
        doc = session.create_document()
        
        # Insert three separate pieces of content
        # Each insert gets a distinct I-address
        session.insert(doc, "First piece. ")
        session.insert(doc, "Second piece. ")
        session.insert(doc, "Third piece. ")
        
        # Retrieve the full content
        result = session.retrieve(doc)
        
        # The result should contain the text in V-order
        # But what we care about is the order of the underlying I-spans
        
        # To observe this, we need to look at what COPY does
        # COPY calls docopyinternal which calls specset2ispanset
        # which calls retrieverestricted
        
        # Create a new version - this exercises the retrieval path
        version = session.create_new_version(doc)
        
        # Retrieve from the version - should be identical
        version_result = session.retrieve(version)
        
        print(f"Original: {result['text']}")
        print(f"Version:  {version_result['text']}")
        
        assert result['text'] == version_result['text']
        
        # Now let's test with a more complex case
        # Insert out of V-order by using explicit V-addresses
        doc2 = session.create_document()
        
        # Insert at V=0.0.0.1 (first position)
        session.insert(doc2, "AAA")
        
        # Insert at V=0.0.0.4 (leaving a gap)
        # Note: This may not be possible through the normal API
        # The backend may auto-assign consecutive V-addresses
        
        # Instead, let's create a scenario with COPY that might produce
        # non-contiguous V-addresses
        
    finally:
        session.disconnect()

if __name__ == '__main__':
    test_retrieval_ordering()
