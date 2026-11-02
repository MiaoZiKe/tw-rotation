"""第 1～2 週 6 篇草稿成圖（美術，2026-11-02）。頻道一用「1 陽光糖果」、頻道二用「3 瑞士極簡」（Andy 選定）。
用法：python render_drafts.py   輸出 <篇代號>/N.png、caption.txt 已另存；印出重疊檢查；產生 overview.png。
文字用 channel_playbook.md 第八節 8-4 草稿原文；頻道二薪資數字一律〔待填〕；沒有「示意・假資料」字樣。
"""
import sys, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "layouts_v2"))
import render_v2 as R
from playwright.sync_api import sync_playwright

T1, T2 = R.T1A, R.T2C
LOGO = (HERE.parent.parent.parent / "brand/tc_logo_1102/c1_開口圈/icon_light.svg").read_text(encoding="utf-8")
LOGO = LOGO.replace('width="512" height="512"', 'width="46" height="46" data-b style="flex:none"')

# ---------------- 頻道一元件 ----------------
def ft1(pk, right):
    return f'<div class="ft"><span data-meta>{T1["P"][pk]["label"]}</span><span data-meta>{right}</span></div>'

def band1(pk, pg, inner, pb=52):
    return f'<div class="band" style="padding-bottom:{pb}px">{R.hd1(T1, pk, pg)}{inner}</div>'

def arrow_pct(v, up):
    col = T1["rise"] if up else T1["fall"]; a = "▲" if up else "▼"
    return f'<span class="n" style="color:{col};white-space:nowrap">{a} {v}</span>'

def S1(pk, band, body, right):
    return (R.css1(T1, pk), f'{band}<div class="body" style="padding-top:36px;gap:26px;justify-content:space-evenly">{body}</div>{ft1(pk, right)}')

OUT = {}   # 篇代號 -> [(css, html)]

# ---------------- A 大跌後歷史怎麼走（熱點，3 張）----------------
P = T1["P"]["hot"]
A = []
A.append(S1("hot", band1("hot", "1 / 3", f'''
  <div class="deco" data-b style="top:176px">{R.svg_fall_chart(P, T1)}</div>
  <div class="kick" style="margin-top:40px">熱點解讀・歷史對照</div>
  <div class="h1" style="margin-top:12px">大跌完隔天<br>就會反彈？</div>
  <div class="card" style="margin-top:28px;display:inline-flex;align-items:center;gap:30px;padding:14px 44px 14px 40px;box-shadow:none">
    <span class="n" style="font-size:240px;line-height:1.02;color:{T1['ink']}">51%</span>
    <span style="font-size:42px;font-weight:800;line-height:1.3;color:{T1['ink2']}">1 週後<br>漲的比例</span></div>''', 56),
  f'''<div style="font-size:54px;font-weight:800;line-height:1.35">我翻了 2000 年以來的加權指數，<span class="acc">答案有點尷尬</span>…</div>
  <div><span class="btn">滑動看結果　→</span></div>''',
  "加權指數收盤價 2000～2026/10/30"))

def hrow(lab, pct, med, up, hi=False):
    fill = P["main"] if hi else P["mid"]
    return f'''<div style="display:flex;align-items:center;gap:16px;height:112px;border-top:2px solid {T1['line']}">
  <div style="width:200px;font-size:46px;font-weight:800">{lab}</div>
  <div style="width:96px;font-size:44px;font-weight:800" class="n">{pct}%</div>
  <div class="trk" style="flex:1;height:30px;border-radius:15px;background:{P['tint']}"><div class="fil" style="width:{pct}%;height:100%;border-radius:15px;background:{fill}"></div></div>
  <div style="width:190px;text-align:right;font-size:44px">{arrow_pct(med, up)}</div></div>'''
