# 驗收段落「信用排行1104」：#market/credit「個股排行」名稱不截斷、標題不出界、排除 ETF 開關（融資／融券都適用、重新整理保留）
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def _rk_fake():
    base = _mf_fake()
    etf = [("00632R", "元大台灣50反1"), ("00403A", "主動統一升級50"), ("00981A", "主動統一台股增長"), ("00940", "元大台灣價值高息"), ("00878", "國泰永續高股息"),
           ("00679B", "元大美債20年"), ("00631L", "元大台灣50正2"), ("00919", "群益台灣精選高息")]
    stk = [("2330", "台灣積體電路製造"), ("2317", "鴻海精密工業"), ("2454", "聯發科技"), ("3711", "日月光投控"), ("2603", "長榮海運"),
           ("2609", "陽明海運"), ("2618", "長榮航空"), ("1301", "台灣塑膠工業"), ("2303", "聯華電子"), ("2881", "富邦金融控股")]
    stk = stk + [(str(3000 + i), "長名稱測試科技股份有限公司" + str(i)) for i in range(10)]
    g = lambda c: ["ETF" if c.startswith("00") else "半導體"]
    up = [{"code": c, "name": nm, "chg": 20000.0 - i * 700, "g": g(c)} for i, (c, nm) in enumerate(etf[:4] + stk[:10])]
    dn = [{"code": c, "name": nm, "chg": -(15000.0 - i * 500), "g": g(c)} for i, (c, nm) in enumerate(etf[4:] + stk[10:])]
    d = base["margin"]["rows"][-1]["d"]
    base["margin"]["rank"] = {"d": d, "rows": up + dn}
    base["margin"]["short_rank"] = {"d": d, "rows": [dict(r, chg=-r["chg"]) for r in base["margin"]["rank"]["rows"]]}
    return base


def t_rank_1104(b, base, code):
    T = "信用排行1104"
    errs = []
    fake = json.dumps(_rk_fake())
    shots = pathlib.Path(os.environ.get("TW_CREDIT_SHOTS", "")) if os.environ.get("TW_CREDIT_SHOTS") else None
    for w in (1440, 800, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/data/market_fut.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=fake))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#market/credit", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            pg.click("#mfTab button[data-k='rank']"); pg.wait_for_selector(".mf-rk", timeout=8000)
            chk = """() => { const r = [...document.querySelectorAll('.mf-rk')]; const nm = [...document.querySelectorAll('.mf-nm')];
              const bad = nm.filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1).length;
              const out = [...document.querySelectorAll('.mf-rank > b, .mf-rk')].filter(e => { const b = e.getBoundingClientRect(); return b.left < -0.5 || b.right > innerWidth + 0.5; }).length;
              const ttl = [...document.querySelectorAll('.mf-rank > b')].map(e => { const b = e.getBoundingClientRect(), p = e.parentElement.getBoundingClientRect(); return b.left >= p.left - 0.5 && e.scrollWidth <= e.clientWidth + 1; });
              const ov = [...document.querySelectorAll('.mf-rk')].filter(a => a.scrollWidth > a.clientWidth + 1).length;
              return { n: r.length, bad, out, ttl, ov, sw: document.documentElement.scrollWidth - innerWidth, hasEtf: r.some(a => /^00/.test(a.querySelector('.mf-nm b').textContent)),
                       full: r.every(a => (a.title || '').includes(a.querySelector('.mf-nm').textContent.trim().split(' ')[0])), cols: document.querySelectorAll('.mf-rank').length,
                       up: document.querySelectorAll('.mf-rank')[0].querySelectorAll('.mf-rk').length, dn: document.querySelectorAll('.mf-rank')[1].querySelectorAll('.mf-rk').length }; }"""
            s0 = pg.evaluate(chk)
            ok(f"【{T}】{w} 名稱完整不被截（scrollWidth≤clientWidth）、列不出界、兩欄標題不被裁、無橫向捲軸", s0["bad"] == 0 and s0["out"] == 0 and all(s0["ttl"]) and s0["ov"] == 0 and s0["sw"] <= 1, s0)
            ok(f"【{T}】{w} 預設不排除 ETF（清單含 ETF）、增減各 8 檔、滑過名稱的提示＝代號＋全名", s0["hasEtf"] and s0["up"] == 8 and s0["dn"] == 8 and s0["full"], s0)
            if shots and w in (1440, 390):
                pg.locator(".mf-ranks").scroll_into_view_if_needed(); pg.locator(".mf-ranks").screenshot(path=str(shots / f"w{w}_etf_on.png"))
            href = pg.evaluate("() => document.querySelector('.mf-rk').getAttribute('href')")
            ok(f"【{T}】{w} 點名稱連到 #stock/<代號>", re.match(r"#stock/\d{4,6}[A-Z]?$", href or "") is not None, href)
            pg.check("#mfNoEtf"); pg.wait_for_timeout(250)
            s1 = pg.evaluate(chk)
            ok(f"【{T}】{w} 勾「排除 ETF」→ 清單不含 ETF、增加／減少仍各 8 檔", (not s1["hasEtf"]) and s1["up"] == 8 and s1["dn"] == 8 and s1["bad"] == 0, s1)
            if shots and w in (1440, 390):
                pg.locator(".mf-ranks").screenshot(path=str(shots / f"w{w}_etf_off.png"))
            pg.click("#mfRkSeg button[data-k='short']"); pg.wait_for_selector(".mf-rk", timeout=8000); pg.wait_for_timeout(250)
            s2 = pg.evaluate(chk)
            ok(f"【{T}】{w} 融券分頁同樣已排除 ETF（勾選狀態沿用）、筆數 8、名稱不被截", pg.is_checked("#mfNoEtf") and not s2["hasEtf"] and s2["up"] == 8 and s2["bad"] == 0, s2)
            pg.reload(wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
            pg.click("#mfTab button[data-k='rank']"); pg.wait_for_selector(".mf-rk", timeout=8000)
            s3 = pg.evaluate(chk)
            ok(f"【{T}】{w} 重新整理後仍排除 ETF（localStorage 保留）", pg.is_checked("#mfNoEtf") and not s3["hasEtf"], s3)
            pg.uncheck("#mfNoEtf"); pg.wait_for_timeout(250)
            ok(f"【{T}】{w} 取消勾選 → ETF 回來", pg.evaluate(chk)["hasEtf"])
        except Exception as e:
            ok(f"【{T}】{w} 流程不出例外", False, repr(e)[:300])
        finally:
            c.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])


register("信用排行1104", lambda pg, b, base, code: t_rank_1104(b, base, code))
