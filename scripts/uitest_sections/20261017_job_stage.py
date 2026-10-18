# 驗收段落「產出進度階段1017」—— 2026-10-17
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_free_port()、ROOT…直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 產出進度階段1017（site/articles.js jobProg、workers/account-api/articles.js stage）
# Andy 10-17（看著管理區「精選文章 → 產出進度」）：「這邊一直顯示排隊中，但我不清楚他狀況如何，所以多一個進度條，並且備註目前的階段 安排？製作？發布？等等」。
# 本機起真的 worker.js（devserver.mjs），管理者真的登入、真的在畫面上排一筆「自訂主題」請求，
# 再用機器路由（devserver 的本機鑰匙，等同 article-jobs.yml 的 mark_id／mark_status／stage）依序標各階段，
# 每一步都「重新整理整頁」（Andy 的用法）或按「↻ 更新進度」重讀，驗：
#   · 進度條寬度＝固定對照的百分比（排隊 0、安排 10、查資料 25、撰寫 45、插圖 65、驗收 80、發布中 92、完成 100），量的是畫面上 <i> 佔整條的比例
#   · 階段文字真的換了（「撰寫・18:42」這種）、排隊中寫「排隊中・下一輪 :05 開工」
#   · 完成變綠、失敗變紅且停在失敗前那一格（寫「卡在撰寫」）、取消變灰
#   · 「全部狀態」篩選照舊（選「失敗」只剩那筆）
#   · 版面：進度條、百分比、階段字兩兩不重疊、不超出格子、字 ≥ 11px、沒有整頁橫向捲軸
#   1440 與 390（觸控）各跑一輪。截圖：TW_JOBSTAGE_SHOTS=<資料夾>
JS_BOT_KEY = "dev-article-bot-key-0123456789abcdef"     # devserver.mjs 寫死的本機鑰匙（不是正式鑰匙）
JS_PCT = {"queued": 0, "plan": 10, "research": 25, "write": 45, "illus": 65, "review": 80, "publish": 92, "done": 100}
JS_LAB = {"plan": "安排主題", "research": "查資料", "write": "撰寫", "illus": "插圖", "review": "驗收", "publish": "發布中"}


def _jw(pg, expr, arg, timeout=6000):
    """帶參數的輪詢（wait_until 不收參數）：逾時回 False，不丟例外 —— 讓後面的 ok() 記下實際畫面。"""
    try:
        pg.wait_for_function(expr, arg=arg, timeout=timeout, polling=150)
        return True
    except Exception:  # noqa: BLE001
        return False


