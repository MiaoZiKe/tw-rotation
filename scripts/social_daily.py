"""每日盤前貼文草稿：從資料湖整理「美股收盤、台積電 ADR、道瓊、台指期夜盤、夜間消息、今日日程」，
寫成 social/threads/queue/<日期>_pre.md（status: draft，必須人工核准才會被發出）。

用法：python scripts/social_daily.py pre [--date YYYY-MM-DD] [--root <專案根目錄>] [--out <queue 目錄>]

原則（Andy 2026-10-26）：
  · 盤前先核准再發：這支只產「草稿」，永遠不會自動核准。
  · 只放事實：指數、匯率、ADR、夜盤、公告標題；不寫進出場、個股買賣、目標價（法遵：docs/marketing/growth_plan_1018.md L7）。
  · 資料拿不到就不寫那一行，並在 notes 記原因；絕不推估。
  · 美股資料日期距今超過 4 天，或台指期夜盤不是最近一晚，會在 notes 警告，核准前要看。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TAIPEI = timezone(timedelta(hours=8))
ADR_RATIO = 5          # 1 股 TSM ADR ＝ 5 股 2330
STALE_DAYS = 4


def _rd(root: Path, table: str, **kw) -> pd.DataFrame:
    import pyarrow.dataset as ds
    p = root / "data" / table
    if not p.exists():
        return pd.DataFrame()
    return ds.dataset(str(p), format="parquet", partitioning="hive").to_table(**kw).to_pandas()


def pct(a: float, b: float) -> float:
    return (a / b - 1) * 100


def fmt(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f}"


def sgn(v: float, d: int = 2) -> str:
    return f"{v:+,.{d}f}"


def last_two(df: pd.DataFrame, symbol: str):
    s = df[df["symbol"] == symbol].sort_values("date")
    if len(s) < 2:
        return None
    a, b = s.iloc[-1], s.iloc[-2]
    return str(a["date"]), float(a["close"]), float(b["close"])


def expected_us_date(target: date) -> date:
    """台北盤前（早上）該看到的最近一個美股交易日＝target 的前一個平日（美國假日會誤報，只當警告）。"""
    d = target - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def us_lines(intl: pd.DataFrame, notes: list[str], target: date | None = None) -> list[str]:
    out: list[str] = []
    spec = [("^GSPC", "標普500"), ("^IXIC", "那斯達克"), ("^DJI", "道瓊"), ("^SOX", "費城半導體")]
    got = {}
    for sym, nm in spec:
        r = last_two(intl, sym)
        if r:
            got[sym] = (nm, r)
        else:
            notes.append(f"資料湖沒有 {nm}（{sym}）；管線新增代碼後需等下一輪抓取")
    if got:
        d = max(r[0] for _, r in got.values())
        out.append(f"🇺🇸 美股收盤（{d[5:].replace('-', '/')}）")
        for sym, (nm, (dd, c, p)) in got.items():
            tag = "" if dd == d else f"（{dd[5:]}）"
            out.append(f"{nm} {fmt(c)}（{sgn(pct(c, p))}%）{tag}")
        if target is not None and date.fromisoformat(d) < expected_us_date(target):
            notes.append(f"美股最新只到 {d}，應該有 {expected_us_date(target)}：05:07 那輪新聞管線可能還沒跑完，或遇美國假日")
        age = (datetime.now(TAIPEI).date() - date.fromisoformat(d)).days
        if age > STALE_DAYS:
            notes.append(f"美股資料已 {age} 天前（{d}），確認是否有假日或管線問題")
    return out


def misc_line(intl: pd.DataFrame) -> str | None:
    parts = []
    for sym, nm, d in (("^VIX", "VIX", 2), ("DX-Y.NYB", "美元指數", 2), ("TWD=X", "美元兌台幣", 2)):
        r = last_two(intl, sym)
        if r:
            parts.append(f"{nm} {fmt(r[1], d)}")
    return "😨 " + "｜".join(parts) if parts else None


def adr_line(intl: pd.DataFrame, price: pd.DataFrame, notes: list[str]) -> str | None:
    t = last_two(intl, "TSM")
    fx = last_two(intl, "TWD=X")
    if not t:
        notes.append("資料湖還沒有台積電 ADR（TSM）")
        return None
    d, c, p = t
    line = f"🇹🇼 台積電 ADR {fmt(c)} 美元（{sgn(pct(c, p))}%）"
    try:
        tw = price[(price["code"].astype(str) == "2330")].sort_values("date").iloc[-1]
        if fx:
            implied = c * fx[1] / ADR_RATIO
            prem = pct(implied, float(tw["close"]))
            line += f"｜換算約 {fmt(implied, 0)} 元，較 2330 前收 {fmt(float(tw['close']), 0)} {'溢價' if prem >= 0 else '折價'} {abs(prem):.1f}%"
    except Exception:
        notes.append("算不出 ADR 折溢價（缺 2330 收盤或匯率）")
    return line


def night_line(root: Path, notes: list[str]) -> str | None:
    ii = _rd(root, "index_intraday")
    ox = _rd(root, "index_ohlc")
    if ii.empty or ox.empty:
        notes.append("查不到台指期夜盤")
        return None
    n = ii[ii["symbol"] == "FUT_N"].sort_values("ts")
    if n.empty:
        notes.append("資料湖沒有台指期夜盤（FUT_N）")
        return None
    last = n.iloc[-1]
    ts = datetime.fromisoformat(str(last["ts"]))
    ref_day = (ts.date() if ts.hour < 8 else ts.date() + timedelta(days=1))
    fut = ox[(ox["symbol"] == "FUT") & (ox["date"].astype(str) < ref_day.isoformat())].sort_values("date")
    if fut.empty:
        notes.append("找不到夜盤對照的日盤收盤")
        return None
    ref = float(fut.iloc[-1]["close"])
    c = float(last["close"])
    age = (datetime.now(TAIPEI) - ts.astimezone(TAIPEI)).total_seconds() / 3600
    if age > 30:
        notes.append(f"台指期夜盤最後一筆是 {ts:%m/%d %H:%M}（{age:.0f} 小時前），可能沒有新夜盤（休市？）")
    return f"🌙 台指期夜盤收 {fmt(c, 0)}（對日盤收 {fmt(ref, 0)} {sgn(pct(c, ref))}%）"


# 法遵：標題帶這些字的是「個股推薦／進出場」語氣的新聞，不轉貼（docs/marketing/growth_plan_1018.md L7）。
_BANNED = ("潛力股", "飆股", "必買", "布局", "進場", "買進", "賣出", "目標價", "作帳", "吃貨", "推薦", "點名", "抄底",
           "搶進", "強勢股", "存股", "翻倍", "大賺", "資金卡位", "加碼", "減碼", "買點", "賣點")


def ok_title(t: str) -> bool:
    return not any(w in t for w in _BANNED)


def news_lines(root: Path, hours: int = 18, k: int = 2) -> list[str]:
    n = _rd(root, "news", columns=["published_at", "source", "title"])
    if n.empty:
        return []
    t = pd.to_datetime(n["published_at"], utc=True, errors="coerce", format="mixed")
    n = n.assign(_t=t).dropna(subset=["_t"])
    cut = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
    n = n[n["_t"] >= cut].sort_values("_t", ascending=False)
    seen, out = set(), []
    for _, r in n.iterrows():
        title = str(r["title"]).strip()
        if not ok_title(title):
            continue
        key = title[:12]
        if key in seen:
            continue
        seen.add(key)
        out.append(f"📰 {title}（{r['source']}）")
        if len(out) >= k:
            break
    return out


def compose_pre(root: Path, target: date) -> tuple[str, list[str]]:
    notes: list[str] = []
    intl = _rd(root, "intl_daily")
    price = _rd(root, "price_daily", columns=["date", "code", "close"]) if (root / "data" / "price_daily").exists() else pd.DataFrame()
    lines = [f"🌅 盤前重點｜{target:%m/%d}"]
    lines += us_lines(intl, notes, target)
    for x in (adr_line(intl, price, notes) if not intl.empty else None, misc_line(intl) if not intl.empty else None,
              night_line(root, notes)):
        if x:
            lines.append(x)
    nl = news_lines(root)
    lines += nl or []
    if not nl:
        notes.append("最近 18 小時沒有新聞標題")
    lines.append("整理公開資訊，非投顧，不構成投資建議。")
    return "\n".join(lines), notes


def write_draft(root: Path, out: Path, target: date, body: str, notes: list[str]) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"{target.isoformat()}_pre.md"
    note = ("；".join(notes) or "無").replace("\n", " ")
    f.write_text(
        f"---\nstatus: draft\npublish_at: {target.isoformat()}T08:00+08:00\n"
        f"title: 盤前重點 {target.isoformat()}（核准前請看 notes）\nnotes: {note}\n---\n{body}\n",
        encoding="utf-8")
    return f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["pre"])
    ap.add_argument("--date", default="")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default=str(ROOT / "social" / "threads" / "queue"))
    a = ap.parse_args(argv)
    target = date.fromisoformat(a.date) if a.date else datetime.now(TAIPEI).date()
    body, notes = compose_pre(Path(a.root), target)
    f = write_draft(Path(a.root), Path(a.out), target, body, notes)
    print(f"已寫入 {f}（draft）")
    for n in notes:
        print("注意：", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
