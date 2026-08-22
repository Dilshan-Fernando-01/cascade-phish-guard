const PRESENTATION_MODE = true;
const STEP_DELAY_MS = PRESENTATION_MODE ? 700 : 120;

const STEP_TITLES = [
  "Web address check",
  "Page content review",
  "Visual comparison",
];

const badge = document.getElementById("badge");
const subtitleEl = document.getElementById("subtitle");
const content = document.getElementById("content");

function setBadge(key, icon, text) {
  badge.className = `badge badge-${key}`;
  badge.innerHTML = `<span class="badge-icon">${icon}</span>${text}`;
}

function setSubtitle(text) {
  subtitleEl.textContent = text || " ";
}

function render(html, target = content) {
  target.innerHTML = html;
}

function hostFromUrl(url) {
  try {
    return new URL(url).hostname;
  } catch (err) {
    return "";
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function heroHtml({ key, label, sub, icon }) {
  return `
    <div class="hero hero-${key}">
      <div class="hero-icon">${icon}</div>
      <div class="hero-text">
        <p class="hero-label">${label}</p>
        <p class="hero-sub">${sub}</p>
      </div>
    </div>
  `;
}

function emptyStateHtml({ icon, title, sub }) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <p class="empty-state-title">${title}</p>
      <p class="empty-state-sub">${sub}</p>
    </div>
  `;
}

function stepIconHtml(status) {
  if (status === "active") return `<div class="step-spinner"></div>`;
  if (status === "done") return "&#10003;";
  if (status === "skipped") return "&#8211;";
  if (status === "unavailable") return "&#8230;";
  return "";
}

function overallProgressHtml(steps) {
  const resolved = steps.filter((s) =>
    ["done", "skipped", "unavailable"].includes(s.status),
  ).length;
  const pct = Math.round((resolved / steps.length) * 100);
  return `
    <div class="overall-progress">
      <div class="overall-progress-track">
        <div class="overall-progress-fill" style="width: ${pct}%"></div>
      </div>
      <span class="overall-progress-label">${pct}%</span>
    </div>
  `;
}

function stepsListHtml(steps) {
  const rows = steps
    .map(
      (s) => `
      <div class="step-row step-${s.status}">
        <div class="step-icon">${stepIconHtml(s.status)}</div>
        <div>
          <p class="step-title">${s.title}</p>
          <p class="step-sub">${s.sub}</p>
        </div>
      </div>
    `,
    )
    .join("");
  return `<div class="steps-list">${rows}</div>`;
}

function renderChecking(steps, target = content) {
  setBadge("loading", "&#8987;", "CHECKING");
  render(overallProgressHtml(steps) + stepsListHtml(steps), target);
}

function deriveStepOutcomes(result) {
  const layer2Ran = (result.layers_used || []).includes("layer2");
  let layer2Status;
  let layer2Sub;
  if (layer2Ran) {
    layer2Status = "done";
    layer2Sub = "Page content reviewed";
  } else if (result.would_escalate) {
    layer2Status = "unavailable";
    layer2Sub =
      "Would run for a borderline case like this (not enabled on this device)";
  } else {
    layer2Status = "skipped";
    layer2Sub = "Skipped -- the web address check alone was conclusive";
  }
  return [
    { status: "done", sub: "Web address analyzed" },
    { status: layer2Status, sub: layer2Sub },
    { status: "unavailable", sub: "Planned for a later phase of this project" },
  ];
}

async function playStepSequence(outcomes, result, target = content) {
  const steps = STEP_TITLES.map((title) => ({
    title,
    status: "pending",
    sub: "Waiting...",
  }));
  steps[0].status = "active";
  steps[0].sub = "Checking the web address...";
  renderChecking(steps, target);

  await wait(STEP_DELAY_MS);
  steps[0].status = outcomes[0].status;
  steps[0].sub = outcomes[0].sub;
  steps[1].status = "active";
  steps[1].sub = "Reviewing page content...";
  renderChecking(steps, target);

  await wait(STEP_DELAY_MS);
  steps[1].status = outcomes[1].status;
  steps[1].sub = outcomes[1].sub;
  steps[2].status = outcomes[2].status;
  steps[2].sub = outcomes[2].sub;
  renderChecking(steps, target);

  await wait(STEP_DELAY_MS);
  renderDoneKeepingSteps(steps, result, target);
}

// --- Verdict + neutral states ----------------------------------------

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

function errorStateHtml(message) {
  return emptyStateHtml({
    icon: "?",
    title: "Couldn't check this page",
    sub: message || "The address couldn't be analyzed.",
  });
}

function offlineStateHtml() {
  return emptyStateHtml({
    icon: "&#9211;",
    title: "Backend not reachable",
    sub: "Make sure the Cascade Phish Guard server is running.",
  });
}

function unknownStateHtml(message) {
  return emptyStateHtml({
    icon: "&#8211;",
    title: "Nothing to check",
    sub: message || "This isn't a page we can analyze.",
  });
}

function renderDone(result, target = content) {
  const { meta, html } = verdictCard(result);
  setBadge(meta.key, meta.icon, meta.badgeText);
  render(html, target);
}

// Keeps the resolved step checklist on screen and appends the verdict
// card after it, instead of replacing the checklist with the verdict.
function renderDoneKeepingSteps(steps, result, target = content) {
  const { meta, html } = verdictCard(result);
  setBadge(meta.key, meta.icon, meta.badgeText);
  render(overallProgressHtml(steps) + stepsListHtml(steps) + html, target);
}

function renderError(message, target = content) {
  setBadge("neutral", "?", "ERROR");
  render(errorStateHtml(message), target);
}

function renderOffline(target = content) {
  setBadge("neutral", "&#9211;", "OFFLINE");
  render(offlineStateHtml(), target);
}

function renderUnknown(target = content) {
  setBadge("neutral", "&#8211;", "N/A");
  render(unknownStateHtml(), target);
}

function renderInitialChecking(target = content) {
  const steps = STEP_TITLES.map((title, i) => ({
    title,
    status: i === 0 ? "active" : "pending",
    sub: i === 0 ? "Checking the web address..." : "Waiting...",
  }));
  renderChecking(steps, target);
}

function handleResolvedStatus(status, payload, target = content) {
  if (status === "done") {
    const outcomes = deriveStepOutcomes(payload.result);
    playStepSequence(outcomes, payload.result, target);
  } else if (status === "offline") {
    renderOffline(target);
  } else if (status === "error") {
    renderError(payload.message, target);
  } else {
    renderUnknown(target);
  }
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
  renderInitialChecking();

  chrome.runtime.sendMessage(
    { type: "getTabResult", tabId: tab.id },
    (response) => {
      if (response && response.status === "analyzing") {
        pollUntilDone(tab.id);
        return;
      }

      if (!response || response.status === "unknown") {
        chrome.runtime.sendMessage(
          { type: "analyzeTabNow", tabId: tab.id, url: tab.url },
          (analyzed) => {
            handleResolvedStatus(analyzed.status, analyzed);
          },
        );
        return;
      }

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
  renderInitialChecking(manualResultEl);

  checkUrlWithBackend(url).then((outcome) => {
    manualButton.disabled = false;
    if (outcome.status === "done") {
      const outcomes = deriveStepOutcomes(outcome.result);
      playStepSequence(outcomes, outcome.result, manualResultEl);
    } else if (outcome.status === "offline") {
      render(offlineStateHtml(), manualResultEl);
    } else {
      render(errorStateHtml(outcome.message), manualResultEl);
    }
  });
});
