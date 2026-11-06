# 驗收段落「漲跌家數字卡1106」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_p12_ctx()、_sub_ctx()、OP_POP、P12_QN 直接可用，不要 import _uitest。
# Andy 2026-11-06：「這邊多一個切換，可以看到全部族群的字卡，整齊排列 字卡需要剛好矩陣填滿，並且點擊該族群也會有對應股票字卡，
#   字卡顏色 -10~+10% 深綠~深紅，目的是更直觀看到 哪些市場跌停 狀況，以及可以依照級距篩選」
# 真的操作：切到「族群字卡」→ 矩陣每一列都填滿 → 顏色紅漲綠跌 → 級距鈕多選（家數對直方圖）→ 點族群出個股字卡 → 返回 → 點個股進個股頁
#   → 上市／上櫃一起作用 → 點直方圖長條也加減同一組篩選 → 手機 390 不橫捲；
#   功能鍵 ov.advdec.tiles：註冊會員用到第 5 次、第 6 次被鎖（反灰＋一行字）、訪客 3 次、體驗額度按「繼續看」、站主不受限。
import json as _t1106_json
import pathlib as _t1106_pl

_T1106_KEY = "ov.advdec.tiles"
_T1106_NOTE = "今日 {n} 次已用完・Plus 以上可增加"


