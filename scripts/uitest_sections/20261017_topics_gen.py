# 驗收段落「新增主題1017」—— 2026-10-17
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_free_port()、ROOT…直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 新增主題1017（site/articles.js paintTopics／tgBind、workers/account-api/articles.js kind:'topics'）
# Andy 10-17（看著管理區「精選文章 → 主題候選清單」）：
#   「幫我每天都下午收盤後三個類別都會更新 3 個主題，並且這邊也需要日期區分。並多新增一個新增主題 Btn，當我點擊，你會在最上新增最新主題，
#    可以單選和多選分類，也可以我提供關鍵字你幫我生成主題」；同日：「產出進度和上面這合併同一份清單」。
# 本機起真的 worker.js（devserver.mjs），管理者真的登入，在畫面上真的操作：
#   · 日期分段：topics.json 改成「今天新增 2 題＋原本 10-14 的」（攔截靜態檔，模擬 Claude 生成完寫回）→ 今天那段在最上面、分隔線寫今天、10/14（二）在下面
#   · 「＋ 新增主題」鈕 → 面板打開；預設三類全勾、每類 3；只勾一類（單選）、勾兩類（多選）、全取消 → 送出反灰並寫「至少勾一個類別」
#   · 關鍵字填「a;b」→ 擋下（送出反灰、提示不能有 ;）；改成「CoWoS 產能」→ 送出 → 機器路由讀得到一筆 kind:'topics'、note＝cats=news,know;n=2;kw=CoWoS 產能
#   · 送出後：提示「完成後會出現在清單最上面」、面板收起、清單最上面那段多一列「新增主題」（不能勾選）、進度欄一條「主題｜排隊中」
#   · 直接打 API 的壞值（note 亂寫、id 不是 gen-）→ 400，佇列沒有多
#   · 機器路由標 working／done → 重新整理，那一條變「已完成」滿條
#   · 版面：面板與表格不重疊、沒有整頁橫向捲軸、字 ≥ 11px
#   1440 與 390（觸控）各跑一輪。截圖：TW_TOPICS_SHOTS=<資料夾>
TG_BOT_KEY = "dev-article-bot-key-0123456789abcdef"     # devserver.mjs 寫死的本機鑰匙（不是正式鑰匙）


def _tgw(pg, expr, arg, timeout=6000):
    try:
        pg.wait_for_function(expr, arg=arg, timeout=timeout, polling=150)
        return True
    except Exception:  # noqa: BLE001
        return False


