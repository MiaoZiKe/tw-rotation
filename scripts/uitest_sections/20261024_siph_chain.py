# 驗收段落「矽光子CPO1024」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa

# ===================================================================== 矽光子CPO1024
# Andy 10-24：「產業地圖幫我新增矽光子 CPO 題材分頁」。這段全部真的點、真的量「畫面因此改變」：
#   ① #industry 的分頁列真的有「矽光子／CPO」；「全市場」的檔數不含它（疊加族群不計入全市場）
#   ② 真的點那個分頁 → 網址換成 #industry/siph_cpo、族群長條圖有 12 條、成員表有 12 組
#   ③ 全市場的族群總覽與熱力圖裡沒有任何一個 siph 族群（成交值不拆分，不能灌水全市場）
#   ④ 點成員表裡的族群連結 → 展開該族群個股長條圖，成員真的出現（晶圓代工那組 ＝ 台積電、聯電）
#   ⑤ 載板／PCB／材料那組：CCL 三檔（台燿、台光電、聯茂）標「風險」、景碩標「中性」，整組沒有任何一檔標「受益」
#   ⑥ 成員表旁「?」點得開、內文真的寫了信心與階段
#   ⑦ 390 手機：沒有橫向捲軸、成員表可框內捲
#   ⑧ 其他鏈（AI 伺服器）的分頁照常，族群數沒被改
#   ⑨ 關聯圖只畫成員（Andy 10-25）：圖上沒有任何非成員台股、成員至少 35 檔出現、國際節點都跟成員有邊、其他鏈的關聯圖照舊含非成員

_SIPH_ST = """() => {
  const sec = document.getElementById('siphSec');
  const groups = sec ? [...sec.querySelectorAll('tr.siphg')].map(r => r.textContent.replace(/\\s+/g, '')) : [];
  const stance = {}; let cur = '';
  if (sec) sec.querySelectorAll('tbody tr').forEach(r => {
    if (r.classList.contains('siphg')) { cur = r.textContent.replace(/\\s+/g, ''); stance[cur] = []; return; }
    const st = r.querySelector('.siphst'); stance[cur].push([r.dataset.code, st ? st.textContent : '', (r.querySelector('.siphstage') || {}).textContent || '']);
  });
  const el = document.getElementById('gpBar'), c = el && window.echarts && echarts.getInstanceByDom(el);
  const cats = c ? ((c.getOption().yAxis && c.getOption().yAxis[0] && c.getOption().yAxis[0].data) || (c.getOption().xAxis && c.getOption().xAxis[0] && c.getOption().xAxis[0].data) || []) : null;
  const wrap = sec && sec.querySelector('.siphwrap');
  return { hash: location.hash, groups, stance, cats, nrows: sec ? sec.querySelectorAll('tbody tr:not(.siphg)').length : 0,
    wrapMax: wrap ? getComputedStyle(wrap).maxHeight : null, wrapScroll: wrap ? wrap.scrollHeight > wrap.clientHeight : null,
    sw: document.documentElement.scrollWidth, iw: innerWidth }; }"""

_TABS_ST = """() => [...document.querySelectorAll('#chainSwitch button')].map(b => ({ c: b.dataset.c, t: b.textContent, n: parseInt((b.querySelector('em') || {}).textContent || '0', 10), on: b.classList.contains('on') }))"""


