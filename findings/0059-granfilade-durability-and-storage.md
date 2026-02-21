# Finding 0059: Granfilade Durability and Storage Organization

**Date:** 2026-02-10
**Category:** Storage / Persistence
**Related:** Finding 0012 (Dual Enfilade Architecture), Finding 0034 (Byte-Opaque Storage)

## Summary

The granfilade (content store implementing σ : I → B) uses **write-through persistence** with a **unified disk file** shared by all enfilades. Text bytes are written to disk **lazily via a grim reaper cache eviction mechanism**, not immediately on INSERT. The POOM and granfilade share the same buffer/cache system and disk file format.

## Storage Organization

### Single Unified Disk File: `enf.enf`

All persistent state lives in **one file**: `enf.enf`

```c
// From disk.c:364-382
fd = open("enf.enf", 2 /*rw*/, 0);
if (fd == -1) {
    fd = creat("enf.enf", 0666);
    initheader();
}
```

**File structure:**
```
Block 0..N:          Disk header (bitmap + metadata)
Block N+1:           granf root (GRANFDISKLOCATION)
Block N+2:           spanf root (SPANFDISKLOCATION)
Block N+3...:        Allocated loaves (nodes/atoms)
```

From `coredisk.h:117-120`:
```c
#define NUMDISKLOAFSINHEADER (sizeof(diskheader)/NUMBYTESINLOAF+1)
#define GRANFDISKLOCATION (NUMDISKLOAFSINHEADER+1)
#define SPANFDISKLOCATION (NUMDISKLOAFSINHEADER+2)
```

### Disk Block Structure

**Block size:** `NUMBYTESINLOAF` bytes (typically 1024)

**Block types:**
- **Upper crums (typeduc):** Internal B-tree nodes with child pointers
- **Bottom crums (typedbc):** Leaf nodes containing data
  - `GRANTEXT`: Text atoms (up to 950 bytes: `GRANTEXTLENGTH`)
  - `GRANORGL`: Document/POOM references
  - Other enfilade-specific data

**Layout** (from `coredisk.h:11-21`):
```c
typedef struct structdiskloafhedr {
    INT sizeofthisloaf;
    SINT isapex;           // TRUE if this is top of orgl
    SINT height;           // 0 = bottom crum (leaf)
    SINT denftype;         // GRAN, SPAN, or POOM
    SINT numberofcrums;
    SINT refcount;         // For subtree sharing / GC
    SINT allignmentdummy;
} typediskloafhedr;
```

Each block can contain **multiple sub-loaves** (uber-loaf packing):
```c
// From coredisk.h:66-71
typedef struct structuberdiskloaf {
    INT versiondisknumber;
    unsigned short numberofunterloafs;  // Sub-loaves in this block
    SINT anoherallignmentdummy;
    typediskloaf fakepartialuberloaf;
} typeuberdiskloaf;
```

### All Enfilades Share One File

There is **no separation** between:
- The granfilade (permascroll / content store)
- The POOM enfilades (document structure)
- The spanfilade (link index)

They are all stored in `enf.enf` using the same block allocator and same on-disk format. Only the `denftype` field (GRAN vs SPAN vs POOM) distinguishes them.

## When Are Bytes Written to Disk?

### INSERT Flow

When `INSERT` is called:

1. **Text is copied into in-memory crum** (`insert.c:17-70`):
   ```c
   int insertseq(typecuc *fullcrumptr, tumbler *address,
                 typegranbottomcruminfo *info) {
       // Text stored in typecbc->cinfo.granstuff.textstuff.textstring
       movmem(textset->string,
              locinfo.granstuff.textstuff.textstring,
              locinfo.granstuff.textstuff.textlength);
       insertseq((typecuc*)fullcrumptr, &lsa, &locinfo);
   }
   ```

2. **Crum is marked modified** (`genf.c:522-544`):
   ```c
   int ivemodified(typecorecrum *ptr) {
       while (ptr) {
           ptr->modified = TRUE;
           ptr = ptr->leftbroorfather;  // Mark ancestors
       }
   }
   ```

3. **Modified crums stay in RAM** until:
   - Memory pressure triggers the **grim reaper**
   - Session ends and `writeenfilades()` is called
   - Explicit flush (not exposed via FEBE)

### The Grim Reaper Cache Eviction

