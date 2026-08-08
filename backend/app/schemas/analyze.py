from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    safe = "safe"
    suspicious = "suspicious"
    phishing = "phishing"


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1, description="The URL to analyze")


class AnalyzeResponse(BaseModel):
    url: str
    verdict: Verdict
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model-reported probability of phishing (0-1)")
    layers_used: list[str] = Field(
        default_factory=list, description="Which analysis layers actually ran, e.g. ['layer1']"
    )
    layer_scores: dict[str, float] = Field(
        default_factory=dict, description="Per-layer raw scores, keyed by layer name"
    )
    would_escalate: bool = Field(
        ..., description="Whether the cascade rule judged this uncertain and would escalate, if a next layer existed"
    )
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
