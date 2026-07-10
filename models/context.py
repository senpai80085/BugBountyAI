from dataclasses import dataclass, field
from typing import Any

from models.tool import ToolResult


@dataclass
class ScanContext:
    """
    State context passed across layers (Planner, Workflow, Analyst, Reporter).
    Never pass raw dictionaries between modules.
    """
    target: str
    workspace: str
    loot_dir: str
    report_dir: str
    variables: dict[str, Any] = field(default_factory=dict)
    shared_results: dict[str, Any] = field(default_factory=dict)
    results: dict[str, ToolResult] = field(default_factory=dict)