A.append(S1("hot", band1("hot", "2 / 3", '''
  <div class="kick" style="margin-top:36px">單日跌幅 ≥ 2.4%・共 63 次獨立事件</div>
  <div class="h2" style="font-size:72px;margin-top:10px">跌完之後，<br>漲的有幾成？</div>''', 50),
  f'''<div style="display:flex;gap:16px;font-size:32px;font-weight:700;color:{T1['ink3']};padding:0 0 0 0"><div style="width:216px">跌完之後</div><div style="flex:1">上漲比例</div><div style="width:190px;text-align:right">中位數</div></div>
  <div class="card box" style="padding:6px 32px 10px">
    {hrow("1 週後",51,"+0.2%",True)}{hrow("1 個月後",55,"+0.4%",True)}{hrow("3 個月後",63,"+4.0%",True,True)}
    <div style="display:flex;align-items:center;gap:16px;height:112px;border-top:2px solid {T1['line']}">
      <div style="flex:1;font-size:40px;font-weight:800;line-height:1.3">最慘一次，<br>3 個月後還再跌</div>
      <div style="font-size:64px" class="n">{arrow_pct("27.7%", False)}</div></div></div>
  <div style="font-size:34px;font-weight:500;color:{T1['ink2']};line-height:1.45">連續幾天算同一次。歷史統計，不代表未來；不含息。</div>''',
  "收盤價 2000～2026/10/30・非投資建議"))

A.append(S1("hot", band1("hot", "3 / 3", '''
  <div class="kick" style="margin-top:36px">現在在哪裡</div>
  <div class="h2" style="font-size:68px;margin-top:10px">短期幾乎是丟銅板，<br>拉長才偏正</div>''', 50),
  f'''<div class="card box" style="padding:26px 32px;display:flex;align-items:center;gap:20px">
    <div style="flex:1"><div style="font-size:34px;font-weight:700;color:{T1['ink3']}">10/6 收盤</div><div class="n" style="font-size:72px">49,822</div></div>
    <div class="n" style="font-size:64px;color:{T1['ink3']}">→</div>
    <div style="flex:1"><div style="font-size:34px;font-weight:700;color:{T1['ink3']}">10/30 收盤</div><div class="n" style="font-size:72px">45,212</div></div></div>
  <div style="display:flex;align-items:center;gap:18px"><span class="n" style="font-size:96px;color:{T1['fall']}">▼ 9.3%</span><span style="font-size:36px;font-weight:700;line-height:1.3;color:{T1['ink2']}">離高點回落<br>（收盤價）</span></div>
  <div style="font-size:42px;font-weight:700;line-height:1.4">但「偏正」不等於「一定」。</div>
  <div style="font-size:54px;font-weight:800;line-height:1.35">你是在<span class="acc">等止跌訊號</span>，還是<span class="acc">根本不敢看盤</span>？</div>
  <div style="font-size:32px;font-weight:600;color:{T1["ink3"]}">〔待更新為最新收盤〕</div>''',
  "加權指數收盤價・非投資建議"))
OUT["A"] = A

# ---------------- B 配息不等於賺（ETF，4 張）----------------
P = T1["P"]["etf"]
B = []
B.append(S1("etf", band1("etf", "1 / 4", '''
  <div class="kick" style="margin-top:40px">ETF・配息</div>
  <div class="h1" style="margin-top:12px">配息率 10%<br>≠ 你賺 10%</div>''', 60),
  f'''<div class="card box" style="padding:30px 36px;display:flex;align-items:center;gap:24px;box-shadow:none;border:4px solid {P['main']}">
    <div style="flex:1;font-size:58px;font-weight:900;line-height:1.3">除息那天，<br>淨值也少了<span class="acc">同樣的錢</span>！</div>
    <div data-b>{R.svg_coins(P, T1, 150)}</div></div>
  <div><span class="btn">滑動看算式　→</span></div>''',
  "公開資料整理・非投資建議"))

def stepcard(lab, big, sub, hi=False):
    bd = f"border:4px solid {P['main']};" if hi else ""
    return f'''<div class="card box" style="flex:1;padding:24px 20px;{bd}display:flex;flex-direction:column;align-items:center;gap:6px">
    <div style="font-size:34px;font-weight:700;color:{T1['ink3']}">{lab}</div><div class="n" style="font-size:80px">{big}</div><div style="font-size:34px;font-weight:600;color:{T1['ink2']}">{sub}</div></div>'''
