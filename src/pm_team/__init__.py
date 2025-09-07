"""pm_team package (src layout).

Provides stub (local heuristic) project management agents and optional
real Autogen wiring. Exposes orchestrator for library consumers.
"""

from .orchestration import PMTeamOrchestrator  # noqa: F401

__all__ = ["PMTeamOrchestrator"]

__version__ = "0.1.0"
