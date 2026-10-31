"""Threads 發文規則程式化檢查器（2026-11-01 Andy：「將發文 Thread 系統修改」＋「Threads 發文規則」，
規則全文見 docs/marketing/social_unit/threads_rules.md）。

檢查一篇 v2 貼文（JSON：hook_type, emotion, main_post, thread_posts, reply_post, image_count, tag …）：
  1. 主文 30–80 字（標點也算、換行不算、標籤不算），整則 ≤150；串文最多 6 則、每則 30–150（2026-11-01 CEO 改：超過 80 不再警告）
  2. 開頭類型恰為 對話／冷知識／反差；情緒恰為 好笑／吐槽
  3. 禁用字詞（客套結尾、私訊、連結在留言、喊單字）；主文不得有網址
  4. 第一句完整（≥10 字）；主文結尾不是句號（用感嘆或停在半句）
  5. 主文問句（「」裡的對話除外）必須具體：二選一（還是）或帶數字
  6. 圖 0 或 2 張；標籤恰 1 個、不在泛用黑名單、串文與留言不再掛標籤
  7. reply_post 恰 1 個網址

用法：
  python scripts/threads_lint.py <v2 JSON 檔 | manifest.json | queue .md> [...]
結束碼：任一篇有錯誤 → 1（只供人工或 CI 檢查；發文程式自己會改寫或換模板，不會因為 lint 不過就整篇不發）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HOOK_TYPES = ("對話", "冷知識", "反差")
EMOTIONS = ("好笑", "吐槽")
MAIN_MIN, MAIN_MAX, HARD_MAX = 30, 80, 150
THREAD_MIN, THREAD_TARGET = 30, 80
MAX_THREADS = 6            # 2026-11-01 CEO：主文＋≤6 串文＋1 則留言連結
# 客套結尾、導流、喊單（主文、串文、留言全部適用）
BANNED = ("歡迎留言", "謝謝大家", "留言告訴我", "你怎麼看", "私訊", "連結在留言", "連結在下方", "看留言", "買進", "加碼",
          "推薦", "快上車", "必買", "穩賺", "跟單", "抄底", "飆股", "報明牌", "目標價", "趕快買", "現在進場")
AI_TONE = ("綜上所述", "值得注意的是", "讓我們一起", "小編", "本文將", "總而言之", "親愛的")
GENERIC_TAGS = {"台股", "投資", "理財", "股票", "股市", "美股", "財經", "盤前", "盤中", "盤後", "資金流向", "熱力圖", "族群輪動",
                "法人買賣超", "外資", "投信", "台指期", "融資融券", "新聞", "財報", "科技", "總經", "國際", "經濟", "AI",
                "台股盤勢", "股票投資", "存股", "賺錢"}
URL_RE = re.compile(r"https?://|www\.|\.com\b|\.tw\b", re.I)
TAG_RE = re.compile(r"#[^\s#，。！？、：；]+")


def clen(s: str) -> int:
    """字數：標點也算、換行不算。"""
    return len((s or "").replace("\n", ""))


def split_tag(main: str) -> tuple[str, list[str]]:
    """回傳（不含標籤的主文, 標籤清單）。"""
    tags = [t[1:] for t in TAG_RE.findall(main or "")]
    body = TAG_RE.sub("", main or "").strip()
    return body, tags


def first_sentence(s: str) -> str:
    s = re.sub(r"「[^」]*」", lambda m: m.group(0).replace("。", "").replace("！", "").replace("？", ""), s)
    return re.split(r"[。！？!?…\n]", s, maxsplit=1)[0]


def lint(p: dict) -> tuple[list[str], list[str]]:
    """回傳（錯誤, 警告）。錯誤＝不符規則，發文程式會改寫或換模板。"""
    err: list[str] = []
    warn: list[str] = []
    if p.get("hook_type") not in HOOK_TYPES:
        err.append(f"開頭類型 {p.get('hook_type')!r} 不是 對話／冷知識／反差")
    if p.get("emotion") not in EMOTIONS:
        err.append(f"情緒 {p.get('emotion')!r} 不是 好笑／吐槽")
    main = p.get("main_post") or ""
    body, tags = split_tag(main)
    n = clen(body)
    if not MAIN_MIN <= n <= MAIN_MAX:
        err.append(f"主文 {n} 字（要 {MAIN_MIN}–{MAIN_MAX}）")
    if clen(main) > HARD_MAX:
        err.append(f"主文含標籤 {clen(main)} 字，超過 {HARD_MAX}")
    if URL_RE.search(main):
        err.append("主文有網址")
    fs = first_sentence(body)
    if clen(fs) < 10:
        err.append(f"第一句太短（{clen(fs)} 字）：{fs}")
    if body.endswith("。"):
        err.append("主文用句號收尾（要用感嘆或停在半句）")
    q = re.sub(r"「[^」]*」", "", body)
    for qs in re.findall(r"[^。！？!?…]*[？?]", q):
        if not re.search(r"還是|\d|幾|哪一?(個|檔|邊)", qs):
            err.append(f"問句太空泛：{qs}")
    for w in AI_TONE:
        if w in body:
            err.append(f"AI 腔／官方用語：{w}")
    allparts = [("主文", main)] + [(f"串文{i}", t) for i, t in enumerate(p.get("thread_posts") or [], 1)] + [("留言", p.get("reply_post") or "")]
    for where, t in allparts:
        for w in BANNED:
            if w in t:
                err.append(f"{where}有禁用字詞「{w}」")
    for i, t in enumerate(p.get("thread_posts") or [], 1):
        c = clen(t)
        if c > HARD_MAX:
            err.append(f"串文{i} {c} 字，超過 {HARD_MAX}")
        elif c < THREAD_MIN:
            err.append(f"串文{i} 只有 {c} 字（最少 {THREAD_MIN}）")
        if TAG_RE.search(t):
            err.append(f"串文{i} 又掛了標籤 {TAG_RE.findall(t)}")
        if URL_RE.search(t):
            err.append(f"串文{i} 有網址（網址只放留言）")
    if len(p.get("thread_posts") or []) > MAX_THREADS:
        err.append(f"串文 {len(p['thread_posts'])} 則（最多 {MAX_THREADS} 則）")
    rp = p.get("reply_post") or ""
    if len(re.findall(r"https?://", rp)) != 1:
        err.append("留言（reply_post）要恰好 1 個網址")
    if TAG_RE.search(re.sub(r"https?://\S+", "", rp)):
        err.append("留言又掛了標籤")
    if clen(rp) > 500:
        err.append("留言超過 500 字")
    ic = p.get("image_count")
    if ic not in (0, 2):
        err.append(f"配圖 {ic} 張（只能 0 或 2）")
    if len(tags) != 1:
        err.append(f"主文標籤 {len(tags)} 個（要恰好 1 個）")
    tag = (p.get("tag") or "").lstrip("#")
    if not tag:
        err.append("沒有標籤")
    elif tag in GENERIC_TAGS:
        err.append(f"標籤「{tag}」是泛用標籤，要用事件型話題")
    elif tags and tags[0] != tag:
        err.append(f"tag 欄位「{tag}」跟主文標籤「{tags[0]}」不一致")
    if tag and (len(tag) > 50 or re.search(r"[.&\s]", tag)):
        err.append(f"標籤格式不合（≤50 字、不含 . & 空白）：{tag}")
    return err, warn


def ok(p: dict) -> bool:
    return not lint(p)[0]


def _load(path: Path) -> list[tuple[str, dict]]:
    txt = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", txt, re.S)
        if not m:
            return []
        meta = dict(l.partition(":")[::2] for l in m.group(1).splitlines() if ":" in l)
        meta = {k.strip(): v.strip() for k, v in meta.items()}
        posts = [x.strip() for x in re.split(r"^-{5,}\s*$", m.group(2), flags=re.M) if x.strip()]
        imgs = [x for x in re.split(r"[\s,]+", meta.get("images", "")) if x]
        return [(path.name, dict(hook_type=meta.get("hook_type"), emotion=meta.get("emotion"), main_post=posts[0] if posts else "",
                                 thread_posts=posts[1:-1], reply_post=posts[-1] if len(posts) > 1 else "",
                                 image_count=len(imgs), tag=meta.get("tag", "")))]
    d = json.loads(txt)
    if "threads" in d and isinstance(d["threads"], dict):
        v2 = d["threads"].get("v2")
        return [(path.name, v2)] if v2 else [(path.name, {"main_post": d["threads"].get("text", "")})]
    if isinstance(d, list):
        return [(f"{path.name}[{i}]", x) for i, x in enumerate(d)]
    return [(path.name, d)]


def main(argv=None) -> int:
    bad = 0
    for a in (argv if argv is not None else sys.argv[1:]):
        for name, p in _load(Path(a)):
            e, w = lint(p)
            print(("✗ " if e else "✓ ") + name)
            for x in e:
                print("   錯誤：" + x)
            for x in w:
                print("   警告：" + x)
            bad += bool(e)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
