# Writing Scenarios

## What is a Scenario

A scenario is a short script that performs a sequence of operations against the enfilade server and records what happens. It creates documents, inserts content, makes links, retrieves state — whatever sequence of operations you want to observe — and captures every return value as JSON. The output is a golden file: a complete record of what the server did in response to that sequence.

Scenarios don't assert anything. They capture. The golden file IS the expected behavior. If you run the same scenario against a different server and the output differs, you know something changed.

## Why Write One

You write a scenario when you want to pin down a specific behavior:

- **You found a bug** and want to capture the exact sequence that triggers it, so you can tell when it's fixed.
- **You're testing an edge case** — what happens when you delete all content and then insert? What happens when you transclude from a document you're about to close?
- **You need to verify a property across servers** — does your new enfilade server preserve I-address identity through transclusion the same way the C server does?
- **You want to understand how an operation works** — insert "Hello" then insert " World" at position 6, and see what the V-spans and I-addresses look like afterward.

## How to Think About Writing One

A good scenario tests **one concept**. Ask yourself: what single question am I answering?

- "Does delete shift V-positions of content after the deletion point?" — insert text, delete from the middle, retrieve, record the V-spans.
- "Do links survive when you delete the content they point to?" — create content, create a link on it, delete the content, find_links.
- "Does vcopy preserve I-address identity?" — insert in doc A, vcopy to doc B, compare_versions between them.

Start with the setup (create document, insert content), perform the operation you're testing, then retrieve the state you care about. Record everything — the setup results and the final state. Golden files are most useful when you can see the full before-and-after.

## The Pattern

The test runner handles all the plumbing — starting the enfilade server, establishing the FEBE connection, and tearing everything down afterward. Your scenario function receives a `session` object (an `XuSession`) that's already connected to a fresh server. You use it to call operations like `session.insert()`, `session.create_document()`, etc.

The function returns a dict that becomes the golden JSON file. The dict records what you did and what the server returned — this is the captured behavior that gets diffed when comparing servers.

```python
def scenario_my_test(session):
    """One-line description of what this tests."""

    # --- Perform operations against the server ---
    doc = session.create_document()                          # create a new document
    opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)  # open it for writing
    session.insert(opened, Address(1, 1), ["Hello"])         # insert "Hello" at position 1

    # --- Read back the result ---
    vspanset = session.retrieve_vspanset(opened)             # ask what spans exist
    specset = SpecSet(VSpec(opened, list(vspanset.spans)))   # build a request for those spans
    contents = session.retrieve_contents(specset)            # get the actual text

    session.close_document(opened)

    # --- Return the golden record ---
    # This dict becomes the JSON file. Each entry in "operations"
    # records one step and what the server returned.
    return {
        "name": "my_test",                                   # must match registration name
        "description": "One-line description of what this tests",
        "operations": [
            {"op": "create_document", "result": str(doc)},   # server returned a doc address
            {"op": "open_document", "doc": str(doc), "result": str(opened)},
            {"op": "insert", "address": "1.1", "text": "Hello"},
            {"op": "retrieve_contents", "result": contents}, # captured text: ["Hello"]
        ]
    }
```

Rules:

1. The function name must start with `scenario_`
2. `session` is an `XuSession` connected to a fresh enfilade server
3. The return dict must have `name`, `description`, and `operations`
4. `name` must match the registration name (used as the JSON filename)
5. Record actual return values in `result` fields — never hardcode expected values

## Imports

Standard imports for a scenario file:

```python
from client import (
    Address, Offset, Span, VSpec, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)
from .common import vspec_to_dict, span_to_dict, specset_to_list
```

Import only what you use. The `common` helpers convert wire types to JSON-serializable dicts.

## Session API Quick Reference

Full reference in `docs/client-api.md`. The most common methods:

```python
# Document lifecycle
doc = session.create_document()
opened = session.open_document(doc, READ_WRITE, CONFLICT_FAIL)
session.close_document(opened)

# Content
session.insert(opened, Address(1, 1), ["text"])
session.remove(opened, VSpan(opened, Span(Address(1, 3), Offset(0, 2))))
contents = session.retrieve_contents(specset)

# Retrieval
vspanset = session.retrieve_vspanset(opened)    # multiple spans
vspan = session.retrieve_vspan(opened)           # single extent

# Transclusion
session.vcopy(target_doc, Address(1, 1), source_specset)

# Versions
version = session.create_version(opened)
shared = session.compare_versions(specset_a, specset_b)

# Links
link_id = session.create_link(home_doc, source_specs, target_specs, type_specs)
found = session.find_links(source_specs, target_specs, type_specs, homedocids)
endset = session.follow_link(link_id, LINK_TARGET)

# Rearrange
session.pivot(opened, start, pivot, end)
session.swap(opened, start_a, end_a, start_b, end_b)

# Discovery
docs = session.find_documents(specset)

# Accounts
session.account(Address(1, 1, 0, 1))
node = session.create_node()
```

## Wire Types

Everything in the enfilade server is addressed by tumblers — hierarchical numbers like `1.1.0.1.0.1`. The wire types are Python objects that represent these addresses and ranges as they travel over the FEBE protocol. You use them to tell the server where to insert, what to retrieve, and which spans to link.

