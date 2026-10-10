const LOW_THRESHOLD = 0.2;
const HIGH_THRESHOLD = 0.8;

const STAGE_CHECKING_ADDRESS = "checking_address";
const STAGE_REVIEWING_CONTENT = "reviewing_content";
const STAGE_COMPARING_VISUAL_IDENTITY = "comparing_visual_identity";
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

const ICON_CHECK =
  '<svg class="icon-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21ZM11.7682 15.6402L16.7682 9.64018L15.2318 8.35982L10.9328 13.5186L8.70711 11.2929L7.29289 12.7071L10.2929 15.7071L11.0672 16.4814L11.7682 15.6402Z" fill="currentColor"/></svg>';

const ICON_CHECK_MARK =
  '<svg class="icon-svg" viewBox="6.8 7.2 10.4 10.4" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11.7682 15.6402L16.7682 9.64018L15.2318 8.35982L10.9328 13.5186L8.70711 11.2929L7.29289 12.7071L10.2929 15.7071L11.0672 16.4814L11.7682 15.6402Z" fill="currentColor"/></svg>';
const ICON_FAIL =
  '<svg class="icon-svg" viewBox="0 -8 528 528" xmlns="http://www.w3.org/2000/svg" fill="currentColor"><path d="M264 456Q210 456 164 429 118 402 91 356 64 310 64 256 64 202 91 156 118 110 164 83 210 56 264 56 318 56 364 83 410 110 437 156 464 202 464 256 464 310 437 356 410 402 364 429 318 456 264 456ZM264 288L328 352 360 320 296 256 360 192 328 160 264 224 200 160 168 192 232 256 168 320 200 352 264 288Z"/></svg>';
const ICON_SKIP =
  '<svg class="icon-svg" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="currentColor"><path d="M17.28 7.78a.75.75 0 00-1.06-1.06l-9.5 9.5a.75.75 0 101.06 1.06l9.5-9.5z"/><path fill-rule="evenodd" d="M12 1C5.925 1 1 5.925 1 12s4.925 11 11 11 11-4.925 11-11S18.075 1 12 1zM2.5 12a9.5 9.5 0 1119 0 9.5 9.5 0 01-19 0z"/></svg>';
const ICON_INFO =
  '<svg class="icon-svg" viewBox="0 0 48.296 48.257" xmlns="http://www.w3.org/2000/svg" fill="currentColor"><path d="M24.149,0C10.812,0,0,10.8,0,24.125c0,13.326,10.812,24.132,24.149,24.132c13.334,0,24.147-10.807,24.147-24.132 C48.296,10.8,37.483,0,24.149,0z M26.171,35.919c0,1.115-0.907,2.021-2.022,2.021c-1.12,0-2.025-0.908-2.025-2.021V22.507 c0-1.114,0.905-2.022,2.025-2.022c1.115,0,2.022,0.908,2.022,2.022V35.919z M26.171,15.101c0,1.119-0.907,2.022-2.022,2.022 c-1.12,0-2.025-0.903-2.025-2.022v-0.633c0-1.119,0.905-2.022,2.025-2.022c1.115,0,2.022,0.903,2.022,2.022V15.101z"/></svg>';
const ICON_SPINNER = '<span class="badge-spinner"></span>';
const ICON_CHEVRON =
  '<svg class="layer-card-chevron" viewBox="0 0 24 24" aria-hidden="true"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 3a9 9 0 100 18 9 9 0 000-18ZM12.707 8.293a1 1 0 0 0-1.414 0l-4 4a1 1 0 1 0 1.414 1.414L12 10.414l3.293 3.293a1 1 0 0 0 1.414-1.414l-4-4Z" fill="currentColor"/></svg>';

const badge = document.getElementById("badge");
const subtitleEl = document.getElementById("subtitle");
const content = document.getElementById("content");
const scanModeToggle = document.getElementById("scan-mode-toggle");
const scanModeHint = document.getElementById("scan-mode-hint");
const devModeToggle = document.getElementById("dev-mode-toggle");

let scanMode = "quick";
let devMode = false;
let currentTab = null;

