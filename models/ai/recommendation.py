from pydantic import BaseModel, Field


class WorkflowRecommendation(BaseModel):
    """
    Structured outcome schema for scan next action recommendations.
    """
    recommended_actions: list[str] = Field(default_factory=list, description="Recommended scanning actions or commands")
    workflow_suggestions: list[str] = Field(default_factory=list, description="Alternative workflows recommended")
    reasoning: str = Field(..., description="Details explaining why these steps are recommended")
