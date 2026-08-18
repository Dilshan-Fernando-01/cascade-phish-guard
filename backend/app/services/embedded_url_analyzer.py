import os
import sys
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.layer1_model import predict as layer1_predict

MAX_URLS_PER_PAGE = 30
TIME_BUDGET_SECONDS = 10
SUSPICIOUS_THRESHOLD = 0.5


def extract_embedded_urls(html, base_url, network_urls=None):
    soup = BeautifulSoup(html or "", "html.parser")
    raw_urls = []

    for tag in soup.find_all("a", href=True):
        raw_urls.append(tag["href"])
    for tag in soup.find_all("iframe", src=True):
        raw_urls.append(tag["src"])
    for tag in soup.find_all("form", action=True):
        raw_urls.append(tag["action"])
    for tag in soup.find_all("script", src=True):
        raw_urls.append(tag["src"])
    for tag in soup.find_all("link", href=True):
        raw_urls.append(tag["href"])
    for tag in soup.find_all("img", src=True):
        raw_urls.append(tag["src"])
    for tag in soup.find_all("meta", attrs={"http-equiv": lambda v: v and v.lower() == "refresh"}):
        content = tag.get("content", "")
        if "url=" in content.lower():
            raw_urls.append(content.lower().split("url=", 1)[1].strip())

    if network_urls:
        raw_urls.extend(network_urls)

    resolved = []
    seen = set()
    for raw in raw_urls:
        if not raw or raw.startswith(("javascript:", "data:", "#", "mailto:")):
            continue
        absolute = urljoin(base_url, raw)
        if absolute in seen:
            continue
        seen.add(absolute)
        resolved.append(absolute)
        if len(resolved) >= MAX_URLS_PER_PAGE:
            break

    return resolved


def analyze_embedded_urls(html, base_url, network_urls=None):
    urls = extract_embedded_urls(html, base_url, network_urls)

    scores = []
    start = time.monotonic()
    for embedded_url in urls:
        if time.monotonic() - start > TIME_BUDGET_SECONDS:
            break
        try:
            score, _features = layer1_predict(embedded_url)
            scores.append(score)
        except Exception:
           
            continue

    if not scores:
        return {
            "suspicious_embedded_url_count": 0,
            "max_embedded_url_risk": 0.0,
            "avg_embedded_url_risk": 0.0,
        }

    suspicious_count = sum(1 for s in scores if s > SUSPICIOUS_THRESHOLD)

    return {
        "suspicious_embedded_url_count": suspicious_count,
        "max_embedded_url_risk": round(max(scores), 4),
        "avg_embedded_url_risk": round(sum(scores) / len(scores), 4),
    }
