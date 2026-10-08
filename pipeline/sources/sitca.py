"""投信投顧公會（SITCA）每月公告的「基金前十大投資標的」—— ETF 成分股的第二順位來源（月資料）。

為什麼要這支（2026-10-08 ETF 成分股第五輪，Andy：「所有 ETF 的成分股分頁都要跟有成分股的 ETF 一樣，有圖、有清單」）：
- 第一順位是各發行投信官網每日公告（pipeline/sources/etf_pcf.py），但有幾家抓不到：兆豐官網對雲端主機回 403（Akamai）、
  貝萊德產品頁同樣擋雲端主機、摩根的使用條款明文禁止程式抓取、富蘭克林華美的 ETF 持股頁找不到、第一金債券型只給類別彙總。
- 公會依法彙整「各投信公司」每月申報的前十大投資標的，公開在 www.sitca.org.tw（政府委託的同業公會統計頁，沒有 robots.txt 限制，
  2026-10-08 在 Actions 上實測 requests 直接 200）。每檔 ETF 都在裡面 —— 這是「官網抓不到時」最一手、最完整的替代來源。
- 代價：**月資料、只有前十大**。前端標「月資料・資料日 YYYY-MM-DD（月底）・來源 投信投顧公會」，讀者看得出不是每日持股。

頁面（2026-10-08 實測，probe-etf-pcf.yml mode=sitca run 37779040871、37779498801）：
  GET  /ROC/Industry/IN2629.aspx            → ASP.NET 表單（__VIEWSTATE、__EVENTVALIDATION）、年月下拉（selected＝最新已公告月）
  POST 同一頁 rdo1=rbClass＋ddlQ_Class=<類型>＋ddlQ_YM=<年月>＋BtnQuery=查詢
       → 表格每列：[基金名稱(rowspan), 名次, 標的種類, 標的代號或 ISIN, 標的名稱, 金額, 擔保機構, 次順位債券, 受益權單位數, 占淨資產%]
         第一名那列帶基金名稱（10 格），第 2～10 名沒有（9 格），最後一列「合計」。
  類型只查 ETF 的（AH 指數股票型、AL 主動式 ETF），槓桿／反向（AH13、AH23、AH24）不查 —— 那些是期貨，不列成分。

回應裡沒有 ETF 代號，只有基金全名（例「兆豐臺灣藍籌30ETF基金」），要用簡稱（company_info 的 name，例「兆豐藍籌30」）對回去：
  match_code() 先把常見縮寫展開（US→美國、投等→投資級…），再看「簡稱去掉投信名」的每個字有沒有依序出現在全名裡；
  同一家投信有兩檔以上都對得上就不猜（寧可空著，也不要把 A 的成分放到 B 頭上）。
失敗一律回空 DataFrame 並把回應前 200 字記進 log（照爬蟲紅線）。
"""
from __future__ import annotations

import calendar
import html as _html
import logging
import re
import time
from typing import Any

import pandas as pd

from ..util import http

log = logging.getLogger(__name__)

URL = "https://www.sitca.org.tw/ROC/Industry/IN2629.aspx"
P = "ctl00$ContentPlaceHolder1$"
# ETF 類型（2026-10-08 實測的下拉選單）。槓桿／反向 AH13、AH23、AH24 不查。
ETF_CLASSES = ["AH11", "AH12", "AH14", "AH15", "AH21", "AH22", "AH25", "AH26", "AL11", "AL12", "AL19", "AL21", "AL22", "AL29"]
COLS = ["date", "ym", "fund", "rank", "kind", "code", "name", "amount", "weight", "etf", "issuer", "src"]
TIMEOUT = 60


def _snip(t: Any) -> str:
    return str(t or "")[:200].replace("\n", " ").replace("\r", " ")


def _txt(cell: str) -> str:
    c = re.sub(r"(?i)<br\s*/?>", "\n", cell)
    return _html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()


def _num(s: Any) -> float | None:
    t = str(s or "").replace(",", "").replace("%", "").strip()
    try:
        return float(t) if t else None
    except ValueError:
        return None


