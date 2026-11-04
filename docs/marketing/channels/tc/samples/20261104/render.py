"""頻道二（科技透明圈）範例貼文圖：瑞士極簡版型＋CC 實景照。1080x1350。
用法：python render.py [編號…]   → 01/02/03/04 各輸出（可只指定部分編號）：image.png＝封面（公司／類別實景照＋頻道 LOGO），image2.png＝第 2 張（圖解／重點），並印出「重疊檢查」。
色票：白 #FFFFFF／黑 #111111／瑞士紅 #D4231A／灰 #595959／細線 #CFCFCF／淡灰面 #EFEFEF。
字型：Noto Sans TC（OFL；可變字重 TTF 路徑由環境變數 TC_FONT 指定，預設 /tmp/.../font/NotoSansTC.ttf；
      取得：raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC[wght].ttf，12MB 不進 repo）。
"""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5] / "social" / "photo_lib"
LIB = ROOT / "_category"
POSTS = [
 dict(n="01", no="01", kicker="供應鏈讀書筆記｜先進封裝", photo=ROOT/"tsmc"/"photo_19.jpg", pos="50% 50%", cover="photo_19", sub="台積電 2026-10-15 法說會", hint="往右滑看重點 →", foot="與各公司無合作或授權關係。CoWoS 為台積電之商標。",
      ccredit="圖：台積電官方（官網 TSMC Fabs 頁）。廠區大樓實景，非先進封裝產線。",
      title="晶片做完還不能出貨<br>AI 的瓶頸在「封裝」",
      fact="2026-10-15 台積電法說會：董事長魏哲家表示，5 倍光罩尺寸的先進封裝目前只有台積電能提供，CoWoS 仍是客戶最優先的選擇。",
      steps=[("晶圓廠","製造運算晶片"),("記憶體廠","製造 HBM 堆疊"),("封裝廠","以 CoWoS 接在同一片矽中介層"),("伺服器廠","組成機櫃出貨")],
      credit="圖：Mister rf／CC BY-SA 4.0／Wikimedia Commons。早期 ROM 晶片打線封裝，示意「晶片要裝進封裝」，非 CoWoS。",
      src="出處：台積電 2026 第三季法說會（2026-10-15）"),
 dict(n="02", no="02", kicker="供應鏈讀書筆記｜HBM 記憶體", photo=None, cover_photo=ROOT/"sk_hynix"/"photo_6.jpg", pos="50% 50%", sub="SK hynix 2026-10-28 第三季財報", hint="往右滑看圖解 →", foot="與各公司無合作或授權關係。",
      ccredit="圖：ITEagle Europe - Sebastiaan Broekhoven／CC BY-SA 4.0／Wikimedia Commons。SK hynix DDR5 記憶體模組，非 HBM；已裁切。",
      title="HBM 為什麼難做<br>把 12 層晶片疊成一棟樓",
      fact="2026-10-28 SK hynix 公布第三季財報：公司表示 DRAM 與 HBM 產能已被長約預訂到 2029 年前後，HBM4 預計第四季出貨量與營收超過 HBM3E。",
      steps=[("DRAM 晶粒","先做好 12 顆"),("TSV 矽穿孔","像電梯上下相連"),("堆疊封裝","灌膠散熱、測試"),("放在 GPU 旁","資料進出更快")],
      credit="示意圖：依公開資料自行繪製的 HBM 堆疊剖面，比例為示意，非任何公司產品圖。",
      src="出處：SK hynix 2026 第三季財報（2026-10-28）"),
 dict(n="03", no="03", kicker="供應鏈讀書筆記｜液冷散熱", photo=LIB/"散熱"/"photo_5.jpg", pos="50% 45%", sub="TrendForce 2026-08-17 市調預估", hint="往右滑看重點 →", foot="與各公司無合作或授權關係。",
      ccredit="圖：Votpuske／CC BY-SA 4.0／Wikimedia Commons。機殼內 CPU 水冷示意，非 AI 伺服器；已裁切。",
      title="AI 伺服器從風扇改水冷<br>熱是怎麼被帶走的",
      fact="2026-08-17 TrendForce 預估：液冷在 AI 晶片的滲透率，2025 年約 33%、2026 年 53%、2027 年接近 60%（市調預估，非公司公告）。",
      steps=[("冷板","貼在晶片上吸熱"),("冷卻液管路","把熱帶出機櫃"),("CDU","二次水路換熱"),("機房外","排出熱")],
      credit="圖：Votpuske／CC BY-SA 4.0／Wikimedia Commons。機殼內 CPU 水冷示意，非 AI 伺服器。",
      src="出處：TrendForce 新聞稿（2026-08-17）"),
 dict(n="04", no="04", kicker="供應鏈讀書筆記｜近封裝光學 NPO", photo=None, svgf="npo_diagram.svg", cover_photo=LIB/"資料中心"/"photo_7.jpg", pos="50% 28%", sub="Tower Semiconductor 新聞稿 2026-11-03", hint="往右滑看圖解 →", foot="與各公司無合作或授權關係。",
      ccredit="圖：Faber／CC BY-SA 2.0／Wikimedia Commons。機房伺服器機櫃示意，非光模組或 NPO 實物；已裁切。",
      title="光模組往晶片靠近一步<br>NPO 是什麼",
      fact="2026-11-03 Tower Semiconductor 新聞稿：Innolight 的第一款近封裝光學（NPO）元件，已在 Tower 的 200 毫米矽光子製程進入早期量產。",
      steps=[("運算晶片","產生高速電訊號"),("光學引擎","近封裝處電轉光"),("光纖","光訊號傳出機櫃"),("對端設備","光轉電再接收")],
      credit="示意圖：依公開資料自行繪製的三種光學位置對照，比例與距離為示意，非任何公司產品圖。",
      src="出處：Tower Semiconductor 新聞稿（2026-11-03）"),
]
CAP = {"01": "誰供應誰：角色分工示意（依公開資料繪製，非特定客戶關係）", "02": "流程示意（依公開資料繪製）", "03": "流程示意（依公開資料繪製）", "04": "流程示意（依公開資料繪製，非特定產品架構）"}
FONT = __import__('os').environ.get('TC_FONT') or '/tmp/claude-0/-home-user-tw-rotation/1662701f-8abb-57a6-b66d-4e0b4e90dd73/scratchpad/font/NotoSansTC.ttf'
for _p in POSTS: _p.setdefault("cover_photo", _p["photo"]); _p["photo"] = None
LOGO = '<svg viewBox="0 0 100 100" width="52" height="52"><rect width="100" height="100" rx="22" fill="#F1F6FD"/><path d="M74.69 46.09 A25 25 0 1 1 53.91 25.31" fill="none" stroke="#1F6FEB" stroke-width="9" stroke-linecap="round"/><circle cx="67.68" cy="32.32" r="6.6" fill="#FF9F1C"/></svg>'  # 頻道 LOGO「開口圈」原色，來源 docs/brand/tc_logo_1102/c1_開口圈/icon_light.svg
def b64(p): return base64.b64encode(Path(p).read_bytes()).decode()
SVGS = {"02": open(HERE / "hbm_diagram.svg", encoding="utf-8").read(), "04": open(HERE / "npo_diagram.svg", encoding="utf-8").read()}
FONTCSS = "@font-face{font-family:'Noto Sans TC';font-weight:100 900;src:url('file://" + FONT + "')}"
BASE = """*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#fff;color:#111;font-family:'Noto Sans TC','WenQuanYi Zen Hei',sans-serif;position:relative;overflow:hidden}
.bar{position:absolute;left:0;top:0;width:1080px;height:14px;background:#D4231A}
.lg{position:absolute;left:60px;top:30px;height:52px;display:flex;align-items:center;gap:14px}
.lg svg{display:block;width:52px;height:52px}
.lg span{font-size:30px;font-weight:700;color:#111;letter-spacing:2px;line-height:52px;white-space:nowrap}
.k{position:absolute;left:400px;top:44px;width:620px;height:34px;font-size:24px;color:#595959;letter-spacing:1px;text-align:right}
.k b{color:#D4231A}
.cr{position:absolute;left:60px;width:960px;font-size:23px;line-height:34px;color:#595959}
.dc{position:absolute;left:60px;width:960px;height:30px;font-size:22px;color:#595959}"""
COVER = """.ph{position:absolute;left:0;top:112px;width:1080px;height:760px;background-color:#EFEFEF;background-size:cover;background-repeat:no-repeat}
.rl{position:absolute;left:60px;top:906px;width:120px;height:6px;background:#D4231A}
.t{position:absolute;left:60px;top:930px;width:960px;height:180px;font-size:72px;font-weight:700;line-height:90px;color:#111}
.sub{position:absolute;left:60px;top:1124px;width:560px;height:40px;font-size:27px;line-height:40px;color:#595959}
.hint{position:absolute;left:640px;top:1124px;width:380px;height:40px;font-size:27px;line-height:40px;font-weight:700;color:#D4231A;text-align:right}
.ln2{position:absolute;left:60px;top:1186px;width:960px;height:2px;background:#CFCFCF}
.cr{top:1200px;height:70px}
.dc{top:1290px}"""
BSL = """.t{position:absolute;left:60px;top:106px;width:960px;height:164px;font-size:68px;font-weight:700;line-height:84px;color:#111}
.ln{position:absolute;left:60px;top:284px;width:960px;height:2px;background:#CFCFCF}
.ph{position:absolute;left:0;top:296px;width:1080px;height:460px;background-color:#EFEFEF}
.q{position:absolute;left:60px;top:326px;width:960px;height:400px;border-left:8px solid #D4231A;padding:0 0 0 36px;display:flex;align-items:center;font-size:46px;line-height:72px;font-weight:500;color:#111}
.f{position:absolute;left:60px;top:778px;width:960px;height:116px;font-size:29px;line-height:38px;color:#111}
.flow{position:absolute;left:60px;top:902px;width:960px;height:188px;display:flex;align-items:stretch}
.st{width:204px;background:#EFEFEF;padding:18px 16px;border-top:4px solid #D4231A}
.ar{width:48px;font-size:34px;color:#595959;display:flex;align-items:center;justify-content:center}
.si{line-height:30px;font-size:24px;color:#D4231A;font-weight:700;height:30px}
.sn{font-size:30px;font-weight:700;margin-top:8px;height:42px}
.sd{font-size:23px;line-height:31px;color:#595959;margin-top:6px;height:70px}
.cap{position:absolute;left:60px;top:1104px;width:960px;height:30px;font-size:22px;color:#595959}
.ln2{position:absolute;left:60px;top:1146px;width:960px;height:2px;background:#CFCFCF}
.cr{top:1158px;height:72px}
.sr{position:absolute;left:60px;top:1236px;width:960px;height:36px;font-size:25px;font-weight:700;color:#111}
.dc{top:1284px}"""
def head_html(p, css, body):
    return '<html><head><meta charset="utf-8"><style>' + FONTCSS + BASE + css + '</style></head><body><div class="bar"></div><div class="lg">' + LOGO + '<span>科技透明圈</span></div>' + body + '</body></html>'
