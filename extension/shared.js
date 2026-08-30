const BACKEND_BASE = "http://127.0.0.1:8000";
const BACKEND_URL = `${BACKEND_BASE}/analyze`;
const API_KEY = "M_jfAWSwXqU56KYHqKvV3sn0_Mo0hEqxmsyx9ErnJHY";

function checkUrlWithBackend(url, fullScan = false, requestId = null) {
  return fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({ url, full_scan: fullScan, request_id: requestId }),
  })
    .then(async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        return {
          status: "error",
          message: body.detail || `Backend returned ${response.status}`,
        };
      }
      const result = await response.json();
      return { status: "done", result };
    })
    .catch((err) => {
      return { status: "offline", message: String(err) };
    });
}

function fetchAnalysisProgress(requestId) {
  return fetch(`${BACKEND_BASE}/analyze/progress/${requestId}`, {
    headers: { "X-API-Key": API_KEY },
  })
    .then((response) => (response.ok ? response.json() : null))
    .catch(() => null);
}
