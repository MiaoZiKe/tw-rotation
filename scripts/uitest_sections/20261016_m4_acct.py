# 驗收段落「手機帳號選單登入框1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 Andy（iPhone）：「右上角打開的畫面太大 需要調整適當大小，條窄一點」＋「登入帳號 不能看不到全部，用拉霸進行調整」
#   ① 手機帳號選單：寬 300～320、靠右（右緣離視窗 ≤ 12）、左邊露出頁面、版面風格分段不溢出、字級 ≥ 12；
#   ② 登入告知框：框在視窗內、內容框內可用手指上下捲（scrollTop 真的變）、捲到頂與捲到底「用 Google 帳號登入」都看得到也點得到（elementFromPoint）；
#   ③ 桌機 1440：同一個告知框維持原樣（按鈕列不是 sticky、框內距 18／20）—— 點了才出現的狀態，桌機守門涵蓋不到，這裡另外驗。
ACCT_MENU_JS = """() => { const m = document.querySelector('.acctmenu.m4am'); if (!m || m.hidden) return null; const r = m.getBoundingClientRect();
  const seg = m.querySelector('.m4seg4');
  const fs = Math.min(...[...m.querySelectorAll('*')].filter(e => e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize)));
  return { l: Math.round(r.left), r: Math.round(r.right), w: Math.round(r.width), W: innerWidth, segOver: seg ? seg.scrollWidth - seg.clientWidth : 0,
           segIn: seg ? seg.getBoundingClientRect().right <= r.right : true, minfs: fs }; }"""
ACCT_DLG_JS = """() => { const b = document.querySelector('#acctDlg .box'), g = document.getElementById('acctGo'); if (!b || !g) return null;
  const r = b.getBoundingClientRect(), q = g.getBoundingClientRect(); const h = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);
  return { top: Math.round(r.top), bot: Math.round(r.bottom), H: innerHeight, sh: b.scrollHeight, ch: b.clientHeight, st: Math.round(b.scrollTop),
           goBot: Math.round(q.bottom), goHit: !!h && (h === g || g.contains(h)), goLines: Math.round(q.height) }; }"""


def t_m4_acct_1016(b, base):
    T = "手機帳號選單登入框1016"
    for w, hgt in ((360, 640), (390, 664), (430, 740)):
        for who in (None, "member"):
            c, _, _ = _sub_ctx(b, who, width=w, touch=True)
            pg = c.new_page(); pg.set_viewport_size({"width": w, "height": hgt})
            pg.goto(base + "#overview", wait_until="domcontentloaded")
            if not ok(f"【{T}】{w} {who or '訪客'}：頂欄帳號鈕就緒", bool(wait_until(pg, "() => document.documentElement.classList.contains('m4') && !!document.getElementById('acctBtn')", 20000))):
                c.close(); continue
            pg.wait_for_timeout(1500)
            pg.locator("#acctBtn").tap()
            m = wait_until(pg, ACCT_MENU_JS, 3000)
            ok(f"【{T}】{w} {who or '訪客'}：帳號選單寬 300～320、靠右、左邊露出頁面", bool(m) and 300 <= m["w"] <= 320 and m["W"] - m["r"] <= 12 and m["l"] >= 28, m)
            ok(f"【{T}】{w} {who or '訪客'}：版面風格分段放得下（不溢出、在選單內）、字級 ≥ 12", bool(m) and m["segOver"] <= 0 and m["segIn"] and m["minfs"] >= 12, m)
            if who is None:
                pg.locator(".acctmenu.m4am .m4login").first.tap()
                d = wait_until(pg, ACCT_DLG_JS, 3000); pg.wait_for_timeout(300); d = pg.evaluate(ACCT_DLG_JS)
                ok(f"【{T}】{w}×{hgt}：登入告知框在視窗內、內容比框高（要捲）", bool(d) and d["top"] >= 0 and d["bot"] <= d["H"] and d["sh"] > d["ch"] + 20, d)
                pg.evaluate("() => { document.querySelector('#acctDlg .box').scrollTop = 0; }"); pg.wait_for_timeout(150)
                d0 = pg.evaluate(ACCT_DLG_JS)
                ok(f"【{T}】{w}×{hgt}：捲在最上面時「用 Google 帳號登入」就看得到、點得到、一行", d0["st"] == 0 and d0["goBot"] <= d0["H"] and d0["goHit"] and d0["goLines"] <= 50, d0)
                # 真的用手指在框裡往上推 300px
                cdp = c.new_cdp_session(pg)
                tp = lambda t, y: cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": [] if t == "touchEnd" else [{"x": w // 2, "y": y, "id": 1}]})
                y0 = int(hgt * 0.6); tp("touchStart", y0)
                for i in range(1, 11):
                    tp("touchMove", y0 - 30 * i)
                tp("touchEnd", 0); pg.wait_for_timeout(600)
                d1 = pg.evaluate(ACCT_DLG_JS)
                ok(f"【{T}】{w}×{hgt}：手指在框裡往上推 → 內容真的捲了（scrollTop {d1['st']}）、整頁沒被帶著捲", d1["st"] > 40 and pg.evaluate("() => scrollY") == 0, d1)
                ok(f"【{T}】{w}×{hgt}：捲動後「用 Google 帳號登入」仍看得到、點得到", d1["goBot"] <= d1["H"] and d1["goHit"], d1)
                pg.locator("#acctDlg [data-close]", has_text="取消").first.tap(); pg.wait_for_timeout(300)
                ok(f"【{T}】{w}：按「取消」→ 告知框關掉", pg.evaluate("() => document.getElementById('acctDlg').hidden"))
            c.close()
    # 桌機 1440：告知框維持原樣
    c, _, _ = _sub_ctx(b, None, width=1440)
    pg = c.new_page(); pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!document.getElementById('acctBtn')", 20000); pg.wait_for_timeout(1500)
    pg.locator("#acctBtn").click()                 # 桌機訪客點帳號鈕＝直接開告知框（account.js）
    wait_until(pg, "() => !!document.querySelector('#acctDlg:not([hidden]) .box')", 4000); pg.wait_for_timeout(300)
    st = pg.evaluate("() => { const b = document.querySelector('#acctDlg .box'), r2 = document.querySelector('#acctDlg .row2'); if (!b) return null; const cs = getComputedStyle(b);"
                     " return { pad: cs.paddingTop + ' ' + cs.paddingRight + ' ' + cs.paddingBottom, pos: getComputedStyle(r2).position, w: Math.round(b.getBoundingClientRect().width) }; }")
    ok(f"【{T}】1440：桌機登入告知框維持原樣（內距 18／20、按鈕列不黏底、寬 520）", bool(st) and st["pad"] == "18px 20px 18px" and st["pos"] == "static" and st["w"] == 520, st)
    c.close()


# ★ 2026-10-16 Andy（iPhone）：帳號選單「條窄一點」＋登入告知框「不能看不到全部，用拉霸」—— 選單寬 300～320 靠右；告知框框內手指捲、登入鈕永遠看得到；1440 告知框不變
register("手機帳號選單登入框1016", lambda pg, b, base, code: t_m4_acct_1016(b, base), after="手機總覽分段圖1016")