B.append(S1("etf", band1("etf", "2 / 4", '''
  <div class="kick" style="margin-top:36px">舉例・假設數字，非任何一檔</div>
  <div class="h2" style="font-size:72px;margin-top:10px">除息那天，<br>發生什麼事？</div>''', 50),
  f'''<div style="display:flex;align-items:center;gap:14px">{stepcard("除息前 淨值","10 元","配 0.5 元")}<div class="n" style="font-size:60px;color:{T1['ink3']}">→</div>{stepcard("除息後 淨值","約 9.5 元","少了 0.5 元",True)}</div>
  <div class="card box" style="padding:24px 32px;display:flex;flex-direction:column;gap:10px">
    <div style="display:flex;justify-content:space-between;align-items:center;font-size:48px;font-weight:800"><span>你的口袋</span>{arrow_pct("多 0.5", True)}</div>
    <div style="display:flex;justify-content:space-between;align-items:center;font-size:48px;font-weight:800;border-top:2px solid {T1['line']};padding-top:12px"><span>你的帳面</span>{arrow_pct("少 0.5", False)}</div></div>
  <div style="font-size:42px;font-weight:800;line-height:1.4">口袋多 0.5，帳面少 0.5。</div>''',
  "假設數字・非任何一檔"))

def numcard(no, t, d):
    return f'''<div class="card box" style="padding:28px 32px;display:flex;gap:24px;align-items:center">
    <div class="n rk" style="width:80px;height:80px;border-radius:50%;background:{P['main']};color:#fff;font-size:44px;display:flex;align-items:center;justify-content:center;flex:none">{no}</div>
    <div><div style="font-size:50px;font-weight:900;line-height:1.25">{t}</div><div style="font-size:36px;color:{T1['ink2']};line-height:1.4;margin-top:6px">{d}</div></div></div>'''
B.append(S1("etf", band1("etf", "3 / 4", '''
  <div class="kick" style="margin-top:36px">真正有沒有賺</div>
  <div class="h2" style="font-size:72px;margin-top:10px">要看兩件事</div>''', 50),
  f'''{numcard("1","之後有沒有填息","淨值回到配息前")}{numcard("2","含息總報酬","不是配息率")}
  <div style="font-size:40px;font-weight:700;line-height:1.45;color:{T1['ink2']}">配息率只告訴你「領了多少」，<br>不告訴你「帳面少了多少」。</div>''',
  "公開資料整理・非投資建議"))

B.append(S1("etf", band1("etf", "4 / 4", '''
  <div class="kick" style="margin-top:36px">還有一個容易搞混的</div>
  <div class="h2" style="font-size:66px;margin-top:10px">年化配息率，<br>不是你領到的錢</div>''', 50),
  f'''<div class="card box" style="padding:26px 32px;font-size:40px;line-height:1.5;font-weight:600">年化配息率是用<span class="acc" style="font-weight:800">「最近一次配息」</span>乘上去算的，不是這一年真的領到的錢。</div>
  <div class="card box" style="padding:26px 32px;font-size:40px;line-height:1.5;font-weight:600">配息來源也可能含<span class="acc" style="font-weight:800">本金或收益平準金</span>，以投信公告為準。</div>
  <div style="font-size:52px;font-weight:800;line-height:1.35">買主動式或高配息 ETF 前，你會先看<span class="acc">配息率</span>，還是<span class="acc">含息總報酬</span>？</div>''',
  "公開資料整理・非投資建議"))
OUT["B"] = B

