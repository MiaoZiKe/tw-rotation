"""全站文字重疊普查（2026-10-06，Andy：「出現文字重疊 幫我CHK 其他是否可能會發生」）。

為什麼另外一支、不併進 _preview.py 的主流程：全站 18 頁 ＋ 4 檔 × 11 分頁 × 3 寬 × 2 主題 ≈ 370 次載入，
一輪 20 分鐘以上，放進每次 push 的關卡會讓大家都多等。日常關卡由 _preview.py 的
「個股分頁文字重疊」那一段抽樣守住；這支是「懷疑還有別處」時手動跑的全掃。

用法：
  python scripts/_overlap_census.py                       # 全部
  ONLY=stock/2330 WS=1440 THEMES=light python scripts/_overlap_census.py
量測本體是 _preview.TEXT_OVERLAP_ALL_JS（SVG 文字＋DOM 文字節點，以卡片為單位兩兩比，交疊 > 2px²）。
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _preview as P  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROUTES = ['overview', 'flow', 'flow/rotation', 'flow/sankey', 'flow/inst', 'heatmap/industry', 'heatmap/theme',
          'industry', 'industry/semiconductor', 'industry/ai_server', 'market', 'market/cand', 'market/ma',
          'explore', 'etf', 'earnings', 'watch', 'admin']
for c in ['2330', '3189', '2603', '0050']:
    for t in ['overview', 'basics', 'tags', 'revenue', 'profit', 'dividend', 'inst', 'margin', 'holders', 'news', 'holdings']:
        ROUTES.append(f'stock/{c}|{t}')


def main():
    only = os.environ.get('ONLY')
    routes = [r for r in ROUTES if not only or any(o in r for o in only.split(','))]
    widths = [int(x) for x in os.environ.get('WS', '1440,800,390').split(',')]
    themes = os.environ.get('THEMES', 'dark,light').split(',')
    srv = P.serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for th in themes:
            for w in widths:
                pg = b.new_page(viewport={'width': w, 'height': 1000})
                pg.add_init_script(f"try{{localStorage.setItem('tw.theme','{th}')}}catch(e){{}}")
                for r in routes:
                    h, _, tab = r.partition('|')
                    pg.goto(f"{base}?svg=1#{h}", wait_until='networkidle')
                    pg.wait_for_timeout(1800)
                    if tab:
                        btn = pg.query_selector(f'#stockTabs button[data-t="{tab}"]')
                        if not btn or not btn.is_visible():   # 390 走手機版個股頁，沒有這排分頁鈕
                            continue
                        btn.click()
                        pg.wait_for_timeout(1500)
                    res = pg.evaluate(P.TEXT_OVERLAP_ALL_JS, 2)
                    for o in res:
                        out.append([th, w, r] + o)
                    print(th, w, r, len(res), flush=True)
                pg.close()
    dst = os.environ.get('OUT', 'overlap_census.json')
    Path(dst).write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print('總計', len(out), '組 →', dst)


if __name__ == '__main__':
    main()
