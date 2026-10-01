

JS_FIND_CANDIDATES = r"""
() => {
  const origin = location.origin;
  const HOME_PATH = /^\/([a-z]{2,3}([-_][a-zA-Z]{2,4})?)?\/?$|^\/(index|home)(\.\w+)?$/;
  const CONTEXT_BAD = /(payment|pay-?methods?|accepted|we-?accept|secure|ssl|badge|partner|sponsor|social|follow|app-?store|play-?store|trust|cards?-?logos?|footer)/i;
  const LOGO_WORD = /(logo|brand|masthead|site-?title|wordmark)/i;

 
  const parentOf = (el) => el.parentElement ||
    ((el.getRootNode && el.getRootNode() instanceof ShadowRoot) ? el.getRootNode().host : null);
  const closestAcross = (el, selector) => {
    for (let cur = el; cur; cur = parentOf(cur)) { if (cur.matches && cur.matches(selector)) return cur; }
    return null;
  };
  const collectAll = (root, acc) => {
    for (const el of root.querySelectorAll('*')) {
      acc.push(el);
      if (el.shadowRoot) collectAll(el.shadowRoot, acc);
    }
    return acc;
  };

  const isHomeHref = (href) => {
    if (!href) return false;
    try {
      const u = new URL(href, location.href);
      return u.origin === origin && !u.search && HOME_PATH.test(u.pathname);
    } catch (e) { return false; }
  };

  const attrText = (el) => {
    const parts = [el.getAttribute('alt'), el.getAttribute('class'), el.getAttribute('id'),
      el.getAttribute('src'), el.getAttribute('aria-label'), el.getAttribute('title'),
      el.getAttribute('data-testid'), el.getAttribute('href')];
    const t = el.querySelector && el.querySelector(':scope > title');
    if (t) parts.push(t.textContent);
    return parts.filter(Boolean).join(' ');
  };

  const ancestorText = (el, levels) => {
    let out = [], cur = parentOf(el);
    for (let i = 0; i < levels && cur; i++, cur = parentOf(cur)) {
      out.push((cur.getAttribute('class') || '') + ' ' + (cur.getAttribute('id') || ''));
    }
    return out.join(' ');
  };

  const CAND_SEL = 'img, svg, picture, [role="img"], [class*="logo" i], [id*="logo" i]';
  const els = collectAll(document, []).filter(e => e.matches && e.matches(CAND_SEL));
  const seen = new Set();
  const cands = [];
  for (const el of els) {
    if (seen.has(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
    if (r.width < 10 || r.height < 10 || r.width > 700 || r.height > 320) continue;
    if (r.bottom < 0 || r.top > 2500) continue;
  
    const tagLower = el.tagName.toLowerCase();
    const hasVisual = tagLower === 'img' || tagLower === 'svg' || tagLower === 'picture' ||
      cs.backgroundImage !== 'none' || el.querySelector('img, svg') || (el.shadowRoot && el.shadowRoot.querySelector('img, svg'));
    if (!hasVisual) continue;

    const anchor = closestAcross(el, 'a');
    const inHeader = !!closestAcross(el, 'header, [role="banner"], nav, [class*="header" i], [id*="header" i], [class*="masthead" i]');
    const inFooter = !!closestAcross(el, 'footer, [role="contentinfo"], [class*="footer" i], [id*="footer" i]');
    const linkedHome = anchor ? isHomeHref(anchor.getAttribute('href')) : false;
    const ownText = attrText(el) + ' ' + (anchor ? attrText(anchor) : '');
    const hasLogoWord = LOGO_WORD.test(ownText) || LOGO_WORD.test(ancestorText(el, 2));
    const badContext = CONTEXT_BAD.test(ancestorText(el, 4)) || CONTEXT_BAD.test(ownText.replace(/logo/ig, ''));
    const topY = r.top + window.scrollY;

    cands.push({ el, r, tag: el.tagName.toLowerCase(), inHeader, inFooter, linkedHome,
      hasLogoWord, badContext, topY, w: r.width, h: r.height,
      snippet: ownText.slice(0, 90) });
  }


  for (const c of cands) {
    c.rowSiblings = cands.filter(o => o !== c && Math.abs((o.r.top + o.r.height / 2) - (c.r.top + c.r.height / 2)) < 30
      && o.w > c.w * 0.5 && o.w < c.w * 2 && o.h > c.h * 0.5 && o.h < c.h * 2
      && !o.el.contains(c.el) && !c.el.contains(o.el)).length;
  }

  const out = cands.map(c => {
    let score = 0;
    if (c.inHeader) score += 3;
    if (c.linkedHome) score += 3;
    if (c.hasLogoWord) score += 2;
    if (c.topY < 220) score += 2; else if (c.topY < 500) score += 1;
    if (c.inFooter) score -= 4;
    if (c.badContext) score -= 3;
    if (c.rowSiblings >= 3) score -= 3;      
    if (c.w > 500 || c.h > 220) score -= 1;  
    if (c.topY > 600) score -= 3;           
    if (c.w < 24 && c.h < 24) score -= 2;   
    return { tag: c.tag, x: c.r.left, y: c.r.top, w: c.w, h: c.h, score,
      signals: { inHeader: c.inHeader, linkedHome: c.linkedHome, hasLogoWord: c.hasLogoWord,
        inFooter: c.inFooter, badContext: c.badContext, rowSiblings: c.rowSiblings },
      snippet: c.snippet };
  });
  out.sort((a, b) => b.score - a.score);
  return out;
}
"""


def find_logo_candidates(page, top_n=5, min_score=1):
    cands = page.evaluate(JS_FIND_CANDIDATES)
    return [c for c in cands if c["score"] >= min_score][:top_n]


def crop_candidate(page, cand, out_path, viewport_height=800, pad=2):
    x, y, w, h = cand["x"], cand["y"], cand["w"], cand["h"]
    if x < 0 or y < 0 or y + h > viewport_height:
        return False
    page.screenshot(path=out_path, clip={
        "x": max(0, x - pad), "y": max(0, y - pad),
        "width": w + 2 * pad, "height": h + 2 * pad,
    })
    return True
