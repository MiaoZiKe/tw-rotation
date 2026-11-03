"""頻道二（科技透明圈）範例貼文圖：瑞士極簡版型＋CC 實景照。1080x1350。
用法：python render.py   → 01/02/03 各輸出 image.png，並印出「重疊檢查」。
色票：白 #FFFFFF／黑 #111111／瑞士紅 #D4231A／灰 #595959／細線 #CFCFCF／淡灰面 #EFEFEF。
字型：文泉驛正黑（容器內唯一可用中文字型；正式版建議 Noto Sans TC）。
"""
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
LIB = HERE.parents[5] / "social" / "photo_lib" / "_category"
POSTS = [
 dict(n="01", no="01", kicker="供應鏈讀書筆記｜先進封裝", photo=LIB/"半導體"/"photo_3.jpg", pos="50% 50%",
      title="晶片做完還不能出貨<br>AI 的瓶頸在「封裝」",
      fact="2026-10-15 台積電法說會：董事長魏哲家表示，5 倍光罩尺寸的先進封裝目前只有台積電能提供，CoWoS 仍是客戶最優先的選擇。",
      steps=[("晶圓廠","製造運算晶片"),("記憶體廠","製造 HBM 堆疊"),("封裝廠","以 CoWoS 接在同一片矽中介層"),("伺服器廠","組成加速卡與機櫃")],
      credit="圖：Mister rf／CC BY-SA 4.0／Wikimedia Commons。早期 ROM 晶片打線封裝，示意「晶片要裝進封裝」，非 CoWoS。",
      src="出處：台積電 2026 第三季法說會（2026-10-15）"),
 dict(n="02", no="02", kicker="供應鏈讀書筆記｜HBM 記憶體", photo=LIB/"記憶體"/"photo_5.jpg", pos="50% 50%",
      title="HBM 為什麼難做<br>把 12 層晶片疊成一棟樓",
      fact="2026-10-28 SK hynix 公布第三季財報：公司表示 DRAM 與 HBM 產能已被長約預訂到 2029 年前後，HBM4 預計第四季出貨量與營收超過 HBM3E。",
      steps=[("DRAM 晶粒","先做好 12 顆"),("TSV 矽穿孔","像電梯上下相連"),("堆疊封裝","灌膠散熱、測試"),("放在 GPU 旁","資料進出更快")],
      credit="圖：D-Kuru／CC BY-SA 4.0／Wikimedia Commons。一般 DDR4 記憶體模組，示意記憶體晶片，非 HBM。",
      src="出處：SK hynix 2026 第三季財報（2026-10-28）"),
 dict(n="03", no="03", kicker="供應鏈讀書筆記｜液冷散熱", photo=LIB/"散熱"/"photo_5.jpg", pos="50% 45%",
      title="AI 伺服器從風扇改水冷<br>熱是怎麼被帶走的",
      fact="2026-08-17 TrendForce 預估：液冷在 AI 晶片的滲透率，2025 年約 33%、2026 年 53%、2027 年接近 60%（市調預估，非公司公告）。",
      steps=[("冷板","貼在晶片上吸熱"),("冷卻液管路","把熱帶出機櫃"),("CDU","與另一條水路交換熱"),("機房外","排出熱")],
      credit="圖：Votpuske／CC BY-SA 4.0／Wikimedia Commons。伺服器機殼內的 CPU 水冷示意，非 AI 伺服器。",
      src="出處：TrendForce 新聞稿（2026-08-17）"),
]
def b64(p): return base64.b64encode(Path(p).read_bytes()).decode()
def html(p):
    steps = "".join('<div class="st"><div class="si">%d</div><div class="sn">%s</div><div class="sd">%s</div></div>' % (i+1,a,b) + ('<div class="ar">→</div>' if i < 3 else '') for i,(a,b) in enumerate(p["steps"]))
    css = """*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1350px;background:#fff;color:#111;font-family:'WenQuanYi Zen Hei','Noto Sans TC',sans-serif;position:relative;overflow:hidden}
.bar{position:absolute;left:0;top:0;width:1080px;height:14px;background:#D4231A}
.k{position:absolute;left:60px;top:44px;width:960px;height:34px;font-size:26px;color:#595959;letter-spacing:2px}
.k b{color:#D4231A}
.t{position:absolute;left:60px;top:92px;width:960px;height:170px;font-size:68px;font-weight:700;line-height:84px;color:#111}
.ln{position:absolute;left:60px;top:276px;width:960px;height:2px;background:#CFCFCF}
.ph{position:absolute;left:0;top:296px;width:1080px;height:420px;background-color:#EFEFEF;background-size:cover;background-repeat:no-repeat}
.f{position:absolute;left:60px;top:734px;width:960px;height:116px;font-size:29px;line-height:38px;color:#111}
.flow{position:absolute;left:60px;top:872px;width:960px;height:210px;display:flex;align-items:stretch}
.st{width:204px;background:#EFEFEF;padding:18px 16px;border-top:4px solid #D4231A}
.ar{width:48px;font-size:34px;color:#595959;display:flex;align-items:center;justify-content:center}
.si{line-height:30px;font-size:24px;color:#D4231A;font-weight:700;height:30px}
.sn{font-size:30px;font-weight:700;margin-top:8px;height:42px}
.sd{font-size:23px;line-height:31px;color:#595959;margin-top:6px;height:66px}
.cap{position:absolute;left:60px;top:1096px;width:960px;height:28px;font-size:21px;color:#595959}
.ln2{position:absolute;left:60px;top:1138px;width:960px;height:2px;background:#CFCFCF}
.cr{position:absolute;left:60px;top:1152px;width:960px;height:72px;font-size:23px;line-height:34px;color:#595959}
.sr{position:absolute;left:60px;top:1234px;width:960px;height:36px;font-size:25px;font-weight:700;color:#111}
.dc{position:absolute;left:60px;top:1284px;width:700px;height:30px;font-size:22px;color:#595959}
.br{position:absolute;right:60px;top:1284px;width:240px;height:30px;font-size:22px;color:#D4231A;font-weight:700;text-align:right}"""
    ph = '.ph{background-image:url(data:image/jpeg;base64,%s);background-position:%s}' % (b64(p["photo"]), p["pos"])
    return ('<html><head><meta charset="utf-8"><style>' + css + ph + '</style></head><body><div class="bar"></div>'
      '<div class="k"><b>%s</b>　%s</div><div class="t">%s</div><div class="ln"></div><div class="ph"></div>'
      '<div class="f">%s</div><div class="flow">%s</div>'
      '<div class="cap">誰供應誰：角色分工示意（依公開資料繪製，非特定客戶關係）</div><div class="ln2"></div>'
      '<div class="cr">%s</div><div class="sr">%s</div><div class="dc">與各公司無合作或授權關係</div><div class="br">科技透明圈</div></body></html>'
      % (p["no"], p["kicker"], p["title"], p["fact"], steps, p["credit"], p["src"]))
