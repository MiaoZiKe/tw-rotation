"""groups.yaml / themes.yaml 裡的每一個代號，都要是「還在交易」的股票。

為什麼要有這一條（2026-09-19）：
  Andy 問「先前交代的 task 是否有完成」，我派了五位分析師逐檔查族群成分。
  他們抓出一票放錯格的（直播平台被放進半導體材料、醋酸纖維絲束被放進半導體設備），
  但**沒有任何一位回報 2311 日月光與 6806 森崴能源已經下市** —— 那兩檔是我拿
  data/price_daily 對出來的。

  原因很直接：分析師查的是「這家公司做什麼」，那是 WebSearch 查得到的；
  「這個代號現在還有沒有成交」是資料問題，只有機器查得到。
  而且這種錯**不會報錯**：data/company_info 對下市公司留了一筆欄位幾乎全空的殘影
  （2311、2325 矽品都是），所以網站照樣印得出名字，只是那一格的量能永遠是 0，
  M1 的族群資金流就被它稀釋掉。

  2311 日月光 2018-04 下市（與矽品合併為日月光投控 3711）；
  6806 森崴能源因子公司富崴承攬台電離岸風電二期虧損、淨值轉負，
  證交所公告自 2026-06-23 起終止上市。

判準刻意放寬到「最近 60 個交易日有任何一筆」而不是「最近 20 個」，
理由是新上市股與長期停牌後復牌的股票不該被誤判；真正下市的股票差的是好幾年，
不是幾週，60 天的緩衝不會讓 2311 這種案例漏網。

沒有資料湖（例如乾淨 checkout 的 CI）時自動跳過 —— 這條是資料護欄，不是邏輯測試。
"""
from __future__ import annotations

import glob

import pytest
import yaml

from pipeline import config

_LOOKBACK = 60


def _alive_codes() -> set[str]:
    import pandas as pd

    files = sorted(glob.glob(str(config.DATA / "price_daily" / "year=*" / "part.parquet")))
    if not files:
        pytest.skip("沒有 data/price_daily，跳過（這條是資料護欄，不是邏輯測試）")
    px = pd.read_parquet(files[-1], columns=["date", "code"])
    if px.empty:
        pytest.skip("price_daily 最新分割是空的")
    days = sorted(px["date"].unique())[-_LOOKBACK:]
    return set(px[px["date"].isin(days)]["code"].astype(str))


def _codes_of(path, key):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = {}
    for name, blk in (doc.get(key) or {}).items():
        for code in blk.get("codes") or []:
            out.setdefault(str(code), []).append(name)
    return out


@pytest.mark.parametrize(
    ("fname", "key"),
    [("groups.yaml", "groups"), ("themes.yaml", "themes")],
)
def test_族群成分都還在交易(fname, key):
    alive = _alive_codes()
    path = config.GROUPS_DIR / fname
    dead = {c: g for c, g in _codes_of(path, key).items() if c not in alive}
    assert not dead, (
        f"{fname} 裡這些代號在最近 {_LOOKBACK} 個交易日都沒有價量，很可能已經下市／停止買賣：\n"
        + "\n".join(f"  {c}  出現在 {', '.join(g)}" for c, g in sorted(dead.items()))
        + "\n（下市公司在 company_info 裡通常還留著殘影，所以網站不會報錯，"
        "只是那一格的量能永遠是 0 —— 請確認後從 YAML 移除。）"
    )


def test_代號格式都是四碼數字():
    """順手擋掉打錯字的代號 —— 個股頁會去抓完全另一家公司的資料，而且看起來完全正常。"""
    bad = []
    for fname, key in (("groups.yaml", "groups"), ("themes.yaml", "themes")):
        for code, groups in _codes_of(config.GROUPS_DIR / fname, key).items():
            if not (len(code) == 4 and code.isdigit()):
                bad.append(f"{fname}: {code}（{', '.join(groups)}）")
    assert not bad, f"代號格式不對：{bad}"
