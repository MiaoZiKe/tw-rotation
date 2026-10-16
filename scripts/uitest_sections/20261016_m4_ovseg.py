# 驗收段落「手機總覽分段圖1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（LINE 內建瀏覽器，訪客、淺色）：「首頁的資金圖 和 熱力圖都不見了 重大疏失」
#   總覽分段選「資金流向」整塊空白、直接接頁尾。Chromium 重現不出來；修法是防禦性的：
#   分段鈕一律叫最新一輪的切換函式、切段包 try/catch（出錯退回簡單顯示）、切完 450ms 自我檢查（選到的卡往上每層容器拿掉 mp-off、等著畫的圖現在畫）。
#   這段驗：三種身分 × 360／390／430 × 三個分段，選到的卡真的有高度、圖真的有畫布；再注入「切段中途丟錯」與「外層容器被殘留 mp-off」兩種故障，圖仍然出來。
OV_SEG_JS = """() => { const o = {}; for (const id of ['ovRotCard', 'ovFlowCard', 'ovHeatCard', 'ovThemeCard', 'ovBreadthCard']) {
    const e = document.getElementById(id); if (!e) { o[id] = null; continue; } const r = e.getBoundingClientRect();
    const cv = [...e.querySelectorAll('canvas,svg')].map(c => c.getBoundingClientRect()).filter(q => q.width > 50 && q.height > 50).length;
    o[id] = { h: Math.round(r.height), cv }; }
  o.on = ([...document.querySelectorAll('#v-overview > .mpager > button.on')][0] || {}).textContent || ''; return o; }"""
OV_SEG_WANT = {"大盤": ["ovBreadthCard"], "資金流向": ["ovRotCard", "ovFlowCard"], "熱度": ["ovHeatCard", "ovThemeCard"]}


def t_m4_ovseg_1016(b, base):
    T = "手機總覽分段圖1016"
    def check(pg, tag, seg):
        o = pg.evaluate(OV_SEG_JS)
        shown = OV_SEG_WANT[seg]
        good = o["on"].strip() == seg and all(o[k] and o[k]["h"] > 150 and o[k]["cv"] >= 1 for k in shown) \
            and all(o[k] and o[k]["h"] == 0 for s2, ks in OV_SEG_WANT.items() if s2 != seg for k in ks)
        ok(f"【{T}】{tag} 點「{seg}」→ {'、'.join(shown)} 有高度且有畫布、別段的卡藏起來", good, o)
    roles = ((None, None, "訪客"), ("member", None, "註冊會員"), ("member", "p799", "Plus"))
    for w in (360, 390, 430):
        for who, plan, nm in roles:
            if w != 390 and who is not None:
                continue                                    # 寬度掃描只用訪客；三種身分在 390 各一輪
            c, _, _ = _sub_ctx(b, who, width=w, plan=plan, touch=True)
            c.add_init_script("try { localStorage.setItem('tw.theme', 'light'); localStorage.setItem('tw.live.on', '0'); } catch (e) {}")
            pg = c.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            if not ok(f"【{T}】{w} {nm}：總覽分段列就緒", bool(wait_until(pg, "() => document.querySelectorAll('#v-overview > .mpager > button').length === 3", 25000))):
                c.close(); continue
            pg.wait_for_timeout(2500)
            for seg in ("資金流向", "熱度", "大盤", "資金流向"):
                pg.locator("#v-overview > .mpager > button", has_text=seg).first.tap(); pg.wait_for_timeout(1200)
                check(pg, f"{w} {nm}", seg)
            if who is None:
                # 故障注入①：切段中途丟錯（getComputedStyle 第一次被叫就丟）→ try/catch 退回簡單顯示，圖仍出來
                pg.locator("#v-overview > .mpager > button", has_text="大盤").first.tap(); pg.wait_for_timeout(800)
                # 只對 #ovLeft（.ovmain 裡的排版容器，切段時收空殼那一步會量它）丟一次 —— 丟在切段流程裡，不波及別的程式
                pg.evaluate("() => { const g = window.getComputedStyle; window.getComputedStyle = function (el) { if (el && el.id === 'ovLeft') { window.getComputedStyle = g; throw new Error('注入故障'); } return g.apply(this, arguments); }; }")
                pg.locator("#v-overview > .mpager > button", has_text="熱度").first.tap(); pg.wait_for_timeout(1200)
                check(pg, f"{w} {nm} 切段中途丟錯後", "熱度")
                ok(f"【{T}】{w} {nm}：注入的錯誤被切段流程接住（沒有漏成頁面錯誤）、而且真的有被觸發", "注入故障" not in " ".join(errs)
                   and pg.evaluate("() => window.getComputedStyle.toString().includes('[native code]')"), errs[:3])
                # 故障注入②：外層排版容器殘留 mp-off（上一段收掉的空殼沒被拿掉）→ 450ms 自我檢查補開
                pg.evaluate("() => { const b = [...document.querySelectorAll('#v-overview > .mpager > button')].find(x => x.textContent.trim() === '資金流向'); "
                            "b.click(); document.querySelector('#v-overview .ovmain').classList.add('mp-off'); }")
                pg.wait_for_timeout(1200)
                check(pg, f"{w} {nm} 外層容器殘留 mp-off 後", "資金流向")
            ok(f"【{T}】{w} {nm}：沒有 JS 錯誤", not errs, errs[:3])
            c.close()


# ★ 2026-10-16 Andy（LINE）：「首頁的資金圖 和 熱力圖都不見了」—— 三身分 × 三分段圖真的畫出來＋兩種故障注入後仍出來（360／390／430）
register("手機總覽分段圖1016", lambda pg, b, base, code: t_m4_ovseg_1016(b, base), after="精選文章分頁1016")
