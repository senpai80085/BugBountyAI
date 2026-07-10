from __future__ import annotations

from typing import Optional

from core.prompt_manager import PromptManager
from engine.analysis.normalizer import Normalizer
from engine.analysis.deduplicator import Deduplicator
from engine.analysis.classifier import Classifier
from engine.analysis.analyzer import Analyzer
from models.context import ScanContext
from models.finding import Finding
from models.report import AnalysisResult
from models.tool import ToolResult
from providers.base import AIProvider


class Analyst:
    """
    Orchestrator for the security analysis pipeline.
    Coordinates sequential execution of normalizer, deduplicator, classifier, and analyzer stages.
    """

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        prompt_manager: Optional[PromptManager] = None,
        normalizer: Optional[Normalizer] = None,
        deduplicator: Optional[Deduplicator] = None,
        classifier: Optional[Classifier] = None,
        analyzer: Optional[Analyzer] = None,
    ) -> None:
        self.provider = provider
        self.prompt_manager = prompt_manager
        self.normalizer = normalizer or Normalizer()
        self.deduplicator = deduplicator or Deduplicator()
        self.classifier = classifier or Classifier()
        self.analyzer = analyzer or Analyzer(provider, prompt_manager)

    def analyze(self, results: list[ToolResult], context: ScanContext) -> AnalysisResult:
        """
        Evaluate ToolResults lists through the stages pipeline and output standard AnalysisResult objects.
        """
        # Stage 1: Standardize tool output items
        raw_findings = self.normalizer.normalize(results)

        # Stage 2: Deduplicate overlapping finding hashes
        deduplicated_raw = self.deduplicator.deduplicate(raw_findings)

        # Stage 3: Map dict entries into domain Finding models
        findings = self.classifier.classify(deduplicated_raw)

        # Stage 4: Validate triages using AI or rule fallbacks
        decision = self.analyzer.analyze(findings)

        # Stage 5: Instantiate domain Finding instances from validation outcome
        validated_findings = []
        for vf in decision.validated_findings:
            validated_findings.append(
                Finding(
                    tool=vf.tool,
                    target=vf.target,
                    data=vf.data,
                    severity=vf.severity,
                    description=vf.description,
                )
            )

        # Map highest severity level for risk categorization score
        highest_severity = "info"
        severity_priority = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        for f in validated_findings:
            sev_val = f.severity.value
            if severity_priority.get(sev_val, 1) > severity_priority.get(highest_severity, 1):
                highest_severity = sev_val

        return AnalysisResult(
            summary=decision.reasoning,
            findings=validated_findings,
            risk_score=highest_severity,
        )
