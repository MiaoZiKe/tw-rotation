# `_uitest.py` 驗收草稿 —— 盤中即時的 SSE 推送與退回輪詢

> 2026-09-23。`site/live.js` 改成「優先走 SSE、連不上就退回輪詢」之後要補的驗收。
> 我這一輪不准動 `scripts/_uitest.py`（有別人在改），所以先寫成草稿，由 CEO 併進去。
>
> **可執行的版本已經跑綠了**，在
> `/tmp/claude-0/-home-user-tw-rotation/75d29511-9547-5033-8c59-f68794f4c9c4/scratchpad/sse_check.py`
> （18 條全過，截圖在 `/tmp/sse/`）。下面這份是把它改寫成 `_uitest.py` 的形狀。

## 先決條件：現有的 `t_live` 要補一行 unroute

`t_live` 目前只攔 `**/quote?*`。live.js 現在啟動時會**另外開一條 EventSource 打 `/stream`**，
沒攔的話它會真的往外連 `tw-quote.kcq01010909.workers.dev`（容器連不出去 → 慢、而且 console 會有紅字）。
所以 `t_live` 開頭要加：

```python
    # /stream 沒攔的話會真的往外連；這一段驗的是輪詢那條路，直接讓它 404
    pg.route("**/stream?*", lambda r: r.fulfill(status=404, content_type="application/json",
                                                body='{"error":"not found"}'))
```

收尾一起 `pg.unroute("**/stream?*")`。

⚠ 順帶一提：`t_live` 現有的斷言**不用改**，我已經確認過
「狀態列顯示報價時間」只比對 `12:34`、「關掉自動更新」只比對 `自動已關`，
新加的 `（輪詢）`／`推送（SSE）` 後綴不會撞到它們。

## 新增段落：`即時推送`（建議段落名 `即時推送`，掛在 `盤中即時` 後面）

段落名進 `SECTIONS`：`"即時推送": lambda pg, b, base, code: t_live_sse(pg, base),`
並在 CLAUDE.md 的對照表「盤中即時／報價／分 K」那一列補上它。

