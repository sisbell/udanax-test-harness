"""Golden test scenarios organized by category."""

from .documents import SCENARIOS as DOCUMENT_SCENARIOS
from .content import SCENARIOS as CONTENT_SCENARIOS  # Now a package with submodules
from .versions import SCENARIOS as VERSION_SCENARIOS
from .links import SCENARIOS as LINK_SCENARIOS  # Now a package with submodules
from .endsets import SCENARIOS as ENDSET_SCENARIOS
from .internal import SCENARIOS as INTERNAL_SCENARIOS
from .interactions import SCENARIOS as INTERACTION_SCENARIOS
from .rearrange import SCENARIOS as REARRANGE_SCENARIOS
from .identity import SCENARIOS as IDENTITY_SCENARIOS
from .accounts import SCENARIOS as ACCOUNT_SCENARIOS
from .discovery import SCENARIOS as DISCOVERY_SCENARIOS
from .edgecases import SCENARIOS as EDGECASE_SCENARIOS
from .partial_overlap import SCENARIOS as PARTIAL_OVERLAP_SCENARIOS
from .insert_vspace_mapping import SCENARIOS as INSERT_VSPACE_SCENARIOS
from .insert_docispan import SCENARIOS as INSERT_DOCISPAN_SCENARIOS
from .provenance import SCENARIOS as PROVENANCE_SCENARIOS
from .docispan_granularity import SCENARIOS as DOCISPAN_GRANULARITY_SCENARIOS
from .multisession import MULTISESSION_SCENARIOS

# All single-session scenarios combined
ALL_SCENARIOS = (
    DOCUMENT_SCENARIOS +
    CONTENT_SCENARIOS +
    VERSION_SCENARIOS +
    LINK_SCENARIOS +
    ENDSET_SCENARIOS +
    INTERNAL_SCENARIOS +
    INTERACTION_SCENARIOS +
    REARRANGE_SCENARIOS +
    IDENTITY_SCENARIOS +
    ACCOUNT_SCENARIOS +
    DISCOVERY_SCENARIOS +
    EDGECASE_SCENARIOS +
    PARTIAL_OVERLAP_SCENARIOS +
    INSERT_VSPACE_SCENARIOS +
    INSERT_DOCISPAN_SCENARIOS +
    PROVENANCE_SCENARIOS +
    DOCISPAN_GRANULARITY_SCENARIOS
)

# Multi-session scenarios are run separately via generate_multisession_golden.py

# Re-export individual scenario modules for direct access
from . import documents
from . import content  # Package with basic, vcopy
from . import versions
from . import links  # Package with basic, survival, patterns, orphaned, discovery
from . import endsets
from . import internal
from . import interactions
from . import rearrange
from . import identity
from . import accounts
from . import discovery
from . import edgecases
from . import partial_overlap
from . import insert_vspace_mapping
from . import insert_docispan
from . import provenance
from . import docispan_granularity
from . import multisession
