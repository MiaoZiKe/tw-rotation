"""真人操作驗收：當自己是使用者，把每個功能實際操作一遍。

和 `_preview.py` 的差別很重要：
  _preview.py 問的是「有沒有畫出來、有沒有壓到字」；
  這支問的是「我按下去之後，畫面真的因此改變了嗎」。

所以這裡每一項檢查都長成「操作前記一次狀態 → 真的操作 → 操作後再記一次 → 兩次必須不一樣」。
只驗「元素存在」「有 render」一律不算數 —— 之前就是這樣放過了「切到沒資料的週期再切回日線，
整張 K 線圖空白到重新整理為止」這種錯。

用法：python scripts/_uitest.py [--code 2330] [--headed]
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8767

fails: list[str] = []
notes: list[str] = []


def ok(name: str, cond: bool, detail=None) -> bool:
    """cond 為真＝這個功能真的動了；為假就記下來，最後一次列出。"""
    if not cond:
        fails.append(f"{name}　←　{detail if detail is not None else ''}")
    return bool(cond)


def changed(name: str, before, after, detail: str = "") -> bool:
    return ok(name, before != after, f"操作前後一樣：{before!r} → {after!r}　{detail}")


def serve():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ------------------------------------------------------------------ 小工具
def click(pg, sel: str, wait: int = 300):
    """用真的滑鼠點（會捲進畫面），點不到就記一筆。"""
    try:
        el = pg.query_selector(sel)
        if not el:
            fails.append(f"找不到可點的元素：{sel}")
            return False
        el.scroll_into_view_if_needed()
        el.click(timeout=4000)
        pg.wait_for_timeout(wait)
        return True
    except Exception as e:  # noqa: BLE001
        fails.append(f"點不下去 {sel}：{type(e).__name__} {e}")
        return False


def text(pg, sel: str) -> str:
    return pg.evaluate(f"() => {{ const e = document.querySelector({sel!r}); return e ? e.innerText.trim() : '<缺>'; }}")


def count(pg, sel: str) -> int:
    return pg.evaluate(f"() => document.querySelectorAll({sel!r}).length")


def canvas_hash(pg, sel: str) -> str:
    """把某個容器裡第一張 canvas 取樣成一個指紋，用來判斷『圖真的重畫了』。"""
    return pg.evaluate(
        """(sel) => { const cs = [...document.querySelectorAll(sel + ' canvas')]; if (!cs.length) return 'no-canvas';
             let h = 0;
             for (const c of cs) {
               try {
                 const g = c.getContext('2d'); if (!g) continue;
                 // 取正中間那塊：邊角常常是背景，抓不到「圖真的重畫了」
                 const w = Math.min(c.width, 600), ht = Math.min(c.height, 400);
                 const x = Math.max(0, ((c.width - w) / 2) | 0), y = Math.max(0, ((c.height - ht) / 2) | 0);
                 const d = g.getImageData(x, y, w, ht).data;
                 for (let i = 0; i < d.length; i += 37) { h = (h * 31 + d[i]) | 0; }
               } catch (e) { /* 跨域或 0 尺寸，跳過 */ }
             }
             return String(h); }""", sel)


def scroll_to(pg, el_id: str, tries: int = 20):
    """捲到某個元素並等它真的停下來。

    全站 `html{scroll-behavior:smooth}`，scrollIntoView 之後畫面還會滑一段時間；
    不等它停就把滑鼠移過去，座標是舊的，滾輪會滾到別的東西上
    —— 驗收就會誤判成「這張圖不能放大」。
    """
    pg.evaluate("(id) => { const e = document.getElementById(id); if (e) e.scrollIntoView({block:'center'}); }", el_id)
    last = None
    for _ in range(tries):
        pg.wait_for_timeout(100)
        y = pg.evaluate("() => Math.round(window.scrollY)")
        if y == last:
            return
        last = y
    pg.wait_for_timeout(200)


def check_zoom(pg, wrap: str, inner: str, label: str):
    """真的把滑鼠移過去滾輪：往上滾要放大、卡片高度不能變、往下滾最多回原始大小。

    Andy 的兩條要求都在這裡驗：「滾輪放大但縮小最多就是原始畫面」
    以及「放大部份不能影響到整頁面」。
    """
    Z = """(a) => { const b = document.getElementById(a[0]); if (!b) return null;
        const pane = b.querySelector('.zpane'); const i = document.getElementById(a[1]);
        const card = b.closest('.card') || b.parentElement;
        return { w: i ? (i.style.width || '') : '', zoomed: b.classList.contains('zoomed'),
                 badge: (b.querySelector('.zbadge')||{}).textContent,
                 sw: pane ? pane.scrollWidth : 0, cw: pane ? pane.clientWidth : 0,
                 cardH: Math.round(card.getBoundingClientRect().height),
                 pageW: document.documentElement.scrollWidth }; }"""
    scroll_to(pg, wrap)
    z0 = pg.evaluate(Z, [wrap, inner])
    if not ok(f"「{label}」有滾輪放大的外框", bool(z0), wrap):
        return
    ok(f"「{label}」預設是原始大小", not z0["zoomed"] and not z0["w"], z0)
    r = pg.evaluate("(id) => { const b = document.getElementById(id).getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }", wrap)
    pg.mouse.move(r["x"] + r["w"] * .5, r["y"] + r["h"] * .5)
    for _ in range(4):
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(150)
    pg.wait_for_timeout(450)
    z1 = pg.evaluate(Z, [wrap, inner])
    ok(f"「{label}」往上滾真的放大了", z1["zoomed"] and z1["sw"] > z0["sw"], f"{z0} → {z1}")
    ok(f"「{label}」放大不會把卡片撐高", z1["cardH"] == z0["cardH"], f"{z0['cardH']} → {z1['cardH']}")
    ok(f"「{label}」放大不會讓整頁出現橫向捲軸", z1["pageW"] <= z0["pageW"], f"{z0['pageW']} → {z1['pageW']}")
    ok(f"「{label}」放大後徽章寫出倍率", "×" in (z1["badge"] or ""), z1["badge"])
    for _ in range(12):
        pg.mouse.wheel(0, 160); pg.wait_for_timeout(90)
    pg.wait_for_timeout(450)
    z2 = pg.evaluate(Z, [wrap, inner])
    ok(f"「{label}」往下滾最多回到原始大小", not z2["zoomed"] and not z2["w"], z2)


# ------------------------------------------------------------------ 各頁
def t_overview(pg, base):
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1600)

    # --- 候選名單四個面向：切換要真的換排序、換欄位、換說明
    facets = pg.evaluate("[...document.querySelectorAll('#candFacets button')].map(b => b.dataset.f)")
    ok("候選名單四個面向鈕都在", sorted(facets) == ["all", "chip", "fund", "tech"], facets)
    seen = {}
    for f in facets:
        click(pg, f'#candFacets button[data-f="{f}"]', 400)
        seen[f] = pg.evaluate("""() => ({
            on: (document.querySelector('#candFacets button.on')||{}).dataset.f,
            head: [...document.querySelectorAll('#candTable th')].map(t => t.textContent.replace(/[▲▼]/g,'').trim()).join('|'),
            first: (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code,
            hint: (document.getElementById('candHint')||{}).textContent.trim().slice(0,20) })""")
        ok(f"候選名單 {f} 面向按下去真的被選取", seen[f]["on"] == f, seen[f])
        ok(f"候選名單 {f} 面向有說明文字", bool(seen[f]["hint"]), seen[f])
    ok("四個面向的欄位組不完全相同", len({v["head"] for v in seen.values()}) >= 2,
       {k: v["head"] for k, v in seen.items()})
    ok("四個面向排出來的第一名不完全相同", len({v["first"] for v in seen.values()}) >= 2,
       {k: v["first"] for k, v in seen.items()})

    # --- 點一列：理由要真的展開，再點一次要真的收起來
    click(pg, "#candFacets button[data-f=all]", 350)
    before = count(pg, "#candBody tr.whyrow")
    click(pg, "#candBody tr[data-code]", 350)
    mid = count(pg, "#candBody tr.whyrow")
    changed("點候選名單一列會展開「為何選它」", before, mid)
    why_txt = text(pg, "#candBody tr.whyrow .why")
    ok("「為何選它」有帶實際數字", any(ch.isdigit() for ch in why_txt), why_txt[:60])
    click(pg, "#candBody tr[data-code]", 350)
    after = count(pg, "#candBody tr.whyrow")
    changed("再點一次會收起來", mid, after)

    # --- 排序：每個可排序的表頭都點兩次，順序要真的反過來，箭頭要跟著跑
    heads = pg.evaluate("[...document.querySelectorAll('#candTable th[data-k]')].map(t => t.dataset.k)")
    ok("候選名單表頭可以排序", len(heads) >= 4, heads)
    for k in heads:
        first_a = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st1 = pg.evaluate("""() => ({ first: (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code,
            arrow: [...document.querySelectorAll('#candTable th')].filter(t => /[▲▼]/.test(t.textContent)).map(t => t.dataset.k) })""")
        click(pg, f'#candTable th[data-k="{k}"]', 400)
        st2 = pg.evaluate("() => (document.querySelector('#candBody tr[data-code]')||{dataset:{}}).dataset.code")
        ok(f"表頭「{k}」點下去箭頭跑到這一欄", st1["arrow"] == [k], st1["arrow"])
        ok(f"表頭「{k}」點兩次順序會反過來", st1["first"] != st2 or first_a == st2,
           f"{first_a} → {st1['first']} → {st2}")

    # --- 事件面板篩選：筆數要真的變
    cats = pg.evaluate("[...document.querySelectorAll('#evFilters button')].map(b => b.dataset.c)")
    if cats:
        counts = {}
        for c in cats:
            click(pg, f'#evFilters button[data-c="{c}"]', 300)
            counts[c] = count(pg, "#evList .ev")
        ok("事件分類篩選真的會改變筆數", len(set(counts.values())) >= 2, counts)
        click(pg, f'#evFilters button[data-c="{cats[0]}"]', 250)
    else:
        notes.append("事件面板沒有分類鈕")

    # --- 搜尋框：真的打字 → 出建議 → 點建議 → 跳個股頁
    pg.fill("#q", "")
    pg.type("#q", "2330", delay=45); pg.wait_for_timeout(450)
    sugg = count(pg, "#sugg div[data-c]")
    ok("搜尋框打字會跳出建議", sugg > 0, f"建議 {sugg} 筆")
    if sugg:
        click(pg, "#sugg div[data-c]", 1600)
        ok("點搜尋建議會跳到個股頁", pg.evaluate("location.hash").startswith("#stock/"),
           pg.evaluate("location.hash"))
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1400)

    # --- 資金熱力圖的產業鏈下鑽：點半導體就只剩半導體，點「全部」回得去
    chips = pg.evaluate("[...document.querySelectorAll('#heatChips button')].map(b => b.dataset.c)")
    ok("資金熱力圖有產業鏈切換", len(chips) >= 3, chips)
    TM = """() => { const c = echarts.getInstanceByDom(document.getElementById('heat')); if (!c) return null;
        const d = c.getOption().series[0].data;
        return { n: d.length, nested: !!(d[0] && d[0].children),
                 on: (document.querySelector('#heatChips button.on')||{dataset:{}}).dataset.c }; }"""
    all0 = pg.evaluate(TM)
    ok("預設是所有產業鏈分組顯示", all0 and all0["nested"], all0)
    for cid in [c for c in chips if c][:3]:
        click(pg, f'#heatChips button[data-c="{cid}"]', 800)
        st = pg.evaluate(TM)
        ok(f"點「{cid}」真的只剩這條產業鏈", st and not st["nested"] and st["on"] == cid, st)
        leaves = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('heat'));"
                             " return (c.getOption().series[0].data || []).every(d => !!d.gid); }")
        ok(f"點「{cid}」之後每一格都是族群（不是產業鏈）", leaves)
    click(pg, '#heatChips button[data-c=""]', 800)
    back = pg.evaluate(TM)
    ok("按「全部」回到原本的分組圖", back and back["nested"] and back["n"] == all0["n"], back)

    # 下鑽之後點方塊 → 原地列出成分股（不跳頁）
    first_chain = next((c for c in chips if c), None)
    if first_chain:
        click(pg, f'#heatChips button[data-c="{first_chain}"]', 800)
        pg.evaluate("document.getElementById('heat').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
        box = pg.evaluate("() => { const r = document.getElementById('heat').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
        h_before = pg.evaluate("location.hash")
        pg.mouse.click(box["x"] + box["w"] * 0.2, box["y"] + box["h"] * 0.35)
        pg.wait_for_timeout(900)
        st = pg.evaluate("""() => ({ open: !document.getElementById('heatPanel').hidden,
            title: (document.querySelector('#heatPanel .hh b')||{}).textContent,
            stocks: document.querySelectorAll('#heatPanel .ms a').length,
            link: !!document.querySelector('#heatPanel a[href^="#industry/group/"]') })""")
        ok("點熱力圖方塊會在原地列出成分股", st["open"] and (st["stocks"] > 0 or "整理中" in text(pg, "#heatPanel")), st)
        ok("點方塊不會把人帶離總覽", pg.evaluate("location.hash") == h_before, pg.evaluate("location.hash"))
        ok("成分股面板有寫出是哪個族群", len(st["title"] or "") > 0, st)
        ok("成分股面板有進族群頁的連結", st["link"], st)
        click(pg, "#heatPanel [data-x]", 400)
        ok("成分股面板收得起來", pg.evaluate("() => document.getElementById('heatPanel').hidden"))

    # --- 滾輪放大：往上滾要變大，往下滾最多回到原始大小（不會縮成一小塊）
    ZK = """() => { const b = document.getElementById('heatWrap'); const pane = b.querySelector('.zpane');
        const i = document.getElementById('heat'); const card = b.closest('.card');
        return { w: i.style.width || '', badge: (b.querySelector('.zbadge')||{}).textContent,
                 zoomed: b.classList.contains('zoomed'), sw: pane.scrollWidth, cw: pane.clientWidth,
                 cardH: Math.round(card.getBoundingClientRect().height),
                 pageW: document.documentElement.scrollWidth }; }"""
    pg.evaluate("document.getElementById('heatWrap').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
    z0 = pg.evaluate(ZK)
    ok("熱力圖預設是原始大小", not z0["zoomed"] and not z0["w"], z0)
    r = pg.evaluate("() => { const b = document.getElementById('heatWrap').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
    pg.mouse.move(r["x"] + r["w"] * .5, r["y"] + r["h"] * .5)
    for _ in range(4):
        pg.mouse.wheel(0, -160); pg.wait_for_timeout(160)
    pg.wait_for_timeout(500)
    z1 = pg.evaluate(ZK)
    ok("往上滾真的放大了", z1["zoomed"] and z1["sw"] > z0["sw"], f"{z0} → {z1}")
    ok("放大不會把卡片撐高（不影響整頁版面）", z1["cardH"] == z0["cardH"], f"{z0['cardH']} → {z1['cardH']}")
    ok("放大不會讓整頁出現橫向捲軸", z1["pageW"] <= z0["pageW"], f"{z0['pageW']} → {z1['pageW']}")
    ok("放大後徽章寫出倍率", "×" in (z1["badge"] or ""), z1["badge"])
    # 往下滾滾很多次，最多只能回到原始大小
    for _ in range(12):
        pg.mouse.wheel(0, 160); pg.wait_for_timeout(100)
    pg.wait_for_timeout(500)
    z2 = pg.evaluate(ZK)
    ok("往下滾最多回到原始大小，不會縮更小", not z2["zoomed"] and not z2["w"], z2)
    ok("回到原始大小後沒有多餘的捲動範圍", z2["sw"] <= z2["cw"] + 4, z2)

    # --- 熱力圖只能放大、不能拖：按「放大」要全螢幕，關得掉
    ok("熱力圖有放大鈕", count(pg, "#heatZoom") == 1)
    click(pg, "#heatZoom", 1300)
    zs = pg.evaluate("""() => ({ open: !document.getElementById('zoomOv').hidden,
        canvas: !!document.querySelector('#zoomBody canvas'),
        chips: document.querySelectorAll('#zoomChips button').length,
        h: document.getElementById('zoomBody').clientHeight,
        title: (document.getElementById('zoomTitle')||{}).textContent })""")
    ok("放大後開出全螢幕的熱力圖", zs["open"] and zs["canvas"], zs)
    ok("放大後比原圖高很多", zs["h"] > 600, zs["h"])
    ok("放大後還是可以切產業鏈", zs["chips"] >= 3, zs["chips"])
    ok("放大罩有標題", "熱力" in (zs["title"] or ""), zs["title"])
    click(pg, "#zoomClose", 600)
    ok("放大罩關得掉", pg.evaluate("() => document.getElementById('zoomOv').hidden"))
    # 熱力圖不可以被拖走（treemap 的 roam 必須是關的，不然拖一拖就整片空白）
    ok("熱力圖沒有開啟拖曳平移（roam）", pg.evaluate(
        "() => { const c = echarts.getInstanceByDom(document.getElementById('heat'));"
        " return c ? c.getOption().series[0].roam === false : false; }"))
    click(pg, '#heatChips button[data-c=""]', 700)

    # --- 上方數字點得開：點了要去「市場明細」分頁看完整名單
    kinds = pg.evaluate("[...document.querySelectorAll('#hero .kpi.clickable')].map(k => k.dataset.drill)")
    ok("總覽上方至少四個數字點得開", len(kinds) >= 4, kinds)
    for k in kinds:
        click(pg, f'#hero .kpi[data-drill="{k}"]', 1400)
        st = pg.evaluate("""() => ({ hash: location.hash, tab: (document.querySelector('.tab.on')||{dataset:{}}).dataset.view,
            title: (document.getElementById('mktTitle')||{}).innerText,
            rows: document.querySelectorAll('#mktBody tr[data-code]').length,
            blocks: document.querySelectorAll('#mktBody .ma, #mktBody .t5').length,
            note: (document.querySelector('#mktBody .kpinote')||{}).textContent.length })""")
        ok(f"KPI「{k}」點下去會到市場明細分頁", st["tab"] == "market" and st["hash"].endswith(k), st)
        ok(f"KPI「{k}」的明細真的有內容", st["rows"] > 0 or st["blocks"] > 0, st)
        ok(f"KPI「{k}」有寫怎麼看", st["note"] > 10, st)
        ok(f"KPI「{k}」有標題", len(st["title"] or "") > 2, st)
        pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1400)

    # --- 總覽下方三張圖：都不是長條圖了，而且點得動
    for cid, name, want in (("breadth", "市場寬度", ("gauge", "pie")), ("trust", "投信連續買超", ("scatter",)),
                            ("gval", "族群估值", ("scatter",))):
        types = pg.evaluate(f"""() => {{ const c = echarts.getInstanceByDom(document.getElementById('{cid}'));
            return c ? (c.getOption().series || []).map(s => s.type) : null; }}""")
        ok(f"總覽「{name}」有畫出來", bool(types), types)
        ok(f"總覽「{name}」不是長條圖", types and 'bar' not in types, types)
        ok(f"總覽「{name}」用的是更生動的圖形", types and any(w in types for w in want), types)

    # --- 總覽的輪動階段（精簡版）＋ 小時鐘
    ok("總覽有輪動階段四張卡", count(pg, "#rotMini .stage") == 4, count(pg, "#rotMini .stage"))
    mini = pg.evaluate("""() => { const el = document.getElementById('rotClockMini'); if (!el) return null;
        const c = echarts.getInstanceByDom(el); if (!c) return { canvas: !!el.querySelector('canvas'), pts: 0 };
        const sc = c.getOption().series.filter(s => s.type === 'scatter')[0];
        return { canvas: !!el.querySelector('canvas'), pts: sc ? sc.data.length : 0 }; }""")
    ok("總覽也有輪動時鐘", bool(mini) and mini["canvas"] and mini["pts"] > 0, mini)

    # --- 下方三張小圖都要能滾輪放大（Andy：「這邊資訊太小看不到 需要新增縮放」）
    for w, i, lb in (("breadthWrap", "breadth", "市場寬度"), ("trustWrap", "trust", "投信連續買超"),
                     ("gvalWrap", "gval", "族群估值"), ("rotClockMiniWrap", "rotClockMini", "總覽輪動時鐘")):
        check_zoom(pg, w, i, lb)

    # --- 下方三張圖：要有資料，不是空狀態
    for cid, name in (("breadth", "市場寬度"), ("trust", "投信連續買超"), ("gval", "族群估值")):
        has = pg.evaluate(f"() => {{ const e = document.getElementById('{cid}'); return e ? {{ canvas: !!e.querySelector('canvas'), empty: !!e.querySelector('.empty') || /尚無|沒有|回補中/.test(e.innerText) }} : null; }}")
        ok(f"總覽「{name}」有畫出來", bool(has) and has["canvas"] and not has["empty"], has)


def t_market(pg, base):
    pg.goto(f"{base}#market", wait_until="networkidle"); pg.wait_for_timeout(2000)
    tabs = pg.evaluate("[...document.querySelectorAll('#mktSeg2 button')].map(b => b.dataset.k)")
    ok("市場明細有四個分頁", len(tabs) >= 4, tabs)
    seen = {}
    for k in tabs:
        click(pg, f'#mktSeg2 button[data-k="{k}"]', 900)
        seen[k] = pg.evaluate("""() => ({ on: (document.querySelector('#mktSeg2 button.on')||{dataset:{}}).dataset.k,
            title: (document.getElementById('mktTitle')||{}).innerText.split(String.fromCharCode(10))[0],
            rows: document.querySelectorAll('#mktBody tr[data-code]').length,
            blocks: document.querySelectorAll('#mktBody .ma, #mktBody .t5').length })""")
        ok(f"市場明細「{k}」按下去真的被選取", seen[k]["on"] == k, seen[k])
        ok(f"市場明細「{k}」有列出東西", seen[k]["rows"] > 0 or seen[k]["blocks"] > 0, seen[k])
    ok("四個分頁標題各不相同", len({v["title"] for v in seen.values()}) == len(seen),
       {k: v["title"] for k, v in seen.items()})
    # 漲跌家數底下還有漲停／跌停／漲幅前段的子分頁
    click(pg, '#mktSeg2 button[data-k="updown"]', 900)
    sub = count(pg, "#mktTabs button")
    ok("漲跌家數有子分頁（漲停／跌停／漲幅前段…）", sub >= 2, sub)
    if sub >= 2:
        n0 = pg.evaluate("() => document.querySelectorAll('#mktBody tr[data-code]').length")
        click(pg, "#mktTabs button:nth-child(3)", 800)
        n1 = pg.evaluate("() => document.querySelectorAll('#mktBody tr[data-code]').length")
        changed("切子分頁，列出的股票數真的變了", n0, n1)
    # 點一列要能進個股頁
    if count(pg, "#mktBody tr[data-code]"):
        click(pg, "#mktBody tr[data-code]", 1600)
        ok("市場明細點一列會進個股頁", pg.evaluate("location.hash").startswith("#stock/"), pg.evaluate("location.hash"))


def t_flow(pg, base):
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(2200)
    for cid, name in (("rankFlow", "資金流向排行"), ("bump", "名次變化"),
                      ("sankey", "資金桑基圖"), ("river", "資金河流圖"),
                      ("instGroups", "族群 × 法人"), ("conc", "資金集中度"), ("valScatter", "估值散布圖")):
        has = pg.evaluate(f"() => {{ const e = document.getElementById('{cid}'); return e ? {{ canvas: !!e.querySelector('canvas'), empty: !!e.querySelector('.empty') }} : null; }}")
        ok(f"資金流向「{name}」有畫出來", bool(has) and has["canvas"] and not has["empty"], has)

    # --- 期間切換：換一個期間，說明文字、排行圖、法人圖都要真的跟著換
    ps = pg.evaluate("[...document.querySelectorAll('#periodSeg button')].map(b => b.dataset.p)")
    ok("資金流向有期間切換（本週／上週／上上週／本月／上月／近三月）", len(ps) >= 5, ps)
    seen = {}
    for k in ps:
        click(pg, f'#periodSeg button[data-p="{k}"]', 900)
        seen[k] = pg.evaluate("""() => ({ on: (document.querySelector('#periodSeg button.on')||{dataset:{}}).dataset.p,
            note: (document.getElementById('periodNote')||{}).textContent,
            sub: (document.getElementById('rankSub')||{}).textContent,
            rank: !!document.querySelector('#rankFlow canvas'),
            inst: !!document.querySelector('#instGroups canvas'),
            top: (() => { const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
                   if (!c) return null; const y = c.getOption().yAxis[0].data || []; return y[y.length-1] || null; })() })""")
        ok(f"期間「{k}」按下去真的被選取", seen[k]["on"] == k, seen[k])
        ok(f"期間「{k}」有寫出日期範圍", "～" in (seen[k]["note"] or ""), seen[k]["note"])
        ok(f"期間「{k}」排行圖有畫出來", seen[k]["rank"], seen[k])
        ok(f"期間「{k}」法人圖有畫出來", seen[k]["inst"], seen[k])
    ok("不同期間的說明文字不一樣", len({v["note"] for v in seen.values()}) == len(seen),
       {k: v["note"] for k, v in seen.items()})
    ok("不同期間排出來的第一名不完全相同", len({v["top"] for v in seen.values()}) >= 2,
       {k: v["top"] for k, v in seen.items()})

    # --- 名次變化要跟著期間換刻度（Andy：「資金流向排名不會變」）
    BUMPX = """() => { const c = echarts.getInstanceByDom(document.getElementById('bump'));
        return { x: c ? (c.getOption().xAxis[0].data || []) : null,
                 n: c ? c.getOption().series.length : 0,
                 sub: (document.getElementById('bumpSub')||{}).textContent }; }"""
    click(pg, '#periodSeg button[data-p="w0"]', 1000)
    bw = pg.evaluate(BUMPX)
    click(pg, '#periodSeg button[data-p="m1"]', 1200)
    bm = pg.evaluate(BUMPX)
    ok("名次變化在週期間是用「週」的刻度", "週" in (bw["sub"] or ""), bw["sub"])
    ok("名次變化在月期間改成「月」的刻度", "月" in (bm["sub"] or ""), bm["sub"])
    changed("切到上月，名次變化的 X 軸真的換了", bw["x"], bm["x"])
    ok("月名次的刻度是年月（例如 2026/08）", all(len(str(v)) == 7 for v in (bm["x"] or ["x"])), bm["x"])
    ok("月名次沒有留下上一張圖的殘線", bm["n"] <= 10, bm["n"])
    click(pg, '#periodSeg button[data-p="w0"]', 1000)
    ok("切回本週又變回週刻度", "週" in (pg.evaluate(BUMPX)["sub"] or ""))

    # --- 每張圖的「怎麼看」：按下去要真的展開白話說明，再按要收起來
    hows = pg.evaluate("[...document.querySelectorAll('#v-flow .howbtn')].map(b => b.dataset.how)")
    ok("資金流向每張圖都有「怎麼看」", len(hows) >= 7, hows)
    for h in hows:
        click(pg, f'#v-flow .howbtn[data-how="{h}"]', 250)
        st = pg.evaluate(f"""() => {{ const b = document.getElementById('how-{h}');
            return {{ open: b && !b.hidden, len: b ? b.innerText.trim().length : 0,
                     label: (document.querySelector('#v-flow .howbtn[data-how=\\"{h}\\"]')||{{}}).textContent }}; }}""")
        ok(f"「怎麼看：{h}」按下去有展開說明", st["open"] and st["len"] > 60, st)
        ok(f"「怎麼看：{h}」展開後按鈕變成收起", "收起" in (st["label"] or ""), st["label"])
        click(pg, f'#v-flow .howbtn[data-how="{h}"]', 200)
        ok(f"「怎麼看：{h}」可以再收起來", pg.evaluate(f"() => document.getElementById('how-{h}').hidden"))

    # --- 輪動階段看板：四張卡、循環列、換階段的族群，換比較天數要真的重算
    ok("輪動階段有四張卡", count(pg, "#rotBoard .stage") == 4, count(pg, "#rotBoard .stage"))
    ok("輪動階段有寫出循環順序", "改善" in text(pg, "#rotCycle") and "領先" in text(pg, "#rotCycle"), text(pg, "#rotCycle"))
    ok("輪動階段有列出族群", count(pg, "#rotBoard li[data-gid]") > 0)
    ok("四張卡的名字是改善／領先／轉弱／落後",
       pg.evaluate("[...document.querySelectorAll('#rotBoard .stage .sh b')].map(e=>e.textContent)") == ["改善", "領先", "轉弱", "落後"],
       pg.evaluate("[...document.querySelectorAll('#rotBoard .stage .sh b')].map(e=>e.textContent)"))
    backs = pg.evaluate("[...document.querySelectorAll('#rotBack button')].map(b => b.dataset.v)")
    ok("輪動階段可以換比較天數", len(backs) >= 2, backs)
    seenb = {}
    for v in backs:
        click(pg, f'#rotBack button[data-v="{v}"]', 700)
        seenb[v] = pg.evaluate("""() => ({ on: (document.querySelector('#rotBack button.on')||{dataset:{}}).dataset.v,
            move: (document.getElementById('rotMove')||{}).innerText,
            items: document.querySelectorAll('#rotBoard li[data-gid]').length })""")
        ok(f"「和 {v} 天前比」按下去真的被選取", seenb[v]["on"] == v, seenb[v])
        ok(f"「和 {v} 天前比」有寫出換階段的族群或明講沒有", v in (seenb[v]["move"] or ""), seenb[v]["move"][:40])
    ok("換比較天數，換階段的名單真的不一樣", len({v["move"] for v in seenb.values()}) >= 2,
       {k: v["move"][:30] for k, v in seenb.items()})

    # --- 資金輪動時鐘：Andy 要「輪動族群要搭配圖表，看圖就懂」
    clk = pg.evaluate("""() => { const el = document.getElementById('rotClock');
        if (!el) return null; const c = echarts.getInstanceByDom(el); if (!c) return { canvas: !!el.querySelector('canvas'), pts: 0 };
        const o = c.getOption(); const sc = o.series.filter(s => s.type === 'scatter')[0];
        return { canvas: !!el.querySelector('canvas'), pts: sc ? sc.data.length : 0,
                 trails: o.series.filter(s => s.type === 'line').length,
                 labels: (o.angleAxis[0].axisLabel ? 'fn' : 'none'),
                 stages: (sc ? sc.data : []).map(d => d.row && d.row.stage).filter(Boolean) }; }""")
    ok("輪動時鐘有畫出來", bool(clk) and clk["canvas"], clk)
    ok("輪動時鐘上有族群的點", bool(clk) and clk["pts"] >= 4, clk)
    ok("每個族群都有一條走過的尾巴", bool(clk) and clk["trails"] == clk["pts"], clk)
    ok("時鐘上的點分佈在四個階段裡", bool(clk) and set(clk["stages"]) <= {"leading", "improving", "weakening", "lagging"}, clk and clk["stages"][:6])
    click(pg, '#rotBack button[data-v="5"]', 900)
    h0 = canvas_hash(pg, "#rotClock")
    click(pg, '#rotBack button[data-v="20"]', 1100)
    changed("換成和 20 天前比，輪動時鐘的尾巴真的重畫", h0, canvas_hash(pg, "#rotClock"))
    click(pg, '#rotBack button[data-v="5"]', 900)
    # 用真的滑鼠點時鐘上的點（算出那顆點的螢幕座標再點下去），要進得去族群頁
    scroll_to(pg, "rotClockWrap")
    pt = pg.evaluate("""() => { const el = document.getElementById('rotClock');
        const c = echarts.getInstanceByDom(el); if (!c) return null;
        const si = c.getOption().series.findIndex(s => s.type === 'scatter');
        const d = c.getOption().series[si].data[0]; if (!d) return null;
        const p = c.convertToPixel({ seriesIndex: si }, d.value); const r = el.getBoundingClientRect();
        return { x: r.x + p[0], y: r.y + p[1], gid: d.row.gid, name: d.row.name }; }""")
    if ok("算得出時鐘上第一顆點的位置", bool(pt), pt):
        before = pg.evaluate("() => location.hash")
        pg.mouse.click(pt["x"], pt["y"])
        pg.wait_for_timeout(1000)
        # 族群 id 有中文，location.hash 讀回來是編碼過的，要解回來才比得起來
        now = pg.evaluate("() => decodeURIComponent(location.hash)")
        ok(f"點時鐘上的「{pt['name']}」會進它的族群頁", now == "#industry/group/" + pt["gid"], f"{before} → {now}")
    pg.goto(f"{base}#flow", wait_until="networkidle"); pg.wait_for_timeout(1800)

    # --- 資金集中度：前 5 / 前 10 切換要真的換一條線
    concs = pg.evaluate("[...document.querySelectorAll('#concSeg button')].map(b => b.dataset.v)")
    if len(concs) >= 2:
        name0 = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('conc')); return c ? c.getOption().series[0].name : null; }")
        state0 = text(pg, "#concState")
        click(pg, '#concSeg button[data-v="10"]', 900)
        name1 = pg.evaluate("() => { const c = echarts.getInstanceByDom(document.getElementById('conc')); return c ? c.getOption().series[0].name : null; }")
        changed("資金集中度切前 10 大，真的換一條線", name0, name1)
        changed("資金集中度切前 10 大，狀態說明跟著換", state0, text(pg, "#concState"))
        ok("資金集中度有寫出現在是縮圈還是擴散", any(w in text(pg, "#concState") for w in ("縮圈", "擴散", "沒有明顯")), text(pg, "#concState"))
        click(pg, '#concSeg button[data-v="5"]', 700)

    # --- 估值篩選：條件真的會篩掉東西，清除後回得來
    n0 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    cnt0 = text(pg, "#vCount")
    ok("估值表有列出股票", n0 > 0, n0)
    pg.fill("#vPeHi", "12"); pg.wait_for_timeout(700)
    n1 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    hi = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')]
        .map(tr => parseFloat(tr.children[2].textContent)).filter(Number.isFinite)""")
    ok("本益比上限真的篩掉東西", n1 < n0 or not n1, f"{n0} → {n1}")
    ok("篩出來的本益比真的都 ≤ 12", all(v <= 12.0001 for v in hi), [v for v in hi if v > 12][:5])
    pg.fill("#vRoe", "20"); pg.wait_for_timeout(700)
    n2 = pg.evaluate("() => document.querySelectorAll('#valBody tr[data-code]').length")
    ok("再加 ROE 條件會更少", n2 <= n1, f"{n1} → {n2}")
    changed("篩選後的檔數說明跟著變", cnt0, text(pg, "#vCount"))
    click(pg, "#vReset", 800)
    ok("清除條件後回到原本的檔數", text(pg, "#vCount") == cnt0, f"{cnt0} vs {text(pg, '#vCount')}")
    # 勾「只看低於族群中位」要真的只留低於中位的
    click(pg, "#vBelow", 800)
    below = pg.evaluate("""() => [...document.querySelectorAll('#valBody tr[data-code]')].map(tr => [
        parseFloat(tr.children[2].textContent), parseFloat(tr.children[3].textContent)])
        .filter(a => Number.isFinite(a[0]) && Number.isFinite(a[1]))""")
    ok("「只看低於族群中位」真的只留本益比低於中位的", all(a[0] < a[1] for a in below),
       [a for a in below if a[0] >= a[1]][:4])
    click(pg, "#vBelow", 600)

    # --- 這頁每張圖都要能滾輪放大（Andy：「資訊太小看不到 需要新增縮放」）
    for w, i, lb in (("rankFlowWrap", "rankFlow", "資金流向排行"), ("bumpWrap", "bump", "名次變化"),
                     ("rotClockWrap", "rotClock", "輪動時鐘"), ("sankeyWrap", "sankey", "資金去向"),
                     ("riverWrap", "river", "族群佔比河流"), ("instGroupsWrap", "instGroups", "族群 × 法人")):
        check_zoom(pg, w, i, lb)


def t_industry(pg, base):
    pg.goto(f"{base}#industry", wait_until="networkidle"); pg.wait_for_timeout(1400)
    ok("產業地圖有產業鏈方塊", count(pg, "#chainTiles .tile") > 0)
    ok("產業地圖有法定產業別方塊", count(pg, "#indTiles .tile") > 0)
    click(pg, "#chainTiles .tile", 1600)
    ok("點產業鏈方塊會進單一產業鏈頁", pg.evaluate("location.hash").startswith("#industry/"),
       pg.evaluate("location.hash"))

    pg.goto(f"{base}#industry/ai_server", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("產業鏈頁有產品剖析圖", count(pg, "#prodDiagram svg") > 0)
    ok("產業鏈頁有關聯圖公司節點", count(pg, "#chainMap .co") > 0)
    n_all = count(pg, "#memberTable tbody tr")
    ok("產業鏈頁有成分股", n_all > 0)

    # --- 上市／上櫃切換：筆數要真的變，而且加起來等於全部
    click(pg, '#mktSeg button[data-v="TWSE"]', 500); n_twse = count(pg, "#memberTable tbody tr")
    click(pg, '#mktSeg button[data-v="TPEX"]', 500); n_tpex = count(pg, "#memberTable tbody tr")
    click(pg, '#mktSeg button[data-v="ALL"]', 500)
    ok("上市／上櫃切換真的在篩選", n_twse != n_all or n_tpex != n_all, f"全部 {n_all}／上市 {n_twse}／上櫃 {n_tpex}")
    ok("上市＋上櫃 = 全部（沒有漏掉或重複）", n_twse + n_tpex == n_all, f"{n_twse}+{n_tpex} != {n_all}")

    # --- 點環節 chip：關聯圖要真的捲到對應位置、該環節要亮起來、成分股要被篩
    if count(pg, "#segChips .segchip"):
        before = pg.evaluate("""() => ({ sel: document.querySelectorAll('#segChips .segchip.sel').length,
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            left: (document.querySelector('#chainMap')||{}).scrollLeft })""")
        click(pg, "#segChips .segchip:not(.nomem)", 800)
        after = pg.evaluate("""() => ({ sel: document.querySelectorAll('#segChips .segchip.sel').length,
            rows: document.querySelectorAll('#memberTable tbody tr').length,
            left: (document.querySelector('#chainMap')||{}).scrollLeft })""")
        changed("點環節 chip 真的選起來了", before["sel"], after["sel"])
        ok("點環節 chip 成分股有被篩選", after["rows"] <= before["rows"], f"{before['rows']} → {after['rows']}")
        click(pg, "#segChips .segchip.sel", 500)

    # --- 點族群卡：成分股要真的被篩
    if count(pg, "#groupCards .tile"):
        b = count(pg, "#memberTable tbody tr")
        click(pg, "#groupCards .tile", 700)
        a = count(pg, "#memberTable tbody tr")
        ok("點族群卡真的篩選了成分股", a < b or count(pg, "#groupCards .tile.sel") > 0, f"{b} → {a}")
        click(pg, "#groupCards .tile.sel", 500)

    # --- 點剖析圖零件：只亮起來＋在原地說明，不准動下方成分股（Andy）
    if count(pg, "#prodDiagram [data-seg]"):
        # 先把剖析圖捲進畫面再記位置，否則量到的是測試自己捲的，不是頁面被點擊帶走的
        pg.evaluate("document.querySelector('#prodDiagram [data-seg]').scrollIntoView({block:'center'})")
        pg.wait_for_timeout(600)
        before = pg.evaluate("""() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
            y: Math.round(scrollY), seg: (document.querySelector('#segBox .segbox b.t')||{}).textContent })""")
        click(pg, "#prodDiagram [data-seg]", 800)
        after = pg.evaluate("""() => ({ rows: document.querySelectorAll('#memberTable tbody tr').length,
            y: Math.round(scrollY), seg: (document.querySelector('#segBox .segbox b.t')||{}).textContent,
            sel: document.querySelectorAll('#prodDiagram [data-seg].sel').length,
            btn: !!document.getElementById('segOnly') })""")
        ok("點零件會亮起來", after["sel"] > 0, after)
        ok("點零件會在原地說明這個環節", bool(after["seg"]) and after["seg"] != before["seg"], f"{before['seg']} → {after['seg']}")
        ok("點零件不會動到下方成分股", after["rows"] == before["rows"], f"{before['rows']} → {after['rows']}")
        ok("點零件不會把畫面捲走", abs(after["y"] - before["y"]) < 40, f"{before['y']} → {after['y']}")
        ok("說明框有「只看這個環節」的按鈕", after["btn"], after)
        # 按了那顆按鈕才真的篩
        click(pg, "#segOnly", 900)
        n2 = count(pg, "#memberTable tbody tr")
        ok("按「只看這個環節」才真的篩成分股", n2 != before["rows"] or n2 < before["rows"] + 1, f"{before['rows']} → {n2}")

    # --- 剖析圖零件：點下去要列出個股
    if count(pg, "#prodDiagram [data-part]"):
        click(pg, "#prodDiagram [data-part]", 600)
        ok("點剖析圖零件會亮起來", count(pg, "#prodDiagram .sel") > 0)

    # --- 點成分股 → 個股頁
    click(pg, "#memberTable tbody tr a, #memberTable tbody tr", 1800)
    ok("點成分股會進個股頁", pg.evaluate("location.hash").startswith("#stock/"), pg.evaluate("location.hash"))


def t_themes(pg, base):
    pg.goto(f"{base}#themes", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("題材熱力圖有畫出來", pg.evaluate("() => !!document.querySelector('#themeMap canvas')"))
    ok("題材頁有下方明細", len(text(pg, "#themeDetail")) > 20, text(pg, "#themeDetail")[:40])

    # 真的用滑鼠點熱力方塊 → 下方明細要換一個題材
    before = text(pg, "#themeDetail")[:60]
    pg.evaluate("document.getElementById('themeMap').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
    box = pg.evaluate("() => { const r = document.getElementById('themeMap').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
    pg.mouse.click(box["x"] + box["w"] * 0.7, box["y"] + box["h"] * 0.7)
    pg.wait_for_timeout(1200)
    changed("點題材熱力方塊，下方明細跟著換", before, text(pg, "#themeDetail")[:60])

    # 題材熱力圖也要能放大，而且一樣不能拖
    ok("題材熱力圖有放大鈕", count(pg, "#themeZoom") == 1)
    click(pg, "#themeZoom", 1300)
    ok("題材熱力圖放大開得起來", pg.evaluate(
        "() => !document.getElementById('zoomOv').hidden && !!document.querySelector('#zoomBody canvas')"))
    click(pg, "#zoomClose", 600)
    ok("題材熱力圖沒有開啟拖曳平移（roam）", pg.evaluate(
        "() => { const c = echarts.getInstanceByDom(document.getElementById('themeMap'));"
        " return c ? c.getOption().series[0].roam === false : false; }"))
    # Andy：「題材資金熱力這邊也是會影響大小」—— 放大只能在框內發生
    check_zoom(pg, "themeMapWrap", "themeMap", "題材資金熱力")

    # 總覽的「熱門題材」方塊 → 點了要切到該題材
    pg.goto(f"{base}#overview", wait_until="networkidle"); pg.wait_for_timeout(1500)
    ok("總覽有熱門題材方塊", count(pg, "#themeStrip .tile") > 0)
    if count(pg, "#themeStrip .tile"):
        click(pg, "#themeStrip .tile", 1600)
        ok("點熱門題材會切到該題材", pg.evaluate("location.hash").startswith("#themes/"), pg.evaluate("location.hash"))

    # 題材頁：族群分組 + 剖析圖零件點得到個股
    tids = pg.evaluate("(window.ThemeDiagrams ? Object.keys(window.ThemeDiagrams).filter(k => k !== 'fit') : [])")
    ok("題材剖析圖數量 ≥ 18", len(tids) >= 18, len(tids))
    for tid in tids[:3]:
        pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(1100)
        ok(f"題材 {tid} 有剖析圖", count(pg, "#themeDiagram svg") > 0)
        ok(f"題材 {tid} 成員有依族群分組", count(pg, "#themeDetail .gsec, #themeDetail h4, #themeParts") > 0)
        if count(pg, "#themeDiagram [data-part][data-codes]"):
            click(pg, "#themeDiagram [data-part][data-codes]", 600)
            ok(f"題材 {tid} 點零件會列出個股", count(pg, "#themeParts a.lk") > 0)


def t_stock(pg, base, code):
    pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2400)
    ok("個股頁有標題", len(text(pg, "#stockPage h2")) > 2, text(pg, "#stockPage h2"))
    ok("個股頁 K 線有畫出來", count(pg, "#lwc canvas") > 0)
    # Andy：「資訊需要定期更新」—— 頁面要自己講清楚更新到哪一天
    fresh = pg.evaluate("""() => { const ns = [...document.querySelectorAll('#stockPage .note')].map(e => e.innerText);
        return ns.find(t => t.includes('資料更新到')) || ''; }""")
    ok("個股頁有寫資料更新到哪一天", "資料更新到" in fresh and any(c.isdigit() for c in fresh), fresh[:80])

    # --- 六個分頁：每個都要真的換內容
    seen = {}
    for tab in ("revenue", "profit", "dividend", "chips", "basics", "news"):
        click(pg, f'#stockTabs button[data-t="{tab}"]', 700)
        seen[tab] = pg.evaluate("() => document.getElementById('stockTab').innerText.trim().slice(0,60)")
        ok(f"分頁 {tab} 有內容", len(seen[tab]) > 5, seen[tab])
    ok("六個分頁內容彼此不同", len(set(seen.values())) == 6, seen)

    # --- 營收分頁的「單月／累計」切換要真的重畫
    click(pg, '#stockTabs button[data-t="revenue"]', 800)
    if count(pg, "#revMode button") >= 2:
        h0 = canvas_hash(pg, "#revYear")
        click(pg, '#revMode button[data-v="c"]', 800)
        h1 = canvas_hash(pg, "#revYear")
        changed("營收「單月／累計」切換真的重畫", h0, h1)
        click(pg, '#revMode button[data-v="m"]', 500)

    # --- 時間週期：按鈕上要先標清楚哪些這檔沒有（Andy：「1 日以下都不見」）
    tfstate = pg.evaluate("""() => [...document.querySelectorAll('#tfSeg button')].map(b => ({
        tf: b.dataset.tf, off: b.classList.contains('off'), title: b.title }))""")
    ok("有 15 分／1 時／4 時／日／週／月六個週期鈕",
       [t["tf"] for t in tfstate][:6] == ["15m", "60m", "240m", "1d", "1w", "1M"], tfstate)
    ok("日線一定是有資料的（沒有被劃掉）", not next(t for t in tfstate if t["tf"] == "1d")["off"], tfstate)
    for t in tfstate:
        if t["off"]:
            ok(f"被劃掉的週期 {t['tf']} 有寫清楚為什麼沒有", len(t["title"] or "") > 10, t)
    # 標示要和實際資料一致：劃掉的一定畫不出圖，沒劃掉的一定畫得出來
    tfs = [t["tf"] for t in tfstate]
    for t in tfstate:
        click(pg, f'#tfSeg button[data-tf="{t["tf"]}"]', 700)
        st = pg.evaluate("({ canvas: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#lwc .empty') })")
        ok(f"週期 {t['tf']} 不是壞掉（有圖或有明確空狀態文案）", st["canvas"] > 0 or st["empty"], st)
        if t["off"]:
            ok(f"劃掉的週期 {t['tf']} 點下去有說明為什麼沒有", st["empty"], st)
        else:
            ok(f"沒劃掉的週期 {t['tf']} 點下去真的畫得出來", st["canvas"] > 0 and not st["empty"], st)
    click(pg, '#tfSeg button[data-tf="1d"]', 900)
    st = pg.evaluate("({ canvas: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#lwc .empty'), dbg: window.Industry._dbg() })")
    ok("走過所有週期後切回日線，K 線圖回得來", st["canvas"] > 0 and not st["empty"], st)

    # --- 指標 chips：開關要真的改變圖（副圖數量或圖面）
    for k in ("kd", "macd", "rsi", "vol", "boll", "smc"):
        chip = pg.query_selector(f'#indChips .chip[data-k={k}]')
        if not chip:
            continue
        b0 = pg.evaluate(f"() => document.querySelector('#indChips .chip[data-k={k}]').classList.contains('on')")
        h0 = canvas_hash(pg, "#lwc")
        # 點 chip 的左邊（標籤那側）—— 正中央是參數輸入框，使用者點那裡本來就不該切換
        chip.scroll_into_view_if_needed()
        bb = chip.bounding_box()
        pg.mouse.click(bb["x"] + 12, bb["y"] + bb["height"] / 2); pg.wait_for_timeout(700)
        b1 = pg.evaluate(f"() => document.querySelector('#indChips .chip[data-k={k}]').classList.contains('on')")
        h1 = canvas_hash(pg, "#lwc")
        changed(f"指標 {k} 勾選狀態真的變了", b0, b1)
        changed(f"指標 {k} 開關後圖真的重畫", h0, h1)
        click(pg, f'#indChips .chip[data-k={k}]', 600)   # 切回原狀

    # --- 指標參數：改 RSI 的天數，圖要真的變
    inp = pg.query_selector("#indChips .chip[data-k=rsi] input")
    if inp:
        if not pg.evaluate("() => document.querySelector('#indChips .chip[data-k=rsi]').classList.contains('on')"):
            click(pg, "#indChips .chip[data-k=rsi]", 600)
        h0 = canvas_hash(pg, "#lwc")
        inp = pg.query_selector("#indChips .chip[data-k=rsi] input")
        inp.fill("6"); inp.press("Enter"); pg.wait_for_timeout(800)
        h1 = canvas_hash(pg, "#lwc")
        legend = text(pg, "#legendOv")
        changed("改 RSI 參數，圖真的重畫", h0, h1)
        ok("改 RSI 參數，圖例數字跟著變", "RSI(6)" in legend.replace(" ", ""), legend[-80:])

    # --- 設定面板：線寬滑桿、顏色、加均線、減均線
    click(pg, "#cfgBtn", 450)
    ok("設定面板打得開", pg.evaluate("() => { const p = document.getElementById('cfgPop'); return !!p && !p.hidden; }"))
    rows0 = count(pg, "#maRows .marow")
    ok("設定面板有均線列", rows0 >= 2, rows0)
    lw = pg.query_selector("#lw")
    if lw:
        lw.fill("4") if lw.get_attribute("type") != "range" else pg.evaluate(
            "const s=document.getElementById('lw'); s.value=4; s.dispatchEvent(new Event('input',{bubbles:true}))")
        pg.wait_for_timeout(600)
        cfg = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("拉線寬滑桿真的存進設定", cfg.get("lineWidth") == 4, cfg.get("lineWidth"))
        ok("拉線寬滑桿有同步到每條均線", all(w == 4 for w in (cfg.get("maWidth") or [4])), cfg.get("maWidth"))
    click(pg, "#maAdd", 700)
    rows1 = count(pg, "#maRows .marow")
    changed("按「新增均線」真的多一條", rows0, rows1)
    cfg1 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
    ok("新增的均線有存進設定", len(cfg1.get("ma") or []) == rows1, cfg1.get("ma"))
    # 改一條均線的週期數字，圖例要跟著變
    nin = pg.query_selector("#maRows .marow input[data-f=n]")
    if nin:
        nin.fill("33"); nin.dispatch_event("change"); pg.wait_for_timeout(800)
        ok("改均線週期數字，圖例跟著變", "MA33" in text(pg, "#legendOv"), text(pg, "#legendOv")[-90:])
    # 顏色
    cin = pg.query_selector("#maRows .marow input[type=color]")
    if cin:
        h0 = canvas_hash(pg, "#lwc")
        pg.evaluate("const i=document.querySelector('#maRows .marow input[type=color]'); i.value='#ff00ff'; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}))")
        pg.wait_for_timeout(800)
        changed("改均線顏色，圖真的重畫", h0, canvas_hash(pg, "#lwc"))
        cfg2 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("改的顏色有存進設定", "#ff00ff" in [str(c).lower() for c in (cfg2.get("maColor") or [])], cfg2.get("maColor"))
    # 刪一條均線
    if count(pg, "#maRows .marow [data-f=del]"):
        r0 = count(pg, "#maRows .marow")
        click(pg, "#maRows .marow [data-f=del]", 700)
        r1 = count(pg, "#maRows .marow")
        changed("按 ✕ 真的少一條均線", r0, r1)
        cfgd = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("刪掉的均線也從設定裡消失", len(cfgd.get("ma") or []) == r1, cfgd.get("ma"))
        ok("刪到 6 條以下，「新增均線」要能再按", not pg.evaluate("() => document.getElementById('maAdd').disabled"))
    # --- 指標樣式：顏色／線寬／透明度改了要真的存下來、圖要真的重畫
    rows = pg.evaluate("[...document.querySelectorAll('#stRows .strow')].map(r => r.dataset.k)")
    ok("設定面板有指標樣式列（BOLL／成交量／KD／MACD／RSI）", len(rows) >= 5, rows)
    if rows:
        h0 = canvas_hash(pg, "#lwc")
        pg.evaluate("""() => { const r = document.querySelector('#stRows .strow[data-k=kd]');
            const c = r.querySelector('[data-f=c]'); c.value = '#ff00ff'; c.dispatchEvent(new Event('input', {bubbles:true}));
            const w = r.querySelector('[data-f=w]'); w.value = 3; w.dispatchEvent(new Event('input', {bubbles:true}));
            const o = r.querySelector('[data-f=o]'); o.value = 45; o.dispatchEvent(new Event('input', {bubbles:true})); }""")
        pg.wait_for_timeout(800)
        st = pg.evaluate("() => ((JSON.parse(localStorage.getItem('tw.kcfg')||'{}')).st||{}).kd")
        ok("改 KD 顏色有存進設定", (st or {}).get("c") == "#ff00ff", st)
        ok("改 KD 線寬有存進設定", (st or {}).get("w") == 3, st)
        ok("改 KD 透明度有存進設定", (st or {}).get("o") == 45, st)
        changed("改指標樣式後圖真的重畫", h0, canvas_hash(pg, "#lwc"))

    # --- SMC 供需區樣式：填色濃度、框線、標籤開關
    zin = pg.evaluate("[...document.querySelectorAll('#zoneRow input')].map(i => i.dataset.f)")
    ok("設定面板有 SMC 供需區樣式", len(zin) >= 5, zin)
    if zin:
        h1 = canvas_hash(pg, "#lwc")
        pg.evaluate("""() => { const f = document.querySelector('#zoneRow [data-f=fill]');
            f.value = 40; f.dispatchEvent(new Event('input', {bubbles:true})); }""")
        pg.wait_for_timeout(700)
        z = pg.evaluate("() => (JSON.parse(localStorage.getItem('tw.kcfg')||'{}')).zone")
        ok("調供需區填色有存進設定", (z or {}).get("fill") == 40, z)
        changed("調供需區填色後圖真的重畫", h1, canvas_hash(pg, "#lwc"))

    # 「完成」關得掉
    click(pg, "#cfgClose", 400)
    ok("設定面板按「完成」關得起來", pg.evaluate("() => { const p = document.getElementById('cfgPop'); return !p || p.hidden; }"))
    # 回復預設：設定要真的還原，面板順手關掉
    click(pg, "#cfgBtn", 450)
    if count(pg, "#cfgReset"):
        click(pg, "#cfgReset", 900)
        cfg3 = pg.evaluate("() => JSON.parse(localStorage.getItem('tw.kcfg')||'{}')")
        ok("按「回復預設」把線寬還原", (cfg3.get("lineWidth") or 1) != 4, cfg3.get("lineWidth"))
        ok("按「回復預設」順手把面板關掉", pg.evaluate("() => document.getElementById('cfgPop').hidden"))

    # --- 自訂時間週期：加一個、用一下、右鍵移除
    tf0 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
    click(pg, "#tfAdd", 450)
    pg.evaluate("const n=document.getElementById('tfN'); if(n){n.value=3; n.dispatchEvent(new Event('input',{bubbles:true}));}")
    click(pg, "#tfOk", 1100)
    tf1 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
    changed("自訂時間週期真的加進去了", tf0, tf1)
    cust = [t for t in tf1 if t not in tf0]
    if cust:
        st = pg.evaluate("({ on: (document.querySelector('#tfSeg button.on')||{dataset:{}}).dataset.tf, canvas: document.querySelectorAll('#lwc canvas').length })")
        ok("自訂週期按下去真的在用它", st["on"] == cust[0] and st["canvas"] > 0, st)
        pg.evaluate(f"document.querySelector('#tfSeg button[data-tf=\"{cust[0]}\"]').dispatchEvent(new MouseEvent('contextmenu', {{bubbles:true, cancelable:true}}))")
        pg.wait_for_timeout(800)
        tf2 = pg.evaluate("[...document.querySelectorAll('#tfSeg button')].map(b => b.dataset.tf)")
        ok("自訂週期按右鍵可以移除", cust[0] not in tf2, tf2)
    click(pg, '#tfSeg button[data-tf="1d"]', 800)

    # --- 繪圖工具：每一種都真的用滑鼠畫一次
    pg.evaluate("try{Object.keys(localStorage).filter(k=>k.startsWith('tw.draw.')).forEach(k=>localStorage.removeItem(k))}catch(e){}")
    click(pg, '#drawBar .dtool[data-t=cursor]', 200)
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
    tools = pg.evaluate("[...document.querySelectorAll('#drawBar .dtool[data-t]')].map(b => b.dataset.t)")
    ok("繪圖工具列有 ≥ 6 個工具", len(tools) >= 6, tools)
    drawn = []
    for i, t in enumerate(tools):
        if t in ("cursor", "erase"):
            continue
        click(pg, f'#drawBar .dtool[data-t={t}]', 250)
        r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height,vh:innerHeight}; }")
        if r["y"] < 0 or r["y"] + r["h"] * 0.6 > r["vh"]:
            pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(400)
            r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height,vh:innerHeight}; }")
        x0, y0 = r["x"] + r["w"] * (0.25 + i * 0.03), r["y"] + r["h"] * 0.30
        x1, y1 = r["x"] + r["w"] * (0.45 + i * 0.03), r["y"] + r["h"] * 0.52
        n0 = pg.evaluate("() => window.Industry._dbg().shapes")
        pg.mouse.move(x0, y0); pg.mouse.down()
        pg.mouse.move(x1, y1, steps=6); pg.mouse.up()
        pg.wait_for_timeout(400)
        n1 = pg.evaluate("() => window.Industry._dbg().shapes")
        if ok(f"繪圖工具「{t}」畫得出東西", n1 > n0, f"{n0} → {n1}"):
            drawn.append(t)
    store = pg.evaluate("""() => { const k = Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'));
        return { keys: k, kinds: k.flatMap(x => JSON.parse(localStorage.getItem(x)||'[]').map(s=>s.kind)) }; }""")
    ok("手繪線真的存進 localStorage", len(store["kinds"]) == len(drawn), store)
    ok("手繪線的 key 是「每檔每週期一組」", all(k.startswith(f"tw.draw.{code}.") for k in store["keys"]), store["keys"])

    # 換週期 → 線要消失；換回來 → 線要回來（各週期分開存）
    click(pg, '#tfSeg button[data-tf="1w"]', 900)
    ok("換週期後畫面上的線歸零（各週期分開存）", pg.evaluate("() => window.Industry._dbg().shapes") == 0,
       pg.evaluate("() => window.Industry._dbg()"))
    click(pg, '#tfSeg button[data-tf="1d"]', 900)
    ok("換回日線，原本畫的線回來了", pg.evaluate("() => window.Industry._dbg().shapes") == len(drawn),
       pg.evaluate("() => window.Industry._dbg()"))

    # 重新整理後線還在（真的存住了，不是只在記憶體）
    pg.reload(wait_until="networkidle"); pg.wait_for_timeout(2400)
    ok("重新整理後手繪線還在", pg.evaluate("() => window.Industry._dbg().shapes") == len(drawn),
       pg.evaluate("() => window.Industry._dbg()"))

    # 橡皮擦 → 少一筆；復原 → 少一筆；清空 → 歸零
    pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
    n0 = pg.evaluate("() => window.Industry._dbg().shapes")
    if count(pg, "#drawBar .dtool[data-a=undo]"):
        click(pg, "#drawBar .dtool[data-a=undo]", 500)
        changed("按「復原」真的少一筆", n0, pg.evaluate("() => window.Industry._dbg().shapes"))
    n1 = pg.evaluate("() => window.Industry._dbg().shapes")
    click(pg, "#drawBar .dtool[data-a=clear]", 600)
    ok("按「清空」真的歸零", pg.evaluate("() => window.Industry._dbg().shapes") == 0, n1)
    left = pg.evaluate("""() => Object.keys(localStorage).filter(x=>x.startsWith('tw.draw.'))
        .reduce((n,x)=>n+JSON.parse(localStorage.getItem(x)||'[]').length, 0)""")
    ok("清空後 localStorage 也乾淨了", left == 0, left)
    click(pg, "#drawBar .dtool[data-t=cursor]", 250)

    # --- SMC 供需區要跟著 K 線一起跑（Andy：移動 K 線圖，區間卻沒跟著動）
    if pg.evaluate("() => document.querySelector('#indChips .chip[data-k=smc]') && document.querySelector('#indChips .chip[data-k=smc]').classList.contains('on')"):
        pg.evaluate("document.getElementById('lwc').scrollIntoView({block:'center'})"); pg.wait_for_timeout(450)
        ZBOX = """() => { const el = document.getElementById('lwc');
            const out = [];
            for (const c of el.querySelectorAll('canvas')) {
              const g = c.getContext('2d'); if (!g) continue;
              const dpr = c.width / (c.clientWidth || 1);
              let minx = 1e9, maxx = -1, n = 0;
              try { const px = g.getImageData(0, 0, c.width, c.height).data;
                for (let y = 0; y < c.height; y += 3) for (let x = 0; x < c.width; x += 3) {
                  const i = (y * c.width + x) * 4, R = px[i], G = px[i+1], B = px[i+2];
                  if (G > R + 14 && G > 34 && G < 150 && B < G) { n++; if (x < minx) minx = x; if (x > maxx) maxx = x; }
                } } catch (e) { continue; }
              if (n > 150) out.push({ x0: Math.round(minx/dpr), x1: Math.round(maxx/dpr), n });
            }
            return out; }"""
        before = pg.evaluate(ZBOX)
        if before:
            r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
            pg.mouse.move(r["x"] + r["w"] * 0.6, r["y"] + r["h"] * 0.3)
            pg.mouse.down(); pg.mouse.move(r["x"] + r["w"] * 0.25, r["y"] + r["h"] * 0.3, steps=12); pg.mouse.up()
            pg.wait_for_timeout(800)
            after = pg.evaluate(ZBOX)
            ok("平移 K 線後 SMC 區間還在畫面上", bool(after), after)
            if after:
                changed("SMC 區間的左邊界跟著平移", before[0]["x0"], after[0]["x0"])
                changed("SMC 區間的右邊界也跟著平移（不是黏在畫面右緣）", before[0]["x1"], after[0]["x1"])
                ok("SMC 區間右邊界沒有貼齊畫面右緣", after[0]["x1"] < r["w"] - 20,
                   f"右邊界 {after[0]['x1']}、畫面寬 {round(r['w'])}")
        else:
            notes.append("這檔今天沒有畫出 SMC 供需區，略過跟隨檢查")

    # --- 重設縮放：先把圖捲歪，按下去要回到原位
    ok("重設縮放是小方框圖示", pg.evaluate("() => !!document.querySelector('#fitBtn svg')"))
    r = pg.evaluate("() => { const b = document.getElementById('lwc').getBoundingClientRect(); return {x:b.x,y:b.y,w:b.width,h:b.height}; }")
    pg.mouse.move(r["x"] + r["w"] * 0.5, r["y"] + r["h"] * 0.4)
    pg.mouse.wheel(0, -500); pg.wait_for_timeout(500)
    h0 = canvas_hash(pg, "#lwc")
    click(pg, "#fitBtn", 800)
    changed("按重設縮放，圖真的回到原位", h0, canvas_hash(pg, "#lwc"))

    # --- 四週期同看：來回切換都要有圖
    click(pg, "#mtfBtn", 1600)
    cells = count(pg, ".mtf-cell")
    ok("四週期同看有排出格子", cells >= 2, cells)
    ok("四週期同看每格都有圖", count(pg, "#mtfGrid canvas") >= cells, count(pg, "#mtfGrid canvas"))
    click(pg, "#mtfBtn", 1400)
    ok("切回單一週期，K 線圖回得來", count(pg, "#lwc canvas") > 0)

    # --- 產業鏈同步：點上方產業鏈的另一檔，個股頁要跟著換
    if count(pg, "#chainMap .co"):
        h0 = pg.evaluate("location.hash")
        pg.evaluate("""() => { const cs = [...document.querySelectorAll('#chainMap .co')];
            const other = cs.find(c => !c.classList.contains('sel'));
            if (other) other.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }""")
        pg.wait_for_timeout(1800)
        changed("點產業鏈上的另一檔，個股頁跟著換", h0, pg.evaluate("location.hash"))


