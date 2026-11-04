"""Threads 發文 v2（2026-11-01 Andy：「CEO 交給對應單位 將發文 Thread 系統修改」「在 IG Thread 上面也需要進行優化
讓熱度提升，並且 盡量不要千篇一律的方式要有點變化」；規則全文 docs/marketing/social_unit/threads_rules.md）。

★ 2026-11-02 Andy：「這頁不需要 都濃縮到第一頁，另外下面留言太多了 盡可能都是在主業面就好」
  → 主文＝鉤子（第一段 30–80 字）＋重點數據（標題、重點數字、代表什麼、接下來觀察…），用滿 Threads 單則 500 字；
    串文 0 則；只剩 1 則留言放網址（＋「完整盤勢見網站」）。放不下依序拿掉次要段落（fit(budget=…)）。
    主題文章圖只留 1 張（實景封面，數字卡不再產生）；主貼文圖照舊 0 或 2 張。
★ 2026-11-03 Andy：「首先 網頁都不公開先，人數沒有起來，沒有建立信任關係，我覺得不妥」
  → 留言只放「以上為公開資料整理，非投資建議」，不放網址、不放「完整盤勢見網站」（threads_lint.PROMOTE_SITE=False）。
★ 2026-11-04 Andy：「要，盤後也改成專業語氣」（11-05 盤後起生效）
  → 鉤子模板全部換成專業的「吊胃口問句」（用當天數據帶入，例：「外資連 5 日賣超、累計 5,120 億，這一波和前幾次有什麼不同？」），
    蓋掉下面「對話／冷知識／反差＋好笑／吐槽」：輸出 hook_type="問句"、emotion="專業"、profile="auto"（threads_lint 自動貼文模式：
    開頭須為問句、擋口語吐槽字）；切入角度（數據／對比／趨勢）存 angle 供輪替，14 天不重複照舊。條列裡帶口語字的新聞行不放進主文。
  下面是 11-01 的原始設計（串文 ≤6 則那段已被上面取代；鉤子類型與情緒已被 11-04 取代）。

把原本一整篇的盤前／盤中／盤後／主題文章文案，改成：
  main_post   主文 30–80 字：鉤子（對話／冷知識／反差）＋情緒（好笑／吐槽）＋恰 1 個事件型標籤，不放網址
  thread_posts 串文：原本的盤勢、族群、新聞焦點、相關公司同類合併，**最多 6 則**、每則目標 80～130 字、硬上限 150
               （2026-11-01 CEO：10～12 則太長）；放不下的次要數據精簡，留言那則寫「完整盤勢見網站」
  reply_post  留言串最後一則：網站連結（帶 ?u= 來源參數）
  圖 0 或 2 張（主貼文從原本的卡片挑最強的 2 張）

鉤子不千篇一律：模板庫 HOOKS（三種開頭各 ≥15 個、好笑與吐槽都有），依當天數據自動填；
  同一類型不連續用、同一模板 14 天內不重複（狀態檔：主貼文在 social-snaps 分支 state/hook_history.json，
  主題文章在 repo social/news/log/hook_history.json）。
每篇都過 scripts/threads_lint.py；不過就換下一個模板，全部不過用保底模板，**絕不因為檢查不過就整篇不發**（CLAUDE.md 10-29）。
Actions 上沒有 LLM 金鑰（workflow 只引用 THREADS／IG／FINMIND 等），所以全部用模板＋規則組合，不呼叫任何 LLM。

用法（social-live.yml 在產完 manifest 後呼叫；出錯 continue-on-error，manifest 維持舊版照發）：
  python scripts/threads_v2.py --manifest <OUT>/manifest.json [--state hook_history.json] [--out-state <OUT>/hook_history.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from threads_lint import BANNED, GENERIC_TAGS, HARD_MAX, MAIN_BUDGET, MAIN_LIMIT, MAX_THREADS, THREAD_MIN, THREAD_TARGET, clen, content_issues, lint, split_tag, tlen  # noqa: E402,F401
import threads_lint as _TL  # noqa: E402  11-03 不放網址（PROMOTE_SITE／strip_urls／scrub_post）

TPE = timezone(timedelta(hours=8))
COOLDOWN_DAYS = 14
KIND_NAME = {"intraday": "盤中", "close": "盤後", "premarket": "盤前", "credit": "融資融券", "article": "這則新聞"}
# 喊單字在串文（新聞原句）出現時的自動改寫：保留事實、拿掉叫人買的語氣
REWRITE = {"買進": "買入", "加碼": "增持", "推薦": "點名", "目標價": "預估價", "飆股": "強勢股", "抄底": "低接",
           "私訊": "訊息", "跟單": "跟進", "穩賺": "看好", "快上車": "", "必買": "", "報明牌": "", "趕快買": "",
           "現在進場": "", "歡迎留言": "", "謝謝大家": "", "留言告訴我": "", "你怎麼看": "", "連結在留言": "", "連結在下方": "",
           "看留言": "看下一則"}

# ---------------------------------------------------------------- 鉤子模板庫
# (id, kind, 切入角度, 語氣, 模板, 條件)；kind="any" 是保底（只用 {kind_name}，任何資料都填得起來）
# 模板裡的 {xxx} 由 facts() 從當天數據取；缺任何一個欄位或條件不成立 → 這個模板今天不用。
def _neg(v):
    return isinstance(v, str) and v.strip().startswith(("-", "−"))


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("−", "-").replace("+", "").rstrip("%"))
    except (TypeError, ValueError):
        return None


def _ge(v, n):
    x = _num(v)
    return x is not None and x >= n


# ★ 2026-11-04 Andy：「要，盤後也改成專業語氣」（熱點文規則 threads_rules.md 最上面「2026-11-04 Andy 定案」一節）
#   → 64 個口語／吐槽舊模板（「朋友問…我只能默默拍拍他…」）全部換掉：開頭＝1 句吊胃口問句，用當天數據帶入，專業中性，
#     不用對話、第一人稱、感嘆、語助詞。第三欄改成「切入角度」（數據／對比／趨勢）供輪替（同角度不連續、同模板 14 天不重複）；
#     輸出的 hook_type 一律「問句」、emotion「專業」、profile「auto」（threads_lint 自動貼文模式）。
#   ★ 2026-11-05 CEO 法遵退件：開頭不點名個股（「買超第一名是旺矽，資金為什麼選它？」「外資賣超以台積電最多…」拿掉）、
#     不問時機（「能撐多久」→「過去通常出現在什麼盤勢」）；開頭只講指數、族群、法人總量、期貨、家數層級。
#     主題文章的 {subj} 若是公司名，lint 會擋下、自動改用保底模板（不點名）。
HOOKS = [
    # ---- 盤後 ----
    ("c_t1", "close", "趨勢", "專業", "外資連 {fx_streak} 日{fx_act}、累計 {fx_cum_r} 億，這一波和前幾次有什麼不同？", lambda f: _ge(f.get("fx_streak"), 3) and f.get("fx_cum_r")),
    ("c_t2", "close", "趨勢", "專業", "投信連 {trust_streak} 日{trust_act}、累計 {trust_cum_r} 億，和外資方向相反的買盤過去通常出現在什麼盤勢？", lambda f: _ge(f.get("trust_streak"), 3) and f.get("fx_act") and f.get("fx_act") != f.get("trust_act")),
    ("c_t3", "close", "趨勢", "專業", "外資今天{fx_act} {fx_amt_r} 億、已連 {fx_streak} 日，這股力道是在加速還是放緩？", lambda f: _ge(f.get("fx_streak"), 2)),
    ("c_t4", "close", "趨勢", "專業", "投信已連 {trust_streak} 日{trust_act}、今天再{trust_act} {trust_amt_r} 億，資金集中在哪幾個族群？", lambda f: _ge(f.get("trust_streak"), 5)),
    ("c_c1", "close", "對比", "專業", "加權指數{idx_dir} {idx_pts} 點，但漲停 {lim_up} 家、跌停只有 {lim_dn} 家，盤面透露什麼訊號？", lambda f: f.get("idx_dir") == "跌" and _num(f.get("lim_up")) >= 3 * max(_num(f.get("lim_dn")) or 0, 1)),
    ("c_c2", "close", "對比", "專業", "加權指數{idx_dir} {idx_pts} 點，跌停多達 {lim_dn} 家、漲停 {lim_up} 家，賣壓集中在哪一類股票？", lambda f: f.get("idx_dir") == "跌" and _num(f.get("lim_dn")) >= 2 * max(_num(f.get("lim_up")) or 0, 1)),
    ("c_c3", "close", "對比", "專業", "外資{fx_act} {fx_amt_r} 億，投信反向{trust_act} {trust_amt_r} 億，法人看法分歧的關鍵在哪裡？", lambda f: f.get("fx_act") and f.get("trust_act") and f.get("fx_act") != f.get("trust_act")),
    ("c_c4", "close", "對比", "專業", "加權指數{idx_dir} {idx_pts} 點，上漲家數卻只有 {adv} 家、下跌 {dec} 家，指數和個股為什麼走不同方向？", lambda f: f.get("idx_dir") == "漲" and _num(f.get("adv")) < _num(f.get("dec"))),
    ("c_c5", "close", "對比", "專業", "加權指數{idx_dir} {idx_pts} 點，上漲 {adv} 家、下跌 {dec} 家，跌勢是集中在權值股還是全面擴散？", lambda f: f.get("idx_dir") == "跌"),
    ("c_d1", "close", "數據", "專業", "只有 {above_ma} 的個股站在月線之上，這個比例代表市場走到哪個階段？", lambda f: (_num(f.get("above_ma")) or 100) < 40),
    ("c_d2", "close", "數據", "專業", "外資{fx_act}集中度偏高、單一最大檔就占當日{fx_act} {fx_top_share}，這次調整和前幾波有何不同？", lambda f: f.get("fx_top_share") and _ge(f.get("fx_top_share"), 15)),
    ("c_d3", "close", "數據", "專業", "外資{fut_act}台指期 {fut_lots} 口、淨{fut_side}來到 {fut_oi} 口，期貨布局透露什麼方向？", lambda f: f.get("fut_oi")),
    ("c_d4", "close", "數據", "專業", "外資{fx_act} {fx_amt_r} 億、投信{trust_act} {trust_amt_r} 億，兩大法人的資金各自流向哪些族群？", lambda f: f.get("fx_act") and f.get("trust_act")),
    ("c_d5", "close", "數據", "專業", "三大法人合計{tot_act} {tot_amt_r} 億、加權指數{idx_dir} {idx_pts} 點，這個量級在近期屬於什麼水準？", lambda f: f.get("tot_act")),
    ("c_d6", "close", "數據", "專業", "加權指數{idx_dir} {idx_pts} 點、幅度 {idx_pct_abs}，今天盤後最值得留意的是哪一個數字？", None),
    # ---- 盤中 ----
    ("i_c1", "intraday", "對比", "專業", "{n_all} 個族群只有 {n_up} 個上漲、族群平均 {avg}，盤中賣壓集中在哪一塊？", lambda f: _num(f.get("n_up")) * 2 < _num(f.get("n_all"))),
    ("i_c2", "intraday", "對比", "專業", "{n_all} 個族群有 {n_up} 個上漲、族群平均 {avg}，資金是全面回流還是集中在少數族群？", lambda f: _num(f.get("n_up")) * 2 >= _num(f.get("n_all"))),
    ("i_c3", "intraday", "對比", "專業", "{dn1}跌 {dn1p_abs}、{up1}漲 {up1p_abs}，同一個盤面為什麼分化這麼大？", lambda f: _neg(f.get("dn1p")) and not _neg(f.get("up1p"))),
    ("i_d1", "intraday", "數據", "專業", "盤中漲幅最大的是{up1}（{up1p}），這波漲勢是消息帶動還是資金輪動？", lambda f: not _neg(f.get("up1p"))),
    ("i_d2", "intraday", "數據", "專業", "盤中跌幅最大的是{dn1}（{dn1p}），是短線獲利了結還是基本面轉弱？", lambda f: _neg(f.get("dn1p"))),
    ("i_d3", "intraday", "數據", "專業", "族群平均 {avg}，{up1}卻逆勢 {up1p}，它和大盤走勢分開的原因在哪裡？", lambda f: _neg(f.get("avg")) and not _neg(f.get("up1p"))),
    ("i_t1", "intraday", "趨勢", "專業", "資金從{out1}流向{in1}，這次輪動背後是消息面還是籌碼面？", None),
    ("i_t2", "intraday", "趨勢", "專業", "資金輪盤上{lead1}領先、{lag1}落後，族群強弱是延續前幾天還是出現換手？", None),
    # ---- 盤前 ----
    ("p_d1", "premarket", "數據", "專業", "費半{sox_dir} {sox_pct}%、台指期夜盤 {tx_chg} 點，這兩個數字的方向一致還是分歧？", None),
    ("p_d2", "premarket", "數據", "專業", "費半一夜{sox_dir} {sox_pct}%，這個幅度放在近一個月的波動裡屬於大還是小？", None),
    ("p_d3", "premarket", "數據", "專業", "美股四大指數{us_all}、費半{sox_dir} {sox_pct}%，哪一個指數和台股半導體族群的連動最高？", lambda f: f.get("us_all")),
    ("p_c1", "premarket", "對比", "專業", "美股四大指數{us_all}，台指期夜盤只變動 {tx_chg} 點，夜盤和美股的反應為什麼一大一小？", lambda f: f.get("us_all") and (_num(f.get("tx_chg_abs")) or 999) < 150),
    ("p_c2", "premarket", "對比", "專業", "美股四大指數{us_all}，台指期夜盤卻變動 {tx_chg} 點，兩邊的落差來自哪個因素？", lambda f: f.get("us_all") and (_num(f.get("tx_chg_abs")) or 0) >= 150),
    ("p_t1", "premarket", "趨勢", "專業", "台指期夜盤收 {tx}、較日盤 {tx_chg} 點，夜盤的變動幅度在近期屬於大還是小？", None),
    # ---- 融資融券 ----
    ("r_d1", "credit", "數據", "專業", "上市融資維持率估算 {margin_ratio}%，距離 130% 的追繳警戒線還有多少空間？", None),
    ("r_t1", "credit", "趨勢", "專業", "融資維持率較前日變動 {margin_chg} 個百分點、來到 {margin_ratio}%，槓桿資金是在降溫還是加溫？", None),
    # ---- 主題文章（新聞、常備文庫、週末文） ----
    ("a_d1", "article", "數據", "專業", "{subj}交出{num1}，這個數字背後代表的是短期波動還是長期趨勢？", None),
    ("a_d2", "article", "數據", "專業", "{subj}這則新聞的關鍵數字是{num1}，和市場原本的預期相比是高還是低？", None),
    ("a_d3", "article", "數據", "專業", "一則{subj}的新聞列了 {n_nums} 個數字，最值得留意的是哪一個？", lambda f: _ge(f.get("n_nums"), 3)),
    ("a_c1", "article", "對比", "專業", "標題沒寫到的是{num1}，{subj}這則新聞真正的重點在哪裡？", None),
    ("a_c2", "article", "對比", "專業", "{subj}這次的{hero}和前一期相比，是加速成長還是開始放緩？", lambda f: f.get("hero") and f.get("hero") not in f.get("num1", "")),
    ("a_t1", "article", "趨勢", "專業", "{subj}的{num1}，是一次性的變化還是新一輪趨勢的開始？", None),
    # 主旨數字是有前提的推估（原文「若…才…」「恐…」）→ 鉤子一定把前提講出來（2026-11-02 CEO：鉤子要忠於原文條件）
    ("a_k1", "article", "對比", "專業", "{num1}成立的前提是{cond}，這個條件目前已經具備，還是仍只是推估？", lambda f: f.get("cond")),
    ("a_k2", "article", "數據", "專業", "{subj}的{num1}是推估，前提是{cond}，這個前提現在已經成立，還是還差一段距離？", lambda f: f.get("cond")),
    # ---- 保底（任何時段、任何資料都填得起來）----
    ("g_d1", "any", "數據", "專業", "{kind_name}的重點數字整理如下，哪一個變化最值得留意？", None),
    ("g_c1", "any", "對比", "專業", "{kind_name}的這幾組數字，是延續前一天的走勢還是出現轉折？", None),
    ("g_t1", "any", "趨勢", "專業", "從{kind_name}的資金與籌碼數據來看，哪一個族群的變化最大？", lambda f: f.get("kind") in ("close", "intraday")),
    ("g_c2", "any", "對比", "專業", "{kind_name}的重點整理如下，和市場預期落差最大的是哪一個？", None),
]
FALLBACK_IDS = ("g_d1", "g_c1")      # 全部模板都不過時的最後保底（輪流用，類型不連續）
HOOK_BY_ID = {h[0]: h for h in HOOKS}


# ---------------------------------------------------------------- 文案解析
HEAD_RE = re.compile(r"^(?!・)(.{1,30}?)[：:]\s*$")
URL_RE = re.compile(r"https?://\S+")


def _norm_head(h: str) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", re.sub(r"（.*?）|\(.*?\)", "", h))


def parse_caption(text: str) -> dict:
    """舊版（10-26 auto_post.md）一整篇文案 → {title, sections:[(標題, [條列])], url}。hashtag 行、說明句、網址行拿掉。"""
    title, secs, url = "", [], ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = URL_RE.search(line)
        if m:
            url = url or m.group(0)
            if URL_RE.sub("", line).strip():
                line = URL_RE.sub("", line).strip()
            else:
                continue
        if line.startswith("👉") or re.fullmatch(r"(#[^\s#]+\s*)+", line):
            continue
        if HEAD_RE.match(line):
            secs.append((line, []))
        elif not secs and not title:
            title = line
        elif secs:
            secs[-1][1].append(line)
        else:
            secs.append(("", [line]))
    return dict(title=title, sections=secs, url=url)


def sec_map(secs) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for h, items in secs:
        out.setdefault(_norm_head(h), []).extend(items)
    return out


def _first_name(s: str) -> str:
    return re.split(r"[、；;，]", s.strip(), maxsplit=1)[0].strip()


def _abs(v: str) -> str:
    return re.sub(r"^[+\-−]", "", v.strip())


def _round_amt(v: str) -> str:
    x = _num(v)
    if x is None:
        return v
    return f"{round(abs(x)):,}" if abs(x) >= 100 else f"{abs(x):,.1f}".rstrip("0").rstrip(".")


def facts(kind: str, text: str, reply: str = "", extra: dict | None = None) -> dict:
    """從文案取鉤子模板要用的數字與名稱（找不到的欄位就不放，用到它的模板今天自動不用）。"""
    allt = (text or "") + "\n" + (reply or "")
    f: dict = {"kind_name": KIND_NAME.get(kind, "今天"), "kind": kind}
    sm = sec_map(parse_caption(text)["sections"] + parse_caption(reply)["sections"])

    def grab(pat, *names, src=allt):
        m = re.search(pat, src)
        if m:
            for n, v in zip(names, m.groups()):
                if v is not None and v.strip():
                    f[n] = v.strip()
        return m

    grab(r"領先 ([^\n；;]+)", "lead_all"); grab(r"落後 ([^\n；;]+)", "lag_all")
    grab(r"流入 ([^\n；;]+)", "in_all"); grab(r"流出 ([^\n；;]+)", "out_all")
    for k in ("lead", "lag", "in", "out"):
        if f.get(k + "_all"):
            f[k + "1"] = _first_name(f.pop(k + "_all"))
    grab(r"漲最多 (.+?) ([+\-−]?\d+(?:\.\d+)?%)", "up1", "up1p")
    grab(r"跌最多 (.+?) ([+\-−]?\d+(?:\.\d+)?%)", "dn1", "dn1p")
    grab(r"(\d+) 個族群 (\d+) 漲 (\d+) 跌，族群平均 ([+\-−]?\d+(?:\.\d+)?%)", "n_all", "n_up", "n_dn", "avg")
    grab(r"加權指數(漲|跌) ([\d,]+(?:\.\d+)?) 點（([+\-−]?[\d.]+%)）", "idx_dir", "idx_pts", "idx_pct")
    grab(r"上漲 ([\d,]+) 家、下跌 ([\d,]+) 家", "adv", "dec")
    grab(r"漲停 (\d+) 家、跌停 (\d+) 家", "lim_up", "lim_dn")
    grab(r"僅?([\d.]+%) 個股站上月線", "above_ma")
    grab(r"外資(買超|賣超) ([\d,.]+) ?億(?:，已連 (\d+) 日(?:買超|賣超)?(?:，累計 ([\d,.]+) ?億)?)?", "fx_act", "fx_amt", "fx_streak", "fx_cum")
    grab(r"投信(買超|賣超) ([\d,.]+) ?億(?:，已連 (\d+) 日(?:買超|賣超)?(?:，累計 ([\d,.]+) ?億)?)?", "trust_act", "trust_amt", "trust_streak", "trust_cum")
    # 11-04 專業問句鉤子要用的：外資賣超第一名的金額與占比、台指期未平倉、三大法人合計、融資維持率
    grab(r"外資(?:買超|賣超)以(.+?)最多（([+\-−]?[\d,.]+) ?億，占外資當日(?:買超|賣超) (\d+(?:\.\d+)?%)）", "fx_top_name", "fx_top_amt", "fx_top_share")
    grab(r"外資(加空|減空|加多|減多)台指期 ([\d,]+) 口，未平倉淨(空單|多單)(?:升至|降至|為) ([\d,]+) 口", "fut_act", "fut_lots", "fut_side", "fut_oi")
    m = grab(r"合計 ?([+\-−]?[\d,.]+) ?億", "tot")
    if m:
        f["tot_act"] = "賣超" if _neg(f["tot"]) else "買超"
        f["tot_amt"] = _abs(f["tot"])
    grab(r"上市（估算?）([\d.]+)%(?:，較前日 ([+\-−]?[\d.]+) ?pp)?", "margin_ratio", "margin_chg")
    for items in (sm.get("外資") or []):
        m = re.match(r"・?買超 (.+)", items)
        if m:
            f["fbuy1"] = _first_name(m.group(1))
        m = re.match(r"・?賣超 (.+)", items)
        if m:
            f["fsell1"] = _first_name(m.group(1))
    if f.get("fx_act"):
        f["fx_top"] = f.get("fsell1" if f["fx_act"] == "賣超" else "fbuy1", "")
        if not f["fx_top"]:
            f.pop("fx_top")
    m = grab(r"費半(上漲|下跌) ([\d.]+)%", "sox_dir", "sox_pct")
    if m:
        f["sox_v"] = "漲" if f["sox_dir"] == "上漲" else "跌"
    grab(r"四大指數(全數收黑|全數收紅|漲跌互見)", "us_all")
    grab(r"台積電 ?ADR ([+\-−][\d.]+%)", "adr")
    grab(r"台指期夜盤 ([\d,]+)，較日盤 ([+\-−][\d,]+) 點", "tx", "tx_chg")
    for k in ("up1p", "dn1p", "idx_pct", "tx_chg", "fx_top_amt"):
        if f.get(k):
            f[k + "_abs"] = _abs(f[k])
    for k in ("fx_amt", "fx_cum", "trust_amt", "trust_cum", "tot_amt"):     # 「5,120.1 億」→「5,120 億」（百億以上取整數）
        if f.get(k):
            f[k + "_r"] = _round_amt(f[k])
    if f.get("fx_top_name") and f.get("fx_top") and f["fx_top_name"] != f["fx_top"]:
        f.pop("fx_top_share", None)                    # 名單第一名跟這句講的不是同一檔 → 不用占比模板
    f["fx_top"] = f.get("fx_top") or f.get("fx_top_name", "")
    if not f["fx_top"]:
        f.pop("fx_top")
    news = []
    for h in ("新聞焦點", "今日焦點"):
        for it in sm.get(h, []):
            t = it.lstrip("・").strip()
            if t.startswith("美股四大指數"):
                continue
            short = t.split("：", 1)[0].strip()
            if 6 <= len(short) <= 22:
                news.append(short)
    if news:
        f["news1"] = news[0]
    f["news_all"] = news
    if extra:
        f.update({k: v for k, v in extra.items() if v not in (None, "")})
    return f


# ---------------------------------------------------------------- 標籤（恰 1 個、事件型）
KNOWN_CO = ("台積電", "聯發科", "鴻海", "廣達", "緯穎", "緯創", "日月光投控", "大立光", "台達電", "聯電", "瑞昱", "華碩", "國巨",
            "長榮", "陽明", "萬海", "富邦金", "國泰金", "中華電", "光寶科", "欣興", "南亞科", "華邦電", "力積電", "世芯-KY", "創意",
            "奇鋐", "雙鴻", "健策", "智邦", "穩懋", "宏達電", "英業達", "仁寶", "和碩", "技嘉", "微星", "輝達", "NVIDIA", "Apple",
            "蘋果", "Google", "Alphabet", "微軟", "Meta", "亞馬遜", "特斯拉", "AMD", "英特爾", "Intel", "高通", "博通", "三星", "美光")
EVENT_WORD = r"(法說會?|財報|EPS|毛利率|營收)"


def _clean_tag(t: str) -> str:
    return re.sub(r"[\s.&#，。！？、：；()（）「」]", "", t)[:50]


def pick_tag(kind: str, text: str, f: dict) -> str:
    """依當天新聞／財報／Fed 自動選 1 個事件型標籤；沒有就用最熱個股事件；永遠回得出一個不在黑名單的標籤。"""
    t = text or ""
    if re.search(r"FOMC|聯準會|Fed\b|鮑爾|利率決策", t):
        return "Fed利率決策"
    if re.search(r"\bCPI\b|消費者物價", t):
        return "美國CPI"
    if re.search(r"非農", t):
        return "美國非農"
    # 大盤單日漲跌 ≥500 點：當天討論度最高的就是這件事
    pts = _num(f.get("idx_pts")) if f.get("idx_pts") else None
    m = re.search(r"(?:加權指數|台股|加權)[^。\n]{0,8}?(大?漲|大?跌|重挫|暴跌|狂飆)\s*([\d,]{3,}(?:\.\d+)?)\s*點", t)
    if pts is None and m:
        pts = _num(m.group(2))
    if pts and pts >= 500:
        down = (f.get("idx_dir") == "跌") if f.get("idx_dir") else bool(m and re.search(r"跌|挫", m.group(1)))
        return "台股大跌" if down else "台股大漲"
    cands = []
    for m in re.finditer(r"([一-鿿A-Za-z\-]{2,8}?)\s?[（(]\d{4}[)）][^。\n]{0,15}?" + EVENT_WORD, t):
        cands.append((m.start(), m.group(1), m.group(2)))
    for nm in KNOWN_CO:
        m = re.search(re.escape(nm) + r"[^。\n：]{0,15}?" + EVENT_WORD, t)
        if m:
            cands.append((m.start(), nm, m.group(1)))
    if kind == "article" and f.get("subj") and f.get("cat") == "財報" and _clean_tag(f["subj"]) not in GENERIC_TAGS:
        cands.insert(0, (-1, f["subj"], "財報"))
    if cands:
        cands.sort(key=lambda x: x[0])
        _, nm, ev = cands[0]
        tag = _clean_tag(nm + ("法說會" if ev.startswith("法說") else "財報"))
        if tag and tag not in GENERIC_TAGS:
            return tag
    # 沒有財報／央行事件 → 最熱個股事件
    if kind == "article" and f.get("subj") and _clean_tag(f["subj"]) not in GENERIC_TAGS and len(_clean_tag(f["subj"])) >= 2:
        return _clean_tag(f["subj"])
    if kind == "premarket":
        return "台積電ADR"
    stock = f.get("fx_top") or next((nm for nm in KNOWN_CO if nm in t), "") or "台積電"
    if kind == "close" and f.get("fx_top"):
        return _clean_tag(f"{stock}外資{f.get('fx_act', '賣超')}")
    return _clean_tag(f"{stock}股價")


# ---------------------------------------------------------------- 串文切段
def _rewrite(t: str) -> str:
    for a, b in REWRITE.items():
        t = t.replace(a, b)
    return t


def _strip_tags(t: str) -> str:
    return re.sub(r"#(?=[^\s#])", "", t)


def _split_long(unit: str, hard: int = HARD_MAX - 5) -> list[str]:
    """單一段落超過上限 → 句號／分號處切，再不行逗號處切，最後才硬切（硬切不丟字）。"""
    if clen(unit) <= hard:
        return [unit]
    out, cur = [], ""
    for sent in re.split(r"(?<=[。！？；;\n])", unit):
        if not sent:
            continue
        if clen(sent) > hard:
            for piece in re.split(r"(?<=[，、])", sent):
                while clen(piece) > hard:
                    out += [cur] if cur.strip() else []
                    cur = ""
                    out.append(piece[:hard]); piece = piece[hard:]
                if clen(cur + piece) > hard and cur.strip():
                    out.append(cur); cur = ""
                cur += piece
            continue
        if clen(cur + sent) > hard and cur.strip():
            out.append(cur); cur = ""
        cur += sent
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out if x.strip()]


def section_units(secs, title: str = "", target: int = THREAD_TARGET, item_max: int = HARD_MAX - 5) -> list[str]:
    """每一段（標題＋條列）一個單位；一段超過 target（80 字）就逐條拆開，續段標題加「（續）」，
    單一條列超過上限才在句讀處切（不丟字）。"""
    units = []
    for h, items in secs:
        items = [_rewrite(_strip_tags(x)) for x in items]
        h = _rewrite(_strip_tags(h))
        block = "\n".join(([h] if h else []) + items)
        if clen(block) <= target:
            units.append(block); continue
        cont = (re.sub(r"（[^）]*）|\([^)]*\)", "", h).rstrip("：: ") + "（續）：") if h else ""
        cur = h
        for it in items:
            for piece in _split_long(it, item_max):
                if cur and cur not in (h, cont) and clen(cur + "\n" + piece) > target:
                    units.append(cur.strip())
                    cur = cont
                cur = (cur + "\n" + piece) if cur else piece
        if cur.strip() and cur.strip() not in (h, cont):
            units.append(cur.strip())
    if title:
        t = _rewrite(_strip_tags(title))
        if clen(t) < THREAD_MIN and units:
            units[0:1] = _lead_with_title(t, units[0], item_max)
        else:
            units.insert(0, t)
    return [u for u in units if u.strip()]


def _lead_with_title(t: str, first: str, hard: int) -> list[str]:
    """標題太短（<30 字）自己一則會不合規 → 跟下一段合併；合起來太長就把下一段開頭幾個子句（句號優先、再逗號）搬上來，
    兩則都 ≥30 字、≤上限（2026-11-02：標題拿掉重複詞後變短）。"""
    if clen(t + "\n" + first) <= hard:
        return [t + "\n" + first]
    if "\n" in first:
        return [t, first]                 # 下一段是「段名＋條列」（主貼文）：不拆條列，交給 pack() 合併
    for pat in (r"(?<=[。！？；])", r"(?<=[，、])"):
        pieces = [x for x in re.split(pat, first) if x]
        head, best = "", None
        for k, pc in enumerate(pieces):
            if clen(t + "\n" + head + pc) > hard:
                break
            head += pc
            rest = "".join(pieces[k + 1:])
            if clen(t + head) >= THREAD_MIN and clen(rest) >= THREAD_MIN:
                best = [t + "\n" + head.strip(), rest.strip()]      # 盡量多搬（不要只搬「11/1，」）
        if best:
            return best
    return [t, first]


def pack(units: list[str], target: int = THREAD_TARGET, hard: int = HARD_MAX, min_n: int = THREAD_MIN) -> list[str]:
    """把單位裝成串文：合起來 ≤target 就合併；目前這則還不到 min_n 字就再塞（≤hard）；最後太短的併到前一則。"""
    posts: list[str] = []
    cur = ""
    for u in units:
        if not cur:
            cur = u; continue
        both = cur + "\n" + u
        if clen(both) <= target or (clen(cur) < min_n and clen(both) <= hard):
            cur = both
        else:
            posts.append(cur); cur = u
    if cur:
        posts.append(cur)
    i = 0
    while i < len(posts):            # 太短的：先往前併，不行往後併
        if clen(posts[i]) < min_n and len(posts) > 1:
            if i > 0 and clen(posts[i - 1] + posts[i]) + 1 <= hard:
                posts[i - 1] += "\n" + posts.pop(i); continue
            if i + 1 < len(posts) and clen(posts[i] + posts[i + 1]) + 1 <= hard:
                posts[i] += "\n" + posts.pop(i + 1); continue
        i += 1
    return posts


def sections_from_posts(posts: list[str]) -> tuple[str, list, str]:
    """舊版串文（pack_threads 的輸出）→（標題, [(段名, [行])], 網址）。標題取開頭兩行 hashtag 句、拿掉 #。"""
    txt = "\n\n".join(re.sub(r"\n?\(\d+/\d+\)\s*$", "", p.strip()) for p in posts)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    title, secs, url = "", [], ""
    for b in blocks:
        m = re.search(r"https?://\S+", b)
        if m:
            url = url or m.group(0)
            rest = [l for l in b.splitlines() if not re.search(r"https?://|👉|非投資建議", l)]
            if rest:
                secs.append(("", rest))
            continue
        lines = b.splitlines()
        if not title and not secs and all(l.startswith("#") for l in lines):
            parts = []
            for l in lines:
                t = l.lstrip("#").strip()
                w0, sp, rest = t.partition(" ")
                if parts and sp and w0 in "".join(parts):
                    t = rest.strip()          # 2026-11-02：「台股 融資…｜台股 今天的…」第二行開頭的分類標籤跟標題重複 → 拿掉
                parts.append(t)
            title = "｜".join(parts)
            continue
        if len(lines) > 1 and len(lines[0]) <= 20 and not lines[0].startswith(("▪", "・")):
            secs.append((lines[0], lines[1:]))
        else:
            secs.append(("", lines))
    return title, secs, url