def cover_html(p):
    css = COVER + '.ph{background-image:url(data:image/jpeg;base64,%s);background-position:%s}' % (b64(p["cover_photo"]), p["pos"])
    body = ('<div class="k"><b>%s</b>　%s</div><div class="ph"></div><div class="rl"></div><div class="t">%s</div>'
            '<div class="sub">%s</div><div class="hint">%s</div><div class="ln2"></div><div class="cr">%s</div><div class="dc">%s</div>'
            % (p["no"], p["kicker"], p["title"], p["sub"], p["hint"], p["ccredit"], p["foot"]))
    return head_html(p, css, body)
def b_html(p):
    steps = "".join('<div class="st"><div class="si">%d</div><div class="sn">%s</div><div class="sd">%s</div></div>' % (i+1,a,b) + ('<div class="ar">→</div>' if i < 3 else '') for i,(a,b) in enumerate(p["steps"]))
    dia = p["n"] in SVGS
    inner = SVGS[p["n"]] if dia else ''
    quote = '' if dia else '<div class="q">%s</div>' % p["fact"]
    fact = '<div class="f">%s</div>' % p["fact"] if dia else ''
    cr = p["credit"] if dia else "示意圖：依公開資料自行繪製的流程示意，非實際設備、非任何公司產品圖。"
    body = ('<div class="k"><b>%s</b>　%s</div><div class="t">%s</div><div class="ln"></div><div class="ph">%s</div>%s%s'
            '<div class="flow">%s</div><div class="cap">%s</div><div class="ln2"></div>'
            '<div class="cr">%s</div><div class="sr">%s</div><div class="dc">%s</div>'
            % (p["no"], p["kicker"], p["title"], inner, quote, fact, steps, CAP[p["n"]], cr, p["src"], p["foot"]))
    return head_html(p, BSL, body)
