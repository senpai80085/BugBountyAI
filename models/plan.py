from dataclasses import dataclass, field
from typing import Any

from models.tool import ToolResult


@dataclass(frozen=True)
class Plan:
    """
    Structured representation of a planned scanning path or step list.
    """
    selected_workflow: str
    execution_strategy: str
    reasoning: str
    expected_outputs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    estimated_duration: float = 0.0


@dataclass(frozen=True)
class PlanResult:
    """
    Structured output returned by the Planner engine after running an objective.
    """
    plan: Plan
    success: bool
    summary: str
    results: list[ToolResult] = field(default_factory=list)
    planning_duration: float = 0.0
    actual_duration: float = 0.0
    tool_count: int = 0
    decisions: dict[str, Any] = field(default_factory=dict)
