"""ETF 每週一檔 v2（0050 最壞情境回測）：封面＋7 張內頁。數字沿用 ../etf/etf_0050_snapshot.json 與 ../etf/plan.md，不重算口徑。
用法：python render_etf_v2.py <輸出資料夾>   輸出 1.jpg（封面）～8.jpg"""
import sys, json, math, datetime as D
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "event_v2_lib"))
from lib import *
E_ = json.load(open(Path(__file__).resolve().parents[1] / "etf" / "etf_0050_snapshot.json")); X = E_["series"]["0050"]
dd, P_, TR = X["d"], X["p"], X["t"]; N = len(dd); asof = E_["asof"]
Y = lambda a, b: (D.date.fromisoformat(dd[b]) - D.date.fromisoformat(dd[a])).days / 365.25
def peak(lo, hi): return max((k for k in range(N) if lo <= dd[k] <= hi), key=lambda k: P_[k])
def stats(i):
    rp = next(j for j in range(i+1, N) if P_[j] > P_[i]); rt = next(j for j in range(i+1, N) if TR[j] > TR[i]); lo = min(range(i, N), key=lambda j: TR[j]); hz = {}
    for h in (1, 3, 5, 10):
        j = next((j for j in range(i, N) if Y(i, j) >= h), None)
        if j: hz[h] = (round((TR[j]/TR[i]-1)*100, 1), round((P_[j]/P_[i]-1)*100, 1))
    return dict(i=i, rp=rp, rt=rt, lo=lo, dd=round((TR[lo]/TR[i]-1)*100, 1), yp=round(Y(i, rp), 1), yt=round(Y(i, rt), 1), hz=hz,
                now_tr=TR[-1]/TR[i], now_p=P_[-1]/P_[i], yrs=Y(i, N-1), ann=((TR[-1]/TR[i])**(1/Y(i, N-1))-1)*100)
A = stats(peak("2007-01-01", "2008-03-01")); B = stats(peak("2021-01-01", "2022-03-01")); hz = A["hz"]
d = lambda i: dd[i].replace("-", "/")
K, NAME, DATE, ASOF, TOT = "ETF", "0050 每週一檔", "歷史回測", f"資料日 {asof}", 8
def Pg(h, body, i, bib, bh=104): return page_in(K, NAME, DATE, h, body, i, TOT, ASOF, bib, bh)
def chart():
    i0 = A["i"]; W, H, L, R, Tp, Bt = 968, 660, 92, 16, 16, 44; lo, hi = 30, 1200
    fx = lambda k: L + (k-i0)/(N-1-i0)*(W-L-R); fy = lambda v: Tp + (math.log(hi)-math.log(v))/(math.log(hi)-math.log(lo))*(H-Tp-Bt)
    pl = lambda arr, col, w: f'<polyline fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" points="' + " ".join(f"{fx(k):.1f},{fy(100*arr[k]/arr[i0]):.1f}" for k in range(i0, N)) + '"/>'
    g = "".join(f'<line x1="{L}" x2="{W-R}" y1="{fy(v):.1f}" y2="{fy(v):.1f}" stroke="#D5DDE4" stroke-width="1.5"/><text x="{L-12}" y="{fy(v)+9:.1f}" text-anchor="end" font-size="26" font-weight="700" fill="{INK3}" class="num">{v}</text>' for v in (50, 100, 300, 1000))
    xl = "".join(f'<text x="{fx(next(k for k in range(N) if dd[k]>=f"{y}-01-01")):.1f}" y="{H-10}" text-anchor="middle" font-size="26" font-weight="700" fill="{INK3}" class="num">{y}</text>' for y in (2010, 2015, 2020, 2025))
    lo_k, rt = A["lo"], A["rt"]; ly = fy(100*TR[lo_k]/TR[i0])
    mk = (f'<circle cx="{fx(i0):.1f}" cy="{fy(100):.1f}" r="11" fill="{YEL}" stroke="{INK}" stroke-width="3"/><circle cx="{fx(lo_k):.1f}" cy="{ly:.1f}" r="11" fill="{FALL}" stroke="#fff" stroke-width="3"/><circle cx="{fx(rt):.1f}" cy="{fy(100):.1f}" r="11" fill="{RISE}" stroke="#fff" stroke-width="3"/>')
    lab = (f'<text x="{fx(i0)+20:.1f}" y="{fy(100)-26:.1f}" font-size="30" font-weight="800" fill="{INK}">買在高點</text>'
           f'<text x="{fx(lo_k)+22:.1f}" y="{ly+8:.1f}" font-size="30" font-weight="800" fill="{FALL}">最低 {A["dd"]:+.1f}%</text>'
           f'<text x="{fx(rt)+26:.1f}" y="{fy(100)+56:.1f}" font-size="30" font-weight="800" fill="{RISE}">含息回本</text>')
    return f'<svg class="ch" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{g}{xl}{pl(P_,"#8AA3B5",5)}{pl(TR,RISE,7)}{mk}{lab}</svg>'
def bar(lb, v, mx, txt, col):
    return f'<div class="row" style="flex:1;min-height:110px"><div class="lb">{lb}</div><div class="track" style="height:52px"><div class="bar" style="width:{abs(v)/mx*100:.1f}%;background:{col}"></div></div><div class="val num" style="color:{col}">{txt}</div></div>'
def kpi(tint, ic, lab, v, unit, chip="", cc="nt", vc=""):
    return (f'<div class="blk" style="background:{TINT[tint]}"><div class="row"><div class="ic">{icon(ic, INK2, 54)}</div><div style="flex:1"><div class="lab">{lab}</div>'
            f'<div class="kv num {vc}">{v}<small>{unit}</small></div></div></div>' + (f'<span class="chip {cc}">{chip}</span>' if chip else '') + '</div>')
