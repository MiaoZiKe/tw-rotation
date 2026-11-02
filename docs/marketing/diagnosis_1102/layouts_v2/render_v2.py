"""兩個頻道版型 v2（美術，2026-11-02）：頻道一明亮友善、頻道二企業專業，各 2 套配色。
用法：python render_v2.py   輸出 PNG 到本資料夾，並印出「重疊檢查」與對比度表。
字型：優先用 Noto Sans TC（OFL 授權，可商用；由 `npm pack @fontsource/noto-sans-tc` 取得，
解開後放在 TW_FONT_DIR，預設見下方；68MB，不進 repo），找不到就退回文泉驛正黑。數字用 Inter。
全部為假資料／〔待填〕，每張右下角有「示意」小字。沒有比比、沒有 AI 生圖，圖示全是 SVG 幾何。
"""
import os, random, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FONT_DIR = Path(os.environ.get("TW_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/b18b8d62-af9e-5c62-ba83-cf290f45823d/scratchpad/noto_tc"))
TMP = Path(os.environ.get("TW_TMP", str(FONT_DIR.parent)))
W, H = 1080, 1350
HAVE_NOTO = (FONT_DIR / "noto.css").exists()
FONT = "'Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
NUM = "Inter,'Noto Sans TC',sans-serif"


# ======================= 色票 =======================
# 頻道一：四個內容柱各一色（熱點／ETF／產業輪動／知識），框架一致、顏色有變化。紅漲綠跌只用在漲跌。
T1A = dict(key="1A", name="方案 1　陽光糖果", bg="#FFF7E8", bgx="", ink="#1F2A44", ink2="#46526E", ink3="#5B6682",
           card="#FFFFFF", line="#EBDFC8", rise="#D62839", fall="#0B8F4D", mode="solid",
           shadow="0 10px 28px rgba(31,42,68,.12)", cardbd="none",
           P=dict(hot=dict(main="#E8590C", tint="#FFE1CF", deep="#C2410C", mid="#F7B58F", label="熱點解讀"),
                  etf=dict(main="#2B6BF3", tint="#DCE8FF", deep="#1F55CC", mid="#A9C4FA", label="ETF 存股"),
                  rot=dict(main="#7B4FE0", tint="#E6DCFB", deep="#6238C4", mid="#C9B8F4", label="產業輪動"),
                  know=dict(main="#0A8CA3", tint="#D3F0F5", deep="#08758A", mid="#9ED5DF", label="小知識")))
T1B = dict(key="1B", name="方案 2　粉彩糖霜", bg="#F6F4FF", bgx="background-image:radial-gradient(#EAE5FB 2.2px,transparent 2.6px);background-size:40px 40px;",
           ink="#241F47", ink2="#4A4670", ink3="#605C86", card="#FFFFFF", line="#E1DBF7", rise="#D62839", fall="#0B8F4D", mode="pastel",
           shadow="0 8px 24px rgba(60,40,160,.10)", cardbd="2px solid #E1DBF7",
           P=dict(hot=dict(main="#F4511E", tint="#FFE4D9", deep="#C2410C", mid="#FFC2A8", label="熱點解讀"),
                  etf=dict(main="#1F6FEB", tint="#DCEBFF", deep="#1856B8", mid="#AFCCF8", label="ETF 存股"),
                  rot=dict(main="#7C3AED", tint="#EADFFF", deep="#5B21B6", mid="#CDB6F8", label="產業輪動"),
                  know=dict(main="#0891B2", tint="#D5F2F8", deep="#0E7490", mid="#A3DAE8", label="小知識")))

# 頻道二：企業簡報質感。2A 白底＋深藍灰＋藍綠；2B 午夜藍灰＋香檳金。
T2A = dict(key="2A", name="方案 1　藍灰報告", dark=False, bg="#FFFFFF", band="#13263B", bandtx="#FFFFFF", rule="#00857C",
           ink="#13263B", ink2="#3C4B5C", ink3="#586879", line="#D3DAE2", panel="#F4F6F8", panel2="#E9EEF3",
           acc="#00857C", accdeep="#00675F", acctint="#DDF0EE", onacc="#FFFFFF", good="#E3E9EF", goodbd="#9AA9B8", bad="#00857C")
T2B = dict(key="2B", name="方案 2　午夜香檳", dark=True, bg="#0D1B2A", band="#08121D", bandtx="#F2F5F8", rule="#D9B36C",
           ink="#F2F5F8", ink2="#C2CDD9", ink3="#94A5B8", line="#2A415A", panel="#14263A", panel2="#1B3249",
           acc="#D9B36C", accdeep="#D9B36C", acctint="#2A2F36", onacc="#0D1B2A", good="#1E3550", goodbd="#4A6683", bad="#D9B36C")


def lum(h):
    h = h.lstrip("#"); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def cr(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)


# ======================= 圖示（SVG 幾何，沒有比比、沒有 AI）=======================
def icon(kind, size=40, color="#fff", sw=2.4):
    p = {
        "hot": '<path d="M13 2 4 14h7l-1 8 9-12h-7z" fill="%s" stroke="none"/>' % color,
        "etf": '<circle cx="12" cy="12" r="9"/><path d="M12 3v9h9" fill="%s" stroke="none" opacity=".95"/><path d="M12 12 5.6 18.4"/>' % color,
        "rot": '<path d="M21 4v5h-5"/><path d="M3 20v-5h5"/><path d="M4.6 9a8.5 8.5 0 0 1 14.6-2.6L21 9"/><path d="M3 15l1.8 2.6A8.5 8.5 0 0 0 19.4 15"/>',
        "know": '<path d="M9 18h6M10 21.5h4"/><path d="M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.6.5 1 1.2 1 2h5.6c0-.8.4-1.5 1-2A6.5 6.5 0 0 0 12 2.5z"/>',
    }[kind]
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" style="flex:none">{p}</svg>'


