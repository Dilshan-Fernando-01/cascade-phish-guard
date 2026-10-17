function findLogoCandidatesInPage() {
  const LOGO_SEARCH_TOP_PX = 300;
  const LOGO_MIN_PX = 24;
  const LOGO_MIN_DIMENSION_PX = 10;
  const LOGO_MIN_AREA_PX = LOGO_MIN_PX * LOGO_MIN_PX;
  const LOGO_MAX_W_PX = 480;
  const LOGO_MAX_H_PX = 160;
  const LOGO_WORD = /(logo|brand|site-?title|wordmark)/i;
  const inputs = Array.from(
    document.querySelectorAll("input, textarea, select"),
  ).map((el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
  });
  const overlapsInput = (r) =>
    inputs.some(
      (i) =>
        r.left < i.right &&
        r.right > i.left &&
        r.top < i.bottom &&
        r.bottom > i.top,
    );

  const LOGO_SELECTOR =
    'img, svg, picture, [role="img"], [class*="logo" i], [id*="logo" i]';
  const collectLogoElements = (root, out) => {
    out.push(...root.querySelectorAll(LOGO_SELECTOR));
    for (const host of root.querySelectorAll("*")) {
      if (host.shadowRoot) collectLogoElements(host.shadowRoot, out);
    }
    return out;
  };
  const els = collectLogoElements(document, []);
  const candidates = [];
  let considered = 0;
  for (const el of els) {
    considered += 1;
    const r = el.getBoundingClientRect();

    if (r.width < LOGO_MIN_DIMENSION_PX || r.height < LOGO_MIN_DIMENSION_PX)
      continue;
    if (r.width * r.height < LOGO_MIN_AREA_PX) continue;
    if (r.width > LOGO_MAX_W_PX || r.height > LOGO_MAX_H_PX) continue;
    if (r.bottom < 0 || r.top > LOGO_SEARCH_TOP_PX) continue;
    if (r.right < 0 || r.left > window.innerWidth) continue;
    const style = getComputedStyle(el);
    const hasBackgroundImage =
      style.backgroundImage && style.backgroundImage !== "none";
    const isImage =
      el.matches("img, svg, picture, [role='img']") || hasBackgroundImage;
    if (!isImage && el.textContent.trim().length > 0) continue;
    if (style.display === "none" || style.visibility === "hidden") continue;
    if (overlapsInput(r)) continue;

    let score = 0;
    if (el.closest("header, [role='banner'], nav")) score += 3;
    const anchor = el.closest("a");

    let isHomeLink = false;
    if (anchor) {
      try {
        const target = new URL(
          anchor.getAttribute("href") || "",
          location.href,
        );
        if (
          target.origin === location.origin &&
          (target.pathname === "/" || target.pathname === "")
        ) {
          isHomeLink = true;
          score += 6;
        }
      } catch (e) {
        // ignore malformed links
      }
    }
    const label = `${el.getAttribute("alt") || ""} ${el.getAttribute("class") || ""} ${el.getAttribute("id") || ""}`;
    const labelled = LOGO_WORD.test(label);
    if (labelled) score += 2;
    if (r.top < 220) score += 2;
    if (el.closest("footer, [role='contentinfo']")) score -= 4;

    const hasAltText = (el.getAttribute("alt") || "").trim().length > 0;

    if (
      !labelled &&
      !hasAltText &&
      !isHomeLink &&
      (r.width < 40 || r.height < 40)
    )
      score -= 3;

    candidates.push({
      score,
      area: r.width * r.height,
      x: r.left,
      y: r.top,
      w: r.width,
      h: r.height,
    });
  }

  candidates.sort((a, b) => b.score - a.score || b.area - a.area);
  return {
    best: candidates.length && candidates[0].score >= 2 ? candidates[0] : null,
    devicePixelRatio: window.devicePixelRatio || 1,
    considered,
    kept: candidates.length,
    topScore: candidates.length ? candidates[0].score : null,
  };
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",")[1] : null);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function cropLogoFromScreenshot(dataUrl, box, dpr) {
  const blob = await (await fetch(dataUrl)).blob();
  const bitmap = await createImageBitmap(blob);
  const sx = Math.max(0, Math.floor(box.x * dpr));
  const sy = Math.max(0, Math.floor(box.y * dpr));
  const sw = Math.min(bitmap.width - sx, Math.ceil(box.w * dpr));
  const sh = Math.min(bitmap.height - sy, Math.ceil(box.h * dpr));
  if (sw <= 0 || sh <= 0) return null;
  const canvas = new OffscreenCanvas(sw, sh);
  canvas.getContext("2d").drawImage(bitmap, sx, sy, sw, sh, 0, 0, sw, sh);
  const cropped = await canvas.convertToBlob({ type: "image/png" });
  return blobToBase64(cropped);
}