def t_advdec_tiles_1106(b, base, code):
    T = "漲跌家數字卡1106"
    errs: list = []
    sh = os.environ.get("TW_ADT_SHOTS")
    if sh:
        _t1106_pl.Path(sh).mkdir(parents=True, exist_ok=True)

    def shot(pg, name, sel="#ovBreadthCard"):
        if not sh:
            return
        try:
            pg.locator(sel).first.screenshot(path=str(_t1106_pl.Path(sh) / name))
        except Exception as ex:  # noqa: BLE001
            print("  截圖失敗", name, ex)

    def go(pg, h="#overview", t=25000):
        if pg.url == "about:blank":
            pg.goto(base + h, wait_until="domcontentloaded")
            wait_until(pg, "() => window.TwPerm && TwPerm.state().src === 'server' && !!window.TwQuota", 15000)
        else:
            pg.evaluate(f"() => {{ location.hash = '{h}'; }}")
        pg.evaluate("() => { const e = document.getElementById('ovBreadthCard'); if (e) e.scrollIntoView({ block: 'center' }); }")
        wait_until(pg, "() => { const e = document.getElementById('breadth'); return !!e && +e.dataset.total > 0 && !!echarts.getInstanceByDom(e); }", t)
        pg.wait_for_timeout(500)

    used = lambda pg: pg.evaluate(f"() => (TwQuota.used('{_T1106_KEY}') || []).length")  # noqa: E731
    pop = lambda pg: pg.evaluate(OP_POP)  # noqa: E731
    TILES = "() => document.querySelectorAll('#adtGrid .adt-g').length"
    SUMN = "() => [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.n), 0)"
    CHIP = "(i) => +document.querySelector('#adtBins button[data-b=\"' + i + '\"] em').textContent"
    MATRIX = """() => { const rows = [...document.querySelectorAll('#adtGrid .adt-row')]; if (!rows.length) return null;
        const g = document.getElementById('adtGrid').getBoundingClientRect();
        const full = rows.map(r => { const k = [...r.children].map(c => c.getBoundingClientRect()); const a = r.getBoundingClientRect();
          return { n: k.length, left: Math.abs(k[0].left - a.left), right: Math.abs(a.right - k[k.length - 1].right), minW: Math.min(...k.map(x => x.width)) }; });
        const per = full.slice(0, -1).map(x => x.n);
        return { rows: rows.length, tiles: full.reduce((a, x) => a + x.n, 0), cols: per.length ? per[0] : full[0].n, sameCols: per.every(x => x === per[0]),
                 lastFill: full[full.length - 1].n / (per.length ? per[0] : full[0].n), flush: full.every(x => x.left <= 1.5 && x.right <= 1.5), minW: Math.min(...full.map(x => x.minW)),
                 hScroll: document.getElementById('adtGrid').scrollWidth > document.getElementById('adtGrid').clientWidth + 1 }; }"""

    # ---------------------------------------------------------------- 0. 功能鍵登記、範本、體驗編輯器
    c = _p12_ctx(b, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    d = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, k = 'ov.advdec.tiles', tier = (x) => P.tiers.find(t => t.key === x);
        const BAN = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
        const ed = F.list.filter(f => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && !BAN.includes(f.id)).map(f => f.id);
        const f = F.byId(k);
        return { reg: f ? [f.kind, f.cat, !!f.limBy, !!f.route, f.qper, !!f.qspent, !!f.qcount, !!f.qblock] : null, free: TwPerm.lim(k), can: TwPerm.can(k),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).lims[k] == null ? null : tier(t).lims[k]), feats: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats[k]),
          inEditor: ed.includes(k) }; }""")
    ok(f"{T} 功能鍵 ov.advdec.tiles 登記了（bool、總覽、每點一次算一次、有計次與擋點選擇器）", d["reg"] == ["bool", "overview", True, True, "each", True, True, True], d["reg"])
    ok(f"{T} 註冊會員範本沒寫時：每日 5 次、開關是開的", d["free"] == 5 and d["can"] is True, (d["free"], d["can"]))
    ok(f"{T} plan_presets.js：訪客 3／註冊會員 5／Plus 50／Pro 不限（不寫）、四個方案都開", d["lims"] == [3, 5, 50, None] and d["feats"] == [True] * 4, d)
    ok(f"{T} 「編輯：新會員體驗」清單列得到這個鍵（不在法遵禁止清單，額度由 Andy 自己設）", d["inEditor"] is True)
    pg.evaluate("() => { try { localStorage.removeItem('tw.udMkt'); } catch (e) {} }")
    c.close()

    # ---------------------------------------------------------------- 1. 站主（不受限）：整條操作流程
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    c.add_init_script("try { localStorage.setItem('tw.theme', 'dark'); localStorage.setItem('tw.live.on', '0'); localStorage.removeItem('tw.udMkt'); } catch (e) {}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    dist_h = pg.evaluate("() => document.getElementById('ovBreadthCard').getBoundingClientRect().height")
    a0 = pg.evaluate("""() => ({ labels: [...document.querySelectorAll('#udView button')].map(x => x.textContent), on: [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v),
        tilesHidden: document.getElementById('adtWrap').hidden, chartVis: document.getElementById('breadthWrap').getClientRects().length > 0,
        vals: echarts.getInstanceByDom(document.getElementById('breadth')).getOption().series[0].data.map(d => d.value), total: +document.getElementById('breadth').dataset.total }); """)
    ok(f"{T} 右上有「分布｜族群字卡」，預設分布（直方圖在、字卡藏著）", a0["labels"] == ["分布", "族群字卡"] and a0["on"] == ["dist"] and a0["tilesHidden"] and a0["chartVis"], a0)
    vals0, total0 = a0["vals"], a0["total"]

    pg.click('#udView button[data-v="tiles"]'); pg.wait_for_timeout(600)
    wait_until(pg, TILES.replace("() =>", "() => !!document.querySelector('#adtGrid .adt-g') &&"), 6000)
    a1 = pg.evaluate("""() => ({ on: [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v), tilesVis: document.getElementById('adtWrap').getClientRects().length > 0,
        chartVis: document.getElementById('breadthWrap').getClientRects().length > 0, chips: [...document.querySelectorAll('#adtBins button')].map(x => x.firstChild.textContent),
        sub: document.getElementById('adtSub').innerText }); """)
    ok(f"{T} 按「族群字卡」→ 字卡出現、直方圖藏起來、鈕亮在族群字卡", a1["on"] == ["tiles"] and a1["tilesVis"] and not a1["chartVis"], a1)
    ok(f"{T} 級距鈕跟直方圖同一組 11 級（跌停、<-5、-5~-3、-3~-1、-1~0、平、0~1、1~3、3~5、>5、漲停）",
       a1["chips"] == ["跌停", "<-5", "-5~-3", "-3~-1", "-1~0", "平", "0~1", "1~3", "3~5", ">5", "漲停"], a1["chips"])
    ok(f"{T} 級距鈕上的家數＝直方圖每一根的家數", pg.evaluate("""(v) => [0,1,2,3,4,5,6,7,8,9,10].every(i => +document.querySelector('#adtBins button[data-b="' + i + '"] em').textContent === v[i])""", vals0), vals0)
    n_all = pg.evaluate(TILES)
    ok(f"{T} 全部族群都有字卡：族群數 ≥ 20、各族群家數加總＝直方圖的「共 N 檔」（{total0}）", n_all >= 20 and pg.evaluate(SUMN) == total0, (n_all, pg.evaluate(SUMN), total0))
    mx = pg.evaluate(MATRIX)
    ok(f"{T} 矩陣剛好填滿：每一整列欄數相同、每一列左右貼齊容器（含最後一列）、最後一列至少 60% 滿、不橫捲、字卡寬 ≥ 80",
       mx and mx["sameCols"] and mx["flush"] and mx["lastFill"] >= 0.6 and not mx["hScroll"] and mx["minW"] >= 80 and mx["tiles"] == n_all, mx)
    ok(f"{T} 切換不改變卡片高度（A9）：分布 {dist_h:.0f}px → 字卡 ±2px", abs(pg.evaluate("() => document.getElementById('ovBreadthCard').getBoundingClientRect().height") - dist_h) <= 2,
       pg.evaluate("() => document.getElementById('ovBreadthCard').getBoundingClientRect().height"))
    avgs = pg.evaluate("() => [...document.querySelectorAll('#adtGrid .adt-g')].map(g => +g.dataset.avg)")
    ok(f"{T} 預設依平均漲跌幅由高到低排", all(avgs[i] >= avgs[i + 1] for i in range(len(avgs) - 1)), avgs[:6])
    cl = pg.evaluate("""() => { const rgb = (e) => getComputedStyle(e).backgroundColor.match(/[\\d.]+/g).map(Number); const gs = [...document.querySelectorAll('#adtGrid .adt-g')];
        const top = gs[0], bot = gs[gs.length - 1]; return { top: rgb(top), bot: rgb(bot), topAvg: +top.dataset.avg, botAvg: +bot.dataset.avg }; }""")
    ok(f"{T} 顏色紅漲綠跌：最強那張偏紅（R>G）、最弱那張偏綠（G>R）", cl["topAvg"] > 0 > cl["botAvg"] and cl["top"][0] > cl["top"][1] and cl["bot"][1] > cl["bot"][0], cl)
    shot(pg, "desk_groups_dark.png")

    # ---- 級距篩選：跌停
    pg.click('#adtBins button[data-b="0"]'); pg.wait_for_timeout(500)
    f0 = pg.evaluate("""() => ({ n: document.querySelectorAll('#adtGrid .adt-g').length, sum: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.n), 0),
        ld: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.ld), 0), lu: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.lu), 0),
        pressed: [...document.querySelectorAll('#adtBins button.on')].map(x => x.dataset.b), clr: !document.getElementById('udSum').parentElement.querySelector('#adtClear').hidden }); """)
    c0 = pg.evaluate(CHIP, 0)
    ok(f"{T} 點「跌停」→ 只留下有跌停的族群、家數加總＝跌停那一級（{c0}）、每張都標跌停", f0["pressed"] == ["0"] and f0["sum"] == c0 and f0["ld"] == c0 and f0["lu"] == 0 and 0 < f0["n"] < n_all, (f0, c0, n_all))
    ok(f"{T} 篩選之後右上出現「清除篩選（1）」", f0["clr"] and "清除篩選（1）" in pg.evaluate("() => document.getElementById('adtClear').textContent"), f0)
    mx2 = pg.evaluate(MATRIX)
    ok(f"{T} 篩選後矩陣仍然填滿（欄數會跟著張數重算）", mx2 and mx2["sameCols"] and mx2["flush"] and not mx2["hScroll"], mx2)
    shot(pg, "desk_filter_limitdown.png")
    # 多選：再點漲停
    pg.click('#adtBins button[data-b="10"]'); pg.wait_for_timeout(400)
    c10 = pg.evaluate(CHIP, 10)
    f1 = pg.evaluate("() => ({ sum: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.n), 0), pressed: [...document.querySelectorAll('#adtBins button.on')].map(x => x.dataset.b) })")
    ok(f"{T} 多選：跌停＋漲停 → 家數加總＝兩級相加（{c0}+{c10}）", f1["pressed"] == ["0", "10"] and f1["sum"] == c0 + c10, (f1, c0, c10))
    # 篩選作用在直方圖：回到分布，沒選的長條淡掉
    pg.click('#udView button[data-v="dist"]'); pg.wait_for_timeout(700)
    dh = pg.evaluate("""() => { const e = document.getElementById('breadth'), c = echarts.getInstanceByDom(e); const d = c.getOption().series[0].data;
        return { op: d.map(x => x.itemStyle.opacity), w: e.clientWidth, h: e.clientHeight, vis: document.getElementById('breadthWrap').getClientRects().length > 0, canvas: !!e.querySelector('canvas') && e.querySelector('canvas').width > 0 }; }""")
    ok(f"{T} 切回分布：圖有高度、有畫出來；篩選選的兩級（跌停、漲停）亮、其他淡掉", dh["vis"] and dh["h"] > 200 and dh["w"] > 200 and dh["canvas"]
       and dh["op"][0] == 1 and dh["op"][10] == 1 and all(dh["op"][i] < 1 for i in range(1, 10)), dh)
    # 直方圖點長條 → 加減同一組篩選
    pg.evaluate("() => document.getElementById('breadth').scrollIntoView({ block: 'center' })"); pg.wait_for_timeout(400)
    bb = pg.evaluate("""(i) => { const e = document.getElementById('breadth'), c = echarts.getInstanceByDom(e);
        const p = c.convertToPixel({seriesIndex: 0}, [i, c.getOption().series[0].data[i].value / 2]); const r = e.getBoundingClientRect(); return {x: r.left + p[0], y: r.top + p[1]}; }""", 6 + 1)
    i_pick = 7
    pg.mouse.click(bb["x"], bb["y"]); pg.wait_for_timeout(700)
    pr = pg.evaluate("() => ({ size: AdvDec.size(), has: AdvDec.has(7), clr: document.getElementById('adtClear').textContent })")
    ok(f"{T} 點直方圖長條（1~3）→ 加進同一組篩選（變 3 級）、右上「清除篩選（3）」", pr["size"] == 3 and pr["has"] and "（3）" in pr["clr"], pr)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pg.click('#adtClear'); pg.wait_for_timeout(500)
    cz = pg.evaluate("() => ({ size: AdvDec.size(), hidden: document.getElementById('adtClear').hidden, op: echarts.getInstanceByDom(document.getElementById('breadth')).getOption().series[0].data.map(x => x.itemStyle.opacity) })")
    ok(f"{T} 按「清除篩選」→ 篩選清空、鈕收起、直方圖全部恢復", cz["size"] == 0 and cz["hidden"] and all(x == 1 for x in cz["op"]), cz)

    # ---- 點族群 → 個股字卡
    pg.click('#udView button[data-v="tiles"]'); pg.wait_for_timeout(500)
    wait_until(pg, TILES.replace("() =>", "() => !!document.querySelector('#adtGrid .adt-g') &&"), 6000)
    pg.click('#adtBins button[data-b="0"]'); pg.wait_for_timeout(400)        # 先篩跌停，再點進族群：個股字卡也只剩符合的
    gn = pg.evaluate("() => { const g = document.querySelector('#adtGrid .adt-g'); return { name: g.dataset.g, n: +g.dataset.n, ld: +g.dataset.ld }; }")
    pg.locator('#adtGrid .adt-g').first.click(); pg.wait_for_timeout(500)
    s1 = pg.evaluate("""() => ({ back: !!document.getElementById('adtBack'), head: document.querySelector('#adtSub .gn') && document.querySelector('#adtSub .gn').textContent,
        stocks: [...document.querySelectorAll('#adtGrid .adt-s')].map(a => ({ href: a.getAttribute('href'), txt: a.innerText, cls: a.className, pct: +a.dataset.pct, lim: !!a.querySelector('.lim') })),
        groups: document.querySelectorAll('#adtGrid .adt-g').length }); """)
    ok(f"{T} 點族群字卡（{gn['name']}）→ 變成它的個股字卡：有「← 返回族群」、標題是族群名、張數＝那張字卡的 {gn['n']} 檔、不再有族群字卡",
       s1["back"] and s1["head"] == gn["name"] and len(s1["stocks"]) == gn["n"] and s1["groups"] == 0, (s1["back"], s1["head"], len(s1["stocks"]), gn))
    ok(f"{T} 個股字卡：每張有名稱、代號、漲跌幅，連到 #stock/<代號>；篩選跌停 → 全部標「跌停」且漲跌幅 ≤ -9.5",
       all(re.match(r"^#stock/\d{4,6}[A-Z]?$", s["href"]) and re.search(r"\d{4,6}", s["txt"]) and "%" in s["txt"] and s["lim"] and "ld" in s["cls"].split() and s["pct"] <= -9.5 for s in s1["stocks"]), s1["stocks"][:3])
    mx3 = pg.evaluate(MATRIX)
    ok(f"{T} 個股字卡也是填滿的矩陣", mx3 and mx3["sameCols"] and mx3["flush"] and not mx3["hScroll"], mx3)
    shot(pg, "desk_stocks_limitdown.png")
    # 清掉篩選看整個族群的個股：有漲停／跌停以外的字卡
    pg.click('#adtClear'); pg.wait_for_timeout(400)
    s2 = pg.evaluate("() => ({ back: !!document.getElementById('adtBack'), n: document.querySelectorAll('#adtGrid .adt-s').length, lim: document.querySelectorAll('#adtGrid .adt-s .lim').length })")
    ok(f"{T} 清除篩選：停在同一個族群、個股字卡變回整個族群（{s2['n']} 檔 ≥ 之前 {gn['n']} 檔）", s2["back"] and s2["n"] >= gn["n"], s2)
    pg.click('#adtBack'); pg.wait_for_timeout(400)
    r1 = pg.evaluate("() => ({ groups: document.querySelectorAll('#adtGrid .adt-g').length, back: !!document.getElementById('adtBack') })")
    ok(f"{T} 按「返回族群」→ 回到全部族群字卡", r1["groups"] == n_all and not r1["back"], (r1, n_all))
    # 點個股字卡 → 個股頁
    pg.locator('#adtGrid .adt-g').first.click(); pg.wait_for_timeout(400)
    code0 = pg.evaluate("() => document.querySelector('#adtGrid .adt-s').getAttribute('href')")
    pg.locator('#adtGrid .adt-s').first.click(); pg.wait_for_timeout(900)
    ok(f"{T} 點個股字卡 → 進個股頁（{code0}）", pg.evaluate("() => location.hash") == code0, pg.evaluate("() => location.hash"))
    pg.evaluate("() => { location.hash = '#overview'; }")
    go(pg, "#overview")
    rs = pg.evaluate("() => ({ mode: [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v), sel: AdvDec.size() })")
    ok(f"{T} 離開總覽再回來：回到預設（分布、沒有篩選）", rs["mode"] == ["dist"] and rs["sel"] == 0, rs)

    # ---- 上市／上櫃一起作用
    pg.click('#udView button[data-v="tiles"]'); pg.wait_for_timeout(500)
    wait_until(pg, TILES.replace("() =>", "() => !!document.querySelector('#adtGrid .adt-g') &&"), 6000)
    pg.click('#udMkt button[data-m="twse"]'); pg.wait_for_timeout(700)
    tw = pg.evaluate("() => ({ sum: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.n), 0), total: +document.getElementById('breadth').dataset.total, tiles: document.querySelectorAll('#adtGrid .adt-g').length, mode: [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v) })")
    ok(f"{T} 按「上市」→ 仍在字卡模式、家數加總＝上市共 N 檔、族群字卡重算", tw["mode"] == ["tiles"] and tw["sum"] == tw["total"] and tw["total"] < total0 and tw["tiles"] > 0, (tw, total0))
    pg.click('#udMkt button[data-m="tpex"]'); pg.wait_for_timeout(700)
    tp = pg.evaluate("() => ({ sum: [...document.querySelectorAll('#adtGrid .adt-g')].reduce((a, g) => a + (+g.dataset.n), 0), total: +document.getElementById('breadth').dataset.total })")
    ok(f"{T} 按「上櫃」→ 家數加總＝上櫃共 N 檔，上市＋上櫃＝全部", tp["sum"] == tp["total"] and tw["total"] + tp["total"] <= total0, (tp, tw["total"], total0))
    pg.click('#udMkt button[data-m="all"]'); pg.wait_for_timeout(500)
    # 說明「?」換成字卡版
    pg.click('#ovBreadthCard .howbtn'); pg.wait_for_timeout(400)
    how = pg.evaluate("() => (document.querySelector('.howpop, #how-breadth, .pophow') || document.body).innerText")
    ok(f"{T} 字卡模式的「?」講得出顏色（-10% 深綠到 +10% 深紅）、等權平均、級距篩選", "-10%" in how and "等權" in how and "級距" in how, how[:200])
    pg.keyboard.press("Escape")
    ok(f"{T} 站主不受限：上面這一路已經點了十幾次（切換、級距、族群、上市／上櫃），全部照常、沒有被鎖、沒有計次", used(pg) == 0 and not pop(pg)
       and not pg.evaluate("() => !!document.querySelector('#udView button[data-qnote], #adtBins button[data-qnote]')"), used(pg))
    c.close()

    # ---------------------------------------------------------------- 2. 手機 390
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free", width=390, touch=True)
    c.add_init_script("try { localStorage.setItem('tw.live.on', '0'); localStorage.removeItem('tw.udMkt'); } catch (e) {}")
    pm = c.new_page(); pm.on("pageerror", lambda e: errs.append(str(e)))
    go(pm)
    pm.tap('#udView button[data-v="tiles"]'); pm.wait_for_timeout(600)
    wait_until(pm, TILES.replace("() =>", "() => !!document.querySelector('#adtGrid .adt-g') &&"), 6000)
    mm = pm.evaluate("""() => { const q = (s) => document.querySelector(s); const r = (e) => e.getBoundingClientRect(); const card = r(q('#ovBreadthCard'));
        return { docOverflow: document.documentElement.scrollWidth > innerWidth + 1, cardIn: card.left >= -0.5 && card.right <= innerWidth + 0.5,
                 segH: Math.min(...[...document.querySelectorAll('#udView button')].map(b => r(b).height)), chipH: Math.min(...[...document.querySelectorAll('#adtBins button')].map(b => r(b).height)),
                 fs: Math.min(...[...document.querySelectorAll('#adtWrap .adt-g .nm, #adtWrap .adt-g .pc, #adtBins button, #adtSub')].map(e => parseFloat(getComputedStyle(e).fontSize))),
                 gridVisible: r(q('#adtGrid')).height > 150, binsScroll: q('#adtBins').scrollWidth > q('#adtBins').clientWidth, tileH: r(q('#adtGrid .adt-g')).height }; }""")
    ok(f"{T} 手機 390：沒有橫向捲軸、卡片不超出螢幕、分段鈕與級距鈕高 ≥ 40（手指點得到）、字 ≥ 11px、字卡區 > 150px", not mm["docOverflow"] and mm["cardIn"] and mm["segH"] >= 40 and mm["chipH"] >= 40 and mm["fs"] >= 11 and mm["gridVisible"], mm)
    ok(f"{T} 手機 390：級距鈕一排放不下 → 框內橫拖（不換行）", mm["binsScroll"], mm)
    mxm = pm.evaluate(MATRIX)
    ok(f"{T} 手機 390：矩陣欄數自動適應（2～4 欄）、每列貼齊、不橫捲", mxm and 2 <= mxm["cols"] <= 4 and mxm["sameCols"] and mxm["flush"] and not mxm["hScroll"], mxm)
    pm.tap('#adtBins button[data-b="0"]'); pm.wait_for_timeout(400)
    pm.locator('#adtGrid .adt-g').first.tap(); pm.wait_for_timeout(500)
    ms = pm.evaluate("() => ({ back: !!document.getElementById('adtBack'), n: document.querySelectorAll('#adtGrid .adt-s').length, over: document.documentElement.scrollWidth > innerWidth + 1, backH: document.getElementById('adtBack').getBoundingClientRect().height })")
    ok(f"{T} 手機：手指點跌停鈕、點族群 → 個股字卡出現、「返回族群」鈕高 ≥ 32、沒有橫捲", ms["back"] and ms["n"] >= 1 and not ms["over"] and ms["backH"] >= 32, ms)
    shot(pm, "m390_stocks_limitdown.png")
    pm.tap('#adtBack'); pm.wait_for_timeout(300)
    pm.tap('#adtClear'); pm.wait_for_timeout(300)
    shot(pm, "m390_groups.png")
    pm.tap('#udView button[data-v="dist"]'); pm.wait_for_timeout(600)
    ok(f"{T} 手機：切回分布 → 圖回來、沒有橫捲", pm.evaluate("() => document.getElementById('breadth').clientHeight > 200 && document.documentElement.scrollWidth <= innerWidth + 1"))
    c.close()

    # ---------------------------------------------------------------- 3. 次數：註冊會員 5 次、訪客 3 次
    def spend(pg, n):
        """依序用掉 n 次：切進字卡(1)、點級距(2..)，每一次都算一次"""
        pg.click('#udView button[data-v="tiles"]'); pg.wait_for_timeout(350)
        wait_until(pg, "() => !!document.querySelector('#adtGrid .adt-g')", 6000)
        for i in range(n - 1):
            pg.click(f'#adtBins button[data-b="{[0, 1, 2, 3][i % 4]}"]'); pg.wait_for_timeout(250)

    c = _p12_ctx(b, plan="free", seed={_T1106_KEY: 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    spend(pg, 2)   # 3（種子）＋切進字卡＋點 1 個級距 ＝ 5
    ok(f"{T} 註冊會員第 5 次（種子 3 ＋ 切進字卡、點級距）照常、計數 5、沒有彈出層", used(pg) == 5 and not pop(pg), used(pg))
    before = pg.evaluate("() => AdvDec.size()")
    pg.click('#adtBins button[data-b="6"]', force=True); pg.wait_for_timeout(400)
    qn = pg.evaluate(P12_QN, ["#adtBins button", _T1106_KEY])
    ok(f"{T} 註冊會員第 6 次：點級距沒反應（篩選不變）、計數還是 5、沒有彈出層、鈕反灰＋一行「{_T1106_NOTE.replace('{n}', '5')}」（≥12px）",
       pg.evaluate("() => AdvDec.size()") == before and used(pg) == 5 and not pop(pg) and qn["q"] and qn["op"] < 0.6 and qn["note"] == _T1106_NOTE.replace("{n}", "5") and qn["fs"] >= 12, (qn, used(pg)))
    pg.click('#adtGrid .adt-g', force=True); pg.wait_for_timeout(300)
    ok(f"{T} 註冊會員用完：點族群也沒反應（還在族群字卡、沒有返回鈕）", pg.evaluate("() => !document.getElementById('adtBack') && document.querySelectorAll('#adtGrid .adt-g').length > 5"))
    shot(pg, "free_spent.png")
    # 已經在字卡裡：切回分布、再切進字卡 → 用完擋住（不再放行）
    pg.click('#udView button[data-v="dist"]'); pg.wait_for_timeout(400)
    ok(f"{T} 用完之後仍可切回「分布」（不擋退路）", pg.evaluate("() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)") == ["dist"])
    pg.click('#udView button[data-v="tiles"]', force=True); pg.wait_for_timeout(400)
    ok(f"{T} 用完之後再按「族群字卡」進不去（還是分布）", pg.evaluate("() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)") == ["dist"] and used(pg) == 5)
    c.close()

    c = _p12_ctx(b, plan="guest", seed={_T1106_KEY: 3})
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    go(pg)
    pg.click('#udView button[data-v="tiles"]', force=True); pg.wait_for_timeout(400)
    ok(f"{T} 訪客用滿 3 次後第 4 次被鎖（按「族群字卡」沒反應、一行「{_T1106_NOTE.replace('{n}', '3')}」）",
       pg.evaluate("() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)") == ["dist"] and used(pg) == 3 and not pop(pg)
       and _T1106_NOTE.replace("{n}", "3") in pg.evaluate("() => document.getElementById('ovBreadthCard').innerText"), (used(pg), pg.evaluate("() => document.getElementById('ovBreadthCard').innerText.slice(0, 200)")))
    c.close()

    # ---------------------------------------------------------------- 4. 體驗額度：被鎖後按「繼續看」，扣完能繼續看
    now = int(__import__("time").time() * 1000)
    API = "https://adtiles1106.example.test"
    stt = {"left": 3, "hit": 0}
    key = _T1106_KEY

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
                                                     "feats": {key: {"max": 3, "used": 3 - stt["left"], "left": stt["left"]}}}]}
        elif path == "/v1/grants/hit":
            stt["hit"] += 1
            stt["left"] -= 1
            out = {"ok": True, "gid": "welcome", "left": stt["left"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        route.fulfill(status=200, body=_t1106_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _t1106_json.dumps({"api": API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.acct.tok','tok-test');localStorage.setItem('tw.live.on','0');"
                      "const day = new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10); localStorage.setItem('tw.quota', JSON.stringify({ day, k: { '" + key + "': Array.from({length: 5}, (_, i) => 'seed' + i) } }));}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route(API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    ag = pg.get_by_role("button", name="同意並繼續")
    if ag.count() and ag.first.is_visible():
        ag.first.click(); pg.wait_for_timeout(300)
    wait_until(pg, "() => window.TwGrants && TwGrants.left('" + key + "') === 3 && !!document.getElementById('breadth') && +document.getElementById('breadth').dataset.total > 0", 30000)
    pg.evaluate("() => document.getElementById('ovBreadthCard').scrollIntoView({ block: 'center' })")
    pg.wait_for_timeout(500)
    pg.evaluate("() => document.querySelector('#udView button[data-v=\"tiles\"]').click()"); pg.wait_for_timeout(1200)   # 體驗額度的鎖在「點了」才彈卡：用 DOM click，不受版面位移影響
    st0 = pg.evaluate("() => ({ mode: [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v), left: TwGrants.left('" + key + "'), modal: !!document.querySelector('.qcard, .qmodal') })")
    ok(f"{T} 體驗中的註冊會員用完 5 次後按「族群字卡」：被擋下（還在分布）、體驗還剩 3 次", st0["mode"] == ["dist"] and st0["left"] == 3, st0)
    btn = pg.locator(".qc-try")
    if btn.count():
        with pg.expect_response(lambda r: "/v1/grants/hit" in r.url, timeout=6000) as ri:
            pg.evaluate("() => document.querySelector('.qc-try').click()")
        hj = ri.value.json()
        ok(f"{T} 按「繼續看」→ 真的 /v1/grants/hit（ok、剩 2 次）", hj.get("ok") is True and hj.get("left") == 2 and stt["hit"] == 1, (hj, stt))
        pg.wait_for_timeout(600)
        wait_until(pg, "() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)[0] === 'tiles'", 3000)   # 扣完會幫他再按一次那顆鈕（grants.pending）
        if pg.evaluate("() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)[0]") != "tiles":
            pg.evaluate("() => document.querySelector('#udView button[data-v=\"tiles\"]').click()"); pg.wait_for_timeout(500)
        ok(f"{T} 扣完之後「族群字卡」真的打得開、字卡出現，體驗剩 2 次", pg.evaluate("() => [...document.querySelectorAll('#udView button.on')].map(x => x.dataset.v)") == ["tiles"]
           and pg.evaluate("() => document.querySelectorAll('#adtGrid .adt-g').length") > 5 and pg.evaluate("() => TwGrants.left('" + key + "')") == 2, pg.evaluate("() => TwGrants.left('" + key + "')"))
        shot(pg, "grant_after.png")
    else:
        ok(f"{T} 體驗額度：被鎖之後有「繼續看」可按（沒有就是這個計次型功能的體驗卡沒跳出來）", False, pg.evaluate("() => ({ modal: (document.getElementById('qcModal') || {}).outerHTML, used: (TwQuota.used('ov.advdec.tiles')||[]).length })"))
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("漲跌家數字卡1106", lambda pg, b, base, code: t_advdec_tiles_1106(b, base, code))
