# 驗收段落「產貼文頻率設定v2」—— 2026-10-16（site/artsched.js 第 2 版；Worker 格式 {ver:2, enabled, rules}）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_acctm4_ctx、ACCTM4_API 直接可用。不要寫三引號模組說明。
# flake8: noqa

# Andy 10-16：「這邊設計好糟糕 應該是可以選擇 日期 後面是時段以小時為單位， 10:00 AM/PM 這樣 然後接者是產的類型選擇，
#             啟用應該是這邊都選完才會輪到，不應該是這樣順序 … 這裡好亂」
# 真人照畫面順序操作（每一步驗畫面或送出的 body 真的變了）：
#   桌機 1440 深色：預設全空關閉 → 每週一三五 → 10:00 AM、2:00 PM → 快訊 ＋1 → 加入排程（清單文字、送出 body）→ 指定日期（過去日期擋、加兩天、刪一天）
#     → 一模一樣的規則不能重加 → 加一條再刪掉 → 編輯第 1 條 → 開啟用 → 重新整理讀回 → 刪光自動關閉；版面不重疊、無橫向捲軸、字 ≥ 12
#   桌機 1440 淺色、800 窄桌機：讀回兩條規則的畫面、步驟改上下排、無橫向捲軸
#   後端還沒更新（404）：畫面寫原因、規則留在畫面
#   手機 390：手指照順序點一遍主要流程、觸控 ≥ 32、字 ≥ 11、元素兩兩不重疊、無橫向捲軸
# 截圖：環境變數 TW_ASD2_SHOTS＝資料夾 時存 desk-dark／desk-light／w800／mob-390。
def t_artsched_v2(b, base):
    T = "產貼文頻率設定v2"
    import datetime as _dt
    shots = Path(os.environ["TW_ASD2_SHOTS"]) if os.environ.get("TW_ASD2_SHOTS") else None
    now_tpe = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)
    today = now_tpe.date()
    WD = "一二三四五六日"
    hl = lambda h: f"{12 if h % 12 == 0 else h % 12}:00 {'AM' if h < 12 else 'PM'}"
    mdl = lambda d: f"{d.month}/{d.day}（{WD[d.isoweekday() - 1]}）"
    d3, d5 = today + _dt.timedelta(days=3), today + _dt.timedelta(days=5)
    SCH = {"cfg": None, "log": [], "mode": "ok"}

    def api(r):
        hd = {"access-control-allow-origin": "*", "content-type": "application/json"}
        req = r.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return r.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            body = json.loads(req.post_data or "{}")
        except Exception:  # noqa: BLE001
            body = {}
        if path.startswith("/v1/articles/schedule/"):
            if SCH["mode"] == "old":
                return r.fulfill(status=404, body='{"error":"not_found"}', headers=hd)
            if path.endswith("/get"):
                return r.fulfill(status=200, body=json.dumps({"schedule": SCH["cfg"], "allowed": {"hours": list(range(24)), "cats": ["news", "intro", "know"], "max": 3, "maxRules": 20, "maxDates": 31}}), headers=hd)
            if path.endswith("/add"):
                SCH["log"].append({k: v for k, v in body.items() if k != "t"})
                SCH["cfg"] = {"ver": 2, "enabled": body.get("enabled"), "rules": body.get("rules"), "updated": int(time.time() * 1000)}
                return r.fulfill(status=200, body=json.dumps({"ok": True, "schedule": SCH["cfg"]}), headers=hd)
        if path == "/v1/articles/jobs/list":
            return r.fulfill(status=200, body='{"jobs":[]}', headers=hd)
        if path == "/v1/articles/stats":
            return r.fulfill(status=200, body='{"views":{}}', headers=hd)
        if path == "/v1/articles/stats/daily":
            return r.fulfill(status=200, body='{"first":null,"rows":[]}', headers=hd)
        return r.fulfill(status=200, body='{"ok":true}', headers=hd)

    def open_page(ctx):
        ctx.add_init_script("try{localStorage.removeItem('tw.art.sched.draft2');localStorage.setItem('tw.art.admtab','topics');localStorage.setItem('tw.live.on','0')}catch(e){}")
        ctx.route(ACCTM4_API + "/v1/articles/**", api)
        p = ctx.new_page()
        p.goto(base + "#admin/articles", wait_until="domcontentloaded")
        wait_until(p, "() => !!document.getElementById('asdOn') && !/讀取/.test(document.getElementById('asdState').textContent)", 20000)
        p.wait_for_timeout(400)
        return p

    SS = """() => { const q = (s) => document.querySelector(s), on = q('#asdOn');
        return { on: on.checked, dis: on.disabled, lbl: q('#asdOnLbl').textContent, days: [...document.querySelectorAll('#asdDays .dd[aria-pressed=true]')].map(b => +b.dataset.d),
                 hours: [...document.querySelectorAll('.asd .hb[aria-pressed=true]')].map(b => +b.dataset.h), cats: [...document.querySelectorAll('#artSchedCard input[data-kn]')].map(i => +i.value),
                 chips: [...document.querySelectorAll('#asdChips .asd-chip')].map(c => c.dataset.date), mode: (q('.asd-seg button.on') || {}).dataset ? q('.asd-seg button.on').dataset.mode : '',
                 add: q('#asdAdd').disabled, addTxt: q('#asdAdd').textContent, lack: q('#asdLack').textContent, prev: q('#asdPrev').textContent,
                 rows: [...document.querySelectorAll('#asdRules .asd-rule')].map(li => [...li.querySelectorAll('.asd-rd,.asd-rh,.asd-rc')].map(x => x.textContent.trim()).join('｜')),
                 ed: [...document.querySelectorAll('#asdRules .asd-rule.ed')].map(li => +li.dataset.i), cnt: q('#asdCnt').textContent,
                 state: q('#asdState').textContent, note: q('#asdNote').textContent, retry: !q('#asdRetry').hidden }; }"""
    ss = lambda p: p.evaluate(SS)

    def card_shot(p, path):
        # 整頁截圖再裁出卡片：直接截元素會把固定在頂端的頁首疊在卡片上（只是截圖假象，真人捲動時不會），交件截圖要看得到整張卡
        if p.viewport_size["width"] <= 640:   # 手機的捲動容器不是 window，整頁截圖裁不到 → 截圖那一下把固定頁首藏起來再截元素，截完還原
            p.evaluate("() => { const c = document.getElementById('artSchedCard'); window.__asdHid = [...document.querySelectorAll('body *')].filter(e => { const s = getComputedStyle(e).position; return (s === 'fixed' || s === 'sticky') && !e.contains(c) && !c.contains(e); }).map(e => { const v = e.style.visibility; e.style.visibility = 'hidden'; return [e, v]; }); }")
            p.locator("#artSchedCard").screenshot(path=path)
            p.evaluate("() => (window.__asdHid || []).forEach(([e, v]) => { e.style.visibility = v; })")
            return
        p.evaluate("() => window.scrollTo(0, 0)"); p.wait_for_timeout(150)
        r = p.evaluate("() => { const r = document.getElementById('artSchedCard').getBoundingClientRect(); return { x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height }; }")
        p.screenshot(path=path, full_page=True, clip=r)
    # 版面：步驟由上而下、同一個左緣（不是左右兩欄跳）；每組按鈕兩兩不重疊、字不溢出按鈕；整頁無橫向捲軸；最小字級
    LAY = """() => { const V = (e) => !!e && e.getClientRects().length > 0, R = (e) => e.getBoundingClientRect();
        const steps = [...document.querySelectorAll('#artSchedCard .asd-st')].map(R);
        const hit = (a, b) => a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
        const groups = ['#asdDays', '#asdHoursAm', '#asdHoursPm', '.asd-quick', '.asd-cats', '.asd-act', '.asd-seg', '#asdChips', '.asd-save'].map(s => document.querySelector('#artSchedCard ' + s)).filter(V)
          .concat([...document.querySelectorAll('#asdRules .asd-rule, #artSchedCard .asd-st, #artSchedCard .asd-kr, #artSchedCard .asd-rb')]);
        let over = [];
        groups.forEach(g => { const k = [...g.children].filter(V); for (let i = 0; i < k.length; i++) for (let j = i + 1; j < k.length; j++) if (hit(R(k[i]), R(k[j]))) over.push((g.id || g.className) + ':' + i + '×' + j); });
        const clip = [...document.querySelectorAll('#artSchedCard button, #artSchedCard .asd-rule span')].filter(V).filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.textContent.trim().slice(0, 12));
        let minfs = 99; document.querySelectorAll('#artSchedCard *').forEach(e => { if (!V(e)) return; if ([...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) minfs = Math.min(minfs, parseFloat(getComputedStyle(e).fontSize)); });
        const c = R(document.getElementById('artSchedCard'));
        const out = [...document.querySelectorAll('#artSchedCard *')].filter(V).filter(e => { const r = R(e); return r.width > 0 && (r.right > c.right + 0.5 || r.left < c.left - 0.5); }).length;
        const small = [...document.querySelectorAll('#artSchedCard button, #artSchedCard input')].filter(V).filter(e => { const r = R(e); return e.type !== 'checkbox' && !e.closest('.asd-chip') && (r.height < 31.5 || r.width < 31.5); }).length;
        const lb = document.querySelector('#asdStep2 .asd-lb'), bd = document.querySelector('#asdStep2 .asd-bd');
        return { order: steps.every((r, i) => i === 0 || r.top >= steps[i - 1].bottom - 0.5), lefts: [...new Set(steps.map(r => Math.round(r.left)))].length, n: steps.length,
                 over, clip, minfs, out, small, sx: document.documentElement.scrollWidth - innerWidth, stacked: R(bd).top >= R(lb).bottom - 0.5, cardW: Math.round(c.width) }; }"""

    # ================================================================ 桌機 1440 深色
    ctx, _ = _acctm4_ctx(b, "admin", desk=True)
    p = open_page(ctx)
    p.locator("#artSchedCard").scroll_into_view_if_needed()
    s0 = ss(p); t0 = p.inner_text("#artSchedCard")
    ok(f"{T}：預設全空＝沒有星期、時段、篇數、規則；啟用關閉且不能按；加入排程不能按並寫出缺 ①②③",
       s0["days"] == [] and s0["hours"] == [] and s0["cats"] == [0, 0, 0] and s0["rows"] == [] and not s0["on"] and s0["dis"] and s0["add"]
       and all(x in s0["lack"] for x in ("①", "②", "③")) and s0["mode"] == "days", s0)
    ok(f"{T}：頂部只剩一句「到點後最多約 1 小時內，Claude 會自動把文章排進上面的產出進度」，舊說明（09:50 三輪、每小時一次的同步）都拿掉",
       "到點後最多約 1 小時內，Claude 會自動把文章排進上面的產出進度" in t0 and not any(x in t0 for x in ("09:50", "14:50", "20:50", "每小時一次的同步", "儲存設定")), t0[:200])
    hb = p.evaluate("() => [...document.querySelectorAll('.asd .hb')].map(b => b.textContent.trim())")
    ok(f"{T}：② 時段 24 格、12 小時制（上午 12:00 AM…11:00 AM、下午 12:00 PM…11:00 PM），畫面標「台北時間」",
       hb == [hl(h) for h in range(24)] and "台北時間" in t0 and p.evaluate("() => document.querySelectorAll('#asdHoursAm .hb').length") == 12, hb[:3] + hb[-2:])
    l0 = p.evaluate(LAY)
    ok(f"{T}：五個步驟由上而下照 ①→⑤ 排、同一個左緣（不是左右兩欄跳來跳去），⑤ 啟用在最後", l0["n"] == 5 and l0["order"] and l0["lefts"] == 1
       and p.evaluate("() => [...document.querySelectorAll('#artSchedCard .asd-n')].map(n => n.textContent).join('')") == "12345", l0)
    p.click("#asdOn", force=True); p.wait_for_timeout(250)
    ok(f"{T}：清單是空的時硬點啟用 → 打不開、也沒送出任何儲存", not ss(p)["on"] and not SCH["log"], SCH["log"])
    # ① 每週一三五
    for d in (1, 3, 5):
        p.click(f"#asdDays .dd[data-d='{d}']")
    p.wait_for_timeout(100)
    s1 = ss(p)
    ok(f"{T}：① 點週一、三、五 → 三顆亮起、加入鈕仍不能按、缺的只剩 ②③", s1["days"] == [1, 3, 5] and s1["add"] and "①" not in s1["lack"] and "②" in s1["lack"] and "③" in s1["lack"], s1)
    # ② 10:00 AM、2:00 PM
    p.click("#asdHoursAm .hb[data-h='10']"); p.click("#asdHoursPm .hb[data-h='14']"); p.wait_for_timeout(100)
    s2 = ss(p)
    ok(f"{T}：② 點 10:00 AM、2:00 PM → 兩格亮起、缺的只剩 ③", s2["hours"] == [10, 14] and s2["add"] and s2["lack"] == "還缺：③ 至少一類 1 篇以上", s2)
    # ③ 快訊 +1
    p.click("#artSchedCard .asd-kr[data-cat='news'] button[data-st='1']"); p.wait_for_timeout(100)
    s3 = ss(p)
    ok(f"{T}：③ 比比快訊 ＋1 → 加入排程可以按、缺什麼清空、預覽寫「每週一、三、五｜10:00 AM、2:00 PM｜快訊 1」、還沒送出任何儲存",
       not s3["add"] and s3["lack"] == "" and "每週一、三、五｜10:00 AM、2:00 PM｜快訊 1" in s3["prev"] and s3["cats"] == [1, 0, 0] and not SCH["log"], s3)
    # ④ 加入
    p.click("#asdAdd"); p.wait_for_timeout(500)
    s4 = ss(p)
    r1 = {"days": [1, 3, 5], "hours": [10, 14], "cats": {"news": 1, "intro": 0, "know": 0}}
    ok(f"{T}：④ 按「加入排程」→ 自動儲存，送出 {{ver:2, enabled:false, rules:[每週一三五 10、14 點 快訊 1]}}", SCH["log"] == [{"ver": 2, "enabled": False, "rules": [r1]}], SCH["log"])
    ok(f"{T}：④ 清單出現第 1 條「每週一、三、五｜10:00 AM、2:00 PM｜快訊 1」、計數 1／20、上面 ①②③ 清空回預設、⑤ 寫「已儲存 HH:MM」",
       s4["rows"] == ["每週一、三、五｜10:00 AM、2:00 PM｜快訊 1"] and s4["cnt"] == "1／20 條" and s4["days"] == [] and s4["hours"] == [] and s4["cats"] == [0, 0, 0]
       and re.match(r"^已儲存 \d\d:\d\d$", s4["state"]) and not s4["dis"] and not s4["on"], s4)
    # 一模一樣的規則不能重加
    for d in (1, 3, 5):
        p.click(f"#asdDays .dd[data-d='{d}']")
    p.click("#asdHoursAm .hb[data-h='10']"); p.click("#asdHoursPm .hb[data-h='14']"); p.click("#artSchedCard .asd-kr[data-cat='news'] button[data-st='1']"); p.wait_for_timeout(100)
    sd = ss(p)
    ok(f"{T}：再組一條一模一樣的 → 加入鈕不能按、寫「跟第 1 條一模一樣」", sd["add"] and "第 1 條一模一樣" in sd["lack"], sd)
    p.click(".asd-quick button[data-q='none']"); p.click("#asdHoursAm .hb[data-h='10']"); p.click("#asdHoursPm .hb[data-h='14']"); p.click("#artSchedCard .asd-kr[data-cat='news'] button[data-st='-1']"); p.wait_for_timeout(100)
    ok(f"{T}：「清除」星期、再點一次時段與 − → 全部取消", ss(p)["days"] == [] and ss(p)["hours"] == [] and ss(p)["cats"] == [0, 0, 0], ss(p))
    # 指定日期
    p.click("#asdModeDates"); p.wait_for_timeout(100)
    yest = (today - _dt.timedelta(days=1)).isoformat()
    p.fill("#asdDate", yest); p.click("#asdDateAdd"); p.wait_for_timeout(100)
    tip = p.inner_text("#asdDateTip")
    ok(f"{T}：指定日期模式：日曆最早只能選今天（min＝{today}），硬填昨天按加入 → 寫「過去的日期不能選」、沒有變成標籤",
       p.get_attribute("#asdDate", "min") == today.isoformat() and "過去的日期不能選" in tip and ss(p)["chips"] == [] and ss(p)["mode"] == "dates", [tip, ss(p)["chips"]])
    for d in (d5, d3, today + _dt.timedelta(days=4)):
        p.fill("#asdDate", d.isoformat()); p.click("#asdDateAdd"); p.wait_for_timeout(80)
    p.click(f"#asdChips button[data-undate='{(today + _dt.timedelta(days=4)).isoformat()}']"); p.wait_for_timeout(100)
    sc = ss(p)
    ok(f"{T}：加三天再按 × 刪掉中間那天 → 剩兩個小標籤（由早到晚：{d3}、{d5}）", sc["chips"] == [d3.isoformat(), d5.isoformat()], sc["chips"])
    p.click("#asdHoursPm .hb[data-h='21']")
    for _ in range(2):
        p.click("#artSchedCard .asd-kr[data-cat='intro'] button[data-st='1']")
    p.wait_for_timeout(100)
    p.click("#asdAdd"); p.wait_for_timeout(500)
    s5 = ss(p)
    r2 = {"dates": [d3.isoformat(), d5.isoformat()], "hours": [21], "cats": {"news": 0, "intro": 2, "know": 0}}
    ok(f"{T}：指定日期那條加入 → 送出 rules 第 2 條＝{{dates:[{d3}, {d5}], hours:[21], cats 產業鏈 2}}；清單第 2 條「{mdl(d3)}、{mdl(d5)}｜9:00 PM｜產業鏈 2」",
       SCH["log"][-1] == {"ver": 2, "enabled": False, "rules": [r1, r2]} and s5["rows"][1] == f"{mdl(d3)}、{mdl(d5)}｜9:00 PM｜產業鏈 2", [SCH["log"][-1], s5["rows"]])
    # 再加一條然後刪掉
    p.click("#asdModeDays"); p.click(".asd-quick button[data-q='all']"); p.click("#asdHoursAm .hb[data-h='8']"); p.click("#artSchedCard .asd-kr[data-cat='know'] button[data-st='1']"); p.wait_for_timeout(100)
    p.click("#asdAdd"); p.wait_for_timeout(500)
    s6 = ss(p)
    ok(f"{T}：「每天」快捷＋8:00 AM＋知識 1 → 第 3 條「每天｜8:00 AM｜知識 1」、送出 3 條", s6["rows"][2:] == ["每天｜8:00 AM｜知識 1"] and len(SCH["log"][-1]["rules"]) == 3, s6["rows"])
    p.click("#asdRules .asd-rule[data-i='2'] button[data-del]"); p.wait_for_timeout(500)
    s7 = ss(p)
    ok(f"{T}：按第 3 條的「刪除」→ 清單剩 2 條、馬上送出剩下的 2 條、畫面寫「已刪除第 3 條」", len(s7["rows"]) == 2 and SCH["log"][-1]["rules"] == [r1, r2] and "已刪除第 3 條" in s7["note"], [s7, SCH["log"][-1]])
    # 編輯第 1 條
    p.click("#asdRules .asd-rule[data-i='0'] button[data-ed]"); p.wait_for_timeout(300)
    s8 = ss(p)
    ok(f"{T}：按第 1 條「編輯」→ 上面 ①②③ 帶回（週一三五、10:00 AM、2:00 PM、快訊 1）、按鈕變「更新第 1 條」、那一列標成編輯中",
       s8["mode"] == "days" and s8["days"] == [1, 3, 5] and s8["hours"] == [10, 14] and s8["cats"] == [1, 0, 0] and s8["addTxt"] == "更新第 1 條" and s8["ed"] == [0], s8)
    p.click("#asdHoursPm .hb[data-h='20']"); p.wait_for_timeout(100)
    p.click("#asdAdd"); p.wait_for_timeout(500)
    s9 = ss(p)
    r1b = {**r1, "hours": [10, 14, 20]}
    ok(f"{T}：加 8:00 PM 再按「更新第 1 條」→ 第 1 條變「…｜10:00 AM、2:00 PM、8:00 PM｜快訊 1」（還是 2 條、不是多一條）、送出的第 1 條 hours＝[10,14,20]、按鈕回到「加入排程」",
       s9["rows"][0] == "每週一、三、五｜10:00 AM、2:00 PM、8:00 PM｜快訊 1" and len(s9["rows"]) == 2 and SCH["log"][-1]["rules"] == [r1b, r2] and s9["addTxt"] == "加入排程" and s9["ed"] == [], [s9, SCH["log"][-1]])
    # ⑤ 啟用
    n0 = len(SCH["log"])
    p.click("#asdOn"); p.wait_for_timeout(500)
    sa = ss(p)
    ok(f"{T}：⑤ 開啟用 → 立刻送出 {{ver:2, enabled:true, rules:兩條}}、開關亮、寫「已啟用」與「已儲存 HH:MM」",
       len(SCH["log"]) == n0 + 1 and SCH["log"][-1] == {"ver": 2, "enabled": True, "rules": [r1b, r2]} and sa["on"] and "已啟用" in sa["lbl"] and re.match(r"^已儲存 \d\d:\d\d$", sa["state"]), [sa, SCH["log"][-1]])
    la = p.evaluate(LAY)
    ok(f"{T}：1440 版面：沒有橫向捲軸、卡片內沒有東西超出、按鈕兩兩不重疊、按鈕字沒被截斷、字 ≥ 12（最小 {la['minfs']}）",
       la["sx"] <= 0 and la["out"] == 0 and not la["over"] and not la["clip"] and la["minfs"] >= 12 and la["small"] == 0, la)
    if shots:
        p.click("#asdModeDates"); p.fill("#asdDate", d3.isoformat()); p.click("#asdDateAdd"); p.click("#asdModeDays"); p.click("#asdDays .dd[data-d='2']"); p.wait_for_timeout(150)
        card_shot(p, str(shots / "desk-1440-dark.png"))
        p.click("#asdDays .dd[data-d='2']")
    # 重新整理讀回
    p.reload(wait_until="domcontentloaded")
    wait_until(p, "() => !!document.getElementById('asdOn') && /已儲存/.test(document.getElementById('asdState').textContent)", 20000); p.wait_for_timeout(300)
    sr = ss(p)
    ok(f"{T}：重新整理 → 從伺服器讀回一樣的兩條規則、啟用中、寫「已儲存」", sr["rows"] == s9["rows"] and sr["on"] and "已儲存" in sr["state"], sr)
    # 開著把規則刪光 → 自動關閉
    p.click("#asdRules .asd-rule[data-i='0'] button[data-del]"); p.wait_for_timeout(500)
    p.click("#asdRules .asd-rule[data-i='0'] button[data-del]"); p.wait_for_timeout(500)
    sz = ss(p)
    ok(f"{T}：開著時把規則刪光 → 自動關閉、送出 {{enabled:false, rules:[]}}、啟用鈕又變成不能按、寫「已自動關閉」",
       not sz["on"] and sz["dis"] and SCH["log"][-1] == {"ver": 2, "enabled": False, "rules": []} and "已自動關閉" in sz["note"] and sz["rows"] == [], [sz, SCH["log"][-1]])
    ctx.close()

    # ================================================================ 後端還沒更新（404）
    SCH["mode"] = "old"; SCH["log"].clear()
    ctx, _ = _acctm4_ctx(b, "admin", desk=True)
    p = open_page(ctx)
    p.click("#asdDays .dd[data-d='2']"); p.click("#asdHoursAm .hb[data-h='9']"); p.click("#artSchedCard .asd-kr[data-cat='news'] button[data-st='1']"); p.click("#asdAdd"); p.wait_for_timeout(400)
    so = ss(p)
    ok(f"{T}：後端還沒更新（404）→ ⑤ 寫「後端還沒更新」、規則照樣留在清單（不丟）、沒有假裝已儲存", "後端還沒更新" in so["state"] and so["rows"] == ["每週二｜9:00 AM｜快訊 1"] and "已儲存" not in so["state"], so)
    p.click("#asdOn"); p.wait_for_timeout(300)
    ok(f"{T}：後端還沒更新時切啟用 → 退回關閉、寫「開關沒切成功」", not ss(p)["on"] and "沒切成功" in ss(p)["note"], ss(p))
    ctx.close()
    SCH["mode"] = "ok"

    # ================================================================ 桌機 1440 淺色、800 窄桌機（讀回兩條、已啟用）
    SCH["cfg"] = {"ver": 2, "enabled": True, "rules": [r1b, r2], "updated": int(time.time() * 1000)}
    for w, light in ((1440, True), (800, False)):
        ctx, _ =_acctm4_ctx(b, "admin", desk=True)
        if light:
            ctx.add_init_script("try{localStorage.setItem('tw.theme','light')}catch(e){}")
        p = open_page(ctx)
        if w != 1440:
            p.set_viewport_size({"width": w, "height": 900}); p.wait_for_timeout(500)
        p.locator("#artSchedCard").scroll_into_view_if_needed()
        sl = ss(p); ll = p.evaluate(LAY)
        th = p.evaluate("() => document.documentElement.dataset.theme || document.documentElement.getAttribute('data-theme4') || ''")
        ok(f"{T}：{w}{'（淺色）' if light else ''}：讀回 2 條、已啟用；無橫向捲軸、卡內不超出、按鈕不重疊、字沒截斷" + ("；步驟標題改到內容上面（上下排）" if w <= 820 else ""),
           len(sl["rows"]) == 2 and sl["on"] and ll["sx"] <= 0 and ll["out"] == 0 and not ll["over"] and not ll["clip"] and (ll["stacked"] if w <= 820 else not ll["stacked"]), [sl["rows"], ll, th])
        if shots:
            card_shot(p, str(shots / ("desk-1440-light.png" if light else "desk-800.png")))
        ctx.close()

    # ================================================================ 手機 390
    SCH["cfg"] = None; SCH["log"].clear()
    ctx, _ = _acctm4_ctx(b, "admin", vp=(390, 844))
    p = open_page(ctx)
    p.locator("#artSchedCard").scroll_into_view_if_needed()
    for d in (1, 3, 5):
        p.locator(f"#asdDays .dd[data-d='{d}']").tap()
    p.locator("#asdHoursAm .hb[data-h='10']").tap(); p.locator("#asdHoursPm .hb[data-h='14']").tap()
    p.locator("#artSchedCard .asd-kr[data-cat='news'] button[data-st='1']").tap(); p.wait_for_timeout(100)
    p.locator("#asdAdd").tap(); p.wait_for_timeout(500)
    m1 = ss(p)
    ok(f"{T}：手機 390：手指點週一三五 → 10:00 AM、2:00 PM → 快訊 ＋ → 加入排程 → 清單第 1 條文字正確、送出 body 正確",
       m1["rows"] == ["每週一、三、五｜10:00 AM、2:00 PM｜快訊 1"] and SCH["log"] == [{"ver": 2, "enabled": False, "rules": [r1]}], [m1["rows"], SCH["log"]])
    p.locator("#asdModeDates").tap(); p.fill("#asdDate", d3.isoformat()); p.locator("#asdDateAdd").tap()
    p.locator("#asdHoursPm .hb[data-h='21']").tap(); p.locator("#artSchedCard .asd-kr[data-cat='know'] button[data-st='1']").tap(); p.wait_for_timeout(100)
    p.locator("#asdAdd").tap(); p.wait_for_timeout(500)
    p.locator("#asdOn").tap(); p.wait_for_timeout(500)
    m2 = ss(p)
    ok(f"{T}：手機 390：指定日期加一條、手指開啟用 → 2 條、送出 enabled:true 且第 2 條是 dates", len(m2["rows"]) == 2 and m2["on"] and SCH["log"][-1]["enabled"] is True and SCH["log"][-1]["rules"][1] == {"dates": [d3.isoformat()], "hours": [21], "cats": {"news": 0, "intro": 0, "know": 1}}, [m2, SCH["log"][-1]])
    p.locator("#asdModeDays").tap(); p.locator("#asdDays .dd[data-d='6']").tap(); p.locator("#asdHoursAm .hb[data-h='11']").tap(); p.wait_for_timeout(150)
    lm = p.evaluate(LAY)
    ok(f"{T}：手機 390：沒有橫向捲軸、卡內不超出、元素兩兩不重疊、按鈕字沒截斷、觸控 ≥ 32px、字 ≥ 11（最小 {lm['minfs']}）、步驟上下排",
       lm["sx"] <= 0 and lm["out"] == 0 and not lm["over"] and not lm["clip"] and lm["small"] == 0 and lm["minfs"] >= 11 and lm["stacked"] and lm["order"], lm)
    hw = p.evaluate("() => { const r = [...document.querySelectorAll('#asdHoursAm .hb')].map(b => b.getBoundingClientRect()); return [new Set(r.map(x => Math.round(x.top))).size, Math.round(Math.min(...r.map(x => x.width)))]; }")
    ok(f"{T}：手機 390：上午 12 格排成 3 排（每排 4 顆、每顆寬 {hw[1]}px ≥ 64）", hw[0] == 3 and hw[1] >= 64, hw)
    if shots:
        card_shot(p, str(shots / "mob-390.png"))
    ctx.close()


register("產貼文頻率設定v2", lambda pg, b, base, code: t_artsched_v2(b, base), after="文章主題兩分頁1016")
