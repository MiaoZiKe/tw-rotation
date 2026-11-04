"""2026-11-04 Andy「可以發，規則定下來」：頻道①熱點文（rule: hot_1104）的 lint 標準。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_lint as L  # noqa: E402

MAIN = (ROOT / "social/threads/queue/2026-11-04_midterm-pro-v2.md")


def _p(**kw):
    body = ("美國期中選舉結束，台股接下來 3 個月會重演歷史嗎？\n\n" + "過去六次期中選舉，加權指數選後三個月全部上漲，平均七點一個百分點，樣本有限。" * 5
            + "\n\n#美國期中選舉")
    d = dict(profile="hot", hook_type="問句", emotion="中性", main_post=body, thread_posts=[],
             reply_post="資料說明。以上為公開資料整理，非投資建議", image_count=1, tag="美國期中選舉")
    d.update(kw)
    return d


def test_hot_passes_without_funny_emotion():
    e, _ = L.lint(_p())
    assert e == [], e


def test_hot_rejects_casual_words_and_length():
    e, _ = L.lint(_p(main_post="台股會不會重演歷史？\n\n不是一路順風啦！\n\n#美國期中選舉"))
    assert any("口語" in x for x in e) and any("200–250" in x for x in e)


def test_hot_requires_question_hook():
    e, _ = L.lint(_p(hook_type="反差"))
    assert any("問句" in x for x in e)


def test_default_profile_unchanged():
    e, _ = L.lint(_p(profile=None))
    assert any("好笑／吐槽" in x for x in e)


def test_midterm_queue_file_passes():
    if MAIN.exists():
        assert L.main([str(MAIN)]) == 0
