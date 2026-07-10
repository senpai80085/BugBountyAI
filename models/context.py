from dataclasses import dataclass, field
import threading
from typing import Any, Optional

from models.tool import ToolResult


@dataclass
class ScanContext:
    """
    State context passed across layers (Planner, Workflow, Analyst, Reporter).
    Thread-safe accessors are provided to secure concurrent modifications.
    """
    target: str
    workspace: str
    loot_dir: str
    report_dir: str
    variables: dict[str, Any] = field(default_factory=dict)
    shared_results: dict[str, Any] = field(default_factory=dict)
    results: dict[str, ToolResult] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a variable value thread-safely.
        """
        with self._lock:
            self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """
        Get a variable value thread-safely.
        """
        with self._lock:
            return self.variables.get(key, default)

    def set_result(self, tool_name: str, result: ToolResult) -> None:
        """
        Store a ToolResult thread-safely.
        """
        with self._lock:
            self.results[tool_name] = result

    def get_result(self, tool_name: str) -> Optional[ToolResult]:
        """
        Retrieve a ToolResult thread-safely.
        """
        with self._lock:
            return self.results.get(tool_name)
