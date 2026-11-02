"""兩個頻道版型 v2（美術，2026-11-02）：頻道一、頻道二各 6 套配色／風格，每套 4 張 1080×1350 樣張。
用法：python render_v2.py   輸出 PNG 到本資料夾，並印出「重疊檢查」與對比度表。
字型：Noto Sans TC（OFL，可商用；`npm pack @fontsource/noto-sans-tc` 取得，放在 TW_FONT_DIR，68MB 不進 repo），找不到退回文泉驛正黑。數字用 Inter／JetBrains Mono。
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




def lum(h):
    h = h.lstrip("#"); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def cr(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)


# ======================= 頻道一色票與風格（6 套）=======================
# 共通：4 個內容柱（熱點／ETF／產業輪動／知識）各一色，框架一致；紅漲綠跌只用在漲跌。
LAB = dict(hot="熱點解讀", etf="ETF 存股", rot="產業輪動", know="小知識")
def pil(**kw):
    out = {}
    for k, v in kw.items():
        main, tint, deep, mid = v[:4]; on = v[4] if len(v) > 4 else "#FFFFFF"
        out[k] = dict(main=main, tint=tint, deep=deep, mid=mid, on=on, label=LAB[k])
    return out

# --- 1 陽光糖果：暖奶油底＋飽和整塊色帶＋白字 ---
T1A = dict(key="1A", no=1, name="陽光糖果", bg="#FFF7E8", bgx="", ink="#1F2A44", ink2="#46526E", ink3="#5B6682",
           card="#FFFFFF", line="#EBDFC8", rise="#D62839", fall="#0B8F4D", darkband=True, deco=True, sk="none", skw=0,
           P=pil(hot=("#E8590C", "#FFE1CF", "#C2410C", "#F7B58F"), etf=("#2B6BF3", "#DCE8FF", "#1F55CC", "#A9C4FA"),
                 rot=("#7B4FE0", "#E6DCFB", "#6238C4", "#C9B8F4"), know=("#0A8CA3", "#D3F0F5", "#08758A", "#9ED5DF")),
           bandcss=lambda P: f"background:{P['main']};color:#fff;border-radius:0 0 64px 64px;padding:56px 64px 56px",
           bandtx=lambda P: "#fff", bandsub=lambda P: "rgba(255,255,255,.92)", chipbg=lambda P: "rgba(255,255,255,.24)", chiptx=lambda P: "#fff",
           bignum=lambda P: "#fff", brandcss="background:#fff;color:#1F2A44;border-radius:36px;padding:0 30px;font-size:36px;font-weight:900",
           cardcss="border-radius:28px;box-shadow:0 10px 28px rgba(31,42,68,.12)", hw=900, pre="",
           hl=lambda P: "background:rgba(255,255,255,.22);border-radius:14px;padding:0 14px;color:#fff",
           eqhi=lambda P: dict(bg=P["main"], col="#fff", sub="#fff", bd=""), x=lambda P: "")

# --- 2 粉彩糖霜：薰衣草白底＋淡點＋粉彩色帶＋飽和小膠囊 ---
T1B = dict(key="1B", no=2, name="粉彩糖霜", bg="#F6F4FF", bgx="background-image:radial-gradient(#EAE5FB 2.2px,transparent 2.6px);background-size:40px 40px;",
           ink="#241F47", ink2="#4A4670", ink3="#605C86", card="#FFFFFF", line="#E1DBF7", rise="#D62839", fall="#0B8F4D", darkband=False, deco=True, sk="none", skw=0,
           P=pil(hot=("#F4511E", "#FFE4D9", "#C2410C", "#FFC2A8"), etf=("#1F6FEB", "#DCEBFF", "#1856B8", "#AFCCF8"),
                 rot=("#7C3AED", "#EADFFF", "#5B21B6", "#CDB6F8"), know=("#0891B2", "#D5F2F8", "#0E7490", "#A3DAE8")),
           bandcss=lambda P: f"background:{P['tint']};color:#241F47;border-radius:0 0 64px 64px;padding:56px 64px 56px",
           bandtx=lambda P: "#241F47", bandsub=lambda P: "#4A4670", chipbg=lambda P: P["main"], chiptx=lambda P: "#fff",
           bignum=lambda P: P["deep"], brandcss="background:#fff;color:#241F47;border-radius:36px;padding:0 30px;font-size:36px;font-weight:900",
           cardcss="border-radius:28px;box-shadow:0 8px 24px rgba(60,40,160,.10);border:2px solid #E1DBF7", hw=900, pre="",
           hl=lambda P: f"background:#fff;border-radius:14px;padding:0 14px;color:{P['deep']}",
           eqhi=lambda P: dict(bg=P["tint"], col=P["deep"], sub="#4A4670", bd=f"border:4px solid {P['main']};"), x=lambda P: "")

# --- 3 薄荷清新：薄荷白底＋內縮圓角漸層面板＋深綠墨字，健康理財感 ---
T1C = dict(key="1C", no=3, name="薄荷清新", bg="#F0FAF6", bgx="", ink="#123B33", ink2="#3D5F57", ink3="#4F6F67", card="#FFFFFF", line="#CDE8DE",
           rise="#D62839", fall="#0B8F4D", darkband=False, deco=True, sk="none", skw=0,
           P=pil(hot=("#FF7A59", "#FFE7DF", "#BF4220", "#FFC2B0", "#123B33"), etf=("#14B8A6", "#D3F5EF", "#0B7F72", "#8FE0D4", "#123B33"),
                 rot=("#2B7FD1", "#DBEBFB", "#1F5FA8", "#A6CDF0"), know=("#F4B400", "#FFF1C2", "#7F5C00", "#FADE7A", "#123B33")),
           bandcss=lambda P: f"margin:28px 28px 0;border-radius:56px;background:linear-gradient(155deg,{P['tint']} 0%,#FFFFFF 100%);border:3px solid {P['main']};color:#123B33;padding:32px 36px 44px;overflow:hidden",
           bandtx=lambda P: "#123B33", bandsub=lambda P: "#3D5F57", chipbg=lambda P: "#FFFFFF", chiptx=lambda P: "#123B33",
           bignum=lambda P: P["deep"], brandcss="background:#123B33;color:#fff;border-radius:36px;padding:0 30px;font-size:36px;font-weight:900",
           cardcss="border-radius:36px;box-shadow:0 10px 26px rgba(20,120,100,.12);border:2px solid #D7EFE6", hw=800, pre="",
           hl=lambda P: f"background:{P['main']};border-radius:14px;padding:0 14px;color:{P['on']}",
           eqhi=lambda P: dict(bg=P["tint"], col=P["deep"], sub="#3D5F57", bd=f"border:4px solid {P['main']};"),
           x=lambda P: f".band::after{{content:'';position:absolute;right:-70px;bottom:-90px;width:300px;height:300px;border-radius:50%;background:{P['main']};opacity:.16}}"
                       f".chip{{border:2px solid {P['main']}}}.chip svg{{stroke:{P['deep']}}}")

# --- 4 日系雜誌：莫蘭迪低飽和、大留白、細線、無整塊色帶、細體大數字 ---
T1D = dict(key="1D", no=4, name="日系雜誌", bg="#F4F0E9", bgx="", ink="#34322E", ink2="#58544C", ink3="#6B665B", card="#FBF9F5", line="#D9D2C5",
           rise="#C0392B", fall="#2E7D5B", darkband=False, deco=False, sk="none", skw=0,
           P=pil(hot=("#B97A67", "#EADBD3", "#8A4E3E", "#D8B8AC"), etf=("#6C8F7A", "#DCE6DF", "#46664F", "#B4C9BA"),
                 rot=("#7C84B3", "#DFE1EE", "#565E91", "#BCC1DD"), know=("#CDAE6A", "#EFE5CC", "#7A6126", "#E2D0A3", "#2B2A27")),
           bandcss=lambda P: "background:transparent;color:#34322E;border-radius:0;padding:64px 64px 44px;border-bottom:1px solid #D9D2C5;margin:0 64px;padding-left:0;padding-right:0",
           bandtx=lambda P: "#34322E", bandsub=lambda P: "#6B665B", chipbg=lambda P: "transparent", chiptx=lambda P: "#58544C",
           bignum=lambda P: P["deep"], brandcss="background:none;color:#34322E;padding:0;font-size:34px;font-weight:600;letter-spacing:.3em",
           cardcss="border-radius:4px;box-shadow:none;border:1px solid #D9D2C5", hw=500, pre="",
           hl=lambda P: f"border-bottom:8px solid {P['main']};padding:0 2px;color:#34322E",
           eqhi=lambda P: dict(bg=P["main"], col=P["on"], sub=P["on"], bd=""),
           x=lambda P: (f"body::before{{content:'';position:absolute;left:64px;top:0;width:140px;height:16px;background:{P['main']}}}"
                        f".n.big,.n.fig{{font-weight:300;letter-spacing:-.03em}}.chip{{border-bottom:3px solid {P['main']};border-radius:0;padding:0 4px 0 0;height:50px}}"
                        f".chip svg{{stroke:{P['deep']}}}.pg{{color:#6B665B}}"
                        "[style*='font-weight:900'],[style*='font-weight:800']{font-weight:600!important}"
                        ".hd{height:64px}.body{padding:0 64px}.ft{margin:auto 64px 40px}.trk{border-radius:2px!important}.fil{border-radius:2px!important}"))

# --- 5 撞色積木：黃×藍等高彩度撞色、粗黑框＋硬陰影、幾何積木插畫（Duolingo／Notion 插畫感）---
T1E = dict(key="1E", no=5, name="撞色積木", bg="#E9F0FF", bgx="", ink="#0E1330", ink2="#2B3260", ink3="#4A5280", card="#FFFFFF", line="#0E1330",
           rise="#D62839", fall="#0B8F4D", darkband=True, deco=True, sk="#0E1330", skw=4,
           P=pil(hot=("#FFC933", "#FFF1BF", "#7A5B00", "#FFE08A", "#0E1330"), etf=("#3D5AFE", "#DCE2FF", "#2339C9", "#A9B6FF"),
                 rot=("#B28CFF", "#EADFFF", "#5B3BB3", "#D5C0FF", "#0E1330"), know=("#2EC4F1", "#D4F3FC", "#0A6F8F", "#9DE2F6", "#0E1330")),
           bandcss=lambda P: f"background:{P['main']};color:{P['on']};border-radius:0;border-bottom:5px solid #0E1330;padding:56px 64px 56px",
           bandtx=lambda P: P["on"], bandsub=lambda P: P["on"], chipbg=lambda P: "#0E1330", chiptx=lambda P: "#fff",
           bignum=lambda P: P["on"], brandcss="background:#fff;color:#0E1330;border-radius:14px;border:3px solid #0E1330;padding:0 28px;font-size:36px;font-weight:900",
           cardcss="border-radius:22px;border:3px solid #0E1330;box-shadow:7px 7px 0 #0E1330", hw=900, pre="",
           hl=lambda P: "background:#fff;border:3px solid #0E1330;border-radius:12px;padding:0 12px;color:#0E1330",
           eqhi=lambda P: dict(bg=P["main"], col=P["on"], sub=P["on"], bd=""),
           x=lambda P: (".chip{border-radius:14px}.btn{border:3px solid #0E1330;box-shadow:5px 5px 0 #0E1330;border-radius:16px}"
                        ".trk{border:3px solid #0E1330;border-radius:20px!important;background:#fff!important}.fil{border-right:3px solid #0E1330;border-radius:17px!important}"
                        ".rk{border:3px solid #0E1330}.yp{border:3px solid #0E1330;border-radius:14px!important}"
                        ".hd .pg{color:" + P["on"] + "}"))

# --- 6 玻璃漸層：淺色柔和漸層底＋模糊光球＋毛玻璃面板與卡片 ---
T1F = dict(key="1F", no=6, name="玻璃漸層", bg="#EEF0FF", bgx="background-image:linear-gradient(160deg,#E9ECFF 0%,#F8ECFF 48%,#FFEFE3 100%);", ink="#1C2144", ink2="#444B7A", ink3="#5A6190",
           card="#FFFFFF", line="rgba(255,255,255,.8)", rise="#D62839", fall="#0B8F4D", darkband=False, deco=True, sk="none", skw=0,
           P=pil(hot=("#F05A28", "#FFE5D8", "#B93A0E", "#FFB899"), etf=("#4A6CF7", "#DDE5FF", "#2F4BC8", "#AEBFFB"),
                 rot=("#8B5CF6", "#EADFFF", "#5B21B6", "#CFB8FA"), know=("#0E96AA", "#D2F1F6", "#0A6F80", "#9FDCE6")),
           bandcss=lambda P: "margin:28px 28px 0;border-radius:56px;background:rgba(255,255,255,.55);backdrop-filter:blur(26px);border:2px solid rgba(255,255,255,.95);box-shadow:0 18px 50px rgba(80,70,170,.16);color:#1C2144;padding:32px 36px 44px",
           bandtx=lambda P: "#1C2144", bandsub=lambda P: "#444B7A", chipbg=lambda P: "rgba(255,255,255,.8)", chiptx=lambda P: "#1C2144",
           bignum=lambda P: P["deep"], brandcss="background:linear-gradient(90deg,#4A6CF7,#8B5CF6);color:#fff;border-radius:36px;padding:0 30px;font-size:36px;font-weight:900",
           cardcss="border-radius:34px;background:rgba(255,255,255,.62);backdrop-filter:blur(18px);border:2px solid rgba(255,255,255,.95);box-shadow:0 12px 36px rgba(80,70,170,.14)", hw=800,
           pre=lambda P: (f'<div class="blob" style="left:-140px;top:-120px;width:520px;height:520px;background:{P["main"]};opacity:.34"></div>'
                          f'<div class="blob" style="right:-160px;top:420px;width:520px;height:520px;background:{P["mid"]};opacity:.7"></div>'
                          f'<div class="blob" style="left:60px;bottom:-200px;width:560px;height:560px;background:#FFC9A8;opacity:.55"></div>'),
           hl=lambda P: f"background:rgba(255,255,255,.8);border-radius:14px;padding:0 14px;color:{P['deep']}",
           eqhi=lambda P: dict(bg="rgba(255,255,255,.85)", col=P["deep"], sub="#444B7A", bd=f"border:3px solid {P['main']};"),
           x=lambda P: (".blob{position:absolute;border-radius:50%;filter:blur(70px);z-index:0}.band,.body,.ft{position:relative;z-index:1}"
                        ".ft{background:transparent!important}"
                        f".n.big{{background:linear-gradient(100deg,{P['main']},{P['deep']});-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent!important}}"
                        f".chip svg{{stroke:{P['deep']}}}"))

T1 = {"1A": T1A, "1B": T1B, "1C": T1C, "1D": T1D, "1E": T1E, "1F": T1F}


# ======================= 圖示（SVG 幾何，沒有比比、沒有 AI）=======================
def icon(kind, size=40, color="#fff", sw=2.4):
    p = {
        "hot": '<path d="M13 2 4 14h7l-1 8 9-12h-7z" fill="%s" stroke="none"/>' % color,
        "etf": '<circle cx="12" cy="12" r="9"/><path d="M12 3v9h9" fill="%s" stroke="none" opacity=".95"/><path d="M12 12 5.6 18.4"/>' % color,
        "rot": '<path d="M21 4v5h-5"/><path d="M3 20v-5h5"/><path d="M4.6 9a8.5 8.5 0 0 1 14.6-2.6L21 9"/><path d="M3 15l1.8 2.6A8.5 8.5 0 0 0 19.4 15"/>',
        "know": '<path d="M9 18h6M10 21.5h4"/><path d="M12 2.5a6.5 6.5 0 0 0-3.8 11.8c.6.5 1 1.2 1 2h5.6c0-.8.4-1.5 1-2A6.5 6.5 0 0 0 12 2.5z"/>',
    }[kind]
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" style="flex:none">{p}</svg>'


def _sk(T):
    return f'stroke="{T["sk"]}" stroke-width="{T["skw"]}" stroke-linejoin="round"' if T["skw"] else ""


def svg_fall_chart(P, T):
    """熱點封面插圖：下滑的長條＋向下箭頭（綠＝跌）。純幾何，沒有字。"""
    bars = [(34, 150), (96, 124), (158, 96), (220, 64)]
    cols = [P["mid"], P["mid"], P["mid"], P["main"]]
    r = "".join(f'<rect x="{x}" y="{200-h}" width="44" height="{h}" rx="12" fill="{c}" {_sk(T)}/>' for (x, h), c in zip(bars, cols))
    return (f'<svg data-b width="330" height="270" viewBox="-4 -4 338 278"><rect x="0" y="0" width="330" height="270" rx="36" fill="#fff" {_sk(T)}/>'
            f'<rect x="20" y="226" width="290" height="6" rx="3" fill="{T["line"] if not T["skw"] else T["sk"]}"/>{r}'
            f'<circle cx="274" cy="70" r="40" fill="{T["fall"]}" {_sk(T)}/><path d="M274 52v34M258 72l16 16 16-16" stroke="#fff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')


def svg_coins(P, T, w=150):
    def coin(y):
        return (f'<rect x="25" y="{y}" width="100" height="26" fill="{P["main"]}"/><ellipse cx="75" cy="{y+26}" rx="50" ry="16" fill="{P["main"]}" {_sk(T)}/>'
                f'<ellipse cx="75" cy="{y}" rx="50" ry="16" fill="{P["tint"]}" stroke="{T["sk"] if T["skw"] else P["main"]}" stroke-width="6"/><ellipse cx="75" cy="{y}" rx="26" ry="7" fill="none" stroke="{P["mid"]}" stroke-width="4"/>')
    return f'<svg data-b width="{w}" height="{w}" viewBox="0 0 150 150">{coin(96)}{coin(66)}{coin(36)}</svg>'


def svg_pie(P, T, w=170):
    return (f'<svg data-b width="{w}" height="{w}" viewBox="-4 -4 178 178"><circle cx="85" cy="85" r="78" fill="#fff" {_sk(T)}/>'
            f'<circle cx="85" cy="85" r="64" fill="{P["tint"]}"/><path d="M85 85V21A64 64 0 0 1 143 112Z" fill="{P["main"]}"/>'
            f'<path d="M85 85 143 112A64 64 0 0 1 40 134Z" fill="{P["mid"]}"/><circle cx="85" cy="85" r="24" fill="#fff" {_sk(T)}/></svg>')


def svg_cycle(P, T, w=170):
    return (f'<svg data-b width="{w}" height="{w}" viewBox="-4 -4 178 178"><circle cx="85" cy="85" r="78" fill="#fff" {_sk(T)}/>'
            f'<g fill="none" stroke="{P["main"]}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M40 82a46 46 0 0 1 80-24"/><path d="M130 88a46 46 0 0 1-80 24" stroke="{P["mid"]}"/></g>'
            f'<path d="M126 36l-4 28-26-10z" fill="{P["main"]}"/><path d="M44 134l4-28 26 10z" fill="{P["mid"]}"/></svg>')


# ======================= 頻道一 =======================
def css1(T, pk):
    P = T["P"][pk]
    return f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{T['ink']};background:{T['bg']};{T['bgx']}display:flex;flex-direction:column;overflow:hidden;position:relative}}
.n{{font-family:{NUM};font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
.band{{{T['bandcss'](P)};flex:none;position:relative}}
.hd{{display:flex;align-items:center;gap:16px;height:72px}}
.brand{{{T['brandcss']};height:64px;display:flex;align-items:center;white-space:nowrap}}
.chip{{display:flex;align-items:center;gap:10px;height:56px;padding:0 22px 0 16px;border-radius:28px;background:{T['chipbg'](P)};color:{T['chiptx'](P)};font-size:32px;font-weight:700;white-space:nowrap}}
.pg{{margin-left:auto;font-size:32px;font-weight:700;color:{T['bandsub'](P)}}}
.kick{{font-size:38px;font-weight:700;color:{T['bandsub'](P)};letter-spacing:.03em}}
.h1{{font-size:112px;font-weight:{T['hw']};line-height:1.18;color:{T['bandtx'](P)}}}
.h2{{font-weight:{T['hw']};line-height:1.2;color:{T['bandtx'](P)}}}
.acc{{color:{P['deep']}}}
.body{{padding:0 64px;flex:1;display:flex;flex-direction:column}}
.card{{background:{T['card']};{T['cardcss']}}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {T['line']};display:flex;align-items:flex-end;justify-content:space-between;background:{T['bg']}}}
.ft span{{font-size:28px;color:{T['ink3']};font-weight:500}}
.deco{{position:absolute;right:64px}}
.btn{{display:inline-flex;align-items:center;gap:12px;height:84px;padding:0 38px;border-radius:42px;background:{P['main']};color:{P['on']};font-size:40px;font-weight:800;white-space:nowrap}}
{T['x'](P)}
"""


