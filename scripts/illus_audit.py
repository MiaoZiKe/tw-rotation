"""精選文章插圖第 2 版（"style": 2）的機器量測 —— 規格 docs/articles/illus_style.md 第 4.2 節。

Andy 2026-10-17：「自動產精選文章，之後的圖需要再更細緻，顏色不要太單一……」
→ 每張 style:2 插圖交件前跑這支，輸出 illus_audit.json（深色、淺色各一份），門檻照規格 4.2 節；
  驗收段落 scripts/uitest_sections/20261017_illus_v2.py 也是呼叫這裡的 measure()／judge()。

用法（文章 JSON 只從本機路徑讀、經瀏覽器攔截餵進頁面，不會寫進 site/）：
    python scripts/illus_audit.py --post <文章或單一 illus 區塊的 json> --out <輸出 json> [--shots <截圖資料夾>]

量什麼（全部是畫面上或渲染器正規化後的實際值，不是讀設定）：
  · 色彩：只截 svg.ilsvg（藏掉引線與浮水印），去掉卡片底色後逐像素轉 OKLCH；
    C ≥ 0.03 算有彩度，色相 30° 一組。hue_* 與 warm／cool 是「占有彩度面積」的比例，neutral_pct 是「占整張插圖面積」的比例。
  · 結構：讀 TwArtIllus.spec2()（白名單＋夾值之後真正拿去畫的積木）：mat 數、零件數、同 mat 當不同零件、相鄰色差、不可相鄰清單、空白方塊。
    「同 mat 當不同零件」只算本體（box／cyl／hcyl／wheel／shell）；錫球、凸塊、銅柱、管線本來就是同一種材料（錫就是錫），不算。
  · 尺寸：390 寬時每顆球（balls）的螢幕半徑、每一層（layers）的螢幕高度；構圖填滿＝所有零件實際外框占 viewBox 的比例。
  · 重疊：說明兩兩、編號兩兩、說明壓到圖、引線互相交叉、引線穿過別人的說明或編號 —— 1440 與 390 都量。
    引線經過別的零件上方（指向內層零件時一定會經過外層）另外列 leader_over_parts，只報數、不擋。
  · 不螢光：發光濾鏡、模糊、CSS filter／drop-shadow 的數量；所有填色與漸層色的最大 OKLCH 彩度。
"""
from __future__ import annotations

import argparse
import json
import math
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# 規格 4.2 節的門檻（機殼類 neutral 放寬到 0.50：插圖 JSON 帶 "audit": {"enclosure": 1} 時）
TH = {"hue_groups_ge5": 4, "hue_top1": 0.35, "hue_top2_sum": 0.60, "warm_pct": 0.10, "cool_pct": 0.10, "neutral_pct": 0.35,
      "adjacent_min_de00": 15, "same_stack_min_de00": 8, "max_chroma": 0.15, "bbox_fill_w": 0.85, "bbox_fill_h": 0.70,
      "min_ball_px_390": 2.5, "min_layer_px_390": 2.0}
# 規格 2.4 不可相鄰清單
FORBID = [("si", "steel"), ("si", "magnet"), ("si", "tim"), ("steel", "magnet"), ("steel", "tim"), ("magnet", "tim"), ("steel", "tray"),
          ("dark", "rubber"), ("dark", "mold"), ("dark", "plastic"), ("rubber", "mold"), ("rubber", "plastic"), ("mold", "plastic"), ("tray", "plastic"),
          ("chip", "battery"), ("chip", "cold"), ("battery", "cold"), ("chip", "tray"), ("tray", "battery"), ("tray", "cold"),
          ("fiber", "gold"), ("fiber", "underfill"), ("fiber", "plate"), ("gold", "underfill"), ("gold", "plate"), ("underfill", "plate"),
          ("cu", "hot"), ("solder", "ceramic")]
FORBID = {frozenset(p) for p in FORBID}


