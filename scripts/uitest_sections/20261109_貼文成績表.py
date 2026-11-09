# 驗收段落「貼文成績表」：#channels/scores 子分頁（只給管理者）——切過去表格有第一筆、頻道篩選真的改變列數、非管理者看不到、手機卡片式預設收起
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def t_channel_scores(b, base, code):
    import json as _json
    T = "貼文成績表"
    errs = []
    data = _json.loads((SITE / "channels" / "scores.json").read_text(encoding="utf-8"))
    first = data[0]
    EXTRA = {"date": "2026-11-08", "channel": "②", "title": "驗收假資料（只在這次測試用）", "platforms": {"threads": True, "ig": False},
             "score": 45, "comment": "測試用低分", "template": False, "rule_added": "", "links": {"threads": "", "ig": ""}, "cover": ""}
    for w in (1440, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, is_mobile=mob, has_touch=mob)
        # TW_SC_TODAY 固定「今天」＝第一筆那一天，週平均才算得出來；加一筆上週低分驗證「與上週差」
        c.add_init_script("window.TW_CH_OVERRIDE=true;window.TW_SC_TODAY='%s';try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.removeItem('chn.open')}catch(e){}" % first["date"])
        # 攔截 scores.json：原資料加一筆不同頻道、上週、<60 的假資料，才驗得到篩選與待改標籤
        c.route("**/channels/scores.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_json.dumps(data + [EXTRA], ensure_ascii=False)))
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#channels/overview", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#v-channels .chn-tabs a').length >= 8", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            ok(f"【{T}】{w} 子分頁列有「貼文成績表」", pg.evaluate("() => [...document.querySelectorAll('#v-channels .chn-tabs a')].some(a => a.dataset.sub === 'scores' && a.textContent.trim() === '貼文成績表')"))
            if not mob:
                ok(f"【{T}】{w} 側欄看得到「貼文成績表」子項", pg.evaluate("() => { const s = document.querySelector('.l4subtab[data-parent=channels][data-h=\"#channels/scores\"], .l4subtab[data-parent=channels]:last-of-type'); return [...document.querySelectorAll('.l4subtab[data-parent=channels]')].some(e => e.offsetParent !== null && e.textContent.indexOf('貼文成績表') >= 0); }"))
            pg.click("#v-channels .chn-tabs a[data-sub=scores]")
            wait_until(pg, "() => document.querySelector('#v-channels .chn-grid') && document.querySelector('#v-channels .chn-grid').dataset.sub === 'scores' && document.querySelector('#chsBody')", 8000)
            ok(f"【{T}】{w} 切到子分頁 → 網址與高亮都換了", "#channels/scores" in pg.url and pg.evaluate("() => document.querySelector('#v-channels .chn-tabs a.on').dataset.sub") == "scores")
            # 摘要卡
            cards = pg.evaluate("() => [...document.querySelectorAll('.chs-card')].map(e => [e.querySelector('.l').textContent, e.querySelector('b').textContent, e.querySelector('em').textContent])")
            ok(f"【{T}】{w} 三張摘要卡：本週平均 90、上週平均 45、範本數 1", len(cards) == 3 and cards[0][:2] == ["本週平均", "90"] and cards[1][:2] == ["上週平均", "45"] and cards[2][:2] == ["範本數", "1"], cards)
            ok(f"【{T}】{w} 上週卡寫出進退步（本週比上週 ▲ +45）", "▲ +45" in cards[1][2], cards[1])
            if mob:
                ok(f"【{T}】{w} 手機表格預設收起（Andy 規矩 G1）", not pg.is_visible("#chsTable"))
                pg.click("#v-channels .chs-blk .chn-h h3"); pg.wait_for_timeout(250)
                ok(f"【{T}】{w} 點「每篇成績」標題展開", pg.is_visible("#chsTable"))
            # 表格第一筆
            rows = pg.evaluate("() => [...document.querySelectorAll('#chsTable tr.chs-r')].map(r => ({ch: r.dataset.ch, t: r.querySelector('.chs-ti').textContent, s: r.querySelector('.chs-sc b').textContent, tag: (r.querySelector('.chs-tag') || {}).textContent || '', cm: r.querySelector('.chs-cm').textContent}))")
            ok(f"【{T}】{w} 表格有第一筆（日期、標題、90 分「範本」、評語）", any(r["t"] == first["title"] and r["s"] == "90" and r["tag"] == "範本" and first["comment"] in r["cm"] for r in rows), rows)
            ok(f"【{T}】{w} <60 分那筆標「待改」、顯示尚未寫規則", any(r["s"] == "45" and r["tag"] == "待改" and "尚未寫規則" in r["cm"] for r in rows), rows)
            ok(f"【{T}】{w} 預設「全部」＝ {len(data) + 1} 列、日期新到舊", len(rows) == len(data) + 1 and rows[0]["s"] == "90", len(rows))
            ok(f"【{T}】{w} 連結空白時顯示「待補」不是壞連結", pg.evaluate("() => document.querySelectorAll('#chsTable .chs-lk a').length") == 0 and "待補" in pg.evaluate("() => document.querySelector('#chsTable .chs-lk').textContent"))
            # 頻道篩選：點「②」→ 列數真的變
            n_all = len(rows)
            pg.click("#v-channels .chs-seg button[data-ch='②']"); pg.wait_for_timeout(200)
            n2 = pg.evaluate("() => document.querySelectorAll('#chsTable tr.chs-r').length")
            only2 = pg.evaluate("() => [...document.querySelectorAll('#chsTable tr.chs-r')].every(r => r.dataset.ch === '②')")
            ok(f"【{T}】{w} 篩選「②」→ 列數 {n_all}→{n2} 且全是②", n2 == 1 and only2 and n2 < n_all, (n_all, n2))
            ok(f"【{T}】{w} 篩選鈕選中狀態與筆數標示跟著變", pg.evaluate("() => document.querySelector('.chs-seg button.on').dataset.ch") == "②" and pg.evaluate("() => document.querySelector('.chs-n').textContent") == "1 篇")
            pg.click("#v-channels .chs-seg button[data-ch='①']"); pg.wait_for_timeout(200)
            ok(f"【{T}】{w} 篩選「①」→ 1 列且為第一筆", pg.evaluate("() => [...document.querySelectorAll('#chsTable tr.chs-r .chs-ti')].map(e => e.textContent)") == [first["title"]])
            pg.click("#v-channels .chs-seg button[data-ch='全部']"); pg.wait_for_timeout(200)
            ok(f"【{T}】{w} 回「全部」→ 列數還原", pg.evaluate("() => document.querySelectorAll('#chsTable tr.chs-r').length") == n_all)
            # 離開再進來回預設
            pg.click("#v-channels .chs-seg button[data-ch='②']"); pg.click("#v-channels .chn-tabs a[data-sub=ch1]")
            wait_until(pg, "() => document.querySelector('#v-channels .chn-grid').dataset.sub === 'ch1'", 6000)
            pg.click("#v-channels .chn-tabs a[data-sub=scores]"); wait_until(pg, "() => document.querySelector('#chsBody')", 6000)
            ok(f"【{T}】{w} 離開再進來篩選回「全部」", pg.evaluate("() => document.querySelector('.chs-seg button.on').dataset.ch") == "全部")
            # 版面
            if mob:
                pg.click("#v-channels .chs-blk .chn-h h3"); pg.wait_for_timeout(200)
                pg.click("#v-channels .chs-blk .chn-h h3"); pg.wait_for_timeout(200)
            m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth - innerWidth, small: [...document.querySelectorAll('#v-channels *')].filter(e => !e.childElementCount && (e.textContent||'').trim() && e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 11).length, h: document.getElementById('v-channels').getBoundingClientRect().height })")
            ok(f"【{T}】{w} 無橫向捲軸、字級不小於 11px、整頁 ≤3 屏（{m['h']:.0f}px）", m["sw"] <= 1 and m["small"] == 0 and m["h"] <= (844 if mob else 900) * 3, m)
            if mob:
                pg.click("#v-channels .chs-blk .chn-h h3"); pg.wait_for_timeout(250)
                ok(f"【{T}】{w} 手機展開後表格是卡片式（欄名前綴、無表頭）", pg.evaluate("() => getComputedStyle(document.querySelector('#chsTable thead')).display") == "none" and pg.evaluate("() => getComputedStyle(document.querySelector('#chsTable tr.chs-r')).display") == "block")
            shots = os.environ.get("TW_CH_SHOTS")
            if shots:
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(pathlib.Path(shots) / f"scores_{w}.png"), full_page=True)
        except Exception as e:
            ok(f"【{T}】{w} 流程不出例外", False, repr(e)[:300])
        finally:
            c.close()
    # 非管理者：看不到入口、導回總覽、不畫成績
    for tag, vp, mob in [("桌機", {"width": 1440, "height": 900}, False), ("手機", {"width": 390, "height": 844}, True)]:
        c3 = b.new_context(viewport=vp, is_mobile=mob, has_touch=mob)
        c3.add_init_script("window.TW_CH_OVERRIDE=false;try{localStorage.setItem('tw.tour','done')}catch(e){};setTimeout(function(){window.dispatchEvent(new Event('tw:account'))},1000)")
        p3 = c3.new_page(); p3.on("pageerror", lambda e: errs.append(str(e)))
        p3.goto(base + "#channels/scores", wait_until="load"); wait_until(p3, "() => location.hash === '#overview'", 9000); p3.wait_for_timeout(300)
        ok(f"【{T}】非管理者（{tag}）：#channels/scores 被導回總覽", p3.evaluate("() => location.hash") == "#overview", p3.url)
        ok(f"【{T}】非管理者（{tag}）：沒畫成績表、也沒有側欄入口", p3.evaluate("() => document.querySelectorAll('#chsBody, .chs-card, .chs-t').length") == 0 and p3.evaluate("() => [...document.querySelectorAll('.l4subtab[data-parent=channels], .tab[data-view=channels]')].every(e => e.offsetParent === null)"))
        c3.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])


register("貼文成績表", lambda pg, b, base, code: t_channel_scores(b, base, code))