**When memory runs low** (`credel.c:54-76`):
```c
INT *ealloc(unsigned nbytes) {
    for (;;) {
        ret = (char *)falloc(nbytes+sizeof(tagtype));
        if (ret) {
            return (INT *)(ret+sizeof(tagtype));
        }
        if (grimreaper == NULL) {
            xgrabmorecore();
            continue;
        }
        grimlyreap();  // <-- Write old crums to disk
    }
}
```

**Grim reaper logic** (`credel.c:106-162`):
- Circular list of all in-memory crums (`grimreaper` global)
- Each crum has an `age` counter
- When memory needed:
  - Scan for crums with `age >= OLD` and not `RESERVED`
  - If modified: write subtree to disk via `reap() → orglwrite()`
  - Free memory

**Write to disk** (`corediskout.c:300-356`):
```c
int orglwrite(typecbc *orglcbcptr) {
    if (!orglcbcptr->modified && orglptr) {
        orglfree(orglptr);  // Already on disk, just free
        return(0);
    }
    if (infoptr->granstuff.orglstuff.orglincore) {
        subtreewriterecurs(taskptr, orglptr);  // Write children
        size = packloaf(orglptr, &loaf, 1, 1); // Serialize
        writeloaf(&loaf, temploaf, newloaf);   // Disk I/O
    }
}
```

### Session Exit

**When the backend daemon exits** (`bed.c:134, 183`):
```c
writeenfilades();
closediskfile();
```

**What this does** (`corediskout.c:68-88`):
```c
int writeenfilades(void) {
    typecbc temporgl;
    temporgl.modified = TRUE;
    temporgl.cinfo.granstuff.orglstuff.diskorglptr.diskblocknumber
        = GRANFDISKLOCATION;
    temporgl.cinfo.granstuff.orglstuff.orglptr = (typecuc *)granf;
    orglwrite(&temporgl);  // Write entire granfilade

    temporgl.cinfo.granstuff.orglstuff.diskorglptr.diskblocknumber
        = SPANFDISKLOCATION;
    temporgl.cinfo.granstuff.orglstuff.orglptr = (typecuc *)spanf;
    orglwrite(&temporgl);  // Write entire spanfilade
}
```

This recursively writes **all modified crums** in both enfilades to disk.

## Cache/Buffer Mechanism

### Shared Cache for All Enfilades

**Single cache system:**
- All crums (GRAN, SPAN, POOM) participate in the same LRU-like list
- The `grimreaper` pointer forms a circular list of **all** in-memory crums
- No per-enfilade isolation

**Crum lifecycle:**

1. **Creation** (`credel.c:518-532`):
   ```c
   typecorecrum *createcrum(INT crumheight, INT enftype) {
       ptr = createcruminternal(crumheight, enftype, NULL);
       if (grimreaper) {
           ptr->nextcrum = grimreaper;
           ptr->prevcrum = grimreaper->prevcrum;
           grimreaper->prevcrum->nextcrum = ptr;
           grimreaper->prevcrum = ptr;
       } else {
           grimreaper = ptr->nextcrum = ptr->prevcrum = ptr;
       }
       return(ptr);
   }
   ```

2. **Access** (`corediskin.c`): Reading from disk brings crums into cache

3. **Eviction** (`credel.c:106-162`): Age-based LRU eviction writes modified crums

**No write-back buffer** separate from the cache. The in-memory tree **is** the cache.

### Reading from Disk

**On-demand loading** (`disk.c:200-239`):
```c
void readloaf(typeuberrawdiskloaf *loafptr, INT blocknumber) {
    if (lseek(enffiledes, (long)blocknumber*NUMBYTESINLOAF, 0) < 0) {
        gerror("lseek failed\n");
    }
    if (read(enffiledes, (char*)loafptr, sizeof(*loafptr)) <= 0) {
        qerror("read");
    }
    ++nolread;  // Track I/O count
}
```

**Immediate disk I/O**: No read buffering beyond OS page cache.

### Writing to Disk

**Synchronous writes** (`disk.c:300-338`):
```c
void actuallywriteloaf(typeuberrawdiskloaf *loafptr, INT diskblocknumber) {
    if (lseek(enffiledes, (long)diskblocknumber*NUMBYTESINLOAF, 0) < 0) {
        gerror("lseek failed\n");
    }
    if (write(enffiledes, (char*)loafptr, sizeof(*loafptr)) <= 0) {
        qerror("write\n");
    }
    ++nolwrote;  // Track I/O count
}
```