# ------------------------------------------------------------------ 色彩數學（sRGB → OKLab／CIELAB、CIEDE2000）
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgb(h: str):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def css_rgb(s: str):
    import re
    v = re.findall(r"[\d.]+", s or "")
    if s and s.startswith("#"):
        return hex_rgb(s)
    if len(v) < 3:
        return None
    if len(v) >= 4 and float(v[3]) == 0:
        return None
    return tuple(float(x) for x in v[:3])


def oklch(rgb):
    r, g, b = (_lin(x / 255) for x in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), (math.degrees(math.atan2(bb, a)) + 360) % 360


def lab(rgb):
    r, g, b = (_lin(x / 255) for x in rgb)
    X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))


def de00(c1, c2):
    L1, a1, b1 = lab(c1); L2, a2, b2 = lab(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dhp = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else h2p - h1p - 360 if h2p - h1p > 180 else h2p - h1p + 360)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    hbp = h1p + h2p if C1p * C2p == 0 else ((h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else ((h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2))
    T = 1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp)) + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63))
    dth = 30 * math.exp(-((hbp - 275) / 25) ** 2); Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2); Sc = 1 + 0.045 * Cbp; Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


# ------------------------------------------------------------------ 頁面裡量的那一段（給 page.evaluate）
JS_DOM = r"""(bi) => {
  const F = [...document.querySelectorAll('#artBody .artillus')].find(f => +f.dataset.bi === bi) || document.querySelector('#artBody .artillus');
  if (!F) return null;
  const svg = F.querySelector('svg.ilsvg'), W = F.querySelector('.ilw'), WR = W.getBoundingClientRect(), SR = svg.getBoundingClientRect();
  const R = (e) => e.getBoundingClientRect();
  const hit = (a, b) => !(a.right <= b.left + 0.5 || b.right <= a.left + 0.5 || a.bottom <= b.top + 0.5 || b.bottom <= a.top + 0.5);
  const cmp = W.classList.contains('cmp');
  const vb = svg.viewBox.baseVal, sc = SR.width / vb.width;
  // 構圖填滿：所有零件群組的實際外框（SVG 座標）
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  // 只算圖形本身（getBBox 不管裁切，所以被 clip-path 裁掉的斜線、接觸陰影不算進外框）
  svg.querySelectorAll('g[data-part] :is(rect, polygon, path, circle, ellipse, line)').forEach(e => { if (e.closest('[clip-path]')) return; const b = e.getBBox(); if (!b.width && !b.height) return; x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height); });
  const balls = [...svg.querySelectorAll('circle.qball')].map(c => R(c).width / 2);
  const layers = [...svg.querySelectorAll('rect.ql1, rect.ql2')].map(r => R(r).height);
  const bumps = [...svg.querySelectorAll('ellipse.qbump')].map(e => R(e).width / 2);
  // 顏色：所有實心填色、邊線、漸層 stop（給最大彩度、深色主題最亮填色）
  const cols = [], fills = [];
  svg.querySelectorAll('*').forEach(e => { const cs = getComputedStyle(e);
    if (e.tagName === 'stop') { cols.push(cs.stopColor); return; }
    if (cs.fill && cs.fill.startsWith('rgb')) { cols.push(cs.fill); if (!e.matches('.qbh, .qdot, .qsign')) fills.push(cs.fill); }
    if (cs.stroke && cs.stroke.startsWith('rgb') && cs.stroke !== 'none') cols.push(cs.stroke); });
  // 濾鏡、陰影
  let filt = svg.querySelectorAll('filter, feGaussianBlur, feDropShadow').length;
  [F, svg, ...svg.querySelectorAll('*')].forEach(e => { const cs = getComputedStyle(e); if (cs.filter && cs.filter !== 'none') filt++; if (cs.boxShadow && cs.boxShadow !== 'none' && e !== F) filt++; });
  const anim = [...svg.querySelectorAll('animate, animateTransform, animateMotion, set')].length + [svg, ...svg.querySelectorAll('*')].filter(e => getComputedStyle(e).animationName !== 'none').length;
  // 重疊
  const lis = [...F.querySelectorAll('.ill li')].filter(e => R(e).width > 0);
  const nums = (cmp ? [...F.querySelectorAll('.ilbs em')] : lis.map(l => l.querySelector('em'))).filter(e => e && R(e).width > 0);
  const pairs = (els) => { let n = 0, w = []; for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) if (hit(R(els[i]), R(els[j]))) { n++; w.push([els[i].dataset.part || els[i].textContent, els[j].dataset.part || els[j].textContent]); } return [n, w]; };
  const [labHit, labW] = pairs(lis), [numHit, numW] = pairs(nums);
  const labOnSvg = lis.filter(l => hit(R(l), SR)).length;
  const parts = [...svg.querySelectorAll('[data-part]')];
  const numOnArt = cmp ? nums.filter(n => parts.some(p => { const r = R(p); return r.width > 0 && hit(R(n), r); })).length : 0;
  const numLab = cmp ? nums.reduce((t, n) => t + lis.filter(l => hit(R(n), R(l))).length, 0) : 0;      // 手機：右側編號壓到下方清單
  const numOff = cmp ? nums.filter(n => R(n).bottom > SR.bottom + 1 || R(n).top < SR.top - 1).length : 0;   // 手機：編號超出圖的上下範圍（對不到圖）
  const lines = [...F.querySelectorAll('svg.illn g')].map(g => { const d = g.querySelector('path').getAttribute('d'); const t = d.match(/[MVHL]|-?[0-9.]+/g); const P = []; let cx = 0, cy = 0, i = 0;
    while (i < t.length) { const c = t[i++]; if (c === 'M' || c === 'L') { cx = +t[i++]; cy = +t[i++]; } else if (c === 'V') { cy = +t[i++]; } else if (c === 'H') { cx = +t[i++]; } P.push([cx + WR.left, cy + WR.top]); }
    return { id: g.dataset.part, P }; });
  const segX = (a, b, c, d) => { const o = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]); const d1 = o(c, d, a), d2 = o(c, d, b), d3 = o(a, b, c), d4 = o(a, b, d); return ((d1 > 0.01 && d2 < -0.01) || (d1 < -0.01 && d2 > 0.01)) && ((d3 > 0.01 && d4 < -0.01) || (d3 < -0.01 && d4 > 0.01)); };
  let cross = 0; const crossW = [];
  for (let i = 0; i < lines.length; i++) for (let j = i + 1; j < lines.length; j++) { const A = lines[i].P, B = lines[j].P; let x = false;
    for (let a = 0; a + 1 < A.length && !x; a++) for (let b = 0; b + 1 < B.length && !x; b++) if (segX(A[a], A[a + 1], B[b], B[b + 1])) x = true; if (x) { cross++; crossW.push([lines[i].id, lines[j].id]); } }
  // 引線穿過別人的說明／編號：沿線每 2px 取樣
  let thruLab = 0; const thruW = []; let overParts = 0; const overW = {};
  const boxes = lis.map(l => ({ id: l.dataset.part, r: R(l) })).concat(nums.map(n => ({ id: n.dataset.part || (n.closest('li') || {}).dataset?.part, r: R(n) })));
  lines.forEach(L => { let hitLab = false; const seen = new Set();
    for (let s = 0; s + 1 < L.P.length; s++) { const a = L.P[s], b = L.P[s + 1], len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      for (let t = 0; t <= len; t += 2) { const x = a[0] + (b[0] - a[0]) * t / (len || 1), y = a[1] + (b[1] - a[1]) * t / (len || 1);
        if (!hitLab && boxes.some(q => q.id !== L.id && x > q.r.left + 1 && x < q.r.right - 1 && y > q.r.top + 1 && y < q.r.bottom - 1)) { hitLab = true; }
        if (s === 0 && t < 8) continue;
        if (x >= SR.left && x <= SR.right && y >= SR.top && y <= SR.bottom) { const el = document.elementsFromPoint(x, y).map(e => e.closest && e.closest('svg.ilsvg [data-part]')).find(Boolean); if (el && el.dataset.part !== L.id) seen.add(el.dataset.part); } } }
    if (hitLab) { thruLab++; thruW.push(L.id); } if (seen.size) { overParts++; overW[L.id] = [...seen]; } });
  return { cmp, sc, vb: [vb.x, vb.y, vb.width, vb.height], fill: [x0, y0, x1, y1], balls, layers, bumps, cols, fills, filt, anim,
    labHit, labW, numHit, numW, labOnSvg, numOnArt, numLab, numOff, cross, crossW, thruLab, thruW, overParts, overW, nLines: lines.length, nLabels: lis.length,
    bg: getComputedStyle(F).backgroundColor, theme: document.documentElement.getAttribute('data-theme') || 'dark', v2: svg.classList.contains('ilv2'),
    vw: innerWidth, sw: document.documentElement.scrollWidth - innerWidth };
}"""

