const STAGE_MESSAGES = [
  "Checking web address...",
  "Analyzing...",
  "Finalizing result...",
];

const topbar = document.getElementById("topbar");
const badge = document.getElementById("badge");
const content = document.getElementById("content");

function setChrome(stateKey, badgeText) {
  topbar.className = `topbar topbar-${stateKey}`;
  badge.className = `badge badge-${stateKey}`;
  badge.textContent = badgeText;
}

function render(html) {
  content.innerHTML = html;
}

function renderStage(index) {
  setChrome("loading", "CHECKING");
  render(`
    <div class="state">
      <div class="spinner"></div>
      <p class="stage-text">${STAGE_MESSAGES[index]}</p>
    </div>
  `);
}

const VERDICT_META = {
  safe: { key: "safe", label: "Looks safe", badge: "SAFE", icon: "&#10003;" },
  suspicious: {
    key: "suspicious",
    label: "Suspicious",
    badge: "SUSPICIOUS",
    icon: "!",
  },
  phishing: {
    key: "phishing",
    label: "Likely phishing",
    badge: "PHISHING",
    icon: "&#10005;",
  },
};

function renderDone(result) {
  const meta = VERDICT_META[result.verdict] || {
    key: "neutral",
    label: "Unknown",
    badge: "UNKNOWN",
    icon: "?",
  };
  setChrome(meta.key, meta.badge);

  const confidencePct = Math.round(result.confidence * 100);
  const escalateNote = result.would_escalate
    ? `<div class="note-box">
         <span class="note-icon">i</span>
         <span>This page falls in a gray zone our deeper checks aren't built yet to resolve -- treat it with extra caution.</span>
       </div>`
    : "";

  render(`
    <div class="state">
      <div class="verdict-icon icon-${meta.key}">${meta.icon}</div>
      <p class="verdict-label">${meta.label}</p>
      <div class="progress-row">
        <span>Phishing likelihood</span>
        <span class="progress-value">${confidencePct}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill fill-${meta.key}" style="width: ${confidencePct}%"></div>
      </div>
      ${escalateNote}
    </div>
  `);
}

function renderError(message) {
  setChrome("neutral", "ERROR");
  render(`
    <div class="state">
      <div class="verdict-icon icon-neutral">?</div>
      <p class="verdict-label">Couldn't check this page</p>
      <p class="note">${message || "The address couldn't be analyzed."}</p>
    </div>
  `);
}

function renderOffline() {
  setChrome("neutral", "OFFLINE");
  render(`
    <div class="state">
      <div class="verdict-icon icon-neutral">&#9211;</div>
      <p class="verdict-label">Backend not reachable</p>
      <p class="note">Make sure the Cascade Phish Guard server is running.</p>
    </div>
  `);
}

function renderUnknown() {
  setChrome("neutral", "N/A");
  render(`
    <div class="state">
      <p class="note">Nothing to check on this page.</p>
    </div>
  `);
}

function handleResolvedStatus(status, payload) {
  renderStage(2);
  setTimeout(() => {
    if (status === "done") {
      renderDone(payload.result);
    } else if (status === "offline") {
      renderOffline();
    } else if (status === "error") {
      renderError(payload.message);
    } else {
      renderUnknown();
    }
  }, 350);
}

function pollUntilDone(tabId, attempt = 0) {
  if (attempt > 20) {
    renderError("Taking longer than expected.");
    return;
  }
  setTimeout(() => {
    chrome.runtime.sendMessage({ type: "getTabResult", tabId }, (response) => {
      if (!response) return;
      if (response.status === "analyzing") {
        pollUntilDone(tabId, attempt + 1);
      } else {
        handleResolvedStatus(response.status, response);
      }
    });
  }, 500);
}

async function main() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (
    !tab ||
    !tab.url ||
    !(tab.url.startsWith("http://") || tab.url.startsWith("https://"))
  ) {
    renderUnknown();
    return;
  }

  renderStage(0);
  const stageTimer = setTimeout(() => renderStage(1), 900);

  chrome.runtime.sendMessage(
    { type: "getTabResult", tabId: tab.id },
    (response) => {
      if (response && response.status === "analyzing") {
        clearTimeout(stageTimer);
        pollUntilDone(tab.id);
        return;
      }

      if (!response || response.status === "unknown") {
        chrome.runtime.sendMessage(
          { type: "analyzeTabNow", tabId: tab.id, url: tab.url },
          (analyzed) => {
            clearTimeout(stageTimer);
            handleResolvedStatus(analyzed.status, analyzed);
          },
        );
        return;
      }

      clearTimeout(stageTimer);
      handleResolvedStatus(response.status, response);
    },
  );
}

main();
