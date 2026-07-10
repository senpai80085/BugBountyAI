from dataclasses import dataclass, field
from typing import Any

from core.command import Command
from models.artifact import Artifact


@dataclass(frozen=True)
class ToolMetadata:
    """
    Metadata information for tool plugins.
    """
    name: str
    version: str
    author: str
    description: str
    tags: list[str] = field(default_factory=list)
    category: str = ""
    requirements: list[str] = field(default_factory=list)
    supports_parallel: bool = False


@dataclass(frozen=True)
class ToolResult:
    """
    Structured outcome of any executed tool plugin.
    Never subclassed.
    """
    command: Command
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
