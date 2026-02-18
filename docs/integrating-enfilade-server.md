# Integrating an Enfilade Server

Udanax Green is an enfilade server. Every operation — insert, delete, copy, links, versions — is a manipulation of enfilade trees: the granfilade stores content, the spanfilade indexes spans, and the POOM maps between I-space and V-space. The FEBE protocol is the wire interface to this server.

If you've built a custom enfilade server and want to integrate it with the FEBE protocol, the golden test suite validates that your server produces the correct observable behavior. You connect your server to the same test runner that drives the C reference implementation, generate output, and compare operation by operation to see where you match and where you diverge.

This doc covers what your server must implement to speak the FEBE protocol, how to connect it to the test runner, and how to develop incrementally using the golden output as your guide.

## How the Test Runner Connects

The test runner communicates via `PipeStream`: it creates a named FIFO, launches your server with stdin redirected from the FIFO, and reads your stdout. For each of the 263 scenarios, it starts a **fresh process** — no state carries over between scenarios.

```
Python test runner
    |
    | PipeStream("/path/to/server --test-mode")
    |   creates FIFO: pyxi.<pid>
    |   launches: server --test-mode < pyxi.<pid>
    |   writes commands to FIFO
    |   reads responses from stdout
    |
    v
Your enfilade server
    reads stdin  (FEBE protocol)
    writes stdout (FEBE protocol)
```

## What Your Server Must Implement

Your binary must:

1. **Accept `--test-mode`** — run with in-memory storage, no disk persistence. Each scenario starts a fresh process, so state doesn't carry over.

2. **Perform the handshake** — on startup, read bytes until `\n`, then read `P0~`. Respond with `\nP0~`.

3. **Enter a command loop** — repeatedly read a command code (integer terminated by `~`), read that command's arguments, write the response, and flush stdout.

4. **Echo the command code** — every response starts by writing back the command code. The Python client checks this to confirm the response matches the request.

5. **Handle at minimum**:
   - Command 34 (ACCOUNT): read one tumbler address, echo `34~`
   - Command 16 (QUIT): clean exit

   Every scenario begins with ACCOUNT (to set the working account) and ends with QUIT. If you only implement these two, every scenario will fail on its first real operation — but you'll confirm the handshake and command loop work.

6. **Flush after every response** — the Python client blocks reading until it gets the response. If you buffer stdout without flushing, both sides deadlock.

## Commands

The 263 scenarios use 18 distinct commands. You don't need all of them — scenarios that hit an unimplemented command will fail and the runner moves on. But unimplemented commands should consume their wire arguments before returning an error, otherwise leftover bytes corrupt the next command read.

See `docs/febe-protocol.md` for the full wire format and `docs/client-api.md` for the Python client's view of each command.

The commands, roughly ordered by how many scenarios depend on them:

| Code | Name | Scenarios using it |
|------|------|--------------------|
| 34 | ACCOUNT | all |
| 11 | CREATE_DOCUMENT | all |
| 35 | OPEN_DOCUMENT | nearly all |
| 36 | CLOSE_DOCUMENT | nearly all |
| 0 | INSERT | ~200 |
| 1 | RETRIEVE_VSPANSET | ~180 |
| 5 | RETRIEVE_CONTENTS | ~170 |
| 16 | QUIT | all |
| 27 | CREATE_LINK | ~80 |
| 2 | COPY (vcopy) | ~40 |
| 13 | CREATE_VERSION | ~35 |
| 12 | DELETE | ~30 |
| 30 | FIND_LINKS | ~25 |
| 22 | FIND_DOCUMENTS | ~20 |
| 3 | REARRANGE | ~16 |
| 10 | COMPARE_VERSIONS | ~10 |
| 28 | RETRIEVE_ENDSETS | ~8 |
| 18 | FOLLOW_LINK | ~8 |
| 14 | RETRIEVE_VSPAN | ~5 |
| 38 | CREATE_NODE | ~5 |
| 39 | DUMP_STATE | 1 |

Implementing the top 8 (through QUIT) covers the majority of scenarios.

### A note on DUMP_STATE (command 39)

DUMP_STATE is unlike the other commands. It serializes the C backend's internal enfilade tree structure — granfilade nodes, spanfilade nodes, POOM orgls, infotypes, wids, dsps, children — in a custom wire format. The golden output captures a complete snapshot of the tree before and after operations (see `docs/golden-tests.md` for an example).

If your enfilade server uses different internal structures, you have two options: emit the same wire format mapped from your representation, or stub the command. Only one scenario uses it (`internal/internal_state`), so stubbing it won't affect the rest of the suite.

## Running Your Server

From the repo root:

```bash
make golden BACKEND=/path/to/my-server OUTPUT=/tmp/my-golden
```

The runner launches your server exactly as it launches the C implementation. Output goes to a separate directory so you can compare against the reference.

To test a single scenario while developing:

```bash
make golden BACKEND=/path/to/my-server SCENARIO=insert_text
```

## Comparing Against the Reference

Generate golden output from both servers, then compare:

```bash
# Reference (C enfilade server)
make golden OUTPUT=/tmp/golden-ref

# Your server
make golden BACKEND=/path/to/my-server OUTPUT=/tmp/golden-mine

# Compare
make compare ACTUAL=/tmp/golden-mine
```

See `docs/golden-tests.md` for details on reading the comparison output and understanding the difference classifications (match, encoding, address, content, structural).

## Kinds of Differences You'll See

Not all differences mean your server is wrong:

**Address allocation.** Your server may number documents, versions, or links differently. The C server uses per-account counters and hierarchical version addresses (e.g., version of `1.1.0.1.0.1` gets address `1.1.0.1.0.1.1`). If your server uses a different scheme, these diffs will cascade through many scenarios — even ones where the operations themselves are correct.

**Tumbler encoding.** The same tumbler value can be written with different numbers of leading zeros. `0.14` and `0.0.0.0.0.0.0.0.14` decode identically, but the JSON representation differs.

**Behavioral.** The operation actually produces different results — different content, different spans, different link discovery. These are the diffs that matter.

To separate address/encoding diffs from behavioral diffs, start by looking at scenarios that don't involve versions or links: `content/insert_text`, `content/delete_text`, `documents/create_document`. If those match, your wire protocol is solid and the remaining diffs are in higher-level semantics.

## Incremental Development

You don't need to implement everything at once. A practical order:

1. Handshake + ACCOUNT + QUIT — confirms the pipe works
2. CREATE_DOCUMENT + OPEN/CLOSE — confirms tumbler read/write
3. INSERT + RETRIEVE_VSPANSET + RETRIEVE_CONTENTS — confirms content operations
4. Run `make golden BACKEND=... SCENARIO=insert_text` to validate end-to-end
5. Add commands as needed, using the golden diffs to guide you

Each step unlocks more passing scenarios. The comparison tool tells you exactly which scenarios your server handles correctly and which still diverge.
