from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.context import ScanContext
from models.tool import ToolResult


@dataclass(frozen=True)
class Event(ABC):
    """
    Abstract Base Class for all engine events.
    """
    pass


@dataclass(frozen=True)
class ToolStarted(Event):
    tool_name: str
    target: str


@dataclass(frozen=True)
class ToolFinished(Event):
    result: ToolResult


@dataclass(frozen=True)
class WorkflowStarted(Event):
    workflow_name: str
    context: ScanContext


@dataclass(frozen=True)
class WorkflowFinished(Event):
    workflow_name: str
    context: ScanContext


@dataclass(frozen=True)
class AnalysisCompleted(Event):
    context: ScanContext


@dataclass(frozen=True)
class ReportGenerated(Event):
    report_path: str


class EventListener(ABC):
    """
    Interface for classes listening to engine execution events.
    """

    @abstractmethod
    def on_event(self, event: Event) -> None:
        """
        Callback handler invoked when an Event is published.
        """
        pass
