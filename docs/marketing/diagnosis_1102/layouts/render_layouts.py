"""兩個頻道的版型樣張（美術總監，2026-11-02）。
用法：python render_layouts.py            輸出 PNG 到本資料夾，並印出「重疊檢查」。
全部內容為假資料／〔待填〕，每張右下角有「示意」小字。字由 Playwright 渲染。
本機只有文泉驛正黑（單一字重，粗體為合成），正式出圖機有 Noto Sans CJK TC，字寬會略有不同。
"""
import base64, io, json, math, random, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "CLAUDE.md").exists())
W, H = 1080, 1350
FONT = "'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"

# ---------------- 色票 ----------------
C1 = dict(bg="#0B1626", panel="#13233A", line="#2A3D57", t1="#FFFFFF", t2="#C3CFDD", t3="#8FA3BA",
          key="#FFD23F", rise="#FF6B7A", fall="#34D399", bar="#5B7391")
C2 = dict(paper="#F5EFE3", card="#FFFBF2", line="#D8CDB5", ink="#1F1C17", ink2="#4A443A", ink3="#6B6454",
          pen="#D9420F", pen2="#B8340A", blue="#1E3F8F", hl="#FFD9C2", rise="#C4142F", fall="#07784E")


def bibi(name, h):
    im = Image.open(ROOT / "docs/anim/bibi_library" / name / "key.png").convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox())
    buf = io.BytesIO(); im.save(buf, "PNG")
    return f'<img data-b class="bibi" style="height:{h}px" src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'


# ---------------- 頻道一 CSS（深海軍藍＋單一黃）----------------
CSS1 = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{C1['t1']};background:{C1['bg']};
 background-image:linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px);background-size:54px 54px;
 position:relative;overflow:hidden;padding:56px 64px 48px;display:flex;flex-direction:column}}
