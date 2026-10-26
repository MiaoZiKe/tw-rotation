"""哩股哩股社群貼文：原生繪製的卡片（亮色 HUD；規範 docs/marketing/social_unit/post_design_system.md 第十五節）。

為什麼：網站截圖縮進 1080 畫布後，圖內字只剩 9～17px、卡片是橫長條沒撐滿 4:5、留白多。
這裡改成跟 social_premarket.py 同一招：用 HTML／SVG 直接畫，字級全部 ≥24px（排行類每列字 ≥28px），圖撐滿畫布。
資料來源：網站 data/*.json（inst_market、inst_today、fut_oi、retail_ratio、market_fut）；盤中即時那幾張（族群資金排行、
資金分流樹、大盤走勢、漲跌家數）在截圖瀏覽器已套上即時資料的頁面上，由 social_snap 的 dump 讀出（echarts 資料或 DOM 數字）。
網站截圖只保留「資金熱力圖」與「資金輪盤圓盤」。

入口：render(browser, name, mode, ctx, out_png) → 回傳版面檢查報告（欄位同 social_snap.compose 的報告）。
ctx＝dict(kind, title, date, jget(name)->json, site(Path), dump(dict), reads(dict), names(dict), logos(dict))。
"""
from __future__ import annotations

import base64
import html as _h
import math
import re
from pathlib import Path

import social_theme as TH

T = TH.TOKENS
FONTS = TH.FONT
NUMF = TH.NUM_FONT
MIN_FONT = 24           # 畫布字級下限
H_THREADS = 1350


def esc(s) -> str:
    return _h.escape(str(s), quote=True)


def est_w(s: str, size: float) -> float:
    return sum(size if ord(c) > 255 else size * 0.6 for c in str(s))


def ell(s: str, size: float, maxw: float) -> str:
    s = str(s)
    if est_w(s, size) <= maxw:
        return s
    while s and est_w(s + "…", size) > maxw:
        s = s[:-1]
    return s + "…"


def sgn(v: float, nd: int = 2, unit: str = "", plus: bool = True) -> str:
    s = f"{abs(v):,.{nd}f}"
    return ("−" if v < 0 else ("+" if plus and v > 0 else "")) + s + unit


def tone(v: float) -> str:
    return T["rise"] if v > 0 else (T["fall"] if v < 0 else T["flat"])


def svg_t(x, y, s, size, fill, anchor="start", weight=400, mono=False, extra="") -> str:
    ff = f"font-family:{NUMF};" if mono else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="font-size:{size}px;font-weight:{weight};fill:{fill};{ff}" {extra}>{esc(s)}</text>')


def svg_open(w, h) -> str:
    return f'<svg width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" style="display:block">'


# ------------------------------------------------------------------ logo
_LOGO_CACHE: dict = {}
COLS = ["#3558c9", "#5b45c7", "#8a3fb0", "#1b6f99", "#9a5b12", "#4d5b73", "#7a5a3a", "#2f4f8f"]


def logo_html(code: str, name: str, ctx: dict, size: int = 44) -> str:
    key = (code, size)
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    uri = ""
    p = (ctx.get("logos") or {}).get(code)
    if p and str(p).startswith("http"):
        uri = str(p)
    elif p:
        f = Path(ctx["site"]) / str(p)
        if f.exists():
            uri = "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()
    if uri:
        h = f'<span class=lg style="width:{size}px;height:{size}px"><img src="{uri}" style="width:100%;height:100%;object-fit:contain;background:#fff"></span>'
    else:
        hh = 7
        for ch in code:
            hh = (hh * 31 + ord(ch)) & 0xFFFFFFFF
        letter = re.sub(r"[\s*＊\-_.()（）]", "", name or code)[:1] or code[:1]
        h = f'<span class=lg style="width:{size}px;height:{size}px;background:{COLS[hh % len(COLS)]};color:#fff;font-weight:700;font-size:{max(24, int(size * .55))}px">{esc(letter)}</span>'
    _LOGO_CACHE[key] = h
    return h


# ------------------------------------------------------------------ 殼
def css_extra(mode: str) -> str:
    s = TH.CANVAS[mode]["s"]
    H = 1920 if mode == "story" else H_THREADS
    return f"""
html,body{{height:{H}px;overflow:hidden}}body{{height:{H}px}}
.card{{flex:1;min-height:0;display:flex;flex-direction:column;padding:{16 if mode == 'threads' else 18}px}}
.area{{flex:1;min-height:0;position:relative;overflow:hidden}}
svg text{{font-family:{FONTS};font-variant-numeric:tabular-nums}}
.lg{{display:inline-flex;flex:none;border-radius:50%;overflow:hidden;align-items:center;justify-content:center}}
.sub{{border:1.5px solid var(--line);border-radius:10px;background:var(--panel2);position:relative}}
.rl{{height:100%;display:flex;flex-direction:column;gap:10px}}
.rl .sec{{display:flex;flex-direction:column;min-height:0}}
.rl .sh{{flex:none;font-size:{TH.SEC_FS[mode]}px;font-weight:800;line-height:1.4;padding:2px 6px 4px}}
.rl .rows{{flex:1;min-height:0;display:flex;flex-direction:column;border-top:1.5px solid var(--line)}}
.rl .r{{flex:1;min-height:0;display:flex;align-items:center;gap:12px;padding:0 8px;border-bottom:1px dashed var(--line)}}
.rl .r:last-child{{border-bottom:none}}
.rl .rk{{flex:none;width:{round(34 * s)}px;font-size:{round(26 * s)}px;color:var(--ink3);text-align:center;font-family:{NUMF}}}
.rl .nm{{flex:none;display:flex;align-items:baseline;gap:8px;white-space:nowrap;overflow:hidden}}
.rl .nm b{{font-size:{round(30 * s)}px;font-weight:800}}.rl .nm i{{font-style:normal;font-size:{round(24 * s)}px;color:var(--ink3);font-family:{NUMF}}}
.rl .bar{{flex:1;min-width:30px;height:{round(24 * s)}px;border-radius:6px;background:rgba(10,106,134,.08);position:relative;overflow:hidden}}
.rl .bar u{{position:absolute;left:0;top:0;bottom:0;border-radius:6px;text-decoration:none}}
.rl .v{{flex:none;text-align:right;font-size:{round(30 * s)}px;font-weight:800;font-family:{NUMF};white-space:nowrap}}
.rl .v small{{font-size:{round(24 * s)}px;font-weight:600;color:var(--ink2);margin-left:6px}}
.kp{{display:grid;gap:10px;flex:none}}
.k{{padding:10px 14px;min-width:0}}
.k .l{{font-size:{round(28 * s)}px;font-weight:700;color:var(--ink2);line-height:1.3}}
.k .vv{{font-size:{round(44 * s)}px;font-weight:800;line-height:1.2;white-space:nowrap;font-family:{NUMF}}}
.k .vv u{{text-decoration:none;font-size:{round(26 * s)}px;font-weight:600;color:var(--ink2);margin-left:4px}}
.k .ss{{font-size:{round(25 * s)}px;color:var(--ink3);white-space:nowrap;line-height:1.35}}
.ptitle{{display:flex;align-items:baseline;gap:14px;font-size:{TH.SEC_FS[mode]}px;font-weight:800;line-height:1.35;white-space:nowrap;padding:6px 10px 0}}
.ptitle i{{font-style:normal;font-size:{round(44 * s)}px;font-weight:800;font-family:{NUMF}}}
.ptitle em{{font-style:normal;font-size:{round(26 * s)}px;font-weight:600;color:var(--ink2)}}
.ptitle .rt{{margin-left:auto;font-size:{round(26 * s)}px;font-weight:600;color:var(--ink3)}}
"""


