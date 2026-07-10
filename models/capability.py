from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    """
    Representation of a tool's capability discovered dynamically from registry.
    """
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    category: str = ""
    supports_parallel: bool = False
