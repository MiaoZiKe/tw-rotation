"""台積電 3Q26 法說解析 v2：封面＋5 張內頁（1080×1350）。用法：python render_earnings_v2.py <輸出資料夾>
數字沿用 ../earnings/plan.md 查證表。輸出 1.jpg（封面）～6.jpg。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "event_v2_lib"))
from lib import *
K, NAME, DATE, ASOF, TOT = "台股", "台積電 2330 法說", "3Q26", "資料日 2026-10-15", 6
def P(h, body, i, bib, bh=104): return page_in(K, NAME, DATE, h, body, i, TOT, ASOF, bib, bh)
def kpi(tint, ic, lab, v, unit, chip, cc="up"):
    return (f'<div class="blk" style="background:{TINT[tint]}"><div class="row"><div class="ic">{icon(ic, INK2, 54)}</div><div style="flex:1"><div class="lab">{lab}</div>'
            f'<div class="kv num">{v}<small>{unit}</small></div></div></div><span class="chip {cc}">{chip}</span></div>')
def bar(lb, v, mx, txt, col, tint="white"):
    return f'<div class="row" style="height:92px"><div class="lb">{lb}</div><div class="track"><div class="bar" style="width:{v/mx*100:.1f}%;background:{col}"></div></div><div class="val num" style="color:{col}">{txt}</div></div>'
pages = []
pages.append(page_cover(K, "semi", '台積電 Q3<br>每股賺 <span class="yy num">29.43</span> 元', '毛利率回落、第四季財測怎麼說？',
    '2026/10/15 法說會・公司公布數字整理', "10/15", -520))
pages.append(P('營收季增 <span class="y num">16.2%</span>，<br>每股賺 29.43 元',
    kpi("blue", "coin", "第三季營收（美元）", "467", "億", "季增 16.2%（約新台幣 1.49 兆）") +
    kpi("amber", "chart", "稅後純益（歸屬母公司）", "7,631", "億元", "年增 68.7%") +
    kpi("lilac", "target", "每股盈餘（EPS）", "29.43", "元", "稅後純益率 51.1%", "nt"), 2, "face_thumbs"))
pages.append(P('毛利率 <span class="y num">66.4%</span>，<br>較上季少 1.3 個百分點',
    f'<div class="blk" style="background:{TINT["blue"]}"><div class="lab">毛利率</div>' + bar("第二季", 67.7, 70, "67.7%", INK3) + bar("第三季", 66.4, 70, "66.4%", INK) +
    f'</div><div class="blk" style="background:{TINT["amber"]}"><div class="lab">營業利益率</div>' + bar("第三季", 58.7, 70, "58.7%", INK) +
    f'</div><div class="blk" style="background:{TINT["lilac"]}"><div class="lab">稅後純益率</div>' + bar("第三季", 51.1, 70, "51.1%", INK) +
    f'</div><div class="note">財務長說明：主因是 2 奈米量產初期的稀釋</div>', 3, "tilt"))
pages.append(P('第四季指引：美元營收<br><span class="y num">523～543</span> 億',
    '<table><tr><th>項目</th><th>公司指引</th><th>中間值</th></tr>'
    '<tr><td>美元營收</td><td class="n num">523～543 億</td><td class="num">533 億</td></tr>'
    '<tr><td>毛利率</td><td class="n num">65%～67%</td><td class="num">66%</td></tr>'
    '<tr><td>營業利益率</td><td class="n num">56.5%～58.5%</td><td class="num">57.5%</td></tr>'
    '<tr><td>匯率假設</td><td class="n num">31.8</td><td class="num">新台幣／美元</td></tr></table>'
    f'<div class="blk" style="background:{TINT["amber"]}"><div class="note">毛利率中間值較第三季再低約 0.4 個百分點；公司說明原因是 2 奈米爬坡與海外廠稀釋</div></div>', 4, "calendar"))
pages.append(P('全年資本支出<br>維持 <span class="y num">600～640</span> 億美元',
    kpi("blue", "factory", "第三季資本支出", "138", "億美元", "約新台幣 4,430 億元", "nt") +
    kpi("amber", "coin", "2026 全年資本支出指引", "600～640", "億美元", "與前次法說相同", "nt") +
    kpi("teal", "chip", "2 奈米占第三季晶圓營收", "8", "%", "全年美元營收成長指引約 44%", "nt"), 5, "growth"))
li = lambda n, c, t: f'<div class="blk" style="background:#fff"><div class="li"><div class="nb" style="background:{c}">{n}</div><div class="t">{t}</div></div></div>'
pages.append(P('管理層怎麼說？<br><span class="unit" style="font-size:34px">（報導摘述，非逐字）</span>',
    li(1, "#D63A22", "2026 全年美元營收成長指引上調至約 44%") + li(2, "#5145C8", "2026～2028 年資本支出，將比過去三年更顯著提高") +
    li(3, "#0A7F77", "AI 相關需求仍高於供給（報導摘述）") + li(4, "#1F5FB8", "海外廠稀釋：五年期間後段約 3～4 個百分點") +
    '<div class="unit">以上為公司說法的整理，不代表任何方向判斷</div>', 6, "face_think"))
if __name__ == "__main__":
    render(pages, sys.argv[1])
