"""頻道二「科技透明圈」主題文圖（2026-11-10）：封面沿用公司待遇文定案版（藍色開口正圓＋缺口中間橘膠囊＋右側旁白引號與圖示＋右下「右滑看透明圈」），
但沒有公司名：圓圈裡放「主題關鍵字」、膠囊與旁白、圖示依欄目替換；照片框改放乾淨的主題插圖（自繪 SVG，不用 AI 人像、不放公司照片）。
內頁沿用「待遇透明圈」表格頁版型（頁首、白底圓角表格、頁底出處）。
用法：python render_topic.py <ASSETS> <輸出根目錄> [t10b|t01|all]    # 輸出到 <輸出根目錄>/<代號>/1.png～5.png、compare.png、overlap_*.json
字型用 TW_FONT_DIR；封面程式重用 title_d.py（TD_* 參數見該檔）。全部頁面的重疊檢查：封面用 title_d 的墨跡外框＋像素距離，內頁用 render_samples 的 DOM 外框檢查。"""
import os, re, sys, json, io
from pathlib import Path
HERE = Path(__file__).resolve().parent
ASSETS_ARG, OUT_ROOT = sys.argv[1], Path(sys.argv[2]); WHICH = sys.argv[3] if len(sys.argv) > 3 else "all"
OUT_ROOT.mkdir(parents=True, exist_ok=True)
sys.argv = [sys.argv[0], ASSETS_ARG, str(OUT_ROOT / "_tmp")]
src = (HERE / "render_samples.py").read_text(encoding="utf8")
G = {"__file__": str(HERE / "render_samples.py"), "__name__": "rs_prefix"}
exec(compile(src[:src.index("# ---- A1 封面＝")], "render_samples_prefix", "exec"), G)   # 重用 CSS、頁首 top()、頁底 ft()、SWIPE、photo_uri 等
exec(re.search(r'JS = """.*?\n\}"""', src, re.S).group(0), G)
INK, BLUE, ORG, GREY, LINE, TINT = (G[k] for k in ("INK", "BLUE", "ORG", "GREY", "LINE", "TINT"))
for _k, _v in (("TC_VAR", "D6"), ("TC_SW", "46"), ("TC_PW", "176"), ("TC_PH", "66"), ("TC_PF", "48"), ("TC_LG", "18")): os.environ[_k] = os.environ.get(_k) or _v
sys.path.insert(0, str(HERE))
import title_d
from playwright.sync_api import sync_playwright
from PIL import Image

FONT = "font-family='TCS,Noto Sans TC,sans-serif'"


# ---------------- 封面主題插圖（1032×690，自繪；底色淡藍，品牌藍／橘／深藍黑） ----------------
def ill_exam():
    code = [(300, 170, 130, BLUE), (330, 208, 230, "#fff"), (330, 246, 160, ORG), (330, 284, 250, "#fff"), (300, 322, 110, BLUE), (330, 360, 200, "#fff")]
    lines = "".join(f"<rect x='{x+30}' y='{y}' width='{w}' height='16' rx='8' fill='{c}' fill-opacity='{1 if c != '#fff' else .85}'/>" for x, y, w, c in code)
    ticks = "".join(f"<line x1='{820 + 85*__import__('math').cos(a):.1f}' y1='{285 + 85*__import__('math').sin(a):.1f}' x2='{820 + 72*__import__('math').cos(a):.1f}' y2='{285 + 72*__import__('math').sin(a):.1f}' stroke='{BLUE}' stroke-width='5' stroke-linecap='round'/>" for a in [i * 3.14159 / 6 for i in range(12)])
    checks = "".join(f"<path d='M{92} {y+8} l14 14 l26 -30' fill='none' stroke='{ORG}' stroke-width='9' stroke-linecap='round' stroke-linejoin='round'/><rect x='150' y='{y}' width='70' height='14' rx='7' fill='{LINE}'/><rect x='150' y='{y+24}' width='46' height='12' rx='6' fill='{LINE}'/>" for y in (235, 315, 395))
    return f"""<svg width="1032" height="690" viewBox="0 0 1032 690" xmlns="http://www.w3.org/2000/svg"><rect width="1032" height="690" fill="{TINT}"/>
<circle cx="880" cy="120" r="170" fill="#fff" fill-opacity=".55"/><circle cx="120" cy="600" r="150" fill="#fff" fill-opacity=".55"/>
<rect x="62" y="200" width="190" height="270" rx="24" fill="#fff" stroke="{LINE}" stroke-width="3"/>{checks}
<rect x="320" y="110" width="440" height="330" rx="28" fill="{INK}"/><rect x="346" y="136" width="388" height="278" rx="14" fill="#14264A"/>{lines}
<rect x="262" y="440" width="556" height="36" rx="18" fill="#C9D8F0"/><rect x="460" y="440" width="160" height="12" rx="6" fill="#A9BEDD"/>
<circle cx="860" cy="300" r="92" fill="#fff" stroke="{BLUE}" stroke-width="16"/><rect x="838" y="176" width="44" height="22" rx="8" fill="{BLUE}"/>
<line x1="860" y1="300" x2="860" y2="236" stroke="{ORG}" stroke-width="12" stroke-linecap="round"/><line x1="860" y1="300" x2="900" y2="322" stroke="{INK}" stroke-width="9" stroke-linecap="round"/><circle cx="860" cy="300" r="12" fill="{INK}"/>
</svg>"""


