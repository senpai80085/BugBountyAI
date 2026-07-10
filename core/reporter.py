from datetime import datetime

from models.context import ScanContext
from models.report import AnalysisResult, ReportMetadata, ScanReport


class Reporter:
    """
    Reporter formats triaged findings and persists them to JSON or Markdown outputs.
    """

    def generate(self, result: AnalysisResult, context: ScanContext) -> ScanReport:
        """
        Produce a ScanReport and write Markdown/JSON report files to context dirs.
        """
        metadata = ReportMetadata(
            target=context.target,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        # Interface stub only
        return ScanReport(
            metadata=metadata,
            summary=result.summary,
            findings=result.findings
        )
