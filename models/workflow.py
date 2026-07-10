from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class WorkflowStep:
    """
    Representation of a single step within a YAML-defined workflow,
    including dependencies, parallel flags, execution timeouts, retries,
    and continuation strategies on failure.
    """
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    condition: Optional[str] = None
    parallel: bool = False
    timeout: Optional[int] = None
    retry: int = 0
    continue_on_error: bool = False


@dataclass(frozen=True)
class Workflow:
    """
    Modular execution sequence parsed from YAML configurations.
    """
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