def ill_salary():
    base, sc = 600, 0.9
    data = [("聯發科", 446.5, 120), ("祥碩", 428.1, 330), ("台積電", 407.2, 540)]
    bars = ""
    for i, (n, v, x) in enumerate(data):
        h = v * sc; y = base - h
        bars += (f"<rect x='{x}' y='{y:.1f}' width='170' height='{h:.1f}' rx='18' fill='{BLUE if i == 0 else '#5B93F0' if i == 1 else '#9DBFF7'}'/>"
                 f"<text x='{x+85}' y='{y-16:.1f}' text-anchor='middle' {FONT} font-size='44' font-weight='900' fill='{INK}'>{v}</text>"
                 f"<text x='{x+85}' y='{base+48}' text-anchor='middle' {FONT} font-size='36' font-weight='800' fill='{INK}'>{n}</text>"
                 f"<circle cx='{x+85}' cy='{y+54:.1f}' r='28' fill='#fff' fill-opacity='.9'/><text x='{x+85}' y='{y+54+13:.1f}' text-anchor='middle' {FONT} font-size='36' font-weight='900' fill='{BLUE}'>{i+1}</text>")
    y400 = base - 400 * sc
    return f"""<svg width="1032" height="690" viewBox="0 0 1032 690" xmlns="http://www.w3.org/2000/svg"><rect width="1032" height="690" fill="{TINT}"/>
<circle cx="900" cy="90" r="170" fill="#fff" fill-opacity=".55"/><circle cx="70" cy="640" r="140" fill="#fff" fill-opacity=".55"/>
<line x1="70" y1="{base}" x2="960" y2="{base}" stroke="#B9CDEA" stroke-width="5" stroke-linecap="round"/>
{bars}<line x1="70" y1="{y400:.1f}" x2="740" y2="{y400:.1f}" stroke="{ORG}" stroke-width="6" stroke-dasharray="4 14" stroke-linecap="round"/>
<text x="772" y="{y400+30:.1f}" {FONT} font-size="100" font-weight="900" fill="{ORG}">400</text><text x="778" y="{y400+80:.1f}" {FONT} font-size="32" font-weight="800" fill="{INK}">萬・平均年薪</text>
</svg>"""


def ill_ai():
    colors = [BLUE, ORG, "#fff", "#8FB1EA", "#fff", ORG, BLUE]
    rows = [(0, 150, BLUE), (0, 110, "#fff"), (40, 200, ORG), (40, 130, "#fff"), (40, 170, "#8FB1EA"), (0, 90, BLUE), (0, 60, "#fff"), (40, 220, "#fff"), (40, 150, ORG), (0, 70, BLUE)]
    code = "".join(f"<text x='82' y='{128+i*42}' {FONT} font-size='22' font-weight='700' fill='#6E86B3'>{i+1}</text><rect x='{116+dx}' y='{114+i*42}' width='{w}' height='18' rx='9' fill='{c}' fill-opacity='{.9 if c != '#fff' else .8}'/>" for i, (dx, w, c) in enumerate(rows))
    return f"""<svg width="1032" height="690" viewBox="0 0 1032 690" xmlns="http://www.w3.org/2000/svg"><rect width="1032" height="690" fill="{TINT}"/>
<circle cx="930" cy="90" r="170" fill="#fff" fill-opacity=".55"/><circle cx="560" cy="660" r="130" fill="#fff" fill-opacity=".45"/>
<rect x="50" y="46" width="520" height="598" rx="26" fill="{INK}"/><rect x="50" y="46" width="520" height="52" rx="26" fill="#1B2D55"/><rect x="50" y="72" width="520" height="26" fill="#1B2D55"/>
<circle cx="86" cy="72" r="8" fill="#FF6B6B"/><circle cx="114" cy="72" r="8" fill="{ORG}"/><circle cx="142" cy="72" r="8" fill="#4ADE80"/>{code}
<rect x="116" y="540" width="14" height="30" rx="4" fill="{ORG}"/>
<text x="606" y="320" {FONT} font-size="176" font-weight="900" fill="{BLUE}">84%</text>
<text x="618" y="410" {FONT} font-size="44" font-weight="800" fill="{INK}">開發者使用或打算</text><text x="618" y="466" {FONT} font-size="44" font-weight="800" fill="{INK}">使用 AI 工具</text>
<text x="618" y="560" {FONT} font-size="28" font-weight="700" fill="#566580">Stack Overflow 2025 全球</text><text x="618" y="598" {FONT} font-size="28" font-weight="700" fill="#566580">開發者調查（2025-07-29）</text>
</svg>"""


def pic_html(svg):
    return f'<div class="pic" data-k="photo" style="box-shadow:none;height:690px;overflow:hidden;background:{TINT}">{svg}</div>'


# ---------------- 內頁（沿用待遇透明圈表格頁版型） ----------------
def rows_html(rows, lab_w=210, lab_f=50, val_f=44):
    out = ""
    for i, (a, b) in enumerate(rows):
        out += (f'<div class="rw" style="display:flex;align-items:center;flex:1;border-top:2px solid {LINE}">'
                f'<div class="n" style="width:84px;font-size:40px;color:{BLUE}">{i+1:02d}</div>'
                f'<div style="width:{lab_w}px;font-size:{lab_f}px;font-weight:800;white-space:nowrap">{a}</div>'
                f'<div style="flex:1;min-width:0;font-size:{val_f}px;font-weight:700;white-space:nowrap">{b}</div></div>')
    return out