**No batching**: Each `writeloaf()` is an immediate `write()` syscall. No fsync/flush guarantees though—relies on OS buffering.

## Durability Guarantees

### What IS Durable

**On session exit:**
- All modified crums are written to disk via `writeenfilades()`
- Disk header (bitmap, allocation table) is updated via `writeallocinfo()`

**On crash/kill:**
- Only crums written by grim reaper during eviction survive
- Recent INSERTs may be lost if they're still in the cache

### What Is NOT Durable

**No transaction log**: INSERT → RETRIEVE within the same session works because of the in-memory cache, not because bytes are guaranteed on disk.

**No fsync**: `write()` calls go to OS buffers. Kernel decides when to flush.

**No per-operation durability**: The system assumes long-lived sessions. Short-lived sessions that crash lose data.

## Architectural Consequences

### 1. Granfilade and POOM Are Not Separate

The "permascroll" (content store) and POOM (document structure) use:
- **Same disk file** (`enf.enf`)
- **Same cache** (grim reaper list)
- **Same write mechanism** (`orglwrite`)

The distinction is semantic (GRAN vs POOM enftype), not physical.

### 2. Text Bytes Are Not Immediately Durable

```
Client: INSERT("hello")
Backend: Stores in RAM, marks modified
Client: RETRIEVE → returns "hello" (from cache)
[System crash]
Restart: Content lost if not yet written
```

**Durability depends on:**
- Session lifetime
- Memory pressure triggering grim reaper
- Explicit backend shutdown

### 3. No Isolation Between Enfilades

Memory pressure evicts **any** old crum—text, POOM nodes, or link index entries. A large link search could evict modified text atoms before they're written.

### 4. Disk Format Is B-Tree Nodes

The permascroll is **not** a flat file of bytes. It's a B-tree of crums:
- Internal nodes: `typeduc` with child pointers
- Leaf nodes: `typedbc` with `GRANTEXT` containing up to 950 bytes

Retrieving content at I-address X requires:
- Tree traversal (multiple disk reads)
- Copying bytes from crum's textstring field

## Comparison to Ideal σ : I → B

**Conceptual model:** σ maps I-space addresses to bytes, implying direct addressing.

**Actual implementation:**
- σ is a B-tree index
- Bytes are stored in variable-sized atoms (up to 950 bytes)
- I-addresses map to (blocknumber, offset within block)
- Retrieval requires tree walk, not direct lookup

**Why:** 1980s systems couldn't afford gigabyte-sized flat files. B-trees provided efficient sparse storage.

## Related Findings

- **Finding 0012:** Dual enfilade architecture (granf vs spanf)
- **Finding 0034:** Byte-opaque storage (no character encoding)
- **Finding 0022:** Multi-session behavior (shared disk state)

## Files

| File | Role |
|------|------|
| `disk.c` | Low-level disk I/O (read/write blocks) |
| `diskalloc.c` | Block allocator (bitmap management) |
| `coredisk.h` | Disk format structures |
| `corediskout.c` | Serialization (memory → disk) |
| `corediskin.c` | Deserialization (disk → memory) |
| `credel.c` | Grim reaper cache eviction |
| `insert.c` | Text insertion into granfilade |
| `entexit.c` | Initialization (`initenffile`, `writeenfilades`) |

## Code Citations

**Storage file:**
- `disk.c:364`: Open/create `enf.enf`
- `coredisk.h:119-120`: Fixed disk locations for granf/spanf

**INSERT flow:**
- `granf2.c:83-101`: `inserttextgr` copies text into crum
- `insert.c:17-70`: `insertseq` creates new leaf crum
- `genf.c:522`: `ivemodified` marks tree dirty

**Durability:**
- `corediskout.c:68`: `writeenfilades` writes all modified crums
- `bed.c:134`: Daemon exit calls `writeenfilades`
- `credel.c:106`: `grimlyreap` evicts old crums, triggering writes

**Shared cache:**
- `credel.c:15`: `typecorecrum *grimreaper` global
- `credel.c:523`: `createcrum` adds to circular list
- `credel.c:147`: `isreapable` checks age/modified flags
