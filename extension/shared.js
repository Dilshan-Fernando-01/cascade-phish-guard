const BACKEND_URL = "http://127.0.0.1:8000/analyze";

function checkUrlWithBackend(url) {
  return fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
