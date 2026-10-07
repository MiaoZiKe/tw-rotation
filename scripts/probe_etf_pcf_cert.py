"""ETF 成分股第三輪探測（2026-10-08）—— 只在 Actions 手動跑（mode=cert）。

為什麼要這支：
1. 大華銀官網憑證鏈不完整。要把「缺的中繼憑證」補進驗證清單，得先在連得到的主機上
   讀出伺服器送了哪幾張、葉憑證 AIA 欄位指向哪個 CA Issuers 網址，下載下來轉 PEM 印出來，
   再把那張公開的中繼憑證存進 repo（pipeline/sources/certs/），並驗證 certifi＋它能通過。
   全程不關憑證驗證。
2. 玩股網、口袋證券：把 robots.txt 與條款頁原文印出來判斷能不能程式抓取（WebSearch 只給摘要，讀不到條文）。
3. 其他沒接上的投信：命令列參數給的候選網址逐一試。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import certifi
import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def sh(cmd: str, inp: str | None = None) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, input=inp)
    return r.stdout + r.stderr


def cert_chain(host: str) -> None:
    print("=" * 100, "\n[cert]", host)
    out = sh(f"openssl s_client -connect {host}:443 -servername {host} -showcerts", inp="")
    pems = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", out, re.S)
    print("  伺服器送了", len(pems), "張")
    for i, p in enumerate(pems):
        print(sh("openssl x509 -noout -subject -issuer -dates -ext authorityInfoAccess", inp=p + "\n"))
    if not pems:
        print(out[:1000])
        return
    aia = re.findall(r"CA Issuers - URI:(\S+)", sh("openssl x509 -noout -ext authorityInfoAccess", inp=pems[0] + "\n"))
    for u in aia:
        print("  AIA →", u)
        try:
            r = requests.get(u, timeout=30, headers={"User-Agent": UA})
            open("/tmp/inter.der", "wb").write(r.content)
            pem = sh("openssl x509 -inform DER -in /tmp/inter.der")
            if "BEGIN CERTIFICATE" not in pem:
                pem = sh("openssl x509 -in /tmp/inter.der")
            pem = pem[pem.index("-----BEGIN"):] if "-----BEGIN" in pem else pem
            print(sh("openssl x509 -noout -subject -issuer -dates -fingerprint -sha256", inp=pem))
            print("INTERMEDIATE_PEM_BEGIN\n" + pem + "INTERMEDIATE_PEM_END")
            bundle = "/tmp/bundle.pem"
            open(bundle, "w").write(open(certifi.where()).read() + "\n" + pem)
            for url in (f"https://{host}/",
                        f"https://{host}/json/reply/WebSitePcfRequest?fundID=88329556&pcfDate="):
                try:
                    rr = requests.get(url, timeout=30, verify=bundle, headers={"User-Agent": UA})
                    print("  驗證通過", url, rr.status_code, rr.text[:3000].replace("\n", " "))
                except Exception as e:  # noqa: BLE001
                    print("  仍失敗", url, str(e)[:300])
        except Exception as e:  # noqa: BLE001
            print("  AIA 下載失敗", e)


def get(url: str, n: int = 3000, grep: str | None = None) -> None:
    print("=" * 100, "\n[get]", url)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": UA})
        t = r.text
        print(f"  HTTP {r.status_code} bytes={len(r.content)} type={r.headers.get('content-type')} final={r.url}")
        if grep:
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
            for m in list(re.finditer(grep, txt))[:20]:
                print("   >>", txt[max(0, m.start() - 300):m.end() + 400])
        else:
            print(t[:n])
    except Exception as e:  # noqa: BLE001
        print("  失敗", str(e)[:300])


def uob_discover() -> None:
    """第二輪：用 repo 裡的中繼憑證連大華銀，從前端 JS 找出「代號 → 內部 fundID」從哪支 API 來。"""
    import os
    bundle = "/tmp/uob_bundle.pem"
    here = os.path.dirname(os.path.abspath(__file__))
    open(bundle, "w").write(open(certifi.where()).read() + "\n" +
                            open(os.path.join(here, "..", "pipeline", "sources", "certs", "uobam_intermediate.pem")).read())
    S = requests.Session()
    S.headers["User-Agent"] = UA
    S.verify = bundle
    home = S.get("https://www.uobam.com.tw/", timeout=30).text
    js = sorted(set(re.findall(r'src="(/static/js/[^"]+\.js)"', home)))
    print("[uob] js:", js)
    for j in js:
        t = S.get("https://www.uobam.com.tw" + j, timeout=60).text
        for m in sorted(set(re.findall(r'["`/](json/reply/[A-Za-z]+|api/[A-Za-z/]+)', t)))[:200]:
            print("   api:", m)
        for m in list(re.finditer(r"WebSitePcfRequest|fundID|etf002", t))[:15]:
            print("   >>", t[max(0, m.start() - 300):m.end() + 300].replace("\n", " "))
    for u in sys.argv[1:]:
        if "uobam" in u:
            try:
                r = S.get(u, timeout=30)
                print("[uob get]", u, r.status_code, r.text[:4000])
            except Exception as e:  # noqa: BLE001
                print("[uob get] 失敗", u, e)


if __name__ == "__main__":
    if os.environ.get("UOB_ONLY"):
        uob_discover()
        raise SystemExit
    cert_chain("www.uobam.com.tw")
    for u in ("https://www.wantgoo.com/robots.txt", "https://www.pocket.tw/robots.txt"):
        get(u)
    pat = r"爬|程式|自動|擷取|機器人|重製|轉載|複製|robot|crawl|spider"
    get("https://www.wantgoo.com/terms-and-policies", grep=pat)
    for c in range(1, 8):
        get(f"https://www.pocket.tw/footer/?category={c}", grep=pat)
    for u in sys.argv[1:]:
        get(u, 1500)