# ---------------- C 大跌那天錢是跑掉還是換位置（輪動，3 張）----------------
P = T1["P"]["rot"]
C = []
C.append(S1("rot", band1("rot", "1 / 3", f'''
  <div class="deco" data-b style="top:176px">{R.svg_cycle(P, T1, 176)}</div>
  <div class="kick" style="margin-top:40px">產業輪動・10/30</div>
  <div class="h1" style="margin-top:12px;font-size:100px">大跌那天，<br>錢是跑掉了，<br>還是換位置？</div>''', 60),
  f'''<div style="font-size:50px;font-weight:800;line-height:1.4">「跌」跟「錢有沒有離開」，<br><span class="acc">是兩回事</span>。</div>
  <div><span class="btn">滑動看怎麼看　→</span></div>''',
  "公開資料整理・非投資建議"))

def stat(lab, big, col, sub):
    return f'''<div class="card box" style="flex:1;padding:22px 10px;display:flex;flex-direction:column;align-items:center;gap:4px">
    <div style="font-size:34px;font-weight:700;color:{T1['ink3']}">{lab}</div><div class="n" style="font-size:84px;color:{col};white-space:nowrap">{big}</div><div style="font-size:32px;font-weight:600;color:{T1['ink2']}">{sub}</div></div>'''
C.append(S1("rot", band1("rot", "2 / 3", '''
  <div class="kick" style="margin-top:36px">10/30 盤中・83 個族群</div>
  <div class="h2" style="font-size:72px;margin-top:10px">8 個上漲，<br>75 個下跌</div>''', 50),
  f'''<div style="display:flex;gap:14px">{stat("上漲","▲ 8",T1['rise'],"個族群")}{stat("下跌","▼ 75",T1['fall'],"個族群")}{stat("平均","−3.80%",T1['fall'],"全族群")}</div>
  <div style="font-size:32px;font-weight:600;color:{T1["ink3"]}">〔待核對：改成收盤版〕</div>
  <div style="font-size:48px;font-weight:800;line-height:1.4">但「跌」跟「錢有沒有離開」是兩回事，要一起看三件事。</div>''',
  "10/30 盤中資料・公開資料整理"))

def ph1(t): return f'<span style="display:inline-block;border:3px dashed {P["main"]};background:{P["tint"]};color:{P["deep"]};border-radius:12px;padding:2px 16px;font-weight:800;white-space:nowrap">{t}</span>'
def lrow(t, hint):
    return f'''<div class="card box" style="padding:22px 30px;display:flex;flex-direction:column;gap:8px"><div style="font-size:46px;font-weight:900">{t}</div><div style="font-size:36px;color:{T1['ink2']}">{ph1(hint)}</div></div>'''
C.append(S1("rot", band1("rot", "3 / 3", '''
  <div class="kick" style="margin-top:36px">要一起看的三件事</div>
  <div class="h2" style="font-size:70px;margin-top:10px">錢停在哪層樓</div>''', 50),
  f'''{lrow("成交比重","〔待填：比重增加最多的族群＋日期〕")}{lrow("逆勢收紅","〔待填：族群名稱，不放個股〕")}{lrow("連續流入","〔待填：連續 N 日比重上升的環節〕")}
  <div style="font-size:34px;font-weight:600;color:{T1['ink2']};line-height:1.4">這是在描述過去幾天錢停在哪層樓，不是在預告下一個會是誰。</div>
  <div style="font-size:50px;font-weight:800;line-height:1.35">下一篇想看<span class="acc">散熱這一段</span>，還是<span class="acc">載板那一段</span>？</div>''',
  "公開資料整理・非投資建議"))
OUT["C"] = C

# ---------------- 頻道二元件（瑞士極簡）----------------
def top2(pg, label):
    return f'<div class="top">{LOGO}<div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'
def ft2(left="科技透明圈"):
    return f'<div class="ft"><span data-meta>{left}</span><span data-meta>科技透明圈</span></div>'
def ph2(s, fs=40): return f'<span class="ph" style="font-size:{fs}px">{s}</span>'
def S2(pg, label, body, left, pad="52px 64px 0"):
    return (R.css2(T2), f'{top2(pg, label)}<div class="body" style="padding:{pad};justify-content:space-evenly">{body}</div>{ft2(left)}')
RED = T2["acc"]

