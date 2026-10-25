"""哩股哩股社群貼文共用版型（亮色 HUD 科技風）。規範全文：docs/marketing/social_unit/post_design_system.md。

social_snap.py（盤中、盤後法人、盤後融資融券）與 social_premarket.py（盤前）都從這裡拿：
色票（token）、畫布與安全邊距、標題列（LOGO＋時段膠囊＋標題＋靠右日期）、卡片與四角括角的 CSS。
值取自網站「科技 HUD・淺」主題（site/theme4.css @tokens hud light），貼文與網站同一組色；改色只改這個檔。
圖上不放備註、來源、網址（Andy 規定）；日期只在標題列；品牌＝標題列 LOGO，不另放浮水印。
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- 色票（亮色 HUD；對比：紅 5.79、綠 5.31、次要字 9.61、最淡字 6.05，均對卡色 #F8FBFD 實算）----
TOKENS = dict(
    bg="#E8EFF5", panel="#F8FBFD", panel2="#F1F6FA", line="#CFDDE8", line2="#AFC3D3",
    ink="#0A1B2A", ink2="#2C4559", ink3="#4A6377",
    cyan="#0A6A86", rise="#C4142F", fall="#07784E", amber="#8F5600", flat="#566A7C",
    accent="#0A6A86", bracket="rgba(10,106,134,.85)", violet="#5145C8", blue="#1F5FB8",
)
# 時段膠囊（字一律深色 #0A1B2A）
SLOT = {"premarket": ("盤前", "#F5B73B"), "intraday": ("盤中", "#0EA5E9"),
        "close": ("盤後", "#A78BFA"), "credit": ("盤後", "#A78BFA")}
CATEGORY = {"科技": "#1F5FB8", "事件": "#8F5600", "總經": "#5145C8", "新聞": "#0A6A86"}   # 新聞類別色（不得用紅綠）
INST = {"外資": "#2563EB", "投信": "#EA7A12", "自營商": "#7C5CE0", "加權指數": "#0A1B2A"}
MA_COLORS = ["#D99A00", "#0891B2", "#7C5CE0", "#DB2777", "#65A30D", "#0A1B2A"]    # 5、10、20（月）、60（季）、120（半年）、240（年）
MA_NAMES = ["5日", "10日", "月線", "季線", "半年線", "年線"]

FONT = "'Noto Sans CJK TC','Noto Sans TC','PingFang TC','Microsoft JhengHei','WenQuanYi Zen Hei',sans-serif"
NUM_FONT = "Inter,'SF Mono',Consolas,monospace"

# ---- 畫布 ----
CANVAS = {
    "threads": dict(w=1080, pad="36px 40px 40px", s=1.0),                  # 寬 1080；高依內容（≤1350）
    "story": dict(w=1080, h=1920, pad="250px 48px 230px", s=1.1),           # 上 250／下 230 是 IG 介面蓋掉的安全區，不放字
}


def logo_uri() -> str:
    f = ROOT / "site" / "brand" / "icon-192.png"
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def vars_css() -> str:
    return ":root{" + "".join(f"--{k}:{v};" for k, v in TOKENS.items()) + "}"


def base_css(mode: str) -> str:
    """畫布底（冷白藍＋32px 細格線＋左上青藍光暈）、標題列、卡片（四角括角）。mode＝threads｜story。"""
    c = CANVAS[mode]
    s = c["s"]
    h = f"height:{c['h']}px;" if "h" in c else ""
    return vars_css() + f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{c['w']}px;{h}color:var(--ink);font-family:{FONT};padding:{c['pad']};display:flex;flex-direction:column;
background:linear-gradient(rgba(10,106,134,.05) 1px,transparent 1px) 0 0/32px 32px,linear-gradient(90deg,rgba(10,106,134,.05) 1px,transparent 1px) 0 0/32px 32px,
radial-gradient(900px 520px at 12% -10%,rgba(55,200,255,.24),rgba(55,200,255,0) 60%),var(--bg)}}
.num{{font-family:{NUM_FONT};font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.hd{{display:flex;align-items:center;height:88px;gap:18px;flex:none}}
.hd img{{width:72px;height:72px;border-radius:17px;flex:none;display:block}}
.hd .chip{{font-size:{round(28*s)}px;font-weight:800;line-height:1.5;padding:2px 18px;border-radius:12px;color:#0A1B2A;flex:none;white-space:nowrap}}
.hd .nm{{font-size:{round(54*s)}px;font-weight:800;line-height:1.5;white-space:nowrap;min-width:0}}
.hd .dt{{margin-left:auto;font-size:{round(36*s)}px;font-weight:600;line-height:1.5;color:var(--ink2);white-space:nowrap;font-family:{NUM_FONT};font-variant-numeric:tabular-nums}}
.rule{{height:2px;flex:none;margin:14px 0 14px;background:linear-gradient(90deg,#06B6D4,rgba(6,182,212,0));border-radius:2px}}
.card,.q{{position:relative}}
.card{{background:var(--panel);border:1.5px solid var(--line);border-radius:10px;box-shadow:inset 0 1px 0 rgba(255,255,255,.9),0 10px 26px -18px rgba(10,40,60,.45)}}
.card::after,.q::after{{content:"";position:absolute;inset:0;pointer-events:none;border-radius:inherit;background-repeat:no-repeat;background:
linear-gradient(var(--bracket),var(--bracket)) left top/18px 3px,linear-gradient(var(--bracket),var(--bracket)) left top/3px 18px,
linear-gradient(var(--bracket),var(--bracket)) right top/18px 3px,linear-gradient(var(--bracket),var(--bracket)) right top/3px 18px,
linear-gradient(var(--bracket),var(--bracket)) left bottom/18px 3px,linear-gradient(var(--bracket),var(--bracket)) left bottom/3px 18px,
linear-gradient(var(--bracket),var(--bracket)) right bottom/18px 3px,linear-gradient(var(--bracket),var(--bracket)) right bottom/3px 18px;
background-repeat:no-repeat}}
"""


def header_html(kind: str, title: str, date: str, logo: str | None = None, boxes: bool = True) -> str:
    """標題列：LOGO｜時段膠囊｜標題｜日期（靠右）。boxes＝加 data-box 讓重疊檢查量得到。"""
    chip, col = SLOT[kind]
    logo = logo_uri() if logo is None else logo
    d = (lambda n: f" data-box={n}") if boxes else (lambda n: "")
    img = f'<img{d("logo")} src="{logo}">' if logo else ""
    dt = f'<div class=dt{d("date")}>{date}</div>' if date else ""
    return (f'<div class=hd>{img}<span class=chip{d("chip")} style="background:{col}">{chip}</span>'
            f'<div class=nm{d("title")}>{title}</div>{dt}</div><div class=rule></div>')
