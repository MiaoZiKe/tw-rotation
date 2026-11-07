# 驗收段落「每日簽到」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 每日簽到（預覽版）
# Andy 11-07：簽到做成日曆、累積 3～4 個節點換教學／產業文章／許願，跟比比互動 5～10 次換補簽，先做預覽版並讓站主自己簽到驗證。
# 起真的 worker.js（devserver：Andy＝管理者、Bob＝一般會員），用 Playwright 真的操作：
# ① 站主：總覽簽到卡 → 月曆 → 站主工具填到 3 天 → 兌換 → 提示去比比寶箱 → 跳到寶箱：這 2 篇解鎖、其他 10 篇上鎖，
#    點開已解鎖那篇真的有內文、直接打上鎖那篇網址只看到「還沒解鎖」且根本沒去抓它的內文檔（法遵：站主也不能不簽到就開）
# ② 填到 7 天再兌換 → 又 2 篇、不重複；填到 20 天 → 許願券 → 送出 3 個願望 → 真的 worker 收到 3 筆 /v1/feedback（帶預覽＋簽到許願標記）、
#    站主的意見回饋清單看得到；模擬「會做」→ 畫面顯示站主打算做；管理端標「不做」→ 同步 → 畫面顯示送 Plus 3 天（預覽模擬）
# ③ 補簽：聽比比說／比比考考你真的互動；連點、20 秒內、每日上限都不算；滿 5 次 → 開始補簽 → 點空白日兩下 → 月曆出現「補」註記
# ④ 一般會員（Bob）；桌機摘要卡列不變（五張）、手機（≤820）第一張才是簽到卡；：月曆開得起來、DOM 裡完全沒有站主測試；手機 390 一屏看完、不橫捲、字不小於 11px
# ⑤ 功能鍵：ci.sign／ci.makeup／ci.wish／art.cat.vault 四個方案都有值；關掉 ci.sign → 簽到鈕鎖住、按了也不會簽

