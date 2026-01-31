"""Content manipulation scenarios - organized by category.

This package contains content-related test scenarios split into logical groups:
- basic: Insert, delete, retrieve, rearrange operations
- vcopy: Transclusion (virtual copy) operations
"""

from .basic import SCENARIOS as BASIC_SCENARIOS
from .vcopy import SCENARIOS as VCOPY_SCENARIOS

# Combined SCENARIOS list maintains original order
SCENARIOS = (
    BASIC_SCENARIOS +
    VCOPY_SCENARIOS
)
