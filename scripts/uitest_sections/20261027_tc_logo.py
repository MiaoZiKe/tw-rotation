# 驗收段落「科技透明圈站內LOGO」：優先站內個股 Logo、外商才用 Google、不放大糊圖。flake8: noqa
def t_tc_logo_1027(b, base, code):
    T = "科技透明圈站內LOGO"
    errs: list[str] = []
    c = b.new_context(viewport={"width": 1440, "height": 900})
    c.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    # 外部來源一律回 128px 純色圖（排除沙箱無外網的干擾）；站內圖走真檔
    import struct, zlib
    def _png(w):
        raw = b"".join(b"\x00" + b"\x20\x80\xc0\xff" * w for _ in range(w))
        ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
        return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, w, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b"")
    for pat in ("**/faviconV2**", "**/s2/favicons**"):
        pg.route(pat, lambda r: r.fulfill(body=_png(128), content_type="image/png"))
    pg.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    src = lambda sel: pg.evaluate("(s)=>{const i=document.querySelector(s);return i?i.getAttribute('src'):null}", sel)
    s = src("#v-tc .tc-cinfo h4 .tc-lg img")
    ok(f"{T}：台積電公司頁標題 LOGO＝站內 data/logos/2330.png", bool(s) and "data/logos/2330.png" in s, s)
    ok(f"{T}：台積電標題圖真的載入（naturalWidth≥16、白底圓、字標隱藏）", pg.evaluate("()=>{const l=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg'),i=l&&l.querySelector('img');return !!i&&i.naturalWidth>=16&&l.classList.contains('has')&&i.classList.contains('ok')&&getComputedStyle(l.querySelector('i')).visibility==='hidden'}"))
    ok(f"{T}：標題 LOGO 容器 40px、不放大（顯示寬 ≤ 原圖寬）", pg.evaluate("()=>{const l=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg'),i=l.querySelector('img'),r=l.getBoundingClientRect(),q=i.getBoundingClientRect();return Math.round(r.width)===40&&q.width<=i.naturalWidth+0.5}"))
    shot = "/tmp/claude-0/-home-user-tw-rotation/d35d4770-19c6-5ef0-b46f-3181b0b89ae3/scratchpad/tsmc_logo_x3.png"
    try:
        c3 = b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=3)
        c3.add_init_script("window.TW_TC_OVERRIDE=true;try{localStorage.setItem('tw.tour','done')}catch(e){}")
        p3 = c3.new_page(); p3.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); p3.wait_for_timeout(3000)
        p3.locator("#v-tc .tc-cinfo h4").screenshot(path=shot); c3.close()
    except Exception as e:
        print("  ⚠ 截圖失敗", e)
    # 指定公司來源
    r = pg.evaluate("""async()=>{await TcLogo.ready;const o={};
      for(const [n,i] of [['台積電','foundry'],['聯發科','icdesign'],['景碩','material'],['ASML','equipment'],['NVIDIA','foreign']]){
        const d=document.createElement('div');d.innerHTML=TcLogo.html(n,i,28);const im=d.querySelector('img');o[n]=im?im.getAttribute('src'):null}
      return o}""")
    ok(f"{T}：台積電／聯發科／景碩 src 皆為站內 data/logos/*.png", all(r.get(k) and "data/logos/" in r[k] and r[k].endswith(".png") for k in ("台積電", "聯發科", "景碩")), r)
    ok(f"{T}：外商（ASML／NVIDIA）走 gstatic／s2，不含 duckduckgo", all(r.get(k) and ("gstatic" in r[k] or "google.com/s2" in r[k]) for k in ("ASML", "NVIDIA")), r)
    ok(f"{T}：程式碼已移除 DuckDuckGo 來源", pg.evaluate("()=>!TcLogo.sources.some(f=>/duckduckgo/.test(f('a.com')))&&TcLogo.sources.length===2"))
    # 157 家統計
    st = pg.evaluate("""async()=>{await TcLogo.ready;const fs=['equipment','foreign','foundry','icdesign','material','memory','odm','osat','other','panel'];const c={station:0,ext:0,txt:0},ex=[];
      const ds=await Promise.all(fs.map(f=>fetch('tc/json/'+f+'.json').then(r=>r.json())));ds.forEach(d=>(d.companies||[]).forEach(x=>TcLogo.reg(x.name,x.code)));
      ds.forEach(d=>(d.companies||[]).forEach(x=>{const p=TcLogo.plan(x.name);c[p]++;if(p==='txt')ex.push(x.name)}));return {c,ex,n:c.station+c.ext+c.txt}}""")
    print(f"  ℹ {T}：公司來源統計 共 {st['n']} 家｜站內 {st['c']['station']}｜Google s2/gstatic {st['c']['ext']}｜字標 {st['c']['txt']}（{'、'.join(st['ex'])}）")
    ok(f"{T}：統計有站內圖（≥50 家）", st["c"]["station"] >= 50, st["c"])
    # 低解析：站內圖只有 20px → 不放大、原尺寸置中；<16px → 字標
    q = c.new_page()
    q.route("**/data/logos/2330.png", lambda r: r.fulfill(body=_png(20), content_type="image/png"))
    q.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); q.wait_for_timeout(2500)
    ok(f"{T}：站內圖只有 20px → 以 20px 置中、不放大", q.evaluate("()=>{const i=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg img');return !!i&&i.classList.contains('sm')&&Math.round(i.getBoundingClientRect().width)<=20}"))
    q.close()
    q2 = c.new_page()
    q2.route("**/data/logos/2330.png", lambda r: r.fulfill(body=_png(10), content_type="image/png"))
    q2.route("**/faviconV2**", lambda r: r.abort()); q2.route("**/s2/favicons**", lambda r: r.abort())
    q2.goto(base + "#tc/foundry/%E5%8F%B0%E7%A9%8D%E9%9B%BB", wait_until="domcontentloaded"); q2.wait_for_timeout(2500)
    ok(f"{T}：站內圖只有 10px 且外部也失敗 → 字標", q2.evaluate("()=>{const l=document.querySelector('#v-tc .tc-cinfo h4 .tc-lg');return !!l&&!l.querySelector('img')&&l.dataset.lg==='txt'}"))
    q2.close()
    # 第二層：站內網域圖 tc_logos.json（模擬資料同事的產出）
    d2 = c.new_page(); d2.route("**/data/tc_logos.json*", lambda r: r.fulfill(body='{"asml.com":"data/logos/2454.png"}', content_type="application/json"))
    d2.goto(base + "#tc/stats", wait_until="domcontentloaded"); d2.wait_for_timeout(2500)
    r2 = d2.evaluate("""async()=>{await TcLogo.ready;const d=document.createElement('div');d.innerHTML=TcLogo.html('ASML','equipment',28);const i=d.querySelector('img');return [i&&i.getAttribute('src'),TcLogo.plan('ASML'),TcLogo.plan('NVIDIA')]}""")
    ok(f"{T}：網域圖（tc_logos.json）有就用、排在 Google 之前", r2[0] and "data/logos/2454.png" in r2[0] and r2[1] == "domain" and r2[2] == "ext", r2)
    d2.close()
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])
    c.close()

register("科技透明圈站內LOGO", lambda pg, b, base, code: t_tc_logo_1027(b, base, code))
