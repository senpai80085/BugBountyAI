from abc import ABC, abstractmethod


class TelemetryTracker(ABC):
    """
    Interface definition for tracking LLM latency, token usage,
    retry counts, cache hits, and cost estimation telemetry.
    No active implementation required in Phase 4.
    """

    @abstractmethod
    def track_latency(self, provider: str, duration: float) -> None:
        """
        Log latency duration of AI provider requests.
        """
        pass

    @abstractmethod
    def track_tokens(self, provider: str, input_tokens: int, output_tokens: int) -> None:
        """
        Log prompt input and output token counts.
        """
        pass

    @abstractmethod
    def track_retry(self, provider: str, attempt: int) -> None:
        """
        Log invocation retry indexes.
        """
        pass

    @abstractmethod
    def track_cache_hit(self, hit: bool) -> None:
        """
        Log prompt cache hits.
        """
        pass

    @abstractmethod
    def estimate_cost(self, provider: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate financial cost estimation for cost analytics dashboards.
        """
        pass