const PREVIEW_MAX_WIDTH = 480;

async function downscaleForPreview(dataUrl, maxWidth) {
  const blob = await (await fetch(dataUrl)).blob();
  const bitmap = await createImageBitmap(blob);
  const scale = Math.min(1, maxWidth / bitmap.width);
  const w = Math.max(1, Math.round(bitmap.width * scale));
  const h = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = new OffscreenCanvas(w, h);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, w, h);
  const thumb = await canvas.convertToBlob({
    type: "image/jpeg",
    quality: 0.6,
  });
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(thumb);
  });
}

const BANNER_BAND_PX = 300;

function findIframePositions() {
  const out = [];
  document.querySelectorAll("iframe").forEach((el) => {
    const r = el.getBoundingClientRect();
    let src = null;
    try {
      src = new URL(el.getAttribute("src") || "", location.href).href;
    } catch (e) {
      src = null;
    }
    out.push({ src, x: r.left, y: r.top });
  });
  return out;
}

function findBestLogoInPage(tabId) {
  return Promise.all([
    chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      func: findLogoCandidatesInPage,
    }),
    chrome.scripting
      .executeScript({
        target: { tabId, frameIds: [0] },
        func: findIframePositions,
      })
      .then((r) => (r && r[0] ? r[0].result : []))
      .catch(() => []),
    chrome.webNavigation.getAllFrames({ tabId }).catch(() => []),
  ]).then(([frameResults, iframePositions, allFrames]) => {
    const frameUrlById = new Map(
      (allFrames || []).map((f) => [f.frameId, f.url]),
    );

    let best = null;
    for (const entry of frameResults || []) {
      const result = entry && entry.result;
      if (!result || !result.best) continue;
      let candidate = result.best;
      if (entry.frameId !== 0) {
        const frameUrl = frameUrlById.get(entry.frameId);
        const host = (iframePositions || []).find((f) => f.src === frameUrl);
        if (!host) continue;
        candidate = {
          ...candidate,
          x: candidate.x + host.x,
          y: candidate.y + host.y,
        };
      }
      if (
        !best ||
        candidate.score > best.score ||
        (candidate.score === best.score && candidate.area > best.area)
      ) {
        best = { ...candidate, devicePixelRatio: result.devicePixelRatio };
      }
    }
    return best;
  });
}

const LOGO_RETRY_DELAY_MS = 900;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function captureLayer3Images(tabId) {
  return findBestLogoInPage(tabId)
    .catch(() => null)
    .then(async (best) => {
      if (!best) {
        await sleep(LOGO_RETRY_DELAY_MS);
        best = await findBestLogoInPage(tabId).catch(() => null);
      }
      if (!best) {
        console.log("Cascade Phish Guard logo: no logo found in any frame");
      }
      const tab = await chrome.tabs.get(tabId);
      const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
        format: "png",
      });
      const dpr = best ? best.devicePixelRatio : 1;
      const bannerPng = await cropLogoFromScreenshot(
        dataUrl,
        { x: 0, y: 0, w: 100000, h: BANNER_BAND_PX },
        dpr,
      );
      const logoPng = best
        ? await cropLogoFromScreenshot(dataUrl, best, dpr)
        : null;
      const previewDataUrl = await downscaleForPreview(
        dataUrl,
        PREVIEW_MAX_WIDTH,
      ).catch(() => null);
      return { logoPng, bannerPng, previewDataUrl };
    })
    .catch((err) => {
      console.warn("Cascade Phish Guard layer 3 capture failed", String(err));
      return { logoPng: null, bannerPng: null, previewDataUrl: null };
    });
}
