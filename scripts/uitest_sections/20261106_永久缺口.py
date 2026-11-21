# 驗收段落「永久缺口1106」—— 2026-11-06（資料來源健康 A 段）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用。不要寫三引號模組說明。
# flake8: noqa

# CEO 拍板：盤中快照超過來源保存期、補不回來的交易日＝「永久缺口」。
# 要列在資料狀態（頂端徽章的提示）裡，但不算失敗、不亮紅燈。
# 驗法：同一份 meta.json 做兩組對照 —— 有缺口 vs 沒缺口。
#   · 有缺口：提示要列出日期與「永久缺口」字樣，且不出現「更新失敗」「沒有更新」（那些是紅／黃燈的字）。
#   · 沒缺口：提示照舊只說「所有資料都已更新」。
# 注意：頁面上級別（warn／bad）只存在隱藏的橫幅裡，DOM 讀不到燈號，所以「不亮燈」用對照組＋否定字樣來驗。
def t_gaps_1106(b, base):
    import datetime as _dt
    T = "永久缺口1106"
    now = _dt.datetime.now(_dt.timezone.utc)
    ago = lambda h: (now - _dt.timedelta(hours=h)).isoformat()
    BASE = {"status": "ok", "history_days": 6595, "groups_health": {}, "table_summary": [],
            "last_run_trade_date": None, "last_run_phase": "full", "last_run_errors": [],
            "last_run_empty": [], "data_date": "2026-11-05", "price_latest": "2026-11-05",
            "price_ahead_of_payload": False, "generated_at": ago(2), "last_run_at": ago(3)}
    gaps = [{"date": "2026-10-28", "reason": "永久缺口"}, {"date": "2026-10-29", "reason": "永久缺口"}]
    seen = {}
    for name, meta in (("有缺口", {**BASE, "gaps": gaps}), ("沒缺口", {**BASE, "gaps": []})):
        ctx = b.new_context(viewport={"width": 1500, "height": 1000})
        pg = ctx.new_page()
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.route("**/data/meta.json*", (lambda m: lambda r: r.fulfill(
            status=200, content_type="application/json; charset=utf-8",
            headers={"cache-control": "no-store"}, body=json.dumps(m, ensure_ascii=False)))(meta))
        pg.goto(base + "#overview", wait_until="domcontentloaded", timeout=90000)
        wait_until(pg, "() => { const e = document.getElementById('asof'); return !!e && (e.dataset.fresh || '') !== ''; }", 90000)
        tip = pg.evaluate("() => document.getElementById('asof').dataset.fresh || ''")
        seen[name] = tip
        ctx.close()
    g, n = seen["有缺口"], seen["沒缺口"]
    ok(f"{T}：有缺口時提示列出兩個永久缺口日期與「永久缺口」字樣",
       "永久缺口" in g and "2026-10-28" in g and "2026-10-29" in g, g[:160])
    ok(f"{T}：有缺口時不出現「更新失敗」「沒有更新」（缺口不算紅燈、黃燈）",
       "更新失敗" not in g and "沒有更新" not in g, g[:160])
    ok(f"{T}：沒缺口時提示照舊，不出現「永久缺口」", "永久缺口" not in n and "所有資料都已更新" in n, n[:160])


register("永久缺口1106", lambda pg, b, base, code: t_gaps_1106(b, base), after="資料狀態")
