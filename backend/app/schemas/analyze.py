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
    html: Optional[str] = Field(
        default=None,
        description="Already-rendered page HTML (e.g. from a content script reading the user's own tab). When present, Layer 2 analyzes this directly instead of independently re-rendering the URL with Playwright.",
    )
    skip_layer2: bool = Field(
        default=False,
        description="Force a Layer-1-only pass regardless of full_scan or Layer 1's escalation band. Used for the fast initial check before a page has finished loading.",
    )
    logo_png_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded PNG of the candidate logo cropped from the page. Layer 3's logo check only runs when this is present; the extension supplies it in a later phase.",
    )
    screenshot_png_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded PNG screenshot of the visible tab. Layer 3 only runs in full_scan mode and only when this is present.",
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
    layer1_features: Optional[dict] = Field(
        default=None,
        description="Raw Layer 1 URL features. Always computed (Layer 1 always runs); kept out of the default popup display and meant for a developer/debug view.",
    )
    layer2_features: Optional[dict] = Field(
        default=None,
        description="Raw Layer 2 DOM features, when Layer 2 actually ran. ",
    )
    reasons: Optional[dict] = Field(
        default=None,
        description="Plain-language signals behind each layer's result (no thresholds or values)",
    )
    layer3_results: Optional[dict] = Field(
        default=None,
        description="Layer 3 checks, reported separately (logo_check, banner_wording_check). Present only when Layer 3 actually ran.",
    )
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