def table_page(label, pg, title, rows, foot, lab_w=210, lab_f=50, val_f=44, tag=None):
    tg = f'<div style="display:flex;gap:14px"><span class="tag">{tag}</span></div>' if tag else ""
    return (f"{G['top'](label, pg)}<div class='body' style='padding-top:28px'>{tg}"
            f"<div style='font-size:64px;font-weight:900;line-height:84px;margin-top:{20 if tag else 8}px;flex:none'>{title}</div>"
            f"<div class='box' style='margin-top:14px;margin-bottom:24px;flex:1;display:flex;flex-direction:column;min-height:0'>{rows_html(rows, lab_w, lab_f, val_f)}</div></div>{G['ft'](foot, '科技透明圈')}")


def foot2(lines):
    if not lines: return "<div style='height:22px;flex:none'></div>"
    return (f"<div style='margin:auto 48px 34px;border-top:2px solid {LINE};padding-top:10px;font-size:26px;color:{GREY};line-height:36px;flex:none'>" + "<br>".join(lines) + "</div>")


def table2(label, pg, title, rows, foot_lines, lab_w=190, lab_f=54, val_f=38, lab_color=None):
    # 值可含 <br>（多行）；底註多行
    out = ""
    for i, (a, b) in enumerate(rows):
        out += (f'<div class="rw" style="display:flex;align-items:center;flex:1;border-top:2px solid {LINE}">'
                f'<div class="n" style="width:84px;font-size:40px;color:{BLUE}">{i+1:02d}</div>'
                f'<div style="width:{lab_w}px;font-size:{lab_f}px;font-weight:900;white-space:nowrap;color:{lab_color or INK}">{a}</div>'
                f'<div style="flex:1;min-width:0;font-size:{val_f}px;font-weight:700;line-height:54px;white-space:nowrap">{b}</div></div>')
    return (f"{G['top'](label, pg)}<div class='body' style='padding-top:28px'>"
            f"<div style='font-size:64px;font-weight:900;line-height:84px;margin-top:8px;flex:none'>{title}</div>"
            f"<div class='box' style='margin-top:14px;margin-bottom:24px;flex:1;display:flex;flex-direction:column;min-height:0'>{out}</div></div>{foot2(foot_lines)}")


def statement_page(label, pg, title, lines, foot):
    big = "".join(f"<div style='font-size:62px;font-weight:900;line-height:92px;color:{INK if i % 2 == 0 else BLUE}'>{l}</div>" for i, l in enumerate(lines))
    return (f"{G['top'](label, pg)}<div class='body' style='padding-top:28px'>"
            f"<div style='font-size:64px;font-weight:900;line-height:84px;margin-top:8px;flex:none'>{title}</div>"
            f"<div class='box' style='margin-top:14px;margin-bottom:24px;flex:1;display:flex;flex-direction:column;justify-content:center;padding:0 40px'>{big}</div></div>{G['ft'](foot, '科技透明圈')}")


ARTICLES = {
    "t12": dict(company="AI 寫|Code", layout="two", pill="透明說", sub=["AI 都能寫程式了，", "還需要會寫", "Code 嗎？"], icon="bubble", ill=ill_ai, label="下班後聊的", pages=[
        lambda l, p: table2(l, p, "用到多普遍", [("開發者", "84% 使用或打算使用 AI 工具<br>前一年是 76%"), ("GitHub<br>新帳號", "近 80% 第一週就用 GitHub Copilot<br>（只算新加入 GitHub 的帳號）")], ["Stack Overflow 2025 全球開發者調查（自願填答，49,009 份）", "（2025-07-29）；GitHub Octoverse 2025（2025-10-28）"], lab_w=240),
        lambda l, p: table2(l, p, "信任沒跟上", [("46%", "不信任 AI 輸出的準確度"), ("66%", "最困擾：差不多對，但不完全對"), ("45%", "除錯 AI 寫的程式更花時間")], ["Stack Overflow 2025 全球開發者調查", "（自願填答，49,009 份，2025-07-29）"], lab_w=190, lab_f=60, lab_color=BLUE, val_f=40),
        lambda l, p: table2(l, p, "職缺怎麼走", [("台灣", "軟體／工程類職缺年減 5%<br>仍是每月徵才最多的類別"), ("美國", "22～25 歲軟體開發員就業人數<br>較 2022 年底高點降近 20%<br>（作者提醒：不全是 AI 的影響）")], ["104《2026 科技業人才報告書》（2026-04-28）", "美國資料：Stanford Digital Economy Lab（2025-08），非台灣"], lab_w=190),
        lambda l, p: table2(l, p, "給新人三件事（建議）", [("先自己寫", "寫過一遍，再讓 AI 寫"), ("看懂", "AI 給的每一行都要看得懂"), ("練除錯", "AI 寫得快，錯的要有人看出來")], ["以上是一般性建議，不保證求職結果", "出處見第 1 則留言"], lab_w=260, lab_f=48, val_f=40),
    ]),
    "t10b": dict(company="上機考", pill="避雷區", sub=["上機考怎麼準備：", "考前一天要確認的事"], icon="mic", ill=ill_exam, label="面試避雷區", pages=[
        lambda l, p: table_page(l, p, "上機考看什麼", [("答案", "結果對不對"), ("拆題", "解題過程怎麼想"), ("除錯", "AI 寫的程式要看得懂、會除錯")], "出處：104 人力銀行，2026-09"),
        lambda l, p: table_page(l, p, "常見題型（各家不同）", [("演算法", "有人考"), ("SQL", "有人考"), ("基礎知識", "有人考"), ("邏輯測驗", "有人考")], "出處：面試經驗分享（vocus 等），只列分類、不寫題目", val_f=46),
        lambda l, p: table_page(l, p, "限時策略（建議）", [("先做", "會的題先寫"), ("卡住", "先跳下一題"), ("留時間", "檢查邊界案例")], "以上是做法建議，不是公司規定", lab_w=250),
        lambda l, p: table_page(l, p, "考前一天清單", [("看通知信", "時長、語言、查資料、鏡頭"), ("測設備", "網路與電腦先測一次"), ("刷題平台", "104 整理了五個"), ("模擬題", "熟悉作答節奏")], "出處：104 人力銀行，2026-09；每家規定不同，以通知信為準", lab_w=280, lab_f=46, val_f=40),
    ]),
    "t01": dict(company="年薪榜", pill="透明說", sub=["前三名非主管", "平均都破 400 萬"], icon="cup", ill=ill_salary, label="待遇透明圈", pages=[
        lambda l, p: table_page(l, p, "前五名平均年薪", [("聯發科", "446.5 萬・年增 3.6%"), ("祥碩", "428.1 萬・年增約 38.8%"), ("台積電", "407.2 萬・年增約 20%"), ("瑞昱", "387.1 萬"), ("達發", "353.3 萬")], "證交所 2025 年度非主管全時員工（2026-06-30 公布）", lab_w=200, val_f=44),
        lambda l, p: table_page(l, p, "同一批人的中位數", [("聯發科", "355.2 萬"), ("祥碩", "337.4 萬"), ("瑞昱", "319.3 萬"), ("台積電", "316.2 萬")], "證交所 2025 年度非主管全時員工（2026-06-30 公布）", lab_w=200, val_f=50),
        lambda l, p: statement_page(l, p, "為什麼榜上全是半導體", ["半導體業分紅與獎金占比高", "景氣好時，差距會被放大"], "這是平均，不是每個人的數字"),
        lambda l, p: table_page(l, p, "含主管的榜是另一組", [("日月光投控", "628.2 萬（含主管全體員工）"), ("口徑", "兩個榜不能拿來比")], "出處：證交所，2026-06-30 公布", lab_w=300, lab_f=46, val_f=42),
    ]),
}