JS = """()=>{const els=[...document.querySelectorAll('.k,.t,.f,.cap,.cr,.sr,.dc,.br,.si,.sn,.sd,.ar,.ph,.bar')];
const R=els.map(e=>{const r=e.getBoundingClientRect();return [e.className,r.left,r.top,r.right,r.bottom,e.scrollHeight>e.clientHeight+1]});
const bad=[];for(let i=0;i<R.length;i++){if(R[i][5])bad.push('溢出:'+R[i][0]);for(let j=i+1;j<R.length;j++){const a=R[i],b=R[j];
if(a[1]<b[3]-0.5&&b[1]<a[3]-0.5&&a[2]<b[4]-0.5&&b[2]<a[4]-0.5)bad.push(a[0]+'x'+b[0])}}
const fl=document.querySelector('.flow').getBoundingClientRect();const c=document.querySelector('.cap').getBoundingClientRect();
if(fl.bottom>c.top)bad.push('flow x cap');return bad}"""
if __name__ == "__main__":
    tot = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=__import__("os").environ.get("TW_CHROME") or None); pg = br.new_page(viewport=dict(width=1080, height=1350))
        for p in POSTS:
            pg.set_content(html(p)); pg.wait_for_timeout(300)
            bad = pg.evaluate(JS); tot += len(bad)
            pg.screenshot(path=str(HERE / p["n"] / "image.png"))
            print(p["n"], "重疊/溢出", len(bad), bad)
        br.close()
    print("重疊檢查：程式 3 張", tot, "筆")
