# Bug 009: Root Cause Analysis

**Date:** 2026-01-30
**Status:** Root cause identified

## Summary

When `compare_versions` is called on documents with links, the backend crashes with SIGABRT. The crash is caused by a NULL vspanset being passed to `intersectspansets()`, which doesn't handle NULL inputs gracefully.

## Root Cause

There are **two bugs** that combine to cause the crash:

### Bug 1: Nested Loop Consumes Iterator (correspond.c:65-66)

```c
for (; ispanset; ispanset = ispanset->next) {
    for (; specset; specset = (typespecset)((typeitemheader *)specset)->next) {
```

The inner loop uses `specset` directly and advances it. After the first outer iteration, `specset` is NULL and stays NULL. This means **only the first ispan is processed**, and subsequent ispans are ignored.

**Impact:** The restricted specset may be incomplete or empty when it should contain valid vspans.

### Bug 2: ispan2vspanset Return Value Misuse (correspond.c:74-81)

```c
docvspanset = NULL;
if(ispan2vspanset(taskptr,versionorgl,ispanset,&docvspanset)){
    s1=(typevspec *)taskalloc(taskptr,sizeof(typevspec ));
    // ...
    s1->vspanset = docvspanset;  // May be NULL!
}
```

`ispan2vspanset()` returns a pointer (the target spanset pointer), not a boolean. The pointer is never NULL (it's the address of a local variable). So the `if` condition **always succeeds**, even when `docvspanset` remains NULL because no V-addresses were found.

**Impact:** A vspec is created with a NULL vspanset.

### The Crash

In `removespansnotinoriginal()` (correspond.c:116):
```c
if (intersectspansets (taskptr,
    ((typevspec *)new)->vspanset,
    ((typevspec *)old)->vspanset,  // <-- This may be NULL!
    &newspanset, VSPANID)) {
```

If `old->vspanset` is NULL (from Bug 2), `intersectspansets()` calls `gerror("")` which calls `abort()`, causing SIGABRT.

## Why Links Trigger This

Without links:
- Document vspanset: `at 1.1 for 0.16` (text only)
- All common I-addresses map to V-positions in range 1.x
- The first ispan matches, vspanset is populated

With links:
- Document vspanset: `at 0 for 0.1, at 1 for 1` (links + text)
- Link subspace (0.x) contains link ISA addresses, not text I-addresses
- Due to Bug 1, only the first ispan is processed
- If that ispan doesn't match for some reason, vspanset stays NULL
- Bug 2 allows a vspec with NULL vspanset to be created
- Crash ensues

## Proper Fix

### THE Semantic Fix (Recommended)

**Filter V-spans to text subspace (V ≥ 1) before comparison.**

See **Finding 015** for full analysis. The key insight:

`compare_versions` is defined as finding content with "common origin" (FEBE: SHOWRELATIONOF2VERSIONS). "Common origin" means shared **permascroll content identity**:

| V-Position | Contains | I-Address Type | Has "Common Origin"? |
|------------|----------|----------------|----------------------|
| 0.x | Link references | Link orgl ISAs | **No** |
| 1.x | Text content | Permascroll addresses | **Yes** |

Link ISAs stored at 0.x are document metadata, not transcludable content. They are unique identifiers for link orgls, not permascroll addresses. Comparing link ISAs:
- Will never find matches (each link is unique)
- Is semantically undefined (links don't have "common origin")

The correct behavior is to compare only the text subspace:

```c
// In compare_versions, before processing:
vspanset = filter_to_text_subspace(vspanset);  // Keep only spans where V >= 1.0
```

This is NOT a workaround - it's the semantically correct definition of the operation.

### Why the Code Path Bugs Still Matter

The bugs in correspond.c (nested loop, return value misuse) are real bugs that should be fixed independently:

**Bug A: Nested Loop Consumes Iterator (correspond.c:65-66)**

```c
for (; ispanset; ispanset = ispanset->next) {
    typespecset tmpspecset = specset;  // FIX: Use temporary
    for (; tmpspecset; tmpspecset = ...) {
```

**Bug B: Return Value Misuse (correspond.c:74-81)**

```c
docvspanset = NULL;
(void)ispan2vspanset(taskptr,versionorgl,ispanset,&docvspanset);
if(docvspanset){  // FIX: Check actual result, not return pointer
```

These bugs would cause incorrect results even for text-only comparisons in edge cases. But the **crash with links** is fundamentally a semantic issue: the code tries to compare link metadata that has no "common origin" to compare.

### Defensive NULL Handling (Applied as Stopgap)

The existing patches in correspond.c prevent crashes but don't fix the semantic issue:
- `intersectspansets()` handles NULL inputs gracefully
- `restrictspecsetsaccordingtoispans()` checks for NULL

This is a workaround that masks the real problem.

## Files Affected

- `correspond.c:65-66` - Nested loop bug
- `correspond.c:74-81` - Return value misuse
- `correspond.c:103-108` - Crash point in removespansnotinoriginal
- `correspond.c:145-169` - intersectspansets NULL handling

## Test Case

`febe/debug_bug009.py` - Reproduces the issue by:
1. Creating a document with text
2. Creating a version (before adding link)
3. Adding a link to the original
4. Calling compare_versions with full vspansets (including link subspace)

## Related Findings

- **Finding 015**: Semantic definition of compare_versions (the definitive fix)
- **Finding 009**: Document address space structure (text vs link subspace)
- **Finding 010**: Unified storage abstraction leaks (this is one of the leaks)
- **Finding 011**: Convention over enforcement design philosophy