JS = """()=>{const els=[...document.querySelectorAll('.k,.lg,.t,.f,.q,.cap,.cr,.sr,.dc,.si,.sn,.sd,.ar,.ph,.bar,.rl,.sub,.hint')];
const R=els.map(e=>{const r=e.getBoundingClientRect();let o=false;if(e.textContent.trim()){const g=document.createRange();g.selectNodeContents(e);const t=g.getBoundingClientRect();const fs=parseFloat(getComputedStyle(e).fontSize);const tol=fs*0.3;o=t.bottom>r.bottom+tol||t.right>r.right+1||t.top<r.top-tol}return [e.className,r.left,r.top,r.right,r.bottom,o]});
const bad=[];for(let i=0;i<R.length;i++){if(R[i][5])bad.push('溢出:'+R[i][0]);for(let j=i+1;j<R.length;j++){const a=R[i],b=R[j];
if(!(a[0]=='ph'&&b[0]=='q')&&a[1]<b[3]-0.5&&b[1]<a[3]-0.5&&a[2]<b[4]-0.5&&b[2]<a[4]-0.5)bad.push(a[0]+'x'+b[0])}}
const fl=document.querySelector('.flow');if(fl){const c=document.querySelector('.cap').getBoundingClientRect();if(fl.getBoundingClientRect().bottom>c.top)bad.push('flow x cap')}
const q=document.querySelector('.q');if(q&&q.scrollHeight>q.clientHeight+1)bad.push('q內容溢出');
const sv=document.querySelector('.ph svg');if(sv){const T=[...sv.querySelectorAll('text')].map(t=>[t.textContent,t.getBoundingClientRect()]);
for(let i=0;i<T.length;i++){const a=T[i][1];if(a.left<0||a.right>1080||a.top<296||a.bottom>756)bad.push('svg出界:'+T[i][0]);
for(let j=i+1;j<T.length;j++){const b=T[j][1];if(a.left<b.right&&b.left<a.right&&a.top<b.bottom&&b.top<a.bottom)bad.push('svg字重疊:'+T[i][0]+'x'+T[j][0])}}
T.forEach(([tx,a])=>{const l=[...sv.querySelectorAll('line')].some(r=>{const b=r.getBoundingClientRect();return a.left<b.right&&b.left<a.right&&a.top<b.bottom&&b.top<a.bottom});
if(l&&tx!='電訊號走很長一段')bad.push('svg字壓線:'+tx)})}
return bad}"""
if __name__ == "__main__":
    import os, sys
    tot = 0; n_done = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=os.environ.get("TW_CHROME") or None); pg = br.new_page(viewport=dict(width=1080, height=1350))
        for p in [q for q in POSTS if not sys.argv[1:] or q["n"] in sys.argv[1:]]:
            for kind, fn, out in (("封面", cover_html, "image.png"), ("第2張", b_html, "image2.png")):
                (HERE / '_tmp.html').write_text(fn(p), encoding='utf-8'); pg.goto('file://' + str(HERE / '_tmp.html')); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(500)
                bad = pg.evaluate(JS); tot += len(bad); n_done += 1
                pg.screenshot(path=str(HERE / p["n"] / out))
                print(p["n"], kind, "重疊/溢出", len(bad), bad)
        br.close()
    (HERE / "_tmp.html").unlink(missing_ok=True)
    print("重疊檢查：程式", n_done, "張", tot, "筆")
