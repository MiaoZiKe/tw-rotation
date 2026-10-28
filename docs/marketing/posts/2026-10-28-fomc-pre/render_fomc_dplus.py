"""FOMC 前一天貼文 D+ 版（Andy 10-28 選 D 雜誌編輯風，要求色彩更豐富協調）。內容與法遵文字照 v4_D，只換顏色與色塊。
用法：CHROMIUM=... python render_fomc_dplus.py <輸出資料夾>；輸出 1～5.jpg＋sheet.jpg。共用元件在 ../lib_dplus.py。"""
import sys, io, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib_dplus import *
import lib_dplus as L

TOT = 5; ASOF = "資料日 10/27・CME FedWatch"; LABEL = "10/28 事件前"
FOOT2 = "12 月升息機率各媒體引述 73%～80% 以上，圖取 73%。這是期貨市場定價，不是本帳號的預測"
BG_PATH = Path(L._l.HERE)/"bg"/"fomc_day.jpg"
def crop(y0, h, w=1080):
    im = Image.open(BG_PATH).convert("RGB").crop((0, y0, 1080, y0+h))
    if w != 1080: im = im.resize((w, int(h*w/1080)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=88); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
SVGF = "font-family=\"Inter,'Noto Sans CJK TC',sans-serif\""
G, CO, BL, MY, MU, INK, BG, LN = (P[k] for k in ("green", "coral", "blue", "mustard", "mu", "ink", "bg", "ln"))
CH3 = [("coin", "美元", "反映利差預期，升降方向都可能", CO, "tc"), ("pct", "美債殖利率", "常隨利率預期調整", BL, "tb"), ("chart", "股票估值", "折現率隨利率預期改變", G, "tg")]
BIB = ["face_think", "calendar", "magnifier", "coins"]

css = """
.tick{position:absolute;top:0;width:2px;height:8px;background:var(--mu)}
"""
def build():
    cover = (f'<body style="{V}">{cover_head(LABEL)}'
             f'<img class="a" data-g=1 style="left:64px;top:144px;width:952px;height:560px;object-fit:cover;border-radius:4px" src="{crop(330, 560, 1904)}">'
             f'<div class="kick T4b" style="top:736px"><i></i>FOMC 前夕</div>'
             f'<div class="a T1" style="left:64px;top:784px;width:952px;height:240px">聯準會利率<br>明天凌晨{u(2)}點公布</div>'
             f'<div class="a T2" style="left:64px;top:1040px;color:var(--co)">利率會變嗎？</div>'
             f'<div class="hr" style="top:1152px"></div>'
             f'<div class="a row" style="left:64px;top:1176px;gap:16px">{chip("02:00 公布","green")}{chip("02:30 記者會","coral")}{chip("目前 3.75～4.00%","blue")}</div>'
             f'<div class="a T4" style="left:64px;top:1240px;color:var(--mu)">台灣時間 10/29（四）凌晨 02:00 公布</div></body>')
    # --- 2 兩塊淡色底：本次（綠／珊瑚）、12 月（珊瑚）
    tk = ''.join(f'<span class="a T4 num" style="left:{t}%;top:8px;transform:translateX(-{t}%);color:var(--mu)">{t}%</span><i class="tick" style="left:{t}%;transform:translateX(-{min(t,100)//50}px)"></i>' for t in (0, 25, 50, 75, 100))
    p2 = (f'<div class="blk col" style="gap:8px;background:var(--tg)"><div class="lab">本次會議（10/28）</div>'
          f'<div class="row" style="height:112px"><div class="row" style="flex:1;gap:16px;align-items:baseline"><span class="ser T1" style="color:var(--gr);font-weight:700">91%</span><span class="T3b">持平</span></div>'
          f'<div style="width:2px;height:96px;background:var(--ln)"></div><div class="row" style="flex:1;gap:16px;padding-left:32px;align-items:baseline"><span class="ser T1" style="color:var(--co);font-weight:700">9%</span><span class="T3b">升息</span></div></div>'
          f'<div class="sbar" style="height:48px"><i style="width:91%;background:var(--gr)"></i><i style="flex:1;background:var(--co)"></i></div></div>'
          f'<div class="blk col" style="gap:8px;background:var(--tc)"><div class="lab" style="color:var(--co)">12 月會議：升息機率</div>'
          f'<div class="row" style="height:112px;gap:16px;align-items:baseline"><span class="ser T1" style="color:var(--co);font-weight:700">73%</span><span class="T3b">起</span></div>'
          f'<div style="position:relative;height:48px;background:#fff;border-radius:4px"><i style="position:absolute;left:0;top:0;height:100%;width:73%;background:var(--co);border-radius:4px"></i></div>'
          f'<div style="position:relative;height:48px">{tk}</div></div>'
          f'<div class="T4" style="color:var(--mu);border-top:2px solid var(--ln);padding-top:16px">{FOOT2}</div>')
    # --- 3 區間列：降息藍、升息珊瑚、未定虛線綠；左欄日期旁有色點
    PW = 624
    def rowbar(date, cap, lo, hi, col, txt, dot, dashed=False):
        x = (lo-3.5)/0.25*(PW/3); w = (hi-lo)/0.25*(PW/3)
        bar = (f'<div class="fb" style="left:{x:.0f}px;top:44px;width:{w:.0f}px;background:{"var(--tg)" if dashed else col};'
               f'{"border:3px dashed var(--gr);" if dashed else ""}color:{"var(--gr)" if dashed else TXT_ON["green" if col==G else "blue" if col==BL else "coral"]}"><span class="T4b num">{txt}</span></div>')
        return (f'<div class="row" style="height:144px;position:relative"><div style="width:288px" class="col"><span class="T3b ser row" style="font-weight:700;gap:12px"><i class="dot" style="background:{dot}"></i>{date}</span><span class="T4" style="color:var(--mu)">{cap}</span></div>'
                f'<div style="position:relative;width:{PW}px;height:144px">{bar}</div></div>')
    gl = ''.join(f'<i class="gl" style="left:{288+k*PW/3:.0f}px"></i>' for k in range(4))
    ax = ''.join(f'<span class="a T4 num" style="left:{288+k*PW/3:.0f}px;top:0;transform:translateX(-50%);color:var(--mu)">{3.5+k*.25:.2f}</span>' for k in range(4))
    p3 = (f'<img style="width:952px;height:208px;object-fit:cover;border-radius:4px;flex:none" src="{crop(540, 208, 1904)}">'
          f'<div class="col" style="gap:8px"><div class="lab">聯邦基金利率目標區間（%）</div>'
          f'<div style="position:relative;height:432px">{gl}'
          + rowbar("2025/12", "降息 1 碼", 3.5, 3.75, BL, "3.50–3.75%", BL)
          + rowbar("2026/09", "升息 1 碼<br>（12 比 0）", 3.75, 4.0, CO, "3.75–4.00%", CO)
          + rowbar("10/29 凌晨", "02:00 公布", 3.5, 4.25, "", "？", MY, True).replace('<span class="T4b num">？</span>', '<span class="T2 ser">？</span>')
          + f'</div><div style="position:relative;height:40px">{ax}</div></div>')
    # --- 4 時間軸（三色點）＋2×2 四色淡底格
    tl = ('<svg width="952" height="136" viewBox="0 0 952 136"><line x1="64" x2="888" y1="20" y2="20" stroke="#D6CFBD" stroke-width="4"/>'
          f'<circle cx="64" cy="20" r="14" fill="{G}"/><circle cx="476" cy="20" r="14" fill="{CO}"/><circle cx="888" cy="20" r="12" fill="{BG}" stroke="{MY}" stroke-width="4" stroke-dasharray="5 5"/>'
          + ''.join(f'<text x="{x}" y="84" text-anchor="{an}" class="num" {SVGF} font-size="36" font-weight="800" fill="{INK}">{a}</text><text x="{x}" y="124" text-anchor="{an}" {SVGF} font-size="28" font-weight="500" fill="{MU}">{b}</text>'
                    for x, an, a, b in ((64, "start", "02:00", "公布聲明"), (476, "middle", "02:30", "記者會"), (888, "end", "之後", "看反應"))) + '</svg>')
    def c4(n, t, s, tint, col): return (f'<div class="col" style="width:470px;height:288px;padding:32px;background:var(--{tint});border-radius:4px;border-top:6px solid {col}">'
                                        f'<span class="ser T1" style="color:{INK if col==MY else col};font-weight:700">0{n}</span><span class="T3b" style="margin-top:8px">{t}</span><span class="T4" style="color:var(--mu)">{s}</span></div>')
    p4 = (f'<div class="col" style="gap:16px"><div class="lab">時間軸</div>{tl}</div>'
          f'<div class="row" style="flex-wrap:wrap;width:952px;height:592px;align-content:space-between;justify-content:space-between">'
          + c4(1, "聲明措辭", "對通膨與就業的描述有沒有改", "tg", G) + c4(2, "投票結果", "有沒有人投反對票", "tc", CO)
          + c4(3, "02:30 記者會", "對 12 月的說法", "tb", BL) + c4(4, "本次沒有點陣圖", "不是經濟預測（SEP）會議", "tm", MY) + '</div>')
    # --- 5 三欄：每欄一色（珊瑚／藍／綠），圖示同色，淡底
    def col3(i, ic, t, s, col, tint): return (f'<div class="col" style="width:296px;height:408px;gap:8px;background:var(--{tint});border-top:6px solid {col};border-radius:4px;padding:24px 20px 0"><span class="ser T2" style="color:{col};font-weight:700">0{i}</span>'
                                              f'<div style="height:112px;margin-top:8px">{icon(ic, col, 96)}</div><span class="T3b">{t}</span><span class="T3" style="color:var(--mu)">{s}</span></div>')
    ar = f'<i style="border:16px solid transparent;border-top:24px solid var(--my);border-bottom:0"></i>'
    p5 = (f'<div class="col" style="gap:8px"><div class="row" style="height:96px;background:var(--gr);border-radius:4px;justify-content:center"><span class="T2" style="color:#fff">利率預期變動</span></div>'
          f'<div class="row" style="justify-content:space-between;height:48px;padding:0 140px">{ar}{ar}{ar}</div>'
          f'<div class="row" style="justify-content:space-between;align-items:flex-start;height:408px">' + ''.join(col3(i+1, *CH3[i]) for i in range(3)) + '</div></div>'
          f'<div class="col" style="gap:8px;border-top:2px solid var(--ln);padding-top:24px"><span class="T3b">收藏這張，明天凌晨公布後回來對照</span><span class="T4" style="color:var(--mu)">只說明傳導管道，不預測方向、非投資建議</span></div>')
    return [cover,
        page(LABEL, "FOMC 前夕 No.2", f'明天約{u("9 成")}預期持平；<br>12 月的定價則偏向升息', p2, 2, TOT, ASOF, BIB[0]),
        page(LABEL, "FOMC 前夕 No.3", f'利率現在在<br>{u("3.75～4.00%")}', p3, 3, TOT, ASOF, BIB[1]),
        page(LABEL, "FOMC 前夕 No.4", f'明天凌晨<br>看這{u(4)}件事', p4, 4, TOT, ASOF, BIB[2]),
        page(LABEL, "FOMC 前夕 No.5", f'利率預期變動時，<br>常被討論的{u(3)}個管道', p5, 5, TOT, ASOF, BIB[3])]
if __name__ == "__main__":
    out = Path(sys.argv[1]); render(css, build(), out)
    sheet(out, [f"{i}.jpg" for i in range(1, 6)], out/"sheet.jpg", 5, 400)
