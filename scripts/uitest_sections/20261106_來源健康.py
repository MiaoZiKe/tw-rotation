# 驗收段落「來源健康1106」—— 2026-11-06（稽核 B：來源連續失敗）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用。不要寫三引號模組說明。
# flake8: noqa

# 驗法：同一份 meta.json 做兩組對照。
#   · 有 source_failing（連續 3 天）→ 提示要講「連續 3 天沒有取得資料」與最後成功日期，且不列內部代號（twse.price_daily）。
#   · 沒有 → 提示不出現「連續」字樣。
def t_source_health_1106(b, base):
    import datetime as _dt
    T = "來源健康1106"
    now = _dt.datetime.now(_dt.timezone.utc)
    ago = lambda h: (now - _dt.timedelta(hours=h)).isoformat()
    BASE = {"status": "ok", "history_days": 6595, "groups_health": {}, "table_summary": [],
            "last_run_trade_date": None, "last_run_phase": "full", "last_run_errors": [],
            "last_run_empty": [], "gaps": [], "data_date": "2026-11-05", "price_latest": "2026-11-05",
            "price_ahead_of_payload": False, "generated_at": ago(2), "last_run_at": ago(3)}
    failing = [{"source": "twse.price_daily", "days": 3, "last_ok_date": "2026-11-02", "last_error": "HTTP 500"}]
    seen = {}
    for name, meta in (("連續失敗", {**BASE, "source_failing": failing}), ("正常", {**BASE, "source_failing": []})):
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
    f, n = seen["連續失敗"], seen["正常"]
    ok(f"{T}：連續失敗時提示講「連續 3 天沒有取得資料」與最後一次取得資料的日期",
       "連續 3 天" in f and "2026-11-02" in f, f[:200])
    ok(f"{T}：提示不列內部代號（twse.price_daily 不出現）", "twse.price_daily" not in f, None)
    ok(f"{T}：沒有連續失敗時提示不出現「連續」字樣", "連續" not in n and "所有資料都已更新" in n, n[:160])


register("來源健康1106", lambda pg, b, base, code: t_source_health_1106(b, base), after="永久缺口1106")
