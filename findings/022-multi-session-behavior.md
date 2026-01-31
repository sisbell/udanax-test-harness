# Finding 022: Multi-Session Behavior

## Summary

When multiple FEBE sessions connect to the same `backenddaemon`, they share global state (documents, links, content identity) while maintaining isolated session state (current account).

## Evidence

Tests in `golden/multisession/` demonstrate these behaviors.

## Key Findings

### 1. Session Isolation for Account Context

Each session maintains its own account state. Changing accounts in session A does not affect session B:

```
Session A: account(1.1.0.1)
Session B: account(1.1.0.1)
Session A: create_document() → 1.1.0.1.0.1
Session A: account(1.1.0.2)              # A switches accounts
Session B: create_document() → 1.1.0.1.0.2   # B still uses 1.1.0.1
Session A: create_document() → 1.1.0.2.0.1   # A uses new account
```

**Evidence:** `session_isolation.json`

### 2. Global Address Allocation

Document addresses are globally unique, even when multiple sessions use the same account:

```
Both sessions: account(1.1.0.1)
Session A: create_document() → 1.1.0.1.0.1
Session B: create_document() → 1.1.0.1.0.2
```

The backend maintains a per-account counter that is shared across all sessions.

**Evidence:** `concurrent_write_same_account.json`

### 3. Global Link Visibility

Links are stored in a global database and visible to all sessions:

```
Session A: create_link(source, target) → link_id
Session B: find_links(source) → [link_id]
```

Session B can discover links created by session A without any special coordination.

**Evidence:** `cross_session_link_visibility.json`

### 4. Content Identity Across Sessions

When session A transcludes content from session B's document, content identity is preserved:

```
Session B: create_document(source), insert("Shared content")
Session A: create_document(dest), vcopy(source → dest)
compare_versions(dest, source) → shared spans detected
```

The SPORGL (provenance tracking) system maintains content identity globally.

**Evidence:** `cross_session_transclusion.json`

### 5. CONFLICT_COPY Creates Separate Copies

When both sessions open the same document with `CONFLICT_COPY`:
- Each session works on an independent copy
- Changes are NOT merged
- Final state depends on which copy is accessed

```
Document contains: "AAAA____BBBB"
Session A: opens with CONFLICT_COPY, changes AAAA → XXXX
Session B: opens with CONFLICT_COPY, changes BBBB → YYYY
Final read: "XXXX____BBBB" (only A's changes visible)
```

**Implication:** True concurrent editing requires application-level merge logic.

**Evidence:** `concurrent_edit_different_regions.json`

### 6. Version Addresses Are Unique Per Session

When multiple sessions create versions of the same document:

```
Session A: create_version(original) → version_a
Session B: create_version(original) → version_b
version_a ≠ version_b
```

Each version can be modified independently while sharing content identity with the original.

**Evidence:** `concurrent_versioning.json`

## Architecture

The `backenddaemon` (bed.c + socketbe.c):
- Listens on TCP port (default 55146)
- Maintains a `player[]` array for connected sessions
- Uses `select()` for multiplexing
- Maximum 25 concurrent connections (MAX_PLAYERS)
- Each player has: socket, input/output streams, account, wantsout flag

Global state shared across sessions:
- Enfilades (granf, spanf)
- Document storage (disk.c)
- Link storage
- Content identity (SPORGL)

Per-session state:
- Current account (set via `account()` command)
- Open document handles
- Connection socket

## Implications for Xanadu Semantics

1. **Documents are globally addressable** - Any session can read any document by address
2. **Links are global annotations** - Content carries its links regardless of who created them
3. **Content identity transcends sessions** - Transclusion works across session boundaries
4. **No built-in concurrent edit merging** - Applications must handle this
5. **Accounts are session-local context** - Not authentication, just a namespace selector

## Related

- Finding 021: Address Allocation Mechanism
- Finding 018: Content Identity Tracking
- Finding 004: Link Endpoint Semantics
