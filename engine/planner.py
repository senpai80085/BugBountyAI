from core.executor import Executor
from core.registry import ToolRegistry
from models.context import ScanContext
from models.plan import Plan
from providers.base import AIProvider


class Planner:
    """
    Orchestrator that decides which workflows or tool steps to execute
    using AI reasoning or deterministic static plan fallbacks.
    """

    def __init__(self, registry: ToolRegistry, provider: AIProvider, executor: Executor) -> None:
        self.registry = registry
        self.provider = provider
        self.executor = executor

    def run(self, context: ScanContext) -> Plan:
        """
        Analyze ScanContext and output a structured scanning Plan.
        """
        # Interface stub only
        return Plan(objective=f"Scan {context.target}", steps=["subfinder"])