def t_topics_gen_1017(b, base):
    T = "新增主題1017"
    import urllib.request
    import datetime as _dt
    shots = os.environ.get("TW_TOPICS_SHOTS")
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
    origin = re.match(r"^(https?://[^/]+)", base).group(1)
    port = _free_port()
    dev = subprocess.Popen(["node", "--no-warnings", str(ROOT / "workers" / "account-api" / "devserver.mjs"), "--port", str(port), "--origin", origin],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = f"http://127.0.0.1:{port}"
    errs: list[str] = []
    today = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).date()
    lab = lambda d: f"{d.month:02d}/{d.day:02d}（{'一二三四五六日'[d.weekday()]}）"
    tp = json.loads((ROOT / "site" / "articles" / "topics.json").read_text(encoding="utf-8"))
    new2 = [{"id": "n_uitest_new1", "cat": "news", "title": "驗收：今天新增的快訊主題", "why": "驗收用", "score": 4, "format_hint": "兩者", "added": today.isoformat()},
            {"id": "k_uitest_new2", "cat": "know", "title": "驗收：今天新增的知識主題", "why": "驗收用", "score": 2, "format_hint": "文章", "added": today.isoformat()}]
    tp2 = dict(tp, topics=new2 + tp["topics"], updated=today.isoformat())
    ok(f"{T}：repo 裡的 topics.json 每一題都有 added（YYYY-MM-DD）", all(re.match(r"^\d{4}-\d{2}-\d{2}$", str(t.get("added", ""))) for t in tp["topics"]), [t["id"] for t in tp["topics"] if not t.get("added")][:5])

    def bot(body):
        r = urllib.request.Request(api + "/v1/articles/jobs/bot", data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + TG_BOT_KEY}, method="POST")
        try:
            return json.loads(urllib.request.urlopen(r, timeout=5).read())
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def gen_jobs():
        return [j for j in (bot({"op": "open"}).get("jobs") or []) if j.get("kind") == "topics"]

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
        c0 = b.new_context(viewport={"width": 1440, "height": 900})
        c0.add_init_script(INIT); c0.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        p0 = c0.new_page()
        p0.goto(base + "#overview", wait_until="domcontentloaded")
        wait_until(p0, "() => !!document.getElementById('acctBtn')", 8000)
        p0.click("#acctBtn")
        with p0.expect_popup() as pi:
            p0.click("#acctGo")
        pop = pi.value; pop.wait_for_selector("#as-andy", timeout=8000); pop.click("#as-andy")
        if not ok(f"{T}：管理者（Andy 測試帳號）登入成功", bool(wait_until(p0, "() => !!(window.TwAccount && TwAccount.user())", 12000))):
            return
        p0.wait_for_timeout(500)
        state = c0.storage_state()
        c0.close()

        SEC = """() => { const b = document.getElementById('artTpBody'); const sec = [];
            [...b.children].forEach(r => { if (r.classList.contains('jdsep')) sec.push({ d: r.dataset.date, t: r.textContent, bw: parseFloat(getComputedStyle(r.cells[0]).borderTopWidth), rows: [] });
              else if (r.dataset.tid && sec.length) sec[sec.length - 1].rows.push({ id: r.dataset.tid, gen: !!r.dataset.nosel, cus: !!r.dataset.custom, s: r.dataset.score,
                lines: [...r.querySelectorAll('.jline')].map(l => [l.dataset.kind, l.querySelector('.kd').textContent, l.querySelector('.jcap').textContent, l.querySelector('.jprog').dataset.tone]) }); });
            return sec; }"""
        PANEL = """() => { const q = (s) => document.querySelector(s), pn = q('#artTgPanel');
            return { open: pn.getClientRects().length > 0 && pn.getBoundingClientRect().height > 0, exp: q('#artTgBtn').getAttribute('aria-expanded'),
                     cats: [...document.querySelectorAll('#artTgPanel input[data-tgcat]')].filter(c => c.checked).map(c => c.dataset.tgcat),
                     n: q('#artTgN').value, go: q('#artTgGo').disabled, hint: q('#artTgHint').textContent, msg: q('#artTpMsg').hidden ? '' : q('#artTpMsg').textContent }; }"""
        for W in (1440, 390):
            mob = W <= 640
            kw = {"has_touch": True, "is_mobile": True, "device_scale_factor": 1} if mob else {}
            ctx = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, storage_state=state, **kw)
            ctx.add_init_script(INIT); ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            # 模擬 Claude 已經照 topic_gen.md 生成、寫回 topics.json（今天 2 題）
            ctx.route("**/articles/topics.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(tp2, ensure_ascii=False)))
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
            TW = f"{T} {W}"
            try:
                pg.goto(base + "#admin/articles", wait_until="domcontentloaded")
                if not ok(f"{TW}：管理者打開 #admin/articles 看得到主題候選清單與「＋ 新增主題」鈕",
                          bool(wait_until(pg, "() => document.querySelectorAll('#artTpBody tr[data-tid]').length > 10 && !!document.getElementById('artTgBtn')", 15000))):
                    continue
                pg.wait_for_timeout(300)
                # ① 日期分段
                sec = [s for s in pg.evaluate(SEC)]
                ok(f"{TW}：依日期分段、新到舊；最上面那段＝今天 {lab(today)}、只有今天新增的 2 題且分數高的在上；下面有 {lab(_dt.date(2026, 10, 14))} 那段（主題 added）",
                   len(sec) >= 2 and sec[0]["d"] == today.isoformat() and sec[0]["t"] == lab(today) and [r["id"] for r in sec[0]["rows"] if not r["cus"]][:2] == ["n_uitest_new1", "k_uitest_new2"]
                   and any(s["d"] == "2026-10-14" and s["t"] == lab(_dt.date(2026, 10, 14)) for s in sec) and [s["d"] for s in sec] == sorted([s["d"] for s in sec], reverse=True)
                   and all(s["bw"] >= 1 for s in sec), [(s["d"], s["t"], [r["id"] for r in s["rows"]][:4]) for s in sec])
                n_rows0 = pg.evaluate("() => document.querySelectorAll('#artTpBody tr[data-tid]:not([data-custom])').length")
                ok(f"{TW}：候選主題 {len(tp2['topics'])} 題全列出（合併後一題一列）", n_rows0 == len(tp2["topics"]), n_rows0)
                cut = pg.evaluate("() => [...document.querySelectorAll('#artTpBody tr[data-tid]')].filter(r => r.cells[2].getClientRects().length && getComputedStyle(r.cells[2]).display !== 'none' && r.cells[2].scrollWidth > r.cells[2].clientWidth + 1).map(r => r.dataset.tid).slice(0, 5)")
                ok(f"{TW}：類別欄（類別標籤）每一列都沒被截掉", not cut, cut)
                ok(f"{TW}：沒有請求的主題進度欄寫「未產出」", pg.evaluate("() => document.querySelector('#artTpBody tr[data-tid=\"k_uitest_new2\"] .jnone').textContent") == "未產出", None)

                # ② 新增主題面板：預設收起 → 點開、預設三類全勾、每類 3
                st = pg.evaluate(PANEL)
                ok(f"{TW}：面板預設收起", not st["open"] and st["exp"] == "false", st)
                pg.click("#artTgBtn"); pg.wait_for_timeout(150)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：按「＋ 新增主題」→ 面板打開；預設三類全勾、每類 3、送出可按、提示寫三類各 3 個",
                   st["open"] and st["exp"] == "true" and st["cats"] == ["news", "intro", "know"] and st["n"] == "3" and not st["go"]
                   and "比比快訊、比比產業鏈、比比知識 各 3 個" in st["hint"], st)
                # 單選：取消產業鏈、知識 → 只剩快訊
                pg.click("#artTgPanel input[data-tgcat=intro]"); pg.click("#artTgPanel input[data-tgcat=know]"); pg.wait_for_timeout(100)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：單選（只留比比快訊）→ 提示寫「比比快訊 各 3 個」、送出可按", st["cats"] == ["news"] and not st["go"] and "比比快訊 各 3 個" in st["hint"], st)
                # 全取消 → 擋下
                pg.click("#artTgPanel input[data-tgcat=news]"); pg.wait_for_timeout(100)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：三類全取消 → 送出反灰、提示「至少勾一個類別」", st["cats"] == [] and st["go"] and "至少勾一個類別" in st["hint"], st)
                # 多選：快訊＋知識，每類 2
                pg.click("#artTgPanel input[data-tgcat=news]"); pg.click("#artTgPanel input[data-tgcat=know]"); pg.select_option("#artTgN", "2"); pg.wait_for_timeout(100)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：多選（快訊＋知識）、每類改 2 → 提示寫「比比快訊、比比知識 各 2 個」", st["cats"] == ["news", "know"] and st["n"] == "2" and not st["go"] and "比比快訊、比比知識 各 2 個" in st["hint"], st)
                # 壞關鍵字
                n_before = len(gen_jobs())
                pg.fill("#artTgKw", "a;b"); pg.wait_for_timeout(100)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：關鍵字填「a;b」→ 送出反灰、提示不能有 ;", st["go"] and ";" in st["hint"] and "不能有" in st["hint"], st)
                pg.evaluate("() => { const g = document.getElementById('artTgGo'); g.disabled = false; g.click(); }"); pg.wait_for_timeout(300)   # 硬把反灰拿掉再按，送出前的檢查也要擋
                ok(f"{TW}：硬按送出 → 提示「新增主題沒送出」、佇列沒有多", "新增主題沒送出" in pg.evaluate(PANEL)["msg"] and len(gen_jobs()) == n_before, pg.evaluate(PANEL))
                pg.evaluate("() => { const i = document.getElementById('artTgKw'); i.removeAttribute('maxlength'); i.value = '字'.repeat(45); i.dispatchEvent(new Event('input', {bubbles: true})); }")
                st = pg.evaluate(PANEL)
                ok(f"{TW}：關鍵字超過 40 字 → 送出反灰、提示最多 40 個字", st["go"] and "40" in st["hint"], st)
                pg.evaluate("() => document.getElementById('artTgKw').setAttribute('maxlength', '40')")
                pg.fill("#artTgKw", "  CoWoS   產能 "); pg.wait_for_timeout(100)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：關鍵字改「CoWoS 產能」（多餘空白自動收掉）→ 送出可按、提示帶關鍵字", not st["go"] and "「CoWoS 產能」" in st["hint"], st)
                if shots:
                    pg.locator("#artAdmTopics").screenshot(path=str(Path(shots) / f"topics_{W}_panel.png"))
                # 面板版面：裡面的元件兩兩不重疊、不超出卡片
                ov = pg.evaluate("""() => { const pn = document.getElementById('artTgPanel'), P = pn.getBoundingClientRect();
                    const els = [...pn.querySelectorAll(':scope > *, .tgc')].filter(e => !e.classList.contains('tgcats') && e.getClientRects().length).map(e => [e.id || e.className, e.getBoundingClientRect()]);
                    const out = []; for (let i = 0; i < els.length; i++) { const a = els[i][1]; if (a.left < P.left - 1 || a.right > P.right + 1) out.push(['out', els[i][0]]);
                      for (let j = i + 1; j < els.length; j++) { const c = els[j][1]; if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > 1 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 1) out.push([els[i][0], els[j][0]]); } }
                    const fs = Math.min(...[...pn.querySelectorAll('*')].filter(e => e.getClientRects().length && e.textContent.trim()).map(e => parseFloat(getComputedStyle(e).fontSize)));
                    const tb = Math.min(...[...pn.querySelectorAll('button, select, input[type=text], label.tgc')].map(e => e.getBoundingClientRect().height));
                    return { out, fs, tb, sw: document.scrollingElement.scrollWidth - innerWidth }; }""")
                ok(f"{TW}：新增主題面板元件兩兩不重疊、不超出卡片、字 ≥ 11px、按鈕／勾選高 ≥ 32px、沒有整頁橫向捲軸",
                   not ov["out"] and ov["fs"] >= 11 and ov["tb"] >= 31.5 and ov["sw"] <= 1, ov)
                # ③ 送出 → 真的排進一筆 kind:'topics'
                pg.click("#artTgGo")
                _tgw(pg, "() => !!document.querySelector('#artTpBody tr[data-nosel]')", None, 8000)
                pg.wait_for_timeout(300)
                gj = gen_jobs()
                new = [j for j in gj if j.get("note") == "cats=news,know;n=2;kw=CoWoS 產能"]
                ok(f"{TW}：送出 → 佇列真的多一筆 kind:'topics'、topic_id＝gen-時間戳、title＝「新增主題：快訊、知識（各 2 個）」、note＝cats=news,know;n=2;kw=CoWoS 產能",
                   len(gj) == n_before + 1 and len(new) == 1 and re.match(r"^gen-\d{13}$", new[0]["topic_id"]) and new[0]["title"] == "新增主題：快訊、知識（各 2 個）", gj)
                st = pg.evaluate(PANEL)
                ok(f"{TW}：提示「完成後會出現在清單最上面」、面板收起、關鍵字清空", "完成後會出現在清單最上面" in st["msg"] and not st["open"]
                   and pg.input_value("#artTgKw") == "", st)
                jid = new[0]["id"] if new else -1
                sec = pg.evaluate(SEC)
                top = sec[0]["rows"] if sec else []
                g = [r for r in top if r["gen"]]
                ok(f"{TW}：清單最上面那段（今天）第一列＝這筆新增主題（類別寫「新增主題」且沒被截掉、理由欄寫關鍵字、不能勾選）、進度欄一條「主題｜排隊中」",
                   bool(top) and top[0]["gen"] and top[0]["cus"] and len(g) >= 1 and g[0]["lines"][0][:2] == ["topics", "主題"] and g[0]["lines"][0][2].startswith("排隊中")
                   and pg.evaluate(f"() => {{ const r = document.querySelector('#artTpBody .jline[data-job=\"{jid}\"]').closest('tr'); const c = r.cells[2]; return r.querySelector('.tgb').textContent + '|' + r.querySelector('td.dm').textContent + '|' + (c.scrollWidth <= c.clientWidth + 1); }}") == "新增主題|關鍵字：CoWoS 產能|true", top[:2])
                gtid = pg.evaluate(f"() => document.querySelector('#artTpBody .jline[data-job=\"{jid}\"]').closest('tr').dataset.tid")
                pg.click(f"#artTpBody tr[data-tid=\"{gtid}\"] td.l"); pg.wait_for_timeout(150)
                ok(f"{TW}：點新增主題那一列 → 不會被勾選（它不是可以寫文章的主題）", pg.evaluate(f"() => document.querySelector('#artTpBody tr[data-tid=\"{gtid}\"]').getAttribute('aria-selected')") == "false"
                   and pg.evaluate("() => document.querySelector('#artTpSel .tpcnt').textContent") == "0／5", None)
                # 種類篩選「新增主題」→ 只剩新增主題請求
                pg.select_option("#artJfKind", "topics"); pg.wait_for_timeout(150)
                ks = pg.evaluate("() => [...document.querySelectorAll('#artTpBody .jline')].map(l => l.dataset.kind)")
                ok(f"{TW}：種類篩選選「新增主題」→ 只剩新增主題那幾條", bool(ks) and set(ks) == {"topics"}, ks)
                pg.click("#artJfClr"); pg.wait_for_timeout(150)
                # ④ 直接打 API 的壞值 → 400、佇列不變
                n1 = len(gen_jobs())
                bad = pg.evaluate("""async () => { const out = []; for (const b of [{ topic_id: 'gen-1792130000123', kind: 'topics', title: 'x', note: 'cats=news;n=9' },
                    { topic_id: 'c-news-xx', kind: 'topics', title: 'x', note: 'cats=news;n=3' }, { topic_id: 'gen-1792130000124', kind: 'topics', title: 'x', note: 'cats=news;n=3;kw=<b>' }]) {
                    const r = await TwAccount.call('/v1/articles/jobs/add', b); out.push(r && (r.error || (r.job ? 'ok' : '?'))); } return out; }""")
                ok(f"{TW}：直接打 API 送壞值（n=9、id 不是 gen-、關鍵字有 <）→ 全部被擋（bad_input）、佇列沒有多", bad == ["bad_input"] * 3 and len(gen_jobs()) == n1, bad)
                # ⑤ 機器路由標 working → done（Claude 排程做完）→ 重新整理，那一條變已完成
                bot({"op": "mark", "id": jid, "status": "working", "stage": "research"})
                r = bot({"op": "mark", "id": jid, "status": "done", "result": "topics+4"})
                pg.reload(wait_until="domcontentloaded")
                _tgw(pg, "(id) => { const p = document.querySelector(`#artTpBody .jline[data-job=\"${id}\"] .jprog`); return p && p.dataset.tone === 'done'; }", jid, 12000)
                pg.wait_for_timeout(500)
                d = pg.evaluate("(id) => { const l = document.querySelector(`#artTpBody .jline[data-job=\"${id}\"]`); const i = l.querySelector('.jbar i'), bb = l.querySelector('.jbar'); return [l.querySelector('.jcap .js').textContent, i.getBoundingClientRect().width / bb.getBoundingClientRect().width]; }", jid)
                ok(f"{TW}：機器路由標完成 → 重新整理後那一條寫「已完成」、滿條", r.get("ok") is True and d[0] == "已完成" and d[1] > 0.98, [r.get("error"), d])
                # ⑥ 整張表版面
                lay = pg.evaluate("""() => { const out = []; document.querySelectorAll('#artTpBody tr[data-tid]').forEach(tr => {
                    const cs = [...tr.children].filter(td => td.getClientRects().length && getComputedStyle(td).display !== 'none').map(td => [td.cellIndex, td.getBoundingClientRect()]);
                    for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) { const a = cs[i][1], c = cs[j][1];
                      if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > 1 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 1) out.push([tr.dataset.tid, cs[i][0], cs[j][0]]); } });
                    const tiny = [...document.querySelectorAll('#artAdmTopics *')].filter(e => e.getClientRects().length && e.childElementCount === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11).map(e => e.textContent.trim()).slice(0, 5);
                    return { ov: out.slice(0, 5), tiny, sw: document.scrollingElement.scrollWidth - innerWidth }; }""")
                ok(f"{TW}：合併後每一列的格子互不重疊、表內沒有 < 11px 的字、沒有整頁橫向捲軸", not lay["ov"] and not lay["tiny"] and lay["sw"] <= 1, lay)
                if mob:
                    pv = pg.evaluate(f"() => {{ const td = document.querySelector('#artTpBody .jline[data-job=\"{jid}\"]').closest('td.jpc'); const r = td.getBoundingClientRect(), w = td.closest('.tbw').getBoundingClientRect(); return [r.left >= w.left - 1 && r.right <= w.right + 1, Math.round(r.width)]; }}")
                    ok(f"{TW}：手機一題一張卡，進度欄不用左右捲就看得到（寬 {pv[1]}px）", pv[0] and pv[1] > 200, pv)
                if shots:
                    pg.evaluate("() => { const w = document.querySelector('#artAdmTopics .tbw'); w.scrollTop = 0; }")
                    pg.locator("#artAdmTopics").screenshot(path=str(Path(shots) / f"topics_{W}_merged.png"))
                    if mob:
                        pg.locator("#artAdmTopics").scroll_into_view_if_needed()
                        pg.screenshot(path=str(Path(shots) / f"topics_{W}_screen.png"))
            finally:
                ctx.close()
        ok(f"{T}：沒有 JS 錯誤", not errs, errs[:3])
    finally:
        dev.terminate()
        try:
            dev.wait(timeout=5)
        except Exception:  # noqa: BLE001
            dev.kill()


register("新增主題1017", lambda pg, b, base, code: t_topics_gen_1017(b, base))
