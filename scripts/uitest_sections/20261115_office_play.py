# 驗收段落「辦公室互動小房間」：site/office/play.html（角色圖鑑與互動小房間）在各種視窗尺寸都真的畫得出 3D 畫面
# 事故（2026-11-15）：擁有者在 1550×700 進去只看到底色與按鈕。根因＝主迴圈第一幀的 rAF 時間戳比 last 早 → dt 為負 → 角色位置 NaN →
#   相機跟著 NaN → 整張 3D 都畫不出來；視窗比例會改變模組載入耗時，所以看起來像「只有某些尺寸才空白」（主控台沒有錯誤）。
# 驗法（不看元素存在，看像素）：把中央區塊截成圖、量化顏色後數有幾種；單色（只剩底色）＝空白＝失敗。
#   ① 直接開 ×（1280×600、1366×768、1550×700、1920×1080、手機 390×844）：中央畫面有多種顏色、角色位置不是 NaN
#   ② 從入口頁（index.html）真的點「角色圖鑑與互動小房間」進去，1550×700 也有畫面
#   ③ 模擬「第一幀時間戳比 last 早」：把 requestAnimationFrame 的時間戳全部減 500ms，仍有畫面（這就是修好前會空白的情形）
#   ④ 小房間真的能互動：點「大笑」表情鈕、角色表情真的變
#   ⑤ world.html（進辦公室）1550×700 也有畫面
# 只用 ok()／wait_until()／register()；函式名一律 _op_ 前綴。這支用 PIL 判像素（環境沒有就只看 PLAY.char 位置）。
# flake8: noqa

import io as _io

_OP_SIZES = [(1280, 600), (1366, 768), (1550, 700), (1920, 1080), (390, 844)]


def _op_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _op_colors(pg, frac=(0.2, 0.25, 0.8, 0.75)):
    """螢幕中央區塊量化後的顏色種數（單色＝空白）。"""
    try:
        from PIL import Image
    except Exception:
        return -1
    vp = pg.viewport_size
    x0, y0, x1, y1 = int(vp["width"] * frac[0]), int(vp["height"] * frac[1]), int(vp["width"] * frac[2]), int(vp["height"] * frac[3])
    im = Image.open(_io.BytesIO(pg.screenshot(clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}))).convert("RGB").resize((64, 40))
    return len({(r >> 3, g >> 3, b >> 3) for (r, g, b) in im.getdata()})


def _op_drawn(pg, what, timeout=60000):
    """等到中央畫面真的有圖（顏色種數 ≥ 30）。回傳最後一次的種數。"""
    n = 0

    def chk():
        nonlocal n
        n = _op_colors(pg)
        return n < 0 or n >= 30

    wait_until(pg, "() => true", 100)
    import time as _t
    t0 = _t.time()
    while (_t.time() - t0) * 1000 < timeout:
        if chk():
            return n
        pg.wait_for_timeout(600)
    return n


def _op_page(b, w, h, touch=False):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return c, pg


def _op_play(pg, b, base, code):
    root = _op_root(base)
    # ①直接開：每個尺寸
    for (w, h) in _OP_SIZES:
        c, p = _op_page(b, w, h, touch=(w < 500))
        try:
            p.goto(root + "/office/play.html?test=1", wait_until="domcontentloaded")
            n = _op_drawn(p, "play")
            pos = p.evaluate("() => { const P = window.PLAY; return P && P.char ? P.char.pos.toArray() : null }")
            ok(f"小房間 {w}×{h}：直接開，中央畫面有圖（顏色 {n} 種，不是單色）", n < 0 or n >= 30, f"顏色只有 {n} 種")
            ok(f"小房間 {w}×{h}：角色位置是有限數字（不是 NaN）", bool(pos) and all(v == v and abs(v) < 1e6 for v in pos), pos)
            ok(f"小房間 {w}×{h}：沒有頁面錯誤", not p.errs, p.errs[:2])
        finally:
            c.close()

    # ③第一幀時間戳比 last 早（修好前會空白）
    c, p = _op_page(b, 1550, 700)
    try:
        p.add_init_script("""(() => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = (f) => raf((t) => f(t - 500)); })();""")
        p.goto(root + "/office/play.html?test=1", wait_until="domcontentloaded")
        n = _op_drawn(p, "play")
        ok(f"小房間：rAF 時間戳比載入完成時間早 500ms，仍有畫面（顏色 {n} 種）", n < 0 or n >= 30, n)

        # ④互動：點「大笑」，表情真的變
        before = p.evaluate("() => window.PLAY.state().expr")
        p.get_by_role("button", name="大笑").click()
        p.wait_for_timeout(600)
        after = p.evaluate("() => window.PLAY.state().expr")
        ok(f"小房間：點「大笑」後角色表情真的變了（{before} → {after}）", before != after, (before, after))
    finally:
        c.close()

    # ②從入口頁點進去
    c, p = _op_page(b, 1550, 700)
    try:
        p.goto(root + "/office/index.html", wait_until="domcontentloaded")
        p.locator('a.door[href="play.html"]').first.click()
        p.wait_for_url("**/play.html*")
        n = _op_drawn(p, "play")
        ok(f"入口頁點「角色圖鑑與互動小房間」進去，1550×700 有畫面（顏色 {n} 種）", n < 0 or n >= 30, n)
    finally:
        c.close()

    # ⑤world.html
    c, p = _op_page(b, 1550, 700)
    try:
        p.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        got = wait_until(p, "() => window.__world && window.__world.ready", 90000)
        n = _op_drawn(p, "world") if got else 0
        ok(f"進辦公室 world.html 1550×700 有畫面（顏色 {n} 種）", got and (n < 0 or n >= 30), (got, n))
    finally:
        c.close()


register("辦公室互動小房間", lambda pg, b, base, code: _op_play(pg, b, base, code))
