"""財經日曆錄影用：個股代號與名稱逐字模糊（只在錄影的瀏覽器裡；公司名單取自資料湖與 earnings.json）。自 03 舊版 capture_cal.py 搬出。"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs" / "marketing" / "video_1010"))
import capture as C  # noqa: E402


def blur_js() -> str:
    """個股代號與名稱逐字模糊（只在錄影的瀏覽器裡）。名單＝資料湖 company_info 全部普通股＋財經日曆資料裡出現的公司。"""
    names, codes = set(), set()
    try:
        import pandas as pd
        fs = glob.glob(str(REPO / "data" / "company_info" / "**" / "*.parquet"), recursive=True)
        df = pd.concat([pd.read_parquet(f, columns=["code", "name"]) for f in fs])
        df = df[df["code"].astype(str).str.fullmatch(r"\d{4}")]
        codes |= set(df["code"].astype(str))
        # 兩字公司名裡的一般用語（新聞標題、說明文常見）不當名字模糊，免得說明文字被糊掉；
        # 真的出現在財經日曆的公司（下面 earnings.json 那段）一律加回來。
        generic = {"世界", "全國", "中華", "大陸", "數字", "介面", "互動", "統一", "全新", "大量", "地球", "光明", "幸福", "相互",
                   "時報", "典範", "冠軍", "新產", "卓越", "無敵", "正道", "必應", "有益", "有量", "立誠", "國產", "大同", "東洋",
                   "台南", "南港", "大成", "國建", "新興", "精華", "公準", "力成", "可成", "大立", "華新"}
        names |= {n for n in df["name"].astype(str) if len(n) >= 2 and n not in generic}
    except Exception:  # noqa: BLE001
        pass
    try:
        e = json.loads((C.SITE / "data" / "earnings.json").read_text(encoding="utf-8"))
        for c, v in (e.get("companies") or {}).items():
            codes.add(str(c))
            if v.get("name"):
                names.add(v["name"])
        for ev in e.get("events") or []:
            if ev.get("code"):
                codes.add(str(ev["code"]))
            if ev.get("name"):
                names.add(ev["name"])
    except Exception:  # noqa: BLE001
        pass
    import re
    names = sorted(names, key=len, reverse=True)
    names = [n.replace("*", "") for n in names]   # 公司名後綴的「*」是證交所標記，不是名字的一部分
    pat = "|".join(re.escape(n) for n in names if n) + "|" + "|".join(sorted(codes))
    return r"""
(() => {
  const RE = new RegExp('(?<![0-9A-Za-z.,/:\\-])(' + %s + ')(?![0-9.,%%/:\\-])|(?<=收盤 |市值第 )([0-9][0-9,]*(?:\\.[0-9]+)?)', 'g');   // 第二組：面板裡「收盤 X 元」的股價、「市值第 N 名」的名次也模糊（避免由價位、名次認出是哪一家）
  const SKIP = '.fcard,[data-sec=spark],[data-sec=rule],#earnFilt,.elegend,.ehd,.wd,.dn,.edisc,.__blur,script,style,.badge,.stars';
  const css = () => { const st = document.createElement('style'); st.textContent = '.__blur{filter:blur(5px)!important;display:inline-block}'; document.head.appendChild(st); };
  const sweep = (root) => {
    const v = document.getElementById('v-earnings'); if (!v) return;
    const p = document.getElementById('earnPanel'); const fedMode = p && p.dataset.mode === 'fed';
    const w = document.createTreeWalker(root && v.contains(root) ? root : v, NodeFilter.SHOW_TEXT); const hits = []; let n;
    while ((n = w.nextNode())) { const t = n.nodeValue; if (!t || !t.trim()) continue; const e = n.parentElement; if (!e || e.closest(SKIP)) continue;
      if (fedMode && e.closest('#earnPanel')) continue; RE.lastIndex = 0; if (RE.test(t)) hits.push(n); }
    for (const n of hits) { const t = n.nodeValue; RE.lastIndex = 0; const f = document.createDocumentFragment(); let last = 0, m;
      while ((m = RE.exec(t))) { if (m.index > last) f.appendChild(document.createTextNode(t.slice(last, m.index)));
        const g = m[1] || m[2]; const s = document.createElement('span'); s.className = '__blur'; s.textContent = g; f.appendChild(s); last = m.index + g.length; }
      if (last < t.length) f.appendChild(document.createTextNode(t.slice(last)));
      n.parentNode.replaceChild(f, n); }
  };
  const go = () => { css(); sweep(); new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true, characterData: true }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(pat)
