"""期中選舉範例貼文 A 柔和版／B 專業版（1080x1350 x5）。內容文字沿用已定稿，只改視覺。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = Path(__file__).resolve().parent
SP = HERE.parent
FONTS = SP / "fontdl/x/package"
PHOTO = (SP / "eccles.jpg").as_uri()
OUT = SP / "stock_samples_1104"
W, H = 1080, 1350
CREDIT = "圖：Federal Reserve／公有領域（Wikimedia Commons）"
CHECK = (HERE / "check.js").read_text()

FONT_LINKS = "".join(f'<link rel="stylesheet" href="{(FONTS / f"{w}.css").as_uri()}">' for w in (500, 700, 900))
BASE = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;position:relative;overflow:hidden;font-family:'Noto Sans TC','WenQuanYi Zen Hei',sans-serif}
.num{font-family:Inter,'Noto Sans TC',sans-serif;font-variant-numeric:tabular-nums}
.abs{position:absolute}
"""

# ---------- 共用資料（文字不改；僅第 3 張分類改「歷史對照」）----------
HIST = [("2002", 2.3), ("2006", 9.2), ("2010", 10.3), ("2014", 6.1), ("2018", 0.2), ("2022", 14.4)]
NOW = [("多家媒體預測民主黨拿下眾議院", "並預測參議院也翻盤，各家席次略有不同"),
       ("美股期貨早盤下跌", "標普 500 約 −0.8%～−1%，那斯達克約 −1.8%"),
       ("市場擔心的是 AI 與資料中心", "政治版圖改變，監管可能趨嚴；美債殖利率同步回落")]
WORST = [("選後 1 個月最差", "2018 年；6 次中 5 次收紅", "−1.5%", "dn"),
         ("3 個月途中最深回檔", "2002 年；2018 年也有 −5.3%", "−5.8%", "dn"),
         ("美股標普 500 選後 1 個月", "2010～2022 四次，最差 −2.2%（2018）", "3 / 4", "ink")]
TRI = '<svg width="30" height="26" viewBox="0 0 30 26" style="vertical-align:-2px"><path d="M15 1 29 25H1z" fill="currentColor"/></svg>'
BOLT = '<svg width="26" height="26" viewBox="0 0 24 24" style="vertical-align:-4px"><path d="M13 2 4 14h6l-1 8 9-12h-6z" fill="currentColor"/></svg>'
BULB = '<svg width="26" height="26" viewBox="0 0 24 24" style="vertical-align:-4px" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.7.6 1 1.3 1 2.1h5c0-.8.3-1.5 1-2.1A6 6 0 0 0 12 3z"/></svg>'
CLOCK = '<svg width="26" height="26" viewBox="0 0 24 24" style="vertical-align:-4px" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'
ICON = {"熱點解讀": BOLT, "歷史對照": CLOCK, "小知識": BULB}

# ===================== A 柔和版 =====================
A = dict(bg="#FBF5EA", card="#FFFFFF", ink="#2D3550", ink2="#5C657D", line="#E9E1D2",
         ter="#B9653F", ter_t="#F5E2D3", blue="#6C74A8", blue_t="#E6E8F3", sage="#4F8E84", sage_t="#DCEBE6",
         up="#C84F4A", dn="#3E8F6B")
PAGE_ACC = {1: ("ter", "ter_t"), 2: ("ter", "ter_t"), 3: ("blue", "blue_t"), 4: ("sage", "sage_t"), 5: ("ter", "ter_t")}


