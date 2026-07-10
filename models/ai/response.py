from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """
    Standardized wrapper enclosing the raw text response and exact cost/latency telemetry.
    """
    content: str = Field(..., description="Raw text outcome of the LLM content generation")
    input_tokens: int = Field(default=0, description="Tokens in user and system prompts")
    output_tokens: int = Field(default=0, description="Tokens in generation completion output")
    total_tokens: int = Field(default=0, description="Total input + output tokens consumed")
    estimated_cost: float = Field(default=0.0, description="Estimated dollar cost of token generation")
    provider_latency: float = Field(default=0.0, description="Response time in seconds")
