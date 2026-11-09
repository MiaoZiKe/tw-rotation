# 驗收段落「事件歷史統計1109」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_sub_ctx()、_p12_ctx()、P12_INL、OP_POP 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _ES1109_ 開頭（所有段落 exec 進同一個命名空間）。
# P-1107-06（Andy 2026-11-09 點頭「02 05 03 04 06」）：個股頁「歷史統計」分頁 —— 除息／財報公布前後的歷史走勢（site/eventstudy.js）。
# 法遵 docs/feature_proposals/p1107_06_legal_review.md 第四節 R1～R15 逐條對到下面的斷言（每條 ok() 的名稱前面標 R 幾）。
# 資料用假的（個股 JSON 的 evstudy 鍵換成下面這幾份）：2330 除息 8 次（樣本夠）、財報 3 次（樣本不足）＋排除 10 季；0056 是 ETF（沒有財報）。
# 真的操作：
#   1. 1440 站主：點「歷史統計」→ 卡片出現；六格數字、點數＝樣本數、免責在數字正下方且字級 ≥ 正文 0.85 倍；「?」打開方法說明
#   2. 切「財報公布」→ 標題換、樣本 3 次 → 不出中位數與上漲次數、出現「樣本太少，不代表趨勢」、顯示排除 10 次
#   3. 切「原始」→ 中位數數字真的變、口徑字樣換；切「前後 20 日」→ 數字真的變
#   4. 禁用字掃描（卡片＋「?」說明）＝0；卡片沒有任何晚於資料日的日期、沒有「下次」「倒數」字樣、沒有連到除權息分頁的連結
#   5. 只在個股頁：總覽、市場明細、產業地圖等路由畫面上沒有這張卡；ETF 0056「財報公布」鈕反灰
#   6. 手機 390：「歷史統計」分頁在、卡片在可視寬度內、整頁沒有橫向捲軸
#   7. 功能鍵 stock.eventstudy：四方案 訪客關／註冊會員 5／Plus 5／Pro 5（Plus 與註冊會員同權限）、在體驗編輯清單；
#      訪客被鎖（鎖頭寫免費註冊）；註冊會員第 5 檔照常、第 6 檔被鎖＋一行字；站主種 99 次不鎖；體驗中的會員被鎖後按「繼續看」→ 真的打 /v1/grants/hit、卡片出現
import json as _es1109_json

_ES1109_KEY = "stock.eventstudy"
_ES1109_NOTE = "歷史統計今日 {n} 檔已用完・明天重置"
_ES1109_ASOF = "2026-11-06"
_ES1109_BAN = ("勝率", "搶息", "穩賺", "必漲", "卡位", "上車", "下車", "埋伏", "買點", "賣點",
               # neutral_copy 既有清單（tests/test_neutral_copy.py BANNED）
               "進場", "出場", "可追", "該跑", "加碼", "減碼", "布局", "佈局", "抄底", "逢低", "便宜", "好機會", "找買", "追高", "追進",
               "觀望", "可留意", "不要碰", "不要接", "承接", "抬轎", "停利", "該賣", "別急", "獲利了結", "短打", "划算", "出不掉", "沒人氣")


def _es1109_ev(dates, vals5, vals20, earn=False):
    out = []
    for i, d in enumerate(dates):
        e = {"d": d, "d0": d, "r": {"5": [vals5[i] + 0.004, vals5[i]], "20": [vals20[i] + 0.01, vals20[i]]}}
        if earn:
            e["q"] = f"{d[:4]}Q{(int(d[5:7]) - 2) // 3 or 4}"
        out.append(e)
    return out


def _es1109_stats(v, few_n=5):
    v = sorted(v)
    if len(v) < few_n:
        return {"n": len(v), "few": True, "up": None, "med": None, "best": None, "worst": None}
    n = len(v)
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    return {"n": n, "few": False, "up": sum(1 for x in v if x > 0), "med": round(med, 5), "best": v[-1], "worst": v[0]}