def svg_fall_chart(P, T):
    """熱點封面插圖：下滑的長條＋向下箭頭（綠＝跌）。純幾何，沒有字。"""
    bars = [(34, 150), (96, 124), (158, 96), (220, 64)]
    cols = [P["mid"], P["mid"], P["mid"], P["main"] if T["mode"] == "pastel" else P["main"]]
    r = "".join(f'<rect x="{x}" y="{200-h}" width="44" height="{h}" rx="12" fill="{c}"/>' for (x, h), c in zip(bars, cols))
    return (f'<svg data-b width="330" height="270" viewBox="0 0 330 270"><rect x="0" y="0" width="330" height="270" rx="36" fill="#fff"/>'
            f'<rect x="20" y="226" width="290" height="6" rx="3" fill="{T["line"]}"/>{r}'
            f'<circle cx="274" cy="70" r="40" fill="{T["fall"]}"/><path d="M274 52v34M258 72l16 16 16-16" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')


def svg_coins(P, T, w=150):
    def coin(y):
        return (f'<rect x="25" y="{y}" width="100" height="26" fill="{P["main"]}"/><ellipse cx="75" cy="{y+26}" rx="50" ry="16" fill="{P["main"]}"/>'
                f'<ellipse cx="75" cy="{y}" rx="50" ry="16" fill="{P["tint"]}" stroke="{P["main"]}" stroke-width="6"/><ellipse cx="75" cy="{y}" rx="26" ry="7" fill="none" stroke="{P["mid"]}" stroke-width="4"/>')
    return f'<svg data-b width="{w}" height="{w}" viewBox="0 0 150 150">{coin(96)}{coin(66)}{coin(36)}</svg>'


def svg_pie(P, T, w=170):
    return (f'<svg data-b width="{w}" height="{w}" viewBox="0 0 170 170"><circle cx="85" cy="85" r="78" fill="#fff" opacity=".95"/>'
            f'<circle cx="85" cy="85" r="64" fill="{P["tint"]}"/><path d="M85 85V21A64 64 0 0 1 143 112Z" fill="{P["main"]}"/>'
            f'<path d="M85 85 143 112A64 64 0 0 1 40 134Z" fill="{P["mid"]}"/><circle cx="85" cy="85" r="24" fill="#fff"/></svg>')


def svg_cycle(P, T, w=170):
    return (f'<svg data-b width="{w}" height="{w}" viewBox="0 0 170 170"><circle cx="85" cy="85" r="78" fill="#fff" opacity=".95"/>'
            f'<g fill="none" stroke="{P["main"]}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M40 82a46 46 0 0 1 80-24"/><path d="M130 88a46 46 0 0 1-80 24" stroke="{P["mid"]}"/></g>'
            f'<path d="M126 36l-4 28-26-10z" fill="{P["main"]}"/><path d="M44 134l4-28 26 10z" fill="{P["mid"]}"/></svg>')


# ======================= 頻道一 =======================
def css1(T, pk):
    P = T["P"][pk]; solid = T["mode"] == "solid"
    band = P["main"] if solid else P["tint"]
    bandtx = "#FFFFFF" if solid else T["ink"]
    bandsub = "rgba(255,255,255,.92)" if solid else T["ink2"]
    chipbg = "rgba(255,255,255,.24)" if solid else P["main"]
    return f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{T['ink']};background:{T['bg']};{T['bgx']}display:flex;flex-direction:column;overflow:hidden;position:relative}}
