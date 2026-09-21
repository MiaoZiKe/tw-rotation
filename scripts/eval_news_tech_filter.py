"""評估 TechNews 的「科技」分類篩選器：拿資料湖裡的真實新聞算 precision / recall。

為什麼要這支（Andy 2026-09-21：「今日事件這邊的科技新聞請確實篩選跟科技有關的」）：
篩選清單一定會被反覆調整（清單就是放在 `config.py` 讓人調的），
每次調完都要能立刻知道「有沒有改壞」。**不接受「看起來好多了」當結論，只看數字。**

評估集：`docs/fixtures/technews_labels.tsv` —— 從 `data/news` 的 363 則真實 technews
裡每 3 則取 1 則（121 則）人工標註，標註判準寫在檔頭與 DECISIONS。
標註值三種：科技 / 總經 / 不收。

跑法：
    python scripts/eval_news_tech_filter.py           # 印總表 ＋ 每一個誤判
    python scripts/eval_news_tech_filter.py --all     # 另外印整包 363 則的前後筆數變化
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.sources.news import classify_technews  # noqa: E402

LABELS = ROOT / "docs" / "fixtures" / "technews_labels.tsv"
LAKE = ROOT / "data" / "news" / "year=2026" / "part.parquet"


def load_labels() -> list[dict]:
    with LABELS.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def evaluate(rows: list[dict]) -> dict:
    """算「科技」這一類的 precision / recall，並收集每一個誤判。

    台股與總經在這裡都算「不是科技」—— Andy 抱怨的是科技格裡有雜訊，
    所以先把科技這一格的二元判斷算清楚，三類的完整對照另外印。
    """
    tp = fp = fn = 0
    wrong_cut, wrong_keep, wrong_bucket = [], [], []
    for r in rows:
        got = classify_technews(r["title"], r["keywords"])
        want = r["label"]
        is_got_tech, is_want_tech = got == "科技", want == "科技"
        if is_got_tech and is_want_tech:
            tp += 1
        elif is_got_tech and not is_want_tech:
            fp += 1
            wrong_keep.append((r, got, want))
        elif not is_got_tech and is_want_tech:
            fn += 1
            wrong_cut.append((r, got, want))
        # 兩邊都同意「不是科技」，但改標的去處不一樣（總經 vs 不收）
        elif (got or "不收") != want:
            wrong_bucket.append((r, got, want))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1,
            "wrong_cut": wrong_cut, "wrong_keep": wrong_keep, "wrong_bucket": wrong_bucket}


def _show(title: str, items: list) -> None:
    print(f"\n── {title}（{len(items)} 則）")
    for r, got, want in items:
        print(f"  人工={want} / 程式={got or '不收'}")
        print(f"    {r['title']}")
        print(f"    tags: {r['keywords']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="另外印整包 363 則的前後筆數變化")
    args = ap.parse_args()

    rows = load_labels()
    res = evaluate(rows)
    n = len(rows)
    print(f"評估集：{n} 則人工標註（{LABELS.relative_to(ROOT)}）")
    print(f"科技這一格：TP={res['tp']} FP={res['fp']} FN={res['fn']}")
    print(f"  precision = {res['precision']:.3f}   （判成科技的裡面，真的是科技的比例）")
    print(f"  recall    = {res['recall']:.3f}   （真的是科技的裡面，有被留下的比例）")
    print(f"  F1        = {res['f1']:.3f}")
    exact = n - len(res["wrong_cut"]) - len(res["wrong_keep"]) - len(res["wrong_bucket"])
    print(f"三類完全一致：{exact}/{n} = {exact / n:.3f}")

    _show("被錯砍的（該留卻沒留）", res["wrong_cut"])
    _show("被錯留的（不該留卻留了）", res["wrong_keep"])
    _show("科技判斷對、但改標去處不同", res["wrong_bucket"])

    if args.all:
        import pandas as pd
        df = pd.read_parquet(LAKE)
        tn = df[df.source == "technews"]
        after = [classify_technews(t, k) for t, k in zip(tn["title"], tn["keywords"])]
        print(f"\n── 整包 {len(tn)} 則 technews 的前後變化")
        print(f"  篩選前：科技 {len(tn)} 則（全部無條件標成科技）")
        for cat in ("科技", "總經", "台股"):
            print(f"  篩選後：{cat} {after.count(cat)} 則")
        print(f"  不收：{sum(1 for a in after if a is None)} 則")

    bad = res["precision"] < 0.85 or res["recall"] < 0.85
    print("\n" + ("✗ precision 或 recall 低於 0.85，回去調清單" if bad else "✓ 兩項都在 0.85 以上"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
