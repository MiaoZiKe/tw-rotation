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


def run(code):
    a = ARTICLES[code]; od = OUT_ROOT / code; od.mkdir(parents=True, exist_ok=True)
    # 封面：重用 title_d
    g = dict(G, OUT=od, PIC_H=690, TD_PIC_HTML=pic_html(a["ill"]()), TD_PILL=a["pill"], TD_SUB_LINES=a["sub"], TD_ICON=a["icon"], sync_playwright=sync_playwright)
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