D = []
D.append(S2("1 / 3", "公司待遇行情", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">公司待遇行情</span><span class="tag g">網友回報，非公司公告</span></div>
  <div class="cofield" style="margin-top:34px"><span class="cotext" style="font-size:150px;font-weight:900;line-height:1.2">聯發科</span></div>
  <div style="font-size:150px;font-weight:900;line-height:1.2;margin-top:6px">行情分享</div>
  <div style="margin-top:40px;display:flex;border-top:3px solid {T2['ink']};border-bottom:2px solid {T2['line']}">
    <div style="flex:1;padding:18px 24px 18px 0"><div class="lab">回報人數</div><div style="margin-top:8px">{ph2("〔待填〕 位",42)}</div></div>
    <div style="flex:1;padding:18px 24px;border-left:2px solid {T2['line']}"><div class="lab">回報年份</div><div style="margin-top:8px">{ph2("〔待填〕",42)}</div></div>
    <div style="flex:1;padding:18px 24px;border-left:2px solid {T2['line']}"><div class="lab">圈內俗稱</div><div style="margin-top:8px">{ph2("〔待填〕",42)}</div></div></div>
  <div class="box callout" style="margin-top:40px;display:flex;align-items:center;gap:30px;padding:26px 34px">
    <div style="font-size:46px;font-weight:800;line-height:1.2">碩畢<br>月薪</div>
    <div class="n" style="font-size:80px;line-height:1;color:{T2['accdeep']}">〔待填〕K</div></div>
  <div style="margin-top:34px;font-size:38px;font-weight:600;color:{T2['ink2']}">朋友提供，有誤請指正</div>''',
  "網友回報，非公司公告；有誤請指正"))

def frow(i, nm, hint):
    return (f'<div style="display:flex;align-items:center;min-height:118px;border-top:2px solid {T2["line"]};padding:10px 0">'
            f'<div class="n" style="width:78px;padding-left:12px;font-size:32px;color:{T2["accdeep"]}">{i:02d}</div>'
            f'<div style="width:262px;font-size:42px;font-weight:800;white-space:nowrap">{nm}</div><div style="flex:1">{ph2(hint,34)}</div></div>')
D.append(S2("2 / 3", "公司待遇行情", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">欄位一覽</span><span class="tag g">區間供參考，N 位回報</span></div>
  <div style="font-size:70px;font-weight:900;line-height:1.2;margin-top:24px">聯發科 五個欄位</div>
  <div style="font-size:34px;font-weight:600;color:{T2['ink2']};line-height:1.4;margin-top:10px">非主管平均薪資連年在證交所公開榜單前段 {ph2("〔待核對：年度・數字・口徑〕",32)}</div>
  <div class="box" style="margin-top:24px;padding:0">
    {frow(1,"總部地點","〔待填〕")}{frow(2,"碩畢薪資","〔待填：月薪區間・N 位・年份〕")}{frow(3,"分紅發放","〔待填：月份・整包約幾個月〕")}{frow(4,"加班狀況","〔待填：網友普遍回報〕")}{frow(5,"出差需求","〔待填〕")}</div>
  <div style="margin-top:18px;font-size:36px;font-weight:700;color:{T2['ink2']}">以上隨部門、年資差很多。</div>''',
  "網友回報，非公司公告；有誤請指正"))