# ---------------- t01v2：年薪 400 萬的真相（7 頁，一頁一個重點、大字數字當主角） ----------------
def boxpage(label, pg, title, inner, foot_lines=None, pad="28px 36px"):
    ft_ = foot2(foot_lines) if foot_lines else G["ft"]("", "科技透明圈")
    return (f"{G['top'](label, pg)}<div class='body' style='padding-top:28px'>"
            f"<div style='font-size:64px;font-weight:900;line-height:84px;margin-top:8px;flex:none'>{title}</div>"
            f"<div class='box' style='margin-top:14px;margin-bottom:24px;flex:1;display:flex;flex-direction:column;justify-content:center;padding:{pad};min-height:0'>{inner}</div></div>{ft_}")


def pill(t, size=64):
    return f"<div style='align-self:flex-start;display:inline-block;white-space:nowrap;background:{ORG};color:{INK};font-size:{size}px;font-weight:900;padding:6px 34px;border-radius:60px;line-height:1.3'>{t}</div>"


def v2_avg_med(l, p):
    sc = 1.2
    rows = ""
    for n, a, m in (("聯發科", 446.5, 355.2), ("祥碩", 428.1, 337.4), ("台積電", 407.2, 316.2)):
        rows += (f"<div style='margin-top:30px'><div style='font-size:46px;font-weight:900;line-height:56px'>{n}</div>"
                 f"<div style='display:flex;align-items:center;margin-top:6px'><div style='width:130px;font-size:30px;font-weight:700;color:{GREY}'>平均</div>"
                 f"<div style='height:40px;width:{m*sc:.0f}px;background:{BLUE};border-radius:20px 0 0 20px'></div><div style='height:40px;width:{(a-m)*sc:.0f}px;background:{ORG};border-radius:0 20px 20px 0'></div>"
                 f"<div style='margin-left:16px;font-size:42px;font-weight:900'>{a}</div></div>"
                 f"<div style='display:flex;align-items:center;margin-top:8px'><div style='width:130px;font-size:30px;font-weight:700;color:{GREY}'>中位數</div>"
                 f"<div style='height:40px;width:{m*sc:.0f}px;background:#9DBFF7;border-radius:20px'></div><div style='margin-left:16px;font-size:42px;font-weight:900'>{m}</div></div></div>")
    return boxpage(l, p, "非主管平均 vs 中位數", pill("三家都差約 91 萬") + rows, ["證交所 2025 年度非主管全時員工薪資（2026-06-30 公布）", "單位：萬元；差＝平均−中位數，自行計算"])


def v2_formula(l, p):
    chip = lambda t, bg, fg: f"<div style='background:{bg};color:{fg};font-size:52px;font-weight:900;padding:8px 26px;border-radius:24px;white-space:nowrap'>{t}</div>"
    op = lambda t: f"<div style='font-size:50px;font-weight:900;color:{GREY};white-space:nowrap'>{t}</div>"
    formula = f"<div style='display:flex;align-items:center;gap:14px;flex-wrap:nowrap'><div style='font-size:52px;font-weight:900;white-space:nowrap'>年薪</div>{op('＝')}{chip('底薪', BLUE, '#fff')}{op('＋')}{chip('年終', '#9DBFF7', INK)}{op('＋')}{chip('分紅', ORG, INK)}</div>"
    bar = (f"<div style='display:flex;height:120px;margin-top:60px;border-radius:26px;overflow:hidden'><div style='flex:2.2;background:{BLUE}'></div><div style='flex:1.8;background:#9DBFF7'></div><div style='flex:5;background:{ORG}'></div></div>"
           f"<div style='display:flex;margin-top:10px;font-size:32px;font-weight:800'><div style='flex:2.2'>月薪</div><div style='flex:1.8'>年終</div><div style='flex:5'>分紅（員工酬勞）</div></div>"
           f"<div style='margin-top:16px;font-size:28px;color:{GREY};font-weight:700'>示意圖，比例不代表任何公司的實際數字</div>")
    sub = f"<div style='margin-top:40px;font-size:48px;font-weight:800;line-height:64px'>分紅依公司法 235-1，<br>跟獲利連動</div>"
    return boxpage(l, p, "月薪只是底", formula + bar + sub, ["依據：公司法第 235 條之 1（員工酬勞）"])


