# 驗收段落「恐慌圖軸1109」
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_sub_ctx() 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _FEAR1109_ 開頭（所有段落 exec 進同一個命名空間）。
# Andy 11-09：「確認一下恐慌指數上限 若只有 100 就調整 100 就好，不要上面有那麼多空白」（美股 3 月：上格 Y 軸 94～106 一片空白、下格 VIX 被擠扁）。
# 真的操作：
#   1. 台股、美股各切一次、期間 1月／3月／全部各按一次：上格每條線在視窗內都有資料；上格 Y 軸上限 ≤ 視窗內資料最大值＋3% 呼吸＋0.1，下限同理
#   2. 下格（恐慌指數）Y 軸上限 ≤ 視窗內最大值＋4% 呼吸＋0.1（不再多留一整格、不硬撐恐慌色帶）
#   3. 美股上格資料被清空（模擬指數缺）→ 不畫空的上格：只剩 1 個 grid、整張圖高度讓給 VIX，圖例也沒有「上格：期間起點＝100」

def t_fear_1109(b, base, code):
    T = "恐慌圖軸1109"
    errs: list = []
    c, sent, st = _sub_ctx(b, "admin", owner=True, plan="free")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.querySelector('#hero .osc[data-k=\"fear\"]') && !!window.FearCard && !!FearCard._s.data", 30000)
    pg.wait_for_timeout(700)
    if pg.evaluate("() => { const o = document.getElementById('pwOv'); return !!o && o.getClientRects().length > 0; }"):
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('#hero .osc[data-k=\"fear\"]').scrollIntoView({block: 'center'})")
    pg.locator('#hero .osc[data-k="fear"]').click(position={"x": 30, "y": 60})
    if not ok(f"{T} 走勢圖卡打得開", wait_until(pg, "() => !!document.querySelector('#ovFearChart')", 6000)):
        return
    pg.wait_for_timeout(1000)
    JS = """() => { const el = document.getElementById('ovFearChart'); const ch = echarts.getInstanceByDom(el); const o = ch.getOption();
        const z = o.dataZoom[0], a = +z.startValue, b2 = +z.endValue;
        const rng = (s) => { const v = s.data.filter(p => p[0] >= a && p[0] <= b2).map(p => p[1]); return v.length ? [Math.min(...v), Math.max(...v)] : null; };
        const tops = o.series.filter(s => /^top-/.test(s.id || '')), bot = o.series.find(s => /^bot-/.test(s.id || ''));
        const tr = tops.map(rng).filter(Boolean), br = bot ? rng(bot) : null;
        return { grids: o.grid.length, ys: o.yAxis.map(y => [y.min, y.max]), tops: tops.length, topsWithData: tr.length,
          topLo: tr.length ? Math.min(...tr.map(x => x[0])) : null, topHi: tr.length ? Math.max(...tr.map(x => x[1])) : null, bot: br,
          h: Math.round(el.getBoundingClientRect().height), leg: document.getElementById('fzLeg').innerText }; }"""
    for mkt, label in (("tw", "台股"), ("us", "美股")):
        pg.locator("#fzMkt button", has_text=label).click(); pg.wait_for_timeout(700)
        for per in ("1月", "3月", "全部"):
            pg.locator("#fzPer button", has_text=per).click(); pg.wait_for_timeout(500)
            f = pg.evaluate(JS)
            if f["tops"]:
                ok(f"{T} {label}／{per}：上格每條線都有資料（{f['tops']} 條）", f["topsWithData"] == f["tops"] and f["grids"] == 2, f)
                ok(f"{T} {label}／{per}：上格 Y 軸貼齊資料（上限 ≤ 最高值＋3%＋0.1、下限 ≥ 最低值－3%－0.1）",
                   f["ys"][0][1] <= f["topHi"] * 1.03 + 0.1 + (f["topHi"] - f["topLo"]) * 0.03 and f["ys"][0][0] >= f["topLo"] * 0.97 - 0.1 - (f["topHi"] - f["topLo"]) * 0.03 - 0.1, f)
            if f["bot"]:
                yb = f["ys"][-1]; span = f["bot"][1] - f["bot"][0]
                ok(f"{T} {label}／{per}：下格恐慌指數 Y 軸上限貼齊（≤ 最高值＋4% 呼吸＋0.1）", yb[1] <= f["bot"][1] + max(0.5, span * 0.04) + 0.1 and yb[1] >= f["bot"][1], f)
    # 3. 上格沒資料 → 不畫空的上格
    pg.locator("#fzMkt button", has_text="台股").click(); pg.wait_for_timeout(500)
    pg.evaluate("() => { FearCard._s.data.idx.us = {}; }")
    pg.locator("#fzMkt button", has_text="美股").click(); pg.wait_for_timeout(800)
    f = pg.evaluate(JS)
    ok(f"{T} 美股上格沒資料 → 只剩 1 格、不畫空的上格，圖高度給 VIX（Y 軸 1 組、圖例沒有「上格」）", f["grids"] == 1 and len(f["ys"]) == 1 and "上格" not in f["leg"] and "VIX" in f["leg"], f)
    ok(f"{T} 沒有 JS 例外", not errs, errs[:3])
    c.close()


register("恐慌圖軸1109", lambda pg, b, base, code: t_fear_1109(b, base, code))