let lastResult = null;
let lastFullScanMode = false;
let lastCapturedLogoPng = null;

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
          ${gaugeHtml({ id: `${ns}-gauge-layer3`, size: 72, strokeWidth: 8, big: false })}
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

  const layer3Score = result.layer_scores && result.layer_scores.layer3;
  if (typeof layer3Score === "number") {
    const s = statusForScore(layer3Score);
    animateGauge(`${ns}-gauge-layer3`, {
      value: layer3Score * 100,
      statusKey: s.key,
      statusLabel: s.label,
    });
  } else {
    animateGauge(`${ns}-gauge-layer3`, {
      value: 0,
      statusKey: "neutral",
      statusLabel: "N/A",
    });
  }
}

function stepIconHtml(status) {
  if (status === "active") return `<div class="step-spinner"></div>`;
  if (status === "done") return ICON_CHECK_MARK;
  if (status === "skipped") return ICON_SKIP;
  if (status === "unavailable") return ICON_FAIL;
  return "";
}

function progressSummaryHtml(steps) {
  const resolved = steps.filter((s) =>
    ["done", "skipped", "unavailable"].includes(s.status),
  ).length;
  const pct = Math.round((resolved / steps.length) * 100);
  const allDone = resolved === steps.length;
  return `
    <div class="progress-summary">
      <div class="progress-summary-icon ${allDone ? "is-done" : ""}">${allDone ? ICON_CHECK_MARK : ""}</div>
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
        <span class="substep-icon">${i < doneCount ? ICON_CHECK_MARK : ""}</span>
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
    line = `Checked ${checked} embedded ${linkWord} on this page - none looked suspicious.`;
  } else {
    const maxRisk = Math.round((features.max_embedded_url_risk || 0) * 100);
    const flagWord = suspicious === 1 ? "link" : "links";
    line = `Checked ${checked} embedded ${linkWord} on this page - ${suspicious} ${flagWord} looked suspicious (highest risk: ${maxRisk}%).`;
  }
  return `<div class="embedded-url-summary">${line}</div>`;
}

function layerCardHtml(step, index) {
  const substeps = LAYER_SUBSTEPS[index] || [];

  const showSubsteps =
    !step.receiving &&
    substeps.length > 0 &&
    (step.status === "active" || step.status === "done");
  const defaultSubstepsDone = step.status === "done" ? substeps.length : 0;
  const detail = showSubsteps
    ? substepChecklistHtml(index, step.substepsDone ?? defaultSubstepsDone) +
      (step.extraDetail || "")
    : step.detail;
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
        ${hasDetail ? ICON_CHEVRON : ""}
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
    `${gaugeRowHtml(fullScanMode, ns)}<div class="note-slot"></div><div class="steps-wrap"><div class="steps-slot"></div></div><div class="quality-slot"></div>`,
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
  if (!slot || slot.dataset.renderedHtml === html) return;
  slot.dataset.renderedHtml = html;
  slot.innerHTML = html;
}

function updateQuality(html, target) {
  const slot = target.querySelector(".quality-slot");
  if (!slot || slot.dataset.renderedHtml === html) return;
  slot.dataset.renderedHtml = html;
  slot.innerHTML = html;
  if (html) wireQualityToggle(slot);
}

const QUALITY_BAND_META = {
  good: { label: "Good", key: "good" },
  fair: { label: "Fair", key: "fair" },
  poor: { label: "Poor", key: "poor" },
};

function pageQualityHtml(pageQuality) {
  if (!pageQuality) return "";
  const meta = QUALITY_BAND_META[pageQuality.band] || { label: pageQuality.band, key: "neutral" };
  const findings = pageQuality.findings
    .map((f) => `<li>${escapeHtml(f.label)}</li>`)
    .join("");
  const findingsBlock = pageQuality.findings.length
    ? `<ul class="quality-findings-list">${findings}</ul>`
    : `<p class="quality-all-clear">No issues found in these checks.</p>`;
  return `<div class="quality-box">
    <button type="button" class="quality-header" id="quality-toggle" aria-expanded="false">
      <span class="quality-title">Page quality - things to consider</span>
      <span class="quality-badge quality-badge-${meta.key}">${meta.label} (${pageQuality.score}/100)</span>
      <span class="quality-chevron">${ICON_CHEVRON}</span>
    </button>
    <div class="quality-detail" id="quality-detail" hidden>
      ${findingsBlock}
      <p class="quality-disclaimer">${escapeHtml(pageQuality.disclaimer)}</p>
    </div>
  </div>`;
}

function wireQualityToggle(slot) {
  const toggle = slot.querySelector("#quality-toggle");
  const detail = slot.querySelector("#quality-detail");
  if (!toggle || !detail) return;
  toggle.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!expanded));
    detail.hidden = expanded;
    slot.classList.toggle("quality-open", !expanded);
  });
}

function reasonsHtml(reasons) {
  if (!reasons || reasons.length === 0) return "";
  const items = reasons.map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  return `<div class="reasons"><p class="reasons-title">Why</p><ul class="reasons-list">${items}</ul></div>`;
}

function devScoreFirst(result, layerKey, features) {
  if (!features) return features;
  const score = (result.layer_scores || {})[layerKey];
  if (typeof score !== "number") return features;
  return { score: `${(score * 100).toFixed(1)}%`, ...features };
}

function devDetailsHtml(title, data, { asJson = false } = {}) {
  if (!data || (typeof data === "object" && Object.keys(data).length === 0))
    return "";
  if (!devMode) return "";
  if (asJson) {
    return `<div class="dev-details">
      <p class="dev-details-title">${escapeHtml(title)}</p>
      <pre class="dev-details-json">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </div>`;
  }
  const rows = Object.entries(data)
    .map(
      ([key, value]) =>
        `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(String(value))}</dd>`,
    )
    .join("");
  return `<div class="dev-details">
    <p class="dev-details-title">${escapeHtml(title)}</p>
    <dl class="dev-details-grid">${rows}</dl>
  </div>`;
}

function devLogoCaptureHtml(capturedLogoPng) {
  if (!devMode || !capturedLogoPng) return "";
  return `<div class="dev-details">
    <p class="dev-details-title">Captured logo crop (dev mode only - checks capture quality, never sent to the report)</p>
    <img class="dev-logo-capture" src="data:image/png;base64,${capturedLogoPng}" alt="Captured logo crop" />
  </div>`;
}

function deriveStepOutcomes(result, fullScanMode, capturedLogoPng) {
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
    layer2Sub = "Skipped - the web address check alone was conclusive";
  }
  const reasons = result.reasons || {};
  return [
    {
      status: "done",
      sub: "Web address analyzed",
      extraDetail:
        reasonsHtml(reasons.layer1) +
        devDetailsHtml(
          "Layer 1 captured (score decided from these)",
          devScoreFirst(result, "layer1", result.layer1_features),
        ),
    },
    {
      status: layer2Status,
      sub: layer2Sub,
      extraDetail:
        layer2ExtraDetail +
        reasonsHtml(reasons.layer2) +
        devDetailsHtml(
          "Layer 2 captured (score decided from these)",
          devScoreFirst(result, "layer2", result.layer2_features),
        ),
    },
    layer3Outcome(result, fullScanMode, capturedLogoPng),
  ];
}

const VISUAL_SUBSTEP_LABELS = [
  "Brand on the page (logo)",
  "Brand named in the address",
  "Home-page logos compared",
  "Home-page layout compared",
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
  let layoutRow;
  if (!background) {
    homeRow = { status: "skipped", detail: "Not needed for this page" };
    layoutRow = { status: "skipped", detail: "Not needed for this page" };
  } else if (background.status === "checked") {
    homeRow = background.band
      ? {
          status: "done",
          detail: `Home-page logos: ${BAND_LABELS[background.band] || background.band}`,
        }
      : {
          status: "unavailable",
          detail: "No logo found to compare on one of the home pages",
        };

    const region = background.region || {};
    layoutRow =
      region.status === "checked"
        ? {
            status: "done",
            detail: region.both_match
              ? "Home-page layout matches"
              : "Home-page layout does not match",
          }
        : {
            status: "unavailable",
            detail: "Not enough detail on the page to compare layout",
          };
  } else {
    homeRow = {
      status: "unavailable",
      detail: background.reason || "Could not compare the home pages",
    };
    layoutRow = {
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

  return [logoRow, addressRow, homeRow, layoutRow, wordingRow].map(
    (row, i) => ({
      label: VISUAL_SUBSTEP_LABELS[i],
      ...row,
    }),
  );
}

function visualSubstepsHtml(substeps) {
  const rows = substeps
    .map((step) => {
      const icon =
        step.status === "done"
          ? ICON_CHECK_MARK
          : step.status === "skipped"
            ? ICON_SKIP
            : step.status === "unavailable"
              ? ICON_FAIL
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

function layer3Outcome(result, fullScanMode, capturedLogoPng) {
  const layer3 = result.layer3_results;
  if (!layer3) {
    if (!fullScanMode) {
      return { status: "skipped", sub: "Only runs on a Full scan" };
    }

    return {
      status: "unavailable",
      sub: "Not available for a pasted address - open the page in a tab for this check",
    };
  }
  if (layer3.error) {
    return {
      status: "unavailable",
      sub: "Could not run the visual check on this machine",
    };
  }

  const substeps = layer3Substeps(layer3).map((row) =>
    result.verdict === "safe" ? { ...row, detail: "" } : row,
  );
  return {
    status: "done",
    sub: "Four checks run, in order",
    substeps,
    detail:
      visualSubstepsHtml(substeps) +
      reasonsHtml((result.reasons || {}).layer3) +
      devLogoCaptureHtml(capturedLogoPng) +
      devDetailsHtml(
        "Layer 3 full detail (score decided from this)",
        devScoreFirst(result, "layer3", layer3),
        { asJson: true },
      ),
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
  if (
    stage === STAGE_REVIEWING_CONTENT ||
    stage === STAGE_COMPARING_VISUAL_IDENTITY ||
    stage === STAGE_DONE
  ) {
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
  if (stage === STAGE_COMPARING_VISUAL_IDENTITY) {
    steps[1].status = "done";
    steps[1].sub = "Page content reviewed";
    steps[1].substepsDone = (LAYER_SUBSTEPS[1] || []).length;
    steps[2].status = "active";
    steps[2].sub = "Comparing visual identity...";
  }
  return steps;
}

function scanningPreviewHtml(previewDataUrl) {
  if (!previewDataUrl) return "";
  return `<div class="scan-preview-box">
    <img class="scan-preview-img" src="${previewDataUrl}" alt="" />
    <div class="scan-preview-overlay">
      <span class="scan-preview-dot"></span>
      <span>Comparing visual identity&hellip;</span>
    </div>
  </div>`;
}

function applyLiveProgress(progress, fullScanMode, target) {
  if (!progress) return;
  const ns = targetNamespace(target);
  updateSteps(stepsForStage(progress.stage), target);
  if (fullScanMode) {
    updateNote(
      progress.stage === STAGE_COMPARING_VISUAL_IDENTITY
        ? scanningPreviewHtml(progress.previewDataUrl)
        : "",
      target,
    );
  }
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

  if (fullScanMode && typeof progress.layer2_score === "number") {
    const s2 = statusForScore(progress.layer2_score);
    animateGauge(`${ns}-gauge-layer2`, {
      value: progress.layer2_score * 100,
      statusKey: s2.key,
      statusLabel: s2.label,
    });
    animateGauge(`${ns}-gauge-overall`, {
      value: progress.layer2_score * 100,
      statusKey: s2.key,
      statusLabel: s2.label,
    });
  }
}

function finishWithResult(
  result,
  fullScanMode,
  target = content,
  capturedLogoPng = null,
) {
  if (target === content) {
    lastResult = result;
    lastFullScanMode = fullScanMode;
    lastCapturedLogoPng = capturedLogoPng;
  }
  const outcomes = deriveStepOutcomes(result, fullScanMode, capturedLogoPng);
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

function flowSources(result) {
  const sources = [];
  if ((result.layers_used || []).includes("layer2")) sources.push(1);
  if (result.layer3_results) sources.push(2);
  return sources;
}

function runFlow(fromIndex, delayMs, target, { onStart, onEnd }) {
  return new Promise((resolve) => {
    setTimeout(() => {
      onStart();
      setTimeout(() => {
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

const VERDICT_META = {
  safe: {
    key: "safe",
    label: "Looks safe",
    badgeText: "SAFE",
    icon: ICON_CHECK,
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
     <span class="note-icon">${ICON_INFO}</span>
     <span>This page falls in a gray zone our deeper checks aren't built yet to resolve - treat it with extra caution.</span>
   </div>`;
}

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

