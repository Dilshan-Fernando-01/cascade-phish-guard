importScripts("shared.js");

console.log("Cascade Phish Guard: background service worker loaded.");

const tabResults = new Map();

const inFlight = new Map();

const tabGeneration = new Map();

function getScanMode() {
  return chrome.storage.local.get(["scanMode"]).then((stored) => stored.scanMode || "quick");
}

function analyzeAndStore(tabId, url, { force = false } = {}) {
  if (!force && inFlight.has(tabId)) {
    return inFlight.get(tabId);
  }

  const generation = (tabGeneration.get(tabId) || 0) + 1;
  tabGeneration.set(tabId, generation);

  tabResults.set(tabId, { status: "analyzing" });

  const promise = getScanMode()
    .then((mode) => checkUrlWithBackend(url, mode === "full").then((outcome) => ({ outcome, mode })))
    .then(({ outcome, mode }) => {
      if (tabGeneration.get(tabId) === generation) {
        tabResults.set(tabId, { ...outcome, modeUsed: mode });
      }
    })
    .finally(() => {
      if (tabGeneration.get(tabId) === generation) {
        inFlight.delete(tabId);
      }
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
  tabGeneration.delete(tabId);
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

  if (message.type === "rescanTab") {
    analyzeAndStore(message.tabId, message.url, { force: true }).then(() => {
      sendResponse(tabResults.get(message.tabId));
    });
    return true;
  }
});
