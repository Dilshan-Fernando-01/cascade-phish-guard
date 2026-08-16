import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "api"))
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main():
    resp = client.get("/health")
    check("GET /health returns 200", resp.status_code == 200)
    check("GET /health status is 'ok'", resp.json().get("status") == "ok")

    resp = client.get("/version")
    check("GET /version returns 200", resp.status_code == 200)
    check("GET /version reports a layer1_model", bool(resp.json().get("layer1_model")))

    # Known legitimate
    resp = client.post("/analyze", json={"url": "https://www.google.com/"})
    check("POST /analyze (google.com) returns 200", resp.status_code == 200)
    check("POST /analyze (google.com) verdict is 'safe'", resp.json().get("verdict") == "safe")

    # Known confirmed phishing URL (manually verified during dataset work)
    resp = client.post("/analyze", json={"url": "https://facebookloginbd.blogspot.com/"})
    check("POST /analyze (known phishing) returns 200", resp.status_code == 200)
    check(
        "POST /analyze (known phishing) verdict is 'suspicious' or 'phishing'",
        resp.json().get("verdict") in ("suspicious", "phishing"),
    )

    # Missing field
    resp = client.post("/analyze", json={})
    check("POST /analyze (missing url) returns 422", resp.status_code == 422)

    # Empty string
    resp = client.post("/analyze", json={"url": ""})
    check("POST /analyze (empty url) returns 422", resp.status_code == 422)

    # Malformed/garbage input
    resp = client.post("/analyze", json={"url": "not a url at all"})
    check("POST /analyze (garbage url) returns 400", resp.status_code == 400)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed:")
        for failure in FAILURES:
            print(f"  - {failure}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
