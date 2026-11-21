# `_uitest.py` 驗收草稿：② 當根 K 棒即時更新 ／ ③ 歷史無限回溯

> 這份是**草稿**。`scripts/_uitest.py` 這批不准動（有別人在改），所以段落先寫在這裡，
> 由 CEO 之後併進去。段落名建議：`K線即時當根`（②）與 `K線歷史回溯`（③），
> 對照表歸在「個股頁（K 線、多週期、營收、籌碼）」那一列，
> 也就是 `--only 個股,K線縮放,K線即時當根,K線歷史回溯`。
>
> 可執行的完整版在 `/tmp` 不會留，實作時直接照下面的程式碼抄 ——
> 這些斷言我已經在 1440／800／390 三個寬度各跑過一輪，全綠（47 條 × 3）。

## 為什麼要用計數器，不能用眼睛看

② 的需求是「**只更新最後那一根**，不重畫整張圖」。
「有沒有重畫」用截圖是驗不出來的 —— 重畫一次跟不重畫長得一模一樣。
所以 `chart.js` 上掛了計數器 `KChart.last.stats`：

| 欄位 | 什麼時候 +1 | 驗收時要它怎樣 |
|---|---|---|
| `setData` | 整條 K 棒重灌（換股／換週期／③ 回補） | 灌報價時**不准增加** |
| `rebuild` | 指標 series 整組重建 | 灌報價時**不准增加** |
| `tick` | 走了一次「只更新尾巴」的快路 | 灌報價時**要增加** |
| `point` | 推了幾個單點（K 棒＋各指標線） | 參考用 |

③ 用 `KChart.last.histStats()`：`{ code, added, bars, fetches, hits, done, pages }`。
`fetches` 是真的打出去的請求數，`hits` 是吃到快取的次數 —— 「會不會重抓」也一樣不准用眼睛猜。

## 段落一：`K線即時當根`（②）

```python
def t_k_live_bar(pg, base):
    pg.goto(f"{base}#stock/2330", wait_until="networkidle"); pg.wait_for_timeout(2500)
    pg.wait_for_function("() => window.KChart && window.KChart.last && window.KChart.last.data.length > 100")
    d0 = pg.evaluate(DBG)          # 見下面的 DBG
    ok("K線 圖真的畫出來了", d0["n"] > 500, d0["n"])

    # ---- 同一根：灌一筆比現價高 1.3% 的報價（形狀＝live.js normalise() 的產出）
    base_bar, prev_before, sd0 = d0["last"], d0["prev"], d0["stats"]["setData"]
    newp = round(base_bar["close"] * 1.013, 2)
    r = pg.evaluate("""(p) => window.KChart.last.applyQuote(
          { price: p.price, volume: p.vol, time: '11:02:31', date: p.date })""",
        {"price": newp, "vol": 92345, "date": base_bar["time"]})
    d1 = pg.evaluate(DBG)
    ok("② 回報「更新同一根」", r == "update", r)
    ok("② 最後那根的收盤真的變了", abs(d1["last"]["close"] - newp) < 1e-6)
    ok("② 開盤價沒被動到", d1["last"]["open"] == base_bar["open"])
    ok("② 最高價跟著抬上去", d1["last"]["high"] >= newp)
    ok("② 量換成當天累計（張×1000）", d1["last"]["volume"] == 92345 * 1000)
    ok("② 沒有多出一根", d1["n"] == d0["n"])
    ok("② 前一根一個數字都沒動", d1["prev"] == prev_before)      # ← 「沒重畫」的正面證據
    ok("② 第一根也沒動", d1["first"] == d0["first"])
    ok("② 沒有重畫整張圖", d1["stats"]["setData"] == sd0, d1["stats"])
    ok("② 走的是單點更新", d1["stats"]["tick"] > d0["stats"]["tick"])
    ok("② 指標跟著重算（MA20 變了）", d1["ma20"] != d0["ma20"])
    ok("② KD 也跟著動", d1["kdK"] != d0["kdK"])

    # ---- 跨根：日期換成隔天 → 要「開一根新的」，不是把舊的改掉
    nxt = 隔一天(base_bar["time"]); p2 = round(newp * 1.004, 2)
    r2 = pg.evaluate("""(p) => window.KChart.last.applyQuote(
          { price: p.price, volume: 1200, time: '09:01:05', date: p.date })""",
        {"price": p2, "date": nxt})
    d2 = pg.evaluate(DBG)
    ok("② 回報「開了新的一根」", r2 == "new", r2)
    ok("② 真的多了一根", d2["n"] == d1["n"] + 1)
    ok("② 新的一根 開＝高＝低＝收＝報價",
       {d2["last"]["open"], d2["last"]["high"], d2["last"]["low"], d2["last"]["close"]} == {p2})
    ok("② 新的一根日期就是報價那天", str(d2["last"]["time"]) == nxt)
    ok("② 舊的那根沒有被改掉", abs(d2["prev"]["close"] - newp) < 1e-6)
    ok("② 開新棒也沒有整張重畫", d2["stats"]["setData"] == sd0)

    # ---- industry.js 真正走的那條路（LiveK.onUpdate → apply() → setBars + applyIndicators）
    res = pg.evaluate("""() => {
      const k = window.KChart.last;
      const before = JSON.parse(JSON.stringify(k.stats));
      const bars = k.bars.map(b => b.slice());
      bars[bars.length - 1][4] *= 1.02;              // 只改最後一根的收盤
      k.setBars(bars, k.tf, true); k.applyIndicators(k.cfg);
      return { before, after: JSON.parse(JSON.stringify(k.stats)), close: k.bars[k.bars.length-1][4] };
    }""")
    ok("② 呼叫端那條路也不重灌",
       res["after"]["setData"] == res["before"]["setData"]
       and res["after"]["rebuild"] == res["before"]["rebuild"], res)
```

