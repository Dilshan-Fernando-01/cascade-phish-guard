import concurrent.futures
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
from schemas.analyze import AnalyzeRequest, AnalyzeResponse
from schemas.system import HealthResponse, VersionResponse
from services.cascade_analyzer import analyze as run_cascade_analysis

load_dotenv()

APP_VERSION = "0.1.0"
_COMPARISON_PATH = Path(__file__).resolve().parents[2] / "data" / "reports" / "layer1_model_comparison.json"
_API_KEY = os.environ.get("API_KEY")


REQUEST_TIMEOUT_SECONDS = 12

EXTENSION_ORIGIN = "chrome-extension://ecnkllhbcnponkmgmeenkoijnpkociaj"

app = FastAPI(title="Cascade Phish Guard API", version=APP_VERSION)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[EXTENSION_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def verify_api_key(x_api_key: str = Header(default=None)):
    if not _API_KEY:
        raise RuntimeError("API_KEY is not set on the server -- refusing to serve /analyze")
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid API key")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.get("/version", response_model=VersionResponse)
def version():
    layer1_model_name = "unknown"
    try:
        with open(_COMPARISON_PATH) as f:
            layer1_model_name = json.load(f)["winner"]
    except Exception:
        pass
    return VersionResponse(version=APP_VERSION, layer1_model=layer1_model_name)


@app.post("/analyze", response_model=AnalyzeResponse, dependencies=[Depends(verify_api_key)])
def analyze_url(request: AnalyzeRequest):
    future = _executor.submit(run_cascade_analysis, request.url, request.full_scan)
    try:
        return future.result(timeout=REQUEST_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyze URL: {exc}")
