# 驗收段落「頻道規劃」：#channels 母分頁（只給管理者）——管理者看得到並切子分頁內容真的變、非管理者看不到、手機收展
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def t_channels_1104(b, base, code):
    T = "頻道規劃"
    errs = []
    shots = pathlib.Path(os.environ.get("TW_CH_SHOTS", "")) if os.environ.get("TW_CH_SHOTS") else None
    SUBS = [("overview", "總覽", "頻道清單"), ("ch1", "① 哩股哩股", "內容柱與比重"), ("ch2", "② 科技透明圈", "公司待遇行情"),
            ("ch3", "③ AI 介紹", "上班族的 AI 實戰"), ("ch4", "④ 心靈雞湯", "內容柱與比重"), ("funnel", "LINE＋Email", "漏斗流程"), ("review", "檢討指標", "沒達標怎麼調")]
    for w in (1440, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("window.TW_CH_OVERRIDE=true;try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#channels", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#v-channels .chn-tabs a').length >= 7", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            ok(f"【{T}】{w} 管理者開 #channels：七個子分頁都在", pg.evaluate("() => document.querySelectorAll('#v-channels .chn-tabs a').length") == 7)
            if not mob:
                ok(f"【{T}】{w} 側欄看得到「頻道規劃」母項與七個子項", pg.evaluate("() => { const t = document.querySelector('.tab[data-view=channels]'); const s = [...document.querySelectorAll('.l4subtab[data-parent=channels]')]; return !!t && t.offsetParent !== null && s.length === 7 && s.every(e => e.offsetParent !== null); }"))
            seen = set()
            for sid, nm, blk in SUBS:
                pg.click(f"#v-channels .chn-tabs a[data-sub={sid}]")
                wait_until(pg, f"() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === '{sid}'", 8000)
                if mob:   # 手機區塊預設收起，標題仍在 DOM
                    pass
                heads = pg.evaluate("() => [...document.querySelectorAll('#v-channels .chn-h h3')].map(e => e.textContent)")
                sig = "|".join(heads)
                ok(f"【{T}】{w} 切到「{nm}」→ 網址、分頁高亮、區塊內容都換了", f"#channels/{sid}" in pg.url and pg.evaluate("() => document.querySelector('#v-channels .chn-tabs a.on').dataset.sub") == sid and (blk in sig or blk in pg.evaluate("() => document.querySelector('#v-channels .chn-grid').textContent")) and sig not in seen, heads)
                seen.add(sig)
            # 頻道頁必備七塊
            for sid in ("ch1", "ch2", "ch3", "ch4"):
                pg.goto(base + f"#channels/{sid}", wait_until="domcontentloaded")
                wait_until(pg, f"() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === '{sid}'", 8000)
                heads = pg.evaluate("() => [...document.querySelectorAll('#v-channels .chn-h h3')].map(e => e.textContent)")
                need = ["主題方向", "短中長期目標", "經營方式", "發文方式", "IG／Threads 分配", "發文時段", "法遵紅線"]
                ok(f"【{T}】{w} {sid} 頁有 {len(need)} 個必備區塊", all(n in heads for n in need), heads)
            # 總覽點一列進該頻道
            pg.goto(base + "#channels/overview", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === 'overview'", 8000)
            if mob:
                pg.click("#v-channels .chn-blk >> nth=0 >> .chn-h")
                pg.wait_for_timeout(200)
            pg.click("#v-channels tr.chn-go >> nth=0")
            wait_until(pg, "() => location.hash === '#channels/ch1'", 6000)
            ok(f"【{T}】{w} 總覽點「① 哩股哩股」那列 → 進頻道①", "#channels/ch1" in pg.url)
            # 「?」點開、點背景關閉
            pg.goto(base + "#channels/ch1", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === 'ch1'", 8000)
            closed0 = pg.evaluate("() => [...document.querySelectorAll('#v-channels .chn-blk')].filter(e => e.querySelector('.chn-b').offsetParent !== null).length")
            ht0 = pg.evaluate("() => document.documentElement.scrollHeight")
            if mob:
                pg.click("#v-channels .chn-blk[data-k='ch1.0'] .chn-h h3"); pg.wait_for_timeout(200)
            pg.click("#v-channels .chn-blk[data-k='ch1.0'] .chn-q"); pg.wait_for_timeout(150)
            vis1 = pg.is_visible("#v-channels .chn-blk[data-k='ch1.0'] .chn-pop")
            pg.click("#v-channels .chn-tag"); pg.wait_for_timeout(150)
            vis2 = pg.is_visible("#v-channels .chn-blk[data-k='ch1.0'] .chn-pop")
            ok(f"【{T}】{w} 「?」點開出現說明、點背景就關", vis1 and not vis2, (vis1, vis2))
            # 版面：不橫向捲動、字級 ≥11
            m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth - innerWidth, small: [...document.querySelectorAll('#v-channels *')].filter(e => !e.childElementCount && (e.textContent||'').trim() && e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 11).length })")
            ok(f"【{T}】{w} 無橫向捲軸、字級不小於 11px", m["sw"] <= 1 and m["small"] == 0, m)
            if mob:
                for sid2 in ("overview", "ch1", "ch2", "ch3", "ch4", "funnel", "review"):
                    pg.goto(base + f"#channels/{sid2}", wait_until="domcontentloaded")
                    wait_until(pg, f"() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === '{sid2}'", 8000); pg.wait_for_timeout(300)
                    h2 = pg.evaluate("() => document.getElementById('v-channels').getBoundingClientRect().height")
                    ok(f"【{T}】{w} 手機 {sid2} 預設收起整頁 ≤3 屏（{h2:.0f}px / {844 * 3}）", h2 <= 844 * 3, h2)
                pg.goto(base + "#channels/ch1", wait_until="domcontentloaded")
                wait_until(pg, "() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === 'ch1'", 8000)
                ok(f"【{T}】{w} 手機區塊預設全收起（一頁看完重點）", closed0 == 0, closed0)
                ok(f"【{T}】{w} 頻道頁收起時整頁 ≤3 屏", ht0 <= 844 * 3, ht0)
                pg.click("#v-channels .chn-blk[data-k='ch1.1'] .chn-h h3"); pg.wait_for_timeout(200)
                ok(f"【{T}】{w} 點標題展開、再點收起", pg.is_visible("#v-channels .chn-blk[data-k='ch1.1'] .chn-b"))
                pg.click("#v-channels .chn-blk[data-k='ch1.1'] .chn-h h3"); pg.wait_for_timeout(200)
                ok(f"【{T}】{w} 再點收起", not pg.is_visible("#v-channels .chn-blk[data-k='ch1.1'] .chn-b"))
            else:
                ht = pg.evaluate("() => document.documentElement.scrollHeight")
                ok(f"【{T}】{w} 桌機頻道頁 ≤3 屏", ht <= 900 * 3, ht)
            if shots:
                for sid in ("overview", "ch1"):
                    pg.goto(base + f"#channels/{sid}", wait_until="domcontentloaded"); pg.wait_for_timeout(900)
                    pg.screenshot(path=str(shots / f"w{w}_{sid}.png"), full_page=True)
        except Exception as e:
            ok(f"【{T}】{w} 流程不出例外", False, repr(e)[:300])
        finally:
            c.close()
    # 非管理者：入口看不到、路由導回總覽、內容不畫
    for tag, vp, mob in [("桌機", {"width": 1440, "height": 900}, False), ("手機", {"width": 390, "height": 844}, True)]:
        c3 = b.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
        c3.add_init_script("window.TW_CH_OVERRIDE=false;try{localStorage.setItem('tw.tour','done')}catch(e){};setTimeout(function(){window.dispatchEvent(new Event('tw:account'))},1000)")
        p3 = c3.new_page(); p3.on("pageerror", lambda e: errs.append(str(e)))
        p3.goto(base + "#channels/ch1", wait_until="load"); p3.wait_for_timeout(1900)
        ok(f"【{T}】非管理者（{tag}）：#channels 被導回總覽", p3.evaluate("() => location.hash") == "#overview", p3.url)
        ok(f"【{T}】非管理者（{tag}）：導覽看不到「頻道規劃」", p3.evaluate("() => [...document.querySelectorAll('.tab[data-view=channels], .l4subtab[data-parent=channels], a[href=\"#channels\"]')].every(e => e.offsetParent === null)"))
        ok(f"【{T}】非管理者（{tag}）：沒畫任何區塊", p3.evaluate("() => document.querySelectorAll('#v-channels .chn-blk').length") == 0)
        c3.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])





