from unittest.mock import MagicMock
from engine.analyst import Analyst
from models.context import ScanContext
from models.report import AnalysisResult


def test_analyst_interface():
    mock_provider = MagicMock()
    analyst = Analyst(provider=mock_provider)

    context = ScanContext(
        target="example.com",
        workspace="workspace",
        loot_dir="loot",
        report_dir="reports",
    )

    res = analyst.analyze(results=[], context=context)
    assert isinstance(res, AnalysisResult)
    assert res.summary == "Scan completed successfully."
