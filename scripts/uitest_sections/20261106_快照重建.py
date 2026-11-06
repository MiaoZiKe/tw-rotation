# 驗收段落「快照重建1106」—— 2026-11-06（盤中快照缺口用替代來源補回）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用。不要寫三引號模組說明。
# flake8: noqa

# 缺口日用 Yahoo 5 分 K 重建後，資料狀態提示要講「替代來源重建」與日期，口徑不同要明說，但不算失敗、不亮紅黃燈。
# 驗法：同一份 meta.json 對照 —— 有 tape_rebuilt vs 沒有。
def t_rebuilt_1106(b, base):
    import datetime as _dt
    T = "快照重建1106"
    now = _dt.datetime.now(_dt.timezone.utc)
    ago = lambda h: (now - _dt.timedelta(hours=h)).isoformat()
    BASE = {"status": "ok", "history_days": 6595, "groups_health": {}, "table_summary": [],
            "last_run_trade_date": None, "last_run_phase": "full", "last_run_errors": [],
            "last_run_empty": [], "data_date": "2026-11-05", "price_latest": "2026-11-05",
            "price_ahead_of_payload": False, "generated_at": ago(2), "last_run_at": ago(3), "gaps": []}
    rbt = [{"date": "2026-10-28", "src": "rebuild:yahoo5m", "note": "x"}, {"date": "2026-10-29", "src": "rebuild:yahoo5m", "note": "x"}]
    seen = {}
    for name, meta in (("有重建", {**BASE, "tape_rebuilt": rbt}), ("沒重建", {**BASE, "tape_rebuilt": []})):
        ctx = b.new_context(viewport={"width": 1500, "height": 1000})
        pg = ctx.new_page()
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("**/data/meta.json*", (lambda m: lambda r: r.fulfill(
            status=200, content_type="application/json; charset=utf-8",
            headers={"cache-control": "no-store"}, body=json.dumps(m, ensure_ascii=False)))(meta))
        pg.goto(base + "#overview", wait_until="domcontentloaded", timeout=90000)
        wait_until(pg, "() => { const e = document.getElementById('asof'); return !!e && (e.dataset.fresh || '') !== ''; }", 90000)
        seen[name] = pg.evaluate("() => document.getElementById('asof').dataset.fresh || ''")
        ctx.close()
    g, n = seen["有重建"], seen["沒重建"]
    ok(f"{T}：有重建時提示列出兩個日期與「替代來源重建」字樣",
       "替代來源重建" in g and "2026-10-28" in g and "2026-10-29" in g, g[:160])
    ok(f"{T}：有重建時不出現「更新失敗」「沒有更新」（不算紅燈、黃燈）",
       "更新失敗" not in g and "沒有更新" not in g, g[:160])
    ok(f"{T}：沒重建時提示照舊，不出現「替代來源」", "替代來源" not in n and "所有資料都已更新" in n, n[:160])


register("快照重建1106", lambda pg, b, base, code: t_rebuilt_1106(b, base), after="永久缺口1106")
