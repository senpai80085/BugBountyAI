from dataclasses import dataclass, field
from datetime import datetime

from models.finding import Finding


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