def shell(mode: str, kind: str, title: str, date: str) -> str:
    return (f"<!doctype html><html><head><meta charset=utf-8><style>{TH.base_css(mode)}{css_extra(mode)}</style></head><body>"
            f'{TH.header_html(kind, esc(title), esc(date))}<div class=card><div class=area id=area></div></div></body></html>')


CHECK_JS = """() => {
  const els = [...document.querySelectorAll('[data-box]')];
  const R = els.map(e => { const r = e.getBoundingClientRect(); let b = { x: r.x, y: r.y, w: r.width, h: r.height };
    if (e.tagName !== 'IMG') { const rg = document.createRange(); rg.selectNodeContents(e); const t = rg.getBoundingClientRect(); if (t.width) b = { x: t.x, y: t.y, w: t.width, h: t.height }; }
    return { n: e.dataset.box, ...b, cut: e.tagName !== 'IMG' && e.scrollWidth > e.clientWidth + 1 }; });
  const hits = [];
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) { const a = R[i], b = R[j];
    if (a.x < b.x + b.w - 0.5 && b.x < a.x + a.w - 0.5 && a.y < b.y + b.h - 0.5 && b.y < a.y + a.h - 0.5) hits.push(a.n + '×' + b.n); }
  const W = document.documentElement.clientWidth, H = document.documentElement.clientHeight;
  const out = R.filter(b => b.x < -0.5 || b.y < -0.5 || b.x + b.w > W + 0.5 || b.y + b.h > H + 0.5).map(b => b.n);
  const ar = document.getElementById('area'); const cut = R.filter(r => r.cut).map(r => r.n);
  if (ar.scrollHeight > ar.clientHeight + 2 || ar.scrollWidth > ar.clientWidth + 2) cut.push('area');
  // 字級下限：HTML 與 SVG 文字節點的實際字級
  let minf = 999; const small = [];
  const it = document.createTreeWalker(ar, NodeFilter.SHOW_TEXT);
  while (it.nextNode()) { const n = it.currentNode; if (!n.textContent.trim()) continue; const el = n.parentElement; const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < minf) minf = fs; if (fs < 23.5) small.push(n.textContent.trim().slice(0, 12) + ':' + fs); }
  return { hits, out, cut, n: R.length, min_font: minf, small: small.slice(0, 6), imgs_ok: [...document.images].every(i => i.complete) };
}"""


def render(browser, name: str, mode: str, ctx: dict, out_png: Path) -> dict:
    spec = BUILDERS[name]
    kind = ctx["kind"]
    H = 1920 if mode == "story" else H_THREADS
    pg = browser.new_page(viewport={"width": 1080, "height": H}, device_scale_factor=1)
    pg.set_content(shell(mode, kind, ctx["title"], ctx["date"]), wait_until="load")
    w, h = pg.evaluate("() => { const r = document.getElementById('area').getBoundingClientRect(); return [Math.floor(r.width), Math.floor(r.height)]; }")
    inner = spec(mode, w, h, ctx)
    pg.evaluate("(h) => { document.getElementById('area').innerHTML = h; }", inner)
    pg.wait_for_timeout(500)
    pg.evaluate("() => Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = r; i.onerror = r; setTimeout(r, 5000); })))")
    res = pg.evaluate(CHECK_JS)
    res.update(file=out_png.name, w=1080, h=H, scale=1.0, shot_ratio=1.0, content_ratio=1.0, native=True)
    pg.screenshot(path=str(out_png), full_page=False)
    pg.close()
    return res


# ================================================================== 各張
def S_(mode):
    return TH.CANVAS[mode]["s"]


