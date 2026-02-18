# Golden Tests

The Udanax Green backend has no unit tests and no specification. The only way to know what it does is to run it and observe. Golden tests solve this: they run 263 scenarios against the backend, capture every return value as JSON, and give you a diffable snapshot of the system's behavior.

Golden files serve two purposes:

1. **Understanding behavior.** Each golden file is a step-by-step record of how an operation affects state — what addresses are returned, how V-spans change, what content appears where. Some scenarios include `dump_state` operations that capture the internal enfilade tree structure before and after an operation, so you can see exactly how the granfilade, spanfilade, and POOM trees change. This is the closest thing to documentation of what the backend actually does.

2. **Comparing enfilade backends.** When you build a new enfilade backend or change the existing one, you diff the golden output to see exactly what changed. The comparison tool classifies differences by severity so you can separate address allocation noise from real behavioral bugs.

This doc covers how to run them, read the output, and compare backends.

## Running Tests

From the repo root:

```bash
# Full suite against C backend (default)
make golden

# Single scenario
make golden SCENARIO=create_document

# List all available scenarios
make golden-list

# Custom output directory
make golden OUTPUT=/tmp/my-golden

# Custom enfilade server (see docs/integrating-enfilade-server.md)
make golden BACKEND=/path/to/server OUTPUT=/tmp/my-golden
```

The C backend must be built first (`make` or `make all`).

## Output Structure

Output is organized by category:

```
golden/
  documents/
    create_document.json
    multiple_documents.json
    ...
  content/
    insert_text.json
    delete_text.json
    ...
  links/
    create_link.json
    find_links.json
    ...
```

Each JSON file records one scenario's operations and results:

```json
{
  "name": "create_document",
  "description": "Create a new empty document",
  "operations": [
    {"op": "create_document", "result": "1.1.0.1.0.1"}
  ]
}
```

## How It Works

For each scenario, the runner:

1. Starts a **fresh backend process** (`--test-mode` for in-memory storage)
2. Establishes a FEBE session (handshake + account setup)
3. Calls the scenario function, which performs operations via `XuSession`
4. Writes the returned dict as JSON
5. Kills the backend

Every scenario gets clean state. No test depends on another.

## Comparing Enfilade Backends

If you're building a new enfilade backend that speaks the FEBE protocol, you need to know where it agrees with the reference C implementation and where it diverges. Raw file diffs don't help much — they mix trivial differences (tumbler encoding, address allocation schemes) with real behavioral bugs. `compare_golden.py` solves this by comparing operation by operation and classifying each difference by severity.

Generate golden output from both servers, then compare them:

```bash
# Generate from both servers
make golden OUTPUT=/tmp/golden-c
make golden BACKEND=/path/to/my-server OUTPUT=/tmp/golden-mine

# Compare
make compare ACTUAL=/tmp/golden-mine
```

The comparison tool classifies every scenario into one of five categories:

| Classification | Meaning |
|---------------|---------|
| **match** | Identical output |
| **encoding** | Same tumbler values, different encoding (e.g., `0.14` vs `0.0.0.0.0.0.0.0.14`) |
| **address** | Different tumbler addresses but same structure (allocation scheme difference) |
| **content** | Different behavior — different content, counts, or results returned |
| **structural** | Different number of operations or missing fields |

Example output:

```
  match           96  identical output
  encoding         0  same values, different tumbler encoding
  address         87  different addresses (allocation scheme)
  content         25  different behavior (content, counts, results)
  structural      54  different operation count or missing fields
                ----
  total          263
```

**match** and **encoding** are passing. **address** means the operations work correctly but addresses are numbered differently — usually acceptable. **content** and **structural** are real behavioral differences.

### Verbose output

Use `VERBOSE=1` to see which operations differ and why:

```bash
make compare ACTUAL=/tmp/golden-mine VERBOSE=1
```

This shows per-operation, per-field diffs:

```
  ADDRESS     accounts/account_switch
             op[3].result: 1.1.0.2.0.1
                           1.1.0.2.0.2
  CONTENT     rearrange/swap_non_adjacent
             op[3].result: AFGDEBCH
                           ABCDEFGH
```

### Filter by category

```bash
make compare ACTUAL=/tmp/golden-mine CATEGORY=content
```

### Exit code

The tool exits 0 if there are no content or structural diffs (match, encoding, and address are all acceptable). Exits 1 if any content or structural diffs exist.

### Note on `generate_golden.py` output

The generator reports "ok" for every scenario that runs to completion without crashing. This means the **protocol worked**, not that the results are correct. A scenario can produce completely wrong results and still show "ok." Always use `compare_golden.py` to check actual behavioral correctness.

## Scenario Categories