def a_css(p):
    c = A; acc, tint = PAGE_ACC[p]
    return BASE + f"""
body{{background:{c['bg']};color:{c['ink']}}}
.top{{left:64px;right:64px;top:56px;display:flex;align-items:center;gap:14px;height:64px}}
.brand{{background:#fff;border:2px solid {c['line']};border-radius:32px;padding:0 28px;height:60px;display:flex;align-items:center;font-weight:900;font-size:34px;color:{c['ink']}}}
.chip{{background:{c[tint]};color:{c[acc]};border-radius:32px;padding:0 24px;height:56px;display:flex;align-items:center;gap:8px;font-weight:700;font-size:30px}}
.pg{{margin-left:auto;font-size:30px;font-weight:700;color:{c['ink2']}}}
.kick{{font-size:34px;font-weight:700;color:{c[acc]}}}
.ttl{{font-weight:900;color:{c['ink']};line-height:1.2}}
.panel{{left:0;right:0;top:0;background:{c[tint]};border-radius:0 0 56px 56px}}
.box{{background:#fff;border-radius:28px;box-shadow:0 6px 22px rgba(120,100,70,.10);border:2px solid #F1EADC}}
.foot{{left:64px;right:64px;bottom:44px;border-top:2px solid {c['line']};padding-top:16px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;color:{c['ink2']}}}
.note{{font-size:34px;font-weight:500;color:{c['ink2']};line-height:1.5}}
.up{{color:{c['up']}}} .dn{{color:{c['dn']}}} .hl{{color:{c[acc]}}}
.credit{{font-size:20px;font-weight:500;color:{c['ink2']};text-align:right}}
"""


def a_top(p, chip):
    return (f'<div class="abs top" data-meta><div class="brand">哩股哩股</div><div class="chip">{ICON[chip]}{chip}</div>'
            f'<div class="pg num">{p} / 5</div></div>')


def a_foot(l, r):
    return f'<div class="abs foot" data-meta><span>{l}</span><span>{r}</span></div>'


