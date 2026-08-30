importScripts("shared.js");

console.log("Cascade Phish Guard: background service worker loaded.");

const tabResults = new Map();

const inFlight = new Map();

const tabGeneration = new Map();

function getScanMode() {
  return chrome.storage.local
    .get(["scanMode"])
    .then((stored) => stored.scanMode || "quick");
}

function analyzeAndStore(tabId, url, { force = false } = {}) {
  if (!force && inFlight.has(tabId)) {
    return inFlight.get(tabId);
  }

  const generation = (tabGeneration.get(tabId) || 0) + 1;
  tabGeneration.set(tabId, generation);

  const requestId = crypto.randomUUID();
  let lastProgress = null;

  tabResults.set(tabId, { status: "analyzing" });

  const progressInterval = setInterval(() => {
    if (tabGeneration.get(tabId) !== generation) {
      clearInterval(progressInterval);
      return;
    }
    fetchAnalysisProgress(requestId).then((progress) => {
      if (!progress || tabGeneration.get(tabId) !== generation) return;
      lastProgress = progress;
      const current = tabResults.get(tabId);
      if (current && current.status === "analyzing") {
        tabResults.set(tabId, {
          status: "analyzing",
          stage: progress.stage,
          layer1_score: progress.layer1_score,
        });
      }
    });
  }, 500);

  const promise = getScanMode()
    .then((mode) =>
      checkUrlWithBackend(url, mode === "full", requestId).then((outcome) => ({
        outcome,
        mode,
      })),
    )
    .then(({ outcome, mode }) => {
      let finalOutcome = outcome;

      if (
        outcome.status !== "done" &&
        lastProgress &&
        lastProgress.stage === "done" &&
        lastProgress.result
      ) {
        finalOutcome = { status: "done", result: lastProgress.result };
      }
      if (finalOutcome.status !== "done") {
        console.warn(
          `Cascade Phish Guard: analysis for ${url} resolved as "${finalOutcome.status}"`,
          finalOutcome.message || finalOutcome,
        );
      }
      if (tabGeneration.get(tabId) === generation) {
        tabResults.set(tabId, { ...finalOutcome, modeUsed: mode });
      }
    })
    .finally(() => {
      clearInterval(progressInterval);
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
