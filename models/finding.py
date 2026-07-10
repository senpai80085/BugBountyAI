from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """
    Standard representation of a discovered vulnerability, open port, subdomain, or info item.
    """
    tool: str
    target: str
    data: dict
    severity: str  # "info", "low", "medium", "high", "critical"
    description: str