def a_pages():
    c = A; P = {}
    # 1 封面：照片區（含圓角）＋標題＋6/6
    P[1] = a_css(1) + """
.photo{left:64px;top:150px;width:952px;height:430px;border-radius:32px;overflow:hidden;box-shadow:0 8px 26px rgba(120,100,70,.16)}
.photo img{width:100%;height:100%;object-fit:cover;object-position:50% 62%;filter:saturate(.62) contrast(.96) brightness(1.04) sepia(.12)}
""", (a_top(1, "熱點解讀")
      + '<div class="abs photo" data-b data-b1><img src="%s"></div>' % PHOTO
      + f'<div class="abs credit" data-credit style="left:64px;width:952px;top:590px;height:26px">{CREDIT}</div>'
      + '<div class="abs kick" style="left:64px;top:646px">熱點解讀・11/04</div>'
      + '<div class="abs ttl" style="left:64px;top:694px;font-size:84px;width:952px;white-space:nowrap">期中選舉後台股怎麼走？</div>'
      + '<div class="abs box" style="left:64px;top:822px;width:760px;height:200px;display:flex;align-items:center;gap:36px;padding:0 44px">'
        f'<div class="num" style="font-size:150px;font-weight:800;line-height:1;letter-spacing:-4px;color:{c["ink"]}">6<span style="color:{c["ter"]}">/</span>6</div>'
        f'<div style="font-size:38px;font-weight:900;line-height:1.35;color:{c["ink2"]}">選後 3 個月<br>收紅次數</div></div>'
      + f'<div class="abs" style="left:64px;top:1062px;font-size:46px;font-weight:900;white-space:nowrap">但途中最深回檔 <span class="num hl">5.8%</span>，這次呢？</div>'
      + f'<div class="abs chip" style="left:64px;top:1148px;height:68px;font-size:34px;padding:0 34px;background:{c["ter"]};color:#fff">滑動看歷史數字　→</div>'
      + a_foot("熱點解讀", "加權指數・6 次樣本"))
    # 2
    rows = "".join(
        f'<div class="abs box" style="left:64px;top:{y}px;width:952px;height:168px">'
        f'<div class="abs num" style="left:30px;top:48px;width:64px;height:64px;border-radius:32px;background:{c["ter_t"]};color:{c["ter"]};font-weight:900;font-size:34px;text-align:center;line-height:64px">{i+1}</div>'
        f'<div class="abs" style="left:126px;top:26px;font-size:40px;font-weight:900;white-space:nowrap">{t}</div>'
        f'<div class="abs" style="left:126px;top:90px;font-size:32px;font-weight:500;color:{c["ink2"]};white-space:nowrap">{s}</div></div>'
        for i, (t, s), y in [(i, x, 498 + i * 188) for i, x in enumerate(NOW)])
    P[2] = a_css(2) + ".panel{height:460px}", (
        '<div class="abs panel" style="height:460px"></div>' + a_top(2, "熱點解讀")
        + '<div class="abs kick" style="left:64px;top:168px">熱點解讀・11/04 早盤快照</div>'
        + '<div class="abs ttl" style="left:64px;top:216px;font-size:84px;width:952px">開票中，市場先<br>怎麼反應？</div>'
        + rows
        + f'<div class="abs note" style="left:64px;top:1066px;width:952px">11/3 台股已先收 <span class="num">43,307.54</span> 點（−1,612 點）。開票仍在進行，數字會變動。</div>'
        + a_foot("熱點解讀", "來源：CNBC、CBS、NBC 即時報導"))
    # 3
    mx = 14.4; bars = ""
    for i, (y, v) in enumerate(HIST):
        w = max(v / mx, .07) * 470; top = 574 + i * 96; last = y == "2022"
        bars += (f'<div class="abs num" style="left:92px;top:{top}px;width:110px;font-size:36px;font-weight:700;color:{c["ink2"] if not last else c["blue"]}">{y}</div>'
                 f'<div class="abs" style="left:216px;top:{top+12}px;width:470px;height:26px;border-radius:13px;background:{c["blue_t"]}"></div>'
                 f'<div class="abs" style="left:216px;top:{top+12}px;width:{w:.0f}px;height:26px;border-radius:13px;background:{c["blue"] if last else "#BFC4E0"}"></div>'
                 f'<div class="abs num up" style="left:700px;width:270px;top:{top}px;text-align:right;font-size:38px;font-weight:800;white-space:nowrap">{TRI.replace("currentColor", c["up"])} +{v}%</div>')
    P[3] = a_css(3), (
        '<div class="abs panel" style="height:460px"></div>' + a_top(3, "歷史對照")
        + '<div class="abs kick" style="left:64px;top:168px">加權指數・6 次期中選舉</div>'
        + '<div class="abs ttl" style="left:64px;top:216px;font-size:84px">選後 3 個月<br>6 次都收紅</div>'
        + '<div class="abs note" style="left:64px;top:490px;font-weight:700;white-space:nowrap">各次期中選舉後，第一個台股交易日起算 3 個月</div>'
        + '<div class="abs box" style="left:64px;top:546px;width:952px;height:610px"></div>' + bars
        + f'<div class="abs" style="left:64px;top:1178px;font-size:38px;font-weight:900;white-space:nowrap">平均 <span class="num">+7.1%</span>，最低只有 <span class="num hl">+0.2%</span>（2018）。</div>'
        + a_foot("歷史對照", "來源：證交所指數（本站資料庫）"))
    # 4
    rows = ""
    for i, (t, s, v, k) in enumerate(WORST):
        y = 498 + i * 188
        col = c["dn"] if k == "dn" else c["ink"]
        rows += (f'<div class="abs box" style="left:64px;top:{y}px;width:952px;height:168px">'
                 f'<div class="abs" style="left:34px;top:30px;font-size:38px;font-weight:900;white-space:nowrap">{t}</div>'
                 f'<div class="abs" style="left:34px;top:92px;font-size:32px;font-weight:500;color:{c["ink2"]};white-space:nowrap">{s}</div>'
                 f'<div class="abs num" style="right:34px;top:36px;font-size:84px;font-weight:800;line-height:1;color:{col};white-space:nowrap">{v}</div></div>')
    P[4] = a_css(4) , (
        '<div class="abs panel" style="height:460px"></div>' + a_top(4, "小知識")
        + '<div class="abs kick" style="left:64px;top:168px">但不是一路順風</div>'
        + '<div class="abs ttl" style="left:64px;top:216px;font-size:84px">最差的情況長<br>這樣</div>'
        + rows
        + '<div class="abs note" style="left:64px;top:1066px;width:952px">樣本只有 6 次，當時利率與景氣都不同，這是歷史統計，不是預測。</div>'
        + a_foot("小知識", "來源：本站資料庫、公開統計"))
    # 5
    P[5] = a_css(5), (
        '<div class="abs panel" style="height:540px"></div>' + a_top(5, "熱點解讀")
        + '<div class="abs kick" style="left:64px;top:168px">你怎麼看</div>'
        + '<div class="abs ttl" style="left:64px;top:224px;font-size:92px">這次台股的<br>關鍵是？</div>'
        + f'<div class="abs box" style="left:64px;top:590px;width:952px;height:230px">'
          f'<div class="abs num" style="left:48px;top:30px;font-size:64px;font-weight:900;line-height:90px">A</div><div class="abs hl" style="left:140px;top:30px;font-size:60px;font-weight:900;line-height:90px">選舉結果</div>'
          f'<div class="abs num" style="left:48px;top:118px;font-size:64px;font-weight:900;line-height:90px">B</div><div class="abs hl" style="left:140px;top:118px;font-size:60px;font-weight:900;line-height:90px">外資賣超</div></div>'
        + '<div class="abs" style="left:64px;top:860px;font-size:42px;font-weight:900">留言 A 或 B，說說你的理由。</div>'
        + f'<div class="abs note" style="left:64px;top:950px;width:952px;font-weight:700">追蹤哩股哩股，<br>明天解讀下一個熱點。</div>'
        + '<div class="abs note" style="left:64px;top:1096px;width:952px;font-size:32px">公開資料整理，非投資建議。</div>'
        + a_foot("熱點解讀", "資料日期：2026-11-04"))
    return P


