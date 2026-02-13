"""Golden test scenarios organized by category."""

from .documents import SCENARIOS as DOCUMENT_SCENARIOS
from .content import SCENARIOS as CONTENT_SCENARIOS  # Now a package with submodules
from .versions import SCENARIOS as VERSION_SCENARIOS
from .links import SCENARIOS as LINK_SCENARIOS  # Now a package with submodules
from .endsets import SCENARIOS as ENDSET_SCENARIOS
from .internal import SCENARIOS as INTERNAL_SCENARIOS
from .interactions import SCENARIOS as INTERACTION_SCENARIOS
from .rearrange import SCENARIOS as REARRANGE_SCENARIOS
from .rearrange_semantics import SCENARIOS as REARRANGE_SEMANTICS_SCENARIOS
from .identity import SCENARIOS as IDENTITY_SCENARIOS
from .accounts import SCENARIOS as ACCOUNT_SCENARIOS
from .discovery import SCENARIOS as DISCOVERY_SCENARIOS
from .edgecases import SCENARIOS as EDGECASE_SCENARIOS
from .partial_overlap import SCENARIOS as PARTIAL_OVERLAP_SCENARIOS
from .insert_vspace_mapping import SCENARIOS as INSERT_VSPACE_SCENARIOS
from .insert_docispan import SCENARIOS as INSERT_DOCISPAN_SCENARIOS
from .provenance import SCENARIOS as PROVENANCE_SCENARIOS
from .docispan_granularity import SCENARIOS as DOCISPAN_GRANULARITY_SCENARIOS
from .subspace_shifts import SCENARIOS as SUBSPACE_SCENARIOS
from .bert_enforcement import SCENARIOS as BERT_SCENARIOS
from .version_link_test import SCENARIOS as VERSION_LINK_SCENARIOS
from .spanfilade_cleanup import SCENARIOS as SPANFILADE_CLEANUP_SCENARIOS
from .delete_all_content import SCENARIOS as DELETE_ALL_SCENARIOS
from .delete_link_gap_closure import SCENARIOS as DELETE_LINK_GAP_SCENARIOS
from .granfilade_split import SCENARIOS as GRANFILADE_SPLIT_SCENARIOS
from .iaddress_allocation import SCENARIOS as IADDRESS_ALLOCATION_SCENARIOS
from .interior_typing import SCENARIOS as INTERIOR_TYPING_SCENARIOS
from .insert_coalescing import SCENARIOS as INSERT_COALESCING_SCENARIOS
from .type_c_delete import SCENARIOS as TYPE_C_DELETE_SCENARIOS
from .document_isolation import SCENARIOS as ISOLATION_SCENARIOS
from .allocation_independence import SCENARIOS as ALLOCATION_INDEPENDENCE_SCENARIOS
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
    REARRANGE_SEMANTICS_SCENARIOS +
    IDENTITY_SCENARIOS +
    ACCOUNT_SCENARIOS +
    DISCOVERY_SCENARIOS +
    EDGECASE_SCENARIOS +
    PARTIAL_OVERLAP_SCENARIOS +
    INSERT_VSPACE_SCENARIOS +
    INSERT_DOCISPAN_SCENARIOS +
    PROVENANCE_SCENARIOS +
    DOCISPAN_GRANULARITY_SCENARIOS +
    SUBSPACE_SCENARIOS +
    BERT_SCENARIOS +
    VERSION_LINK_SCENARIOS +
    SPANFILADE_CLEANUP_SCENARIOS +
    DELETE_ALL_SCENARIOS +
    DELETE_LINK_GAP_SCENARIOS +
    GRANFILADE_SPLIT_SCENARIOS +
    IADDRESS_ALLOCATION_SCENARIOS +
    INTERIOR_TYPING_SCENARIOS +
    INSERT_COALESCING_SCENARIOS +
    TYPE_C_DELETE_SCENARIOS +
    ISOLATION_SCENARIOS +
    ALLOCATION_INDEPENDENCE_SCENARIOS
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
from . import rearrange_semantics
from . import identity
from . import accounts
from . import discovery
from . import edgecases
from . import partial_overlap
from . import insert_vspace_mapping
from . import insert_docispan
from . import provenance
from . import docispan_granularity
from . import subspace_shifts
from . import bert_enforcement
from . import version_link_test
from . import spanfilade_cleanup
from . import delete_all_content
from . import delete_link_gap_closure
from . import granfilade_split
from . import iaddress_allocation
from . import interior_typing
from . import insert_coalescing
from . import type_c_delete
from . import document_isolation
from . import allocation_independence
from . import multisession