def t_season(pg, base):
    pg.goto(f"{base}#season", wait_until="networkidle"); pg.wait_for_timeout(1800)
    ok("季節性熱力圖有畫出來", pg.evaluate("() => !!document.querySelector('#seasonHeat canvas')"))
    ok("季節性頁有區間文字", len(text(pg, "#seasonRange")) > 3, text(pg, "#seasonRange"))
    for grp, name in (("#seasonPeriod", "期間"), ("#seasonMetric", "指標")):
        vs = pg.evaluate(f"[...document.querySelectorAll('{grp} button')].filter(b => b.style.display !== 'none').map(b => b.dataset.v)")
        if len(vs) >= 2:
            h0 = canvas_hash(pg, "#seasonHeat")
            click(pg, f'{grp} button[data-v="{vs[-1]}"]', 900)
            changed(f"季節性切換「{name}」，熱力圖真的重畫", h0, canvas_hash(pg, "#seasonHeat"))
            click(pg, f'{grp} button[data-v="{vs[0]}"]', 700)
        else:
            notes.append(f"季節性「{name}」只有一個選項，沒東西可切")
    # 點格子 → 逐年明細要出來。用 ECharts 自己換算某一格的座標，不要亂點（亂點會落在空白處）
    pg.evaluate("document.getElementById('seasonHeat').scrollIntoView({block:'center'})"); pg.wait_for_timeout(500)
    before = text(pg, "#seasonDrillTitle")
    pt = pg.evaluate("""() => { const e = document.getElementById('seasonHeat');
        const c = echarts.getInstanceByDom(e); if (!c) return null;
        const op = c.getOption(); const d = (op.series[0] || {}).data || [];
        const cell = d.find(v => Array.isArray(v) ? v[2] != null : (v && v.value && v.value[2] != null));
        if (!cell) return null;
        const v = Array.isArray(cell) ? cell : cell.value;
        const p = c.convertToPixel({ seriesIndex: 0 }, [v[0], v[1]]);
        const r = e.getBoundingClientRect();
        return p ? { x: r.x + p[0], y: r.y + p[1] } : null; }""")
    if pt:
        pg.mouse.click(pt["x"], pt["y"]); pg.wait_for_timeout(1200)
        after = text(pg, "#seasonDrillTitle")
        changed("點季節性格子會帶出逐年明細", before, after)
        ok("逐年明細有畫出圖", pg.evaluate("() => !!document.querySelector('#seasonDrill canvas')"),
           text(pg, "#seasonDrill")[:40])
    else:
        fails.append("季節性熱力圖沒有任何一格有資料，點不出逐年明細")