# ===================================================================== 頻道規劃總覽加掛：頻道卡、週曆撞時段、時數、缺漏清單（2026-11-04 併入；資料在 plan.json 的 cards／schedule／gaps）
def t_channels_cal(b, base, code):
    import json as _json, re as _re
    T = "頻道規劃總覽"
    plan = _json.loads((SITE / "channels" / "plan.json").read_text(encoding="utf-8"))
    cards, sched, gaps = plan["cards"], plan["schedule"], plan["gaps"]
    isfix = lambda w: bool(_re.match(r"^週[一二三四五六日]", w["day"]) and _re.match(r"^\d{1,2}:\d{2}", w["time"]))

    def open_page(W, H, adm):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script(f"window.TW_CH_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}}catch(e){{}}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.goto(base + "#channels/overview", wait_until="load")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count() and ag.first.is_visible():
            ag.first.click()
        wait_until(pg, "() => document.querySelectorAll('#v-channels .chx-card').length >= 1", 15000)
        pg.wait_for_timeout(400)
        return ctx, pg

    ctx, pg = open_page(1440, 900, True)
    ok(f"【{T}】管理者：頻道卡 {len(cards)} 張，名稱對得上 plan.json（含頻道④）", pg.evaluate("() => [...document.querySelectorAll('.chx-card .chx-nm')].map(e => e.textContent)") == [c["name"] for c in cards])
    ok(f"【{T}】卡片上「每週發文」數字對得上排程筆數", pg.evaluate("() => [...document.querySelectorAll('.chx-card')].map(e => +e.querySelector('.chx-kv em').textContent)") == [sum(1 for w in sched if w["ch"] == c["id"]) for c in cards])
    n_fix = sum(1 for w in sched if isfix(w)); n_flex = len(sched) - n_fix
    n_chip = pg.evaluate("() => document.querySelectorAll('.chx-cal .chx-chip').length")
    ok(f"【{T}】週曆小標數 {n_chip} ＝ 排程裡有星期有時間的 {n_fix}", n_chip == n_fix, f"{n_chip} vs {n_fix}")
    ok(f"【{T}】機動（不限時段）{n_flex} 筆另列", pg.evaluate("() => document.querySelectorAll('.chx-flex .chx-chip').length") == n_flex)
    clash = pg.evaluate("() => [...document.querySelectorAll('.chx-cr .cell.clash')].map(e => e.dataset.day + ' ' + e.dataset.tm)")
    ok(f"【{T}】週一 20:30（頻道①）與 21:00（頻道③、④）相隔 30 分：標撞時段", "週一 20:30" in clash and "週一 21:00" in clash, str(clash))
    ok(f"【{T}】週曆裡看得到頻道④的小標", pg.evaluate("() => [...document.querySelectorAll('.chx-cal .chx-chip')].some(e => e.className.indexOf('c3') >= 0)"))
    ok(f"【{T}】缺漏清單預設收起、點開 {len(gaps)} 項（含「頻道④由另一聊天室規劃」）",
       pg.evaluate("() => !document.getElementById('chxGaps').open") and pg.evaluate("() => { document.querySelector('#chxGaps summary').click(); return document.querySelectorAll('#chxGaps .chx-gr').length; }") == len(gaps)
       and pg.evaluate("() => document.getElementById('chxGaps').innerText.indexOf('頻道④由另一聊天室規劃') >= 0"))
    pg.click(".chx-card[data-ch=ch4]"); wait_until(pg, "() => location.hash === '#channels/ch4'", 6000)
    ok(f"【{T}】點頻道④卡進頻道④子頁", pg.evaluate("() => document.querySelector('#v-channels .chn-grid').dataset.sub") == "ch4" or wait_until(pg, "() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === 'ch4'", 6000))
    pg.goto(base + "#channels/overview", wait_until="load"); wait_until(pg, "() => document.querySelectorAll('.chx-cal .chx-chip').length > 0", 8000)
    pg.click(".chx-cal .chx-chip >> nth=0"); wait_until(pg, "() => /^#channels\\/ch\\d$/.test(location.hash)", 6000)
    ok(f"【{T}】點週曆小標進該頻道子頁", bool(pg.evaluate("() => /^#channels\\/ch\\d$/.test(location.hash)")))
    pg.goto(base + "#channels/overview", wait_until="load"); wait_until(pg, "() => document.querySelectorAll('.chx-card').length >= 1", 8000)
    ov = pg.evaluate("() => { const bad = []; document.querySelectorAll('.chx-card, .chx-sec, .chx-cal').forEach(e => { if (e.scrollWidth > e.clientWidth + 2) bad.push(e.className); }); const cs = [...document.querySelectorAll('.chx-card')].map(e => e.getBoundingClientRect()); for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) { const a = cs[i], c = cs[j]; if (a.left < c.right - 1 && c.left < a.right - 1 && a.top < c.bottom - 1 && c.top < a.bottom - 1) bad.push('card重疊'); } return bad; }")
    ok(f"【{T}】桌機 1440：頻道卡與週曆沒有溢出或重疊", not ov, str(ov))
    ctx.close()
    # 非管理者：沒有入口、沒有畫週曆（導回由主段落驗）
    ctx, pg = open_page_nonadm(b, base, T)
    ctx.close()
    # 手機 390
    ctx, pg = open_page(390, 844, True)
    m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, small: [...document.querySelectorAll('#v-channels *')].filter(e => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11 && e.getBoundingClientRect().width > 0).map(e => e.className).slice(0, 5) })")
    ok(f"【{T}】手機 390：無橫向捲軸、沒有小於 11px 的字", m["sw"] <= m["cw"] + 1 and not m["small"], str(m))
    # 手機卡片列距收緊（表格轉卡片後每欄位一列，列距 ≤ 22px）
    pg.goto(base + "#channels/ch1", wait_until="load"); wait_until(pg, "() => document.querySelector('#v-channels .chn-grid')", 8000); pg.wait_for_timeout(300)
    pg.click("#v-channels .chn-blk[data-k='ch1.2'] .chn-h h3"); pg.wait_for_timeout(250)
    gap = pg.evaluate("() => { const t = [...document.querySelectorAll('#v-channels .chn-blk[data-k=\\'ch1.2\\'] .chn-t td')].filter(e => e.offsetParent); if (t.length < 3) return -1; const r = t.map(e => e.getBoundingClientRect()); let mx = 0; for (let i = 1; i < r.length; i++) { const g = r[i].top - r[i - 1].bottom; if (g > mx) mx = g; } return mx; }")
    ok(f"【{T}】手機 390：卡片列與列的間距收緊（最大 {gap:.0f}px ≤ 14）", gap >= 0 and gap <= 14, gap)
    ctx.close()


def open_page_nonadm(b, base, T):
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("window.TW_CH_OVERRIDE=false;try{localStorage.setItem('tw.tour','done')}catch(e){};setTimeout(function(){window.dispatchEvent(new Event('tw:account'))},1000)")
    pg = ctx.new_page()
    pg.goto(base + "#channels/overview", wait_until="load"); pg.wait_for_timeout(1900)
    ok(f"【{T}】非管理者：導回總覽、沒畫頻道卡與週曆", pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => document.querySelectorAll('.chx-card, .chx-cal').length") == 0)
    return ctx, pg


def t_channels_all(b, base, code):
    t_channels_1104(b, base, code)
    t_channels_cal(b, base, code)


register("頻道規劃", lambda pg, b, base, code: t_channels_all(b, base, code))
