"""Link scenarios - organized by category.

This package contains link-related test scenarios split into logical groups:
- basic: Core link operations (create, find, follow, types)
- survival: How links behave when content changes
- patterns: Complex link topologies (chains, self-referential, overlapping)
- orphaned: Link permanence and orphaned link behavior
- discovery: find_links with homedocids filtering
- chains: Cross-document link chains (cycles, diamonds, hubs, transclusion)
- search_endpoint_removal: find_links behavior when endpoints removed from V-stream
"""

from .basic import SCENARIOS as BASIC_SCENARIOS
from .survival import SCENARIOS as SURVIVAL_SCENARIOS
from .patterns import SCENARIOS as PATTERN_SCENARIOS
from .orphaned import SCENARIOS as ORPHANED_SCENARIOS
from .discovery import SCENARIOS as DISCOVERY_SCENARIOS
from .chains import SCENARIOS as CHAIN_SCENARIOS
from .search_endpoint_removal import SCENARIOS as SEARCH_ENDPOINT_REMOVAL_SCENARIOS

# Combined SCENARIOS list maintains original order
SCENARIOS = (
    BASIC_SCENARIOS +
    SURVIVAL_SCENARIOS +
    PATTERN_SCENARIOS +
    ORPHANED_SCENARIOS +
    DISCOVERY_SCENARIOS +
    CHAIN_SCENARIOS +
    SEARCH_ENDPOINT_REMOVAL_SCENARIOS
)
