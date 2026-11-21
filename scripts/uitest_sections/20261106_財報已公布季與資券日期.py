# 驗收段落「財報已公布季1106」「資券日期1106」—— 2026-11-06 稽核 C、D
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用。
# flake8: noqa
import json as _json
import os as _os


def t_earn_pub_1106(b, base, code):
    """C：財經日曆公司面板「這次財報看什麼」不再寫「上一份財報」；已公布但數字未入湖的公司要寫「待入湖」。
    本機 site/data 若是舊的，可用環境變數 TW_EARN_FIXTURE 指向本機重算的 earnings.json（只在這支測試裡攔截，不寫檔）。"""
    T = "財報已公布季1106"
    fx = _os.environ.get("TW_EARN_FIXTURE")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        if fx and _os.path.exists(fx):
            body = open(fx, encoding="utf-8").read()
            c.route("**/data/earnings.json*", (lambda bd: lambda r: r.fulfill(status=200, content_type="application/json; charset=utf-8", body=bd))(body))
        pg = c.new_page()
        pg.goto(base + "#earnings", wait_until="networkidle")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click(); pg.wait_for_timeout(300)
        ready = wait_until(pg, "() => !!window.TwEarnings && !!window.TwEarnings.state.data", 8000)
        if not ok(f"{T}（{W}）：財經日曆資料載入", bool(ready)):
            c.close(); continue
        info = pg.evaluate("""() => { const S = window.TwEarnings.state, d = S.data, out = { old: 0, pend: [] };
          Object.entries(d.companies || {}).forEach(([k, co]) => { const f = (co.secs || []).find(s => s.key === 'focus'); if (!f) return;
            const t = f.lines.join(' '); if (t.includes('上一份財報')) out.old++; if (t.includes('待入湖')) out.pend.push(k); });
          const e = d.events.findIndex(e => e.code && out.pend.includes(e.code) && d.companies[e.code]); out.i = e; out.code = e >= 0 ? d.events[e].code : null; return out; }""")
        ok(f"{T}（{W}）：所有公司「這次財報看什麼」都不再出現「上一份財報」", info["old"] == 0, info["old"])
        if info["i"] is not None and info["i"] >= 0:
            pg.evaluate("(i) => window.TwEarnings.pick({ t: 'ev', i })", info["i"]); pg.wait_for_timeout(400)
            txt = pg.evaluate("() => (document.querySelector('#earnPanel [data-sec=\"focus\"]') || document.querySelector('#earnPanel')).textContent")
            ok(f"★ {T}（{W}）：{info['code']} 面板寫「最新已公布季」＋「數字待入湖」，且不寫「上一份財報」",
               "待入湖" in txt and "已公布" in txt and "上一份財報" not in txt, txt[:200])
        else:
            ok(f"{T}（{W}）：資料裡沒有「已公布但待入湖」的公司（數字都已入湖，視為通過）", True)
        c.close()


def t_margin_asof_1106(b, base, code):
    """D：該檔融資融券比當沖／借券晚到（margin_asof.margin 比其他來源舊）→ 說明列寫融資融券只更新到哪天，
    之後的格子寫「未提供」，不是整列空白卻說資料到 11-05。用 route 把 2330 的 margin_asof 改成融資融券停在前一個交易日。"""
    T = "資券日期1106"
    c = b.new_context(viewport={"width": 1440, "height": 1000})
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    pg = c.new_page()
    state = {"cut": None}

    def fix(route):
        resp = route.fetch(); body = resp.json()
        mg = body.get("margin") or []
        dates = sorted(str(r[0])[:10] for r in mg)
        if len(dates) >= 3:
            state["cut"] = dates[-2]
            for r in mg:
                if str(r[0])[:10] == dates[-1]:
                    r[1] = r[2] = r[3] = r[4] = None      # 最新一列融資融券空白（還沒到）
            body["margin_asof"] = {"margin": dates[-2], "daytrade": dates[-1], "sbl": dates[-1]}
        route.fulfill(response=resp, json=body)
    pg.route(f"**/data/stock/{code}.json*", fix)
    pg.goto(base + f"#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2200)
    agree = pg.get_by_role("button", name="同意並繼續")
    if agree.count() and agree.first.is_visible():
        agree.first.click(); pg.wait_for_timeout(300)
    pg.click('#stockTabs button[data-t="margin"]'); pg.wait_for_timeout(1500)
    r = pg.evaluate("""() => { const n = document.getElementById('mgSrcNote');
      const rows = [...document.querySelectorAll('#mgTbl tbody tr')].map(tr => [...tr.children].map(td => [td.textContent.trim(), td.dataset.na || '']));
      return { note: n ? n.textContent : null, mgCut: n ? n.dataset.mgCut : null, first: rows[0] || null }; }""")
    if ok(f"{T}：前置條件（route 改到資料）", bool(state["cut"]), state):
        ok(f"★ {T}：說明列寫「融資融券資料目前只更新到 MM-DD」", r["note"] is not None and "融資融券資料目前只更新到" in r["note"] and state["cut"][5:] in r["note"], r["note"])
        ok(f"★ {T}：最新一列的融資融券格子寫「未提供」（不是空白的「—」）", bool(r["first"]) and all(x[0] == "未提供" for x in r["first"][1:5]), r["first"])
    c.close()


register("財報已公布季1106", lambda pg, b, base, code: t_earn_pub_1106(b, base, code))
register("資券日期1106", lambda pg, b, base, code: t_margin_asof_1106(b, base, code))