| Category | Count | What it tests |
|----------|-------|---------------|
| documents | 9 | Create, open, close, reopen, conflict modes, vspan retrieval |
| content | 22 | Insert, delete, retrieve, vcopy (transclusion), rearrange |
| versions | 18 | Create version, compare versions, version chains, version isolation |
| links | 61 | Create links, find links, follow links, link survival, orphaned links |
| endsets | 8 | Retrieve endsets, endsets after mutations |
| rearrange | 10 | Pivot and swap operations |
| rearrange_semantics | 6 | Pivot placement edge cases (before/after/inside source) |
| identity | 10 | Find documents by shared I-addresses, identity through operations |
| discovery | 16 | Find documents via transclusion, versions, partial content |
| interactions | 7 | Combined operations: transclusion + links + versions |
| internal | 18 | I-span consolidation, transclusion identity, interior typing |
| edgecases | 20 | Single char ops, zero-width spans, empty documents, large inserts |
| partial-overlap | 7 | Overlapping transclusions, partial deletes across links |
| accounts | 6 | Account switching, node creation, per-account addressing |
| isolation | 6 | Cross-document isolation for insert, delete, vcopy, links |
| allocation_independence | 4 | I-address allocation ordering across operations |
| bert | 5 | Write-token enforcement (insert/delete/rearrange/copy without token) |
| provenance | 4 | I-address sharing via copy, version, delete+recopy |
| subspace | 4 | Link/text subspace separation and displacement |
| delete_all | 5 | Delete all content, then operate on empty document |
| spanfilade | 3 | Spanfilade cleanup after deleting transcluded content |
| link_poom | 3 | Link V-position observation (POOM behavior) |
| granfilade_split | 3 | Granfilade node splitting under multiple inserts |
| iaddress_allocation | 3 | I-address monotonicity and gap behavior |
| type_c_delete | 5 | Type-C interior deletion (within a single crum) |

**Total: 263 scenarios.**

## Reading a Golden File

A typical golden file (`content/insert_middle.json`):

```json
{
  "name": "insert_middle",
  "description": "Insert text in the middle of existing content",
  "operations": [
    {"op": "create_document", "result": "1.1.0.1.0.1"},
    {"op": "open_document", "doc": "1.1.0.1.0.1", "mode": "read_write",
     "result": "1.1.0.1.0.1"},
    {"op": "insert", "doc": "1.1.0.1.0.1", "address": "1.1",
     "text": "HelloWorld"},
    {"op": "insert", "doc": "1.1.0.1.0.1", "address": "1.6",
     "text": " ",
     "comment": "Insert space between Hello and World"},
    {"op": "retrieve_contents", "result": ["Hello World"]}
  ]
}
```

Key fields in each operation:
- `op` — the operation name (maps to a `session.*` method)
- `result` — what the backend returned
- `doc` — document address (when applicable)
- `comment` — human explanation (not machine-checked)

Results are **captured, not asserted**. The golden file IS the assertion. If you change the backend and the output changes, the diff tells you what changed.

## Internal State with dump_state

Some scenarios use `dump_state` to capture the backend's internal enfilade tree structure. This is the only way to see how the data structures actually change in response to operations.

The `internal/internal_state.json` golden file captures the tree before and after inserting "Hello, World!":

```json
{"op": "dump_state", "state": {
  "granf": {
    "depth": 0, "height": 2, "enftype": "GRAN",
    "wid": ["1.1.0.1.0.1.0.1.1"],
    "children": [
      {"enftype": "GRAN", "infotype": 0, "comment": "document node"},
      {"enftype": "GRAN", "infotype": 2, "orgl": {
        "enftype": "POOM",
        "wid": ["0.0.0.0.0.0.0.0.13", "0.13"],
        "dsp": ["1.1.0.1.0.1.0.1.1", "1.1"],
        "comment": "POOM maps 13 I-addresses to 13 V-positions"
      }},
      {"enftype": "GRAN", "infotype": 1, "text": "Hello, World!"}
    ]
  },
  "spanf": {"enftype": "SPAN", "wid": ["0", "0.0.0.0.0.0.0.0.13"]}
}}
```

What you can read from this:
- **granfilade** has three children: a document node (infotype 0), a POOM orgl (infotype 2), and a text crum (infotype 1)
- **POOM** shows width `[0.13, 0.13]` — 13 I-addresses mapped to 13 V-positions, with displacements showing where in I-space and V-space they start
- **spanfilade** shows the span index with width `0.13` — 13 characters indexed
- **text crum** holds the actual bytes

The dump_state scenarios are particularly useful for understanding how operations like insert, delete, and transclusion change the tree structure. Comparing the before/after dumps shows exactly which nodes were added, split, or modified.
