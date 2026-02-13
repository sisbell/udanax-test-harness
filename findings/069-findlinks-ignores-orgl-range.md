# Finding 069: find_links Ignores Orgl Range Parameter

**Date discovered:** 2026-02-12
**Category:** Link Search, Spanfilade
**Source:** Code reading of `sporgl.c:222-237`

## Summary

`find_links` always searches the entire orgl address space (up to width 100) regardless of what orgl range the caller specifies. The `sporglset2linkset` function contains an always-true condition (`TRUE||!homeset`) that overrides the `homeset` parameter with a hardcoded range, making orgl filtering a no-op.

## The Code

In `sporgl.c:222-237`:

```c
int sporglset2linkset(taskptr, spanfptr, sporglset, linksetptr, homeset, spantype)
{
  typeispan nullhomeset;
    *linksetptr = NULL;
    if (TRUE||!homeset) {
        tumblerclear (&nullhomeset.stream);
        tumblerclear (&nullhomeset.width);
        nullhomeset.width.mantissa[0] = 100;
        nullhomeset.next = NULL;
        homeset = &nullhomeset;
    }
    for (; homeset; homeset = homeset->next) {
        sporglset2linksetinrange (taskptr, spanfptr, sporglset, linksetptr, homeset, spantype);
    }
}
```

The `if (TRUE||!homeset)` always evaluates true. The original intent was likely `if (!homeset)` — provide a default range only when no range is specified. The `TRUE||` prefix disables the parameter entirely.

## Implications

1. **All link searches are global.** A `find_links` call scoped to a specific document's orgl range will still return links from any document within orgl width 100. The spanfilade search uses the span dimension for filtering, but the orgl dimension is unbounded.

2. **The FEBE protocol's orgl range parameter is cosmetic.** Callers can pass an orgl range, but the backend discards it. The actual scoping comes entirely from the span-dimension match.

3. **Width 100 is a practical ceiling.** The hardcoded `mantissa[0] = 100` means the system supports up to 100 top-level tumbler digits in the orgl dimension. For any realistic deployment this is effectively unbounded.

## Related Code

- `sporglset2linksetinrange()` at `sporgl.c:239-269` — the actual search, called with the overridden range
- `findlinksfromtothreesp()` at `spanf1.c:56-103` — caller that passes `orglrange` through to `sporglset2linkset`
- `retrieverestricted()` at `retrie.c:56-85` — converts the range into span start/end for 2D search

## Related Findings

- **Finding 012**: Dual enfilade architecture (spanfilade indexes links by span × orgl)
- **Finding 026**: Link discovery through content identity (links found via shared I-addresses, not document scope)
