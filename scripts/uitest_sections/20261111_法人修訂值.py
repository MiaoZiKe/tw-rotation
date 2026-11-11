# 驗收段落「法人修訂值1111」（Andy 2026-11-11「加修訂值」）：#market/inst 四格主數字下方的「晚間修訂」小字。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# 全部用 page.route 換掉 inst_market.json 的最後一列（資料才是確定的），分四種情境，1440 與 390 各一輪：
#   A 投信、合計有修訂值（外資、自營商與主數字相同）→ 只有「投信」「合計」兩格出現小字，文字＝「晚間修訂 ±xx.x 億」且數字等於 rev，主數字仍是首次公布值
#   B 整列沒有 rev → 四格都沒有小字（不留空行）
#   C rev 只差 0.02 億（四捨五入到 0.1 後一樣）→ 不顯示
#   D 自營商修訂值變號（買超變賣超）→ 小字顏色跟著變（綠／down），主數字仍是紅（up）
#   390 另驗：沒有橫向捲軸、小字 ≥ 11px、小字不超出所屬格子

import json as _json


def _rev_fmt(v):
    s = f"{abs(v):,.1f}"
    return ("+" if v > 0 else "−" if v < 0 else "") + s


_REV_ST = """() => { const r = document.getElementById('instToday'); if (!r) return null;
  const tiles = [...r.querySelectorAll('.itile')].map(t => { const e = t.querySelector('.irev'), iv = t.querySelector('.iv'), tr = t.getBoundingClientRect();
    const er = e ? e.getBoundingClientRect() : null;
    return { k: t.dataset.k, iv: iv.textContent.trim(), ivCls: iv.className, tag: e ? e.textContent.replace(/\\s+/g, ' ').trim() : null,
      bCls: e ? e.querySelector('b').className : '', fs: e ? parseFloat(getComputedStyle(e).fontSize) : 0,
      inside: er ? (er.left >= tr.left - 0.5 && er.right <= tr.right + 0.5) : true,
      below: er ? er.top >= iv.getBoundingClientRect().bottom - 1 : true }; });
  return { tiles, sw: document.documentElement.scrollWidth, iw: innerWidth }; }"""


def _rev_case(c, base, tag, mutate):
    pg = c.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    box = {}

    def h(route):
        resp = route.fetch()
        d = _json.loads(resp.text())
        box["last"] = dict(d["rows"][-1])
        mutate(d["rows"][-1])
        box["new"] = dict(d["rows"][-1])
        route.fulfill(response=resp, body=_json.dumps(d, ensure_ascii=False), content_type="application/json")

    pg.route("**/data/inst_market.json*", h)
    pg.goto(f"{base}#market/inst", wait_until="networkidle")
    got = wait_until(pg, "() => { const r = document.getElementById('instToday'); return !!r && r.dataset.ready === '1' && !!r.querySelector('.itile'); }", 15000)
    ok(f"[{tag}] 日報畫出來", got)
    st = pg.evaluate(_REV_ST) if got else None
    return pg, st, box, errs


def t_rev_1111(b, base):
    errs_all = []
    for vtag, vp, mobile in (("1440", {"width": 1440, "height": 1000}, False), ("390", {"width": 390, "height": 844}, True)):
        kw = dict(viewport=vp)
        if mobile:
            kw.update(device_scale_factor=2, is_mobile=True, has_touch=True)
        # A
        def mutA(row):
            row["rev"] = {"f": row["f"], "t": round(row["t"] + 45.6, 2), "dl": row["dl"], "tot": round(row["tot"] + 45.6, 2)}
        c = b.new_context(**kw)
        try:
            pg, st, box, errs = _rev_case(c, base, f"{vtag}・A 投信與合計有修訂值", mutA)
            errs_all += errs
            if st:
                by = {t["k"]: t for t in st["tiles"]}
                new, last = box["new"], box["last"]
                want_t = "晚間修訂 " + _rev_fmt(new["rev"]["t"]) + " 億"
                want_tot = "晚間修訂 " + _rev_fmt(new["rev"]["tot"]) + " 億"
                ok(f"★ [{vtag}] A：只有投信、合計兩格出現小字（外資、自營商與主數字相同不顯示）", [k for k, t in by.items() if t["tag"]] == ["t", "tot"], {k: t["tag"] for k, t in by.items()})
                ok(f"★ [{vtag}] A：小字文字與 rev 完全一致（{by['t']['tag']}／{by['tot']['tag']}）", by["t"]["tag"] == want_t and by["tot"]["tag"] == want_tot, [by["t"]["tag"], want_t, by["tot"]["tag"], want_tot])
                ok(f"★ [{vtag}] A：主數字仍是首次公布值（不是修訂值）", all(by[k]["iv"] == _rev_fmt(last[k]) + " 億" for k in ("f", "t", "dl", "tot")), [by[k]["iv"] for k in by])
                ok(f"[{vtag}] A：小字在主數字下方、字級 ≥ 11px、沒超出格子", all(by[k]["below"] and by[k]["inside"] and by[k]["fs"] >= 11 for k in ("t", "tot")), [(by[k]["fs"], by[k]["inside"], by[k]["below"]) for k in ("t", "tot")])
                if mobile:
                    ok(f"★ [{vtag}] A：沒有橫向捲軸", st["sw"] <= st["iw"] + 1, [st["sw"], st["iw"]])
        finally:
            c.close()
        # B
        def mutB(row):
            row.pop("rev", None)
        c = b.new_context(**kw)
        try:
            pg, st, box, errs = _rev_case(c, base, f"{vtag}・B 沒有修訂值", mutB)
            errs_all += errs
            if st:
                ok(f"★ [{vtag}] B：整列沒有 rev → 四格都沒有小字", all(t["tag"] is None for t in st["tiles"]) and len(st["tiles"]) == 4, [t["tag"] for t in st["tiles"]])
        finally:
            c.close()
        # C
        def mutC(row):
            row["rev"] = {"f": round(row["f"] + 0.02, 2), "t": row["t"], "dl": round(row["dl"] - 0.01, 2), "tot": round(row["tot"] + 0.02, 2)}
        c = b.new_context(**kw)
        try:
            pg, st, box, errs = _rev_case(c, base, f"{vtag}・C 差 0.02 億", mutC)
            errs_all += errs
            if st:
                ok(f"[{vtag}] C：修訂值只差 0.02 億（顯示起來一樣）→ 不出現小字", all(t["tag"] is None for t in st["tiles"]), [t["tag"] for t in st["tiles"]])
        finally:
            c.close()
        # D
        def mutD(row):
            row["dl"] = abs(row["dl"]) + 20.0
            row["rev"] = {"f": row["f"], "t": row["t"], "dl": -(abs(row["dl"]) + 15.0), "tot": row["tot"]}
        c = b.new_context(**kw)
        try:
            pg, st, box, errs = _rev_case(c, base, f"{vtag}・D 自營商變號", mutD)
            errs_all += errs
            if st:
                by = {t["k"]: t for t in st["tiles"]}
                ok(f"★ [{vtag}] D：自營商主數字紅(up)、小字數字綠(down)，其餘三格沒有小字", "up" in by["dl"]["ivCls"] and by["dl"]["tag"] and "down" in by["dl"]["bCls"] and by["dl"]["tag"].startswith("晚間修訂 −") and [k for k, t in by.items() if t["tag"]] == ["dl"], [by["dl"], [k for k, t in by.items() if t["tag"]]])
        finally:
            c.close()
    ok("法人修訂值1111：沒有網頁錯誤", not errs_all, errs_all[:3])


register("法人修訂值1111", lambda pg, b, base, code: t_rev_1111(b, base))
