importScripts("shared.js");

console.log("Cascade Phish Guard: background service worker loaded.");

const tabResults = new Map();

const inFlight = new Map();

const tabGeneration = new Map();

const PAGE_COMPLETE_FALLBACK_MS = 20000;

const pageCompleteWaiters = new Map();

function getScanMode() {
  return chrome.storage.local
    .get(["scanMode"])
    .then((stored) => stored.scanMode || "quick");
}

function removeWaiter(tabId, entry) {
  const list = pageCompleteWaiters.get(tabId);
  if (!list) return;
  const next = list.filter((w) => w !== entry);
  if (next.length) {
    pageCompleteWaiters.set(tabId, next);
  } else {
    pageCompleteWaiters.delete(tabId);
  }
}

function waitForPageComplete(tabId, generation) {
  return chrome.tabs
    .get(tabId)
    .then((tab) => {
      if (tab.status === "complete") {
        return true;
      }
      return new Promise((resolve) => {
        const entry = { generation, resolve, timer: null };
        entry.timer = setTimeout(() => {
          removeWaiter(tabId, entry);
          resolve(tabGeneration.get(tabId) === generation);
        }, PAGE_COMPLETE_FALLBACK_MS);
        const list = pageCompleteWaiters.get(tabId) || [];
        list.push(entry);
        pageCompleteWaiters.set(tabId, list);
      });
    })
    .catch(() => false);
}

chrome.webNavigation.onCompleted.addListener((details) => {
  if (details.frameId !== 0) return;
  const waiters = pageCompleteWaiters.get(details.tabId);
  if (!waiters) return;
  pageCompleteWaiters.delete(details.tabId);
  waiters.forEach(({ generation, resolve, timer }) => {
    clearTimeout(timer);
    resolve(tabGeneration.get(details.tabId) === generation);
  });
});

// Reads the DOM the user is already looking at, instead of having the
// backend visit the URL a second time itself -- the page only ever renders
// once, in the user's own browser session.
function grabRenderedHtml(tabId) {
  return chrome.scripting
    .executeScript({
      target: { tabId, frameIds: [0] },
      func: () => document.documentElement.outerHTML,
    })
    .then((results) => (results && results[0] ? results[0].result : null))
    .catch(() => null);
}

function pollProgressInto(tabId, generation, requestId) {
  let lastProgress = null;
  const interval = setInterval(() => {
    if (tabGeneration.get(tabId) !== generation) {
      clearInterval(interval);
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
  return {
    stop: () => clearInterval(interval),
    getLast: () => lastProgress,
  };
}

function runBackendCall(
  tabId,
  generation,
  url,
  { fullScan, html, skipLayer2 },
) {
  const requestId = crypto.randomUUID();
  const progress = pollProgressInto(tabId, generation, requestId);
  return checkUrlWithBackend(url, fullScan, requestId, html, skipLayer2)
    .then((outcome) => {
      const lastProgress = progress.getLast();
      if (
        outcome.status !== "done" &&
        lastProgress &&
        lastProgress.stage === "done" &&
        lastProgress.result
      ) {
        return { status: "done", result: lastProgress.result };
      }
      return outcome;
    })
    .finally(() => progress.stop());
}

function analyzeAndStore(tabId, url, { force = false } = {}) {
  if (!force && inFlight.has(tabId)) {
    return inFlight.get(tabId);
  }

  const generation = (tabGeneration.get(tabId) || 0) + 1;
  tabGeneration.set(tabId, generation);

  tabResults.set(tabId, { status: "analyzing" });

  const promise = getScanMode()
    .then((mode) => {
      const fullScan = mode === "full";

      // Fast pass: Layer 1 (URL-only) never needs the page to have loaded,
      // so this runs immediately regardless of scan mode.
      return runBackendCall(tabId, generation, url, {
        fullScan: false,
        html: null,
        skipLayer2: true,
      }).then((firstOutcome) => {
        if (tabGeneration.get(tabId) !== generation) return;

        if (firstOutcome.status !== "done") {
          console.warn(
            `Cascade Phish Guard: layer 1 check for ${url} resolved as "${firstOutcome.status}"`,
            firstOutcome.message || firstOutcome,
          );
          tabResults.set(tabId, { ...firstOutcome, modeUsed: mode });
          return;
        }

        const needsLayer2 = fullScan || firstOutcome.result.would_escalate;
        if (!needsLayer2) {
          tabResults.set(tabId, { ...firstOutcome, modeUsed: mode });
          return;
        }

        // Stay "analyzing" -- a deeper content check is still coming. Wait
        // for the real navigation to finish, then read its rendered DOM.
        // If that fails for any reason (restricted page, injection error),
        // fall back to the backend's own Playwright-based Layer 2 exactly
        // as before -- html stays null, which is what the backend already
        // treats as "load it yourself".
        return waitForPageComplete(tabId, generation)
          .then((stillCurrent) => {
            if (!stillCurrent || tabGeneration.get(tabId) !== generation) {
              return null;
            }
            return grabRenderedHtml(tabId);
          })
          .then((html) => {
            if (tabGeneration.get(tabId) !== generation) return;
            return runBackendCall(tabId, generation, url, {
              fullScan,
              html,
              skipLayer2: false,
            }).then((finalOutcome) => {
              if (tabGeneration.get(tabId) !== generation) return;
              if (finalOutcome.status !== "done") {
                console.warn(
                  `Cascade Phish Guard: analysis for ${url} resolved as "${finalOutcome.status}"`,
                  finalOutcome.message || finalOutcome,
                );
              }
              tabResults.set(tabId, { ...finalOutcome, modeUsed: mode });
            });
          });
      });
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
  pageCompleteWaiters.delete(tabId);
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