def t_job_stage_1017(b, base):
    T = "產出進度階段1017"
    import urllib.request
    shots = os.environ.get("TW_JOBSTAGE_SHOTS")
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    errs: list[str] = []

    def bot(body):
        r = urllib.request.Request(api + "/v1/articles/jobs/bot", data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + JS_BOT_KEY}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(r, timeout=5).read())
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    PROG = """(id) => { const tr = document.querySelector(`#artTpBody .jline[data-job="${id}"]`); if (!tr) return null;
        const p = tr.querySelector('.jprog'); if (!p) return { nop: true };
        const bar = p.querySelector('.jbar'), i = bar && bar.querySelector('i'), cap = p.querySelector('.jcap'), pc = p.querySelector('.jpct'), td = p.closest('td');
        const R = (e) => { const q = e.getBoundingClientRect(); return { l: q.left, r: q.right, t: q.top, b: q.bottom, w: q.width, h: q.height }; };
        const rb = R(bar), ri = R(i), rc = R(cap), rp = R(pc), rt = R(td);
        return { tone: p.dataset.tone, stage: p.dataset.stage, pct: +p.dataset.pct, ratio: rb.w ? ri.w / rb.w : -1, cap: cap.textContent, js: (cap.querySelector('.js') || {}).textContent,
                 color: getComputedStyle(i).backgroundColor, capColor: getComputedStyle(cap).color, aria: +bar.getAttribute('aria-valuenow'),
                 rb, rc, rp, rt, capCut: cap.scrollWidth > cap.clientWidth + 1,
                 fs: Math.min(...[cap, pc, ...cap.querySelectorAll('*')].map(e => parseFloat(getComputedStyle(e).fontSize))),
                 vis: rb.w > 20 && rb.h >= 4 && rt.r <= innerWidth + 1 && rt.l >= -1 }; }"""

    def layout_ok(st):
        """進度條那一列在階段字上面、兩者不重疊；百分比在條的右邊；三個都在格子裡面。"""
        if not st or st.get("nop"):
            return False
        rb, rc, rp, rt = st["rb"], st["rc"], st["rp"], st["rt"]
        return (max(rb["b"], rp["b"]) <= rc["t"] + 0.5 and rp["l"] >= rb["r"] - 0.5
                and all(x["l"] >= rt["l"] - 1 and x["r"] <= rt["r"] + 1 for x in (rb, rc, rp)) and not st["capCut"] and st["fs"] >= 11)

    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api（devserver）起得來", up):
            return
        INIT = "window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + "; try{localStorage.setItem('tw.live.on','0')}catch(e){}"

        # 管理者登入一次（桌機），之後兩個寬度都用同一份登入狀態
        c0 = b.new_context(viewport={"width": 1440, "height": 900})
        c0.add_init_script(INIT); c0.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        p0 = c0.new_page()
        p0.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(p0, "() => !!document.getElementById('acctBtn')", 8000)
        p0.click("#acctBtn")
        with p0.expect_popup() as pi:
            p0.click("#acctGo")
        pop = pi.value; pop.wait_for_selector("#as-andy", timeout=8000); pop.click("#as-andy")
        logged = wait_until(p0, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        if not ok(f"{T}：管理者（Andy 測試帳號）登入成功", bool(logged)):
            return
        p0.wait_for_timeout(500)
        state = c0.storage_state()
        c0.close()

        for W in (1440, 390):
            mob = W <= 640
            kw = {"has_touch": True, "is_mobile": True, "device_scale_factor": 1} if mob else {}
            ctx = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, storage_state=state, **kw)
            ctx.add_init_script(INIT); ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            TW = f"{T} {W}"

            def open_adm():
                pg.goto(base + "#admin/articles", wait_until="domcontentloaded")
                return wait_until(pg, "() => !!document.getElementById('artTpBody') && !!document.getElementById('artCusT') && !/讀取中/.test(document.getElementById('artTpBody').textContent)", 15000)

            def reload_adm():
                pg.reload(wait_until="domcontentloaded")
                wait_until(pg, "() => !!document.querySelector('#artTpBody .jline[data-job]')", 15000)
                pg.wait_for_timeout(250)

            try:
                if not ok(f"{TW}：管理者打開 #admin/articles 看得到主題候選清單（10-17 產出進度併進來）", bool(open_adm())):
                    continue
                hd = pg.evaluate("() => [...document.querySelectorAll('#artAdmTopics thead th')].map(t => t.textContent)")
                ok(f"{TW}：表頭有「進度」與「操作」、沒有舊的「產出狀態」，舊的產出進度表不在了", "進度" in hd and "操作" in hd and not any("狀態" in h for h in hd)
                   and pg.evaluate("() => !document.getElementById('artAdmJobs')"), hd)

                def add_custom(title):
                    pg.select_option("#artCusCat", "news")
                    pg.fill("#artCusT", title)
                    pg.click("#artCusArt")
                    _jw(pg, "(t) => [...document.querySelectorAll('#artTpBody tr[data-custom]')].some(r => r.textContent.includes(t) && r.querySelector('.jline[data-job]'))", title, 8000)
                    return pg.evaluate("(t) => { const r = [...document.querySelectorAll('#artTpBody tr[data-custom]')].find(r => r.textContent.includes(t)); const l = r && r.querySelector('.jline[data-job]'); return l ? +l.dataset.job : null; }", title)

                # ① 排一筆 → 排隊中：灰空條、「排隊中・下一輪 :05 開工」
                ja = add_custom(f"進度條驗收A-{W}")
                st = pg.evaluate(PROG, ja)
                ok(f"{TW}：畫面上排一筆 → 進度欄寫「排隊中・已通知 Claude・準備開工」（晚上寫明早 08:05）、空條（0%）、灰色", bool(st) and st["tone"] == "queued" and st["pct"] == 0
                   and st["ratio"] < 0.01 and st["cap"] in ("排隊中・已通知 Claude・準備開工", "排隊中・明早 08:05 開工") and st["vis"], st)
                ok(f"{TW}：排隊中那一格版面不重疊、不截字、字 ≥ 11px", layout_ok(st), st)
                if shots:
                    Path(shots).mkdir(parents=True, exist_ok=True)

                # ② 依序標各階段，每一步重新整理（奇數步重新整理整頁、偶數步按「↻ 更新進度」）
                prev = None
                for k, sg in enumerate(["plan", "research", "write", "illus", "review", "publish"]):
                    r = bot({"op": "mark", "id": ja, "status": "working", "stage": sg})
                    if k % 2 == 0:
                        reload_adm()
                        how = "重新整理整頁"
                    else:
                        before = pg.evaluate(PROG, ja)
                        pg.click("#artJfRef")
                        _jw(pg, "([id, s]) => { const p = document.querySelector(`#artTpBody .jline[data-job=\"${id}\"] .jprog`); return p && p.dataset.stage === s; }", [ja, sg], 6000)
                        pg.wait_for_timeout(500)      # 等寬度動畫（.45s）跑完再量
                        how = "按「↻ 更新進度」"
                        ok(f"{TW}：按「↻ 更新進度」之前畫面還是上一格（{before and before['stage']}），按了才換", bool(before) and before["stage"] != sg, before and before["stage"])
                    pg.wait_for_timeout(500)
                    st = pg.evaluate(PROG, ja)
                    want = JS_PCT[sg]
                    hm = re.compile(r"^" + JS_LAB[sg] + r"・\d{2}:\d{2}$")
                    ok(f"{TW}：機器路由標「{JS_LAB[sg]}」→ {how} → 進度條 {want}%（實際量 {st and round(st['ratio'] * 100, 1)}%）、寫「{JS_LAB[sg]}・時:分」、青色",
                       r.get("ok") is True and bool(st) and st["tone"] == "working" and st["stage"] == sg and st["pct"] == want and st["aria"] == want
                       and abs(st["ratio"] * 100 - want) <= 1.5 and bool(hm.match(st["cap"])) and (prev is None or st["ratio"] > prev), [r.get("error"), st])
                    ok(f"{TW}：「{JS_LAB[sg]}」那一格版面不重疊、不截字、字 ≥ 11px", layout_ok(st), st)
                    prev = st["ratio"]
                    if shots and sg == "write":
                        pg.locator("#artAdmTopics").screenshot(path=str(Path(shots) / f"jobstage_{W}_write.png"))

                # ③ 完成 → 綠、滿條
                r = bot({"op": "mark", "id": ja, "status": "done", "result": "uitest-done"})
                reload_adm(); pg.wait_for_timeout(500)
                st = pg.evaluate(PROG, ja)
                ok(f"{TW}：標「完成」→ 滿條 100%、綠色、寫「已完成・時:分」",
                   bool(st) and st["tone"] == "done" and abs(st["ratio"] - 1) < 0.015 and bool(re.match(r"^已完成・\d{2}:\d{2}$", st["cap"]))
                   and st["color"] != pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--cyan')"), st)
                green = st["color"]

                # ④ 另一筆：做到撰寫失敗 → 紅、停在 45%、「失敗・卡在撰寫」
                jb_ = add_custom(f"進度條驗收B-{W}")
                bot({"op": "mark", "id": jb_, "status": "working", "stage": "write"})
                r = bot({"op": "mark", "id": jb_, "status": "failed", "result": "驗收：故意失敗"})
                reload_adm(); pg.wait_for_timeout(500)
                st = pg.evaluate(PROG, jb_)
                ok(f"{TW}：撰寫時標「失敗」→ 紅條停在撰寫那一格（45%）、寫「失敗・卡在撰寫・時:分」、字也變紅",
                   r.get("job", {}).get("stage") == "write" and bool(st) and st["tone"] == "failed" and st["pct"] == 45 and abs(st["ratio"] * 100 - 45) <= 1.5
                   and bool(re.match(r"^失敗・卡在撰寫・\d{2}:\d{2}$", st["cap"])) and st["color"] != green and st["capColor"] == st["color"], st)
                ok(f"{TW}：失敗那一格版面不重疊、不截字", layout_ok(st), st)

                # ⑤ 第三筆：畫面上按「取消」→ 已取消、灰、空條
                jc = add_custom(f"進度條驗收C-{W}")
                pg.click(f"#artTpBody button[data-cancel=\"{jc}\"]")
                _jw(pg, "(id) => { const p = document.querySelector(`#artTpBody .jline[data-job=\"${id}\"] .jprog`); return p && p.dataset.tone === 'cancelled'; }", jc, 6000)
                st = pg.evaluate(PROG, jc)
                ok(f"{TW}：畫面上按「取消」→ 寫「已取消・時:分」、空條", bool(st) and st["js"] == "已取消" and st["ratio"] < 0.01 and bool(re.match(r"^已取消・\d{2}:\d{2}$", st["cap"])), st)

                # ⑥ 第四筆做到插圖、第五筆留在排隊 → 一張表五種狀態並排（截圖給人看）
                jd = add_custom(f"進度條驗收D-{W}")
                bot({"op": "mark", "id": jd, "status": "working", "stage": "illus"})
                je = add_custom(f"進度條驗收E-{W}")
                reload_adm(); pg.wait_for_timeout(600)
                allp = pg.evaluate(f"() => [{ja},{jb_},{jc},{jd},{je}].map(id => {{ const p = document.querySelector(`#artTpBody .jline[data-job=\"${{id}}\"] .jprog`); return p ? [p.dataset.tone, +p.dataset.pct] : null; }})")
                ok(f"{TW}：同一張表五種狀態並排（完成 100／失敗 45／取消 0／插圖 65／排隊 0）", allp == [["done", 100], ["failed", 45], ["cancelled", 0], ["working", 65], ["queued", 0]], allp)
                bad = [i for i in (ja, jb_, jc, jd, je) if not layout_ok(pg.evaluate(PROG, i))]
                ok(f"{TW}：五列的進度格版面全部不重疊、不截字、字 ≥ 11px", not bad, bad)
                # 整張卡：各列的格子彼此不重疊（手機改成一列一張卡，格子在卡裡排成三行）
                ov = pg.evaluate("""() => { const out = []; document.querySelectorAll('#artTpBody tr[data-tid]').forEach(tr => {
                    const cs = [...tr.children].filter(td => td.getClientRects().length && getComputedStyle(td).display !== 'none').map(td => [td.cellIndex, td.getBoundingClientRect()]);
                    for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) { const a = cs[i][1], c = cs[j][1];
                      if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > 1 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 1) out.push([tr.dataset.tid, cs[i][0], cs[j][0]]); } }); return out; }""")
                ok(f"{TW}：每一列的各格（選／分數／類別／標題／進度／操作）互不重疊", not ov, ov[:5])
                hs = pg.evaluate("() => document.scrollingElement.scrollWidth - innerWidth")
                ok(f"{TW}：沒有整頁橫向捲軸", hs <= 1, hs)
                if mob:
                    inview = pg.evaluate(f"() => {{ const td = document.querySelector('#artTpBody .jline[data-job=\"{jd}\"]').closest('td.jpc'); const r = td.getBoundingClientRect(); const w = td.closest('.tbw').getBoundingClientRect(); return r.left >= w.left - 1 && r.right <= w.right + 1 && r.width > 200; }}")
                    ok(f"{TW}：手機每筆一張卡，進度條不用左右捲就看得到（吃滿卡寬）", inview, None)
                # ⑦ 「全部狀態」篩選照舊：選「失敗」只剩那一筆；選回全部恢復
                n_all = pg.evaluate("() => document.querySelectorAll('#artTpBody .jline[data-job]').length")
                pg.select_option("#artJfSt", "failed"); pg.wait_for_timeout(200)
                # 同一個 devserver 兩個寬度共用：1440 那輪的失敗那筆也在（所以驗「全部都是失敗、這輪那筆在裡面」）
                fl = pg.evaluate("() => [...document.querySelectorAll('#artTpBody .jline[data-job]')].map(r => [+r.dataset.job, r.querySelector('.jprog').dataset.tone])")
                ok(f"{TW}：篩選「失敗」→ 只剩失敗的（這一輪故意失敗的那筆在裡面）", bool(fl) and all(t == "failed" for _, t in fl) and jb_ in [i for i, _ in fl] and len(fl) < n_all, fl)
                pg.select_option("#artJfSt", ""); pg.wait_for_timeout(200)
                ok(f"{TW}：篩選選回「全部狀態」→ {n_all} 筆都回來", pg.evaluate("() => document.querySelectorAll('#artTpBody .jline[data-job]').length") == n_all, None)
                if shots:
                    pg.locator("#artAdmTopics").scroll_into_view_if_needed()
                    pg.locator("#artAdmTopics").screenshot(path=str(Path(shots) / f"jobstage_{W}_all.png"))
                    if mob:
                        pg.screenshot(path=str(Path(shots) / f"jobstage_{W}_screen.png"))
            finally:
                ctx.close()
        ok(f"{T}：沒有 JS 錯誤", not errs, errs[:3])
    finally:
        dev.terminate()
        try:
            dev.wait(timeout=5)
        except Exception:  # noqa: BLE001
            dev.kill()


register("產出進度階段1017", lambda pg, b, base, code: t_job_stage_1017(b, base))