sg = lambda v: f'{v:+.1f}%'.replace("-", "−")
pages = []
pages.append(page_cover(K, "etf", '買在 0050 最高點<br>含息 <span class="yy num">' + str(A["yt"]) + '</span> 年才回本', '最慘賠多少？撐到今天又剩多少？',
    f'2007/10 一次投入 100 萬・歷史回測，非預測', "10/28", -430))
pages.append(Pg(f'2007 年買在高點，<br>走了 <span class="y num">19</span> 年',
    f'<div class="blk" style="background:#fff;padding:24px 0 14px 0;align-items:center;flex:none">{chart()}</div><div class="note">假設 {d(A["i"])} 一次投入 <b>100 萬</b>、不加碼不賣出</div><div class="unit">紅線＝含息再投入　灰線＝只看價格　縱軸對數，買點＝100</div>', 2, "calendar"))
pages.append(Pg(f'最痛的時候：<span class="y num">{sg(A["dd"])}</span>',
    f'<div class="blk" style="background:{TINT["blue"]}"><div class="lab">{d(A["lo"])}　含息再投入</div><div class="kv num dn" style="font-size:150px">{sg(A["dd"])}</div></div>'
    + kpi("amber", "coin", "100 萬剩下", f'{round(100*(1+A["dd"]/100))}', "萬", "約剩四成多") + kpi("lilac", "down", "買進後第 1 年", sg(hz[1][0]), "", "第一年就大幅回檔", "dn", "dn"), 3, "face_shock"))
pages.append(Pg('含息報酬，隨持有年數<br>怎麼走', f'<div class="blk" style="background:{TINT["blue"]}">' + "".join(bar(f"{h} 年", hz[h][0], 60, sg(hz[h][0]), RISE if hz[h][0] >= 0 else FALL) for h in (1, 3, 5, 10)) + '</div><div class="unit">買進後第 N 年的累計報酬（含息再投入）</div>', 4, "face_relief"))
pages.append(Pg(f'回到買點，要等 <span class="y num">{A["yt"]}</span> 年<br>（只看價 {A["yp"]} 年）',
    f'<div class="blk" style="background:{TINT["amber"]}">' + bar("含息", A["yt"], 8, f'{A["yt"]} 年', INK) + bar("只看價", A["yp"], 8, f'{A["yp"]} 年', INK3) + '</div>'
    f'<div class="blk s" style="background:{TINT["teal"]}"><div class="row"><div class="ic">{icon("cal", INK2, 54)}</div><div class="note">含息回本：{d(A["rt"])}<br>只看價回本：{d(A["rp"])}</div></div></div>', 5, "clock"))
pages.append(Pg(f'撐到今天，約 <span class="y num">{A["now_tr"]*100:,.0f}</span> 萬',
    '<div class="two">' + kpi("blue", "chart", "含息", f'{A["now_tr"]*100:,.0f}', "萬", f'約 {A["now_tr"]:.1f} 倍', "up", "up").replace('<div class="row">', '<div class="row" style="flex-direction:column;align-items:flex-start;gap:10px">', 1) +
    kpi("lilac", "chart", "只看價", f'{A["now_p"]*100:,.0f}', "萬", f'約 {A["now_p"]:.1f} 倍', "up").replace('<div class="row">', '<div class="row" style="flex-direction:column;align-items:flex-start;gap:10px">', 1) + '</div>'
    f'<div class="blk s" style="background:{TINT["amber"]}"><div class="note">投入 100 萬、持有約 {A["yrs"]:.0f} 年，年化約 <b>{A["ann"]:.1f}%</b>（含息）</div></div><div class="unit">未扣交易費與稅；配息假設全數再投入　資料到 {asof[:4]}/{asof[5:7]}</div>', 6, "growth"))
pages.append(Pg('換成 2022 年高點，<br>結果差很多', '<div class="two">' + kpi("blue", "down", "最深回檔", sg(B["dd"]), "", "當年高點買進", "nt", "dn").replace('<div class="row">', '<div class="row" style="flex-direction:column;align-items:flex-start;gap:10px">', 1) +
    kpi("amber", "clock", "含息回本", f'{B["yt"]}', "年", "只看價 " + str(B["yp"]) + " 年").replace('<div class="row">', '<div class="row" style="flex-direction:column;align-items:flex-start;gap:10px">', 1) + '</div>'
    f'<div class="blk s" style="background:{TINT["lilac"]}"><div class="note">{d(B["i"])} 買在當時高點<br>對照：2007 年 {sg(A["dd"])}、{A["yt"]} 年</div></div>', 7, "face_thumbs"))
pages.append(Pg(f'跌 <span class="y num">{abs(A["dd"]):.0f}%</span>，你撐得住嗎？',
    f'<div class="blk" style="background:{TINT["blue"]}"><div class="row"><div class="note" style="font-size:48px;flex:1">回測只是在說「過去發生過什麼」。<br><br>想一想：自己能接受最深回檔多少、等多久？</div>{bibi("tilt", 330)}</div></div>'
    f'<div class="blk s" style="background:#fff"><div class="unit">過去績效不代表未來。本內容為歷史資料情境說明，不構成投資建議。</div></div>', 8, None))
if __name__ == "__main__":
    print("A", A["dd"], A["yt"], A["yp"], round(A["now_tr"]*100), "B", B["dd"], B["yt"])
    render(pages, sys.argv[1])
