from abc import ABC, abstractmethod
from typing import Optional

from core.command import Command
from models.tool import ToolResult


class ScanCache(ABC):
    """
    Interface for caching tool results to speed up resume and dry-run execution.
    """

    @abstractmethod
    def get(self, command: Command) -> Optional[ToolResult]:
        """
        Retrieve a cached ToolResult based on the command and its arguments.
        """
        pass

    @abstractmethod
    def set(self, command: Command, result: ToolResult) -> None:
        """
        Store a ToolResult in the cache.
        """
        pass
