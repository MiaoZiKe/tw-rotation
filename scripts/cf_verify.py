"""部署後驗證：本地部署包的每一個檔，在 Cloudflare 那一份是不是都拿得到（HTTP 200）。

用法：python scripts/cf_verify.py <本地目錄> <基底網址> [--sample N] [--out 缺漏清單.txt]
  · 預設逐檔檢查；--sample N 只抽 N 檔（用在自訂網域，避免大量打正式網域）。
  · 缺漏（非 200）清單寫到 --out；有缺漏 → 結束碼 1。
  · 不看內容雜湊（Cloudflare/自訂網域可能壓縮 HTML）；內容新舊另用 index.html 的版本戳比對（--stamp）。
"""
import argparse, random, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKIP = {"_headers", "_redirects", "_routes.json", "_worker.js"}


def head(base, rel):
    p = rel.as_posix()
    if p.endswith("index.html"):
        p = p[: -len("index.html")]
    url = base.rstrip("/") + "/" + urllib.parse.quote(p)
    code = 0
    for i in range(4):
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "tw-rotation-cf-verify"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return rel, r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = 0
        time.sleep(1 + i)
    return rel, code


def stamp_of(text):
    return sorted(set(re.findall(r"\?v=([0-9A-Za-z._-]+)", text)))[:3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir"); ap.add_argument("base")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--out", default="cf_missing.txt")
    ap.add_argument("--stamp", action="store_true", help="另比對 index.html 的 ?v= 版本戳")
    a = ap.parse_args()
    root = Path(a.dir)
    files = [f.relative_to(root) for f in root.rglob("*") if f.is_file() and f.name not in SKIP]
    if a.sample and len(files) > a.sample:
        keep = [f for f in files if "/" not in f.as_posix()]  # 根目錄的檔一律檢查
        rest = [f for f in files if f not in set(keep)]
        random.seed(1); files = keep + random.sample(rest, max(0, a.sample - len(keep)))
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(lambda f: head(a.base, f), files))
    bad = [(r.as_posix(), c) for r, c in res if c != 200]
    Path(a.out).write_text("".join(f"{c} {p}\n" for p, c in bad), encoding="utf-8")
    print(f"檢查 {len(files)} 檔 @ {a.base}：缺漏 {len(bad)}")
    for p, c in bad[:30]:
        print("  缺", c, p)
    rc = 1 if bad else 0
    if a.stamp:
        loc = stamp_of((root / "index.html").read_text(encoding="utf-8"))
        try:
            with urllib.request.urlopen(urllib.request.Request(a.base, headers={"User-Agent": "tw-rotation-cf-verify"}), timeout=30) as r:
                rem = stamp_of(r.read().decode("utf-8", "replace"))
        except Exception as e:
            rem = [f"讀取失敗 {e}"]
        ok = loc == rem and loc
        print(f"版本戳 本地 {loc} / 線上 {rem} → {'一致' if ok else '不一致'}")
        if not ok:
            rc = 1
    sys.exit(rc)


if __name__ == "__main__":
    main()
