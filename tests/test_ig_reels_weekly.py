"""IG 每週短影片：題庫合規、重疊檢查器、開關。不渲染影片。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ig_reels_weekly as R  # noqa: E402
import post_quota as Q  # noqa: E402
import pytest  # noqa: E402


def _has_cjk_font() -> bool:
    # 2026-11-09：daily.yml 的 runner 沒裝 fonts-noto-cjk，渲染測試直接 SystemExit，
    # 擋掉整條資料管線（價量、法人當天都沒更新）。沒字型就跳過，渲染驗收交給有字型的工作流。
    return any(Path(p).exists() for p, _i, _b in R.FONT_CANDIDATES)


def test_bank_all_compliant():
    bank = R.load_bank()
    assert len(bank) >= 6
    for t in bank:
        assert R.lint_topic(t) == [], t["id"]


def test_lint_catches_bad():
    t = dict(R.load_bank()[0])
    t["sub"] = "建議買進 2330"
    assert R.lint_topic(t)


def test_overlap_checker():
    assert R.check_frame([("a", (100, 300, 200, 400)), ("b", (300, 300, 400, 400))]) == []
    assert R.check_frame([("a", (100, 300, 200, 400)), ("b", (195, 300, 400, 400))])      # 重疊
    assert R.check_frame([("a", (100, 300, 200, 400)), ("b", (205, 300, 400, 400))])      # 外擴 6px 內也算
    assert R.check_frame([("a", (10, 300, 200, 400))])                                    # 出安全框


@pytest.mark.skipif(not _has_cjk_font(), reason="沒有中文字型（fonts-noto-cjk），渲染測試跳過")
def test_scene_frames_no_overlap_all_topics():
    for t in R.load_bank():
        scenes = R.build_scenes(t)
        total = sum(d for _, d, _ in scenes)
        assert 15 <= total <= 30
        for i in range(0, int(total * R.FPS), 5):
            c, _ = R.render_frame(t, scenes, i, total)
            assert R.check_frame(c.elems) == [], (t["id"], i)


def test_quota_switches():
    assert Q.reels_enabled({"ig": {"reels_weekly": True}}) and not Q.reels_enabled({"ig": {"reels_weekly": False}})
    assert Q.reels_enabled({})                      # 沒寫＝開
    assert Q.queue_allowed("ig", "2026-11-10_reel-cost.md", {"live": {}, "queue": {"manual": {"ig": False}}, "ig": {"reels_weekly": True}})
    assert not Q.queue_allowed("ig", "2026-11-10_reel-cost.md", {"live": {}, "queue": {}, "ig": {"reels_weekly": False}})
    assert Q.is_reel("2026-11-10_reel-cost.md") and not Q.is_reel("2026-11-10_news-a-1.md")