They build on each other:

- **`Address(1, 1, 0, 1)`** — a position in tumbler space. Documents, characters, links, and versions all have addresses.
- **`Offset(0, 5)`** — a width. How many positions a range covers.
- **`Span(address, offset)`** — a contiguous range: start position + width. "Characters 3 through 7" is `Span(Address(1, 3), Offset(0, 5))`.
- **`VSpec(docid, [span1, span2])`** — one or more spans within a specific document. This is how you say "these ranges in this document."
- **`SpecSet(vspec)`** — a collection of VSpecs. Most retrieval and comparison operations take a SpecSet as input.
- **`NOSPECS`** — empty SpecSet, used as a default for optional parameters (e.g., "find links with any target").

In practice, the most common pattern is building a SpecSet to pass to `retrieve_contents` or `compare_versions`:

```python
specset = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
contents = session.retrieve_contents(specset)
```

When recording results in the operations dict, convert wire types to strings with `str()` — the golden output is JSON, not Python objects.

## Common Helpers

The wire types (`Span`, `VSpec`, `SpecSet`) are Python objects, but golden output is JSON. Every scenario needs to convert between the two when building the operations dict. Rather than writing `{"start": str(span.start), "width": str(span.width)}` everywhere, use the helpers in `scenarios/common.py`:

```python
span_to_dict(span)       # {"start": "1.1", "width": "0.5"}
vspec_to_dict(vspec)     # {"docid": "1.1.0.1.0.1", "spans": [...]}
specset_to_list(specset) # [{"docid": ..., "spans": ...}, ...]
```

These are especially useful when recording `retrieve_vspanset` results or link endsets, where the return values are complex nested wire types.

## The Retrieve Pattern

There's no "give me the contents of this document" command. The enfilade server thinks in spans, not documents — a document's content may be spread across multiple V-ranges (after deletions, transclusions, rearrangements). To read content, you first ask what spans exist, then request those specific spans:

```
retrieve_vspanset(doc)  →  spans[]  →  SpecSet(VSpec(doc, spans))  →  retrieve_contents(specset)  →  text
```

In code:

```python
# 1. Ask the server what V-positions exist in this document
vspanset = session.retrieve_vspanset(opened)

# 2. Build a SpecSet from those spans
specset = SpecSet(VSpec(opened, list(vspanset.spans)))

# 3. Retrieve the actual content for those positions
contents = session.retrieve_contents(specset)
```

If you already know the exact range you want (e.g., "characters 1 through 10"):

```python
specset = SpecSet(VSpec(opened, [Span(Address(1, 1), Offset(0, 10))]))
contents = session.retrieve_contents(specset)
```

Almost every scenario uses one of these two forms. The first is more common because you usually want all content, not a specific slice.

## Registering a Scenario

Writing a scenario function isn't enough — the test runner doesn't discover functions automatically. You register a scenario by adding it to a `SCENARIOS` list, which tells the runner which function to call and where to put the output.

### Categories

Golden output is organized into directories by category: `golden/content/`, `golden/links/`, `golden/versions/`, etc. A category groups related scenarios so the output is browsable. When you register a scenario, you pick which category it belongs to. See `docs/golden-tests.md` for the full list of existing categories.

### How to register

Each scenario module has a `SCENARIOS` list at the bottom. Each entry is a tuple of `(category, name, function)`:

```python
SCENARIOS = [
    ("content", "insert_middle", scenario_insert_middle),
    ("content", "my_new_test", scenario_my_new_test),  # add here
]
```

- **category** — output subdirectory (e.g., `"content"` → `golden/content/`)
- **name** — JSON filename (must match `return {"name": ...}` in your function)
- **function** — the scenario function to call

Most of the time, you're adding a scenario to an existing module that already has the right category. Just append to its `SCENARIOS` list.

### Creating a new module

If none of the existing modules fit — say you're testing a new area of behavior — create a new one:

1. Create `scenarios/my_module.py` with scenario functions and a `SCENARIOS` list
2. In `scenarios/__init__.py`, import it and add it to `ALL_SCENARIOS`:

```python
from .my_module import SCENARIOS as MY_SCENARIOS

ALL_SCENARIOS = (
    ...
    ALLOCATION_INDEPENDENCE_SCENARIOS +
    MY_SCENARIOS
)
```

Some categories have grown large enough to split across multiple files (e.g., `scenarios/links/` has `basic.py`, `survival.py`, `orphaned.py`, `discovery.py`). These use a package `__init__.py` to combine their `SCENARIOS` lists. You only need this structure if a single module gets unwieldy — start with a single file and split later if needed.

## Tips

- **Close your documents.** The backend tracks open documents. Leaking them can cause CONFLICT_FAIL on reopen.
- **Use `str()` for addresses.** Always `str(docid)` in the operations dict, never the raw object.
- **Record intermediate state.** If testing that insert-then-delete restores content, record the state after insert AND after delete.
- **One concept per scenario.** Don't test delete and rearrange in the same scenario unless you're specifically testing their interaction.
- **Comments are free.** Add `"comment"` fields to explain non-obvious operations.
