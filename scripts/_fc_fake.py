# 「流向驗證」頁的假資料產生器（規格 docs/design/20261030_flow_verify_page.md 第七節）。
# 為什麼要假資料：真資料由 build_payload 產出，前端先照規格欄位寫完才能驗收；
# 驗收與截圖時用 Playwright 的 route 攔 /data/flowcheck/**，回這裡造的 JSON，真資料上線後不攔就吃真的。
# 族群、成分股、名稱取自本機 site/data/groups_detail.json（真名字，畫面才看得出像不像）；數字是決定性的偽隨機。
# flake8: noqa
import json
import math
import random
from pathlib import Path

LATEST = "2026-10-30"
M60_DAY = None     # build() 內設為倒數第 2 個交易日：這天有 60 分資料（歷史單日內切 4 格）
DAILY_ONLY_DAY = None   # 倒數第 3 個交易日：只有日線（驗「灰字原因」）


def _r(seed):
    return random.Random(seed)


def _slots():
    out = []
    m = 9 * 60 + 5
    while m <= 13 * 60 + 30:
        out.append("%02d:%02d" % (m // 60, m % 60))
        m += 5
    return out


def build(site):
    site = Path(site)
    det = json.loads((site / "data" / "groups_detail.json").read_text(encoding="utf-8"))
    sd = json.loads((site / "data" / "sankey_daily.json").read_text(encoding="utf-8"))
    chain_of = {g["gid"]: (g["chain"], g["chain_name"]) for g in sd["groups"]}
    gids = [k for k, v in det.items() if not k.startswith("ind_") and len(v.get("members") or []) >= 4][:56]
    dates = sd["dates"][-60:]
    dates = [d for d in dates if d < LATEST][-59:] + [LATEST]
    global M60_DAY, DAILY_ONLY_DAY
    M60_DAY, DAILY_ONLY_DAY = dates[-2], dates[-3]
    groups = []
    for k in gids:
        ch = chain_of.get(k, ("other", "其他"))
        groups.append({"gid": k, "name": det[k]["group_name"], "chain": ch[0], "chain_name": ch[1], "tier": "mid",
                       "members": [str(m["code"]) for m in det[k]["members"]], "is_bucket": False})
    gmap = {g["gid"]: g for g in groups}
    layers = {d: ["daily"] for d in dates}
    layers[M60_DAY] = ["daily", "m60"]
    layers[LATEST] = ["daily", "m5"]
    idx = {
        "schema": 1, "dates": dates, "layers": layers, "latest": LATEST, "updated_at": LATEST + "T15:40:00+08:00",
        "data_start": "2023-09-19", "m5_start": "2026-10-30",
        "groups": groups,
        "baseline": {"same_rate": 0.619, "ic": 0.28, "crash_same_rate": 0.55, "period": "近 3 年"},
        "market": {"basis": "加權指數日報酬（假資料）", "dates": dates, "ret": [round(_r(i).uniform(-1.2, 1.2), 3) for i in range(len(dates))]},
    }
    out = {"flowcheck/index.json": idx}
    mret = dict(zip(dates, idx["market"]["ret"]))
    tvmap = {}
    for d in dates:
        r = _r(d)
        tot = sum(1 for _ in gids)
        raw = {k: r.uniform(0.3, 6) for k in gids}
        sm = sum(raw.values())
        share = {k: raw[k] / sm * 100 for k in gids}
        tvmap[d] = {k: share[k] * 1e10 for k in gids}
        gd = {}
        for k in gids:
            rr = _r(d + k)
            ds = rr.uniform(-1.2, 1.2)
            rel = ds * 0.7 + rr.uniform(-1.4, 1.4)
            chg = mret[d] + rel
            mem = det[k]["members"]
            adv = sum(1 for _ in mem if rr.random() < (0.5 + rel / 6))
            rot = rr.uniform(-1.5, 1.5)
            trail = [[round(rot - (4 - i) * rr.uniform(-.3, .3), 3), round(ds - (4 - i) * rr.uniform(-.4, .4), 3)] for i in range(4)] + [[round(rot, 3), round(ds, 3)]]
            rsx, rsy = 100 + rel * 2 + rr.uniform(-3, 3), 100 + rr.uniform(-4, 4)
            quad = lambda x, y: ("leading" if x >= 100 and y >= 100 else "weakening" if x >= 100 else "improving" if y >= 100 else "lagging")
            mq = ("湧入" if rot >= 0 and ds >= 0 else "續進" if rot >= 0 else "轉出" if ds < 0 else "退場")
            mq = {"湧入": "inflow", "續進": "keep", "轉出": "outflow", "退場": "exit"}[mq]
            gd[k] = {"share": round(share[k], 3), "dshare": round(ds, 3), "rot": round(rot, 3), "chg": round(chg, 3), "rel": round(rel, 3),
                     "adv": adv, "dec": len(mem) - adv, "tv": round(tvmap[d][k]), "rs_x": round(rsx, 2), "rs_y": round(rsy, 2), "quadrant": quad(rsx, rsy),
                     "m_x": round(rot, 3), "m_y": round(ds, 3), "m_quadrant": mq, "m_trail": trail,
                     "inst": {"f": round(rr.uniform(-9, 9), 2), "t": round(rr.uniform(-2, 2), 2), "d": round(rr.uniform(-1.5, 1.5), 2)}}
        members = {}
        for k in gids:
            mem = det[k]["members"]
            tvs = [max(m.get("turnover") or 1e8, 1e8) * _r(d + str(m["code"])).uniform(.6, 1.4) for m in mem]
            st = sum(tvs)
            for m, tv in zip(mem, tvs):
                c = str(m["code"])
                rr = _r(d + c)
                rel = gd[k]["rel"] + rr.uniform(-1.5, 1.5)
                e = members.setdefault(c, {"name": m["name"], "gid": [], "close": round(m.get("close") or 100, 2), "chg": round(mret[d] + rel, 2), "rel": round(rel, 2), "tv": round(tv),
                                           "share_in_group": round(tv / st * 100, 1), "inst": {"f": round(rr.uniform(-5, 5), 2), "t": round(rr.uniform(-1, 1), 2), "d": round(rr.uniform(-.5, .5), 2)},
                                           "contrib": round(rel * tv / st, 3)})
                e["gid"].append(k)
        leaves = []
        for k in gids:
            leaves.append({"gid": k, "name": gmap[k]["name"], "chain": gmap[k]["chain"], "chain_name": gmap[k]["chain_name"], "tv": round(tvmap[d][k])})
        news = []
        for k in gids[:6]:
            c = gmap[k]["members"][0]
            news.append({"id": d + k, "t": "%02d:%02d" % (9 + (len(news) * 7) % 4, (len(news) * 11) % 60), "title": "%s 公告（假資料）：%s" % (members[c]["name"], ["董事會決議", "重大訊息", "法說會時間"][len(news) % 3]),
                         "url": "https://example.com/n/" + c, "source": "公開資訊觀測站", "codes": [c], "kind": "material"})
        sigs = []
        for i, k in enumerate(gids[:5]):
            sigs.append({"gid": k, "type": ["flow_lead", "breadth", "open_low_recover"][i % 3], "t": "%02d:%02d" % (10 + i % 3, 5 + i * 5), "rel_at_trigger": round(_r(d + k).uniform(-1, 1), 2),
                         "rel_to_close": round(_r(d + k + "c").uniform(-1, 1), 2), "rel_next_day": None if d == LATEST else round(_r(d + k + "n").uniform(-1, 1), 2)})
        day = {"date": d, "groups": gd, "members": members, "sankey": {"leaves": leaves}, "signals": sigs, "news": news, "market": {"chg": mret[d]}}
        if d == M60_DAY:
            day["m60"] = {"times": ["10:00", "11:00", "12:00", "13:00", "13:30"], "gap_0900": True,
                          "groups": {k: {"idx_rel": [round(gd[k]["rel"] * f + _r(k + str(f)).uniform(-.3, .3), 3) for f in (.2, .5, .7, .9, 1.0)],
                                         "share": [round(gd[k]["dshare"] * f + _r(k + str(f) + "s").uniform(-.2, .2), 3) for f in (.2, .5, .7, .9, 1.0)]} for k in gids}}
        out["flowcheck/day/%s.json" % d] = day
    # 5 分鐘（只有最新日）
    sl = _slots()
    n = len(sl)
    g5 = {}
    for k in gids:
        rr = _r("m5" + k)
        fin = out["flowcheck/day/%s.json" % LATEST]["groups"][k]
        rel, sh, ch, ad, de = [], [], [], [], []
        walk = rr.uniform(-.4, .4)
        for i in range(n):
            walk += rr.uniform(-.12, .12)
            f = (i + 1) / n
            rel.append(round(fin["rel"] * f + walk * (1 - f) * 0.8, 3))
            sh.append(round(fin["dshare"] * f + rr.uniform(-.25, .25) * (1 - f), 3))
            ch.append(round(rel[-1] + 0.3, 3))
            a = max(0, min(len(gmap[k]["members"]), round(len(gmap[k]["members"]) * (0.5 + rel[-1] / 5))))
            ad.append(a)
            de.append(len(gmap[k]["members"]) - a)
        g5[k] = {"idx_rel": rel, "share": sh, "chg": ch, "adv": ad, "dec": de}
    mem5 = {}
    for k in gids:
        top = sorted(det[k]["members"], key=lambda m: -(m.get("turnover") or 0))[:6]
        for m in top:
            rr = _r("m5" + str(m["code"]))
            p = 0
            arr = []
            for i in range(n):
                p += rr.uniform(-.25, .25)
                arr.append(round(p, 3))
            mem5[str(m["code"])] = {"chg": arr, "close": [round((m.get("close") or 100) * (1 + v / 100), 2) for v in arr]}
    out["flowcheck/m5/%s.json" % LATEST] = {"date": LATEST, "slots": sl, "groups": g5, "members": mem5}
    # 日線序列
    for k in gids:
        rr = _r("ser" + k)
        idxv, relidx, shr, dsh, chg, rel = [], [], [], [], [], []
        v, rv = 100.0, 100.0
        for d in dates:
            gdd = out["flowcheck/day/%s.json" % d]["groups"][k]
            v *= 1 + gdd["chg"] / 100
            rv *= 1 + gdd["rel"] / 100
            idxv.append(round(v, 2)); relidx.append(round(rv, 2)); shr.append(gdd["share"]); dsh.append(gdd["dshare"]); chg.append(gdd["chg"]); rel.append(gdd["rel"])
        mem = {}
        for m in sorted(det[k]["members"], key=lambda m: -(m.get("turnover") or 0))[:6]:
            p = m.get("close") or 100
            arr = []
            for d in dates:
                p *= 1 + out["flowcheck/day/%s.json" % d]["members"][str(m["code"])]["chg"] / 100 * 0.2
                arr.append(round(p, 2))
            mem[str(m["code"])] = {"name": m["name"], "close": arr}
        out["flowcheck/series/%s.json" % k] = {"gid": k, "dates": dates, "idx": idxv, "rel_idx": relidx, "share": shr, "dshare": dsh, "chg": chg, "rel": rel, "members": mem,
                                                        "inst_f": [out["flowcheck/day/%s.json" % d]["groups"][k]["inst"]["f"] for d in dates], "inst_t": [out["flowcheck/day/%s.json" % d]["groups"][k]["inst"]["t"] for d in dates], "inst_d": [out["flowcheck/day/%s.json" % d]["groups"][k]["inst"]["d"] for d in dates]}
    rules = [
        {"id": "share_up3", "label": "資金連 3 日流入但股價落後", "n": 640, "hit_rate": 0.53, "ci": [0.49, 0.57], "avg_excess_net": -0.21, "passed": False},
        {"id": "inst_buy5", "label": "法人連買 5 日", "n": 410, "hit_rate": 0.55, "ci": [0.50, 0.60], "avg_excess_net": 0.12, "passed": False},
        {"id": "vol_up_flat", "label": "量增價穩", "n": 22, "hit_rate": 0.6, "ci": [0.38, 0.79], "avg_excess_net": 0.3, "passed": False},
    ]
    items = []
    for di, d in enumerate(dates[-30:]):
        for k in gids[di % 7: di % 7 + 3]:
            rr = _r("ds" + d + k)
            mem = det[k]["members"]
            m = mem[rr.randrange(len(mem))]
            rule = rules[(di + len(k)) % 3]["id"]
            fwd = {h: (None if di + n_ >= 30 else round(rr.uniform(-4, 5), 2)) for h, n_ in (("d5", 5), ("d10", 10), ("d20", 20))}
            items.append({"rule": rule, "date": d, "gid": k, "code": str(m["code"]) if rr.random() < .7 else None, "name": m["name"],
                          "reason": "占比連 3 日上升 +%.2fpp，相對大盤 %+.1f%%" % (rr.uniform(.2, 1.5), rr.uniform(-1, .5)), "fwd": fwd})
    out["flowcheck/daily_signals.json"] = {"as_of": LATEST, "rules": rules, "items": items}
    out["flowcheck/backtest.json"] = {
        "as_of": LATEST, "period": "2023-09 ~ 2026-10",
        "rows": [
            {"type": "flow_lead", "label": "資金先行", "n": 412, "hit_rate": 0.512, "ci": [0.463, 0.561], "avg_excess": 0.04, "avg_excess_net": -0.43, "ic": 0.03, "t_nw": 0.6, "passed_multiple_test": False},
            {"type": "breadth", "label": "擴散", "n": 288, "hit_rate": 0.504, "ci": [0.446, 0.562], "avg_excess": -0.02, "avg_excess_net": -0.49, "ic": 0.01, "t_nw": -0.2, "passed_multiple_test": False},
            {"type": "open_low_recover", "label": "開低回升", "n": 18, "hit_rate": 0.61, "ci": [0.4, 0.8], "avg_excess": 0.2, "avg_excess_net": -0.27, "ic": 0.05, "t_nw": 0.4, "passed_multiple_test": False},
        ],
        "events": [],
    }
    return out


if __name__ == "__main__":
    import sys
    o = build(sys.argv[1] if len(sys.argv) > 1 else "site")
    print(len(o), "files;", sum(len(json.dumps(v)) for v in o.values()) // 1024, "KB")