def hd1(T, pk, pg=""):
    P = T["P"][pk]
    return (f'<div class="hd"><div class="brand">哩股哩股</div><div class="chip">{icon(pk, 34, T["chiptx"](P))}<span>{P["label"]}</span></div>'
            f'<div class="pg">{pg}</div></div>')


def ft1(T, pk):
    return f'<div class="ft"><span data-meta>{T["P"][pk]["label"]}</span><span data-meta>示意・假資料</span></div>'


def pre1(T, pk):
    p = T["pre"]; return p(T["P"][pk]) if callable(p) else p


def build_ch1(T):
    S = {}; n = T["no"]; mk = lambda pk: pre1(T, pk)
    deco = lambda svg, top: f'<div class="deco" data-b style="top:{top}px">{svg}</div>' if T["deco"] else ""
    # ---- 1 熱點封面 ----
    P = T["P"]["hot"]
    S[f"ch1_s{n}_1_hot_cover"] = (css1(T, "hot"), f"""{mk('hot')}
<div class="band" style="padding-bottom:60px">
  {hd1(T,'hot','1 / 5')}
  {deco(svg_fall_chart(P, T), 176 if n not in (3, 6) else 200)}
  <div class="kick" style="margin-top:44px">熱點解讀・11/02</div>
  <div class="h1" style="margin-top:14px">某晶片大廠<br>單日重挫</div>
  <div class="card" style="margin-top:30px;display:inline-flex;align-items:center;gap:8px;padding:10px 44px 10px 40px;box-shadow:none">
    <svg data-b width="124" height="108" viewBox="0 0 124 108" style="margin-right:14px"><path d="M8 10h108L62 100z" fill="{T['fall']}" stroke="{T['fall']}" stroke-width="10" stroke-linejoin="round"/></svg>
    <span class="n fig" style="font-size:270px;line-height:1.02;color:{T['fall']}">17%</span></div>
</div>
<div class="body" style="padding-top:60px;gap:40px">
  <div style="font-size:60px;font-weight:800;line-height:1.35">AI 浪潮裡，它到底<span class="acc">少了什麼</span>？</div>
  <div><span class="btn">滑動看 3 個原因　→</span></div>
</div>
{ft1(T,'hot')}""")

    # ---- 2 知識大數字卡 ----
    P = T["P"]["know"]; eqh = T["eqhi"](P)
    def eq(label, val, hi=False):
        if hi: bg, col, bd, sub = eqh["bg"], eqh["col"], eqh["bd"], eqh["sub"]
        else: bg, col, bd, sub = T["card"], T["ink"], "", T["ink2"]
        return (f'<div class="card box eqc" style="width:{268 if hi else 290}px;height:208px;background:{bg};{bd}display:flex;flex-direction:column;justify-content:center;align-items:center;gap:6px">'
                f'<div style="font-size:34px;font-weight:700;color:{sub}">{label}</div><div class="n" style="font-size:62px;color:{col}">{val}</div></div>')
    op = lambda s: f'<div class="n" style="width:60px;text-align:center;font-size:64px;color:{T["ink3"]}">{s}</div>'
    S[f"ch1_s{n}_2_know_number"] = (css1(T, "know"), f"""{mk('know')}
<div class="band" style="padding-bottom:56px">
  {hd1(T,'know','2 / 5')}
  <div class="kick" style="margin-top:40px">一個數字・小知識</div>
  <div class="n big" style="font-size:340px;line-height:1.04;margin:6px 0 0 -10px;color:{T['bignum'](P)}">4.2%</div>
</div>
<div class="body" style="padding-top:44px;gap:34px">
  <div style="display:flex;align-items:center;justify-content:space-between">
    <div style="font-size:66px;font-weight:900;line-height:1.25">殖利率是<span class="acc">怎麼算</span>的？</div>
    {('<div data-b>' + svg_coins(P, T, 140) + '</div>') if T['deco'] else ''}</div>
  <div style="display:flex;align-items:center">{eq('每股配息','2.1 元')}{op('÷')}{eq('股價','50 元')}{op('＝')}{eq('殖利率','4.2%',True)}</div>
  <div style="font-size:38px;font-weight:500;color:{T['ink2']};line-height:1.45">用過去的配息算出來的數字，<br>不是保證，會隨股價變動。</div>
</div>
{ft1(T,'know')}""")

    # ---- 3 ETF 配息比較表 ----
    P = T["P"]["etf"]
    def row(rank, code, tag, freq, yld, ex, hi=False):
        ypill = (f'<div class="n yp" style="background:{P["main"]};color:{P["on"]};border-radius:22px;padding:4px 20px;font-size:54px;white-space:nowrap">{yld}</div>' if hi
                 else f'<div class="n" style="font-size:54px;padding:4px 20px;white-space:nowrap">{yld}</div>')
        rb = P["main"] if hi else P["tint"]; rc = P["on"] if hi else P["deep"]
        return f"""<div class="card box" style="height:156px;display:flex;align-items:center;padding:0 24px 0 24px;gap:14px">
  <div class="n rk" style="width:62px;height:62px;border-radius:50%;background:{rb};color:{rc};font-size:34px;display:flex;align-items:center;justify-content:center;flex:none">{rank}</div>
  <div style="width:236px;display:flex;flex-direction:column;gap:0"><div class="n" style="font-size:48px;line-height:1.15">{code}</div><div style="font-size:32px;color:{T['ink3']};font-weight:500">{tag}</div></div>
  <div style="width:150px;font-size:40px;font-weight:700;color:{T['ink2']}">{freq}</div>
  <div style="width:210px;display:flex">{ypill}</div>
  <div class="n" style="flex:1;font-size:44px;text-align:right;color:{T['ink2']}">{ex}</div></div>"""
    colhd = f'<div style="display:flex;padding:0 24px;gap:14px;font-size:32px;font-weight:700;color:{T["ink3"]}"><div style="width:62px"></div><div style="width:236px">名稱</div><div style="width:150px">配息頻率</div><div style="width:210px">殖利率</div><div style="flex:1;text-align:right">下次除息</div></div>'
    S[f"ch1_s{n}_3_etf_table"] = (css1(T, "etf"), f"""{mk('etf')}
<div class="band" style="padding-bottom:52px">
  {hd1(T,'etf','2 / 6')}
  {deco(svg_pie(P, T, 176), 170 if n not in (3, 6) else 190)}
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
        wpct = max(6, abs(val) / maxv * 100); fill = P["main"] if hi else P["mid"]
        return f"""<div style="display:flex;align-items:center;gap:18px;height:106px">
  <div class="n" style="width:50px;font-size:46px;color:{P['deep'] if hi else T['ink3']}">{rank}</div>
  <div style="width:176px;font-size:48px;font-weight:800">{name}</div>
  <div class="trk" style="flex:1;height:34px;border-radius:17px;background:{P['tint']}"><div class="fil" style="width:{wpct:.0f}%;height:100%;border-radius:17px;background:{fill}"></div></div>
  <div class="n" style="width:170px;text-align:right;font-size:46px;color:{col};white-space:nowrap">{arr} {sign}{abs(val)}</div></div>"""
    S[f"ch1_s{n}_4_rotation"] = (css1(T, "rot"), f"""{mk('rot')}
<div class="band" style="padding-bottom:52px">
  {hd1(T,'rot','2 / 5')}
  {deco(svg_cycle(P, T, 176), 170 if n not in (3, 6) else 190)}
  <div class="kick" style="margin-top:36px">產業輪動・本週</div>
  <div class="h2" style="font-size:72px;margin-top:10px">錢這週停在<span style="{T['hl'](P)}">散熱</span><br>這一段</div>
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


# ======================= 頻道二色票與風格（6 套）=======================
# 共通：企業質感、嚴謹網格、清楚的資訊層級；數字用 Inter 或等寬字；沒有紙張／手寫感。
T2A = dict(key="2A", no=1, name="藍灰報告", dark=False, bg="#FFFFFF", band="#13263B", bandtx="#FFFFFF", rule="#00857C",
           ink="#13263B", ink2="#3C4B5C", ink3="#586879", line="#D3DAE2", panel="#F4F6F8", panel2="#E9EEF3",
           acc="#00857C", accdeep="#00675F", acctint="#DDF0EE", onacc="#FFFFFF", good="#E3E9EF", goodbd="#9AA9B8", bad="#00857C", zebra=True, x="")
T2B = dict(key="2B", no=2, name="午夜香檳", dark=True, bg="#0D1B2A", band="#08121D", bandtx="#F2F5F8", rule="#D9B36C",
           ink="#F2F5F8", ink2="#C2CDD9", ink3="#94A5B8", line="#2A415A", panel="#14263A", panel2="#1B3249",
           acc="#D9B36C", accdeep="#D9B36C", acctint="#2A2F36", onacc="#0D1B2A", good="#1E3550", goodbd="#4A6683", bad="#D9B36C", zebra=True, x="")
# 3 瑞士極簡：純白、黑字、一個紅，只有細線與嚴謹網格，沒有填色面板
T2C = dict(key="2C", no=3, name="瑞士極簡", dark=False, bg="#FFFFFF", band="#FFFFFF", bandtx="#111111", rule="#111111",
           ink="#111111", ink2="#333333", ink3="#595959", line="#CFCFCF", panel="#FFFFFF", panel2="#EFEFEF",
           acc="#D4231A", accdeep="#C0190F", acctint="#FFFFFF", onacc="#FFFFFF", good="#EDEDED", goodbd="#BDBDBD", bad="#D4231A", zebra=False,
           x=""".top{height:104px;border-bottom:4px solid #111}.top .t{color:#595959}.top .b{letter-spacing:.02em}
.tag{background:none!important;border:2px solid #111;color:#111!important;border-radius:0}.tag.g{border-color:#BDBDBD;color:#595959!important}
.ph{border:none;border-bottom:4px solid #D4231A;background:none;border-radius:0;color:#111;padding:0 4px}
.box{border:none;border-top:3px solid #111;border-radius:0;background:#fff}
.thead{background:#fff!important;color:#111!important;border-bottom:2px solid #111}
.cofield{border:none!important;border-left:12px solid #D4231A!important;background:none!important;border-radius:0!important}
.qb{background:#111!important;color:#fff!important;border-radius:0!important}
.callout{border-left:12px solid #D4231A!important;background:#F4F4F4!important;border-top:none!important;border-radius:0!important}
.cotext{color:#111!important}.mono{font-family:Inter}""")
# 4 電光藍深灰：近黑石墨＋電光藍，大圓角卡片與微光，像發表會簡報
T2D = dict(key="2D", no=4, name="電光深灰", dark=True, bg="#0A0B0E", band="#0A0B0E", bandtx="#F5F7FA", rule="#2F6BFF",
           ink="#F5F7FA", ink2="#C5CBD5", ink3="#8E97A6", line="#272B33", panel="#14161B", panel2="#1C1F26",
           acc="#2F6BFF", accdeep="#7FA6FF", acctint="#101A33", onacc="#FFFFFF", good="#1C1F26", goodbd="#3A404B", bad="#3D7BFF", zebra=False,
           x="""body{background-image:radial-gradient(900px 520px at 88% -6%,rgba(47,107,255,.30),transparent 62%),radial-gradient(700px 420px at -10% 108%,rgba(47,107,255,.14),transparent 60%)}
.top{background:transparent!important;height:112px;border-bottom:1px solid #272B33}
.tag{border-radius:999px;background:#101A33;color:#8FB3FF!important;border:1px solid #2F6BFF}.tag.g{background:#1C1F26;color:#C5CBD5!important;border:1px solid #333843}
.ph{border:1.5px solid #2F6BFF;background:#101A33;border-radius:999px;color:#9DBBFF;padding:2px 18px}
.box{border-radius:24px;border:1px solid #2A2E37;background:#14161B}
.thead{background:#1C1F26!important;color:#C5CBD5!important}
.cofield{border:1.5px solid #2F6BFF!important;border-radius:28px!important;background:linear-gradient(135deg,#12224A,#0D1426)!important}
.cotext{color:#9DBBFF!important}
.qb{border-radius:24px!important;background:linear-gradient(135deg,#2F6BFF,#5C8CFF)!important}
.callout{border-left:none!important;border-radius:24px!important;background:linear-gradient(135deg,#12224A,#14161B)!important;border:1px solid #2F6BFF!important}""")
# 5 墨綠研究：米白底＋墨綠＋雙線頁眉，像投銀研究報告
T2E = dict(key="2E", no=5, name="墨綠研究", dark=False, bg="#F7F5EE", band="#F7F5EE", bandtx="#0F3D2E", rule="#0F3D2E",
           ink="#15211B", ink2="#3B4A41", ink3="#56655C", line="#CBD2C8", panel="#EFEDE4", panel2="#E3E6DC",
           acc="#0F4C3A", accdeep="#0F4C3A", acctint="#E1EAE1", onacc="#FFFFFF", good="#E6E9E0", goodbd="#A5B0A3", bad="#0F4C3A", zebra=True,
           x=""".top{height:112px;border-top:16px solid #0F3D2E;border-bottom:1px solid #0F3D2E;box-shadow:0 5px 0 #F7F5EE,0 6px 0 #0F3D2E}.top .t{color:#56655C}
.tag{background:none!important;border-bottom:3px solid #0F4C3A;border-radius:0;padding:0 2px;color:#0F4C3A!important}.tag.g{border-bottom-color:#A5B0A3;color:#56655C!important}
.ph{border:1.5px solid #0F4C3A;background:#E1EAE1;border-radius:2px;color:#0F4C3A}
.box{border-radius:2px;border:1px solid #CBD2C8}
.thead{background:#0F3D2E!important;color:#fff!important}
.cofield{border:1.5px solid #0F4C3A!important;border-radius:2px!important;background:#E1EAE1!important}
.qb{border-radius:2px!important}
.callout{border-left:12px solid #0F4C3A!important;border-radius:2px!important;background:#EFEDE4!important}""")
# 6 彭博終端：純黑＋白字＋單一琥珀橘，等寬字、密集格線
T2F = dict(key="2F", no=6, name="終端琥珀", dark=True, bg="#000000", band="#000000", bandtx="#FFFFFF", rule="#FF8A00",
           ink="#FFFFFF", ink2="#E0E0E0", ink3="#A6A6A6", line="#3A3A3A", panel="#0D0D0D", panel2="#1A1A1A",
           acc="#FF8A00", accdeep="#FF9F2E", acctint="#1F1200", onacc="#000000", good="#1A1A1A", goodbd="#555555", bad="#FF8A00", zebra=True,
           x=""".top{height:104px;border-bottom:4px solid #FF8A00}.top .b{color:#FF9F2E}
.n,.mono{font-family:'JetBrains Mono','Noto Sans TC',monospace!important;letter-spacing:-.02em}
.tag{background:#FF8A00!important;color:#000!important;border-radius:0}.tag.g{background:#262626!important;color:#E0E0E0!important}
.ph{border:1px solid #FF8A00;background:#1F1200;border-radius:0;color:#FF9F2E;font-family:'JetBrains Mono','Noto Sans TC',monospace}
.box{border-radius:0;border:1px solid #4A4A4A;background:#0D0D0D}
.thead{background:#FF8A00!important;color:#000!important}
.cofield{border:2px solid #FF8A00!important;border-radius:0!important;background:#000!important}
.cotext{color:#FF9F2E!important}
.qb{background:#FF8A00!important;color:#000!important;border-radius:0!important}
.callout{border-left:12px solid #FF8A00!important;border-radius:0!important;background:#111!important}""")
T2 = {"2A": T2A, "2B": T2B, "2C": T2C, "2D": T2D, "2E": T2E, "2F": T2F}


def css2(T):
    return f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:{FONT};color:{T['ink']};background:{T['bg']};display:flex;flex-direction:column;overflow:hidden;position:relative}}
