from core.reporter import Reporter
from models.context import ScanContext
from models.report import AnalysisResult, ScanReport


def test_reporter_interface():
    reporter = Reporter()
    context = ScanContext(
        target="example.com",
        workspace="workspace",
        loot_dir="loot",
        report_dir="reports",
    )
    result = AnalysisResult(
        summary="Audit summary",
        findings=[],
        risk_score="low",
    )

    report = reporter.generate(result, context)
    assert isinstance(report, ScanReport)
    assert report.summary == "Audit summary"
