const LOGO_SEARCH_TOP_PX = 300;
const LOGO_MIN_PX = 24;
const LOGO_MAX_W_PX = 400;
const LOGO_MAX_H_PX = 160;

function findLogoCandidatesInPage() {
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

  const els = Array.from(
    document.querySelectorAll(
      'img, svg, picture, [role="img"], [class*="logo" i], [id*="logo" i]',
    ),
  );
  const candidates = [];
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width < LOGO_MIN_PX || r.height < LOGO_MIN_PX) continue;
    if (r.width > LOGO_MAX_W_PX || r.height > LOGO_MAX_H_PX) continue;
    if (r.bottom < 0 || r.top > LOGO_SEARCH_TOP_PX) continue;
    if (r.right < 0 || r.left > window.innerWidth) continue;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") continue;
    if (overlapsInput(r)) continue;

    let score = 0;
    if (el.closest("header, [role='banner'], nav")) score += 3;
    const anchor = el.closest("a");
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
          score += 3;
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
    if (!labelled && (r.width < 40 || r.height < 40)) score -= 3;

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

// Returns base64 PNG of the logo, or null when no confident logo is found or
// the tab can't be captured (for example, a restricted page).
function captureLogoPng(tabId) {
  return chrome.scripting
    .executeScript({
      target: { tabId, frameIds: [0] },
      func: findLogoCandidatesInPage,
    })
    .then(async (results) => {
      const found = results && results[0] ? results[0].result : null;
      if (!found || !found.best) return null;
      const tab = await chrome.tabs.get(tabId);
      const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {
        format: "png",
      });
      return cropLogoFromScreenshot(
        dataUrl,
        found.best,
        found.devicePixelRatio,
      );
    })
    .catch(() => null);
}