// Under the verdict: the main reasons behind a suspicious or phishing result,
// taken from each layer (first two per layer). Never shown for a safe result.
function verdictReasonsHtml(result) {
  if (!result || result.verdict === "safe") return "";
  const reasons = result.reasons || {};
  const lines = [];
  [
    ["layer1", "Web address"],
    ["layer2", "Page content"],
    ["layer3", "Visual"],
  ].forEach(([key, label]) => {
    (reasons[key] || [])
      .slice(0, 2)
      .forEach((text) => lines.push(`${label}: ${text}`));
  });
  if (lines.length === 0) {
    return `<div class="note-box"><span class="note-icon">${ICON_INFO}</span><span>No specific signal was recorded for this result. The score comes from the combined model.</span></div>`;
  }
  const items = lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("");
  return `<div class="note-box verdict-reasons"><span class="note-icon">${ICON_INFO}</span><div><p class="reasons-title">What led to this result</p><ul class="reasons-list">${items}</ul></div></div>`;
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
    verdictReasonsHtml(result) +
      escalateNoteHtml(result) +
      identityNoteHtml(result.layer3_results) +
      noticeHtml(result.layer3_results),
    target,
  );
  updateSteps(steps, target);
  updateQuality(pageQualityHtml(result.page_quality), target);
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
  setBadge("loading", ICON_SPINNER, "CHECKING");
  updateSteps(steps, target);
}