.n{{font-family:{NUM};font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
.band{{background:{band};color:{bandtx};border-radius:0 0 64px 64px;padding:56px 64px 56px;flex:none;position:relative}}
.hd{{display:flex;align-items:center;gap:16px;height:72px}}
.brand{{background:#fff;color:{T['ink']};border-radius:36px;height:64px;padding:0 30px;display:flex;align-items:center;font-size:36px;font-weight:900;white-space:nowrap}}
.chip{{display:flex;align-items:center;gap:10px;height:56px;padding:0 22px 0 16px;border-radius:28px;background:{chipbg};color:#fff;font-size:32px;font-weight:700;white-space:nowrap}}
.pg{{margin-left:auto;font-size:32px;font-weight:700;color:{bandsub}}}
.kick{{font-size:38px;font-weight:700;color:{bandsub};letter-spacing:.03em}}
.h1{{font-size:112px;font-weight:900;line-height:1.18;color:{bandtx}}}
.h2{{font-weight:900;line-height:1.2;color:{bandtx}}}
.acc{{color:{P['deep']}}}
.body{{padding:0 64px;flex:1;display:flex;flex-direction:column}}
.card{{background:{T['card']};border-radius:28px;box-shadow:{T['shadow']};border:{T['cardbd']}}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {T['line']};display:flex;align-items:flex-end;justify-content:space-between;background:{T['bg']}}}
.ft span{{font-size:28px;color:{T['ink3']};font-weight:500}}
.deco{{position:absolute;right:64px}}
.btn{{display:inline-flex;align-items:center;gap:12px;height:84px;padding:0 38px;border-radius:42px;background:{P['main']};color:#fff;font-size:40px;font-weight:800;white-space:nowrap}}
"""


def hd1(T, pk, pg=""):
    P = T["P"][pk]; kind = {"hot": "hot", "etf": "etf", "rot": "rot", "know": "know"}[pk]
    return (f'<div class="hd"><div class="brand">哩股哩股</div><div class="chip">{icon(kind, 34)}<span>{P["label"]}</span></div>'
            f'<div class="pg">{pg}</div></div>')


def ft1(T, pk):
    return f'<div class="ft"><span data-meta>{T["P"][pk]["label"]}</span><span data-meta>示意・假資料</span></div>'


def build_ch1(T):
    S = {}
    key = T["key"]; n = "1" if key[1] == "A" else "2"
    # ---- 1 熱點封面 ----
    P = T["P"]["hot"]
    S[f"ch1_s{n}_1_hot_cover"] = (css1(T, "hot"), f"""
<div class="band" style="padding-bottom:60px">
  {hd1(T,'hot','1 / 5')}
  <div class="deco" data-b style="top:176px">{svg_fall_chart(P, T)}</div>
  <div class="kick" style="margin-top:44px">熱點解讀・11/02</div>
  <div class="h1" style="margin-top:14px">某晶片大廠<br>單日重挫</div>
  <div class="card" style="margin-top:30px;display:inline-flex;align-items:center;gap:8px;padding:10px 44px 10px 40px;box-shadow:none">
    <svg data-b width="124" height="108" viewBox="0 0 124 108" style="margin-right:14px"><path d="M8 10h108L62 100z" fill="{T['fall']}" stroke="{T['fall']}" stroke-width="10" stroke-linejoin="round"/></svg>
    <span class="n" style="font-size:270px;line-height:1.02;color:{T['fall']}">17%</span></div>
</div>
<div class="body" style="padding-top:60px;gap:40px">
  <div style="font-size:60px;font-weight:800;line-height:1.35">AI 浪潮裡，它到底<span class="acc">少了什麼</span>？</div>
  <div><span class="btn">滑動看 3 個原因　→</span></div>
</div>
{ft1(T,'hot')}""")

    # ---- 2 知識大數字卡 ----
    P = T["P"]["know"]
    def eq(label, val, hi=False):
        if hi:
            bg = P["main"] if T["mode"] == "solid" else P["tint"]
            col = "#fff" if T["mode"] == "solid" else P["deep"]
            bd = "" if T["mode"] == "solid" else f"border:4px solid {P['main']};"
            sub = "#fff" if T["mode"] == "solid" else T["ink2"]
        else:
            bg, col, bd, sub = T["card"], T["ink"], "", T["ink2"]
        return (f'<div class="card box" style="width:{268 if hi else 290}px;height:208px;background:{bg};{bd}display:flex;flex-direction:column;justify-content:center;align-items:center;gap:6px">'
                f'<div style="font-size:34px;font-weight:700;color:{sub}">{label}</div><div class="n" style="font-size:62px;color:{col}">{val}</div></div>')
    op = lambda s: f'<div class="n" style="width:60px;text-align:center;font-size:64px;color:{T["ink3"]}">{s}</div>'
    S[f"ch1_s{n}_2_know_number"] = (css1(T, "know"), f"""
<div class="band" style="padding-bottom:56px">
  {hd1(T,'know','2 / 5')}
  <div class="kick" style="margin-top:40px">一個數字・小知識</div>
  <div class="n" style="font-size:340px;line-height:1.04;margin:6px 0 0 -10px;color:{'#fff' if T['mode']=='solid' else P['deep']}">4.2%</div>
</div>
<div class="body" style="padding-top:44px;gap:34px">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <div style="font-size:66px;font-weight:900;line-height:1.25">殖利率是<span class="acc">怎麼算</span>的？</div>
    <div data-b>{svg_coins(P, T, 140)}</div></div>
  <div style="display:flex;align-items:center">{eq('每股配息','2.1 元')}{op('÷')}{eq('股價','50 元')}{op('＝')}{eq('殖利率','4.2%',True)}</div>
  <div style="font-size:38px;font-weight:500;color:{T['ink2']};line-height:1.45">用過去的配息算出來的數字，<br>不是保證，會隨股價變動。</div>
</div>
{ft1(T,'know')}""")

    # ---- 3 ETF 配息比較表 ----
    P = T["P"]["etf"]
    def row(rank, code, tag, freq, yld, ex, hi=False):
        ypill = (f'<div class="n" style="background:{P["main"]};color:#fff;border-radius:22px;padding:4px 20px;font-size:54px;white-space:nowrap">{yld}</div>' if hi
                 else f'<div class="n" style="font-size:54px;padding:4px 20px;white-space:nowrap">{yld}</div>')
        rb = P["main"] if hi else P["tint"]; rc = "#fff" if hi else P["deep"]
        return f"""<div class="card box" style="height:156px;display:flex;align-items:center;padding:0 24px 0 24px;gap:14px">
  <div class="n" style="width:62px;height:62px;border-radius:50%;background:{rb};color:{rc};font-size:34px;display:flex;align-items:center;justify-content:center;flex:none">{rank}</div>
  <div style="width:236px;display:flex;flex-direction:column;gap:0"><div class="n" style="font-size:48px;line-height:1.15">{code}</div><div style="font-size:32px;color:{T['ink3']};font-weight:500">{tag}</div></div>
  <div style="width:150px;font-size:40px;font-weight:700;color:{T['ink2']}">{freq}</div>
  <div style="width:210px;display:flex">{ypill}</div>
  <div class="n" style="flex:1;font-size:44px;text-align:right;color:{T['ink2']}">{ex}</div></div>"""
    colhd = f'<div style="display:flex;padding:0 24px;gap:14px;font-size:32px;font-weight:700;color:{T["ink3"]}"><div style="width:62px"></div><div style="width:236px">名稱</div><div style="width:150px">配息頻率</div><div style="width:210px">殖利率</div><div style="flex:1;text-align:right">下次除息</div></div>'
    S[f"ch1_s{n}_3_etf_table"] = (css1(T, "etf"), f"""
<div class="band" style="padding-bottom:52px">
  {hd1(T,'etf','2 / 6')}
  <div class="deco" data-b style="top:170px">{svg_pie(P, T, 176)}</div>
  <div class="kick" style="margin-top:36px">ETF 配息比較</div>
  <div class="h2" style="font-size:72px;margin-top:10px">這 4 檔，誰配最多？</div>
</div>
<div class="body" style="padding-top:34px;gap:14px">
  {colhd}
  {row(1,'ETF-A','高股息型','月配','6.1%','11/18',True)}
  {row(2,'ETF-B','市值型','半年配','2.4%','12/20')}
  {row(3,'ETF-C','主動式','季配','4.0%','11/25')}
  {row(4,'ETF-D','高股息型','季配','5.2%','12/02')}
  <div style="font-size:34px;font-weight:500;color:{T['ink2']};margin-top:8px;line-height:1.4">殖利率是歷史配息率，不代表未來。ETF-A～D 為示意名稱。</div>
</div>
{ft1(T,'etf')}""")

    # ---- 4 產業輪動圖 ----
    P = T["P"]["rot"]
    def brow(rank, name, val, up, hi=False, maxv=38):
        col = T["rise"] if up else T["fall"]; arr = "▲" if up else "▼"; sign = "+" if up else "−"
        wpct = max(6, abs(val) / maxv * 100)
        fill = P["main"] if hi else P["mid"]
        return f"""<div style="display:flex;align-items:center;gap:18px;height:106px">
  <div class="n" style="width:50px;font-size:46px;color:{P['deep'] if hi else T['ink3']}">{rank}</div>
  <div style="width:176px;font-size:48px;font-weight:800">{name}</div>
  <div style="flex:1;height:34px;border-radius:17px;background:{P['tint']}"><div style="width:{wpct:.0f}%;height:34px;border-radius:17px;background:{fill}"></div></div>
  <div class="n" style="width:170px;text-align:right;font-size:46px;color:{col};white-space:nowrap">{arr} {sign}{abs(val)}</div></div>"""
    S[f"ch1_s{n}_4_rotation"] = (css1(T, "rot"), f"""
<div class="band" style="padding-bottom:52px">
  {hd1(T,'rot','2 / 5')}
  <div class="deco" data-b style="top:170px">{svg_cycle(P, T, 176)}</div>
  <div class="kick" style="margin-top:36px">產業輪動・本週</div>
  <div class="h2" style="font-size:72px;margin-top:10px">錢這週停在<span style="color:{'#fff' if T['mode']=='solid' else P['deep']};{'background:rgba(255,255,255,.22);border-radius:14px;padding:0 14px;' if T['mode']=='solid' else 'background:#fff;border-radius:14px;padding:0 14px;'}">散熱</span><br>這一段</div>
</div>
<div class="body" style="padding-top:34px;gap:22px">
  <div style="font-size:36px;font-weight:600;color:{T['ink2']}">AI 伺服器供應鏈・資金淨流入（億元）</div>
  <div class="card box" style="padding:10px 32px">
    {brow(1,'散熱',38,True,True)}{brow(2,'電源',21,True)}{brow(3,'光通訊',12,True)}{brow(4,'組裝',4,True)}{brow(5,'載板',-9,False)}
  </div>
  <div style="font-size:44px;font-weight:800;line-height:1.4">資金先到<span class="acc">散熱</span>，其次電源。</div>
</div>
{ft1(T,'rot')}""")
    return S


# ======================= 頻道二 =======================
def css2(T):
    dark = T["dark"]
    return f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{T['ink']};background:{T['bg']};display:flex;flex-direction:column;overflow:hidden;position:relative}}
.n{{font-family:{NUM};font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.top{{background:{T['band']};height:128px;flex:none;padding:0 64px;display:flex;align-items:center;gap:20px;border-bottom:6px solid {T['rule']}}}
.top .b{{font-size:38px;font-weight:900;color:{T['bandtx']};letter-spacing:.04em}}
.top .t{{font-size:32px;font-weight:500;color:{'#C2CDD9' if dark else '#C9D4DF'}}}
.top .p{{margin-left:auto;font-size:32px;font-weight:700;color:{T['bandtx']}}}
.body{{padding:52px 64px 0;flex:1;display:flex;flex-direction:column}}
.tag{{display:inline-flex;align-items:center;height:52px;padding:0 20px;font-size:32px;font-weight:700;border-radius:4px;background:{T['acctint']};color:{T['accdeep']};white-space:nowrap}}
.tag.g{{background:{T['panel2']};color:{T['ink2']}}}
.ph{{display:inline-block;border:2px dashed {T['acc']};background:{T['acctint']};color:{T['accdeep']};border-radius:4px;padding:2px 14px;font-weight:700;white-space:nowrap}}
.box{{background:{T['panel']};border:2px solid {T['line']};border-radius:6px}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {T['line']};display:flex;align-items:flex-end;justify-content:space-between}}
.ft span{{font-size:28px;color:{T['ink3']};font-weight:500}}
.lab{{font-size:32px;font-weight:700;color:{T['ink3']}}}
"""


def hd2(T, pg, label="薪資行情簡報"):
    return f'<div class="top"><div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'


def ft2(T, left="資料來源：朋友提供，有誤請指正"):
    return f'<div class="ft"><span data-meta>{left}</span><span data-meta>示意・假資料</span></div>'


def wafer_svg(T, die_w, die_h, defects, size=380):
    R = size / 2; cx = cy = R; ndies = bad = 0; rects = []
    ny = int(size // die_h); nx = int(size // die_w)
    ox = (size - nx * die_w) / 2; oy = (size - ny * die_h) / 2
    for j in range(ny):
        for i in range(nx):
            x0 = ox + i * die_w; y0 = oy + j * die_h
            corners = [(x0, y0), (x0 + die_w, y0), (x0, y0 + die_h), (x0 + die_w, y0 + die_h)]
            if all((px - cx) ** 2 + (py - cy) ** 2 <= (R - 6) ** 2 for px, py in corners):
                hit = any(x0 <= dx < x0 + die_w and y0 <= dy < y0 + die_h for dx, dy in defects)
                ndies += 1; bad += hit
                fill = T["bad"] if hit else T["good"]; st = T["bad"] if hit else T["goodbd"]
                rects.append(f'<rect x="{x0+2:.1f}" y="{y0+2:.1f}" width="{die_w-4:.1f}" height="{die_h-4:.1f}" rx="3" fill="{fill}" stroke="{st}" stroke-width="1.5"/>')
    dots = "".join(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="7" fill="{T["ink"] if not T["dark"] else "#0D1B2A"}" stroke="{"#fff" if not T["dark"] else "#F2F5F8"}" stroke-width="2.5"/>' for dx, dy in defects)
    svg = (f'<svg data-b width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{cx}" cy="{cy}" r="{R-2}" fill="{T["bg"] if not T["dark"] else T["panel2"]}" stroke="{T["goodbd"]}" stroke-width="3"/>'
           f'{"".join(rects)}{dots}</svg>')
    return svg, ndies, bad


def make_defects(seed, size=380):
    rnd = random.Random(seed); out = []; R = size / 2
    while len(out) < 8:
        x, y = rnd.uniform(30, size - 30), rnd.uniform(30, size - 30)
        if (x - R) ** 2 + (y - R) ** 2 <= (R - 30) ** 2: out.append((x, y))
    return out


_T_REF = dict(bad="#000", good="#eee", goodbd="#999", ink="#000", dark=False, bg="#fff", panel2="#eee")
SEED = min(range(400), key=lambda sd: abs(wafer_svg(_T_REF, 36, 36, make_defects(sd))[2] - 8) + abs(wafer_svg(_T_REF, 36, 72, make_defects(sd))[2] - 7))
DEF = make_defects(SEED)


def build_ch2(T):
    S = {}; k = "1" if T["key"][1] == "A" else "2"; css = css2(T)
    ph = lambda s, fs=36: f'<span class="ph" style="font-size:{fs}px">{s}</span>'
    # ---- 1 薪資欄位卡封面 ----
    cell = lambda lab, v: (f'<div style="flex:1;padding:18px 24px;border-left:2px solid {T["line"]}"><div class="lab">{lab}</div>'
                           f'<div style="margin-top:8px">{ph(v,44)}</div></div>')
    S[f"ch2_s{k}_1_cover"] = (css, f"""
{hd2(T,'1 / 3')}
<div class="body">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">公司薪資行情</span><span class="tag g">碩畢・研發職類</span></div>
  <div style="margin-top:34px;display:inline-flex;align-self:flex-start;border:3px dashed {T['acc']};background:{T['acctint']};border-radius:6px;padding:6px 34px 12px">
     <span style="font-size:150px;font-weight:900;line-height:1.2;color:{T['accdeep']}">〔公司名〕</span></div>
  <div style="font-size:150px;font-weight:900;line-height:1.2;margin-top:6px;color:{T['ink']}">薪資行情</div>
  <div style="margin-top:44px;display:flex;border-top:3px solid {T['ink']};border-bottom:2px solid {T['line']}">
    <div style="flex:1;padding:18px 24px 18px 0"><div class="lab">職類</div><div style="margin-top:8px">{ph('〔待填〕',44)}</div></div>
    {cell('學歷','〔待填〕')}{cell('年資','〔待填〕')}</div>
  <div class="box" style="margin-top:44px;display:flex;align-items:center;gap:30px;padding:26px 34px;border-left:12px solid {T['acc']}">
    <div style="font-size:46px;font-weight:800;line-height:1.2">碩畢<br>月薪</div>
    <div class="n" style="font-size:96px;line-height:1;color:{T['accdeep']}">〔待填〕K</div></div>
  <div style="margin-top:40px;font-size:38px;font-weight:600;color:{T['ink2']}">朋友提供，有誤請指正</div>
</div>
{ft2(T)}""")

    # ---- 2 七欄位卡 ----
    rows = [("總部地點", "〔待填〕", ""), ("碩畢月薪", "〔待填〕", "K"), ("年終・分紅", "〔待填〕", "個月"), ("升等路徑", "〔待填〕", ""),
            ("加班時數", "〔待填〕", "h"), ("繁忙程度", "〔待填〕", "/ 5"), ("出差頻率", "〔待填〕", "")]
    def trow(i, nm, v, u):
        z = T["bg"] if i % 2 == 0 else T["panel"]
        return (f'<div style="display:flex;align-items:center;height:104px;background:{z};border-top:2px solid {T["line"]}">'
                f'<div class="n" style="width:78px;padding-left:22px;font-size:32px;color:{T["acc"]}">{i+1:02d}</div>'
                f'<div style="width:250px;font-size:40px;font-weight:800;white-space:nowrap">{nm}</div>'
                f'<div style="width:276px">{ph(v + u, 36)}</div>'
                f'<div style="flex:1;font-size:36px;color:{T["ink3"]};font-weight:500;white-space:nowrap">〔一句評語〕</div></div>')
    S[f"ch2_s{k}_2_fields"] = (css, f"""
{hd2(T,'2 / 3')}
<div class="body" style="padding-top:44px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">欄位一覽</span><span class="tag g">七欄固定，方便比較</span></div>
  <div style="font-size:78px;font-weight:900;line-height:1.2;margin-top:24px">七個欄位，一次看完</div>
  <div class="box" style="margin-top:28px;overflow:hidden;padding:0">
    <div style="display:flex;align-items:center;height:70px;background:{T['band'] if not T['dark'] else T['panel2']};color:{T['bandtx']};font-size:32px;font-weight:700">
      <div style="width:78px"></div><div style="width:250px">欄位</div><div style="width:276px">內容</div><div style="flex:1">一句評語</div></div>
    {''.join(trow(i,*r) for i,r in enumerate(rows))}
  </div>
</div>
{ft2(T)}""")

    # ---- 3 面試題卡 ----
    cell3 = lambda lab, v: (f'<div style="flex:1;padding:18px 24px;border-left:2px solid {T["line"]}"><div class="lab">{lab}</div>'
                            f'<div style="font-size:42px;font-weight:800;margin-top:6px;white-space:nowrap">{v}</div></div>')
    S[f"ch2_s{k}_3_interview"] = (css, f"""
{hd2(T,'1 / 3','面試題庫')}
<div class="body">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">面試題 #〔待填〕</span><span class="tag g">製程整合</span></div>
  <div style="display:flex;align-items:center;gap:26px;margin-top:60px">
    <div class="n" style="width:150px;height:150px;background:{T['acc']};color:{T['onacc']};font-size:112px;display:flex;align-items:center;justify-content:center;border-radius:6px;flex:none">Q</div>
    <div style="font-size:38px;font-weight:700;color:{T['ink3']};letter-spacing:.12em">題目</div></div>
  <div style="font-size:88px;font-weight:900;line-height:1.3;margin-top:44px">晶片面積放大 2 倍，<br><span style="color:{T['accdeep']}">良率會剛好剩一半</span>嗎？</div>
  <div class="box" style="margin-top:60px;padding:30px 34px;border-left:12px solid {T['acc']};font-size:46px;font-weight:700">先想 10 秒，再滑動看答案　→</div>
  <div style="margin-top:60px;display:flex;border-top:3px solid {T['ink']};border-bottom:2px solid {T['line']}">
    <div style="flex:1;padding:22px 24px 22px 0"><div class="lab">領域</div><div style="font-size:42px;font-weight:800;margin-top:6px">製程整合</div></div>
    {cell3('考察重點','良率模型')}{cell3('建議作答','3 分鐘')}</div>
</div>
{ft2(T,'科技透明圈（暫名）')}""")

    # ---- 4 知識圖解 ----
    svgS, nS, bS = wafer_svg(T, 36, 36, DEF); svgB, nB, bB = wafer_svg(T, 36, 72, DEF)
    yS, yB = (nS - bS) / nS, (nB - bB) / nB
    def panel(title, svg, n, b, y):
        return f"""<div class="box" style="flex:1;padding:16px 0 16px;display:flex;flex-direction:column;align-items:center;gap:10px">
  {svg}<div style="font-size:42px;font-weight:800;margin-top:4px">{title}</div>
  <div class="n" style="font-size:40px;color:{T['ink2']}">良品 {n-b} / 共 {n}</div>
  <div class="n" style="font-size:60px;color:{T['accdeep']};line-height:1.1">{y*100:.0f}%</div></div>"""
    leg = lambda c, bd, s: f'<span style="display:inline-flex;align-items:center;gap:10px;font-size:32px;color:{T["ink2"]};font-weight:600"><span style="width:28px;height:28px;border-radius:4px;background:{c};border:2px solid {bd};display:inline-block"></span>{s}</span>'
    dotleg = f'<span style="display:inline-flex;align-items:center;gap:10px;font-size:32px;color:{T["ink2"]};font-weight:600"><span style="width:22px;height:22px;border-radius:50%;background:{T["ink"] if not T["dark"] else "#0D1B2A"};border:3px solid {"#fff" if not T["dark"] else "#F2F5F8"};outline:2px solid {T["goodbd"]};display:inline-block"></span>缺陷</span>'
    S[f"ch2_s{k}_4_diagram"] = (css, f"""
{hd2(T,'3 / 3','知識圖解')}
<div class="body" style="padding-top:44px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">圖表 1・良率</span><span class="tag g">8 顆缺陷，隨機落點</span></div>
  <div style="font-size:62px;font-weight:900;line-height:1.2;margin-top:22px">同樣 8 顆缺陷，<span style="color:{T['accdeep']}">大晶片良率更低</span></div>
  <div style="display:flex;gap:20px;margin-top:34px">{panel('小晶片',svgS,nS,bS,yS)}{panel('面積 ×2',svgB,nB,bB,yB)}</div>
  <div style="display:flex;gap:28px;margin-top:26px;align-items:center">{leg(T['good'],T['goodbd'],'良品')}{leg(T['bad'],T['bad'],'壞品')}{dotleg}</div>
  <div class="box" style="margin-top:26px;padding:14px 30px;display:flex;align-items:center;gap:26px;border-left:12px solid {T['acc']}">
    <div class="n" style="font-size:54px;white-space:nowrap">Y = e<sup style="font-size:32px">−A·D</sup></div>
    <div style="font-size:36px;font-weight:700;color:{T['ink2']};line-height:1.3">面積 ×2，良率變平方</div></div>
</div>
{ft2(T,'示意模擬，缺陷位置為隨機')}""")
    return S, (nS, bS, yS, nB, bB, yB)


# ======================= 組合、檢查、輸出 =======================
SCHEMES = {"1A": T1A, "1B": T1B, "2A": T2A, "2B": T2B}
SLIDES = {}
STATS = None
for _k in ("1A", "1B"):
    SLIDES.update(build_ch1(SCHEMES[_k]))
for _k in ("2A", "2B"):
    _s, STATS = build_ch2(SCHEMES[_k]); SLIDES.update(_s)

CHECK_JS = """
() => {
  const W = 1080, H = 1350, M = 40;
  const out = {overlap: [], bounds: [], small: [], overflow: [], textBlock: [], clip: [], n: 0};
  const items = []; const byEl = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = walker.nextNode())) { if (!t.nodeValue.trim()) continue; const el = t.parentElement; if (!byEl.has(el)) byEl.set(el, []); byEl.get(el).push(t); }
  for (const [el, nodes] of byEl) {
    const rects = [];
    for (const n of nodes) { const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) if (q.width > 1 && q.height > 1) { const d = q.height * 0.1; rects.push({left:q.left, right:q.right, top:q.top + d, bottom:q.bottom - d}); } }
    if (!rects.length) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    items.push({el, rects, fs, meta: !!el.closest('[data-meta]'), txt: nodes.map(n => n.nodeValue.trim()).join('').slice(0, 14)});
  }
  out.n = items.length;
  const inter = (a, b, tol) => !(a.right <= b.left + tol || b.right <= a.left + tol || a.bottom <= b.top + tol || b.bottom <= a.top + tol);
  for (const it of items) {
    if (!it.meta && it.fs < 32 - 0.01) out.small.push(it.txt + ' ' + it.fs);
    if (it.meta && it.fs < 24) out.small.push('meta ' + it.txt + ' ' + it.fs);
    for (const r of it.rects) if (r.left < M - 1 || r.right > W - M + 1 || r.top < M - 1 || r.bottom > H - M + 1) out.bounds.push(it.txt);
    const box = it.el.closest('.box');
    if (box) { const b = box.getBoundingClientRect();
      for (const r of it.rects) if (r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1) out.overflow.push(it.txt); }
  }
  for (const el of document.querySelectorAll('.box,.chip,.tag,.ph,.btn,.brand')) if (el.scrollWidth > el.clientWidth + 2) out.clip.push(el.className + ' ' + (el.textContent||'').slice(0,10));
  for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
    const a = items[i], b = items[j]; let hit = false;
    for (const ra of a.rects) { for (const rb of b.rects) if (inter(ra, rb, 2)) { hit = true; break; } if (hit) break; }
    if (hit) out.overlap.push(a.txt + ' x ' + b.txt);
  }
  const blocks = [...document.querySelectorAll('[data-b]')];
  for (const blk of blocks) {
    const br = blk.getBoundingClientRect();
    for (const it of items) { if (blk.contains(it.el)) continue;
      for (const r of it.rects) if (inter(r, br, 2)) { out.textBlock.push(it.txt + ' x [圖]'); break; } }
    if (br.left < M - 1 || br.right > W - M + 1 || br.top < M - 1 || br.bottom > H - M + 1) out.bounds.push('[圖]');
  }
  // 圖與圖（外層 data-b 與其內層 svg 不算）
  for (let i = 0; i < blocks.length; i++) for (let j = i + 1; j < blocks.length; j++) {
    if (blocks[i].contains(blocks[j]) || blocks[j].contains(blocks[i])) continue;
    if (inter(blocks[i].getBoundingClientRect(), blocks[j].getBoundingClientRect(), 2)) out.overlap.push('[圖] x [圖]');
  }
  return out;
}
"""


def page_html(css, body):
    fonts = f'<link rel="stylesheet" href="{(FONT_DIR / "noto.css").as_uri()}">' if HAVE_NOTO else ""
    return f"<!doctype html><meta charset=utf-8>{fonts}<style>{css}</style><body>{body}</body>"


def launch(p):
    import glob
    exe = next(iter(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome"))), None)
    return p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()


def render():
    results = {}
    with sync_playwright() as p:
        br = launch(p)
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for name, (css, body) in SLIDES.items():
            f = TMP / "_slide.html"; f.write_text(page_html(css, body), encoding="utf-8")
            pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(350)
            res = pg.evaluate(CHECK_JS)
            pg.screenshot(path=str(HERE / f"{name}.png")); results[name] = res
        br.close()
    (TMP / "_slide.html").unlink(missing_ok=True)
    return results


def contrast_table():
    rows = []
    for T in (T1A, T1B):
        for pk, P in T["P"].items():
            band = P["main"] if T["mode"] == "solid" else P["tint"]; tx = "#FFFFFF" if T["mode"] == "solid" else T["ink"]
            rows.append((T["key"], pk, "標題字/帶底", tx, band, cr(tx, band)))
            rows.append((T["key"], pk, "白字/主色(膠囊)", "#FFFFFF", P["main"], cr("#FFFFFF", P["main"])))
            rows.append((T["key"], pk, "強調字/白卡", P["deep"], "#FFFFFF", cr(P["deep"], "#FFFFFF")))
        rows.append((T["key"], "-", "內文/底", T["ink"], T["bg"], cr(T["ink"], T["bg"])))
        rows.append((T["key"], "-", "輔助字/底", T["ink3"], T["bg"], cr(T["ink3"], T["bg"])))
        rows.append((T["key"], "-", "跌綠/白", T["fall"], "#FFFFFF", cr(T["fall"], "#FFFFFF")))
        rows.append((T["key"], "-", "漲紅/白", T["rise"], "#FFFFFF", cr(T["rise"], "#FFFFFF")))
    for T in (T2A, T2B):
        rows.append((T["key"], "-", "內文/底", T["ink"], T["bg"], cr(T["ink"], T["bg"])))
        rows.append((T["key"], "-", "輔助字/底", T["ink3"], T["bg"], cr(T["ink3"], T["bg"])))
        rows.append((T["key"], "-", "強調字/底", T["accdeep"], T["bg"], cr(T["accdeep"], T["bg"])))
        rows.append((T["key"], "-", "強調字/面板", T["accdeep"], T["panel"], cr(T["accdeep"], T["panel"])))
        rows.append((T["key"], "-", "強調字/淡強調底", T["accdeep"], T["acctint"], cr(T["accdeep"], T["acctint"])))
        rows.append((T["key"], "-", "頂欄字/頂欄", T["bandtx"], T["band"], cr(T["bandtx"], T["band"])))
        rows.append((T["key"], "-", "強調底上字", T["onacc"], T["acc"], cr(T["onacc"], T["acc"])))
    return rows



# ======================= 總覽圖 =======================
FILES = {k: sorted(n for n in SLIDES if n.startswith(p)) for k, p in
         (("1A", "ch1_s1_"), ("1B", "ch1_s2_"), ("2A", "ch2_s1_"), ("2B", "ch2_s2_"))}
BLURB = {
 "1A": ("暖奶油底＋四個內容柱各一個飽和主色，整塊色帶配白字，像友善的 App 卡片",
        "帳號牆：熱點橘、ETF 藍、輪動紫、知識青輪流出現，一眼知道這則是哪一柱；框架（圓角色帶、白卡、膠囊）每張一樣。白字壓橘／青只有 3.6～4.0:1，全部是 ≥ 32px 粗體大字（達 AA 大字 3:1）。"),
 "1B": ("薰衣草白底＋淡點，四柱各一個粉彩色帶＋飽和小膠囊，深靛字，像糖霜般柔和",
        "帳號牆：整體偏淡、偏柔，變化靠色帶與膠囊顏色；深靛字對粉彩底 12:1 以上，最好讀。比 1A 安靜，縮圖時的「抓眼度」略低於 1A。"),
 "2A": ("白底＋深藍灰頂欄＋藍綠細條，斑馬紋表格、欄位標頭，像顧問公司報告",
        "最像正式報告，適合要截圖轉傳的薪資表；明亮、列印也成立。強調色藍綠只做資訊層級（欄位編號、重點字、左側色條），不做裝飾。"),
 "2B": ("午夜藍灰底＋香檳金強調，像科技公司財報簡報的深色頁",
        "夜間閱讀舒服、有科技感；金色只標重點。與頻道一（明亮、多彩）反差最大；代價是列印與轉傳到淺色環境時不如 2A 俐落。"),
}
SW = {
 "1A": [("底", T1A["bg"]), ("墨藍字", T1A["ink"]), ("熱點橘", "#E8590C"), ("ETF 藍", "#2B6BF3"), ("輪動紫", "#7B4FE0"), ("知識青", "#0A8CA3"), ("漲（紅）", T1A["rise"]), ("跌（綠）", T1A["fall"])],
 "1B": [("底", T1B["bg"]), ("靛字", T1B["ink"]), ("熱點橘", "#F4511E"), ("橘色帶", "#FFE4D9"), ("ETF 藍", "#1F6FEB"), ("藍色帶", "#DCEBFF"), ("輪動紫", "#7C3AED"), ("紫色帶", "#EADFFF"), ("知識青", "#0891B2"), ("青色帶", "#D5F2F8"), ("漲（紅）", T1B["rise"]), ("跌（綠）", T1B["fall"])],
 "2A": [("頁底", T2A["bg"]), ("頂欄", T2A["band"]), ("強調藍綠", T2A["acc"]), ("強調深字", T2A["accdeep"]), ("淡強調底", T2A["acctint"]), ("面板", T2A["panel"]), ("線", T2A["line"]), ("輔助字", T2A["ink3"])],
 "2B": [("頁底", T2B["bg"]), ("頂欄", T2B["band"]), ("面板", T2B["panel"]), ("線", T2B["line"]), ("香檳金", T2B["acc"]), ("主字", T2B["ink"]), ("次字", T2B["ink2"]), ("輔助字", T2B["ink3"])],
}
def sw(hexv, name, size=(104, 54)):
    lt = lum(hexv) > .55
    return (f'<div style="display:flex;flex-direction:column;gap:3px;width:112px"><div style="width:{size[0]}px;height:{size[1]}px;border-radius:8px;background:{hexv};border:1px solid rgba(128,128,128,.45)"></div>'
            f'<div style="font-size:19px;font-weight:700">{name}</div><div style="font-size:18px;font-family:monospace;opacity:.8">{hexv}</div></div>')
def scheme_panel(k, tw, dark_bg=None):
    T = SCHEMES[k]; ch = "頻道一　哩股哩股" if k[0] == "1" else "頻道二　科技透明圈（暫名）"
    sub = "平易近人・明亮" if k[0] == "1" else "專業・企業風格"
    imgs = "".join(f'<img src="{n}.png" style="width:{tw}px;display:block;border-radius:10px;border:1px solid rgba(128,128,128,.4)">' for n in FILES[k])
    swh = "".join(sw(h, n) for n, h in SW[k])
    return (f'<div style="background:#fff;border-radius:18px;padding:26px 28px 30px;border:2px solid #D8DCE2;color:#14202E">'
            f'<div style="display:flex;align-items:baseline;gap:18px"><div style="font-size:42px;font-weight:900">{T["name"]}</div><div style="font-size:26px;font-weight:700;color:#5A6676">{ch}・{sub}</div></div>'
            f'<div style="font-size:26px;font-weight:600;margin:6px 0 14px;color:#2B3846">{BLURB[k][0]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:12px 14px;margin-bottom:18px">{swh}</div>'
            f'<div style="display:flex;gap:16px">{imgs}</div>'
            f'<div style="font-size:23px;line-height:1.5;margin-top:14px;color:#3A4756">{BLURB[k][1]}</div></div>')
def shoot(html, out, width, fp=None):
    f = TMP / "_ov.html"; f.write_text(html, encoding="utf-8")
    # 圖片要用相對路徑：把 html 寫在輸出資料夾
    f2 = HERE / "_ov.html"; f2.write_text(html, encoding="utf-8"); f.unlink(missing_ok=True)
    with sync_playwright() as p:
        br = launch(p); pg = br.new_page(viewport={"width": width, "height": 900})
        pg.goto(f2.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(500)
        pg.screenshot(path=str(HERE / out), full_page=True); br.close()
    f2.unlink(missing_ok=True)
def page(body, width):
    fonts = f'<link rel="stylesheet" href="{(FONT_DIR / "noto.css").as_uri()}">' if HAVE_NOTO else ""
    return f'<!doctype html><meta charset=utf-8>{fonts}<body style="margin:0;width:{width}px;background:#EDEFF2;font-family:{FONT};padding:36px 40px 40px">{body}</body>'

def overviews():
    names = {"1A": "overview_ch1_s1.png", "1B": "overview_ch1_s2.png", "2A": "overview_ch2_s1.png", "2B": "overview_ch2_s2.png"}
    for k, out in names.items():
        shoot(page(scheme_panel(k, 440), 2000), out, 2000)
    head = ('<div style="font-size:54px;font-weight:900;color:#14202E">兩頻道版型 v2：四個方案並排（2026-11-02）</div>'
            '<div style="font-size:26px;color:#44505F;margin:6px 0 24px">每個方案 4 張 1080×1350 樣張；內容全是示意假資料，薪資數字一律〔待填〕；沒有比比、沒有 AI 生圖。左欄頻道一（明亮友善），右欄頻道二（企業專業）。</div>')
    grid = ('<div style="display:grid;grid-template-columns:1fr 1fr;gap:34px">'
            + scheme_panel("1A", 300) + scheme_panel("2A", 300) + scheme_panel("1B", 300) + scheme_panel("2B", 300) + '</div>')
    shoot(page(head + grid, 2780), "overview.png", 2780)
    # 33% 縮圖（手機實際大小），16 張一張圖
    cells = "".join(f'<img src="{n}.png" style="width:356px;display:block">' for k in ("1A", "1B", "2A", "2B") for n in FILES[k])
    body = f'<div style="display:grid;grid-template-columns:repeat(4,356px);gap:8px;background:#888;padding:8px;width:1488px">{cells}</div>'
    f2 = HERE / "_t33.html"; f2.write_text(f'<!doctype html><meta charset=utf-8><body style="margin:0">{body}</body>', encoding="utf-8")
    with sync_playwright() as p:
        br = launch(p); pg = br.new_page(viewport={"width": 1504, "height": 800}); pg.goto(f2.as_uri()); pg.wait_for_timeout(500)
        pg.screenshot(path=str(HERE / "check_33pct.png"), full_page=True); br.close()
    f2.unlink(missing_ok=True)


if __name__ == "__main__":
    print("字型：", "Noto Sans TC（fontsource）" if HAVE_NOTO else "退回文泉驛正黑")
    res = render(); total = 0
    for name, r in res.items():
        issues = sum(len(r[k]) for k in ("overlap", "bounds", "small", "overflow", "textBlock", "clip")); total += issues
        print(f"{name:26s} 文字塊 {r['n']:3d}  重疊 {len(r['overlap'])}  出界 {len(r['bounds'])}  出框 {len(r['overflow'])}  壓圖 {len(r['textBlock'])}  字太小 {len(r['small'])}  截斷 {len(r['clip'])}")
        for k in ("overlap", "bounds", "small", "overflow", "textBlock", "clip"):
            for x in r[k]: print("    ", k, x)
    print(f"重疊檢查：程式 {len(res)} 張 {total} 筆")
    nS, bS, yS, nB, bB, yB = STATS
    print(f"良率圖：小 {nS} 顆壞 {bS}（良率 {yS:.2f}）；大 {nB} 顆壞 {bB}（良率 {yB:.2f}）")
    if "--contrast" in sys.argv:
        for r in contrast_table(): print(f"{r[0]} {r[1]:5s} {r[2]:14s} {r[3]} on {r[4]}  {r[5]:.2f}")
    overviews()