def _es1109_payload(code, div, earn, excl=0, etf=False):
    def summ(evs):
        o = {}
        for k in ("5", "20"):
            rows = [e for e in evs if e["r"].get(k)]
            o[k] = {"raw": _es1109_stats([e["r"][k][0] for e in rows]), "ex": _es1109_stats([e["r"][k][1] for e in rows]),
                    "from": rows[0]["d"] if rows else None, "to": rows[-1]["d"] if rows else None}
        return o
    return {"v": 1, "code": code, "asof": _ES1109_ASOF, "windows": [[5, 5], [20, 20]], "min_n": 5,
            "basis": {"stock": "股價已還原除權息、含息（總報酬）", "bench": "發行量加權股價指數（不含息）"}, "src": "證交所／櫃買中心公開資料",
            "div": {"events": div, "pending": 1, "sum": summ(div)},
            "earn": {"events": earn, "pending": 0, "excl": excl, "excl_from": "2012Q1" if excl else None, "excl_to": "2026Q2" if excl else None, "sum": summ(earn)}}


_ES1109_DIV = _es1109_ev(["2019-06-24", "2020-06-18", "2021-06-17", "2022-06-16", "2023-06-15", "2024-06-13", "2025-06-12", "2026-06-11"],
                         [0.012, -0.021, 0.034, -0.008, 0.019, 0.044, -0.031, 0.006], [0.05, -0.04, 0.02, -0.03, 0.07, 0.01, -0.06, 0.03])
_ES1109_EARN = _es1109_ev(["2026-05-12", "2026-08-12", "2026-10-20"], [0.021, -0.013, 0.008], [0.03, -0.02, 0.01], earn=True)
_ES1109_FILES = {
    "2330.json": _es1109_payload("2330", _ES1109_DIV, _ES1109_EARN, excl=10),
    "0056.json": _es1109_payload("0056", _ES1109_DIV[:6], [], etf=True),
}
for _c in ("2303", "2454", "2317", "1301", "2412"):
    _ES1109_FILES[_c + ".json"] = _es1109_payload(_c, _ES1109_DIV, _ES1109_EARN, excl=10)


def _es1109_route(c):
    """個股 JSON（data/stock/<代號>.json）照原檔回，但 evstudy 鍵換成上面的假資料（資料就放在個股 JSON 裡，不另外發請求）。"""
    def h(route):
        name = route.request.url.split("?")[0].rsplit("/", 1)[-1]
        r = route.fetch()
        if r.status != 200 or name not in _ES1109_FILES:
            return route.fulfill(response=r)
        j = r.json(); j["evstudy"] = _ES1109_FILES[name]
        return route.fulfill(response=r, body=_es1109_json.dumps(j, ensure_ascii=False), content_type="application/json")
    c.route("**/data/stock/*.json*", h)


_ES1109_STATE = """() => { const c = document.getElementById('esCard'); if (!c) return null; const r = c.getBoundingClientRect();
  const k = (id) => { const e = c.querySelector('#esKpi [data-k="' + id + '"] b'); return e ? e.innerText.trim() : null; };
  const el = (id) => document.getElementById(id); const ch = el('esChart') && window.echarts && echarts.getInstanceByDom(el('esChart')); const o = ch && ch.getOption();
  return { kind: c.dataset.kind, win: c.dataset.win, mode: c.dataset.mode, title: (el('esTitle') || {}).innerText, vis: r.width > 0 && r.height > 0,
    n: k('n'), per: k('per'), up: k('up'), med: k('med'), best: k('best'), worst: k('worst'), pts: o ? o.series[0].data.length : 0,
    few: !!el('esFew') && el('esFew').innerText, excl: el('esExcl') ? el('esExcl').innerText : '', basis: (el('esBasis') || {}).innerText || '',
    txt: c.innerText, st: window.TwEventStudy && TwEventStudy.state() }; }"""


