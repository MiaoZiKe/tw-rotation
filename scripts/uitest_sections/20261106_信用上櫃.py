# 驗收段落「信用上櫃1106」：#market/credit 融資維持率（估算）上市／上櫃／合計 分段開關（2026-11-06 Andy）
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# 真的按：上市 → 上櫃 → 合計 → 重新整理（選擇保留）→ 上市；每一步驗大數字、標題、圖的右軸指數名、明細表第一列、localStorage 真的換了。
# 另一輪用「上櫃還沒有資料」的假資料：切上櫃 → 看到「資料累積中」且開關還在，按上市能切回來。
# 「?」說明要有官方 159.77% 的對照與證交所「不存在單一個股維持率低於 130% 即追繳」。
# flake8: noqa

def _mk_fake(otc_empty=False):
    import datetime as _dt
    days, d = [], _dt.date(2026, 6, 1)
    while len(days) < 120:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += _dt.timedelta(days=1)
    mk = lambda base, i, x, idx: {"d": x, "ratio": base + (i % 11) * .7, "margin_lots": 7e6 + i * 900, "margin_chg": (i % 7 - 3) * 1200.0,
                                  "margin_yi": 2500 + i * 2.0, "cap_yi": 4200.0, "short_lots": 2e5 + i * 30, "short_chg": (i % 5 - 2) * 200.0,
                                  "partial": False, "taiex": idx + i}
    tw = [mk(170.0, i, x, 27000.0) for i, x in enumerate(days)]
    otc = [] if otc_empty else [mk(231.0, i, x, 300.0) for i, x in enumerate(days[-40:])]
    al = [] if otc_empty else [mk(181.0, i, x, 27000.0) for i, x in enumerate(days[-40:])]
    return {"margin": {"rows": tw, "asof": days[-1], "rank": None, "short_rank": None, "mkts": {"twse": tw, "tpex": otc, "all": al},
                       "idx_name": {"twse": "加權指數", "tpex": "櫃買指數", "all": "加權指數"}, "otc_from": otc[0]["d"] if otc else None}}


