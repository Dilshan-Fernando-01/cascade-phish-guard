console.log("Cascade Phish Guard: background service worker loaded.");

const BACKEND_URL = "http://127.0.0.1:8000/analyze";

const tabResults = new Map();

chrome.webNavigation.onBeforeNavigate.addListener((details) => {
  if (details.frameId !== 0) {
    return;
  }

  if (
    !details.url.startsWith("http://") &&
    !details.url.startsWith("https://")
  ) {
    tabResults.delete(details.tabId);
    return;
  }

  tabResults.set(details.tabId, { status: "analyzing" });

  fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: details.url }),
  })
    .then(async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        tabResults.set(details.tabId, {
          status: "error",
          message: body.detail || `Backend returned ${response.status}`,
        });
        return;
      }
      const result = await response.json();
      tabResults.set(details.tabId, { status: "done", result });
    })
    .catch((err) => {
      tabResults.set(details.tabId, {
        status: "offline",
        message: String(err),
      });
    });
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabResults.delete(tabId);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "getTabResult") {
    sendResponse(tabResults.get(message.tabId) || { status: "unknown" });
  }
});
