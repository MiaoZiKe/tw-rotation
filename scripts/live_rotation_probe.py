"""盤中巡檢：線上網站的「資金輪動 → 即時」在盤中是不是真的每分鐘在動。

為什麼要有這支（2026-09-24，Andy 說「很重要」的那個問題）：
  「在盤中時，他真的有辦法達到即時功能？是會更新上面的輪動？」
  `_uitest.py` 的「輪動時鐘即時」那一段是**假報價**（容器打不到證交所），
  它只證明「給它報價，畫面會動」，證明不了「線上那一台在盤中真的拿得到報價、真的每分鐘重算」。
  只有 GitHub Actions 的 runner 打得到線上網站與 Worker，所以這件事只能在那裡驗。

做的事（每一步都讀**畫面上真的在用的那一份**，不另外算一次）：
  ① 打開線上 `#flow`、按「即時」，等第一輪算完 → 快照 A
  ② 等約 2.5 分鐘（頁面自己的 60 秒計時器會跑兩輪，這支**不催**它）→ 快照 B
  ③ 判定：抓到報價了沒／報價時間有沒有前進／盤上的點有沒有移動／排行第一名換了沒／涵蓋率

三態（CLAUDE.md：「沒設定」「還沒到」「真的壞了」永遠分開記）：
  · 今天不是交易日（週末、休市）→ 綠燈結束，摘要寫「今天不是交易日」
  · 現在不是盤中（手動在盤後按的）→ 只判 ①「抓不抓得到報價」，②③ 列出來但不判紅
  · 盤中而且抓不到報價、或兩次之間點完全沒動 → 紅燈

用法：
  python scripts/live_rotation_probe.py                         # 打線上
  python scripts/live_rotation_probe.py --url http://127.0.0.1:8768/#flow --stub --wait 70
      # 本機自測：用會變動的假報價把整條判定走一遍（容器打不到線上時用）

輸出：`--out` 指定的 JSON（Actions 會存成 artifact）、`--summary` 指定的 Markdown
（Actions 給 `$GITHUB_STEP_SUMMARY`）、兩張時鐘截圖。結束碼 0＝綠、1＝紅。
**不寫進 repo 的任何資料**：巡檢結果不 commit（避免跟每日管線搶 commit）。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path

TPE = dt.timezone(dt.timedelta(hours=8))
LIVE_URL = "https://miaozike.github.io/tw-rotation/#flow"
HOLIDAY_API = "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"

# 條款橫幅與導覽啟用那天，不先寫好這兩個 key 就會被擋住按不到「即時」（和 _uitest 同一套）
CONSENT_PRESET = ("try{if(!localStorage.getItem('tw.consent'))localStorage.setItem('tw.consent',"
                  "JSON.stringify({v:'*',at:'probe'}));"
                  "if(!localStorage.getItem('tw.tour'))localStorage.setItem('tw.tour','*');}catch(e){}")

# 本機自測用的假報價：**每呼叫一次就變一次**（漲跌幅與成交時間都往前走），
# 這樣才走得到「兩次快照之間點有沒有動」那條判定。真實巡檢不會用到。
STUB = """() => {
  const D = window.App.D, det = D.groups_detail || {};
  const rrg = (D.flow_v3 || {}).rrg || {};
  const base = {};
  (rrg.points || []).forEach((p, i) => ((det[p.group_id] || {}).members || []).forEach(m => {
    const c = String(m.code); if (base[c] == null) base[c] = ((i % 13) - 6) * 0.4; }));
  let n = 0;
  const now = new Date(Date.now() + 8 * 3600e3);
  const ymd = now.toISOString().slice(0, 10).replace(/-/g, '');
  window.Live = Object.assign({}, window.Live || {}, { isIntraday: () => true,
    fetchQuotes: async (cs) => {
      n++;
      const o = {}, t = `10:${String(10 + n).padStart(2, '0')}:00`;
      cs.forEach((c, k) => { const b = base[c] != null ? base[c] : 0;
        o[c] = { price: 100, volume: 800 + k, chgPct: b + ((k % 5) - 2) * 0.15 * n, time: t, date: ymd }; });
      return o; } });
  window.Market3 = { lastAt: Date.now(), marketAmt: 4.2e11, refresh: async () => {} };
  return Object.keys(base).length; }"""

# 一次快照。三個來源都讀「畫面正在用的那一份」：
#   rlvState() —— 即時續算的資料座標（2026-09-24 為這支加的唯讀窗口；舊版網站沒有就退回 rotLive()）
#   _rotPts    —— 時鐘上**真的畫出去**的那一點（使用者看到的東西）
#   rankFlow   —— 右邊「資金流向排行」那張圖的第一名（圖的 y 軸最後一個＝最上面）
SNAP = """() => {
  const A = window.App || {};
  const s = A.rlvState ? A.rlvState() : null;
  const r = A.rotLive ? A.rotLive() : {};
  const drawn = {};
  (A._rotPts || []).forEach(p => { if (!p.stock) drawn[p.gid] = { x: p.x, y: p.y, live: !!p.live, name: p.name }; });
  let rankTop = null;
  try {
    const c = echarts.getInstanceByDom(document.getElementById('rankFlow'));
    const ys = ((c.getOption() || {}).yAxis || [])[0] || {};
    const d = ys.data || [];
    const v = d[d.length - 1];
    rankTop = v == null ? null : (typeof v === 'object' ? v.value : v);
  } catch (e) { rankTop = null; }
  const chips = [...document.querySelectorAll('#rotLive .rlvchip .g')].map(e => e.textContent.trim());
  const note = (document.getElementById('rotLive') || {}).innerText || '';
  return {
    hasRlvState: !!A.rlvState,
    state: s || { on: r.on, at: r.at, quoteAt: r.quoteAt, hit: r.hit, codes: r.codes,
                  reqs: r.reqs, err: r.err, cover: r.cover, pts: null },
    intraday: r.intraday, skipped: r.skipped, mkt: r.mkt,
    top: (r.top || []).map(t => ({ gid: t.gid, name: t.name, tdx: t.tdx, tdy: t.tdy, stage: t.stage })),
    drawn, rankTop, chips, note: note.slice(0, 400),
    btnPressed: (document.getElementById('rotLiveBtn') || {}).getAttribute
      ? document.getElementById('rotLiveBtn').getAttribute('aria-pressed') : null,
  }; }"""


def tpe_now() -> dt.datetime:
    return dt.datetime.now(TPE)


def fetch_holidays(today: dt.date) -> tuple[str | None, str]:
    """證交所 openapi 的休市表。回 (今天休市的理由 或 None, 狀態說明)。
    抓不到就回 (None, '抓不到')，交給「報價日期是不是今天」做最後判斷。
    ⚠「開始交易」「最後交易」那兩種列是**交易日**（例如春節前最後交易日），不可以當成休市。"""
    try:
        req = urllib.request.Request(HOLIDAY_API, headers={"User-Agent": "tw-rotation-probe"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — 抓不到就退回報價日期判斷，理由寫進摘要
        return None, f"抓不到（{type(e).__name__}）"
    roc = f"{today.year - 1911}{today:%m%d}"
    ad = today.strftime("%Y%m%d")
    for row in rows if isinstance(rows, list) else []:
        vals = {str(v).strip() for v in row.values()}
        if roc in vals or ad in vals or today.isoformat() in vals:
            text = " ".join(str(v) for v in row.values())
            if "開始交易" in text or "最後交易" in text:
                return None, f"休市表有今天，但那一列是交易日（{text[:40]}）"
            return text[:60], "休市表有今天"
    return None, f"休市表沒有今天（{len(rows) if isinstance(rows, list) else 0} 列）"


def moved_points(a: dict, b: dict) -> list[dict]:
    out = []
    for g, p in a.items():
        q = b.get(g)
        if not q:
            continue
        d = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
        out.append({"gid": g, "name": p.get("name") or g, "d": round(d, 4),
                    "dx": round(q["x"] - p["x"], 4), "dy": round(q["y"] - p["y"], 4),
                    "live": bool(p.get("live")) and bool(q.get("live"))})
    return sorted(out, key=lambda r: -r["d"])


def run(args) -> dict:
    from playwright.sync_api import sync_playwright

    started = tpe_now()
    res: dict = {"url": args.url, "started": started.strftime("%Y-%m-%d %H:%M:%S"), "stub": args.stub}
    today = started.date()
    wk = started.weekday()
    intraday = (9 * 60) <= started.hour * 60 + started.minute <= (13 * 60 + 30)
    res["intraday_clock"] = intraday

    if not args.stub and wk >= 5:
        res["verdict"] = "not_trading"
        res["why"] = f"今天是星期{'一二三四五六日'[wk]}，不是交易日"
        return res

    holiday, hol_note = (None, "自測模式不查") if args.stub else fetch_holidays(today)
    res["holiday_api"] = hol_note
    if holiday:
        res["verdict"] = "not_trading"
        res["why"] = f"證交所休市表：{holiday}"
        return res

    out_dir = Path(args.out).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-TW",
                             timezone_id="Asia/Taipei")
        ctx.add_init_script(CONSENT_PRESET)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)[:200]))
        # 不用 networkidle：線上會開著即時報價的推送連線（SSE），那條連線不會結束，
        # networkidle 會一直等到逾時。改成 load 之後再等 App 與「即時」鈕真的長出來。
        pg.goto(args.url, wait_until="load", timeout=90_000)
        pg.wait_for_function("() => window.App && window.App.rotLive && document.getElementById('rotLiveBtn')",
                             timeout=90_000)
        pg.wait_for_timeout(1500)
        if args.stub:
            res["stub_codes"] = pg.evaluate(STUB)

        # ---- 今天有沒有開盤：問一檔台積電，看報價日期（mis 回的 `d`，不是執行當下的日期）
        try:
            q = pg.evaluate("async () => { const o = await window.Live.fetchQuotes(['2330']);"
                            " const x = o['2330'] || {}; return { date: x.date || '', time: x.time || '' }; }")
        except Exception as e:  # noqa: BLE001
            q = {"date": "", "time": "", "err": str(e)[:160]}
        res["probe_quote"] = q
        if q.get("date") and q["date"] != today.strftime("%Y%m%d"):
            before_open = started.hour * 60 + started.minute < 9 * 60
            res["verdict"] = "not_yet" if before_open else "not_trading"
            res["why"] = (f"還沒開盤：報價日期仍是 {q['date']}" if before_open else
                          f"報價日期停在 {q['date']}，今天沒有開盤（休市表：{hol_note}）")
            br.close()
            return res

        # ---- 按「即時」：用真的滑鼠點，不呼叫內部函式（要驗的就是使用者那一下）
        pg.locator("#rotLiveBtn").scroll_into_view_if_needed()
        pg.locator("#rotLiveBtn").click()
        pg.wait_for_function("() => { const s = window.App.rotLive(); return s.at > 0 || !!s.err; }",
                             timeout=60_000)
        pg.wait_for_timeout(1500)                      # 補間動畫走完，量畫上去的點
        a = pg.evaluate(SNAP)
        a["t"] = tpe_now().strftime("%H:%M:%S")
        pg.locator("#rotClock").screenshot(path=str(out_dir / "clock_A.png"))

        # ---- 等 2.5 分鐘：頁面自己的計時器每 60 秒跑一輪，這裡只記錄它跑了幾輪
        ticks, last_at, t_end = [], a["state"]["at"], time.time() + args.wait
        while time.time() < t_end:
            time.sleep(5)
            s = pg.evaluate("() => { const s = window.App.rotLive(); return { at: s.at, q: s.quoteAt, err: s.err }; }")
            if s["at"] != last_at:
                ticks.append({"t": tpe_now().strftime("%H:%M:%S"), "quoteAt": s["q"], "err": s["err"]})
                last_at = s["at"]
        pg.wait_for_timeout(1500)
        b = pg.evaluate(SNAP)
        b["t"] = tpe_now().strftime("%H:%M:%S")
        pg.locator("#rotClock").screenshot(path=str(out_dir / "clock_B.png"))
        br.close()

    res.update({"A": a, "B": b, "ticks": ticks, "pageerrors": errors[:10]})
    return judge(res, intraday or args.stub)


def judge(res: dict, strict: bool) -> dict:
    a, b = res["A"], res["B"]
    sa, sb = a["state"], b["state"]
    checks = []

    def add(key, label, passed, detail, gate=True):
        checks.append({"key": key, "label": label, "pass": bool(passed), "detail": detail,
                       "gate": gate})

    got = all(s.get("on") and (s.get("hit") or 0) > 0 and not s.get("err") for s in (sa, sb))
    add("fetch", "① 真的抓到報價（hit>0、沒有錯誤訊息）", got,
        f"A：{sa.get('hit')}/{sa.get('codes')} 檔、{sa.get('reqs')} 個請求、錯誤「{sa.get('err') or '無'}」；"
        f"B：{sb.get('hit')}/{sb.get('codes')} 檔、錯誤「{sb.get('err') or '無'}」")
    add("quote", "② 報價時間有前進（兩次 quoteAt 不同）", sa.get("quoteAt") != sb.get("quoteAt"),
        f"{sa.get('quoteAt') or '—'} → {sb.get('quoteAt') or '—'}（頁面自己跑了 {len(res['ticks'])} 輪）",
        gate=strict)
    mv = moved_points(a["drawn"], b["drawn"])
    live_n = sum(1 for r in mv if r["live"])
    # 只數「即時續算的點」有沒有動：自動桶（ETF、〇〇・其他）與抓不到報價的族群本來就停在盤後，
    # 把它們算進分母只會讓「有在動」的比例看起來比較差，算進分子則是灌水 —— 兩邊都不准。
    n_moved = sum(1 for r in mv if r["live"] and r["d"] > 1e-4)
    add("move", "③ 時鐘上的族群點真的移動了", n_moved > 0,
        f"盤上 {len(mv)} 個族群點裡有 {live_n} 個是即時續算的點，其中 {n_moved} 個兩次之間有移動"
        f"（另外 {len(mv) - live_n} 個是自動桶或抓不到報價的族群，設計上停在盤後）",
        gate=strict)
    if a.get("hasRlvState") and sa.get("pts") and sb.get("pts"):
        dm = moved_points(sa["pts"], sb["pts"])
        res["data_moved_top"] = dm[:5]
    ta = (a["top"] or [{}])[0].get("name"), (b["top"] or [{}])[0].get("name")
    add("rank", "④ 「今天被推得最多」第一名", True,
        f"{ta[0] or '—'} → {ta[1] or '—'}（{'換人了' if ta[0] != ta[1] else '沒換'}）；"
        f"右邊「資金流向排行」第一名 {a.get('rankTop') or '—'} → {b.get('rankTop') or '—'}"
        "（這張排行吃的是**盤後**逐日佔比，設計上不跟即時走）", gate=False)
    cov = sb.get("cover")
    add("cover", "⑤ 涵蓋率", True,
        f"{cov:.1f}%" if isinstance(cov, (int, float)) else "這一輪沒取到分母（證交所總成交值）", gate=False)
    res["checks"] = checks
    res["moved_top"] = mv[:5]
    failed = [c for c in checks if c["gate"] and not c["pass"]]
    res["verdict"] = "fail" if failed else ("pass" if strict else "pass_off_hours")
    return res


def summary_md(res: dict) -> str:
    v = res.get("verdict")
    head = {"pass": "✅ 盤中即時真的在動", "fail": "❌ 盤中即時沒有在動",
            "pass_off_hours": "✅ 抓得到報價（但現在不是盤中，②③ 只列出來不判定）",
            "not_trading": "⏸ 今天不是交易日", "not_yet": "⏳ 還沒開盤"}.get(v, str(v))
    L = [f"### 資金輪動「即時」盤中巡檢：{head}", "",
         f"- 開始（台北）：{res['started']}　網址：{res['url']}" + ("　**（自測：假報價）**" if res.get("stub") else "")]
    if res.get("why"):
        L += [f"- {res['why']}", "", "非交易日不判定，這不是失敗。"]
        return "\n".join(L) + "\n"
    a, b = res["A"], res["B"]
    L += [f"- 快照 A {a['t']}／快照 B {b['t']}；休市表：{res.get('holiday_api', '—')}；"
          f"網站{'有' if a.get('hasRlvState') else '**還沒有**'} `App.rlvState()`",
          "", "| 判定 | 結果 | 細節 |", "|---|---|---|"]
    for c in res["checks"]:
        mark = ("✅" if c["pass"] else "❌") if c["gate"] else ("ℹ️" if c["pass"] else "⚠")
        L.append(f"| {c['label']} | {mark} | {c['detail']} |")
    L += ["", "**畫上去的點位移最大的 5 個族群**（強弱／動能的資料單位；兩次快照之間）", "",
          "| 族群 | 位移 | Δ強弱 | Δ動能 |", "|---|---|---|---|"]
    for r in res["moved_top"]:
        L.append(f"| {r['name']} | {r['d']:.4f} | {r['dx']:+.4f} | {r['dy']:+.4f} |")
    if res["ticks"]:
        L += ["", "頁面自己跑的輪次：" + "、".join(f"{t['t']}（報價 {t['quoteAt']}）" for t in res["ticks"])]
    if res.get("pageerrors"):
        L += ["", "⚠ 頁面錯誤：" + "；".join(res["pageerrors"][:3])]
    if res["verdict"] == "fail":
        L += ["", "查的順序：",
              "1. ① 紅 → 看「盯即時報價代理（Worker）」那條工作流；錯誤訊息就是畫面上狀態列那一句。",
              "2. ① 綠但 ② 紅 → 報價時間沒前進：Worker 是不是回了快取？（`/quote` 不該快取）",
              "3. ②綠但 ③ 紅 → 報價有變、點卻沒動：看 app.js 的 `rlvCompute`／`rlvRedraw`。"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default=LIVE_URL)
    ap.add_argument("--wait", type=int, default=150, help="兩次快照之間等幾秒（預設 150＝約兩輪）")
    ap.add_argument("--out", default="probe-out/live_rotation.json")
    ap.add_argument("--summary", default=os.environ.get("GITHUB_STEP_SUMMARY", ""))
    ap.add_argument("--stub", action="store_true", help="本機自測：換成會變動的假報價")
    args = ap.parse_args()
    try:
        res = run(args)
    except Exception as e:  # noqa: BLE001 — 打不開網站也是「真的壞了」，一樣要寫進摘要
        res = {"url": args.url, "started": tpe_now().strftime("%Y-%m-%d %H:%M:%S"),
               "verdict": "fail", "why": f"巡檢本身跑不完：{type(e).__name__}: {str(e)[:300]}"}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = summary_md(res)
    if res.get("verdict") == "fail" and res.get("why"):
        md = md.replace("非交易日不判定，這不是失敗。", "**這是失敗**：巡檢沒有跑到判定那一步。")
    print(md)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(md)
    return 1 if res.get("verdict") == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
