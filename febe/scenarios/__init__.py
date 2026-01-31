"""Golden test scenarios organized by category."""

from .documents import SCENARIOS as DOCUMENT_SCENARIOS
from .content import SCENARIOS as CONTENT_SCENARIOS
from .versions import SCENARIOS as VERSION_SCENARIOS
from .links import SCENARIOS as LINK_SCENARIOS
from .internal import SCENARIOS as INTERNAL_SCENARIOS
from .interactions import SCENARIOS as INTERACTION_SCENARIOS
from .rearrange import SCENARIOS as REARRANGE_SCENARIOS
from .identity import SCENARIOS as IDENTITY_SCENARIOS

# All scenarios combined
ALL_SCENARIOS = (
    DOCUMENT_SCENARIOS +
    CONTENT_SCENARIOS +
    VERSION_SCENARIOS +
    LINK_SCENARIOS +
    INTERNAL_SCENARIOS +
    INTERACTION_SCENARIOS +
    REARRANGE_SCENARIOS +
    IDENTITY_SCENARIOS
)

# Re-export individual scenario modules for direct access
from . import documents
from . import content
from . import versions
from . import links
from . import internal
from . import interactions
from . import rearrange
from . import identity