def v2_link(l, p):
    H = lambda v: v * 0.2
    col = lambda x, v, lab, c: (f"<div style='display:flex;flex-direction:column;align-items:center;justify-content:flex-end;width:250px'><div style='font-size:42px;font-weight:900;margin-bottom:10px;white-space:nowrap'>約 {v:,} 億</div>"
                              f"<div style='width:200px;height:{H(v):.0f}px;background:{c};border-radius:24px 24px 0 0'></div><div style='font-size:44px;font-weight:800;margin-top:12px'>{lab}</div></div>")
    chart = (f"<div style='display:flex;align-items:flex-end;justify-content:center;gap:20px;height:560px'>{col(0, 1406, '2024', '#9DBFF7')}"
             f"<div style='align-self:center'>{pill('+46%', 54)}</div>{col(0, 2061, '2025', BLUE)}</div>")
    return boxpage(l, p, "分紅跟獲利連動", chart, ["台積電董事會 2026-02-10 核准；依據：公司法第 235 條之 1", "員工業績獎金與酬勞合計，與平均年薪口徑不同、不能相除"])


def v2_ask(l, p):
    def card(n, t, sub):
        return (f"<div style='display:flex;align-items:center;gap:26px;flex:1'><div style='flex:none;width:96px;height:96px;border-radius:48px;background:{BLUE};color:#fff;font-size:60px;font-weight:900;display:flex;align-items:center;justify-content:center'>{n}</div>"
                f"<div><div style='font-size:56px;font-weight:900;line-height:76px'>{t}</div><div style='font-size:34px;font-weight:700;color:{GREY};line-height:48px;margin-top:6px'>{sub}</div></div></div>")
    inner = card(1, "保障幾個月", "合約有寫才算數") + f"<div style='border-top:2px solid {LINE}'></div>" + card(2, "浮動占多少", "占整包幾成") + f"<div style='border-top:2px solid {LINE}'></div>" + card(3, "過去幾年實發多少", "看實發，不看承諾")
    return boxpage(l, p, "看 offer 先問這三件事", inner, None, pad="20px 40px")


def v2_src(l, p):
    return table2(l, p, "出處", [("證交所", "2025 年度非主管全時員工薪資統計<br>2026-06-30 公布"), ("台積電", "董事會 2026-02-10 核准<br>員工業績獎金與酬勞"), ("公司法", "第 235 條之 1（員工酬勞）")], ["資料皆為公開統計；平均與中位數為證交所公布值", "含主管的全體員工榜是另一組，不能互比"], lab_w=200, lab_f=50, val_f=38)


def v2_end(l, p):
    plane = f"<svg width='150' height='150' viewBox='0 0 64 64' fill='none' stroke-linecap='round' stroke-linejoin='round'><path d='M6 30 L58 8 L44 56 L30 38 Z' stroke='{BLUE}' stroke-width='4'/><path d='M30 38 L58 8' stroke='{BLUE}' stroke-width='4'/><path d='M30 38 L28 52 L36 44' stroke='{ORG}' stroke-width='4'/></svg>"
    inner = (f"<div style='display:flex;align-items:center;gap:30px'>{plane}<div style='font-size:78px;font-weight:900;line-height:100px;color:{BLUE}'>傳給正在<br>比 offer 的同事</div></div>"
             f"<div style='margin-top:70px;border-top:2px solid {LINE};padding-top:44px;font-size:54px;font-weight:800;line-height:74px'>數字好看，<br>要看多少是你拿得到的</div>")
    return boxpage(l, p, "最後一件事", inner, None, pad="28px 44px")


# ---------------- t01v3 封面：非主管平均＋中位數並排長條、400 萬虛線、公司 LOGO（沒檔先用灰框佔位） ----------------
def _logo_img(slug, x, y, w, h):
    """social/photo_lib/<slug>/logo.png 存在就原色原比例置入 w×h 框（meet），否則畫同尺寸灰色佔位框。"""
    import base64
    root = Path(os.environ.get("TC_PHOTO_ROOT") or G.get("PHOTO_ROOT") or "/nonexistent")
    f = root / slug / "logo.png"
    if f.is_file():
        uri = "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()
        return f"<image href='{uri}' x='{x}' y='{y}' width='{w}' height='{h}' preserveAspectRatio='xMidYMid meet'/>"
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='8' fill='#CBD5E3'/>"


