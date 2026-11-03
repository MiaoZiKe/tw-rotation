# 驗收段落「頻道規劃」—— Andy 11-04：「幫我在我那網頁新增頻道規劃 母分頁 方便我管理 觀看」。
# 管理者限定（#channels）：非管理者導回 #overview；管理者看得到三張頻道卡、週曆、分頁籤，點了內容真的換。
# 本機 127.0.0.1 用 window.TW_LAB_OVERRIDE（true／false）模擬管理者／一般人（與流向驗證同一個覆寫）。
# flake8: noqa

def t_channels(b, base):
    import json as _json
    T = "頻道規劃"
    plan = _json.loads((SITE / "channels" / "plan.json").read_text(encoding="utf-8"))
    chs = plan["channels"]

    def open_page(W, H, adm, h="#overview"):
        kw = {"viewport": {"width": W, "height": H}, "timezone_id": "Asia/Taipei"}
        if W < 641:
            kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        ctx = b.new_context(**kw)
        ctx.add_init_script(f"window.TW_LAB_OVERRIDE={'true' if adm else 'false'};try{{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}}catch(e){{}}")
        ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fails.append(f"{T} pageerror: {str(e)[:160]}"))
        pg.goto(base + h, wait_until="load")
        agree = pg.get_by_role("button", name="同意並繼續")
        if agree.count() and agree.first.is_visible():
            agree.first.click()
        pg.wait_for_timeout(1500)
        return ctx, pg

    TAB = "() => { const t = document.querySelector('.tab[data-view=channels]'); return !!t && t.getBoundingClientRect().width > 0 && getComputedStyle(t).display !== 'none'; }"
    # 一般人：側欄沒有；直接開網址導回總覽
    ctx, pg = open_page(1440, 900, False)
    ok(f"[{T}] 一般人：沒有 ch-adm、側欄看不到「頻道規劃」", (not pg.evaluate("() => document.documentElement.classList.contains('ch-adm')")) and not pg.evaluate(TAB))
    pg.evaluate("() => { location.hash = '#channels'; }"); pg.wait_for_timeout(500)
    pg.evaluate("() => window.dispatchEvent(new Event('tw:account'))"); pg.wait_for_timeout(1500)
    ok(f"[{T}] 一般人：開 #channels 被導回 #overview、沒畫內容", pg.evaluate("() => location.hash") == "#overview" and pg.evaluate("() => document.querySelectorAll('.chn-card').length") == 0, pg.evaluate("() => location.hash"))
    ctx.close()
    ctx, pg = open_page(390, 844, False)
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 一般人：手機抽屜沒有「頻道規劃」", pg.evaluate("() => ![...document.querySelectorAll('#m4Drawer *')].some(e => e.dataset && e.dataset.v === 'channels')"))
    ctx.close()

    # 管理者桌機
    ctx, pg = open_page(1440, 900, True)
    ok(f"[{T}] 站主：有 ch-adm、側欄看得到「頻道規劃」", pg.evaluate("() => document.documentElement.classList.contains('ch-adm')") and pg.evaluate(TAB))
    pg.evaluate("() => { location.hash = '#channels'; }"); wait_until(pg, "() => document.querySelectorAll('.chn-card').length >= 3", 15000); pg.wait_for_timeout(400)
    ok(f"[{T}] 站主：總覽有 {len(chs)} 張頻道卡，名稱對得上 JSON", pg.evaluate("() => [...document.querySelectorAll('.chn-card .chn-nm')].map(e => e.textContent)") == [c["name"] for c in chs])
    # 週曆格數＝JSON 排程裡「有星期＋有時間」的列（同格多筆合併成多個小標）
    import re as _re
    n_json = sum(1 for c in chs for w in c["posting"]["weekly"] if _re.match(r"^週[一二三四五六日]", w["day"]) and _re.match(r"^\d{1,2}:\d{2}", w["time"]))
    n_flex = sum(1 for c in chs for w in c["posting"]["weekly"] if not (_re.match(r"^週[一二三四五六日]", w["day"]) and _re.match(r"^\d{1,2}:\d{2}", w["time"])))
    n_chip = pg.evaluate("() => document.querySelectorAll('.chn-cal .chn-chip').length")
    ok(f"[{T}] 週曆小標數 {n_chip} ＝ JSON 有星期有時間的排程 {n_json}", n_chip == n_json, f"{n_chip} vs {n_json}")
    ok(f"[{T}] 機動（不限時段）{n_flex} 筆另列在週曆下", pg.evaluate("() => document.querySelectorAll('.chn-flex .chn-chip').length") == n_flex)
    # 頻道三 週一 21:00 與頻道一 20:30 相隔 30 分 → 兩格都標紅框
    clash = pg.evaluate("() => [...document.querySelectorAll('.chn-cr .cell.clash')].map(e => e.dataset.day + ' ' + e.dataset.tm)")
    ok(f"[{T}] 週一 20:30（頻道①）與 21:00（頻道③）相鄰：兩格都標撞時段", "週一 20:30" in clash and "週一 21:00" in clash, str(clash))
    ok(f"[{T}] 缺漏清單預設收起、點開看得到 {len(plan.get('gaps', []))} 項", pg.evaluate("() => !document.getElementById('chnGaps').open") and (pg.evaluate("() => { document.querySelector('#chnGaps summary').click(); return document.querySelectorAll('#chnGaps .chn-gr').length; }") == len(plan.get("gaps", []))))
    # 點頻道卡 → 子頁內容換成該頻道
    for c in chs:
        pg.evaluate("() => { location.hash = '#channels'; }"); wait_until(pg, "() => document.querySelectorAll('.chn-card').length >= 3", 8000)
        pg.click(f".chn-card[data-ch={c['id']}]"); wait_until(pg, f"() => location.hash.indexOf('#channels/{c['id']}') === 0 && document.querySelector('.chn-subhd .chn-nm')", 8000); pg.wait_for_timeout(300)
        nm = pg.evaluate("() => document.querySelector('.chn-subhd .chn-nm').textContent")
        ok(f"[{T}] 點頻道卡 {c['id']}：子頁標題換成「{c['name']}」", nm == c["name"], nm)
        ok(f"[{T}] {c['id']}：主題方向分頁甜甜圈畫出來、主題 {len(c['topics'])} 列", pg.evaluate("() => !!document.querySelector('.chn-dnc canvas, .chn-dnc svg')") and pg.evaluate("() => document.querySelectorAll('.chn-tl li').length") == len(c["topics"]))
    # 分頁籤切換：內容真的換
    seen = {}
    for tid in ["topics", "plan", "goals", "run", "post", "team", "kpi", "docs"]:
        pg.click(f".chn-tabs a[data-tab={tid}]"); pg.wait_for_timeout(250)
        seen[tid] = pg.evaluate("() => document.getElementById('chnBody').innerText.length")
        ok(f"[{T}] 分頁「{tid}」：網址、選中鈕、內容區標記都跟著換", pg.evaluate("(t) => location.hash.endsWith('/' + t) && document.querySelector('.chn-tabs a.on').dataset.tab === t && document.getElementById('chnBody').dataset.tab === t", tid) and seen[tid] > 20, str(seen[tid]))
    ok(f"[{T}] 八個分頁的內容彼此不同（不是同一份）", len(set(seen.values())) >= 6, str(seen))
    # 發文方式：排程表列數＝JSON
    c3 = chs[-1]
    pg.click(".chn-tabs a[data-tab=post]"); pg.wait_for_timeout(250)
    ok(f"[{T}] 發文方式：排程表 {len(c3['posting']['weekly'])} 列對得上 JSON", pg.evaluate("() => document.querySelectorAll('#chnPostTb tbody tr').length") == len(c3["posting"]["weekly"]))
    # 文件分頁：連結指向 GitHub
    pg.click(".chn-tabs a[data-tab=docs]"); pg.wait_for_timeout(250)
    ok(f"[{T}] 文件分頁：連結都指向 github.com/MiaoZiKe/tw-rotation", pg.evaluate("() => { const a = [...document.querySelectorAll('.chn-docs a')]; return a.length > 0 && a.every(x => x.href.indexOf('https://github.com/MiaoZiKe/tw-rotation/blob/main/') === 0); }"))
    # 子頁切其他頻道（右上圓鈕）
    pg.click(".chn-sw a"); pg.wait_for_timeout(500)
    ok(f"[{T}] 右上圓鈕切到另一個頻道、停留在同一分頁", pg.evaluate("() => document.querySelector('.chn-subhd .chn-nm').textContent") != c3["name"] and pg.evaluate("() => document.querySelector('.chn-tabs a.on').dataset.tab") == "docs")
    # 「?」說明
    pg.evaluate("() => { location.hash = '#channels'; }"); wait_until(pg, "() => document.querySelectorAll('.chn-card').length >= 3", 8000)
    pg.click(".chn-q"); ok(f"[{T}] 「?」點開有說明、再點背景關閉", not pg.evaluate("() => document.querySelector('.chn-pop').hidden")); pg.mouse.click(700, 5); pg.wait_for_timeout(200)
    ok(f"[{T}] 「?」點背景後關閉", pg.evaluate("() => document.querySelector('.chn-pop').hidden"))
    # 桌機無重疊／溢出
    ov = pg.evaluate("""() => { const r = document.querySelector('#v-channels'); const bad = [];
      r.querySelectorAll('.chn-card, .chn-sec, .chn-cal').forEach(e => { if (e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).overflowX === 'visible') bad.push(e.className); });
      const cs = [...document.querySelectorAll('.chn-card')].map(e => e.getBoundingClientRect());
      for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) { const a = cs[i], b = cs[j]; if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) bad.push('card重疊'); }
      return bad; }""")
    ok(f"[{T}] 桌機 1440：卡片與週曆沒有溢出或互相重疊", not ov, str(ov))
    ctx.close()

    # 管理者手機 390
    ctx, pg = open_page(390, 844, True)
    pg.evaluate("() => document.getElementById('m4Burger') && document.getElementById('m4Burger').click()"); pg.wait_for_timeout(700)
    ok(f"[{T}] 站主：手機抽屜有「頻道規劃」", pg.evaluate("() => [...document.querySelectorAll('#m4Drawer [data-v], .m4item')].some(e => e.dataset.v === 'channels')"))
    pg.evaluate("() => { location.hash = '#channels'; }"); wait_until(pg, "() => document.querySelectorAll('.chn-card').length >= 3", 15000); pg.wait_for_timeout(500)
    m = pg.evaluate("""() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, h: document.getElementById('v-channels').getBoundingClientRect().height, vh: innerHeight,
      small: [...document.querySelectorAll('#v-channels *')].filter(e => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11 && e.getBoundingClientRect().width > 0).map(e => e.className + ':' + getComputedStyle(e).fontSize).slice(0, 5) })""")
    ok(f"[{T}] 手機 390：總覽沒有橫向捲軸", m["sw"] <= m["cw"] + 1, str(m))
    ok(f"[{T}] 手機 390：總覽 ≤ 3 屏（{m['h']:.0f}px / 屏高 {m['vh']}）", m["h"] <= m["vh"] * 3, str(m["h"]))
    ok(f"[{T}] 手機 390：沒有小於 11px 的字", not m["small"], str(m["small"]))
    pg.click(".chn-card[data-ch=ch1]"); wait_until(pg, "() => document.querySelector('.chn-subhd')", 8000); pg.wait_for_timeout(400)
    for tid in ["topics", "post"]:
        pg.click(f".chn-tabs a[data-tab={tid}]"); pg.wait_for_timeout(300)
        m = pg.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, h: document.getElementById('v-channels').getBoundingClientRect().height, vh: innerHeight })")
        ok(f"[{T}] 手機 390 子頁「{tid}」：無橫向捲軸、≤ 3 屏", m["sw"] <= m["cw"] + 1 and m["h"] <= m["vh"] * 3, str(m))
    ctx.close()


register("頻道規劃", lambda pg, b, base, code: t_channels(b, base))
