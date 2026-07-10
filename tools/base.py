import os
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
        If output_file is specified, registers the output artifact using Executor's artifact_manager.
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

        # Register remote file artifact if execution was successful and output_file was requested
        artifacts = []
        output_file = kwargs.get("output_file")
        if success and output_file and getattr(executor, "artifact_manager", None) is not None:
            filename = os.path.basename(output_file)
            artifact = executor.artifact_manager.register_artifact(
                artifact_type=self.metadata.name,
                filename=filename,
                remote_path=output_file
            )
            artifacts.append(artifact)

        return ToolResult(
            command=command,
            success=success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=duration,
            artifacts=artifacts,
            metadata=parsed_data,
        )