# 驗收段落「搜尋框清除1101」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 搜尋框清除1101
# Andy 11-01 00:12：「全站搜尋清單也加清除鈕」。全站共用 site/searchclear.js 自動掛 ×。
# 逐頁：打字 → × 出現（桌機 ≥24px、手機 ≥32px）→ 按 × → 框空、焦點仍在框內、清單筆數恢復；Esc 也清空。

# (頁面名, hash, 輸入框 selector, 前置 JS（可空）, 量「清單筆數」的 JS, 要打的字)
_SC_TARGETS = [
    ("側欄代號搜尋", "#overview", "#q", "", "() => document.querySelectorAll('#sugg > *').length", "台積"),
    ("文章列表", "#articles", "#artQ", "", "() => [...document.querySelectorAll('#artList .artc, #artList > *, .artmain .artrow, .artmain article')].filter(e => e.offsetParent).length", "zzqq不存在"),
    ("自選頁加入股票", "#watch", "#wpQ", "", "() => document.querySelectorAll('#wpRes li').length", "台積"),
    ("大盤族群下拉內搜尋", "#market/ma", "#maGroupDD .sndd-q", "() => { const b = document.querySelector('#maGroupDD .ddbtn'); if (b) b.click(); }",
     "() => [...document.querySelectorAll('#maGroupDD .ddlist > *')].filter(e => e.offsetParent).length", "zzqq不存在"),
    ("ETF 成分股搜尋", "#stock/0050", ".hdq", "() => { const t=[...document.querySelectorAll('button,a,[role=tab]')].find(e=>/成分股/.test(e.textContent)&&e.offsetParent); if (t) t.click(); }",
     "() => [...document.querySelectorAll('.hdgrid tbody tr')].filter(r => !r.hidden && r.offsetParent).length", "zzqq不存在"),
]

_SC_STATE = """(sel) => { const i = [...document.querySelectorAll(sel)].find(e => e.offsetParent); if (!i) return null;
  const b = i.nextElementSibling; const r = b && b.classList.contains('scx') && !b.hidden ? b.getBoundingClientRect() : null;
  return { val: i.value, btn: !!r, w: r ? r.width : 0, h: r ? r.height : 0, focus: document.activeElement === i,
           pad: parseFloat(getComputedStyle(i).paddingRight) }; }"""


def t_searchclear_1101(b, base, code):
    T = "搜尋框清除1101"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_SCLEAR_SHOT")
    for W in (1440, 390):
        c = b.new_context(viewport={"width": W, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}: {e}"))
        J = lambda js, *a: pg.evaluate(js, *a)
        minpx = 32 if W < 641 else 24
        for name, hsh, sel, pre, cnt, txt in _SC_TARGETS:
            if W < 641 and name in ("側欄代號搜尋", "大盤族群下拉內搜尋"):
                continue    # 手機沒有側欄；手機的族群下拉是 mobile4 另一套面板，× 同樣由共用工具掛上（見 _preview 截圖）
            pg.goto(base + hsh, wait_until="networkidle")
            agree = pg.get_by_role("button", name="同意並繼續")
            if agree.count() and agree.first.is_visible():
                agree.first.click(); pg.wait_for_timeout(300)
            pg.wait_for_timeout(1200)
            if pre:
                J(pre); pg.wait_for_timeout(500)
            loc = pg.locator(sel + ":visible")
            if not loc.count():
                ok(f"{T}（{W}）{name}：找得到搜尋框", False, sel); continue
            n0 = J(cnt)
            s0 = J(_SC_STATE, sel)
            ok(f"{T}（{W}）{name}：沒打字時沒有 ×", s0 and not s0["btn"], s0)
            loc.first.click(); loc.first.fill(txt); loc.first.dispatch_event("input"); pg.wait_for_timeout(600)
            s1 = J(_SC_STATE, sel); n1 = J(cnt)
            ok(f"{T}（{W}）{name}：打字後 × 出現且 ≥{minpx}px、輸入框留出右側空間", bool(s1 and s1["btn"] and s1["w"] >= minpx - 0.5 and s1["h"] >= minpx - 0.5 and s1["pad"] >= 30), s1)
            if shot_dir:
                os.makedirs(shot_dir, exist_ok=True)
                pg.screenshot(path=f"{shot_dir}/{name}_{W}.png")
            pg.locator(sel + ":visible").first.locator("xpath=following-sibling::button[contains(@class,'scx')]").first.click(); pg.wait_for_timeout(600)
            s2 = J(_SC_STATE, sel); n2 = J(cnt)
            ok(f"{T}（{W}）{name}：按 × → 框空、× 消失、焦點仍在框內", bool(s2 and s2["val"] == "" and not s2["btn"] and s2["focus"]), s2)
            if name == "側欄代號搜尋":   # 這個框空著聚焦時本來就列「預設建議」，清除後應回到比篩選後多的預設清單
                ok(f"{T}（{W}）{name}：清除後建議清單回到預設（篩選後 {n1}／清除後 {n2}）", n2 > n1, [n0, n1, n2])
            else:
                ok(f"{T}（{W}）{name}：清單筆數恢復（原 {n0}／篩選後 {n1}／清除後 {n2}）", n2 == n0 and n1 != n0, [n0, n1, n2])
            # Esc 也清空
            loc = pg.locator(sel + ":visible"); loc.first.click(); loc.first.fill(txt); pg.wait_for_timeout(400)
            pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
            s3 = J(_SC_STATE, sel)
            ok(f"{T}（{W}）{name}：Esc 清空", bool(s3 and s3["val"] == ""), s3)
        c.close()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("搜尋框清除1101", lambda pg, b, base, code: t_searchclear_1101(b, base, code))