JS_SPEC = r"""(bi) => { const F = [...document.querySelectorAll('#artBody .artillus')].find(f => +f.dataset.bi === bi) || document.querySelector('#artBody .artillus'); return F ? +F.dataset.bi : null; }"""


def pixel_stats(png: bytes, bg) -> dict:
    """插圖截圖逐像素：去掉卡片底色 → OKLCH → 色相 30° 一組。"""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(BytesIO(png)).convert("RGB")).reshape(-1, 3).astype(np.float64)
    bgv = np.array(bg, dtype=np.float64)
    keep = np.abs(im - bgv).max(axis=1) > 10            # 跟卡片底色差超過 10／255 才算插圖
    px = im[keep] / 255.0
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    l_ = np.cbrt(lin @ np.array([0.4122214708, 0.5363325363, 0.0514459929]))
    m_ = np.cbrt(lin @ np.array([0.2119034982, 0.6806995451, 0.1073969566]))
    s_ = np.cbrt(lin @ np.array([0.0883024619, 0.2817188376, 0.6299787005]))
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = np.hypot(a, b); H = (np.degrees(np.arctan2(b, a)) + 360) % 360
    tot = len(px)
    if not tot:
        return {"px": 0}
    chrom = C >= 0.03
    nc = int(chrom.sum())
    Hc = H[chrom]
    bins = np.bincount((Hc // 30).astype(int), minlength=12)[:12] / max(1, nc)
    order = sorted(range(12), key=lambda i: -bins[i])
    return {"px": int(tot), "neutral_pct": round(1 - nc / tot, 4), "hue_bins": {f"{i * 30}-{i * 30 + 30}": round(float(bins[i]), 4) for i in range(12)},
            "hue_groups_ge5": int((bins >= 0.05).sum()), "hue_top1": round(float(bins[order[0]]), 4), "hue_top2_sum": round(float(bins[order[0]] + bins[order[1]]), 4),
            "warm_pct": round(float(((Hc >= 20) & (Hc <= 110)).sum() / max(1, nc)), 4), "cool_pct": round(float(((Hc >= 180) & (Hc <= 300)).sum() / max(1, nc)), 4)}


def structure(pg, block: dict, theme: str) -> dict:
    """讀渲染器正規化後的積木（spec2），算 mat 數、零件數、同 mat、相鄰色差、不可相鄰、空白方塊。"""
    if block.get("kind") != "custom":     # 內建 kind（cowos／rack）：幾何寫在程式裡，沒有 JSON 積木可讀 → 結構類量測不適用（色彩、尺寸、重疊照量）
        return {"builtin": True, "parts_count": None, "mat_count": None, "mats": [], "same_mat_parts": 0, "same_mat_detail": [], "adjacent_min_de00": None, "adjacent_min_pair": None,
                "same_stack_min_de00": None, "forbidden_pairs": 0, "forbidden_detail": [], "empty_boxes": 0, "empty_detail": [],
                "front_grad_dl_min": None, "front_side_dl_min": None, "top_front_dl_min": None}
    sp = pg.evaluate("(b) => window.TwArtIllus.spec2(b)", block)
    th = "light" if theme == "light" else "dark"
    cache = {}

    def front(s):
        k = (s["mat"], s["tone"], s["back"])
        if k not in cache:
            cache[k] = pg.evaluate("([m, t, bk, th]) => window.TwArtIllus.colors2(m, t, bk, th)", [s["mat"], s["tone"], s["back"], th])
        return hex_rgb(cache[k]["f"])

    sh = [s for s in sp["shapes"] if s["type"] != "guide" and s.get("bb")]
    parts = sorted({s["part"] for s in sh})
    mats = sorted({s["mat"] for s in sh})
    body = [s for s in sh if s["type"] in ("box", "cyl", "hcyl", "wheel", "shell")]   # 10-17 晚：新積木（橫躺圓柱、車輪、外殼）也是本體
    same = []
    by_mat: dict = {}
    for s in body:
        by_mat.setdefault(s["mat"], {}).setdefault(s["part"], set()).add(s["tone"])
    for m, pp in by_mat.items():
        if len(pp) < 2:
            continue
        items = [(p, t) for p, ts in pp.items() for t in ts]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (p1, t1), (p2, t2) = items[i], items[j]
                if p1 == p2:
                    continue
                if t1 == t2:
                    same.append([m, p1, p2, "同 tone"])
                else:
                    d = de00(front({"mat": m, "tone": t1, "back": 0}), front({"mat": m, "tone": t2, "back": 0}))
                    if d < 8:
                        same.append([m, p1, p2, f"ΔE00 {d:.1f} < 8"])
    gap = lambda a, b: max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3], 0)  # noqa: E731
    adj_min, stack_min, adj_w, forb = 1e9, 1e9, None, []
    for i in range(len(sh)):
        for j in range(i + 1, len(sh)):
            a, b = sh[i], sh[j]
            if gap(a["bb"], b["bb"]) > 2:
                continue
            if a["mat"] != b["mat"] and frozenset((a["mat"], b["mat"])) in FORBID:
                forb.append([a["part"], a["mat"], b["part"], b["mat"]])
            if a["mat"] == b["mat"] and a["tone"] == b["tone"] and a["part"] == b["part"]:
                continue
            d = de00(front(a), front(b))
            if a["part"] != b["part"]:
                if d < adj_min:
                    adj_min, adj_w = d, [a["part"], a["mat"], b["part"], b["mat"]]
            else:
                stack_min = min(stack_min, d)
    vb_area = max(1.0, (max(s["bb"][2] for s in sh) - min(s["bb"][0] for s in sh)) * (max(s["bb"][3] for s in sh) - min(s["bb"][1] for s in sh))) if sh else 1
    empty = [s["part"] for s in sh if s["type"] == "box" and not s["details"] and s["w"] * s["h"] > 0.02 * vb_area]
    # 光影落差（用到的色組：正面漸層上下、正−側、頂−正，CIELAB L*）
    shade = {"front_grad_dl_min": 1e9, "front_side_dl_min": 1e9, "top_front_dl_min": 1e9}
    for s in body:
        c = cache.get((s["mat"], s["tone"], s["back"])) or pg.evaluate("([m, t, bk, th]) => window.TwArtIllus.colors2(m, t, bk, th)", [s["mat"], s["tone"], s["back"], th])
        L = {k: lab(hex_rgb(c[k]))[0] for k in ("t", "f", "s", "g0", "g1")}
        shade["front_grad_dl_min"] = min(shade["front_grad_dl_min"], L["g0"] - L["g1"])
        shade["front_side_dl_min"] = min(shade["front_side_dl_min"], L["f"] - L["s"])
        shade["top_front_dl_min"] = min(shade["top_front_dl_min"], L["t"] - L["f"])
    shade = {k: round(v, 1) for k, v in shade.items()}
    return {"parts_count": len(parts), "mat_count": len(mats), "mats": mats, "same_mat_parts": len(same), "same_mat_detail": same,
            "adjacent_min_de00": round(adj_min, 1) if adj_min < 1e9 else None, "adjacent_min_pair": adj_w,
            "same_stack_min_de00": round(stack_min, 1) if stack_min < 1e9 else None,
            "forbidden_pairs": len(forb), "forbidden_detail": forb, "empty_boxes": len(empty), "empty_detail": empty, **shade}


