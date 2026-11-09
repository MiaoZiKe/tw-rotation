"""回覆專用安全閘（2026-11-09，自動回覆 A／B 層共用）。

貼文用的 scripts/threads_lint.py 管的是「整篇貼文」（開頭問句、500 字、標籤），不適合 30～80 字的回覆；
這支只管回覆，但重用它的網址偵測（has_url）、個股名單（stock_in）與時機字（AUTO_TIMING）。

check(text, recent) → 錯誤清單（空＝可以送）。紅線：
  1. 長度 30～80 字（不算空白換行）
  2. 不帶網址、不導流（網站、追蹤我、私訊、連結、主頁……）
  3. 不預測漲跌、不給進場時機、不喊單（會漲、上看、目標價、買點、加碼、抄底、梭哈、穩賺……）
  4. 不點名個股（stock_in；只要出現個股簡稱或 4 碼代號就擋 —— 寧可錯殺，回覆用族群／指數講就好）
  5. 黑名單字（髒話、政治、人身攻擊；reply_quota.json 的 blacklist 可再加）
  6. 不貼模板句（感謝分享、說得好、推推、學到了……）；跟最近 50 則已送回覆太像（字元二元組 Jaccard ≥ 0.5）也擋
skip_reason(text) → 對方留言／原串本身該不該跳過（政治、謾罵、未證實指控、詐騙廣告）；回空字串＝可以回。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_lint as TL  # noqa: E402

MIN_LEN, MAX_LEN = 30, 80
SIM_MAX = 0.5
PROMO = ("網站", "官網", "網址", "連結", "link", "追蹤我", "追蹤一下", "私訊", "私我", "主頁", "頁面看", "我的貼文", "我們的貼文",
         "哩股", "liguligu", "免費領", "加賴", "LINE群", "群組", "訂閱", "+1", "留言領")
PREDICT = ("會漲", "會跌", "必漲", "必跌", "看漲", "看跌", "噴出", "大漲在即", "要噴", "上看", "下看", "目標價", "漲到", "跌到",
           "買進", "賣出", "加碼", "減碼", "抄底", "接刀", "梭哈", "all in", "歐印", "穩賺", "保證", "明牌", "飆股", "存股首選",
           "可以買", "趕快買", "快賣", "停損", "停利", "撿便宜", "上車", "下車") + TL.AUTO_TIMING
ABUSE = ("幹你", "幹爆", "操你", "靠北", "白痴", "白癡", "智障", "腦殘", "去死", "畜生", "王八", "低能", "8+9", "廢物")
POLITICS = ("民進黨", "國民黨", "民眾黨", "賴清德", "柯文哲", "侯友宜", "鄭麗文", "黃國昌", "川普", "習近平", "共匪", "台獨", "罷免", "選舉",
            "綠營", "藍營", "白營")
BLACK = ABUSE + POLITICS + ("韭菜", "垃圾股", "割韭菜")      # 我們自己的回覆一律不准出現
TEMPLATE = ("感謝分享", "謝謝分享", "說得好", "說得對", "推推", "推一個", "學到了", "受教了", "同意樓上", "好文", "已追蹤", "互追",
            "大推", "太強了", "讚讚")
CODE_RE = re.compile(r"(?<![\d.])\d{4}[A-Z]?(?![\d.%％年])")
SKIP_ACCUSE = ("詐騙", "坑殺", "割韭菜", "內線", "炒作", "掏空", "作帳", "主力倒貨", "老師帶單", "飆股群", "跟單", "保證獲利")


def clen(s: str) -> int:
    return len(re.sub(r"\s", "", s or ""))


def _bigrams(s: str) -> set[str]:
    t = re.sub(r"[\s，。！？、,.!?~～…「」]", "", s or "")
    return {t[i:i + 2] for i in range(len(t) - 1)}


def similarity(a: str, b: str) -> float:
    x, y = _bigrams(a), _bigrams(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def check(text: str, recent: list[str] | None = None, extra_black: list[str] | None = None) -> list[str]:
    t = (text or "").strip()
    err: list[str] = []
    n = clen(t)
    if not MIN_LEN <= n <= MAX_LEN:
        err.append(f"長度 {n} 字（要 {MIN_LEN}～{MAX_LEN}）")
    if TL.has_url(t) or re.search(r"https?://|www\.|\.com|\.tw\b", t, re.I):
        err.append("帶網址")
    low = t.lower()
    for w in PROMO:
        if w.lower() in low:
            err.append(f"導流／推銷字「{w}」")
    for w in PREDICT:
        if w in low:
            err.append(f"預測漲跌／時機／喊單字「{w}」")
    for w in tuple(BLACK) + tuple(extra_black or ()):
        if w and w in t:
            err.append(f"黑名單字「{w}」")
    for w in TEMPLATE:
        if w in t:
            err.append(f"模板句「{w}」")
    for nm in TL.stock_in(t)[:3]:
        err.append(f"點名個股「{nm}」")
    if CODE_RE.search(t):
        err.append("出現股票代號")
    if "#" in t or "＃" in t or "@" in t:
        err.append("回覆不放標籤或 @")
    for r in (recent or [])[-50:]:
        if similarity(t, r) >= SIM_MAX:
            err.append(f"跟最近的回覆太像：{r[:20]}…")
            break
    return err


def skip_reason(text: str, extra_black: list[str] | None = None) -> str:
    """對方的內容該不該跳過。回原因；空字串＝可以回。"""
    t = text or ""
    if not t.strip() or clen(t) < 2:
        return "空白或只有表情"
    for w in POLITICS:
        if w in t:
            return f"政治（{w}）"
    for w in ABUSE + tuple(extra_black or ()):
        if w and w in t:
            return f"謾罵／黑名單（{w}）"
    for w in SKIP_ACCUSE:
        if w in t:
            return f"未證實指控／帶單廣告（{w}）"
    if TL.has_url(t):
        return "對方帶網址（多半是廣告）"
    return ""
