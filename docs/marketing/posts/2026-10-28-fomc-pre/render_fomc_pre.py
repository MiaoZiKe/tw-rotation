"""FOMC 前一天貼文（2026-10-28 發）：v2 版型＋Andy 10-28 修改（明亮封面、左上只留 LOGO＋名稱、直角長條）。
用法：CHROMIUM=... python render_fomc_pre.py <輸出資料夾>；輸出 1.jpg～5.jpg，印「重疊檢查：程式 N 張 M 筆」。"""
import sys, io, base64
from pathlib import Path
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p/"docs/marketing/posts/samples_1028/event_v2_lib").exists())/"docs/marketing/posts/samples_1028/event_v2_lib"))
import lib
from lib import *
EXTRA = """
.track,.bar{border-radius:0 !important}
.track{background:rgba(15,34,51,.10) !important}
.hd .hname{font-size:36px;font-weight:800;color:#0F2233}
body.cv{background:#EAF2FC;color:#0F2233}
.shade{background:linear-gradient(180deg,rgba(255,255,255,.35) 0%,rgba(255,255,255,0) 14%,rgba(244,248,255,.0) 40%,rgba(244,248,255,.90) 56%,rgba(244,248,255,.98) 70%,#F4F8FF 100%) !important}
.cvtop .brand{color:#0F2233;text-shadow:0 1px 6px rgba(255,255,255,.7)}
.cvtop .cvdate{color:#0F2233;text-shadow:0 1px 6px rgba(255,255,255,.7)}
.cvt{color:#0F2233 !important;text-shadow:none !important}
.cvt .yy{background:#FFD23F;color:#0F2233;padding:0 14px;border-radius:0}
.hook{color:#3F35A8 !important}
.cvsub{color:#33485B !important;border-top:2px solid rgba(15,34,51,.18) !important}
.pic{width:100%;object-fit:cover;border-radius:28px;display:block;flex:none}
.col{display:flex;flex-direction:column;gap:22px}
"""
lib.CSS += EXTRA
ASOF = "資料日 10/27・CME FedWatch"; TOT = 5
bgd = "data:image/jpeg;base64," + base64.b64encode((Path(lib.HERE)/"bg"/"fomc_day.jpg").read_bytes()).decode()
def crop(y0, h):
    im = Image.open(Path(lib.HERE)/"bg"/"fomc_day.jpg").convert("RGB").crop((0, y0, 1080, y0+h)); b = io.BytesIO(); im.save(b, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def pin(headline, body, idx, bib=None, bh=100, asof=ASOF):
    f = f'<div class="ft"><span class="d">{asof}</span><span class="pg num">{idx} / {TOT}</span>{bibi(bib, bh) if bib else ""}</div>'
    return (f'<body class="in" style="background:#F0EEFA"><div class="hd">{logo()}<span class="hname">哩股哩股</span><span class="hdate num">10/28 事件前</span></div>'
            f'<div class="head">{headline}</div><div class="main">{body}</div>{f}</body>')
def cover():
    return (f'<body class="cv"><img class="bgimg" data-bg="1" style="top:-380px" src="{bgd}"><div class="shade"></div>'
            f'<div class="cvtop"><img src="{logo_uri()}"><span class="brand">哩股哩股</span><span class="cvdate num">10/28 事件前</span></div>'
            f'<div class="cvbody"><div class="cvt">聯準會利率<br>明天凌晨<span class="yy num">2 點</span>公布</div><div class="hook">利率會變嗎？</div>'
            f'<div class="cvsub">台灣 10/29（四）02:00 公布・02:30 記者會</div></div></body>')
def bar(lb, v, txt, col, lab_w=190):
    return f'<div class="row" style="flex:1;min-height:110px"><div class="lb" style="width:{lab_w}px;font-size:36px">{lb}</div><div class="track" style="height:56px"><div class="bar" style="width:{v}%;background:{col}"></div></div><div class="val num" style="color:{col};width:190px">{txt}</div></div>'
def node(d, v, n, tint, q=False):
    return (f'<div class="blk" style="background:{TINT[tint]};flex:1"><div class="row"><div class="lab num" style="width:230px;font-size:36px">{d}</div>'
            f'<div style="flex:1"><div class="kv num" style="font-size:78px">{v}</div><div class="note" style="font-size:32px">{n}</div></div></div></div>')
def li(k, t, s, c):
    return f'<div class="li"><div class="nb" style="background:{c}">{k}</div><div><div class="t">{t}</div><div class="note" style="font-size:32px">{s}</div></div></div>'
def card(k, t, sub, c, tint):
    return (f'<div class="blk" style="background:{TINT[tint]};flex:1"><div class="row" style="gap:30px"><div class="nb" style="background:{c};width:84px;height:84px;font-size:48px">{k}</div>'
            f'<div><div class="t" style="font-size:54px;font-weight:800;line-height:1.3">{t}</div><div class="note" style="font-size:38px">{sub}</div></div></div></div>')
P = [cover(),
 pin('明天約 <span class="y num">9 成</span>預期持平；<br>12 月的定價則偏向升息',
   f'<div class="blk" style="background:{TINT["blue"]}">' + bar("10/28 持平", 90.6, "91%", INK, 250) + bar("10/28 升息", 9.4, "9%", "#8F5600", 250) + bar("12 月升息", 73, "73%起", "#3F35A8", 250) +
   '</div><div class="unit">CME FedWatch 約 10/27 資料。12 月升息機率各媒體引述 73%～80% 以上，圖取 73%。這是期貨市場定價，不是本帳號的預測</div>', 2, "face_think", 100),
 pin('利率現在在 <span class="y num">3.75～4.00%</span>',
   f'<img class="pic" style="height:250px" src="{crop(560, 250)}">' +
   node("2025/12", "3.50–3.75%", "降息 1 碼", "amber") + node("2026/09", "3.75–4.00%", "升息 1 碼（12 比 0）", "teal") + node("10/29 凌晨", "？", "02:00 公布", "lilac"), 3, "calendar", 100),
 pin('明天凌晨看這 <span class="y num">4</span> 件事',
   card("1", "聲明措辭", "對通膨與就業的描述有沒有改", "#5145C8", "blue") + card("2", "投票結果", "有沒有人投反對票", "#0A7F77", "teal") + card("3", "02:30 記者會", "對 12 月的說法", "#B26A00", "amber") + card("4", "本次沒有點陣圖", "不是經濟預測（SEP）會議", "#3F35A8", "lilac"), 4, "magnifier", 100),
 pin('利率預期變動時，<br>常被討論的 <span class="y num">3</span> 個管道',
   card("1", "美元：反映利差預期", "升降方向都可能", "#5145C8", "blue") + card("2", "美債殖利率", "常隨利率預期調整", "#0A7F77", "teal") + card("3", "股票估值", "折現率隨利率預期改變", "#B26A00", "amber") +
   f'<div class="blk s" style="background:#fff"><div class="note"><b>收藏這張</b>，明天凌晨公布後回來對照<br><span style="font-size:30px;color:{INK3}">只說明傳導管道，不預測方向、非投資建議</span></div></div>', 5, "clock", 100),
]
if __name__ == "__main__":
    out = Path(sys.argv[1]); render(P, out)
    sheet(out, [f"{i}.jpg" for i in range(1, 6)], out/"sheet.jpg", 5, 360)
