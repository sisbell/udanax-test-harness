# Finding 0034: Byte-Opaque Storage (No Character Encoding)

**Date discovered:** 2026-02-03
**Category:** Storage Model

## Summary

Udanax-green treats content as **opaque bytes**. It has no concept of character encoding - not ASCII, not UTF-8, not any encoding. Each byte is stored and retrieved independently, with each byte position assigned exactly one I-space address.

## Key Behaviors Verified

### 1. Storage Structure

Text is stored in `typegrantext`:
```c
typedef struct structgrantext {
    char textstring[GRANTEXTLENGTH];  // GRANTEXTLENGTH = 950 bytes
    unsigned textlength;              // byte count
} typegrantext;
```

`char` in C is a single byte (8 bits). The system stores raw bytes with no encoding interpretation.

### 2. Byte-Level Copy

Content retrieval uses `movmem` (mapped to `memmove`):
```c
// From context.c:308
movmem(&context->contextinfo.granbottomcruminfo.granstuff.textstuff.textstring[i],
       ((typetext *)vstuffset)->string,
       ((typetext *)vstuffset)->length);
```

This is a raw byte copy - no encoding conversion, no character boundary checking.

### 3. Width Equals Byte Count

When text is inserted, the `length` field equals byte count:
```c
// From xumain.c:143
textsetptr->length = strlen(textsetptr->string);
```

V-space width = number of bytes. A 5-character UTF-8 string that uses 10 bytes occupies 10 V-space positions.

### 4. No Validation

No part of the backend validates:
- That bytes are valid ASCII (0-127)
- That bytes form valid UTF-8 sequences
- Character boundaries during partial retrieval or deletion

## Implications

### 1. UTF-8 Is Supported By Accident

UTF-8 works because it's just bytes. The backend doesn't care what the bytes represent.

**Example:**
- UTF-8 string "hello" (5 bytes) -> width 0.5
- UTF-8 string "hello\xc3\xa9" (7 bytes, includes e-acute) -> width 0.7
- Emoji "\xf0\x9f\x98\x80" (4 bytes) -> width 0.4

### 2. Partial Retrieval Can Split Characters

Retrieving positions 1-3 of a UTF-8 string might return invalid UTF-8 if a multi-byte character straddles the boundary.

**Example:**
```
Content: "caf\xc3\xa9" (cafe with e-acute = 5 bytes)
V-space: 1.1 through 1.5

Retrieve V-span [1.1, 1.4]: Returns "caf\xc3" - invalid UTF-8
```

The backend doesn't protect against this.

### 3. Transclusion Preserves Byte Identity

When you vcopy content, byte identity is preserved. The same byte at the same I-address appears in multiple documents. This means:
- If the original was UTF-8, the transclusion is UTF-8
- If the original was Latin-1, the transclusion is Latin-1
- Mixed encodings in the same document are possible

### 4. Link Endpoints Are Byte-Addressed

Links point to I-addresses (permascroll positions). Since each byte has its own I-address, link endpoints can point into the middle of multi-byte characters.

## Verified Through Code Analysis

**Storage layer:**
- `wisp.h:76`: `char textstring[GRANTEXTLENGTH]` - byte array
- `common.h:115`: `#define GRANTEXTLENGTH 950` - max bytes per atom

**Copy operations:**
- `context.c:308`: `movmem()` for raw byte copy
- `corediskout.c:242`: Same for disk persistence

**Length tracking:**
- `wisp.h:77`: `unsigned textlength` - byte count, not character count
- `xumain.c:143`: `strlen()` used for length - byte count

## Design Intent

This appears intentional:
1. 1980s computing didn't have Unicode
2. ASCII was dominant; other encodings existed (ISO-8859, etc.)
3. Treating bytes as opaque allows any encoding
4. The frontend/application layer handles encoding interpretation

## Consequences for Modern Use

| Aspect | Behavior |
|--------|----------|
| UTF-8 storage | Works (bytes stored correctly) |
| UTF-8 retrieval | Works (bytes returned correctly) |
| Partial character retrieval | Allowed (can return invalid UTF-8) |
| Character-aware deletion | Not supported (must calculate byte offsets) |
| Character-aware links | Not supported (links are byte-addressed) |

## Related

- **Finding 0010:** Unified storage abstraction (all content is byte-addressed)
- **Finding 0009:** Document address space structure (I-space is byte-addressed)