D.append(S2("3 / 3", "公司待遇行情", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">順便分享</span><span class="tag g">面談經驗</span></div>
  <div style="font-size:78px;font-weight:900;line-height:1.25;margin-top:30px">面談經驗，<br>只講題型方向</div>
  <div class="box callout" style="margin-top:40px;padding:30px 34px;font-size:42px;font-weight:700;line-height:1.5">{ph2("〔待 Andy 填：2～3 個題型〕",40)}</div>
  <div style="margin-top:auto;margin-bottom:46px;border-top:3px solid {T2['ink']};padding-top:30px;font-size:62px;font-weight:900;line-height:1.3">你那一組的行情是多少，<br>或你覺得<span style="color:{T2['accdeep']}">誰的差最多</span>？</div>''',
  "網友回報，非公司公告；有誤請指正"))
OUT["D"] = D

E = []
E.append(S2("1 / 3", "面試・職涯", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">面試・職涯</span><span class="tag g">期望薪資</span></div>
  <div style="display:flex;align-items:center;gap:26px;margin-top:50px"><div class="n qb">Q</div><div style="font-size:38px;font-weight:700;color:{T2['ink3']};letter-spacing:.1em">面試官問</div></div>
  <div style="font-size:104px;font-weight:900;line-height:1.2;margin-top:30px">期望薪資<br>多少？</div>
  <div style="font-size:40px;font-weight:700;color:{T2['ink3']};margin-top:44px">最不該回的一句是</div>
  <div style="font-size:82px;font-weight:900;line-height:1.25;color:{T2['accdeep']};margin-top:10px;border-bottom:6px solid {RED};display:inline-block;align-self:flex-start">「依公司規定就好」</div>''',
  "科技透明圈"))
def step2(no, t, d):
    return (f'<div style="display:flex;gap:26px;align-items:flex-start;border-top:3px solid {T2["ink"]};padding:26px 0 24px">'
            f'<div class="n" style="font-size:72px;line-height:1;color:{RED};width:76px;flex:none">{no}</div>'
            f'<div><div style="font-size:50px;font-weight:900;line-height:1.25">{t}</div><div style="font-size:36px;color:{T2["ink2"]};line-height:1.45;margin-top:8px">{d}</div></div></div>')
E.append(S2("2 / 3", "面試・職涯", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">答題框架</span><span class="tag g">三步</span></div>
  <div style="font-size:70px;font-weight:900;line-height:1.2;margin-top:24px">比較穩的三步</div>
  <div style="margin-top:20px;border-bottom:2px solid {T2['line']}">
   {step2("1","先查行情","公開的證交所非主管薪資、同職缺的徵才區間，抓一個範圍")}
   {step2("2","回答給區間，不給單點","「依經驗和行情，期待在 X 到 Y，實際看整包（含分紅）和職責」")}
   {step2("3","把分紅算進去再談","底薪一樣，整包可以差好幾個月")}</div>''',
  "科技透明圈"))
E.append(S2("3 / 3", "面試・職涯", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">我的經驗</span></div>
  <div class="box callout" style="margin-top:30px;padding:30px 34px;font-size:42px;font-weight:700;line-height:1.6">我第一次面試就是直接報了最低的那個數字…<br>{ph2("〔待 Andy 填：真實經驗一句；沒有就整張刪，不要編〕",32)}</div>
  <div style="margin-top:50px;font-size:66px;font-weight:900;line-height:1.3">你被問到期望薪資的時候，是報<span style="color:{T2['accdeep']}">單點</span>還是報<span style="color:{T2['accdeep']}">區間</span>？</div>
  <div style="display:flex;gap:20px;margin-top:40px">
    <div style="flex:1;border:3px solid {T2['ink']};padding:28px 0;text-align:center;font-size:60px;font-weight:900">單點</div>
    <div style="flex:1;border:3px solid {RED};padding:28px 0;text-align:center;font-size:60px;font-weight:900;color:{T2['accdeep']}">區間</div></div>''',
  "科技透明圈"))
OUT["E"] = E

