"""Threads 發文規則程式化檢查器（2026-11-01 Andy：「將發文 Thread 系統修改」＋「Threads 發文規則」，
規則全文見 docs/marketing/social_unit/threads_rules.md）。

檢查一篇 v2 貼文（JSON：hook_type, emotion, main_post, thread_posts, reply_post, image_count, tag …）：
  1. 主文第一段（鉤子）30–80 字（標點也算、換行不算、標籤不算）；整則主文 ≤500（Threads 上限，emoji 以位元組計）；
     串文 0 則、只剩 1 則留言放網址（2026-11-02 Andy：「都濃縮到第一頁」「下面留言太多了 盡可能都是在主業面就好」）
  2. 開頭類型恰為 對話／冷知識／反差；情緒恰為 好笑／吐槽
  3. 禁用字詞（客套結尾、私訊、連結在留言、喊單字）；主文不得有網址
  4. 第一句完整（≥10 字）；主文結尾不是句號（用感嘆或停在半句）
  5. 主文問句（「」裡的對話除外）必須具體：二選一（還是）或帶數字
  6. 圖：主題文章 0 或 1 張（11-02 Andy，數字卡併進封面）；主貼文 0 或 2 張；標籤恰 1 個、不在泛用黑名單、串文與留言不再掛標籤
  7. reply_post 恰 1 個網址
  8.（2026-11-02 CEO：盤前主題文章「台股融資融資約4200億元」那篇的生成瑕疵）
     同詞重複（「融資融資」「台股 台股」）、段落內容照抄前段（「和前期比」＝「重點數字」）、
     解讀只是重述數字（「下跌逾7%，代表…下跌約7%」）、分類與內容不符（講台股融資標成美股）、
     條件句被改寫成事實（原文「指數若跌破年線，融資恐需降至約4200億元」→ 鉤子當成已發生）

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
MAIN_MIN, MAIN_MAX, HARD_MAX = 30, 80, 150      # MAIN_MIN／MAIN_MAX 管的是主文第一段「鉤子」
THREAD_MIN, THREAD_TARGET = 30, 80
# 2026-11-02 Andy：「這頁不需要 都濃縮到第一頁，另外下面留言太多了 盡可能都是在主業面就好」
#   → 主文＝鉤子＋重點數據（用滿 Threads 單則 500 字上限）；串文 0 則；只剩 1 則留言放網址。
MAIN_LIMIT = 500           # Threads 單則上限（emoji 以 UTF-8 位元組計，tlen()）
MAIN_BUDGET = 490          # 產文用的目標上限，留 10 字餘裕
MAX_THREADS = 0            # 11-01 CEO 的「≤6 則串文」→ 11-02 Andy 改成全部進主文
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


def _is_emoji(c: str) -> bool:
    o = ord(c)
    return o >= 0x1F000 or 0x2190 <= o <= 0x2BFF or o in (0xFE0F, 0x200D, 0x20E3)


def tlen(s: str) -> int:
    """Threads 500 字上限的算法（同 threads_post._tlen）：emoji 以 UTF-8 位元組數計，其他字元（含換行）算 1。"""
    return sum(len(c.encode("utf-8")) if _is_emoji(c) else 1 for c in (s or ""))


def hook_of(body: str) -> tuple[str, str]:
    """主文（不含標籤）→（第一段鉤子, 其餘重點內容）。"""
    a, _, b = (body or "").strip().partition("\n\n")
    return a.strip(), b.strip()


def split_tag(main: str) -> tuple[str, list[str]]:
    """回傳（不含標籤的主文, 標籤清單）。"""
    tags = [t[1:] for t in TAG_RE.findall(main or "")]
    body = TAG_RE.sub("", main or "").strip()
    return body, tags


def first_sentence(s: str) -> str:
    s = re.sub(r"「[^」]*」", lambda m: m.group(0).replace("。", "").replace("！", "").replace("？", ""), s)
    return re.split(r"[。！？!?…\n]", s, maxsplit=1)[0]


# ---------------- 8. 內容品質（2026-11-02 CEO） ----------------
REPEAT_OK = {"一點", "一步", "一檔", "一個", "一家", "一天", "一季", "一年", "一月", "哈哈", "呵呵", "很長", "很多", "好多", "好久", "一再",
             "一次", "一波", "一層", "不斷", "越來"}       # 口語疊用（「很長很長」「一波一波」）不算重複
REPEAT_RE = re.compile(r"([一-鿿A-Za-z]{2,6})[\s　：:的]*\1")      # 「融資融資」「台股 台股」「亞馬遜的亞馬遜」


def dup_words(text: str) -> list[str]:
    """相鄰重複的詞（「融資融資」「台股 台股」）；「一點一點」這種疊字不算。"""
    out = []
    for line in (text or "").splitlines():
        line = re.sub(r"https?://\S+|www\.\S+", "", line)
        for m in REPEAT_RE.finditer(line):
            w = m.group(1)
            if w in REPEAT_OK or not re.search(r"[一-鿿]", w):
                continue
            if re.search(r"[：:]", m.group(0)) and len(line) > 40:
                continue          # 內文的「美國非農就業：非農就業反映…」是先點名再解釋；標題行（短）才算重複
            out.append(m.group(0))
    return list(dict.fromkeys(out))


def _norm_line(s: str) -> str:
    s = re.sub(r"（[^）]*(報導|來源|換算|計算|摘述)[^）]*）", "", s)
    return re.sub(r"[^一-鿿A-Za-z0-9.%]", "", s)


HEAD_LINE = re.compile(r"^\S{1,2}\s*#?[^\s▪・]{2,14}$")      # 「📊 重點數字」這種段名行


def dup_lines(posts: list[str]) -> list[str]:
    """後面段落照抄前面段落的內容（整行一樣），或解讀句只是把前面的數字再講一次（「X，代表…」的 X 前面已經列過）。
    第一則的第一行是標題，標題跟「重點數字」第一條同一個數字是正常的，不算照抄。"""
    seen: set[str] = set()
    out = []
    for pi, t in enumerate(posts):
        for li, raw in enumerate((t or "").splitlines()):
            if pi == 0 and li == 0:
                continue
            line = raw.strip().lstrip("▪・").strip()
            if not line or HEAD_LINE.match(raw.strip()):
                continue
            for sent in re.split(r"(?<=。)", line):
                n = _norm_line(sent)
                if len(n) < 6:
                    continue
                if n in seen:
                    out.append(f"照抄前段：{sent.strip()[:40]}")
                    continue
                if "代表" in sent:
                    a, b = sent.split("代表", 1)
                    pre = _norm_line(a)
                    nums = NUM_RE.findall(a)
                    same = bool(nums) and all(re.search(r"(?<![\d.])" + re.escape(re.sub(r"\.0+$", "", v)) + r"(?![\d])", b) for v in nums)
                    if len(pre) >= 6 and pre in seen and same and re.search(r"相比|較|增加|減少|上漲|下跌|成長|衰退", b):
                        out.append(f"解讀只是重述數字：{sent.strip()[:40]}")
                seen.add(n)
    return out


CAT_KW = {
    "台股": r"台股|加權指數|加權|大盤|上市櫃|集中市場|櫃買|融資|融券|三大法人|台指期|年線|半年線|季線|月線",
    "美股": r"美股|道瓊|那斯達克|標普|費半|費城半導體|S&P|Nasdaq|輝達|NVIDIA|微軟|蘋果|Apple|Alphabet|Google|Meta|亞馬遜|特斯拉|博通|超微|AMD|甲骨文|美國",
}


def cat_mismatch(cat: str, title: str, body: str = "") -> str:
    """分類（topic_category）跟內容對不起來：只比台股／美股這組最容易混的。標題有判定力就看標題，標題都沒有再看導言多數。"""
    if cat not in CAT_KW:
        return ""
    other = "美股" if cat == "台股" else "台股"
    t_self, t_other = len(re.findall(CAT_KW[cat], title or "")), len(re.findall(CAT_KW[other], title or ""))
    if t_self == 0 and t_other > 0:
        return f"分類「{cat}」但標題講的是{other}：{(title or '')[:30]}"
    if t_self == 0 and t_other == 0 and body:
        b_self, b_other = len(re.findall(CAT_KW[cat], body)), len(re.findall(CAT_KW[other], body))
        if b_other >= b_self + 2:
            return f"分類「{cat}」但內容多在講{other}（{b_other} 比 {b_self}）"
    return ""


COND_W = r"若|如果|一旦|假如|萬一|倘若|假設"
COND_RESULT = r"恐|才|將|會|需|可能|就|降至|升至|上看|下看"
SPEC_W = r"恐|可能|預估|估計|估|可望|或將|有望|預期|料將|上看"
HEDGE_COND = r"若|如果|一旦|假如|萬一|倘若|假設|前提|條件|情境|推估"
HEDGE_SPEC = HEDGE_COND + "|" + SPEC_W
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _nkey(v: str) -> str:
    return v.replace(",", "")


def conditional_numbers(text: str) -> dict[str, str]:
    """{數字: "cond"／"spec"}：數字所在子句前面（同一句）有「若／如果／一旦…」→ cond；子句本身有「恐／可能／預估…」→ spec。"""
    out: dict[str, str] = {}
    for sent in re.split(r"[。！？\n；]", text or ""):
        prev_cond = False
        for cl in re.split(r"[，,]", sent):
            here = bool(re.search(COND_W, cl))
            cond = (here or prev_cond) and bool(re.search(COND_RESULT, cl) or here)   # 條件只管同一子句與緊接的「結果」子句
            prev_cond = here
            kind = "cond" if cond else ("spec" if re.search(SPEC_W, cl) else "")
            if not kind:
                continue
            for v in NUM_RE.findall(cl):
                if len(_nkey(v)) >= 2 and out.get(_nkey(v)) != "cond":
                    out[_nkey(v)] = kind
    return out


def cond_as_fact(main: str, source: str) -> list[str]:
    """主文用了原文裡「有條件／推估」的數字，卻沒帶出條件或推估語氣 → 把條件句改寫成事實。"""
    cn = conditional_numbers(source)
    body = split_tag(main)[0]
    out = []
    for v in NUM_RE.findall(body):
        k = cn.get(_nkey(v))
        if k == "cond" and not re.search(HEDGE_COND, body):
            out.append(f"主文把條件句寫成事實：原文 {v} 有前提條件（若／一旦…），主文沒寫")
        elif k == "spec" and not re.search(HEDGE_SPEC, body):
            out.append(f"主文把推估寫成事實：原文 {v} 是推估（恐／預估…），主文沒寫")
    return out


def content_issues(posts: list[str], category: str = "", title: str = "") -> list[str]:
    """串文內容檢查（主題文章產稿的品質閘也用這支）：同詞重複、照抄前段、解讀只重述、分類不符。"""
    err = [f"同詞重複「{w}」" for w in dup_words("\n".join(posts))]
    err += dup_lines(posts)
    if category:
        first = title or ((posts[0].splitlines() or [""])[0] if posts else "")
        first = re.split(r"[｜|]", first, maxsplit=1)[0]          # 「｜」後面是分類標籤＋小問句，不算標題內容
        c = cat_mismatch(category, first, "\n".join(posts[:2]))
        if c:
            err.append(c)
    return err


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
    hook, rest = hook_of(body)
    n = clen(hook)
    if not MAIN_MIN <= n <= MAIN_MAX:
        err.append(f"主文鉤子 {n} 字（要 {MAIN_MIN}–{MAIN_MAX}）")
    if tlen(main) > MAIN_LIMIT:
        err.append(f"主文 {tlen(main)} 字，超過 Threads 上限 {MAIN_LIMIT}")
    if URL_RE.search(main):
        err.append("主文有網址")
    fs = first_sentence(hook)
    if clen(fs) < 10:
        err.append(f"第一句太短（{clen(fs)} 字）：{fs}")
    if hook.endswith("。"):
        err.append("主文鉤子用句號收尾（要用感嘆或停在半句）")
    q = re.sub(r"「[^」]*」", "", hook)
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
    kind = p.get("kind") or ""
    allow = (0, 1) if kind == "article" else (0, 2) if kind else (0, 1, 2)   # 11-02 Andy：主題文章只留 1 張；主貼文照 11-01 的 0 或 2
    if ic not in allow:
        err.append(f"配圖 {ic} 張（只能 {' 或 '.join(map(str, allow))}）")
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
    # 8. 內容品質（2026-11-02）：主文同詞重複、條件句改寫成事實；串文同詞重複／照抄前段／解讀只重述／分類不符
    err += [f"主文同詞重複「{w}」" for w in dup_words(hook)]
    err += cond_as_fact(hook, "\n".join([rest] + list(p.get("thread_posts") or [])))
    err += content_issues([x for x in [rest] + list(p.get("thread_posts") or []) if x], p.get("category") or p.get("topic_category") or "")
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
                                 image_count=len(imgs), tag=meta.get("tag", ""), category=meta.get("topic_category", ""),
                                 kind="article" if "_news-" in path.name else ""))]
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