def t_credit_otc_1106(b, base, code):
    T = "信用上櫃1106"
    errs = []
    shots = pathlib.Path(os.environ.get("TW_CREDIT_SHOTS", "")) if os.environ.get("TW_CREDIT_SHOTS") else None
    st_js = """() => { const big = document.querySelector('.mf-big .mf-bn'), lab = document.querySelector('.mf-big .mf-l');
      const on = document.querySelector('#mfMkSeg button.on'); const h = [...document.querySelectorAll('.mf-cbox h4')].map(e => e.textContent);
      const td = document.querySelector('#mfTbl tbody tr td:nth-child(2)'); let ls = null; try { ls = localStorage.getItem('tw.mf.mk'); } catch (e) {}
      return { big: big ? big.textContent.trim() : '', lab: lab ? lab.textContent.trim() : '', on: on ? on.textContent : '', h, td: td ? td.textContent : '', ls,
               n: document.querySelectorAll('#mfMkSeg button').length, empty: (document.querySelector('#mf-credit .empty') || {}).textContent || '',
               sw: document.documentElement.scrollWidth - innerWidth }; }"""
    for w in (1440, 390):
        mob = w <= 640
        for otc_empty in (False, True):
            fake = json.dumps(_mk_fake(otc_empty))
            c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
            c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            # 注意：Playwright 會看處理函式的參數個數，兩個參數就把 request 塞進第二個 —— 不能用 lambda r, f=fake 綁值
            c.route("**/data/market_fut.json*", (lambda f: (lambda r: r.fulfill(status=200, content_type="application/json", body=f)))(fake))
            pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
            tag = f"{w}{'（上櫃無資料）' if otc_empty else ''}"
            try:
                pg.goto(base + "#market/credit", wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
                ag = pg.get_by_role("button", name="同意並繼續")
                if ag.count():
                    try: ag.first.click(timeout=1500)
                    except Exception: pass
                s0 = pg.evaluate(st_js)
                ok(f"【{T}】{tag} 預設上市：三顆開關、標題「上市融資維持率（估算）」、右軸加權指數",
                   s0["n"] == 3 and s0["on"] == "上市" and "上市融資維持率（估算）" in s0["lab"] and any("加權指數" in x for x in s0["h"]), s0)
                if not otc_empty:
                    pg.click("#mfMkSeg button[data-k='tpex']"); pg.wait_for_timeout(300)
                    s1 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 按「上櫃」→ 大數字換成上櫃（235.20%）、標題與圖改上櫃＋櫃買指數、明細表換、localStorage＝tpex",
                       s1["on"] == "上櫃" and s1["big"].startswith("235.20%") and s1["big"] != s0["big"] and "上櫃融資維持率" in s1["lab"]
                       and all("櫃買指數" in x for x in s1["h"]) and s1["td"] != s0["td"] and s1["ls"] == "tpex", s1)
                    if shots:
                        (pg.locator("#mf-credit").screenshot(path=str(shots / f"credit_otc_w{w}_tpex.png")) if not mob else
                         (pg.evaluate("() => scrollTo(0, document.querySelector('#mf-credit').getBoundingClientRect().top + scrollY - 70)"), pg.screenshot(path=str(shots / f"credit_otc_w{w}_tpex.png"))))
                    xo = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('mfChart')); const x = c.getOption().xAxis[0].data; return [x[0], x[x.length - 1], document.querySelector('#mfDays button.on').textContent]; }")
                    ok(f"【{T}】{tag} 上櫃只有 40 天 →「全部」期間，圖的 X 軸仍由舊到新（明細表排序不能把圖倒過來）", xo[2] == "全部" and xo[0] < xo[1], xo)
                    pg.click("#mfMkSeg button[data-k='all']"); pg.wait_for_timeout(300)
                    s2 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 按「合計」→ 大數字換成合計（185.20%）、標題「上市＋上櫃」、右軸回加權指數",
                       s2["on"] == "合計" and s2["big"].startswith("185.20%") and "上市＋上櫃融資維持率" in s2["lab"]
                       and any("加權指數" in x for x in s2["h"]) and s2["ls"] == "all", s2)
                    if shots:
                        (pg.locator("#mf-credit").screenshot(path=str(shots / f"credit_otc_w{w}_all.png")) if not mob else
                         (pg.evaluate("() => scrollTo(0, document.querySelector('#mf-credit').getBoundingClientRect().top + scrollY - 70)"), pg.screenshot(path=str(shots / f"credit_otc_w{w}_all.png"))))
                    pg.reload(wait_until="domcontentloaded")
                    wait_until(pg, "() => !!document.querySelector('[data-snap=margin] .mf-tile')", 20000)
                    s3 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 重新整理後仍是合計（選擇有記住）", s3["on"] == "合計" and s3["big"] == s2["big"], s3)
                    pg.click("#mfMkSeg button[data-k='twse']"); pg.wait_for_timeout(300)
                    s4 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 按「上市」→ 回到上市數字", s4["on"] == "上市" and s4["big"] == s0["big"] and s4["ls"] == "twse", s4)
                    ok(f"【{T}】{tag} 無橫向捲軸", s4["sw"] <= 1 and s1["sw"] <= 1 and s2["sw"] <= 1, [s1["sw"], s2["sw"], s4["sw"]])
                    pg.click("#mf-credit .howbtn"); pg.wait_for_timeout(300)
                    how = pg.evaluate("() => (document.querySelector('#how-mf-credit') || {}).textContent || ''")
                    ok(f"【{T}】{tag} 「?」說明有官方 159.77% 對照、不是整戶、沒有融券保證金、證交所「不存在單一個股維持率低於 130% 即追繳」",
                       "159.77" in how and "不是整戶" in how and "融券保證金" in how and "不存在單一個股維持率低於 130% 即追繳" in how, how[:200])
                else:
                    pg.click("#mfMkSeg button[data-k='tpex']"); pg.wait_for_timeout(300)
                    s1 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 按「上櫃」→ 顯示「資料累積中」、開關還在、上櫃亮起", "資料累積中" in s1["empty"] and s1["n"] == 3 and s1["on"] == "上櫃", s1)
                    pg.click("#mfTab button[data-k='rank']"); pg.wait_for_timeout(300)
                    rk_on = pg.evaluate("() => (document.querySelector('#mfTab button.on') || {}).textContent")
                    pg.click("#mfTab button[data-k='mkt']"); pg.wait_for_timeout(300)
                    back = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 上櫃沒資料時仍可切「個股排行」再切回「大盤」（回來仍是上櫃的資料累積中）", rk_on == "個股排行" and "資料累積中" in back["empty"], [rk_on, back])
                    pg.click("#mfMkSeg button[data-k='twse']"); pg.wait_for_timeout(300)
                    s2 = pg.evaluate(st_js)
                    ok(f"【{T}】{tag} 再按「上市」→ 大數字回來", s2["on"] == "上市" and s2["big"] == s0["big"] and not s2["empty"], s2)
            except Exception as e:
                ok(f"【{T}】{tag} 流程不出例外", False, repr(e)[:300])
            finally:
                c.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])


register("信用上櫃1106", lambda pg, b, base, code: t_credit_otc_1106(b, base, code))
