"""新聞「數字照用、句子自己寫」（2026-11-02 法遵：`docs/marketing/diagnosis_1102/legal_tech_transparency.md` 6-2）。

事故：主題文章導言、盤前「📌 今日焦點」、盤中／盤後「📰 新聞焦點」把媒體摘要整句貼上（10-30 光寶科卡照貼經濟日報
「……每股純益3.27元，年增60%，締歷史新猷……」卻標「報導摘述」；盤前 91APP 那條也是原文句子）。
數字（公司、期間、營收、年增、EPS、日期、事件名）是事實沒有著作權；句子、選材、用語有。註明出處不等於授權。

這支只做兩件事：
  1. fact_parts(title, summary)：從一則新聞只取事實欄位（主體、事件類別、數字），用本站固定句型組「短標題」與「一句描述」；
     取不到就回空字串，呼叫端換下一則（不准退回原文句子）。
  2. verbatim_runs(posts, sources)：貼文與來源新聞原文連續 ≥ 15 個中文字相同 → 回傳那幾段（threads_lint／品質閘用）。
"""
from __future__ import annotations

import html
import re

CJK = re.compile(r"[一-鿿]")
VERBATIM_N = 15            # 連續幾個中文字相同就算照抄（CEO 11-02）

# 短標題可以帶的事件名：只收「看標題就確定」的財報類（法說會、財報、營收）；其他事件（合作、擴產、回應…）用規則猜動作
# 容易寫錯事實（試跑：「財報受惠股領軍」被寫成「旺矽公布財報」），所以不猜，短標題只寫主體。
EVENTS = [(r"法說", "法說會"), (r"財報|季報|營運成果|EPS|每股(?:純益|盈餘)", "財報"), (r"營收", "營收")]


def event_of(title: str) -> str:
    for pat, name in EVENTS:
        if re.search(pat, title or ""):
            return name
    return ""


def cjk_len(s: str) -> int:
    return len(CJK.findall(s or ""))


# 2026-11-02 CEO 退件（盤前卡「OpenAI奧特曼／使用率 5%」「Google／擬參與 1,850 億美元」看不懂發生什麼事）：
#   短標題必須是「主體＋事件動作」（「超微單日重挫11%」），只有主體名一律不收；
#   描述的數字必須帶著意義（「XX 營收 YY 億元」），「使用率 5%」「擬參與 1,850 億美元」這種脫離脈絡的數字片語不放。
ACTION = re.compile(
    r"漲|跌|挫|崩|飆|暴|彈|揚|走高|走低|收高|收低|拉抬|升|降|增|減|創|破|突破|擴|砸|投資|收購|併購|合併|入股|出售|發表|推出|展示|亮相|登場|公布|宣布|發布|上修|下修|"
    r"調升|調降|調漲|上調|下調|漲價|降價|加徵|課徵|禁|限|暫停|停|恢復|追回|簽|合作|攜手|結盟|聯手|拿下|贏得|獲|接單|出貨|量產|"
    r"擴產|建廠|設廠|裁員|請辭|辭職|卸任|接任|上任|上市|上櫃|掛牌|IPO|申請|募資|融資|發債|財報|營收|獲利|虧損|賺|賠|法說|股利|配息|除息|"
    r"降息|升息|利率|通膨|關稅|制裁|管制|罷工|遭駭|竊|事件|需求|報價|成長|衰退|新高|新低|上路|生效|啟動|鎖定|擬|布局|轉型|搶|"
    r"警告|示警|看好|看淡|預估|上看|喊|回應|澄清|否認|批准|核准|通過|否決|起訴|調查|罰|大選|選舉|失守|站上|站回|收復|翻紅|翻黑|"
    r"買|賣|買超|賣超|加碼|減碼|釋出|開出|交貨|供貨|缺貨|斷貨|延後|提前|取消|退出|進軍|跨足|切入|打入|開發|研發|導入|採用|訂購|下單")
# 有意義的數字標籤：財報／市場指標（metric_of）或可量測的名詞；否則要寫出是誰（標籤裡有公司／機構／指數名稱）的什麼動作
MEAS = re.compile(r"銷量|銷售|產能|產量|估值|市占|價格|報價|成本|規模|需求|出口|進口|金額|預算|罰款|薪資|人數|用戶|庫存|稅|利潤|現金流|"
                  r"支出|投資額|交易額|交易量|成交量|持股|股價|匯率|殖利率|指數|油價|金價|房價|物價|訂單|合約|營業額|業績")


_ALIAS = None


