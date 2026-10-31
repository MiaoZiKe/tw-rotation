"""Threads 發文 v2（2026-11-01 Andy：「CEO 交給對應單位 將發文 Thread 系統修改」「在 IG Thread 上面也需要進行優化
讓熱度提升，並且 盡量不要千篇一律的方式要有點變化」；規則全文 docs/marketing/social_unit/threads_rules.md）。

把原本一整篇的盤前／盤中／盤後／主題文章文案，改成：
  main_post   主文 30–80 字：鉤子（對話／冷知識／反差）＋情緒（好笑／吐槽）＋恰 1 個事件型標籤，不放網址
  thread_posts 串文：原本的盤勢、族群、新聞焦點、相關公司逐段搬過來（每則 30–80 字，最多 150），數據一個都不少
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
from threads_lint import BANNED, GENERIC_TAGS, HARD_MAX, THREAD_MIN, THREAD_TARGET, clen, lint, split_tag  # noqa: E402,F401

TPE = timezone(timedelta(hours=8))
COOLDOWN_DAYS = 14
KIND_NAME = {"intraday": "盤中", "close": "盤後", "premarket": "盤前", "credit": "融資融券", "article": "這則新聞"}
# 喊單字在串文（新聞原句）出現時的自動改寫：保留事實、拿掉叫人買的語氣
REWRITE = {"買進": "買入", "加碼": "增持", "推薦": "點名", "目標價": "預估價", "飆股": "強勢股", "抄底": "低接",
           "私訊": "訊息", "跟單": "跟進", "穩賺": "看好", "快上車": "", "必買": "", "報明牌": "", "趕快買": "",
           "現在進場": "", "歡迎留言": "", "謝謝大家": "", "留言告訴我": "", "你怎麼看": "", "連結在留言": "", "連結在下方": "",
           "看留言": "看下一則"}

# ---------------------------------------------------------------- 鉤子模板庫
# (id, kind, 開頭類型, 情緒, 模板, 條件)；kind="any" 是保底（只用 {kind_name}，任何資料都填得起來）
# 模板裡的 {xxx} 由 facts() 從當天數據取；缺任何一個欄位或條件不成立 → 這個模板今天不用。
def _neg(v):
    return isinstance(v, str) and v.strip().startswith(("-", "−"))


def _num(v):
    try:
        return float(str(v).replace(",", "").replace("−", "-").replace("+", "").rstrip("%"))
    except (TypeError, ValueError):
        return None


HOOKS = [
    # ---- 盤中 ----
    ("i_d1", "intraday", "對話", "好笑", "同事午餐問我：「今天吃什麼？」我說看{up1}，它漲{up1p_abs}，所以今天加一顆滷蛋！", lambda f: not _neg(f.get("up1p"))),
    ("i_d2", "intraday", "對話", "吐槽", "早上群組還在喊衝，中午{n_dn}個族群翻黑，群組安靜到聽得到冷氣聲…", lambda f: _num(f.get("n_dn")) > _num(f.get("n_up"))),
    ("i_d3", "intraday", "對話", "好笑", "朋友問：「錢跑去哪了？」我說：「{in1}。」他再問{out1}呢，我只能拍拍他說節哀…", None),
    ("i_d4", "intraday", "對話", "吐槽", "「這盤很健康，只是在整理。」說這句話的人應該沒看到{dn1}今天{dn1p}…", lambda f: _neg(f.get("dn1p"))),
    ("i_d5", "intraday", "對話", "好笑", "老闆問我中午在看什麼這麼專心，我說{lead1}在領先，他以為我在看運動比賽！", None),
    ("i_k1", "intraday", "冷知識", "吐槽", "冷知識：今天{n_all}個族群只有{n_up}個是紅的，比我這個月的存款餘額還少見！", lambda f: _num(f.get("n_up")) * 2 < _num(f.get("n_all"))),
    ("i_k2", "intraday", "冷知識", "好笑", "冷知識：中午漲最多的不是新聞天天講的那群，是{up1}，{up1p}，我自己都嚇一跳！", lambda f: not _neg(f.get("up1p"))),
    ("i_k3", "intraday", "冷知識", "吐槽", "冷知識：盤面看起來很平靜，資金其實正從{out1}搬去{in1}，搬家速度比房東漲租還快…", None),
    ("i_k4", "intraday", "冷知識", "好笑", "冷知識：族群平均{avg}，{up1}卻硬是逆勢{up1p}，每個班上總有一個不合群的！", lambda f: _neg(f.get("avg")) and not _neg(f.get("up1p"))),
    ("i_k5", "intraday", "冷知識", "吐槽", "冷知識：跌最兇的往往不是你最怕的那檔，今天是{dn1}{dn1p}，是大家最放心的那群…", lambda f: _neg(f.get("dn1p"))),
    ("i_f1", "intraday", "反差", "吐槽", "以為今天又是AI的主場，結果中午資金輪盤領先的是{lead1}，市場真的很會打臉…", lambda f: "AI" not in f.get("lead1", "")),
    ("i_f2", "intraday", "反差", "好笑", "大家都在討論{out1}，資金卻偷偷溜去{in1}，這就是傳說中的聲東擊西吧！", None),
    ("i_f3", "intraday", "反差", "吐槽", "嘴上說沒差，實際上{n_dn}個族群在跌、族群平均{avg}，嘴再硬也救不了帳面…", lambda f: _num(f.get("n_dn")) > _num(f.get("n_up"))),
    ("i_f4", "intraday", "反差", "好笑", "早上最多人聊的{lag1}，中午直接掉進落後組，人氣跟資金果然是兩回事！", None),
    ("i_f5", "intraday", "反差", "好笑", "{dn1}跌{dn1p_abs}，{up1}卻漲{up1p_abs}，同一個盤面活得像兩個平行宇宙！", lambda f: _neg(f.get("dn1p")) and not _neg(f.get("up1p"))),
    # ---- 盤後 ----
    ("c_d1", "close", "對話", "吐槽", "「外資只是短線調節啦。」調節了{fx_amt}億，這叫調節的話，我的薪水也只是短線入帳…", lambda f: f.get("fx_act") == "賣超"),
    ("c_d2", "close", "對話", "好笑", "朋友問：「外資今天在幹嘛？」我說{fx_act}{fx_amt}億，他問那{fx_top}呢，我只能默默拍拍他…", None),
    ("c_d3", "close", "對話", "吐槽", "「投信又買了？」對，已經連{trust_streak}天，比我上健身房還有毅力，我先檢討自己…", lambda f: f.get("trust_act") == "買超" and (_num(f.get("trust_streak")) or 0) >= 3),
    ("c_d4", "close", "對話", "好笑", "下班問同事今天盤怎樣，他只回一句「{dec}家在跌」，然後默默把看盤APP關掉…", lambda f: _num(f.get("dec")) > _num(f.get("adv"))),
    ("c_d5", "close", "對話", "好笑", "老闆問我今天心情如何，我說看大盤，加權{idx_dir}了{idx_pts}點，所以今天先別找我聊KPI！", None),
    ("c_k1", "close", "冷知識", "吐槽", "冷知識：今天上市櫃只有{adv}家上漲、{dec}家下跌，紅色比我的發票中獎率還稀有！", lambda f: _num(f.get("dec")) > _num(f.get("adv")) * 2),
    ("c_k2", "close", "冷知識", "好笑", "冷知識：投信已經連{trust_streak}天{trust_act}，比大多數人的新年新希望撐得還久！", lambda f: (_num(f.get("trust_streak")) or 0) >= 5),
    ("c_k3", "close", "冷知識", "吐槽", "冷知識：外資今天賣超名單第一名是{fx_top}，越多人天天討論的股票，越常被當成提款機…", lambda f: f.get("fx_act") == "賣超"),
    ("c_k4", "close", "冷知識", "好笑", "冷知識：今天漲停{lim_up}家、跌停{lim_dn}家，數字幾乎一樣，市場大概在玩平衡遊戲！", lambda f: abs((_num(f.get("lim_up")) or 0) - (_num(f.get("lim_dn")) or 99)) <= 3),
    ("c_k5", "close", "冷知識", "吐槽", "冷知識：今天只有{above_ma}的個股站在月線上，剩下的都在月線下面排隊等救援…", lambda f: (_num(f.get("above_ma")) or 100) < 40),
    ("c_f1", "close", "反差", "吐槽", "外資{fx_act}{fx_amt}億，投信卻{trust_act}{trust_amt}億，兩邊吵成這樣，夾在中間的散戶最無辜！", lambda f: f.get("fx_act") and f.get("fx_act") != f.get("trust_act")),
    ("c_f2", "close", "反差", "好笑", "盤前大家都說今天守得住，結果加權跌了{idx_pts}點，盤前的信心大概是我最便宜的東西…", lambda f: f.get("idx_dir") == "跌"),
    ("c_f3", "close", "反差", "好笑", "加權漲{idx_pts}點看起來很嗨，但其實只有{adv}家在漲，這根本是少數人的派對！", lambda f: f.get("idx_dir") == "漲" and _num(f.get("adv")) < _num(f.get("dec"))),
    ("c_f4", "close", "反差", "吐槽", "說好的護國神山，今天卻是外資賣超第一名的{fx_top}，信仰跟現實差了一大截…", lambda f: f.get("fx_top") == "台積電" and f.get("fx_act") == "賣超"),
    ("c_f5", "close", "反差", "好笑", "外資買最多的是{fbuy1}，不是你天天聽到的那幾檔，熱門跟資金根本不走同一條路！", None),
    ("c_f6", "close", "反差", "好笑", "大盤漲了{idx_pts}點，群組卻有人說「我的還是綠的」，這反差我先笑為敬！", lambda f: f.get("idx_dir") == "漲"),
    # ---- 盤前 ----
    ("p_d1", "premarket", "對話", "吐槽", "起床第一句不是早安，是「費半跌多少？」答案是{sox_pct}%，咖啡突然變得特別苦…", lambda f: f.get("sox_v") == "跌"),
    ("p_d2", "premarket", "對話", "好笑", "老婆問我為什麼一早就在笑，我說費半漲了{sox_pct}%，她說那你今天負責洗碗！", lambda f: f.get("sox_v") == "漲"),
    ("p_d3", "premarket", "對話", "吐槽", "朋友一早傳訊息問ADR怎樣，我回「台積電ADR {adr}」，他已讀不回，我懂…", lambda f: _neg(f.get("adr"))),
    ("p_d4", "premarket", "對話", "好笑", "同事問今天開盤會怎樣，我說夜盤{tx_chg}點，他說那就是先看戲，我說對！", None),
    ("p_d5", "premarket", "對話", "好笑", "朋友問：「台積電ADR昨晚怎樣？」我說{adr}，他說那他今天要假裝很忙！", None),
    ("p_k1", "premarket", "冷知識", "好笑", "冷知識：台指期夜盤收{tx}，跟日盤只差{tx_chg_abs}點，夜貓子昨晚其實沒什麼戲看…", lambda f: (_num(f.get("tx_chg_abs")) or 999) < 150),
    ("p_k2", "premarket", "冷知識", "吐槽", "冷知識：費半一個晚上{sox_v}{sox_pct}%，比我一整年的加薪幅度還戲劇化…", None),
    ("p_k3", "premarket", "冷知識", "好笑", "冷知識：今天早上最搶戲的不是美股，是「{news1}」這則，連咖啡都還沒喝完…", None),
    ("p_k4", "premarket", "冷知識", "吐槽", "冷知識：台積電ADR昨晚{adr}，很多人開盤前只看這一個數字，就決定了一整天的心情…", None),
    ("p_k5", "premarket", "冷知識", "好笑", "冷知識：美股收盤是台灣清晨四五點，所以今天的心情其實在你睡著時就決定了！", None),
    ("p_f1", "premarket", "反差", "吐槽", "昨天大家還在說美股很穩，一覺醒來四大指數{us_all}，信心果然不能放著過夜…", lambda f: f.get("us_all") in ("全數收黑", "全數收紅")),
    ("p_f2", "premarket", "反差", "好笑", "美股四大指數{us_all}，台指期夜盤卻只動了{tx_chg}點，台股今天是打算裝沒看到吧！", lambda f: f.get("us_all")),
    ("p_f3", "premarket", "反差", "好笑", "標題都在吵美股，真正讓我早上醒過來的卻是「{news1}」這則…", None),
    ("p_f4", "premarket", "反差", "吐槽", "大家都說今天要看美股臉色，結果我先被「{news1}」嚇醒了…", None),
    # ---- 主題文章（新聞、常備文庫、週末文） ----
    ("a_d1", "article", "對話", "好笑", "同事問我{subj}最近怎樣，我只回了一個數字：{hero}，他就安靜去倒水了！", None),
    ("a_d2", "article", "對話", "吐槽", "朋友說「{subj}沒什麼好看的」，我把{num1}丟給他，他到現在都還沒回…", None),
    ("a_d3", "article", "對話", "好笑", "「這新聞看標題就好了吧？」不行，{subj}的{num1}藏在後面，只看標題會錯過重點！", None),
    ("a_d4", "article", "對話", "吐槽", "主管問我{subj}這則重點是什麼，我說一句話：{num1}，剩下的都在解釋這個數字…", None),
    ("a_d5", "article", "對話", "好笑", "朋友問：「{subj}到底在紅什麼？」我說先看{num1}，看完他自己就懂了！", None),
    ("a_k1", "article", "冷知識", "好笑", "冷知識：{subj}這則新聞最重要的數字不在標題，是{num1}，多數人滑過去就錯過了！", None),
    ("a_k2", "article", "冷知識", "吐槽", "冷知識：{subj}的{num1}，媒體標題通常只寫一半，另一半要自己翻內文才看得到…", None),
    ("a_k3", "article", "冷知識", "好笑", "冷知識：一則{subj}的新聞塞了{n_nums}個數字，真正值得記住的只有{num1}這一個！", lambda f: (_num(f.get("n_nums")) or 0) >= 3),
    ("a_k4", "article", "冷知識", "吐槽", "冷知識：{subj}的{num1}，比大多數人以為的還誇張，數字自己會說話…", None),
    ("a_f1", "article", "反差", "好笑", "標題看起來很平淡，{subj}的{num1}卻一點都不平淡，這反差我先笑為敬！", None),
    ("a_f2", "article", "反差", "吐槽", "大家都在吵別的題目，{subj}卻默默交出{num1}，安靜的人最可怕…", None),
    ("a_f3", "article", "反差", "好笑", "以為{subj}只是例行公事，結果{num1}一攤開，連標題都要重寫！", None),
    ("a_f4", "article", "反差", "吐槽", "說{subj}不重要的人，看到{num1}應該會想把話默默收回去…", None),
    # ---- 保底（任何時段、任何資料都填得起來）----
    ("g_d1", "any", "對話", "好笑", "朋友問我{kind_name}重點能不能一句話講完，我說可以，但你一定會想看完整串！", None),
    ("g_d2", "any", "對話", "吐槽", "同事問今天{kind_name}有什麼好看，我說一言難盡，所以直接拆成一整串給他…", None),
    ("g_k1", "any", "冷知識", "好笑", "冷知識：{kind_name}最有用的資訊通常不在第一張圖，在後面的串文，往下滑就知道了！", None),
    ("g_k2", "any", "冷知識", "吐槽", "冷知識：多數人只看第一張圖就下結論，{kind_name}真正的轉折都藏在後面的數字裡…", None),
    ("g_f1", "any", "反差", "好笑", "以為今天{kind_name}會很無聊，結果數字一攤開，劇情比八點檔還精彩！", None),
    ("g_f2", "any", "反差", "吐槽", "表面上風平浪靜，{kind_name}的數字一排出來根本暗潮洶湧…", None),
]
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
    grab(r"外資(買超|賣超) ([\d,.]+) ?億", "fx_act", "fx_amt")
    grab(r"投信(買超|賣超) ([\d,.]+) ?億(?:，已連 (\d+) 日)?", "trust_act", "trust_amt", "trust_streak")
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
    for k in ("up1p", "dn1p", "idx_pct", "tx_chg"):
        if f.get(k):
            f[k + "_abs"] = _abs(f[k])
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
        units.insert(0, _rewrite(_strip_tags(title)))
    return [u for u in units if u.strip()]


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
            title = "｜".join(l.lstrip("#").strip() for l in lines)
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
    return build("article", allt, images=["x"] * (n_images if n_images in (0, 2) else 0), url=url, state=state, today=today,
                 extra=ex, sections=secs, title=title, legal=legal, item_max=THREAD_TARGET,
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
    h = HOOK_BY_ID["g_f1"] if last_type != "反差" else HOOK_BY_ID["g_d1"]
    return h, _fill(h[4], f) or h[4], "保底"


# ---------------------------------------------------------------- 圖：0 或 2 張
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
    if len(imgs) < 2:
        return []           # 只有 1 張不准發 1 張 → 0 張（規則 8）；呼叫端寫 alert
    pri = IMG_PRIORITY.get(kind, [])
    ranked = sorted(imgs, key=lambda x: next((i for i, k in enumerate(pri) if k in Path(x).stem), 99))
    return ranked[:2]


def idea_of(path: str) -> str:
    st = Path(path).stem
    return next((v for k, v in IMG_IDEA.items() if k in st), st)


# ---------------------------------------------------------------- 組裝
def reply_text(url: str, kind: str, legal: str = "") -> str:
    lead = {"intraday": "完整熱力圖、資金分流樹都在網站，族群一個一個點得開：",
            "close": "法人、融資融券完整排行都在網站，個股一檔一檔查得到：",
            "premarket": "美股、台指期夜盤與今天的事件行事曆都在網站：",
            "credit": "融資融券完整排行都在網站："}.get(kind, "整理好的圖表與產業鏈都在網站：")
    return ((legal + "\n") if legal else "") + "👉 " + lead + "\n" + url


def assemble(kind: str, hook, hook_txt: str, tag: str, threads: list[str], reply: str, images: list[str], level: str = "") -> dict:
    main = f"{hook_txt}\n#{tag}"
    d = dict(hook_type=hook[2], emotion=hook[3], main_post=main, main_post_length=clen(hook_txt),
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
    ttl = p1["title"] if title is None else title
    f = facts(kind, text, reply, extra)
    tag = pick_tag(kind, (text + "\n" + reply) if tag_text is None else tag_text, f)
    units = section_units(secs, ttl, item_max=item_max)
    threads = pack(units)
    rp = reply_text(url, kind, legal)
    imgs = list(images or [])
    if kind != "article":
        imgs = pick_images(kind, imgs)

    def check(h, txt):
        return not lint(assemble(kind, h, txt, tag, threads, rp, imgs))[0]

    hook, txt, level = choose_hook(kind, f, state, today, tag, check)
    d = assemble(kind, hook, txt, tag, threads, rp, imgs, level)
    d["images"] = imgs
    return d


def record(state: dict, d: dict, kind: str, today: str, key: str = "") -> None:
    state.setdefault("history", []).append(dict(date=today, kind=kind, template=d["template"], type=d["hook_type"],
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
    m["threads"] = dict(text=d["main_post"], images=d["images"], thread_posts=d["thread_posts"],
                        reply_post=d["reply_post"], v2={k: v for k, v in d.items() if k != "images"})
    if len(th.get("images", [])) and not d["images"]:
        (mp.parent / "alert.txt").open("a", encoding="utf-8").write("Threads 只有 1 張圖可用，依規則改成 0 張\n")
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
