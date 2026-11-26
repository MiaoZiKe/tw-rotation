# 驗收段落「文章上中下游1126」（site/articles.js：上中下游分類鈕）
# 由 _uitest.py 用 exec 載入：ok()、wait_until() 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 11-26：「並且要幫我類別分類 例如半導體上 中下游等等 其他」
# 真的操作：桌機 1440 點各分類 → 篇數與卡片真的改變、每張卡都是那一類；點「全部」回復；手機鈕列可橫向拖。
import json as _st_json
import os as _st_os

_ST_SHOT = _st_os.environ.get("TW_SHOT_DIR", "/tmp/claude-0/-home-user/d68c9f33-7cf0-5a76-b297-0eb800ee0511/scratchpad/shots")


def t_art_stage_1126(b, base, code):
    T = "文章上中下游1126"
    errs = []
    _st_os.makedirs(_ST_SHOT, exist_ok=True)
    idx = _st_json.load(open(str(SITE / "articles" / "index.json"), encoding="utf-8"))["articles"]
    stage = {a["id"]: a.get("chain_stage") or "other" for a in idx}
    for W in (1440, 390):
        mob = W <= 640
        c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}:{e}"))
        pg.goto(base + "#articles", wait_until="domcontentloaded")
        try:
            ag = pg.get_by_role("button", name="同意並繼續"); ag.first.wait_for(timeout=2500); ag.first.click(timeout=1500)
        except Exception: pass
        wait_until(pg, "() => document.querySelectorAll('#artStage button').length === 6 && document.querySelector('#artList .artc')", 20000)
        pg.wait_for_timeout(800)
        # 日期區間放寬，所有文章都進來
        pg.fill("#artFrom", "2020-01-01"); pg.dispatch_event("#artFrom", "change"); pg.wait_for_timeout(400)
        ids = lambda: pg.evaluate("() => [...document.querySelectorAll('#artList .artc')].map(a => a.dataset.id)")
        all_ids = ids()
        labels = pg.evaluate("() => [...document.querySelectorAll('#artStage button')].map(b => b.textContent.trim())")
        ok(f"[{T}（{W}）] 分類鈕＝全部／半導體上游／半導體中游／半導體下游／AI 伺服器與應用／其他", labels == ["全部", "半導體上游", "半導體中游", "半導體下游", "AI 伺服器與應用", "其他"], labels)
        for k in ("up", "mid", "down", "ai", "other"):
            pg.click(f"#artStage button[data-stage={k}]"); pg.wait_for_timeout(300)
            got = ids()
            want = [i for i in all_ids if stage.get(i, "other") == k]
            ok(f"★ [{T}（{W}）] 點「{k}」→ 卡片只剩 {len(want)} 篇且都是這一類、按鈕亮起", sorted(got) == sorted(want) and len(got) < len(all_ids)
               and pg.evaluate(f"() => document.querySelector('#artStage button[data-stage={k}]').classList.contains('on')"), [len(got), len(want)])
            if k == "up" and W == 1440:
                pg.screenshot(path=f"{_ST_SHOT}/stage_up_1440.png", full_page=True)
        pg.click("#artStage button[data-stage=all]"); pg.wait_for_timeout(300)
        ok(f"★ [{T}（{W}）] 點「全部」→ 回到 {len(all_ids)} 篇", len(ids()) == len(all_ids), len(ids()))
        # 11-26 分組：每組標題＋篇數，預設收起、點標題展開、再點收起
        g = pg.evaluate("() => [...document.querySelectorAll('#artList .artstg')].map(x => [x.dataset.stage, x.querySelector('.artgrid').hidden, +x.querySelector('em').textContent.replace(/\\D/g, ''), x.querySelectorAll('.artc').length])")
        ok(f"★ [{T}（{W}）] 清單依上中下游分組、每組篇數對、超過一組時預設收起", len(g) >= 2 and all(x[2] == x[3] for x in g) and all(x[1] for x in g), g)
        k0 = g[0][0]
        pg.click(f"#artList .artstg[data-stage={k0}] .artsech"); pg.wait_for_timeout(200)
        op = pg.evaluate(f"() => !document.querySelector('#artList .artstg[data-stage={k0}] .artgrid').hidden && JSON.parse(localStorage.getItem('tw.art.stgfold') || '{{}}')['{k0}'] === 1")
        pg.click(f"#artList .artstg[data-stage={k0}] .artsech"); pg.wait_for_timeout(200)
        cl = pg.evaluate(f"() => document.querySelector('#artList .artstg[data-stage={k0}] .artgrid').hidden")
        ok(f"★ [{T}（{W}）] 點組標題 → 展開並記住、再點 → 收起", op and cl, [op, cl])
        if W == 1440:
            pg.screenshot(path=f"{_ST_SHOT}/stage_groups_guest_1440.png", full_page=True)
        # 族群選項只算目前分頁
        pg.click("#artCats>button[data-cat=know]"); pg.wait_for_timeout(400)
        pg.fill("#artFrom", "2020-01-01"); pg.dispatch_event("#artFrom", "change"); pg.wait_for_timeout(300)
        know = [a for a in idx if a["cat"] == "know"]
        want = sorted({gg["id"] for a in know for gg in (a.get("groups") or [])})
        pg.click("#artGrp .twms-btn"); pg.wait_for_timeout(300)
        got = pg.evaluate("() => [...document.querySelectorAll('.twms-pan[data-ms=artGroups] input[data-v]')].map(i => i.dataset.v).sort()")
        ok(f"★ [{T}（{W}）] 族群下拉只列目前分頁（比比知識）有的族群", got == want, [len(got), len(want), [x for x in got if x not in want][:3]])
        pg.keyboard.press("Escape")
        if mob:
            m = pg.evaluate("() => { const s = document.getElementById('artStage'); return { ox: getComputedStyle(s).overflowX, sw: s.scrollWidth, cw: s.clientWidth, page: document.documentElement.scrollWidth - innerWidth } }")
            ok(f"[{T}（{W}）] 手機分類鈕一列、可橫向拖、頁面不橫向捲", m["ox"] == "auto" and m["page"] <= 0, m)
        c.close()
    ok(f"[{T}] 沒有 JS 錯誤", not errs, errs[:3])


register("文章上中下游1126", lambda pg, b, base, code: t_art_stage_1126(b, base, code))
