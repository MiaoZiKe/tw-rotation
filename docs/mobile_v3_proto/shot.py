"""手機版 v3 原型的截圖＋操作驗收（docs/mobile_v3_spec.md §6）：390 與 360，is_mobile＋has_touch＋DPR2。
每一項驗「畫面真的變了」，並量一屏可讀性（關鍵元素 bottom ≤ 可視高度 − 底部導覽）。

用法（repo 根目錄）：python docs/mobile_v3_proto/shot.py
截圖輸出到 docs/mobile_v3_proto/_shots/（不進版控）。"""
import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import serve  # noqa: E402  同一個資料夾的原型伺服器

OUT = str(HERE / '_shots')
os.makedirs(OUT, exist_ok=True)
serve.serve(block=False)
U = f'http://127.0.0.1:{serve.PORT}/proto/index.html'
NAV = 58
checks = []


def ok(name, cond, detail=''):
    checks.append((name, bool(cond), detail))
    print(('OK  ' if cond else 'FAIL'), name, detail)


def bottom(pg, sel):
    return pg.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(sel)});if(!e)return null;const r=e.getBoundingClientRect();return [Math.round(r.top),Math.round(r.bottom)]}})()")


with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
    for w, h in [(390, 844), (360, 780)]:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        vis = h - NAV
        # ---------------- 總覽 ① 足跡輪盤
        pg.goto(U + '#ov'); pg.wait_for_timeout(1800)
        pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(2000)
        pg.screenshot(path=f'{OUT}/ov1_radar_{w}.png')
        rb = bottom(pg, '.p-radar'); fb = bottom(pg, '.p-focus')
        ok(f'[{w}] 總覽①：輪盤＋焦點數字同一屏', rb and fb and fb[1] <= vis, f'輪盤 {rb} 焦點 {fb} 可視 {vis}')
        ok(f'[{w}] 整頁沒有橫向捲動', pg.evaluate("document.documentElement.scrollWidth") <= w)
        sel0 = pg.evaluate("document.querySelector('.p-rhost').dataset.sel")
        # 點另一顆：取第三顆點的座標
        pt = pg.evaluate("(()=>{const g=[...document.querySelectorAll('.p-radar svg g[data-g]')][2];const c=g.querySelectorAll('circle')[1].getBoundingClientRect();return [c.left+c.width/2,c.top+c.height/2,g.dataset.g]})()")
        pg.touchscreen.tap(pt[0], pt[1]); pg.wait_for_timeout(300)
        sel1 = pg.evaluate("document.querySelector('.p-rhost').dataset.sel")
        ok(f'[{w}] 點輪盤上的點 → 焦點換成那一顆', sel1 == pt[2] and sel1 != sel0, f'{sel0} → {sel1}')
        n0 = int(pg.evaluate("document.querySelector('.p-rhost').dataset.shown"))
        pg.locator('.qb[data-quad="improving"]').tap(); pg.wait_for_timeout(300)
        n1 = int(pg.evaluate("document.querySelector('.p-rhost').dataset.shown"))
        ok(f'[{w}] 點角落「改善」→ 只剩改善的點', n1 < n0, f'{n0} → {n1}')
        pg.screenshot(path=f'{OUT}/ov1_quad_{w}.png')
        pg.locator('.qb[data-quad="improving"]').tap(); pg.wait_for_timeout(200)
        # 「?」打開、點背景關閉
        pg.locator('.p-q[data-q="rot"]').tap(); pg.wait_for_timeout(250)
        opened = pg.evaluate("!document.getElementById('pPop').hidden")
        pg.screenshot(path=f'{OUT}/ov1_help_{w}.png')
        pg.touchscreen.tap(w / 2, h - NAV - 20); pg.wait_for_timeout(250)
        closed = pg.evaluate("document.getElementById('pPop').hidden")
        ok(f'[{w}] 「?」點開說明、點背景關閉', opened and closed)
        # ---------------- 總覽 ② 大盤合併圖
        pg.locator('.p-steps button[data-step="1"]').tap(); pg.wait_for_timeout(900)
        ok(f'[{w}] 步驟記進 localStorage', pg.evaluate("localStorage.getItem('p3.step')") == '1')
        pg.screenshot(path=f'{OUT}/ov2_idx_{w}.png')
        cb = bottom(pg, '#pIdxChart'); nb = bottom(pg, '#pIdxNum')
        ok(f'[{w}] 大盤：數字與整張圖同一屏', cb and cb[1] <= vis and nb[0] >= 0, f'數字 {nb} 圖 {cb} 可視 {vis}')
        k0 = pg.evaluate("document.getElementById('pIdx').dataset.cur")
        pg.locator('#pIdxSw button[data-i="1"]').tap(); pg.wait_for_timeout(400)
        k1 = pg.evaluate("document.getElementById('pIdx').dataset.cur")
        px1 = pg.evaluate("document.querySelector('#pIdxNum .px').textContent")
        ok(f'[{w}] 點「櫃買」→ 圖換成櫃買', k0 == 'TSE' and k1 == 'OTC', f'{k0} → {k1}（{px1}）')
        # 左右滑
        box = pg.locator('#pIdxChart').bounding_box()
        pg.dispatch_event('#pIdxChart', 'touchstart', {'touches': [{'identifier': 1, 'clientX': box['x'] + 300, 'clientY': box['y'] + 150}]}) if False else None
        pg.evaluate("""(()=>{const el=document.getElementById('pIdxChart');const r=el.getBoundingClientRect();
          const mk=(x)=>new Touch({identifier:1,target:el,clientX:r.left+x,clientY:r.top+150});
          el.dispatchEvent(new TouchEvent('touchstart',{touches:[mk(300)],changedTouches:[mk(300)],bubbles:true}));
          el.dispatchEvent(new TouchEvent('touchend',{touches:[],changedTouches:[mk(120)],bubbles:true}));})()""")
        pg.wait_for_timeout(400)
        k2 = pg.evaluate("document.getElementById('pIdx').dataset.cur")
        ok(f'[{w}] 在圖上往左滑 → 換下一張（台指期）', k2 == 'FUT', f'{k1} → {k2}')
        pg.locator('#pNight').tap(); pg.wait_for_timeout(300)
        ok(f'[{w}] 台指期切夜盤', pg.evaluate("document.getElementById('pIdx').dataset.cur") == 'FUT_N')
        pg.screenshot(path=f'{OUT}/ov2_fut_{w}.png')
        # ---------------- 資金流向
        pg.locator('#pNav button[data-go="flow"]').tap(); pg.wait_for_timeout(1800)
        pg.screenshot(path=f'{OUT}/flow_rot_{w}.png')
        rk = bottom(pg, '#pRank li:nth-child(5)'); rd = bottom(pg, '.p-radar')
        ok(f'[{w}] 資金流向：輪盤＋排行前 5 同一屏', rk and rk[1] <= vis, f'輪盤 {rd} 排行第5列 {rk} 可視 {vis}')
        g3 = pg.evaluate("document.querySelectorAll('#pRank li')[3].dataset.g")
        pg.locator('#pRank li').nth(3).tap(); pg.wait_for_timeout(300)
        ok(f'[{w}] 點排行第 4 列 → 輪盤／焦點跟著換', pg.evaluate("document.querySelector('.p-card').dataset.sel") == g3, g3)
        n0 = int(pg.evaluate("document.querySelector('.p-card').dataset.n"))
        pg.locator('#pFilt').tap(); pg.wait_for_timeout(300)
        pg.screenshot(path=f'{OUT}/flow_filter_{w}.png')
        pg.locator('#pShChain a[data-c="semiconductor"]').tap(); pg.wait_for_timeout(400)
        n1 = int(pg.evaluate("document.querySelector('.p-card').dataset.n"))
        ok(f'[{w}] 篩選「半導體」→ 輪盤族群數變少', n1 < n0, f'{n0} → {n1}')
        ok(f'[{w}] 篩選寫進 localStorage', pg.evaluate("localStorage.getItem('p3.flow.chain')") == 'semiconductor')
        pg.screenshot(path=f'{OUT}/flow_semi_{w}.png')
        pg.locator('#pFilt').tap(); pg.wait_for_timeout(200); pg.locator('#pShChain a[data-c=""]').tap(); pg.wait_for_timeout(300)
        pg.locator('.p-segs button[data-seg="資金去向"]').tap(); pg.wait_for_timeout(700)
        c0 = pg.evaluate("document.querySelectorAll('.p-drill li[data-k]').length")
        pg.locator('.p-drill li[data-k]', has_text='半導體').first.tap(); pg.wait_for_timeout(300)
        c1 = pg.evaluate("document.querySelectorAll('.p-drill li[data-k]').length")
        ok(f'[{w}] 資金去向：點產業鏈 → 展開族群', c1 > c0, f'{c0} → {c1} 列')
        pg.screenshot(path=f'{OUT}/flow_drill_{w}.png')
        pg.locator('.p-segs button[data-seg="法人"]').tap(); pg.wait_for_timeout(900)
        pg.locator('#pInstSw button[data-k="trust"]').tap(); pg.wait_for_timeout(300)
        ok(f'[{w}] 法人：切投信', pg.evaluate("document.querySelector('.p-card').dataset.k") == 'trust')
        pg.screenshot(path=f'{OUT}/flow_inst_{w}.png')
        pg.locator('.p-segs button[data-seg="集中度"]').tap(); pg.wait_for_timeout(900)
        pg.screenshot(path=f'{OUT}/flow_conc_{w}.png')
        # ---------------- 剖析圖（平面）
        pg.locator('#pNav button[data-go="dg"]').tap(); pg.wait_for_timeout(2500)
        pg.screenshot(path=f'{OUT}/dg2d_fit_{w}.png')
        n = pg.evaluate("+document.getElementById('pNums').dataset.n"); ov = pg.evaluate("+document.getElementById('pNums').dataset.overlap")
        cards_vis = pg.evaluate("[...document.querySelectorAll('.dgcards .dgc')].filter(e=>e.getBoundingClientRect().height>0).length")
        ok(f'[{w}] 剖析圖：只留編號（字卡 0 張可見）', n > 0 and cards_vis == 0, f'編號 {n} 個、可見字卡 {cards_vis}、重疊對數 {ov}')
        small = pg.evaluate("[...document.querySelectorAll('.p-num')].filter(b=>{const r=b.getBoundingClientRect();return r.width<28}).length")
        ok(f'[{w}] 編號鈕 ≥ 28px（觸控範圍 44px）', small == 0)
        stg = bottom(pg, '.p-dgstage')
        ok(f'[{w}] 整張圖在一屏內', stg and stg[1] <= vis, f'圖 {stg} 可視 {vis}')
        pg.locator('.p-num').nth(2).tap(); pg.wait_for_timeout(400)
        no = pg.evaluate("document.getElementById('pSheet').dataset.no"); shown = pg.evaluate("!document.getElementById('pSheet').hidden")
        ok(f'[{w}] 點編號 03 → 抽屜顯示 03 的說明', shown and no == '03', f'抽屜編號 {no}')
        btn = bottom(pg, '.p-num.on'); sh = pg.evaluate("document.getElementById('pSheet').getBoundingClientRect().top")
        ok(f'[{w}] 被選的編號沒有被抽屜蓋住', btn and btn[1] <= sh, f'編號 {btn} 抽屜頂 {round(sh)}')
        pg.screenshot(path=f'{OUT}/dg2d_sheet_{w}.png')
        pg.locator('.p-shnav button[data-d="1"]').tap(); pg.wait_for_timeout(300)
        ok(f'[{w}] 抽屜 › → 下一個編號 04', pg.evaluate("document.getElementById('pSheet').dataset.no") == '04')
        pg.touchscreen.tap(w / 2, 70); pg.wait_for_timeout(300)
        ok(f'[{w}] 點背景關閉抽屜', pg.evaluate("document.getElementById('pSheet').hidden"))
        pg.locator('.p-q[data-q="dg"]').tap(); pg.wait_for_timeout(250)
        pg.screenshot(path=f'{OUT}/dg2d_help_{w}.png')
        pg.touchscreen.tap(w / 2, h - NAV - 10); pg.wait_for_timeout(200)
        pg.locator('#pDgZoom button[data-z="big"]').tap(); pg.wait_for_timeout(600)
        sw = pg.evaluate("[document.getElementById('pDgScroll').scrollWidth, document.getElementById('pDgScroll').clientWidth]")
        ov2 = pg.evaluate("+document.getElementById('pNums').dataset.overlap")
        ok(f'[{w}] 放大 → 圖變寬可左右滑', sw[0] > sw[1] * 1.5, f'{sw}，重疊對數 {ov2}')
        pg.screenshot(path=f'{OUT}/dg2d_big_{w}.png')
        pg.locator('#pDgZoom button[data-z="fit"]').tap(); pg.wait_for_timeout(300)
        # 換一張圖
        pg.locator('#pDgPick button[data-id="hbm"]').tap(); pg.wait_for_timeout(1500)
        pg.screenshot(path=f'{OUT}/dg2d_hbm_{w}.png')
        ok(f'[{w}] 換 HBM → 編號重算', pg.evaluate("+document.getElementById('pNums').dataset.n") > 0, str(pg.evaluate("document.getElementById('pNums').dataset.n")))
        # ---------------- 3D
        dis = pg.evaluate("document.querySelector('#pDgMode button[data-m=\"3d\"]').disabled")
        if not dis:
            pg.locator('#pDgMode button[data-m="3d"]').tap()
            pg.wait_for_function("+(document.getElementById('p3d').dataset.n||0) > 0 && document.querySelectorAll('#p3d .p-num').length > 0", timeout=20000); pg.wait_for_timeout(800)
            n3 = pg.evaluate("+(document.getElementById('p3d').dataset.n||0)")
            lbl = pg.evaluate("[...document.querySelectorAll('#p3d .lbl3d')].filter(e=>e.getBoundingClientRect().height>0).length")
            nos = pg.evaluate("document.querySelectorAll('#p3d .p-num').length")
            ov3 = pg.evaluate("+(document.querySelector('#p3d .p-num3')||{dataset:{}}).dataset.overlap")
            old = pg.evaluate("[...document.querySelectorAll('#p3d .ld-no')].filter(e=>getComputedStyle(e).display!=='none').length")
            ok(f'[{w}] 3D：字卡 0 張、畫布上有編號、不互相擋', n3 > 0 and lbl == 0 and nos == n3 and ov3 == 0 and old == 0, f'編號資料 {n3}、可見字卡 {lbl}、HTML 編號 {nos}、重疊對數 {ov3}、站上舊圓點可見 {old}')
            pg.screenshot(path=f'{OUT}/dg3d_{w}.png')
            if nos:
                pt = pg.evaluate("(()=>{const g=document.querySelectorAll('#p3d .p-num')[0];const r=g.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2,g.textContent.trim()]})()")
                pg.touchscreen.tap(pt[0], pt[1]); pg.wait_for_timeout(400)
                ok(f'[{w}] 3D：點編號 → 抽屜', pg.evaluate("document.getElementById('pSheet').dataset.no") == pt[2] and pg.evaluate("!document.getElementById('pSheet').hidden"), pt[2])
                pg.screenshot(path=f'{OUT}/dg3d_sheet_{w}.png')
                pg.touchscreen.tap(w / 2, 70); pg.wait_for_timeout(200)
        else:
            ok(f'[{w}] 3D 可用', False, 'WebGL 不可用或無場景')
        ok(f'[{w}] 沒有頁面錯誤', not errs, '; '.join(errs[:3]))
        ctx.close()
print(sum(1 for c in checks if c[1]), '/', len(checks))
json.dump(checks, open(OUT + '/checks.json', 'w'), ensure_ascii=False, indent=1)