`DBG`（放 `_uitest.py` 的小工具區）：

```js
() => {
  const k = window.KChart && window.KChart.last;
  if (!k) return null;
  const n = k.bars.length;
  const row = (b) => b ? { time: String(b[0]), open: b[1], high: b[2], low: b[3], close: b[4], volume: b[5] || 0 } : null;
  return { tf: k.tf, n, stats: JSON.parse(JSON.stringify(k.stats)),
    last: row(k.bars[n-1]), prev: row(k.bars[n-2]), first: row(k.bars[0]),
    hist: k.histStats(),
    ma20: (k.values && k.values.MA20) ? k.values.MA20[n-1] : null,
    kdK: (k.values && k.values.KD) ? k.values.KD.k[n-1] : null };
}
```

> ⚠ 不要用 `k.data[i].time` 當日期比對。Lightweight Charts 會把
> `'2026-09-22'` 就地改寫成 `{year,month,day}` 物件（它會動我們傳進去的那個物件），
> 所以日期一律讀 `k.bars`（原始陣列，它不碰）。這一條我自己踩過一次。

## 段落二：`K線歷史回溯`（③）

```python
def t_k_history(pg, base, width):
    pg.goto(f"{base}#stock/2330", wait_until="networkidle"); pg.wait_for_timeout(2500)
    # 「載入中」的表示：呼叫下去的當下（還沒 await 回來）就要看得到字
    note = pg.evaluate("() => { const k = window.KChart.last; k.loadOlder(); "
                       "const e = k._noteEl; return e ? { txt: e.textContent, shown: e.style.display !== 'none' } : null; }")
    ok("③ 有「載入中」的表示", note and note["shown"] and "載入" in note["txt"], note)
    pg.wait_for_timeout(1200)
    ok("③ 載完換成「已回補到 …」",
       "已回補到" in pg.evaluate("() => window.KChart.last._noteEl.textContent"))

    # 拉到左邊界附近，**跨過邊界那一下用真的滑鼠拖**
    pg.evaluate("() => window.KChart.last.chart.timeScale().setVisibleLogicalRange({from: 40, to: 160})")
    d3 = pg.evaluate(DBG)
    drag_right(pg, times=2)        # 見下面
    d4 = pg.evaluate(DBG)
    ok("③ 往左拖之後棒數真的變多", d4["n"] > d3["n"], (d3["n"], d4["n"]))
    ok("③ 有去抓更舊的一段", d4["hist"]["fetches"] >= 1, d4["hist"])
    ok("③ 左邊界往前推了", str(d4["first"]["time"]) < str(d3["first"]["time"]))

    # 快取：再要一次已經抓過的段落，fetches 不可以跟著一直漲
    f = d4["hist"]["fetches"]
    again = pg.evaluate("async () => { const k = window.KChart.last; await k.loadOlder(); return k.histStats(); }")
    ok("③ 抓過的不重抓", again["fetches"] <= f + 1, again)

    # 一路拖到最早一筆
    for _ in range(14):
        pg.evaluate("async () => { const k = window.KChart.last; for (let i=0;i<3;i++) await k.loadOlder(); }")
        if pg.evaluate("() => window.KChart.last.histStats().done"): break
    d5 = pg.evaluate(DBG)
    ok("③ 拖到最早一筆會停下來", d5["hist"]["done"], d5["hist"])
    ok("③ 最早一筆＝資料湖第一天 2000-01-04", str(d5["first"]["time"]) == "2000-01-04")
    f_end = d5["hist"]["fetches"]
    pg.evaluate("async () => { const k = window.KChart.last; for (let i=0;i<5;i++) await k.loadOlder(); }")
    d6 = pg.evaluate(DBG)
    ok("③ 到底之後不會再打請求", d6["hist"]["fetches"] == f_end)
    ok("③ 到底之後棒數也不再增加", d6["n"] == d5["n"])
    ok("③ 回補完指標還在", d6["ma20"] is not None)

    # 週線：回補的日線要能合成成週 K，而且是吃快取不是重抓
    pg.evaluate("() => { const b=[...document.querySelectorAll('#tfSeg button')].find(x=>x.dataset.tf==='1w'); if(b) b.click(); }")
    pg.wait_for_timeout(1800)
    pg.evaluate("async () => { const k = window.KChart.last; for (let i=0;i<8;i++) await k.loadOlder(); }")
    dw = pg.evaluate(DBG)
    ok("③ 週線也回補得到", dw["n"] > 1000 and str(dw["first"]["time"]) < "2001-01-01", dw["n"])
    ok("③ 週線直接吃快取", dw["hist"]["hits"] > 0, dw["hist"])
```

