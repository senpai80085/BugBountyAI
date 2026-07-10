import time
from abc import ABC, abstractmethod
from typing import Any

from core.command import Command
from core.executor import Executor
from models.tool import ToolMetadata, ToolResult


class Tool(ABC):
    """
    Base class for all tools.
    Every tool plugin MUST inherit from this class.
    Each tool is responsible for validating args, building commands,
    executing via backends, and parsing stdout.
    """

    metadata: ToolMetadata

    @abstractmethod
    def validate(self, **kwargs) -> None:
        """
        Validate input arguments before building the command.
        """
        pass

    @abstractmethod
    def build(self, **kwargs) -> Command:
        """
        Build the structured Command representation.
        """
        pass

    @abstractmethod
    def parse(self, stdout: str) -> dict[str, Any]:
        """
        Parse raw stdout from tool execution into tool-specific metadata dict.
        """
        pass

    def execute(self, executor: Executor, **kwargs) -> ToolResult:
        """
        Execute the tool via the given Executor, parse stdout, and return a ToolResult.
        """
        self.validate(**kwargs)
        command = self.build(**kwargs)

        start_time = time.perf_counter()
        result = executor.run(command)
        duration = time.perf_counter() - start_time

        success = (result.exit_code == 0)
        parsed_data = {}
        if success:
            try:
                parsed_data = self.parse(result.stdout)
            except Exception as e:
                success = False
                parsed_data = {"parsing_error": str(e)}

        return ToolResult(
            command=command,
            success=success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=duration,
            artifacts=[],
            metadata=parsed_data,
        )