F = []
F.append(S2("1 / 3", "分紅怎麼看", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">分紅怎麼看</span><span class="tag g">舉例・假設數字，非任何公司</span></div>
  <div style="font-size:70px;font-weight:900;line-height:1.3;margin-top:34px">分紅寫「整包 20 個月」，<br>不等於你的年薪是 20 個月！</div>
  <div style="border-top:3px solid {T2['ink']};margin-top:40px;padding-top:20px;display:flex;align-items:baseline;gap:24px"><span class="n" style="font-size:230px;line-height:1.05;color:{RED}">72</span><span style="font-size:96px;font-weight:900">萬</span></div>
  <div style="font-size:48px;font-weight:800;line-height:1.4;margin-top:8px">同樣是「20」，差了 72 萬。<br>差的只有兩個字：<span style="color:{T2['accdeep']}">整包，還是額外</span>。</div>''',
  "舉例：月薪 6 萬，假設數字"))
def calc(lab, formula, total, note, hi=False):
    bd = f"border-left:12px solid {RED};" if hi else f"border-left:12px solid {T2['ink']};"
    return (f'<div class="box" style="{bd}padding:24px 30px;margin-top:22px"><div style="font-size:46px;font-weight:900">{lab}</div>'
            f'<div style="font-size:36px;color:{T2["ink2"]};margin-top:4px;line-height:1.4">{note}</div>'
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;margin-top:10px"><span class="n" style="font-size:40px;color:{T2["ink2"]}">{formula}</span>'
            f'<span class="n" style="font-size:84px;color:{RED if hi else T2["ink"]};white-space:nowrap">{total}</span></div></div>')
F.append(S2("2 / 3", "分紅怎麼看", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">算給你看</span><span class="tag g">月薪 6 萬・假設數字</span></div>
  <div style="font-size:66px;font-weight:900;line-height:1.2;margin-top:24px">同樣是「20」</div>
  {calc("整包 20 個月","6 × 20","120 萬","通常指含底薪的年度總額")}
  {calc("額外分紅 20 個月","72 萬底薪 ＋ 120 萬","192 萬","底薪 12 個月再加 20 個月分紅",True)}
  <div style="margin-top:26px">{ph2("〔待 Andy 確認：你們圈子慣用的「整包」定義〕",32)}</div>''',
  "舉例：月薪 6 萬，假設數字，非任何公司"))
def q3(no, t):
    return (f'<div style="display:flex;gap:26px;align-items:center;border-top:3px solid {T2["ink"]};padding:26px 0"><div class="n" style="font-size:64px;color:{RED};width:70px">{no}</div>'
            f'<div style="font-size:56px;font-weight:900">{t}</div></div>')
F.append(S2("3 / 3", "分紅怎麼看", f'''
  <div style="display:flex;gap:14px;align-items:center"><span class="tag">拿到 offer</span></div>
  <div style="font-size:70px;font-weight:900;line-height:1.2;margin-top:24px">先問三件事</div>
  <div style="margin-top:20px;border-bottom:2px solid {T2['line']}">{q3("1","是現金還是股票？")}{q3("2","什麼月份發？")}{q3("3","有沒有歸屬年限？")}</div>
  <div style="margin-top:50px;font-size:60px;font-weight:900;line-height:1.3">你拿到 offer 時，對方講的是<span style="color:{T2['accdeep']}">「整包」</span>還是<span style="color:{T2['accdeep']}">「額外」</span>？</div>''',
  "科技透明圈"))
OUT["F"] = F

# ---------------- 轉圖與檢查 ----------------
def main():
    total = 0; n = 0; files = {}
    with sync_playwright() as p:
        br = R.launch(p); pg = br.new_page(viewport={"width": R.W, "height": R.H}, device_scale_factor=1)
        for code, slides in OUT.items():
            (HERE / code).mkdir(exist_ok=True)
            for i, (css, body) in enumerate(slides, 1):
                f = R.TMP / "_d.html"; f.write_text(R.page_html(css, body), encoding="utf-8")
                pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
                r = pg.evaluate(R.CHECK_JS); path = HERE / code / f"{i}.png"
                pg.screenshot(path=str(path)); files.setdefault(code, []).append(path)
                iss = sum(len(r[k]) for k in ("overlap", "bounds", "small", "overflow", "textBlock", "clip")); total += iss; n += 1
                print(f"{code}{i}  文字塊 {r['n']:3d}  問題 {iss}")
                for k in ("overlap", "bounds", "small", "overflow", "textBlock", "clip"):
                    for x in r[k]: print("    ", k, x)
        br.close()
    print(f"重疊檢查：程式 {n} 張 {total} 筆")
    return files

if __name__ == "__main__":
    main()