def ill_salary_v3():
    base, sc = 548, 0.74
    data = [("聯發科", "mediatek", 446.5, 355.2, 70), ("祥碩", "asmedia", 428.1, 337.4, 320), ("台積電", "tsmc", 407.2, 316.2, 570)]
    g_ = ""
    for n, slug, a, m, x in data:
        ha, hm = a * sc, m * sc; ya, ym = base - ha, base - hm
        cx = x + 90
        nm_w = 40 * len(n); tot = 110 + 12 + nm_w; x0 = cx - tot / 2
        g_ += (f"<rect x='{x}' y='{ya:.1f}' width='100' height='{ha:.1f}' rx='16' fill='{BLUE}'/><rect x='{x+108}' y='{ym:.1f}' width='72' height='{hm:.1f}' rx='14' fill='#9DBFF7'/>"
               f"<text x='{x+50}' y='{ya-14:.1f}' text-anchor='middle' {FONT} font-size='46' font-weight='900' fill='{INK}'>{a}</text>"
               f"<text x='{x+144}' y='{ym+46:.1f}' text-anchor='middle' {FONT} font-size='30' font-weight='900' fill='{INK}'>{m}</text>"
               + _logo_img(slug, f"{x0:.0f}", base + 28, 110, 44)
               + f"<text x='{x0+122:.0f}' y='{base+62}' {FONT} font-size='40' font-weight='900' fill='{INK}'>{n}</text>")
    y400 = base - 400 * sc
    return f"""<svg width="1032" height="690" viewBox="0 0 1032 690" xmlns="http://www.w3.org/2000/svg"><rect width="1032" height="690" fill="{TINT}"/>
<circle cx="930" cy="80" r="170" fill="#fff" fill-opacity=".55"/><circle cx="60" cy="650" r="130" fill="#fff" fill-opacity=".5"/>
<rect x="70" y="44" width="30" height="30" rx="8" fill="{BLUE}"/><text x="110" y="70" {FONT} font-size="30" font-weight="800" fill="{INK}">非主管平均</text>
<rect x="290" y="44" width="30" height="30" rx="8" fill="#9DBFF7"/><text x="330" y="70" {FONT} font-size="30" font-weight="800" fill="{INK}">中位數</text>
<line x1="50" y1="{base}" x2="780" y2="{base}" stroke="#B9CDEA" stroke-width="5" stroke-linecap="round"/>
{g_}<line x1="50" y1="{y400:.1f}" x2="800" y2="{y400:.1f}" stroke="{ORG}" stroke-width="6" stroke-dasharray="4 14" stroke-linecap="round"/>
<text x="808" y="{y400+34:.1f}" {FONT} font-size="96" font-weight="900" fill="{ORG}">400</text><text x="814" y="{y400+90:.1f}" {FONT} font-size="44" font-weight="900" fill="{INK}">萬</text>
</svg>"""


# ---------------- t01v4 內頁：上市／上櫃前 15 名（LOGO＋平均＋中位數並排長條）＋為什麼台積電不是第一 ----------------
import base64 as _b64


def _logo_tag(code, name, has):
    d = Path(os.environ.get("TC_LOGO_DIR", "/nonexistent")) / f"{code}.png"
    if has and d.is_file():
        from PIL import Image as _I
        im = _I.open(d).convert("RGBA"); _bg = _I.new("RGBA", im.size, "#fff"); _bg.alpha_composite(im)
        from PIL import ImageChops as _C
        bb = _C.difference(_bg.convert("RGB"), _I.new("RGB", im.size, "#fff")).convert("L").point(lambda v: 255 if v > 25 else 0).getbbox() or im.getchannel("A").getbbox()   # 去掉透明或白色留邊，只留真正的圖形
        if bb: im = im.crop(bb)
        w0, h0 = im.size; k = min(1.5, 40 / h0)   # 原色原比例；不放大超過 1.5 倍
        k = min(k, 1.5, 56 / w0, 40 / h0)
        _o = io.BytesIO(); im.save(_o, "PNG")
        return f"<img src='data:image/png;base64,{_b64.b64encode(_o.getvalue()).decode()}' width='{round(w0*k)}' height='{round(h0*k)}' style='display:block'>"
    return f"<div style='width:46px;height:40px;border-radius:8px;background:#9AA7BC;color:#fff;font-size:22px;font-weight:900;display:flex;align-items:center;justify-content:center;white-space:nowrap'>{name[:2]}</div>"   # 沒有 LOGO：同尺寸灰底字標


IND_FINE = {"2454": "IC設計（手機晶片）", "5269": "IC設計（高速傳輸）", "2330": "晶圓代工", "2379": "IC設計（網通）", "6526": "IC設計（藍牙・網通）", "7769": "半導體設備（測試分選機）", "3034": "面板IC設計", "3443": "ASIC設計服務", "3592": "面板IC設計", "4961": "面板IC設計", "6669": "伺服器系統廠", "2317": "電子代工・組裝", "2207": "汽車代理", "2548": "建設", "3014": "IC設計（電腦控制晶片）", "5274": "IC設計（伺服器管理晶片）", "3293": "遊戲開發", "3529": "矽智財（IP）", "3227": "IC設計（光學感測）", "6186": "建設", "8299": "IC設計（記憶體控制晶片）", "6996": "面板IC設計（車用）", "6104": "IC設計（USB晶片）", "6561": "資料中心", "6643": "矽智財（IP）", "3131": "半導體設備（濕製程）", "6411": "IC設計（靜電保護）", "3260": "記憶體模組", "3526": "連接器", "6435": "IC設計（功率元件）"}


def _ind_html(code, fallback):
    t = IND_FINE.get(code, fallback)
    if '（' in t:
        a, b = t.split('（', 1)
        return f"<div style='line-height:28px'>{a}<div style='font-size:21px;font-weight:700;line-height:24px'>（{b}</div></div>"
    return t


