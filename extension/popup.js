const LOW_THRESHOLD = 0.2;
const HIGH_THRESHOLD = 0.8;

const STAGE_CHECKING_ADDRESS = "checking_address";
const STAGE_REVIEWING_CONTENT = "reviewing_content";
const STAGE_DONE = "done";

const STEP_TITLES = [
  "Web address check",
  "Page content review",
  "Visual comparison",
];

const LAYER_SUBSTEPS = [
  [
    "Analyzing URL structure",
    "Checking domain reputation",
    "Cross-referencing threat lists",
  ],
  [
    "Loading page content",
    "Scanning page structure",
    "Checking embedded links",
  ],
  [],
];

const badge = document.getElementById("badge");
const subtitleEl = document.getElementById("subtitle");
const content = document.getElementById("content");
const scanModeToggle = document.getElementById("scan-mode-toggle");
const scanModeHint = document.getElementById("scan-mode-hint");

let scanMode = "quick";
let currentTab = null;

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

function emptyStateHtml({ icon, title, sub }) {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <p class="empty-state-title">${title}</p>
      <p class="empty-state-sub">${sub}</p>
    </div>
  `;
}

function gaugeArcPath(size, strokeWidth) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - strokeWidth / 2 - 1;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const startDeg = 135;
  const endDeg = 405;
  const x1 = cx + r * Math.cos(toRad(startDeg));
  const y1 = cy + r * Math.sin(toRad(startDeg));
  const x2 = cx + r * Math.cos(toRad(endDeg));
  const y2 = cy + r * Math.sin(toRad(endDeg));
  return `M ${x1.toFixed(2)},${y1.toFixed(2)} A ${r.toFixed(2)},${r.toFixed(2)} 0 1,1 ${x2.toFixed(2)},${y2.toFixed(2)}`;
}

function statusForScore(score) {
  if (score > HIGH_THRESHOLD) return { key: "critical", label: "Phishing" };
  if (score < LOW_THRESHOLD) return { key: "good", label: "Safe" };
  return { key: "warning", label: "Suspicious" };
}

function statusForVerdict(verdict) {
  if (verdict === "phishing") return { key: "critical", label: "Phishing" };
  if (verdict === "safe") return { key: "good", label: "Safe" };
  if (verdict === "suspicious") return { key: "warning", label: "Suspicious" };
  return { key: "neutral", label: "Unknown" };
}

function gaugeHtml({ id, size, strokeWidth, big, label }) {
  const path = gaugeArcPath(size, strokeWidth);
  const valueSize = big ? "gauge-big" : "gauge-small";
  return `
    <div class="${big ? "gauge-big-wrap" : "gauge-small-wrap"}">
      <svg class="gauge-svg" viewBox="0 0 ${size} ${size}">
        <path class="gauge-track" d="${path}" stroke-width="${strokeWidth}" />
        <path
          class="gauge-fill gauge-neutral"
          id="${id}"
          d="${path}"
          stroke-width="${strokeWidth}"
          pathLength="100"
          style="stroke-dashoffset: 100"
        />
      </svg>
      <div class="gauge-center ${valueSize}">
        <span class="gauge-value" id="${id}-value">--</span>
        <span class="gauge-status-label gauge-neutral" id="${id}-status">${label || ""}</span>
      </div>
    </div>
  `;
}

function animateGauge(id, { value, statusKey, statusLabel }) {
  const fillEl = document.getElementById(id);
  const valueEl = document.getElementById(`${id}-value`);
  const statusEl = document.getElementById(`${id}-status`);
  if (!fillEl) return;

  requestAnimationFrame(() => {
    fillEl.className = `gauge-fill gauge-${statusKey}`;
    fillEl.style.strokeDashoffset = String(100 - value);
    if (valueEl) valueEl.textContent = `${Math.round(value)}%`;
    if (statusEl) {
      statusEl.className = `gauge-status-label gauge-${statusKey}`;
      statusEl.textContent = statusLabel;
    }
  });
}

function gaugeRowHtml(fullScanMode, ns) {
  if (!fullScanMode) {
    return `
      <div class="gauge-row">
        ${gaugeHtml({ id: `${ns}-gauge-overall`, size: 148, strokeWidth: 14, big: true })}
      </div>
    `;
  }
  return `
    <div class="gauge-row">
      ${gaugeHtml({ id: `${ns}-gauge-overall`, size: 148, strokeWidth: 14, big: true })}
      <div class="gauge-small-row">
        <div class="gauge-small-col">
          ${gaugeHtml({ id: `${ns}-gauge-layer1`, size: 72, strokeWidth: 8, big: false })}
          <p class="gauge-small-label">Web address</p>
        </div>
        <div class="gauge-small-col">
          ${gaugeHtml({ id: `${ns}-gauge-layer2`, size: 72, strokeWidth: 8, big: false })}
          <p class="gauge-small-label">Page content</p>
        </div>
        <div class="gauge-small-col">
          ${gaugeHtml({ id: `${ns}-gauge-layer3`, size: 72, strokeWidth: 8, big: false, label: "N/A" })}
          <p class="gauge-small-label">Visual</p>
        </div>
      </div>
    </div>
  `;
}

function pulseGauge(id) {
  const wrap = document
    .getElementById(id)
    ?.closest(".gauge-big-wrap, .gauge-small-wrap");
  if (!wrap) return;
  wrap.classList.remove("is-updating");
  void wrap.offsetWidth;
  wrap.classList.add("is-updating");
}

function animateResultGauges(result, fullScanMode, ns) {
  const overallStatus = statusForVerdict(result.verdict);
  animateGauge(`${ns}-gauge-overall`, {
    value: result.confidence * 100,
    statusKey: overallStatus.key,
    statusLabel: overallStatus.label,
  });

  if (!fullScanMode) return;

  const layer1Score = result.layer_scores && result.layer_scores.layer1;
  if (typeof layer1Score === "number") {
    const s = statusForScore(layer1Score);
    animateGauge(`${ns}-gauge-layer1`, {
      value: layer1Score * 100,
      statusKey: s.key,
      statusLabel: s.label,
    });
  }

  const layer2Score = result.layer_scores && result.layer_scores.layer2;
  if (typeof layer2Score === "number") {
    const s = statusForScore(layer2Score);
    animateGauge(`${ns}-gauge-layer2`, {
      value: layer2Score * 100,
      statusKey: s.key,
      statusLabel: s.label,
    });
  } else {
    animateGauge(`${ns}-gauge-layer2`, {
      value: 0,
      statusKey: "neutral",
      statusLabel: "N/A",
    });
  }

  animateGauge(`${ns}-gauge-layer3`, {
    value: 0,
    statusKey: "neutral",
    statusLabel: "N/A",
  });
}

function stepIconHtml(status) {
  if (status === "active") return `<div class="step-spinner"></div>`;
  if (status === "done") return "&#10003;";
  if (status === "skipped") return "&#8211;";
  if (status === "unavailable") return "&#8230;";
  return "";
}

// A summary pill showing analysis PROGRESS (how many layers have run) --
// distinct from the gauges above, which show the RISK score. "Resolved"
// covers done/skipped/unavailable -- anything no longer waiting or active.
function progressSummaryHtml(steps) {
  const resolved = steps.filter((s) =>
    ["done", "skipped", "unavailable"].includes(s.status),
  ).length;
  const pct = Math.round((resolved / steps.length) * 100);
  const allDone = resolved === steps.length;
  return `
    <div class="progress-summary">
      <div class="progress-summary-icon ${allDone ? "is-done" : ""}">${allDone ? "&#10003;" : ""}</div>
      <span class="progress-summary-count">${resolved} of ${steps.length}</span>
      <div class="progress-summary-track">
        <div class="progress-summary-fill" style="width: ${pct}%"></div>
      </div>
      <span class="progress-summary-pct">${pct}%</span>
    </div>
  `;
}

// The mini progress pill + checklist inside one layer's own card, tracking
// that layer's sub-steps (not the score, not the outer 3-layer progress).
function substepChecklistHtml(index, doneCount) {
  const labels = LAYER_SUBSTEPS[index] || [];
  if (labels.length === 0) return "";
  const syntheticSteps = labels.map((_, i) => ({
    status: i < doneCount ? "done" : "pending",
  }));
  const rows = labels
    .map(
      (label, i) => `
      <div class="substep-row ${i < doneCount ? "is-done" : ""}">
        <span class="substep-icon">${i < doneCount ? "&#10003;" : ""}</span>
        <span class="substep-label">${label}</span>
      </div>
    `,
    )
    .join("");
  return `${progressSummaryHtml(syntheticSteps)}<div class="substep-list">${rows}</div>`;
}

function embeddedUrlSummaryHtml(features) {
  if (!features) return "";
  const checked = features.checked_embedded_url_count;
  if (!checked) return "";
  const suspicious = features.suspicious_embedded_url_count || 0;
  const linkWord = checked === 1 ? "link" : "links";
  let line;
  if (suspicious === 0) {
    line = `Checked ${checked} embedded ${linkWord} on this page -- none looked suspicious.`;
  } else {
    const maxRisk = Math.round((features.max_embedded_url_risk || 0) * 100);
    const flagWord = suspicious === 1 ? "link" : "links";
    line = `Checked ${checked} embedded ${linkWord} on this page -- ${suspicious} ${flagWord} looked suspicious (highest risk: ${maxRisk}%).`;
  }
  return `<div class="embedded-url-summary">${line}</div>`;
}

function layerCardHtml(step, index) {
  const substeps = LAYER_SUBSTEPS[index] || [];

  const showSubsteps =
    !step.receiving &&
    substeps.length > 0 &&
    (step.status === "active" || step.status === "done");
  // Default to 0 (not started) while still active, and only assume "fully
  // done" once the layer has actually resolved -- the previous fallback
  // defaulted to fully-done any time substepsDone wasn't set yet, which
  // included the very first render of a newly-active layer, showing 100%
  // before the animation had even started.
  const defaultSubstepsDone = step.status === "done" ? substeps.length : 0;
  const detail = showSubsteps
    ? substepChecklistHtml(index, step.substepsDone ?? defaultSubstepsDone) +
      (step.extraDetail || "")
    : step.detail;
  // Only show the expandable body/chevron when there's real additional
  // detail to show -- previously this fell back to repeating `sub`,
  // showing the exact same line twice for no reason.
  const hasDetail = Boolean(detail);
  const remembered = userExpanded[index];
  const expanded =
    hasDetail &&
    (remembered !== undefined ? remembered : step.status === "active");
  const activeClass = step.status === "active" ? "is-active" : "";
  return `
    <div class="layer-card step-${step.status} ${activeClass} ${expanded ? "is-expanded" : ""}" data-step-index="${index}">
      <button type="button" class="layer-card-header" ${hasDetail ? `data-toggle-index="${index}"` : ""}>
        <div class="step-icon">${stepIconHtml(step.status)}</div>
        <div class="step-title-wrap">
          <p class="step-title">${step.title}</p>
          <p class="step-sub">${step.sub}</p>
        </div>
        ${hasDetail ? `<svg class="layer-card-chevron" viewBox="0 0 24 24" aria-hidden="true"><path fill-rule="evenodd" clip-rule="evenodd" d="M5.4 3h13.2A2.4 2.4 0 0 1 21 5.4v13.2a2.4 2.4 0 0 1-2.4 2.4H5.4A2.4 2.4 0 0 1 3 18.6V5.4A2.4 2.4 0 0 1 5.4 3Zm7.307 5.293a1 1 0 0 0-1.414 0l-4 4a1 1 0 1 0 1.414 1.414L12 10.414l3.293 3.293a1 1 0 0 0 1.414-1.414l-4-4Z" fill="currentColor"/></svg>` : ""}
      </button>
      ${
        hasDetail
          ? `<div class="layer-card-body-outer">
        <div class="layer-card-body-inner">
          <div class="layer-card-body">${detail}</div>
        </div>
      </div>`
          : ""
      }
    </div>
  `;
}

function stepsListHtml(steps) {
  // No outer "N of 3 layers" summary here -- per-layer progress (inside
  // each card, via substepChecklistHtml) is enough on its own. The overlay
  return `<div class="steps-list">${steps.map(layerCardHtml).join("")}</div>`;
}

const userExpanded = {};

function wireLayerCardToggles(scope) {
  scope.querySelectorAll("[data-toggle-index]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".layer-card");
      card.classList.toggle("is-expanded");
      userExpanded[btn.dataset.toggleIndex] =
        card.classList.contains("is-expanded");
    });
  });
}

function targetNamespace(target) {
  return (target && target.id) || "content";
}

function renderShell(fullScanMode, target) {
  const ns = targetNamespace(target);
  Object.keys(userExpanded).forEach((key) => delete userExpanded[key]);
  render(
    `${gaugeRowHtml(fullScanMode, ns)}<div class="note-slot"></div><div class="steps-wrap"><svg class="flow-overlay" aria-hidden="true"></svg><div class="steps-slot"></div></div>`,
    target,
  );
}

// Rebuilding the list on every poll restarts the spinner animation and
// collapses any card the user opened, so only rebuild when something changed.
function updateSteps(steps, target) {
  const slot = target.querySelector(".steps-slot");
  if (!slot) return;
  const html = stepsListHtml(steps);
  if (slot.dataset.renderedHtml === html) return;
  slot.dataset.renderedHtml = html;
  slot.innerHTML = html;
  wireLayerCardToggles(slot);
}

function updateNote(html, target) {
  const slot = target.querySelector(".note-slot");
  if (slot) slot.innerHTML = html;
}

function deriveStepOutcomes(result) {
  const layer2Attempted = (result.layers_used || []).includes("layer2");
  const layer2Failed =
    layer2Attempted && result.layer2_features && result.layer2_features.error;
  const layer2Succeeded = layer2Attempted && !layer2Failed;

  let layer2Status;
  let layer2Sub;
  let layer2ExtraDetail = "";
  if (layer2Succeeded) {
    layer2Status = "done";
    layer2Sub = "Page content reviewed";
    layer2ExtraDetail = embeddedUrlSummaryHtml(result.layer2_features);
  } else if (layer2Failed) {
    layer2Status = "unavailable";
    layer2Sub = "Could not load the page to review it";
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
    { status: layer2Status, sub: layer2Sub, extraDetail: layer2ExtraDetail },
    layer3Outcome(result),
  ];
}

const VISUAL_SUBSTEP_LABELS = [
  "Brand on the page (logo)",
  "Brand named in the address",
  "Home-page logos compared",
  "Alarming banner wording",
];
const VISUAL_REVEAL_MS = 700;

function layer3Substeps(layer3) {
  const logo = layer3.logo_check || {};
  let logoRow;
  if (logo.status === "checked") {
    logoRow = logo.identified_brand
      ? { status: "done", detail: `Logo matches ${logo.identified_brand}` }
      : { status: "done", detail: "Logo found, no known brand matched" };
  } else if (logo.status === "no_logo_provided") {
    logoRow = {
      status: "unavailable",
      detail: "No logo of usable size found on this page",
    };
  } else {
    logoRow = {
      status: "unavailable",
      detail: "Logo check not available on this machine",
    };
  }

  const hints = layer3.url_brand_hints || [];
  const addressRow = hints.length
    ? { status: "done", detail: `The address names ${hints[0].brand}` }
    : { status: "done", detail: "No brand named in the address" };

  const background = layer3.background;
  let homeRow;
  if (!background) {
    homeRow = { status: "skipped", detail: "Not needed for this page" };
  } else if (background.status === "checked") {
    homeRow = {
      status: "done",
      detail: `Home-page logos: ${BAND_LABELS[background.band] || background.band}`,
    };
  } else {
    homeRow = {
      status: "unavailable",
      detail: background.reason || "Could not compare the home pages",
    };
  }

  const wording = layer3.banner_wording_check || {};
  const wordingRow =
    wording.status === "checked"
      ? {
          status: "done",
          detail: (wording.matched_phrases || []).length
            ? "Alarming wording found (provisional check)"
            : "No alarming wording found (provisional check)",
        }
      : { status: "unavailable", detail: "Banner text not checked" };

  return [logoRow, addressRow, homeRow, wordingRow].map((row, i) => ({
    label: VISUAL_SUBSTEP_LABELS[i],
    ...row,
  }));
}

function visualSubstepsHtml(substeps) {
  const rows = substeps
    .map((step) => {
      const icon =
        step.status === "done"
          ? "&#10003;"
          : step.status === "skipped"
            ? "&#8211;"
            : step.status === "unavailable"
              ? "&#8230;"
              : "";
      const detail = step.detail
        ? `<p class="substep-detail">${escapeHtml(step.detail)}</p>`
        : "";
      return `
      <div class="substep-row ${step.status === "done" ? "is-done" : ""}">
        <span class="substep-icon">${icon}</span>
        <div class="substep-text">
          <span class="substep-label">${escapeHtml(step.label)}</span>
          ${detail}
        </div>
      </div>`;
    })
    .join("");
  return `${progressSummaryHtml(substeps)}<div class="substep-list">${rows}</div>`;
}

function layer3Outcome(result) {
  const layer3 = result.layer3_results;
  if (!layer3) {
    return {
      status: "unavailable",
      sub: "Planned for a later phase of this project",
    };
  }
  if (layer3.error) {
    return {
      status: "unavailable",
      sub: "Could not run the visual check on this machine",
    };
  }
  const substeps = layer3Substeps(layer3);
  return {
    status: "done",
    sub: "Four checks run, in order",
    substeps,
    detail: visualSubstepsHtml(substeps),
  };
}

function visualPendingStep(step) {
  const pending = (step.substeps || []).map((s) => ({
    label: s.label,
    status: "pending",
    detail: "",
  }));
  return {
    ...step,
    status: "active",
    sub: "Checking the visual signals...",
    detail: visualSubstepsHtml(pending),
    extraDetail: "",
  };
}

async function revealVisualSubsteps(shown, finalSteps, target) {
  const finalSubs = finalSteps[2].substeps || [];
  const revealed = finalSubs.map((s) => ({
    label: s.label,
    status: "pending",
    detail: "",
  }));
  const showCard = () => {
    shown[2] = {
      ...finalSteps[2],
      status: "active",
      sub: "Checking the visual signals...",
      detail: visualSubstepsHtml(revealed),
      extraDetail: "",
    };
    updateSteps(shown, target);
  };
  showCard();
  for (let i = 0; i < finalSubs.length; i++) {
    await new Promise((resolve) => setTimeout(resolve, VISUAL_REVEAL_MS));
    revealed[i] = finalSubs[i];
    showCard();
  }
  shown[2] = finalSteps[2];
  updateSteps(shown, target);
}

function stepsForStage(stage) {
  const steps = STEP_TITLES.map((title) => ({
    title,
    status: "pending",
    sub: "Waiting...",
  }));
  if (stage === STAGE_REVIEWING_CONTENT || stage === STAGE_DONE) {
    steps[0].status = "done";
    steps[0].sub = "Web address analyzed";
    steps[0].substepsDone = (LAYER_SUBSTEPS[0] || []).length;
  } else {
    steps[0].status = "active";
    steps[0].sub = "Checking the web address...";
  }
  if (stage === STAGE_REVIEWING_CONTENT) {
    steps[1].status = "active";
    steps[1].sub = "Reviewing page content...";
  }
  return steps;
}

function applyLiveProgress(progress, fullScanMode, target) {
  if (!progress) return;
  const ns = targetNamespace(target);
  updateSteps(stepsForStage(progress.stage), target);
  if (typeof progress.layer1_score === "number") {
    const s = statusForScore(progress.layer1_score);
    animateGauge(`${ns}-gauge-overall`, {
      value: progress.layer1_score * 100,
      statusKey: s.key,
      statusLabel: s.label,
    });
    if (fullScanMode) {
      animateGauge(`${ns}-gauge-layer1`, {
        value: progress.layer1_score * 100,
        statusKey: s.key,
        statusLabel: s.label,
      });
    }
  }
}

function finishWithResult(result, fullScanMode, target = content) {
  const outcomes = deriveStepOutcomes(result);
  const steps = STEP_TITLES.map((title, i) => ({
    title,
    status: outcomes[i].status,
    sub: outcomes[i].sub,
    substepsDone: (LAYER_SUBSTEPS[i] || []).length,
    extraDetail: outcomes[i].extraDetail,
    detail: outcomes[i].detail,
    substeps: outcomes[i].substeps,
  }));
  if (!target.querySelector(".gauge-row")) {
    renderShell(fullScanMode, target);
  }
  const sources = flowSources(result);
  const shown = steps.map((step, i) =>
    i === 2 && sources.includes(2)
      ? visualPendingStep(step)
      : sources.includes(i)
        ? {
            ...step,
            status: "active",
            sub: "Sending result to the web address check...",
            detail: "",
            extraDetail: "",
          }
        : step,
  );
  renderDoneKeepingSteps(shown, result, fullScanMode, target);
  if (sources.length) {
    playLayerFlows(sources, shown, steps, target).then(() => {
      if (sources.includes(2))
        return revealVisualSubsteps(shown, steps, target);
    });
  }
}

const FLOW_START_DELAY_MS = 500;
const FLOW_DURATION_MS = 1800;
const FLOW_GAP_MS = 2000;
const SVG_NS = "http://www.w3.org/2000/svg";

function flowSources(result) {
  const sources = [];
  if ((result.layers_used || []).includes("layer2")) sources.push(1);
  if (result.layer3_results) sources.push(2);
  return sources;
}

function stepCardOf(index, scope) {
  return scope.querySelector(`.layer-card[data-step-index="${index}"]`);
}

function drawFlowConnector(fromIndex, target) {
  const wrap = target.querySelector(".steps-wrap");
  const overlay = wrap && wrap.querySelector(".flow-overlay");
  const from = wrap && stepCardOf(fromIndex, wrap);
  const to = wrap && stepCardOf(0, wrap);
  if (!overlay || !from || !to) return null;

  const listRect = wrap.getBoundingClientRect();
  const f = from.getBoundingClientRect();
  const t = to.getBoundingClientRect();
  const gutterX = -10;
  const startY = f.top + f.height / 2 - listRect.top;
  const endY = t.top + t.height / 2 - listRect.top;
  const startX = f.left - listRect.left;
  const endX = t.left - listRect.left;

  overlay.setAttribute("viewBox", `0 0 ${listRect.width} ${listRect.height}`);
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute(
    "d",
    `M ${startX} ${startY} H ${gutterX} V ${endY} H ${endX}`,
  );
  path.setAttribute("class", "flow-line");
  overlay.appendChild(path);
  return { path };
}

function runFlow(fromIndex, delayMs, target, { onStart, onEnd }) {
  return new Promise((resolve) => {
    setTimeout(() => {
      const drawn = drawFlowConnector(fromIndex, target);
      if (!drawn) {
        onEnd();
        return resolve();
      }
      drawn.path.style.animationDuration = `${FLOW_DURATION_MS}ms`;
      onStart();
      setTimeout(() => {
        drawn.path.remove();
        onEnd();
        resolve();
      }, FLOW_DURATION_MS);
    }, delayMs);
  });
}

const LAYER_SOURCE_LABELS = { 1: "page content", 2: "visual comparison" };

async function playLayerFlows(sources, shown, finalSteps, target) {
  const ns = targetNamespace(target);
  for (let i = 0; i < sources.length; i++) {
    const src = sources[i];
    const delay = FLOW_START_DELAY_MS + (i === 0 ? 0 : FLOW_GAP_MS);
    await runFlow(src, delay, target, {
      onStart: () => {
        shown[0] = {
          ...finalSteps[0],
          status: "active",
          sub: `Receiving the ${LAYER_SOURCE_LABELS[src]} result...`,
          receiving: true,
          detail: "",
          extraDetail: "",
        };
        updateSteps(shown, target);
      },
      onEnd: () => {
        shown[0] = finalSteps[0];
        if (src !== 2) shown[src] = finalSteps[src];
        updateSteps(shown, target);
        pulseGauge(`${ns}-gauge-layer1`);
      },
    });
  }
  pulseGauge(`${ns}-gauge-overall`);
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

function escalateNoteHtml(result) {
  if (!result.would_escalate) return "";
  return `<div class="note-box">
     <span class="note-icon">i</span>
     <span>This page falls in a gray zone our deeper checks aren't built yet to resolve -- treat it with extra caution.</span>
   </div>`;
}

// --- Layer 3 (visual identity) display ---------------------------------
// Wording is fixed on purpose: levels say what was seen ("closely resembles",
// "may be imitating", "could not confirm") and never claim phishing.

const IDENTITY_LEVEL_KEYS = {
  matches: "good",
  "closely resembles": "warning",
  "may be imitating": "warning",
  "could not confirm": "neutral",
};

const BAND_LABELS = {
  strong: "Strong logo match",
  moderate: "Partial logo match",
  weak: "Weak logo match",
};

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function identityNoteHtml(layer3) {
  const note = layer3 && layer3.identity_note;
  if (!note) return "";
  const key = IDENTITY_LEVEL_KEYS[note.level] || "neutral";
  return `<div class="identity-box identity-${key}">
     <p class="identity-title">Visual identity check: ${escapeHtml(note.level)}</p>
     <p class="identity-text">${escapeHtml(note.text)}</p>
     <p class="identity-disclaimer">${escapeHtml(note.disclaimer)}</p>
   </div>`;
}

function noticeHtml(layer3) {
  const combination = layer3 && layer3.combination;
  if (!combination || !combination.notice) return "";
  const logoBrand = layer3.logo_check && layer3.logo_check.identified_brand;
  const hintBrand = (layer3.url_brand_hints || [])[0];
  const brand = logoBrand || (hintBrand && hintBrand.brand) || "a known brand";
  const disclaimer = layer3.identity_note
    ? layer3.identity_note.disclaimer
    : "";
  return `<div class="identity-box identity-notice">
     <p class="identity-title">Check this page further</p>
     <p class="identity-text">This page looks like ${escapeHtml(brand)}, but its address is not ${escapeHtml(brand)}'s. Open the page's sign-in or sign-up area with this extension for a deeper check.</p>
     <p class="identity-disclaimer">${escapeHtml(disclaimer)}</p>
   </div>`;
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

function renderDoneKeepingSteps(steps, result, fullScanMode, target = content) {
  const ns = targetNamespace(target);
  const meta = VERDICT_META[result.verdict] || {
    key: "neutral",
    icon: "?",
    badgeText: "UNKNOWN",
  };
  setBadge(meta.key, meta.icon, meta.badgeText);
  updateNote(
    escalateNoteHtml(result) +
      identityNoteHtml(result.layer3_results) +
      noticeHtml(result.layer3_results),
    target,
  );
  updateSteps(steps, target);
  animateResultGauges(result, fullScanMode, ns);
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

function renderInitialChecking(fullScanMode, target = content) {
  const steps = STEP_TITLES.map((title, i) => ({
    title,
    status: i === 0 ? "active" : "pending",
    sub: i === 0 ? "Checking the web address..." : "Waiting...",
  }));
  renderShell(fullScanMode, target);
  setBadge("loading", "&#8987;", "CHECKING");
  updateSteps(steps, target);
}

function handleResolvedStatus(status, payload, tabId, target = content) {
  const fullScanMode = scanMode === "full";
  if (status === "done") {
    finishWithResult(payload.result, fullScanMode, target);
  } else if (status === "offline") {
    renderOffline(target);
  } else if (status === "error") {
    renderError(payload.message, target);
  } else if (status === "analyzing" && tabId != null) {
    // A newer navigation superseded the request that just resolved (e.g.
    // multiple redirects on a login page) while it was in flight -- the
    // real analysis is still legitimately running, so keep polling instead
    // of showing "nothing to check" for a page that's actually being
    // analyzed right now.
    pollUntilDone(tabId, 0, target);
  } else {
    renderUnknown(target);
  }
}

// 90 attempts * 500ms = 45s -- must stay above the backend's own
// REQUEST_TIMEOUT_SECONDS (40s), or the popup gives up and shows a false
// "taking longer than expected" error for a page that's still legitimately
// working and might succeed a few seconds later.
const MAX_POLL_ATTEMPTS = 90;

function pollUntilDone(tabId, attempt = 0, target = content) {
  if (attempt > MAX_POLL_ATTEMPTS) {
    renderError("Taking longer than expected.");
    return;
  }
  setTimeout(() => {
    chrome.runtime.sendMessage({ type: "getTabResult", tabId }, (response) => {
      if (!response) return;
      if (response.status === "analyzing") {
        applyLiveProgress(response, scanMode === "full", target);
        pollUntilDone(tabId, attempt + 1, target);
      } else {
        handleResolvedStatus(response.status, response, tabId, target);
      }
    });
  }, 500);
}

function setScanModeUI(mode) {
  scanMode = mode;
  scanModeToggle.querySelectorAll(".scan-mode-option").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.mode === mode);
  });
  scanModeHint.textContent =
    mode === "full"
      ? "Runs every available layer for a more thorough (slower) check."
      : "Only runs deeper checks when the web address alone is inconclusive.";
}

function requestRescan(tab) {
  renderInitialChecking(scanMode === "full");

  chrome.runtime.sendMessage({
    type: "rescanTab",
    tabId: tab.id,
    url: tab.url,
  });
  pollUntilDone(tab.id);
}

scanModeToggle.addEventListener("click", (event) => {
  const btn = event.target.closest(".scan-mode-option");
  if (!btn || btn.classList.contains("is-active")) return;
  const mode = btn.dataset.mode;
  setScanModeUI(mode);
  chrome.storage.local.set({ scanMode: mode });
  if (currentTab) {
    requestRescan(currentTab);
  }
});

async function main() {
  const stored = await chrome.storage.local.get(["scanMode"]);
  setScanModeUI(stored.scanMode || "quick");

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

  currentTab = tab;
  setSubtitle(hostFromUrl(tab.url));
  renderInitialChecking(scanMode === "full");

  chrome.runtime.sendMessage(
    { type: "getTabResult", tabId: tab.id },
    (response) => {
      if (response && response.status === "analyzing") {
        pollUntilDone(tab.id);
        return;
      }

      if (!response || response.status === "unknown") {
        chrome.runtime.sendMessage({
          type: "analyzeTabNow",
          tabId: tab.id,
          url: tab.url,
        });
        pollUntilDone(tab.id);
        return;
      }

      if (response.modeUsed && response.modeUsed !== scanMode) {
        requestRescan(tab);
        return;
      }

      handleResolvedStatus(response.status, response, tab.id);
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
  const fullScanMode = scanMode === "full";
  renderInitialChecking(fullScanMode, manualResultEl);

  const requestId = crypto.randomUUID();
  let lastProgress = null;
  let polling = true;

  const pollLoop = () => {
    if (!polling) return;
    fetchAnalysisProgress(requestId).then((progress) => {
      if (!polling || !progress) return;
      lastProgress = progress;
      applyLiveProgress(progress, fullScanMode, manualResultEl);
    });
    setTimeout(pollLoop, 500);
  };
  pollLoop();

  checkUrlWithBackend(url, fullScanMode, requestId).then((outcome) => {
    polling = false;
    manualButton.disabled = false;

    let finalOutcome = outcome;
    if (
      outcome.status !== "done" &&
      lastProgress &&
      lastProgress.stage === STAGE_DONE &&
      lastProgress.result
    ) {
      finalOutcome = { status: "done", result: lastProgress.result };
    }

    if (finalOutcome.status === "done") {
      finishWithResult(finalOutcome.result, fullScanMode, manualResultEl);
    } else if (finalOutcome.status === "offline") {
      render(offlineStateHtml(), manualResultEl);
    } else {
      render(errorStateHtml(finalOutcome.message), manualResultEl);
    }
  });
});
