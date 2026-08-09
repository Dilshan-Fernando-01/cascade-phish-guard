importScripts("shared.js");

console.log("Cascade Phish Guard: background service worker loaded.");

const tabResults = new Map();

const inFlight = new Map();

function analyzeAndStore(tabId, url) {
  if (inFlight.has(tabId)) {
    return inFlight.get(tabId);
  }

  tabResults.set(tabId, { status: "analyzing" });

  const promise = checkUrlWithBackend(url)
    .then((outcome) => {
      tabResults.set(tabId, outcome);
    })
    .finally(() => {
      inFlight.delete(tabId);
    });

  inFlight.set(tabId, promise);
  return promise;
}

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

  analyzeAndStore(details.tabId, details.url);
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabResults.delete(tabId);
  inFlight.delete(tabId);
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "getTabResult") {
    sendResponse(tabResults.get(message.tabId) || { status: "unknown" });
    return;
  }

  if (message.type === "analyzeTabNow") {
    analyzeAndStore(message.tabId, message.url).then(() => {
      sendResponse(tabResults.get(message.tabId));
    });
    return true;
  }
});