def v4_rank(key, title, foot_lines, hi_code="2330"):
    data = json.load(open(os.environ.get("TC_RANK_JSON", "/tmp/claude-0/-home-user-tw-rotation/1662701f-8abb-57a6-b66d-4e0b4e90dd73/scratchpad/tc_plan/rank_top15.json")))[key]
    mx = max(r["avg"] for r in data); W = 204
    rows = ""
    for r in data:
        hi = r["code"] == hi_code
        bg = f"background:{TINT};" if hi else ""
        bar = (f"<div style='width:{W}px;flex:none'><div style='height:16px;width:{r['avg']/mx*W:.0f}px;background:{BLUE};border-radius:8px'></div>"
               f"<div style='height:10px;width:{r['median']/mx*W:.0f}px;background:#9DBFF7;border-radius:5px;margin-top:5px'></div></div>")
        rows += (f"<div style='display:flex;align-items:center;flex:1;border-top:2px solid {LINE};{bg}padding:0 12px;position:relative'>"
                 + (f"<div style='position:absolute;left:0;top:6px;bottom:6px;width:6px;border-radius:3px;background:{BLUE}'></div>" if hi else "")
                 + f"<div class='n' style='width:50px;font-size:26px;color:{BLUE}'>{r['rank']}</div><div style='width:78px;flex:none;display:flex;justify-content:flex-start;padding-right:10px;box-sizing:border-box'>{_logo_tag(r['code'], r['name'], r['logo'])}</div>"
                 f"<div style='width:126px;font-size:{28 if len(r['name']) <= 3 else 25}px;font-weight:900;white-space:nowrap'>{r['name']}</div>"
                 f"<div style='width:216px;font-size:20px;font-weight:700;color:#6B7A92;white-space:nowrap'>{_ind_html(r['code'], r['industry'])}</div>{bar}"
                 f"<div style='margin-left:10px;width:134px;font-size:30px;font-weight:900;text-align:right;white-space:nowrap' class='n'>{r['avg']}<span style='font-size:20px'>萬</span></div>"
                 f"<div style='margin-left:6px;width:112px;font-size:24px;font-weight:700;color:#7C8AA3;text-align:right;white-space:nowrap' class='n'>{r['median']}<span style='font-size:16px'>萬</span></div></div>")
    head = (f"<div style='display:flex;align-items:center;padding:0 12px;height:44px;font-size:22px;font-weight:700;color:#8793A8;white-space:nowrap'><div style='width:50px;white-space:nowrap'>名次</div><div style='width:78px'></div><div style='width:126px'>公司</div><div style='width:216px'>細分類</div>"
            f"<div style='width:226px;display:flex;align-items:center;gap:8px;font-size:18px;white-space:nowrap'><span style='display:inline-block;width:16px;height:12px;background:{BLUE};border-radius:3px'></span>平均<span style='display:inline-block;width:16px;height:9px;background:#9DBFF7;border-radius:3px;margin-left:8px'></span>中位數</div><div style='width:144px;text-align:right'>平均</div><div style='width:118px;text-align:right'>中位數</div></div>")
    return (f"{G['top']('待遇透明圈', '__PG__')}<div class='body' style='padding-top:20px'>"
            f"<div style='font-size:56px;font-weight:900;line-height:74px;margin-top:4px;flex:none'>{title}</div>"
            f"<div class='box' style='margin-top:10px;margin-bottom:16px;flex:1;display:flex;flex-direction:column;min-height:0;padding:0 12px'>{head}{rows}</div></div>{foot2(foot_lines)}")


def v4_why(l, p):
    def para(tag, head, lines, extra=""):
        ls = "".join(f"<div style='font-size:30px;font-weight:600;line-height:60px;color:{INK}'>・{t}</div>" for t in lines)
        return (f"<div style='padding:0;flex:1;display:flex;flex-direction:column;justify-content:center'><div style='display:flex;align-items:center;gap:14px'><div style='background:{BLUE};color:#fff;font-size:26px;font-weight:900;padding:3px 18px;border-radius:22px;line-height:38px'>{tag}</div>"
                f"<div style='font-size:36px;font-weight:900;line-height:56px'>{head}</div></div><div style='margin-top:14px'>{ls}</div>{extra}</div>")
    # 示意圖：一條橫軸，中位數 316.2 與平均 407.2 兩點，中間標「被少數高薪拉高」
    x0, x1, lo, hi = 190, 880, 316.2, 407.2
    sc = lambda v: x0 + (v - 250) / (450 - 250) * (x1 - x0)
    xm, xa = sc(lo), sc(hi)
    F = "font-family='TCS,Noto Sans TC,sans-serif'"
    dia = (f"<svg width='940' height='250' viewBox='0 0 940 250' xmlns='http://www.w3.org/2000/svg' style='display:block;margin:14px 0 0'>"
           f"<rect x='0' y='88' width='150' height='62' rx='31' fill='{BLUE}'/><text x='75' y='130' text-anchor='middle' {F} font-size='34' font-weight='900' fill='#fff'>台積電</text>"
           f"<line x1='{x0}' y1='119' x2='{x1}' y2='119' stroke='#B9CDEA' stroke-width='8' stroke-linecap='round'/>"
           f"<line x1='{xm:.0f}' y1='119' x2='{xa:.0f}' y2='119' stroke='{ORG}' stroke-width='14' stroke-linecap='round'/>"
           f"<circle cx='{xm:.0f}' cy='119' r='23' fill='#9DBFF7'/><circle cx='{xa:.0f}' cy='119' r='23' fill='{BLUE}'/>"
           f"<text x='{xm:.0f}' y='56' text-anchor='middle' {F} font-size='32' font-weight='800' fill='{INK}'>中位數 316.2萬</text>"
           f"<text x='{xa:.0f}' y='56' text-anchor='middle' {F} font-size='32' font-weight='800' fill='{INK}'>平均 407.2萬</text>"
           f"<text x='{(xm+xa)/2:.0f}' y='206' text-anchor='middle' {F} font-size='34' font-weight='900' fill='#B85400'>被少數高薪拉高</text></svg>")
    inner = (para("原因一", "員工組成不一樣", ["台積電全集團 8.4 萬人，有很多晶圓廠的技術人員。", "聯發科 1.9 萬人，近九成是研發及技術人員。", "人多、職種廣，是平均沒那麼高的原因之一。"])
             + f"<div style='border-top:2px solid {LINE};margin:0;flex:none'></div>"
             + para("原因二", "平均會被上面的人拉高", ["非主管裡，資深、職級高的少數人領得多，會把平均往上帶。", "中位數是排在正中間那個人，比較接近一般員工。", "上市、上櫃前 15 名共 30 家，29 家平均高於中位數。"], dia))
    end = f"<div style='background:{TINT};border-radius:20px;padding:20px 30px;font-size:30px;font-weight:800;line-height:44px;margin-bottom:6px'>看待遇先看中位數。<br>之後會一家一家整理各公司的待遇行情。</div>"
    return (f"{G['top'](l, p)}<div class='body' style='padding-top:20px'><div style='font-size:52px;font-weight:900;line-height:70px;margin-top:4px;flex:none'>台積電這麼大，為什麼不是第一？</div>"
            f"<div class='box' style='margin-top:10px;margin-bottom:14px;flex:1;display:flex;flex-direction:column;justify-content:space-between;min-height:0;padding:14px 30px'>{inner}</div>{end}</div><div style='height:22px;flex:none'></div>")


