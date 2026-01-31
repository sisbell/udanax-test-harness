# Multi-Session Test Scenarios

Tests for behavior when multiple FEBE sessions interact with the same backend.

## Running Tests

```bash
cd febe

# Run all single-session tests
python3 generate_golden.py

# Run all multi-session tests
python3 tests/generate_multisession_golden.py

# Run specific multi-session test
python3 tests/generate_multisession_golden.py --scenario cross_session_doc_visibility

# Verbose output for debugging
python3 tests/generate_multisession_golden.py --verbose

# List available multi-session tests
python3 tests/generate_multisession_golden.py --list
```

**Requirements:** The backend binaries must be built:
```bash
cd backend && make
```

## Test Scenarios

| Scenario | Description |
|----------|-------------|
| `cross_session_doc_visibility` | Session A creates document, session B reads it |
| `concurrent_document_creation` | Both sessions create documents with interleaved operations |
| `concurrent_write_same_account` | Both sessions use same account - verifies unique addresses |
| `cross_session_link_visibility` | Session A creates link, session B finds it |
| `concurrent_versioning` | Both sessions create versions of the same document |
| `cross_session_transclusion` | Session A transcludes from document created by session B |
| `session_isolation` | Account changes in one session don't affect another |
| `concurrent_edit_different_regions` | Both sessions edit non-overlapping regions |
| `link_from_session_a_to_session_b_doc` | A creates link pointing to B's document |
| `node_creation_cross_session` | A creates node, both sessions create docs in it |

## Key Findings

### Document Address Allocation

When multiple sessions create documents under the **same account**, each gets a unique address:

```
Session A (account 1.1.0.1): creates 1.1.0.1.0.1
Session B (account 1.1.0.1): creates 1.1.0.1.0.2
```

The backend maintains a global counter per account, ensuring no collisions.

### Session Isolation

Each session maintains **independent account state**. Switching accounts in session A does not affect session B:

```
A: account(1.1.0.1)
B: account(1.1.0.1)
A: create_document() → 1.1.0.1.0.1
A: account(1.1.0.2)           # A switches
B: create_document() → 1.1.0.1.0.2   # B still under 1.1.0.1
A: create_document() → 1.1.0.2.0.1   # A under 1.1.0.2
```

### Link Visibility

Links are **globally visible** across all sessions. A link created by session A can be found by session B searching the same content:

```
A: create_link(source_doc, target_doc) → link_id
B: find_links(source_doc) → [link_id]  # B finds A's link
```

### Content Identity (Transclusion)

When session A transcludes content from session B's document, **content identity is preserved**:

```
B: create_document() → source_doc
B: insert(source_doc, "Shared content from B")

A: create_document() → dest_doc
A: insert(dest_doc, "A's prefix: ")
A: vcopy(from=source_doc, to=dest_doc)  # Transclude "Shared content"

compare_versions(dest_doc, source_doc) → shared spans found
```

The `compare_versions` operation confirms the transcluded content shares identity.

### Concurrent Editing with CONFLICT_COPY

When both sessions open the same document with `CONFLICT_COPY`:

- Each session gets a **separate working copy**
- Changes are **not merged** between copies
- The final state depends on which copy is read

```
A: open_document(doc, READ_WRITE, CONFLICT_COPY)
B: open_document(doc, READ_WRITE, CONFLICT_COPY)

A: delete + insert at position 1-4
B: delete + insert at position 9-12

# Result: Only one session's changes visible (no merge)
```

**Implication:** For true concurrent editing, applications need to implement their own merge logic or use versioning.

### Version Creation

When multiple sessions create versions of the same document, each gets a **unique version address**:

```
A: create_version(original) → version_a
B: create_version(original) → version_b

version_a ≠ version_b  # Different addresses
```

Both versions share content identity with the original but can be modified independently.

## Architecture Notes

Multi-session tests use `backenddaemon` which:
- Listens on TCP port (default 55146, configurable via `.backendrc`)
- Supports up to 25 concurrent connections
- Maintains shared state across all sessions
- Each session has independent account context

The test runner:
1. Starts a fresh daemon for each test scenario
2. Connects two TCP sessions (A and B)
3. Runs the scenario with interleaved operations
4. Captures results as JSON golden files
5. Cleans up daemon and data directory

## Output

Golden test files are written to `golden/multisession/`:
```
golden/multisession/
├── concurrent_document_creation.json
├── concurrent_edit_different_regions.json
├── concurrent_versioning.json
├── concurrent_write_same_account.json
├── cross_session_doc_visibility.json
├── cross_session_link_visibility.json
├── cross_session_transclusion.json
├── link_from_session_a_to_session_b_doc.json
├── node_creation_cross_session.json
└── session_isolation.json
```