def measure(pg, block: dict, bi: int, theme: str, width: int, shot_dir: Path | None = None, tag: str = "") -> dict:
    """在已經打開那篇文章的頁面上量一張插圖（當下的主題與視窗寬）。"""
    pg.evaluate(f"() => {{ const F = [...document.querySelectorAll('#artBody .artillus')].find(f => +f.dataset.bi === {bi}); if (F) F.scrollIntoView({{block: 'center', behavior: 'instant'}}); }}")
    pg.wait_for_timeout(300)
    dom = pg.evaluate(JS_DOM, bi)
    if not dom:
        return {"error": "找不到插圖"}
    out = {"theme": theme, "width": width, "v2": dom["v2"], "cmp": dom["cmp"]}
    fx0, fy0, fx1, fy1 = dom["fill"]; vb = dom["vb"]
    out["bbox_fill_w"] = round((fx1 - fx0) / vb[2], 3) if vb[2] else 0
    out["bbox_fill_h"] = round((fy1 - fy0) / vb[3], 3) if vb[3] else 0
    out["balls_n"] = len(dom["balls"]); out["min_ball_px"] = round(min(dom["balls"]), 2) if dom["balls"] else None
    out["min_layer_px"] = round(min(dom["layers"]), 2) if dom["layers"] else None
    out["min_bump_px"] = round(min(dom["bumps"]), 2) if dom["bumps"] else None
    chroma = [oklch(c)[1] for c in (css_rgb(x) for x in dom["cols"]) if c]
    out["max_chroma"] = round(max(chroma), 4) if chroma else 0
    fl = [oklch(c)[0] for c in (css_rgb(x) for x in dom["fills"]) if c]
    out["max_fill_L"] = round(max(fl), 3) if fl else 0
    out["filters"] = dom["filt"]; out["animations"] = dom["anim"]
    ov = {"labels": dom["labHit"], "numbers": dom["numHit"], "label_on_art": dom["labOnSvg"], "number_on_part": dom["numOnArt"], "number_on_label": dom["numLab"], "number_off_figure": dom["numOff"],
          "leader_cross": dom["cross"], "leader_thru_label": dom["thruLab"]}
    out["overlap"] = sum(ov.values()); out["overlap_detail"] = {**ov, "where": {"labels": dom["labW"], "numbers": dom["numW"], "cross": dom["crossW"], "thru": dom["thruW"]}}
    out["leader_over_parts"] = dom["overParts"]; out["leader_over_detail"] = dom["overW"]
    out["n_leaders"] = dom["nLines"]; out["hscroll"] = dom["sw"] > 0
    if width >= 1000:
        # 只截插圖本身：先把引線、浮水印藏起來，量完還原
        pg.add_style_tag(content="#artPost::after{display:none!important} .artillus svg.illn{visibility:hidden!important} .artillus .ilbs{visibility:hidden!important}")
        pg.wait_for_timeout(100)
        loc = pg.locator(f"#artBody .artillus[data-bi='{bi}'] svg.ilsvg")
        png = loc.screenshot()
        out.update(pixel_stats(png, css_rgb(dom["bg"])))
        pg.evaluate("() => { const s = [...document.querySelectorAll('style')].pop(); if (s && /illn\\{visibility/.test(s.textContent)) s.remove(); }")
        if shot_dir:
            Path(shot_dir).mkdir(parents=True, exist_ok=True)
            (Path(shot_dir) / f"audit_art_{tag or theme}.png").write_bytes(png)
    return out


