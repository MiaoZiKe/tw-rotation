"""社群貼文的「資料是不是當天」把關（2026-10-26，Andy：「確保數據都是當天訊息」）。

純函式、不連網、不依賴 Playwright／PyYAML（社群工作流只裝 playwright、pillow、requests），
social_snap.py 與 tests/test_social_gate.py 共用。

交易日怎麼判斷（不用 weekday 硬猜）
------------------------------------
1. **已知休市日**：pipeline/calendar/tw_holidays.yaml（證交所公告的開休市日，例如 2026-10-26 光復節補假）。在表上 → 一定不是交易日。
2. **資料本身**：今天有沒有交易，看資料裡有沒有今天 —— 盤後看每張卡自己的資料日、盤中看即時報價回應裡的成交日 d。
   資料沒有今天 → 不當作交易日（寧可少發，不拿舊資料冒充）。
唯一用到「週末不開市」的地方是 next_open()：要算「下一個交易日幾點開盤」只能往未來推，未來還沒有資料可看，
所以用「休市日表＋週六日不開市」推算（證交所自 2017 年起補班日的週六也不開市）。
3. **臨時休市（颱風等，例：2026-10-23 颱風全日休市）**：靜態表事前不會有，所以以「即時成交日」為準 ——
   證交所 mis 即時報價（加權指數 tse_t00.tw）回應的成交日 d ＝ 現在手上最新的交易日（last_trade，live=True）。
   排定要開盤的日子過了 09:30 還沒有成交（last_trade 仍是更早的日子）→ 判定那天臨時休市，不是資料缺漏。
   09:00～09:30 之間分不出「還沒成交」與「休市」→ 保守不發。查不到即時成交日 → 只用靜態表（保守）。

三種貼文的規則
--------------
· 盤後法人（close）：每張卡的資料日都要＝今天（台北）且今天是交易日；任何一張不是今天 → 不發（結束碼 10），log 寫哪張是哪天。
· 盤後融資（credit）：融資隔天清晨才到齊，允許「最近一個已收盤的交易日」，但只在該資料日收盤後、下一個交易日 09:00 開盤前發。
· 盤中（intraday）：只在交易日 12:00–12:30（11:55 起可開跑，截圖前等到 12:00；一天一篇），而且即時報價的成交日要是今天。
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[1]
HOLIDAY_YAML = ROOT / "pipeline" / "calendar" / "tw_holidays.yaml"
OPEN_T, CLOSE_T = time(9, 0), time(13, 30)
INTRA_FROM, INTRA_TO = time(11, 55), time(12, 30)      # 盤中一天一篇、台北 12:00：11:55 起可開跑（截圖前等到 12:00），12:30 後不發
_LINE = re.compile(r'^\s*"?(\d{4}-\d{2}-\d{2})"?\s*:\s*\{\s*n\s*:\s*(.*?)\s*\}\s*$')


def load_holidays(path: Path | str | None = None) -> dict[str, str]:
    """讀休市日表 → {YYYY-MM-DD: 名稱}。讀不到回 {}（呼叫端照樣用資料判斷）。"""
    p = Path(path) if path else HOLIDAY_YAML
    out: dict[str, str] = {}
    try:
        for ln in p.read_text(encoding="utf-8").splitlines():
            m = _LINE.match(ln)
            if m:
                out[m.group(1)] = m.group(2)
    except OSError:
        pass
    return out


def _iso(x) -> str:
    """'2026-10-22'、'20261022'、'10/22'（不帶年不收）→ 'YYYY-MM-DD'；認不得回 ''。"""
    s = str(x or "").strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""


def trading_day(today: str, evidence: list | set | tuple, holidays: dict[str, str]) -> tuple[bool, str]:
    """今天是不是交易日：先看休市日表（在表上一定不是），再看資料裡有沒有今天（evidence＝資料日清單）。"""
    t = _iso(today)
    if t in holidays:
        return False, f"{t} 是休市日（{holidays[t]}）"
    ev = {_iso(x) for x in evidence or []}
    if t in ev:
        return True, f"資料裡有 {t} 的交易"
    return False, f"資料裡沒有 {t} 的交易（資料日：{'、'.join(sorted(x for x in ev if x)) or '無'}）"


def is_open_day(d: date, holidays: dict[str, str]) -> bool:
    """推算未來某天會不會開市（只給 next_open 用）：休市日表上的不開、週六日不開。"""
    return d.weekday() < 5 and d.isoformat() not in holidays


def next_open(data_date: str, holidays: dict[str, str]) -> datetime:
    """資料日之後的下一個交易日 09:00（台北）。"""
    d = date.fromisoformat(_iso(data_date)) + timedelta(days=1)
    for _ in range(40):
        if is_open_day(d, holidays):
            break
        d += timedelta(days=1)
    return datetime.combine(d, OPEN_T, TPE)


CONFIRM_T = time(9, 30)      # 排定開盤日過了這個時間還沒有成交 → 判定臨時休市


def closed_by_evidence(day: date, now: datetime, last_trade: str | None, live: bool) -> bool:
    """day（排定要開盤的日子）是不是臨時休市：即時成交日 last_trade 比 day 早，且 day 已過 09:30 確認時間。"""
    if not (live and last_trade):
        return False
    lt = _iso(last_trade)
    now = now.astimezone(TPE)
    return lt < day.isoformat() and now >= datetime.combine(day, CONFIRM_T, TPE)


def close_gate(today: str, card_dates: dict[str, str], holidays: dict[str, str],
               last_trade: str | None = None, live: bool = False, now: datetime | None = None) -> tuple[bool, str]:
    """盤後法人：每張卡的資料日都要＝今天，而且今天是交易日。card_dates＝{卡名: 資料日}（缺日期的卡＝不知道哪天，也不發）。
    last_trade／live：即時成交日（mis）。今天排定開盤、但即時成交日不是今天 → 臨時休市（不是資料缺漏），照樣不發。"""
    t = _iso(today)
    if not card_dates:
        return False, "讀不到任何一張卡的資料日"
    bad = {k: (_iso(v) or "沒有日期") for k, v in card_dates.items() if _iso(v) != t}
    if t not in holidays and now is not None and closed_by_evidence(date.fromisoformat(t), now, last_trade, live):
        return False, f"今天 {t} 臨時休市（即時成交日停在 {_iso(last_trade)}，例如颱風停市）—— 不是資料缺漏"
    ok_day, why = trading_day(t, [v for v in card_dates.values()], holidays)
    if not ok_day:
        if live and last_trade and _iso(last_trade) == t:
            why += "；但即時成交日是今天 → 今天有開盤，是資料還沒更新／缺漏"
        return False, f"今天不是交易日：{why}"
    if bad:
        return False, "這幾張的資料日不是今天 " + t + "：" + "、".join(f"{k}＝{v}" for k, v in bad.items())
    return True, ""


# 2026-10-29 事故：上市個股法人（FinMind）到 18:25 還沒出，盤後主貼文整段沒發 → 鐵則「沒有條件不符就不發」。
# 過了保底時間（預設台北 19:00，環境變數 CLOSE_FALLBACK_AT 可改）還有卡不是今天：拿掉過期的那幾張、當天的照發；
# 法人那幾張晚到再由 social_snap.py --supplement 另發一則補充（posted.json 另一個鍵 close-inst-<日期>）。
CLOSE_FALLBACK_AT = "19:00"
INST_CARDS = ("inst-today", "streak-foreign", "streak-trust")


def close_fallback(today: str, card_dates: dict[str, str], holidays: dict[str, str],
                   last_trade: str | None = None, live: bool = False, now: datetime | None = None,
                   fallback_at: str = "") -> tuple[bool, str, list[str]]:
    """盤後保底：回 (發不發, 說明, 要拿掉的卡)。

    只有這些情況才走保底：今天是交易日（休市日表＋至少一張卡是今天）、不是臨時休市、
    現在已過保底時間、至少還剩一張卡是今天。過期的卡（資料日不是今天）一律拿掉，絕不拿舊資料冒充今天。"""
    t = _iso(today)
    if now is None or not card_dates:
        return False, "沒有現在時間或沒有卡", []
    hm = (fallback_at or CLOSE_FALLBACK_AT).strip()
    now = now.astimezone(TPE)
    try:
        cut = datetime.combine(date.fromisoformat(t), datetime.strptime(hm, "%H:%M").time(), TPE)
    except ValueError:
        cut = datetime.combine(date.fromisoformat(t), datetime.strptime(CLOSE_FALLBACK_AT, "%H:%M").time(), TPE)
    if now < cut:
        return False, f"還沒到保底時間 {cut:%H:%M}", []
    if t in holidays:
        return False, f"{t} 是休市日（{holidays[t]}）", []
    if closed_by_evidence(date.fromisoformat(t), now, last_trade, live):
        return False, f"今天 {t} 臨時休市", []
    good = [k for k, v in card_dates.items() if _iso(v) == t]
    drop = [k for k, v in card_dates.items() if _iso(v) != t]
    if not good:
        return False, "沒有任何一張卡是今天的資料", drop
    if not drop:
        return True, "", []
    return True, (f"過了 {cut:%H:%M} 保底：拿掉資料日不是今天的 " + "、".join(f"{k}＝{_iso(card_dates[k]) or '沒有日期'}" for k in drop)
                  + "，其他 " + "、".join(good) + " 照發"), drop


def credit_gate(now: datetime, data_date: str, holidays: dict[str, str],
                last_trade: str | None = None, live: bool = False) -> tuple[bool, str]:
    """盤後融資：資料日收盤（13:30）之後、下一個交易日 09:00 之前才發；過了就不發舊的。
    last_trade／live：即時成交日（mis）。比資料日新 → 已有更新的交易日，不發；
    排定開盤日過了 09:30 還沒有成交 → 那天臨時休市（颱風），下一個交易日往後順延，資料日仍是最近一個已收盤的交易日。"""
    d = _iso(data_date)
    if not d:
        return False, "沒有融資資料日"
    if d in holidays:
        return False, f"融資資料日 {d} 是休市日（{holidays[d]}），資料有問題"
    now = now.astimezone(TPE)
    start = datetime.combine(date.fromisoformat(d), CLOSE_T, TPE)
    if now < start:
        return False, f"現在 {now:%m/%d %H:%M} 還沒到資料日 {d} 收盤"
    lt = _iso(last_trade) if last_trade else ""
    if lt and lt > d:
        return False, f"即時成交日 {lt} 比融資資料日 {d} 新（已有更新的交易日）→ 舊資料不發"
    end = next_open(d, holidays)
    skipped = []
    # 排定的開盤日已過確認時間、即時成交日仍停在資料日 → 那天臨時休市，往後順延
    while now >= end and closed_by_evidence(end.date(), now, last_trade, live) and len(skipped) < 20:
        skipped.append(end.date().isoformat())
        end = next_open(end.date().isoformat(), holidays)
    note = f"（{'、'.join(skipped)} 臨時休市：即時成交日停在 {lt}）" if skipped else ""
    if now >= end:
        if live and lt == d and now < datetime.combine(end.date(), CONFIRM_T, TPE):
            return False, f"{end:%m/%d} 已到開盤時間但還沒有成交，分不出是還沒成交還是臨時休市 → 先不發{note}"
        if not live:
            return False, f"融資資料日 {d} 的下一個交易日（照休市日表推算）已在 {end:%m/%d %H:%M} 開盤，查不到即時成交日、無法確認是否臨時休市 → 不發"
        return False, f"融資資料日 {d} 的下一個交易日已在 {end:%m/%d %H:%M} 開盤 → 舊資料不發{note}"
    return True, f"可發到 {end:%m/%d %H:%M}（下一個交易日開盤）{note}"


def intraday_gate(now: datetime, quote_dates, holidays: dict[str, str], check_quotes: bool = True) -> tuple[bool, str]:
    """盤中：交易日 09:00–13:30，且即時報價成交日是今天。check_quotes=False＝還沒截圖、先只看時段與休市日表。"""
    now = now.astimezone(TPE)
    t = now.date().isoformat()
    if t in holidays:
        return False, f"{t} 是休市日（{holidays[t]}）"
    if not (INTRA_FROM <= now.time() <= INTRA_TO):
        return False, f"現在台北 {now:%H:%M} 不在盤中發文時段 12:00～12:30（一天一篇）"
    if not check_quotes:
        return True, ""
    qd = {_iso(x) for x in quote_dates or []}
    if not qd:
        return False, "沒有讀到任何即時報價的成交日"
    if t not in qd:
        why = f"即時報價的成交日 {'、'.join(sorted(qd))} 不是今天 {t}"
        if now.time() >= CONFIRM_T:
            why += "（今天臨時休市，例如颱風停市）"
        return False, why
    return True, ""