function handleResolvedStatus(status, payload, tabId, target = content) {
  const fullScanMode = scanMode === "full";
  if (status === "done") {
    finishWithResult(
      payload.result,
      fullScanMode,
      target,
      payload.capturedLogoPng,
    );
  } else if (status === "offline") {
    renderOffline(target);
  } else if (status === "error") {
    renderError(payload.message, target);
  } else if (status === "analyzing" && tabId != null) {
    pollUntilDone(tabId, 0, target);
  } else {
    renderUnknown(target);
  }
}

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

const sidePanelButton = document.getElementById("side-panel-button");
sidePanelButton.addEventListener("click", async () => {
  if (!chrome.sidePanel) return; // older Chrome without side panel support
  const win = await chrome.windows.getCurrent();
  chrome.sidePanel.open({ windowId: win.id });
});

devModeToggle.addEventListener("change", () => {
  devMode = devModeToggle.checked;
  chrome.storage.local.set({ devMode });
  if (lastResult) {
    finishWithResult(
      lastResult,
      lastFullScanMode,
      content,
      lastCapturedLogoPng,
    );
  }
});

async function loadActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (
    !tab ||
    !tab.url ||
    !(tab.url.startsWith("http://") || tab.url.startsWith("https://"))
  ) {
    currentTab = null;
    setSubtitle("");
    renderUnknown();
    return;
  }

  if (currentTab && currentTab.id === tab.id && currentTab.url === tab.url) {
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

async function main() {
  const stored = await chrome.storage.local.get(["scanMode", "devMode"]);
  setScanModeUI(stored.scanMode || "quick");
  devMode = Boolean(stored.devMode);
  devModeToggle.checked = devMode;

  await loadActiveTab();

  // A popup is short-lived (closes on blur) so these never fire in that
  // context. A side panel stays open across tab switches, so without this it
  // would keep showing whichever tab was active when it was first opened -
  // these keep it following the tab the user is actually looking at.
  chrome.tabs.onActivated.addListener(() => loadActiveTab());
  chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.status === "complete" && tabId === currentTab?.id) {
      loadActiveTab();
    }
  });
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