def t_eventstudy_1109(b, base, code):
    T = "事件歷史統計1109"
    errs: list = []

    def open_tab(pg, cd="2330", mobile=False):
        pg.goto(base + "#stock/" + cd, wait_until="domcontentloaded")
        sel = '#mbTabs button[data-t="evt"]' if mobile else '#stockTabs button[data-t="evstudy"]'
        wait_until(pg, f"() => !!document.querySelector('{sel}')", 30000)
        pg.wait_for_timeout(500)
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        pg.evaluate(f"() => {{ const b = document.querySelector('{sel}'); b.scrollIntoView({{block: 'center', inline: 'center'}}); }}")
        pg.locator(sel).first.click()
        wait_until(pg, "() => !!document.getElementById('esCard')", 8000)
        pg.wait_for_timeout(700)

    def click(pg, sel):
        pg.locator(sel).first.click(); pg.wait_for_timeout(500)

    # ---------------------------------------------------------------- 1～5. 桌機 1440 站主
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    open_tab(pg)
    wait_until(pg, "() => !!(window.TwEventStudy && TwEventStudy.state().loaded)", 8000)
    s = pg.evaluate(_ES1109_STATE)
    ok(f"{T} 點「歷史統計」→ 卡片出現、預設「除息」「前後 5 日」「超額（相對大盤）」、標題「除息前後的歷史走勢」",
       bool(s) and s["vis"] and s["kind"] == "div" and s["win"] == "5" and s["mode"] == "ex" and s["title"] == "除息前後的歷史走勢", s)
    ok(f"{T} R3 六格都在且非空：樣本數、期間、上漲次數（a 次／共 N 次）、中位數、最好、最差",
       s["n"] == "8 次" and s["per"] == "2019/06～2026/06" and s["up"] == "5 次／共 8 次" and all(s[k] and "%" in s[k] for k in ("med", "best", "worst")), s)
    ok(f"{T} R4 主圖是分布：散點數＝樣本數 8（每次事件一個點）", s["pts"] == 8, s["pts"])
    lay = pg.evaluate("""() => { const c = document.getElementById('esCard'), k = document.getElementById('esKpi'), d = document.getElementById('esDisc'), s = document.getElementById('esSub');
        const kr = k.getBoundingClientRect(), dr = d.getBoundingClientRect(), b = document.getElementById('esBasis').getBoundingClientRect();
        return { inCard: c.contains(d), below: dr.top >= kr.bottom - 1, gap: Math.round(dr.top - kr.bottom), fs: parseFloat(getComputedStyle(d).fontSize), body: parseFloat(getComputedStyle(s).fontSize),
          txt: d.innerText, boxed: getComputedStyle(d).borderTopWidth !== '0px' }; }""")
    ok(f"{T} R11 免責在卡片內、數字正下方（中間只隔一行口徑）、字級 ≥ 卡內正文 0.85 倍、內容照法遵 5-4",
       lay["inCard"] and lay["below"] and lay["gap"] <= 60 and lay["fs"] >= 0.85 * lay["body"] and "不代表下一次會一樣" in lay["txt"] and "不構成任何買賣建議" in lay["txt"], lay)
    ok(f"{T} R6 口徑寫明：超額＝相對加權指數、股價已還原除權息、含息；加權指數不含息", all(w in s["basis"] for w in ("超額報酬", "還原除權息", "含息", "不含息")), s["basis"])
    click(pg, "#esCard .howbtn")
    wait_until(pg, "() => { const e = document.getElementById('how-skes'); return !!e && !e.hidden && e.getClientRects().length > 0; }", 4000)
    hw = pg.evaluate("() => (document.getElementById('how-skes') || {}).innerText || ''")
    ok(f"{T} R12「?」→ 方法說明打開：第 0 天定義、超額＝個股減加權指數、含息、資料來源", all(w in hw for w in ("第 0 天", "超額報酬＝個股報酬減同期加權指數報酬", "含息", "資料來源")), hw[:300])
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    full_txt = s["txt"] + "\n" + hw

    # 切原始 → 數字真的變
    med_ex = s["med"]
    click(pg, '#esMode button[data-v="raw"]')
    s2 = pg.evaluate(_ES1109_STATE)
    ok(f"{T} R6 切「原始」→ 中位數真的改變、口徑改寫成個股本身、按鈕亮在原始", s2["mode"] == "raw" and s2["med"] != med_ex and "個股本身" in s2["basis"]
       and pg.evaluate("() => document.querySelector('#esMode button.on').dataset.v") == "raw", (med_ex, s2["med"], s2["basis"]))
    click(pg, '#esMode button[data-v="ex"]')
    click(pg, '#esWin button[data-v="20"]')
    s3 = pg.evaluate(_ES1109_STATE)
    ok(f"{T} 切「前後 20 日」→ 數字真的改變（中位數或最差不同）、副標寫「前 20 日到後 20 日」", s3["win"] == "20" and (s3["med"] != med_ex or s3["worst"] != s["worst"]) and "前 20 日到後 20 日" in s3["txt"], s3)
    click(pg, '#esWin button[data-v="5"]')
    # 財報：樣本 3 次（< 5）
    click(pg, '#esKind button[data-v="earn"]')
    s4 = pg.evaluate(_ES1109_STATE)
    ok(f"{T} 切「財報公布」→ 標題換成「財報公布前後的歷史走勢」、樣本 3 次", s4["kind"] == "earn" and s4["title"] == "財報公布前後的歷史走勢" and s4["n"] == "3 次", s4)
    ok(f"{T} R5 樣本 < 5：中位數、上漲次數、最好、最差都不給（—），出現「樣本太少，不代表趨勢」，仍列每一次的原始數字（3 列）",
       all(s4[k] == "—" for k in ("up", "med", "best", "worst")) and s4["few"] and "樣本太少，不代表趨勢" in s4["few"]
       and pg.evaluate("() => document.querySelectorAll('#esTbl tbody tr').length") == 3, s4)
    ok(f"{T} R7 財報只用實際公告日：卡內顯示「缺實際公告日的季度不納入：本檔排除 10 次」", "排除 10 次" in s4["excl"] and "實際公告日" in s4["excl"], s4["excl"])
    full_txt += "\n" + s4["txt"]
    hits = [w for w in _ES1109_BAN if w in full_txt]
    ok(f"{T} R2 禁用字掃描（卡片三種狀態＋「?」說明）＝ 0", not hits, hits)
    dates = re.findall(r"20\d\d[-/]\d\d(?:[-/]\d\d)?", full_txt)
    fut = [d for d in dates if d.replace("/", "-")[:len(d)] > _ES1109_ASOF[:len(d)]]
    ok(f"{T} R8 卡內沒有晚於資料日（{_ES1109_ASOF}）的日期、沒有「下次」「倒數」「行事曆」字樣、卡內沒有任何連結",
       not fut and not any(w in full_txt for w in ("下次", "下一次除息", "倒數", "行事曆", "距今")) and pg.evaluate("() => document.querySelectorAll('#esCard a').length") == 0, (fut, len(dates)))
    # R1：其他路由畫面上沒有這張卡
    seen = {}
    for h in ("#overview", "#market/updown", "#industry", "#flow", "#etf", "#explore"):
        pg.goto(base + h, wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
        seen[h] = pg.evaluate("() => [...document.querySelectorAll('#esCard')].some(e => e.getClientRects().length > 0)")
    ok(f"{T} R1／R9 只在個股頁：總覽、市場明細、產業地圖、資金流向、ETF、選股策略畫面上都沒有這張卡", not any(seen.values()), seen)
    # ETF：沒有財報
    open_tab(pg, "0056")
    wait_until(pg, "() => !!(window.TwEventStudy && TwEventStudy.state().loaded && TwEventStudy.state().code === '0056')", 8000)
    e = pg.evaluate("() => { const b = document.querySelector('#esKind button[data-v=\"earn\"]'); return { dis: !!b && b.disabled, title: b && b.title, n: (document.querySelector('#esKpi [data-k=\"n\"] b') || {}).innerText }; }")
    ok(f"{T} R13 ETF 0056：除息照算（6 次）、「財報公布」鈕反灰並說明 ETF 沒有財報公布事件", e["dis"] and "ETF" in (e["title"] or "") and e["n"] == "6 次", e)
    c.close()

    # ---------------------------------------------------------------- 6. 手機 390
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free", width=390, touch=True)
    _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    open_tab(pg, mobile=True)
    wait_until(pg, "() => !!(window.TwEventStudy && TwEventStudy.state().loaded)", 8000)
    pg.wait_for_timeout(600)
    m = pg.evaluate("""() => { const c = document.getElementById('esCard').getBoundingClientRect(), k = document.getElementById('esKpi').getBoundingClientRect(), ch = document.getElementById('esChart').getBoundingClientRect();
        const segs = [...document.querySelectorAll('#esCard .seg button')].map(b => Math.round(b.getBoundingClientRect().height));
        return { l: Math.round(c.left), r: Math.round(c.right), vw: innerWidth, sw: document.documentElement.scrollWidth, kr: Math.round(k.right), chh: Math.round(ch.height), segs,
          tab: (document.querySelector('#mbTabs button[data-t="evt"]') || {}).innerText }; }""")
    ok(f"{T} 390：「歷史統計」分頁在、卡片與數字格在可視寬內、整頁沒有橫向捲軸、圖高 ≥ 200、切換鈕高 ≥ 32",
       m["tab"] == "歷史統計" and m["l"] >= 0 and m["r"] <= m["vw"] and m["kr"] <= m["vw"] and m["sw"] <= m["vw"] and m["chh"] >= 200 and all(h >= 32 for h in m["segs"]), m)
    click(pg, '#esMode button[data-v="raw"]')
    ok(f"{T} 390：手指點「原始」真的切換", pg.evaluate("() => document.getElementById('esCard').dataset.mode") == "raw")
    c.close()

    # ---------------------------------------------------------------- 7. 功能鍵 stock.eventstudy
    c = _p12_ctx(b, plan="free"); _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#stock/2330", wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwFeatures && !!window.TW_PLAN_PRESETS && !!window.TwPerm", 20000)
    r = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, k = 'stock.eventstudy', f = F.byId(k); const tier = (t) => P.tiers.find(x => x.key === t);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(x => x.kind === 'bool' && !x.adminOnly && x.cat !== 'grp' && !BAN.includes(x.id)).map(x => x.id);
        return { reg: f ? [f.kind, f.cat, !!f.qnote, JSON.stringify(f.defBy), JSON.stringify(f.limBy)] : null, veil: f ? f.veil.map(v => v.join('|')) : [],
          feats: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats[k]), lims: ['guest', 'free', 'plus', 'pro'].map(t => (tier(t).lims || {})[k] == null ? null : tier(t).lims[k]),
          ed: ed.includes(k), lim: TwPerm.lim(k) }; }""")
    ok(f"{T} R14 功能鍵登記（bool、個股分頁、訪客預設關、註冊會員／Plus／Pro 每日 5 檔）、四方案 訪客關＋註冊會員／Plus／Pro 同權限（開＋5）、在體驗編輯清單",
       r["reg"] == ["bool", "stocktab", True, '{"guest":false}', '{"free":5,"plus":5,"pro":5}'] and r["feats"] == [False, True, True, True]
       and r["lims"] == [None, 5, 5, 5] and r["ed"] and r["lim"] == 5 and any("evstudy" in v for v in r["veil"]) and any("evt" in v for v in r["veil"]), r)
    c.close()

    locked = "() => !!document.querySelector('#stockTab > .qcov .qcard.qcnote')"
    c = _p12_ctx(b, plan="free", seed={_ES1109_KEY: 4}); _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    open_tab(pg, "2330"); pg.wait_for_timeout(900)
    a = pg.evaluate(P12_INL, "#stockTab")
    n5 = pg.evaluate(f"() => (TwQuota.used('{_ES1109_KEY}') || []).length")
    ok(f"{T} 註冊會員第 5 檔照常看得到（沒鎖、數字在）、計數 5", not a["on"] and n5 == 5 and pg.evaluate("() => !!document.querySelector('#esKpi')"), (a, n5))
    open_tab(pg, "2303"); wait_until(pg, locked, 8000)
    a2 = pg.evaluate(P12_INL, "#stockTab")
    want = _ES1109_NOTE.replace("{n}", "5")
    ok(f"{T} 註冊會員第 6 檔被鎖＋一行「{want}」（不寫「Plus 以上可增加」）、不跳彈出層", a2["on"] and want in a2["txt"] and "Plus" not in a2["txt"] and not pg.evaluate(OP_POP), a2)
    open_tab(pg, "2330"); pg.wait_for_timeout(900)
    ok(f"{T} 回到今天看過的 2330 不重算、照常看得到", not pg.evaluate(P12_INL, "#stockTab")["on"])
    c.close()

    c = _p12_ctx(b, plan="guest"); _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    open_tab(pg, "2330"); pg.wait_for_timeout(1200)
    g = pg.evaluate("""() => { const t = document.getElementById('stockTab'); return { plk: !!t && t.hasAttribute('data-plk'), txt: t ? t.innerText : '',
        kpi: !!document.querySelector('#esKpi'), go: (document.querySelector('#stockTab .plkgo') || {}).innerText || '' }; }""")
    ok(f"{T} 訪客：歷史統計分頁被鎖（此功能需開通、鈕寫免費註冊／登入）、沒有畫出任何統計數字", g["plk"] and not g["kpi"] and "免費註冊" in g["go"] and "%" not in g["txt"], g)
    c.close()

    seed_js = ("try { if (!localStorage.getItem('es1109.init')) { localStorage.setItem('es1109.init', '1'); localStorage.setItem('tw.live.on', '0');"
               " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); const k = {};"
               " Object.entries(%s).forEach(([id, n]) => { k[id] = Array.from({length: n}, (_, i) => 'seed' + i); });"
               " localStorage.setItem('tw.quota', JSON.stringify({ day, k })); } } catch (e) {}")
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    _es1109_route(c)
    c.add_init_script(seed_js % _es1109_json.dumps({_ES1109_KEY: 99}))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    open_tab(pg, "2330"); pg.wait_for_timeout(900)
    o = pg.evaluate(P12_INL, "#stockTab")
    ok(f"{T} 站主（owner）種 99 次也不鎖、統計數字在", not o["on"] and not o["big"] and pg.evaluate("() => !!document.querySelector('#esKpi')"), o)
    c.close()

    # 體驗：被鎖後按「繼續看」
    now = int(__import__("time").time() * 1000)
    API = "https://es1109.example.test"
    stt = {"left": 3, "hit": 0}

    def handle(route, _rq=None):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        out = {}
        if path == "/v1/me":
            out = {"user": {"email": "new@example.com", "name": "新會員", "admin": False, "owner": False}}
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": "free", "planName": "註冊會員", "feats": {}, "lims": {}, "dq": None}
        elif path == "/v1/grants/public":
            out = {"now": now, "promo": [], "welcome": []}
        elif path == "/v1/grants/me":
            out = {"now": now, "today": {}, "grants": [{"gid": "welcome", "name": "新會員體驗", "kind": "welcome", "start": now, "end": now + 14 * 86400000 - 1000, "per": "day",
                                                     "feats": {_ES1109_KEY: {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1; stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_es1109_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _es1109_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
    c.add_init_script(seed_js % _es1109_json.dumps({_ES1109_KEY: 5}))
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    _es1109_route(c)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#stock/2330", wait_until="domcontentloaded")
    ag = pg.get_by_role("button", name="同意並繼續")
    if ag.count() and ag.first.is_visible():
        ag.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, f"() => window.TwGrants && TwGrants.left('{_ES1109_KEY}') === 3", 30000)
    open_tab(pg, "2330")
    wait_until(pg, "() => !!document.querySelector('#stockTab .qc-try')", 8000)
    btn = pg.locator("#stockTab .qc-try")
    ok(f"{T} 體驗中的註冊會員用完 5 檔後，歷史統計原位置多一顆「繼續看」、體驗剩 3 次", btn.count() == 1, pg.evaluate("() => ((document.querySelector('#stockTab') || {}).innerText || '').slice(0, 200)"))
    if btn.count():
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
            btn.first.click()
        hj = ri.value.json()
        ok(f"{T} 按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
        shown = wait_until(pg, "() => { const e = document.querySelector('#stockTab'); return !!e && !e.hasAttribute('data-qlk') && !e.querySelector(':scope > .qcov') && !!document.querySelector('#esKpi'); }", 6000)
        ok(f"{T} 扣完統計卡真的出現（鎖與一行字拿掉）", bool(shown))
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("事件歷史統計1109", lambda pg, b, base, code: t_eventstudy_1109(b, base, code))
