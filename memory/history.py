from abc import ABC, abstractmethod

from models.context import ScanContext
from models.tool import ToolResult


class ScanHistory(ABC):
    """
    Interface for logging scan executions, timelines, and command logs.
    """

    @abstractmethod
    def log_tool_execution(self, context: ScanContext, result: ToolResult) -> None:
        """
        Record a single tool execution to the log history.
        """
        pass

    @abstractmethod
    def get_execution_log(self, context: ScanContext) -> list[ToolResult]:
        """
        Retrieve all execution entries registered in this scan context.
        """
        pass