def from_posts(posts: list[str], n_images: int, today: str, state: dict | None = None, extra: dict | None = None,
               legal: str = "以上為公開資料整理，非投資建議") -> dict:
    """舊格式串文（手動加發、主題文章舊檔）→ v2。threads_post.py 發文前呼叫；圖張數照原檔（1 張時呼叫端警告）。"""
    title, secs, url = sections_from_posts(posts)
    head = re.sub(r"[｜|].*", "", title)
    subj = (re.match(r"\S+", head) or [""])[0] if head else ""
    allt = "\n".join(posts)
    m = re.search(r"([\d,.]+\s?(?:%|億元|億|元|點|美元))", allt)
    ex = dict(subj=subj[:10], num1=(m.group(1) if m else ""), hero=(m.group(1) if m else ""))
    ex.update(extra or {})
    return build("article", allt, images=["x"] * min(n_images, 1), url=url, state=state, today=today,
                 extra=ex, sections=secs, title=title, legal=legal, item_max=HARD_MAX - 5,
                 tag_text=title + "\n" + "\n".join(secs[0][1] if secs else []))


# ---------------------------------------------------------------- 狀態（輪替）
def load_state(path) -> dict:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("history"), list) else {"history": []}
    except Exception:
        return {"history": []}


def save_state(state: dict, path, keep_days: int = 60, today: str | None = None) -> None:
    today = today or datetime.now(TPE).strftime("%Y-%m-%d")
    lim = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    state["history"] = [h for h in state.get("history", []) if h.get("date", "") >= lim]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def _fill(tpl: str, f: dict) -> str | None:
    try:
        return tpl.format(**{k: v for k, v in f.items() if isinstance(v, str)})
    except (KeyError, IndexError, ValueError):
        return None


