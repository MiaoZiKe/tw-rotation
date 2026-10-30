# 驗收段落「一致性普查1030」—— 2026-10-30 新增（外掛段落，見 _uitest.py「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、count()、text()、fails、SITE… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 一致性普查1030
# Andy 10-30 13:17：「總覽的資訊為何和熱力圖對不上 需要修正 並檢查其他資訊是否一樣狀況」。
# 起因：總覽「資金熱力圖」顏色依資金流向 pp、方塊文字卻混寫「資金 +0.4pp」與「漲跌 -4.4%」，跟熱力圖頁「整個台股一次看」（漲跌幅）同一族群顏色相反。
# 這一段在同一個資料日、同一個頁面工作階段，讀「同一份資訊在兩處顯示」的數字逐項比對：
#   ① 總覽資金熱力圖（預設）與熱力圖頁：同一族群的漲跌幅、成交值占比、顏色完全一致；整張圖的第二行只用一種指標（沒有「資金」「漲跌」混寫）
#   ② 總覽熱力圖切「資金流向」：整張一致寫「資金 ±x.xpp／資金 —」、圖例換 pp、不出現 %；切回來還原；偏好重新整理後還在（localStorage）
#   ③ 漲跌家數：總覽摘要卡＝總覽漲跌家數分佈卡＝市場明細標題（上漲／下跌各一個數字）
#   ④ 資金輪盤四段家數：總覽摘要卡＝資金輪動頁
#   ⑤ 熱門題材：總覽與熱力圖頁題材資金熱力的熱度／漲跌／占比逐題材一致
#   ⑥ 盤中即時：同一個瀏覽器工作階段從總覽切到熱力圖頁，兩張熱力圖同一族群的即時漲跌幅一致、即時鈕狀態一致
CS_LEAF = """(id) => { const el = document.getElementById(id); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return null;
  const o = {}; const w = (a) => (a || []).forEach(d => { if (d.children && d.children.length) w(d.children);
    else o[d.gid || d.id || d.name] = { chg: d.chg, rot: d.rot, share: d.share, color: (d.itemStyle && d.itemStyle.color) || '', lab: ((el._hmLab || {})[d.gid || d.id || d.name] || {}).text || '' }; });
  w(((i.getOption().series || [])[0] || {}).data); return o; }"""