# ===================== B 專業版 =====================
B = dict(bg="#FBFAF6", ink="#14213D", ink2="#4A5468", rule="#CFC8B8", hair="#E3DDCF", navy="#14213D",
         acc="#A8482A", up="#C0392B", dn="#1F7A57", tint="#F1EDE3")


def b_css():
    c = B
    return BASE + f"""
body{{background:{c['bg']};color:{c['ink']}}}
.strip{{left:0;right:0;top:0;height:96px;background:{c['navy']};color:#fff}}
.brand{{left:64px;top:0;height:96px;display:flex;align-items:center;font-weight:900;font-size:34px;letter-spacing:2px}}
.cat{{left:300px;top:0;height:96px;display:flex;align-items:center;gap:10px;font-size:28px;font-weight:500;color:#D9DCE6;border-left:2px solid rgba(255,255,255,.3);padding-left:22px}}
.pg{{right:64px;top:0;height:96px;display:flex;align-items:center;font-size:28px;font-weight:700;color:#fff}}
.kick{{font-size:32px;font-weight:700;color:{c['acc']};letter-spacing:1px}}
.ttl{{font-weight:900;color:{c['ink']};line-height:1.22}}
.rule{{left:64px;width:952px;height:4px;background:{c['navy']}}}
.hair{{left:64px;width:952px;height:2px;background:{c['hair']}}}
.foot{{left:64px;right:64px;bottom:44px;border-top:2px solid {c['rule']};padding-top:16px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;color:{c['ink2']}}}
.note{{font-size:34px;font-weight:500;color:{c['ink2']};line-height:1.5}}
.up{{color:{c['up']}}} .dn{{color:{c['dn']}}} .hl{{color:{c['acc']}}}
.box{{background:#fff;border:2px solid {c['hair']}}}
.credit{{font-size:20px;font-weight:500;color:{c['ink2']}}}
"""


def b_strip(p, chip):
    return (f'<div class="abs strip" data-meta data-strip><div class="abs brand" style="color:#fff">哩股哩股</div>'
            f'<div class="abs cat">{ICON[chip]}{chip}</div><div class="abs pg num">{p} / 5</div></div>')


def b_foot(l, r):
    return f'<div class="abs foot" data-meta><span>{l}</span><span>{r}</span></div>'


