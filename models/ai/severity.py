from pydantic import BaseModel, Field

from models.finding import Severity


class SeverityAssessment(BaseModel):
    """
    Structured outcome schema for validating vulnerability severity levels.
    """
    severity: Severity = Field(..., description="Vulnerability severity level")
    justification: str = Field(..., description="Reasoning/justification supporting this severity score")
