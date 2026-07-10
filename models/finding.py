from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """
    Vulnerability and discovery severity levels.
    """
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Finding:
    """
    Standard representation of a discovered vulnerability, open port, subdomain, or info item.
    """
    tool: str
    target: str
    data: dict
    severity: Severity
    description: str