def t_siph_chain_1024(pg, b, base, code):
    T = "矽光子CPO1024"
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.goto(base + "#industry", wait_until="networkidle")
    wait_until(pg, "() => document.querySelectorAll('#chainSwitch button').length > 3", 8000)
    tabs = pg.evaluate(_TABS_ST)
    siph = next((t for t in tabs if t["c"] == "siph_cpo"), None)
    ok(f"{T}：分頁列有「矽光子／CPO」", bool(siph) and "矽光子" in siph["t"], [t["t"] for t in tabs])
    allt = next((t for t in tabs if t["c"] == "_all"), None)
    rest = sum(t["n"] for t in tabs if t["c"] not in ("_all", "siph_cpo", "industry"))
    ok(f"{T}：「全市場」檔數（{allt and allt['n']}）不含疊加分頁（其餘各鏈合計 {rest}）", bool(allt) and allt["n"] == rest, [allt, rest])
    # ③ 全市場的族群總覽沒有 siph 族群
    wait_until(pg, "() => { const e = document.getElementById('gpBar'); return !!(e && window.echarts && echarts.getInstanceByDom(e)); }", 8000)
    st0 = pg.evaluate(_SIPH_ST)
    ok(f"{T}：全市場族群長條圖沒有任何矽光子／CPO 的組別", bool(st0["cats"]) and not any(("磊晶與雷射" in str(x) or "外置光源" in str(x) or "CPO 交換器" in str(x)) for x in st0["cats"]), (st0["cats"] or [])[:20])
    # ② 真的點分頁
    pg.locator('#chainSwitch button[data-c="siph_cpo"]').click()
    wait_until(pg, "() => location.hash.indexOf('siph_cpo') >= 0 && !!document.getElementById('siphSec') && document.querySelectorAll('#siphSec tr.siphg').length > 0", 10000)
    st = pg.evaluate(_SIPH_ST)
    ok(f"{T}：點分頁 → 網址換成 #industry/siph_cpo", "#industry/siph_cpo" in st["hash"], st["hash"])
    # 10-25 合併剖析圖後：有剖析圖的鏈，預設頁是第一張剖析圖（industry.js 規則），族群總覽搬到 /overview
    ok(f"{T}：分頁預設先看剖析圖（CPO 封裝圖有畫出來）", bool(wait_until(pg, "() => !!document.querySelector('[data-part^=\"sp_\"], svg [data-part^=\"sp_\"]') ? 1 : 0", 10000)))
    pg.goto(base + "#industry/siph_cpo/overview", wait_until="networkidle")
    wait_until(pg, "() => !!document.getElementById('siphSec') && document.querySelectorAll('#siphSec tr.siphg').length > 0", 10000)
    st = pg.evaluate(_SIPH_ST)
    ok(f"{T}：成員表有 12 組", len(st["groups"]) == 12, st["groups"])
    wait_until(pg, "() => { const e = document.getElementById('gpBar'); const c = e && window.echarts && echarts.getInstanceByDom(e); return !!c; }", 8000)
    st = pg.evaluate(_SIPH_ST)
    ok(f"{T}：族群漲幅長條圖有 12 條（疊加族群各自有行情）", st["cats"] is not None and len(st["cats"]) == 12, st["cats"])
    ok(f"{T}：成員表至少 40 檔、限高框內捲", st["nrows"] >= 40 and st["wrapMax"] not in (None, "none"), [st["nrows"], st["wrapMax"]])
    # ⑤ 載板／PCB／材料：風險不畫成受益
    sub = next((v for k, v in st["stance"].items() if "載板" in k), None)
    ok(f"{T}：載板／PCB／材料那組找得到", sub is not None, list(st["stance"]))
    if sub is not None:
        mp = {c: s for c, s, _ in sub}
        ok(f"{T}：台燿 6274、台光電 2383、聯茂 6213 標「風險」", all(mp.get(c) == "風險" for c in ("6274", "2383", "6213")), mp)
        ok(f"{T}：景碩 3189 標「中性」", mp.get("3189") == "中性", mp)
        ok(f"{T}：整組沒有任何一檔標「受益」（CCL 不能畫成受益）", "受益" not in mp.values(), mp)
    # 時程措辭：階段欄沒有把計畫寫成現在式
    allstage = " ".join(x[2] for v in st["stance"].values() for x in v)
    ok(f"{T}：階段欄有寫日期／計畫字樣（不是只寫「量產中」）", ("2027" in allstage or "2026" in allstage) and "已量產" not in allstage, allstage[:120])
    # ④ 點族群連結
    pg.locator('#siphSec tr.siphg a.lk-group', has_text="矽光子晶圓代工").first.click()
    wait_until(pg, "() => location.hash.indexOf('siph_foundry') >= 0", 6000)
    wait_until(pg, "() => { const e = document.getElementById('gpBar'); const c = e && window.echarts && echarts.getInstanceByDom(e); if (!c) return false; const o = c.getOption(); const a = (o.yAxis && o.yAxis[0] && o.yAxis[0].data) || (o.xAxis && o.xAxis[0] && o.xAxis[0].data) || []; return a.length === 2; }", 8000)
    st2 = pg.evaluate(_SIPH_ST)
    names = " ".join(str(x) for x in (st2["cats"] or []))
    ok(f"{T}：點「矽光子晶圓代工」→ 個股長條圖是台積電＋聯電（2 條）", "台積電" in names and "聯電" in names and len(st2["cats"]) == 2, st2["cats"])
    # ⑥ 「?」
    pg.goto(base + "#industry/siph_cpo/overview", wait_until="networkidle")
    wait_until(pg, "() => !!document.querySelector('#siphSec .howbtn')", 8000)
    pg.locator('#siphSec .howbtn').first.click()
    shown = wait_until(pg, "() => { const t = document.body.innerText; return t.indexOf('信心') >= 0 && t.indexOf('受益、中性、風險') >= 0; }", 4000)
    ok(f"{T}：成員表「?」點得開、寫了信心與受益／中性／風險", shown)
    pg.keyboard.press("Escape")
    # ⑧ 其他鏈照常
    pg.goto(base + "#industry/ai_server", wait_until="networkidle")
    wait_until(pg, "() => document.querySelectorAll('#chainSwitch button').length > 3", 8000)
    ai = next((t for t in pg.evaluate(_TABS_ST) if t["c"] == "ai_server"), None)
    ok(f"{T}：AI 伺服器分頁檔數照常（>0 且為 on）", bool(ai) and ai["n"] > 0 and ai["on"], ai)
    ok(f"{T}：AI 伺服器頁沒有成員與階段表（只有疊加鏈才有）", pg.evaluate("() => !document.getElementById('siphSec')"))

    # ⑨ 關聯圖只畫成員（1440 與 /overview 兩個入口各量一次）
    for hz in ("#industry/siph_cpo", "#industry/siph_cpo/overview"):
        pg.set_viewport_size({"width": 1440, "height": 900})
        pg.goto(base + hz, wait_until="networkidle")
        wait_until(pg, "() => document.querySelectorAll('#chainMap .co').length > 10 && document.querySelectorAll('#siphSec tr[data-code]').length > 30", 10000)
        g = pg.evaluate("""async () => {
          const members = [...new Set([...document.querySelectorAll('#siphSec tr[data-code]')].map(r => r.dataset.code))];
          const nodes = [...document.querySelectorAll('#chainMap .co')].map(n => ({ id: n.dataset.id, code: n.dataset.code || '', foreign: n.classList.contains('foreign') }));
          const sc = await (await fetch('data/supply_chain.json')).json();
          const edges = sc.edges, tw = {}; sc.companies.forEach(c => { tw[c.id] = c.tw_code || ''; });
          const mset = new Set(members);
          const foreignOk = nodes.filter(n => n.foreign).map(n => ({ id: n.id, ok: edges.some(e => (e.from === n.id && mset.has(tw[e.to])) || (e.to === n.id && mset.has(tw[e.from]))) }));
          return { members, shown: nodes.filter(n => n.code).map(n => n.code), nonMember: nodes.filter(n => n.code && !mset.has(n.code)).map(n => n.code),
                   foreignOk, nForeign: nodes.filter(n => n.foreign).length }; }""")
        ok(f"{T}（{hz}）：關聯圖沒有任何非成員台股", not g["nonMember"], g["nonMember"])
        ok(f"{T}（{hz}）：成員至少 35 檔出現在關聯圖（{len(set(g['shown']))}／{len(g['members'])}）", len(set(g["shown"])) >= 35, sorted(set(g["members"]) - set(g["shown"])))
        ok(f"{T}（{hz}）：國際節點（{g['nForeign']} 個）都和成員有邊", g["nForeign"] > 0 and all(x["ok"] for x in g["foreignOk"]), [x for x in g["foreignOk"] if not x["ok"]])
    # 其他鏈不受影響：AI 伺服器的關聯圖照舊含非成員（例如京元電 2449）
    pg.goto(base + "#industry/ai_server/overview", wait_until="networkidle")
    wait_until(pg, "() => document.querySelectorAll('#chainMap .co').length > 10", 10000)
    ai_codes = pg.evaluate("() => [...document.querySelectorAll('#chainMap .co[data-code]')].map(n => n.dataset.code)")
    ok(f"{T}：AI 伺服器關聯圖不受影響（仍有京元電 2449、共 {len(ai_codes)} 檔）", "2449" in ai_codes and len(ai_codes) > 40, len(ai_codes))
    # ⑦ 390
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    ctx.add_init_script("try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0')}catch(e){}")
    ctx.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    mp = ctx.new_page()
    try:
        mp.goto(base + "#industry/siph_cpo/overview", wait_until="networkidle")
        wait_until(mp, "() => document.querySelectorAll('#siphSec tr.siphg').length === 12", 10000)
        ms = mp.evaluate(_SIPH_ST)
        ok(f"{T}（390）：成員表 12 組、沒有橫向捲軸", len(ms["groups"]) == 12 and ms["sw"] <= ms["iw"] + 1, [len(ms["groups"]), ms["sw"], ms["iw"]])
        ok(f"{T}（390）：成員表框內可捲（不把整頁撐長）", bool(ms["wrapScroll"]), ms["wrapScroll"])
    finally:
        ctx.close()


register("矽光子CPO1024", lambda pg, b, base, code: t_siph_chain_1024(pg, b, base, code))
