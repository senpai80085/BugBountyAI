from __future__ import annotations

import time
from typing import Any, Optional

from core.executor import Executor
from core.logger import logger
from core.registry import ToolRegistry
from engine.workflow import WorkflowEngine
from memory.conversation import Conversation, Role
from models.ai import PlanDecision
from models.capability import Capability
from models.context import ScanContext
from models.objective import Objective, PlanningMode
from models.plan import Plan, PlanResult
from providers.base import AIProvider


class Planner:
    """
    Decides which security scan workflow to run based on user objectives,
    planning modes (AUTO, MANUAL, HYBRID), and dynamically discovered registry capabilities.
    Works independently of AI availability using rule-based and default selection fallbacks.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        workflow_engine: WorkflowEngine,
        provider: Optional[AIProvider] = None,
        executor: Optional[Executor] = None,
    ) -> None:
        self.registry = registry
        self.workflow_engine = workflow_engine
        self.provider = provider
        self.executor = executor

    def run(self, objective: Objective, context: ScanContext) -> PlanResult:
        """
        Execute the entire planning and scanning workflow pipeline.
        Always returns a valid PlanResult and never raises exceptions to the caller.
        """
        plan_start_time = time.perf_counter()
        
        # Default empty plan definition in case planning fails early
        failed_plan = Plan(
            selected_workflow="unknown",
            execution_strategy="none",
            reasoning="Planning phase failed.",
            expected_outputs=[],
            confidence=0.0,
            estimated_duration=0.0,
        )

        try:
            # 1. Normalize Objective
            normalized_text = objective.text.strip().lower()

            # 2. Discover Capabilities dynamically from the registry
            self.registry.discover()
            capabilities = []
            for name in self.registry.list():
                tool_cls = self.registry.get(name)
                capabilities.append(
                    Capability(
                        name=tool_cls.metadata.name,
                        description=tool_cls.metadata.description,
                        tags=tool_cls.metadata.tags,
                        category=tool_cls.metadata.category,
                        supports_parallel=tool_cls.metadata.supports_parallel,
                    )
                )

            # 3. Select Workflow based on Operative Mode
            selected_workflow = "recon"  # Default fallback
            reasoning = "Default rule-based selection."
            decisions: dict[str, Any] = {"mode": objective.mode}

            if objective.mode == PlanningMode.MANUAL:
                if not objective.suggested_workflow:
                    raise ValueError("Manual mode requires suggested_workflow to be specified.")
                selected_workflow = objective.suggested_workflow
                reasoning = "Explicitly requested by user in MANUAL mode."

            elif objective.mode == PlanningMode.HYBRID:
                if objective.suggested_workflow:
                    # Check if suggested workflow exists
                    w_file = self.workflow_engine.workflows_dir / f"{objective.suggested_workflow}.yaml"
                    if w_file.exists():
                        selected_workflow = objective.suggested_workflow
                        reasoning = "User suggestion validated and accepted in HYBRID mode."
                    else:
                        logger.warning(
                            f"Suggested workflow '{objective.suggested_workflow}' not found. "
                            "Falling back to rule-based selection."
                        )
                        selected_workflow, reasoning = self._rule_based_selection(normalized_text)
                else:
                    selected_workflow, reasoning = self._rule_based_selection(normalized_text)

            else:  # AUTO Mode
                # Try AI recommendation first if provider is available
                ai_success = False
                if self.provider is not None:
                    try:
                        ai_success, selected_workflow, reasoning = self._ai_recommendation(
                            objective.text, capabilities
                        )
                        decisions["ai_used"] = ai_success
                    except Exception as e:
                        logger.warning(f"AI planner recommendation failed: {e}. Falling back to rule-based.")

                if not ai_success:
                    selected_workflow, reasoning = self._rule_based_selection(normalized_text)

            decisions["selected_workflow"] = selected_workflow
            decisions["reasoning"] = reasoning

            # 4. Validate Workflow and Capabilities
            workflow = self.workflow_engine.load(selected_workflow)
            
            # Check capabilities
            registered_tools = set(self.registry.list())
            for step in workflow.steps:
                if step.tool not in registered_tools:
                    raise ValueError(f"Required tool capability '{step.tool}' not found in registry.")

            # Compute estimated duration (10 seconds per tool step as baseline)
            est_duration = len(workflow.steps) * 10.0
            
            plan = Plan(
                selected_workflow=selected_workflow,
                execution_strategy="parallel" if any(s.parallel for s in workflow.steps) else "sequential",
                reasoning=reasoning,
                expected_outputs=[f"{s.tool}_output" for s in workflow.steps],
                confidence=0.9 if objective.mode == PlanningMode.MANUAL else 0.8,
                estimated_duration=est_duration,
            )

            planning_duration = time.perf_counter() - plan_start_time

            # 5. Execute Workflow
            exec_start_time = time.perf_counter()
            results = self.workflow_engine.run(workflow, context)
            actual_duration = time.perf_counter() - exec_start_time

            success = all(r.success for r in results) if results else False
            summary = (
                f"Workflow '{selected_workflow}' executed successfully."
                if success
                else "Workflow completed with some step failures."
            )

            return PlanResult(
                plan=plan,
                success=success,
                summary=summary,
                results=results,
                planning_duration=planning_duration,
                actual_duration=actual_duration,
                tool_count=len(workflow.steps),
                decisions=decisions,
            )

        except Exception as e:
            logger.error(f"Planner failed with exception: {e}")
            planning_duration = time.perf_counter() - plan_start_time
            return PlanResult(
                plan=failed_plan,
                success=False,
                summary=f"Failed during planning/execution: {e}",
                results=[],
                planning_duration=planning_duration,
                actual_duration=0.0,
                tool_count=0,
                decisions={"error": str(e)},
            )

    def _rule_based_selection(self, normalized_text: str) -> tuple[str, str]:
        """
        Perform keyword matching logic to select workflow.
        """
        if any(kw in normalized_text for kw in ["recon", "subdomain", "dns", "scan"]):
            return "recon", "Matched recon keywords in target objective."
        return "recon", "Default fallback workflow selected."

    def _ai_recommendation(
        self, objective_text: str, capabilities: list[Capability]
    ) -> tuple[bool, str, str]:
        """
        Consult AIProvider to suggest a workflow from available choices.
        """
        assert self.provider is not None
        
        cap_names = [c.name for c in capabilities]
        prompt = (
            f"Analyze this target objective: '{objective_text}'.\n"
            f"Available tools: {cap_names}.\n"
            f"Select the best workflow to run. Currently available workflows: ['recon']."
        )

        conversation = Conversation()
        conversation.add_message(Role.SYSTEM, "You are a professional scan planner assistant.")
        conversation.add_message(Role.USER, prompt)

        decision = self.provider.structured(conversation, PlanDecision)
        if isinstance(decision, PlanDecision):
            wf_name = decision.selected_workflow.strip()
            reasoning = decision.reasoning
            
            # Confirm workflow file exists on disk
            wf_file = self.workflow_engine.workflows_dir / f"{wf_name}.yaml"
            if wf_file.exists():
                return True, wf_name, reasoning

        return False, "recon", "AI returned invalid workflow. Fallback used."
