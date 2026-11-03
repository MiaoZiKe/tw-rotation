"""頻道二「科技透明圈」瑞士極簡版型套版範例（1080x1350）。
用法：python render_samples.py <素材根目錄 ASSETS> <輸出目錄 OUT>
ASSETS 內要有 logos/、diagrams/、brand/icon_light.svg。字型 Noto Sans TC 由 TW_FONT_DIR（fontsource 解開的 package 目錄）提供。
色票：白底、黑 #111111、瑞士紅 #D4231A、輔助灰 #595959、細線 #CFCFCF、淡灰面 #EFEFEF。
輸出每張 PNG 之後，用 DOM 量每個文字／圖片的外框，兩兩比對重疊（程式檢查），結果印出並寫 overlap_report.json。"""
import base64, json, os, random, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ASSETS = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
FD = Path(os.environ.get("TW_FONT_DIR", ""))
W, H = 1080, 1350
INK, RED, GREY, LINE, PALE = "#111111", "#D4231A", "#595959", "#CFCFCF", "#EFEFEF"


def b64(p):
    p = Path(p); mime = {"png": "image/png", "svg": "image/svg+xml"}[p.suffix[1:]]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


FONTCSS = "".join(f'<link rel="stylesheet" href="file://{FD}/{w}.css">' for w in (400, 700, 900)) if FD.exists() else ""
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:'Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{INK};background:#fff;display:flex;flex-direction:column;overflow:hidden}}
.n{{font-family:Inter,'Noto Sans TC',sans-serif;font-weight:800;font-variant-numeric:tabular-nums}}
.top{{height:128px;flex:none;padding:0 64px;display:flex;align-items:center;gap:20px;border-bottom:4px solid {INK}}}
.top .b{{font-size:38px;font-weight:900;letter-spacing:.02em}}
.top .t{{font-size:32px;font-weight:400;color:{GREY}}}
.top .p{{margin-left:auto;font-size:32px;font-weight:700}}
.body{{padding:52px 64px 0;flex:1;display:flex;flex-direction:column;min-height:0}}
.tag{{display:inline-flex;align-items:center;height:52px;padding:0 20px;font-size:32px;font-weight:700;border:2px solid {INK};white-space:nowrap}}
.tag.g{{border-color:#BDBDBD;color:{GREY}}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {LINE};display:flex;align-items:flex-end;justify-content:space-between;flex:none}}
.ft span{{font-size:28px;color:{GREY};font-weight:400}}
.lab{{font-size:32px;font-weight:700;color:{GREY}}}
.ph{{border-bottom:4px solid {RED};font-weight:700;padding:0 4px;white-space:nowrap}}
.callout{{border-left:12px solid {RED};background:#F4F4F4;padding:26px 34px}}
.box{{border-top:3px solid {INK}}}
.red{{color:{RED}}}
"""


def top(label, pg):   # 統一決策：A/B/C 全系列頁首只放純文字「科技透明圈」，不放開口圈（A1 帶公司 LOGO，法遵 ② 不與開口圈組合；三系列一致才像同一頻道）
    ic = ""   # 不放開口圈
    return f'<div class="top">{ic}<div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'


def ft(left, right="示意・範例"):
    return f'<div class="ft"><span>{left}</span><span>{right}</span></div>'


S = {}   # 檔名 -> body html

# ---------------- 範例 A：公司行情（法遵 7-3 六條）----------------
NAME = "台積電"
from PIL import Image, ImageChops
import io
def trimmed(path):
    im = Image.open(path).convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    im = im.crop(bb); bio = io.BytesIO(); im.save(bio, "PNG")
    return "data:image/png;base64," + base64.b64encode(bio.getvalue()).decode(), im.size
logo, LSZ = trimmed(ASSETS / "logos" / f"{NAME}.png")
LH = 80; LW = round(LSZ[0] * LH / LSZ[1])
DISC_LOGO = "文中公司標誌僅用於標示公司，本帳號與各公司無合作或授權關係。"   # 法遵 5：放 LOGO 的版本用完整固定句
DISC = "網友回報，非公司公告・與各公司無合作或授權關係"


def cells(items):
    return "".join(f'<div style="flex:1;padding:18px 24px;border-left:2px solid {LINE}"><div class="lab">{a}</div>'
                   f'<div style="margin-top:8px;font-size:44px"><span class="ph">{b}</span></div></div>' for a, b in items)


def a_cover(with_logo):
    # LOGO 高度 80px ≤ 公司名字高 120px 的 1.5 倍（實際 0.67 倍），緊貼公司名左側，原色原比例
    lg = f'<img data-b src="{logo}" width="{LW}" height="{LH}" style="flex:none;display:block" alt="">' if with_logo else ""
    return f"""{top('公司行情', '1 / 3')}
<div class="body">
  <div style="display:flex;gap:14px"><span class="tag">公司薪資行情</span><span class="tag g">碩畢・研發職類</span></div>
  <div style="margin-top:56px;display:flex;align-items:center;gap:22px">{lg}<div style="font-size:120px;font-weight:900;line-height:1.2">{NAME}</div></div>
  <div style="font-size:150px;font-weight:900;line-height:1.2;margin-top:34px">薪資行情</div>
  <div style="margin-top:56px;display:flex;border-top:3px solid {INK};border-bottom:2px solid {LINE}">
    <div style="flex:1;padding:18px 24px 18px 0"><div class="lab">職類</div><div style="margin-top:8px;font-size:44px"><span class="ph">〔待填〕</span></div></div>
    {cells([('學歷', '〔待填〕'), ('年資', '〔待填〕')])}</div>
  <div class="callout" style="margin-top:56px;display:flex;align-items:center;gap:30px">
    <div style="font-size:46px;font-weight:800;line-height:1.2">碩畢<br>月薪</div><div class="n" style="font-size:96px;line-height:1">〔待填〕K</div></div>
  <div style="margin-top:44px;font-size:38px;font-weight:700;color:{GREY}">〔N〕位網友提供（2026）</div>
</div>{ft(DISC_LOGO, "") if with_logo else ft(DISC)}"""


S["A1_cover_logo"] = a_cover(True)
S["A1_cover_textonly"] = a_cover(False)
rows = [("總部地點", "〔待填〕"), ("碩畢月薪", "〔待填〕K"), ("年終・分紅", "〔待填〕個月"), ("升等路徑", "〔待填〕"),
        ("加班時數", "網友普遍回報工時偏長"), ("繁忙程度", "〔待填〕/ 5"), ("出差頻率", "〔待填〕")]
trs = "".join(f'<div style="display:flex;align-items:center;height:118px;border-top:2px solid {LINE}">'
              f'<div class="n" style="width:78px;font-size:32px;color:{RED}">{i+1:02d}</div>'
              f'<div style="width:240px;font-size:40px;font-weight:800;white-space:nowrap">{a}</div>'
              f'<div style="width:400px;font-size:36px"><span class="ph">{b}</span></div>'
              f'<div style="flex:1;font-size:34px;color:{GREY};white-space:nowrap">〔一句評語〕</div></div>' for i, (a, b) in enumerate(rows))
# 含「加班」等負面欄位：只寫公司名、不放 LOGO（法遵 ④）
S["A2_fields_textonly"] = f"""{top('公司行情', '2 / 3')}
<div class="body" style="padding-top:44px">
  <div style="display:flex;gap:14px"><span class="tag">{NAME}</span><span class="tag g">七欄固定，方便比較</span></div>
  <div style="font-size:78px;font-weight:900;line-height:1.2;margin-top:24px">七個欄位，一次看完</div>
  <div class="box" style="margin-top:28px">{trs}</div>
</div>{ft(DISC)}"""
S["A3_cta"] = f"""{top('公司行情', '3 / 3')}
<div class="body">
  <div style="font-size:50px;font-weight:700;color:{GREY};margin-top:40px">你那一組的行情是多少？</div>
  <div style="font-size:112px;font-weight:900;line-height:1.25;margin-top:30px">留言告訴我們，<br>幫大家<span class="red">補齊</span>這張表</div>
  <div class="callout" style="margin-top:70px;font-size:46px;font-weight:700;line-height:1.5">所有數字為網友自述、未經查證，<br>區間僅供參考，有誤請指正。</div>
  <div style="margin-top:70px;display:flex;border-top:3px solid {INK};border-bottom:2px solid {LINE}">
    <div style="flex:1;padding:22px 24px 22px 0"><div class="lab">下一篇</div><div style="font-size:42px;font-weight:800;margin-top:6px">〔下一家公司〕</div></div>
    <div style="flex:1;padding:22px 24px;border-left:2px solid {LINE}"><div class="lab">追蹤</div><div style="font-size:42px;font-weight:800;margin-top:6px">科技透明圈</div></div></div>
</div>{ft(DISC)}"""

# ---------------- 範例 B：技術白話（帶架構圖）----------------
DG = ASSETS / "diagrams" / "raw" / "ai_adv_packaging_2d_raw.png"
dg = b64(DG)
S["B1_cover"] = f"""{top('技術白話', '1 / 3')}
<div class="body">
  <div style="display:flex;gap:14px"><span class="tag">技術白話</span><span class="tag g">2.5D 先進封裝</span></div>
  <div style="font-size:60px;font-weight:700;color:{GREY};margin-top:48px;margin-bottom:12px">AI 晶片為什麼要「疊」起來？</div>
  <div style="font-size:150px;font-weight:900;line-height:1.15;margin-top:36px">CoWoS<br>是什麼</div>
  <div class="box" style="margin-top:56px;padding-top:30px;font-size:46px;font-weight:700;line-height:1.5">一句話：把運算晶粒和記憶體<br>放在同一片<span class="ph">矽中介層</span>上，<br>讓它們靠得很近、傳得很快。</div>
  <div style="margin-top:auto;margin-bottom:24px;font-size:36px;font-weight:700;color:{GREY}">往右滑，看剖面示意圖　→</div>
</div>{ft('CoWoS 為台積電之商標。', '示意圖，非實物比例')}"""
# B2：只取「主剖面」(裁掉原圖左上導言——它在講已移除的卡片；與圖內 12px 級小字)，放大到滿版，標題改 56px 大字
_im = Image.open(DG).convert("RGB").crop((150, 285, 1235, 1080))
_bio = io.BytesIO(); _im.save(_bio, "PNG"); dgc = "data:image/png;base64," + base64.b64encode(_bio.getvalue()).decode()
S["B2_diagram"] = f"""{top('技術白話', '2 / 3')}
<div class="body" style="padding-top:36px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">2.5D 先進封裝剖面（以 CoWoS 為例）</span></div>
  <div style="font-size:60px;font-weight:900;line-height:1.25;margin-top:22px">接點由下往上，<span class="red">一路變小</span></div>
  <div style="margin-top:22px;border-top:3px solid {INK};padding-top:14px"><img data-b src="{dgc}" width="952" style="display:block;margin:0 auto;border-bottom:2px solid {LINE}"></div>
  <div style="display:flex;margin-top:18px">{''.join(f'<div style="flex:1;font-size:34px;font-weight:800;line-height:1.35;white-space:nowrap;{"padding-left:18px;border-left:2px solid "+LINE if i else ""}"><span class="n red">{n}</span> {t}</div>' for i,(n,t) in enumerate([("上","晶粒＋記憶體"),("中","矽中介層"),("下","載板＋BGA 球")]))}</div>
</div>{ft('示意圖，非實物比例。CoWoS 為台積電之商標。', '科技透明圈')}"""
S["B3_points"] = f"""{top('技術白話', '3 / 3')}
<div class="body">
  <div style="display:flex;gap:14px"><span class="tag">三個重點</span></div>
  <div style="font-size:84px;font-weight:900;line-height:1.25;margin-top:30px">看懂這張圖，<br>記住三件事</div>
  {''.join(f'<div style="display:flex;gap:26px;align-items:flex-start;margin-top:40px;border-top:2px solid {LINE};padding-top:28px"><div class="n red" style="font-size:64px;line-height:1;width:84px">{i}</div><div><div style="font-size:50px;font-weight:800">{a}</div><div style="font-size:36px;color:{GREY};margin-top:8px;line-height:1.5">{b}</div></div></div>' for i, a, b in [("01", "晶片之間靠「中介層」連", "線路密度比一般載板高很多，所以訊號又短又快"), ("02", "記憶體貼在運算晶粒旁邊", "距離縮短，頻寬才拉得上去"), ("03", "封裝本身變成產能瓶頸", "不只是製程，連「怎麼組起來」都排隊")])}
</div>{ft('示意圖，非實物比例', '科技透明圈')}"""


# ---------------- 範例 C：面試題（帶示意圖）----------------
def wafer(die_w, die_h, defects, size=380):
    R = size / 2; cx = cy = R; rects = []; nd = bd = 0
    ny, nx = int(size // die_h), int(size // die_w); ox = (size - nx * die_w) / 2; oy = (size - ny * die_h) / 2
    for j in range(ny):
        for i in range(nx):
            x0, y0 = ox + i * die_w, oy + j * die_h
            cs = [(x0, y0), (x0 + die_w, y0), (x0, y0 + die_h), (x0 + die_w, y0 + die_h)]
            if all((px - cx) ** 2 + (py - cy) ** 2 <= (R - 6) ** 2 for px, py in cs):
                hit = any(x0 <= dx < x0 + die_w and y0 <= dy < y0 + die_h for dx, dy in defects)
                nd += 1; bd += hit
                rects.append(f'<rect x="{x0+2:.1f}" y="{y0+2:.1f}" width="{die_w-4:.1f}" height="{die_h-4:.1f}" rx="3" fill="{RED if hit else "#EDEDED"}" stroke="{RED if hit else "#BDBDBD"}" stroke-width="1.5"/>')
    dots = "".join(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="7" fill="{INK}" stroke="#fff" stroke-width="2.5"/>' for dx, dy in defects)
    return (f'<svg data-b width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{cx}" cy="{cy}" r="{R-2}" fill="#fff" stroke="#BDBDBD" stroke-width="3"/>{"".join(rects)}{dots}</svg>'), nd, bd


def defects(seed, size=380):
    r = random.Random(seed); out = []; R = size / 2
    while len(out) < 8:
        x, y = r.uniform(30, size - 30), r.uniform(30, size - 30)
        if (x - R) ** 2 + (y - R) ** 2 <= (R - 30) ** 2: out.append((x, y))
    return out


seed = min(range(400), key=lambda s: abs(wafer(36, 36, defects(s))[2] - 8) + abs(wafer(36, 72, defects(s))[2] - 7))
DF = defects(seed)
svS, nS, bS = wafer(36, 36, DF); svB, nB, bB = wafer(36, 72, DF)
yS, yB = (nS - bS) / nS, (nB - bB) / nB


def panel(title, svg, n, b, y):
    return (f'<div style="flex:1;border-top:3px solid {INK};padding:16px 0;display:flex;flex-direction:column;align-items:center;gap:10px">{svg}'
            f'<div style="font-size:42px;font-weight:800;margin-top:4px">{title}</div><div class="n" style="font-size:38px;color:{GREY}">良品 {n-b} / 共 {n}</div>'
            f'<div class="n red" style="font-size:64px;line-height:1.1">{y*100:.0f}%</div></div>')


S["C1_question"] = f"""{top('面試題庫', '1 / 3')}
<div class="body">
  <div style="display:flex;gap:14px"><span class="tag">面試題 #〔待填〕</span><span class="tag g">製程整合</span></div>
  <div style="display:flex;align-items:center;gap:26px;margin-top:56px"><div class="n" style="width:150px;height:150px;background:{INK};color:#fff;font-size:112px;display:flex;align-items:center;justify-content:center;flex:none">Q</div>
    <div style="font-size:38px;font-weight:700;color:{GREY};letter-spacing:.12em">題目</div></div>
  <div style="font-size:88px;font-weight:900;line-height:1.3;margin-top:44px">晶片面積放大 2 倍，<br><span class="ph">良率會剛好剩一半</span>嗎？</div>
  <div class="callout" style="margin-top:60px;font-size:46px;font-weight:700">先想 10 秒，再滑動看答案　→</div>
  <div style="margin-top:60px;display:flex;border-top:3px solid {INK};border-bottom:2px solid {LINE}">
    <div style="flex:1;padding:22px 24px 22px 0"><div class="lab">領域</div><div style="font-size:42px;font-weight:800;margin-top:6px">製程整合</div></div>
    <div style="flex:1;padding:22px 24px;border-left:2px solid {LINE}"><div class="lab">考察重點</div><div style="font-size:42px;font-weight:800;margin-top:6px;white-space:nowrap">良率模型</div></div>
    <div style="flex:1;padding:22px 24px;border-left:2px solid {LINE}"><div class="lab">建議作答</div><div style="font-size:42px;font-weight:800;margin-top:6px;white-space:nowrap">3 分鐘</div></div></div>
</div>{ft('科技透明圈')}"""
S["C2_diagram"] = f"""{top('面試題庫', '2 / 3')}
<div class="body" style="padding-top:40px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">示意圖</span><span style="font-size:32px;color:{GREY}">同一片晶圓、同樣 8 顆缺陷</span></div>
  <div style="display:flex;gap:28px;margin-top:28px">{panel('小晶粒（面積 1 倍）', svS, nS, bS, yS)}{panel('大晶粒（面積 2 倍）', svB, nB, bB, yB)}</div>
  <div class="callout" style="margin-top:34px;font-size:40px;font-weight:700;line-height:1.5">缺陷數不變，大晶粒吃到缺陷的機會變大，<br>良品比例掉得比直覺快（下一頁用公式算平均）。</div>
</div>{ft('示意圖，非實際晶圓資料（缺陷位置為隨機示意）', '科技透明圈')}"""
S["C3_answer"] = f"""{top('面試題庫', '3 / 3')}
<div class="body">
  <div style="display:flex;align-items:center;gap:26px"><div class="n" style="width:150px;height:150px;background:{RED};color:#fff;font-size:112px;display:flex;align-items:center;justify-content:center;flex:none">A</div>
    <div style="font-size:38px;font-weight:700;color:{GREY};letter-spacing:.12em">參考答案</div></div>
  <div style="font-size:76px;font-weight:900;line-height:1.3;margin-top:36px">不是剛好剩一半，<br>而是<span class="ph">良率變平方</span></div>
  <div class="callout" style="margin-top:32px;padding:20px 34px"><div class="lab">一階模型（Poisson）</div><div class="n" style="font-size:64px;margin-top:6px">Y ＝ e<sup style="font-size:.55em">−A·D₀</sup></div></div>
  <div style="margin-top:30px;border-top:3px solid {INK}">
    <div style="display:flex;align-items:center;height:96px;border-bottom:2px solid {LINE}"><div style="width:420px;font-size:36px;font-weight:700">面積 1 倍（D₀ 0.1）</div><div class="n" style="font-size:48px">e<sup style="font-size:.55em">−0.1</sup> ≈ 90.5%</div></div>
    <div style="display:flex;align-items:center;height:96px;border-bottom:2px solid {LINE}"><div style="width:420px;font-size:36px;font-weight:700">面積 2 倍（D₀ 0.1）</div><div class="n red" style="font-size:48px">e<sup style="font-size:.55em">−0.2</sup> ≈ 81.9%</div></div></div>
  <div style="margin-top:22px;font-size:36px;line-height:1.5;font-weight:500">面積加倍 ＝ 良率自己乘自己（0.905² ≈ 0.819）。<br>真正變貴的是：每片晶圓能切的顆數少一半，<br>每顆好晶粒的成本因此不止翻倍。</div>
</div>{ft('教學用假設值，非任何公司實際良率', '科技透明圈')}"""

# ---------------- 轉圖 + 重疊檢查 ----------------
JS = """() => {
 const out=[]; const els=[...document.querySelectorAll('body *')];
 const rects=[];
 for (const e of els) {
   if (e.tagName==='IMG'||e.tagName==='svg'||e.hasAttribute('data-b')) { const r=e.getBoundingClientRect(); if(r.width>0) rects.push({k:(e.tagName+(e.className&&e.className.baseVal===undefined?'.'+e.className:'')),r:[r.left,r.top,r.right,r.bottom],e}); continue; }
   for (const n of e.childNodes) if (n.nodeType===3 && n.textContent.trim()) { const g=document.createRange(); g.selectNodeContents(n); for (const r of g.getClientRects()) if(r.width>1) rects.push({k:'txt:'+n.textContent.trim().slice(0,12),r:[r.left,r.top,r.right,r.bottom],e}); }
 }
 const bad=[];
 for (let i=0;i<rects.length;i++) for (let j=i+1;j<rects.length;j++) {
   const a=rects[i], b=rects[j]; if (a.e===b.e) continue; if (a.e.contains(b.e)||b.e.contains(a.e)) continue;
   if (a.e.closest('svg') && b.e.closest('svg') && a.e.closest('svg')===b.e.closest('svg')) continue;
   const ox=Math.min(a.r[2],b.r[2])-Math.max(a.r[0],b.r[0]), oy=Math.min(a.r[3],b.r[3])-Math.max(a.r[1],b.r[1]);
   if (ox>2 && oy>2) bad.push([a.k,b.k,Math.round(ox),Math.round(oy)]);
 }
 const oob=rects.filter(x=>x.r[0]<-1||x.r[2]>1081||x.r[3]>1351||x.r[1]<-1).map(x=>x.k);
 const body=document.body; const ovf = body.scrollHeight>1350+1 || body.scrollWidth>1081;
 const small=[...document.querySelectorAll('body *')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<24).map(e=>e.textContent.trim().slice(0,10));
 return {bad,oob,ovf,small,n:rects.length};
}"""

report = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for name, html in S.items():
        doc = f'<!doctype html><html><head><meta charset="utf-8">{FONTCSS}<style>{CSS}</style></head><body>{html}</body></html>'
        f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600)
        pg.evaluate("document.fonts.ready")
        res = pg.evaluate(JS)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        pg.close(); f.unlink()
        report[name] = res
        print(name, "重疊", len(res["bad"]), "出界", len(res["oob"]), "溢出", res["ovf"], "小字(<24px)", res["small"], res["bad"][:3])
    b.close()
json.dump(report, open(OUT / "overlap_report.json", "w"), ensure_ascii=False, indent=1)
tot = sum(len(v["bad"]) + len(v["oob"]) + int(v["ovf"]) for v in report.values())
print(f"重疊檢查：程式 {len(report)} 張 {tot} 筆")
