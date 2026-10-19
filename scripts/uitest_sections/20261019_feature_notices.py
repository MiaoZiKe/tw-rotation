# 驗收段落「功能公告1019」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_sub_ctx()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 功能公告1019
# Andy 10-19：「新增功能需要有通知給其他人」。site/notices/features.json（repo 內靜態「功能更新」）併進鈴鐺與 #notices。
# 全部用真的點擊，每一步量畫面真的變了：
#  ① 訪客、沒有 Worker（本機就是這個狀態）1440／390：鈴鐺出現、紅點數＝今天的功能公告數、下拉列得出每一則標題、類型「功能更新」
#  ② 點一則 → 那則展開（.ex）、紅點少 1、已讀寫進 localStorage tw.notice.read
#  ③ 重新整理 → 那則仍是已讀（紅點數不回來）
#  ④ 內文的站內連結（[文字](#路由)）是 <a href="#...">，點了真的換頁、下拉收起
#  ⑤ #notices 頁列得出全部、「全部標為已讀」→ 紅點消失
#  ⑥ 內容裡的 <script>／<img onerror> 被跳脫成文字、沒有執行；javascript: 不會變成連結
#  ⑦ 登入者：點功能公告 → 不送 /v1/notices/read（Worker 不認得 f- 開頭的 id），已讀照樣記在本機
#  全程沒有網頁錯誤、390 沒有橫向捲軸
import json as _fn_json

_FN_FILE = SITE / "notices" / "features.json"
_FN_ST = """() => { const d = document.getElementById('ntDot'), b = document.getElementById('ntBell');
  return { bell: !!b && b.getClientRects().length > 0, dot: d && !d.hidden ? d.textContent : '',
    read: (() => { try { return JSON.parse(localStorage.getItem('tw.notice.read') || '[]'); } catch (e) { return []; } })() }; }"""


def _fn_ctx(b, W, init_read=True):
    c = b.new_context(viewport={"width": W, "height": 900}, **({"has_touch": True, "is_mobile": True} if W <= 640 else {}))
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    return c


def _fn_agree(pg):
    a = pg.get_by_role("button", name="同意並繼續")
    if a.count() and a.first.is_visible():
        a.first.click(); pg.wait_for_timeout(300)


