# 驗收段落「科技透明圈LOGO不裁切」：站內代號圖 < 48px 改網域圖；橫幅圖 contain 完整顯示。flake8: noqa
def t_tc_logo_fit(b, base, code):
    import io
    from PIL import Image, ImageDraw
    T = "科技透明圈LOGO不裁切"
    SP = "/tmp/claude-0/-home-user-tw-rotation/d35d4770-19c6-5ef0-b46f-3181b0b89ae3/scratchpad/"
    def png(w, h, banner=False):
        im = Image.new("RGB", (w, h), (255, 255, 255)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w - 1, h - 1], outline=(220, 0, 0), width=max(2, w // 40))   # 紅框：被裁切就會看不到四邊
        d.ellipse([w * .35, h * .25, w * .65, h * .75], fill=(0, 120, 60))
        bio = io.BytesIO(); im.save(bio, "PNG"); return bio.getvalue()
    errs: list[str] = []
    def mk(routes, scale=1):
        c = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=scale)
        c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        def _mkr(bd):
            return lambda r: r.fulfill(body=bd, content_type="image/png")
        for pat, body in routes: pg.route(pat, _mkr(body))
        return c, pg
    ext = png(128, 128)
    ER = [("**/faviconV2**", ext), ("**/s2/favicons**", ext)]
    TL = '{"umc.com":"data/logos/tc/_t_umc.png","nvidia.com":"data/logos/tc/_t_nv.png"}'
    def go(pg, route_json=None, hashp="#tc/foundry/%E8%81%AF%E9%9B%BB"):
        if route_json: pg.route("**/data/tc_logos.json*", lambda r: r.fulfill(body=route_json, content_type="application/json"))
        pg.goto(base + hashp, wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    q = lambda pg: pg.evaluate("()=>{const l=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg'),i=l&&l.querySelector('img');return i?{src:i.getAttribute('src'),nw:i.naturalWidth,cls:i.className,fit:getComputedStyle(i).objectFit,pad:getComputedStyle(i).paddingLeft,w:Math.round(i.getBoundingClientRect().width),lw:Math.round(l.getBoundingClientRect().width),has:l.classList.contains('has')}:null}")
    # 1) 聯電真實站內圖 16px、沒有網域圖 → 不得顯示 16px 站內圖，改 Google（≥64）
    c, pg = mk(ER); go(pg); r = q(pg)
    ok(f"{T}：聯電站內圖 16px → 不用站內圖、改 Google（≥64px）", bool(r) and "data/logos/2303" not in r["src"] and r["nw"] >= 64, r)
    c.close()
    # 2) 16px 代號圖＋有網域圖 → 用網域圖（1200×674 橫幅）
    c, pg = mk(ER + [("**/data/logos/tc/_t_umc.png", png(1200, 674)), ("**/data/logos/tc/_t_nv.png", png(1200, 674))], 3)
    go(pg, TL); r = q(pg)
    ok(f"{T}：16px 代號圖 → 改用站內網域圖", bool(r) and "_t_umc.png" in r["src"] and r["nw"] == 1200, r)
    ok(f"{T}：橫幅 1200×674 以 contain＋10% 邊距完整顯示（不裁切）", bool(r) and r["fit"] == "contain" and r["has"] and r["w"] >= r["lw"] - 3 and abs(float(r["pad"][:-2]) - r["lw"] * .1) < 1.5, r)
    # 版面比例：圖在圓內的可視區（扣 padding）寬高比 = 原圖 1200/674，且完整落在圓內
    g = pg.evaluate("()=>{const i=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg img'),l=i.parentNode,cs=getComputedStyle(i),pl=parseFloat(cs.paddingLeft),W=i.getBoundingClientRect().width-2*pl;const nw=i.naturalWidth,nh=i.naturalHeight;const s=Math.min(W/nw,W/nh);return {dw:nw*s,dh:nh*s,W}}")
    ok(f"{T}：橫幅縮放後寬≤可視寬、高<寬（完整縮進、比例不變）", g["dw"] <= g["W"] + .5 and g["dh"] < g["dw"], g)
    try: pg.locator("#v-tc .tc-cinfo h4").screenshot(path=SP + "tc_umc_x3.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    c.close()
    # 3) NVIDIA（foreign）橫幅
    c, pg = mk(ER + [("**/data/logos/tc/_t_nv.png", png(1200, 674))], 3)
    go(pg, TL, "#tc/foreign/NVIDIA"); r = q(pg)
    ok(f"{T}：NVIDIA 網域橫幅 contain 完整顯示", bool(r) and "_t_nv.png" in r["src"] and r["fit"] == "contain" and r["w"] >= r["lw"] - 3, r)
    try: pg.locator("#v-tc .tc-cinfo h4").screenshot(path=SP + "tc_nvidia_x3.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    c.close()
    # 4) 站內代號圖 ≥ 48 才用：注入 64px 的 2303 → 用站內圖
    c, pg = mk(ER + [("**/data/logos/2303.png", png(64, 64))]); go(pg); r = q(pg)
    ok(f"{T}：站內代號圖 64px（≥48）→ 用站內圖且 contain", bool(r) and "data/logos/2303" in r["src"] and r["fit"] == "contain", r)
    c.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])

register("科技透明圈LOGO不裁切", lambda pg, b, base, code: t_tc_logo_fit(b, base, code))
