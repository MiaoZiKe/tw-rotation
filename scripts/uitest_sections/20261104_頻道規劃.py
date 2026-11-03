# 驗收段落「頻道規劃」：#channels 母分頁（只給管理者）——管理者看得到並切子分頁內容真的變、非管理者看不到、手機收展
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

def t_channels_1104(b, base, code):
    T = "頻道規劃"
    errs = []
    shots = pathlib.Path(os.environ.get("TW_CH_SHOTS", "")) if os.environ.get("TW_CH_SHOTS") else None
    SUBS = [("overview", "總覽", "頻道清單"), ("ch1", "① 哩股哩股", "內容柱與比重"), ("ch2", "② 科技透明圈", "公司待遇行情"),
            ("ch3", "③ AI 介紹", "上班族的 AI 實戰"), ("funnel", "LINE＋Email", "漏斗流程"), ("review", "檢討指標", "沒達標怎麼調")]
    for w in (1440, 390):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob)
        c.add_init_script("window.TW_CH_OVERRIDE=true;try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        try:
            pg.goto(base + "#channels", wait_until="domcontentloaded")
            wait_until(pg, "() => document.querySelectorAll('#v-channels .chn-tabs a').length >= 6", 20000)
            ag = pg.get_by_role("button", name="同意並繼續")
            if ag.count():
                try: ag.first.click(timeout=1500)
                except Exception: pass
            ok(f"【{T}】{w} 管理者開 #channels：六個子分頁都在", pg.evaluate("() => document.querySelectorAll('#v-channels .chn-tabs a').length") == 6)
            if not mob:
                ok(f"【{T}】{w} 側欄看得到「頻道規劃」母項與六個子項", pg.evaluate("() => { const t = document.querySelector('.tab[data-view=channels]'); const s = [...document.querySelectorAll('.l4subtab[data-parent=channels]')]; return !!t && t.offsetParent !== null && s.length === 6 && s.every(e => e.offsetParent !== null); }"))
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
            for sid in ("ch1", "ch2", "ch3"):
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


register("頻道規劃", lambda pg, b, base, code: t_channels_1104(b, base, code))