def hidden_fields(page: str) -> dict:
    out = {}
    for m in re.finditer(r'(?is)<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page or ""):
        out[m.group(1)] = _html.unescape(m.group(2))
    return out


def latest_ym(page: str) -> str | None:
    """年月下拉裡 selected 的那個（＝公會最新已公告月）；沒標 selected 就取最大的。"""
    m = re.search(r'(?is)<select[^>]*name="[^"]*ddlQ_YM"[^>]*>(.*?)</select>', page or "")
    if not m:
        return None
    sel = re.search(r'<option[^>]*selected[^>]*value="(\d{6})"', m.group(1)) or re.search(r'<option[^>]*value="(\d{6})"[^>]*selected', m.group(1))
    if sel:
        return sel.group(1)
    vals = re.findall(r'value="(\d{6})"', m.group(1))
    return max(vals) if vals else None


def month_end(ym: str) -> str:
    y, mo = int(ym[:4]), int(ym[4:6])
    return f"{y:04d}-{mo:02d}-{calendar.monthrange(y, mo)[1]:02d}"


def parse_top10(page: str, ym: str) -> list[dict]:
    """POST 回應 → 每檔基金的前十大。第一名那列 10 格（帶基金名稱），其後 9 格；「合計」列略過。"""
    rows: list[dict] = []
    fund = None
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page or ""):
        cells = [_txt(c) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", tr)]
        if not cells:
            continue
        if cells[0].startswith("合計"):
            continue
        if len(cells) >= 10 and re.fullmatch(r"\d{1,2}", cells[1] or ""):
            fund = cells[0].split("\n")[0].strip()
            cells = cells[1:]
        elif len(cells) == 9 and re.fullmatch(r"\d{1,2}", cells[0] or ""):
            pass
        else:
            continue
        if not fund:
            continue
        rank, kind, code, name, amount = cells[0], cells[1], cells[2], cells[3], cells[4]
        w = _num(cells[8])
        if not code or w is None:
            continue
        rows.append({"date": month_end(ym), "ym": ym, "fund": fund, "rank": int(rank), "kind": kind,
                     "code": code.strip(), "name": name.rstrip("*").strip(), "amount": _num(amount), "weight": w})
    return rows


# ───────────────────────────── 基金全名 → ETF 代號
_ABBR = [("US", "美國"), ("美債", "美國公債"), ("非投等", "非投資等級"), ("投等", "投資級"), ("臺", "台"), ("ＥＴＦ", "ETF"),
         ("+", ""), ("＋", "")]
_ISSUER_WORDS = ("富蘭克林華美", "富蘭克林", "兆豐", "貝萊德", "摩根", "聯邦", "第一金", "元大", "國泰", "群益", "富邦", "統一", "凱基",
                 "大華銀", "大華", "復華", "中信", "中國信託", "野村", "新光", "台新", "永豐", "聯博", "安聯", "玉山", "華南永昌", "街口")


def _norm(s: str) -> str:
    s = re.sub(r"[（(].*?[)）]", "", str(s or ""))        # 「(基金之配息來源可能為收益平準金)」這類括號註記
    s = re.sub(r"^(主動|平衡|期)", "", s.strip())
    s = re.sub(r"^FT", "富蘭克林華美", s)                   # 證交所簡稱「FT臺灣Smart」＝富蘭克林華美
    for a, b in _ABBR:
        s = s.replace(a, b)
    return re.sub(r"\s+", "", s)


def _core(short: str) -> str:
    s = _norm(short)
    for w in _ISSUER_WORDS:
        if s.startswith(w):
            return s[len(w):]
    return s


def _issuer_prefix(full: str) -> str:
    s = _norm(full)
    for w in _ISSUER_WORDS:
        if s.startswith(w):
            return w
    return ""


def _subseq(a: str, b: str) -> bool:
    it = iter(b)
    return all(ch in it for ch in a)


def match_code(fund: str, names: dict[str, str]) -> str | None:
    """基金全名 → ETF 代號。names＝{代號: 簡稱}。只在同一家投信的 ETF 裡找；簡稱核心字依序出現在全名裡才算；
    對上兩檔以上時，取「全名去掉投信與 ETF/基金 字樣後最短、而且只有一檔是最短」的；還是平手就回 None（不猜）。"""
    full = _norm(fund)
    pre = _issuer_prefix(fund)
    body = full[len(pre):] if pre else full
    body = re.sub(r"(證券投資信託|ETF|基金|傘型|子基金)", "", body)
    hits = []
    for code, short in names.items():
        sn = _norm(short)
        spre = _issuer_prefix(short)
        if pre and spre and _norm(spre)[:2] != _norm(pre)[:2]:
            continue
        core = re.sub(r"(ETF)", "", _core(short))
        if core and _subseq(core, body):
            hits.append((len(body) - len(core), code))
    if not hits:
        return None
    hits.sort()
    if len(hits) > 1 and hits[0][0] == hits[1][0]:
        log.info("公會基金「%s」對到兩檔以上（%s），不猜", fund, [c for _, c in hits[:4]])
        return None
    return hits[0][1]


def top10(names: dict[str, str], ym: str | None = None, classes: list[str] | None = None,
          have_yms: set[str] | None = None) -> pd.DataFrame:
    """抓公會「基金前十大投資標的」ETF 類型的全部基金，對回代號。ym 不給就用公會最新已公告月。
    回傳欄位 COLS；對不回代號的基金照樣保留（etf 空白），build 時只用有代號的。"""
    s = http.session()
    try:
        r = s.get(URL, timeout=TIMEOUT)
        r.encoding = r.apparent_encoding or "utf-8"
        first = r.text
    except Exception as exc:  # noqa: BLE001
        log.warning("公會前十大 GET 失敗：%s", str(exc)[:200])
        return pd.DataFrame(columns=COLS)
    ym = ym or latest_ym(first)
    if ym and have_yms and ym in have_yms:
        # 資料湖已經有公會最新這個月 → 不重抓（DECISIONS #155：會重複用到的存湖、抓取一律增量）
        log.info("公會前十大 %s 已在資料湖，跳過", ym)
        return pd.DataFrame(columns=COLS)
    base = hidden_fields(first)
    if not ym or "__VIEWSTATE" not in base:
        log.warning("公會前十大頁面認不得（前 200 字）：%s", _snip(first))
        return pd.DataFrame(columns=COLS)
    rows: list[dict] = []
    for cls in classes or ETF_CLASSES:
        data = {k: v for k, v in base.items() if k.startswith("__")}
        data.update({P + "ddlQ_YM": ym, P + "rdo1": "rbClass", P + "ddlQ_Class": cls, P + "BtnQuery": "查詢"})
        try:
            time.sleep(1)
            r2 = s.post(URL, data=data, timeout=TIMEOUT)
            r2.encoding = r2.apparent_encoding or "utf-8"
            got = parse_top10(r2.text, ym)
        except Exception as exc:  # noqa: BLE001 —— 一個類型失敗不影響其他類型
            log.warning("公會前十大 %s %s 失敗：%s", ym, cls, str(exc)[:200])
            continue
        if not got and "基金名稱" not in r2.text:
            log.warning("公會前十大 %s %s 回應認不得（前 200 字）：%s", ym, cls, _snip(r2.text))
        log.info("公會前十大 %s %s：%d 檔基金、%d 列", ym, cls, len({x['fund'] for x in got}), len(got))
        rows += got
    if not rows:
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame(rows)
    fmap = {f: match_code(f, names) for f in df["fund"].unique()}
    df["etf"] = df["fund"].map(fmap)
    from .etf_pcf import issuer_of
    df["issuer"] = df["etf"].map(lambda c: issuer_of(names.get(c, "")) if c else None)
    df["src"] = URL
    return df[COLS]


if __name__ == "__main__":  # Actions 上自我測試：python -m pipeline.sources.sitca（不寫湖）
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from ..util import store

    ci = store.read("company_info")
    m = ci["industry"].isin(["ETF", "上櫃ETF"])
    nm = dict(zip(ci.loc[m, "code"].astype(str), ci.loc[m, "name"].astype(str)))
    out = top10(nm)
    print("合計", len(out), "列，基金", out["fund"].nunique() if len(out) else 0, "檔，對上代號", out["etf"].nunique() if len(out) else 0, "檔")
    for f, g in out.groupby("fund"):
        print(f"  {g['etf'].iloc[0] or '（對不上）'}\t{nm.get(g['etf'].iloc[0] or '', '')}\t← {f}\t{g['date'].iloc[0]}\t{len(g)} 列\t前三：",
              g.sort_values('rank').head(3)[['code', 'name', 'weight']].values.tolist())