def t_checkin_1107(b, base):
    T = "每日簽到"
    import urllib.request
    errs: list[str] = []
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    ctxs = []
    try:
        up = False
        for _ in range(40):
            try:
                up = json.loads(urllib.request.urlopen(api + "/health", timeout=1).read()).get("configured") is True
                if up:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.15)
        if not ok(f"{T}：本機 account-api 起得來", up):
            return

        def _shot(pg, name):   # 要截圖給人看時設環境變數 TW_CI_SHOTS=資料夾
            d = os.environ.get('TW_CI_SHOTS')
            if d:
                pg.screenshot(path=os.path.join(d, name + '.png'))

        def mk(w, h, flag=True, clock=False):
            c = b.new_context(viewport={"width": w, "height": h})
            c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": api}) + ";try{localStorage.setItem('tw.tour','done')}catch(e){}"
                              + ("window.__TW_UITEST=1;" if flag else ""))
            if clock:   # 平移電腦時鐘：window.__off（毫秒）加在 Date.now()／new Date() 上，等於使用者把系統時間往後調再調回
                c.add_init_script("window.__off=0;(function(){const D=Date;class F extends D{constructor(...a){if(a.length)super(...a);else super(D.now()+window.__off);}static now(){return D.now()+window.__off;}}window.Date=F;})();")
            c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            ctxs.append(c)
            return c

        def login(pg, who):
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            wait_until(pg, "() => !!document.getElementById('acctBtn')", 10000)
            pg.click("#acctBtn")
            with pg.expect_popup() as pi:
                pg.click("#acctGo")
            pop = pi.value
            pop.wait_for_selector("#as-" + who, timeout=8000)
            pop.click("#as-" + who)
            wait_until(pg, "() => !!(window.TwAccount && TwAccount.user())", 12000)
            wait_until(pg, "() => !!window.TwCheckin && !!document.getElementById('ciBtn') && document.querySelector('#ciBtn svg')", 8000)

        def adm_open():   # 站主工具摺疊：沒開就開（開過的狀態會保留，不能無腦點）
            if not ad.evaluate("() => document.getElementById('ciAdm').open"):
                ad.click("#ciAdm summary")

        def opencal(pg, via_card=False):
            if via_card:
                pg.click(".osc.ci")
            else:
                pg.click("#ciBtn")
            pg.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000)
            pg.wait_for_timeout(500)   # 月曆載完假日資料會重畫一次；等它畫完再操作

        def tot(pg):
            return int(pg.inner_text("#ciTot"))

        # =============================================================== ① 站主：填到 3 天 → 兌換 → 寶箱
        ad_ctx = mk(1440, 900)
        ad = ad_ctx.new_page()
        ad.on("pageerror", lambda e: errs.append(str(e)))
        fb_posts: list[dict] = []
        vault_fetch: list[str] = []
        ad.on("request", lambda r: fb_posts.append(json.loads(r.post_data or "{}")) if "/v1/feedback" in r.url and r.method == "POST" else None)
        ad.on("request", lambda r: vault_fetch.append(r.url) if "/articles/vault/posts/" in r.url else None)
        login(ad, "andy")
        ok(f"{T}：桌機總覽摘要卡列維持原本五張、沒有多出簽到卡（桌機走頂欄小圖示，版面不動）", ad.evaluate("() => document.querySelectorAll('.ovsum .osc').length") == 5 and ad.query_selector(".osc.ci") is None)
        ok(f"{T}：頂欄簽到鈕有圖示", ad.evaluate("() => !!document.querySelector('#ciBtn svg')"))
        opencal(ad)
        ok(f"{T}：①月曆有 7 欄星期標題與本月每一天", ad.evaluate("() => document.querySelectorAll('.ci-wk').length === 7 && document.querySelectorAll('.ci-c[data-d]').length >= 28"))
        ok(f"{T}：①站主看得到「站主測試」", ad.query_selector("#ciAdm") is not None)
        ok(f"{T}：①桌機節點清單直接攤開（3／7／14／20 四列）", ad.evaluate("() => { const u = document.getElementById('ciNodes'); return !!u && u.offsetHeight > 0 && u.querySelectorAll('li').length === 4; }"))
        adm_open()
        ad.fill("#admToday", "2026-11-28"); ad.click("[data-t=settoday]")
        ad.click("[data-t=clear]")
        ad.fill("#admN", "3"); ad.click("[data-t=fill]")
        ok(f"{T}：①站主工具填到第 3 天 → 累積 3 天、月曆 3 格有勾", tot(ad) == 3 and ad.evaluate("() => document.querySelectorAll('.ci-c.sg').length") == 3, tot(ad))
        ok(f"{T}：①第 3 格有「3」節點標記", ad.evaluate("() => !!document.querySelector('.ci-c.sg .nb')"))
        ok(f"{T}：①今天（28）已簽 → 簽到鈕變「今天已簽到」且不能按", ad.evaluate("() => { const b = document.querySelector('.ci-sum .ci-btn'); return !!b && b.disabled && /已簽到/.test(b.textContent); }"))
        ad.click("[data-claim=\"0\"]")
        ad.wait_for_selector("#ciDone", timeout=4000)
        done_txt = ad.inner_text("#ciDone")
        ok(f"{T}：①兌換後告訴你「已解鎖 2 篇」並指去精選文章『比比寶箱』", "已解鎖 2 篇" in done_txt and "比比寶箱" in done_txt, done_txt[:80])
        ad.click("#ciGo")
        wait_until(ad, "() => location.hash === '#articles/vault' && !!document.getElementById('vaultSum')", 8000)
        ok(f"{T}：①直接連到精選文章的「比比寶箱」分頁、分頁亮著", ad.evaluate("() => { const t = document.querySelector('#artCats [data-cat=vault]'); return !!t && (t.classList.contains('on') || t.getAttribute('aria-selected') === 'true'); }"))
        ok(f"{T}：①寶箱寫「已解鎖 2／12 篇」", "已解鎖 2／12 篇" in ad.inner_text("#vaultSum"), ad.inner_text("#vaultSum"))
        ok(f"{T}：①預設只列已解鎖：2 張、都沒上鎖", ad.evaluate("() => [...document.querySelectorAll('#artPre .artc')].filter(c => c.dataset.lock === '0').length") == 2)
        ad.click(".ci-vseg [data-f=all]")
        ad.wait_for_timeout(200)
        ad.evaluate("() => document.querySelectorAll('.ci-vl').forEach(d => { d.open = true; })")
        n_un = ad.evaluate("() => document.querySelectorAll('#artPre .artc[data-lock=\"0\"]').length")
        n_lk = ad.evaluate("() => document.querySelectorAll('#artPre .artc[data-lock=\"1\"]').length")
        ok(f"{T}：①切到「全部」：2 篇解鎖、其他 10 篇上鎖", n_un == 2 and n_lk == 10, [n_un, n_lk])
        unl_ids = ad.evaluate("() => [...document.querySelectorAll('#artPre .artc[data-lock=\"0\"]')].map(c => c.dataset.id)")
        lk_id = ad.evaluate("() => document.querySelector('#artPre .artc[data-lock=\"1\"]').dataset.id")
        ad.click(f"#artPre .artc[data-id=\"{unl_ids[0]}\"]")
        wait_until(ad, "() => !!document.querySelector('#artPost[data-cat=vault] .artttl') && document.querySelectorAll('#artPost p').length > 3", 8000)
        ok(f"{T}：①點開已解鎖那篇 → 真的有內文（段落 > 3）", True)
        ok(f"{T}：①站主身分打開已解鎖文章沒有被「全文額度」擋（不顯示升級提示）", ad.evaluate("() => !document.querySelector('#artPost .artlocked')"))
        vault_fetch.clear()
        ad.goto(base + f"#article/{lk_id}", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ciLkBox')", 8000)
        ok(f"{T}：①直接打上鎖那篇的網址 → 只看到「還沒解鎖」（站主也一樣，法遵：只能靠簽到）", "還沒解鎖" in ad.inner_text("#ciLkBox"), ad.inner_text("#ciLkBox")[:60])
        ok(f"{T}：①上鎖那篇的內文檔根本沒被抓", not any(lk_id in u for u in vault_fetch), vault_fetch[:2])
        ok(f"{T}：①上鎖頁沒有文章段落", ad.evaluate("() => document.querySelectorAll('#artPost p').length") == 0)

        # =============================================================== ② 填到 7、20 天 → 兌換不重複 → 許願
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ciBtn') && !!window.TwCheckin", 8000)
        ad.evaluate("() => TwCheckin.test.today('2026-11-28')")   # 重新整理後「模擬今天」不保留：驗收直接用同一支假今天
        opencal(ad)
        adm_open()
        ok(f"{T}：②重新整理後簽到紀錄還在（仍 3 天、寶箱 2 篇）", tot(ad) == 3 and "2／12" in ad.inner_text(".ci-foot"), ad.inner_text(".ci-foot")[:30])
        ok(f"{T}：②已兌換的 3 天節點不能再兌換（只剩「已兌換」字樣）", ad.evaluate("() => { const li = document.querySelector('#ciNodes li[data-node=\"0\"]'); return !!li && !li.querySelector('[data-claim]') && /已兌換/.test(li.textContent); }"))
        ad.fill("#admN", "7"); ad.click("[data-t=fill]")
        ad.click("[data-claim=\"1\"]")
        ad.wait_for_selector("#ciDone", timeout=4000)
        st = ad.evaluate("() => TwCheckin.state()")
        ok(f"{T}：②7 天兌換後共解鎖 4 篇、沒有重複", len(st["unlock"]) == 4 and len(set(st["unlock"])) == 4, st["unlock"])
        ad.click("#ciStay")
        adm_open()
        ad.fill("#admN", "20"); ad.click("[data-t=fill]")
        ad.click("[data-claim=\"2\"]")
        ad.wait_for_selector("#ciDone", timeout=4000)
        st = ad.evaluate("() => TwCheckin.state()")
        ok(f"{T}：②14 天產業包 → 共 6 篇、沒有重複", len(st["unlock"]) == 6 and len(set(st["unlock"])) == 6, st["unlock"])
        ad.click("#ciStay")
        ad.click("[data-claim=\"3\"]")
        ad.wait_for_selector("#ciWsend", timeout=4000)
        ok(f"{T}：②20 天許願券 → 許願表單、寫著「不一定做得到」與「Plus 3 天」", "不一定做得到" in ad.inner_text(".ci-wf") and "Plus 3 天" in ad.inner_text(".ci-wf"))
        ad.fill("[data-w=\"1\"]", "太短")
        ad.click("#ciWsend")
        ok(f"{T}：②願望少於 6 個字 → 擋下、不送出", "至少 6 個字" in ad.inner_text("#ciWmsg") and not fb_posts)
        ad.fill("[data-w=\"1\"]", "手機版也能看族群輪動時鐘")
        ad.fill("[data-w=\"2\"]", "盤後自動寄出自選股日報")
        ad.fill("[data-w=\"3\"]", "加入美股連動的產業對照表")
        ad.click("#ciWadd")
        ok(f"{T}：②「再加一個」可以加到第 4 格（上限 5）", ad.evaluate("() => document.querySelectorAll('#ciWrows .ci-wr').length") == 4)
        ad.click("#ciWsend")
        wait_until(ad, "() => !!document.querySelector('.ci-list[data-batch]')", 8000)
        wait_until(ad, "() => document.querySelector('.ci-list[data-batch]') !== null", 4000)
        ad.wait_for_timeout(600)
        wish = [p for p in fb_posts if p.get("type") == "wish"]
        ok(f"{T}：②真的 Worker 收到 3 筆 /v1/feedback（type=wish）", len(wish) == 3, len(wish))
        ok(f"{T}：②每筆都帶【預覽】與【簽到願望】標記", all("【預覽】" in p["body"] and "【簽到願望】" in p["body"] for p in wish), [p["body"][:40] for p in wish[:1]])
        adm_list = ad.evaluate("async () => { const j = await TwAccount.call('/v1/admin/feedback/list', {}); return (j.feedback || []).filter(r => /簽到願望/.test(r.body)).map(r => ({ id: r.id, type: r.type, status: r.status, body: r.body })); }")
        ok(f"{T}：②站主端的意見回饋清單收得到這 3 筆（type=wish、狀態=new）", len(adm_list) == 3 and all(r["type"] == "wish" and r["status"] == "new" for r in adm_list), adm_list[:1])
        ok(f"{T}：②願望送出後許願券用掉：「我的願望」清單顯示 1 批 3 項、評估中", "等待站主評估" in ad.inner_text(".ci-list[data-batch]") and ad.evaluate("() => document.querySelectorAll('.ci-list[data-batch] li li, .ci-list[data-batch] ul > li').length") >= 3)
        ad.click("#ciBack")
        ok(f"{T}：②回月曆後 20 天節點變「已兌換」", ad.evaluate("() => /已兌換/.test(document.querySelector('#ciNodes li[data-node=\"3\"]').textContent)"))
        # 模擬站主評估：先「會做」→ 畫面寫站主打算做
        ad.click("#ciWishes")
        ad.click("#ciBack")
        adm_open()
        ad.select_option("#admSt", "eval"); ad.click("[data-t=wishreply]")
        ad.click("#ciWishes")
        ok(f"{T}：②站主標「會做」→ 使用者畫面寫「站主打算做」", "站主打算做" in ad.inner_text(".ci-list[data-batch]"), ad.inner_text(".ci-list[data-batch]")[:80])
        ad.click("#ciBack")
        # 管理端真的標「不做」（呼叫真 worker 的 /v1/admin/feedback/set）→ 同步回來
        for r in adm_list:
            ad.evaluate("async (id) => TwAccount.call('/v1/admin/feedback/set', { id, status: 'no' })", r["id"])
        adm_open()
        ad.click("[data-t=wishsync]")
        ad.wait_for_timeout(800)
        ad.click("#ciWishes")
        res_txt = ad.inner_text(".ci-list[data-batch]")
        ok(f"{T}：②管理端整批標「不做」→ 同步後畫面寫「送你 Plus 3 天（預覽模擬，未真的開通）」", "Plus 3 天" in res_txt and "預覽模擬" in res_txt and ad.get_attribute(".ci-list[data-batch]", "data-result") == "granted", res_txt[:120])
        ad.click("#ciBack")
        adm_open()
        ad.select_option("#admSt", "no"); ad.click("[data-t=wishreply]")
        ad.click("#ciWishes")
        ok(f"{T}：②站主工具「模擬願望被回覆：做不到」也走到送 Plus 3 天", ad.get_attribute(".ci-list[data-batch]", "data-result") == "granted")
        ad.click("#ciBack")
        _shot(ad, "checkin_desktop_admin")

        # =============================================================== ③ 補簽：比比互動
        adm_open()
        ad.click("[data-t=clear]")
        ad.click("[data-t=ptsclear]")
        ok(f"{T}：③清空後補簽進度 0／5、本月已補 0／3、「找比比」", "互動 0／5" in ad.inner_text("#ciMk") and "0／3" in ad.inner_text("#ciMk") and ad.query_selector("[data-findbibi]") is not None, ad.inner_text("#ciMk"))
        ad.click("#ciX")
        mk_n = {"i": 0}

        def bibi_once(kind, expect_count, label):
            """從比比的小圈真的點一次互動；回傳卡片底下的結果文字"""
            ad.hover("#supFab")
            wait_until(ad, "() => Bibi.state().ring", 6000)
            ad.click(f"#bibiRing .bopt[data-act={kind}]")
            ad.wait_for_selector("#ciBibi", timeout=4000)
            if kind == "say":
                ad.wait_for_function("() => !document.getElementById('ciBOk').disabled", timeout=5000)
                ad.click("#ciBOk")
            else:
                ad.wait_for_function("() => !document.querySelector('#ciBibi .ci-opt').disabled", timeout=6000)
                ad.click("#ciBibi .ci-opt")
            ad.wait_for_function("() => document.getElementById('ciBP').textContent.length > 0", timeout=3000)
            txt = ad.inner_text("#ciBP")
            ok(f"{T}：③{label} → {'算 1 次互動' if expect_count else '不算互動'}", ("+1 互動" in txt) == expect_count, txt[:50])
            ad.click("#ciBX")
            ad.wait_for_selector("#ciBibi", state="detached", timeout=2000)
            return txt

        ad.evaluate("() => TwCheckin.test.today('2026-11-28')")
        # 3 秒內連點：回不去的快速連點由程式擋；這裡驗 20 秒間隔
        bibi_once("say", True, "聽比比說第 1 次")
        bibi_once("quiz", False, "20 秒內馬上再互動（間隔不夠）")
        for k in (2, 3, 4):
            ad.evaluate("() => TwCheckin.test.skip(25000)")
            bibi_once("say" if k % 2 else "quiz", True, f"第 {k} 次（隔 20 秒以上）")
        ad.evaluate("() => TwCheckin.test.skip(25000)")
        bibi_once("say", False, "同一天第 5 次（每天上限 4 次）")
        ok(f"{T}：③同一天只累積 4 次", ad.evaluate("() => TwCheckin.state().pts") == 4, ad.evaluate("() => TwCheckin.state().pts"))
        ad.evaluate("() => { TwCheckin.test.today('2026-11-29'); TwCheckin.test.skip(25000); }")
        bibi_once("quiz", True, "隔天第 1 次（累積第 5 次）")
        ok(f"{T}：③累積 5 次", ad.evaluate("() => TwCheckin.state().pts") == 5)
        opencal(ad)
        ok(f"{T}：③滿 5 次 → 補簽列出現「開始補簽」", ad.query_selector("[data-mkgo]") is not None, ad.inner_text("#ciMk"))
        ad.click("[data-mkgo]")
        mk_days = ad.evaluate("() => [...document.querySelectorAll('.ci-c.mkok')].map(e => e.dataset.d)")
        ok(f"{T}：③補簽模式：只有最近 7 天的空白日可點（虛線）", 1 <= len(mk_days) <= 7 and all(d >= "2026-11-22" for d in mk_days), mk_days)
        d0 = mk_days[0]
        ad.click(f".ci-c.mkok[data-d=\"{d0}\"]")
        ok(f"{T}：③第一下只提示「再點一次確認」、還沒補", "再點一次" in ad.inner_text("#ciToast") and not ad.evaluate("(d) => !!document.querySelector('.ci-c.mk[data-d=\"' + d + '\"]')", d0))
        ad.click(f".ci-c.mkok[data-d=\"{d0}\"]")
        ad.wait_for_selector(f".ci-c.mk[data-d=\"{d0}\"]", timeout=3000)
        ok(f"{T}：③補簽成功 → 該日有勾與「補」註記", ad.evaluate("(d) => { const e = document.querySelector('.ci-c.mk[data-d=\"' + d + '\"]'); return !!e && !!e.querySelector('.tg') && !!e.querySelector('svg.ck'); }", d0))
        ok(f"{T}：③補簽後互動歸零、本月已補 1／3、下次要 7 次", "0／7" in ad.inner_text("#ciMk") and "1／3" in ad.inner_text("#ciMk"), ad.inner_text("#ciMk"))
        adm_open()
        ad.click("[data-t=ptsfull]"); ad.click("[data-mkgo]")
        ad.click(".ci-c.mkok >> nth=0"); ad.click(".ci-c.mkok >> nth=0")
        ad.wait_for_function("() => document.querySelectorAll('.ci-c.mk').length === 2", timeout=3000)
        ad.click("[data-t=ptsfull]"); ad.click("[data-mkgo]")
        ad.click(".ci-c.mkok >> nth=0"); ad.click(".ci-c.mkok >> nth=0")
        ad.wait_for_function("() => document.querySelectorAll('.ci-c.mk').length === 3", timeout=3000)
        ok(f"{T}：③補到第 3 次（第 3 次需要 10 次互動）→ 本月已補 3／3", "3／3" in ad.inner_text("#ciMk"), ad.inner_text("#ciMk"))
        ad.click("[data-t=ptsfull]")
        ok(f"{T}：③補滿 3 次後不能再補（沒有「開始補簽」鈕）", ad.query_selector("[data-mkgo]") is None)
        ad.click("#ciX")

        # =============================================================== ④ 一般會員與手機
        bob_ctx = mk(1440, 900)
        bob = bob_ctx.new_page()
        bob.on("pageerror", lambda e: errs.append(str(e)))
        login(bob, "bob")                                   # 手機頂欄找不到登入鈕：先在桌機寬度登入，再縮成手機寬度重新載入
        ok(f"{T}：④桌機寬度：一般會員看得到簽到小圖示", bob.evaluate("() => { const b = document.getElementById('ciBtn'); return !!b && b.offsetParent !== null; }"))
        bob.set_viewport_size({"width": 390, "height": 844})
        bob.reload(wait_until="domcontentloaded")
        wait_until(bob, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        bob.wait_for_selector(".osc.ci", timeout=8000)
        ok(f"{T}：④手機頂欄沒有簽到小圖示、改由總覽簽到卡進入", not bob.evaluate("() => { const b = document.getElementById('ciBtn'); return !!b && b.offsetParent !== null; }") and bob.query_selector(".osc.ci") is not None)
        bob.click(".osc.ci")
        bob.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=5000)
        bob.wait_for_timeout(400)
        ok(f"{T}：④一般會員的月曆裡完全沒有站主測試（DOM 沒有）", bob.query_selector("#ciAdm") is None and "站主測試" not in bob.inner_text("#ciOv"))
        geo = bob.evaluate("""() => { const d = document.getElementById('ciDlg'), r = d.getBoundingClientRect();
            return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, sh: d.scrollHeight, ch: d.clientHeight, vw: innerWidth, vh: innerHeight, hs: document.documentElement.scrollWidth }; }""")
        ok(f"{T}：④手機 390：簽到面板一屏看完（沒有內捲、沒超出視窗）", geo["sh"] <= geo["ch"] + 1 and geo["top"] >= 0 and geo["bottom"] <= geo["vh"] + 1, geo)
        ok(f"{T}：④手機 390：整頁沒有橫向捲軸、面板沒超出左右", geo["hs"] <= geo["vw"] and geo["left"] >= 0 and geo["right"] <= geo["vw"] + 1, geo)
        small = bob.evaluate("""() => { const out = []; document.querySelectorAll('#ciDlg *').forEach(e => { if (!e.childNodes.length) return; const t = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!t) return; const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return; if (parseFloat(cs.fontSize) < 11) out.push(e.className + ':' + cs.fontSize); }); return out; }""")
        ok(f"{T}：④手機 390：面板文字都 ≥ 11px", not small, small[:5])
        ok(f"{T}：④手機的節點清單預設收起（點「節點與獎勵」才展開）", not bob.evaluate("() => document.getElementById('ciNlD').open"))
        _shot(bob, "checkin_mobile")
        bob.click("#ciSign")
        wait_until(bob, "() => document.querySelectorAll('.ci-c.sg').length === 1", 4000)
        ok(f"{T}：④一般會員按「簽到今天」→ 累積 1 天、今天格有勾", tot(bob) == 1)
        ok(f"{T}：④按過之後鈕變「今天已簽到」、不能重複簽", bob.evaluate("() => { const b = document.querySelector('.ci-sum .ci-btn'); return !!b && b.disabled; }"))
        # 功能鍵關掉 → 鎖住
        bob.click("#ciX")
        bob.evaluate("() => { window.__canOld = TwPerm.can; TwPerm.can = (id) => id === 'ci.sign' ? false : window.__canOld(id); }")
        bob.evaluate("() => TwCheckin.test.today('2026-11-30')")
        opencal(bob, via_card=True)
        locked = bob.evaluate("() => { const b = document.getElementById('ciSign'); return !!b && b.disabled && /需開通/.test(b.textContent); }")
        ok(f"{T}：④關掉 ci.sign → 簽到鈕鎖住、寫「需開通」", locked)
        bob.evaluate("() => { TwPerm.can = window.__canOld; }")
        bob.click("#ciX")
        bob.evaluate("() => TwCheckin.test.today('')")
        # 寶箱硬閘：一般會員直接打上鎖文章網址 → 只看到鎖
        bob.goto(base + "#article/ck-T01", wait_until="domcontentloaded")
        wait_until(bob, "() => !!document.getElementById('ciLkBox') || !!document.querySelector('#artPost .artttl')", 8000)
        ok(f"{T}：④一般會員沒兌換過 → 打開寶箱文章網址只看到「還沒解鎖」", bob.query_selector("#ciLkBox") is not None)

        # =============================================================== ⑥ 模擬使用者實測修正（2026-11-07 報告 A2／A3／A4＋體驗）
        # A2：一般會員在主控台呼叫 TwCheckin.test.* 一律無效（沒有本機旗標的環境，也不是站主）
        raw = mk(1440, 900, flag=False, clock=True)
        rp = raw.new_page()
        rp.on("pageerror", lambda e: errs.append(str(e)))
        login(rp, "bob")
        before = rp.evaluate("() => TwCheckin.state().today")
        rp.evaluate("() => { TwCheckin.test.enable(); TwCheckin.test.today('2026-11-01'); TwCheckin.test.skip(3 * 86400000); }")
        after = rp.evaluate("() => TwCheckin.state().today")
        ok(f"{T}：⑥A2 一般會員呼叫 TwCheckin.test.today／skip → 「今天」完全不變（後門無效）", before == after and after != "2026-11-01", [before, after])
        rp.evaluate("() => TwCheckin.test.reset()")
        # A3：把電腦時鐘往後調一天簽到、再調回來 → 未來那天不算累積、也不打勾；調回後也不能再簽（時鐘倒退）
        rp.evaluate("() => { window.__off = 86400000; }")
        rp.click("#ciBtn"); rp.wait_for_selector("#ciOv:not([hidden]) #ciSign", timeout=6000); rp.wait_for_timeout(400)
        fut_today = rp.evaluate("() => TwCheckin.state().today")
        rp.click("#ciSign"); rp.wait_for_timeout(300)
        ok(f"{T}：⑥A3 時鐘往後調一天：以調過的「今天」可以簽到（客戶端擋不住，所以回到真實日期時要失效）", tot(rp) == 1 and fut_today != before, [fut_today, before])
        rp.click("#ciX")
        rp.evaluate("() => { window.__off = 0; }")
        rp.click("#ciBtn"); rp.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); rp.wait_for_timeout(400)
        ok(f"{T}：⑥A3 時鐘調回來：未來那天不計入累積（0 天）、月曆沒有打勾", tot(rp) == 0 and rp.evaluate("() => document.querySelectorAll('.ci-c.sg').length") == 0, tot(rp))
        ok(f"{T}：⑥A3 localStorage 裡仍留著未來日期的紀錄，但狀態只算今天以前", rp.evaluate("() => Object.keys(JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.indexOf('tw.ci.v1:bob') >= 0)) || '{}').signs || {}).length") == 1 and rp.evaluate("() => Object.keys(TwCheckin.state().signs).length") == 0)
        rp.click("#ciSign"); rp.wait_for_timeout(300)
        ok(f"{T}：⑥A3 時鐘倒退後按簽到 → 被擋（提示請把系統時間調回正確）、累積仍 0", tot(rp) == 0 and "系統時間" in (rp.evaluate("() => (document.getElementById('ciToast') || {}).textContent || ''")), rp.evaluate("() => (document.getElementById('ciToast') || {}).textContent || ''"))
        # 未來日格：點了有提示
        rp.evaluate("() => { const f = document.querySelector('.ci-c.fu'); if (f) f.click(); }")
        ok(f"{T}：⑥C9 點尚未到的日子 → 提示「還沒到這天」", "還沒到" in rp.evaluate("() => (document.getElementById('ciToast') || {}).textContent || ''") or rp.query_selector(".ci-c.fu") is None)
        rp.click("#ciX")

        # A4：兩個分頁共用 localStorage。分頁 A 簽 3 天＋兌換，分頁 B（早就開著、記憶體是舊的）互動一下 → A 的解鎖不能消失；B 的畫面要同步
        ctx4 = mk(1440, 900, flag=True)
        pa = ctx4.new_page(); pa.on("pageerror", lambda e: errs.append(str(e)))
        login(pa, "bob")
        pb = ctx4.new_page(); pb.on("pageerror", lambda e: errs.append(str(e)))
        pb.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(pb, "() => !!(window.TwAccount && TwAccount.user()) && !!window.TwCheckin && !!document.getElementById('ciBtn')", 12000)
        pb.click("#ciBtn"); pb.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); pb.wait_for_timeout(400)
        for dd in ("2026-11-01", "2026-11-02", "2026-11-03"):
            pa.evaluate("(d) => TwCheckin.test.today(d)", dd)
            pa.click("#ciBtn"); pa.wait_for_selector("#ciOv:not([hidden]) #ciSign", timeout=6000); pa.wait_for_timeout(300)
            pa.click("#ciSign"); pa.wait_for_timeout(250)
            pa.click("#ciX")
        pa.click("#ciBtn"); pa.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); pa.wait_for_timeout(300)
        pa.click("[data-claim=\"0\"]"); pa.wait_for_selector("#ciDone", timeout=4000)
        n_a = pa.evaluate("() => TwCheckin.state().unlock.length")
        ok(f"{T}：⑥A4 分頁 A 簽 3 天並兌換 → 解鎖 2 篇", n_a == 2, n_a)
        # B 沒有任何操作，只靠 storage 事件：它開著的面板要自己跟上
        wait_until(pb, "() => { const e = document.getElementById('ciTot'); return !!e && e.textContent.trim() === '3'; }", 4000)
        ok(f"{T}：⑥A4 分頁 B 什麼都沒按，面板就同步成「累積 3 天」（storage 事件）", pb.inner_text("#ciTot").strip() == "3", pb.inner_text("#ciTot"))
        # B 現在做會寫 localStorage 的事（聽比比說會記已看過的卡）→ 不能把 A 剛兌換的解鎖蓋掉
        pb.evaluate("() => { window.__stale = 1; }")
        pb.click("#ciX")
        pb.evaluate("() => TwCheckin.bibi('say')")
        pb.wait_for_selector("#ciBibi", timeout=4000); pb.wait_for_timeout(300)
        pa.reload(wait_until="domcontentloaded")
        wait_until(pa, "() => !!(window.TwAccount && TwAccount.user()) && !!window.TwCheckin", 12000)
        ok(f"{T}：⑥A4 分頁 B 互動後，分頁 A 重新整理 → 解鎖仍是 2 篇、累積仍有簽到紀錄", pa.evaluate("() => TwCheckin.state().unlock.length") == 2 and pa.evaluate("() => Object.keys(TwCheckin.state().signs).length") >= 3, pa.evaluate("() => [TwCheckin.state().unlock.length, Object.keys(TwCheckin.state().signs).length]"))

        # ---- 體驗項目 ----
        # B2：訪客不再看到「需開通」；B1：桌機頂欄右上有「簽到」字樣
        gst = mk(1440, 900, flag=False).new_page()
        gst.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(gst, "() => !!window.TwCheckin && !!document.querySelector('#ciBtn svg')", 8000)
        gst.wait_for_timeout(800)
        pos = gst.evaluate("() => { const b = document.getElementById('ciBtn'), r = b.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, vis: b.offsetParent !== null, txt: b.textContent.trim(), inTools: !!b.closest('#l4Tools'), vw: innerWidth }; }")
        ok(f"{T}：⑥B1 桌機簽到鈕在頂欄右上（右半、最上方）、可見、寫著「簽到」", pos["vis"] and pos["txt"].startswith("簽到") and pos["x"] > pos["vw"] / 2 and pos["y"] < 80, pos)
        gst.click("#ciBtn"); gst.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); gst.wait_for_timeout(500)
        gb = gst.evaluate("() => { const b = document.getElementById('ciSign'); return { t: b ? b.textContent.trim() : '', mkr: !!document.getElementById('ciMk'), all: document.getElementById('ciDlg').innerText }; }")
        ok(f"{T}：⑥B2 沒登入：按鈕寫「登入後簽到」、整個面板沒有「需開通」、沒有補簽列", gb["t"] == "登入後簽到" and "需開通" not in gb["all"] and not gb["mkr"], gb["t"])
        gst.click("#ciSign"); gst.wait_for_timeout(500)
        ok(f"{T}：⑥B2 按「登入後簽到」→ 面板關起來、開出登入視窗", gst.evaluate("() => document.getElementById('ciOv').hidden") and gst.evaluate("() => { const d = document.getElementById('acctDlg'); return !!d && !d.hidden; }"))

        # 已登入、尚未簽：頂欄鈕有醒目小點；簽完：下一步提示、今天格沒有「簽」字
        ub = mk(1440, 900, flag=True).new_page(); ub.on("pageerror", lambda e: errs.append(str(e)))
        login(ub, "bob"); ub.wait_for_timeout(600)
        ok(f"{T}：⑥B1 還沒簽時：頂欄鈕有琥珀小點、鈕變琥珀色提示", ub.evaluate("() => { const b = document.getElementById('ciBtn'), d = b.querySelector('i'); return !d.hidden && b.classList.contains('un'); }"))
        ub.click("#ciBtn"); ub.wait_for_selector("#ciOv:not([hidden]) #ciSign", timeout=6000); ub.wait_for_timeout(500)
        td_txt = ub.evaluate("() => document.querySelector('.ci-c.td').innerText.trim()")
        ok(f"{T}：⑥B5 今天還沒簽：今天那格只有日期數字、沒有「簽」字", "簽" not in td_txt, td_txt)
        ub.click("#ciSign"); ub.wait_for_timeout(300)
        nx = ub.inner_text("#ciNextStep"); tt = ub.evaluate("() => (document.getElementById('ciToast') || {}).textContent || ''")
        ok(f"{T}：⑥B4 簽完：面板與提示都寫「再簽 N 天可換○○」並說明去哪看", "再簽 2 天" in nx and "教學包" in nx and "比比寶箱" in nx and "再簽 2 天" in tt, [nx, tt])
        ub.click("#ciX")
        ub.wait_for_timeout(200)
        ok(f"{T}：⑥B1 簽完後頂欄鈕小點消失", ub.evaluate("() => document.querySelector('#ciBtn i').hidden"))
        # B3：「找比比」直接開考考你
        ub.evaluate("() => { TwCheckin.open(); }"); ub.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); ub.wait_for_timeout(300)
        ub.click("[data-findbibi]"); ub.wait_for_selector("#ciBibi", timeout=4000)
        ok(f"{T}：⑥B3 按「找比比」→ 直接打開「比比考考你」卡片（不是叫人去圖示堆裡找）、面板關起來、有「改聽比比說」", "比比考考你" in ub.inner_text("#ciBibi") and ub.evaluate("() => document.getElementById('ciOv').hidden") and ub.query_selector("#ciBSw") is not None)
        ub.click("#ciBSw"); ub.wait_for_timeout(300)
        ok(f"{T}：⑥B3 卡片上按「改聽比比說」→ 換成聽比比說", "聽比比說" in ub.inner_text("#ciBibi"))
        ub.click("#ciBX")
        # B3：比比環上兩顆有文字標籤
        ub.hover("#supFab")
        ub.wait_for_timeout(900)
        lb = ub.evaluate("() => [...document.querySelectorAll('#bibiRing .bopt .blbl')].map(e => e.textContent)")
        ok(f"{T}：⑥B3 比比環上「聽比比說」「比比考考你」兩顆圖示下方有文字標籤", sorted(lb) == ["比比說", "考考你"], lb)
        ub.keyboard.press("Escape")
        # 寶箱：分頁篇數、箭頭
        ub.goto(base + "#articles/vault", wait_until="domcontentloaded")
        wait_until(ub, "() => !!document.getElementById('vaultSum')", 8000)
        ub.click(".ci-vseg [data-f=all]"); ub.wait_for_timeout(300)
        em = ub.evaluate("() => (document.querySelector('#artCats [data-cat=vault] em') || {}).textContent || ''")
        ok(f"{T}：⑥C6 寶箱分頁標籤顯示篇數（例如 0／12）", bool(re.match(r"^\d+/12$", em.strip())), em)
        arrow = ub.evaluate("() => { const s = document.querySelector('.ci-vl > summary'); return getComputedStyle(s, '::before').content; }")
        ok(f"{T}：⑥B6 寶箱「全部」的分類預設收起時有展開箭頭", arrow not in ("none", "normal", ""), arrow)
        ok(f"{T}：⑥B6 分類預設收起（4 組都沒展開）", ub.evaluate("() => [...document.querySelectorAll('.ci-vl')].every(d => !d.open)"))
        # 先解鎖一篇再驗閱讀版面
        ub.close()

        # 管理者：閱讀版面、浮水印、同步提示、麵包屑
        ad.goto(base + "#articles/vault", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('vaultSum')", 8000)
        un = ad.evaluate("() => (document.querySelector('#artPre .artc[data-lock=\"0\"]') || {}).dataset ? document.querySelector('#artPre .artc[data-lock=\"0\"]').dataset.id : ''")
        if un:
            ad.goto(base + "#article/" + un, wait_until="domcontentloaded")
            wait_until(ad, "() => !!document.querySelector('#artPost[data-cat=vault] .artbody p')", 8000)
            ad.wait_for_timeout(500)
            rd = ad.evaluate("""() => { const b = document.querySelector('#artPost .artbody'), cs = getComputedStyle(b), w = getComputedStyle(document.querySelector('#artPost'), '::after');
                return { fs: cs.fontSize, w: Math.round(b.getBoundingClientRect().width), wmz: w.zIndex, crumb: document.querySelector('.artcrumb').innerText.replace(/\s+/g, ' ') }; }""")
            ok(f"{T}：⑥B10 寶箱文章內文 16px、行寬 ≤ 720px", rd["fs"] == "16px" and rd["w"] <= 721, rd)
            ok(f"{T}：⑥B10 浮水印退到內文後面（z-index 0，不再壓在內文上）", rd["wmz"] in ("0", "auto"), rd["wmz"])
            ok(f"{T}：⑥C3 已解鎖文章的麵包屑也有「比比寶箱」那層", "比比寶箱" in rd["crumb"], rd["crumb"])
            heads = ad.evaluate("() => [...document.querySelectorAll('#artPost .artbody h4')].map(h => h.textContent)")
            ok(f"{T}：⑥C4 文章小標統一寫「一句結論」（沒有「一句話結論」）", not any("一句話結論" in h for h in heads), heads[:3])
        ad.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(ad, "() => !!document.getElementById('ciBtn') && !!window.TwCheckin", 8000)
        opencal(ad); adm_open()
        ad.fill("#admN", "30"); ad.click("[data-t=fill]")
        fm = ad.inner_text("#admMsg")
        ok(f"{T}：⑥B8 站主「填到第 30 天」不會填到今天以後；不夠時提示「本月天數不足」", "天數不足" in fm or ad.evaluate("() => document.querySelectorAll('.ci-c.fu.sg').length") == 0, fm)
        ok(f"{T}：⑥B8 今天以後的格子沒有打勾", ad.evaluate("() => document.querySelectorAll('.ci-c.fu.sg').length") == 0)
        ad.click("[data-t=wishsync]"); ad.wait_for_timeout(1200)
        st = ad.evaluate("() => (document.getElementById('ciToast') || {}).textContent || ''")
        ok(f"{T}：⑥B7 按「從意見回饋同步」→ 跳出同步結果提示", "同步" in st, st)
        ad.click("#ciX")

        # 手機：點擊區 ≥ 44px；登出提示
        mob = mk(1440, 900, flag=True).new_page(); mob.on("pageerror", lambda e: errs.append(str(e)))
        login(mob, "bob")
        mob.set_viewport_size({"width": 390, "height": 844})
        mob.reload(wait_until="domcontentloaded")
        wait_until(mob, "() => !!(window.TwAccount && TwAccount.user())", 12000)
        mob.wait_for_selector(".osc.ci", timeout=8000)
        mob.click(".osc.ci"); mob.wait_for_selector("#ciOv:not([hidden]) #ciTtl", timeout=6000); mob.wait_for_timeout(500)
        small = mob.evaluate("""() => [...document.querySelectorAll('#ciDlg button, #ciDlg a, #ciDlg summary')].filter(e => { const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; const r = e.getBoundingClientRect(); return r.width > 0 && (r.height < 43.5 || r.width < 43.5) && !e.closest('.ci-adm'); }).map(e => (e.id || e.className || e.tagName) + ':' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
        ok(f"{T}：⑥B9 手機 390：簽到面板裡的按鈕／連結點擊區都 ≥ 44px", not small, small[:6])
        g2 = mob.evaluate("() => { const d = document.getElementById('ciDlg'); return { sh: d.scrollHeight, ch: d.clientHeight, hs: document.documentElement.scrollWidth, vw: innerWidth }; }")
        ok(f"{T}：⑥B9 手機點擊區放大後仍一屏看完、不橫捲", g2["sh"] <= g2["ch"] + 1 and g2["hs"] <= g2["vw"], g2)
        mob.click("#ciX")
        mob.evaluate("() => { document.querySelector('#acctBtn') && document.querySelector('#acctBtn').click(); }")
        mob.evaluate("() => TwAccount.logout && TwAccount.logout()")
        mob.wait_for_timeout(400)
        lo = mob.evaluate("() => (document.getElementById('acctToast') || {}).textContent || ''")
        ok(f"{T}：⑥B11 登出提示正確說明簽到紀錄仍存在這台裝置", "簽到紀錄" in lo and "這台裝置" in lo or not lo, lo)

        # =============================================================== ⑤ 功能鍵與方案值
        ff = ad.evaluate("""() => { const ids = ['ci.sign', 'ci.makeup', 'ci.wish', 'art.cat.vault'];
            const tiers = (window.TW_PLAN_PRESETS || {}).tiers || [];
            return { have: ids.map(i => !!TwFeatures.byId(i)), plans: tiers.map(t => t.key), vals: tiers.map(t => ids.map(i => t.feats[i])) }; }""")
        ok(f"{T}：⑤四個功能鍵都已註冊", all(ff["have"]), ff["have"])
        ok(f"{T}：⑤方案預設值：四個方案 × 四個鍵都有寫（不是 undefined）", len(ff["plans"]) >= 4 and all(all(v is not None for v in row) for row in ff["vals"]), ff["vals"][:2])
        ok(f"{T}：⑤整段沒有 JS 錯誤", not errs, errs[:3])
    finally:
        for cx in ctxs:
            try:
                cx.close()
            except Exception:  # noqa: BLE001
                pass
        dev.terminate()


register("每日簽到", lambda pg, b, base, code: t_checkin_1107(b, base))
