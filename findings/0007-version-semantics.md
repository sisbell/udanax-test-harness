# Finding 0007: Version Semantics and Content Identity

**Date:** 2026-01-30
**Status:** Validated via golden tests
**Tests:** `golden/versions/*.json` (15 scenarios)

## Summary

Versions in Udanax Green implement copy-on-write semantics with preserved content identity. This has profound implications for transclusion and links.

## Key Findings

### 1. Versions Are Fully Independent

Once created, a version is a separate document that can be modified independently:

- **Deleting from version doesn't affect original** (`version_delete_preserves_original`)
- **Deleting from original doesn't affect version** (`delete_from_original_check_version`)
- **Modifying original after versioning doesn't affect version** (`modify_original_after_version`)
- **Both can be modified independently** (`both_versions_modified`)

This is true copy-on-write: the version starts as a logical copy sharing content identity with the original, but edits create new content without affecting the other.

### 2. Content Identity Is Preserved Through Versioning

When you create a version, the content maintains its identity. This means:

```
Original: "Shared base content"
Version:  "Shared base content"  (same content identity)

After modifying version:
Original: "Shared base content"
Version:  "version-only Shared base content"

compare_versions() still finds shared region: "Shared base content"
```

The `compare_versions` operation finds shared content because both documents reference the same underlying content identity, not because the bytes happen to match.

### 3. Transclusion Identity Is Preserved in Versions

If document A transcludes content from document B, and you create a version of A, the version also shares content identity with B:

```
Source:  "Shared transcluded content"
Doc:     "Prefix: Shared"  (vcopy from Source)
Version: "Prefix: Shared"  (version of Doc)

compare_versions(Version, Source) finds "Shared" as shared content!
```

**Test:** `version_preserves_transclusion`

This means transclusion relationships are inherited through versioning - a fundamental Xanadu principle.

### 4. Links Transfer to Versions (Critical Finding)

**Links are bound to content identity, not document addresses.**

When you create a link from "here" in document A to document B, and then create a version of A:

```
Source:  "Click here for info"  (link on "here" points to Target)
Version: "Click here for info"  (version of Source)

find_links(Source)  → [link_id]
find_links(Version) → [link_id]  (SAME LINK!)
```

**Test:** `version_with_links`

The version can find the same link because:
1. The version shares content identity with the original for "here"
2. Links are attached to content identity, not document identity
3. Therefore, any document containing that content identity can discover the link

This is a key Xanadu semantic: **links follow content, not containers**.

### 5. Insert in Middle Splits Content Identity

When you insert text in the middle of versioned content, the original content identity is split into two regions:

```
Original: "FirstSecond"
Version:  "First MIDDLE Second"  (insert " MIDDLE " at position 6)

compare_versions() finds TWO shared regions:
  - "First" (width 5) at original:1.1, version:1.1
  - "Second" (width 6) at original:1.6, version:1.14
```

**Test:** `version_insert_in_middle`

The content identity of "First" and "Second" is preserved, but they are now at different positions in the version.

### 6. Cross-Version Operations

Content can be copied between versions:

```
Original: "Original text"
Version:  "Original text with version-only addition"

vcopy "version-only" from Version to Original:
Original: "Original textversion-only"

compare_versions() finds both shared regions:
  - "Original text" (from original creation)
  - "version-only" (from vcopy back)
```

**Test:** `cross_version_vcopy`

### 7. Transitive Content Sharing

Content identity is transitive across version chains:

```
v1: "Original from v1"
v2: "Original from v1 plus v2"  (version of v1)
v3: "Original from v1 plus v2 plus v3"  (version of v2)

compare_versions(v1, v3) finds "Original from v1" as shared!
```

**Test:** `compare_across_version_chain`

Even though v3 was created from v2 (not v1), the content identity from v1 is preserved transitively.

### 8. Empty Document Versioning

Empty documents can be versioned, and the version can have content added independently:

```
Empty:   (no content)
Version: (no content initially)

After insert to Version:
Empty:   (still no content)
Version: "Content in version only"
```

**Test:** `version_of_empty_document`

## Implications for Specification

### For Dafny Specs

1. **Version creation** should model copy-on-write with content identity preservation
2. **compare_versions** should find shared content by identity, not byte comparison
3. **find_links** should search by content identity, discovering links from any document containing that content
4. **Insert/delete** should maintain content identity for unaffected regions

### For Oracle Tests

The golden tests provide concrete expected behaviors:
- Version operations preserve specific content identity relationships
- Link discovery works across documents sharing content
- Compare operations return specific span pairs

### Address Structure

Version addresses extend the original document address:
```
Original: 1.1.0.1.0.1
Version:  1.1.0.1.0.1.1
```

The version is a "child" in the address space of the original, but operationally independent.

## Test Matrix

| Scenario | Original Modified | Version Modified | Shared Content Found |
|----------|-------------------|------------------|---------------------|
| create_version | No | Yes | Yes |
| version_delete_preserves_original | No | Yes (delete) | Yes (partial) |
| modify_original_after_version | Yes | No | Yes |
| delete_from_original_check_version | Yes (delete) | No | Yes |
| both_versions_modified | Yes | Yes | Yes |
| version_insert_in_middle | No | Yes (insert) | Yes (split) |

## Related Findings

- **Finding 0002: Transclusion Content Identity** - Versioning and transclusion both preserve content identity; the same principles apply
- **Finding 0004: Link Endpoint Semantics** - Links are bound to content identity, which is why they transfer to versions
- **Finding 0005: Link Survivability** - Links survive document edits through content identity preservation

## Related Bugs

- **Bug 0009**: `compare_versions` crashes when documents have links. The link subspace (V-position 0.x) stores link ISAs rather than text content, which breaks assumptions in `correspond.c`. See Finding 0009 for the architectural explanation.

## Conclusion

Xanadu versioning implements a sophisticated model where:
1. Documents are independent after versioning
2. Content identity is the fundamental unit of sharing
3. Links follow content, not document containers
4. Transclusion relationships are inherited through versions

This is fundamentally different from traditional version control (which tracks document-level diffs) or file systems (which copy bytes). The Udanax model preserves **semantic relationships** (transclusion, links) through versioning by anchoring them to content identity rather than document identity.
