from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from models.finding import Finding
from models.artifact import Artifact
from models.metrics import ScanMetrics



if TYPE_CHECKING:
    from models.plan import PlanResult


@dataclass(frozen=True)
class ReportMetadata:
    """
    Metadata relating to report execution scope, duration, and target.
    """
    target: str
    started_at: datetime
    completed_at: datetime
    engine_version: str = "1.0"


@dataclass(frozen=True)
class AnalysisResult:
    """
    Structured outcome of Analyst triage, summary, and severity classification.
    """
    summary: str
    findings: list[Finding] = field(default_factory=list)
    risk_score: str = "info"


@dataclass(frozen=True)
class ScanReport:
    """
    Aggregated scan results containing summaries, findings, and target information.
    """
    metadata: ReportMetadata
    summary: str
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True)
class ScanResult:
    """
    Structured execution result summarizing the entire bug bounty scan pipeline.
    """
    scan_id: str
    target: str
    started_at: datetime
    finished_at: datetime
    duration: float
    engine_version: str
    success: bool
    plan_result: "PlanResult"
    analysis_result: AnalysisResult
    artifacts: list[Artifact] = field(default_factory=list)
    metrics: Optional[ScanMetrics] = None

