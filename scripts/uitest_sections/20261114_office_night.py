# 驗收段落「辦公室夜晚開燈」：夜晚室內要像「裡面開燈、亮的」，而不是「光從窗戶照進來」。
#   夜晚：窗光斜影（W.patchMat）強度 0；室內地板與角色臉部平均亮度達門檻（修改前約 128／139，門檻 150／155）；
#         室外天空仍是深色；白天窗光斜影仍在；黃昏仍有（偏橘）；繪製次數增量 ≤ +5；無主控台錯誤
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

import io as _io
from PIL import Image as _Im


def _nt_lum(png, box):
    d = list(_Im.open(_io.BytesIO(png)).convert("L").crop(box).get_flattened_data() if hasattr(_Im.Image, "get_flattened_data") else _Im.open(_io.BytesIO(png)).convert("L").crop(box).getdata())
    return sum(d) / len(d)


def t_office_night(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 1280, "height": 800})
    pg = c.new_page()
    pg.set_default_timeout(120000)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    try:
        pg.goto(root + "/office/world.html?ambient=0&q=low&pr=0.6&sim=1", wait_until="domcontentloaded")
        ok("夜晚段：場景載入", wait_until(pg, "() => window.__world && window.__world.ready", 90000))
        info = {}
        for k in ("day", "dusk", "night"):
            pg.evaluate("(k) => __world.daytime.set(k)", k)
            pg.wait_for_timeout(1800)
            info[k] = pg.evaluate("""() => { const W = __world, cv = W.skyTex.image, d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let s = 0, n = 0;
              for (let i = 0; i < d.length; i += 4) { s += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; n++; }
              return { patch: W.patchMat.opacity, sky: s / n, calls: W.stats.calls, glass: W.glassMat.opacity }; }""")
            if k == "night":
                info[k]["overview"] = pg.screenshot()
                pg.evaluate("() => __world.jumpTo(__world.rooms.keys().next().value)")
                pg.wait_for_timeout(2200)
                info[k]["room"] = pg.screenshot()
        ok("夜晚：窗邊斜影（窗光貼片）強度為 0（%.3f）" % info["night"]["patch"], info["night"]["patch"] < 0.001, info["night"]["patch"])
        ok("白天：窗光斜影仍在（%.2f）" % info["day"]["patch"], info["day"]["patch"] >= 0.08, info["day"]["patch"])
        ok("黃昏：斜影比白天更明顯（偏橘，%.2f）" % info["dusk"]["patch"], info["dusk"]["patch"] > info["day"]["patch"], info["dusk"])
        ok("夜晚：窗玻璃自發光暖黃（不透明 %.2f，看得到屋裡透出的光）" % info["night"]["glass"], info["night"]["glass"] >= 0.7, info["night"]["glass"])
        ind = _nt_lum(info["night"]["overview"], (250, 300, 1050, 600))
        floor = _nt_lum(info["night"]["room"], (400, 480, 900, 600))
        face = _nt_lum(info["night"]["room"], (600, 320, 680, 380))
        ok("夜晚：俯瞰室內平均亮度 ≥ 150（%.0f，修改前約 128）" % ind, ind >= 150, ind)
        ok("夜晚：室內地板平均亮度 ≥ 150（%.0f，修改前約 131）" % floor, floor >= 150, floor)
        ok("夜晚：角色臉部平均亮度 ≥ 155（%.0f，修改前約 139）" % face, face >= 155, face)
        px = list(_Im.open(_io.BytesIO(info["night"]["overview"])).convert("RGB").crop((0, 200, 80, 560)).getdata()) if not hasattr(_Im.Image, "get_flattened_data") else list(_Im.open(_io.BytesIO(info["night"]["overview"])).convert("RGB").crop((0, 200, 80, 560)).get_flattened_data())
        rgb = [sum(q[i] for q in px) / len(px) for i in range(3)]
        gl = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        ok("夜晚：屋外草地樹木平均亮度 ≤ 室內的 55%%（%.0f 對 %.0f）" % (gl, ind), gl <= ind * 0.55, (gl, ind))
        ok("夜晚：屋外草地色相偏藍綠（R %.0f、G %.0f、B %.0f，綠或藍 ≥ 紅）" % tuple(rgb), max(rgb[1], rgb[2]) >= rgb[0], rgb)
        ok("夜晚：室外天空仍是深色（亮度 %.0f ≤ 90）" % info["night"]["sky"], info["night"]["sky"] <= 90, info["night"]["sky"])
        ok("夜晚：繪製次數增量 ≤ +5（%d → %d）" % (info["day"]["calls"], info["night"]["calls"]), info["night"]["calls"] - info["day"]["calls"] <= 5, info)
        ok("夜晚段：沒有主控台錯誤", not errs, errs[:3])
    finally:
        c.close()


register("辦公室夜晚開燈", lambda pg, b, base, code: t_office_night(b, base))
