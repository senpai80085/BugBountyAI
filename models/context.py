from dataclasses import dataclass, field
import threading
from typing import Any, Optional
import uuid

from models.tool import ToolResult


@dataclass(frozen=True)
class ScanContext:
    """
    State context passed across layers (Planner, Workflow, Analyst, Reporter).
    This dataclass is frozen for immutability of its reference attributes.
    Internal dictionaries are modified thread-safely via its lock.
    """
    target: str
    workspace: str
    loot_dir: str
    report_dir: str
    scan_id: str = ""
    variables: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)
    shared_results: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)
    results: dict[str, ToolResult] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        # Use object.__setattr__ to bypass frozen checks
        object.__setattr__(self, "_lock", threading.Lock())
        if not self.scan_id:
            object.__setattr__(self, "scan_id", str(uuid.uuid4()))

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a variable value thread-safely.
        """
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """
        Get a variable value thread-safely.
        """
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            return self.variables.get(key, default)

    def set_result(self, tool_name: str, result: ToolResult) -> None:
        """
        Store a ToolResult thread-safely.
        """
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            self.results[tool_name] = result

    def get_result(self, tool_name: str) -> Optional[ToolResult]:
        """
        Retrieve a ToolResult thread-safely.
        """
        lock: threading.Lock = getattr(self, "_lock")
        with lock:
            return self.results.get(tool_name)
