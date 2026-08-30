from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    safe = "safe"
    suspicious = "suspicious"
    phishing = "phishing"


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1, description="The URL to analyze")
    full_scan: bool = Field(
        default=False,
        description="Run every available layer regardless of Layer 1's confidence, instead of only escalating on an uncertain score",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Client-generated id for polling live progress via GET /analyze/progress/{request_id} while this request is still in flight",
    )


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
    layer2_features: Optional[dict] = Field(
        default=None,
        description="Raw Layer 2 DOM features, when Layer 2 actually ran. ",
    )
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