def _who_in(s: str) -> str:
    """s 裡寫到的主體：只認名單上的（台股簡稱、外國公司／機構名單、央行、商品）與英文專有名詞（Google、OpenAI），
    不用「開頭兩三個字接動詞」那種猜法（會把「估本季再成長」的「估本季」當主體）。沒有回空字串。"""
    import social_news as S
    global _ALIAS
    if _ALIAS is None:
        _ALIAS = sorted(set(S._alias(_names())) | set(S.ENT) | set(S.INST), key=len, reverse=True)
    for v in _ALIAS:
        if len(v) >= 2 and v in s:
            return v
    m = re.search(S.BANKS, s) or re.search(S.COMMOD, s)
    if m:
        return m.group(0)
    for m in re.finditer(r"(?<![A-Za-z])([A-Z][A-Za-z0-9&.]{1,20})(?![A-Za-z])", s):
        if m.group(1) not in S.ENG_STOP:
            return m.group(1)
    return ""


def has_action(short: str) -> bool:
    """短標題是「主體＋事件動作」：拿掉主體名與英數字後，還要有一個事件動作字（漲跌、公布、收購、財報…）。
    「OpenAI奧特曼」「Google」這種只有名字的不算。"""
    w = _who_in(short)
    rest = short.replace(w, "") if w else short
    rest = re.sub(r"[A-Za-z0-9.,%\s]+", "", rest)
    return bool(ACTION.search(rest))


def meaningful_label(lab: str) -> bool:
    """數字標籤看得出意義：是財報／市場指標或可量測的名詞（營收、銷量、市值…），或寫了「主體＋動作」（「英特爾崩」）。
    「使用率」「擬參與」這種看不出是誰的什麼 → False。"""
    import social_news as S
    if S.metric_of(lab) or MEAS.search(lab):
        return True
    w = _who_in(lab)
    return bool(w) and cjk_len(lab.replace(w, "")) >= 1 and bool(ACTION.search(lab.replace(w, "")) or re.search(S.GROWTH, lab))


_NAMES = None


def _names() -> dict:
    global _NAMES
    if _NAMES is None:
        try:
            import social_news as S
            _NAMES = S.names_map()
        except Exception:  # noqa: BLE001
            _NAMES = {}
    return _NAMES


# 標籤開頭的日期、連接詞、時間副詞拿掉（「30日盤中一度下跌」→「盤中一度下跌」、「起從 30%」整個不收）
LAB_HEAD = re.compile(r"^(?:\d{1,2}(?:/\d{1,2})?日?|今|昨|代價是|早盤更|更|起從|起|從|僅|約|達|為|但|並|且|也|則|其中)+")


# 只有動詞的標籤（「宣布完成 1,700 萬美元」「完成 10 億美元」）看不出是什麼數字 → 不收
VERB_ONLY = re.compile(r"^(?:宣布|正式|已|將|再)?(?:完成|獲得|取得|投資|募得|斥資|砸|達|突破|拿下|簽下|上看|估)$")


def _num_items(title: str, summary: str, subj: str, skip: str = "", k: int = 2) -> list[str]:
    """新聞裡「標籤＋數字＋單位」→ 本站格式「標籤 數字單位」（標籤開頭的主體拿掉，短標題已經寫了）。
    取標題與摘要第一句的數字（標題的優先），跳過 skip（短標題）裡已經寫到的數字；漲停家數、張數、名次這類不收。"""
    import social_news as S
    from news_legal import clean_ok
    first = re.split(r"[。\n]", summary or "", maxsplit=1)[0]
    sk = (skip or "").replace(",", "")
    out = []
    for x in S.numbers_of(title + "，" + first):
        if not clean_ok(x["label"]) or re.search(S.JUNK, x["label"]) or x.get("range"):
            continue
        v = re.sub(r"[^\d.]", "", x["value"])
        if not v or re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", sk):
            continue
        try:                       # 短標題已寫的數字換個寫法（標題「8836億美元」、內文「8835.81 億美元」）也算重複，不再列一次
            fv = float(v)
            if any(abs(fv - float(w)) <= max(abs(float(w)) * 0.01, 1e-9) for w in re.findall(r"\d+(?:\.\d+)?", sk)):
                continue
        except ValueError:
            pass
        lab = x["label"]
        if subj and lab.startswith(subj) and len(lab) > len(subj) + 1:
            lab = lab[len(subj):]
        lab = LAB_HEAD.sub("", lab).strip(" 的")
        lab = re.sub(r"^年(?=第|度|初|底|前)", "", lab)     # 11-04：「2026 年第三季毛利率」數字被吃掉剩「年第三季毛利率」→「第三季毛利率」
        if cjk_len(lab) < 2 or re.search(r"\d", lab) and cjk_len(lab) < 3 or VERB_ONLY.match(lab):
            continue
        if not meaningful_label(lab if not subj else subj + lab):      # 主體在短標題，標籤加回主體再判斷（「營收」→「三星營收」）
            continue
        sep = "" if x["unit"] == "%" else " "
        out.append(f"{lab} {x['value']}{sep}{x['unit']}")
        if len(out) >= k:
            break
    return out


