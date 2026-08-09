const STAGE_MESSAGES = [
  "Checking web address...",
  "Analyzing...",
  "Finalizing result...",
];

const badge = document.getElementById("badge");
const subtitleEl = document.getElementById("subtitle");
const content = document.getElementById("content");

function setBadge(key, icon, text) {
  badge.className = `badge badge-${key}`;
  badge.innerHTML = `<span class="badge-icon">${icon}</span>${text}`;
}

function setSubtitle(text) {
  subtitleEl.textContent = text || " ";
}

function render(html) {
  content.innerHTML = html;
}

function hostFromUrl(url) {
  try {
    return new URL(url).hostname;
  } catch (err) {
    return "";
  }
}

function heroHtml({ key, label, sub, icon, spinner }) {
  const iconBlock = spinner
    ? `<div class="hero-icon"><div class="spinner"></div></div>`
    : `<div class="hero-icon">${icon}</div>`;
  return `
    <div class="hero hero-${key}">
      ${iconBlock}
      <div class="hero-text">
        <p class="hero-label">${label}</p>
        <p class="hero-sub">${sub}</p>
      </div>
    </div>
  `;
}

function renderStage(index) {
  setBadge("loading", "&#8987;", "CHECKING");
  render(
    heroHtml({
      key: "loading",
      label: "Checking...",
      sub: STAGE_MESSAGES[index],
      spinner: true,
    }),
  );
}

const VERDICT_META = {
  safe: {
    key: "safe",
    label: "Looks safe",
    badgeText: "SAFE",
    icon: "&#10003;",
  },
  suspicious: {
    key: "suspicious",
    label: "Suspicious",
    badgeText: "SUSPICIOUS",
    icon: "!",
  },
  phishing: {
    key: "phishing",
    label: "Likely phishing",
    badgeText: "PHISHING",
    icon: "&#10005;",
  },
};

function verdictCard(result) {
  const meta = VERDICT_META[result.verdict] || {
    key: "neutral",
    label: "Unknown",
    badgeText: "UNKNOWN",
    icon: "?",
  };
  const confidencePct = Math.round(result.confidence * 100);
  const hero = heroHtml({
    key: meta.key,
    label: meta.label,
    sub: `${confidencePct}% phishing likelihood`,
    icon: meta.icon,
  });
  const bar = `
    <div class="progress-track">
      <div class="progress-fill fill-${meta.key}" style="width: ${confidencePct}%"></div>
    </div>
  `;
  const escalateNote = result.would_escalate
    ? `<div class="note-box">
         <span class="note-icon">i</span>
         <span>This page falls in a gray zone our deeper checks aren't built yet to resolve -- treat it with extra caution.</span>
       </div>`
    : "";
  return { meta, html: hero + bar + escalateNote };
}

function errorCard(message) {
  return heroHtml({
    key: "neutral",
    label: "Couldn't check this page",
    sub: message || "The address couldn't be analyzed.",
    icon: "?",
  });
}

function offlineCard() {
  return heroHtml({
    key: "neutral",
    label: "Backend not reachable",
    sub: "Make sure the Cascade Phish Guard server is running.",
    icon: "&#9211;",
  });
}

function unknownCard(message) {
  return heroHtml({
    key: "neutral",
    label: "Nothing to check",
    sub: message || "This isn't a page we can analyze.",
    icon: "&#8211;",
  });
}

function renderDone(result) {
  const { meta, html } = verdictCard(result);
  setBadge(meta.key, meta.icon, meta.badgeText);
  render(html);
}

function renderError(message) {
  setBadge("neutral", "?", "ERROR");
  render(errorCard(message));
}

function renderOffline() {
  setBadge("neutral", "&#9211;", "OFFLINE");
  render(offlineCard());
}

function renderUnknown() {
  setBadge("neutral", "&#8211;", "N/A");
  render(unknownCard());
}

function handleResolvedStatus(status, payload) {
  setBadge("loading", "&#8987;", "CHECKING");
  render(
    heroHtml({
      key: "loading",
      label: "Checking...",
      sub: STAGE_MESSAGES[2],
      spinner: true,
    }),
  );
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
    setSubtitle("");
    renderUnknown();
    return;
  }

  setSubtitle(hostFromUrl(tab.url));
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

const manualForm = document.getElementById("manual-form");
const manualInput = document.getElementById("manual-url");
const manualResultEl = document.getElementById("manual-result");
const manualButton = manualForm.querySelector(".manual-button");

manualForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const url = manualInput.value.trim();
  if (!url) {
    return;
  }

  manualButton.disabled = true;
  manualResultEl.innerHTML = heroHtml({
    key: "loading",
    label: "Checking...",
    sub: "Analyzing...",
    spinner: true,
  });

  checkUrlWithBackend(url).then((outcome) => {
    manualButton.disabled = false;
    if (outcome.status === "done") {
      manualResultEl.innerHTML = verdictCard(outcome.result).html;
    } else if (outcome.status === "offline") {
      manualResultEl.innerHTML = offlineCard();
    } else {
      manualResultEl.innerHTML = errorCard(outcome.message);
    }
  });
});