def judge(block: dict, res: dict) -> list:
    """把量到的數字對規格 4.2 節門檻，回傳不過的清單（空＝全過）。res＝{theme: {wide, narrow, struct}}。"""
    enclosure = bool((block.get("audit") or {}).get("enclosure")) if isinstance(block.get("audit"), dict) else False
    fails = []
    for th, r in res.items():
        w, n, s = r["wide"], r["narrow"], r["struct"]
        chk = [("hue_groups_ge5", w.get("hue_groups_ge5", 0) >= TH["hue_groups_ge5"]), ("hue_top1", w.get("hue_top1", 1) <= TH["hue_top1"]),
               ("hue_top2_sum", w.get("hue_top2_sum", 1) <= TH["hue_top2_sum"]), ("warm_pct", w.get("warm_pct", 0) >= TH["warm_pct"]),
               ("cool_pct", w.get("cool_pct", 0) >= TH["cool_pct"]), ("neutral_pct", w.get("neutral_pct", 1) <= (0.50 if enclosure else TH["neutral_pct"])),
               ("mat_count", s.get("builtin") or s["mat_count"] >= (5 if s["parts_count"] >= 6 else 3 if s["parts_count"] >= 3 else 1)),
               ("same_mat_parts", s["same_mat_parts"] == 0), ("adjacent_min_de00", s["adjacent_min_de00"] is None or s["adjacent_min_de00"] >= TH["adjacent_min_de00"]),
               ("same_stack_min_de00", s["same_stack_min_de00"] is None or s["same_stack_min_de00"] >= TH["same_stack_min_de00"]),
               ("forbidden_pairs", s["forbidden_pairs"] == 0), ("max_chroma", max(w["max_chroma"], n["max_chroma"]) <= TH["max_chroma"]),
               ("bbox_fill_w", w["bbox_fill_w"] >= TH["bbox_fill_w"]), ("bbox_fill_h", w["bbox_fill_h"] >= TH["bbox_fill_h"]),
               ("min_ball_px_390", n["min_ball_px"] is None or n["min_ball_px"] >= TH["min_ball_px_390"]),
               ("min_layer_px_390", n["min_layer_px"] is None or n["min_layer_px"] >= TH["min_layer_px_390"]),
               ("empty_boxes", s["empty_boxes"] == 0), ("overlap", w["overlap"] == 0 and n["overlap"] == 0),
               ("filters", w["filters"] == 0 and n["filters"] == 0 and w["animations"] == 0),
               ("dark_fill_L", th != "dark" or w["max_fill_L"] <= 0.90)]
        fails += [f"{th}:{k}" for k, okk in chk if not okk]
    return fails


