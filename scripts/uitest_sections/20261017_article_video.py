# 驗收段落「文章影片區塊1017」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ===================================================================== 文章影片區塊1017（Andy 10-17：「像是這種發佈會，他會有影片，最好是把影片也可以附上在文章中」「會有的區塊是可以直接播放」）
# 拿一篇公開的舊文章，在這個 context 裡把它的全文換成「原文＋影片區塊」（repo 不動），1440 與 390：
#   ① YouTube 區塊 → 文章裡直接是播放器（iframe，youtube-nocookie 網域、16:9、寬度吃滿內文欄），下方有來源・日期與「在 YouTube 開啟」
#   ② X 區塊 → 官方嵌入頁的 iframe；「在 X 開啟」連到 x.com/i/status/<id>
#   ③ id 格式不對（帶引號、網址）→ 整塊不畫，不會把字串塞進網址
#   ④ 播放器不超出內文欄、沒有橫向捲軸
VID_BLOCKS = [
    {"t": "video", "provider": "youtube", "id": "dQw4w9WgXcQ", "title": "發表會影片（測試）", "source": "測試頻道", "date": "2026-10-15"},
    {"t": "video", "provider": "x", "id": "2110165104713183485", "title": "X 影片（測試）", "source": "Tesla on X"},
    {"t": "video", "provider": "youtube", "id": "\"><img src=x onerror=window.__vidXss=1>"},
    {"t": "video", "provider": "vimeo", "id": "123"},
]


def t_article_video_1017(b, base, code):
    T = "文章影片區塊1017"
    errs: list[str] = []
    idx = json.loads((SITE / "articles" / "index.json").read_text(encoding="utf-8"))["articles"]
    pub = [a for a in idx if a.get("src") != "api" and (SITE / "articles" / "posts" / f"{a['id']}.json").exists()]
    if not ok(f"{T}：有公開的舊文章可以拿來測", bool(pub)):
        return
    aid = pub[0]["id"]
    post = json.loads((SITE / "articles" / "posts" / f"{aid}.json").read_text(encoding="utf-8"))
    post["blocks"] = VID_BLOCKS[:1] + post["blocks"] + VID_BLOCKS[1:]
    for w in (1440, 390):
        c = b.new_context(viewport={"width": w, "height": 900})
        c.add_init_script("try{localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.tour','done')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(f"**/articles/posts/{aid}.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(post, ensure_ascii=False)))
        c.route(re.compile(r"https://(www\.youtube-nocookie\.com|platform\.twitter\.com)/.*"), lambda r: r.fulfill(status=200, content_type="text/html", body="<html><body style='background:#123'>player</body></html>"))
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + f"#article/{aid}", wait_until="domcontentloaded")
        got = wait_until(pg, "() => document.querySelectorAll('.artvid').length >= 1 ? 1 : 0", 15000)
        if not ok(f"{T}（{w}）：文章頁畫出影片區塊", bool(got)):
            c.close(); continue
        pg.wait_for_timeout(600)
        st = pg.evaluate("""() => { const v = [...document.querySelectorAll('.artvid')], body = document.querySelector('.artbody') || document.body, br = body.getBoundingClientRect();
            return { n: v.length, items: v.map(f => { const i = f.querySelector('iframe'), r = f.querySelector('.avw').getBoundingClientRect(), a = f.querySelector('.avc a');
                return { cls: f.className, src: i && i.src, ratio: +(r.width / r.height).toFixed(2), w: r.width, inCol: r.left >= br.left - 1 && r.right <= br.right + 1, full: (() => { const p = f.parentElement.getBoundingClientRect(); return Math.abs(r.width - p.width) <= 2 && Math.abs((r.left + r.right) / 2 - (p.left + p.right) / 2) <= 2; })(), href: a && a.href, cap: f.querySelector('.avc').textContent, lazy: i && i.loading }; }),
                sw: document.documentElement.scrollWidth - innerWidth, xss: !!window.__vidXss }; }""")
        it = st["items"]
        yt = next((x for x in it if "youtube" in x["cls"]), None)
        xx = next((x for x in it if " x" in " " + x["cls"]), None)
        ok(f"{T}（{w}）：YouTube 區塊＝文章內播放器（nocookie、16:9、填滿內文欄寬並置中、lazy），有來源・日期與開啟連結",
           bool(yt) and yt["src"].startswith("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ") and 1.7 <= yt["ratio"] <= 1.8 and yt["inCol"] and yt["full"] and yt["lazy"] == "lazy"
           and "測試頻道" in yt["cap"] and "2026-10-15" in yt["cap"] and yt["href"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ", yt)
        ok(f"{T}（{w}）：X 區塊＝官方嵌入頁 iframe，「在 X 開啟」連到原貼文", bool(xx) and xx["src"].startswith("https://platform.twitter.com/embed/Tweet.html?id=2110165104713183485")
           and xx["href"] == "https://x.com/i/status/2110165104713183485" and xx["inCol"], xx)
        ok(f"{T}（{w}）：格式不對的 id 與不支援的平台整塊不畫、沒有被塞進網址；沒有橫向捲軸", st["n"] == 2 and not st["xss"] and st["sw"] <= 1, {"n": st["n"], "sw": st["sw"]})
        shot = os.environ.get("TW_VID_SHOT")
        if shot:
            pg.locator(".artvid >> nth=0").scroll_into_view_if_needed(); pg.wait_for_timeout(300)
            pg.screenshot(path=shot.replace(".png", f"_{w}.png"))
        c.close()
    ok(f"{T}：沒有網頁錯誤", not errs, errs[:3])


register("文章影片區塊1017", lambda pg, b, base, code: t_article_video_1017(b, base, code))
