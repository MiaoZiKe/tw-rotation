"""手動加發（緊急快訊、補發）的封面：跟自動主題文章走同一套選圖與渲染（social_news.render_cards → render_news_cards.card_auto）。

2026-10-30 Andy：「相這種跟公司有關的 優先附上公司圖片」—— 那天早上緊急加發「Alphabet 跌 12.6%」，
手寫的渲染腳本直接指定了 Intel 圖池，封面配成 Intel 處理器。之後手動加發一律用這支，不准在腳本裡指定圖池。

用法：
  python scripts/news_cover.py <post.json> <輸出.jpg> [--slot pre|mid|post] [--day YYYY-MM-DD] [--record]
post.json 要有 {"d": {...}}（或直接是 d）：d.card.subject＝標題主體（例：Alphabet），選圖照
  主體公司圖池（14 天輪替）→ 該公司類別池 → 新聞文字類別池 → 總類通用圖池。
--record：把這張記進 social/photo_lib 的使用紀錄（輪替用；正式發出的才加）。
重疊 0 筆才回 0；有重疊或選不到圖回 1。
"""
import json, shutil, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_news as S


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    src, out = Path(argv[0]), Path(argv[1])
    opt = lambda k, dv="": argv[argv.index(k) + 1] if k in argv else dv
    j = json.loads(src.read_text(encoding="utf-8"))
    d = j.get("d", j)
    d.setdefault("meta", {}); d.setdefault("id", out.stem)
    slot = opt("--slot", d.get("slot") or "pre"); day = opt("--day", (d.get("data_date") or "")[:10])
    with tempfile.TemporaryDirectory() as td:
        bad = S.render_cards([d], slot, Path(td), day, usage_path=S.PHOTO_USAGE if "--record" in argv else None)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(td) / f"{d['id']}.jpg", out)
    m = d["meta"]
    print(f"主體：{d['card'].get('subject')}　選圖：{m.get('photo')}（{m.get('layout')}／{m.get('photo_kind')}）　重疊：{bad[d['id']]} 筆　→ {out}")
    return 1 if bad[d["id"]] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
