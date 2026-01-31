"""Common utilities for link scenarios."""

from client import Address


def contents_to_list(contents):
    """Convert retrieve_contents result to JSON-serializable list.

    retrieve_contents can return strings (text) or Address objects (link IDs),
    so we need to convert Address objects to strings.
    """
    result = []
    for item in contents:
        if isinstance(item, Address):
            result.append({"link_id": str(item)})
        else:
            result.append(item)
    return result