.n{{font-family:Inter,'DejaVu Sans',sans-serif;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
.hd{{display:flex;align-items:center;gap:18px;height:72px;flex:none}}
.av{{width:64px;height:64px;border-radius:50%;background:#F6EEDD;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.av .bibi{{height:56px}}
.nm{{font-size:36px;font-weight:700;color:{C1['t2']}}}
.pg{{margin-left:auto;font-size:34px;font-weight:700;color:{C1['t3']}}}
.ft{{display:flex;align-items:center;justify-content:space-between;height:48px;flex:none;border-top:2px solid {C1['line']};margin-top:auto;padding-top:0}}
.ft span{{font-size:28px;color:{C1['t3']}}}
.kick{{font-size:38px;font-weight:700;color:{C1['t2']};letter-spacing:.04em}}
.h1{{font-size:112px;font-weight:900;line-height:1.18}}
.h2{{font-size:84px;font-weight:900;line-height:1.22}}
.y{{color:{C1['key']}}}
.sub{{font-size:52px;font-weight:600;color:{C1['t2']};line-height:1.4}}
.box{{background:{C1['panel']};border:2px solid {C1['line']};border-radius:20px}}
.bibi{{object-fit:contain}}
.grow{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:28px}}
"""

# ---------------- 頻道二 CSS（暖紙＋墨黑＋一支紅橘筆）----------------
CSS2 = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{C2['ink']};background:{C2['paper']};
 background-image:radial-gradient({C2['line']} 2.2px,transparent 2.6px);background-size:36px 36px;
 position:relative;overflow:hidden;padding:56px 64px 48px;display:flex;flex-direction:column}}
.m{{font-family:'JetBrains Mono','DejaVu Sans Mono',monospace;font-weight:700;font-variant-numeric:tabular-nums}}
.hd{{display:flex;align-items:center;gap:16px;height:64px;flex:none}}
.logo{{font-family:'JetBrains Mono',monospace;font-weight:800;font-size:40px;color:{C2['pen']};letter-spacing:-.05em}}
.nm{{font-size:34px;font-weight:700;color:{C2['ink2']}}}
.pg{{margin-left:auto;font-size:32px;font-weight:700;color:{C2['ink3']}}}
.ft{{display:flex;align-items:center;justify-content:space-between;height:48px;flex:none;border-top:3px solid {C2['ink']};margin-top:auto}}
.ft span{{font-size:28px;color:{C2['ink3']}}}
.card{{background:{C2['card']};border:3px solid {C2['ink']};border-radius:6px;box-shadow:8px 8px 0 {C2['ink']}}}
.box{{}}
.ph{{display:inline-block;border:3px dashed {C2['pen']};background:{C2['hl']};border-radius:6px;padding:2px 16px;color:{C2['pen2']};font-family:'JetBrains Mono','WenQuanYi Zen Hei',monospace;font-weight:800}}
.pen{{color:{C2['pen']}}}
.note{{color:{C2['blue']};font-weight:700;transform:rotate(-2deg);transform-origin:left center;display:inline-block}}
.chip{{display:inline-block;font-family:'JetBrains Mono',monospace;font-weight:800;font-size:32px;border:3px solid {C2['ink']};padding:2px 16px;border-radius:6px;background:{C2['card']}}}
.tape{{position:absolute;z-index:0;width:170px;height:44px;background:rgba(217,66,15,.28);transform:rotate(-3deg)}}
.hl{{background:linear-gradient(transparent 58%,{C2['hl']} 58%)}}
.bibi{{object-fit:contain}}
.grow{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:28px}}
"""

STAMP = "示意・假資料"


def ft1(left="熱點解讀"):
    return f'<div class="ft"><span data-meta>{left}</span><span data-meta>{STAMP}</span></div>'


def hd1(pg=""):
    return (f'<div class="hd"><div class="av">{bibi("face_cool", 56)}</div><div class="nm">哩股哩股</div>'
            f'<div class="pg">{pg}</div></div>')


def ft2(left="科技圈薪水透明（暫名）"):
    return f'<div class="ft"><span data-meta>{left}</span><span data-meta>{STAMP}</span></div>'


def hd2(pg=""):
    return (f'<div class="hd"><div class="logo">[·]</div><div class="nm">科技圈薪水透明</div>'
            f'<div class="pg">{pg}</div></div>')


SLIDES = {}   # 檔名 -> (css, body html)


# =============== 頻道一 ===============
# A1 熱點解讀封面
SLIDES["ch1_A1_hotcover"] = (CSS1, f"""
{hd1("1 / 5")}
<div class="grow" style="gap:20px;justify-content:flex-end;padding-bottom:28px;position:relative">
  <div style="position:absolute;right:0;top:40px">{bibi("face_shock", 250)}</div>
  <div class="kick" style="margin-top:0">熱點解讀・11/02</div>
  <div class="h1" style="margin-top:8px">某晶片大廠<br>單日重挫</div>
  <div class="n y" style="font-size:340px;line-height:1;margin:-10px 0 0 -10px">−17%</div>
  <div class="sub">AI 浪潮裡，它到底少了什麼？</div>
  <div style="font-size:40px;font-weight:700;color:{C1['t3']};margin-top:6px">滑動看 3 個原因　→</div>
</div>
{ft1()}""")

# A3 為什麼（因果鏈）
def chain_card(no, title, desc, hi=False):
    bd = f"border-color:{C1['key']};border-width:4px;" if hi else ""
    tcol = f"color:{C1['key']}" if hi else ""
    return f"""<div class="box" style="{bd}padding:28px 36px;display:flex;gap:28px;align-items:center">
      <div class="n" style="font-size:72px;color:{C1['key'] if hi else C1['t3']};width:96px;flex:none">{no}</div>
      <div style="display:flex;flex-direction:column;gap:6px"><div style="font-size:52px;font-weight:800;{tcol}">{title}</div>
      <div style="font-size:36px;color:{C1['t2']};line-height:1.35">{desc}</div></div></div>"""
def arrow():
    return f'<div style="height:44px;display:flex;justify-content:center"><div style="width:0;height:0;border-left:22px solid transparent;border-right:22px solid transparent;border-top:30px solid {C1["line"]}"></div></div>'
SLIDES["ch1_A3_hotwhy"] = (CSS1, f"""
{hd1("3 / 5")}
<div style="display:flex;flex-direction:column;gap:20px;margin-top:28px">
  <div class="kick">原因・因果鏈</div>
  <div class="h2">為什麼會跌？</div>
</div>
<div class="grow" style="gap:0;justify-content:center">
  {chain_card("1","財測低於預期","下一季營收指引，低於市場原本的預期")}
  {arrow()}
  {chain_card("2","客戶轉單","主力客戶把新訂單轉給競爭對手")}
  {arrow()}
  {chain_card("3","市場重新定價","<span class='y' style='font-weight:800'>預期被砍</span>，一天把成長故事賣掉")}
</div>
{ft1()}""")

# A4 台股影響（紅漲綠跌）
def imp_row(name, desc, val, up):
    col = C1['rise'] if up else C1['fall']
    arr = "▲" if up else "▼"
    return f"""<div class="box" style="display:flex;align-items:center;padding:22px 36px;gap:24px">
     <div style="flex:1;display:flex;flex-direction:column;gap:4px"><div style="font-size:56px;font-weight:800">{name}</div><div style="font-size:34px;color:{C1['t2']}">{desc}</div></div>
     <div class="n" style="font-size:64px;color:{col}">{arr} {val}</div></div>"""
SLIDES["ch1_A4_hotimpact"] = (CSS1, f"""
{hd1("4 / 5")}
<div style="display:flex;flex-direction:column;gap:20px;margin-top:28px">
  <div class="kick">熱點解讀・對台股的影響</div>
  <div class="h2">台股誰受影響？</div>
</div>
<div class="grow" style="gap:18px">
  {imp_row("記憶體","訂單與它綁最深","2.1%",False)}
  {imp_row("封測","上游少下單，連帶減速","1.4%",False)}
  {imp_row("散熱","與它的相關度低","0.3%",False)}
  {imp_row("AI 伺服器","需求不同線，相對抗跌","0.8%",True)}
  <div style="font-size:44px;font-weight:800;line-height:1.4;margin-top:6px">先看 <span class="y">記憶體與封測</span>，不是全面崩。</div>
</div>
{ft1()}""")

# A5 結尾（階段 0 不放網址）
SLIDES["ch1_A5_hotcta"] = (CSS1, f"""
{hd1("5 / 5")}
<div class="grow" style="align-items:flex-start;gap:30px">
  <div>{bibi("face_think", 330)}</div>
  <div class="h1" style="font-size:128px">你怎麼看？</div>
  <div class="sub">留言說說，你覺得是<span class="y" style="font-weight:800">殺錯</span>還是<span class="y" style="font-weight:800">殺對</span>？</div>
  <div style="font-size:44px;font-weight:700;color:{C1['t2']};line-height:1.4">追蹤哩股哩股，明天解讀下一個熱點</div>
</div>
{ft1()}""")

# B 單一數字大字卡
SLIDES["ch1_B_bignumber"] = (CSS1, f"""
{hd1("")}
<div class="grow" style="gap:12px;align-items:flex-start">
  <div class="kick">一個數字・ETF</div>
  <div class="n y" style="font-size:380px;line-height:1.05;margin-left:-12px">4.2%</div>
  <div class="h2" style="font-size:76px">某 ETF 近 12 個月<br>配息率</div>
  <div class="sub" style="font-size:44px;margin-top:10px">是歷史配息率，不是保證，<br>會隨配息與股價變動。</div>
</div>
{ft1("ETF")}""")

# C ETF 配息比較表
def etf_row(code, tag, freq, yld, ex, hi=False):
    bd = f"border-left:10px solid {C1['key']};" if hi else f"border-left:10px solid {C1['panel']};"
    ycol = C1['key'] if hi else C1['t1']
    return f"""<div class="box" style="{bd}display:flex;align-items:center;padding:24px 22px 24px 26px;height:164px">
      <div style="width:300px;display:flex;flex-direction:column;gap:2px"><div class="n" style="font-size:56px">{code}</div><div style="font-size:32px;color:{C1['t3']}">{tag}</div></div>
      <div style="width:200px;font-size:44px;font-weight:700;color:{C1['t2']}">{freq}</div>
      <div class="n" style="width:230px;font-size:64px;color:{ycol}">{yld}</div>
      <div class="n" style="flex:1;font-size:48px;color:{C1['t2']};text-align:right">{ex}</div></div>"""
SLIDES["ch1_C_etftable"] = (CSS1, f"""
{hd1("2 / 6")}
<div style="display:flex;flex-direction:column;gap:20px;margin-top:28px">
  <div class="kick">ETF 配息比較</div>
  <div class="h2" style="font-size:76px">這 4 檔，誰配最多？</div>
</div>
<div style="display:flex;padding:30px 26px 10px 36px;font-size:34px;font-weight:700;color:{C1['t3']}">
  <div style="width:300px">名稱</div><div style="width:200px">頻率</div><div style="width:230px">殖利率</div><div style="flex:1;text-align:right">下次除息</div></div>
<div style="display:flex;flex-direction:column;gap:16px">
  {etf_row("ETF-A","高股息型","月配","6.1%","11/18",True)}
  {etf_row("ETF-B","市值型","半年配","2.4%","12/20")}
  {etf_row("ETF-C","主動式","季配","4.0%","11/25")}
  {etf_row("ETF-D","高股息型","季配","5.2%","12/02")}
</div>
<div style="font-size:36px;color:{C1['t2']};margin-top:28px;line-height:1.4">殖利率是歷史配息率，不代表未來。</div>
{ft1("ETF")}""")

# D 產業輪動
def bar_row(rk, name, v, pct, hi=False, up=True):
    col = C1['key'] if hi else C1['bar']
    vc = C1['rise'] if up else C1['fall']
    arr = "▲" if up else "▼"
    return f"""<div style="display:flex;align-items:center;gap:22px;height:128px">
      <div class="n" style="font-size:60px;width:64px;color:{C1['key'] if hi else C1['t3']}">{rk}</div>
      <div style="width:230px;font-size:52px;font-weight:800;{'color:'+C1['key'] if hi else ''}">{name}</div>
      <div style="flex:1;height:56px;background:{C1['panel']};border-radius:8px"><div style="width:{pct}%;height:100%;background:{col};border-radius:8px"></div></div>
      <div class="n" style="width:230px;text-align:right;font-size:46px;color:{vc}">{arr} {v}</div></div>"""
SLIDES["ch1_D_rotation"] = (CSS1, f"""
{hd1("")}
<div style="display:flex;flex-direction:column;gap:20px;margin-top:28px">
  <div class="kick">產業輪動・本週</div>
  <div class="h2" style="font-size:80px">錢這週停在<br><span class="y">散熱</span>這一段</div>
</div>
<div style="font-size:38px;color:{C1['t2']};margin-top:22px">AI 伺服器供應鏈・資金淨流入（億元）</div>
<div class="grow" style="gap:6px;justify-content:flex-start;margin-top:18px">
  {bar_row(1,"散熱","+38",100,True)}
  {bar_row(2,"電源","+21",56)}
  {bar_row(3,"光通訊","+12",32)}
  {bar_row(4,"組裝","+4",11)}
  {bar_row(5,"載板","−9",24,False,False)}
</div>
{ft1("產業輪動")}""")

# E 純文字串（不附圖）規格圖
def seg(no, label, text):
    return f"""<div style="display:flex;gap:22px;align-items:stretch">
      <div style="width:210px;flex:none;display:flex;flex-direction:column;gap:6px"><div class="n y" style="font-size:60px;line-height:1.1">{no}</div><div style="font-size:34px;font-weight:700;color:{C1['t2']};line-height:1.3">{label}</div></div>
      <div class="box" style="flex:1;padding:18px 26px;font-size:36px;line-height:1.5">{text}</div></div>"""
SLIDES["ch1_E_textthread"] = (CSS1, f"""
{hd1("")}
<div style="display:flex;flex-direction:column;gap:14px;margin-top:22px">
  <div class="kick">純文字串・Threads（不附圖）</div>
  <div class="h2" style="font-size:68px">一則文字，五個段落</div>
</div>
<div class="grow" style="gap:20px;justify-content:flex-start;margin-top:26px">
  {seg("1","鉤子","某晶片大廠一天跌 17%，台股供應鏈怎麼辦？")}
  {seg("2","結論","先講結論：影響集中在兩段，不是全面崩。")}
  {seg("3","三點","・原因：財測低於預期<br>・受影響：記憶體、封測<br>・相對抗跌：AI 伺服器")}
  {seg("4","提醒","以上是邏輯整理，不是買賣建議。")}
  {seg("5","問句","你覺得這波是殺錯還是殺對？")}
</div>
{ft1("純文字串")}""")


# =============== 頻道二 ===============
def tight(t):
    return t
def ph(t="〔待填〕", fs=44):
    return f'<span class="ph" style="font-size:{fs}px;white-space:nowrap">{tight(t)}</span>'

# F1 薪資行情封面
SLIDES["ch2_F1_salarycover"] = (CSS2, f"""
{hd2("1 / 3")}
<div class="tape" data-b style="left:520px;top:52px"></div>
<div style="display:flex;flex-direction:column;gap:14px;margin-top:70px;position:relative">
  <div class="chip" style="align-self:flex-start">公司行情 / 01</div>
  <div style="font-size:150px;font-weight:900;line-height:1.1;margin-top:12px">{ph("〔公司名〕",150).replace('white-space:nowrap','white-space:nowrap;letter-spacing:-.06em;border-width:5px')}</div>
  <div style="font-size:150px;font-weight:900;line-height:1.1"><span class="hl">薪資行情</span></div>
  <div style="font-size:44px;font-weight:700;color:{C2['ink2']};margin-top:14px">碩畢・職類 {ph("〔待填〕",40)}</div>
</div>
<div class="grow" style="justify-content:flex-end;gap:20px;padding-bottom:20px">
  <div class="note" style="font-size:44px;align-self:flex-start;margin-bottom:10px">朋友提供，有誤請指正 ↓</div>
  <div class="card box" style="padding:24px 36px;display:flex;align-items:center;gap:28px;align-self:flex-start">
    <div style="font-size:40px;font-weight:800;white-space:nowrap">碩畢月薪</div>{ph("〔待填〕K",72)}</div>
  <div style="font-size:38px;font-weight:700;color:{C2['ink3']};text-align:right;margin-top:6px">滑動看七個欄位　→</div>
</div>
{ft2()}""")

# F2 欄位一覽
FIELDS = [("總部地點", "〔待填〕", "〔一句評語〕"), ("碩畢月薪", "〔待填〕K", "〔一句評語〕"), ("年終・分紅", "〔待填〕個月", "〔一句評語〕"),
          ("升等路徑", "〔待填〕", "〔一句評語〕"), ("加班時數", "〔待填〕h", "〔一句評語〕"), ("繁忙程度", "〔待填〕/5", "〔一句評語〕"), ("出差頻率", "〔待填〕", "〔一句評語〕")]
rows2 = "".join(f"""<div style="display:flex;align-items:center;gap:18px;height:112px;border-bottom:2px dashed {C2['line']}">
   <div style="width:250px;font-size:42px;font-weight:800">{a}</div><div style="width:290px">{ph(b,40)}</div>
   <div class="note" style="font-size:36px;transform:rotate(-1deg)">{c}</div></div>""" for a, b, c in FIELDS)
SLIDES["ch2_F2_fields"] = (CSS2, f"""
{hd2("2 / 3")}
<div style="margin-top:28px;display:flex;flex-direction:column;gap:12px">
  <div class="chip" style="align-self:flex-start">SPEC SHEET</div>
  <div style="font-size:80px;font-weight:900;line-height:1.2"><span class="hl">七個欄位</span>一次看完</div>
</div>
<div class="card box" style="margin-top:26px;padding:10px 36px 6px">{rows2}</div>
{ft2()}""")

# F3 結尾
SLIDES["ch2_F3_cta"] = (CSS2, f"""
{hd2("3 / 3")}
<div class="grow" style="align-items:flex-start;gap:30px">
  <div style="font-size:120px;font-weight:900;line-height:1.2">你那一組的<br><span class="hl">行情</span>呢？</div>
  <div style="font-size:52px;font-weight:700;color:{C2['ink2']};line-height:1.4">同業朋友補一下，<br>讓大家知道自己的價錢。</div>
  <div class="card box" style="padding:26px 34px;width:100%;display:flex;flex-direction:column;gap:12px">
     <div style="font-size:36px;font-weight:700;color:{C2['ink3']}">留言格式</div>
     <div class="m" style="font-size:44px">職類 / 年資 / 月薪區間</div></div>
  <div class="note" style="font-size:40px;margin-top:16px">只填你願意公開的範圍就好</div>
</div>
{ft2()}""")

# G 純文字手寫風（不附圖）
def seg2(no, label, text):
    return f"""<div style="display:flex;gap:20px;align-items:stretch">
      <div style="width:200px;flex:none;display:flex;flex-direction:column;gap:4px"><div class="m pen" style="font-size:52px;line-height:1">{no}</div><div style="font-size:32px;font-weight:700;color:{C2['blue']}">{label}</div></div>
      <div class="card box" style="flex:1;padding:14px 24px;font-size:34px;line-height:1.5;box-shadow:5px 5px 0 {C2['ink']};display:flex;flex-direction:column;justify-content:center">{text}</div></div>"""
SLIDES["ch2_G_textnote"] = (CSS2, f"""
{hd2("")}
<div style="display:flex;flex-direction:column;gap:12px;margin-top:20px">
  <div class="chip" style="align-self:flex-start">純文字・Threads（不附圖）</div>
  <div style="font-size:66px;font-weight:900;line-height:1.2">一則文字，<span class="hl">七個段落</span></div>
</div>
<div class="grow" style="gap:16px;justify-content:flex-start;margin-top:24px">
  {seg2("1","搜尋詞標題","〔公司名〕 行情分享")}
  {seg2("2","圈內梗","代號〔綽號〕，因為〔一句好笑的由來〕")}
  {seg2("3","來源說明","以下是業內朋友的分享，有誤麻煩告知")}
  {seg2("4","欄位清單","・碩畢：〔待填〕　・分紅：〔待填〕<br>・繁忙：〔待填〕")}
  {seg2("5","軟評語","〔一句有立場的話〕")}
  {seg2("6","面試加料","順便分享面談經驗：〔一點〕")}
  {seg2("7","邀請補充","歡迎同業補自己那組的行情")}
</div>
{ft2("純文字手寫風")}""")

# H1 面試題卡
SLIDES["ch2_H1_interviewQ"] = (CSS2, f"""
{hd2("1 / 3")}
<div class="tape" data-b style="left:560px;top:52px;transform:rotate(3deg)"></div>
<div class="grow" style="align-items:flex-start;gap:22px;position:relative">
  <div class="chip">面試題 #〔編號〕・製程整合</div>
  <div class="m pen" style="font-size:240px;line-height:1.15;margin-left:-6px">Q.</div>
  <div style="font-size:84px;font-weight:900;line-height:1.3">晶片面積放大 2 倍，<br><span class="hl">良率會剛好剩一半嗎？</span></div>
  <div class="note" style="font-size:46px;margin-top:10px">先想 10 秒，再滑動看答案 →</div>
</div>
{ft2()}""")

# H2 答題框架
def step(no, t, d, hi=False):
    bd = f"border-color:{C2['pen']};" if hi else ""
    return f"""<div class="card box" style="{bd}padding:24px 30px;display:flex;gap:26px;align-items:center">
     <div class="m pen" style="font-size:72px;width:100px;flex:none">{no}</div>
     <div style="display:flex;flex-direction:column;gap:6px"><div style="font-size:50px;font-weight:900">{t}</div><div style="font-size:36px;color:{C2['ink2']};line-height:1.4">{d}</div></div></div>"""
SLIDES["ch2_H2_interviewA"] = (CSS2, f"""
{hd2("2 / 3")}
<div style="margin-top:26px;display:flex;flex-direction:column;gap:12px">
  <div class="chip" style="align-self:flex-start">答題框架</div>
  <div style="font-size:76px;font-weight:900;line-height:1.2">不是一半，<span class="hl">是平方</span></div>
</div>
<div class="grow" style="gap:22px;justify-content:flex-start;margin-top:26px">
  {step("01","先講結論","比一半更少，良率會被「平方」")}
  {step("02","缺陷是隨機落點","面積越大，被打到的機率越高")}
  {step("03","一條公式收尾",'<span class="m">Y = e<sup style="font-size:36px">−A·D</sup></span>　面積 ×2 → 良率²',True)}
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px"><div class="chip" style="align-self:flex-start;border-color:{C2['pen']};color:{C2['pen2']}">常見踩雷</div>
  <div style="font-size:44px;font-weight:800;line-height:1.4">只答「剩一半」，面試官會追問：<br>缺陷為什麼是<span class="hl">隨機</span>的？</div></div>
</div>
{ft2()}""")

# I 知識圖解：良率（缺陷位置用固定種子模擬，數量用程式實際數）
def wafer_svg(die_w, die_h, defects, size=420, name=""):
    R = size / 2
    cx = cy = R
    ndies = bad = 0
    rects = []
    y = -R + (R % die_h) * 0
    ny = int(size // die_h); nx = int(size // die_w)
    ox = (size - nx * die_w) / 2; oy = (size - ny * die_h) / 2
    for j in range(ny):
        for i in range(nx):
            x0 = ox + i * die_w; y0 = oy + j * die_h
            corners = [(x0, y0), (x0 + die_w, y0), (x0, y0 + die_h), (x0 + die_w, y0 + die_h)]
            if all((px - cx) ** 2 + (py - cy) ** 2 <= (R - 6) ** 2 for px, py in corners):
                hit = any(x0 <= dx < x0 + die_w and y0 <= dy < y0 + die_h for dx, dy in defects)
                ndies += 1; bad += hit
                fill = C2['pen'] if hit else "#E7DCC2"
                rects.append(f'<rect x="{x0+2:.1f}" y="{y0+2:.1f}" width="{die_w-4:.1f}" height="{die_h-4:.1f}" fill="{fill}" stroke="{C2["ink"]}" stroke-width="1.5"/>')
    dots = "".join(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="7" fill="{C2["ink"]}" stroke="#fff" stroke-width="2"/>' for dx, dy in defects)
    svg = (f'<svg data-b width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{cx}" cy="{cy}" r="{R-2}" fill="{C2["card"]}" stroke="{C2["ink"]}" stroke-width="4"/>'
           f'{"".join(rects)}{dots}</svg>')
    return svg, ndies, bad

def make_defects(seed):
    rnd = random.Random(seed)
    out = []
    while len(out) < 8:
        x, y = rnd.uniform(40, 380), rnd.uniform(40, 380)
        if (x - 210) ** 2 + (y - 210) ** 2 <= 180 ** 2:
            out.append((x, y))
    return out
# 8 顆缺陷隨機落點；挑最接近期望值（小片壞約 7～8 顆、大片壞約 7 顆）的一次模擬當樣張，不是挑最戲劇化的
SEED = min(range(300), key=lambda sd: abs(wafer_svg(40, 40, make_defects(sd))[2] - 8) + abs(wafer_svg(40, 80, make_defects(sd))[2] - 7))
DEF = make_defects(SEED)
svgS, nS, bS = wafer_svg(40, 40, DEF)
svgB, nB, bB = wafer_svg(40, 80, DEF)    # 面積 2 倍：40×80
yS, yB = (nS - bS) / nS, (nB - bB) / nB
SLIDES["ch2_I_diagram"] = (CSS2, f"""
{hd2("")}
<div style="margin-top:24px;display:flex;flex-direction:column;gap:12px">
  <div class="chip" style="align-self:flex-start">圖解・良率</div>
  <div style="font-size:70px;font-weight:900;line-height:1.2">同樣 8 顆缺陷，<br><span class="hl">大晶片良率更低</span></div>
</div>
<div style="display:flex;gap:40px;margin-top:26px;justify-content:space-between">
  <div style="display:flex;flex-direction:column;gap:14px;align-items:center">{svgS}
     <div style="font-size:42px;font-weight:800">小晶片</div>
     <div class="m" style="font-size:44px">好 {nS-bS} / 共 {nS}</div>
     <div class="m pen" style="font-size:56px">{yS*100:.0f}%</div></div>
  <div style="display:flex;flex-direction:column;gap:14px;align-items:center">{svgB}
     <div style="font-size:42px;font-weight:800">面積 ×2</div>
     <div class="m" style="font-size:44px">好 {nB-bB} / 共 {nB}</div>
     <div class="m pen" style="font-size:56px">{yB*100:.0f}%</div></div>
</div>
<div class="card box" style="margin-top:auto;margin-bottom:30px;padding:16px 34px;display:flex;align-items:center;gap:28px">
  <div class="m" style="font-size:60px">Y = e<sup style="font-size:36px">−A·D</sup></div>
  <div style="font-size:38px;font-weight:700;color:{C2['ink2']};line-height:1.35">面積 ×2，<br>良率變平方</div></div>
{ft2("業內知識")}""")

ORDER = list(SLIDES)

# ---------------- 檢查器（頁面內執行）----------------
CHECK_JS = """
() => {
  const W = 1080, H = 1350, M = 40;
  const out = {overlap: [], bounds: [], small: [], overflow: [], textBlock: [], n: 0};
  const items = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const byEl = new Map();
  let t;
  while ((t = walker.nextNode())) {
    if (!t.nodeValue.trim()) continue;
    const el = t.parentElement;
    if (!byEl.has(el)) byEl.set(el, []);
    byEl.get(el).push(t);
  }
  for (const [el, nodes] of byEl) {
    const rects = [];
    for (const n of nodes) {
      const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) if (q.width > 1 && q.height > 1) { const d = q.height * 0.1; rects.push({left:q.left, right:q.right, top:q.top + d, bottom:q.bottom - d}); }
    }
    if (!rects.length) continue;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    const meta = !!el.closest('[data-meta]');
    items.push({el, rects, fs, meta, txt: nodes.map(n => n.nodeValue.trim()).join('').slice(0, 14)});
  }
  out.n = items.length;
  const inter = (a, b, tol) => !(a.right <= b.left + tol || b.right <= a.left + tol || a.bottom <= b.top + tol || b.bottom <= a.top + tol);
  for (const it of items) {
    if (!it.meta && it.fs < 32 - 0.01) out.small.push(it.txt + ' ' + it.fs);
    if (it.meta && it.fs < 24) out.small.push('meta ' + it.txt + ' ' + it.fs);
    for (const r of it.rects) {
      if (r.left < M - 1 || r.right > W - M + 1 || r.top < M - 1 || r.bottom > H - M + 1) out.bounds.push(it.txt);
    }
    const box = it.el.closest('.box');
    if (box) {
      const b = box.getBoundingClientRect();
      for (const r of it.rects) if (r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1) out.overflow.push(it.txt);
    }
  }
  for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
    const a = items[i], b = items[j];
    if (a.el.contains(b.el) || b.el.contains(a.el)) {
      // 巢狀：只比各自自己的文字節點
    }
    let hit = false;
    for (const ra of a.rects) { for (const rb of b.rects) if (inter(ra, rb, 2)) { hit = true; break; } if (hit) break; }
    if (hit) out.overlap.push(a.txt + ' x ' + b.txt);
  }
  // 文字 vs 圖片／圖形
  for (const blk of document.querySelectorAll('[data-b]')) {
    const br = blk.getBoundingClientRect();
    for (const it of items) {
      if (blk.contains(it.el)) continue;
      for (const r of it.rects) if (inter(r, br, 2)) { out.textBlock.push(it.txt + ' x [圖]'); break; }
    }
    if (br.left < M - 1 || br.right > W - M + 1 || br.top < M - 1 || br.bottom > H - M + 1) out.bounds.push('[圖]');
  }
  return out;
}
"""


def render():
    results = {}
    with sync_playwright() as p:
        import glob, os
        exe = next(iter(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome"))), None)
        br = p.chromium.launch(executable_path=exe) if exe and not os.environ.get("PW_DEFAULT") else p.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for name in ORDER:
            css, body = SLIDES[name]
            pg.set_content(f"<!doctype html><meta charset=utf-8><style>{css}</style><body>{body}</body>")
            pg.wait_for_timeout(150)
            res = pg.evaluate(CHECK_JS)
            pg.screenshot(path=str(HERE / f"{name}.png"))
            results[name] = res
        br.close()
    return results


if __name__ == "__main__":
    res = render()
    total = 0
    for name, r in res.items():
        issues = sum(len(r[k]) for k in ("overlap", "bounds", "small", "overflow", "textBlock"))
        total += issues
        print(f"{name:24s} 文字塊 {r['n']:3d}  重疊 {len(r['overlap'])}  出界 {len(r['bounds'])}  出框 {len(r['overflow'])}  壓圖 {len(r['textBlock'])}  字太小 {len(r['small'])}")
        for k in ("overlap", "bounds", "small", "overflow", "textBlock"):
            for x in r[k]:
                print("    ", k, x)
    print(f"重疊檢查：程式 {len(res)} 張 {total} 筆")
    print(f"良率圖：小 {nS} 顆壞 {bS}（良率 {yS:.2f}）；大 {nB} 顆壞 {bB}（良率 {yB:.2f}）")
