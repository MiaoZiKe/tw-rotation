"""頻道②「科技透明圈」留言關鍵字：每篇貼文的專屬關鍵字與回覆內容（2026-11-15）。

Andy 原話：「往後製作影片後面可以補上 留言『XXXX』我就把資訊傳給他，IG Thread 都是」。

設定都在 social/tc/dm_config.json（不放在 post.md），理由：
  ① 讀的人有三個：scripts/tc_threads_replies.py、scripts/tc_ig_dm.py、workers/tc-dm（Worker 從 GitHub 讀 dm_config.json，
     讀不到佇列裡的 post.md）；放同一個檔，三邊不會各講各的。
  ② 關鍵字和它要回的內容（文章連結）擺在一起，法遵一次看完全部對外文案。
  ③ 貼文發出前、發出後都能改（post.md 發完會被程式回寫，人工再改容易撞到）。

規則：
  - 全域 keywords（第一版「透明」）：任何一篇的留言含這個字都會觸發，回該篇的內容（沒有就回 default）。
  - post_keywords[<貼文代號>]：只在那一篇觸發。貼文代號＝佇列資料夾名稱（例 20261122_2nm），
    也可以只寫日期後面的那段（例 2nm）—— 影片還沒排進佇列、不知道哪天發時先用這種寫法。
  - 以「_」開頭的鍵是說明，不當代號。
  - 內容裡還有「待填」字樣（例如文章網址還沒拿到）→ 不送半成品，改送 default（保底，不會整段不回）。
  - legal_pending 列著的代號＝新文案還沒過法遵 → 一樣改送 default（已審過的那份）；法遵審過後把代號拿掉。
  - 防洗版（2026-11-15）：內容可以寫成 2～3 句意思相同、措辭不同的清單，用留言 id 的 sha256 決定用哪一句
    （固定、可重現：同一則留言永遠拿到同一句，不同留言平均分散）。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

PLACEHOLDER = "待填"
CTA_RE = re.compile(r"留言「([^」]+)」")


def norm(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s or "").lower().split())


def slug(post: str) -> str:
    """20261122_2nm → 2nm；沒有日期前綴就原樣。"""
    m = re.match(r"^\d{8}_(.+)$", post or "")
    return m.group(1) if m else (post or "")


def pick(table: dict | None, post: str):
    """依「完整代號 → 日期後那段」找；以 _ 開頭的鍵不算。找不到回 None。"""
    t = {k: v for k, v in (table or {}).items() if not str(k).startswith("_")}
    for k in (post, slug(post)):
        if k and k in t:
            return t[k]
    return None


def keywords_for(cfg: dict, post: str | None) -> list[str]:
    """這篇貼文的留言要比對哪些字：全域＋這篇專屬。"""
    kws = list(cfg.get("keywords") or [])
    own = pick(cfg.get("post_keywords"), post or "") if post and post != "default" else None
    if isinstance(own, str):
        own = [own]
    return kws + [k for k in (own or []) if k not in kws]


def has_kw(text: str, kws) -> bool:
    t = norm(text)
    return any(norm(k) and norm(k) in t for k in kws or [])


def ready(text) -> bool:
    if isinstance(text, list):
        return bool(text) and all(ready(x) for x in text)
    return bool(text) and PLACEHOLDER not in str(text)


def rotate(v, key: str = "") -> str:
    """清單 → 依 key（留言 id）的 sha256 取一句；字串原樣回。"""
    if not isinstance(v, list):
        return v or ""
    if not v:
        return ""
    return v[int(hashlib.sha256(str(key).encode()).hexdigest(), 16) % len(v)]


def in_pending(post: str | None, pending) -> bool:
    return bool(post) and any(x in (pending or []) for x in (post, slug(post)))


def text_for(table: dict | None, post: str | None, fallback, pending=None, key: str = "") -> str:
    """這篇要回的內容；沒設、還有「待填」、或代號在 legal_pending（還沒過法遵）→ 用 fallback（default）。
    內容是清單時用 key（留言 id）輪流挑一句。"""
    v = pick(table, post or "") if post and post != "default" else None
    return rotate(v if ready(v) and not in_pending(post, pending) else fallback, key)


def cta_keywords(text: str) -> list[str]:
    """文案裡「留言「X」」的 X（交件檢查用）。"""
    return CTA_RE.findall(text or "")


def with_unlock(text: str, code: str) -> str:
    """私訊專用：把網站連結改成帶頻道憑證 https://liguligu-puipui.com/?tc=碼#article/…（2026-11-16 Andy：
    追蹤＋註冊的人才能看頻道全部文章）。碼來自環境變數 TC_UNLOCK_CODE（GitHub Secret），repo 只放它的 sha256
    （site/articles/unlock.json）。沒碼就原樣回傳＝連結只能看單篇。已帶 ?tc= 的不重複加；公開回覆（Threads／IG 留言）不要用這個。"""
    import re
    if not code or not re.fullmatch(r"[\w-]{4,40}", code):
        return text
    return re.sub(r"https://liguligu-puipui\.com/(?!\?tc=)", "https://liguligu-puipui.com/?tc=" + code, text)
