"""Common helpers for golden test scenarios."""

from client import (
    XuSession, XuConn, PipeStream, Address, Offset, Span, VSpec, VSpan, SpecSet,
    READ_ONLY, READ_WRITE, CONFLICT_FAIL, CONFLICT_COPY, ALWAYS_COPY,
    LINK_SOURCE, LINK_TARGET, LINK_TYPE,
    JUMP_TYPE, QUOTE_TYPE, FOOTNOTE_TYPE, MARGIN_TYPE,
    NOSPECS
)

# Default account address for test mode
DEFAULT_ACCOUNT = Address(1, 1, 0, 1)


def addr_to_str(addr):
    """Convert an Address to its string representation."""
    return str(addr)


def offset_to_str(offset):
    """Convert an Offset to its string representation."""
    return str(offset)


def span_to_dict(span):
    """Convert a Span to a dictionary."""
    return {
        "start": str(span.start),
        "width": str(span.width)
    }


def vspec_to_dict(vspec):
    """Convert a VSpec to a dictionary."""
    return {
        "docid": str(vspec.docid),
        "spans": [span_to_dict(s) for s in vspec.spans]
    }


def specset_to_list(specset):
    """Convert a SpecSet to a list of dictionaries."""
    result = []
    for spec in specset.specs:
        if hasattr(spec, 'docid'):
            result.append(vspec_to_dict(spec))
        else:
            result.append({"span": span_to_dict(spec)})
    return result
