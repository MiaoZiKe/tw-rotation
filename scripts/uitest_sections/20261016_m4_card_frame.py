# 驗收段落「手機卡片外框1016」—— 2026-10-16 從 scripts/_uitest.py 原封搬出（拆檔防合併衝突，見 _uitest.py 開頭「外掛段落」）。
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、SITE、fails… 直接可用，不要 import _uitest。
# 不要在這裡寫三引號模組說明（會蓋掉 _uitest 的 __doc__）。
# flake8: noqa

# ★ 2026-10-16 手機卡片外框1016（Andy iPhone 實機：「所有內容都需要在背景路上他適合大小的方框」）
#   手機每一塊內容（圖、表、清單）的最近容器要有「邊框或底色」而且圓角 ≥ 8；不准橫向捲動、頁高不超過準則（≤3 屏）。
#   分批上線：CARD1016_ROUTES 逐批擴充（批 1 = 總覽、資金流向、熱力圖；批 2 = 產業地圖、題材、市場明細、週期統計、選股；批 3 = 財經日曆、自選、訂單、訂閱、交付、ETF、個股）。每個寬度都用觸控點頁內分頁再量一次。
CARD1016_ROUTES = {
    "總覽": "#overview", "資金流向": "#flow", "資金分流樹": "#flow/sankey", "族群法人": "#flow/inst", "熱力圖": "#heatmap",
    "產業地圖": "#industry", "產業鏈": "#industry/semiconductor", "題材": "#themes", "市場明細": "#market", "週期統計": "#season", "選股": "#explore",
    "財經日曆": "#earnings", "自選": "#watch", "訂單": "#orders", "訂閱方案": "#pricing", "交付": "#delivery",
    "ETF行事曆": "#etf/cal", "ETF總覽": "#etf/list", "ETF試算": "#etf/inc", "個股": "#stock/2330",
}
CARD1016_JS = r"""()=>{
 const v=document.querySelector('main .view.on')||document.querySelector('main');
 const vis=e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'};
 const alpha=c=>{const m=c.match(/rgba?\(([^)]+)\)/);if(!m)return 0;const a=m[1].split(',').map(parseFloat);return a.length>3?a[3]:1};
 const framed=e=>{const cs=getComputedStyle(e);
   const bw=['Top','Right','Bottom','Left'].every(s=>parseFloat(cs['border'+s+'Width'])>0&&cs['border'+s+'Style']!=='none'&&alpha(cs['border'+s+'Color'])>0.05);
   const bg=alpha(cs.backgroundColor)>0.15;
   const rad=parseFloat(cs.borderTopLeftRadius)>=8;
   return (bw||bg)&&rad};
 const sel='canvas,svg,table,ul,ol,.heat,.hm,[class*=chart],[class*=Chart],[id*=chart],[id*=Chart]';
 const cands=[...v.querySelectorAll(sel)].filter(e=>{
   if(!vis(e))return false; const r=e.getBoundingClientRect();
   if(r.width<120||r.height<60)return false;
   if(e.tagName==='SVG'||e.tagName==='svg'){ if(e.closest('svg')!==e && e.parentElement.closest('svg'))return false; }
   if(e.parentElement.closest('canvas,svg,table')&&e.tagName!=='TABLE')return false;
   if(e.tagName==='UL'||e.tagName==='OL'){ if(e.children.length<3)return false; if(e.closest('nav,#tabs,.topbar'))return false;}
   if(e.closest('.topbar,nav,#tabs,#side,.msheet,#mbar'))return false;
   return true});
 const bare=[];const seen=new Set();
 for(const e of cands){
   let n=e,ok=false;
   while(n&&n!==document.body){ if(framed(n)){ok=true;break} if(n===v)break; n=n.parentElement }
   if(ok)continue;
   const d=(e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(e.className&&typeof e.className==='string'?'.'+e.className.trim().split(/\s+/).slice(0,2).join('.'):''));
   const p=e.parentElement; const pd=(p.tagName.toLowerCase()+(p.id?'#'+p.id:'')+(p.className&&typeof p.className==='string'?'.'+p.className.trim().split(/\s+/).slice(0,2).join('.'):''));
   const k=pd+'>'+d; if(seen.has(k))continue; seen.add(k);
   const r=e.getBoundingClientRect();
   bare.push({d:pd+' > '+d,w:Math.round(r.width),h:Math.round(r.height)});
 }
 return {h:document.documentElement.scrollHeight,sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,n:cands.length,bare};
}
"""
def t_m4_card_frame_1016(b, base):
    T = "手機卡片外框1016"
    for W in (360, 390, 430):
        H = 844
        m = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.on("pageerror", lambda e: fails.append(f"{T} pageerror: {e}"))
        try:
            for nm, h in CARD1016_ROUTES.items():
                m.goto(f"{base}#x", wait_until="domcontentloaded")
                m.evaluate("(h) => { location.hash = h; }", h); m.wait_for_timeout(2500)
                def meas():
                    r = m.evaluate(CARD1016_JS)
                    tops = m.evaluate("""() => { const v = document.querySelector('main .view.on'); if (!v) return [];
                      return [...v.querySelectorAll('.card,.sl-card,.incsec,.prcard,#mbBody')].filter(c => !c.parentElement.closest('.card,.sl-card,.incsec,.prcard') && c.getClientRects().length && c.getBoundingClientRect().height > 60 && !(c.id === 'mbBody' && [...c.children].every(k => k.classList.contains('mbseg'))))
                        .map(c => { const cs = getComputedStyle(c); return { id: c.id || c.className.split(' ')[0], bw: parseFloat(cs.borderTopWidth), rad: parseFloat(cs.borderTopLeftRadius),
                          pad: parseFloat(cs.paddingLeft), right: Math.round(c.getBoundingClientRect().right),
                          // 被卡片左右邊切到的子元素數（不含自己會橫捲的容器裡面的東西）
                          clip: [...c.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(), cr = c.getBoundingClientRect();
                            if (!r.width || !r.height || getComputedStyle(e).position === 'fixed') return false;
                            for (let p = e.parentElement; p && p !== c; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return false; }
                            return r.left < cr.left - 1 || r.right > cr.right + 1; }).length }; }); }""")
                    return r, tops
                r, tops = meas()
                ok(f"{T} {W}px「{nm}」：圖／表／清單的最近容器都有框或底色且圓角 ≥ 8（沒框的 {len(r['bare'])} 個）",
                   len(r["bare"]) == 0 and (r["n"] >= 1 or len(tops) >= 1), r["bare"][:4])
                ok(f"{T} {W}px「{nm}」：每張最外層卡片有 1px 邊框、圓角 ≥ 8、內距 10～12px、沒超出螢幕、裡面沒有東西被卡片邊緣切到",
                   all(t["bw"] >= 1 and t["rad"] >= 8 and 10 <= t["pad"] <= 12 and t["right"] <= W and t["clip"] == 0 for t in tops), tops[:4])
                ok(f"{T} {W}px「{nm}」：沒有橫向捲動、頁高 ≤ 3 屏",
                   r["sw"] <= r["cw"] and r["h"] <= 3 * H + 120, {"sw": r["sw"], "cw": r["cw"], "h": r["h"]})
                # 用手指點頁內分頁（有的話），每點一下再量一次
                tabs = m.evaluate("""() => [...document.querySelectorAll('main .view.on nav.mpager button, #mM3Sw button, #mbTabs button')].filter(b => b.getClientRects().length).length""")
                for i in range(min(tabs, 10 if nm == "個股" else 4)):
                    xy = m.evaluate("""(i) => { const b = [...document.querySelectorAll('main .view.on nav.mpager button, #mM3Sw button, #mbTabs button')].filter(b => b.getClientRects().length)[i];
                        if (!b) return null; b.scrollIntoView({block:'center',inline:'center',behavior:'instant'}); const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }""", i)
                    if not xy:
                        continue
                    m.touchscreen.tap(xy[0], xy[1]); m.wait_for_timeout(1500)
                    r2, t2 = meas()
                    ok(f"{T} {W}px「{nm}」點第 {i + 1} 個分頁後：沒框 0 個、沒橫捲（{m.evaluate('() => location.hash')}）",
                       len(r2["bare"]) == 0 and r2["sw"] <= r2["cw"], {"bare": r2["bare"][:3], "sw": r2["sw"], "cw": r2["cw"]})
        finally:
            m.close()


# ★ 2026-10-16 Andy：「所有內容都需要在背景路上適合大小的方框」——手機每塊內容的最近容器要有框／底色、圓角 ≥ 8（分批擴充路由）
register("手機卡片外框1016", lambda pg, b, base, code: t_m4_card_frame_1016(b, base), after="手機按鈕普查")
