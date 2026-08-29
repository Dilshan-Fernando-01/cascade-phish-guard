const BACKEND_URL = "http://127.0.0.1:8000/analyze";
const API_KEY = "M_jfAWSwXqU56KYHqKvV3sn0_Mo0hEqxmsyx9ErnJHY";

function checkUrlWithBackend(url) {
  return fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify({ url }),
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
