# 辦公室效能（2026-11-15，擁有者：「進入辦公室畫面有點慢」「4 倍速會卡頓」）
#   根因與修法（細節見 docs/ai_office/plan.md 的 P1／P2 與 main.js、newchar.js、office_character.js 的註解）：
#     · 4×：主迴圈每格把模擬切成 ⌈模擬秒數 / 0.034⌉ 個子步，以前每個子步每位角色都做一次完整的「姿勢內插＋腳 IK＋接地投影（蒙皮頂點）＋臉」，
#       那些只影響畫面、只有最後一步會被畫出來。現在 env.draw 只在最後一個子步為真，前面幾步只推進物理；臉與動畫計時拿到累積的全部時間。
#     · 進場：角色取椅子顏色時，每位都把整個場景約 20 萬個頂點轉成世界座標再比對（開場合計約 800 萬次）→ kit.js 的共用索引（結果逐位相同）；
#       模型、個性檔、設定檔與深層模組在 world.html 先預載（不用等 main.js 一層層 import）；房子蓋好先畫一張、載入提示縮成底部小字。
#   棘輪（容器是軟體繪圖、又常有別的測試同時在跑，所以絕對毫秒只當紀錄；門檻用「同一頁裡的相對比例」與「確定性的工作量」）：
#     · 4× 每格（30fps、4 個子步）的模擬成本 ÷ 1× 每格（1 個子步）≤ 2.6（修前約 4.3，修後約 1.7）
#     · 4× 每格每位新模型角色的完整姿態計算（controller.render）次數 ≤ 1（修前 = 子步數 4）
#     · 首次可互動（第一個正式畫面）≤ 30 秒；房子比角色先畫出來（boot.scene 早於 boot.chars）
#     · world.html 預載的每一個檔案都存在（不能預載到 404）

_BENCH = """([sec, n]) => { const W = __world, o = []; for (let r = 0; r < n; r++) { const a = performance.now(); W.advance(sec, 0.034); o.push(performance.now() - a); } o.sort((a, b) => a - b); return o[Math.floor(o.length / 2)]; }"""
_RENDERS = """(sec) => { const W = __world, cs = [...W.chars.values(), ...(W.pets || [])].filter(c => c.newModel && c.inner && c.inner.ctl);
  const f0 = cs.map(c => c.inner.ctl.debug.frames); W.advance(sec, 0.034); const per = cs.map((c, i) => c.inner.ctl.debug.frames - f0[i]); return { n: cs.length, max: Math.max(0, ...per), sum: per.reduce((a, b) => a + b, 0) }; }"""


def t_office_perf(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 1280, "height": 720})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(180000); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    try:
        pg.goto(root + "/office/world.html?ambient=0", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.perf", 120000)
        ok("辦公室效能：頁面載入", got)
        if not got:
            return
        bt = pg.evaluate("() => { const b = __world.perf.boot; return { ...b, t0: b.ready - b.firstFrame }; }")
        ready = round(bt["ready"]); print(f"    開場（毫秒，自導覽起算）：資料到齊 {round(bt['assetsAt'])}、房子畫出 {round(bt['t0'] + bt.get('scene', -1e9))}、角色就座 {round(bt['t0'] + bt['chars'])}、第一個正式畫面 {ready}")
        ok(f"辦公室效能：首次可互動 {ready} 毫秒（門檻 30000）", ready <= 30000, bt)
        ok("辦公室效能：房子比角色先畫出來（載入提示縮成底部小字）", "scene" in bt and bt["scene"] < bt["chars"], bt)
        # 預載清單：每一條都要真的存在
        links = pg.evaluate("() => [...document.querySelectorAll('link[rel=modulepreload],link[rel=preload]')].map(l => l.href)")
        bad = pg.evaluate("async (u) => { const out = []; for (const x of u) { try { const r = await fetch(x, { method: 'HEAD' }); if (!r.ok) out.push([x, r.status]); } catch (e) { out.push([x, String(e)]); } } return out; }", links)
        ok(f"辦公室效能：world.html 預載 {len(links)} 個檔案全部存在", len(links) >= 20 and not bad, bad[:5])
        # 每格模擬成本：暫停畫面推進（speed=0），用 W.advance 模擬「一格畫面的子步」
        pg.evaluate("() => { __world.speed = 0; }"); pg.wait_for_timeout(500)
        pg.evaluate(_BENCH, [1 / 60, 8]); pg.evaluate(_BENCH, [4 / 30, 8])   # 暖身
        x1 = min(pg.evaluate(_BENCH, [1 / 60, 30]) for _ in range(2)); x4 = min(pg.evaluate(_BENCH, [4 / 30, 30]) for _ in range(2)); x4b = min(pg.evaluate(_BENCH, [4 / 60, 30]) for _ in range(2))
        ratio = x4 / max(0.05, x1)
        print(f"    每格模擬（毫秒，中位數）：1×＝{x1:.2f}、4×（60fps，2 子步）＝{x4b:.2f}、4×（30fps，4 子步）＝{x4:.2f}；比例 {ratio:.2f}")
        ok(f"辦公室效能：4× 每格模擬 ÷ 1× 每格 = {ratio:.2f}（門檻 2.6；修前約 4.3）", ratio <= 2.6, (x1, x4))
        r = pg.evaluate(_RENDERS, 4 / 30)
        ok(f"辦公室效能：4× 一格（4 子步）裡每位新模型角色只算一次完整姿態（{r['n']} 位，最多 {r['max']} 次）", r["n"] >= 3 and r["max"] <= 1, r)
        r1 = pg.evaluate(_RENDERS, 1 / 60)
        ok("辦公室效能：1× 一格裡每位新模型角色仍然每格都更新姿態（不可漏畫）", r1["n"] >= 3 and r1["sum"] >= r1["n"] - 1, r1)
        # 4× 實際跑幾秒：沒有主迴圈例外、角色照常在動
        pg.evaluate("() => { __world.speed = 4; __world.director.ambient = true; }"); pg.wait_for_timeout(6000)
        st = pg.evaluate("() => ({ err: __world.loopErr || 0, nan: [...__world.chars.values()].filter(c => !Number.isFinite(c.object3D.position.x) || !Number.isFinite(c.object3D.position.z)).length })")
        ok("辦公室效能：4× 跑 6 秒沒有主迴圈例外、沒有角色位置變 NaN", st["err"] == 0 and st["nan"] == 0, st)
        ok("辦公室效能：沒有頁面錯誤", not errs, errs[:3])
    finally:
        c.close()


register("辦公室效能", lambda pg, b, base, code: t_office_perf(b, base))
