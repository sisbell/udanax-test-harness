# FEBE Protocol Client

Python 3 implementation of the Udanax Green FEBE 88.1 protocol (Front End Back End).

## Components

- `client.py` - Protocol client. Provides API for all backend operations.
- `test_client.py` - Unit tests for protocol parsing.

## Usage

Run the C backend in test mode (in-memory storage, no disk persistence):

```bash
../backend/build/backend --test-mode
```

Connect and execute operations:

```python
from client import Connection

conn = Connection()
doc = conn.create_document()
conn.insert(doc, "Hello, world!")
content = conn.retrieve(doc)
```

## Operations

**Documents**: `create_document()`, `create_version()`, `open_document()`, `close_document()`

**Content**: `insert()`, `vcopy()`, `delete()`, `retrieve()`, `retrieve_vspanset()`

**Editing**: `pivot()`, `swap()`, `remove()`, `rearrange()`

**Links**: `create_link()`, `follow_link()`, `find_links()`

**Comparison**: `compare_versions()`, `find_documents()`

## Origin

client.py was originally written by Ka-Ping Yee <ping@lfw.org> in August 1999 as part of Pyxi, a Tcl/Tk graphical frontend for Udanax Green. In 2026, the protocol client was extracted and ported to Python 3.

See [LICENSE](LICENSE) for the original terms.