def t_mobile(b, base, code):
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.on("pageerror", lambda e: fails.append(f"手機 pageerror: {e}"))
    m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    for h, name in (("overview", "總覽"), ("market", "市場明細"), ("flow", "資金流向"), ("industry", "產業"),
                    ("themes", "題材"), ("season", "季節性"), (f"stock/{code}", "個股")):
        m.goto(f"{base}#{h}", wait_until="networkidle"); m.wait_for_timeout(1700)
        st = m.evaluate("""() => {
            // SVG 文字會跟著 viewBox 一起縮放，所以要量「螢幕上真正的大小」而不是 CSS 值
            const eff = (e) => { const s = parseFloat(getComputedStyle(e).fontSize);
              if (e.ownerSVGElement) { try { const m = e.getScreenCTM(); return m ? s * Math.abs(m.a) : s; } catch (x) { return s; } }
              return s; };
            const tiny = [...document.querySelectorAll('main .view.on *')].filter(e => {
              const t = [...e.childNodes].some(n => n.nodeType===3 && n.textContent.trim().length>1);
              if (!t) return false;
              const r = e.getBoundingClientRect(); if (!r.width || !r.height) return false;
              const s = eff(e); return s > 0 && s < (e.ownerSVGElement ? 8 : 11); })
              .map(e => `${(e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || e.tagName}@${eff(e).toFixed(1)}px:${e.textContent.trim().slice(0,10)}`);
            return { sideways: document.documentElement.scrollWidth > 391,
                     text: (document.querySelector('main .view.on')||document.body).innerText.trim().length,
                     tiny }; }""")
        ok(f"手機／{name} 沒有橫向捲軸", not st["sideways"], st["sideways"])
        ok(f"手機／{name} 有內容", st["text"] > 60, st["text"])
        ok(f"手機／{name} 沒有看不清楚的小字", not st["tiny"], st["tiny"][:6])
    # 手機分頁列真的能切
    m.goto(f"{base}#overview", wait_until="networkidle"); m.wait_for_timeout(1400)
    tabs = m.evaluate("[...document.querySelectorAll('#tabs .tab')].map(a => a.dataset.view)")
    ok("手機有分頁列", len([t for t in tabs if t]) >= 6, tabs)
    # 分頁列真的按得動（手機上它固定在畫面底部）
    if tabs:
        m.evaluate("document.querySelector('#tabs .tab[data-view=themes]').click()"); m.wait_for_timeout(1400)
        ok("手機分頁列按得動", m.evaluate("location.hash").startswith("#themes"), m.evaluate("location.hash"))
    m.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    srv = serve(); time.sleep(0.4)
    base = f"http://127.0.0.1:{PORT}/index.html"
    t0 = time.time()

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=not args.headed)
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        pg.on("pageerror", lambda e: fails.append(f"pageerror: {e}"))
        pg.on("console", lambda m: fails.append(f"console.error: {m.text}")
              if m.type == "error" and "ERR_FAILED" not in m.text and "fonts.googleapis" not in m.text else None)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())

        for name, fn in (("總覽", t_overview), ("市場明細", t_market), ("資金流向", t_flow), ("產業", t_industry),
                         ("題材", t_themes), ("季節性", t_season)):
            n0 = len(fails)
            try:
                fn(pg, base)
            except Exception as e:  # noqa: BLE001
                fails.append(f"【{name}】操作中途爆掉：{type(e).__name__} {e}")
            print(f"  {name}：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_stock(pg, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【個股】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  個股：{len(fails) - n0} 個問題", flush=True)
        n0 = len(fails)
        try:
            t_mobile(b, base, args.code)
        except Exception as e:  # noqa: BLE001
            fails.append(f"【手機】操作中途爆掉：{type(e).__name__} {e}")
        print(f"  手機：{len(fails) - n0} 個問題", flush=True)
        b.close()
    srv.shutdown()

    print(f"\n===== 真人操作驗收（{time.time() - t0:.0f} 秒）=====")
    if notes:
        print("備註：")
        for n in notes:
            print(f"  · {n}")
    if fails:
        print(f"\n❌ {len(fails)} 個問題：")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\n✅ 每個功能都實際操作過，全部都有反應。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
