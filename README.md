# Cascade Phish Guard

A three-layer, cascaded machine learning system for real-time phishing website detection — a browser extension backed by a local Python analysis service.

## What it does

Most phishing detectors look at one signal: the URL, or the page's structure, or its visual appearance. Each view alone misses attacks the others would catch. This project scores every visited page through up to three layers, escalating only when necessary:

1. **Layer 1 — URL Analysis.** Lexical and domain-level features, scored instantly by an ML classifier.
2. **Layer 2 — DOM Analysis.** If Layer 1 is uncertain, the page is loaded in a sandboxed headless browser and its structure, scripts, and embedded content are analysed. URLs found inside the page are re-scored through Layer 1 as secondary evidence.
3. **Layer 3 — Visual Analysis.** If still uncertain, a screenshot is compared against known brand reference images using CNN-based similarity models.

Cheap checks resolve the obvious cases; expensive analysis only runs on genuinely ambiguous pages. Everything runs locally — no page content or URL is ever sent to an external server.

## Architecture

```
Browser Extension (JS)
        │  visited URL
        ▼
FastAPI local backend
        │
   ┌────┴────┐
   │ Layer 1 │  URL features → Logistic Regression / Random Forest / XGBoost / MLP
   └────┬────┘
        │ uncertain?
        ▼
   ┌─────────┐
   │ Layer 2 │  DOM features (Playwright + BeautifulSoup) → RF / XGBoost / SVM / MLP
   └────┬────┘  + bounded re-scan of embedded URLs through Layer 1
        │ uncertain?
        ▼
   ┌─────────┐
   │ Layer 3 │  Screenshot vs. brand reference → MobileNetV2 / EfficientNet-B0 / ResNet-50 / Siamese
   └────┬────┘
        ▼
   Final verdict + confidence
```

## Tech stack

- **Backend:** Python, FastAPI, scikit-learn, XGBoost, PyTorch/Keras, Playwright, BeautifulSoup
- **Extension:** JavaScript (Chromium, Manifest V3)
- **Data:** PhishTank + OpenPhish (dual-source confirmed phishing), Tranco (legitimate)

## Project structure

```
backend/
  api/            # FastAPI routes
  app/
    features/     # feature extraction modules (url_features.py, brand_reference.py)
    models/       # thin wrappers around trained model artifacts
    services/     # orchestration (page loading, analyzers, cascade logic)
    schemas/      # Pydantic request/response models
scripts/
  data_collection/  # one script per data source
  data_filtering/   # validation, dedup, agreement checks, feature build, splits
  training/         # one script per model (common.py holds shared prep/eval logic)
  reporting/        # evidence-pack generation for the paper
data/
  raw/            # untouched downloads (not tracked in git)
  processed/      # cleaned/labelled datasets, feature tables, train/val/test splits
  reports/        # model comparison tables, filtering summaries, figures/
  models/         # trained model artifacts (.joblib, not tracked in git)
notebooks/        # exploratory data analysis, model comparison reports
extension/        # browser extension
tests/            # unit tests
docs/             # architecture notes, future-feature ideas
```

## Project status

| Phase | Status |
|---|---|
| 0 — Project setup | ☑ |
| 1–3 — Dataset collection, filtering, EDA | ☑ (dataset collection continues running in the background; pipeline itself is complete) |
| 4 — Layer 1 (URL) | ☑ all 4 models trained (Logistic Regression, Random Forest, XGBoost, MLP), compared, winner selected |
| 5 — Layer 2 (DOM) | ☐ |
| 6 — FastAPI backend | ☐ |
| 7 — Browser extension | ☐ |
| 8 — Layer 3 (visual) | ☐ |
| 9 — Ensemble / cascade integration | ☐ |
| 10 — Evaluation & evidence pack | ☐ |

## Setup

```bash
git clone <repo-url>
cd cascade-phish-guard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Academic context

This is a final-year research project. The accompanying paper is titled *"A Multi-Layer Machine Learning Framework for Real-Time Phishing Website Detection."* See the project's research documentation for full objectives, scope, and evaluation methodology.
