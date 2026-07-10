from __future__ import annotations

from typing import Optional

from core.prompt_manager import PromptManager
from memory.conversation import Conversation, Role
from models.ai.decision import AnalysisDecision, ValidatedFinding
from models.finding import Finding
from providers.base import AIProvider


class Analyzer:
    """
    Vulnerability triage analyzer validating findings against AI response schemas.
    Falls back to a complete rule-based validation pass-through when AI is disabled.
    """

    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        prompt_manager: Optional[PromptManager] = None,
    ) -> None:
        self.provider = provider
        self.prompt_manager = prompt_manager

    def analyze(self, findings: list[Finding]) -> AnalysisDecision:
        """
        Validate findings list using the AI provider's structured output.
        """
        if not findings:
            return AnalysisDecision(validated_findings=[], reasoning="No findings to analyze.")

        # Fallback pass-through validation when AI is disabled
        if self.provider is None or self.prompt_manager is None:
            validated = [
                ValidatedFinding(
                    tool=f.tool,
                    target=f.target,
                    data=f.data,
                    severity=f.severity,
                    description=f.description,
                )
                for f in findings
            ]
            return AnalysisDecision(
                validated_findings=validated,
                reasoning="AI reasoning is disabled. Automatic validation pass-through applied.",
            )

        # AI Triaging flow
        serialized_findings = "\n".join(
            f"[{f.tool}] Target: {f.target} | Severity: {f.severity.value} | Description: {f.description}"
            for f in findings
        )

        compiled_prompt = self.prompt_manager.render(
            name="analysis",
            variables={"findings": serialized_findings},
        )

        conversation = Conversation()
        conversation.add_message(Role.SYSTEM, "You are a professional security analyst validation assistant.")
        conversation.add_message(Role.USER, compiled_prompt.rendered_text)

        # Invoke structured generation
        decision = self.provider.structured(conversation, AnalysisDecision)
        
        # Verify result type
        if not isinstance(decision, AnalysisDecision):
            raise ValueError("AI provider returned invalid structured decision type.")
            
        return decision
