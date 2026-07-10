from models.context import ScanContext
from models.report import AnalysisResult
from models.tool import ToolResult
from providers.base import AIProvider


class Analyst:
    """
    Analyst evaluates execution tool outcomes, triages severity levels,
    and filters false positives using optional AI provider prompts.
    """

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def analyze(self, results: list[ToolResult], context: ScanContext) -> AnalysisResult:
        """
        Evaluate ToolResults list and output a structured AnalysisResult.
        """
        # Interface stub only
        return AnalysisResult(summary="Scan completed successfully.", findings=[], risk_score="info")