# ---- 族群資金排行（對稱長條）
def b_rotation_rank(mode, w, h, ctx):
    d = ctx.get("dump") or {}
    names, vals = d.get("names") or [], d.get("vals") or []
    names, vals = names[::-1], vals[::-1]            # echarts 類別軸由下往上；畫成由上往下
    n = len(vals)
    if not n:
        return ""
    s = S_(mode)
    f = round(30 * s)
    cap_h = round(40 * s)
    rh = (h - cap_h) / n
    mx, mn = max([0] + vals), abs(min([0] + vals))
    parsed = []
    for nm in names:
        m = re.match(r"^(.*?)\s+(\d+)([↑↓])$", str(nm))
        parsed.append((m.group(1), m.group(2) + m.group(3)) if m else (str(nm), ""))
    aw = round(26 * s) * 2.6
    lw = min(w * 0.46, max(est_w(a, f) for a, b in parsed) + aw + 8)
    vp = est_w("−0.00", f) + 34
    x0 = lw + 14
    pw = w - x0 - 2 * vp - 4
    zero = x0 + vp + (mn / (mx + mn or 1)) * pw
    scale = pw / (mx + mn or 1)
    g = [svg_open(w, h)]
    g.append(svg_t(8, cap_h - 8, "資金占比變化（百分點 pp）", round(26 * s), T["ink3"], weight=600))
    g.append(f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="{cap_h}" y2="{h}" stroke="{T["line2"]}" stroke-width="2"/>')
    for i, ((a, b), v) in enumerate(zip(parsed, vals)):
        cy = cap_h + rh * (i + 0.5)
        bt = min(rh * 0.66, 44 * s)
        col = tone(v)
        wv = abs(v) * scale
        xa = zero if v >= 0 else zero - wv
        g.append(f'<rect x="{xa:.1f}" y="{cy - bt / 2:.1f}" width="{max(wv, 3):.1f}" height="{bt:.1f}" rx="5" fill="{col}" opacity=".88"/>')
        lab = ell(a, f, lw - aw - 4)
        g.append(svg_t(lw - aw, cy + f * 0.35, lab, f, T["ink"], "end", 700))
        if b:
            g.append(svg_t(lw - aw + 8, cy + f * 0.35, b, round(26 * s), T["rise"] if "↑" in b else T["fall"], "start", 600, True))
        tx = (zero + wv + 8) if v >= 0 else (zero - wv - 8)
        g.append(svg_t(tx, cy + f * 0.35, sgn(v, 2), f, col, "start" if v >= 0 else "end", 800, True))
    g.append("</svg>")
    return "".join(g)


# ---- 排行清單（個股：外資／投信／融資／融券）
def is_stock(code) -> bool:
    """個股＝4 碼數字、首碼非 0（排除 ETF 00xxx、ETN 02xxxx、權證等）。2026-10-26 Andy：「排除ETF只列個股」"""
    c = str(code)
    return len(c) == 4 and c.isdigit() and c[0] != "0"


def clean_name(name) -> str:
    """證交所簡稱的「*」拿掉（例：國巨* → 國巨）。2026-10-26 Andy：「星號拿掉」"""
    return str(name or "").replace("*", "").replace("＊", "").strip()


def credit_top(m: dict, which: str, n: int = 8):
    """融資（rank）／融券（short）增減前 n 名，只列個股。回 (增加, 減少)。"""
    rk = (m.get("short_rank") if which == "short" else m.get("rank")) or {}
    rows = [r for r in (rk.get("rows") or []) if is_stock(r.get("code"))]
    up = sorted([r for r in rows if r["chg"] > 0], key=lambda r: -r["chg"])[:n]
    dn = sorted([r for r in rows if r["chg"] < 0], key=lambda r: r["chg"])[:n]
    return up, dn


def rank_list(mode, w, h, ctx, sections, vw=190):
    """sections＝[(標題, 色, [dict(code,name,frac,val,sub)], 顏色)]"""
    s = S_(mode)
    out = ['<div class=rl>']
    tot = sum(len(r) for _, _, r, *_ in sections) or 1
    # 名稱欄固定寬（取這張卡最長的名稱＋代號，上限 42%），長條一律從同一條線開始（2026-10-26 Andy：「長條圖幫我靠左對齊」）
    allr = [r for _, _, rows, *_ in sections for r in rows]
    nmw = min(max([est_w(clean_name(r["name"]), 30 * s) + est_w(str(r["code"]), 24 * s) + 14 for r in allr] + [120]), w * 0.42)
    lotw = max([est_w(f'{r["lots"]:+,}張', 24 * s) for r in allr if r.get("lots") is not None] + [0])     # 不打折：10/21「+168,000張」被切掉
    # 數字欄固定寬（量最長的「數字＋單位＋張數」），每列長條的右端也對齊
    vw = max([vw] + [est_w(r["val"], 30 * s) + est_w(r.get("unit", ""), 24 * s) + 6 + ((lotw + 14) if r.get("lots") is not None else 0) for r in allr])
    for title, col, rows in [(a, b, c) for a, b, c, *_ in sections]:
        out.append(f'<div class=sec style="flex:{len(rows) + 1.3}"><div class=sh style="color:{col}">{esc(title)}</div><div class=rows>')
        for i, r in enumerate(rows):
            lots = (f'<em style="display:inline-block;width:{lotw + 14:.0f}px;font-style:normal;font-size:{round(24 * s)}px;font-weight:600;color:var(--ink2);text-align:right">'
                    f'{r["lots"]:+,}張</em>' if r.get("lots") is not None else "")       # 2026-10-26 Andy：「需要備註買多少張」
            out.append(
                f'<div class=r><span class=rk>{i + 1}</span>{logo_html(r["code"], r["name"], ctx, round(46 * s))}'
                f'<span class=nm style="width:{nmw:.0f}px"><b>{esc(clean_name(r["name"]))}</b><i>{esc(r["code"])}</i></span>'
                f'<span class=bar><u style="width:{max(r["frac"] * 100, 3):.1f}%;background:{col};opacity:.85"></u></span>'
                f'<span class=v style="color:{col};width:{vw:.0f}px;flex:none">{esc(r["val"])}<small>{esc(r.get("unit", ""))}</small>{lots}</span></div>')
        out.append("</div></div>")
    out.append("</div>")
    return "".join(out)


def inst_top(j: dict, side: str, n: int = 10, names: dict | None = None):
    """外資／投信當日買超、賣超前 n 名，只列個股（排除 ETF，2026-10-26 Andy「法人也排除ETF」）。
    用 inst_today.json 的 all_by（全市場逐檔 [代號, 張, 億元]），不用 top（只有前 10、濾掉 ETF 會不足 10 名）；
    all_by 沒有就退回 top。回 (買超, 賣超)，每列 dict(code, name, amt＝元)。"""
    names = names or {}
    for r in ((j.get("top") or {}).get(side) or {}).get("buy", []) + ((j.get("top") or {}).get(side) or {}).get("sell", []):
        names.setdefault(str(r["code"]), r["name"])
    rows = (j.get("all_by") or {}).get(side)
    if rows:
        rs = [dict(code=str(c), name=names.get(str(c), str(c)), amt=float(y) * 1e8, lots=int(l)) for c, l, y in rows if is_stock(c)]
    else:
        t = (j.get("top") or {}).get(side) or {}
        rs = [dict(code=str(r["code"]), name=r["name"], amt=float(r["amt"]), lots=int(r.get("lots") or 0)) for r in t.get("buy", []) + t.get("sell", []) if is_stock(r["code"])]
    buy = sorted([r for r in rs if r["amt"] > 0], key=lambda r: -r["amt"])[:n]
    sell = sorted([r for r in rs if r["amt"] < 0], key=lambda r: r["amt"])[:n]
    return buy, sell


def etf_buy(j: dict, side: str, n: int = 10, names: dict | None = None):
    """外資／投信當日 ETF 買超前 n 名（代號 00 開頭；2026-10-26 Andy「新增一個 ETF 買超排名，外資、投信上下兩張」）。"""
    names = names or {}
    rows = (j.get("all_by") or {}).get(side) or []
    # 含槓桿型／反向型（00631L、00632R…，代號一樣 00 開頭；2026-10-26 Andy「ETF 需要包含槓桿型ETF」）
    rs = [dict(code=str(c), name=names.get(str(c), str(c)), amt=float(y) * 1e8, lots=int(l)) for c, l, y in rows if str(c).startswith("00") and float(y) > 0]
    return sorted(rs, key=lambda r: -r["amt"])[:n]


def b_etf_buy(mode, w, h, ctx):
    j = ctx["jget"]("inst_today")
    nm = _stock_names(ctx)
    secs = []
    for side, title in (("foreign", "外資 ETF 買超"), ("trust", "投信 ETF 買超")):
        rows = etf_buy(j, side, 5, nm)      # 各前 5 名（2026-10-26 Andy：「買超各只要前五名即可」）
        mx = max([abs(r["amt"]) for r in rows] + [1])
        secs.append((title, T["rise"], [dict(code=r["code"], name=r["name"], frac=abs(r["amt"]) / mx, val=sgn(r["amt"] / 1e8, 2), unit="億", lots=r["lots"]) for r in rows]))
    return rank_list(mode, w, h, ctx, secs, vw=round(150 * S_(mode)))


def _stock_names(ctx) -> dict:
    if "_names" not in ctx:
        st = ctx["jget"]("stocks") or []
        ctx["_names"] = {str(r.get("code")): r.get("name") for r in (st if isinstance(st, list) else []) if r.get("code") and r.get("name")}
    return ctx["_names"]


def _streak(side):
    def b(mode, w, h, ctx):
        j = ctx["jget"]("inst_today")
        buy, sell = inst_top(j, side, 10, dict(_stock_names(ctx)))
        s = S_(mode)
        secs = []
        for rows, title, col in ((buy, "當日買超", T["rise"]), (sell, "當日賣超", T["fall"])):
            mx = max([abs(r["amt"]) for r in rows] + [1])
            secs.append((title, col, [dict(code=r["code"], name=r["name"], frac=abs(r["amt"]) / mx,
                                           val=sgn(r["amt"] / 1e8, 1), unit="億", lots=r["lots"]) for r in rows]))
        return rank_list(mode, w, h, ctx, secs, vw=round(150 * s))
    return b


def _credit(which):
    def b(mode, w, h, ctx):
        m = ctx["jget"]("market_fut")["margin"]
        up, dn = credit_top(m, which)      # 只列個股（排除 ETF）
        mx = max([abs(r["chg"]) for r in up + dn] + [1])
        what = "融券" if which == "short" else "融資"
        mk = lambda rs: [dict(code=r["code"], name=r["name"], frac=abs(r["chg"]) / mx, val=sgn(r["chg"] / 1000, 2), unit="千張") for r in rs]
        return rank_list(mode, w, h, ctx, [(f"{what}增加 Top 8", T["rise"], mk(up)), (f"{what}減少 Top 8", T["fall"], mk(dn))], vw=round(170 * S_(mode)))
    return b


# ---- 三大法人買賣超
def b_inst_today(mode, w, h, ctx):
    rows = ctx["jget"]("inst_market")["rows"]
    vals = []
    for r in rows:
        rv = r.get("rev") or {}
        vals.append(dict(d=r["d"], f=rv.get("f", r["f"]), t=rv.get("t", r["t"]), dl=rv.get("dl", r["dl"]), tot=rv.get("tot", r["tot"]), tw=r["tw"]))
    yr = vals[-1]["d"][:4]
    ytd = [v for v in vals if v["d"][:4] == yr]
    last = vals[-1]
    s = S_(mode)
    ks = []
    for lab, key in (("外資", "f"), ("投信", "t"), ("自營商", "dl"), ("合計", "tot")):
        v = last[key]
        acc = sum(x[key] for x in ytd)
        c = tone(v)
        ks.append(f'<div class="k sub"><div class=l>{lab}</div><div class=vv style="color:{c}">{sgn(v, 1)}<u>億</u></div>'
                  f'<div class=ss>年累積 <span style="color:{tone(acc)}">{sgn(acc, 0)}</span></div></div>')
    cols = "repeat(4,minmax(0,1fr))" if mode == "threads" else "repeat(2,minmax(0,1fr))"
    kh = round(150 * s) if mode == "threads" else round(150 * s) * 2 + 10
    chart_h = h - kh - 10
    d = vals[-21:]
    svg = _inst_chart(w, chart_h - round(50 * s), d, round(25 * s), mode)
    return (f'<div class=kp style="grid-template-columns:{cols}">{"".join(ks)}</div>'
            f'<div class="sub" style="margin-top:10px;height:{chart_h}px"><div class=ptitle>每日買賣超與加權指數<span class=rt>左 億元　右 點</span></div>{svg}</div>')


def _inst_chart(W, H, d, fs, mode):
    L, Rr, Tp, B = 100, 118, 64, 50      # 上留 64：最上面的刻度字不貼圖例
    pw, ph = W - L - Rr, H - Tp - B
    ups = [max(0, x["f"]) + max(0, x["t"]) + max(0, x["dl"]) for x in d]
    dns = [min(0, x["f"]) + min(0, x["t"]) + min(0, x["dl"]) for x in d]
    top = max(ups + [1]); bot = min(dns + [-1])
    stp = 500      # 左軸固定每 500 億一格，每格有虛線對應（2026-10-26 Andy：「旁邊的刻度 500 為單位，並且有虛線對應」）
    # 刻度先用原始範圍定，再上下各留 2% 取整：最高／最低那根不貼圖框（2026-10-26 Andy：「圖表不要出現被截圖狀況」，−4,000 那根壓在底線上）
    pad_ = (top - bot) * .02
    hi, lo = math.ceil((top + (pad_ if top > 1 else 0)) / stp) * stp, math.floor((bot - pad_) / stp) * stp
    Y = lambda v: Tp + (hi - v) / (hi - lo) * ph
    tws = [x["tw"] for x in d]
    tp_ = (max(tws) - min(tws)) * .06 or 50      # 加權指數同樣留白：最後一點不貼著底線
    t_lo = math.floor((min(tws) - tp_) / 500) * 500; t_hi = math.ceil((max(tws) + tp_) / 500) * 500
    I = lambda v: Tp + (t_hi - v) / (t_hi - t_lo) * ph
    g = [svg_open(W, H)]
    lx = 10
    for nm, col, kind in (("外資", TH.INST["外資"], "b"), ("投信", TH.INST["投信"], "b"), ("自營商", TH.INST["自營商"], "b"), ("加權指數", TH.INST["加權指數"], "l")):
        if kind == "b":
            g.append(f'<rect x="{lx}" y="14" width="24" height="24" rx="5" fill="{col}"/>')
        else:
            g.append(f'<line x1="{lx}" x2="{lx + 28}" y1="26" y2="26" stroke="{col}" stroke-width="4" stroke-linecap="round"/>')
        g.append(svg_t(lx + 36, 34, nm, fs, T["ink2"]))
        lx += 36 + est_w(nm, fs) + 26
    v = lo
    while v <= hi + 1e-6:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{T["line2"]}" stroke-width="{2 if v == 0 else 1.2}"{"" if v == 0 else ' stroke-dasharray="6 6"'}/>')      # 刻度對應虛線（0 軸實線），2026-10-26 Andy
        g.append(svg_t(L - 10, Y(v) + fs * .35, f'{"−" if v < 0 else ""}{abs(v):,.0f}', fs, T["ink3"], "end"))
        v += stp
    tv = t_lo
    while tv <= t_hi:
        g.append(svg_t(W - Rr + 10, I(tv) + fs * .35, f"{tv:,.0f}", fs, T["ink3"]))
        tv += 500 if (t_hi - t_lo) <= 3000 else 1000
    n = len(d); st = pw / n; bw = st * .62
    for i, x in enumerate(d):
        bx = L + st * i + (st - bw) / 2; pos = neg = 0
        for val, col in ((x["f"], TH.INST["外資"]), (x["t"], TH.INST["投信"]), (x["dl"], TH.INST["自營商"])):
            if val >= 0:
                y0, y1 = Y(pos), Y(pos + val); pos += val
            else:
                y0, y1 = Y(neg), Y(neg + val); neg += val
            g.append(f'<rect x="{bx:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{max(abs(y1 - y0), 1.5):.1f}" fill="{col}" rx="2"/>')
        if i % 4 == 0 or i == n - 1:
            md = x["d"][5:].replace("-", "/")
            g.append(svg_t(bx + bw / 2, H - 14, md, fs - 1, T["ink3"], "middle" if i not in (0, n - 1) else ("start" if i == 0 else "end")))
    pts = " ".join(f"{L + st * i + st / 2:.1f},{I(x['tw']):.1f}" for i, x in enumerate(d))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{TH.INST["加權指數"]}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
    g.append(f'<circle cx="{L + st * (n - 1) + st / 2:.1f}" cy="{I(d[-1]["tw"]):.1f}" r="8" fill="{TH.INST["加權指數"]}" stroke="{T["panel"]}" stroke-width="3"/>')
    g.append("</svg>")
    return "".join(g)


# ---- 台指期三大法人未平倉
def _bars_svg(W, H, vals, dates, fs, pos_col=None, ypad=0.08, month_labels=True, fmt=None):
    L, Rr, Tp, B = 92, 12, 12, 40
    pw, ph = W - L - Rr, H - Tp - B
    hi, lo = max(vals + [0]), min(vals + [0])
    sp = (hi - lo) or 1
    hi += sp * ypad; lo -= sp * ypad if lo < 0 else 0
    if min(vals) >= 0:
        lo = 0
    Y = lambda v: Tp + (hi - v) / (hi - lo) * ph
    raw = (hi - lo) / 4
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    stp = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    g = [svg_open(W, H)]
    v = math.ceil(lo / stp) * stp
    while v <= hi:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{T["line2"]}" stroke-width="{2 if v == 0 else 1.2}"{"" if v == 0 else ' stroke-dasharray="6 6"'}/>')      # 刻度對應虛線（0 軸實線），2026-10-26 Andy
        lab = fmt(v) if fmt else (f'{"−" if v < 0 else ""}{abs(v) / 10000:g}萬' if abs(v) >= 10000 else f'{"−" if v < 0 else ""}{abs(v):g}')
        g.append(svg_t(L - 8, Y(v) + fs * .35, lab, fs, T["ink3"], "end"))
        v += stp
    n = len(vals); st = pw / n; bw = max(2.0, st * .66)
    for i, x in enumerate(vals):
        col = pos_col or (T["rise"] if x >= 0 else T["fall"])
        y0, y1 = Y(0), Y(x)
        g.append(f'<rect x="{L + st * i + (st - bw) / 2:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{max(abs(y1 - y0), 1.2):.1f}" fill="{col}"/>')
    for i in sorted({0, n // 3, 2 * n // 3, n - 1}):
        an = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        g.append(svg_t(L + st * i + st / 2, H - 10, dates[i][5:].replace("-", "/"), fs, T["ink3"], an))
    return g


def b_fut_oi(mode, w, h, ctx):
    """三張面板：標題列（身分＋淨未平倉）→ 每日淨未平倉長條 → 多空比例條（照網站總覽「漲跌家數」那種：細長比例條＋兩端百分比與口數）。
    2026-10-26 Andy：「上方多空比用圖二方式呈現，長條比例圖新增在下方」→ 拿掉最上面的總覽，多空口數改成每張面板下方的比例條。"""
    j = ctx["jget"]("fut_oi")
    s = S_(mode)
    dates = j["dates"][-126:]
    pn = []
    n = 3
    ud_h = round(104 * s)       # 比例條區高度
    ph = (h - 10 * (n - 1)) / n
    for i, (key, lab) in enumerate((("foreign", "外資"), ("trust", "投信"), ("dealer", "自營商"))):
        net = [float(x) if x is not None else 0.0 for x in j[key]["net"][-126:]]
        last = net[-1]
        lg, sh = float(j[key]["long"][-1]), float(j[key]["short"][-1])
        tot = (lg + sh) or 1
        pl, ps = lg / tot * 100, sh / tot * 100
        svg = "".join(_bars_svg(w - 6, ph - round(74 * s) - ud_h, net, dates, round(24 * s))) + "</svg>"
        lf, nf = round(24 * s), round(34 * s)
        ud = (f'<div style="height:{ud_h}px;padding:6px 12px 0;border-top:1px dashed var(--line)">'
              f'<div style="display:flex;height:{round(10 * s)}px;border-radius:5px;overflow:hidden;margin-top:6px">'
              f'<span style="width:{pl:.2f}%;background:{T["rise"]};opacity:.85"></span><span style="flex:1;background:{T["fall"]};opacity:.85"></span></div>'
              f'<div style="display:flex;justify-content:space-between;margin-top:6px;line-height:1.25">'
              f'<div><div style="font-size:{lf}px;color:var(--ink2)">多單 <span style="font-family:{NUMF}">{pl:.1f}%</span></div>'
              f'<div style="font-size:{nf}px;font-weight:800;color:{T["rise"]};font-family:{NUMF}">{lg:,.0f}<small style="font-size:{lf}px;font-weight:600;color:var(--ink2);margin-left:4px">口</small></div></div>'
              f'<div style="text-align:right"><div style="font-size:{lf}px;color:var(--ink2)">空單 <span style="font-family:{NUMF}">{ps:.1f}%</span></div>'
              f'<div style="font-size:{nf}px;font-weight:800;color:{T["fall"]};font-family:{NUMF}">{sh:,.0f}<small style="font-size:{lf}px;font-weight:600;color:var(--ink2);margin-left:4px">口</small></div></div>'
              f'</div></div>')
        pn.append(f'<div class=sub style="height:{ph:.0f}px;{"margin-top:10px;" if i else ""}display:flex;flex-direction:column">'
                  f'<div class=ptitle>{lab} 每日淨未平倉（口）<span class=rt style="font-size:{round(36 * s)}px;font-weight:800;color:{tone(last)}">{sgn(last, 0)}</span></div>{svg}{ud}</div>')
    return "".join(pn)


# ---- 散戶多空比
def b_retail(mode, w, h, ctx):
    j = ctx["jget"]("retail_ratio")["products"]
    s = S_(mode)
    n = 3
    ph = (h - 10 * (n - 1)) / n
    out = []
    names = {"TX": "大台（TX）", "MTX": "小台（MTX）", "TMF": "微台（TMF）"}
    for k in ("TX", "MTX", "TMF"):
        p = j[k]
        dates, ratio, tw = p["dates"][-126:], p["ratio_pct"][-126:], p["taiex"][-126:]
        last, prev = ratio[-1], (ratio[-2] if len(ratio) > 1 else ratio[-1])
        svg = _dual_svg(w - 6, ph - round(70 * s), dates, bars=ratio, line=tw, fs=round(24 * s))
        out.append(f'<div class=sub style="height:{ph:.0f}px"><div class=ptitle><i style="color:{tone(last)}">{sgn(last, 2, "%")}</i>{names[k]}<em>較前日 {sgn(last - prev, 2, "pp")}</em></div>{svg}</div>')
    return '<div style="display:flex;flex-direction:column;gap:10px;height:100%">' + "".join(out) + "</div>"


def _dual_svg(W, H, dates, bars, line, fs, bar_col=None):
    """左軸：長條（百分比）；右軸：加權指數折線"""
    L, Rr, Tp, B = 84, 108, 10, 40
    pw, ph = W - L - Rr, H - Tp - B
    hi, lo = max(bars + [0]), min(bars + [0])
    sp = (hi - lo) or 1
    hi += sp * .06; lo -= sp * .06 if lo < 0 else 0
    if min(bars) >= 0:
        lo = 0
    Y = lambda v: Tp + (hi - v) / (hi - lo) * ph
    tlo, thi = min(line), max(line); ts = (thi - tlo) or 1; tlo -= ts * .05; thi += ts * .05
    I = lambda v: Tp + (thi - v) / (thi - tlo) * ph
    g = [svg_open(W, H)]
    raw = (hi - lo) / 4; mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    stp = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    v = math.ceil(lo / stp) * stp
    while v <= hi:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{T["line2"]}" stroke-width="{2 if v == 0 else 1.2}"{"" if v == 0 else ' stroke-dasharray="6 6"'}/>')      # 刻度對應虛線（0 軸實線），2026-10-26 Andy
        g.append(svg_t(L - 8, Y(v) + fs * .35, f'{"−" if v < 0 else ""}{abs(v):g}%', fs, T["ink3"], "end"))
        v += stp
    traw = (thi - tlo) / 4; tm = 10 ** math.floor(math.log10(traw)); tstp = next(m * tm for m in (1, 2, 2.5, 5, 10) if m * tm >= traw)
    tv = math.ceil(tlo / tstp) * tstp
    while tv <= thi:
        g.append(svg_t(W - Rr + 8, I(tv) + fs * .35, f"{tv:,.0f}", fs, T["ink3"]))
        tv += tstp
    n = len(bars); st = pw / n; bw = max(2.0, st * .66)
    for i, x in enumerate(bars):
        y0, y1 = Y(0), Y(x)
        g.append(f'<rect x="{L + st * i + (st - bw) / 2:.1f}" y="{min(y0, y1):.1f}" width="{bw:.1f}" height="{max(abs(y1 - y0), 1.2):.1f}" fill="{bar_col or T["accent"]}" opacity=".8"/>')
    pts = " ".join(f"{L + st * i + st / 2:.1f},{I(x):.1f}" for i, x in enumerate(line))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{T["ink"]}" stroke-width="3.5" stroke-linejoin="round"/>')
    for i in sorted({0, n // 3, 2 * n // 3, n - 1}):
        an = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        g.append(svg_t(L + st * i + st / 2, H - 10, dates[i][5:].replace("-", "/"), fs, T["ink3"], an))
    g.append("</svg>")
    return "".join(g)


# ---- 融資維持率
def b_credit_ratio(mode, w, h, ctx):
    rows = ctx["jget"]("market_fut")["margin"]["rows"]
    rows = [r for r in rows if r.get("ratio") is not None and r.get("taiex")][-150:]
    s = S_(mode)
    last, prev = rows[-1], rows[-2]
    dpp = last["ratio"] - prev["ratio"]
    ph = (h - 10) / 2
    dates = [r["d"] for r in rows]
    c1 = _line_dual(w - 6, ph - round(72 * s), dates, [r["ratio"] for r in rows], [r["taiex"] for r in rows], round(24 * s), T["rise"], pct=True, ref=130)
    c2 = _line_dual(w - 6, ph - round(72 * s), dates, [r["margin_yi"] for r in rows], [r["taiex"] for r in rows], round(24 * s), "#0EA5E9", pct=False)
    return (f'<div class=sub style="height:{ph:.0f}px;margin-bottom:10px"><div class=ptitle><i style="color:{tone(dpp)}">{last["ratio"]:.2f}%</i>融資維持率（估）<em>較前日 {sgn(dpp, 2, "pp")}</em></div>{c1}</div>'
            f'<div class=sub style="height:{ph:.0f}px"><div class=ptitle><i>{last["margin_yi"]:,.0f}</i>融資餘額（億元）<em>{sgn(last["margin_yi"] - prev["margin_yi"], 0, "億")}</em></div>{c2}</div>')


def _line_dual(W, H, dates, left, right, fs, lcol, pct=True, ref=None):
    L, Rr, Tp, B = 92, 108, 10, 40
    pw, ph = W - L - Rr, H - Tp - B
    lo, hi = min(left + ([ref] if ref else [])), max(left)
    sp = (hi - lo) or 1; lo -= sp * .06; hi += sp * .06
    Y = lambda v: Tp + (hi - v) / (hi - lo) * ph
    tlo, thi = min(right), max(right); ts = (thi - tlo) or 1; tlo -= ts * .05; thi += ts * .05
    I = lambda v: Tp + (thi - v) / (thi - tlo) * ph
    g = [svg_open(W, H)]

    def ticks(a, b, f, x, anchor):
        raw = (b - a) / 4; mag = 10 ** math.floor(math.log10(raw)); stp = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
        v = math.ceil(a / stp) * stp
        while v <= b:
            yield v, f(v)
            v += stp
    for v, y in ticks(lo, hi, Y, 0, ""):
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{T["line"]}" stroke-width="1.2"/>')
        g.append(svg_t(L - 8, Y(v) + fs * .35, f"{v:,.0f}" + ("%" if pct else ""), fs, T["ink3"], "end"))
    for v, y in ticks(tlo, thi, I, 0, ""):
        g.append(svg_t(W - Rr + 8, I(v) + fs * .35, f"{v:,.0f}", fs, T["ink3"]))
    if ref:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(ref):.1f}" y2="{Y(ref):.1f}" stroke="{T["amber"]}" stroke-width="2.5" stroke-dasharray="8 6"/>')
        g.append(svg_t(W - Rr - 6, Y(ref) - 8, f"{ref}%", fs, T["amber"], "end", 700))
    n = len(left); st = pw / (n - 1)
    pr = " ".join(f"{L + st * i:.1f},{I(x):.1f}" for i, x in enumerate(right))
    pl = " ".join(f"{L + st * i:.1f},{Y(x):.1f}" for i, x in enumerate(left))
    g.append(f'<polyline points="{pr}" fill="none" stroke="{T["ink"]}" stroke-width="3" stroke-linejoin="round" opacity=".75"/>')
    g.append(f'<polyline points="{pl}" fill="none" stroke="{lcol}" stroke-width="4" stroke-linejoin="round"/>')
    for i in sorted({0, n // 3, 2 * n // 3, n - 1}):
        an = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        g.append(svg_t(L + st * i, H - 10, dates[i][5:].replace("-", "/"), fs, T["ink3"], an))
    g.append("</svg>")
    return "".join(g)


# ---- 大盤走勢（三張分時線）
def b_market_index(mode, w, h, ctx):
    d = ctx.get("dump") or {}
    panels = d.get("panels") or []
    s = S_(mode)
    n = len(panels) or 1
    ph = (h - 10 * (n - 1)) / n
    out = []
    for p in panels:
        xs, ys, pc = p["x"], p["y"], p.get("prev")
        chg = p.get("chg", 0)
        c = tone(chg)
        svg = _intraday_svg(w - 6, ph - round(74 * s), xs, ys, pc, round(24 * s), c)
        out.append(f'<div class=sub style="height:{ph:.0f}px"><div class=ptitle><i style="color:{c}">{esc(p["price"])}</i>{esc(p["name"])}<em style="color:{c}">{esc(p["chgtxt"])}</em></div>{svg}</div>')
    return '<div style="display:flex;flex-direction:column;gap:10px;height:100%">' + "".join(out) + "</div>"


def _intraday_svg(W, H, xs, ys, prev, fs, col):
    L, Rr, Tp, B = 12, 112, 10, 40
    pw, ph = W - L - Rr, H - Tp - B
    vals = [v for v in ys if v is not None]
    lo, hi = min(vals + ([prev] if prev else [])), max(vals + ([prev] if prev else []))
    sp = (hi - lo) or 1; lo -= sp * .08; hi += sp * .08
    Y = lambda v: Tp + (hi - v) / (hi - lo) * ph
    n = len(ys)
    X = lambda i: L + pw * i / max(n - 1, 1)
    g = [svg_open(W, H)]
    raw = (hi - lo) / 4; mag = 10 ** math.floor(math.log10(raw)); stp = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    v = math.ceil(lo / stp) * stp
    while v <= hi:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{T["line"]}" stroke-width="1.2"/>')
        g.append(svg_t(W - Rr + 8, Y(v) + fs * .35, f"{v:,.{0 if stp >= 1 else 1}f}", fs, T["ink3"]))
        v += stp
    pts = [(X(i), Y(y)) for i, y in enumerate(ys) if y is not None]
    area = f"{pts[0][0]:.1f},{Tp + ph:.1f} " + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" {pts[-1][0]:.1f},{Tp + ph:.1f}"
    g.append(f'<polygon points="{area}" fill="{col}" opacity=".10"/>')
    g.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="3.5" stroke-linejoin="round"/>')
    if prev:
        g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Y(prev):.1f}" y2="{Y(prev):.1f}" stroke="{T["ink3"]}" stroke-width="2" stroke-dasharray="7 6"/>')
        g.append(svg_t(L + 4, Y(prev) - 8, f"昨收 {prev:,.2f}".rstrip("0").rstrip("."), fs, T["ink3"], weight=600))
    g.append(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="7" fill="{col}"/>')
    ticks = [xs[0], xs[len(xs) // 2], xs[-1]]
    for i, t in zip((0, len(xs) // 2, len(xs) - 1), ticks):
        g.append(svg_t(X(i), H - 10, t, fs, T["ink3"], "start" if i == 0 else ("end" if i == len(xs) - 1 else "middle")))
    g.append("</svg>")
    return "".join(g)


# ---- 漲跌家數（分佈直方圖）
def b_market_breadth(mode, w, h, ctx):
    d = ctx.get("dump") or {}
    cats, vals = d.get("cats") or [], d.get("vals") or []
    if not vals:
        return ""
    s = S_(mode)
    up = sum(v for c, v in zip(cats, vals) if _cat_sign(c) > 0)
    dn = sum(v for c, v in zip(cats, vals) if _cat_sign(c) < 0)
    flat = sum(vals) - up - dn
    # 2026-10-26：三格改用網站同一份官方家數（market_heat.json；網站總覽「漲跌家數」也是它）。
    # 原本用直方圖分箱加總，-2~0 那箱含平盤，平盤變 0、跟文案「上漲 530、下跌 1620」對不起來
    mh = (ctx.get("jget") or (lambda n: {}))("market_heat") or {}
    if mh.get("advancers") is not None and mh.get("decliners") is not None:
        up, dn, flat = int(mh["advancers"]), int(mh["decliners"]), int(mh.get("unchanged") or 0)
    tot = (up + dn + flat) or 1
    kp = "".join(
        f'<div class="k sub"><div class=l>{lab}</div><div class=vv style="color:{c}">{v:,}<u>檔</u></div><div class=ss>{v / tot * 100:.1f}%</div></div>'
        for lab, v, c in (("上漲", up, T["rise"]), ("平盤", flat, T["flat"]), ("下跌", dn, T["fall"])))
    kh = round(150 * s)
    svg = _hist_svg(w - 6, h - kh - round(56 * s) - 10, cats, vals, round(24 * s))
    stat = esc(d.get("stat", ""))
    return (f'<div class=kp style="grid-template-columns:repeat(3,minmax(0,1fr))">{kp}</div>'
            f'<div class=sub style="margin-top:10px;height:{h - kh - 10}px"><div class=ptitle>漲跌分佈<em>{stat}</em></div>{svg}</div>')


def _cat_sign(c: str) -> int:
    c = str(c).replace(" ", "")
    if c in ("平", "0"):
        return 0
    m = re.search(r"-?\d+(\.\d+)?", c)
    if "≥" in c or c.startswith(">") or "漲停" in c:
        return 1
    if "≤" in c or c.startswith("<") or "跌停" in c:
        return -1
    if m and c.startswith("-"):
        return -1
    return 1 if m else 0


def _hist_svg(W, H, cats, vals, fs):
    L, Rr, Tp, B = 12, 12, 40, 110
    pw, ph = W - L - Rr, H - Tp - B
    mx = max(vals + [1])
    n = len(vals); st = pw / n; bw = st * .72
    g = [svg_open(W, H)]
    g.append(f'<line x1="{L}" x2="{W - Rr}" y1="{Tp + ph}" y2="{Tp + ph}" stroke="{T["line2"]}" stroke-width="2"/>')
    for i, (c, v) in enumerate(zip(cats, vals)):
        sg = _cat_sign(c)
        col = T["rise"] if sg > 0 else (T["fall"] if sg < 0 else T["flat"])
        bh = v / mx * ph
        x = L + st * i + (st - bw) / 2
        g.append(f'<rect x="{x:.1f}" y="{Tp + ph - bh:.1f}" width="{bw:.1f}" height="{max(bh, 1.5):.1f}" rx="4" fill="{col}" opacity=".85"/>')
        g.append(svg_t(x + bw / 2, Tp + ph - bh - 8, f"{v:,}", fs + 2, T["ink"], "middle", 700, True))
        lx, ly = x + bw / 2, Tp + ph + 14
        g.append(f'<g transform="translate({lx:.1f},{ly:.1f}) rotate(-45)">{svg_t(0, 0, str(c).replace(" ", ""), fs, T["ink2"], "end")}</g>')
    g.append("</svg>")
    return "".join(g)


# ---- 資金分流樹（流入前五／流出前五＋簡化樹）
def b_sankey(mode, w, h, ctx):
    d = ctx.get("dump") or {}
    s = S_(mode)
    secs = []
    for key, title, col in (("in", "資金流入前五", T["rise"]), ("out", "資金流出前五", T["fall"])):
        rows = (d.get(key) or [])[:5]
        secs.append((title, col, rows))
    head = d.get("head") or ""
    hh = round(64 * s) if mode == "threads" else round(100 * s)
    avail = h - hh - 10
    out = [f'<div class=ptitle style="height:{hh}px;white-space:normal;font-size:{round(28 * s)}px;line-height:1.3">{esc(head)}</div>']
    for title, col, rows in secs:
        out.append(_tree_block(title, col, rows, w, (avail - 10) / 2, s))
    return '<div style="display:flex;flex-direction:column;gap:10px;height:100%">' + "".join(out) + "</div>"


def _tree_block(title, col, rows, w, h, s):
    f = round(30 * s)
    th = round(46 * s)
    rh = (h - th - 8) / max(len(rows), 1)
    mx = max([abs(r["dpp"]) for r in rows] + [0.01])
    # 鏈 → 族群：同一條產業鏈的列相鄰，左邊用括線連到鏈名（兩層簡化樹）
    # 只把「相鄰」的同鏈列併成一組：排行是依 pp 排序，同一條鏈可能被隔開；不相鄰還硬併，兩個鏈名會疊在同一個位置（2026-10-27 盤中分流樹「其他電子」壓到「傳產與內需」）
    runs: list = []
    for i, r in enumerate(rows):
        if runs and runs[-1][0] == r["chain"]:
            runs[-1][1].append(i)
        else:
            runs.append((r["chain"], [i]))
    cw = round(150 * s)
    g = [svg_open(w, h), svg_t(8, th - 12, title, f + 2, col, weight=800)]
    root_x, chain_x = 8, 24
    for ch, idxs in runs:
        ys = [th + rh * (i + 0.5) for i in idxs]
        cy = sum(ys) / len(ys)
        tot = sum(rows[i]["amt"] for i in idxs)
        g.append(f'<rect x="{chain_x}" y="{cy - 26 * s:.1f}" width="{cw}" height="{52 * s:.0f}" rx="8" fill="{col}" opacity=".12" stroke="{col}" stroke-width="1.5"/>')
        g.append(svg_t(chain_x + cw / 2, cy + 9 * s, ell(ch, round(26 * s), cw - 12), round(26 * s), T["ink"], "middle", 700))
        for y in ys:
            g.append(f'<path d="M{chain_x + cw:.1f},{cy:.1f} C{chain_x + cw + 24:.1f},{cy:.1f} {chain_x + cw + 24:.1f},{y:.1f} {chain_x + cw + 48:.1f},{y:.1f}" fill="none" stroke="{col}" stroke-width="2.5" opacity=".7"/>')
    x1 = chain_x + cw + 56
    vwid = round(120 * s) + 100
    nmw = round(w * 0.30)
    bx0 = x1 + nmw + 10
    bw_all = w - bx0 - vwid - 6
    for i, r in enumerate(rows):
        cy = th + rh * (i + 0.5)
        g.append(f'<circle cx="{x1 - 8:.1f}" cy="{cy:.1f}" r="7" fill="{col}"/>')
        g.append(svg_t(x1 + 6, cy + f * .35, ell(r["name"], f, nmw), f, T["ink"], weight=800))
        bwid = abs(r["dpp"]) / mx * bw_all
        g.append(f'<rect x="{bx0:.1f}" y="{cy - 14 * s:.1f}" width="{max(bwid, 4):.1f}" height="{28 * s:.0f}" rx="6" fill="{col}" opacity=".85"/>')
        g.append(svg_t(w - 6, cy - 6, f'{sgn(r["dpp"], 2)} pp', f, col, "end", 800, True))
        g.append(svg_t(w - 6, cy + round(30 * s), f'占 {r["share"]:.1f}%・{r["amt"]:,.0f}億', round(24 * s), T["ink2"], "end", 600, True))
    g.append("</svg>")
    return f'<div class=sub style="height:{h:.0f}px">{"".join(g)}</div>'


# ---- 限動結尾頁（2026-10-26 Andy 選 C：IG 限動 API 不能加連結貼紙 → 最後一張請讀者點個人簡介連結；圖上不放網址）
def b_outro(mode, w, h, ctx):
    s = S_(mode)
    big, mid = round(76 * s), round(40 * s)
    arrow = (f'<svg data-box="arrow" width="{round(150 * s)}" height="{round(150 * s)}" viewBox="0 0 100 100">'
             f'<circle cx="50" cy="50" r="46" fill="none" stroke="{T["cyan"]}" stroke-width="4"/>'
             f'<path d="M50 72V30M32 47l18-18 18 18" fill="none" stroke="{T["cyan"]}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return (f'<div class=sub style="height:{h:.0f}px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:{round(44 * s)}px;text-align:center">'
            f'{arrow}<div data-box="t1" style="font-size:{big}px;font-weight:800;line-height:1.25">看完整資料</div>'
            f'<div data-box="t2" style="font-size:{mid}px;font-weight:700;color:{T["ink2"]};line-height:1.5">點個人簡介的連結<br>進入網站看即時更新</div></div>')


BUILDERS = {
    "outro": b_outro,
    "etf-buy": b_etf_buy,
    "rotation-rank": b_rotation_rank,
    "sankey-tree": b_sankey,
    "market-index": b_market_index,
    "market-breadth": b_market_breadth,
    "inst-today": b_inst_today,
    "streak-foreign": _streak("foreign"),
    "streak-trust": _streak("trust"),
    "fut-oi": b_fut_oi,
    "retail-ratio": b_retail,
    "credit-ratio": b_credit_ratio,
    "credit-rank": _credit("rank"),
    "credit-short": _credit("short"),
}
NATIVE = set(BUILDERS)

# ------------------------------------------------------------------ 截圖瀏覽器端的資料讀取（social_snap 在套上即時資料的頁面上呼叫）
DUMP_JS = {
    "rotation-rank": """() => { const e = document.getElementById('rankFlow'); const c = e && window.echarts && echarts.getInstanceByDom(e); if (!c) return {};
      const o = c.getOption(); return { names: (o.yAxis[0].data || []).slice(), vals: (o.series[0].data || []).map(d => (typeof d === 'object' ? d.value : d)) }; }""",
    "market-index": """() => { const out = []; document.querySelectorAll('#m3Frame .m3-card').forEach((card) => {
      const el = card.querySelector('[_echarts_instance_]'); const c = el && window.echarts && echarts.getInstanceByDom(el); if (!c) return;
      const o = c.getOption(); const s = o.series.find(x => x.type === 'line') || o.series[0];
      const ml = s.markLine && s.markLine.data && s.markLine.data[0]; const t = card.innerText.replace(/\\s+/g, ' ').trim();
      const m = /^(\\S+).*?([\\d,]+(?:\\.\\d+)?)\\s+([+\\-−]?[\\d,.]+)\\s+([+\\-−]?[\\d.]+%)/.exec(t.replace(/展開 ⤢/, '').replace(/日盤|夜盤/, ''));
      const chg = m ? parseFloat(m[3].replace('−', '-').replace(/,/g, '')) : 0;
      out.push({ name: m ? m[1] : t.slice(0, 4), price: m ? m[2] : '', chgtxt: m ? m[3].replace('-', '−') + '  ' + m[4].replace('-', '−') : '', chg,
        x: (o.xAxis[0].data || []).slice(), y: (s.data || []).map(v => (v == null ? null : (typeof v === 'object' ? v.value : v))), prev: ml ? ml.yAxis : null }); });
      return { panels: out }; }""",
    "market-breadth": """() => { const e = document.getElementById('chgDist'); const c = e && window.echarts && echarts.getInstanceByDom(e); if (!c) return {};
      const o = c.getOption(); const root = e.closest('.mktdist') || document; const t = root.innerText.replace(/\\s+/g, ' ');
      const m = /(\\d[\\d,]*)\\s*檔\\s*平均\\s*([+\\-−]?[\\d.]+%)\\s*標準差\\s*([\\d.]+%)/.exec(t);
      return { cats: (o.xAxis[0].data || []).slice(), vals: (o.series[0].data || []).map(d => (typeof d === 'object' ? d.value : d)), stat: m ? m[1] + ' 檔・平均 ' + m[2] + '・標準差 ' + m[3] : '' }; }""",
    "sankey-tree": """async () => { const wait = (ms) => new Promise(r => setTimeout(r, ms)); const read = () => [...document.querySelectorAll('#sankeyRank .skr-r')].map(r => {
        const b = r.querySelector('.d'); const sm = r.querySelector('.v small'); const m = /占\\s*([\\d.]+)%.*?([\\d,.]+)\\s*億/.exec(sm ? sm.textContent : '') || [];
        return { name: (r.querySelector('.n b') || {}).textContent || '', chain: (r.querySelector('.n small') || {}).textContent || '', dpp: parseFloat(b ? b.dataset.dpp : '0') || 0,
          share: parseFloat(m[1] || '0'), amt: parseFloat((m[2] || '0').replace(/,/g, '')) }; });
      const out = {}; const note = (document.querySelector('#sankeyRank .skr-s') || {}).textContent || '';
      for (const k of ['in', 'out']) { const btn = document.querySelector('#sankeyRank .skr-tab button[data-t="' + k + '"]'); if (btn) { btn.click(); await wait(500); } out[k] = read(); }
      out.head = note.replace(/資金占比/, '資金占比'); return out; }""",
}