def t_consistency_1030(b, base):
    import json as _json
    import re as _re
    import time as _time
    import datetime as _dt
    from urllib.parse import urlparse, parse_qs
    T = "一致性普查1030"

    def open_page(route, vp=None, clock=None, admin=False, fake=None):
        ctx = b.new_context(viewport=vp or {"width": 1440, "height": 1000}, timezone_id="Asia/Taipei")
        if admin:
            ctx.add_init_script("window.TW_LIVE_OVERRIDE = true;")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        if clock:
            pg.clock.install(time=clock)
        if fake:
            pg.route("https://fake-worker.test/**", lambda r: r.fulfill(status=404, content_type="application/json", body="{}"))
            pg.route("https://fake-worker.test/quote?*", fake)
            pg.goto(base + route, wait_until="domcontentloaded")
            pg.evaluate("() => { try { localStorage.clear(); localStorage.setItem('tw.live.proxy','https://fake-worker.test'); } catch (e) {} }")
            pg.goto("about:blank")
        pg.goto(base + route, wait_until="load")
        return ctx, pg

    def chart_ready(pg, sel):
        return wait_until(pg, f"() => !!document.querySelector('{sel} canvas, {sel} svg')", 25000)

    # ------------------------------------------------------------------ ① ② 總覽熱力圖 vs 熱力圖頁（盤後）
    ctx, pg = open_page("#overview")
    chart_ready(pg, "#heat"); pg.wait_for_timeout(1500)
    ov = pg.evaluate(CS_LEAF, "heat")
    ok(f"[{T}] ① 總覽資金熱力圖標題旁有「顏色：漲跌幅｜資金流向」分段開關，預設選「漲跌幅」",
       count(pg, "#heatMode button") == 2 and "漲跌幅" in text(pg, "#heatMode button.on"), text(pg, "#heatMode"))
    ok(f"[{T}] ① 圖例標題＝漲跌幅 (%)（跟熱力圖頁同一把尺）", "漲跌幅" in text(pg, "#heatLegend .hmttl"), text(pg, "#heatLegend .hmttl"))
    labs = [v["lab"] for v in (ov or {}).values() if v["lab"]]
    two = [s for s in labs if "\n" in s]
    ok(f"[{T}] ① ★ 整張圖第二行只用一種指標：寫了字的 {len(two)} 格都是漲跌幅（有 %），沒有任何「資金」「漲跌」字樣混寫",
       len(two) >= 5 and all(("%" in s.split("\n")[-1]) and "資金" not in s and "漲跌" not in s for s in two), two[:4])
    ctx2, pg2 = open_page("#heatmap/industry")
    chart_ready(pg2, "#indTree"); pg2.wait_for_timeout(1500)
    hm = pg2.evaluate(CS_LEAF, "indTree")
    common = [k for k in (ov or {}) if k in (hm or {})]
    d_chg = [k for k in common if abs((ov[k]["chg"] or 0) - (hm[k]["chg"] or 0)) > 0.005]
    d_share = [k for k in common if abs((ov[k]["share"] or 0) - (hm[k]["share"] or 0)) > 0.005]
    d_col = [k for k in common if ov[k]["color"] != hm[k]["color"]]
    ok(f"[{T}] ① ★ 總覽與熱力圖頁共有的 {len(common)} 個族群：漲跌幅一致", len(common) >= 40 and not d_chg, d_chg[:5])
    ok(f"[{T}] ① ★ 共有的族群：成交值占比一致", not d_share, d_share[:5])
    ok(f"[{T}] ① ★ 共有的族群：方塊顏色一致（同一族群不會一邊紅一邊綠）", not d_col, [(k, ov[k]["color"], hm[k]["color"]) for k in d_col[:3]])
    ctx2.close()
    # ② 切資金流向
    pg.click("#heatMode button[data-hm=flow]"); pg.wait_for_timeout(1500)
    fl = pg.evaluate(CS_LEAF, "heat")
    fl2 = [v["lab"] for v in (fl or {}).values() if "\n" in v["lab"]]
    ok(f"[{T}] ② 切「資金流向」：圖例換成資金流向 (pp)、分段鈕亮在資金流向", "資金流向" in text(pg, "#heatLegend .hmttl") and "資金流向" in text(pg, "#heatMode button.on"), text(pg, "#heatLegend .hmttl"))
    ok(f"[{T}] ② ★ 整張一致：第二行全是「資金 ±x.xpp」或「資金 —」，沒有 %、沒有「漲跌」", len(fl2) >= 5 and all(_re.search(r"資金 (?:[+\-−]?[\d.]+pp|—)$", s.split("\n")[-1]) and "漲跌" not in s and "%" not in s for s in fl2), fl2[:4])
    ok(f"[{T}] ② 切換後方塊顏色真的換了（不是只換字）", any(fl[k]["color"] != ov[k]["color"] for k in ov if k in fl))
    pg.reload(wait_until="load"); chart_ready(pg, "#heat"); pg.wait_for_timeout(1200)
    ok(f"[{T}] ② 偏好記在 localStorage：重新整理後仍是資金流向", "資金流向" in text(pg, "#heatMode button.on"), text(pg, "#heatMode button.on"))
    pg.click("#heatMode button[data-hm=chg]"); pg.wait_for_timeout(1200)
    back = pg.evaluate(CS_LEAF, "heat")
    ok(f"[{T}] ② 切回「漲跌幅」：顏色還原成跟熱力圖頁一致", all(back[k]["color"] == ov[k]["color"] for k in ov if k in back), None)
    # ③ 漲跌家數
    pg.goto(base + "#overview", wait_until="load"); pg.wait_for_timeout(5000)
    s3 = pg.evaluate("""() => { const t = (s) => ((document.querySelector(s) || {}).innerText || '').replace(/\\s+/g, ' ');
      const a = t('#ovSumTrack').match(/上漲\\s*[\\d.]+%\\s*(\\d[\\d,]*)\\s*平盤\\s*[\\d.]+%\\s*(\\d[\\d,]*)\\s*下跌\\s*[\\d.]+%\\s*(\\d[\\d,]*)/);
      const r = t('#ovSumTrack').match(/領先\\s*(\\d+)\\s*改善\\s*(\\d+)\\s*轉弱\\s*(\\d+)\\s*落後\\s*(\\d+)/);
      const c = t('#ovBreadthCard').match(/上漲\\s*([\\d,]+)\\s*家、下跌\\s*([\\d,]+)\\s*家、平盤\\s*([\\d,]+)\\s*家/);
      const n = (x) => x && x.slice(1).map(v => +String(v).replace(/,/g, ''));
      const cc = n(c); return { a: n(a), c: cc && [cc[0], cc[2], cc[1]], r: n(r) }; }   // 分佈卡文字順序是 上漲／下跌／平盤，換成跟摘要卡一樣的 上漲／平盤／下跌""")
    ctx3, pg3 = open_page("#market")
    wait_until(pg3, "() => /漲\\s*／/.test((document.getElementById('mktTitle') || {}).innerText || '')", 20000)
    m = _re.search(r"(\d[\d,]*)\s*漲／\s*(\d[\d,]*)\s*跌", text(pg3, "#mktTitle").replace("\n", " "))
    mk = [int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))] if m else None
    ok(f"[{T}] ③ 漲跌家數：總覽摘要卡（上漲／平盤／下跌）＝總覽漲跌家數分佈卡", bool(s3["a"]) and s3["a"] == s3["c"], s3)
    ok(f"[{T}] ③ ★ 漲跌家數：市場明細標題的「N 漲／M 跌」＝總覽摘要卡的上漲／下跌（以前差 ETF 那幾十檔）", bool(mk) and bool(s3["a"]) and mk == [s3["a"][0], s3["a"][2]], [mk, s3["a"]])
    # ④ 資金輪盤四段
    ctx4, pg4 = open_page("#flow")
    wait_until(pg4, "() => /領先\\s*\\d+/.test(document.body.innerText)", 20000)
    fr = pg4.evaluate("""() => { const t = document.querySelector('main').innerText.replace(/\\s+/g, ' ');
      const g = (k) => { const m = t.match(new RegExp(k + '\\\\s+(\\\\d+)')); return m ? +m[1] : null; }; return [g('領先'), g('改善'), g('轉弱'), g('落後')]; }""")
    ok(f"[{T}] ④ 資金輪盤四段家數：總覽摘要卡（領先／改善／轉弱／落後）＝資金輪動頁", bool(s3["r"]) and fr == s3["r"], [s3["r"], fr])
    ctx4.close(); ctx3.close()
    # ⑤ 題材
    TH = """(id) => { const el = document.getElementById(id); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return null;
      const o = {}; const w = (a) => (a || []).forEach(d => { if (d.children && d.children.length) w(d.children); else o[d.id || d.name] = [d.heat, d.chg, d.share]; });
      w(((i.getOption().series || [])[0] || {}).data); return o; }"""
    chart_ready(pg, "#ovTheme"); ot = pg.evaluate(TH, "ovTheme")
    ctx5, pg5 = open_page("#heatmap/theme")
    chart_ready(pg5, "#themeMap"); pg5.wait_for_timeout(1000)
    tm = pg5.evaluate(TH, "themeMap")
    tc = [k for k in (ot or {}) if k in (tm or {})]
    ok(f"[{T}] ⑤ 熱門題材：總覽與熱力圖頁共有的 {len(tc)} 個題材，熱度／漲跌／占比逐題材一致", len(tc) >= 5 and all(ot[k] == tm[k] for k in tc), [(k, ot[k], tm[k]) for k in tc if ot[k] != tm[k]][:3])
    ctx5.close(); ctx.close()

    # ------------------------------------------------------------------ ⑥ 盤中即時：同一個工作階段，總覽 → 熱力圖頁
    day = _dt.date.today()
    try:
        _dd = _json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8")).get("data_date") or ""
        day = _dt.date.fromisoformat(_dd[:10]) + _dt.timedelta(days=1)
        while day.weekday() >= 5:
            day += _dt.timedelta(days=1)
    except Exception:  # noqa: BLE001
        day = _dt.date(2026, 10, 19)
    DAY = day.isoformat(); DAY8 = DAY.replace("-", "")

    def fake_quote(route):          # 決定性：報價只跟代號有關，不隨請求次數漂移，兩張圖才有「同一個數字」可比
        ex = (parse_qs(urlparse(route.request.url).query).get("ex_ch") or [""])[0]
        arr = []
        for tok in [t for t in ex.split("|") if t]:
            try:
                c = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            if c == "t00":
                z, y = 20100, 20000
            elif c == "o00":
                z, y = 300, 299
            else:
                h = sum(ord(ch) * (i + 3) for i, ch in enumerate(c))
                y = 100.0
                z = round(y * (1 + ((((h * 7) % 21) - 10) * 0.3) / 100), 2)
            vol = 1000 + (sum(map(ord, c)) % 50) * 100
            arr.append({"c": c, "n": "測試" + c, "ex": tok[:3], "z": f"{z:.2f}", "y": f"{y:.2f}", "o": f"{y:.2f}",
                        "h": f"{max(z, y) + 1:.2f}", "l": f"{min(z, y) - 1:.2f}", "v": str(vol), "t": "10:30:05", "d": DAY8,
                        "tlong": str(int(_time.time() * 1000))})
        route.fulfill(status=200, content_type="application/json; charset=utf-8", body=_json.dumps({"rtcode": "0000", "rtmessage": "OK", "msgArray": arr}))

    ctx, pg = open_page("#overview", clock=f"{DAY}T02:30:00Z", admin=True, fake=fake_quote)
    chart_ready(pg, "#heat")
    live_ov = wait_until(pg, "() => { const e = document.querySelector('[data-snap=\"heat-overview\"]'); return !!e && e.dataset.snapLive === 'live'; }", 90000, 300)
    pg.wait_for_timeout(1500)
    lov = pg.evaluate(CS_LEAF, "heat")
    tg1 = pg.evaluate("() => (document.querySelector('#ovHeatCard .livetg-b') || {}).getAttribute && document.querySelector('#ovHeatCard .livetg-b').getAttribute('aria-pressed')")
    pg.evaluate("() => { location.hash = '#heatmap/industry'; }")
    chart_ready(pg, "#indTree")
    live_hm = wait_until(pg, "() => { const e = document.querySelector('[data-snap=\"heat-industry\"]'); return !!e && e.dataset.snapLive === 'live'; }", 90000, 300)
    pg.wait_for_timeout(1500)
    lhm = pg.evaluate(CS_LEAF, "indTree")
    tg2 = pg.evaluate("() => { const b = document.querySelector('[data-hlcard=ind] .livetg-b'); return b ? b.getAttribute('aria-pressed') : null; }")
    lc = [k for k in (lov or {}) if k in (lhm or {})]
    ld = [k for k in lc if abs((lov[k]["chg"] or 0) - (lhm[k]["chg"] or 0)) > 0.005 or lov[k]["color"] != lhm[k]["color"]]
    ok(f"[{T}] ⑥ 盤中：兩張熱力圖都進入即時（data-snap-live=live）", bool(live_ov) and bool(live_hm))
    ok(f"[{T}] ⑥ ★ 盤中即時：同一個工作階段，總覽與熱力圖頁共有的 {len(lc)} 個族群，即時漲跌幅與顏色一致", len(lc) >= 40 and not ld, [(k, lov[k]["chg"], lhm[k]["chg"]) for k in ld[:3]])
    ok(f"[{T}] ⑥ 即時鈕狀態一致（共用同一顆「熱力圖」開關）", tg1 == tg2 == "true", [tg1, tg2])
    ctx.close()


register("一致性普查1030", lambda pg, b, base, code: t_consistency_1030(b, base))
