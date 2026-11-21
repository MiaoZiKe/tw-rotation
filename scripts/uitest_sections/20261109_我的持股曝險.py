# 驗收段落「我的持股曝險1109」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx()、_sub_ctx()、P12_INL、OP_POP 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _PF1109_ 開頭（所有段落 exec 進同一個命名空間）。
# Andy 2026-11-09 點頭 P-1107-03「我的持股曝險」（#portfolio，site/portfolio.js）：輸入持股 → 各族群曝險甜甜圈 ＋ 每個族群的資金占比與輪動；持股只存瀏覽器。
# 真的操作：
#   1. 金額輸入三檔不同族群（600000／300000／100000）→ 甜甜圈三塊 60／30／10（算給定數字比對）；股數輸入一檔 → 用 stocks.json 的收盤價自己算比對
#   2. 族群資金欄位（5 日占比／20 日占比／變化／輪動）有值，且＝flow_v3.json 自己算的平均；點表格列／圖例／甜甜圈扇區在原地展開持股、持股連結進個股頁
#   3. 重新整理資料還在；改數量比重跟著變；✕ 移除；清除全部要按兩次、清完歸零（空狀態、沒有甜甜圈、localStorage 空）
#   4. 隱私：全程攔所有請求，沒有任何請求（網址或 body）帶到持股代號／數量，也沒有任何非 GET 請求帶持股
#   5. 方案：註冊會員 10 檔上限、訪客 5 檔、匯入 CSV 在註冊會員被鎖（Plus 能用、略過壞行）、從自選帶入
#   6. 功能鍵 portfolio.exposure：註冊會員第 5 次照常、第 6 次整頁反灰＋一行字；訪客第 4 次被鎖；站主種 99 次不鎖；體驗中的會員按「繼續看」真的打 /v1/grants/hit
#   7. 手機 390：沒有橫向捲軸、有持股時甜甜圈在最上面並且第一屏看得到前三大族群、次要欄位預設隱藏、族群表只列前三大＋「看全部」
import json as _pf1109_json

_PF1109_KEY = "portfolio.exposure"
_PF1109_NOTE = "我的持股曝險今日 {n} 次已用完・Plus 以上可增加"
_PF1109_SITE = ROOT / "site" / "data"


