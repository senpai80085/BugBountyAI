from dataclasses import dataclass, field
from models.finding import Finding


@dataclass(frozen=True)
class Plan:
    """
    Structured representation of a planned scanning path or step list.
    """
    objective: str
    steps: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlanResult:
    """
    Structured output returned by the Planner engine after running an objective.
    """
    success: bool
    summary: str
    findings: list[Finding] = field(default_factory=list)