def summary(res: dict) -> dict:
    """整理成規格 4.2 節的欄位（每個主題一份）。"""
    out = {}
    for th, r in res.items():
        w, n, s = r["wide"], r["narrow"], r["struct"]
        out[th] = {"hue_groups_ge5": w.get("hue_groups_ge5"), "hue_top1": w.get("hue_top1"), "hue_top2_sum": w.get("hue_top2_sum"),
                   "warm_pct": w.get("warm_pct"), "cool_pct": w.get("cool_pct"), "neutral_pct": w.get("neutral_pct"), "hue_bins": w.get("hue_bins"),
                   "mat_count": s["mat_count"], "parts_count": s["parts_count"], "same_mat_parts": s["same_mat_parts"],
                   "adjacent_min_de00": s["adjacent_min_de00"], "adjacent_min_pair": s["adjacent_min_pair"], "same_stack_min_de00": s["same_stack_min_de00"],
                   "forbidden_pairs": s["forbidden_pairs"], "max_chroma": max(w["max_chroma"], n["max_chroma"]), "max_fill_L": w["max_fill_L"],
                   "bbox_fill_w": w["bbox_fill_w"], "bbox_fill_h": w["bbox_fill_h"], "min_ball_px_390": n["min_ball_px"], "min_layer_px_390": n["min_layer_px"],
                   "min_bump_px_390": n["min_bump_px"], "empty_boxes": s["empty_boxes"], "overlap": w["overlap"] + n["overlap"],
                   "overlap_1440": w["overlap_detail"], "overlap_390": n["overlap_detail"],
                   "leader_over_parts_1440": w["leader_over_parts"], "leader_over_parts_390": n["leader_over_parts"],
                   "filters": w["filters"] + n["filters"], "animations": w["animations"],
                   "front_grad_dl_min": s["front_grad_dl_min"], "front_side_dl_min": s["front_side_dl_min"], "top_front_dl_min": s["top_front_dl_min"],
                   "mats": s["mats"], "same_mat_detail": s["same_mat_detail"], "forbidden_detail": s["forbidden_detail"], "empty_detail": s["empty_detail"]}
    return out


