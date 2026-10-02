"""分支預覽（DECISIONS #301）：scripts/preview_inject.py 與 pages.yml 的守門測試。"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preview_inject as pi  # noqa: E402


def test_safe_name():
    assert pi.safe_name("preview/layout-v2") == "layout-v2"
    assert pi.safe_name("preview/a/b c") == "a-b-c"
    assert pi.safe_name("preview/") == "preview"


def test_inject_html_puts_boot_first_and_is_idempotent():
    html = '<!doctype html><html><head>\n<meta charset="utf-8">\n<script>localStorage.getItem("tw.theme")</script></head><body></body></html>'
    cfg = {"name": "x", "sha": "abc1234"}
    out = pi.inject_html(html, cfg)
    # 開機腳本一定要在第一支讀 localStorage 的 inline script 之前
    assert out.index("preview_boot.js") < out.index('localStorage.getItem("tw.theme")')
    assert out.index('<meta charset="utf-8">') < out.index("twPreviewCfg")
    again = pi.inject_html(out, cfg)
    assert again.count("preview_boot.js") == 1


def test_install_skips_data_and_copies_account_config(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "account_config.js").write_text("window.TW_ACCOUNT = {api: 'https://acc'};", encoding="utf-8")
    src = tmp_path / "branch_site"
    (src / "data").mkdir(parents=True)
    (src / "data" / "big.json").write_text("{}", encoding="utf-8")
    (src / "index.html").write_text('<html><head><meta charset="utf-8"><script src="app.js"></script>'
                                    '<meta name="tw:build" content="dev|"><meta name="tw:commit" content="">'
                                    '</head><body></body></html>', encoding="utf-8")
    (src / "app.js").write_text("1", encoding="utf-8")
    (src / "account_config.js").write_text("window.TW_ACCOUNT = {api: ''};", encoding="utf-8")
    dst = pi.install("lv2", src, "82e00412ba49", "preview/lv2", site=site)
    assert dst == site / "preview" / "lv2"
    assert not (dst / "data").exists(), "資料不准每份預覽各複製一份"
    assert (dst / "preview_boot.js").exists()
    assert "https://acc" in (dst / "account_config.js").read_text(encoding="utf-8")
    html = (dst / "index.html").read_text(encoding="utf-8")
    assert '"dataRoot": "../../data/"' in html
    assert 'app.js?v=82e00412' in html
    assert 'content="82e0041"' in html   # tw:commit 用預覽分支的短碼


def test_pages_yml_preview_wiring():
    d = yaml.safe_load((ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8"))
    on = d.get("on", d.get(True))
    assert "preview/**" in on["push"]["branches"] and "main" in on["push"]["branches"]
    assert "delete" in on
    # CLAUDE.md 絕對不要做的事 #6
    assert d["concurrency"]["cancel-in-progress"] is False
    steps = d["jobs"]["deploy"]["steps"]
    names = [s.get("name", "") + str(s.get("run", "")) for s in steps]
    i_prev = next(i for i, n in enumerate(names) if "preview_inject.py" in n)
    i_upload = next(i for i, s in enumerate(steps) if "upload-pages-artifact" in str(s.get("uses", "")))
    i_acc = next(i for i, n in enumerate(names) if "ACCOUNT_API_URL" in n)
    assert i_acc < i_prev < i_upload
