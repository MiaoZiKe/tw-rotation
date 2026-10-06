"""從「私人 repo 的工作目錄」產出「公開版目錄」（2026-10-07 repo 拆分，說明見 docs/repo_split_plan.md）。

用途
----
私人 repo 是唯一的原始碼來源（含 CLAUDE.md、DECISIONS、docs、Andy 原話…）。
公開 repo 只放「執行需要」的東西。這支腳本決定「什麼可以公開」並處理檔案內容，
**同步工作流（sync-to-public.yml）與本機試跑都用同一支**，確保兩邊的結果一致。

做的事（依序）
--------------
1. 列出 src 裡所有 git 追蹤的檔案（沒有 git 就走訪目錄），逐一用「允許清單＋排除清單」分類。
2. 複製允許的檔案到 --out（先清空 --out；**不碰 --out 以外的任何地方**）。
3. 去註解：
   · site/** 的 JS／CSS／HTML → 呼叫 scripts/minify_site.py（跟 pages.yml 部署前用的是同一套，esbuild）。
   · workers/** 的 .js／.mjs → esbuild 不壓縮、只丟掉註解（格式保留，讓 wrangler 與測試照舊能跑）。
   · .yml／.yaml／.toml／.gitignore → 只拿掉「整行都是註解」的行（行尾註解不動，避免誤砍字串）；
     YAML 資料檔拿掉註解後必須「載入結果完全相同」，否則該檔原樣保留並警告。
   · Python：**不處理**（註解與 docstring 原樣）。只在報告裡數出還剩多少「Andy／原話」。
4. 掃描（硬性關卡，任何一項命中就 exit 1，同步工作流因此失敗、不會推到公開 repo）：
   · 禁止出現的路徑：CLAUDE.md／AGENTS.md／DECISIONS.md／HANDOFF.md、docs/（docs/fixtures 除外）、
     obsidian/、.claude/、tools/、任何 *.md（本腳本自己產生的 README.md 除外）、data/、site/data/
   · 金鑰樣式：github_pat_／ghp_／JWT（FinMind 權杖）／Cloudflare／Google API key
   · 「Andy 原話」這個詞組（Andy 與「原話」相距 12 字內）
   · 只警告不擋（印出數字，供 Andy 判斷）：內文裡的 CLAUDE.md、DECISIONS、HANDOFF、docs/ 提及，以及「Andy」字樣。
     想把這些也變成硬性關卡：加 --strict-mentions。

不放進公開版的目錄／檔案（完整清單在 DENY_* 與 ALLOW_*）：
   data/ 不在這裡處理 —— 資料湖的權威在公開 repo，同步時一律不碰（見 sync-to-public.yml 的 rsync 排除）。

用法
----
    python scripts/build_public_tree.py --out /tmp/public_tree             # 從本 repo 產出
    python scripts/build_public_tree.py --out DIR --no-minify              # 沒有 esbuild 時只看分類與掃描
    python scripts/build_public_tree.py --scan-only DIR [--allow-data]     # 只掃描現成目錄（同步後二次確認）
    python scripts/build_public_tree.py --out DIR --manifest m.json        # 另存清單
退出碼：0 通過；1 掃描失敗或處理失敗；2 參數／環境問題。
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── 允許清單 ────────────────────────────────────────────────────────────────
# 目錄前綴（相對 repo 根，用 / 分隔）。其餘一律不公開。
ALLOW_PREFIXES = ("pipeline/", "site/", "workers/", "tests/")
# 工作流：來源有 public-ci/workflows/ 就用它（私人 repo 的建議配置，見計畫書），否則用 .github/workflows/。
WORKFLOW_SRC_DIRS = ("public-ci/workflows/", ".github/workflows/")
WORKFLOW_DST = ".github/workflows/"
# 只在私人 repo 跑的工作流，永遠不進公開版。
PRIVATE_ONLY_WORKFLOWS = {"sync-to-public.yml", "pull-data-from-public.yml"}
# 根目錄單檔
ALLOW_ROOT_FILES = {"requirements.txt", ".gitattributes", ".gitignore"}
# scripts/：只放「工作流或 pytest 會用到」的。其餘（_uitest、_preview、_show、gen_*、_perf*、gh_push、deploy_wait…）是開發工具，留在私人。
ALLOW_SCRIPTS = {
    "scripts/__init__.py",
    "scripts/stamp_assets.py",       # pages.yml／daily.yml 版本戳；tests/test_stamp_assets.py
    "scripts/minify_site.py",        # pages.yml 部署前壓縮
    "scripts/preview_inject.py",     # pages.yml／daily.yml 分支預覽；tests/test_preview_inject.py
    "scripts/preview_boot.js",       # preview_inject 會複製它
    "scripts/probe_sources.py",      # probe.yml；tests/test_probe_sources.py
    "scripts/live_rotation_probe.py",  # live-rotation-probe.yml；tests/test_live_rotation_probe.py
    "scripts/eval_news_tech_filter.py",  # tests/test_sources_v3.py 以路徑載入
    "scripts/_make_perf_fixture.py",  # tests/test_perf_golden.py 匯入
}
# docs/ 只放測試與 probe 工作流要用的 fixtures
ALLOW_DOC_PREFIXES = ("docs/fixtures/",)

# ── 排除清單（即使落在允許的目錄裡也不放）──────────────────────────────────
DENY_GLOBS = (
    "*.md",                       # 任何 Markdown（說明文件都留私人）；本腳本自己產生的 README.md 例外
    "*.pyc", "*/__pycache__/*", "__pycache__/*",
    "*/node_modules/*", "*.map",
    "site/data/*",                # 工作流產出的 JSON，不進版控也不進公開版
    "*.token", ".env", ".env.*",
)
# 測試若依賴「不公開」的檔案，要在這裡列出、一起排除（公開 repo 的 daily.yml 會跑 pytest）。
# 2026-10-07 以實際跑 pytest 的結果決定：見 docs/repo_split_plan.md §3。
DENY_TESTS: set[str] = {
    "tests/test_delivery_log.py",   # 讀 docs/delivery_log.md（Andy 原話逐字清單，不公開）
}
# 讀「site／workers 原始碼文字」的守門測試：公開版的 site／workers 已去註解、壓縮，文字比對一定對不上，
# 所以在公開 repo 的 pytest 裡略過（這幾條仍在私人 repo 跑，那裡的原始碼才是權威）。
# 2026-10-07 實際在公開版目錄跑完整 pytest 得到的 3 條（其餘 1,043 條全過）。
PUBLIC_SKIP_TESTS = (
    "tests/test_delivery_guard.py::test_前端真的改吃color_idx",
    "tests/test_probe_sources.py::test_對照組的標頭跟_Worker_逐字元相同",
    "tests/test_rrg_lite_payload.py::test_rrg_lite_payload_written_by_build_and_read_by_overview",
)
CONFTEST_APPEND = '''

# ---- 公開版附加（scripts/build_public_tree.py 產生，請勿手改）----
# 下面這些測試比對的是 site／workers「原始碼文字」；公開版已去註解、壓縮，文字比對必然失敗。
_PUBLIC_SKIP = %r


def pytest_collection_modifyitems(config, items):
    for it in items:
        if it.nodeid in _PUBLIC_SKIP:
            it.add_marker(pytest.mark.skip(reason="公開版的 site／workers 已壓縮；此測試只在原始碼 repo 跑"))
'''

# docs/delivery_log.md 的政策：True＝連同交付清單一起公開（網站「交付清單」頁會有內容）；False＝不公開（該頁在公開 repo 產出為空）。
# 預設 False，等 Andy 決定（計畫書 §10 待決事項 2）。
INCLUDE_DELIVERY_LOG = False

# 本腳本自己產生的 README.md（刻意極簡、不提任何內部資訊）
PUBLIC_README = """# tw-rotation