SHORT_CJK_MAX = VERBATIM_N - 1     # 標題短句最多 14 個中文字（短語、標題片段；到 15 就算照抄，改由主體組短標題）


def fact_parts(title: str, summary: str = "", short: str = "", codes: str = "", dl: int = 40) -> tuple[str, str]:
    """(短標題, 一句描述)，不放任何媒體摘要句子：
    短標題＝呼叫端從標題取的第一個短句（short），但中文字 ≥ 15 個就不用，改成「主體（＋財報／營收／法說會）」；
    描述＝新聞裡的數字，用本站格式「標籤 數字單位」，最多 2 個、跳過短標題已經寫到的數字；沒有就空字串（只放短標題）。
    短標題是主體組出來的又沒有數字（「輝達」一個詞）→ ("", "")，呼叫端換下一則。
    11-02 CEO 退件補：短標題必須「主體＋事件動作」（has_action）；描述的數字標籤必須看得出意義（meaningful_label）。"""
    import social_news as S
    t = S.sanitize(re.sub(r"\s+", " ", html.unescape(str(title or ""))).strip())
    sm = S.sanitize(re.sub(r"\s+", " ", html.unescape(str(summary or ""))).strip())
    built = False
    short = (short or "").strip()
    if not short or cjk_len(short) > SHORT_CJK_MAX:
        c = {"lead": {"title": t, "summary": sm, "codes": codes or ""}, "text": t + "，" + sm, "group": []}
        try:
            subj = re.sub(r"\s+", "", S.subject_of(c, _names())[0] or "")
        except Exception:  # noqa: BLE001
            subj = ""
        if not subj or len(subj) > 12:
            return "", ""
        ev = event_of(t)
        if not ev or ev in subj:
            return "", ""              # 只有主體名（「Google」「OpenAI奧特曼」）一律不收，換下一則（11-02 CEO 退件）
        short, built = f"{subj}{ev}", True
    subj0 = re.sub(r"(財報|營收|法說會)$", "", short) if built else ""
    nums = _num_items(t, sm, subj0, skip=short)
    desc = ""
    for i in range(len(nums), 0, -1):          # 放不下就少放一個數字（整項放，不截半個數字）
        d = "、".join(nums[:i])
        if len(d) <= dl:
            desc = d
            break
    if built and not desc:
        return "", ""              # 主體＋財報兩個詞、沒有數字＝沒有內容，不自己編動作句，換下一則
    if not built and not has_action(short):
        return "", ""              # 標題短句只有名字、沒有事件動作（「OpenAI奧特曼」）→ 換下一則
    if not desc:
        # 只有短標題：至少要看得出主體（公司／機構／指數／商品），「兩晚興奮到失眠」「2027年上路」這種標題鉤子不收
        try:
            who = S.subject_of({"lead": {"title": short, "summary": "", "codes": ""}, "text": short, "group": []}, _names())[0]
        except Exception:  # noqa: BLE001
            who = ""
        if not who or who not in short:
            return "", ""
    return short, desc


# ---------------- 照抄檢查 ----------------
def _vnorm(s: str) -> str:
    s = re.sub(r"https?://\S+", "", str(s or ""))
    # 只統一全形／半形（，↔,　；↔;　：↔:　（）↔()　％↔%）；「、」「。」跟「，」不同就算斷開——本站句型用「、」串數字，
    # 才不會把「營收 250 億美元、年增 90%」跟原文「營收250億美元，年增90%」兩個事實並列誤判成照抄
    s = s.replace("％", "%").translate(str.maketrans({"，": ",", "；": ";", "：": ":", "（": "(", "）": ")"}))
    return re.sub(r"[\s　▪・]+", "", s)


def verbatim_runs(posts: list[str] | str, sources: list[str], n: int = VERBATIM_N) -> list[str]:
    """貼文裡跟任一則來源原文「連續一模一樣、而且含 ≥ n 個中文字」的片段（空白拿掉、全半形標點統一；數字與標點照比，
    所以「營收574億元，季增9%，締歷史新猷」這種照抄抓得到；本站句型用「、」串數字，跟原文的「，」不同不會誤判）。"""
    if isinstance(posts, str):
        posts = [posts]
    srcs = [_vnorm(x) for x in sources if x and str(x).strip()]
    if not srcs:
        return []
    out: list[str] = []
    for t in posts:
        p = _vnorm(t)
        i = 0
        while i < len(p):
            if not CJK.match(p[i]):
                i += 1
                continue
            j = i + 1
            while j <= len(p) and any(p[i:j] in s for s in srcs):
                j += 1
            seg = p[i:j - 1]
            if len(CJK.findall(seg)) >= n:
                out.append(seg[:40])
                i = j - 1
            else:
                i += 1
    return list(dict.fromkeys(out))