`drag_right`（真的用滑鼠拖，往右拖＝往回看更早的時間）：

```python
def drag_right(pg, times=1):
    pg.locator("#lwc").scroll_into_view_if_needed(timeout=6000)   # ★ 800/390 一定要先捲進畫面
    for _ in range(times):
        box = pg.evaluate("() => { const r = document.querySelector('#lwc').getBoundingClientRect();"
                          " return {x:r.x,y:r.y,w:r.width,h:r.height}; }")
        x0, x1, y = box["x"] + box["w"] * .18, box["x"] + box["w"] * .92, box["y"] + box["h"] * .3
        pg.mouse.move(x0, y); pg.mouse.down()
        for i in range(1, 9):
            pg.mouse.move(x0 + (x1 - x0) * i / 8, y); pg.wait_for_timeout(18)
        pg.mouse.up(); pg.wait_for_timeout(800)
```

> ⚠ 800px 與 390px 一定要先 `scroll_into_view_if_needed()`。
> 沒捲進畫面的話滑鼠按在別的東西上，圖一動也不動，看起來就像「③ 在窄畫面壞掉」——
> 我第一次跑就是這樣誤判了兩個寬度。

## 段落三：順手回歸（這批改到的東西）

```python
    # MACD 那三個指派被 // 註解吃掉的回歸（見 DECISIONS 待補的那條）
    pg.locator('.chip[data-k="rsi"]').click(); pg.wait_for_timeout(1800)
    pi = pg.evaluate("() => { const k=window.KChart.last; return { idx: k.paneIndex, "
                     "labels: [...document.querySelectorAll('#lwc .pane-labels div')].map(d=>d.textContent.slice(0,12)) }; }")
    ok("RSI 有自己的一格（不再疊在 MACD 上）", pi["idx"]["rsi"] != pi["idx"]["macd"], pi)
    ok("MACD 左上角標題回來了", any("MACD" in x for x in pi["labels"]), pi["labels"])
```

## 前置條件

③ 要有 `site/data/hist/<代號>/p*.json`。那是 `python -m pipeline.build_payload` 產出的，
所以**本機跑這一段之前要先重算 payload**（`SKIP_INTRADAY=1` 可省掉分 K，約 5 分鐘）。
沒有那些檔案時 `loadOlder()` 會安安靜靜地標成 `done`、棒數不變 ——
那會讓這一段整段變紅，而且紅的原因是「資料沒產」不是「功能壞了」，
所以段落開頭建議先 assert 一次檔案在不在：

```python
import pathlib
if not (pathlib.Path("site/data/hist/2330/p0.json")).exists():
    ok("③ 前置：歷史分頁檔已產出", False, "先跑 python -m pipeline.build_payload")
    return
```