ARTICLES["t01v4"] = dict(company="台積電", pill="透明說", sub=["市值第一大企業，", "平均年薪卻不是第一？"], icon="cup", photo=os.environ.get("TC_COVER_PHOTO", ""), label="待遇透明圈", pages=[
    lambda l, p: v4_rank("上市", "上市・非主管平均年薪前 15", []).replace("__PG__", p),
    lambda l, p: v4_rank("上櫃", "上櫃・非主管平均年薪前 15", [], hi_code="").replace("__PG__", p),
    v4_why])
ARTICLES["t01v3"] = dict(company="年薪榜", pill="透明說", sub=["年薪 400 萬的真相，", "差在分紅"], icon="cup", ill=ill_salary_v3, label="待遇透明圈", pages=[])
ARTICLES["t01v2"] = dict(company="年薪榜", pill="透明說", sub=["年薪 400 萬的真相，", "差在分紅"], icon="cup", ill=ill_salary, label="待遇透明圈",
                         pages=[v2_avg_med, v2_formula, v2_link, v2_ask, v2_src, v2_end])


def run(code):
    a = ARTICLES[code]; od = OUT_ROOT / code; od.mkdir(parents=True, exist_ok=True)
    # 封面：重用 title_d
    g = dict(G, OUT=od, PIC_H=690, TD_PILL=a["pill"], TD_SUB_LINES=a["sub"], TD_ICON=a["icon"], sync_playwright=sync_playwright)
    if a.get("photo"):   # 用實景照片當照片框（已確認授權；署名寫在文案）
        import base64
        from PIL import Image as _I
        _im = _I.open(a["photo"]).convert("RGB"); _w, _h = _im.size; _cw = round(_h * 1032 / 690); _x = (_w - _cw) // 2
        _im = _im.crop((_x, 0, _x + _cw, _h)).resize((1032, 690), _I.LANCZOS); _b = io.BytesIO(); _im.save(_b, "JPEG", quality=92)
        _uri = "data:image/jpeg;base64," + base64.b64encode(_b.getvalue()).decode(); g["TD_PHOTO"] = lambda: _uri
    else:
        g["TD_PIC_HTML"] = pic_html(a["ill"]())
    os.environ["TC_COMPANY"] = a["company"]; os.environ["TC_OUTNAME"] = "1"; os.environ["TC_LAYOUT"] = a.get("layout", "one")
    title_d.main(g)
    rep = {}
    ar = json.load(open(od / "overlap_1.json")); rep["1"] = {"bad": ar["重疊"], "oob": ar["出界"], "ovf": False, "small": []}
    n = len(a["pages"]) + 1
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for i, fn in enumerate(a["pages"], start=2):
            html = fn(a["label"], f"{i} / {n}")
            doc = f'<!doctype html><html><head><meta charset="utf-8">{G["FONTCSS"]}<style>{G["CSS"]}{G["COVER_CSS"]}{G["SWIPE_CSS"]}</style></head><body>{html}</body></html>'
            f = od / f"_{i}.html"; f.write_text(doc, encoding="utf8")
            pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
            pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.evaluate("document.fonts.ready")
            res = pg.evaluate(G["JS"]); pg.screenshot(path=str(od / f"{i}.png")); pg.close(); f.unlink()
            rep[str(i)] = res
            print(code, i, "重疊", len(res["bad"]), "出界", len(res["oob"]), "溢出", res["ovf"], "小字", res["small"], res["bad"][:3])
        b.close()
    json.dump(rep, open(od / "overlap_report.json", "w"), ensure_ascii=False, indent=1)
    ims = [Image.open(od / f"{i}.png").resize((330, 412), Image.LANCZOS) for i in range(1, n + 1)]
    cmp_ = Image.new("RGB", (n * 330 + (n + 1) * 20, 412 + 40), "#E9EDF3")
    for k, im in enumerate(ims): cmp_.paste(im, (20 + k * 350, 20))
    cmp_.save(od / "compare.png")
    tot = sum(len(v["bad"]) + len(v["oob"]) + int(v["ovf"]) for v in rep.values())
    print(f"[{code}] 重疊檢查：程式 {n} 張 {tot} 筆")


for code in (ARTICLES if WHICH == "all" else [WHICH]): run(code)
