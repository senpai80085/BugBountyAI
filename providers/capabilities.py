from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderCapabilities:
    """
    Strongly typed capabilities profile of an AI provider.
    Allows planners and execution orchestrators to query capacity boundaries.
    """
    provider_name: str
    provider_version: str
    supported_features: list[str] = field(default_factory=list)
    context_window: int = 8192
    max_output_tokens: int = 2048
    supports_embedding: bool = False
    supports_streaming: bool = False
    supports_structured: bool = False