def t_feature_notices_1019(b, base, code):
    T = "功能公告1019"
    errs: list[str] = []
    shot_dir = os.environ.get("TW_NTF_SHOT")
    feats = _fn_json.loads(_FN_FILE.read_text(encoding="utf-8"))
    today = [f for f in feats if f.get("date") == "2026-10-19" and f.get("aud", "all") == "all"]
    pub = [f for f in feats if f.get("aud", "all") == "all"]
    ok(f"{T}：features.json 有今天（10-19）的功能公告 ≥ 5 則、每則 id 照 f-YYYYMMDD-slug、標題 ≤ 30 字、有日期與內容",
       len(today) >= 5 and all(re.match(r"^f-\d{8}-[a-z0-9-]+$", f["id"]) and len(f["title"]) <= 30 and f.get("body") and re.match(r"^\d{4}-\d\d-\d\d$", f["date"]) for f in feats)
       and len({f["id"] for f in feats}) == len(feats), [(f["id"], len(f["title"])) for f in feats])
    ok(f"{T}：公告內文沒有寫技術細節字眼（Claude／agent／commit／uitest）",
       not [f["id"] for f in feats if re.search(r"Claude|agent|commit|uitest|\.js\b|selDim", f["title"] + f["body"], re.I)])

    for W in (1440, 390):
        c = _fn_ctx(b, W)
        pg = c.new_page(); pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
        pg.goto(base + "#overview", wait_until="domcontentloaded"); _fn_agree(pg)
        n0 = len(pub)
        got = wait_until(pg, f"() => {{ const d = document.getElementById('ntDot'); return !!d && !d.hidden && d.textContent === '{n0}'; }}", 10000)
        st = pg.evaluate(_FN_ST)
        ok(f"{T}（{W}）① 訪客、沒有會員伺服器 → 鈴鐺看得到、紅點 {n0}", bool(got) and st["bell"], st)
        pg.click("#ntBell")
        wait_until(pg, f"() => {{ const d = document.getElementById('ntDrop'); return d && !d.hidden && d.querySelectorAll('.ntitem').length === {n0}; }}", 3000)
        txt = pg.inner_text("#ntDrop")
        miss = [f["title"] for f in today if f["title"] not in txt]
        ok(f"{T}（{W}）① 下拉列出 {n0} 則、今天每一則標題都在、類型「功能更新」", pg.locator("#ntDrop .ntitem").count() == n0 and not miss and "功能更新" in txt, miss or txt[:200])
        dd = pg.evaluate("() => { const r = document.getElementById('ntDrop').getBoundingClientRect(); return [r.left, r.right, innerWidth]; }")
        ok(f"{T}（{W}）① 下拉整個在畫面內", dd[0] >= 0 and dd[1] <= dd[2] + 0.5, dd)
        if shot_dir:
            pg.screenshot(path=os.path.join(shot_dir, f"ntf_drop_{W}.png"))
        # ② 點一則（第二則，避免剛好是置頂那一則）→ 展開、紅點 −1、localStorage
        fid = pg.evaluate("() => document.querySelectorAll('#ntDrop .ntitem')[1].dataset.id")
        h0 = pg.evaluate(f"() => document.querySelector(\"#ntDrop .ntitem[data-id='{fid}'] .bd\").getBoundingClientRect().height")
        pg.click(f"#ntDrop .ntitem[data-id='{fid}'] .ttl")
        got = wait_until(pg, f"() => document.getElementById('ntDot').textContent === '{n0 - 1}'", 3000)
        ex = pg.evaluate(f"() => {{ const e = document.querySelector(\"#ntDrop .ntitem[data-id='{fid}']\"); return {{ ex: e.classList.contains('ex'), unread: e.classList.contains('unread'), h: e.querySelector('.bd').getBoundingClientRect().height }}; }}")
        st = pg.evaluate(_FN_ST)
        ok(f"{T}（{W}）② 點「{fid}」→ 展開（內文高度 {h0:.0f} → {ex['h']:.0f}）、不再是未讀、紅點 {n0 - 1}、已讀記進 localStorage",
           bool(got) and ex["ex"] and not ex["unread"] and ex["h"] >= h0 and fid in st["read"], [ex, st])
        if shot_dir:
            pg.screenshot(path=os.path.join(shot_dir, f"ntf_expand_{W}.png"))
        # ③ 重新整理 → 仍已讀
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && !d.hidden; }", 10000); pg.wait_for_timeout(400)
        st = pg.evaluate(_FN_ST)
        ok(f"{T}（{W}）③ 重新整理 → 紅點仍是 {n0 - 1}（那則還是已讀）", st["dot"] == str(n0 - 1), st)
        # ④ 站內連結：找一則有 #路由 連結的，展開後點連結 → 換頁、下拉收起、那則標已讀
        pg.click("#ntBell")
        wait_until(pg, "() => !document.getElementById('ntDrop').hidden", 3000)
        lk = pg.evaluate("""() => { const a = [...document.querySelectorAll('#ntDrop .ntitem .bd a.ntin')].find(x => /^#/.test(x.getAttribute('href')) && x.getAttribute('href') !== location.hash);
          return a ? { id: a.closest('.ntitem').dataset.id, href: a.getAttribute('href'), tx: a.textContent } : null; }""")
        ok(f"{T}（{W}）④ 內文的站內路由變成連結（顯示文字、href 是 #路由）", bool(lk) and not lk["tx"].startswith("#"), lk)
        if lk:
            pg.click(f"#ntDrop .ntitem[data-id='{lk['id']}'] .ttl"); pg.wait_for_timeout(200)   # 先展開（兩行截斷時連結可能被藏住）
            pg.locator(f"#ntDrop .ntitem[data-id='{lk['id']}'] .bd a.ntin[href='{lk['href']}']").first.click()
            moved = wait_until(pg, f"() => location.hash.startsWith('{lk['href']}')", 4000)
            shut = pg.evaluate("() => { const d = document.getElementById('ntDrop'); return !d || d.hidden; }")
            ok(f"{T}（{W}）④ 點「{lk['tx']}」→ 換到 {lk['href']}、下拉收起、那則已讀", bool(moved) and shut and lk["id"] in pg.evaluate(_FN_ST)["read"], pg.evaluate("() => location.hash"))
        # ⑤ #notices 頁：全部列出、站內連結可點、全部標為已讀
        pg.goto(base + "#notices", wait_until="domcontentloaded")
        got = wait_until(pg, f"() => document.querySelectorAll('#v-notices .npi[data-id]').length === {n0}", 8000)
        ptxt = pg.inner_text("#v-notices") if got else ""
        ok(f"{T}（{W}）⑤ #notices 列出 {n0} 則、今天每一則都在", bool(got) and all(f["title"] in ptxt for f in today), ptxt[:200])
        if shot_dir:
            pg.wait_for_timeout(700)   # 換頁有淡入動畫，等它走完再截
            pg.screenshot(path=os.path.join(shot_dir, f"ntf_page_{W}.png"), full_page=False)
        if W <= 640:
            nox = pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
            ok(f"{T}（{W}）⑤ #notices 沒有橫向捲軸", nox, pg.evaluate("() => [document.documentElement.scrollWidth, innerWidth]"))
        pg.click("#npReadAll")
        ok(f"{T}（{W}）⑤ 「全部標為已讀」→ 紅點消失、頁面不再有未讀框",
           bool(wait_until(pg, "() => document.getElementById('ntDot').hidden && !document.querySelector('#v-notices .npi.unread')", 3000)))
        pl = pg.evaluate("() => { const a = document.querySelector('#v-notices .npi .bd a.ntin'); return a ? a.getAttribute('href') : ''; }")
        if pl:
            pg.locator(f"#v-notices .npi .bd a.ntin[href='{pl}']").first.click()
            ok(f"{T}（{W}）⑤ 公告頁內文連結點了 → 換到 {pl}", bool(wait_until(pg, f"() => location.hash.startsWith('{pl}')", 4000)), pg.evaluate("() => location.hash"))
        c.close()

    # ⑥ 跳脫：塞一份惡意內容的 features.json
    c = _fn_ctx(b, 1440)
    bad = [{"id": "f-20991231-xss", "date": "2099-12-31", "title": "<img src=x onerror=window.__xss=1>測試", "body": "<script>window.__xss=2</script>\n[去資金流向](#flow) javascript:alert(1) [壞](javascript:alert(1)) #market"},
           {"id": "bad id 不收", "date": "2026-10-19", "title": "格式不對", "body": "x"}]
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_fn_json.dumps(bad)))
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"xss: {e}"))
    pg.goto(base + "#overview", wait_until="domcontentloaded"); _fn_agree(pg)
    wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && d.textContent === '1'; }", 10000)
    pg.click("#ntBell"); wait_until(pg, "() => !document.getElementById('ntDrop').hidden", 3000)
    pg.click("#ntDrop .ntitem[data-id='f-20991231-xss'] .ttl"); pg.wait_for_timeout(300)
    x = pg.evaluate("""() => { const it = document.querySelector("#ntDrop .ntitem[data-id='f-20991231-xss']");
      return { n: document.querySelectorAll('#ntDrop .ntitem').length, xss: window.__xss || 0, script: !!it.querySelector('script, img'), txt: it.innerText,
        links: [...it.querySelectorAll('a')].map(a => a.getAttribute('href')) }; }""")
    ok(f"{T} ⑥ 格式不對的 id 不收（只剩 1 則）", x["n"] == 1, x)
    ok(f"{T} ⑥ 標題與內文的 <img onerror>／<script> 變成文字、沒有執行", x["xss"] == 0 and not x["script"] and "<script>" in x["txt"] and "<img" in x["txt"], x)
    ok(f"{T} ⑥ 連結只有站內 #flow、#market；javascript: 沒有變成連結", sorted(x["links"]) == ["#flow", "#market"], x["links"])
    c.close()

    # ⑦ 登入者（假 Worker）：點功能公告不送 /v1/notices/read，本機照樣記已讀
    c, sent, _st = _sub_ctx(b, "member")
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_FN_FILE.read_text(encoding="utf-8")))
    c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"member: {e}"))
    pg.goto(base + "#overview", wait_until="domcontentloaded"); _fn_agree(pg)
    nm = len([f for f in feats if f.get("aud", "all") in ("all", "member")])
    got = wait_until(pg, f"() => {{ const d = document.getElementById('ntDot'); return !!d && d.textContent === '{nm}'; }}", 10000)
    ok(f"{T} ⑦ 登入者也看得到功能公告（紅點 {nm}）", bool(got), pg.evaluate(_FN_ST))
    pg.click("#ntBell"); wait_until(pg, "() => !document.getElementById('ntDrop').hidden", 3000)
    fid = pg.evaluate("() => document.querySelector('#ntDrop .ntitem').dataset.id")
    pg.click(f"#ntDrop .ntitem[data-id='{fid}'] .ttl")
    got = wait_until(pg, f"() => document.getElementById('ntDot').textContent === '{nm - 1}'", 3000)
    pg.wait_for_timeout(500)
    ok(f"{T} ⑦ 登入者點「{fid}」→ 紅點 {nm - 1}、沒有送 /v1/notices/read、已讀記在本機",
       bool(got) and not any(s[0] == "/v1/notices/read" for s in sent) and fid in pg.evaluate(_FN_ST)["read"], [s[0] for s in sent])
    c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("功能公告1019", lambda pg, b, base, code: t_feature_notices_1019(b, base, code))
