from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PlanningMode(str, Enum):
    """
    Modes of operations for workflow selection and decision logic.
    """
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class Objective:
    """
    User-specified target scanning objective.
    """
    text: str
    mode: PlanningMode = PlanningMode.AUTO
    suggested_workflow: Optional[str] = None
