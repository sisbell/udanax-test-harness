"""Link scenarios - organized by category.

This package contains link-related test scenarios split into logical groups:
- basic: Core link operations (create, find, follow, types)
- survival: How links behave when content changes
- patterns: Complex link topologies (chains, self-referential, overlapping)
- orphaned: Link permanence and orphaned link behavior
- discovery: find_links with homedocids filtering
- chains: Cross-document link chains (cycles, diamonds, hubs, transclusion)
- search_endpoint_removal: find_links behavior when endpoints removed from V-stream
- discontiguous_vspan: Link creation when V-spans map to non-contiguous I-addresses
- subspace_independence: V-position subspace independence (1.x text vs 2.x links)
- type_enforcement: Element type restrictions in V-subspaces
- link_subspace_deletion: Testing DELETEVSPAN on link subspace (2.x)
- poom_shifting: Whether CREATELINK shifts existing POOM entries
- vposition_shift: V-position arithmetic when text before links is deleted
"""

from .basic import SCENARIOS as BASIC_SCENARIOS
from .survival import SCENARIOS as SURVIVAL_SCENARIOS
from .patterns import SCENARIOS as PATTERN_SCENARIOS
from .orphaned import SCENARIOS as ORPHANED_SCENARIOS
from .discovery import SCENARIOS as DISCOVERY_SCENARIOS
from .chains import SCENARIOS as CHAIN_SCENARIOS
from .search_endpoint_removal import SCENARIOS as SEARCH_ENDPOINT_REMOVAL_SCENARIOS
from .discontiguous_vspan import SCENARIOS as DISCONTIGUOUS_VSPAN_SCENARIOS
from .subspace_independence import SCENARIOS as SUBSPACE_INDEPENDENCE_SCENARIOS
from .type_enforcement import SCENARIOS as TYPE_ENFORCEMENT_SCENARIOS
from .link_subspace_deletion import SCENARIOS as LINK_SUBSPACE_DELETION_SCENARIOS
from .poom_shifting import SCENARIOS as POOM_SHIFTING_SCENARIOS
from .vposition_shift import SCENARIOS as VPOSITION_SHIFT_SCENARIOS
from .delete_displacement_underflow import SCENARIOS as DELETE_DISPLACEMENT_UNDERFLOW_SCENARIOS

# Combined SCENARIOS list maintains original order
SCENARIOS = (
    BASIC_SCENARIOS +
    SURVIVAL_SCENARIOS +
    PATTERN_SCENARIOS +
    ORPHANED_SCENARIOS +
    DISCOVERY_SCENARIOS +
    CHAIN_SCENARIOS +
    SEARCH_ENDPOINT_REMOVAL_SCENARIOS +
    DISCONTIGUOUS_VSPAN_SCENARIOS +
    SUBSPACE_INDEPENDENCE_SCENARIOS +
    TYPE_ENFORCEMENT_SCENARIOS +
    LINK_SUBSPACE_DELETION_SCENARIOS +
    POOM_SHIFTING_SCENARIOS +
    VPOSITION_SHIFT_SCENARIOS +
    DELETE_DISPLACEMENT_UNDERFLOW_SCENARIOS
)