def candidates(kind: str, f: dict) -> list[tuple]:
    k = "article" if kind == "article" else kind
    out = []
    for h in HOOKS:
        if h[1] not in (k, "any"):
            continue
        txt = _fill(h[4], f)
        if txt is None:
            continue
        try:
            if h[5] and not h[5](f):
                continue
        except Exception:
            continue
        out.append((h, txt))
    return out


def choose_hook(kind: str, f: dict, state: dict, today: str, tag: str, check) -> tuple[tuple, str, str]:
    """回傳（模板, 主文, 放寬到哪一層）。輪替規則：同一類型不連續用、同一模板 14 天內不重複。
    放寬順序：全部規則 → 放掉 14 天 → 放掉類型不連續 → 保底模板（any）→ 最後一個保底硬塞（仍發）。"""
    hist = state.get("history", [])
    last_type = hist[-1]["type"] if hist else None
    lim = (date.fromisoformat(today) - timedelta(days=COOLDOWN_DAYS)).isoformat()
    recent = {h["template"] for h in hist if h.get("date", "") > lim}
    seed = int(hashlib.md5(f"{today}{kind}{len(hist)}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    cands = candidates(kind, f)
    rng.shuffle(cands)
    cands.sort(key=lambda x: x[0][1] == "any")      # 有當天數據的模板優先，保底的排最後
    levels = [("全部規則", lambda h: h[2] != last_type and h[0] not in recent),
              ("放寬14天", lambda h: h[2] != last_type),
              ("放寬類型", lambda h: True)]
    for name, cond in levels:
        for h, txt in cands:
            if cond(h) and check(h, txt):
                return h, txt, name
    h = HOOK_BY_ID[FALLBACK_IDS[0]] if last_type != HOOK_BY_ID[FALLBACK_IDS[0]][2] else HOOK_BY_ID[FALLBACK_IDS[1]]
    return h, _fill(h[4], f) or h[4].replace("{kind_name}", "今天"), "保底"


# ---------------------------------------------------------------- 圖：0 或 2 張
# 2026-11-02 Andy：「主貼文也改成只放 1 張」→ 每時段只貼排第一的那張（其他圖不上 Threads；IG 限時動態照舊多張）
#   盤中＝熱力圖；盤後＝三大法人買賣超（當日盤勢總覽，沒有就外資個股排名…）；盤前＝美股四大指數收盤；融資融券＝融資維持率
IMG_PRIORITY = {
    "intraday": ["heat", "sankey-tree", "rotation-wheel", "rotation-rank"],
    "close": ["inst-today", "streak-foreign", "fut-oi", "credit-rank", "margin", "retail-ratio", "streak-trust", "etf-buy"],
    "premarket": ["us-close", "tx", "news"],
    "credit": ["margin", "credit"],
}
IMG_IDEA = {"heat": "熱力圖：哪些族群漲最多、跌最兇", "sankey-tree": "資金分流樹：錢從哪裡流到哪裡", "rotation-wheel": "資金輪盤：領先與落後族群",
            "rotation-rank": "資金排行", "inst-today": "三大法人買賣超", "streak-foreign": "外資個股買賣超與連買連賣",
            "streak-trust": "投信個股買賣超", "fut-oi": "台指期法人未平倉", "retail-ratio": "散戶多空比", "etf-buy": "ETF 買超排名",
            "us-close": "美股四大指數收盤", "tx": "台指期夜盤＋台積電 ADR", "news": "今日事件與消息", "margin": "融資維持率", "credit": "融資融券增減"}


def pick_images(kind: str, imgs: list[str]) -> list[str]:
    pri = IMG_PRIORITY.get(kind, [])
    ranked = sorted(imgs, key=lambda x: next((i for i, k in enumerate(pri) if k in Path(x).stem), 99))
    return ranked[:1]       # 11-02 Andy「主貼文也改成只放 1 張」


def idea_of(path: str) -> str:
    st = Path(path).stem
    return next((v for k, v in IMG_IDEA.items() if k in st), st)


# ---------------------------------------------------------------- 壓到 ≤6 則（2026-11-01 CEO：「串文 10～12 則太長，讀者不會滑完、也容易撞頻率限制」）
PACK_TARGET = 130          # 每則目標 80～130 字，硬上限 150
DROP_FIRST = ("之前的報導", "其他媒體", "和前期比")          # 主題文章：放不下先整段拿掉的次要段落（重點數字已涵蓋）
NEWS_HEADS = ("新聞焦點", "今日焦點")
DETAIL_HEADS = ("昨日盤面", "盤面分析", "這些數字代表什麼")


def _hn(h: str) -> str:
    return _norm_head(h)


def _render(secs, title, item_max):
    return pack(section_units(secs, title, target=HARD_MAX - 5, item_max=item_max), target=PACK_TARGET)


BUDGET_DROP = ("之前的報導", "其他媒體", "相關公司", "和前期比")     # 11-02 濃縮進主文：先拿掉這些（重點數字／代表什麼／接下來觀察留著）


def _render_one(secs, title: str) -> str:
    """全部段落排成一段文字（主文用）：標題一行、每段「段名＋條列」，段與段之間換行。"""
    blocks = [_rewrite(_strip_tags(title))] if title else []
    for h, items in secs:
        items = [_rewrite(_strip_tags(x)) for x in items if x.strip()]
        h = _rewrite(_strip_tags(h))
        b = "\n".join(([h] if h else []) + items)
        if b.strip():
            blocks.append(b)
    return "\n".join(blocks)


def fit(secs, title: str, item_max: int, max_posts: int = 6, budget: int | None = None) -> tuple[list[str], list[str]]:
    """同類數據合併成一則（盤勢、法人、族群、新聞焦點 3～5 條、昨日盤面），還超過 6 則就依序精簡次要數據：
    ① 主題文章拿掉「之前的報導／其他媒體／和前期比」 ② 新聞焦點描述縮到 28 字 ③ 新聞焦點最多 3 條
    ④ 盤面分析／昨日盤面每條只留第一個分號前 ⑤ 從最長的段落尾巴逐條拿掉。回傳（串文, 被精簡的段名）。"""
    secs = [(h, list(items)) for h, items in secs]
    cut: list[str] = []

    def render():
        return [_render_one(secs, title)] if budget else _render(secs, title, item_max)

    def good(ps):
        return tlen(ps[0]) <= budget if budget else len(ps) <= max_posts

    posts = render()
    if good(posts):
        return posts, cut

    def step_drop():
        nonlocal secs
        for kw in (BUDGET_DROP if budget else DROP_FIRST):
            hit = [x for x in secs if kw in _hn(x[0])]
            if hit:
                secs = [x for x in secs if x not in hit]; cut.append(kw); return True
        return False

    def step_news_short():
        ch = False
        for h, items in secs:
            if any(k in _hn(h) for k in NEWS_HEADS):
                for i, it in enumerate(items):
                    a, sep, b = it.partition("：")
                    if sep and clen(b) > 28:
                        items[i] = f"{a}：{b[:27]}…"; ch = True
        if ch:
            cut.append("新聞描述")
        return ch

    def step_news_three():
        ch = False
        for h, items in secs:
            if any(k in _hn(h) for k in NEWS_HEADS):
                real = [i for i, it in enumerate(items) if not it.lstrip("・").startswith("美股四大指數")]
                while len(real) > 3:
                    items.pop(real.pop()); ch = True
        if ch:
            cut.append("其餘新聞")
        return ch

    def step_detail():
        ch = False
        for h, items in secs:
            if any(k in _hn(h) for k in DETAIL_HEADS):
                for i, it in enumerate(items):
                    a = re.split(r"[；;]", it, maxsplit=1)[0]
                    if a != it:
                        items[i] = a; ch = True
        if ch:
            cut.append("盤面細項")
        return ch

    def step_tail():
        cand = [x for x in secs if len(x[1]) > 1]
        if not cand:
            cand = [x for x in secs if x[1]]
            if len(cand) <= 1:
                return False
            x = min(cand, key=lambda x: clen("".join(x[1])))
            secs.remove(x); cut.append(_hn(x[0]) or "段落"); return True
        x = max(cand, key=lambda x: clen("".join(x[1])))
        x[1].pop(); cut.append(_hn(x[0]) or "段落")
        return True

    def step_intro():
        nonlocal secs
        if budget and secs and not secs[0][0] and len(secs) > 1:      # 導言（11-02 起是本站句型＋出處行，不再是報導摘述）在重點數字之後才捨
            secs = secs[1:]; cut.append("導言"); return True
        return False

    steps = (step_drop,) * (4 if budget else 3) + ((step_intro,) if budget else ()) + (step_news_short, step_news_three, step_detail)
    for step in steps:
        if step():
            posts = render()
            if good(posts):
                return posts, cut
    for _ in range(200):
        if not step_tail():
            break
        posts = render()
        if good(posts):
            break
    if budget:
        t = posts[0]
        while t and tlen(t) > budget:                 # 最後手段：從尾巴截（不會整篇不發）
            t = t[:-1]
        return [t.rstrip() + ("…" if t != posts[0] else "")] if t else [""], cut
    return posts[:max_posts], cut


# ---------------------------------------------------------------- 組裝
def reply_text(url: str, kind: str, legal: str = "", cut: list[str] | None = None) -> str:
    # ★ 2026-11-03 Andy：「首先 網頁都不公開先，人數沒有起來，沒有建立信任關係，我覺得不妥」
    #   → 留言只放免責那句；不放網址、不放「完整盤勢見網站」「👉 …都在網站」這類導流字（threads_lint.PROMOTE_SITE）
    if not _TL.PROMOTE_SITE:
        return legal or _TL.DEFAULT_LEGAL
    lead = {"intraday": "完整熱力圖、資金分流樹都在網站，族群一個一個點得開：",
            "close": "法人、融資融券完整排行都在網站，個股一檔一檔查得到：",
            "premarket": "美股、台指期夜盤與今天的事件行事曆都在網站：",
            "credit": "融資融券完整排行都在網站："}.get(kind, "整理好的圖表與產業鏈都在網站：")
    more = ("完整盤勢見網站（" + "、".join(dict.fromkeys(c for c in cut if c)) + "等）\n") if cut else ""
    return ((legal + "\n") if legal else "") + more + "👉 " + lead + "\n" + url


def assemble(kind: str, hook, hook_txt: str, tag: str, threads: list[str], reply: str, images: list[str], level: str = "",
             body: str = "") -> dict:
    main = f"{hook_txt}\n\n{body}\n#{tag}" if body else f"{hook_txt}\n#{tag}"
    # 11-04 Andy「盤後也改成專業語氣」：開頭一律問句、語氣專業；切入角度（數據／對比／趨勢）另存 angle，輪替用它
    d = dict(kind=kind, profile="auto", rule="auto_1104", hook_type="問句", angle=hook[2], emotion=hook[3], main_post=main, main_post_length=clen(split_tag(main)[0]),
             thread_posts=threads, reply_post=reply, image_count=len(images),
             image_ideas=[idea_of(x) for x in images], tag=tag, template=hook[0], level=level)
    d["checklist_passed"] = not lint(d)[0]
    return d


def build(kind: str, text: str, reply: str = "", images: list[str] | None = None, url: str = "",
          state: dict | None = None, today: str | None = None, extra: dict | None = None,
          sections: list | None = None, title: str | None = None, legal: str = "", item_max: int = HARD_MAX - 5,
          tag_text: str | None = None) -> dict:
    """主入口：舊文案 → v2 JSON。永遠回得出一篇（lint 不過的話 checklist_passed=false，照發並記 alert）。"""
    state = state if state is not None else {"history": []}
    today = today or datetime.now(TPE).strftime("%Y-%m-%d")
    p1, p2 = parse_caption(text), parse_caption(reply)
    url = url or p1["url"] or p2["url"] or "https://liguligu-puipui.com/"
    secs = sections if sections is not None else p1["sections"] + p2["sections"]
    # 11-04 Andy「盤後也改成專業語氣」：條列裡帶口語／吐槽字的那行（多半是新聞原標題）不放進主文
    secs = [(h, [x for x in items if not _TL.casual_words(x)]) for h, items in secs]
    secs = [(h, items) for h, items in secs if items or not h]
    ttl = p1["title"] if title is None else title
    f = facts(kind, text, reply, extra)
    tag = pick_tag(kind, (text + "\n" + reply) if tag_text is None else tag_text, f)
    # 11-02 Andy「都濃縮到第一頁」：重點數據全部進主文（≤500），串文 0 則；標題「｜」後面的小問句不放（主文只有鉤子能問問題）
    ttl_main = re.split(r"[｜|]", ttl or "", maxsplit=1)[0].strip()
    threads: list[str] = []
    budget0 = MAIN_BUDGET - 92 - tlen(tag) - 3          # 鉤子最長約 80 字＋換行
    (body,), cut = fit(secs, ttl_main, item_max, budget=budget0)
    rp = reply_text(url, kind, legal, cut)
    imgs = list(images or [])
    if kind == "article":
        imgs = imgs[:1]                                   # 主題文章只留實景封面 1 張
    else:
        imgs = pick_images(kind, imgs)

    cat = f.get("cat", "") if kind == "article" else ""
    content = set(content_issues([body] if body else [], cat))   # 內容本身的問題換鉤子也修不好，不拿來淘汰鉤子

    def check(h, txt):
        d0 = assemble(kind, h, txt, tag, threads, rp, imgs, body=body)
        d0["category"] = cat
        return not [e for e in lint(d0)[0] if e not in content and "超過 Threads 上限" not in e and not e.startswith("自動貼文主文口語")]

    hook, txt, level = choose_hook(kind, f, state, today, tag, check)
    exact = MAIN_BUDGET - tlen(f"{txt}\n\n\n#{tag}")      # 鉤子定了 → 用實際剩下的字數重排一次，用滿 500
    if exact != budget0:
        (body,), cut = fit(secs, ttl_main, item_max, budget=max(60, exact))
        rp = reply_text(url, kind, legal, cut)
    d = assemble(kind, hook, txt, tag, threads, rp, imgs, level, body=body)
    if cat:
        d["category"] = cat
        d["checklist_passed"] = not lint(d)[0]
    d["images"] = imgs
    return d


def record(state: dict, d: dict, kind: str, today: str, key: str = "") -> None:
    state.setdefault("history", []).append(dict(date=today, kind=kind, template=d["template"], type=d.get("angle") or d["hook_type"],
                                                emotion=d["emotion"], tag=d["tag"], key=key, main=d["main_post"][:90]))


def convert_manifest(mp: Path, state_in: str | None, state_out: str | None) -> dict:
    """social-live 用：manifest.json 的 threads 改成 v2（舊版留在 threads_v1 方便比對與回退）。"""
    m = json.loads(mp.read_text(encoding="utf-8"))
    th = m.get("threads") or {}
    if not th.get("text") or th.get("v2"):
        return m
    kind = m.get("kind", "intraday")
    today = (m.get("taken_at") or datetime.now(TPE).isoformat())[:10]
    state = load_state(state_in) if state_in else {"history": []}
    d = build(kind, th.get("text", ""), th.get("reply", ""), th.get("images", []), state=state, today=today)
    m["threads_v1"] = dict(th)
    if _TL.scrub_post(d):                                  # 11-03：萬一主文／串文帶到網址（新聞原文等）→ 送出前拿掉
        d["checklist_passed"] = not lint(d)[0]
    m["threads"] = dict(text=d["main_post"], images=d["images"], thread_posts=d["thread_posts"],
                        reply_post=d["reply_post"], v2={k: v for k, v in d.items() if k != "images"})
    if not d["checklist_passed"]:
        (mp.parent / "alert.txt").open("a", encoding="utf-8").write(
            "Threads v2 檢查未全過（照發）：" + "；".join(lint(d)[0]) + "\n")
    mp.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    if state_out:
        try:
            from social_publish import slot_key
            key = slot_key(m)
        except Exception:  # noqa: BLE001
            key = f"{kind}-{today}"
        record(state, d, kind, today, key)
        save_state(state, state_out, today=today)
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--state", default="")
    ap.add_argument("--out-state", default="")
    a = ap.parse_args(argv)
    m = convert_manifest(Path(a.manifest), a.state or None, a.out_state or None)
    v2 = (m.get("threads") or {}).get("v2")
    if v2:
        print(json.dumps(v2, ensure_ascii=False, indent=1))
        e, w = lint(v2)
        print("lint：" + ("通過" if not e else "未過（照發）：" + "；".join(e)) + ("；警告：" + "；".join(w) if w else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
