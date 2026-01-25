# C Backend Modernization

Changes made to compile the original 1999 K&R C code with modern clang. All changes preserve original behavior.

## Phase 1: 32-bit Integer Fixes

| Change | Files | Purpose |
|--------|-------|---------|
| `INT` → `int32_t` | common.h | 64-bit compatibility |
| `unsigned INT` → `UINT` | common.h | Unsigned 32-bit type |

## Phase 2: K&R to ANSI Function Declarations

| Change | Files | Purpose |
|--------|-------|---------|
| K&R declarations → ANSI prototypes | All .c files | Modern compiler support |

## Phase 3: Type and Signature Fixes

| Change | Files | Purpose |
|--------|-------|---------|
| Added function prototypes | protos.h (50+) | Compile-time type checking |
| `return;` → `return(0);` | tumble.c, put.c, putfe.c, test.c | Return value in int functions |
| Forward declarations | test.c, recombine.c, tumble.c, multiloaf.c | Functions called before definition |
| `void *crash()` → `void crash(int)` | socketbe.c, players.h | Signal handler signature |
| Added `<string.h>` | rcfile.c | Missing include |
| Added `<fcntl.h>` | disk.c | Missing include |
| `NULL` → `0` | do1.c | INT parameter type |
| Pointer casts for foohex | credel.c, granf2.c | Debug print type safety |

## Name Changes

These are the only changes that affect function/macro names in algorithm code:

| File | Original | Changed To | Reason |
|------|----------|------------|--------|
| recombine.c | `macrogetrightbro` | `findrightbro` | Macro uses lvalue cast (illegal in modern C); function has identical behavior |

Both `macrogetrightbro` and `findrightbro` perform the same operation: traverse to right sibling while calling `rejuvinateifnotRESERVED`.

## Phase 4: Runtime Fixes and Test Mode

| Change | Files | Purpose |
|--------|-------|---------|
| Disabled `NEWALLOC` | credel.c | Prevented 6M+ pre-allocations at startup |
| Added `continue` after `xgrabmorecore` | credel.c | Fix crash when grimreaper list empty during initial alloc |
| Added `--test-mode` flag | be.c, disk.c, diskalloc.c | In-memory storage for testing (no disk persistence) |

## Test Mode

Run the backend with `--test-mode` for in-memory storage:

```bash
./build/backend --test-mode
```

In test mode:
- No `enf.enf` file is created
- All state is held in memory
- State is discarded when process exits
- Useful for golden test generation (restart per test for clean state)