```python
def t_live_sse(pg, base):
    """SSE 推送與「退回輪詢」。

    驗的不是「有沒有連上」，是**畫面上那一格的數字有沒有因此變**。
    三條路各驗一次：① 代理沒有 /stream → 退回輪詢照樣更新
                    ② SSE 推一筆 → 那一格真的變
                    ③ 連線被切斷 → 自動重連 → 補回斷線期間的值
    """
    import json as _json
    from urllib.parse import urlparse, parse_qs

    SEL_PX = "#candBody tr[data-code] [data-live='close']"
    SEL_CHG = "#candBody tr[data-code] [data-live='chg']"
    box = {"z": "999.0000", "t": "11:22:33", "conns": 0}

    def arr(ex, z, t):
        out = []
        for tok in [x for x in ex.split("|") if x]:
            try:
                code = tok.split("_", 1)[1].split(".")[0]
            except IndexError:
                continue
            out.append({"c": code, "n": "測試" + code, "ex": tok[:3], "z": z,
                        "y": "900.0000", "o": "905.0000", "h": "1000.0000",
                        "l": "890.0000", "v": "12345", "t": t, "d": "20260914"})
        return {"rtcode": "0000", "rtmessage": "OK", "msgArray": out}

    def fake_quote(route):
        q = parse_qs(urlparse(route.request.url).query)
        route.fulfill(status=200, content_type="application/json; charset=utf-8",
                      body=_json.dumps(arr((q.get("ex_ch") or [""])[0], box["z"], box["t"])))

    # ---- ① 代理沒有 /stream（＝ Worker 還沒重新部署）：一定要退回輪詢
    pg.route("**/quote?*", fake_quote)
    pg.route("**/stream?*", lambda r: r.fulfill(status=404, content_type="application/json",
                                                body='{"error":"not found"}'))
    pg.evaluate("() => { try{ localStorage.setItem('tw.live.proxy','https://fake-worker.test');"
                "localStorage.setItem('tw.live.on','1'); }catch(e){} }")
    pg.goto(base + "#overview", wait_until="load")
    pg.wait_for_timeout(2500)
    px = text(pg, SEL_PX)
    ok("SSE 連不上時畫面照樣拿到即時價（999）", "999" in px, px)
    ok("漲跌也算出來（999/900 = +11.00%）", "11.00" in text(pg, SEL_CHG), text(pg, SEL_CHG))
    ok("模式是輪詢", pg.evaluate("() => window.Live.mode") == "poll",
       pg.evaluate("() => window.Live.mode"))
    ok("狀態列寫得出現在走輪詢", "輪詢" in text(pg, "#liveState"), text(pg, "#liveState"))
    pg.wait_for_timeout(9000)     # 1+2+4+8 秒退避跑完
    ok("連不上就放棄 SSE，不會一直重試", pg.evaluate("() => window.Live.sseGaveUp") is True)
    box["z"], box["t"] = "888.0000", "12:34:56"
    click(pg, "#liveBtn", 1500)
    changed("退回輪詢後按『更新』畫面真的再變一次", px, text(pg, SEL_PX))
    ok("按更新後顯示新抓到的價格（888）", "888" in text(pg, SEL_PX), text(pg, SEL_PX))

    # ---- ② SSE 正常：推一筆 → 那一格真的變
    # Playwright 的 route.fulfill 一次送完整包 body 就關連線，剛好等於
    #「推幾筆 → 斷線」，第二次連線就是重連。用 conns 分辨第幾條。
    def fake_stream(route):
        q = parse_qs(urlparse(route.request.url).query)
        ids = (q.get("ids") or [""])[0]
        box["conns"] += 1
        z = "777.0000" if box["conns"] == 1 else "555.0000"
        body = ("retry: 1000\n\n"
                "event: hello\ndata: {\"session\":\"trade\",\"pollMs\":5000}\n\n"
                "event: quote\ndata: " + _json.dumps(arr(ids, z, "11:30:01")) + "\n\n")
        route.fulfill(status=200, content_type="text/event-stream; charset=utf-8", body=body)

    pg.unroute("**/stream?*")
    pg.route("**/stream?*", fake_stream)
    before = text(pg, SEL_PX)
    click(pg, "#liveBtn", 500)          # 手動更新會把 sseGaveUp 歸零並重開連線
    wait_until(pg, "window.Live.mode === 'sse'", 8000)
    wait_until(pg, f"(document.querySelector({SEL_PX!r})||{{}}).textContent.indexOf('777') >= 0", 8000)
    after = text(pg, SEL_PX)
    changed("SSE 推一筆之後那一格真的變了", before, after)
    ok("變成的是推送過來的價格（777）", "777" in after, after)
    ok("模式切成推送", pg.evaluate("() => window.Live.mode") == "sse")
    st = text(pg, "#liveState")
    ok("狀態列看得出現在走推送", "推送" in st and "SSE" in st, st)

    # ---- ③ 斷線 → 自動重連 → 補回斷線期間的值
    wait_until(pg, f"(document.querySelector({SEL_PX!r})||{{}}).textContent.indexOf('555') >= 0", 15000)
    ok("重連拿到的第一筆快照補回了漏掉的值（555）", "555" in text(pg, SEL_PX), text(pg, SEL_PX))
    ok("真的重連過（第二條連線成立）", box["conns"] >= 2, box["conns"])
    ok("重連後模式回到推送", pg.evaluate("() => window.Live.mode") == "sse")

    # ---- 收拾
    pg.unroute("**/quote?*"); pg.unroute("**/stream?*")
    pg.evaluate("() => { try{ localStorage.removeItem('tw.live.proxy');"
                "localStorage.removeItem('tw.live.on'); }catch(e){} }")
```

## 我在本機跑綠、但這份草稿沒涵蓋的

- **連線輪替（`bye`）**：Worker 每 4 分鐘會送 `bye` 讓前端立刻重連。
  用 `route.fulfill` 模擬得出來（body 最後放一則 `event: bye`），但要多等一輪，
  值不值得放進 `_uitest` 由 CEO 決定。
- **看門狗（連著卻不推）**：門檻是 90 秒，放進驗收會讓那一段多跑一分半，我沒寫。
- **分頁切到背景會收掉連線**：Playwright 不好造 `document.hidden`，沒寫。