# ------------------------------------------------------------------ 命令列
def _serve():
    class H(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store"); super().end_headers()

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(H, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def run_audit(post: dict, shot_dir: Path | None = None, browser=None) -> dict:
    from playwright.sync_api import sync_playwright
    if post.get("t") == "illus":                       # 只給了一個 illus 區塊 → 包成一篇最小文章
        post = {"id": "audit-illus", "cat": "know", "title": "插圖量測", "date": "2026-10-17", "tags": [], "summary": "", "reading_min": 1, "groups": [], "blocks": [post]}
    aid = "audit-illus-" + str(abs(hash(json.dumps(post, sort_keys=True))) % 10 ** 8)
    post = dict(post, id=aid)
    bi = next((i for i, b in enumerate(post["blocks"]) if isinstance(b, dict) and b.get("t") == "illus" and b.get("style") == 2),
              next(i for i, b in enumerate(post["blocks"]) if isinstance(b, dict) and b.get("t") == "illus"))
    block = post["blocks"][bi]
    body = json.dumps(post, ensure_ascii=False)
    srv = _serve(); base = f"http://127.0.0.1:{srv.server_address[1]}/"
    res = {}
    with sync_playwright() as p:
        br = browser or p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        try:
            for theme in ("dark", "light"):
                r = {}
                for w in (1440, 390):
                    mob = w < 640
                    ctx = br.new_context(viewport={"width": w, "height": 844 if mob else 900}, device_scale_factor=2, is_mobile=mob, has_touch=mob)
                    ctx.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.theme'," + json.dumps(theme) + ")}catch(e){}")
                    ctx.route("**/fonts.googleapis.com/**", lambda rt: rt.abort())
                    ctx.route(f"**/articles/posts/{aid}.json", lambda rt: rt.fulfill(status=200, content_type="application/json", body=body))
                    pg = ctx.new_page()
                    pg.goto(base + "#article/" + aid, wait_until="domcontentloaded")
                    pg.wait_for_function("() => { const f = document.querySelector('#artBody .artillus'); return f && +f.dataset.lines > 0; }", timeout=20000)
                    pg.wait_for_timeout(500)
                    r["wide" if not mob else "narrow"] = measure(pg, block, bi, theme, w, shot_dir, f"{theme}{w}")
                    if not mob:
                        r["struct"] = structure(pg, block, theme)
                    ctx.close()
                res[theme] = r
        finally:
            if not browser:
                br.close()
            srv.shutdown()
    fails = judge(block, res)
    return {"pass": not fails, "fails": fails, "thresholds": TH, "per_theme": summary(res)}


def main():
    ap = argparse.ArgumentParser(description="精選文章插圖第 2 版機器量測（規格 4.2 節）")
    ap.add_argument("--post", required=True, help="文章 JSON（或單一 illus 區塊）的本機路徑；不會被複製進 site/")
    ap.add_argument("--out", required=True, help="輸出 illus_audit.json 的路徑")
    ap.add_argument("--shots", default="", help="插圖截圖（量色彩用的那張）存放資料夾，可省略")
    a = ap.parse_args()
    post = json.loads(Path(a.post).read_text(encoding="utf-8"))
    res = run_audit(post, Path(a.shots) if a.shots else None)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("✅ 全部過" if res["pass"] else "❌ 不過：" + "、".join(res["fails"])))
    for th, r in res["per_theme"].items():
        print(th, {k: r[k] for k in ("hue_groups_ge5", "hue_top1", "hue_top2_sum", "warm_pct", "cool_pct", "neutral_pct", "mat_count", "parts_count", "same_mat_parts",
                                     "adjacent_min_de00", "forbidden_pairs", "max_chroma", "bbox_fill_w", "bbox_fill_h", "min_ball_px_390", "min_layer_px_390", "empty_boxes", "overlap", "filters")})


if __name__ == "__main__":
    main()