def b_pages():
    c = B; P = {}
    css = b_css()
    P[1] = css + ".photo img{width:100%;height:100%;object-fit:cover;object-position:50% 58%;filter:saturate(.8) contrast(1.02)}", (
        '<div class="abs photo" data-b data-full style="left:0;top:96px;width:1080px;height:520px"><img src="%s"></div>' % PHOTO
        + b_strip(1, "熱點解讀")
        + f'<div class="abs credit" data-credit style="left:64px;top:626px;width:952px;text-align:right;height:26px">{CREDIT}</div>'
        + '<div class="abs kick" style="left:64px;top:672px">熱點解讀・11/04</div>'
        + '<div class="abs ttl" style="left:64px;top:718px;font-size:78px;white-space:nowrap">期中選舉後台股怎麼走？</div>'
        + f'<div class="abs rule" style="top:836px"></div>'
        + f'<div class="abs num" style="left:64px;top:860px;font-size:148px;font-weight:800;line-height:1.05;letter-spacing:-3px">6<span style="color:{c["acc"]}">/</span>6</div>'
        + '<div class="abs" style="left:400px;top:896px;font-size:38px;font-weight:700;line-height:1.4;color:%s">選後 3 個月<br>收紅次數</div>' % c["ink2"]
        + f'<div class="abs hair" style="top:1060px"></div>'
        + f'<div class="abs" style="left:64px;top:1086px;font-size:44px;font-weight:900;white-space:nowrap">但途中最深回檔 <span class="num hl">5.8%</span>，這次呢？</div>'
        + f'<div class="abs" style="left:64px;top:1160px;font-size:32px;font-weight:700;color:{c["ink2"]}">滑動看歷史數字　→</div>'
        + b_foot("熱點解讀", "加權指數・6 次樣本"))
    rows = "".join(
        f'<div class="abs hair" style="top:{y}px"></div>'
        f'<div class="abs num" style="left:64px;top:{y+36}px;font-size:44px;font-weight:800;color:{c["acc"]}">0{i+1}</div>'
        f'<div class="abs" style="left:150px;top:{y+22}px;font-size:40px;font-weight:900;white-space:nowrap">{t}</div>'
        f'<div class="abs" style="left:150px;top:{y+86}px;font-size:32px;font-weight:500;color:{c["ink2"]};white-space:nowrap">{s}</div>'
        for i, (t, s), y in [(i, x, 460 + i * 178) for i, x in enumerate(NOW)])
    P[2] = css, (b_strip(2, "熱點解讀")
        + '<div class="abs kick" style="left:64px;top:140px">熱點解讀・11/04 早盤快照</div>'
        + '<div class="abs ttl" style="left:64px;top:188px;font-size:84px">開票中，市場先<br>怎麼反應？</div>'
        + '<div class="abs rule" style="top:440px"></div>' + rows + '<div class="abs hair" style="top:994px"></div>'
        + '<div class="abs note" style="left:64px;top:1020px;width:952px">11/3 台股已先收 <span class="num">43,307.54</span> 點（−1,612 點）。開票仍在進行，數字會變動。</div>'
        + b_foot("熱點解讀", "來源：CNBC、CBS、NBC 即時報導"))
    mx = 14.4; bars = ""
    for i, (y, v) in enumerate(HIST):
        w = max(v / mx, .05) * 480; top = 538 + i * 94; last = y == "2022"
        bars += (f'<div class="abs hair" style="top:{top-12}px"></div>'
                 f'<div class="abs num" style="left:64px;top:{top}px;width:110px;font-size:36px;font-weight:700">{y}</div>'
                 f'<div class="abs" style="left:190px;top:{top+24}px;width:{w:.0f}px;height:14px;background:{c["navy"]}"></div>'
                 f'<div class="abs num up" style="left:700px;width:316px;top:{top}px;text-align:right;font-size:38px;font-weight:800;white-space:nowrap">{TRI.replace("currentColor", c["up"])} +{v}%</div>')
    P[3] = css, (b_strip(3, "歷史對照")
        + '<div class="abs kick" style="left:64px;top:140px">加權指數・6 次期中選舉</div>'
        + '<div class="abs ttl" style="left:64px;top:188px;font-size:84px">選後 3 個月<br>6 次都收紅</div>'
        + '<div class="abs rule" style="top:420px"></div>'
        + '<div class="abs note" style="left:64px;top:446px;font-weight:700;white-space:nowrap">各次期中選舉後，第一個台股交易日起算 3 個月</div>'
        + bars + f'<div class="abs hair" style="top:{538+6*94-12}px"></div>'
        + f'<div class="abs" style="left:64px;top:1130px;font-size:40px;font-weight:900;white-space:nowrap">平均 <span class="num">+7.1%</span>，最低只有 <span class="num hl">+0.2%</span>（2018）。</div>'
        + b_foot("歷史對照", "來源：證交所指數（本站資料庫）"))
    rows = ""
    for i, (t, s, v, k) in enumerate(WORST):
        y = 460 + i * 178; col = c["dn"] if k == "dn" else c["ink"]
        rows += (f'<div class="abs hair" style="top:{y}px"></div>'
                 f'<div class="abs" style="left:64px;top:{y+26}px;font-size:38px;font-weight:900;white-space:nowrap">{t}</div>'
                 f'<div class="abs" style="left:64px;top:{y+88}px;font-size:32px;font-weight:500;color:{c["ink2"]};white-space:nowrap">{s}</div>'
                 f'<div class="abs num" style="right:64px;top:{y+34}px;font-size:84px;font-weight:800;line-height:1;color:{col};white-space:nowrap">{v}</div>')
    P[4] = css, (b_strip(4, "小知識")
        + '<div class="abs kick" style="left:64px;top:140px">但不是一路順風</div>'
        + '<div class="abs ttl" style="left:64px;top:188px;font-size:84px">最差的情況長<br>這樣</div>'
        + '<div class="abs rule" style="top:440px"></div>' + rows + '<div class="abs hair" style="top:994px"></div>'
        + '<div class="abs note" style="left:64px;top:1020px;width:952px">樣本只有 6 次，當時利率與景氣都不同，這是歷史統計，不是預測。</div>'
        + b_foot("小知識", "來源：本站資料庫、公開統計"))
    P[5] = css, (b_strip(5, "熱點解讀")
        + '<div class="abs kick" style="left:64px;top:140px">你怎麼看</div>'
        + '<div class="abs ttl" style="left:64px;top:188px;font-size:90px">這次台股的<br>關鍵是？</div>'
        + '<div class="abs rule" style="top:466px"></div>'
        + f'<div class="abs box" style="left:64px;top:500px;width:952px;height:230px">'
          f'<div class="abs num" style="left:48px;top:30px;font-size:60px;font-weight:900;line-height:90px">A</div><div class="abs hl" style="left:140px;top:30px;font-size:58px;font-weight:900;line-height:90px">選舉結果</div>'
          f'<div class="abs num" style="left:48px;top:118px;font-size:60px;font-weight:900;line-height:90px">B</div><div class="abs hl" style="left:140px;top:118px;font-size:58px;font-weight:900;line-height:90px">外資賣超</div></div>'
        + '<div class="abs" style="left:64px;top:782px;font-size:42px;font-weight:900">留言 A 或 B，說說你的理由。</div>'
        + '<div class="abs note" style="left:64px;top:876px;width:952px;font-weight:700">追蹤哩股哩股，<br>明天解讀下一個熱點。</div>'
        + '<div class="abs note" style="left:64px;top:1020px;width:952px;font-size:32px">公開資料整理，非投資建議。</div>'
        + b_foot("熱點解讀", "資料日期：2026-11-04"))
    return P


def main():
    names = {1: "01_cover", 2: "02_now", 3: "03_history", 4: "04_worst", 5: "05_close"}
    only = sys.argv[1:] or ["A", "B"]
    report = {}
    with sync_playwright() as p:
        import glob
        exe = next(iter(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome"))), None)
        br = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = br.new_page(viewport={"width": W, "height": H})
        for v in only:
            pages = a_pages() if v == "A" else b_pages()
            d = OUT / v; d.mkdir(parents=True, exist_ok=True)
            for n, (css, body) in pages.items():
                f = HERE / "_s.html"
                f.write_text(f"<!doctype html><meta charset=utf-8>{FONT_LINKS}<style>{css}</style><body>{body}</body>", encoding="utf-8")
                pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(500)
                res = pg.evaluate(CHECK)
                png = d / f"{names[n]}.png"; pg.screenshot(path=str(png))
                Image.open(png).convert("RGB").save(d / f"{names[n]}.jpg", quality=93); png.unlink()
                bad = {k: x for k, x in res.items() if k != "n" and x}
                report[f"{v}{n}"] = (res["n"], bad)
        br.close()
    for k, (n, bad) in report.items():
        print(k, "文字區塊", n, "問題", bad or 0)


main()