.n{{font-family:{NUM};font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.top{{background:{T['band']};height:128px;flex:none;padding:0 64px;display:flex;align-items:center;gap:20px;border-bottom:6px solid {T['rule']}}}
.top .b{{font-size:38px;font-weight:900;color:{T['bandtx']};letter-spacing:.04em}}
.top .t{{font-size:32px;font-weight:500;color:{'#C2CDD9' if T['dark'] else '#C9D4DF'}}}
.top .p{{margin-left:auto;font-size:32px;font-weight:700;color:{T['bandtx']}}}
.body{{padding:52px 64px 0;flex:1;display:flex;flex-direction:column;position:relative}}
.tag{{display:inline-flex;align-items:center;height:52px;padding:0 20px;font-size:32px;font-weight:700;border-radius:4px;background:{T['acctint']};color:{T['accdeep']};white-space:nowrap}}
.tag.g{{background:{T['panel2']};color:{T['ink2']}}}
.ph{{display:inline-block;border:2px dashed {T['acc']};background:{T['acctint']};color:{T['accdeep']};border-radius:4px;padding:2px 14px;font-weight:700;white-space:nowrap}}
.box{{background:{T['panel']};border:2px solid {T['line']};border-radius:6px}}
.cofield{{display:inline-flex;align-self:flex-start;border:3px dashed {T['acc']};background:{T['acctint']};border-radius:6px;padding:6px 34px 12px}}
.cotext{{color:{T['accdeep']}}}
.thead{{display:flex;align-items:center;height:70px;background:{T['band'] if not T['dark'] else T['panel2']};color:{T['bandtx']};font-size:32px;font-weight:700}}
.qb{{width:150px;height:150px;background:{T['acc']};color:{T['onacc']};font-size:112px;display:flex;align-items:center;justify-content:center;border-radius:6px;flex:none}}
.callout{{border-left:12px solid {T['acc']}}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {T['line']};display:flex;align-items:flex-end;justify-content:space-between}}
.ft span{{font-size:28px;color:{T['ink3']};font-weight:500}}
.lab{{font-size:32px;font-weight:700;color:{T['ink3']}}}
{T['x']}
"""


def hd2(T, pg, label="薪資行情簡報"):
    return f'<div class="top"><div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'


def ft2(T, left="資料來源：朋友提供，有誤請指正"):
    return f'<div class="ft"><span data-meta>{left}</span><span data-meta>示意・假資料</span></div>'


def wafer_svg(T, die_w, die_h, defects, size=380):
    R = size / 2; cx = cy = R; ndies = bad = 0; rects = []
    ny = int(size // die_h); nx = int(size // die_w)
    ox = (size - nx * die_w) / 2; oy = (size - ny * die_h) / 2
    dotf, dots_ = ("#0D1B2A", "#F2F5F8") if T["dark"] else (T["ink"], "#fff")
    if T["key"] in ("2D", "2F"): dotf, dots_ = "#000000", "#FFFFFF"
    for j in range(ny):
        for i in range(nx):
            x0 = ox + i * die_w; y0 = oy + j * die_h
            corners = [(x0, y0), (x0 + die_w, y0), (x0, y0 + die_h), (x0 + die_w, y0 + die_h)]
            if all((px - cx) ** 2 + (py - cy) ** 2 <= (R - 6) ** 2 for px, py in corners):
                hit = any(x0 <= dx < x0 + die_w and y0 <= dy < y0 + die_h for dx, dy in defects)
                ndies += 1; bad += hit
                fill = T["bad"] if hit else T["good"]; st = T["bad"] if hit else T["goodbd"]
                rects.append(f'<rect x="{x0+2:.1f}" y="{y0+2:.1f}" width="{die_w-4:.1f}" height="{die_h-4:.1f}" rx="3" fill="{fill}" stroke="{st}" stroke-width="1.5"/>')
    dots = "".join(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="7" fill="{dotf}" stroke="{dots_}" stroke-width="2.5"/>' for dx, dy in defects)
    svg = (f'<svg data-b width="{size}" height="{size}" viewBox="0 0 {size} {size}"><circle cx="{cx}" cy="{cy}" r="{R-2}" fill="{T["bg"] if not T["dark"] else T["panel2"]}" stroke="{T["goodbd"]}" stroke-width="3"/>'
           f'{"".join(rects)}{dots}</svg>')
    return svg, ndies, bad


def make_defects(seed, size=380):
    rnd = random.Random(seed); out = []; R = size / 2
    while len(out) < 8:
        x, y = rnd.uniform(30, size - 30), rnd.uniform(30, size - 30)
        if (x - R) ** 2 + (y - R) ** 2 <= (R - 30) ** 2: out.append((x, y))
    return out


_T_REF = dict(key="ref", bad="#000", good="#eee", goodbd="#999", ink="#000", dark=False, bg="#fff", panel2="#eee")
SEED = min(range(400), key=lambda sd: abs(wafer_svg(_T_REF, 36, 36, make_defects(sd))[2] - 8) + abs(wafer_svg(_T_REF, 36, 72, make_defects(sd))[2] - 7))
DEF = make_defects(SEED)


def build_ch2(T):
    S = {}; k = T["no"]; css = css2(T)
    ph = lambda s, fs=36: f'<span class="ph" style="font-size:{fs}px">{s}</span>'
    # ---- 1 薪資欄位卡封面 ----
    cell = lambda lab, v: (f'<div style="flex:1;padding:18px 24px;border-left:2px solid {T["line"]}"><div class="lab">{lab}</div>'
                           f'<div style="margin-top:8px">{ph(v,44)}</div></div>')
    S[f"ch2_s{k}_1_cover"] = (css, f"""
{hd2(T,'1 / 3')}
<div class="body">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">公司薪資行情</span><span class="tag g">碩畢・研發職類</span></div>
  <div class="cofield" style="margin-top:34px"><span class="cotext" style="font-size:150px;font-weight:900;line-height:1.2">〔公司名〕</span></div>
  <div style="font-size:150px;font-weight:900;line-height:1.2;margin-top:6px;color:{T['ink']}">薪資行情</div>
  <div style="margin-top:44px;display:flex;border-top:3px solid {T['ink']};border-bottom:2px solid {T['line']}">
    <div style="flex:1;padding:18px 24px 18px 0"><div class="lab">職類</div><div style="margin-top:8px">{ph('〔待填〕',44)}</div></div>
    {cell('學歷','〔待填〕')}{cell('年資','〔待填〕')}</div>
  <div class="box callout" style="margin-top:44px;display:flex;align-items:center;gap:30px;padding:26px 34px">
    <div style="font-size:46px;font-weight:800;line-height:1.2">碩畢<br>月薪</div>
    <div class="n" style="font-size:96px;line-height:1;color:{T['accdeep']}">〔待填〕K</div></div>
  <div style="margin-top:40px;font-size:38px;font-weight:600;color:{T['ink2']}">朋友提供，有誤請指正</div>
</div>
{ft2(T)}""")

    # ---- 2 七欄位卡 ----
    rows = [("總部地點", "〔待填〕", ""), ("碩畢月薪", "〔待填〕", "K"), ("年終・分紅", "〔待填〕", "個月"), ("升等路徑", "〔待填〕", ""),
            ("加班時數", "〔待填〕", "h"), ("繁忙程度", "〔待填〕", "/ 5"), ("出差頻率", "〔待填〕", "")]
    def trow(i, nm, v, u):
        z = T["panel"] if (T["zebra"] and i % 2 == 1) else T["bg"]
        return (f'<div style="display:flex;align-items:center;height:104px;background:{z};border-top:2px solid {T["line"]}">'
                f'<div class="n" style="width:78px;padding-left:22px;font-size:32px;color:{T["accdeep"] if not T["dark"] else T["acc"]}">{i+1:02d}</div>'
                f'<div style="width:250px;font-size:40px;font-weight:800;white-space:nowrap">{nm}</div>'
                f'<div style="width:276px">{ph(v + u, 36)}</div>'
                f'<div style="flex:1;font-size:36px;color:{T["ink3"]};font-weight:500;white-space:nowrap">〔一句評語〕</div></div>')
    S[f"ch2_s{k}_2_fields"] = (css, f"""
{hd2(T,'2 / 3')}
<div class="body" style="padding-top:44px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">欄位一覽</span><span class="tag g">七欄固定，方便比較</span></div>
  <div style="font-size:78px;font-weight:900;line-height:1.2;margin-top:24px">七個欄位，一次看完</div>
  <div class="box" style="margin-top:28px;overflow:hidden;padding:0">
    <div class="thead"><div style="width:78px"></div><div style="width:250px">欄位</div><div style="width:276px">內容</div><div style="flex:1">一句評語</div></div>
    {''.join(trow(i,*r) for i,r in enumerate(rows))}
  </div>
</div>
{ft2(T)}""")

    # ---- 3 面試題卡 ----
    cell3 = lambda lab, v: (f'<div style="flex:1;padding:22px 24px;border-left:2px solid {T["line"]}"><div class="lab">{lab}</div>'
                            f'<div style="font-size:42px;font-weight:800;margin-top:6px;white-space:nowrap">{v}</div></div>')
    S[f"ch2_s{k}_3_interview"] = (css, f"""
{hd2(T,'1 / 3','面試題庫')}
<div class="body">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">面試題 #〔待填〕</span><span class="tag g">製程整合</span></div>
  <div style="display:flex;align-items:center;gap:26px;margin-top:60px">
    <div class="n qb">Q</div>
    <div style="font-size:38px;font-weight:700;color:{T['ink3']};letter-spacing:.12em">題目</div></div>
  <div style="font-size:88px;font-weight:900;line-height:1.3;margin-top:44px">晶片面積放大 2 倍，<br><span style="color:{T['accdeep']}">良率會剛好剩一半</span>嗎？</div>
  <div class="box callout" style="margin-top:60px;padding:30px 34px;font-size:46px;font-weight:700">先想 10 秒，再滑動看答案　→</div>
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
    dotc = ("#000000", "#FFFFFF") if T["key"] in ("2D", "2F") else (("#0D1B2A", "#F2F5F8") if T["dark"] else (T["ink"], "#fff"))
    leg = lambda c, bd, s: f'<span style="display:inline-flex;align-items:center;gap:10px;font-size:32px;color:{T["ink2"]};font-weight:600"><span style="width:28px;height:28px;border-radius:4px;background:{c};border:2px solid {bd};display:inline-block"></span>{s}</span>'
    dotleg = f'<span style="display:inline-flex;align-items:center;gap:10px;font-size:32px;color:{T["ink2"]};font-weight:600"><span style="width:22px;height:22px;border-radius:50%;background:{dotc[0]};border:3px solid {dotc[1]};outline:2px solid {T["goodbd"]};display:inline-block"></span>缺陷</span>'
    S[f"ch2_s{k}_4_diagram"] = (css, f"""
{hd2(T,'3 / 3','知識圖解')}
<div class="body" style="padding-top:44px">
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">圖表 1・良率</span><span class="tag g">8 顆缺陷，隨機落點</span></div>
  <div style="font-size:62px;font-weight:900;line-height:1.2;margin-top:22px">同樣 8 顆缺陷，<span style="color:{T['accdeep']}">大晶片良率更低</span></div>
  <div style="display:flex;gap:20px;margin-top:34px">{panel('小晶片',svgS,nS,bS,yS)}{panel('面積 ×2',svgB,nB,bB,yB)}</div>
  <div style="display:flex;gap:28px;margin-top:26px;align-items:center">{leg(T['good'],T['goodbd'],'良品')}{leg(T['bad'],T['bad'],'壞品')}{dotleg}</div>
  <div class="box callout" style="margin-top:26px;padding:14px 30px;display:flex;align-items:center;gap:26px">
    <div class="n" style="font-size:54px;white-space:nowrap">Y = e<sup style="font-size:32px">−A·D</sup></div>
    <div style="font-size:36px;font-weight:700;color:{T['ink2']};line-height:1.3">面積 ×2，良率變平方</div></div>
</div>
{ft2(T,'示意模擬，缺陷位置為隨機')}""")
    return S, (nS, bS, yS, nB, bB, yB)
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




# ======================= 組合、對比度、總覽 =======================
SCHEMES = {}; SCHEMES.update(T1); SCHEMES.update(T2)
SLIDES = {}; STATS = None
for _k in T1: SLIDES.update(build_ch1(T1[_k]))
for _k in T2:
    _s, STATS = build_ch2(T2[_k]); SLIDES.update(_s)
FILES = {}
for _k, _T in SCHEMES.items():
    FILES[_k] = sorted(n for n in SLIDES if n.startswith(f"ch{_k[0]}_s{_T['no']}_"))


def contrast_table():
    rows = []
    for k, T in T1.items():
        rows.append((k, "-", "內文/底", T["ink"], T["bg"], cr(T["ink"], T["bg"])))
        rows.append((k, "-", "輔助字/底", T["ink3"], T["bg"], cr(T["ink3"], T["bg"])))
        rows.append((k, "-", "跌綠/白卡", T["fall"], "#FFFFFF", cr(T["fall"], "#FFFFFF")))
        rows.append((k, "-", "漲紅/白卡", T["rise"], "#FFFFFF", cr(T["rise"], "#FFFFFF")))
        for pk, P in T["P"].items():
            rows.append((k, pk, "主色上的字(膠囊/按鈕)", P["on"], P["main"], cr(P["on"], P["main"])))
            rows.append((k, pk, "強調字/白", P["deep"], "#FFFFFF", cr(P["deep"], "#FFFFFF")))
    for k, T in T2.items():
        for lab, a, b in (("內文/底", T["ink"], T["bg"]), ("輔助字/底", T["ink3"], T["bg"]), ("強調字/底", T["accdeep"], T["bg"]),
                          ("強調字/面板", T["accdeep"], T["panel"]), ("強調字/淡強調底", T["accdeep"], T["acctint"]), ("強調底上字", T["onacc"], T["acc"])):
            rows.append((k, "-", lab, a, b, cr(a, b)))
    return rows


SW = {
 "1A": [("底", "#FFF7E8"), ("墨藍字", "#1F2A44"), ("熱點橘", "#E8590C"), ("ETF 藍", "#2B6BF3"), ("輪動紫", "#7B4FE0"), ("知識青", "#0A8CA3")],
 "1B": [("底", "#F6F4FF"), ("靛字", "#241F47"), ("熱點橘", "#F4511E"), ("ETF 藍", "#1F6FEB"), ("輪動紫", "#7C3AED"), ("知識青", "#0891B2"), ("橘帶", "#FFE4D9"), ("藍帶", "#DCEBFF")],
 "1C": [("底", "#F0FAF6"), ("深綠字", "#123B33"), ("熱點珊瑚", "#FF7A59"), ("ETF 薄荷", "#14B8A6"), ("輪動藍", "#2B7FD1"), ("知識黃", "#F4B400")],
 "1D": [("底", "#F4F0E9"), ("墨字", "#34322E"), ("熱點陶土", "#B97A67"), ("ETF 鼠尾草", "#6C8F7A"), ("輪動灰藍", "#7C84B3"), ("知識芥末", "#CDAE6A")],
 "1E": [("底", "#E9F0FF"), ("黑藍字", "#0E1330"), ("熱點黃", "#FFC933"), ("ETF 藍", "#3D5AFE"), ("輪動淡紫", "#B28CFF"), ("知識天藍", "#2EC4F1")],
 "1F": [("底", "#EEF0FF"), ("靛字", "#1C2144"), ("熱點橘", "#F05A28"), ("ETF 藍", "#4A6CF7"), ("輪動紫", "#8B5CF6"), ("知識青", "#0E96AA")],
 "2A": [("頁底", "#FFFFFF"), ("頂欄", "#13263B"), ("強調藍綠", "#00857C"), ("淡強調底", "#DDF0EE"), ("面板", "#F4F6F8"), ("線", "#D3DAE2")],
 "2B": [("頁底", "#0D1B2A"), ("頂欄", "#08121D"), ("面板", "#14263A"), ("香檳金", "#D9B36C"), ("主字", "#F2F5F8"), ("輔助字", "#94A5B8")],
 "2C": [("頁底", "#FFFFFF"), ("黑", "#111111"), ("瑞士紅", "#D4231A"), ("輔助灰", "#595959"), ("細線", "#CFCFCF"), ("淡灰面", "#EFEFEF")],
 "2D": [("頁底", "#0A0B0E"), ("卡片", "#14161B"), ("電光藍", "#2F6BFF"), ("藍字", "#7FA6FF"), ("主字", "#F5F7FA"), ("輔助字", "#8E97A6")],
 "2E": [("頁底", "#F7F5EE"), ("墨綠", "#0F4C3A"), ("深綠頁眉", "#0F3D2E"), ("淡綠底", "#E1EAE1"), ("面板", "#EFEDE4"), ("線", "#CBD2C8")],
 "2F": [("頁底", "#000000"), ("白字", "#FFFFFF"), ("琥珀橘", "#FF8A00"), ("琥珀字", "#FF9F2E"), ("面板", "#0D0D0D"), ("格線", "#3A3A3A")],
}
BLURB = {
 "1A": ("暖奶油底＋四柱各一飽和主色，整塊色帶配白字，像友善的 App 卡片", "白字壓橘／青只有 3.6～4.0:1，皆 ≥ 32px 粗體大字（達 AA 大字 3:1）。"),
 "1B": ("薰衣草白底＋淡點＋粉彩色帶＋飽和小膠囊，深靛字，糖霜般柔和", "深靛字對粉彩帶 12:1 以上，最好讀；比 1 安靜。"),
 "1C": ("薄荷白底＋內縮圓角漸層面板＋深綠墨字，健康理財感", "珊瑚／薄荷／黃柱用深綠字壓色（≥ 5.9:1）；品牌用薄荷綠，漲跌綠為較深的正綠並一律配 ▲▼，避免混淆。"),
 "1D": ("莫蘭迪低飽和、大留白、細線、無整塊色帶，大數字用細體，像日系雜誌", "最安靜、最「質感」；代價是縮圖時抓眼度最低，要靠頂端小色塊辨識內容柱。"),
 "1E": ("黃×藍高彩度撞色、粗黑框＋硬陰影、幾何積木插畫，像 Duolingo／Notion", "最有活力、最像獨立品牌；年輕感強，要注意別壓過「專業」的底線。"),
 "1F": ("淺色柔和漸層底＋模糊光球＋毛玻璃面板與卡片，數字用漸層字", "2026 消費／社群趨勢；字一律深靛字壓在白玻璃上（≥ 10:1），不直接壓在漸層上。"),
 "2A": ("白底＋深藍灰頂欄＋藍綠細條，斑馬紋表格，像顧問公司報告", "明亮、列印成立；強調色只做資訊層級。"),
 "2B": ("午夜藍灰底＋香檳金強調，像科技公司財報簡報深色頁", "夜讀舒服、有科技感；金色只標重點。"),
 "2C": ("純白極簡瑞士風：黑字＋一個瑞士紅、粗細黑線、無填色面板", "最乾淨、資訊層級靠字級與線；紅色是品牌色，頻道二樣張沒有漲跌，但若日後放漲跌要改用別的強調。"),
 "2D": ("近黑石墨＋電光藍微光、大圓角卡片、膠囊標籤，像發表會簡報", "最「科技公司」；藍光暈在不同螢幕可能偏暗，列印不適合。"),
 "2E": ("米白底＋墨綠、雙線頁眉、綠色表頭，像投銀研究報告", "最「金融報告」；米白略有紙感，但無手寫與紋理，仍屬企業風。"),
 "2F": ("純黑底＋白字＋單一琥珀橘、等寬字、方角密集格線，像彭博終端", "對比最高、最有「專業終端」感；偏密、偏硬，閱讀量大時較累。"),
}
def sw(hexv, name, w=104):
    return (f'<div style="display:flex;flex-direction:column;gap:3px;width:{w+8}px"><div style="width:{w}px;height:50px;border-radius:8px;background:{hexv};border:1px solid rgba(128,128,128,.45)"></div>'
            f'<div style="font-size:19px;font-weight:700">{name}</div><div style="font-size:18px;font-family:monospace;opacity:.8">{hexv}</div></div>')
def chname(k): return "頻道一　哩股哩股" if k[0] == "1" else "頻道二　科技透明圈（暫名）"
def scheme_panel(k, tw, only=None, blurb=True):
    T = SCHEMES[k]; sub = "平易近人・明亮" if k[0] == "1" else "專業・企業風格"
    names = FILES[k] if only is None else [FILES[k][i] for i in only]
    imgs = "".join(f'<img src="{n}.png" style="width:{tw}px;display:block;border-radius:10px;border:1px solid rgba(128,128,128,.4)">' for n in names)
    swh = "".join(sw(h, n) for n, h in SW[k])
    note = f'<div style="font-size:23px;line-height:1.5;margin-top:14px;color:#3A4756">{BLURB[k][1]}</div>' if blurb else ""
    return (f'<div style="background:#fff;border-radius:18px;padding:24px 26px 28px;border:2px solid #D8DCE2;color:#14202E">'
            f'<div style="display:flex;align-items:baseline;gap:16px"><div style="font-size:44px;font-weight:900"><span style="color:#fff;background:#14202E;border-radius:10px;padding:0 14px;margin-right:12px">{T["no"]}</span>{T["name"]}</div><div style="font-size:24px;font-weight:700;color:#5A6676">{chname(k)}・{sub}</div></div>'
            f'<div style="font-size:25px;font-weight:600;margin:8px 0 14px;color:#2B3846">{BLURB[k][0]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:10px 12px;margin-bottom:16px">{swh}</div>'
            f'<div style="display:flex;gap:16px">{imgs}</div>{note}</div>')


def shoot(html, out, width):
    f2 = HERE / "_ov.html"; f2.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        br = launch(p); pg = br.new_page(viewport={"width": width, "height": 900})
        pg.goto(f2.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(500)
        pg.screenshot(path=str(HERE / out), full_page=True); br.close()
    f2.unlink(missing_ok=True)
def page(body, width):
    fonts = f'<link rel="stylesheet" href="{(FONT_DIR / "noto.css").as_uri()}">' if HAVE_NOTO else ""
    return f'<!doctype html><meta charset=utf-8>{fonts}<body style="margin:0;width:{width}px;background:#EDEFF2;font-family:{FONT};padding:36px 40px 40px">{body}</body>'


def overviews():
    for k in SCHEMES:
        shoot(page(scheme_panel(k, 440), 2000), f"overview_ch{k[0]}_s{SCHEMES[k]['no']}.png", 2000)
    # 四方案並排（上一版）
    head = ('<div style="font-size:54px;font-weight:900;color:#14202E">兩頻道版型 v2：前四個方案並排（2026-11-02）</div>'
            '<div style="font-size:26px;color:#44505F;margin:6px 0 24px">每個方案 4 張 1080×1350 樣張；內容全是示意假資料，薪資數字一律〔待填〕；沒有比比、沒有 AI 生圖。左欄頻道一，右欄頻道二。</div>')
    grid = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:34px">' + "".join(scheme_panel(k, 300) for k in ("1A", "2A", "1B", "2B")) + '</div>'
    shoot(page(head + grid, 2780), "overview.png", 2780)
    # 頻道一／頻道二 六套總覽：每套 2 張代表樣張
    for ch, only, title in (("1", (0, 3), "頻道一　哩股哩股：6 套配色／風格（每套 2 張代表樣張：熱點封面、產業輪動）"),
                            ("2", (0, 1), "頻道二　科技透明圈（暫名）：6 套配色／風格（每套 2 張代表樣張：薪資欄位卡封面、七欄位卡）")):
        keys = [k for k in SCHEMES if k[0] == ch]
        head = (f'<div style="font-size:50px;font-weight:900;color:#14202E">{title}</div>'
                '<div style="font-size:25px;color:#44505F;margin:6px 0 22px">每套另有 4 張完整樣張與單套總覽（overview_chX_sN.png）。示意假資料、薪資〔待填〕、無比比、無 AI 生圖。</div>')
        grid = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:30px">' + "".join(scheme_panel(k, 330, only, blurb=False) for k in keys) + '</div>'
        shoot(page(head + grid, 2260), f"overview_ch{ch}_all.png", 2260)
    # 33% 縮圖：每頻道一張，每列一套、每列 4 張
    for ch in ("1", "2"):
        rows = ""
        for k in [k for k in SCHEMES if k[0] == ch]:
            rows += "".join(f'<img src="{n}.png" style="width:356px;display:block">' for n in FILES[k])
        f2 = HERE / "_t33.html"
        f2.write_text(f'<!doctype html><meta charset=utf-8><body style="margin:0"><div style="display:grid;grid-template-columns:repeat(4,356px);gap:8px;background:#888;padding:8px;width:1488px">{rows}</div></body>', encoding="utf-8")
        with sync_playwright() as p:
            br = launch(p); pg = br.new_page(viewport={"width": 1504, "height": 800}); pg.goto(f2.as_uri()); pg.wait_for_timeout(500)
            pg.screenshot(path=str(HERE / f"check_33pct_ch{ch}.png"), full_page=True); br.close()
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
        for r in contrast_table(): print(f"{r[0]} {r[1]:5s} {r[2]:18s} {r[3]} on {r[4]}  {r[5]:.2f}")
    if "--no-overview" not in sys.argv: overviews()