自動化資料管線與靜態網站的執行用 repo：每日盤後抓取資料、計算指標、部署網站。

- 原始碼由另一個 repo 同步而來，**請勿直接在此修改程式碼**（下次同步會被覆蓋）。
- `data/` 是資料湖，由本 repo 的排程工作流維護。
"""

# ── 掃描規則 ────────────────────────────────────────────────────────────────
FORBIDDEN_PATH_RULES = (
    (re.compile(r"^(CLAUDE|AGENTS|DECISIONS|HANDOFF|ROADMAP|SETUP|PUSH-README)\.md$"), "內部文件"),
    (re.compile(r"^docs/(?!fixtures/)"), "docs/（只有 docs/fixtures/ 可公開）"),
    (re.compile(r"^obsidian/"), "obsidian/"),
    (re.compile(r"^\.claude/"), ".claude/"),
    (re.compile(r"^tools/"), "tools/"),
    (re.compile(r"^data/"), "data/（資料湖不由同步處理）"),
    (re.compile(r"^site/data/"), "site/data/"),
    (re.compile(r".*\.md$"), "Markdown 檔"),
    (re.compile(r"(^|/)(sync-to-public|pull-data-from-public)\.yml$"), "只限私人 repo 的工作流"),
)
SECRET_RULES = (
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"), "GitHub 權杖"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"), "JWT（FinMind 權杖長這樣）"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "私鑰"),
    (re.compile(r"(?i)finmind[_a-z]*token\s*[=:]\s*[\"'][A-Za-z0-9._-]{20,}[\"']"), "FinMind 權杖明文"),
)
ANDY_QUOTE_RULE = re.compile(r"Andy[^\n]{0,12}原話|原話[^\n]{0,12}Andy")
MENTION_RULES = {
    "CLAUDE.md": re.compile(r"CLAUDE\.md"),
    "DECISIONS": re.compile(r"DECISIONS"),
    "HANDOFF": re.compile(r"HANDOFF"),
    "docs/": re.compile(r"(?<![A-Za-z0-9_])docs/"),
    "Andy": re.compile(r"Andy"),
    "原話": re.compile(r"原話"),
}
TEXT_SUFFIXES = {".py", ".js", ".mjs", ".css", ".html", ".yml", ".yaml", ".toml", ".json", ".txt", ".ts",
                 ".webmanifest", ".svg", ".tsv", ".gitignore", ".gitattributes", ".lock", ".cfg", ".ini", ""}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".gif", ".parquet", ".woff", ".woff2", ".ttf", ".otf", ".zip", ".gz"}


# ── 分類 ────────────────────────────────────────────────────────────────────
def classify(rel: str, wf_dir: str) -> tuple[str | None, str]:
    """回傳 (目的地相對路徑 or None, 分類標籤)。None 表示不公開。"""
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith(wf_dir):
        if name in PRIVATE_ONLY_WORKFLOWS:
            return None, "排除：只限私人 repo 的工作流"
        if not rel.endswith((".yml", ".yaml")):
            return None, "排除：工作流目錄內的非 YAML"
        return WORKFLOW_DST + rel[len(wf_dir):], "工作流"
    if rel.startswith(".github/") or rel.startswith("public-ci/"):
        return None, "排除：另一份工作流目錄（不是本次的來源）"
    for g in DENY_GLOBS:
        if fnmatch.fnmatch(rel, g):
            return None, f"排除：{g}"
    if rel in DENY_TESTS:
        return None, "排除：依賴不公開檔案的測試"
    if rel == "docs/delivery_log.md" and INCLUDE_DELIVERY_LOG:
        return rel, "交付清單（Andy 決定公開）"
    if rel.startswith(ALLOW_DOC_PREFIXES):
        return rel, "docs/fixtures（測試與探測用）"
    if rel in ALLOW_ROOT_FILES:
        return rel, "根目錄設定"
    if rel.startswith("scripts/"):
        return (rel, "scripts（工作流／測試用）") if rel in ALLOW_SCRIPTS else (None, "排除：scripts 開發工具")
    for pre in ALLOW_PREFIXES:
        if rel.startswith(pre):
            return rel, pre.rstrip("/")
    top = rel.split("/", 1)[0]
    if top in ("docs", "obsidian", "tools", ".claude"):
        return None, f"排除：{top}/"
    if top == "data":
        return None, "排除：data/（資料湖由公開 repo 自己維護）"
    return None, "排除：根目錄其他檔（說明文件、本機安裝腳本）"


def list_source_files(src: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(src), "ls-files", "-z"], capture_output=True, check=True).stdout
        files = [f for f in out.decode("utf-8").split("\0") if f]
        # 稀疏檢出時，有些追蹤檔案沒有實體 —— 不算（工作流只檢出需要的目錄）
        return sorted(f for f in files if (src / f).is_file())
    except (OSError, subprocess.CalledProcessError):
        files = []
        for p in src.rglob("*"):
            if p.is_file() and ".git" not in p.relative_to(src).parts:
                files.append(p.relative_to(src).as_posix())
        return sorted(files)


# ── 去註解 ──────────────────────────────────────────────────────────────────
LINE_COMMENT = re.compile(r"^\s*#(?![#!])")     # 整行註解；保留 `###` 開頭（heredoc 內的 Markdown 標題）與 `#!`


def strip_hash_comments(text: str) -> tuple[str, int]:
    out, n = [], 0
    for ln in text.split("\n"):
        if LINE_COMMENT.match(ln):
            n += 1
            continue
        out.append(ln)
    return "\n".join(out), n


def load_minify_module(src: Path):
    p = src / "scripts" / "minify_site.py"
    spec = importlib.util.spec_from_file_location("_minify_site", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esbuild_bin() -> str | None:
    return os.environ.get("ESBUILD") or shutil.which("esbuild")


def esbuild_strip(code: str, binp: str) -> str:
    """只丟註解、不壓縮（保留格式與 ESM 的 import／export）。"""
    r = subprocess.run([binp, "--loader=js", "--legal-comments=none", "--charset=utf8"],
                       input=code.encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:1500])
    return r.stdout.decode("utf-8")


def yaml_equal(a: str, b: str) -> bool:
    try:
        import yaml  # type: ignore
    except ImportError:
        return True  # 沒有 PyYAML 就無法比對；呼叫端另外警告
    try:
        return yaml.safe_load(a) == yaml.safe_load(b)
    except Exception:  # noqa: BLE001
        return False


# ── 掃描 ────────────────────────────────────────────────────────────────────
def scan_tree(tree: Path, allow_data: bool = False, strict_mentions: bool = False) -> dict:
    fails: list[str] = []
    mentions: dict[str, Counter] = {k: Counter() for k in MENTION_RULES}
    mention_files: dict[str, set] = {k: set() for k in MENTION_RULES}
    n_files = 0
    for p in sorted(tree.rglob("*")):
        if not p.is_file() or ".git" in p.relative_to(tree).parts[:1]:
            continue
        rel = p.relative_to(tree).as_posix()
        if allow_data and rel.startswith(("data/", "docs/fixtures/")):
            continue
        n_files += 1
        if rel == "README.md":
            if p.read_text(encoding="utf-8") != PUBLIC_README:
                fails.append(f"路徑：README.md 內容不是腳本產生的版本")
            continue
        for rx, why in FORBIDDEN_PATH_RULES:
            if rx.match(rel):
                fails.append(f"路徑：{rel}（{why}）")
                break
        if p.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for rx, why in SECRET_RULES:
            if rx.search(text):
                fails.append(f"金鑰樣式：{rel}（{why}）")
        for m in ANDY_QUOTE_RULE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            fails.append(f"Andy 原話：{rel}:{line}「{text[m.start():m.end()][:40]}」")
        for k, rx in MENTION_RULES.items():
            c = len(rx.findall(text))
            if c:
                mentions[k][rel.split("/", 1)[0] if "/" in rel else "(根目錄)"] += c
                mention_files[k].add(rel)
    if strict_mentions:
        for k in ("CLAUDE.md", "DECISIONS", "HANDOFF", "docs/"):
            if mention_files[k]:
                fails.append(f"內文提及 {k}：{len(mention_files[k])} 檔（--strict-mentions）")
    return {
        "files": n_files,
        "fails": fails,
        "mentions": {k: dict(v) for k, v in mentions.items()},
        "mention_files": {k: len(v) for k, v in mention_files.items()},
        "mention_file_list": {k: sorted(v) for k, v in mention_files.items()},
    }


def print_scan(res: dict) -> None:
    print(f"\n── 掃描（{res['files']} 檔）──")
    if res["fails"]:
        print(f"✗ 硬性關卡失敗 {len(res['fails'])} 項：")
        for f in res["fails"][:60]:
            print("   ", f)
        if len(res["fails"]) > 60:
            print(f"    …另有 {len(res['fails']) - 60} 項")
    else:
        print("✓ 硬性關卡全部通過（無禁止路徑、無金鑰樣式、無「Andy 原話」詞組）")
    print("  只警告（內文提及，依頂層目錄統計次數／檔數）：")
    for k, per in res["mentions"].items():
        tot = sum(per.values())
        print(f"    {k:<10} {tot:>5} 次 / {res['mention_files'][k]:>3} 檔   {per}")


# ── 主流程 ──────────────────────────────────────────────────────────────────
def build(src: Path, out: Path, minify: bool, strict_mentions: bool, manifest: Path | None) -> int:
    if out.exists():
        if out.resolve() in (src.resolve(), Path("/"), Path.home().resolve()) or src.resolve().is_relative_to(out.resolve()):
            print(f"拒絕清空 {out}（會傷到來源）", file=sys.stderr)
            return 2
        shutil.rmtree(out)
    out.mkdir(parents=True)

    wf_dir = next((d for d in WORKFLOW_SRC_DIRS if (src / d).is_dir()), WORKFLOW_SRC_DIRS[-1])
    files = list_source_files(src)
    kept: list[tuple[str, str]] = []
    excluded: dict[str, list[str]] = defaultdict(list)
    for rel in files:
        dst, label = classify(rel, wf_dir)
        if dst is None:
            excluded[label].append(rel)
        else:
            kept.append((rel, dst))
            (out / dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, out / dst)
    (out / "README.md").write_text(PUBLIC_README, encoding="utf-8")

    stats = Counter()
    warns: list[str] = []
    binp = esbuild_bin()
    if minify and not binp:
        print("找不到 esbuild：請 npm i -g esbuild@0.28.2、設 ESBUILD，或加 --no-minify（只做分類與掃描）", file=sys.stderr)
        return 2

    # 1) 文字去註解：yml／yaml／toml／.gitignore
    for rel, dst in kept:
        p = out / dst
        suf = p.suffix.lower()
        if suf in (".yml", ".yaml", ".toml") or dst == ".gitignore":
            text = p.read_text(encoding="utf-8")
            new, n = strip_hash_comments(text)
            if suf in (".yml", ".yaml") and not yaml_equal(text, new):
                if dst.startswith(".github/workflows/"):
                    # 工作流的 run: 區塊字串會因為拿掉 shell 註解而不同，這是預期的；只確認仍是合法 YAML
                    try:
                        import yaml  # type: ignore
                        yaml.safe_load(new)
                    except ImportError:
                        pass
                    except Exception as e:  # noqa: BLE001
                        warns.append(f"{dst}：去註解後 YAML 不合法，原樣保留（{e}）")
                        continue
                else:
                    warns.append(f"{dst}：去註解後資料不同（區塊字串內有 # 行），原樣保留")
                    continue
            p.write_text(new, encoding="utf-8")
            stats["hash_comment_lines"] += n
            stats["hash_files"] += 1

    # 1a) 公開版 pytest 要略過的「原始碼文字」測試
    conf = out / "tests" / "conftest.py"
    if conf.is_file():
        conf.write_text(conf.read_text(encoding="utf-8") + CONFTEST_APPEND % (PUBLIC_SKIP_TESTS,), encoding="utf-8")
        stats["conftest_skips"] = len(PUBLIC_SKIP_TESTS)

    # 1b) site 的 JSON／manifest：拿掉頂層「_註解…」欄位（site/manifest.webmanifest 有一條寫了內部決策）
    for rel, dst in kept:
        if dst.startswith("site/") and dst.endswith((".json", ".webmanifest")):
            p = out / dst
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if isinstance(d, dict) and any(k.startswith("_註解") for k in d):
                d = {k: v for k, v in d.items() if not k.startswith("_註解")}
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                stats["json_note_keys"] += 1

    # 2) workers 的 JS：只丟註解
    if minify:
        for rel, dst in kept:
            if dst.startswith("workers/") and dst.endswith((".js", ".mjs")):
                p = out / dst
                try:
                    new = esbuild_strip(p.read_text(encoding="utf-8"), binp)
                except RuntimeError as e:
                    print(f"::error::workers 去註解失敗 {dst}：{e}", file=sys.stderr)
                    return 1
                p.write_text(new, encoding="utf-8")
                chk = subprocess.run(["node", "--check", str(p)], capture_output=True) if shutil.which("node") else None
                if chk is not None and chk.returncode != 0:
                    # 檔案是 ESM 時 node --check 需要 .mjs；.js 失敗不代表壞，改用 esbuild 自己重新解析
                    r = subprocess.run([binp, "--loader=js", "--log-level=error"], input=new.encode("utf-8"), capture_output=True)
                    if r.returncode != 0:
                        print(f"::error::workers 去註解後無法解析 {dst}", file=sys.stderr)
                        return 1
                stats["worker_js"] += 1

    # 3) site：同 pages.yml 的壓縮
    if minify and (out / "site").is_dir():
        mod = load_minify_module(src)
        os.environ["ESBUILD"] = binp
        rc = mod.main(out / "site")
        if rc != 0:
            print("::error::site 壓縮失敗", file=sys.stderr)
            return 1

    # 4) 掃描
    res = scan_tree(out, strict_mentions=strict_mentions)

    # ── 報告 ──
    print(f"來源：{src}")
    print(f"工作流來源目錄：{wf_dir}")
    print(f"git 追蹤且有實體的檔案：{len(files)}")
    print(f"公開版：{len(kept)} 檔（+ 產生的 README.md）→ {out}")
    by_label = Counter(l for _, l in [(r, classify(r, wf_dir)[1]) for r, _ in kept])
    for k, v in sorted(by_label.items(), key=lambda kv: -kv[1]):
        print(f"    放入 {k:<28} {v:>5}")
    print(f"排除：{sum(len(v) for v in excluded.values())} 檔")
    for k, v in sorted(excluded.items(), key=lambda kv: -len(kv[1])):
        print(f"    {k:<44} {len(v):>5}   例：{', '.join(v[:2])}")
    print(f"去註解：yml/yaml/toml/.gitignore {stats['hash_files']} 檔、拿掉 {stats['hash_comment_lines']} 行整行註解；"
          f"site JSON 註解欄位 {stats['json_note_keys']} 檔；workers JS {stats['worker_js']} 檔；site 走 minify_site.py（{'已執行' if minify else '略過（--no-minify）'}）")
    for w in warns:
        print("警告：", w)
    if not minify:
        print("警告：--no-minify：site／workers 沒去註解，下面的掃描數字不代表實際同步結果")
    print_scan(res)

    if manifest:
        manifest.write_text(json.dumps({
            "kept": [d for _, d in kept], "excluded": {k: v for k, v in excluded.items()},
            "scan": {k: res[k] for k in ("files", "fails", "mentions", "mention_files")}, "warnings": warns,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if res["fails"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(ROOT), help="私人 repo 工作目錄（預設：本 repo）")
    ap.add_argument("--out", help="輸出目錄（會先清空）")
    ap.add_argument("--no-minify", action="store_true", help="不呼叫 esbuild（只做分類與掃描）")
    ap.add_argument("--strict-mentions", action="store_true", help="內文提及 CLAUDE.md／DECISIONS／HANDOFF／docs/ 也當硬性失敗")
    ap.add_argument("--manifest", help="另存 JSON 清單")
    ap.add_argument("--scan-only", metavar="DIR", help="只掃描現成目錄，不產出")
    ap.add_argument("--allow-data", action="store_true", help="--scan-only 時略過 data/ 與 docs/fixtures/（公開 repo 的工作目錄）")
    a = ap.parse_args()
    if a.scan_only:
        res = scan_tree(Path(a.scan_only), allow_data=a.allow_data, strict_mentions=a.strict_mentions)
        print_scan(res)
        return 1 if res["fails"] else 0
    if not a.out:
        ap.error("需要 --out 或 --scan-only")
    return build(Path(a.src).resolve(), Path(a.out).resolve(), not a.no_minify, a.strict_mentions,
                 Path(a.manifest) if a.manifest else None)


if __name__ == "__main__":
    sys.exit(main())