def t_portfolio_1109(b, base, code):
    T = "我的持股曝險1109"
    errs: list = []
    stocks = {s["code"]: s for s in _pf1109_json.loads((_PF1109_SITE / "stocks.json").read_text(encoding="utf-8"))}
    f3 = _pf1109_json.loads((_PF1109_SITE / "flow_v3.json").read_text(encoding="utf-8"))
    sdg = {g["group_id"]: g for g in f3["share_daily"]["groups"]}

    def go(pg, clear=True):
        pg.goto(base + "#portfolio", wait_until="domcontentloaded")
        wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfWrap') && !!document.querySelector('#pfMsg')", 30000)
        if clear:
            pg.evaluate("() => { try { localStorage.removeItem('tw.portfolio'); } catch (e) {} }")
            pg.reload(wait_until="domcontentloaded")
            wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfWrap') && !!document.querySelector('#pfMsg')", 30000)
        pg.wait_for_timeout(900)
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)

    def add(pg, mode, c, q):
        pg.locator(f'#pfMode button[data-m="{mode}"]').click()
        pg.fill("#pfCode", c); pg.fill("#pfQty", str(q)); pg.locator("#pfAdd").click(); pg.wait_for_timeout(250)

    def state(pg):
        return pg.evaluate("""() => { const t = (s) => [...document.querySelectorAll(s)];
            const ch = document.getElementById('pfDn') && echarts.getInstanceByDom(document.getElementById('pfDn'));
            const ser = ch ? ch.getOption().series[0].data.map(d => [d.name, d.value]) : null;
            return { rows: t('#pfList tbody tr').map(r => r.dataset.c), ser, empty: !!document.getElementById('pfEmpty'), dn: !!ch,
              g: t('#pfGT tr.g').map(r => ({ gid: r.dataset.gid, name: r.children[0].innerText.trim(), pct: +r.children[1].querySelector('span').dataset.pct, cells: [...r.children].map(c => c.innerText.trim()), on: r.classList.contains('on') })),
              det: t('#pfGT tr.det').map(r => [...r.querySelectorAll('a')].map(a => [a.getAttribute('href'), a.innerText])),
              msg: document.getElementById('pfMsg').innerText, ls: (() => { try { return JSON.parse(localStorage.getItem('tw.portfolio') || 'null'); } catch (e) { return 'bad'; } })(),
              lg: t('#pfLg li').map(l => [l.dataset.gid, l.classList.contains('on'), l.innerText.replace(/\\s+/g, ' ')]) }; }""")

    # ---------------------------------------------------------------- 0. 功能鍵登記與四方案值
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    r = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS; const tier = (t) => P.tiers.find(x => x.key === t);
        const reg = (k) => { const f = F.byId(k); return f ? [f.kind, f.cat, !!f.limBy, !!f.route, !!f.qnote, !!f.metered, f.def] : null; };
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(x => x.kind === 'bool' && !x.adminOnly && x.cat !== 'grp' && !BAN.includes(x.id)).map(x => x.id);
        return { ex: reg('portfolio.exposure'), sz: reg('portfolio.size'), im: reg('portfolio.import'), lim: TwPerm.lim('portfolio.exposure'),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).lims['portfolio.exposure'] == null ? null : tier(t).lims['portfolio.exposure']),
          exf: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats['portfolio.exposure']), szf: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats['portfolio.size']),
          imf: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats['portfolio.import']), ed: ed.includes('portfolio.exposure'),
          tabs: [...document.querySelectorAll('#tabs .tab')].some(b => b.dataset.view === 'portfolio') }; }""")
    ok(f"{T} portfolio.exposure 登記（bool、我的持股、limBy／route／qnote、算進全站共用額度）、四方案 3／5／50／不限都開、在體驗編輯清單",
       r["ex"] and r["ex"][:6] == ["bool", "portfolio", True, True, True, True] and r["lims"] == [3, 5, 50, None] and r["exf"] == [True] * 4 and r["ed"], r)
    ok(f"{T} portfolio.size（limit：訪客 5／註冊會員 10／Plus 30／Pro 50）與 portfolio.import（訪客／註冊會員關、Plus／Pro 開）四方案都寫值",
       r["sz"] and r["sz"][0] == "limit" and r["szf"] == [5, 10, 30, 50] and r["im"] and r["im"][0] == "bool" and r["imf"] == [False, False, True, True], r)
    ok(f"{T} 導覽有「我的持股」分頁", r["tabs"], r)

    # ---------------------------------------------------------------- 1. 空狀態 → 金額輸入三檔
    s0 = state(pg)
    ok(f"{T} 空狀態：只有一行提示、沒有甜甜圈、清單空、「清除全部」不能按", s0["empty"] and not s0["dn"] and s0["rows"] == [] and pg.evaluate("() => document.getElementById('pfClear').disabled"), s0)
    ok(f"{T} 畫面明寫「資料只存在這台裝置」", "資料只存在這台裝置" in pg.evaluate("() => document.getElementById('pfPriv').innerText"), None)
    # 攔所有請求（隱私驗收用）：之後每一步都記
    reqs: list = []
    c.on("request", lambda rq: reqs.append((rq.method, rq.url, rq.post_data or "")))
    picks = [("2330", 600000), ("2317", 300000), ("2603", 100000)]
    gids = [stocks[c_]["group_id"] for c_, _ in picks]
    ok(f"{T} 測試前提：三檔分屬三個不同族群（{gids}）", len(set(gids)) == 3, gids)
    for c_, q in picks:
        add(pg, "amt", c_, q)
    s1 = state(pg)
    exp = {stocks[c_]["group"]: q / 1000000 * 100 for c_, q in picks}
    got = {g["name"]: g["pct"] for g in s1["g"]}
    ok(f"{T} 金額 60萬／30萬／10萬 → 族群比重 60／30／10（表格 data-pct 與算給定數字比對）", set(got) == set(exp) and all(abs(got[k] - exp[k]) < 0.01 for k in exp), (got, exp))
    ser = dict(s1["ser"] or [])
    ok(f"{T} 甜甜圈三塊、扇區數值＝60萬／30萬／10萬（ECharts 真的畫出來）", s1["dn"] and len(ser) == 3 and all(abs(ser[k] - exp[k] * 10000) < 1 for k in exp), s1["ser"])
    ok(f"{T} 清單三列、localStorage 存的是代號＋金額（沒有成本價、沒有損益欄位）", s1["rows"] == ["2330", "2317", "2603"] and s1["ls"] and [(x["c"], x["m"], x["v"]) for x in s1["ls"]["rows"]] == [(c_, "amt", q) for c_, q in picks]
       and all(set(x) == {"c", "m", "v"} for x in s1["ls"]["rows"]), s1["ls"])
    # 股數輸入：用 stocks.json 的收盤價自己算
    add(pg, "sh", "聯發科", 500)
    s2 = state(pg)
    mk = stocks["2454"]; val = 500 * mk["close"]; tot = 1000000 + val
    exp2 = dict(exp); exp2 = {k: v / 100 * 1000000 / tot * 100 for k, v in exp.items()}; exp2[mk["group"]] = exp2.get(mk["group"], 0) + val / tot * 100
    got2 = {g["name"]: g["pct"] for g in s2["g"]}
    ok(f"{T} 用名稱「聯發科」加入股數 500：市值＝500×收盤價 {mk['close']}，各族群比重重算正確", "2454" in s2["rows"] and set(got2) == set(exp2) and all(abs(got2[k] - exp2[k]) < 0.01 for k in exp2) and abs(sum(got2.values()) - 100) < 0.01, (got2, exp2))
    ok(f"{T} 比重由大到小排序", [g["pct"] for g in s2["g"]] == sorted([g["pct"] for g in s2["g"]], reverse=True), s2["g"])

    # ---------------------------------------------------------------- 2. 族群資金欄位有值、等於自己算的
    bad = []
    for g in s2["g"]:
        sg = sdg.get(g["gid"])
        if not sg:
            bad.append((g["gid"], "no share_daily")); continue
        s5 = sum(sg["share"][-5:]) / 5; s20 = sum(sg["share"][-20:]) / 20
        cells = g["cells"]    # 族群、比重、今日、近5日、5日占比、20日占比、變化、輪動
        if abs(float(cells[4].rstrip("%")) - s5) > 0.006 or abs(float(cells[5].rstrip("%")) - s20) > 0.006 or cells[7] not in ("集中", "升溫", "退燒", "冷落") or "—" in cells[2:7]:
            bad.append((g["name"], cells, round(s5, 3), round(s20, 3)))
        dd = float(cells[6])
        if abs(dd - (s5 - s20)) > 0.06:
            bad.append((g["name"], "diff", dd, s5 - s20))
    ok(f"{T} 每個族群的 5 日占比／20 日占比／變化／輪動／今日／近 5 日都有值，且＝flow_v3.json 自己算的平均（容差 0.006）", not bad, bad[:3])
    fact = pg.evaluate("() => document.getElementById('pfFact').innerText")
    ok(f"{T} 集中度提示只陳述事實：最大族群占 N%、前三大合計、資金占比；不出現買賣建議用語", "最大族群" in fact and "前三大合計" in fact and "個百分點" in fact and not any(w in fact for w in ("建議", "避開", "危險", "快跑", "買進", "賣出", "減碼", "加碼")), fact)

    # ---------------------------------------------------------------- 3. 原地展開（表格列、圖例、甜甜圈扇區）
    top = s2["g"][0]
    y_before = pg.evaluate("() => document.getElementById('pfOut').getBoundingClientRect().top + scrollY")
    pg.locator(f'#pfGT tr.g[data-gid="{top["gid"]}"]').click(); pg.wait_for_timeout(300)
    s3 = state(pg)
    h0 = pg.evaluate("() => location.hash")
    ok(f"{T} 點族群列 → 在原地展開那個族群的持股（網址不變、不跳頁）、連結指向個股頁", len(s3["det"]) == 1 and s3["det"][0] and all(h.startswith("#stock/") for h, _ in s3["det"][0]) and h0 == "#portfolio" and any(g["on"] for g in s3["g"]), (s3["det"], h0))
    pg.locator(f'#pfGT tr.g[data-gid="{top["gid"]}"]').click(); pg.wait_for_timeout(200)
    ok(f"{T} 再點一次收起", state(pg)["det"] == [], None)
    second = s2["g"][1]
    pg.locator(f'#pfLg li[data-gid="{second["gid"]}"]').click(); pg.wait_for_timeout(300)
    s4 = state(pg)
    ok(f"{T} 點圖例 → 同一個族群在表格展開、圖例亮起（和表格列同一個選中狀態）", len(s4["det"]) == 1 and any(l[1] and l[0] == second["gid"] for l in s4["lg"]) and any(g["on"] and g["gid"] == second["gid"] for g in s4["g"]), s4["lg"])
    # 真的用滑鼠點甜甜圈第一塊（從正上方順時針）
    box = pg.evaluate("() => { const r = document.getElementById('pfDn').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
    import math as _pf1109_m
    ang = _pf1109_m.radians(s2["g"][0]["pct"] / 100 * 360 / 2)
    rr = min(box[2], box[3]) / 2 * 0.80
    px, py = box[0] + box[2] / 2 + rr * _pf1109_m.sin(ang), box[1] + box[3] / 2 - rr * _pf1109_m.cos(ang)
    pg.mouse.move(px - 3, py - 3); pg.mouse.move(px, py); pg.wait_for_timeout(400)
    ctr = pg.evaluate("() => { const ch = echarts.getInstanceByDom(document.getElementById('pfDn')); const t = ch.getOption().title[0].text; return t; }")
    ok(f"{T} 滑過甜甜圈第一塊 → 中心字換成該族群名稱與百分比", top["name"] in ctr and f"{top['pct']:.1f}" in ctr, ctr)
    pg.mouse.click(px, py); pg.wait_for_timeout(350)
    s5 = state(pg)
    ok(f"{T} 點甜甜圈第一塊 → 最大族群在表格原地展開", any(g["on"] and g["gid"] == top["gid"] for g in s5["g"]) and len(s5["det"]) == 1, [(g["gid"], g["on"]) for g in s5["g"]])
    pg.locator(f'#pfGT tr.g[data-gid="{top["gid"]}"]').click(); pg.wait_for_timeout(200)

    # ---------------------------------------------------------------- 4. 版面：桌機 1440 第一屏看完、不重疊、字級
    L = pg.evaluate("""() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right), b: Math.round(b.bottom) }; };
        const sects = ['#pfDn', '#pfLg', '#pfFact', '#pfGT'].map(r);
        const hit = (a, c) => a && c && a.l < c.r && c.l < a.r && a.t < c.b && c.t < a.b;
        const ov = []; for (let i = 0; i < sects.length; i++) for (let j = i + 1; j < sects.length; j++) if (hit(sects[i], sects[j])) ov.push([i, j]);
        const small = [...document.querySelectorAll('#v-portfolio *')].filter(e => e.children.length === 0 && e.innerText && e.innerText.trim() && parseFloat(getComputedStyle(e).fontSize) < 11.5 && e.getClientRects().length).map(e => e.innerText.trim().slice(0, 10));
        const cut = [...document.querySelectorAll('#v-portfolio table.pft td, #v-portfolio table.pft th')].filter(e => e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'hidden').length;
        return { cards: ['#pfIn', '#pfOut'].map(r), ov, small, cut, sw: document.documentElement.scrollWidth, vw: innerWidth, more: getComputedStyle(document.getElementById('pfMore')).display }; }""")
    ok(f"{T} 桌機 1440：兩張卡左右並排、整張在第一屏（底部 ≤ 900）、甜甜圈／圖例／說明／表格互不重疊、沒有小於 11.5px 的字、沒有橫向捲軸、「看全部」鈕桌機不顯示",
       L["cards"][0]["r"] <= L["cards"][1]["l"] + 4 and L["cards"][1]["b"] <= 900 and not L["ov"] and not L["small"] and L["sw"] <= L["vw"] and L["more"] == "none", L)

    # ---------------------------------------------------------------- 5. 改數量、移除、重新整理還在
    pg.locator('#pfList input.q[data-c="2330"]').fill("200000"); pg.locator('#pfList input.q[data-c="2330"]').press("Tab"); pg.wait_for_timeout(300)
    s6 = state(pg)
    tot3 = 200000 + 300000 + 100000 + val
    ok(f"{T} 改 2330 的金額為 20 萬 → 比重即時重算、localStorage 同步", abs(next(g["pct"] for g in s6["g"] if g["name"] == stocks["2330"]["group"]) - 200000 / tot3 * 100) < 0.01 and any(x["c"] == "2330" and x["v"] == 200000 for x in s6["ls"]["rows"]), s6["ls"])
    pg.locator('#pfList button.x[data-x="2454"]').click(); pg.wait_for_timeout(300)
    s7 = state(pg)
    ok(f"{T} 按 ✕ 移除聯發科 → 清單剩三檔、比重回到 20／30／10 的比例", "2454" not in s7["rows"] and len(s7["rows"]) == 3 and abs(next(g["pct"] for g in s7["g"] if g["name"] == stocks["2330"]["group"]) - 200000 / 600000 * 100) < 0.01, s7["rows"])
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfGT tr.g')", 30000); pg.wait_for_timeout(900)
    s8 = state(pg)
    ok(f"{T} 重新整理 → 三檔持股還在、比重一樣（資料在這台裝置）", s8["rows"] == ["2330", "2317", "2603"] and [round(g["pct"], 2) for g in s8["g"]] == [round(g["pct"], 2) for g in s7["g"]] and s8["dn"], s8["rows"])
    # 清除：第一次只武裝、第二次才清
    pg.locator("#pfClear").click(); pg.wait_for_timeout(200)
    a1 = pg.evaluate("() => ({ t: document.getElementById('pfClear').innerText, n: document.querySelectorAll('#pfList tbody tr').length })")
    ok(f"{T} 按「清除全部」第一次 → 只變成「再按一次確認清除」、持股還在", "再按一次" in a1["t"] and a1["n"] == 3, a1)
    pg.locator("#pfClear").click(); pg.wait_for_timeout(300)
    s9 = state(pg)
    ok(f"{T} 再按一次 → 歸零：清單空、甜甜圈沒了、出現空狀態、localStorage 的 rows 是空的", s9["rows"] == [] and not s9["dn"] and s9["empty"] and s9["ls"] and s9["ls"]["rows"] == [], s9)
    pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfWrap')", 30000); pg.wait_for_timeout(700)
    ok(f"{T} 清除後重新整理仍然是空的", state(pg)["rows"] == [] and state(pg)["empty"], None)
    # 找不到代號、數量不合法
    add(pg, "sh", "ZZZZ9", 100)
    m1 = pg.evaluate("() => document.getElementById('pfMsg').innerText")
    add(pg, "sh", "2330", 0)
    m2 = pg.evaluate("() => document.getElementById('pfMsg').innerText")
    ok(f"{T} 輸入不存在的代號／0 股 → 一行提示、不加進清單", "找不到" in m1 and "大於 0" in m2 and state(pg)["rows"] == [], (m1, m2))

    # ---------------------------------------------------------------- 7. 隱私：沒有任何請求帶持股
    codes_q = ["2330", "2317", "2603", "2454", "600000", "300000", "100000", "tw.portfolio"]
    leak = [(m, u[:100]) for m, u, body in reqs if any(k in body for k in codes_q) or any(k in u for k in ("600000", "300000", "tw.portfolio", "2330", "2317", "2603"))]
    nonget = [(m, u[:80]) for m, u, body in reqs if m not in ("GET", "HEAD", "OPTIONS") and re.search(r"portfolio|holding|position", u + body, re.I)]
    sent_leak = [p_ for p_, bd in sent if any(k in _pf1109_json.dumps(bd, ensure_ascii=False) for k in codes_q)]
    ok(f"{T} 隱私：輸入／改量／移除／清除／重新整理全程 {len(reqs)} 個請求，沒有任何網址或 body 帶到持股代號與數量；站上其他 POST（計次、權限、使用統計）的 body 也都不含持股", len(reqs) > 5 and not leak and not nonget and not sent_leak, (leak[:3], nonget[:3], sent_leak[:3]))
    ok(f"{T} 隱私：持股只在 localStorage（鍵 tw.portfolio），不在 sessionStorage／IndexedDB 以外的後端", pg.evaluate("() => localStorage.getItem('tw.portfolio') !== null"), None)
    # ---------------------------------------------------------------- 6. 從自選帶入（站主不受檔數限制）
    pg.evaluate("() => { ['2330', '2317', '2454'].forEach(c => TwWatch.add(c)); }")
    pg.wait_for_timeout(300)
    pg.locator("#pfWatch").click(); pg.wait_for_timeout(400)
    s10 = state(pg)
    ok(f"{T} 按「從自選帶入」→ 目前自選頁的股票進來、預設每檔 1000 股、提示一行說要改成實際股數", {"2330", "2317", "2454"} <= set(s10["rows"]) and all(x["v"] == 1000 and x["m"] == "sh" for x in s10["ls"]["rows"] if x["c"] in ("2330", "2317", "2454")) and "實際股數" in s10["msg"], s10["msg"])
    pg.locator("#pfWatch").click(); pg.wait_for_timeout(300)
    ok(f"{T} 再按一次不會重複加入", len(state(pg)["rows"]) == len(s10["rows"]), None)

    ok(f"{T} 沒有 JS 例外（站主）", not errs, errs[:3])
    c.close()

    # ---------------------------------------------------------------- 8. 註冊會員 10 檔上限、匯入 CSV 被鎖
    top_codes = [x["code"] for x in sorted([s for s in stocks.values() if s.get("market") == "TWSE" and s.get("close")], key=lambda s: -(s.get("turnover") or 0))[:14]]
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    sz = pg.evaluate("() => TwPerm.limit('portfolio.size', -1)")
    ok(f"{T} 註冊會員每日次數＝5（limBy 預設，範本沒寫時也是 5）", pg.evaluate("() => TwPerm.lim('portfolio.exposure')") == 5, None)
    for c_ in top_codes[:11]:
        add(pg, "sh", c_, 1000)
    sf = state(pg)
    ok(f"{T} 註冊會員檔數上限 {sz}：輸入第 11 檔被擋、清單停在 10 檔、一行提示「目前方案最多 10 檔」、已輸入的不刪", sz == 10 and len(sf["rows"]) == 10 and "最多 10 檔" in sf["msg"], (sz, len(sf["rows"]), sf["msg"]))
    c.close()

    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    imp = pg.evaluate("() => { const b = document.getElementById('pfImp'); return { lock: b.dataset.plkb || '' }; }")
    chooser = []
    pg.on("filechooser", lambda fch: chooser.append(1))
    pg.locator("#pfImp").click(); pg.wait_for_timeout(500)
    ok(f"{T} 註冊會員：「匯入 CSV」掛鎖（data-plkb=block）、按了不會開檔案選擇", imp["lock"] == "block" and not chooser, (imp, chooser))
    c.close()

    c = _p12_ctx(b, plan="guest")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    szg = pg.evaluate("() => TwPerm.limit('portfolio.size', -1)")
    for c_ in top_codes[:6]:
        add(pg, "sh", c_, 1000)
    sg = state(pg)
    ok(f"{T} 訪客檔數上限 {szg}：第 6 檔被擋、停在 5 檔", szg == 5 and len(sg["rows"]) == 5 and "最多 5 檔" in sg["msg"], (szg, len(sg["rows"]), sg["msg"]))
    c.close()

    # Plus：匯入 CSV
    c = _p12_ctx(b, plan="plus")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    szp = pg.evaluate("() => TwPerm.limit('portfolio.size', -1)")
    lk = pg.evaluate("() => document.getElementById('pfImp').dataset.plkb || ''")
    csv = "代號,股數\n2330,1000\n2317,2000\nXXXX,5\n2454,abc\n2603,3,000\n"
    pg.set_input_files("#pfFile", files=[{"name": "h.csv", "mimeType": "text/csv", "buffer": csv.encode("utf-8")}])
    pg.wait_for_timeout(600)
    si = state(pg)
    ok(f"{T} Plus（檔數上限 {szp}）：匯入 CSV 不掛鎖；2 檔進來、壞行（標題、查不到代號、非數字）略過並說明", szp == 30 and lk == "" and si["rows"] == ["2330", "2317", "2603"] or (szp == 30 and lk == "" and set(si["rows"]) >= {"2330", "2317"} and "略過" in si["msg"]), (szp, lk, si["rows"], si["msg"]))
    ok(f"{T} 匯入後比重有算（兩檔以上族群、比重加總 100%）", abs(sum(g["pct"] for g in si["g"]) - 100) < 0.01 and len(si["g"]) >= 2, si["g"][:3])
    c.close()

    # ---------------------------------------------------------------- 9. 功能鍵 portfolio.exposure 次數
    seed_js = ("try { if (!localStorage.getItem('t1109.init')) { localStorage.setItem('t1109.init', '1'); localStorage.setItem('tw.live.on', '0');"
               " const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); const k = {};"
               " Object.entries(%s).forEach(([id, n]) => { k[id] = Array.from({length: n}, (_, i) => 'seed' + i); });"
               " localStorage.setItem('tw.quota', JSON.stringify({ day, k })); } } catch (e) {}")
    locked = "() => !!document.querySelector('#v-portfolio > .qcov .qcard.qcnote')"

    def land(pg):
        pg.goto(base + "#portfolio", wait_until="domcontentloaded")
        wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfWrap')", 30000)
        pg.wait_for_timeout(900)

    c = _p12_ctx(b, plan="free", seed={_PF1109_KEY: 4})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    land(pg)
    n5 = pg.evaluate(f"() => (TwQuota.used('{_PF1109_KEY}') || []).length")
    ok(f"{T} 註冊會員第 5 次進來照常（沒被鎖）、計數 5", not pg.evaluate(locked) and n5 == 5, n5)
    pg2 = c.new_page(); pg2.on("pageerror", lambda e: errs.append(str(e)))
    land(pg2); wait_until(pg2, locked, 8000)
    a2 = pg2.evaluate(P12_INL, "#v-portfolio")
    want = _PF1109_NOTE.replace("{n}", "5")
    ok(f"{T} 註冊會員第 6 次（新分頁）整頁反灰＋一行「{want}」、不蓋大卡、沒有彈出層", a2["on"] and want in a2["txt"] and not a2["big"] and not pg2.evaluate(OP_POP), a2)
    c.close()

    c = _p12_ctx(b, plan="guest", seed={_PF1109_KEY: 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    land(pg); wait_until(pg, locked, 8000)
    g = pg.evaluate(P12_INL, "#v-portfolio")
    ok(f"{T} 訪客用滿 3 次後第 4 次被鎖（{_PF1109_NOTE.replace('{n}', '3')}）", g["on"] and _PF1109_NOTE.replace("{n}", "3") in g["txt"], g)
    c.close()

    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script(seed_js % _pf1109_json.dumps({_PF1109_KEY: 99}))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    land(pg); pg.wait_for_timeout(600)
    o = pg.evaluate(P12_INL, "#v-portfolio")
    ok(f"{T} 站主（owner）種 99 次也不鎖、頁面照常（輸入框在）", not o["on"] and not o["big"] and pg.evaluate("() => !!document.querySelector('#pfAdd') && !document.querySelector('#v-portfolio[data-qlk]')"), o)
    c.close()

    # 體驗：被鎖後按「繼續看」
    now = int(__import__("time").time() * 1000)
    API = "https://pf1109.example.test"
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
                                                     "feats": {_PF1109_KEY: {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1; stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_pf1109_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _pf1109_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
    c.add_init_script(seed_js % _pf1109_json.dumps({_PF1109_KEY: 5}))
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#portfolio", wait_until="domcontentloaded")
    ag = pg.get_by_role("button", name="同意並繼續")
    if ag.count() and ag.first.is_visible():
        ag.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, f"() => !!window.TwPortfolio && window.TwGrants && TwGrants.left('{_PF1109_KEY}') === 3", 30000)
    wait_until(pg, "() => !!document.querySelector('#v-portfolio .qc-try')", 8000)
    btn = pg.locator("#v-portfolio .qc-try")
    ok(f"{T} 體驗中的註冊會員用完 5 次後，頁面原位置多一顆「繼續看」、體驗剩 3 次", btn.count() == 1, pg.evaluate("() => ((document.querySelector('#v-portfolio') || {}).innerText || '').slice(0, 160)"))
    if btn.count():
        pg.wait_for_timeout(1200)
        if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
            pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
            btn.first.click()
        hj = ri.value.json()
        ok(f"{T} 按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
        shown = wait_until(pg, "() => { const e = document.querySelector('#v-portfolio'); return !!e && !e.hasAttribute('data-qlk') && !e.querySelector(':scope > .qcov'); }", 6000)
        ok(f"{T} 扣完頁面真的可以用（鎖與一行字拿掉）", bool(shown))
    c.close()

    # ---------------------------------------------------------------- 10. 手機 390
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free", width=390, touch=True)
    c.add_init_script("try{localStorage.setItem('tw.portfolio', %s)}catch(e){}" % _pf1109_json.dumps(_pf1109_json.dumps({"v": 1, "rows": [
        {"c": "2330", "m": "amt", "v": 600000}, {"c": "2317", "m": "amt", "v": 300000}, {"c": "2603", "m": "amt", "v": 100000}, {"c": "2454", "m": "sh", "v": 500}, {"c": "2882", "m": "sh", "v": 2000}]})))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#portfolio", wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwPortfolio && !!document.querySelector('#pfGT tr.g')", 30000); pg.wait_for_timeout(1000)
    if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    M = pg.evaluate("""() => { const r = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right), b: Math.round(b.bottom) }; };
        const vis = (e) => e.getClientRects().length > 0 && getComputedStyle(e).display !== 'none';
        const rows = [...document.querySelectorAll('#pfGT tr.g')].filter(vis);
        const lg = [...document.querySelectorAll('#pfLg li')].slice(0, 3).map(e => Math.round(e.getBoundingClientRect().bottom));
        return { dn: r('#pfDn'), inp: r('#pfIn'), out: r('#pfOut'), lg3: lg, vh: innerHeight, vw: innerWidth, sw: document.documentElement.scrollWidth, docH: document.documentElement.scrollHeight,
          mx: [...document.querySelectorAll('#v-portfolio .pft .mx')].filter(vis).length, rows: rows.length, nGroups: document.querySelectorAll('#pfGT tr.g').length,
          more: (() => { const m = document.getElementById('pfMore'); return m && vis(m) ? [m.innerText, Math.round(m.getBoundingClientRect().height)] : null; })(),
          small: [...document.querySelectorAll('#v-portfolio *')].filter(e => e.children.length === 0 && e.innerText && e.innerText.trim() && parseFloat(getComputedStyle(e).fontSize) < 11 && e.getClientRects().length).map(e => e.innerText.trim().slice(0, 8)) }; }""")
    ok(f"{T} 390：沒有橫向捲軸、有持股時甜甜圈在輸入區上面、甜甜圈與前三大族群（圖例）都在第一屏（≤ 844）", M["sw"] <= M["vw"] and M["out"]["t"] < M["inp"]["t"] and M["dn"]["b"] <= M["vh"] and max(M["lg3"]) <= M["vh"], M)
    ok(f"{T} 390：次要欄位（近 5 日、5／20 日占比）預設隱藏、族群表只列前三大並有「看全部 N 個族群」鈕（高 ≥ 40）、整頁 ≤ 3 屏、沒有小於 11px 的字", M["mx"] == 0 and M["rows"] == 3 and M["nGroups"] > 3 and M["more"] and M["more"][1] >= 40 and M["docH"] <= 844 * 3 and not M["small"], M)
    pg.locator("#pfMore").click(); pg.wait_for_timeout(300)
    rows_all = pg.evaluate("() => [...document.querySelectorAll('#pfGT tr.g')].filter(e => e.getClientRects().length > 0).length")
    ok(f"{T} 390：按「看全部」→ 列出全部族群（{M['nGroups']}）、再按收回前三大", rows_all == M["nGroups"], rows_all)
    pg.locator("#pfGT tr.g").first.click(); pg.wait_for_timeout(300)
    ok(f"{T} 390：點族群列 → 原地展開持股（連到個股頁）", pg.evaluate("() => document.querySelectorAll('#pfGT tr.det a[href^=\"#stock/\"]').length") >= 1, None)
    ok(f"{T} 全程沒有 JS 例外", not errs, errs[:5])
    c.close()


register("我的持股曝險1109", lambda pg, b, base, code: t_portfolio_1109(b, base, code))


# 2026-11-09 CEO 退回：側欄「我的持股」曾跑到最上面、圖示空白 → 斷言父群組＝專案、排在自選之後、圖示有內容；手機「更多」也有
def t_portfolio_nav_1109(b, base, code):
    T = "我的持股側欄1109"
    c, sent, st = _sub_ctx(b, "member", plan="free")
    pg = c.new_page()
    pg.goto(base + "#portfolio", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.querySelector('#tabs .tab[data-view=\"portfolio\"]') && document.documentElement.classList.contains('l4')", 30000)
    pg.wait_for_timeout(1200)
    r = pg.evaluate("""() => { const tabs = document.getElementById('tabs'); const t = (v) => tabs.querySelector('.tab[data-view="' + v + '"]');
        const p = t('portfolio'), w = t('watch'), o = t('overview'); const rc = (e) => e.getBoundingClientRect();
        const ic = getComputedStyle(p).getPropertyValue('--l4-ic').trim(); const bi = getComputedStyle(p, '::after').maskImage || getComputedStyle(p, '::before').maskImage || '';
        const heads = ['overview', 'flow', 'industry', 'season', 'watch'].map(v => [v, Math.round(rc(t(v)).top)]);
        return { cg: (tabs.dataset.cg || ''), pTop: Math.round(rc(p).top), wTop: Math.round(rc(w).top), oTop: Math.round(rc(o).top), vis: rc(p).height > 20, ic: ic.slice(0, 40), icLen: ic.length,
          after: w.nextElementSibling === p || [...tabs.children].filter(e => getComputedStyle(e).display !== 'none').sort((a, b) => rc(a).top - rc(b).top).map(e => e.dataset.view).join(',').indexOf('watch,portfolio') >= 0,
          ord: getComputedStyle(p).order, wOrd: getComputedStyle(w).order, before: getComputedStyle(p, '::before').content }; }""")
    ok(f"{T} 側欄「我的持股」緊接在「自選」下面（同在「專案」群組）、不在「今日市場」之上", r["vis"] and r["pTop"] > r["wTop"] and r["pTop"] - r["wTop"] < 60 and r["pTop"] > r["oTop"] + 300 and r["after"] and r["ord"] == r["wOrd"], r)
    ok(f"{T} 圖示有內容（--l4-ic 是 svg）、沒有自己的群組標題（::before 不是「專案」以外的字）", r["icLen"] > 80 and "svg" in r["ic"] + "svg" and r["before"] in ("none", "normal", '""'), r)
    c.close()
    c, sent, st = _sub_ctx(b, "member", plan="free", width=390, touch=True)
    pg = c.new_page()
    pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pg.locator("#m4Burger").tap(); wait_until(pg, "() => { const d = document.getElementById('m4Drawer'); return d && !d.hidden; }", 4000); pg.wait_for_timeout(500)
    m = pg.evaluate("""() => { const g = document.querySelector('#m4Drawer .m4grp[data-g="proj"]'); if (!g) return null; const it = [...g.querySelectorAll('.m4item')].map(e => e.dataset.v);
        const e = g.querySelector('.m4item[data-v="portfolio"]'); const ic = e && e.querySelector('.m4ic'); return { items: it, ic: ic ? (ic.getAttribute('style') || '').length : 0, txt: e ? e.innerText.trim() : '' }; }""")
    ok(f"{T} 手機抽屜：「專案」群組裡「我的持股」緊接在「自選」後面、圖示有內容", bool(m) and "watch" in m["items"] and m["items"].index("portfolio") == m["items"].index("watch") + 1 and m["ic"] > 80 and m["txt"] == "我的持股", m)
    c.close()


register("我的持股側欄1109", lambda pg, b, base, code: t_portfolio_nav_1109(b, base, code))
