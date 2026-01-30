# Finding 011: Convention Over Enforcement - Udanax Green Design Philosophy

**Date:** 2026-01-30
**Category:** Architecture / Design Philosophy
**Importance:** High - fundamental to understanding the codebase

## Summary

Udanax Green follows a **"convention over enforcement"** design philosophy. The system provides powerful, uniform primitives but relies on calling code to use them correctly. There is minimal runtime validation or type safety - correctness comes from following implicit contracts.

## The Philosophy

### What It Means

| Aspect | Convention Over Enforcement | Alternative (Enforcement) |
|--------|----------------------------|---------------------------|
| **Type safety** | Caller knows what types to use | System validates types |
| **Subspace rules** | V-position encodes meaning by convention | Explicit subspace fields |
| **Validation** | Trust the caller | Check every input |
| **Error handling** | Crash on violation (gerror/abort) | Graceful error returns |
| **Abstraction** | Uniform primitives, implicit contracts | Type-specific operations |

### Historical Context

This was a common design approach in 1970s-80s systems:

- **Unix**: "Everything is a file" - read/write work on everything, but seeking a socket fails
- **C language**: No bounds checking, trust the programmer
- **Lisp machines**: Dynamic typing with runtime errors
- **Original Xanadu**: Designed in this era, reflects these values

The philosophy prioritizes:
- **Simplicity**: Fewer special cases in core code
- **Power**: Uniform primitives compose flexibly
- **Performance**: No validation overhead
- **Trust**: Assumes competent callers

## Evidence in Udanax Green

### 1. Unified Enfilade Storage

**Convention:** V-position 0.x is for links, 1.x is for text

**No enforcement:**
```c
// do2.c:110-113
bool acceptablevsa(tumbler *vsaptr, typeorgl orglptr)
{
    return (TRUE);  // Always accepts any V-position
}
```

**Consequence:** Can store anything at any V-position. System trusts you won't.

### 2. I-Address Interpretation

**Convention:** Permascroll I-addresses are content, document ISAs are references

**No enforcement:** Both are just tumblers. The system doesn't distinguish.

```c
// specset2ispanset treats all I-addresses uniformly
// ispanset2vstuffset assumes all I-addresses are in permascroll
```

**Consequence:** Dereferencing a link ISA as content produces garbage.

### 3. Error Handling via Abort

**Convention:** Invalid states shouldn't happen

**Enforcement style:** When they do, crash immediately

```c
// genf.c:546
INT qerror(char *message)
{
    fprintf (stderr, "Error: %s\n", message);
    abort();  // No recovery, just die
    return(1);
}
```

**Consequence:** Violations are fatal, not recoverable. Debug by preventing, not handling.

### 4. Linked List Iteration

**Convention:** Loops should check for NULL before dereferencing

**No enforcement:** The nested loop bug in correspond.c shows what happens when conventions are violated:

```c
for (; ispanset; ispanset = ispanset->next) {
    for (; specset; specset = ...) {  // Consumes specset!
```

**Consequence:** Subtle bugs when iteration patterns don't match expectations.

### 5. Function Return Values

**Convention:** Check return values, understand what they mean

**No enforcement:** Many functions return pointers that are always non-NULL but indicate failure through other means:

```c
// ispan2vspanset returns pointer (never NULL), but docvspanset may be NULL
if(ispan2vspanset(taskptr, orgl, ispanset, &docvspanset)) {
    // This always succeeds! But docvspanset might be NULL
}
```

**Consequence:** Callers must understand the actual semantics, not just the return type.

## Implications

### For Understanding the Code

1. **Read conventions, not just signatures**: Function behavior depends on implicit contracts
2. **Trace data flow**: Understand what types of data flow through uniform interfaces
3. **Question assumptions**: "What if this isn't what I expect?"
4. **Check for validation**: Often there isn't any

### For Maintaining the Code

1. **Preserve conventions**: Breaking them causes subtle bugs
2. **Document assumptions**: Make implicit contracts explicit
3. **Add validation carefully**: May break existing code that relies on permissiveness
4. **Defensive coding at boundaries**: Validate at system entry points (FEBE protocol)

### For Formal Specification

1. **Preconditions are implicit**: Must be inferred from conventions, not code
2. **Postconditions assume valid input**: Garbage in, garbage out
3. **Invariants are social contracts**: Enforced by convention, not runtime

## The Trade-offs

### Benefits

| Benefit | Example |
|---------|---------|
| **Simplicity** | One `docopy` function handles text and links |
| **Flexibility** | Primitives compose in unexpected ways |
| **Performance** | No validation overhead |
| **Small code** | Fewer special cases |

### Costs

| Cost | Example |
|------|---------|
| **Subtle bugs** | Bug 009 - crash when conventions violated |
| **Hard debugging** | No error messages, just crashes |
| **Documentation burden** | Conventions must be learned, not discovered |
| **Security concerns** | Malicious input can corrupt state |

## Modern Perspective

Today's systems typically favor enforcement:

| Modern Approach | Udanax Approach |
|-----------------|-----------------|
| Type systems (Rust, TypeScript) | Untyped tumblers |
| Validation libraries | Trust the caller |
| Error types (Result, Option) | Abort on error |
| Defensive programming | Assume valid input |

The Udanax approach works well for:
- Small teams with shared understanding
- Research/prototype code
- Performance-critical paths

It struggles with:
- Large codebases
- Multiple implementers
- Untrusted input
- Long-term maintenance

## Recommendations

### For the Test Harness

1. **Validate at FEBE boundary**: Filter/validate before calling backend
2. **Document conventions**: Make implicit contracts explicit in client code
3. **Test edge cases**: Verify behavior when conventions are violated
4. **Add defensive filtering**: e.g., filter to text subspace before compare_versions

### For Formal Specification

1. **Make preconditions explicit**: What the C code assumes, Dafny should require
2. **Model the conventions**: Subspace types, I-address categories
3. **Specify valid states**: What document states are semantically meaningful
4. **Document the gaps**: Where enforcement is missing

## Related

- **Finding 009**: Document address space structure (the primary convention)
- **Finding 010**: Unified storage abstraction leaks (where conventions break)
- **Bug 009**: compare_versions crash (convention violation consequence)
- **Bug 010**: acceptablevsa always TRUE (missing enforcement)

## Conclusion

**"Convention over enforcement" is not a bug - it's a design philosophy.**

Understanding this is essential for working with Udanax Green. The code is elegant and powerful, but requires understanding the implicit contracts. Violations don't produce helpful errors - they produce crashes or corruption.

When extending or specifying this system:
- **Respect the conventions** even when not enforced
- **Add enforcement at boundaries** where untrusted input enters
- **Document what the code assumes** so future readers understand
- **Test convention violations** to understand failure modes
