# 驗收段落「會員概況真實人數1125」
# 由 _uitest.py exec 載入：ok()、wait_until()、_adm2_ctx… 直接可用。
# flake8: noqa

# Andy 11-25：「需要確認會員概況，訪客人數有變多但會員人數固定 是否有沒更新到?」
# 根因：甜甜圈的「註冊會員」是 ev:session_login 開站次數 × 名單比例的估算，不是人數。
# 驗：① 流量觀測卡片出現「註冊會員 N 人・近 7 天新增 M」，N 等於 /v1/admin/members/count 的 total（示範資料＝示範會員數）
#     ② 甜甜圈裡估算那段改名「登入開站次數（估算）」，不再叫「註冊會員」
#     ③ 把 members/count 換成 total=4321、new7=17 → 畫面跟著變（真的讀端點，不是寫死）
def t_member_count_1125(b, base, code):
    T = "會員概況真實人數1125"
    pbase = base.replace("/index.html", "/preview/style-guide/index.html")
    for fake in (None, {"total": 4321, "new7": 17, "new30": 88}):
        c, sent = _adm2_ctx(b, width=1440)
        if fake:   # 正式路徑（非預覽、不走示範資料）：Worker 的 members/count 回假值，後註冊的 route 優先
            body = json.dumps(fake)
            c.route(ADM2_API + "/v1/admin/members/count", lambda r: r.fulfill(status=200, content_type="application/json", body=body, headers={"Access-Control-Allow-Origin": "*"}))
        else:
            c.route(re.compile(r".*/preview/style-guide/.*"), lambda r: r.continue_(url=r.request.url.replace("/preview/style-guide/", "/")))
        pg = c.new_page()
        pg.goto((base if fake else pbase) + "#admin/traffic", wait_until="domcontentloaded")
        got = wait_until(pg, "() => !!document.getElementById('trMemCnt')", 15000)
        if not ok(f"{T}：會員概況卡出現註冊會員人數列", bool(got)):
            c.close(); continue
        r = pg.evaluate("""() => { const m = document.getElementById('trMemCnt'); const n = (k) => { const e = m.querySelector('[data-n=' + k + ']'); return e ? +e.textContent.replace(/,/g, '') : null; };
            const lg = [...document.querySelectorAll('#trDonut ul.lg li')].map((li) => li.textContent);
            return { total: n('total'), new7: n('new7'), txt: m.textContent, est: lg.some((t) => t.includes('登入開站次數（估算）')), oldName: lg.some((t) => /^註冊會員/.test(t.trim())) }; }""")
        if fake is None:
            ok(f"{T}：顯示人數與近 7 天新增", r["total"] is not None and r["total"] > 0 and r["new7"] is not None and "近 7 天新增" in r["txt"], r)
            ok(f"{T}：甜甜圈估算段改名「登入開站次數（估算）」、不再叫註冊會員", r["est"] and not r["oldName"], r)
        else:
            ok(f"{T}：端點值變了畫面跟著變（4321／17）", r["total"] == 4321 and r["new7"] == 17, r)
        c.close()


register("會員概況真實人數1125", lambda pg, b, base, code: t_member_count_1125(b, base, code))
