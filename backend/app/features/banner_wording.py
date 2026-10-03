import io
import re

import pytesseract
from PIL import Image

URGENCY_PHRASES = [
    "account suspended",
    "account will be closed",
    "unusual activity",
    "verify your account",
    "confirm your identity",
    "update your payment",
    "limited time",
    "act now",
    "your account has been",
    "security alert",
]

CALL_TO_ACTION_PHRASES = [
    "verify now",
    "click here",
    "download now",
    "login now",
    "sign in now",
    "update now",
]

MATCH_WEIGHT = 0.25
DUPLICATE_WEIGHT = 0.25
MAX_DUPLICATE_COUNT = 2


def _normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_text(png_bytes):
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    return pytesseract.image_to_string(image)


def banner_wording_features(png_bytes):
    raw_text = extract_text(png_bytes)
    text = _normalize(raw_text)

    matched = sorted(p for p in URGENCY_PHRASES + CALL_TO_ACTION_PHRASES if p in text)

    duplicate_cta = 0
    for phrase in CALL_TO_ACTION_PHRASES:
        count = text.count(phrase)
        if count > 1:
            duplicate_cta += count - 1

    score = min(
        1.0,
        MATCH_WEIGHT * len(matched) + DUPLICATE_WEIGHT * min(duplicate_cta, MAX_DUPLICATE_COUNT),
    )

    return {
        "matched_phrases": matched,
        "duplicate_cta_count": duplicate_cta,
        "text_length": len(text),
        "score": round(score, 4),
    }
